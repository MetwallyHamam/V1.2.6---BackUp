from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.modules.clients.models import Client, ClientStatus
from app.modules.configuration.models import FeaturePolicy
from app.modules.contracts.models import (
    BusinessCalendar,
    Contract,
    ContractClientLink,
    ContractType,
)
from app.modules.contracts.service import evaluate_entitlement
from app.modules.iam.models import User


def setup_contract_context(db: Session) -> tuple[Client, BusinessCalendar]:
    status = ClientStatus(code="TYPE_ACTIVE", name="Type active", portal_allowed=True, ticket_creation_allowed=True, is_active=True)
    calendar = BusinessCalendar(code="TYPE_CAL", name="Type calendar", timezone="Africa/Cairo", is_active=True)
    db.add_all([status, calendar]); db.flush()
    client = Client(code="TYPE_CLIENT", name="Type Client", status_id=status.id, is_active=True)
    db.add(client); db.commit()
    return client, calendar


def contract_payload(client_id: int, calendar_id: int, number: str, **extra: object) -> dict[str, object]:
    return {
        "contract_number": number, "client_id": client_id, "name": number,
        "status": "ACTIVE", "start_date": date.today().isoformat(),
        "end_date": (date.today() + timedelta(days=365)).isoformat(),
        "calendar_id": calendar_id, "is_active": True, **extra,
    }


def test_contract_type_catalog_management(client: TestClient, admin_headers: dict[str, str]) -> None:
    catalog = client.get("/api/v1/contract-types", headers=admin_headers)
    assert catalog.status_code == 200
    assert {item["code"] for item in catalog.json()} >= {"LEGACY", "WARRANTY", "SUPPORT", "SERVICE"}
    created = client.post("/api/v1/contract-types", headers=admin_headers, json={
        "name":"Managed Service", "description":"Managed support",
        "precedence":50, "default_has_sla":False, "default_duration_days":730,
        "expiry_behavior":"CONTINUE_WITH_APPROVAL", "approval_behavior":"REQUIRE_APPROVAL", "is_active":True,
    })
    assert created.status_code == 201, created.text
    assert created.json()["code"].startswith("CTY-")
    assert created.json()["is_system"] is False
    updated = client.put(f"/api/v1/contract-types/{created.json()['id']}", headers=admin_headers, json={**created.json(), "name":"Managed Service Plus"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Managed Service Plus"


def test_contract_type_clients_are_counted_searched_and_paginated(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    primary, calendar = setup_contract_context(database)
    status = database.get(ClientStatus, primary.status_id)
    assert status is not None
    linked = Client(code="TYPE_LINKED", name="Linked Client", status_id=status.id, is_active=True)
    kind = ContractType(code="CLIENT_COUNT", name="Client Count", precedence=40, default_has_sla=True, expiry_behavior="EXPIRE", approval_behavior="INHERIT", is_active=True)
    database.add_all([linked, kind]); database.flush()
    contract = Contract(contract_number="TYPE-CLIENTS", client_id=primary.id, contract_type_id=kind.id, name="Typed contract", status="ACTIVE", start_date=date.today(), end_date=date.today()+timedelta(days=365), calendar_id=calendar.id, is_active=True)
    database.add(contract); database.flush()
    database.add(ContractClientLink(contract_id=contract.id, client_id=linked.id)); database.commit()

    catalog = client.get("/api/v1/contract-types", headers=admin_headers)
    row = next(item for item in catalog.json() if item["id"] == kind.id)
    assert row["linked_client_count"] == 2

    page = client.get(f"/api/v1/contract-types/{kind.id}/clients", headers=admin_headers, params={"limit": 1, "offset": 1})
    assert page.status_code == 200, page.text
    assert page.json()["total"] == 2
    assert len(page.json()["items"]) == 1
    searched = client.get(f"/api/v1/contract-types/{kind.id}/clients", headers=admin_headers, params={"search": "LINKED"})
    assert searched.status_code == 200
    assert searched.json()["total"] == 1
    assert searched.json()["items"][0]["code"] == "TYPE_LINKED"


def test_off_mode_preserves_legacy_contract_creation(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    scoped_client, calendar = setup_contract_context(database)
    response = client.post("/api/v1/contracts", headers=admin_headers, json=contract_payload(scoped_client.id, calendar.id, "TYPE-OFF"))
    assert response.status_code == 201, response.text
    legacy = database.scalar(select(ContractType).where(ContractType.code == "LEGACY"))
    assert response.json()["contract_type_id"] == legacy.id
    assert response.json()["has_sla"] is True


def test_enforced_mode_requires_type_and_applies_sla_default(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    scoped_client, calendar = setup_contract_context(database)
    actor_id = database.scalar(select(User.id).where(User.username == "admin"))
    no_sla = ContractType(code="NO_SLA_TYPE", name="No SLA Type", precedence=10, default_has_sla=False, expiry_behavior="EXPIRE", approval_behavior="INHERIT", is_active=True)
    database.add(no_sla); database.flush()
    now = server_now()
    database.add(FeaturePolicy(feature_key="contract_types", scope_type="SYSTEM", scope_key="SYSTEM", mode="ENFORCED", configuration_json="{}", effective_from=now-timedelta(minutes=1), version=1, created_by_user_id=actor_id, updated_by_user_id=actor_id))
    database.commit()
    missing = client.post("/api/v1/contracts", headers=admin_headers, json=contract_payload(scoped_client.id, calendar.id, "TYPE-MISSING"))
    assert missing.status_code == 409
    assert missing.json()["error"]["code"] == "CONTRACT_TYPE_REQUIRED"
    created = client.post("/api/v1/contracts", headers=admin_headers, json=contract_payload(scoped_client.id, calendar.id, "TYPE-ENFORCED", contract_type_id=no_sla.id))
    assert created.status_code == 201, created.text
    assert created.json()["contract_type_id"] == no_sla.id
    assert created.json()["has_sla"] is False
    preview = client.get(
        f"/api/v1/contract-types/{no_sla.id}/defaults-preview",
        headers=admin_headers,
        params={"client_id": scoped_client.id},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json() == {
        "contract_type_id": no_sla.id,
        "code": "NO_SLA_TYPE",
        "feature_mode": "ENFORCED",
        "source_scope": "SYSTEM",
        "default_has_sla": False,
        "default_duration_days": None,
        "expiry_behavior": "EXPIRE",
        "approval_behavior": "INHERIT",
        "type_required": True,
    }
    stored = database.get(Contract, created.json()["id"])
    assert stored is not None and stored.contract_type_id == no_sla.id


def test_enforced_applicability_uses_type_precedence(database: Session) -> None:
    scoped_client, calendar = setup_contract_context(database)
    actor_id = database.scalar(select(User.id).where(User.username == "admin"))
    preferred = ContractType(code="PREFERRED", name="Preferred", precedence=10, default_has_sla=True, expiry_behavior="EXPIRE", approval_behavior="INHERIT", is_active=True)
    fallback = ContractType(code="FALLBACK", name="Fallback", precedence=20, default_has_sla=True, expiry_behavior="EXPIRE", approval_behavior="INHERIT", is_active=True)
    database.add_all([preferred, fallback]); database.flush()
    today = date.today()
    database.add_all([
        Contract(contract_number="PRECEDENCE-LOW", client_id=scoped_client.id, contract_type_id=preferred.id, name="Preferred", status="ACTIVE", start_date=today-timedelta(days=1), end_date=today+timedelta(days=30), calendar_id=calendar.id, is_active=True),
        Contract(contract_number="PRECEDENCE-HIGH", client_id=scoped_client.id, contract_type_id=fallback.id, name="Fallback", status="ACTIVE", start_date=today-timedelta(days=1), end_date=today+timedelta(days=60), calendar_id=calendar.id, is_active=True),
        FeaturePolicy(feature_key="contract_types", scope_type="SYSTEM", scope_key="SYSTEM", mode="ENFORCED", configuration_json="{}", effective_from=server_now()-timedelta(minutes=1), version=1, created_by_user_id=actor_id, updated_by_user_id=actor_id),
    ]); database.commit()
    status, contract, reason = evaluate_entitlement(database, client_id=scoped_client.id)
    assert status == "COVERED"
    assert contract is not None and contract.contract_number == "PRECEDENCE-LOW"
    assert "precedence" in reason


def test_enforced_applicability_rejects_equal_precedence_ambiguity(
    database: Session, client: TestClient, admin_headers: dict[str, str]
) -> None:
    scoped_client, calendar = setup_contract_context(database)
    actor_id = database.scalar(select(User.id).where(User.username == "admin"))
    kind = ContractType(code="EQUAL", name="Equal", precedence=30, default_has_sla=True, expiry_behavior="EXPIRE", approval_behavior="INHERIT", is_active=True)
    database.add(kind); database.flush()
    today = date.today()
    for suffix in ("A", "B"):
        database.add(Contract(contract_number=f"AMBIGUOUS-{suffix}", client_id=scoped_client.id, contract_type_id=kind.id, name=f"Ambiguous {suffix}", status="ACTIVE", start_date=today-timedelta(days=1), end_date=today+timedelta(days=30), calendar_id=calendar.id, is_active=True))
    database.add(FeaturePolicy(feature_key="contract_types", scope_type="SYSTEM", scope_key="SYSTEM", mode="ENFORCED", configuration_json="{}", effective_from=server_now()-timedelta(minutes=1), version=1, created_by_user_id=actor_id, updated_by_user_id=actor_id)); database.commit()
    status, contract, reason = evaluate_entitlement(database, client_id=scoped_client.id)
    assert status == "AMBIGUOUS"
    assert contract is None
    assert "AMBIGUOUS-A" in reason and "AMBIGUOUS-B" in reason
    candidates = client.get(
        "/api/v1/entitlements/candidates",
        headers=admin_headers,
        params={"client_id": scoped_client.id},
    )
    assert candidates.status_code == 200, candidates.text
    assert {item["contract_number"] for item in candidates.json()} == {
        "AMBIGUOUS-A", "AMBIGUOUS-B"
    }
    selected_id = candidates.json()[0]["contract_id"]
    status, selected, _ = evaluate_entitlement(
        database, client_id=scoped_client.id, preferred_contract_id=selected_id
    )
    assert status == "COVERED"
    assert selected is not None and selected.id == selected_id


def test_warranty_to_support_transition_uses_effective_dates(database: Session) -> None:
    scoped_client, calendar = setup_contract_context(database)
    actor_id = database.scalar(select(User.id).where(User.username == "admin"))
    warranty = database.scalar(select(ContractType).where(ContractType.code == "WARRANTY"))
    support = database.scalar(select(ContractType).where(ContractType.code == "SUPPORT"))
    assert warranty is not None and support is not None
    today = date.today()
    database.add_all([
        Contract(contract_number="ENDED-WARRANTY", client_id=scoped_client.id, contract_type_id=warranty.id, name="Ended warranty", status="ACTIVE", start_date=today-timedelta(days=365), end_date=today-timedelta(days=1), calendar_id=calendar.id, is_active=True),
        Contract(contract_number="CURRENT-SUPPORT", client_id=scoped_client.id, contract_type_id=support.id, name="Current support", status="ACTIVE", start_date=today, end_date=today+timedelta(days=365), calendar_id=calendar.id, is_active=True),
        FeaturePolicy(feature_key="contract_types", scope_type="SYSTEM", scope_key="SYSTEM", mode="ENFORCED", configuration_json="{}", effective_from=server_now()-timedelta(minutes=1), version=1, created_by_user_id=actor_id, updated_by_user_id=actor_id),
    ]); database.commit()
    status, contract, _ = evaluate_entitlement(database, client_id=scoped_client.id, on_date=today)
    assert status == "COVERED"
    assert contract is not None and contract.contract_number == "CURRENT-SUPPORT"
