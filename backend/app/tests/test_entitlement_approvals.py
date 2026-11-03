from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Client, ClientStatus
from app.modules.contracts.models import BusinessCalendar, TicketSlaClock
from app.modules.entitlements.models import EntitlementApproval, EntitlementApprovalHistory
from app.modules.tickets.models import TicketType


def approval_payload(database: Session) -> dict[str, object]:
    client = database.scalar(select(Client).order_by(Client.id))
    if client is None:
        status = ClientStatus(
            code="APPROVAL_ACTIVE", name="Approval active", portal_allowed=True,
            ticket_creation_allowed=True, is_active=True,
        )
        database.add(status); database.flush()
        client = Client(
            code="APPROVAL_CLIENT", name="Approval Client", status_id=status.id, is_active=True
        )
        database.add(client); database.commit()
    return {
        "idempotency_key": "portal:submission:123456",
        "source_channel": "CLIENT_PORTAL",
        "reason_code": "SERVICE_NOT_COVERED",
        "requested_action": "REQUIRE_APPROVAL",
        "justification": "Client requests support outside the contracted service.",
        "request_payload": {"subject": "Outside scope request"},
        "evidence": {"client_id": client.id, "service_id": 99},
        "feature_mode": "ENFORCED",
        "policy_version": 4,
        "policy_scope": f"CLIENT:{client.id}",
        "client_id": client.id,
    }


def test_duplicate_submission_returns_one_approval(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    payload = approval_payload(database)
    first = client.post("/api/v1/entitlement-approvals", json=payload, headers=admin_headers)
    second = client.post("/api/v1/entitlement-approvals", json=payload, headers=admin_headers)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]
    assert database.query(EntitlementApproval).count() == 1
    assert database.query(EntitlementApprovalHistory).count() == 1


def test_pending_approval_can_be_decided_once(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    created = client.post(
        "/api/v1/entitlement-approvals",
        json=approval_payload(database),
        headers=admin_headers,
    )
    approval_id = created.json()["id"]
    decision = client.post(
        f"/api/v1/entitlement-approvals/{approval_id}/decision",
        json={"decision": "APPROVED", "comment": "Approved for this customer request."},
        headers=admin_headers,
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()["status"] == "APPROVED"
    assert [row["to_status"] for row in decision.json()["history"]] == ["PENDING", "APPROVED"]
    repeated = client.post(
        f"/api/v1/entitlement-approvals/{approval_id}/decision",
        json={"decision": "REJECTED", "comment": "A second decision must fail."},
        headers=admin_headers,
    )
    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "APPROVAL_ALREADY_DECIDED"


def test_internal_out_of_contract_ticket_reaches_queue_filter_and_dashboard(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    customer = client.post("/api/v1/clients", headers=admin_headers, json={
        "code": "APPROVAL-E2E", "name": "Approval E2E Client", "status_id": status_id,
    }).json()
    calendar_id = database.scalar(select(BusinessCalendar.id))
    contract = client.post("/api/v1/contracts", headers=admin_headers, json={
        "contract_number": "APPROVAL-E2E-2026", "client_id": customer["id"],
        "name": "Approval E2E Contract", "start_date": str(date.today() - timedelta(days=1)),
        "end_date": str(date.today() + timedelta(days=30)), "calendar_id": calendar_id,
    })
    assert contract.status_code == 201, contract.text
    product = client.post("/api/v1/products", headers=admin_headers, json={
        "code": "APPROVAL-E2E-PRODUCT", "name": "Uncovered approval product",
    }).json()
    service = client.post("/api/v1/services", headers=admin_headers, json={
        "code": "APPROVAL-E2E-SERVICE", "name": "Uncovered approval service",
    }).json()
    excluded = client.post(f"/api/v1/contracts/{contract.json()['id']}/coverage", headers=admin_headers, json={
        "product_id": product["id"], "service_id": service["id"], "is_covered": False,
    })
    assert excluded.status_code == 201, excluded.text
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    created = client.post("/api/v1/tickets", headers=admin_headers, json={
        "ticket_type_id": ticket_type_id, "client_id": customer["id"],
        "product_id": product["id"], "service_id": service["id"], "source_channel": "WEB",
        "impact": "MEDIUM", "urgency": "MEDIUM", "priority": "P3",
        "subject": "Approval workflow verification", "description": "Verify the complete pending approval workflow.",
        "request_entitlement_approval": True,
        "entitlement_approval_justification": "Manager approval is required for this uncovered service.",
        "submission_idempotency_key": "approval-e2e-submission-001",
    })
    assert created.status_code == 201, created.text
    assert created.json()["entitlement_status"] == "PENDING_APPROVAL"
    ticket_id = created.json()["id"]

    queue = client.get("/api/v1/entitlement-approvals", params={"status": "PENDING"}, headers=admin_headers)
    assert queue.status_code == 200, queue.text
    assert any(item["ticket_id"] == ticket_id for item in queue.json())

    filtered = client.get("/api/v1/tickets", params={"entitlement_status": "PENDING_APPROVAL", "limit": 100}, headers=admin_headers)
    assert filtered.status_code == 200, filtered.text
    assert any(item["id"] == ticket_id for item in filtered.json())

    dashboard = client.get("/api/v1/dashboards/summary", headers=admin_headers)
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["pending_approvals"] >= 1


def test_product_only_contract_ignores_service_for_entitlement(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    customer = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "PRODUCT-POLICY", "name": "Product Policy", "status_id": status_id},
    ).json()
    product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "PRODUCT-POLICY-P", "name": "Covered Product"},
    ).json()
    service = client.post(
        "/api/v1/services",
        headers=admin_headers,
        json={"code": "PRODUCT-POLICY-S", "name": "Classification Service"},
    ).json()
    calendar_id = database.scalar(select(BusinessCalendar.id))
    contract = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "PRODUCT-POLICY-2026",
            "client_id": customer["id"],
            "name": "Product-only contract",
            "start_date": str(date.today() - timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=30)),
            "calendar_id": calendar_id,
            "coverage_validation_level": "PRODUCT",
            "has_sla": False,
        },
    ).json()
    assert client.post(
        f"/api/v1/contracts/{contract['id']}/coverage",
        headers=admin_headers,
        json={"product_id": product["id"], "is_covered": True},
    ).status_code == 201
    result = client.get(
        "/api/v1/entitlements/check",
        headers=admin_headers,
        params={
            "client_id": customer["id"],
            "product_id": product["id"],
            "service_id": service["id"],
        },
    )
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "COVERED"
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": customer["id"],
            "product_id": product["id"],
            "service_id": service["id"],
            "impact": "LOW",
            "urgency": "LOW",
            "priority": "P4",
            "subject": "Covered contract without SLA",
            "description": "The active covered contract intentionally has no SLA clocks.",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["entitlement_status"] == "COVERED"
    assert database.scalar(
        select(TicketSlaClock.id).where(TicketSlaClock.ticket_id == created.json()["id"])
    ) is None


def test_expired_contract_uses_grace_then_automatic_pending_approval(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    customer = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "GRACE-POLICY", "name": "Grace Policy", "status_id": status_id},
    ).json()
    product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "GRACE-POLICY-P", "name": "Grace Product"},
    ).json()
    calendar_id = database.scalar(select(BusinessCalendar.id))
    contract = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "GRACE-POLICY-2026",
            "client_id": customer["id"],
            "name": "Expired contract with grace",
            "status": "EXPIRED",
            "start_date": str(date.today() - timedelta(days=30)),
            "end_date": str(date.today() - timedelta(days=1)),
            "calendar_id": calendar_id,
            "coverage_validation_level": "PRODUCT",
            "expiry_grace_days": 5,
            "has_sla": False,
            "is_active": False,
        },
    ).json()
    assert client.post(
        f"/api/v1/contracts/{contract['id']}/coverage",
        headers=admin_headers,
        json={"product_id": product["id"], "is_covered": True},
    ).status_code == 201
    grace = client.get(
        "/api/v1/entitlements/check",
        headers=admin_headers,
        params={"client_id": customer["id"], "product_id": product["id"]},
    )
    assert grace.status_code == 200, grace.text
    assert grace.json()["status"] == "GRACE_COVERAGE"

    updated = client.patch(
        f"/api/v1/contracts/{contract['id']}",
        headers=admin_headers,
        json={"expiry_grace_days": 0},
    )
    assert updated.status_code == 200, updated.text
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": customer["id"],
            "product_id": product["id"],
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "priority": "P3",
            "subject": "Expired contract approval",
            "description": "Preserve this request and route it for contract approval.",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["entitlement_status"] == "PENDING_APPROVAL"
    approval = database.scalar(
        select(EntitlementApproval).where(EntitlementApproval.ticket_id == created.json()["id"])
    )
    assert approval is not None
    assert approval.reason_code == "EXPIRED_CONTRACT"
    assert approval.contract_id == contract["id"]
