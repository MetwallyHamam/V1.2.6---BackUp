import csv
import io
import json
import math
import statistics
from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import date, datetime, time, timedelta
from typing import Any, Literal, cast

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased, load_only, selectinload

from app.api.dependencies import current_user
from app.core.clock import server_timezone, server_today
from app.core.exceptions import AuthorizationError, ConflictError
from app.db.session import get_db
from app.modules.clients.models import (
    Branch,
    Client,
    ClientLocation,
    Country,
    Product,
    SupportTeam,
    SupportTeamMember,
)
from app.modules.complaints.models import Complaint
from app.modules.contracts.models import (
    BusinessCalendar,
    BusinessCalendarDay,
    Contract,
    Holiday,
    SlaPolicy,
    TicketSlaClock,
)
from app.modules.contracts.service import working_minutes_between
from app.modules.iam.models import Department, User
from app.modules.iam.service import effective_permissions
from app.modules.sla.service import AccountableSlaResult, resolution_sla_results
from app.modules.tickets.models import (
    RootCause,
    Ticket,
    TicketRootCause,
    TicketSatisfaction,
    TicketStatus,
    TicketType,
    TicketWorklog,
)

router = APIRouter(prefix="/management-dashboards", tags=["management dashboards"])
EVIDENCE_LIMIT = 100


def _period_bounds(period: Literal["MONTH", "QUARTER", "YEAR"], anchor: date) -> tuple[datetime, datetime, datetime, datetime]:
    if period == "YEAR":
        start = date(anchor.year, 1, 1); previous = date(anchor.year - 1, 1, 1)
    elif period == "QUARTER":
        month = ((anchor.month - 1) // 3) * 3 + 1; start = date(anchor.year, month, 1)
        previous = (start - timedelta(days=1)).replace(day=1)
        previous = date(previous.year, ((previous.month - 1) // 3) * 3 + 1, 1)
    else:
        start = date(anchor.year, anchor.month, 1); last = start - timedelta(days=1); previous = date(last.year, last.month, 1)
    if period == "YEAR": end = date(start.year + 1, 1, 1); previous_end = start
    elif period == "QUARTER":
        end = date(start.year + (start.month + 2) // 12, (start.month + 2) % 12 + 1, 1); previous_end = start
    else: end = date(start.year + start.month // 12, start.month % 12 + 1, 1); previous_end = start
    def aware(value: date) -> datetime:
        return datetime.combine(value, datetime.min.time(), tzinfo=server_timezone())
    return aware(start), aware(end), aware(previous), aware(previous_end)


def _analytics_bounds(
    period: Literal["MONTH", "QUARTER", "YEAR"],
    anchor: date,
    date_from: date | None,
    date_to: date | None,
    timezone_offset_minutes: int = 0,
) -> tuple[datetime, datetime, datetime, datetime]:
    if (date_from is None) != (date_to is None):
        raise ConflictError("INVALID_ANALYTICS_PERIOD", "Both From and To dates are required.")
    if date_from and date_to:
        if date_from > date_to:
            raise ConflictError("INVALID_ANALYTICS_PERIOD", "From date cannot be after To date.")
        start = datetime.combine(date_from, datetime.min.time(), tzinfo=server_timezone())
        end = datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=server_timezone())
        duration = end - start
        return start, end, start - duration, start
    bounds = _period_bounds(period, anchor)
    return bounds


def _breakdown(items: list[str]) -> list[dict[str, object]]:
    counts = Counter(items)
    return [
        {"key": key, "label": key, "value": value}
        for key, value in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _breakdown_rows(rows: list[tuple[str, int]]) -> list[dict[str, object]]:
    return [
        {"key": key, "label": key, "value": value}
        for key, value in sorted(rows, key=lambda item: (-item[1], item[0]))
    ]


def _duration_statistics(values: list[float]) -> dict[str, float | int | None]:
    """Return transparent distribution measures for a governed duration sample."""
    ordered = sorted(value for value in values if value >= 0)
    if not ordered:
        return {"average": None, "median": None, "p90": None, "sample_size": 0}
    p90_index = max(0, math.ceil(len(ordered) * 0.9) - 1)
    return {
        "average": round(sum(ordered) / len(ordered), 2),
        "median": round(statistics.median(ordered), 2),
        "p90": round(ordered[p90_index], 2),
        "sample_size": len(ordered),
    }


@router.get("/metadata")
def metadata(db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict[str, object]:
    if "dashboard.executive" not in effective_permissions(db, user).permissions:
        raise AuthorizationError()
    clients = list(db.scalars(select(Client).where(Client.is_active.in_([True])).order_by(Client.name)))
    countries = list(db.scalars(select(Country).where(Country.is_active.in_([True])).order_by(Country.name)))
    locations = list(db.scalars(select(ClientLocation).where(ClientLocation.is_active.in_([True])).order_by(ClientLocation.name)))
    return {
        "countries": [{"id": item.id, "name": item.name, "iso_alpha2": item.iso_alpha2} for item in countries],
        "zones": sorted({item.zone for item in locations if item.zone}),
        "clients": [{"id": item.id, "name": item.name} for item in clients],
        "locations": [{"id": item.id, "client_id": item.client_id, "name": item.name} for item in locations],
        "products": [{"id": item.id, "name": item.name} for item in db.scalars(select(Product).where(Product.is_active.in_([True])).order_by(Product.name))],
        "teams": [{"id": item.id, "name": item.name} for item in db.scalars(select(SupportTeam).where(SupportTeam.is_active.in_([True])).order_by(SupportTeam.name))],
        "engineers": [{"id": item.id, "name": item.full_name} for item in db.scalars(select(User).where(User.is_active.in_([True]), User.user_type == "EMPLOYEE").order_by(User.full_name))],
        "departments": [{"id": item.id, "name": item.name} for item in db.scalars(select(Department).where(Department.is_active.in_([True])).order_by(Department.name))],
    }


@router.get("/analytics")
def analytics(period: Literal["MONTH", "QUARTER", "YEAR"] = "MONTH", anchor: date = Query(default_factory=date.today), date_from: date | None = None, date_to: date | None = None, country_id: int | None = None, zone: str | None = None, client_id: int | None = None, location_id: int | None = None, product_id: int | None = None, team_id: int | None = None, engineer_id: int | None = None, department_id: int | None = None, timezone_offset_minutes: int = Query(default=180, ge=-840, le=840), db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict[str, object]:
    if "dashboard.executive" not in effective_permissions(db, user).permissions:
        raise AuthorizationError()
    start, end, previous_start, previous_end = _analytics_bounds(period, anchor, date_from, date_to, timezone_offset_minutes)
    clients = {item.id: item for item in db.scalars(select(Client))}
    countries = {item.id: item for item in db.scalars(select(Country))}; locations = {item.id: item for item in db.scalars(select(ClientLocation))}
    team_users = set(db.scalars(select(SupportTeamMember.user_id).where(SupportTeamMember.team_id == team_id))) if team_id else None
    ticket_scope = select(Ticket).where(Ticket.archived_at.is_(None))
    if client_id:
        ticket_scope = ticket_scope.where(Ticket.client_id == client_id)
    if product_id:
        ticket_scope = ticket_scope.where(Ticket.product_id == product_id)
    if engineer_id:
        ticket_scope = ticket_scope.where(Ticket.assigned_user_id == engineer_id)
    if department_id:
        department_users = select(User.id).where(User.department_id == department_id)
        ticket_scope = ticket_scope.where(Ticket.assigned_user_id.in_(department_users))
    if team_users is not None:
        ticket_scope = ticket_scope.where(Ticket.assigned_user_id.in_(team_users or [-1]))
    if country_id or zone or location_id:
        branch_location = aliased(ClientLocation)
        client_location = aliased(ClientLocation)
        ticket_scope = (
            ticket_scope
            .join(Client, Client.id == Ticket.client_id)
            .outerjoin(Branch, Branch.id == Ticket.branch_id)
            .outerjoin(branch_location, branch_location.id == Branch.location_id)
            .outerjoin(client_location, client_location.id == Client.primary_location_id)
        )
        effective_location_id = func.coalesce(branch_location.id, client_location.id)
        effective_country_id = func.coalesce(branch_location.country_id, client_location.country_id, Client.country_id)
        effective_zone = func.coalesce(branch_location.zone, client_location.zone, Client.zone)
        if location_id:
            ticket_scope = ticket_scope.where(effective_location_id == location_id)
        if country_id:
            ticket_scope = ticket_scope.where(effective_country_id == country_id)
        if zone:
            ticket_scope = ticket_scope.where(effective_zone == zone)
    scoped_tickets = ticket_scope.subquery("management_tickets")
    current_period_filter = and_(
        scoped_tickets.c.created_at >= start,
        scoped_tickets.c.created_at < end,
    )
    def average(values: list[float]) -> float | None:
        return round(sum(values) / len(values), 2) if values else None
    response_clock_rows = list(
        db.execute(
            select(
                TicketSlaClock.ticket_id,
                TicketSlaClock.policy_id,
                TicketSlaClock.calendar_id,
                TicketSlaClock.started_at,
                TicketSlaClock.completed_at,
                TicketSlaClock.actual_response_minutes,
                scoped_tickets.c.ticket_number,
                scoped_tickets.c.client_id,
                scoped_tickets.c.priority,
            )
            .join(scoped_tickets, scoped_tickets.c.id == TicketSlaClock.ticket_id)
            .where(
                current_period_filter,
            TicketSlaClock.clock_type == "FIRST_RESPONSE",
            TicketSlaClock.completed_at.is_not(None),
            )
        )
    )
    resolution_clock_rows = list(
        db.execute(
            select(
                TicketSlaClock.ticket_id,
                TicketSlaClock.target_minutes,
                TicketSlaClock.accountable_minutes,
                TicketSlaClock.customer_pending_minutes,
                TicketSlaClock.millensys_pending_minutes,
                TicketSlaClock.escalation_minutes,
                TicketSlaClock.saved_minutes,
                TicketSlaClock.overrun_minutes,
                TicketSlaClock.started_at,
                TicketSlaClock.completed_at,
                scoped_tickets.c.ticket_number,
                scoped_tickets.c.client_id,
                scoped_tickets.c.priority,
            )
            .join(scoped_tickets, scoped_tickets.c.id == TicketSlaClock.ticket_id)
            .where(
                current_period_filter,
                TicketSlaClock.clock_type == "RESOLUTION",
            )
        )
    )
    completed_resolution_ids = {
        row.ticket_id for row in resolution_clock_rows if row.completed_at is not None
    }
    snapshot_sla = {
        row.ticket_id: AccountableSlaResult(
            row.target_minutes,
            row.accountable_minutes,
            row.customer_pending_minutes,
            row.millensys_pending_minutes,
            row.escalation_minutes,
            row.saved_minutes,
            row.overrun_minutes,
            row.accountable_minutes <= row.target_minutes,
            row.started_at,
            row.completed_at,
        )
        for row in resolution_clock_rows
        if row.completed_at is not None
        and row.accountable_minutes is not None
        and row.customer_pending_minutes is not None
        and row.millensys_pending_minutes is not None
        and row.escalation_minutes is not None
        and row.saved_minutes is not None
        and row.overrun_minutes is not None
    }
    resolution_client_ids = {
        row.ticket_id: int(row.client_id) for row in resolution_clock_rows
    }
    resolution_evidence_details = {
        row.ticket_id: (row.ticket_number, int(row.client_id), row.priority)
        for row in resolution_clock_rows
    }
    incomplete_resolution_snapshot = or_(
        TicketSlaClock.completed_at.is_(None),
        TicketSlaClock.accountable_minutes.is_(None),
        TicketSlaClock.customer_pending_minutes.is_(None),
        TicketSlaClock.millensys_pending_minutes.is_(None),
        TicketSlaClock.escalation_minutes.is_(None),
        TicketSlaClock.saved_minutes.is_(None),
        TicketSlaClock.overrun_minutes.is_(None),
    )
    unresolved_resolution_tickets = list(
        db.execute(
            ticket_scope
            .join(TicketSlaClock, TicketSlaClock.ticket_id == Ticket.id)
            .where(
                Ticket.created_at >= start,
                Ticket.created_at < end,
                TicketSlaClock.clock_type == "RESOLUTION",
                incomplete_resolution_snapshot,
            )
            .options(
                load_only(
                    Ticket.id,
                    Ticket.ticket_number,
                    Ticket.client_id,
                    Ticket.priority,
                    Ticket.closed_at,
                )
            )
        ).unique().scalars()
    )
    calculated_sla = resolution_sla_results(
        db, unresolved_resolution_tickets,
    )
    # Historical ranges must not age still-open clocks through the current day.
    # Compliance and resolution duration describe completed support work only.
    sla = {ticket_id: result for ticket_id, result in {**snapshot_sla, **calculated_sla}.items()
           if ticket_id in completed_resolution_ids}
    response_policies = {
        item.id: item for item in db.scalars(select(SlaPolicy).where(
            SlaPolicy.id.in_({row.policy_id for row in response_clock_rows} or {-1})
        ))
    }
    response_calendar_ids = {
        row.calendar_id or policy.calendar_id
        for row in response_clock_rows
        if (policy := response_policies.get(row.policy_id)) is not None
    }
    response_calendars = {
        item.id: item
        for item in db.scalars(
            select(BusinessCalendar).where(
                BusinessCalendar.id.in_(response_calendar_ids or {-1})
            )
        )
    }
    response_working_days: dict[int, dict[int, tuple[time, time]]] = defaultdict(dict)
    for day in db.scalars(
        select(BusinessCalendarDay).where(
            BusinessCalendarDay.calendar_id.in_(response_calendar_ids or {-1}),
            BusinessCalendarDay.is_working_day.in_([True]),
        )
    ):
        response_working_days[day.calendar_id][day.weekday] = (day.start_time, day.end_time)
    response_holidays: dict[int, set[date]] = defaultdict(set)
    for holiday in db.scalars(
        select(Holiday).where(Holiday.calendar_id.in_(response_calendar_ids or {-1}))
    ):
        response_holidays[holiday.calendar_id].add(holiday.holiday_date)
    response_hours = []
    response_evidence: list[dict[str, object]] = []
    for clock_row in response_clock_rows:
        policy = response_policies.get(clock_row.policy_id)
        if not policy or clock_row.completed_at is None:
            continue
        calendar_id = clock_row.calendar_id or policy.calendar_id
        calendar = response_calendars.get(calendar_id)
        if not calendar:
            continue
        hours = (
            clock_row.actual_response_minutes / 60
            if clock_row.actual_response_minutes is not None
            else working_minutes_between(
                clock_row.started_at,
                clock_row.completed_at,
                calendar.timezone,
                response_working_days.get(calendar_id, {}),
                response_holidays.get(calendar_id, set()),
            )
            / 60
        )
        response_hours.append(hours)
        if len(response_evidence) < EVIDENCE_LIMIT:
            response_evidence.append({"ticket":clock_row.ticket_number,"client":clients[int(clock_row.client_id)].name,"priority":clock_row.priority,"business_hours":round(hours,2),"completed_at":clock_row.completed_at,"route":f"/tickets/{clock_row.ticket_id}"})
    resolution_hours = [result.accountable_minutes / 60 for ticket_id, result in sla.items() if ticket_id in completed_resolution_ids]
    resolution_evidence: list[dict[str, object]] = []
    for ticket_id, result in sla.items():
        if ticket_id not in completed_resolution_ids or ticket_id not in resolution_evidence_details:
            continue
        ticket_number, linked_client_id, ticket_priority = resolution_evidence_details[ticket_id]
        resolution_evidence.append({"ticket":ticket_number,"client":clients[linked_client_id].name,"priority":ticket_priority,"accountable_hours":round(result.accountable_minutes/60,2),"customer_pending_hours":round(result.customer_pending_minutes/60,2),"saved_hours":round(result.saved_minutes/60,2),"route":f"/tickets/{ticket_id}"})
        if len(resolution_evidence) >= EVIDENCE_LIMIT:
            break
    response_stats = _duration_statistics(response_hours)
    resolution_stats = _duration_statistics(resolution_hours)
    contracts = [item for item in db.scalars(select(Contract)) if (not client_id or item.client_id == client_id)]
    survey_rows = list(
        db.execute(
            select(TicketSatisfaction.service_rating, scoped_tickets.c.client_id)
            .join(scoped_tickets, scoped_tickets.c.id == TicketSatisfaction.ticket_id)
            .where(
                current_period_filter,
                TicketSatisfaction.submitted_at.is_not(None),
            )
        )
    )
    current_count, previous_count = db.execute(select(
        func.sum(case((and_(scoped_tickets.c.created_at >= start, scoped_tickets.c.created_at < end), 1), else_=0)),
        func.sum(case((and_(scoped_tickets.c.created_at >= previous_start, scoped_tickets.c.created_at < previous_end), 1), else_=0)),
    )).one()
    current_count = int(current_count or 0)
    previous_count = int(previous_count or 0)
    current_period_scope = and_(
        scoped_tickets.c.created_at >= start,
        scoped_tickets.c.created_at < end,
    )

    def grouped_breakdown(
        label: Any, *, group_expression: Any | None = None, outer: bool = False
    ) -> list[dict[str, object]]:
        statement = select(label, func.count(scoped_tickets.c.id)).select_from(scoped_tickets)
        if label is TicketStatus.code:
            statement = statement.join(TicketStatus, TicketStatus.id == scoped_tickets.c.status_id)
        elif label is User.full_name:
            statement = statement.join(User, User.id == scoped_tickets.c.assigned_user_id)
        elif outer:
            statement = statement.outerjoin(Product, Product.id == scoped_tickets.c.product_id)
        rows = db.execute(
            statement.where(current_period_scope).group_by(
                group_expression if group_expression is not None else label
            )
        ).all()
        return _breakdown_rows([(str(key), int(value)) for key, value in rows])

    status_mix = grouped_breakdown(TicketStatus.code)
    priority_mix = grouped_breakdown(scoped_tickets.c.priority)
    product_mix = [
        {"key": str(key) if key is not None else "__NONE__", "label": str(name or "Unspecified"), "value": int(count)}
        for key, name, count in db.execute(
            select(scoped_tickets.c.product_id, Product.name, func.count(scoped_tickets.c.id))
            .select_from(scoped_tickets).outerjoin(Product, Product.id == scoped_tickets.c.product_id)
            .where(current_period_scope).group_by(scoped_tickets.c.product_id, Product.name)
            .order_by(func.count(scoped_tickets.c.id).desc())
        )
    ]
    workload = [
        {"key": str(key), "label": str(name), "value": int(count)}
        for key, name, count in db.execute(
            select(User.id, User.full_name, func.count(scoped_tickets.c.id))
            .select_from(scoped_tickets).join(User, User.id == scoped_tickets.c.assigned_user_id)
            .where(current_period_scope).group_by(User.id, User.full_name)
            .order_by(func.count(scoped_tickets.c.id).desc())
        )
    ]
    support_consumption = [
        {"key": str(key), "label": str(name), "value": int(count)}
        for key, name, count in db.execute(
            select(Client.id, Client.name, func.count(scoped_tickets.c.id))
            .select_from(scoped_tickets).join(Client, Client.id == scoped_tickets.c.client_id)
            .where(current_period_scope).group_by(Client.id, Client.name)
            .order_by(func.count(scoped_tickets.c.id).desc(), Client.name)
        )
    ]
    approved_worklog_minutes: dict[int, int] = {}
    customer_minutes: dict[int, int] = defaultdict(int)
    for ticket_id, linked_client_id, minutes in db.execute(
        select(TicketWorklog.ticket_id, scoped_tickets.c.client_id, func.sum(TicketWorklog.duration_minutes))
        .select_from(TicketWorklog)
        .join(scoped_tickets, scoped_tickets.c.id == TicketWorklog.ticket_id)
        .where(TicketWorklog.status == "APPROVED", TicketWorklog.started_at >= start, TicketWorklog.started_at < end)
        .group_by(TicketWorklog.ticket_id, scoped_tickets.c.client_id)
    ):
        approved_worklog_minutes[int(ticket_id)] = int(minutes or 0)
        customer_minutes[int(linked_client_id)] += int(minutes or 0)
    if sla:
        for ticket_id, linked_client_id in db.execute(
            select(scoped_tickets.c.id, scoped_tickets.c.client_id)
            .select_from(scoped_tickets)
            .join(TicketStatus, TicketStatus.id == scoped_tickets.c.status_id)
            .where(
                current_period_scope,
                scoped_tickets.c.id.in_(set(sla)),
                TicketStatus.code.in_(["RESOLVED", "CLOSED"]),
            )
        ):
            if int(ticket_id) not in approved_worklog_minutes:
                customer_minutes[int(linked_client_id)] += sla[int(ticket_id)].accountable_minutes
    customer_workhours = [
        {"key": str(linked_client_id), "label": clients[linked_client_id].name, "value": round(minutes / 60, 2)}
        for linked_client_id, minutes in sorted(
            customer_minutes.items(), key=lambda item: (-item[1], clients[item[0]].name)
        ) if minutes and linked_client_id in clients
    ]
    root_cause_mix = [
        {"key": str(key), "label": str(name), "value": int(count)}
        for key, name, count in db.execute(
            select(RootCause.id, RootCause.name, func.count(TicketRootCause.ticket_id))
            .select_from(TicketRootCause).join(scoped_tickets, scoped_tickets.c.id == TicketRootCause.ticket_id)
            .join(RootCause, RootCause.id == TicketRootCause.root_cause_id)
            .where(current_period_scope).group_by(RootCause.id, RootCause.name)
            .order_by(func.count(TicketRootCause.ticket_id).desc())
        )
    ]
    resolved_count = int(
        db.scalar(
            select(func.count(scoped_tickets.c.id)).where(
                current_period_scope,
                scoped_tickets.c.resolved_at.is_not(None),
            )
        )
        or 0
    )
    sla_evidence = [
        {
            "ticket": resolution_evidence_details[ticket_id][0],
            "client": clients[resolution_evidence_details[ticket_id][1]].name,
            "priority": resolution_evidence_details[ticket_id][2],
            "met": result.met,
            "target_minutes": result.target_minutes,
            "accountable_minutes": result.accountable_minutes,
            "route": f"/tickets/{ticket_id}",
        }
        for ticket_id, result in sla.items()
        if ticket_id in resolution_evidence_details
    ]
    satisfaction_evidence = [
        {
            "ticket": ticket_number,
            "client": clients[int(linked_client_id)].name,
            "rating": rating,
            "submitted_at": submitted_at,
            "route": f"/tickets/{ticket_id}",
        }
        for ticket_id, ticket_number, linked_client_id, rating, submitted_at in db.execute(
            select(
                scoped_tickets.c.id,
                scoped_tickets.c.ticket_number,
                scoped_tickets.c.client_id,
                TicketSatisfaction.service_rating,
                TicketSatisfaction.submitted_at,
            )
            .join(scoped_tickets, scoped_tickets.c.id == TicketSatisfaction.ticket_id)
            .where(current_period_filter, TicketSatisfaction.submitted_at.is_not(None))
            .order_by(TicketSatisfaction.submitted_at.desc())
        )
    ]
    def comparison(value: int, old: int) -> dict[str, int | float]:
        return {"current": value, "previous": old, "change_percent": round((value-old)*100/old, 1) if old else (100.0 if value else 0.0)}
    trend=[]; bucket_bounds: list[tuple[datetime, datetime]] = []; cursor=start; period_days=(end-start).days
    while cursor < end:
        if period_days <= 45:
            bucket_end=min(cursor+timedelta(days=1),end); label=cursor.strftime("%d %b")
        elif period_days <= 180:
            bucket_end=min(cursor+timedelta(days=7),end); label=cursor.strftime("%d %b")
        else:
            bucket_end=min(datetime(cursor.year + cursor.month//12,cursor.month%12+1,1,tzinfo=server_timezone()),end); label=cursor.strftime("%b %Y")
        trend.append({"label":label,"created":0,"resolved":0})
        bucket_bounds.append((cursor, bucket_end))
        cursor=bucket_end
    trend_expressions: list[Any] = []
    for bucket_start, bucket_end in bucket_bounds:
        trend_expressions.extend((
            func.sum(case((and_(scoped_tickets.c.created_at >= bucket_start, scoped_tickets.c.created_at < bucket_end), 1), else_=0)),
            func.sum(case((and_(scoped_tickets.c.resolved_at >= bucket_start, scoped_tickets.c.resolved_at < bucket_end), 1), else_=0)),
        ))
    trend_values = db.execute(select(*trend_expressions)).one()
    for index in range(len(bucket_bounds)):
        trend[index]["created"] = int(trend_values[index * 2] or 0)
        trend[index]["resolved"] = int(trend_values[index * 2 + 1] or 0)
    # Supported markets are a client-master fact, not a ticket-volume fact.
    # Include every structured country linked directly to an active client or
    # through one of its active locations, while counting each client once per
    # country. This keeps zero-ticket client markets visible and excludes
    # unrelated entries from the country catalog.
    active_clients = [item for item in clients.values() if item.is_active and (not client_id or item.id == client_id)]
    active_locations = [item for item in locations.values() if item.is_active and item.client_id in {client.id for client in active_clients}]
    if location_id:
        active_locations = [item for item in active_locations if item.id == location_id]
        allowed_client_ids = {item.client_id for item in active_locations}
        active_clients = [item for item in active_clients if item.id in allowed_client_ids]
    if zone:
        active_locations = [item for item in active_locations if item.zone == zone]
        allowed_client_ids = {item.client_id for item in active_locations}
        active_clients = [item for item in active_clients if item.id in allowed_client_ids or item.zone == zone]
    country_clients: dict[int, set[int]] = {}
    country_locations: dict[int, list[ClientLocation]] = {}
    for linked_client in active_clients:
        if linked_client.country_id and (not country_id or linked_client.country_id == country_id):
            country_clients.setdefault(linked_client.country_id, set()).add(linked_client.id)
    for linked_location in active_locations:
        if not country_id or linked_location.country_id == country_id:
            country_clients.setdefault(linked_location.country_id, set()).add(linked_location.client_id)
            country_locations.setdefault(linked_location.country_id, []).append(linked_location)
    country_rows: list[dict[str, object]] = []
    for key, linked_client_ids in country_clients.items():
        country = countries.get(key)
        if not country:
            continue
        positioned = [row for row in country_locations.get(key, []) if row.latitude is not None and row.longitude is not None]
        country_rows.append({
            "key": country.iso_alpha2, "label": country.name, "value": len(linked_client_ids),
            "clients": [
                {"id": linked_id, "name": clients[linked_id].name}
                for linked_id in sorted(linked_client_ids, key=lambda item: clients[item].name.lower())
                if linked_id in clients
            ],
            "latitude": round(sum(float(row.latitude) for row in positioned if row.latitude is not None) / len(positioned), 6) if positioned else None,
            "longitude": round(sum(float(row.longitude) for row in positioned if row.longitude is not None) / len(positioned), 6) if positioned else None,
        })
    country_rows.sort(key=lambda row: (-int(str(row["value"])), str(row["label"])))
    # These analytics are creation-period based. Use the ticket queue's date
    # parameter names so a card opens the same population that produced it.
    filters={"created_from":date_from.isoformat() if date_from else (start + timedelta(minutes=timezone_offset_minutes)).date().isoformat(),"created_to":date_to.isoformat() if date_to else (end + timedelta(minutes=timezone_offset_minutes) - timedelta(days=1)).date().isoformat(),"timezone_offset_minutes":timezone_offset_minutes,"department_id":department_id,"country_id":country_id,"zone":zone,"client_id":client_id,"location_id":location_id,"product_id":product_id,"team_id":team_id,"engineer_id":engineer_id}
    def widget(code: str, title: str, value: object, route: str = "/tickets", params: dict[str, object] | None = None, evidence: list[dict[str, object]] | None = None) -> dict[str, object]:
        return {"code":code,"title":title,"value":value,"drilldown":{"route":route,"params":{**{k:v for k,v in filters.items() if v is not None},**(params or {})}},"evidence":evidence}
    profile_clients = sorted(
        (item for item in clients.values() if item.is_active and (not client_id or item.id == client_id)),
        key=lambda item: item.name,
    )
    surveys_by_client: dict[int, list[float]] = {}
    for service_rating, linked_client_id in survey_rows:
        if service_rating is not None:
            surveys_by_client.setdefault(int(linked_client_id), []).append(
                float(service_rating)
            )
    health_ticket_rows = db.execute(
        select(
            scoped_tickets.c.client_id,
            func.count(scoped_tickets.c.id),
            func.sum(case((scoped_tickets.c.resolved_at.is_(None), 1), else_=0)),
            func.sum(
                case(
                    (
                        and_(
                            scoped_tickets.c.resolved_at.is_(None),
                            scoped_tickets.c.priority == "P1",
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
            func.sum(case((scoped_tickets.c.resolved_at.is_not(None), 1), else_=0)),
            func.sum(case((scoped_tickets.c.reopened_at.is_not(None), 1), else_=0)),
        )
        .where(
            scoped_tickets.c.created_at >= start,
            scoped_tickets.c.created_at < end,
        )
        .group_by(scoped_tickets.c.client_id)
    )
    health_tickets_by_client = {
        int(client_key): {
            "tickets": int(total or 0),
            "open": int(open_count or 0),
            "critical_open": int(critical_open or 0),
            "resolved": int(resolved_count or 0),
            "reopened": int(reopened_count or 0),
        }
        for client_key, total, open_count, critical_open, resolved_count, reopened_count
        in health_ticket_rows
    }
    sla_by_client: dict[int, list[AccountableSlaResult]] = defaultdict(list)
    for ticket_id, result in sla.items():
        sla_client_id = resolution_client_ids.get(ticket_id)
        if sla_client_id is not None:
            sla_by_client[sla_client_id].append(result)
    contracts_by_client: dict[int, list[Contract]] = defaultdict(list)
    for contract in contracts:
        if contract.is_active:
            for customer_id in contract.customer_ids:
                contracts_by_client[customer_id].append(contract)
    client_health: list[dict[str, object]] = []
    today = server_today()
    incident_type_ids = set(
        db.scalars(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    )
    active_incident_scope = and_(
        current_period_scope,
        scoped_tickets.c.ticket_type_id.in_(incident_type_ids or {-1}),
        TicketStatus.is_closed_state.in_([False]),
    )
    active_incident_count = int(
        db.scalar(
            select(func.count(scoped_tickets.c.id))
            .select_from(scoped_tickets)
            .join(TicketStatus, TicketStatus.id == scoped_tickets.c.status_id)
            .where(active_incident_scope)
        )
        or 0
    )
    active_incident_evidence = [
        {
            "ticket": ticket_number,
            "client": clients[int(linked_client_id)].name,
            "priority": priority,
            "status": status_name,
            "subject": subject,
            "route": f"/tickets/{ticket_id}",
        }
        for ticket_id, ticket_number, linked_client_id, priority, status_name, subject
        in db.execute(
            select(
                scoped_tickets.c.id,
                scoped_tickets.c.ticket_number,
                scoped_tickets.c.client_id,
                scoped_tickets.c.priority,
                TicketStatus.name,
                scoped_tickets.c.subject,
            )
            .select_from(scoped_tickets)
            .join(TicketStatus, TicketStatus.id == scoped_tickets.c.status_id)
            .where(active_incident_scope)
            .order_by(scoped_tickets.c.created_at.desc(), scoped_tickets.c.id.desc())
            .limit(EVIDENCE_LIMIT)
        )
    ]
    profile_client_ids = [item.id for item in profile_clients]
    complaint_rows = db.execute(
        select(
            Complaint.client_id,
            func.count(Complaint.id),
            func.sum(
                case((Complaint.status.not_in(("RESOLVED", "CLOSED")), 1), else_=0)
            ),
        )
        .where(
            Complaint.created_at >= start,
            Complaint.created_at < end,
            Complaint.client_id.in_(profile_client_ids or [-1]),
        )
        .group_by(Complaint.client_id)
    )
    complaints_by_client = {
        int(client_key): (int(total or 0), int(open_count or 0))
        for client_key, total, open_count in complaint_rows
    }
    for linked_client in profile_clients:
        ticket_metrics = health_tickets_by_client.get(
            linked_client.id,
            {"tickets": 0, "open": 0, "critical_open": 0, "resolved": 0, "reopened": 0},
        )
        client_sla = sla_by_client.get(linked_client.id, [])
        client_contracts = contracts_by_client.get(linked_client.id, [])
        critical_open = ticket_metrics["critical_open"]
        sla_percent = round(sum(result.met for result in client_sla) * 100 / len(client_sla), 1) if client_sla else None
        client_ratings = surveys_by_client.get(linked_client.id, [])
        satisfaction = average(client_ratings) if len(client_ratings) >= 3 else None
        complaint_count, open_complaint_count = complaints_by_client.get(linked_client.id, (0, 0))
        ticket_count = ticket_metrics["tickets"]
        resolution_percent = round(ticket_metrics["resolved"] * 100 / ticket_count, 1) if ticket_count else 100.0
        quality_percent = round((ticket_count - ticket_metrics["reopened"]) * 100 / ticket_count, 1) if ticket_count else 100.0
        renewal_score = 100.0 if not any(0 <= (contract.end_date - today).days <= 60 for contract in client_contracts) else 40.0
        components: list[tuple[float, float]] = [(max(0.0, 100.0 - critical_open * 25.0), 20), (resolution_percent, 15), (quality_percent, 10), (renewal_score, 10)]
        if sla_percent is not None:
            components.append((sla_percent, 25))
        if satisfaction is not None:
            components.append((min(100.0, satisfaction * 20), 20))
        if complaint_count:
            components.append((max(0.0, 100.0 - open_complaint_count * 20.0), 15))
        has_health_evidence = bool(ticket_count or complaint_count)
        health_score = round(sum(score * weight for score, weight in components) / sum(weight for _, weight in components), 1) if has_health_evidence else None
        health_status = "INSUFFICIENT_DATA" if health_score is None else "HEALTHY" if health_score >= 80 else "NEEDS_ATTENTION" if health_score >= 60 else "AT_RISK"
        reasons = []
        if critical_open:
            reasons.append(f"{critical_open} open P1")
        if sla_percent is not None and sla_percent < 95:
            reasons.append("SLA below 95%")
        if any(0 <= (contract.end_date - today).days <= 60 for contract in client_contracts):
            reasons.append("contract expires within 60 days")
        if open_complaint_count:
            reasons.append(f"{open_complaint_count} open complaint(s)")
        if client_ratings and len(client_ratings) < 3:
            reasons.append("rating evidence below 3-response minimum")
        client_health.append({
            "key": str(linked_client.id), "label": linked_client.name, "value": health_score,
            "health_score": health_score, "health_status": health_status,
            "tickets": ticket_count, "open_tickets": ticket_metrics["open"], "critical_tickets": critical_open,
            "sla": sla_percent, "satisfaction": satisfaction, "resolution": resolution_percent,
            "complaints": complaint_count, "open_complaints": open_complaint_count, "risk_model_version": "CUSTOMER_SUCCESS_V1",
            "risk_reason": "No support activity in the selected period" if not has_health_evidence else ", ".join(reasons) if reasons else "No material risk identified",
            "route": f"/clients/{linked_client.id}/profile",
        })
    client_health.sort(key=lambda row: (row["health_score"] is None, float(str(row["health_score"] or 0)), str(row["label"])))
    scored_health = [float(str(row["health_score"])) for row in client_health if row["health_score"] is not None]
    average_health = round(sum(scored_health) / len(scored_health), 1) if scored_health else None
    health_distribution = _breakdown([str(row["health_status"]) for row in client_health])
    trend_evidence_tickets = list(
        db.scalars(
            ticket_scope.where(
                or_(
                    and_(Ticket.created_at >= start, Ticket.created_at < end),
                    and_(Ticket.resolved_at >= start, Ticket.resolved_at < end),
                )
            )
            .order_by(func.coalesce(Ticket.resolved_at, Ticket.created_at).desc(), Ticket.id.desc())
            .limit(EVIDENCE_LIMIT)
            .options(
                load_only(
                    Ticket.id,
                    Ticket.ticket_number,
                    Ticket.client_id,
                    Ticket.status_id,
                    Ticket.created_at,
                    Ticket.resolved_at,
                ),
                selectinload(Ticket.status),
            )
        )
    )
    trend_evidence: list[dict[str, object]] = [
        {
            "ticket": item.ticket_number,
            "client": clients[item.client_id].name,
            "created_at": item.created_at,
            "resolved_at": item.resolved_at,
            "status": item.status.name,
            "route": f"/tickets/{item.id}",
        }
        for item in trend_evidence_tickets
    ]
    executive = [
        widget("tickets","Tickets",current_count), widget("resolved","Resolved",resolved_count,params={"resolved_only":"true"}),
        widget("sla","SLA compliance",round(sum(x.met for x in sla.values())*100/len(sla),1) if sla else None,"/tickets",evidence=sla_evidence),
        widget("active_incidents","Active incidents",active_incident_count,params={"ticket_type_id":str(next(iter(incident_type_ids),"")),"open_only":"true"},evidence=active_incident_evidence),
        widget("response",f"Median response business hours (n={response_stats['sample_size']})",response_stats["median"],evidence=response_evidence),
        widget("resolution",f"Median accountable resolution hours (n={resolution_stats['sample_size']})",resolution_stats["median"],evidence=resolution_evidence),
        widget("clients","Active supported clients",len(profile_clients),"/clients"), widget("contracts","Active contracts",sum(x.status=="ACTIVE" and x.is_active for x in contracts),"/contracts",{"status":"ACTIVE"}),
        widget("expiring","Expiring in 60 days",sum(0 <= (x.end_date-today).days <= 60 for x in contracts),"/contracts",{"expiring_days":"60"}),
        widget("trend","Created vs resolved trend",trend,evidence=trend_evidence), widget("status_mix","Tickets by status",status_mix),
        widget("priority_mix","Tickets by priority",priority_mix),
        widget("products","Demand by product",product_mix),
        widget("breaches","SLA breaches",sum(not x.met for x in sla.values()),params={"breached_only":"true"}),
        widget("root_causes","Top root causes",root_cause_mix,"/tickets"),
        widget("workload","Engineer workload",workload),
        widget("support_consumption","Customers with the Highest Support Consumption",support_consumption,"/tickets"),
        widget("customer_workhours","Support work hours per customer",customer_workhours,"/tickets"),
        widget("client_hours","Client working and saved hours",[],"/clients"),
        widget("countries","Countries supported",country_rows,"/clients"),
    ]
    customer_success = [
        widget("customer_health","Average client health",average_health,"/clients"),
        widget("healthy_clients","Healthy clients",sum(row["health_status"] == "HEALTHY" for row in client_health),"/clients"),
        widget("at_risk_clients","At-risk clients",sum(row["health_status"] == "AT_RISK" for row in client_health),"/clients"),
        widget("customer_sla","Customer SLA compliance",round(sum(x.met for x in sla.values())*100/len(sla),1) if sla else None,"/tickets",evidence=sla_evidence),
        widget("customer_satisfaction","Customer satisfaction",average([float(rating) for rating, _ in survey_rows if rating is not None]),"/tickets",evidence=satisfaction_evidence),
        widget("active_incidents","Active incidents",active_incident_count,"/tickets",{"ticket_type_id":str(next(iter(incident_type_ids),"")),"open_only":"true"}),
        widget("health_distribution","Client health distribution",health_distribution,"/clients"),
        widget("client_health_portfolio","Client success portfolio",client_health,"/clients"),
    ]
    return {"period":{"start":filters["created_from"],"end":filters["created_to"],"comparison":comparison(current_count,previous_count)},"dashboards":{"EXECUTIVE_OVERVIEW":executive,"CUSTOMER_SERVICE_SUCCESS":customer_success}}


def _analysis_docx(payload: dict[str, Any], filters: Mapping[str, object], financial: dict[str, Any] | None = None, financial_tabs: dict[str, str] | None = None, hidden: dict[str, list[str]] | None = None) -> bytes:
    document = Document()
    section = document.sections[0]
    section.top_margin = section.bottom_margin = Inches(0.7)
    section.left_margin = section.right_margin = Inches(0.75)
    styles = document.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(9)
    styles["Title"].font.color.rgb = RGBColor(0, 0, 0)
    styles["Title"].font.size = Pt(20)
    for name in ("Heading 1", "Heading 2"):
        styles[name].font.color.rgb = RGBColor(15, 66, 112)
    document.add_paragraph("Top Management Analysis Report", "Title")
    period = payload["period"]
    document.add_paragraph(
        f"Selected period: {str(period['start'])[:10]} to {str(period['end'])[:10]}. "
        "This report contains the dashboard measures for the selected period and filters. "
        "Values can be edited in Word."
    )
    chosen = [f"{key.replace('_', ' ').title()}: {value}" for key, value in filters.items() if value is not None]
    if chosen:
        document.add_paragraph("Filters: " + "; ".join(chosen))
    comparison = period["comparison"]
    document.add_paragraph(
        f"Ticket volume: {comparison['current']} in this period; "
        f"{comparison['previous']} in the previous period; "
        f"change {comparison['change_percent']}%."
    )
    for dashboard, widgets in payload["dashboards"].items():
        document.add_heading(dashboard.replace("_", " ").title(), level=1)
        for item in widgets:
            document.add_heading(str(item["title"]), level=2)
            value = item["value"]
            if isinstance(value, list):
                if not value:
                    document.add_paragraph("No data in the selected period.")
                    continue
                # Preserve every displayed measure as editable table content.
                candidates = ("label", "health_status", "tickets", "open_tickets", "risk_reason") if item["code"] == "client_health_portfolio" else ("label", "value", "created", "resolved", "tickets")
                keys = [key for key in candidates if any(key in row for row in value)]
                table = document.add_table(rows=1, cols=len(keys))
                table.style = "Light Shading Accent 1"
                for cell, key in zip(table.rows[0].cells, keys, strict=True):
                    cell.text = key.replace("_", " ").title()
                for row in value:
                    for cell, key in zip(table.add_row().cells, keys, strict=True):
                        cell.text = "—" if row.get(key) is None else str(row[key])
            else:
                document.add_paragraph("—" if value is None else str(value), style="Normal")
        if financial is not None:
            for code, title, row_key, columns in (
                ("summary", "Financial summary", None, ("invoiced", "collected", "outstanding", "overdue", "collection_rate")),
                ("trend", "Financial trend", "trend", ("label", "invoiced", "collected")),
                ("clients", "Customer contributions", "clients", ("client_name", "invoiced", "collected", "outstanding")),
                ("aging", "Invoice aging", "aging", ("label", "amount", "count")),
                ("status", "Invoice status", "invoice_status", ("label", "amount", "count")),
            ):
                widget_code = f"finance_chart_{code}"
                target = (financial_tabs or {}).get(widget_code, "FINANCIAL_ANALYSIS")
                if target != dashboard or widget_code in (hidden or {}).get(target, []):
                    continue
                document.add_heading(title, level=2)
                for currency in financial.get("analytics", []):
                    document.add_paragraph(str(currency["currency"]))
                    rows = [currency] if row_key is None else currency.get(row_key, [])
                    if not rows:
                        document.add_paragraph("No data in the selected period.")
                        continue
                    table = document.add_table(rows=1, cols=len(columns))
                    table.style = "Light Shading Accent 1"
                    for cell, key in zip(table.rows[0].cells, columns, strict=True):
                        cell.text = key.replace("_", " ").title()
                    for row in rows:
                        for cell, key in zip(table.add_row().cells, columns, strict=True):
                            cell.text = str(row.get(key, "—"))
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


@router.get("/export.docx")
def export_analysis_docx(period: Literal["MONTH", "QUARTER", "YEAR"] = "MONTH", anchor: date = Query(default_factory=date.today), date_from: date | None = None, date_to: date | None = None, country_id: int | None = None, zone: str | None = None, client_id: int | None = None, location_id: int | None = None, product_id: int | None = None, team_id: int | None = None, engineer_id: int | None = None, department_id: int | None = None, timezone_offset_minutes: int = Query(default=180, ge=-840, le=840), widget_tabs: str = "{}", hidden_widgets: str = "{}", db: Session = Depends(get_db), user: User = Depends(current_user)) -> Response:
    if "report.export" not in effective_permissions(db, user).permissions:
        raise AuthorizationError()
    payload = cast(dict[str, Any], analytics(period, anchor, date_from, date_to, country_id, zone, client_id, location_id, product_id, team_id, engineer_id, department_id, timezone_offset_minutes, db, user))
    try:
        assignments = json.loads(widget_tabs)
        hidden = json.loads(hidden_widgets)
        if not isinstance(assignments, dict) or not isinstance(hidden, dict):
            raise ValueError()
    except (ValueError, TypeError):
        raise ConflictError("INVALID_REPORT_LAYOUT", "Report widget layout is invalid.") from None
    rearranged: dict[str, list[dict[str, Any]]] = {key: [] for key in payload["dashboards"]}
    rearranged["FINANCIAL_ANALYSIS"] = []
    for source, widgets in payload["dashboards"].items():
        for item in widgets:
            target = assignments.get(item["code"], source)
            if target not in rearranged:
                target = source
            if item["code"] not in hidden.get(target, []):
                rearranged[target].append(item)
    payload["dashboards"] = rearranged
    filters = {"country_id": country_id, "zone": zone, "client_id": client_id, "location_id": location_id, "product_id": product_id, "team_id": team_id, "engineer_id": engineer_id, "department_id": department_id}
    financial = None
    if "finance.dashboard.view" in effective_permissions(db, user).permissions:
        from app.modules.finance.routes import financial_dashboard

        financial = financial_dashboard(date_from, date_to, client_id, None, department_id, db, user).model_dump(mode="json")
    content = _analysis_docx(payload, filters, financial, assignments, hidden)
    filename = f"top-management-analysis-{str(payload['period']['start'])[:10]}-{str(payload['period']['end'])[:10]}.docx"
    return Response(content, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/export")
def export_analytics(period: Literal["MONTH", "QUARTER", "YEAR"] = "MONTH", anchor: date = Query(default_factory=date.today), date_from: date | None = None, date_to: date | None = None, country_id: int | None = None, zone: str | None = None, client_id: int | None = None, location_id: int | None = None, product_id: int | None = None, team_id: int | None = None, engineer_id: int | None = None, department_id: int | None = None, timezone_offset_minutes: int = Query(default=180, ge=-840, le=840), db: Session = Depends(get_db), user: User = Depends(current_user)) -> Response:
    if "report.export" not in effective_permissions(db, user).permissions:
        raise AuthorizationError()
    payload = cast(dict[str, Any], analytics(period, anchor, date_from, date_to, country_id, zone, client_id, location_id, product_id, team_id, engineer_id, department_id, timezone_offset_minutes, db, user))
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["Dashboard", "Metric", "Category", "Value", "Period start", "Period end"])
    for dashboard, widgets in payload["dashboards"].items():
        for item in widgets:
            values = item["value"] if isinstance(item["value"], list) else [{"label": "", "value": item["value"]}]
            for value in values:
                writer.writerow([dashboard, item["title"], value.get("label", ""), value.get("value", ""), payload["period"]["start"], payload["period"]["end"]])
    filename = f"top-management-{period.lower()}-{anchor.isoformat()}.csv"
    return Response(output.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
