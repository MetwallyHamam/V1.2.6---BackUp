from datetime import timedelta
from types import SimpleNamespace
from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.modules.clients.models import Product, ProductModule, ServiceCatalogItem
from app.modules.contracts.models import BusinessCalendar, SlaPolicy, SlaTarget
from app.modules.contracts.service import resolve_product_scoped_sla_target
from app.modules.sla.service import current_sla_target
from app.modules.tickets.models import Ticket


def test_product_scoped_sla_specificity_and_no_cross_product_leak(database: Session) -> None:
    calendar = database.scalar(select(BusinessCalendar))
    assert calendar is not None
    product_a = Product(code="SLA_PRODUCT_A", name="SLA Product A", is_active=True)
    product_b = Product(code="SLA_PRODUCT_B", name="SLA Product B", is_active=True)
    service = ServiceCatalogItem(code="SLA_SERVICE", name="SLA Service", is_active=True)
    database.add_all([product_a, product_b, service]); database.flush()
    module = ProductModule(product_id=product_a.id, code="SLA_MODULE", name="SLA Module", is_active=True)
    policy = SlaPolicy(code="PRODUCT_SCOPE_TEST", name="Product scope test", calendar_id=calendar.id, is_active=True)
    database.add_all([module, policy]); database.flush()
    database.add_all([
        SlaTarget(policy_id=policy.id, product_id=product_a.id, product_module_id=module.id, service_id=service.id, priority="P3", first_response_minutes=10, resolution_minutes=20, warning_percent=75),
        SlaTarget(policy_id=policy.id, product_id=product_a.id, service_id=service.id, priority="P3", first_response_minutes=20, resolution_minutes=30, warning_percent=75),
        SlaTarget(policy_id=policy.id, product_id=product_a.id, priority="P3", first_response_minutes=30, resolution_minutes=40, warning_percent=75),
        SlaTarget(policy_id=policy.id, service_id=service.id, priority="P3", first_response_minutes=40, resolution_minutes=50, warning_percent=75),
        SlaTarget(policy_id=policy.id, priority="P3", is_fallback=True, first_response_minutes=50, resolution_minutes=60, warning_percent=75),
    ]); database.commit()
    target, reason = resolve_product_scoped_sla_target(database, policy_id=policy.id, priority="P3", product_id=product_a.id, product_module_id=module.id, service_id=service.id)
    assert target is not None and target.first_response_minutes == 10
    assert reason == "PRODUCT_MODULE_SERVICE"
    target, reason = resolve_product_scoped_sla_target(database, policy_id=policy.id, priority="P3", product_id=product_b.id, product_module_id=None, service_id=None)
    assert target is not None and target.first_response_minutes == 50
    assert reason == "CONTRACT_PRIORITY_DEFAULT"


def test_legacy_current_target_helper_falls_back_when_other_service_has_override(database: Session) -> None:
    calendar = database.scalar(select(BusinessCalendar))
    service_a = ServiceCatalogItem(code="LEGACY_SVC_A", name="Legacy service A", is_active=True)
    service_b = ServiceCatalogItem(code="LEGACY_SVC_B", name="Legacy service B", is_active=True)
    policy = SlaPolicy(code="LEGACY_FALLBACK", name="Legacy fallback", calendar_id=calendar.id, is_active=True)
    database.add_all([service_a, service_b, policy]); database.flush()
    database.add_all([
        SlaTarget(policy_id=policy.id, service_id=service_a.id, priority="P2", first_response_minutes=10, resolution_minutes=20, warning_percent=75),
        SlaTarget(policy_id=policy.id, priority="P2", is_fallback=True, first_response_minutes=60, resolution_minutes=120, warning_percent=75),
    ]); database.flush()
    ticket = cast(Ticket, SimpleNamespace(priority="P2", product_id=None, product_module_id=None, service_id=service_b.id, created_at=server_now()))
    target = current_sla_target(database, ticket, policy.id)
    assert target is not None and target.first_response_minutes == 60


def test_product_scoped_sla_respects_effective_dates(database: Session) -> None:
    calendar = database.scalar(select(BusinessCalendar))
    assert calendar is not None
    product = Product(code="DATED_PRODUCT", name="Dated Product", is_active=True)
    database.add(product); database.flush()
    policy = SlaPolicy(code="DATED_SCOPE_TEST", name="Dated scope test", calendar_id=calendar.id, is_active=True)
    database.add(policy); database.flush()
    now = server_now()
    database.add(SlaTarget(policy_id=policy.id, product_id=product.id, priority="P2", effective_from=now+timedelta(days=1), first_response_minutes=15, resolution_minutes=30, warning_percent=75)); database.commit()
    target, reason = resolve_product_scoped_sla_target(database, policy_id=policy.id, priority="P2", product_id=product.id, product_module_id=None, service_id=None, at=now)
    assert target is None
    assert reason == "NO_MATCHING_SLA"
