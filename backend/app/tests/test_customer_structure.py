from sqlalchemy import select

from app.modules.clients.models import Client, ClientStatus
from app.modules.iam.models import AuditLog, Department


def test_account_organization_and_client_foundation(client, admin_headers, database):
    account_response = client.post(
        "/api/v1/accounts",
        headers=admin_headers,
        json={"code": "MEG", "name": "Millensys Egypt"},
    )
    assert account_response.status_code == 201, account_response.text
    account = account_response.json()
    assert account["organization_count"] == 0

    organization_response = client.post(
        "/api/v1/organizations",
        headers=admin_headers,
        json={"account_id": account["id"], "code": "UHIA", "name": "UHIA"},
    )
    assert organization_response.status_code == 201, organization_response.text
    organization = organization_response.json()

    status_id = database.scalar(select(ClientStatus.id))
    client_response = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={
            "name": "UHIA Luxor",
            "status_id": status_id,
            "organization_id": organization["id"],
        },
    )
    assert client_response.status_code == 201, client_response.text
    assert client_response.json()["organization_id"] == organization["id"]

    accounts = client.get("/api/v1/accounts", headers=admin_headers)
    assert accounts.status_code == 200
    assert accounts.json()[0]["organization_count"] == 1

    organizations = client.get(
        "/api/v1/organizations",
        headers=admin_headers,
        params={"account_id": account["id"]},
    )
    assert organizations.status_code == 200
    assert organizations.json()[0]["client_count"] == 1

    actions = set(
        database.scalars(
            select(AuditLog.action).where(
                AuditLog.action.in_(["account.created", "organization.created"])
            )
        )
    )
    assert actions == {"account.created", "organization.created"}


def test_customer_structure_validates_relationships_and_uniqueness(client, admin_headers):
    missing_account = client.post(
        "/api/v1/organizations",
        headers=admin_headers,
        json={"account_id": 999999, "code": "UHIA", "name": "UHIA"},
    )
    assert missing_account.status_code == 404

    account = client.post(
        "/api/v1/accounts",
        headers=admin_headers,
        json={"code": "MEG", "name": "Millensys Egypt"},
    ).json()
    first = client.post(
        "/api/v1/organizations",
        headers=admin_headers,
        json={"account_id": account["id"], "code": "UHIA", "name": "UHIA"},
    )
    assert first.status_code == 201
    duplicate = client.post(
        "/api/v1/organizations",
        headers=admin_headers,
        json={"account_id": account["id"], "code": "UHIA", "name": "Duplicate"},
    )
    assert duplicate.status_code == 409


def test_bulk_assign_clients_to_organization_is_atomic_and_audited(
    client, admin_headers, database
):
    account = client.post(
        "/api/v1/accounts",
        headers=admin_headers,
        json={"code": "MEG", "name": "Millensys Egypt"},
    ).json()
    first_organization = client.post(
        "/api/v1/organizations",
        headers=admin_headers,
        json={"account_id": account["id"], "code": "ORG1", "name": "First"},
    ).json()
    second_organization = client.post(
        "/api/v1/organizations",
        headers=admin_headers,
        json={"account_id": account["id"], "code": "ORG2", "name": "Second"},
    ).json()
    status_id = database.scalar(select(ClientStatus.id))
    first_client = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"name": "Assigned", "status_id": status_id, "organization_id": first_organization["id"]},
    ).json()
    second_client = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"name": "Unassigned", "status_id": status_id},
    ).json()

    response = client.post(
        f"/api/v1/organizations/{second_organization['id']}/clients/bulk-assign",
        headers=admin_headers,
        json={
            "client_ids": [first_client["id"], second_client["id"], second_client["id"]],
            "reason": "Consolidate the customer group.",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["updated_count"] == 2
    assert response.json()["unchanged_count"] == 0
    assert database.get(Client, first_client["id"]).organization_id == second_organization["id"]
    assert database.get(Client, second_client["id"]).organization_id == second_organization["id"]
    logs = list(
        database.scalars(
            select(AuditLog).where(AuditLog.action == "client.organization_bulk_assigned")
        )
    )
    assert len(logs) == 2
    assert "Consolidate the customer group." in logs[0].new_values_json

    missing = client.post(
        f"/api/v1/organizations/{first_organization['id']}/clients/bulk-assign",
        headers=admin_headers,
        json={"client_ids": [first_client["id"], 999999], "reason": "Must be atomic."},
    )
    assert missing.status_code == 404
    database.refresh(database.get(Client, first_client["id"]))
    assert database.get(Client, first_client["id"]).organization_id == second_organization["id"]


def test_department_policy_inheritance_override_and_branch_inheritance(
    client, admin_headers, database
):
    support = Department(code="SUP", name="Support", is_active=True)
    implementation = Department(code="IMP", name="Implementation", is_active=True)
    database.add_all([support, implementation])
    database.commit()

    account = client.post(
        "/api/v1/accounts",
        headers=admin_headers,
        json={"code": "MEG", "name": "Millensys Egypt"},
    ).json()
    organization = client.post(
        "/api/v1/organizations",
        headers=admin_headers,
        json={"account_id": account["id"], "code": "UHIA", "name": "UHIA"},
    ).json()
    status_id = database.scalar(select(ClientStatus.id))
    customer = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={
            "name": "UHIA Luxor",
            "status_id": status_id,
            "organization_id": organization["id"],
        },
    ).json()
    sibling_customer = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={
            "name": "UHIA Aswan",
            "status_id": status_id,
            "organization_id": organization["id"],
        },
    ).json()
    branch = client.post(
        f"/api/v1/clients/{customer['id']}/branches",
        headers=admin_headers,
        json={"name": "Karnak"},
    ).json()

    organization_policy = client.put(
        f"/api/v1/customer-structure/organization/{organization['id']}/department-policy",
        headers=admin_headers,
        json={
            "mode": "EXTEND",
            "change_reason": "Support owns the customer organization.",
            "assignments": [
                {
                    "department_id": support.id,
                    "relationship": "PRIMARY_OWNER",
                    "access_profile": "SUPPORT_OPERATOR",
                }
            ],
        },
    )
    assert organization_policy.status_code == 200, organization_policy.text

    inherited_sibling_policy = client.get(
        f"/api/v1/customer-structure/client/{sibling_customer['id']}/department-policy",
        headers=admin_headers,
    )
    assert inherited_sibling_policy.status_code == 200
    sibling_assignments = inherited_sibling_policy.json()["assignments"]
    assert len(sibling_assignments) == 1
    assert sibling_assignments[0]["department_id"] == support.id
    assert sibling_assignments[0]["source_type"] == "ORGANIZATION"
    assert sibling_assignments[0]["inherited"] is True

    client_policy = client.put(
        f"/api/v1/customer-structure/client/{customer['id']}/department-policy",
        headers=admin_headers,
        json={
            "mode": "OVERRIDE",
            "change_reason": "Implementation is responsible during delivery.",
            "assignments": [
                {
                    "department_id": implementation.id,
                    "relationship": "TEMPORARY_OPERATOR",
                    "access_profile": "IMPLEMENTATION_OPERATOR",
                    "reason": "Implementation phase",
                }
            ],
        },
    )
    assert client_policy.status_code == 200, client_policy.text
    assignments = {item["department_id"]: item for item in client_policy.json()["assignments"]}
    assert assignments[support.id]["visibility_only"] is True
    assert assignments[support.id]["access_profile"] == "CUSTOMER_VIEWER"
    assert assignments[implementation.id]["visibility_only"] is False

    unaffected_sibling_policy = client.get(
        f"/api/v1/customer-structure/client/{sibling_customer['id']}/department-policy",
        headers=admin_headers,
    )
    assert {
        item["department_id"] for item in unaffected_sibling_policy.json()["assignments"]
    } == {support.id}

    branch_policy = client.get(
        f"/api/v1/customer-structure/branch/{branch['id']}/department-policy",
        headers=admin_headers,
    )
    assert branch_policy.status_code == 200
    assert branch_policy.json()["mode"] == "INHERIT"
    assert {item["department_id"] for item in branch_policy.json()["assignments"]} == {
        support.id,
        implementation.id,
    }

    preview = client.post(
        f"/api/v1/customer-structure/organization/{organization['id']}/department-policy/impact-preview",
        headers=admin_headers,
        json={
            "mode": "EXTEND",
            "change_reason": "Preview additional implementation access.",
            "assignments": [
                {
                    "department_id": implementation.id,
                    "relationship": "SHARED_OPERATOR",
                    "access_profile": "IMPLEMENTATION_OPERATOR",
                }
            ],
        },
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["affected_client_count"] == 2
    assert preview.json()["affected_branch_count"] == 1
