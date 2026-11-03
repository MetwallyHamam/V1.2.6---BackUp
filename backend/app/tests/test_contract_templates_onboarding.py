from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Client, ClientDepartmentLink, ClientStatus
from app.modules.contracts.models import BusinessCalendar, Contract, ContractTemplate
from app.modules.dashboards.models import SavedView
from app.modules.iam.models import Department
from app.modules.project_handovers.models import HandoverSourceTemplate


def setup_catalog(database: Session) -> tuple[ClientStatus, Department, BusinessCalendar]:
    status = ClientStatus(
        code="ONBOARD_ACTIVE",
        name="Onboarding active",
        portal_allowed=True,
        ticket_creation_allowed=True,
        is_active=True,
    )
    department = Department(code="ONBOARD_SUPPORT", name="Onboarding Support", is_active=True)
    calendar = BusinessCalendar(
        code="ONBOARD_CAL",
        name="Onboarding calendar",
        timezone="Africa/Cairo",
        is_active=True,
    )
    database.add_all([status, department, calendar])
    database.commit()
    return status, department, calendar


def create_template(client: TestClient, headers: dict[str, str], calendar_id: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/contract-templates",
        headers=headers,
        json={
            "name": "Global starter",
            "template_type": "GLOBAL",
            "calendar_id": calendar_id,
            "default_duration_months": 12,
            "has_sla": True,
            "ticket_catalog_visibility": "CONTRACT_ONLY",
            "is_default": True,
            "is_active": True,
            "coverages": [],
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["code"].startswith("CTP-")
    return response.json()


def test_atomic_onboarding_generates_codes_and_snapshots_template(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status, department, calendar = setup_catalog(database)
    template = create_template(client, admin_headers, calendar.id)
    accepted = date(2026, 8, 22)
    response = client.post(
        "/api/v1/clients/onboard",
        headers=admin_headers,
        json={
            "client": {
                "name": "Template Client",
                "status_id": status.id,
                "owner_department_id": department.id,
                "timezone": "Africa/Cairo",
                "is_active": True,
            },
            "contact": {"full_name": "Optional Contact", "email": "contact@example.com"},
            "contract": {
                "template_id": template["id"],
                "expected_template_version": template["version"],
                "acceptance_date": accepted.isoformat(),
                "idempotency_key": "onboard-template-client-001",
                "change_overrides": {},
            },
            "source": "CLIENT_SETUP",
        },
    )
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["client_code"].startswith("CLI-")
    assert result["contact_code"].startswith("CON-")
    assert result["contract_number"].startswith("CTR-2026-")
    contract = database.get(Contract, result["contract_id"])
    assert contract is not None
    assert contract.acceptance_date == accepted
    assert contract.start_date == accepted
    assert contract.end_date == date(2027, 8, 21)
    assert contract.source_template_id == template["id"]
    assert contract.source_template_version == template["version"]

    update = client.patch(
        f"/api/v1/contract-templates/{template['id']}",
        headers=admin_headers,
        json={**template, "name": "Changed template", "default_duration_months": 24},
    )
    assert update.status_code == 200, update.text
    database.refresh(contract)
    assert contract.end_date == date(2027, 8, 21)
    assert contract.name == "Template Client — Global starter"


def test_client_only_then_create_separate_contract_is_idempotent(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status, department, calendar = setup_catalog(database)
    template = create_template(client, admin_headers, calendar.id)
    onboard = client.post(
        "/api/v1/clients/onboard",
        headers=admin_headers,
        json={
            "client": {
                "name": "Client Without Contract",
                "status_id": status.id,
                "owner_department_id": department.id,
                "timezone": "Africa/Cairo",
            },
            "contact": None,
            "contract": None,
            "source": "DELIVERY_PROJECT",
        },
    )
    assert onboard.status_code == 201, onboard.text
    assert onboard.json()["contract_id"] is None
    client_id = onboard.json()["client_id"]
    payload = {
        "template_id": template["id"],
        "expected_template_version": template["version"],
        "acceptance_date": "2026-08-22",
        "idempotency_key": "existing-client-contract-001",
        "change_overrides": {},
    }
    first = client.post(f"/api/v1/clients/{client_id}/contracts/from-template", headers=admin_headers, json=payload)
    second = client.post(f"/api/v1/clients/{client_id}/contracts/from-template", headers=admin_headers, json=payload)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]
    assert database.scalar(select(Client).where(Client.id == client_id)) is not None
    assert len(database.scalars(select(Contract).where(Contract.client_id == client_id)).all()) == 1
    assert database.scalar(select(ContractTemplate).where(ContractTemplate.id == template["id"])) is not None


def test_client_can_be_shared_with_multiple_departments(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status, owner, _ = setup_catalog(database)
    shared_a = Department(code="SHARED_A", name="Shared A", is_active=True)
    shared_b = Department(code="SHARED_B", name="Shared B", is_active=True)
    database.add_all([shared_a, shared_b])
    database.commit()
    response = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={
            "name": "Multi Department Client",
            "status_id": status.id,
            "owner_department_id": owner.id,
            "shared_department_ids": [owner.id, shared_a.id, shared_b.id],
            "timezone": "Africa/Cairo",
        },
    )
    assert response.status_code == 201, response.text
    assert set(response.json()["shared_department_ids"]) == {shared_a.id, shared_b.id}
    links = database.scalars(
        select(ClientDepartmentLink).where(ClientDepartmentLink.client_id == response.json()["id"])
    ).all()
    assert {link.department_id for link in links} == {shared_a.id, shared_b.id}


def test_department_creation_provisions_escalation_saved_views(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    response = client.post(
        "/api/v1/departments",
        headers=admin_headers,
        json={"name": "Automatic Queue", "is_active": True},
    )
    assert response.status_code == 201, response.text
    assert response.json()["code"].startswith("DEP-")
    rows = database.scalars(
        select(SavedView).where(SavedView.department_id == response.json()["id"])
    ).all()
    assert {row.name.split(" — ")[-1] for row in rows} == {
        "Escalations Received",
        "New Department Requests",
        "Department Work In Progress",
        "Escalations Sent",
        "Resolved / Returned",
    }
    assert all(row.scope == "DEPARTMENT" for row in rows)


def test_contract_template_types_are_managed_master_data(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    seeded = client.get("/api/v1/contract-template-types", headers=admin_headers)
    assert seeded.status_code == 200, seeded.text
    assert "GLOBAL" in {row["code"] for row in seeded.json()}

    created = client.post(
        "/api/v1/contract-template-types",
        headers=admin_headers,
        json={"name": "Cloud Services", "description": "Cloud service agreements", "is_active": True},
    )
    assert created.status_code == 201, created.text
    assert created.json()["code"].startswith("CTT-")

    updated = client.patch(
        f"/api/v1/contract-template-types/{created.json()['id']}",
        headers=admin_headers,
        json={"name": "Managed Cloud", "description": "Managed cloud agreements", "is_active": True},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Managed Cloud"

    deleted = client.delete(
        f"/api/v1/contract-template-types/{created.json()['id']}", headers=admin_headers
    )
    assert deleted.status_code == 204, deleted.text


def test_delivery_project_number_is_generated_automatically(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status, department, _ = setup_catalog(database)
    created_client = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={
            "name": "Delivery Number Client",
            "status_id": status.id,
            "owner_department_id": department.id,
            "timezone": "Africa/Cairo",
        },
    )
    assert created_client.status_code == 201, created_client.text
    handover = client.post(
        "/api/v1/project-handovers",
        headers=admin_headers,
        json={
            "project_name": "Automatic Number Project",
            "client_id": created_client.json()["id"],
            "recipient_user_ids": [],
            "current_status": "DRAFT",
            "products": [],
        },
    )
    assert handover.status_code == 201, handover.text
    assert handover.json()["project_number"].startswith("PRJ-2026-")
    updated = client.patch(
        f"/api/v1/project-handovers/{handover.json()['id']}",
        headers=admin_headers,
        json={
            "project_name": "Updated Pending Project",
            "client_id": created_client.json()["id"],
            "recipient_user_ids": [],
            "current_status": "READY",
            "pending_points": "Awaiting final customer sign-off",
            "products": [],
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["project_name"] == "Updated Pending Project"
    assert updated.json()["pending_points"] == "Awaiting final customer sign-off"
    finalized = client.patch(
        f"/api/v1/project-handovers/{handover.json()['id']}",
        headers=admin_headers,
        json={
            "project_name": "Updated Pending Project",
            "client_id": created_client.json()["id"],
            "recipient_user_ids": [],
            "current_status": "DELIVERED",
            "products": [],
        },
    )
    assert finalized.status_code == 200, finalized.text
    locked = client.patch(
        f"/api/v1/project-handovers/{handover.json()['id']}",
        headers=admin_headers,
        json={
            "project_name": "Forbidden Final Edit",
            "client_id": created_client.json()["id"],
            "recipient_user_ids": [],
            "current_status": "DELIVERED",
            "products": [],
        },
    )
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "HANDOVER_FINALIZED"


def test_project_handover_keeps_multiple_template_versions(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status, department, calendar = setup_catalog(database)
    first = create_template(client, admin_headers, calendar.id)
    second_response = client.post(
        "/api/v1/contract-templates",
        headers=admin_headers,
        json={
            "name": "Additional delivery scope",
            "template_type": "GLOBAL",
            "calendar_id": calendar.id,
            "default_duration_months": 12,
            "has_sla": True,
            "ticket_catalog_visibility": "CONTRACT_ONLY",
            "is_default": False,
            "is_active": True,
            "coverages": [],
        },
    )
    assert second_response.status_code == 201, second_response.text
    second = second_response.json()
    customer = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={
            "name": "Multi-template delivery customer",
            "status_id": status.id,
            "owner_department_id": department.id,
            "timezone": "Africa/Cairo",
        },
    )
    assert customer.status_code == 201, customer.text
    sources = [
        {"template_id": first["id"], "template_version": first["version"]},
        {"template_id": second["id"], "template_version": second["version"]},
    ]
    handover = client.post(
        "/api/v1/project-handovers",
        headers=admin_headers,
        json={
            "project_name": "Combined template project",
            "client_id": customer.json()["id"],
            "recipient_user_ids": [],
            "current_status": "DRAFT",
            "source_templates": sources,
            "products": [],
        },
    )
    assert handover.status_code == 201, handover.text
    assert handover.json()["source_templates"] == sources
    stored = list(
        database.scalars(
            select(HandoverSourceTemplate).where(
                HandoverSourceTemplate.handover_id == handover.json()["id"]
            )
        )
    )
    assert {(row.template_id, row.template_version) for row in stored} == {
        (first["id"], first["version"]),
        (second["id"], second["version"]),
    }
