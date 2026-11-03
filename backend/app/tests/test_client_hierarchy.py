from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.hierarchy import (
    get_client_path,
    get_descendants,
    get_scope_ids,
    is_descendant,
)
from app.modules.clients.models import ClientStatus
from app.modules.iam.models import AuditLog, User, UserClientScope
from app.modules.iam.service import effective_permissions


def _create(api, headers, status_id: int, code: str, name: str, parent_client_id: int | None = None):
    response = api.post(
        "/api/v1/clients",
        headers=headers,
        json={"code": code, "name": name, "status_id": status_id, "parent_client_id": parent_client_id},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_hierarchy_traversal_endpoints_and_standalone_compatibility(client, admin_headers, database: Session) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    root = _create(client, admin_headers, status_id, "HROOT", "Hierarchy Root")
    child = _create(client, admin_headers, status_id, "HCHILD", "Hierarchy Child", root["id"])
    leaf = _create(client, admin_headers, status_id, "HLEAF", "Hierarchy Leaf", child["id"])
    standalone = _create(client, admin_headers, status_id, "HALONE", "Standalone")

    assert [item.id for item in get_client_path(database, leaf["id"])] == [root["id"], child["id"], leaf["id"]]
    assert [item.id for item in get_descendants(database, root["id"])] == [child["id"], leaf["id"]]
    assert get_scope_ids(database, root["id"], "DIRECT_CHILDREN") == [root["id"], child["id"]]
    assert is_descendant(database, root["id"], leaf["id"])

    response = client.get(f"/api/v1/clients/{root['id']}/hierarchy", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["client"]["descendant_count"] == 2
    assert response.json()["descendants"][1]["hierarchy_path"] == "Hierarchy Root > Hierarchy Child > Hierarchy Leaf"
    assert client.get(f"/api/v1/clients/{standalone['id']}", headers=admin_headers).json()["parent_client_id"] is None


def test_hierarchy_rejects_cycles_missing_parent_and_parent_delete(client, admin_headers, database: Session) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    root = _create(client, admin_headers, status_id, "CROOT", "Cycle Root")
    child = _create(client, admin_headers, status_id, "CCHILD", "Cycle Child", root["id"])

    response = client.patch(f"/api/v1/clients/{root['id']}", headers=admin_headers, json={"parent_client_id": child["id"]})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CLIENT_HIERARCHY_CYCLE"
    response = client.patch(f"/api/v1/clients/{root['id']}", headers=admin_headers, json={"parent_client_id": root["id"]})
    assert response.status_code == 409
    response = client.post("/api/v1/clients", headers=admin_headers, json={"code": "BADP", "name": "Bad Parent", "status_id": status_id, "parent_client_id": 999999})
    assert response.status_code == 404
    response = client.delete(f"/api/v1/clients/{root['id']}", headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CLIENT_HAS_CHILDREN"

    response = client.patch(f"/api/v1/clients/{child['id']}", headers=admin_headers, json={"parent_client_id": None})
    assert response.status_code == 200
    audit = database.scalar(select(AuditLog).where(AuditLog.entity_type == "Client", AuditLog.entity_id == str(child["id"]), AuditLog.action == "client.updated").order_by(AuditLog.id.desc()))
    assert audit is not None and "old_hierarchy_path" in (audit.new_values_json or "")


def test_department_master_remains_active_and_assignable(client, admin_headers, database: Session) -> None:
    response = client.post("/api/v1/departments", headers=admin_headers, json={"code": "WAVE1", "name": "Wave 1 Department", "is_active": True})
    assert response.status_code == 201, response.text
    listed = client.get("/api/v1/departments", headers=admin_headers)
    assert any(item["id"] == response.json()["id"] for item in listed.json())


def test_explicit_portal_hierarchy_scope_expands_clients_but_defaults_exact(client, admin_headers, database: Session) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    root = _create(client, admin_headers, status_id, "PSROOT", "Portal Scope Root")
    child = _create(client, admin_headers, status_id, "PSCHILD", "Portal Scope Child", root["id"])
    leaf = _create(client, admin_headers, status_id, "PSLEAF", "Portal Scope Leaf", child["id"])
    user = database.scalar(select(User).where(User.username == "admin"))
    database.add(UserClientScope(user_id=user.id, client_id=root["id"], scope_mode="CLIENT_ONLY")); database.commit()
    assert effective_permissions(database, user).client_scope_ids == [root["id"]]
    scope = database.get(UserClientScope, (user.id, root["id"]))
    scope.scope_mode = "CLIENT_AND_ALL_DESCENDANTS"; database.commit()
    assert effective_permissions(database, user).client_scope_ids == [root["id"], child["id"], leaf["id"]]
