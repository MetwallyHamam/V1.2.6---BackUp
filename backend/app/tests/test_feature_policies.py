from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.modules.clients.models import Client, ClientStatus, Product, ServiceCatalogItem
from app.modules.configuration.models import FeaturePolicy
from app.modules.configuration.policy_service import resolve_feature_policy
from app.modules.contracts.models import BusinessCalendar, Contract
from app.modules.iam.models import AuditLog


def create_context(db: Session) -> tuple[Client, Contract, Product, ServiceCatalogItem]:
    status = ClientStatus(code="POLICY_ACTIVE", name="Policy active", portal_allowed=True, ticket_creation_allowed=True, is_active=True)
    calendar = BusinessCalendar(code="POLICY_CAL", name="Policy calendar", timezone="Africa/Cairo", is_active=True)
    product = Product(code="POLICY_PRODUCT", name="Policy product", is_active=True)
    service = ServiceCatalogItem(code="POLICY_SERVICE", name="Policy service", is_active=True)
    db.add_all([status, calendar, product, service])
    db.flush()
    client = Client(code="POLICY_CLIENT", name="Policy Client", status_id=status.id, is_active=True)
    db.add(client)
    db.flush()
    contract = Contract(
        contract_number="POLICY-001", client_id=client.id, name="Policy Contract",
        status="ACTIVE", start_date=server_now().date(),
        end_date=(server_now() + timedelta(days=365)).date(),
        timezone="Africa/Cairo", calendar_id=calendar.id, is_active=True,
    )
    db.add(contract)
    db.commit()
    return client, contract, product, service


def put_policy(client: TestClient, headers: dict[str, str], feature: str, **values: object):
    payload = {
        "scope_type": "SYSTEM", "mode": "SHADOW", "configuration": {},
        "reason": "Policy test configuration", **values,
    }
    return client.put(f"/api/v1/system/feature-policies/{feature}/policies", json=payload, headers=headers)


def test_feature_catalog_and_system_policy(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    catalog = client.get("/api/v1/system/feature-policies", headers=admin_headers)
    assert catalog.status_code == 200
    assert {item["key"] for item in catalog.json()} >= {"product_scoped_sla", "outlook_inbound_email", "support_tiers"}

    created = put_policy(client, admin_headers, "product_scoped_sla")
    assert created.status_code == 200, created.text
    assert created.json()["version"] == 1
    effective = client.get("/api/v1/system/feature-policies/product_scoped_sla/effective", headers=admin_headers)
    assert effective.status_code == 200
    assert effective.json()["mode"] == "SHADOW"
    assert effective.json()["source_scope"] == "SYSTEM"
    assert database.query(AuditLog).filter(AuditLog.action == "feature_policy.created").count() == 1


def test_scope_precedence_and_inheritance(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    scoped_client, contract, product, service = create_context(database)
    assert put_policy(client, admin_headers, "product_scoped_sla", mode="OFF").status_code == 200
    assert put_policy(client, admin_headers, "product_scoped_sla", scope_type="CLIENT", client_id=scoped_client.id, mode="SHADOW").status_code == 200
    assert put_policy(client, admin_headers, "product_scoped_sla", scope_type="CONTRACT", contract_id=contract.id, mode="ENFORCED").status_code == 200
    result = put_policy(
        client, admin_headers, "product_scoped_sla", scope_type="PRODUCT_SERVICE",
        client_id=scoped_client.id, contract_id=contract.id,
        product_id=product.id, service_id=service.id, mode="SHADOW",
    )
    assert result.status_code == 200, result.text

    exact = resolve_feature_policy(
        database, "product_scoped_sla", client_id=scoped_client.id,
        contract_id=contract.id, product_id=product.id, service_id=service.id,
    )
    assert exact.mode == "SHADOW"
    assert exact.source_scope == "PRODUCT_SERVICE"
    contract_only = resolve_feature_policy(
        database, "product_scoped_sla", client_id=scoped_client.id, contract_id=contract.id,
    )
    assert contract_only.mode == "ENFORCED"
    client_only = resolve_feature_policy(database, "product_scoped_sla", client_id=scoped_client.id)
    assert client_only.mode == "SHADOW"


def test_policy_concurrency_and_delete_inherits(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    created = put_policy(client, admin_headers, "support_tiers")
    item = created.json()
    stale = put_policy(client, admin_headers, "support_tiers", mode="ENFORCED", expected_version=99)
    assert stale.status_code == 409
    updated = put_policy(client, admin_headers, "support_tiers", mode="ENFORCED", expected_version=item["version"])
    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    deleted = client.delete(
        f"/api/v1/system/feature-policies/support_tiers/policies/{item['id']}",
        params={"reason": "Return to inherited default"}, headers=admin_headers,
    )
    assert deleted.status_code == 204
    assert database.get(FeaturePolicy, item["id"]) is None
    effective = client.get("/api/v1/system/feature-policies/support_tiers/effective", headers=admin_headers)
    assert effective.json()["mode"] == "OFF"


def test_invalid_scope_is_rejected(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = put_policy(
        client, admin_headers, "support_tiers", scope_type="PRODUCT_SERVICE",
        client_id=123, mode="ENFORCED",
    )
    assert response.status_code == 422
