from dataclasses import dataclass
from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_now, server_timezone
from app.modules.configuration.models import SiteSetting
from app.modules.contracts.models import (
    BusinessCalendar,
    BusinessCalendarDay,
    Contract,
    Holiday,
    SlaPolicy,
    SlaTarget,
    TicketSlaClock,
    TicketSlaInterval,
)
from app.modules.contracts.service import (
    calculate_working_minutes,
    resolve_product_scoped_sla_target,
    working_minutes_between,
)
from app.modules.iam.models import User
from app.modules.tickets.models import Ticket, TicketAssignmentHistory, TicketType
from app.modules.tickets.service import SLA_EXEMPT_TICKET_TYPE_CODES

# Stay below SQL Server's 2,100-parameter ceiling while minimizing round trips.
SQL_ID_BATCH_SIZE = 1900


def _id_batches(values: list[int]) -> list[list[int]]:
    return [values[offset : offset + SQL_ID_BATCH_SIZE] for offset in range(0, len(values), SQL_ID_BATCH_SIZE)]


@dataclass(frozen=True)
class AccountableSlaResult:
    target_minutes: int
    accountable_minutes: int
    customer_pending_minutes: int
    millensys_pending_minutes: int
    escalation_minutes: int
    saved_minutes: int
    overrun_minutes: int
    met: bool
    started_at: datetime
    completed_at: datetime


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=server_timezone())


def current_sla_target(db: Session, ticket: Ticket, policy_id: int) -> SlaTarget | None:
    """Resolve through the canonical precedence service, including priority fallback."""
    target, _reason = resolve_product_scoped_sla_target(
        db,
        policy_id=policy_id,
        priority=ticket.priority,
        product_id=ticket.product_id,
        product_module_id=ticket.product_module_id,
        service_id=ticket.service_id,
        at=ticket.created_at,
    )
    return target


def ticket_matches_current_sla_target(db: Session, ticket: Ticket, policy_id: int) -> bool:
    """Keep a service-scoped SLA from applying to unrelated ticket services."""
    return current_sla_target(db, ticket, policy_id) is not None


def first_dedicated_assignment_at(db: Session, ticket_id: int) -> datetime | None:
    configured = db.get(SiteSetting, "default_assignee_user_id")
    configured_id = int(configured.value) if configured and configured.value.isdigit() else None
    statement = (
        select(TicketAssignmentHistory.created_at)
        .join(User, User.id == TicketAssignmentHistory.assigned_user_id)
        .where(
            TicketAssignmentHistory.ticket_id == ticket_id,
            TicketAssignmentHistory.assigned_user_id.is_not(None),
            User.username_normalized != "support",
        )
        .order_by(TicketAssignmentHistory.created_at)
        .limit(1)
    )
    if configured_id is not None:
        statement = statement.where(TicketAssignmentHistory.assigned_user_id != configured_id)
    return db.scalar(statement)


def first_dedicated_assignments(db: Session, ticket_ids: list[int]) -> dict[int, datetime]:
    if not ticket_ids:
        return {}
    configured = db.get(SiteSetting, "default_assignee_user_id")
    configured_id = int(configured.value) if configured and configured.value.isdigit() else None
    result: dict[int, datetime] = {}
    for ticket_id_batch in _id_batches(ticket_ids):
        statement = (
            select(TicketAssignmentHistory.ticket_id, TicketAssignmentHistory.created_at)
            .join(User, User.id == TicketAssignmentHistory.assigned_user_id)
            .where(
                TicketAssignmentHistory.ticket_id.in_(ticket_id_batch),
                TicketAssignmentHistory.assigned_user_id.is_not(None),
                User.username_normalized != "support",
            )
            .order_by(TicketAssignmentHistory.ticket_id, TicketAssignmentHistory.created_at)
        )
        if configured_id is not None:
            statement = statement.where(TicketAssignmentHistory.assigned_user_id != configured_id)
        for ticket_id, created_at in db.execute(statement):
            result.setdefault(ticket_id, created_at)
    return result


def dedicated_resolution_hours(db: Session, ticket: Ticket) -> float | None:
    """Return elapsed hours owned by a dedicated engineer for a completed ticket."""
    completed_at = ticket.closed_at or ticket.resolved_at
    if completed_at is None:
        return None
    started_at = first_dedicated_assignment_at(db, ticket.id)
    if started_at is None:
        return None
    started_at, completed_at = _aware(started_at), _aware(completed_at)
    if completed_at < started_at:
        return None
    return (completed_at - started_at).total_seconds() / 3600


def resolution_sla_result(db: Session, ticket: Ticket, *, as_of: datetime | None = None) -> AccountableSlaResult | None:
    clock = db.scalar(select(TicketSlaClock).where(TicketSlaClock.ticket_id == ticket.id, TicketSlaClock.clock_type == "RESOLUTION"))
    if not clock:
        return None
    contract = db.get(Contract, clock.contract_id) if clock.contract_id else None
    if contract and not contract.has_sla:
        return None
    policy = db.get(SlaPolicy, clock.policy_id)
    if not policy:
        return None
    started_at = clock.started_at
    completed_at = ticket.closed_at or clock.completed_at or as_of
    if started_at is None or completed_at is None:
        return None
    if _aware(started_at) > _aware(completed_at):
        started_at = first_dedicated_assignment_at(db, ticket.id) or started_at
    started_at, completed_at = _aware(started_at), _aware(completed_at)
    calendar_id = clock.calendar_id or policy.calendar_id
    gross = calculate_working_minutes(db, calendar_id, started_at, completed_at)
    customer_pending = millensys_pending = escalation = 0
    for item in db.scalars(select(TicketSlaInterval).where(TicketSlaInterval.ticket_id == ticket.id)):
        interval_start = max(started_at, _aware(item.started_at))
        interval_end = min(completed_at, _aware(item.ended_at or completed_at))
        minutes = calculate_working_minutes(db, calendar_id, interval_start, interval_end)
        if item.interval_type == "FLAG_PAUSE":
            customer_pending += minutes
        elif item.interval_type == "PENDING" and item.responsible_party == "CUSTOMER":
            customer_pending += minutes
        elif item.interval_type == "PENDING":
            millensys_pending += minutes
        elif item.interval_type == "ESCALATION":
            escalation += minutes
    accountable = max(0, gross - customer_pending - (0 if policy.include_escalation_time else escalation))
    target_minutes = clock.target_minutes
    return AccountableSlaResult(target_minutes, accountable, customer_pending, millensys_pending, escalation, target_minutes - accountable, max(0, accountable - target_minutes), accountable <= target_minutes, started_at, completed_at)


def resolution_sla_results(
    db: Session, tickets: list[Ticket], *, as_of: datetime | None = None
) -> dict[int, AccountableSlaResult]:
    """Calculate SLA evidence for many tickets with a fixed number of queries."""
    if not tickets:
        return {}
    now = as_of or server_now()
    exempt_type_ids = set(db.scalars(select(TicketType.id).where(
        TicketType.code.in_(SLA_EXEMPT_TICKET_TYPE_CODES)
    )))
    ticket_ids = [item.id for item in tickets if item.ticket_type_id not in exempt_type_ids]
    if not ticket_ids:
        return {}
    clocks: dict[int, TicketSlaClock] = {}
    for ticket_id_batch in _id_batches(ticket_ids):
        clocks.update({
            item.ticket_id: item
            for item in db.scalars(select(TicketSlaClock).where(
                TicketSlaClock.ticket_id.in_(ticket_id_batch),
                TicketSlaClock.clock_type == "RESOLUTION",
            ))
        })
    results: dict[int, AccountableSlaResult] = {}
    for ticket_id, clock in clocks.items():
        if (
            clock.completed_at is not None
            and clock.accountable_minutes is not None
            and clock.customer_pending_minutes is not None
            and clock.millensys_pending_minutes is not None
            and clock.escalation_minutes is not None
            and clock.saved_minutes is not None
            and clock.overrun_minutes is not None
        ):
            results[ticket_id] = AccountableSlaResult(
                clock.target_minutes,
                clock.accountable_minutes,
                clock.customer_pending_minutes,
                clock.millensys_pending_minutes,
                clock.escalation_minutes,
                clock.saved_minutes,
                clock.overrun_minutes,
                clock.accountable_minutes <= clock.target_minutes,
                _aware(clock.started_at),
                _aware(clock.completed_at),
            )
    unresolved_ticket_ids = [ticket_id for ticket_id in ticket_ids if ticket_id not in results]
    unresolved_clocks = [clock for ticket_id, clock in clocks.items() if ticket_id not in results]
    assignments = first_dedicated_assignments(db, unresolved_ticket_ids)
    policy_ids = {item.policy_id for item in unresolved_clocks}
    policies = {item.id: item for item in db.scalars(select(SlaPolicy).where(SlaPolicy.id.in_(policy_ids)))} if policy_ids else {}
    contract_ids = {item.contract_id for item in unresolved_clocks if item.contract_id}
    contracts = {item.id: item for item in db.scalars(select(Contract).where(Contract.id.in_(contract_ids)))} if contract_ids else {}
    calendar_ids = {
        clock.calendar_id or policies[clock.policy_id].calendar_id
        for clock in unresolved_clocks if clock.policy_id in policies
    }
    calendars = {item.id: item for item in db.scalars(select(BusinessCalendar).where(BusinessCalendar.id.in_(calendar_ids)))} if calendar_ids else {}
    schedules: dict[int, dict[int, tuple[time, time]]] = {}
    if calendar_ids:
        for day_row in db.scalars(select(BusinessCalendarDay).where(
            BusinessCalendarDay.calendar_id.in_(calendar_ids),
            BusinessCalendarDay.is_working_day.in_([True]),
        )):
            schedules.setdefault(day_row.calendar_id, {})[day_row.weekday] = (day_row.start_time, day_row.end_time)
    holidays: dict[int, set[date]] = {}
    if calendar_ids:
        for holiday_row in db.scalars(select(Holiday).where(Holiday.calendar_id.in_(calendar_ids))):
            holidays.setdefault(holiday_row.calendar_id, set()).add(holiday_row.holiday_date)
    intervals: dict[int, list[TicketSlaInterval]] = {}
    for ticket_id_batch in _id_batches(unresolved_ticket_ids):
        for interval_row in db.scalars(select(TicketSlaInterval).where(TicketSlaInterval.ticket_id.in_(ticket_id_batch))):
            intervals.setdefault(interval_row.ticket_id, []).append(interval_row)
    for ticket in tickets:
        if ticket.id in results:
            continue
        ticket_clock = clocks.get(ticket.id)
        started_at = ticket_clock.started_at if ticket_clock else None
        contract = contracts.get(ticket_clock.contract_id) if ticket_clock and ticket_clock.contract_id else None
        if not ticket_clock or not started_at or (contract is not None and not contract.has_sla):
            continue
        completed_at = ticket.closed_at or ticket_clock.completed_at or now
        if _aware(started_at) > _aware(completed_at):
            started_at = assignments.get(ticket.id, started_at)
        policy = policies.get(ticket_clock.policy_id)
        calendar_id = ticket_clock.calendar_id or policy.calendar_id if policy else None
        calendar = calendars.get(calendar_id) if calendar_id else None
        if not policy or not calendar:
            continue
        started_at, completed_at = _aware(started_at), _aware(completed_at)
        if completed_at < started_at:
            continue
        schedule = schedules.get(calendar.id, {})
        calendar_holidays = holidays.get(calendar.id, set())
        gross = working_minutes_between(
            started_at, completed_at, calendar.timezone, schedule, calendar_holidays
        )
        customer_pending = millensys_pending = escalation = 0
        for interval in intervals.get(ticket.id, []):
            interval_start = max(started_at, _aware(interval.started_at))
            interval_end = min(completed_at, _aware(interval.ended_at or completed_at))
            minutes = working_minutes_between(
                interval_start, interval_end, calendar.timezone, schedule, calendar_holidays
            )
            if interval.interval_type == "FLAG_PAUSE":
                customer_pending += minutes
            elif interval.interval_type == "PENDING" and interval.responsible_party == "CUSTOMER":
                customer_pending += minutes
            elif interval.interval_type == "PENDING":
                millensys_pending += minutes
            elif interval.interval_type == "ESCALATION":
                escalation += minutes
        accountable = max(0, gross - customer_pending - (0 if policy.include_escalation_time else escalation))
        target_minutes = ticket_clock.target_minutes
        results[ticket.id] = AccountableSlaResult(
            target_minutes, accountable, customer_pending, millensys_pending,
            escalation, target_minutes - accountable,
            max(0, accountable - target_minutes), accountable <= target_minutes,
            started_at, completed_at,
        )
    return results


def attach_ticket_sla_evidence(
    db: Session, tickets: list[Ticket], *, as_of: datetime | None = None
) -> list[Ticket]:
    """Attach response-model-only SLA evidence to ticket ORM instances."""
    if not tickets:
        return tickets
    now = as_of or server_now()
    ticket_ids = [ticket.id for ticket in tickets]
    exempt_type_ids = set(db.scalars(select(TicketType.id).where(
        TicketType.code.in_(SLA_EXEMPT_TICKET_TYPE_CODES)
    )))
    clocks_by_ticket: dict[int, dict[str, TicketSlaClock]] = {}
    for ticket_id_batch in _id_batches(ticket_ids):
        for clock in db.scalars(
            select(TicketSlaClock).where(TicketSlaClock.ticket_id.in_(ticket_id_batch))
        ):
            clocks_by_ticket.setdefault(clock.ticket_id, {})[clock.clock_type] = clock
    resolution_results = resolution_sla_results(
        db, [ticket for ticket in tickets if ticket.entitlement_status == "COVERED"], as_of=now
    )
    for ticket in tickets:
        if ticket.entitlement_status != "COVERED" or ticket.ticket_type_id in exempt_type_ids:
            for field in (
                "sla_first_response_target_minutes", "sla_first_response_actual_minutes",
                "sla_resolution_target_minutes", "sla_actual_business_minutes",
                "sla_saved_minutes", "sla_overrun_minutes", "sla_resolution_state",
                "sla_match_reason", "sla_target_id", "sla_policy_version", "sla_calendar_id",
            ):
                ticket.__dict__[field] = None
            continue
        clocks = clocks_by_ticket.get(ticket.id, {})
        response = clocks.get("FIRST_RESPONSE")
        resolution = clocks.get("RESOLUTION")
        ticket.__dict__["sla_first_response_target_minutes"] = response.target_minutes if response else None
        ticket.__dict__["sla_first_response_actual_minutes"] = response.actual_response_minutes if response else None
        if response and response.completed_at and response.actual_response_minutes is None:
            policy = db.get(SlaPolicy, response.policy_id)
            if policy:
                ticket.__dict__["sla_first_response_actual_minutes"] = calculate_working_minutes(
                    db, response.calendar_id or policy.calendar_id, _aware(ticket.created_at), _aware(response.completed_at)
                )
        ticket.__dict__["sla_resolution_target_minutes"] = resolution.target_minutes if resolution else None
        result = resolution_results.get(ticket.id)
        ticket.__dict__["sla_actual_business_minutes"] = result.accountable_minutes if result else None
        ticket.__dict__["sla_saved_minutes"] = result.saved_minutes if result else None
        ticket.__dict__["sla_overrun_minutes"] = result.overrun_minutes if result else None
        ticket.__dict__["sla_resolution_state"] = resolution.state if resolution else None
        ticket.__dict__["sla_match_reason"] = resolution.match_reason if resolution else None
        ticket.__dict__["sla_target_id"] = resolution.target_id if resolution else None
        ticket.__dict__["sla_policy_version"] = resolution.policy_version if resolution else None
        ticket.__dict__["sla_calendar_id"] = resolution.calendar_id if resolution else None
    return tickets
