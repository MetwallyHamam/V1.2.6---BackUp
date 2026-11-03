import hashlib
import json
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now, server_timezone
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.contact_access import contact_belongs_to_client
from app.modules.clients.models import Client, Contact
from app.modules.configuration.models import SiteSetting
from app.modules.contracts.models import TicketSlaInterval
from app.modules.escalations.models import EscalationEvent
from app.modules.iam.models import AuditLog, User
from app.modules.notifications.models import EventOutbox
from app.modules.tickets.models import (
    Ticket,
    TicketComment,
    TicketLiveUpdate,
    TicketSatisfaction,
    TicketStatus,
    TicketStatusHistory,
)
from app.modules.tickets.satisfaction import (
    SatisfactionSubmit,
    satisfaction_result,
    submit_satisfaction,
)
from app.modules.tickets.satisfaction_tokens import (
    decrypt_satisfaction_token,
    encrypt_satisfaction_token,
)
from app.modules.tickets.service import ensure_ticket_access

public_router = APIRouter(prefix="/public/ticket-updates", tags=["public ticket updates"])
management_router = APIRouter(prefix="/tickets", tags=["tickets"])


class LiveUpdateDeliveryInput(BaseModel):
    channel: str = Field(default="COPY", pattern="^(COPY|WHATSAPP|EMAIL)$")
    contact_id: int | None = None


def _token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _enabled(db: Session) -> bool:
    setting = db.get(SiteSetting, "live_ticket_update_enabled")
    return setting is None or setting.value.lower() == "true"


def _closed_poll_seconds(db: Session) -> int:
    setting = db.get(SiteSetting, "live_ticket_update_closed_poll_seconds")
    try:
        return min(3600, max(60, int(setting.value if setting else "300")))
    except ValueError:
        return 300


def _live_link(db: Session, token: str) -> tuple[TicketLiveUpdate, Ticket]:
    if not _enabled(db):
        raise NotFoundError("This live ticket-update link is unavailable.")
    link = db.scalar(
        select(TicketLiveUpdate).where(TicketLiveUpdate.token_hash == _token_hash(token))
    )
    if not link or not link.is_active:
        raise NotFoundError("This live ticket-update link is invalid.")
    if link.expires_at.replace(tzinfo=server_timezone()) < server_now():
        raise ConflictError(
            "LIVE_TICKET_UPDATE_EXPIRED", "This live ticket-update link has expired."
        )
    ticket = db.get(Ticket, link.ticket_id)
    if not ticket:
        raise NotFoundError()
    return link, ticket


def _satisfaction_state(
    db: Session, ticket: Ticket, status_code: str | None
) -> tuple[str, TicketSatisfaction | None]:
    survey = db.scalar(select(TicketSatisfaction).where(TicketSatisfaction.ticket_id == ticket.id))
    if survey and survey.submitted_at:
        return "SUBMITTED", survey
    if status_code != "CLOSED" or not survey or survey.eligibility_status != "ELIGIBLE":
        return "UNAVAILABLE", survey
    if survey.expires_at.replace(tzinfo=server_timezone()) <= server_now():
        return "EXPIRED", survey
    return "AVAILABLE", survey


@management_router.post("/{ticket_id}/live-update-link")
def issue_live_update_link(
    ticket_id: int,
    data: LiveUpdateDeliveryInput = LiveUpdateDeliveryInput(),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.live_update.send")),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    if not _enabled(db):
        raise ConflictError(
            "LIVE_TICKET_UPDATE_DISABLED", "Public live ticket-update links are disabled."
        )
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    selected_contact_id = data.contact_id or ticket.requester_contact_id
    contact = db.get(Contact, selected_contact_id) if selected_contact_id else None
    if contact and not contact_belongs_to_client(db, contact, ticket.client_id):
        raise ConflictError(
            "CONTACT_CLIENT_MISMATCH", "The selected contact does not belong to this client."
        )
    if data.channel == "WHATSAPP" and not (contact and contact.phone_number):
        raise ConflictError(
            "LIVE_UPDATE_PHONE_MISSING", "The selected contact does not have a mobile number."
        )
    if data.channel == "EMAIL" and not (contact and contact.email):
        raise ConflictError(
            "LIVE_UPDATE_EMAIL_MISSING", "The selected contact does not have an email address."
        )
    now = server_now()
    link = db.scalar(
        select(TicketLiveUpdate)
        .where(
            TicketLiveUpdate.ticket_id == ticket.id,
            TicketLiveUpdate.is_active.in_([True]),
            TicketLiveUpdate.expires_at > now,
        )
        .order_by(TicketLiveUpdate.created_at.desc())
    )
    raw_token = (
        decrypt_satisfaction_token(link.token_ciphertext)
        if link and link.token_ciphertext
        else None
    )
    if raw_token is None:
        for stale in db.scalars(
            select(TicketLiveUpdate).where(
                TicketLiveUpdate.ticket_id == ticket.id, TicketLiveUpdate.is_active.in_([True])
            )
        ):
            stale.is_active = False
        raw_token = secrets.token_urlsafe(40)
        expires_at = now + timedelta(days=365)
        link = TicketLiveUpdate(
            ticket_id=ticket.id,
            token_hash=_token_hash(raw_token),
            token_ciphertext=encrypt_satisfaction_token(raw_token),
            expires_at=expires_at,
            created_by_user_id=actor.id,
            is_active=True,
        )
        db.add(link)
    else:
        assert link is not None
        expires_at = link.expires_at
    assert link is not None
    db.flush()
    url = f"{settings.frontend_base_url}/ticket-update?token={raw_token}"
    message = f"Track ticket {ticket.ticket_number} live and view public updates: {url}"
    if data.channel == "EMAIL":
        assert contact is not None and contact.email
        db.add(
            EventOutbox(
                event_type="TICKET_LIVE_UPDATE",
                aggregate_type="Ticket",
                aggregate_id=str(ticket.id),
                deduplication_key=f"live-update:{ticket.id}:{now.timestamp()}",
                payload_json=json.dumps(
                    {
                        "recipient_email": contact.email,
                        "subject": f"Live update for ticket {ticket.ticket_number}",
                        "body": message,
                    }
                ),
            )
        )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket.id),
            action="ticket.live_update.delivery.prepared",
            new_values_json=json.dumps(
                {"link_id": link.id, "channel": data.channel, "contact_id": selected_contact_id}
            ),
        )
    )
    db.commit()
    return {
        "url": url,
        "message": message,
        "recipient": contact.email
        if data.channel == "EMAIL" and contact
        else contact.phone_number
        if contact
        else None,
        "delivery_status": "QUEUED" if data.channel == "EMAIL" else "PREPARED",
        "expires_at": expires_at,
    }


@public_router.get("")
def read_live_update(token: str, db: Session = Depends(get_db)) -> dict[str, object]:
    _, ticket = _live_link(db, token)
    status = db.get(TicketStatus, ticket.status_id)
    client = db.get(Client, ticket.client_id)
    history_rows = list(
        db.execute(
            select(TicketStatusHistory, TicketStatus)
            .join(TicketStatus, TicketStatus.id == TicketStatusHistory.to_status_id)
            .where(TicketStatusHistory.ticket_id == ticket.id)
            .order_by(TicketStatusHistory.created_at, TicketStatusHistory.id)
        ).all()
    )
    comments = list(
        db.scalars(
            select(TicketComment)
            .where(TicketComment.ticket_id == ticket.id, TicketComment.is_internal.in_([False]))
            .order_by(TicketComment.created_at)
        )
    )
    escalation_times = [
        value
        for value in (
            ticket.escalated_at,
            db.scalar(
                select(TicketSlaInterval.started_at)
                .where(
                    TicketSlaInterval.ticket_id == ticket.id,
                    TicketSlaInterval.interval_type == "ESCALATION",
                )
                .order_by(TicketSlaInterval.started_at)
            ),
            db.scalar(
                select(EscalationEvent.created_at)
                .where(EscalationEvent.ticket_id == ticket.id)
                .order_by(EscalationEvent.created_at)
            ),
        )
        if value is not None
    ]
    escalation_at = min(escalation_times) if escalation_times else None
    escalation_active = (
        ticket.escalation_level is not None or ticket.escalation_assignee_user_id is not None
    )
    flow = [
        {
            "code": history_status.code,
            "name": history_status.name,
            "reached_at": history.created_at,
            "description": None,
        }
        for history, history_status in history_rows
    ]
    if escalation_at:
        flow.append(
            {
                "code": "ESCALATED",
                "name": "Escalated",
                "reached_at": escalation_at,
                "description": "Additional support attention was requested for this ticket.",
            }
        )
    flow.sort(key=lambda item: item["reached_at"])
    satisfaction_state, satisfaction = _satisfaction_state(
        db, ticket, status.code if status else None
    )
    return {
        "ticket_number": ticket.ticket_number,
        "subject": ticket.subject,
        "description": ticket.description,
        "client_name": client.name if client else None,
        "status": status.name if status else None,
        "status_code": status.code if status else None,
        "closed_poll_seconds": _closed_poll_seconds(db),
        "priority": ticket.priority,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "resolved_at": ticket.resolved_at,
        "closed_at": ticket.closed_at,
        "resolution_seconds": int(
            (
                (ticket.resolved_at or ticket.closed_at or server_now())
                - ticket.created_at.replace(tzinfo=server_timezone())
            ).total_seconds()
        ),
        "status_flow": flow,
        "escalation": (
            {
                "state": "ACTIVE" if escalation_active else "HISTORICAL",
                "occurred_at": escalation_at,
                "description": "Additional support attention was requested for this ticket.",
            }
            if escalation_at
            else None
        ),
        "satisfaction": {
            "state": satisfaction_state,
            **(
                satisfaction_result(satisfaction)
                if satisfaction_state == "SUBMITTED" and satisfaction
                else {}
            ),
        },
        "comments": [
            {"id": item.id, "body": item.body, "created_at": item.created_at} for item in comments
        ],
    }


@public_router.post("/satisfaction")
def submit_live_satisfaction(
    data: SatisfactionSubmit,
    token: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _, ticket = _live_link(db, token)
    status = db.get(TicketStatus, ticket.status_id)
    state, survey = _satisfaction_state(db, ticket, status.code if status else None)
    if state == "SUBMITTED" and survey:
        return {
            "submitted": True,
            "already_submitted": True,
            "message": "Thank you. Your feedback was already saved.",
        }
    if state == "EXPIRED":
        raise ConflictError("SURVEY_EXPIRED", "This satisfaction opportunity has expired.")
    if state != "AVAILABLE" or not survey:
        raise ConflictError(
            "SATISFACTION_NOT_AVAILABLE", "Satisfaction feedback is not available for this ticket."
        )
    return submit_satisfaction(db, survey, data, source="LIVE_UPDATE")
