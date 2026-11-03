from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Client, ClientStatus
from app.modules.contracts.models import BusinessCalendar, Contract
from app.modules.finance.models import ContractFinanceProfile, ContractInvoice


def _contract(database: Session) -> Contract:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    client = Client(code="FIN-CLIENT", name="Finance Client", status_id=status_id, is_active=True)
    database.add(client); database.flush()
    contract = Contract(contract_number="FIN-2026", client_id=client.id, name="Optional Finance", status="ACTIVE", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), calendar_id=database.scalar(select(BusinessCalendar.id)), is_active=True)
    database.add(contract); database.commit()
    return contract


def test_contract_without_finance_profile_remains_valid(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    contract = _contract(database)
    response = client.get(f"/api/v1/manager-finance/contracts/{contract.id}/summary", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() is None


def test_confirmed_allocated_receipt_drives_contract_collections(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    contract = _contract(database)
    profile = {"currency":"USD", "contract_value":"1000.0000", "tax_rate":"0.100000", "discount_amount":"0", "billing_model":"INSTALLMENT", "payment_terms_days":30}
    assert client.put(f"/api/v1/manager-finance/contracts/{contract.id}/profile", headers=admin_headers, json=profile).status_code == 200
    invoice_data = {"idempotency_key":"finance-invoice-001", "document_type":"INVOICE", "invoice_number":"INV-001", "issued_date":"2026-01-01", "due_date":"2026-01-31", "subtotal":"100.0000", "tax_amount":"10.0000", "currency":"USD", "status":"ISSUED", "reason":"Initial governed invoice."}
    invoice = client.post(f"/api/v1/manager-finance/contracts/{contract.id}/invoices", headers=admin_headers, json=invoice_data)
    duplicate = client.post(f"/api/v1/manager-finance/contracts/{contract.id}/invoices", headers=admin_headers, json=invoice_data)
    assert invoice.status_code == 201 and duplicate.json()["id"] == invoice.json()["id"]
    receipt = client.post(f"/api/v1/manager-finance/contracts/{contract.id}/receipts", headers=admin_headers, json={"idempotency_key":"finance-receipt-001", "receipt_reference":"BANK-001", "received_date":"2026-02-01", "amount":"60.0000", "currency":"USD", "status":"CONFIRMED", "reason":"Confirmed bank receipt."})
    allocation = client.post(f"/api/v1/manager-finance/contracts/{contract.id}/receipts/{receipt.json()['id']}/allocations", headers=admin_headers, json={"invoice_id":invoice.json()["id"], "amount":"60.0000", "reason":"Allocate confirmed receipt."})
    assert allocation.status_code == 201, allocation.text
    summary = client.get(f"/api/v1/manager-finance/contracts/{contract.id}/summary", headers=admin_headers).json()
    assert summary["invoiced"] == "110.0000"
    assert summary["collected"] == "60.0000"
    assert summary["outstanding"] == "50.0000"


def test_contract_finance_rejects_mixed_currency(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    contract = _contract(database)
    profile = {"currency":"USD", "billing_model":"FIXED"}
    client.put(f"/api/v1/manager-finance/contracts/{contract.id}/profile", headers=admin_headers, json=profile)
    result = client.post(f"/api/v1/manager-finance/contracts/{contract.id}/receipts", headers=admin_headers, json={"idempotency_key":"finance-receipt-eur", "receipt_reference":"BANK-EUR", "received_date":"2026-02-01", "amount":"10.0000", "currency":"EUR", "status":"CONFIRMED", "reason":"Wrong currency receipt."})
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "CONTRACT_FINANCE_CURRENCY_MISMATCH"


def test_invoice_number_is_automatic_but_can_be_overridden_and_payments_are_visible(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    contract = _contract(database)
    client.put(f"/api/v1/manager-finance/contracts/{contract.id}/profile", headers=admin_headers, json={"currency":"EGP", "billing_model":"FIXED"})
    base = {"document_type":"INVOICE", "issued_date":"2026-08-20", "due_date":"2026-09-20", "subtotal":"1000.0000", "tax_amount":"0", "currency":"EGP", "status":"ISSUED", "reason":"Regression coverage."}
    automatic = client.post(f"/api/v1/manager-finance/contracts/{contract.id}/invoices", headers=admin_headers, json={**base, "idempotency_key":"auto-invoice-001"})
    overridden = client.post(f"/api/v1/manager-finance/contracts/{contract.id}/invoices", headers=admin_headers, json={**base, "idempotency_key":"override-invoice-001", "invoice_number":"CUSTOM-2026-42"})
    assert automatic.status_code == 201, automatic.text
    assert automatic.json()["invoice_number"] == "INV-2026-000001"
    assert overridden.status_code == 201 and overridden.json()["invoice_number"] == "CUSTOM-2026-42"
    receipt = client.post(f"/api/v1/manager-finance/contracts/{contract.id}/receipts", headers=admin_headers, json={"idempotency_key":"visible-payment-001", "receipt_reference":"BANK-EGP-1", "received_date":"2026-08-20", "amount":"250.0000", "currency":"EGP", "status":"CONFIRMED", "reason":"Visible payment."})
    allocation = client.post(f"/api/v1/manager-finance/contracts/{contract.id}/receipts/{receipt.json()['id']}/allocations", headers=admin_headers, json={"invoice_id":automatic.json()["id"], "amount":"200.0000", "reason":"Partial allocation."})
    assert allocation.status_code == 201, allocation.text
    payments = client.get("/api/v1/manager-finance/payments", headers=admin_headers)
    assert payments.status_code == 200
    payment = next(row for row in payments.json() if row["receipt_id"] == receipt.json()["id"])
    assert payment["client_name"] == "Finance Client"
    assert payment["allocated"] == "200.0000" and payment["unallocated"] == "50.0000"


def test_profile_generates_monthly_schedule_and_simple_collection_statement(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    contract = _contract(database)
    saved = client.put(
        f"/api/v1/manager-finance/contracts/{contract.id}/profile",
        headers=admin_headers,
        json={"currency":"EGP", "contract_value":"1200000", "billing_model":"INSTALLMENT", "billing_frequency":"MONTHLY", "billing_day":15},
    )
    assert saved.status_code == 200, saved.text
    workspace = client.get(f"/api/v1/manager-finance/contracts/{contract.id}/collection-workspace", headers=admin_headers)
    assert workspace.status_code == 200 and len(workspace.json()) == 12
    invoice = workspace.json()[0]
    assert invoice["scheduled_amount"] == "100000.0000" and invoice["remaining"] == "100000.0000"
    confirmed = client.post(
        f"/api/v1/manager-finance/contracts/{contract.id}/invoices/{invoice['invoice']['id']}/confirm",
        headers=admin_headers,
        json={"reason": "Approved scheduled invoice."},
    )
    assert confirmed.status_code == 200 and confirmed.json()["status"] == "ISSUED"
    reason_response = client.post("/api/v1/manager-finance/adjustment-reasons", headers=admin_headers, json={"name":"SLA deduction", "adjustment_type":"DISCOUNT", "is_active":True})
    assert reason_response.status_code == 201
    reason = reason_response.json()
    assert reason["code"].startswith("FAR-")
    updated_reason = client.patch(
        f"/api/v1/manager-finance/adjustment-reasons/{reason['id']}",
        headers=admin_headers,
        json={"name": "SLA deduction updated", "adjustment_type": "BOTH", "is_active": False},
    )
    assert updated_reason.status_code == 200, updated_reason.text
    assert updated_reason.json()["name"] == "SLA deduction updated"
    assert updated_reason.json()["adjustment_type"] == "BOTH"
    assert updated_reason.json()["is_active"] is False
    listed_reasons = client.get(
        "/api/v1/manager-finance/adjustment-reasons?include_inactive=true",
        headers=admin_headers,
    )
    assert reason["id"] in {item["id"] for item in listed_reasons.json()}
    reactivate_reason = client.patch(
        f"/api/v1/manager-finance/adjustment-reasons/{reason['id']}",
        headers=admin_headers,
        json={"name": "SLA deduction updated", "adjustment_type": "BOTH", "is_active": True},
    )
    assert reactivate_reason.status_code == 200, reactivate_reason.text
    collected = client.post(
        f"/api/v1/manager-finance/contracts/{contract.id}/invoices/{invoice['invoice']['id']}/collect",
        headers=admin_headers,
        json={"idempotency_key":"simple-collection-001", "collected_date":"2026-01-15", "actual_payment":"50000", "discount_amount":"1000", "additional_amount":"0", "adjustment_reason_id":reason["id"], "adjustment_notes":"Approved SLA deduction."},
    )
    assert collected.status_code == 201, collected.text
    refreshed = client.get(f"/api/v1/manager-finance/contracts/{contract.id}/collection-workspace", headers=admin_headers).json()[0]
    assert refreshed["actual_payment"] == "50000.0000"
    assert refreshed["discounts"] == "1000.0000"
    assert refreshed["remaining"] == "49000.0000"
    statement = client.get(f"/api/v1/manager-finance/clients/{contract.client_id}/statement", headers=admin_headers)
    assert statement.status_code == 200
    totals = statement.json()["totals"][0]
    assert totals == {"currency":"EGP", "invoices":"1200000.0000", "collected":"50000.0000", "discounts":"1000.0000", "additional":"0.0000", "remaining":"1149000.0000"}
    report = client.get(f"/api/v1/manager-finance/clients/{contract.client_id}/statement.xlsx", headers=admin_headers)
    assert report.status_code == 200
    assert report.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument")
    assert report.content.startswith(b"PK")


def test_invoice_edit_confirm_cancel_and_financial_dashboard(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    contract = _contract(database)
    client.put(f"/api/v1/manager-finance/contracts/{contract.id}/profile", headers=admin_headers, json={"currency":"EGP", "contract_value":"5000", "billing_model":"FIXED"})
    created = client.post(f"/api/v1/manager-finance/contracts/{contract.id}/invoices", headers=admin_headers, json={"idempotency_key":"lifecycle-invoice-001", "document_type":"INVOICE", "invoice_number":"LIFE-1", "issued_date":"2026-08-01", "due_date":"2026-08-31", "subtotal":"1000", "tax_amount":"0", "currency":"EGP", "status":"DRAFT", "reason":"Lifecycle invoice creation."})
    assert created.status_code == 201, created.text
    invoice_id = created.json()["id"]
    edited = client.put(f"/api/v1/manager-finance/contracts/{contract.id}/invoices/{invoice_id}", headers=admin_headers, json={"invoice_number":"LIFE-1A", "issued_date":"2026-08-01", "due_date":"2026-09-15", "subtotal":"1200", "tax_amount":"100", "reason":"Approved invoice correction."})
    assert edited.status_code == 200 and edited.json()["total_amount"] == "1300.0000"
    confirmed = client.post(f"/api/v1/manager-finance/contracts/{contract.id}/invoices/{invoice_id}/confirm", headers=admin_headers, json={"reason":"Manager confirmed invoice."})
    assert confirmed.status_code == 200 and confirmed.json()["status"] == "ISSUED"
    dashboard = client.get("/api/v1/manager-finance/dashboard", headers=admin_headers)
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["period"]["previous_start"] < dashboard.json()["period"]["start"]
    assert {"trend", "clients", "aging", "invoice_status", "collected_growth_percent"} <= set(dashboard.json()["analytics"][0])
    row = next(item for item in dashboard.json()["contracts"] if item["contract_id"] == contract.id)
    assert row["contract_value"] == "5000.0000" and row["invoice_value"] == "1300.0000"
    assert row["end_date"] == contract.end_date.isoformat()
    filtered = client.get(
        "/api/v1/manager-finance/dashboard",
        headers=admin_headers,
        params={"contract_id": contract.id},
    )
    assert filtered.status_code == 200
    assert [item["contract_id"] for item in filtered.json()["contracts"]] == [contract.id]
    cancelled = client.post(f"/api/v1/manager-finance/contracts/{contract.id}/invoices/{invoice_id}/cancel", headers=admin_headers, json={"reason":"Client requested cancellation."})
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "CANCELLED"


def test_collection_workspace_reads_legacy_invoice_values_without_response_failure(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    contract = _contract(database)
    actor_id = 2
    database.add(ContractFinanceProfile(contract_id=contract.id, currency="EGP", contract_value=None, billing_model="FIXED", updated_by_user_id=actor_id))
    database.add(ContractInvoice(contract_id=contract.id, schedule_id=None, idempotency_key="legacy-invoice-read-001", document_type="INVOICE", invoice_number="LEGACY-1", issued_date=date(2025, 1, 1), due_date=date(2025, 1, 31), subtotal=0, tax_amount=0, total_amount=0, currency="EGP", status="PAID", reason="x", imported_unverified=True, created_by_user_id=actor_id))
    database.commit()
    response = client.get(f"/api/v1/manager-finance/contracts/{contract.id}/collection-workspace", headers=admin_headers)
    assert response.status_code == 200, response.text
    row = response.json()[0]
    assert row["invoice"]["status"] == "PAID"
    assert row["invoice"]["invoice_number"] == "LEGACY-1"
    assert float(row["remaining"]) == 0
