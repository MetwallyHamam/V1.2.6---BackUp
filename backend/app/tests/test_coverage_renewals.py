import json
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Client, ClientStatus, ServiceCatalogItem
from app.modules.contracts.models import (
    BusinessCalendar,
    Contract,
    ContractCoverage,
    ContractCoverageRevision,
)
from app.modules.contracts.service import evaluate_entitlement
from app.modules.iam.models import User


def _contract_data(database: Session) -> tuple[Contract, ServiceCatalogItem, User]:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    client = Client(code="TEMPORAL-CLIENT", name="Temporal Coverage Client", status_id=status_id, is_active=True)
    service = ServiceCatalogItem(code="TEMPORAL-SERVICE", name="Temporal Service", is_active=True)
    database.add_all([client, service]); database.flush()
    calendar_id = database.scalar(select(BusinessCalendar.id))
    contract = Contract(contract_number="TEMPORAL-2026", client_id=client.id, name="Temporal Contract", status="ACTIVE", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), calendar_id=calendar_id, is_active=True)
    database.add(contract); database.flush()
    actor = database.scalar(select(User).where(User.username == "admin"))
    database.commit()
    return contract, service, actor


def _coverage(database: Session, contract: Contract, service: ServiceCatalogItem, actor: User, suffix: str = "") -> ContractCoverage:
    row = ContractCoverage(contract_id=contract.id, service_id=service.id, is_covered=True, notes=f"Initial coverage {suffix}", effective_from=date(2026,1,1), effective_until=date(2026,12,31), current_revision=1)
    database.add(row); database.flush()
    database.add(ContractCoverageRevision(coverage_id=row.id, revision=1, effective_from=date(2026,1,1), effective_until=date(2026,6,30), is_covered=True, notes=row.notes, client_ids_json="[]", change_reason="Initial period", created_by_user_id=actor.id))
    database.add(ContractCoverageRevision(coverage_id=row.id, revision=2, effective_from=date(2026,7,1), effective_until=date(2026,12,31), is_covered=False, notes="Excluded by amendment", client_ids_json="[]", change_reason="Mid-year amendment", created_by_user_id=actor.id))
    row.current_revision=2; row.effective_from=date(2026,7,1); row.is_covered=False
    database.commit()
    return row


def test_entitlement_uses_effective_revision_at_date(database: Session) -> None:
    contract, service, actor = _contract_data(database)
    _coverage(database, contract, service, actor)
    before = evaluate_entitlement(database, client_id=contract.client_id, service_id=service.id, on_date=date(2026,6,30))
    after = evaluate_entitlement(database, client_id=contract.client_id, service_id=service.id, on_date=date(2026,7,1))
    assert before[0] == "COVERED"
    assert after[0] == "EXCLUDED"
    assert "coverage" in before[2].lower()


def test_coverage_amendment_closes_previous_revision(client: TestClient, admin_headers: dict[str,str], database: Session) -> None:
    contract, service, actor = _contract_data(database)
    row = ContractCoverage(contract_id=contract.id, service_id=service.id, is_covered=True, effective_from=date(2026,1,1), effective_until=date(2026,12,31), current_revision=1)
    database.add(row); database.flush(); database.add(ContractCoverageRevision(coverage_id=row.id, revision=1, effective_from=date(2026,1,1), effective_until=date(2026,12,31), is_covered=True, client_ids_json="[]", change_reason="Baseline", created_by_user_id=actor.id)); database.commit()
    result = client.post(f"/api/v1/contracts/{contract.id}/coverage/{row.id}/amend", headers=admin_headers, json={"effective_from":"2026-07-01", "effective_until":"2026-12-31", "is_covered":False, "notes":"Retired service", "applies_to_all_clients":True, "client_ids":[], "reason":"Service removed from the renewed scope.", "expected_revision":1})
    assert result.status_code == 200, result.text
    history = client.get(f"/api/v1/contracts/{contract.id}/coverage/{row.id}/history", headers=admin_headers)
    assert [item["effective_until"] for item in history.json()] == ["2026-06-30", "2026-12-31"]


def test_partial_renewal_is_idempotent_and_links_successor(client: TestClient, admin_headers: dict[str,str], database: Session) -> None:
    contract, service, actor = _contract_data(database)
    first = _coverage(database, contract, service, actor)
    other_service = ServiceCatalogItem(code="TEMPORAL-SECOND", name="Second Temporal Service", is_active=True); database.add(other_service); database.flush()
    second = ContractCoverage(contract_id=contract.id, service_id=other_service.id, is_covered=True, effective_from=date(2026,1,1), effective_until=date(2026,12,31), current_revision=1); database.add(second); database.flush()
    database.add(ContractCoverageRevision(coverage_id=second.id, revision=1, effective_from=date(2026,1,1), effective_until=date(2026,12,31), is_covered=True, client_ids_json=json.dumps([]), change_reason="Baseline", created_by_user_id=actor.id))
    successor = Contract(contract_number="TEMPORAL-2027", client_id=contract.client_id, name="Successor", status="DRAFT", start_date=date(2027,1,1), end_date=date(2027,12,31), calendar_id=contract.calendar_id, is_active=True); database.add(successor); database.commit()
    successor.has_sla = False
    retained = ContractCoverage(contract_id=successor.id, service_id=service.id, is_covered=True)
    database.add(retained)
    database.commit()
    payload={"idempotency_key":"renewal-temporal-001", "owner_user_id":actor.id, "target_close_date":"2026-11-30", "reason":"Prepare the next annual support agreement.", "lines":[{"coverage_id":first.id,"outcome":"PENDING"},{"coverage_id":second.id,"outcome":"PENDING"}]}
    created=client.post(f"/api/v1/contracts/{contract.id}/renewal-opportunities",headers=admin_headers,json=payload)
    repeated=client.post(f"/api/v1/contracts/{contract.id}/renewal-opportunities",headers=admin_headers,json=payload)
    assert created.status_code==201 and created.json()["id"]==repeated.json()["id"]
    closed=client.put(f"/api/v1/contracts/{contract.id}/renewal-opportunities/{created.json()['id']}",headers=admin_headers,json={"stage":"CLOSED","outcome":"PARTIAL","successor_contract_id":successor.id,"reason":"One service renewed and one service was lost.","version":1,"lines":[{"coverage_id":first.id,"outcome":"RENEWED","successor_coverage_id":retained.id},{"coverage_id":second.id,"outcome":"LOST","reason":"Customer removed this service."}]})
    assert closed.status_code==200,closed.text
    assert closed.json()["outcome"]=="PARTIAL"
