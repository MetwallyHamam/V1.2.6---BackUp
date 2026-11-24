from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from threading import Lock
from time import monotonic
from typing import Literal, TypedDict

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import current_user
from app.core.clock import server_now, server_timezone, server_today
from app.core.exceptions import ConflictError
from app.db.session import get_db
from app.modules.clients.models import Client
from app.modules.contracts.models import TicketSlaClock
from app.modules.entitlements.models import EntitlementApproval
from app.modules.iam.models import User
from app.modules.iam.service import effective_permissions
from app.modules.internal_operations.models import InternalOperation, InternalOperationAssignee
from app.modules.notifications.models import Notification
from app.modules.service_checklists.models import (
    ServiceChecklistOccurrence,
    ServiceChecklistOccurrenceItem,
)
from app.modules.shifts.models import Shift
from app.modules.sla.service import resolution_sla_results
from app.modules.tickets.models import SupportAssistantPreference, Ticket, TicketStatus
from app.modules.tickets.service import visible_ticket_query
from app.modules.visits.models import ClientVisitAssignment, ClientVisitOccurrence

router = APIRouter(prefix="/home", tags=["operational home"])

_CACHE_SECONDS = 30.0
_cache: dict[int, tuple[float, dict[str, object]]] = {}
_cache_lock = Lock()
_terminal_statuses = {"RESOLVED", "CLOSED", "CANCELLED"}
AttentionCategory = Literal["CRITICAL", "ACTION_REQUIRED", "DUE_SOON", "WAITING", "INFORMATION"]
_attention_categories: set[AttentionCategory] = {
    "CRITICAL",
    "ACTION_REQUIRED",
    "DUE_SOON",
    "WAITING",
    "INFORMATION",
}


class AttentionPreferencePayload(TypedDict):
    enabled_categories: list[AttentionCategory]
    snoozed_until: dict[str, str]


class AttentionPreferenceUpdate(BaseModel):
    enabled_categories: list[AttentionCategory] = Field(
        default_factory=lambda: sorted(_attention_categories), min_length=1
    )


class AttentionSnoozeCreate(BaseModel):
    item_id: str = Field(min_length=3, max_length=120, pattern=r"^[a-zA-Z0-9:_-]+$")
    minutes: Literal[60, 240, 1440] = 60


def _attention_settings(
    db: Session, user_id: int
) -> tuple[SupportAssistantPreference | None, dict[str, object]]:
    preference = db.scalar(
        select(SupportAssistantPreference).where(SupportAssistantPreference.user_id == user_id)
    )
    if not preference:
        return None, {}
    try:
        settings = json.loads(preference.workspace_settings_json or "{}")
        return preference, settings if isinstance(settings, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return preference, {}


def _attention_preference_payload(settings: dict[str, object]) -> AttentionPreferencePayload:
    enabled = settings.get("attention_categories", sorted(_attention_categories))
    categories: list[AttentionCategory] = []
    if isinstance(enabled, list):
        categories = [
            value for value in enabled if isinstance(value, str) and value in _attention_categories
        ]
    raw_snoozed = settings.get("attention_snoozed_until", {})
    return {
        "enabled_categories": categories or sorted(_attention_categories),
        "snoozed_until": (
            {str(key): str(value) for key, value in raw_snoozed.items()}
            if isinstance(raw_snoozed, dict)
            else {}
        ),
    }


@router.get("/attention/preferences")
def get_attention_preferences(
    db: Session = Depends(get_db), user: User = Depends(current_user)
) -> AttentionPreferencePayload:
    _, settings = _attention_settings(db, user.id)
    return _attention_preference_payload(settings)


@router.put("/attention/preferences")
def update_attention_preferences(
    data: AttentionPreferenceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> AttentionPreferencePayload:
    preference, settings = _attention_settings(db, user.id)
    if not preference:
        preference = SupportAssistantPreference(user_id=user.id)
        db.add(preference)
    settings["attention_categories"] = list(dict.fromkeys(data.enabled_categories))
    preference.workspace_settings_json = json.dumps(settings)
    db.commit()
    return _attention_preference_payload(settings)


@router.post("/attention/snooze")
def snooze_attention_item(
    data: AttentionSnoozeCreate, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> AttentionPreferencePayload:
    preference, settings = _attention_settings(db, user.id)
    if not preference:
        preference = SupportAssistantPreference(user_id=user.id)
        db.add(preference)
    payload = _attention_preference_payload(settings)
    snoozed = dict(payload["snoozed_until"])
    snoozed[data.item_id] = (server_now() + timedelta(minutes=data.minutes)).isoformat()
    settings["attention_snoozed_until"] = snoozed
    preference.workspace_settings_json = json.dumps(settings)
    db.commit()
    return _attention_preference_payload(settings)


@router.delete("/attention/snoozed", status_code=204)
def clear_attention_snoozes(
    db: Session = Depends(get_db), user: User = Depends(current_user)
) -> Response:
    preference, settings = _attention_settings(db, user.id)
    if preference:
        settings["attention_snoozed_until"] = {}
        preference.workspace_settings_json = json.dumps(settings)
        db.commit()
    return Response(status_code=204)


@router.get("/attention")
def unified_attention(
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    """Return unresolved, permission-scoped work that currently needs this user's attention."""
    now = server_now()
    soon = now + timedelta(hours=24)
    permissions = set(effective_permissions(db, user).permissions)
    _, attention_settings = _attention_settings(db, user.id)
    attention_preferences = _attention_preference_payload(attention_settings)
    enabled_categories = set(attention_preferences["enabled_categories"])
    snoozed_until = attention_preferences["snoozed_until"]
    items: list[dict[str, object]] = []

    scoped = visible_ticket_query(db, user).subquery("attention_visible_tickets")
    ticket_rows = db.execute(
        select(
            scoped.c.id,
            scoped.c.ticket_number,
            scoped.c.subject,
            scoped.c.priority,
            scoped.c.due_at,
            scoped.c.assigned_user_id,
            TicketStatus.code,
        )
        .select_from(scoped)
        .join(TicketStatus, TicketStatus.id == scoped.c.status_id)
        .where(
            TicketStatus.code.not_in(_terminal_statuses),
            or_(
                scoped.c.assigned_user_id == user.id,
                and_(scoped.c.assigned_user_id.is_(None), scoped.c.priority.in_(["P1", "P2"])),
            ),
            or_(scoped.c.priority == "P1", scoped.c.due_at <= soon),
        )
        .order_by(
            case((scoped.c.priority == "P1", 0), (scoped.c.due_at < now, 1), else_=2),
            scoped.c.due_at.asc(),
        )
        .limit(limit)
    )
    for row in ticket_rows:
        overdue = row.due_at is not None and row.due_at < now
        items.append(
            {
                "id": f"ticket:{row.id}",
                "source": "TICKET",
                "category": "CRITICAL" if row.priority == "P1" or overdue else "DUE_SOON",
                "title": f"{row.ticket_number} · {row.subject}",
                "reason": "SLA target is overdue"
                if overdue
                else (
                    "Critical priority"
                    if row.priority == "P1"
                    else "SLA target is due within 24 hours"
                ),
                "due_at": row.due_at,
                "deep_link": f"/tickets/{row.id}",
                "primary_action": "Open ticket",
            }
        )

    if "shift.view" in permissions:
        for shift in db.scalars(
            select(Shift)
            .where(
                Shift.user_id == user.id,
                Shift.status.not_in(["CANCELLED", "COMPLETED"]),
                Shift.starts_at >= now,
                Shift.starts_at <= soon,
            )
            .order_by(Shift.starts_at)
            .limit(5)
        ):
            items.append(
                {
                    "id": f"shift:{shift.id}",
                    "source": "SHIFT",
                    "category": "DUE_SOON",
                    "title": "Upcoming shift",
                    "reason": "Your shift starts within 24 hours",
                    "due_at": shift.starts_at,
                    "deep_link": "/internal-operations?tab=shifts",
                    "primary_action": "View schedule",
                }
            )

    visit_rows = db.execute(
        select(ClientVisitAssignment, ClientVisitOccurrence)
        .join(
            ClientVisitOccurrence, ClientVisitOccurrence.id == ClientVisitAssignment.occurrence_id
        )
        .where(
            ClientVisitAssignment.user_id == user.id,
            ClientVisitAssignment.status.not_in(["CANCELLED", "COMPLETED"]),
            ClientVisitAssignment.starts_at >= now,
            ClientVisitAssignment.starts_at <= soon,
        )
        .order_by(ClientVisitAssignment.starts_at)
        .limit(5)
    )
    for assignment, occurrence in visit_rows:
        items.append(
            {
                "id": f"visit:{occurrence.id}",
                "source": "VISIT",
                "category": "DUE_SOON",
                "title": f"Visit #{occurrence.id}",
                "reason": "Assigned visit starts within 24 hours",
                "due_at": assignment.starts_at,
                "deep_link": "/field-visits",
                "primary_action": "View visit",
            }
        )

    if "internal_operation.view" in permissions:
        operation_rows = db.scalars(
            select(InternalOperation)
            .where(
                InternalOperation.id.in_(
                    select(InternalOperationAssignee.operation_id).where(
                        InternalOperationAssignee.user_id == user.id
                    )
                ),
                InternalOperation.status.not_in(["COMPLETED", "CANCELLED"]),
                InternalOperation.starts_at <= soon,
            )
            .order_by(InternalOperation.starts_at)
            .limit(5)
        )
        for operation in operation_rows:
            overdue = operation.ends_at < now
            items.append(
                {
                    "id": f"operation:{operation.id}",
                    "source": "OPERATION",
                    "category": "ACTION_REQUIRED" if overdue else "DUE_SOON",
                    "title": operation.title,
                    "reason": "Assigned operation is overdue"
                    if overdue
                    else "Assigned operation starts within 24 hours",
                    "due_at": operation.starts_at,
                    "deep_link": "/internal-operations",
                    "primary_action": "View operation",
                }
            )

    if "entitlement_approval.decide" in permissions:
        for approval in db.scalars(
            select(EntitlementApproval)
            .where(EntitlementApproval.status == "PENDING")
            .order_by(EntitlementApproval.approval_deadline, EntitlementApproval.created_at)
            .limit(10)
        ):
            items.append(
                {
                    "id": f"approval:{approval.id}",
                    "source": "APPROVAL",
                    "category": "ACTION_REQUIRED",
                    "title": f"Approval request #{approval.id}",
                    "reason": approval.requested_action.replace("_", " ").title(),
                    "due_at": approval.approval_deadline,
                    "deep_link": "/tickets?tab=approvals",
                    "primary_action": "Review approval",
                }
            )

    for notification in db.scalars(
        select(Notification)
        .where(
            Notification.recipient_user_id == user.id,
            Notification.is_read.in_([False]),
            Notification.dismissed_at.is_(None),
            Notification.severity.in_(["CRITICAL", "ERROR", "WARNING"]),
        )
        .order_by(Notification.created_at.desc())
        .limit(10)
    ):
        items.append(
            {
                "id": f"notification:{notification.id}",
                "source": "NOTIFICATION",
                "category": "CRITICAL"
                if notification.severity in {"CRITICAL", "ERROR"}
                else "ACTION_REQUIRED",
                "title": notification.title,
                "reason": notification.message,
                "due_at": None,
                "deep_link": notification.deep_link or "/notifications",
                "primary_action": "Open notification",
            }
        )

    active_snoozes: set[str] = set()
    for item_id, raw_until in snoozed_until.items():
        try:
            until = datetime.fromisoformat(str(raw_until))
            if until.tzinfo is None:
                until = until.replace(tzinfo=server_timezone())
            if until > now:
                active_snoozes.add(str(item_id))
        except (TypeError, ValueError):
            continue
    items = [
        item
        for item in items
        if item["category"] in enabled_categories and item["id"] not in active_snoozes
    ]
    rank = {"CRITICAL": 0, "ACTION_REQUIRED": 1, "DUE_SOON": 2, "WAITING": 3, "INFORMATION": 4}
    items.sort(key=lambda item: (rank.get(str(item["category"]), 9), item["due_at"] or soon))
    selected = items[:limit]
    counts = {category: sum(item["category"] == category for item in items) for category in rank}
    return {"generated_at": now, "total": len(items), "counts": counts, "items": selected}


@router.get("/client-hours")
def client_hours(
    date_from: date = Query(default_factory=lambda: server_today().replace(day=1)),
    date_to: date = Query(default_factory=server_today),
    client_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    if date_to < date_from:
        raise ConflictError(
            "INVALID_REPORT_PERIOD", "The end date must be on or after the start date."
        )
    start = datetime.combine(date_from, time.min, server_timezone())
    end = datetime.combine(date_to + timedelta(days=1), time.min, server_timezone())
    access = effective_permissions(db, user)
    global_hours = (
        "dashboard.executive" in access.permissions or "dashboard.manager" in access.permissions
    )
    ticket_query = (
        select(Ticket).where(Ticket.archived_at.is_(None))
        if global_hours
        else visible_ticket_query(db, user)
    ).where(
        Ticket.created_at >= start,
        Ticket.created_at < end,
        (Ticket.resolved_at.is_not(None) | Ticket.closed_at.is_not(None)),
        Ticket.status_id.in_(
            select(TicketStatus.id).where(TicketStatus.code.in_(["RESOLVED", "CLOSED"]))
        ),
        Ticket.id.in_(
            select(TicketSlaClock.ticket_id).where(
                TicketSlaClock.clock_type == "RESOLUTION",
                TicketSlaClock.completed_at.is_not(None),
            )
        ),
    )
    if client_id is not None:
        ticket_query = ticket_query.where(Ticket.client_id == client_id)
    tickets = list(db.scalars(ticket_query))
    if global_hours or "ticket.view.all" in access.permissions:
        client_ids = {ticket.client_id for ticket in tickets}
    elif user.user_type == "CLIENT_PORTAL":
        client_ids = set(access.client_scope_ids)
    else:
        client_ids = set(
            db.scalars(
                visible_ticket_query(db, user).with_only_columns(Ticket.client_id).distinct()
            )
        )
    client_ids.update(ticket.client_id for ticket in tickets)
    if client_id is not None:
        client_ids.intersection_update({client_id})
    results = resolution_sla_results(db, tickets)
    values: dict[int, dict[str, int]] = {
        key: {"target": 0, "spent": 0, "saved": 0, "operation": 0} for key in client_ids
    }
    for ticket in tickets:
        result = results.get(ticket.id)
        if result is None:
            continue
        # Historical tickets can belong to clients that are now inactive.
        # Keep the aggregation keyed to the tickets actually selected above.
        client_ids.add(ticket.client_id)
        row = values.setdefault(
            ticket.client_id, {"target": 0, "spent": 0, "saved": 0, "operation": 0}
        )
        row["target"] += result.target_minutes
        row["spent"] += result.accountable_minutes
        row["saved"] += result.saved_minutes
    if client_ids or global_hours or "ticket.view.all" in access.permissions:
        operation_query = select(InternalOperation).where(
            InternalOperation.status == "COMPLETED",
            InternalOperation.starts_at >= start,
            InternalOperation.starts_at < end,
            InternalOperation.client_id.is_not(None),
        )
        if client_id is not None:
            operation_query = operation_query.where(InternalOperation.client_id == client_id)
        if not (global_hours or "ticket.view.all" in access.permissions):
            operation_query = operation_query.where(InternalOperation.client_id.in_(client_ids))
        operations = list(db.scalars(operation_query))
        client_ids.update(
            operation.client_id for operation in operations if operation.client_id is not None
        )
        for key in client_ids:
            values.setdefault(key, {"target": 0, "spent": 0, "saved": 0, "operation": 0})
        assignee_counts: dict[int, int] = {}
        operation_ids = [operation.id for operation in operations]
        for offset in range(0, len(operation_ids), 1000):
            assignee_counts.update(
                {
                    operation_id: count
                    for operation_id, count in db.execute(
                        select(InternalOperationAssignee.operation_id, func.count())
                        .where(
                            InternalOperationAssignee.operation_id.in_(
                                operation_ids[offset : offset + 1000]
                            )
                        )
                        .group_by(InternalOperationAssignee.operation_id)
                    )
                }
            )
        for operation in operations:
            if operation.client_id is not None:
                values[operation.client_id]["operation"] += round(
                    max(0, (operation.ends_at - operation.starts_at).total_seconds() / 60)
                    * max(1, assignee_counts.get(operation.id, 0))
                )
    names = {
        key: name for key, name in db.execute(select(Client.id, Client.name)) if key in client_ids
    }
    rows = [
        {
            "client_id": key,
            "client_name": names.get(key, str(key)),
            "working_hours": round((value["spent"] + value["operation"]) / 60, 1),
            "target_hours": round(value["target"] / 60, 1),
            "saved_hours": round(value["saved"] / 60, 1),
        }
        for key, value in values.items()
        if key in names and any(value.values())
    ]
    rows.sort(key=lambda row: (-float(row["working_hours"]), str(row["client_name"])))
    return {"date_from": date_from.isoformat(), "date_to": date_to.isoformat(), "clients": rows}


def _cached(user_id: int) -> dict[str, object] | None:
    with _cache_lock:
        entry = _cache.get(user_id)
        if entry and monotonic() - entry[0] < _CACHE_SECONDS:
            return entry[1]
    return None


def _store(user_id: int, payload: dict[str, object]) -> dict[str, object]:
    with _cache_lock:
        _cache[user_id] = (monotonic(), payload)
    return payload


@router.get("/snapshot")
def operational_snapshot(
    db: Session = Depends(get_db), user: User = Depends(current_user)
) -> dict[str, object]:
    """Return a small current-state snapshot; never run historical analytics."""
    if cached := _cached(user.id):
        return cached

    now = server_now()
    today_start = datetime.combine(server_today(), time.min, tzinfo=now.tzinfo)
    tomorrow_start = today_start + timedelta(days=1)
    scoped = visible_ticket_query(db, user).subquery("home_visible_tickets")
    open_condition = TicketStatus.code.not_in(_terminal_statuses)
    pending_ticket_condition = TicketStatus.code.in_(
        ["PENDING_CLIENT", "PENDING_INTERNAL", "PENDING_VENDOR"]
    )
    pending_approval_condition = (
        func.coalesce(scoped.c.entitlement_status, "") == "PENDING_APPROVAL"
    )
    actionable_open_condition = (
        open_condition & ~pending_ticket_condition & ~pending_approval_condition
    )
    attention_condition = and_(
        actionable_open_condition,
        scoped.c.due_at.is_not(None),
        scoped.c.due_at > now,
        scoped.c.due_at < tomorrow_start,
    )
    totals = db.execute(
        select(
            func.count(scoped.c.id),
            func.sum(case((actionable_open_condition, 1), else_=0)),
            func.sum(case((TicketStatus.code == "IN_PROGRESS", 1), else_=0)),
            func.sum(
                case(
                    (actionable_open_condition & scoped.c.assigned_user_id.is_(None), 1),
                    else_=0,
                )
            ),
            func.sum(case((attention_condition, 1), else_=0)),
            func.sum(
                case(
                    (scoped.c.created_at >= today_start, 1),
                    else_=0,
                )
            ),
            func.sum(case((pending_approval_condition, 1), else_=0)),
            func.sum(case((pending_ticket_condition, 1), else_=0)),
        )
        .select_from(scoped)
        .join(TicketStatus, TicketStatus.id == scoped.c.status_id)
    ).one()

    attention_rows = db.execute(
        select(
            scoped.c.id,
            scoped.c.ticket_number,
            scoped.c.subject,
            scoped.c.priority,
            TicketStatus.code,
            Client.name,
            scoped.c.assigned_user_id,
            scoped.c.due_at,
            scoped.c.last_activity_at,
        )
        .select_from(scoped)
        .join(TicketStatus, TicketStatus.id == scoped.c.status_id)
        .join(Client, Client.id == scoped.c.client_id)
        .where(attention_condition)
        .order_by(
            case((scoped.c.priority == "P1", 0), (scoped.c.priority == "P2", 1), else_=2),
            scoped.c.due_at.asc(),
            scoped.c.last_activity_at.asc(),
        )
        .limit(10)
    ).all()

    status_mix = [
        {"label": code, "value": int(count)}
        for code, count in db.execute(
            select(TicketStatus.code, func.count(scoped.c.id))
            .select_from(scoped)
            .join(TicketStatus, TicketStatus.id == scoped.c.status_id)
            .group_by(TicketStatus.code)
        )
    ]
    priority_mix = [
        {"label": priority, "value": int(count)}
        for priority, count in db.execute(
            select(scoped.c.priority, func.count(scoped.c.id)).group_by(scoped.c.priority)
        )
    ]
    trend_start = today_start - timedelta(days=6)
    created_by_day: dict[str, int] = {}
    for created_at in db.scalars(
        select(scoped.c.created_at).where(scoped.c.created_at >= trend_start)
    ):
        key = created_at.date().isoformat()
        created_by_day[key] = created_by_day.get(key, 0) + 1
    ticket_trend = [
        {
            "date": (server_today() - timedelta(days=offset)).isoformat(),
            "created": created_by_day.get((server_today() - timedelta(days=offset)).isoformat(), 0),
        }
        for offset in range(6, -1, -1)
    ]

    permissions = set(effective_permissions(db, user).permissions)
    internal_user = user.user_type != "CLIENT_PORTAL"
    online_engineers = 0
    active_shifts = 0
    active_operations = 0
    blocked_operations = 0
    checklist_query = select(ServiceChecklistOccurrence.id).where(
        ServiceChecklistOccurrence.status.not_in(("CANCELLED",)),
    )
    if not permissions & {
        "service_checklist.view_all",
        "service_checklist.schedule.manage",
        "dashboard.manager",
        "dashboard.executive",
    }:
        checklist_query = checklist_query.where(
            ServiceChecklistOccurrence.assigned_user_id == user.id
        )
    checklist_scope = checklist_query.subquery("home_checklist_scope")
    completed_checklists = int(
        db.scalar(
            select(func.count(ServiceChecklistOccurrence.id)).where(
                ServiceChecklistOccurrence.id.in_(select(checklist_scope.c.id)),
                ServiceChecklistOccurrence.completed_at >= today_start - timedelta(days=6),
                ServiceChecklistOccurrence.completed_at < tomorrow_start,
            )
        )
        or 0
    )
    attention_checklists = int(
        db.scalar(
            select(func.count(func.distinct(ServiceChecklistOccurrence.id)))
            .outerjoin(
                ServiceChecklistOccurrenceItem,
                ServiceChecklistOccurrenceItem.occurrence_id == ServiceChecklistOccurrence.id,
            )
            .where(
                ServiceChecklistOccurrence.id.in_(select(checklist_scope.c.id)),
                ServiceChecklistOccurrence.status.not_in(("COMPLETED", "CANCELLED")),
                or_(
                    ServiceChecklistOccurrence.status == "BLOCKED",
                    ServiceChecklistOccurrence.due_at < now,
                    ServiceChecklistOccurrenceItem.state == "NEED_ATTENTION",
                ),
            )
        )
        or 0
    )
    if internal_user:
        online_engineers = int(
            db.scalar(
                select(func.count(User.id)).where(
                    User.is_active.in_([True]),
                    User.user_type == "EMPLOYEE",
                    User.last_seen_at >= now - timedelta(minutes=2),
                )
            )
            or 0
        )
        if "shift.view" in permissions or "dashboard.manager" in permissions:
            active_shifts = int(
                db.scalar(
                    select(func.count(Shift.id)).where(
                        Shift.starts_at <= now,
                        Shift.ends_at >= now,
                        Shift.status.not_in(["DRAFT", "CANCELLED"]),
                    )
                )
                or 0
            )
        if {
            "internal_operation.view",
            "internal_operation.workspace.view",
            "dashboard.manager",
        } & permissions:
            operation_counts = db.execute(
                select(
                    func.sum(
                        case(
                            (InternalOperation.status.not_in(["COMPLETED", "CANCELLED"]), 1),
                            else_=0,
                        )
                    ),
                    func.sum(case((InternalOperation.status == "BLOCKED", 1), else_=0)),
                )
            ).one()
            active_operations = int(operation_counts[0] or 0)
            blocked_operations = int(operation_counts[1] or 0)

    payload: dict[str, object] = {
        "generated_at": now,
        "today": server_today().isoformat(),
        "cache_seconds": int(_CACHE_SECONDS),
        "capabilities": {
            "internal_operations": internal_user,
        },
        "tickets": {
            "total": int(totals[0] or 0),
            "open": int(totals[1] or 0),
            "in_progress": int(totals[2] or 0),
            "unassigned": int(totals[3] or 0),
            "needs_attention": int(totals[4] or 0),
            "created_today": int(totals[5] or 0),
            "pending_approval": int(totals[6] or 0),
            "pending": int(totals[7] or 0),
        },
        "operations": {
            "online_engineers": online_engineers,
            "active_shifts": active_shifts,
            "active_operations": active_operations,
            "blocked_operations": blocked_operations,
        },
        "checklists": {
            "completed": completed_checklists,
            "needs_attention": attention_checklists,
        },
        "attention": [
            {
                "id": row.id,
                "ticket_number": row.ticket_number,
                "subject": row.subject,
                "priority": row.priority,
                "status": row.code,
                "client": row.name,
                "assigned": row.assigned_user_id is not None,
                "due_at": row.due_at,
                "last_activity_at": row.last_activity_at,
            }
            for row in attention_rows
        ],
        "status_mix": status_mix,
        "priority_mix": priority_mix,
        "ticket_trend": ticket_trend,
    }
    return _store(user.id, payload)
