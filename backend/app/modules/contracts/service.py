import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.clock import server_now, server_timezone, server_today
from app.modules.configuration.policy_service import resolve_feature_policy
from app.modules.contracts.models import (
    BusinessCalendarDay,
    Contract,
    ContractClientLink,
    ContractCoverage,
    ContractCoverageRevision,
    ContractType,
    Holiday,
    SlaTarget,
)
from app.modules.tickets.models import Ticket

CONTEXT_FIELDS = (
    "branch_id",
    "product_id",
    "product_module_id",
    "environment_id",
    "service_id",
    "ticket_type_id",
)


@dataclass(frozen=True)
class CoverageDecision:
    contract: Contract
    row: ContractCoverage | None
    specificity: int
    covered_override: bool | None = None
    coverage_revision: int | None = None

    @property
    def is_covered(self) -> bool:
        return self.row is None or (self.covered_override if self.covered_override is not None else self.row.is_covered)


def contract_usage(db: Session, contract: Contract) -> dict[str, int | None]:
    primary_request_filter = (
        Ticket.contract_id == contract.id,
        Ticket.escalation_parent_ticket_id.is_(None),
    )
    total = db.scalar(select(func.count(Ticket.id)).where(*primary_request_filter)) or 0
    used = db.scalar(
        select(func.count(Ticket.id)).where(
            *primary_request_filter,
            Ticket.entitlement_status == "COVERED",
        )
    ) or 0
    overrides = db.scalar(
        select(func.count(Ticket.id)).where(
            *primary_request_filter,
            Ticket.entitlement_status == "OVERRIDDEN",
        )
    ) or 0
    remaining = (
        max(contract.included_request_limit - used, 0)
        if contract.included_request_limit is not None
        else None
    )
    return {
        "included_request_limit": contract.included_request_limit,
        "used_requests": used,
        "remaining_requests": remaining,
        "overridden_requests": overrides,
        "total_primary_requests": total,
    }


def _contract_decision(
    rows: list[ContractCoverage],
    contract: Contract,
    values: dict[str, int | None],
    revisions: dict[int, ContractCoverageRevision] | None = None,
) -> CoverageDecision | None:
    if not rows:
        return CoverageDecision(contract, None, 0)
    matching = [
        row
        for row in rows
        if all(
            # A contract dimension only constrains the request when the user selected
            # that dimension. This lets a product-only ticket match coverage rows that
            # also describe modules/services, without allowing a selected value to
            # bypass contract validation.
            values[field] is None
            or getattr(row, field) is None
            or getattr(row, field) == values[field]
            for field in CONTEXT_FIELDS
        )
        and (
            all(getattr(row, field) is None for field in CONTEXT_FIELDS)
            or any(
                values[field] is not None and getattr(row, field) == values[field]
                for field in CONTEXT_FIELDS
            )
        )
    ]
    if not matching:
        return None
    matching.sort(
        key=lambda row: (
            sum(
                values[field] is not None and getattr(row, field) is not None
                for field in CONTEXT_FIELDS
            ),
            -sum(
                values[field] is None and getattr(row, field) is not None
                for field in CONTEXT_FIELDS
            ),
            not row.is_covered,
            row.id,
        ),
        reverse=True,
    )
    selected = matching[0]
    return CoverageDecision(
        contract,
        selected,
        sum(
            values[field] is not None and getattr(selected, field) is not None
            for field in CONTEXT_FIELDS
        ),
        revisions[selected.id].is_covered if revisions and selected.id in revisions else None,
        revisions[selected.id].revision if revisions and selected.id in revisions else selected.current_revision,
    )


def _decision_rank(decision: CoverageDecision) -> tuple[int, bool, date, date, int]:
    return (
        decision.specificity,
        not decision.is_covered,
        decision.contract.start_date,
        decision.contract.end_date,
        decision.contract.id,
    )


def _governed_selection(
    db: Session, decisions: list[CoverageDecision]
) -> tuple[CoverageDecision | None, list[CoverageDecision]]:
    """Select by coverage specificity and configured type precedence.

    Returns no selection when multiple contracts remain equally applicable so callers
    can require an explicit contract choice instead of silently using dates or IDs.
    """
    if not decisions:
        return None, []
    type_ids = {item.contract.contract_type_id for item in decisions if item.contract.contract_type_id}
    precedences = {
        item.id: item.precedence
        for item in db.scalars(select(ContractType).where(ContractType.id.in_(type_ids)))
    }
    best_specificity = max(item.specificity for item in decisions)
    finalists = [item for item in decisions if item.specificity == best_specificity]
    # An equally specific exclusion is intentionally safer than an inclusion.
    if any(not item.is_covered for item in finalists):
        finalists = [item for item in finalists if not item.is_covered]
    best_precedence = min(
        precedences.get(item.contract.contract_type_id or -1, 900) for item in finalists
    )
    finalists = [
        item for item in finalists
        if precedences.get(item.contract.contract_type_id or -1, 900) == best_precedence
    ]
    return (finalists[0] if len(finalists) == 1 else None), finalists


def _validation_values(
    contract: Contract, values: dict[str, int | None]
) -> dict[str, int | None]:
    """Apply the contract's configured entitlement depth.

    Product is the safe operational default. Module and service remain available
    to SLA matching without making a ticket out of contract unless explicitly
    enabled for that contract.
    """
    level = contract.coverage_validation_level or "PRODUCT"
    if level == "PRODUCT" and values["product_id"] is None:
        return values
    if level == "CONTRACT":
        return {field: None for field in CONTEXT_FIELDS}
    allowed = {"product_id"}
    if level in {"PRODUCT_MODULE", "FULL"}:
        allowed.add("product_module_id")
    if level == "FULL":
        allowed.update({"branch_id", "environment_id", "service_id", "ticket_type_id"})
    return {field: values[field] if field in allowed else None for field in CONTEXT_FIELDS}


def _coverage_decision_for_contract(
    db: Session,
    contract: Contract,
    values: dict[str, int | None],
    client_id: int,
    evaluated_on: date,
) -> CoverageDecision | None:
    if contract.coverage_validation_level == "CONTRACT":
        return CoverageDecision(contract, None, 0)
    rows = list(
        db.scalars(
            select(ContractCoverage).where(ContractCoverage.contract_id == contract.id)
        )
    )
    versioned_ids = set(db.scalars(select(ContractCoverageRevision.coverage_id).where(
        ContractCoverageRevision.coverage_id.in_([row.id for row in rows])
    ))) if rows else set()
    revisions = list(
        db.scalars(
            select(ContractCoverageRevision).where(
                ContractCoverageRevision.coverage_id.in_([row.id for row in rows]),
                ContractCoverageRevision.effective_from <= evaluated_on,
                or_(
                    ContractCoverageRevision.effective_until.is_(None),
                    ContractCoverageRevision.effective_until >= evaluated_on,
                ),
            ).order_by(ContractCoverageRevision.revision)
        )
    ) if rows else []
    latest_revisions = {revision.coverage_id: revision for revision in revisions}
    revisions_by_coverage = {
        coverage_id: revision for coverage_id, revision in latest_revisions.items()
        if not (ids := json.loads(revision.client_ids_json)) or client_id in ids
    }
    applicable = [
        row
        for row in rows
        if (
            row.id in revisions_by_coverage
            and not (row.retired_at and evaluated_on >= row.retired_at.date())
        )
        or (
            row.id not in versioned_ids
            and (row.effective_from is None or row.effective_from <= evaluated_on)
            and (row.effective_until is None or row.effective_until >= evaluated_on)
            and row.retired_at is None
            and (not row.client_ids or client_id in row.client_ids)
        )
    ]
    if rows and not applicable:
        return None
    return _contract_decision(
        applicable,
        contract,
        _validation_values(contract, values),
        revisions_by_coverage,
    )


def evaluate_entitlement(
    db: Session,
    *,
    client_id: int,
    branch_id: int | None = None,
    product_id: int | None = None,
    product_module_id: int | None = None,
    environment_id: int | None = None,
    service_id: int | None = None,
    ticket_type_id: int | None = None,
    on_date: date | None = None,
    preferred_contract_id: int | None = None,
) -> tuple[str, Contract | None, str]:
    """Resolve the most specific active contract coverage for a ticket context."""
    checked_on = on_date or server_today()
    contracts = list(
        db.scalars(
            select(Contract)
            .where(
                or_(Contract.applies_to_all_clients.in_([True]), Contract.client_id == client_id, Contract.client_links.any(ContractClientLink.client_id == client_id)),
                Contract.is_active.in_([True]),
                Contract.status == "ACTIVE",
                Contract.start_date <= checked_on,
                Contract.end_date >= checked_on,
            )
            .order_by(
                Contract.is_shared_default.asc(),
                Contract.start_date.desc(),
                Contract.end_date.desc(),
                Contract.id.desc(),
            )
        )
    )
    values: dict[str, int | None] = {
        "branch_id": branch_id,
        "product_id": product_id,
        "product_module_id": product_module_id,
        "environment_id": environment_id,
        "service_id": service_id,
        "ticket_type_id": ticket_type_id,
    }
    if not contracts:
        expired = db.scalar(
            select(Contract)
            .where(
                or_(
                    Contract.applies_to_all_clients.in_([True]),
                    Contract.client_id == client_id,
                    Contract.client_links.any(ContractClientLink.client_id == client_id),
                ),
                Contract.start_date <= checked_on,
                Contract.end_date < checked_on,
                Contract.status.in_(["ACTIVE", "EXPIRED"]),
            )
            .order_by(Contract.end_date.desc(), Contract.id.desc())
        )
        if not expired:
            return "NO_CONTRACT", None, "No support contract exists for this ticket date."
        expired_decision = _coverage_decision_for_contract(
            db, expired, values, client_id, expired.end_date
        )
        if expired_decision is None or not expired_decision.is_covered:
            return (
                "NOT_COVERED",
                expired,
                "The latest contract does not cover the selected product scope.",
            )
        elapsed_days = (checked_on - expired.end_date).days
        if elapsed_days <= expired.expiry_grace_days:
            return (
                "GRACE_COVERAGE",
                expired,
                f"The contract expired {elapsed_days} day(s) ago and is within its configured {expired.expiry_grace_days}-day grace period.",
            )
        return (
            "EXPIRED_CONTRACT",
            expired,
            f"The contract grace period ended {elapsed_days - expired.expiry_grace_days} day(s) ago.",
        )
    decisions = [
        decision
        for contract in contracts
        if (
            decision := _coverage_decision_for_contract(
                db, contract, values, client_id, checked_on
            )
        )
        is not None
    ]
    specific = [decision for decision in decisions if not decision.contract.is_shared_default]
    shared = [decision for decision in decisions if decision.contract.is_shared_default]
    tier = specific or shared
    if not tier:
        # An unrelated active contract must not hide an expired contract that
        # actually covered the requested product/service scope.
        historical = list(
            db.scalars(
                select(Contract)
                .where(
                    or_(
                        Contract.client_id == client_id,
                        Contract.client_links.any(ContractClientLink.client_id == client_id),
                    ),
                    Contract.start_date <= checked_on,
                    or_(
                        Contract.end_date < checked_on,
                        Contract.status != "ACTIVE",
                        Contract.is_active.in_([False]),
                    ),
                )
                .order_by(Contract.end_date.desc(), Contract.id.desc())
            )
        )
        for historical_contract in historical:
            historical_decision = _coverage_decision_for_contract(
                db,
                historical_contract,
                values,
                client_id,
                min(checked_on, historical_contract.end_date),
            )
            if historical_decision and historical_decision.is_covered:
                elapsed_days = max(0, (checked_on - historical_contract.end_date).days)
                if (
                    historical_contract.end_date < checked_on
                    and elapsed_days <= historical_contract.expiry_grace_days
                    and historical_contract.status in {"ACTIVE", "EXPIRED"}
                ):
                    return (
                        "GRACE_COVERAGE",
                        historical_contract,
                        f"Matching coverage expired {elapsed_days} day(s) ago and remains in its approved grace period.",
                    )
                return (
                    "EXPIRED_CONTRACT",
                    historical_contract,
                    f"Matching product/service coverage belongs to inactive or expired contract {historical_contract.contract_number}.",
                )
        preferred_contract = next(
            (contract for contract in contracts if not contract.is_shared_default), contracts[0]
        )
        return (
            "NOT_COVERED",
            preferred_contract,
            "No matching coverage rule exists in an eligible customer-specific or shared-default contract.",
        )
    selected: CoverageDecision | None
    governed: CoverageDecision | None
    if preferred_contract_id is not None:
        selected_preference = next(
            (item for item in tier if item.contract.id == preferred_contract_id), None
        )
        if selected_preference is None:
            return (
                "INVALID_SELECTION",
                None,
                "The selected contract is not applicable to this ticket context.",
            )
        selected = selected_preference
        governed = selected
        feature_mode = resolve_feature_policy(
            db, "contract_types", client_id=client_id
        ).mode
    else:
        feature_mode = resolve_feature_policy(
            db, "contract_types", client_id=client_id
        ).mode
        governed, ambiguous = _governed_selection(db, tier)
        if feature_mode == "ENFORCED" and governed is None:
            numbers = ", ".join(sorted(item.contract.contract_number for item in ambiguous))
            return (
                "AMBIGUOUS",
                None,
                f"Multiple equally applicable contracts require an explicit selection: {numbers}.",
            )
        selected = governed if feature_mode == "ENFORCED" else max(tier, key=_decision_rank)
    assert selected is not None
    if not selected.is_covered:
        assert selected.row is not None
        return (
            "EXCLUDED",
            selected.contract,
            (selected.row.notes or "The highest-specificity contract rule excludes this ticket context.")
            + (f" Coverage revision {selected.coverage_revision} applied." if selected.coverage_revision else ""),
        )
    if selected.contract.included_request_limit:
        used = int(contract_usage(db, selected.contract)["used_requests"] or 0)
        if used >= selected.contract.included_request_limit:
            return (
                "LIMIT_EXCEEDED",
                selected.contract,
                "The included support request limit has been reached.",
            )
    tier_name = "customer-specific" if not selected.contract.is_shared_default else "shared-default"
    reason = (
        f"Covered by configured contract-type precedence ({selected.contract.contract_type.name})."
        if feature_mode == "ENFORCED" and selected.contract.contract_type
        else f"Covered by the highest-specificity {tier_name} contract rule."
    )
    if feature_mode == "SHADOW" and governed is None:
        reason += " Shadow evaluation detected equally applicable contracts."
    if selected.coverage_revision:
        reason += f" Coverage revision {selected.coverage_revision} applied."
    return (
        "COVERED",
        selected.contract,
        reason,
    )


def resolve_product_scoped_sla_target(
    db: Session,
    *,
    policy_id: int,
    priority: str,
    product_id: int | None,
    product_module_id: int | None,
    service_id: int | None,
    at: datetime | None = None,
) -> tuple[SlaTarget | None, str]:
    """Resolve the approved six-level SLA target order without cross-product leakage."""
    evaluated_at = at or server_now()
    targets = list(db.scalars(select(SlaTarget).where(
        SlaTarget.policy_id == policy_id,
        SlaTarget.priority == priority,
        or_(SlaTarget.effective_from.is_(None), SlaTarget.effective_from <= evaluated_at),
        or_(SlaTarget.effective_until.is_(None), SlaTarget.effective_until > evaluated_at),
    )))
    match_levels = (
        ("PRODUCT_MODULE_SERVICE", product_id, product_module_id, service_id, False),
        ("PRODUCT_SERVICE", product_id, None, service_id, False),
        ("PRODUCT", product_id, None, None, False),
        ("CONTRACT_SERVICE_DEFAULT", None, None, service_id, False),
        ("CONTRACT_PRIORITY_DEFAULT", None, None, None, True),
    )
    for reason, target_product, target_module, target_service, fallback in match_levels:
        if reason.startswith("PRODUCT") and product_id is None:
            continue
        if reason == "PRODUCT_MODULE_SERVICE" and (product_module_id is None or service_id is None):
            continue
        if reason in {"PRODUCT_SERVICE", "CONTRACT_SERVICE_DEFAULT"} and service_id is None:
            continue
        matching = [item for item in targets if (
            item.product_id == target_product
            and item.product_module_id == target_module
            and item.service_id == target_service
            and (not fallback or item.is_fallback or (
                item.product_id is None and item.product_module_id is None
                and item.service_id is None
            ))
        )]
        if len(matching) == 1:
            return matching[0], reason
        if len(matching) > 1:
            return None, f"AMBIGUOUS_{reason}"
    return None, "NO_MATCHING_SLA"


def add_working_minutes(
    start_utc: datetime,
    minutes: int,
    timezone_name: str,
    working_days: dict[int, tuple[time, time]],
    holidays: set[date],
) -> datetime:
    if minutes <= 0:
        return start_utc
    zone = ZoneInfo(timezone_name)
    current = start_utc.astimezone(zone)
    remaining = minutes
    # Historical tickets remain subject to SLA reporting and escalation after
    # their first year. Keep a finite ceiling to reject clearly corrupt dates,
    # while allowing the long-lived support records retained by the system.
    for _ in range(36_600):
        day = current.date()
        schedule = working_days.get(current.weekday())
        if schedule and day not in holidays:
            day_start = datetime.combine(day, schedule[0], zone)
            day_end = datetime.combine(day, schedule[1], zone)
            if schedule[1] <= schedule[0]:
                day_end += timedelta(days=1)
            if current < day_start:
                current = day_start
            if current < day_end:
                available = int((day_end - current).total_seconds() // 60)
                if remaining <= available:
                    return (current + timedelta(minutes=remaining)).astimezone(server_timezone())
                remaining -= available
        current = datetime.combine(day + timedelta(days=1), time.min, zone)
    raise ValueError("SLA duration exceeds the supported calculation horizon.")


def calculate_due_at(db: Session, calendar_id: int, start: datetime, minutes: int) -> datetime:
    days = list(
        db.scalars(
            select(BusinessCalendarDay).where(
                BusinessCalendarDay.calendar_id == calendar_id,
                BusinessCalendarDay.is_working_day.in_([True]),
            )
        )
    )
    calendar_days = {item.weekday: (item.start_time, item.end_time) for item in days}
    holiday_dates = set(
        db.scalars(select(Holiday.holiday_date).where(Holiday.calendar_id == calendar_id))
    )
    from app.modules.contracts.models import BusinessCalendar

    calendar = db.get(BusinessCalendar, calendar_id)
    if not calendar:
        raise ValueError("Business calendar does not exist.")
    return add_working_minutes(start, minutes, calendar.timezone, calendar_days, holiday_dates)


def calculate_working_minutes(
    db: Session, calendar_id: int, start: datetime, end: datetime
) -> int:
    """Return business-calendar minutes elapsed between two UTC timestamps."""
    if end <= start:
        return 0
    days = list(
        db.scalars(
            select(BusinessCalendarDay).where(
                BusinessCalendarDay.calendar_id == calendar_id,
                BusinessCalendarDay.is_working_day.in_([True]),
            )
        )
    )
    working_days = {item.weekday: (item.start_time, item.end_time) for item in days}
    holidays = set(
        db.scalars(select(Holiday.holiday_date).where(Holiday.calendar_id == calendar_id))
    )
    from app.modules.contracts.models import BusinessCalendar

    calendar = db.get(BusinessCalendar, calendar_id)
    if not calendar:
        raise ValueError("Business calendar does not exist.")
    return working_minutes_between(start, end, calendar.timezone, working_days, holidays)


def working_minutes_between(
    start: datetime,
    end: datetime,
    timezone_name: str,
    working_days: dict[int, tuple[time, time]],
    holidays: set[date],
) -> int:
    """Return working minutes using already-loaded calendar data."""
    if end <= start:
        return 0
    zone = ZoneInfo(timezone_name)
    local_start = start.astimezone(zone)
    local_end = end.astimezone(zone)
    current_day = local_start.date()
    end_day = local_end.date()
    elapsed = 0
    # SLA reporting and escalation must support historical tickets. The cap
    # remains finite to detect corrupt timestamps without rejecting records
    # simply because they are more than one year old.
    for _ in range(36_600):
        schedule = working_days.get(current_day.weekday())
        if schedule and current_day not in holidays:
            day_start = datetime.combine(current_day, schedule[0], zone)
            day_end = datetime.combine(current_day, schedule[1], zone)
            if schedule[1] <= schedule[0]:
                day_end += timedelta(days=1)
            overlap_start = max(local_start, day_start)
            overlap_end = min(local_end, day_end)
            if overlap_end > overlap_start:
                elapsed += int((overlap_end - overlap_start).total_seconds() // 60)
        if current_day >= end_day:
            return elapsed
        current_day += timedelta(days=1)
    raise ValueError("SLA elapsed-time calculation exceeds the supported horizon.")
