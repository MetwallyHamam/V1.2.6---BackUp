from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Client, ClientStatus
from app.modules.contracts.models import BusinessCalendar, ContractCoverage
from app.modules.entitlements.models import EntitlementApproval
from app.modules.iam.models import AuditLog, User
from app.modules.tickets.models import Ticket, TicketType


def test_contract_customer_links_can_be_updated_incrementally(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    customers = [
        client.post(
            "/api/v1/clients",
            headers=admin_headers,
            json={
                "code": f"MULTI-{index}",
                "name": f"Multi Contract Client {index}",
                "status_id": status_id,
            },
        ).json()
        for index in range(1, 4)
    ]
    calendar_id = database.scalar(select(BusinessCalendar.id))
    created = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "MULTI-CUSTOMER-001",
            "client_id": customers[0]["id"],
            "linked_client_ids": [customers[0]["id"]],
            "is_shared_default": True,
            "name": "Multiple customer contract",
            "start_date": str(date.today() - timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=365)),
            "calendar_id": calendar_id,
        },
    )
    assert created.status_code == 201, created.text

    updated = client.patch(
        f"/api/v1/contracts/{created.json()['id']}",
        headers=admin_headers,
        json={"linked_client_ids": [item["id"] for item in customers]},
    )
    assert updated.status_code == 200, updated.text
    assert set(updated.json()["linked_client_ids"]) == {item["id"] for item in customers}
    linked = client.get(f"/api/v1/contracts/{created.json()['id']}/clients", headers=admin_headers)
    assert linked.status_code == 200, linked.text
    assert {item["id"] for item in linked.json()} == {item["id"] for item in customers}

    reduced = client.patch(
        f"/api/v1/contracts/{created.json()['id']}",
        headers=admin_headers,
        json={"linked_client_ids": [customers[0]["id"], customers[2]["id"]]},
    )
    assert reduced.status_code == 200, reduced.text
    assert set(reduced.json()["linked_client_ids"]) == {
        customers[0]["id"],
        customers[2]["id"],
    }


def test_all_matching_contract_selection_honors_exclusions_without_primary(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    customers = [
        Client(code=f"CAP-{index:04d}", name=f"Capacity Client {index:04d}", status_id=status_id)
        for index in range(413)
    ]
    database.add_all(customers)
    database.commit()
    calendar_id = database.scalar(select(BusinessCalendar.id))
    contract = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "CAPACITY-413",
            "client_id": customers[0].id,
            "linked_client_ids": [customers[0].id],
            "name": "Capacity contract",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=365)),
            "calendar_id": calendar_id,
        },
    ).json()
    intent = {
        "mode": "ALL_MATCHING",
        "search": "Capacity Client",
        "explicit_ids": [],
        "excluded_ids": [customers[0].id],
    }
    preview = client.post(
        f"/api/v1/contracts/{contract['id']}/client-selection/preview",
        headers=admin_headers,
        json=intent,
    )
    assert preview.status_code == 200
    assert preview.json()["matched_count"] == 413
    assert preview.json()["selected_count"] == 412
    assert preview.json()["primary_forced"] is False
    applied = client.post(
        f"/api/v1/contracts/{contract['id']}/client-selection/apply",
        headers=admin_headers,
        json=intent,
    )
    assert applied.status_code == 200
    assert len(applied.json()["linked_client_ids"]) == 412
    assert customers[0].id not in applied.json()["linked_client_ids"]


def test_bulk_assignments_scope_products_and_services_by_client(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    customers = [
        client.post(
            "/api/v1/clients",
            headers=admin_headers,
            json={
                "code": f"SCOPE-{index}",
                "name": f"Scoped Client {index}",
                "status_id": status_id,
            },
        ).json()
        for index in range(1, 4)
    ]
    product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "SCOPED-PRODUCT", "name": "Scoped Product"},
    ).json()
    module = client.post(
        f"/api/v1/products/{product['id']}/modules",
        headers=admin_headers,
        json={"code": "SCOPED-MODULE", "name": "Scoped Module"},
    ).json()
    service = client.post(
        "/api/v1/services",
        headers=admin_headers,
        json={"code": "SCOPED-SERVICE", "name": "Scoped Service"},
    ).json()
    calendar_id = database.scalar(select(BusinessCalendar.id))
    contract = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "ALL-CLIENTS-SCOPED",
            "client_id": customers[0]["id"],
            "name": "All clients with scoped assignments",
            "applies_to_all_clients": True,
            "is_shared_default": True,
            "start_date": str(date.today() - timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=365)),
            "calendar_id": calendar_id,
        },
    )
    assert contract.status_code == 201, contract.text
    assigned = client.post(
        f"/api/v1/contracts/{contract.json()['id']}/assignments/bulk",
        headers=admin_headers,
        json={
            "products": [{"product_id": product["id"], "module_ids": [module["id"]]}],
            "applies_to_all_clients": False,
            "client_ids": [customers[0]["id"], customers[1]["id"]],
        },
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()[0]["client_ids"] == [customers[0]["id"], customers[1]["id"]]
    all_service = client.post(
        f"/api/v1/contracts/{contract.json()['id']}/assignments/bulk",
        headers=admin_headers,
        json={"service_ids": [service["id"]], "applies_to_all_clients": True},
    )
    assert all_service.status_code == 200, all_service.text

    covered_product = client.get(
        "/api/v1/entitlements/check",
        headers=admin_headers,
        params={
            "client_id": customers[1]["id"],
            "product_id": product["id"],
            "product_module_id": module["id"],
        },
    )
    covered_product_without_optional_module = client.get(
        "/api/v1/entitlements/check",
        headers=admin_headers,
        params={"client_id": customers[1]["id"], "product_id": product["id"]},
    )
    uncovered_product = client.get(
        "/api/v1/entitlements/check",
        headers=admin_headers,
        params={
            "client_id": customers[2]["id"],
            "product_id": product["id"],
            "product_module_id": module["id"],
        },
    )
    covered_service = client.get(
        "/api/v1/entitlements/check",
        headers=admin_headers,
        params={"client_id": customers[2]["id"], "service_id": service["id"]},
    )
    assert covered_product.json()["status"] == "COVERED"
    assert covered_product_without_optional_module.json()["status"] == "COVERED"
    assert uncovered_product.json()["status"] == "NOT_COVERED"
    assert covered_service.json()["status"] == "COVERED"


def test_coverage_removal_deletes_unused_rules_and_retires_ticket_history(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    customers = [
        client.post(
            "/api/v1/clients",
            headers=admin_headers,
            json={"code": f"COVERAGE-REMOVE-{index}", "name": f"Coverage Remove {index}", "status_id": status_id},
        ).json()
        for index in range(1, 3)
    ]
    product = client.post(
        "/api/v1/products", headers=admin_headers,
        json={"code": "COVERAGE-REMOVE", "name": "Coverage Removal Product"},
    ).json()
    used_module = client.post(
        f"/api/v1/products/{product['id']}/modules", headers=admin_headers,
        json={"code": "COVERAGE-USED", "name": "Used Module"},
    ).json()
    unused_module = client.post(
        f"/api/v1/products/{product['id']}/modules", headers=admin_headers,
        json={"code": "COVERAGE-UNUSED", "name": "Unused Module"},
    ).json()
    calendar_id = database.scalar(select(BusinessCalendar.id))
    contract = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "COVERAGE-REMOVE-001",
            "client_id": customers[0]["id"],
            "linked_client_ids": [customer["id"] for customer in customers],
            "name": "Coverage removal rules",
            "start_date": str(date.today() - timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=365)),
            "calendar_id": calendar_id,
        },
    ).json()
    used_coverage = client.post(
        f"/api/v1/contracts/{contract['id']}/coverage", headers=admin_headers,
        json={"product_id": product["id"], "product_module_id": used_module["id"]},
    ).json()
    unused_coverage = client.post(
        f"/api/v1/contracts/{contract['id']}/coverage", headers=admin_headers,
        json={"product_id": product["id"], "product_module_id": unused_module["id"]},
    ).json()
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": customers[1]["id"],
            "contract_id": contract["id"],
            "product_id": product["id"],
            "product_module_id": used_module["id"],
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "Keep coverage history",
            "description": "A linked-client ticket must preserve its matching coverage rule.",
        },
    )
    assert ticket.status_code == 201, ticket.text

    removed = client.post(
        f"/api/v1/contracts/{contract['id']}/coverage/retire-batch",
        headers=admin_headers,
        json={
            "coverage_ids": [used_coverage["id"], unused_coverage["id"]],
            "reason": "Product removed from the contract workspace.",
        },
    )
    assert removed.status_code == 204, removed.text
    database.expire_all()
    assert database.get(ContractCoverage, unused_coverage["id"]) is None
    retained = database.get(ContractCoverage, used_coverage["id"])
    assert retained is not None
    assert retained.retired_at is not None
    actions = set(database.scalars(select(AuditLog.action).where(
        AuditLog.entity_type == "ContractCoverage",
        AuditLog.entity_id.in_([str(used_coverage["id"]), str(unused_coverage["id"])]),
    )))
    assert {"contract.coverage.deleted", "contract.coverage.retired"}.issubset(actions)


def test_contract_delete_is_privileged_audited_and_blocks_ticket_history(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    customer = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "DELETE-CONTRACT", "name": "Contract Delete Client", "status_id": status_id},
    ).json()
    calendar_id = database.scalar(select(BusinessCalendar.id))

    def create_contract(number: str) -> dict[str, object]:
        response = client.post(
            "/api/v1/contracts",
            headers=admin_headers,
            json={
                "contract_number": number,
                "client_id": customer["id"],
                "name": number,
                "start_date": str(date.today() - timedelta(days=1)),
                "end_date": str(date.today() + timedelta(days=365)),
                "calendar_id": calendar_id,
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    unused = create_contract("DELETE-UNUSED")
    deleted = client.delete(f"/api/v1/contracts/{unused['id']}", headers=admin_headers)
    assert deleted.status_code == 204, deleted.text
    assert client.get(f"/api/v1/contracts/{unused['id']}", headers=admin_headers).status_code == 404
    assert (
        database.scalar(
            select(AuditLog.id).where(
                AuditLog.entity_type == "Contract",
                AuditLog.entity_id == str(unused["id"]),
                AuditLog.action == "contract.deleted",
            )
        )
        is not None
    )

    used = create_contract("DELETE-USED")
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": customer["id"],
            "contract_id": used["id"],
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "Contract history must remain",
            "description": "Deleting the selected contract must be blocked after ticket creation.",
        },
    )
    assert ticket.status_code == 201, ticket.text
    blocked = client.delete(f"/api/v1/contracts/{used['id']}", headers=admin_headers)
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["error"]["code"] == "CONTRACT_IN_USE"


def test_contract_coverage_requires_audited_override(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    customer = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "ENTITLEMENT", "name": "Entitlement Client", "status_id": status_id},
    ).json()
    calendar_id = database.scalar(select(BusinessCalendar.id))
    contract = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "SUP-ENT-001",
            "client_id": customer["id"],
            "name": "Entitlement Test",
            "start_date": str(date.today() - timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=365)),
            "calendar_id": calendar_id,
        },
    )
    assert contract.status_code == 201, contract.text
    product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "EXCLUDED", "name": "Excluded Product"},
    )
    assert product.status_code == 201, product.text
    coverage = client.post(
        f"/api/v1/contracts/{contract.json()['id']}/coverage",
        headers=admin_headers,
        json={"product_id": product.json()["id"], "is_covered": False, "notes": "Not purchased"},
    )
    assert coverage.status_code == 201, coverage.text
    document = client.post(
        f"/api/v1/contracts/{contract.json()['id']}/documents",
        headers=admin_headers,
        files={"upload": ("support-contract.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
    )
    assert document.status_code == 201, document.text
    downloaded = client.get(
        f"/api/v1/contracts/{contract.json()['id']}/documents/{document.json()['id']}/download",
        headers=admin_headers,
    )
    assert downloaded.status_code == 200
    assert downloaded.content.startswith(b"%PDF-")
    removed = client.delete(
        f"/api/v1/contracts/{contract.json()['id']}/documents/{document.json()['id']}",
        headers=admin_headers,
    )
    assert removed.status_code == 204
    check = client.get(
        "/api/v1/entitlements/check",
        headers=admin_headers,
        params={"client_id": customer["id"], "product_id": product.json()["id"]},
    )
    assert check.status_code == 200
    assert check.json()["status"] == "EXCLUDED"
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    payload = {
        "ticket_type_id": ticket_type_id,
        "client_id": customer["id"],
        "product_id": product.json()["id"],
        "impact": "MEDIUM",
        "urgency": "MEDIUM",
        "subject": "Excluded product support request",
        "description": "The contract exclusion must require an explicit override.",
    }
    created = client.post("/api/v1/tickets", headers=admin_headers, json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["entitlement_status"] == "PENDING_APPROVAL"
    assert created.json()["contract_id"] == contract.json()["id"]


def test_extended_contract_releases_stale_ticket_approval_block(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    customer = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "EXTENDED-ENT", "name": "Extended Entitlement", "status_id": status_id},
    ).json()
    calendar_id = database.scalar(select(BusinessCalendar.id))
    contract = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "SUP-EXTENDED-001",
            "client_id": customer["id"],
            "name": "Expired then extended contract",
            "start_date": str(date.today() - timedelta(days=60)),
            "end_date": str(date.today() - timedelta(days=2)),
            "calendar_id": calendar_id,
        },
    )
    assert contract.status_code == 201, contract.text
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": customer["id"],
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Ticket created after contract expiry",
            "description": "The extended contract should remove the stale approval block.",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["entitlement_status"] == "PENDING_APPROVAL"

    extended = client.patch(
        f"/api/v1/contracts/{contract.json()['id']}",
        headers=admin_headers,
        json={"end_date": str(date.today() + timedelta(days=60)), "status": "ACTIVE", "is_active": True},
    )
    assert extended.status_code == 200, extended.text
    progressed = client.post(
        f"/api/v1/tickets/{created.json()['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "IN_PROGRESS",
            "reason": "Contract was extended and support work can proceed",
            "version": created.json()["version"],
        },
    )
    assert progressed.status_code == 200, progressed.text
    assert progressed.json()["entitlement_status"] == "COVERED"
    ticket = database.get(Ticket, created.json()["id"])
    assert ticket is not None and ticket.contract_id == contract.json()["id"]
    approval = database.scalar(
        select(EntitlementApproval).where(EntitlementApproval.ticket_id == ticket.id)
    )
    assert approval is not None and approval.status == "CANCELLED"


def test_contract_coverage_rejects_invalid_context_and_duplicates(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    first_client = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "COV-A", "name": "Coverage A", "status_id": status_id},
    ).json()
    second_client = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "COV-B", "name": "Coverage B", "status_id": status_id},
    ).json()
    foreign_branch = client.post(
        f"/api/v1/clients/{second_client['id']}/branches",
        headers=admin_headers,
        json={"code": "SITE-B", "name": "Foreign Site"},
    ).json()
    calendar_id = database.scalar(select(BusinessCalendar.id))
    contract = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "SUP-COV-VALIDATION",
            "client_id": first_client["id"],
            "name": "Coverage Validation",
            "start_date": str(date.today() - timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=365)),
            "calendar_id": calendar_id,
        },
    ).json()
    own_contact = client.post(
        "/api/v1/contacts",
        headers=admin_headers,
        json={
            "client_id": first_client["id"],
            "full_name": "Contract Escalation",
            "is_escalation_contact": True,
        },
    ).json()
    foreign_contact = client.post(
        "/api/v1/contacts",
        headers=admin_headers,
        json={"client_id": second_client["id"], "full_name": "Foreign Escalation"},
    ).json()
    invalid_contact = client.patch(
        f"/api/v1/contracts/{contract['id']}",
        headers=admin_headers,
        json={"escalation_contact_id": foreign_contact["id"]},
    )
    assert invalid_contact.status_code == 409
    assert invalid_contact.json()["error"]["code"] == "INVALID_ESCALATION_CONTACT"
    updated_contract = client.patch(
        f"/api/v1/contracts/{contract['id']}",
        headers=admin_headers,
        json={
            "support_summary": "24x7 database and application support",
            "exclusions": "Project work requires a separate statement of work",
            "included_request_limit": 25,
            "escalation_contact_id": own_contact["id"],
        },
    )
    assert updated_contract.status_code == 200, updated_contract.text
    assert updated_contract.json()["included_request_limit"] == 25
    assert updated_contract.json()["escalation_contact_id"] == own_contact["id"]
    product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "COVPROD", "name": "Coverage Product"},
    ).json()
    other_product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "OTHERPROD", "name": "Other Product"},
    ).json()
    module = client.post(
        f"/api/v1/products/{product['id']}/modules",
        headers=admin_headers,
        json={"code": "COVMOD", "name": "Coverage Module"},
    ).json()

    wrong_branch = client.post(
        f"/api/v1/contracts/{contract['id']}/coverage",
        headers=admin_headers,
        json={"branch_id": foreign_branch["id"]},
    )
    assert wrong_branch.status_code == 409
    assert wrong_branch.json()["error"]["code"] == "INVALID_COVERAGE_BRANCH"

    wrong_module = client.post(
        f"/api/v1/contracts/{contract['id']}/coverage",
        headers=admin_headers,
        json={"product_id": other_product["id"], "product_module_id": module["id"]},
    )
    assert wrong_module.status_code == 409
    assert wrong_module.json()["error"]["code"] == "COVERAGE_MODULE_PRODUCT_MISMATCH"

    rule = {"product_id": product["id"], "product_module_id": module["id"]}
    first = client.post(
        f"/api/v1/contracts/{contract['id']}/coverage",
        headers=admin_headers,
        json=rule,
    )
    assert first.status_code == 201, first.text
    duplicate = client.post(
        f"/api/v1/contracts/{contract['id']}/coverage",
        headers=admin_headers,
        json=rule,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_COVERAGE_RULE"


def test_included_request_limit_requires_an_audited_override(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    customer = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "LIMITED", "name": "Limited Support", "status_id": status_id},
    ).json()
    calendar_id = database.scalar(select(BusinessCalendar.id))
    contract = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "SUP-LIMIT-001",
            "client_id": customer["id"],
            "name": "One Request Contract",
            "start_date": str(date.today() - timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=30)),
            "calendar_id": calendar_id,
            "included_request_limit": 1,
        },
    )
    assert contract.status_code == 201, contract.text
    covered = client.post(
        f"/api/v1/contracts/{contract.json()['id']}/coverage",
        headers=admin_headers,
        json={"is_covered": True},
    )
    assert covered.status_code == 201, covered.text
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    payload = {
        "ticket_type_id": ticket_type_id,
        "client_id": customer["id"],
        "assigned_user_id": admin.id,
        "impact": "LOW",
        "urgency": "LOW",
        "subject": "Limited contract request",
        "description": "A request counted against the included contract allowance.",
    }
    first = client.post("/api/v1/tickets", headers=admin_headers, json=payload)
    assert first.status_code == 201, first.text
    assert first.json()["entitlement_status"] == "COVERED"
    escalated = client.post(
        f"/api/v1/tickets/{first.json()['id']}/escalation",
        headers=admin_headers,
        json={
            "escalation_assignee_user_id": admin.id,
            "escalation_level": "SENIOR_ENGINEER",
            "reason": "Allowance accounting must ignore this internal child",
            "version": first.json()["version"],
        },
    )
    assert escalated.status_code == 200, escalated.text
    usage_after_child = client.get(
        f"/api/v1/contracts/{contract.json()['id']}/usage", headers=admin_headers
    )
    assert usage_after_child.status_code == 200, usage_after_child.text
    assert usage_after_child.json()["used_requests"] == 1
    assert usage_after_child.json()["total_primary_requests"] == 1
    pending = client.post(
        "/api/v1/tickets", headers=admin_headers, json={**payload, "subject": "Second request"}
    )
    assert pending.status_code == 201, pending.text
    assert pending.json()["entitlement_status"] == "PENDING_APPROVAL"
    usage = client.get(f"/api/v1/contracts/{contract.json()['id']}/usage", headers=admin_headers)
    assert usage.status_code == 200, usage.text
    assert usage.json() == {
        "included_request_limit": 1,
        "used_requests": 1,
        "remaining_requests": 0,
        "overridden_requests": 0,
        "total_primary_requests": 2,
    }


def test_coverage_uses_specificity_and_equal_specificity_exclusion_precedence(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    customer = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "PRECEDENCE", "name": "Coverage Precedence", "status_id": status_id},
    ).json()
    branch = client.post(
        f"/api/v1/clients/{customer['id']}/branches",
        headers=admin_headers,
        json={"code": "HQ", "name": "Head Office"},
    ).json()
    product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "PRECPROD", "name": "Precedence Product"},
    ).json()
    calendar_id = database.scalar(select(BusinessCalendar.id))
    contract = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "SUP-PRECEDENCE-001",
            "client_id": customer["id"],
            "name": "Coverage Precedence Contract",
            "start_date": str(date.today() - timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=30)),
            "calendar_id": calendar_id,
            "coverage_validation_level": "FULL",
        },
    ).json()
    broad_exclusion = client.post(
        f"/api/v1/contracts/{contract['id']}/coverage",
        headers=admin_headers,
        json={"is_covered": False, "notes": "Unspecified contexts are excluded"},
    )
    assert broad_exclusion.status_code == 201, broad_exclusion.text
    product_inclusion = client.post(
        f"/api/v1/contracts/{contract['id']}/coverage",
        headers=admin_headers,
        json={"product_id": product["id"], "is_covered": True},
    )
    assert product_inclusion.status_code == 201, product_inclusion.text
    specific_result = client.get(
        "/api/v1/entitlements/check",
        headers=admin_headers,
        params={
            "client_id": customer["id"],
            "branch_id": branch["id"],
            "product_id": product["id"],
        },
    )
    assert specific_result.status_code == 200
    assert specific_result.json()["status"] == "COVERED"

    branch_exclusion = client.post(
        f"/api/v1/contracts/{contract['id']}/coverage",
        headers=admin_headers,
        json={"branch_id": branch["id"], "is_covered": False},
    )
    assert branch_exclusion.status_code == 201, branch_exclusion.text
    equal_specificity_result = client.get(
        "/api/v1/entitlements/check",
        headers=admin_headers,
        params={
            "client_id": customer["id"],
            "branch_id": branch["id"],
            "product_id": product["id"],
        },
    )
    assert equal_specificity_result.status_code == 200
    assert equal_specificity_result.json()["status"] == "EXCLUDED"


def test_customer_specific_and_shared_default_precedence_is_deterministic(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    customer = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "TIERED", "name": "Tiered Contracts", "status_id": status_id},
    ).json()
    first_product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "TIER-A", "name": "Shared Product"},
    ).json()
    second_product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "TIER-B", "name": "Specific Product"},
    ).json()
    calendar_id = database.scalar(select(BusinessCalendar.id))

    def create_contract(number: str, name: str, **extra: object) -> dict[str, object]:
        response = client.post(
            "/api/v1/contracts",
            headers=admin_headers,
            json={
                "contract_number": number,
                "client_id": customer["id"],
                "linked_client_ids": [customer["id"]],
                "name": name,
                "start_date": str(date.today() - timedelta(days=10)),
                "end_date": str(date.today() + timedelta(days=90)),
                "calendar_id": calendar_id,
                **extra,
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    shared = create_contract("SUP-TIER-SHARED", "Shared fallback", is_shared_default=True)
    specific = create_contract("SUP-TIER-SPECIFIC", "Customer-specific")
    shared_rule = client.post(
        f"/api/v1/contracts/{shared['id']}/coverage",
        headers=admin_headers,
        json={"product_id": first_product["id"], "is_covered": True},
    )
    specific_rule = client.post(
        f"/api/v1/contracts/{specific['id']}/coverage",
        headers=admin_headers,
        json={"product_id": second_product["id"], "is_covered": True},
    )
    assert shared_rule.status_code == 201, shared_rule.text
    assert specific_rule.status_code == 201, specific_rule.text

    shared_result = client.get(
        "/api/v1/entitlements/check",
        headers=admin_headers,
        params={"client_id": customer["id"], "product_id": first_product["id"]},
    )
    specific_result = client.get(
        "/api/v1/entitlements/check",
        headers=admin_headers,
        params={"client_id": customer["id"], "product_id": second_product["id"]},
    )
    assert shared_result.json()["status"] == "COVERED"
    assert shared_result.json()["contract_id"] == shared["id"]
    assert specific_result.json()["status"] == "COVERED"
    assert specific_result.json()["contract_id"] == specific["id"]

    exclusion = client.post(
        f"/api/v1/contracts/{specific['id']}/coverage",
        headers=admin_headers,
        json={
            "product_id": first_product["id"],
            "is_covered": False,
            "notes": "Customer-specific exclusion wins",
        },
    )
    assert exclusion.status_code == 201, exclusion.text
    excluded = client.get(
        "/api/v1/entitlements/check",
        headers=admin_headers,
        params={"client_id": customer["id"], "product_id": first_product["id"]},
    )
    assert excluded.json()["status"] == "EXCLUDED"
    assert excluded.json()["contract_id"] == specific["id"]

    suspended = client.patch(
        f"/api/v1/contracts/{specific['id']}",
        headers=admin_headers,
        json={"status": "SUSPENDED"},
    )
    assert suspended.status_code == 200, suspended.text
    fallback_after_suspension = client.get(
        "/api/v1/entitlements/check",
        headers=admin_headers,
        params={"client_id": customer["id"], "product_id": first_product["id"]},
    )
    assert fallback_after_suspension.json()["status"] == "COVERED"
    assert fallback_after_suspension.json()["contract_id"] == shared["id"]

    future_specific = create_contract(
        "SUP-TIER-FUTURE",
        "Future customer contract",
        start_date=str(date.today() + timedelta(days=1)),
        end_date=str(date.today() + timedelta(days=365)),
    )
    future_exclusion = client.post(
        f"/api/v1/contracts/{future_specific['id']}/coverage",
        headers=admin_headers,
        json={"product_id": first_product["id"], "is_covered": False},
    )
    assert future_exclusion.status_code == 201, future_exclusion.text
    ignored_future = client.get(
        "/api/v1/entitlements/check",
        headers=admin_headers,
        params={"client_id": customer["id"], "product_id": first_product["id"]},
    )
    assert ignored_future.json()["status"] == "COVERED"
    assert ignored_future.json()["contract_id"] == shared["id"]


def test_contract_rule_specificity_precedes_contract_recency(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    customer = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "RANKING", "name": "Rule Ranking", "status_id": status_id},
    ).json()
    product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "RANK-PRODUCT", "name": "Ranked Product"},
    ).json()
    calendar_id = database.scalar(select(BusinessCalendar.id))
    broad = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "SUP-RANK-BROAD",
            "client_id": customer["id"],
            "name": "Newer broad exclusion",
            "start_date": str(date.today() - timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=365)),
            "calendar_id": calendar_id,
        },
    ).json()
    specific = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "SUP-RANK-SPECIFIC",
            "client_id": customer["id"],
            "name": "Older specific inclusion",
            "start_date": str(date.today() - timedelta(days=30)),
            "end_date": str(date.today() + timedelta(days=30)),
            "calendar_id": calendar_id,
        },
    ).json()
    client.post(
        f"/api/v1/contracts/{broad['id']}/coverage",
        headers=admin_headers,
        json={"is_covered": False},
    )
    client.post(
        f"/api/v1/contracts/{specific['id']}/coverage",
        headers=admin_headers,
        json={"product_id": product["id"], "is_covered": True},
    )
    result = client.get(
        "/api/v1/entitlements/check",
        headers=admin_headers,
        params={"client_id": customer["id"], "product_id": product["id"]},
    )
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "COVERED"
    assert result.json()["contract_id"] == specific["id"]
