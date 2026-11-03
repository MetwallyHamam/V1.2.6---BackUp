import csv
import io
from datetime import date, datetime, time
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_clock_settings, server_now, server_timezone
from app.core.exceptions import AuthorizationError, ConflictError
from app.db.session import get_db
from app.modules.clients.models import Client
from app.modules.iam.models import Department, DepartmentMembership, User
from app.modules.iam.service import effective_permissions
from app.modules.shifts.models import Shift
from app.modules.tickets.models import (
    Ticket,
    TicketAssignmentHistory,
    TicketComment,
    TicketStatusHistory,
    TicketWorklog,
)
from app.modules.tickets.service import visible_ticket_query
from app.modules.visits.models import (
    ClientVisitAssignment,
    ClientVisitEntitlement,
    ClientVisitOccurrence,
    VisitEntitlementLedgerEntry,
    VisitGenerationException,
)

router = APIRouter(prefix="/reports/operations", tags=["operational reports"])
FORMULA_VERSION = "WAVE7-1.0"
ACHIEVEMENT_VERSION = "TICKETS-WORKED-1.0"
MINIMUM_ACHIEVEMENT_SAMPLE = 5
DASHBOARD_INVENTORY = [
    {
        "code": "ticket_volume",
        "canonical_route": "/operational-reports",
        "owner": "Support Operations",
        "audience": "Managers",
        "decision": "KEEP",
        "evidence_contract": "tickets?created_from&created_to&client_id",
        "freshness": "LIVE",
    },
    {
        "code": "visit_balance",
        "canonical_route": "/operational-reports",
        "owner": "Contract Operations",
        "audience": "Managers",
        "decision": "KEEP",
        "evidence_contract": "operational-reports?date_from&date_to&client_id",
        "freshness": "LIVE",
    },
    {
        "code": "shift_capacity",
        "canonical_route": "/operational-reports",
        "owner": "Workforce Operations",
        "audience": "Managers",
        "decision": "KEEP",
        "evidence_contract": "shifts?date_from&date_to&department_id",
        "freshness": "LIVE",
    },
    {
        "code": "department_achievements",
        "canonical_route": "/operational-reports",
        "owner": "Support Governance",
        "audience": "Managers and teams",
        "decision": "KEEP",
        "evidence_contract": "reports/operations/achievements/evidence",
        "freshness": "LIVE",
    },
]


def bounds(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    if date_to < date_from:
        raise ConflictError(
            "INVALID_REPORT_PERIOD", "The report end date must not precede its start date."
        )
    return datetime.combine(date_from, time.min, tzinfo=server_timezone()), datetime.combine(
        date_to, time.max, tzinfo=server_timezone()
    )


def operational_payload(
    db: Session,
    user: User,
    date_from: date,
    date_to: date,
    client_id: int | None,
    department_id: int | None,
) -> dict[str, object]:
    start, end = bounds(date_from, date_to)
    permissions = set(effective_permissions(db, user).permissions)
    clients_query = select(Client).order_by(Client.name)
    if "ticket.view.all" not in permissions:
        visible_client_ids = (
            visible_ticket_query(db, user).with_only_columns(Ticket.client_id).distinct()
        )
        clients_query = clients_query.where(Client.id.in_(visible_client_ids))
    if client_id is not None:
        clients_query = clients_query.where(Client.id == client_id)
    clients = list(db.scalars(clients_query))
    client_rows: list[dict[str, object]] = []
    for client in clients:
        tickets = (
            db.scalar(
                select(func.count(Ticket.id)).where(
                    Ticket.client_id == client.id,
                    Ticket.created_at >= start,
                    Ticket.created_at <= end,
                )
            )
            or 0
        )
        entitlements = list(
            db.scalars(
                select(ClientVisitEntitlement).where(
                    ClientVisitEntitlement.client_id == client.id,
                    ClientVisitEntitlement.service_period_end >= date_from,
                    ClientVisitEntitlement.service_period_start <= date_to,
                )
            )
        )
        entitlement_ids = [item.id for item in entitlements]
        completed = (
            db.scalar(
                select(func.count(ClientVisitOccurrence.id)).where(
                    ClientVisitOccurrence.client_id == client.id,
                    ClientVisitOccurrence.status == "COMPLETED",
                    ClientVisitOccurrence.actual_ended_at >= start,
                    ClientVisitOccurrence.actual_ended_at <= end,
                )
            )
            or 0
        )
        consumed = 0
        if entitlement_ids:
            consumed = (
                db.scalar(
                    select(func.coalesce(func.sum(VisitEntitlementLedgerEntry.quantity), 0)).where(
                        VisitEntitlementLedgerEntry.entitlement_id.in_(entitlement_ids),
                        VisitEntitlementLedgerEntry.entry_type.in_(["CONSUMPTION", "REVERSAL"]),
                    )
                )
                or 0
            )
        entitled = sum(item.allowed_visits for item in entitlements)
        client_rows.append(
            {
                "client_id": client.id,
                "client": client.name,
                "tickets_created": tickets,
                "entitled_visits": entitled,
                "completed_visits": completed,
                "consumed_visits": -int(consumed),
                "remaining_visits": entitled + int(consumed),
                "evidence_url": f"/tickets?client_id={client.id}&created_from={date_from}&created_to={date_to}",
            }
        )

    departments_query = select(Department).order_by(Department.name)
    if "dashboard.executive" not in permissions:
        departments_query = departments_query.where(Department.id == user.department_id)
    if department_id is not None:
        departments_query = departments_query.where(Department.id == department_id)
    departments = list(db.scalars(departments_query))
    department_rows: list[dict[str, object]] = []
    for department in departments:
        user_ids = list(
            db.scalars(
                select(User.id).where(
                    User.department_id == department.id, User.is_active.in_([True])
                )
            )
        )
        shift_minutes = 0
        scheduled_visits = completed_visits = exceptions = 0
        if user_ids:
            shifts = list(
                db.scalars(
                    select(Shift).where(
                        Shift.user_id.in_(user_ids),
                        Shift.starts_at <= end,
                        Shift.ends_at >= start,
                        Shift.status.in_(["PUBLISHED", "APPROVED"]),
                    )
                )
            )
            shift_minutes = sum(
                max(
                    0,
                    int(
                        (
                            min(item.ends_at.replace(tzinfo=server_timezone()), end)
                            - max(item.starts_at.replace(tzinfo=server_timezone()), start)
                        ).total_seconds()
                        // 60
                    ),
                )
                for item in shifts
            )
            occurrence_ids = list(
                db.scalars(
                    select(ClientVisitAssignment.occurrence_id)
                    .where(
                        ClientVisitAssignment.user_id.in_(user_ids),
                        ClientVisitAssignment.starts_at <= end,
                        ClientVisitAssignment.ends_at >= start,
                    )
                    .distinct()
                )
            )
            scheduled_visits = len(occurrence_ids)
            if occurrence_ids:
                completed_visits = (
                    db.scalar(
                        select(func.count(ClientVisitOccurrence.id)).where(
                            ClientVisitOccurrence.id.in_(occurrence_ids),
                            ClientVisitOccurrence.status == "COMPLETED",
                        )
                    )
                    or 0
                )
            entitlement_ids = list(
                db.scalars(
                    select(ClientVisitEntitlement.id).where(
                        ClientVisitEntitlement.department_id == department.id
                    )
                )
            )
            if entitlement_ids:
                exceptions = (
                    db.scalar(
                        select(func.count(VisitGenerationException.id)).where(
                            VisitGenerationException.entitlement_id.in_(entitlement_ids),
                            VisitGenerationException.status == "OPEN",
                        )
                    )
                    or 0
                )
        department_rows.append(
            {
                "department_id": department.id,
                "department": department.name,
                "active_headcount": len(user_ids),
                "published_shift_minutes": shift_minutes,
                "scheduled_visits": scheduled_visits,
                "completed_visits": completed_visits,
                "open_visit_exceptions": exceptions,
                "evidence_url": f"/shifts?department_id={department.id}&date_from={date_from}&date_to={date_to}",
            }
        )

    definitions = [
        {
            "code": "tickets_created",
            "owner": "Support Operations",
            "formula": "Distinct tickets created inside the selected server-date boundaries.",
            "freshness": "Live at request time",
            "version": FORMULA_VERSION,
        },
        {
            "code": "visit_balance",
            "owner": "Contract Operations",
            "formula": "Allowed visits plus append-only consumption and reversal ledger quantities.",
            "freshness": "Live at request time",
            "version": FORMULA_VERSION,
        },
        {
            "code": "shift_capacity",
            "owner": "Workforce Operations",
            "formula": "Minutes intersecting published or approved shifts in the selected server-time period.",
            "freshness": "Live at request time",
            "version": FORMULA_VERSION,
        },
        {
            "code": "visit_execution",
            "owner": "Service Operations",
            "formula": "Distinct assigned occurrences in-period and their current completion state.",
            "freshness": "Live at request time",
            "version": FORMULA_VERSION,
        },
    ]
    return {
        "formula_version": FORMULA_VERSION,
        "generated_at": server_now(),
        "timezone": server_clock_settings()[0],
        "date_from": date_from,
        "date_to": date_to,
        "warnings": [],
        "definitions": definitions,
        "clients": client_rows,
        "departments": department_rows,
    }


def qualifying_ticket_evidence(db: Session, start: datetime, end: datetime) -> dict[int, set[int]]:
    """Return distinct ticket evidence by historical primary department."""
    events: set[tuple[int, int, date]] = set()
    assignments = select(
        TicketAssignmentHistory.ticket_id,
        TicketAssignmentHistory.assigned_user_id,
        TicketAssignmentHistory.created_at,
    ).where(
        TicketAssignmentHistory.assigned_user_id.is_not(None),
        TicketAssignmentHistory.created_at >= start,
        TicketAssignmentHistory.created_at <= end,
    )
    for ticket_id, user_id, occurred_at in db.execute(assignments):
        if user_id is not None:
            events.add((ticket_id, user_id, occurred_at.date()))
    event_queries = [
        select(
            TicketComment.ticket_id, TicketComment.author_user_id, TicketComment.created_at
        ).where(TicketComment.created_at >= start, TicketComment.created_at <= end),
        select(
            TicketStatusHistory.ticket_id,
            TicketStatusHistory.changed_by_user_id,
            TicketStatusHistory.created_at,
        ).where(
            TicketStatusHistory.source != "AUTOMATION",
            TicketStatusHistory.created_at >= start,
            TicketStatusHistory.created_at <= end,
        ),
        select(TicketWorklog.ticket_id, TicketWorklog.user_id, TicketWorklog.ended_at).where(
            TicketWorklog.status == "APPROVED",
            TicketWorklog.ended_at >= start,
            TicketWorklog.ended_at <= end,
        ),
    ]
    for query in event_queries:
        for ticket_id, user_id, occurred_at in db.execute(query):
            events.add((ticket_id, user_id, occurred_at.date()))
    result: dict[int, set[int]] = {}
    for ticket_id, user_id, occurred_on in events:
        membership = db.scalar(
            select(DepartmentMembership)
            .where(
                DepartmentMembership.user_id == user_id,
                DepartmentMembership.is_primary.in_([True]),
                DepartmentMembership.effective_from <= occurred_on,
                (
                    DepartmentMembership.effective_until.is_(None)
                    | (DepartmentMembership.effective_until >= occurred_on)
                ),
            )
            .order_by(DepartmentMembership.effective_from.desc())
            .limit(1)
        )
        user = db.get(User, user_id)
        department_id = (
            membership.department_id if membership else (user.department_id if user else None)
        )
        if department_id is not None:
            result.setdefault(department_id, set()).add(ticket_id)
    return result


@router.get("")
def operational_report(
    date_from: date,
    date_to: date,
    client_id: int | None = None,
    department_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("dashboard.manager")),
) -> dict[str, object]:
    return operational_payload(db, user, date_from, date_to, client_id, department_id)


@router.get("/dashboard-inventory")
def dashboard_inventory(
    _: User = Depends(require_permission("dashboard.manager")),
) -> dict[str, object]:
    return {
        "inventory_version": "WAVE7A-1.0",
        "items": DASHBOARD_INVENTORY,
        "duplicate_metric_codes": [],
        "compatibility_route": "/",
        "canonical_route": "/operational-reports",
    }


@router.get("/department-structure")
def department_structure(
    as_of: date,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("dashboard.manager")),
) -> dict[str, object]:
    rows = []
    statement = select(Department).where(Department.is_active.in_([True])).order_by(Department.name)
    if "dashboard.executive" not in effective_permissions(db, user).permissions:
        statement = statement.where(Department.id == user.department_id)
    for department in db.scalars(statement):
        memberships = list(
            db.scalars(
                select(DepartmentMembership).where(
                    DepartmentMembership.department_id == department.id,
                    DepartmentMembership.effective_from <= as_of,
                    (
                        DepartmentMembership.effective_until.is_(None)
                        | (DepartmentMembership.effective_until >= as_of)
                    ),
                    DepartmentMembership.is_primary.in_([True]),
                )
            )
        )
        rows.append(
            {
                "id": department.id,
                "name": department.name,
                "parent_department_id": department.parent_department_id,
                "head_user_id": department.head_user_id,
                "headcount": len({item.user_id for item in memberships}),
                "vacant_head": department.head_user_id is None,
                "effective_as_of": as_of,
            }
        )
    return {
        "as_of": as_of,
        "departments": rows,
        "warnings": ["A department with no assigned head is shown as vacant."],
    }


@router.get("/achievements")
def department_achievements(
    date_from: date,
    date_to: date,
    department_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("dashboard.manager")),
) -> dict[str, object]:
    start, end = bounds(date_from, date_to)
    evidence = qualifying_ticket_evidence(db, start, end)
    statement = select(Department).order_by(Department.name)
    if "dashboard.executive" not in effective_permissions(db, user).permissions:
        statement = statement.where(Department.id == user.department_id)
    if department_id is not None:
        statement = statement.where(Department.id == department_id)
    rows = []
    for department in db.scalars(statement):
        ticket_ids = sorted(evidence.get(department.id, set()))
        rows.append(
            {
                "department_id": department.id,
                "department": department.name,
                "tickets_worked_on": len(ticket_ids),
                "sample_size": len(ticket_ids),
                "eligible": len(ticket_ids) >= MINIMUM_ACHIEVEMENT_SAMPLE,
                "minimum_sample": MINIMUM_ACHIEVEMENT_SAMPLE,
                "formula_version": ACHIEVEMENT_VERSION,
                "data_quality_warning": None
                if ticket_ids
                else "No qualifying human activity in the selected period.",
                "evidence_url": f"/api/v1/reports/operations/achievements/evidence?date_from={date_from}&date_to={date_to}&department_id={department.id}",
            }
        )
    return {
        "definition": "Distinct tickets with a human assignment, comment, status change, or approved worklog, attributed using effective primary department membership on the event date.",
        "formula_version": ACHIEVEMENT_VERSION,
        "individual_ranking": False,
        "rows": rows,
    }


@router.get("/achievements/evidence")
def department_achievement_evidence(
    date_from: date,
    date_to: date,
    department_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("dashboard.manager")),
) -> dict[str, object]:
    if (
        "dashboard.executive" not in effective_permissions(db, user).permissions
        and department_id != user.department_id
    ):
        raise AuthorizationError("Department evidence is outside your reporting scope.")
    start, end = bounds(date_from, date_to)
    ids = sorted(qualifying_ticket_evidence(db, start, end).get(department_id, set()))
    tickets = (
        list(db.scalars(select(Ticket).where(Ticket.id.in_(ids)).order_by(Ticket.ticket_number)))
        if ids
        else []
    )
    return {
        "formula_version": ACHIEVEMENT_VERSION,
        "department_id": department_id,
        "date_from": date_from,
        "date_to": date_to,
        "count": len(tickets),
        "tickets": [
            {
                "id": item.id,
                "ticket_number": item.ticket_number,
                "subject": item.subject,
                "url": f"/tickets/{item.id}",
            }
            for item in tickets
        ],
    }


@router.get("/export.csv")
def operational_export(
    date_from: date,
    date_to: date,
    report: Literal["clients", "departments"] = Query(),
    client_id: int | None = None,
    department_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("report.export")),
) -> StreamingResponse:
    payload = operational_payload(db, user, date_from, date_to, client_id, department_id)
    rows = payload[report]
    assert isinstance(rows, list)
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="operational-{report}-{date_from}-{date_to}.csv"'
        },
    )
