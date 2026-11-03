import asyncio
import json
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query, Response, WebSocket, WebSocketDisconnect
from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, require_permission
from app.core.clock import server_now, server_timezone
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import SessionLocal, get_db
from app.modules.configuration.models import SiteSetting
from app.modules.escalations.models import EscalationRule
from app.modules.escalations.scheduler import run_lock, scheduler_state
from app.modules.escalations.service import evaluate_escalations
from app.modules.iam.models import AuditLog, User
from app.modules.notifications.email_service import process_email_outbox
from app.modules.notifications.models import Notification, NotificationPreference, NotificationView
from app.modules.notifications.realtime import realtime_tickets
from app.modules.notifications.schemas import (
    EscalationRuleCreate,
    EscalationRuleRead,
    EscalationRuleUpdate,
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
    NotificationRead,
    NotificationViewCreate,
    NotificationViewRead,
    RealtimeTicketRead,
)
from app.modules.notifications.sms_service import process_sms_outbox
from app.modules.notifications.teams_service import process_teams_outbox

router = APIRouter(tags=["notifications and escalations"])


def notification_query(
    user_id: int, *, unread_only: bool = False, is_read: bool | None = None,
    unacknowledged_only: bool = False,
    severity: str | None = None, notification_type: str | None = None,
    search: str | None = None, date_from: date | None = None, date_to: date | None = None,
    date_scope: str = "TODAY",
) -> Select[tuple[Notification]]:
    statement = select(Notification).where(Notification.recipient_user_id == user_id)
    if unacknowledged_only:
        statement = statement.where(Notification.acknowledged_at.is_(None))
    if unread_only or is_read is False:
        statement = statement.where(Notification.is_read.in_([False]))
    elif is_read is True:
        statement = statement.where(Notification.is_read.in_([True]))
    if severity:
        statement = statement.where(Notification.severity == severity)
    if notification_type:
        statement = statement.where(Notification.notification_type == notification_type)
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(or_(Notification.title.ilike(term), Notification.message.ilike(term)))
    effective_from = date_from or (server_now().date() if date_scope != "ALL" else None)
    if effective_from:
        statement = statement.where(Notification.created_at >= datetime.combine(effective_from, time.min, tzinfo=server_timezone()))
    if date_to:
        statement = statement.where(Notification.created_at < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=server_timezone()))
    return statement


def _default_sound(db: Session) -> bool:
    setting = db.get(SiteSetting, "default_sound")
    return not setting or setting.value == "true"


def notification_snapshot(user_id: int) -> dict[str, int]:
    with SessionLocal() as db:
        unread_count = db.scalar(
            select(func.count(Notification.id)).where(
                Notification.recipient_user_id == user_id,
                Notification.is_read.in_([False]),
            )
        ) or 0
        latest_id = db.scalar(
            select(func.max(Notification.id)).where(Notification.recipient_user_id == user_id)
        ) or 0
    return {"unread_count": unread_count, "latest_id": latest_id}


@router.get("/notifications", response_model=list[NotificationRead])
def list_notifications(
    unread_only: bool = False,
    unacknowledged_only: bool = False,
    is_read: bool | None = None,
    severity: str | None = None,
    notification_type: str | None = None,
    search: str | None = Query(default=None, max_length=100),
    date_from: date | None = None,
    date_to: date | None = None,
    date_scope: str = Query(default="TODAY", pattern="^(TODAY|ALL)$"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[Notification]:
    statement = notification_query(user.id, unread_only=unread_only, unacknowledged_only=unacknowledged_only, is_read=is_read, severity=severity, notification_type=notification_type, search=search, date_from=date_from, date_to=date_to, date_scope=date_scope)
    return list(db.scalars(statement.order_by(Notification.created_at.desc()).limit(100)))


@router.post("/notifications/mentions/acknowledge-all", status_code=204)
def acknowledge_all_mentions(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> Response:
    now = server_now()
    db.query(Notification).filter(
        Notification.recipient_user_id == user.id,
        Notification.notification_type == "TICKET_MENTION",
        Notification.acknowledged_at.is_(None),
    ).update(
        {Notification.is_read: True, Notification.read_at: now, Notification.acknowledged_at: now},
        synchronize_session=False,
    )
    db.commit()
    return Response(status_code=204)


@router.post("/notifications/{notification_id}/acknowledge", status_code=204)
def acknowledge_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> Response:
    item = db.scalar(select(Notification).where(Notification.id == notification_id, Notification.recipient_user_id == user.id))
    if not item:
        raise NotFoundError()
    now = server_now()
    item.is_read = True
    item.read_at = item.read_at or now
    item.acknowledged_at = now
    db.commit()
    return Response(status_code=204)


@router.post("/notifications/{notification_id}/read", status_code=204)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> Response:
    item = db.scalar(select(Notification).where(Notification.id == notification_id, Notification.recipient_user_id == user.id))
    if not item:
        raise NotFoundError()
    item.is_read = True
    item.read_at = server_now()
    db.commit()
    return Response(status_code=204)


@router.post("/notifications/mark-all-read", status_code=204)
def mark_all_read(
    filtered: bool = False, severity: str | None = None, notification_type: str | None = None,
    search: str | None = Query(default=None, max_length=100), date_from: date | None = None,
    date_to: date | None = None, date_scope: str = Query(default="ALL", pattern="^(TODAY|ALL)$"),
    db: Session = Depends(get_db), user: User = Depends(current_user),
) -> Response:
    statement = notification_query(user.id, unread_only=True, severity=severity if filtered else None, notification_type=notification_type if filtered else None, search=search if filtered else None, date_from=date_from if filtered else None, date_to=date_to if filtered else None, date_scope=date_scope if filtered else "ALL")
    now = server_now()
    ids = list(db.scalars(statement.with_only_columns(Notification.id)))
    if ids:
        db.query(Notification).filter(Notification.id.in_(ids)).update({Notification.is_read: True, Notification.read_at: now}, synchronize_session=False)
        db.commit()
    return Response(status_code=204)


@router.get("/notification-preferences/me", response_model=NotificationPreferenceRead)
def get_notification_preferences(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> NotificationPreferenceRead:
    preference = db.scalar(
        select(NotificationPreference).where(NotificationPreference.user_id == user.id)
    )
    return NotificationPreferenceRead(
        sound_enabled=preference.sound_enabled if preference else _default_sound(db),
        desktop_enabled=preference.desktop_enabled if preference else False,
        sound_code=preference.sound_code if preference else "CHIME",
        volume_percent=preference.volume_percent if preference else 70,
    )


@router.put("/notification-preferences/me", response_model=NotificationPreferenceRead)
def update_notification_preferences(
    data: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> NotificationPreference:
    preference = db.scalar(
        select(NotificationPreference).where(NotificationPreference.user_id == user.id)
    )
    if not preference:
        preference = NotificationPreference(user_id=user.id)
        db.add(preference)
    preference.sound_enabled = data.sound_enabled
    preference.desktop_enabled = data.desktop_enabled
    preference.sound_code = data.sound_code
    preference.volume_percent = data.volume_percent
    db.commit()
    db.refresh(preference)
    return preference


@router.get("/notification-views", response_model=list[NotificationViewRead])
def list_notification_views(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[NotificationView]:
    return list(db.scalars(select(NotificationView).where(NotificationView.user_id == user.id).order_by(NotificationView.name)))


@router.post("/notification-views", response_model=NotificationViewRead, status_code=201)
def create_notification_view(data: NotificationViewCreate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> NotificationView:
    if data.is_default:
        db.query(NotificationView).filter(NotificationView.user_id == user.id).update({NotificationView.is_default: False})
    view = NotificationView(user_id=user.id, name=data.name, filters_json=json.dumps(data.filters), is_default=data.is_default)
    db.add(view); db.commit(); db.refresh(view)
    return view


@router.delete("/notification-views/{view_id}", status_code=204)
def delete_notification_view(view_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Response:
    view = db.scalar(select(NotificationView).where(NotificationView.id == view_id, NotificationView.user_id == user.id))
    if not view:
        raise NotFoundError()
    db.delete(view); db.commit()
    return Response(status_code=204)


@router.post("/notifications/realtime-ticket", response_model=RealtimeTicketRead)
def create_realtime_ticket(user: User = Depends(current_user)) -> RealtimeTicketRead:
    return RealtimeTicketRead(ticket=realtime_tickets.issue(user.id), expires_in=30)


@router.websocket("/notifications/ws")
async def notification_socket(websocket: WebSocket, ticket: str = "") -> None:
    user_id = realtime_tickets.consume(ticket)
    if user_id is None:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    previous: dict[str, int] | None = None
    try:
        while True:
            snapshot = await asyncio.to_thread(notification_snapshot, user_id)
            if snapshot != previous:
                await websocket.send_json({"type": "notifications.changed", **snapshot})
                previous = snapshot
            # Notifications are durable in the database; a modest cadence avoids two
            # aggregate queries every three seconds for every connected browser/tab.
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        return


def _validate_escalation_rule_context(
    db: Session,
    data: EscalationRuleCreate,
    *,
    exclude_id: int | None = None,
) -> None:
    statement = select(EscalationRule.id).where(
        EscalationRule.clock_type == data.clock_type,
        EscalationRule.threshold_percent == data.threshold_percent,
        EscalationRule.priority == data.priority,
    )
    if exclude_id is not None:
        statement = statement.where(EscalationRule.id != exclude_id)
    if db.scalar(statement):
        raise ConflictError(
            "DUPLICATE_ESCALATION_RULE",
            "A rule already exists for this clock, threshold, and priority.",
        )


@router.get("/escalation-rules", response_model=list[EscalationRuleRead])
def list_rules(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("configuration.manage")),
) -> list[EscalationRule]:
    return list(db.scalars(select(EscalationRule).order_by(EscalationRule.clock_type, EscalationRule.threshold_percent, EscalationRule.priority)))


@router.post("/escalation-rules", response_model=EscalationRuleRead, status_code=201)
def create_escalation_rule(
    data: EscalationRuleCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> EscalationRule:
    _validate_escalation_rule_context(db, data)
    item = EscalationRule(code=f"PENDING-{server_now().timestamp()}", **data.model_dump())
    db.add(item)
    try:
        db.flush()
        item.code = f"SLA_RULE_{item.id:06d}"
        db.add(AuditLog(actor_user_id=actor.id, entity_type="EscalationRule", entity_id=str(item.id), action="escalation_rule.created", new_values_json=json.dumps(data.model_dump(mode="json"))))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("DUPLICATE_ESCALATION_RULE", "That escalation rule already exists.") from exc
    db.refresh(item)
    return item


@router.patch("/escalation-rules/{rule_id}", response_model=EscalationRuleRead)
def update_escalation_rule(
    rule_id: int,
    data: EscalationRuleUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> EscalationRule:
    item = db.get(EscalationRule, rule_id)
    if not item:
        raise NotFoundError("Escalation rule does not exist.")
    if item.version != data.expected_version:
        raise ConflictError("STALE_ESCALATION_RULE", "The escalation rule changed; reload and try again.")
    _validate_escalation_rule_context(db, data, exclude_id=item.id)
    before = {
        key: getattr(item, key)
        for key in type(data).model_fields
        if key != "expected_version"
    }
    for key, value in data.model_dump(exclude={"expected_version"}).items():
        setattr(item, key, value)
    item.version += 1
    db.add(AuditLog(actor_user_id=actor.id, entity_type="EscalationRule", entity_id=str(item.id), action="escalation_rule.updated", old_values_json=json.dumps(before), new_values_json=json.dumps(data.model_dump(mode="json"))))
    db.commit()
    db.refresh(item)
    return item


@router.post("/escalations/evaluate")
def evaluate(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("configuration.manage")),
) -> dict[str, int]:
    if not run_lock.acquire(blocking=False):
        raise ConflictError(
            "ESCALATION_EVALUATION_RUNNING",
            "An SLA escalation evaluation is already running.",
        )
    try:
        return {"created_events": evaluate_escalations(db)}
    finally:
        run_lock.release()


@router.get("/escalations/scheduler-status")
def scheduler_status(
    settings: Settings = Depends(get_settings),
    _: User = Depends(require_permission("configuration.manage")),
) -> dict[str, object]:
    return scheduler_state.snapshot(settings)


@router.post("/notifications/email/process")
def process_email(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(require_permission("configuration.manage")),
) -> dict[str, int]:
    result = process_email_outbox(db, settings)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="EmailOutbox",
            entity_id="manual",
            action="email.outbox.processed_manually",
            new_values_json=json.dumps(result),
        )
    )
    db.commit()
    return result


@router.post("/notifications/sms/process")
def process_sms(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: User = Depends(require_permission("configuration.manage")),
) -> dict[str, int]:
    return process_sms_outbox(db, settings)


@router.post("/notifications/teams/process")
def process_teams(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: User = Depends(require_permission("configuration.manage")),
) -> dict[str, int]:
    return process_teams_outbox(db, settings)
