from datetime import timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.modules.clients.models import Client, ClientStatus
from app.modules.entitlements.models import EntitlementApproval
from app.modules.finance.models import TicketCommercialDecision, TicketFinanceLedgerEntry
from app.modules.iam.models import User
from app.modules.tickets.models import Ticket, TicketStatus, TicketType


def test_approval_group_code_is_generated_automatically(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/entitlement-approvals/groups",
        headers=admin_headers,
        json={"name": "Automatic Approval Group", "member_user_ids": [], "is_active": True},
    )
    assert response.status_code == 201, response.text
    assert response.json()["code"].startswith("AGR-")


def _ticket(database: Session) -> Ticket:
    client = database.scalar(select(Client).order_by(Client.id))
    if not client:
        status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
        client = Client(code="FINANCE-CLIENT", name="Finance Client", status_id=status_id, is_active=True)
        database.add(client); database.flush()
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    status_id = database.scalar(select(TicketStatus.id).where(TicketStatus.code == "NEW"))
    actor = database.scalar(select(User).where(User.username == "admin"))
    ticket = Ticket(ticket_number="INC-FINANCE-0001", ticket_type_id=ticket_type_id, client_id=client.id, created_by_user_id=actor.id, status_id=status_id, impact="MEDIUM", urgency="MEDIUM", priority="P3", subject="Finance governance test", description="Verify append-only finance evidence and confirmed collection handling.")
    database.add(ticket); database.commit()
    return ticket


def test_approval_consumption_is_exact_and_one_time(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    ticket = _ticket(database)
    actor = database.scalar(select(User).where(User.username == "admin"))
    approval = EntitlementApproval(idempotency_key="scope-consume-0001", source_channel="WEB", status="APPROVED", reason_code="INACTIVE_CLIENT", requested_action="CREATE_INACTIVE_CLIENT_TICKET", justification="Explicit exception for one operation.", request_payload_json="{}", evidence_json="{}", feature_mode="ENFORCED", policy_version=1, policy_scope=f"CLIENT:{ticket.client_id}", operation_scope=f"TICKET:{ticket.id}:CREATE", client_id=ticket.client_id, ticket_id=ticket.id, requested_by_user_id=actor.id, decided_by_user_id=actor.id, decided_at=server_now(), version=2)
    database.add(approval); database.commit()
    wrong = client.post(f"/api/v1/entitlement-approvals/{approval.id}/consume", headers=admin_headers, json={"operation_scope":f"TICKET:{ticket.id}:DELETE", "version":2, "comment":"Attempt wrong operation"})
    assert wrong.status_code == 409
    consumed = client.post(f"/api/v1/entitlement-approvals/{approval.id}/consume", headers=admin_headers, json={"operation_scope":f"TICKET:{ticket.id}:CREATE", "version":2, "comment":"Create the approved ticket"})
    assert consumed.status_code == 200, consumed.text
    repeated = client.post(f"/api/v1/entitlement-approvals/{approval.id}/consume", headers=admin_headers, json={"operation_scope":f"TICKET:{ticket.id}:CREATE", "version":3, "comment":"Attempt reuse"})
    assert repeated.status_code == 409


def test_finance_ledger_only_counts_confirmed_collections(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    ticket = _ticket(database)
    decision = client.post(f"/api/v1/manager-finance/tickets/{ticket.id}/decisions", headers=admin_headers, json={"chargeability":"CHARGEABLE", "approval_status":"APPROVED", "estimated_amount":"150.0000", "quoted_amount":"125.0000", "currency":"USD", "reason":"Customer approved the quoted out-of-contract work.", "expected_sequence":0})
    assert decision.status_code == 201, decision.text
    stale = client.post(f"/api/v1/manager-finance/tickets/{ticket.id}/decisions", headers=admin_headers, json={"chargeability":"NON_CHARGEABLE", "approval_status":"APPROVED", "currency":"USD", "reason":"A stale overwrite must not be accepted.", "expected_sequence":0})
    assert stale.status_code == 409
    base = {"currency":"USD", "occurred_at":server_now().isoformat(), "reason":"Commercial evidence recorded for reconciliation."}
    for key, entry_type, status, amount, reference in (("billable-1", "BILLABLE", "CONFIRMED", "125.0000", None), ("invoice-1", "INVOICE", "CONFIRMED", "125.0000", "INV-100"), ("collection-pending", "COLLECTION", "PENDING", "125.0000", None), ("collection-confirmed", "COLLECTION", "CONFIRMED", "50.0000", "BANK-100")):
        result = client.post(f"/api/v1/manager-finance/tickets/{ticket.id}/ledger", headers=admin_headers, json={**base, "idempotency_key":key, "entry_type":entry_type, "status":status, "amount":amount, "external_reference":reference, "payment_method":"BANK_TRANSFER" if entry_type == "COLLECTION" and status == "CONFIRMED" else None})
        assert result.status_code == 201, result.text
    view = client.get(f"/api/v1/manager-finance/tickets/{ticket.id}", headers=admin_headers)
    assert view.status_code == 200
    totals = view.json()["totals"][0]
    assert totals["collected"] == "50.0000"
    assert totals["outstanding"] == "75.0000"
    assert database.query(TicketCommercialDecision).count() == 1
    assert database.query(TicketFinanceLedgerEntry).count() == 4


def test_confirmed_collection_requires_external_reference(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    ticket = _ticket(database)
    response = client.post(f"/api/v1/manager-finance/tickets/{ticket.id}/ledger", headers=admin_headers, json={"idempotency_key":"collection-no-reference", "entry_type":"COLLECTION", "status":"CONFIRMED", "amount":"10.0000", "currency":"USD", "reason":"Missing bank reference must be rejected.", "occurred_at":(server_now()-timedelta(minutes=1)).isoformat()})
    assert response.status_code == 422


def test_confirmed_collection_requires_payment_method(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    ticket = _ticket(database)
    response = client.post(f"/api/v1/manager-finance/tickets/{ticket.id}/ledger", headers=admin_headers, json={"idempotency_key":"collection-no-method", "entry_type":"COLLECTION", "status":"CONFIRMED", "amount":"10", "currency":"USD", "external_reference":"BANK-101", "reason":"Missing payment method must be rejected.", "occurred_at":server_now().isoformat()})
    assert response.status_code == 422


def test_ticket_payment_uses_selected_ticket_client_and_enforces_balance(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    ticket = _ticket(database)
    now = server_now().isoformat()
    payload = {
        "idempotency_key": "ticket-payment-001",
        "amount": "40",
        "currency": "USD",
        "payment_method": "BANK_TRANSFER",
        "reference": "BANK-TICKET-001",
        "paid_at": now,
        "notes": "First client payment for this ticket.",
    }
    payment = client.post(
        f"/api/v1/manager-finance/tickets/{ticket.id}/payments",
        headers=admin_headers,
        json=payload,
    )
    assert payment.status_code == 201
    assert payment.json()["entry_type"] == "COLLECTION"
    assert payment.json()["amount"] == "40.0000"

    finance = client.get(
        f"/api/v1/manager-finance/tickets/{ticket.id}", headers=admin_headers
    ).json()
    assert finance["client_id"] == ticket.client_id
    assert finance["totals"][0]["invoiced"] == "40.0000"
    assert finance["totals"][0]["collected"] == "40.0000"
    assert Decimal(finance["totals"][0]["outstanding"]) == Decimal()
    assert [entry["entry_type"] for entry in finance["entries"]] == ["INVOICE", "COLLECTION"]

    repeated = client.post(
        f"/api/v1/manager-finance/tickets/{ticket.id}/payments",
        headers=admin_headers,
        json=payload,
    )
    assert repeated.status_code == 201
    assert repeated.json()["id"] == payment.json()["id"]

    second = client.post(
        f"/api/v1/manager-finance/tickets/{ticket.id}/payments",
        headers=admin_headers,
        json={**payload, "idempotency_key": "ticket-payment-002", "amount": "61", "reference": "BANK-TICKET-002"},
    )
    assert second.status_code == 201
    finance = client.get(
        f"/api/v1/manager-finance/tickets/{ticket.id}", headers=admin_headers
    ).json()
    assert finance["totals"][0]["invoiced"] == "101.0000"
    assert finance["totals"][0]["collected"] == "101.0000"
    assert Decimal(finance["totals"][0]["outstanding"]) == Decimal()


def test_overdue_exception_is_expired_once(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    ticket = _ticket(database)
    actor = database.scalar(select(User).where(User.username == "admin"))
    approval = EntitlementApproval(idempotency_key="expired-exception-0001", source_channel="WEB", status="PENDING", reason_code="COVERAGE_EXCEPTION", requested_action="OVERRIDE_COVERAGE", justification="Temporary approval window for uncovered work.", request_payload_json="{}", evidence_json="{}", feature_mode="ENFORCED", policy_version=1, policy_scope=f"CLIENT:{ticket.client_id}", operation_scope=f"TICKET:{ticket.id}:OVERRIDE_COVERAGE", client_id=ticket.client_id, ticket_id=ticket.id, requested_by_user_id=actor.id, approval_deadline=server_now()-timedelta(minutes=1), version=1)
    database.add(approval); database.commit()
    first = client.post("/api/v1/entitlement-approvals/expire-overdue", headers=admin_headers)
    second = client.post("/api/v1/entitlement-approvals/expire-overdue", headers=admin_headers)
    assert first.json() == {"expired": 1}
    assert second.json() == {"expired": 0}
