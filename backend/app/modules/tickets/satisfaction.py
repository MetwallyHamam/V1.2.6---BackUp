import hashlib
import json
import re
import secrets
from datetime import timedelta
from typing import Any, cast

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now, server_timezone
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.contact_access import contact_belongs_to_client
from app.modules.clients.models import Client, Contact
from app.modules.configuration.models import SiteSetting
from app.modules.iam.models import AuditLog, User
from app.modules.notifications.models import EventOutbox
from app.modules.tickets.models import Ticket, TicketSatisfaction, TicketStatus
from app.modules.tickets.satisfaction_tokens import (
    decrypt_satisfaction_token,
    encrypt_satisfaction_token,
)
from app.modules.tickets.service import ensure_ticket_access

router = APIRouter(prefix="/public/satisfaction", tags=["public satisfaction"])
management_router = APIRouter(prefix="/tickets", tags=["ticket satisfaction"])

DEFAULT_SUBJECT = "Rate support ticket {ticket_number}"
DEFAULT_BODY = "Dear {client_name},\n\nPlease rate the service for ticket {ticket_number}:\n{rating_url}\n\nThis link expires on {expires_at}."
ALLOWED_PLACEHOLDERS = {"client_name", "ticket_number", "rating_url", "company_name", "expires_at"}


class SatisfactionSubmit(BaseModel):
    ticket_rating: int = Field(ge=1, le=5)
    service_rating: int = Field(ge=1, le=5)
    engineer_rating: int = Field(ge=1, le=5)
    comments: str | None = Field(default=None, max_length=2000)


class ManualSatisfactionDelivery(BaseModel):
    channel: str = Field(pattern="^(COPY|WHATSAPP|EMAIL)$")
    contact_id: int | None = None


def submit_satisfaction(
    db: Session,
    survey: TicketSatisfaction,
    data: SatisfactionSubmit,
    *,
    source: str,
    actor_user_id: int | None = None,
) -> dict[str, object]:
    """Persist one response atomically for both public satisfaction surfaces."""
    if survey.submitted_at:
        return {
            "submitted": True,
            "already_submitted": True,
            "message": "Thank you. Your feedback was already saved.",
        }
    submitted_at = server_now()
    result = cast(
        CursorResult[Any],
        db.execute(
            update(TicketSatisfaction)
            .where(TicketSatisfaction.id == survey.id, TicketSatisfaction.submitted_at.is_(None))
            .values(
                ticket_rating=data.ticket_rating,
                service_rating=data.service_rating,
                engineer_rating=data.engineer_rating,
                comments=data.comments,
                submitted_at=submitted_at,
                feedback_source=source,
            )
        ),
    )
    if result.rowcount == 0:
        db.commit()
        return {
            "submitted": True,
            "already_submitted": True,
            "message": "Thank you. Your feedback was already saved.",
        }
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            entity_type="TicketSatisfaction",
            entity_id=str(survey.id),
            action="ticket.satisfaction.submitted",
            new_values_json=json.dumps({"ticket_id": survey.ticket_id, "source": source}),
        )
    )
    db.commit()
    return {
        "submitted": True,
        "already_submitted": False,
        "message": "Thank you for your feedback.",
    }


def satisfaction_result(survey: TicketSatisfaction) -> dict[str, object]:
    return {
        "ticket_rating": survey.ticket_rating,
        "service_rating": survey.service_rating,
        "engineer_rating": survey.engineer_rating,
        "comments": survey.comments,
        "submitted_at": survey.submitted_at,
        "source": survey.feedback_source,
    }


def ensure_satisfaction_survey(
    db: Session, ticket: Ticket, recipient_email: str = ""
) -> TicketSatisfaction:
    survey = db.scalar(
        select(TicketSatisfaction).where(TicketSatisfaction.ticket_id == ticket.id)
    )
    if survey:
        return survey
    raw_token = secrets.token_urlsafe(40)
    survey = TicketSatisfaction(
        ticket_id=ticket.id,
        engineer_user_id=ticket.assigned_user_id,
        recipient_email=recipient_email,
        token_hash=token_hash(raw_token),
        token_ciphertext=encrypt_satisfaction_token(raw_token),
        expires_at=server_now() + timedelta(days=30),
    )
    db.add(survey)
    db.flush()
    return survey


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _setting(db: Session, key: str, default: str) -> str:
    row = db.get(SiteSetting, key)
    return row.value if row else default


def _enabled(db: Session, key: str, default: bool = False) -> bool:
    return _setting(db, key, str(default).lower()).lower() == "true"


def _render(template: str, values: dict[str, str]) -> str:
    placeholders = set(re.findall(r"\{([a-z_]+)\}", template))
    invalid = placeholders - ALLOWED_PLACEHOLDERS
    if invalid:
        raise ConflictError(
            "INVALID_SATISFACTION_TEMPLATE",
            f"Unsupported satisfaction template placeholder: {sorted(invalid)[0]}.",
        )
    return template.format_map(values)


def enqueue_satisfaction_invitation(db: Session, ticket: Ticket, settings: Settings) -> None:
    if db.scalar(select(TicketSatisfaction.id).where(TicketSatisfaction.ticket_id == ticket.id)):
        return
    contact = db.get(Contact, ticket.requester_contact_id) if ticket.requester_contact_id else None
    client = db.get(Client, ticket.client_id)
    recipient = contact.email if contact and contact.email else (client.email if client else None)
    raw_token = secrets.token_urlsafe(40)
    expires = server_now() + timedelta(days=30)
    survey = TicketSatisfaction(
        ticket_id=ticket.id,
        engineer_user_id=ticket.assigned_user_id,
        recipient_email=recipient or "",
        token_hash=token_hash(raw_token),
        token_ciphertext=encrypt_satisfaction_token(raw_token),
        expires_at=expires,
    )
    db.add(survey)
    db.flush()
    if not recipient:
        return
    url = f"{settings.frontend_base_url}/satisfaction?token={raw_token}"
    db.add(
        EventOutbox(
            event_type="SATISFACTION_INVITATION",
            aggregate_type="Ticket",
            aggregate_id=str(ticket.id),
            deduplication_key=f"satisfaction:{ticket.id}",
            payload_json=json.dumps(
                {
                    "recipient_email": recipient,
                    "subject": f"Rate support ticket {ticket.ticket_number}",
                    "body": f"Your ticket {ticket.ticket_number} has been closed. Please rate the service and assigned engineer using this secure one-time link:\n\n{url}\n\nThe link expires in 30 days.",
                    "survey_id": survey.id,
                }
            ),
        )
    )


@management_router.post("/{ticket_id}/satisfaction-delivery")
def prepare_manual_satisfaction_delivery(
    ticket_id: int,
    data: ManualSatisfactionDelivery,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.satisfaction.send")),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    if not _enabled(db, "satisfaction_manual_enabled"):
        raise ConflictError(
            "SATISFACTION_MANUAL_DISABLED", "Manual rating-link delivery is disabled."
        )
    channel_key = f"satisfaction_{data.channel.lower()}_enabled"
    if data.channel != "COPY" and not _enabled(db, channel_key, True):
        raise ConflictError(
            "SATISFACTION_CHANNEL_DISABLED", f"{data.channel.title()} delivery is disabled."
        )
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    status = db.get(TicketStatus, ticket.status_id)
    if not status or status.code != "CLOSED":
        raise ConflictError(
            "SATISFACTION_NOT_ELIGIBLE", "Only closed tickets are eligible for rating."
        )
    selected_contact_id = data.contact_id or ticket.requester_contact_id
    contact = db.get(Contact, selected_contact_id) if selected_contact_id else None
    if contact and not contact_belongs_to_client(db, contact, ticket.client_id):
        raise ConflictError(
            "CONTACT_CLIENT_MISMATCH", "The selected contact does not belong to this client."
        )
    client = db.get(Client, ticket.client_id)
    email = contact.email if contact and contact.email else (client.email if client else None)
    phone = contact.phone_number if contact and contact.phone_number else None
    if data.channel == "EMAIL" and not email:
        raise ConflictError(
            "SATISFACTION_EMAIL_MISSING", "The caller or client does not have an email address."
        )
    if data.channel == "WHATSAPP" and not phone:
        raise ConflictError(
            "SATISFACTION_PHONE_MISSING", "The caller does not have a mobile number."
        )
    survey = db.scalar(select(TicketSatisfaction).where(TicketSatisfaction.ticket_id == ticket.id))
    if survey and survey.submitted_at:
        raise ConflictError(
            "SURVEY_ALREADY_SUBMITTED", "This satisfaction survey was already submitted."
        )
    now = server_now()
    expiry_days = min(365, max(1, int(_setting(db, "satisfaction_token_expiry_days", "30"))))
    raw_token: str | None = None
    if (
        survey
        and survey.token_ciphertext
        and survey.expires_at.replace(tzinfo=server_timezone()) > now
    ):
        raw_token = decrypt_satisfaction_token(survey.token_ciphertext)
    if raw_token is None:
        raw_token = secrets.token_urlsafe(40)
        expires_at = now + timedelta(days=expiry_days)
        if survey:
            survey.token_hash = token_hash(raw_token)
            survey.token_ciphertext = encrypt_satisfaction_token(raw_token)
            survey.expires_at = expires_at
            survey.recipient_email = email or survey.recipient_email
        else:
            survey = TicketSatisfaction(
                ticket_id=ticket.id,
                engineer_user_id=ticket.assigned_user_id,
                recipient_email=email or "",
                token_hash=token_hash(raw_token),
                token_ciphertext=encrypt_satisfaction_token(raw_token),
                expires_at=expires_at,
            )
            db.add(survey)
    assert survey is not None
    db.flush()
    rating_url = f"{settings.frontend_base_url}/satisfaction?token={raw_token}"
    values = {
        "client_name": client.name if client else "valued customer",
        "ticket_number": str(ticket.ticket_number),
        "rating_url": rating_url,
        "company_name": _setting(db, "company_name", "Millensys Support Hub"),
        "expires_at": survey.expires_at.date().isoformat(),
    }
    subject = _render(_setting(db, "satisfaction_email_subject", DEFAULT_SUBJECT), values)
    template_key = (
        "satisfaction_email_body" if data.channel == "EMAIL" else "satisfaction_whatsapp_template"
    )
    message = _render(_setting(db, template_key, DEFAULT_BODY), values)
    if data.channel == "EMAIL":
        db.add(
            EventOutbox(
                event_type="SATISFACTION_INVITATION",
                aggregate_type="Ticket",
                aggregate_id=str(ticket.id),
                deduplication_key=f"satisfaction-manual:{ticket.id}:{now.timestamp()}",
                payload_json=json.dumps(
                    {
                        "recipient_email": email,
                        "subject": subject,
                        "body": message,
                        "survey_id": survey.id,
                    }
                ),
            )
        )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket.id),
            action="ticket.satisfaction.delivery.prepared",
            new_values_json=json.dumps(
                {
                    "channel": data.channel,
                    "recipient": email if data.channel == "EMAIL" else phone,
                    "contact_id": selected_contact_id,
                    "survey_id": survey.id,
                }
            ),
        )
    )
    db.commit()
    return {
        "channel": data.channel,
        "recipient": email if data.channel == "EMAIL" else phone,
        "subject": subject,
        "message": message,
        "url": rating_url,
        "delivery_status": "QUEUED" if data.channel == "EMAIL" else "PREPARED",
        "expires_at": survey.expires_at,
    }


def _survey(db: Session, raw_token: str) -> TicketSatisfaction:
    survey = db.scalar(
        select(TicketSatisfaction).where(TicketSatisfaction.token_hash == token_hash(raw_token))
    )
    if not survey:
        raise NotFoundError("This satisfaction link is invalid.")
    if survey.expires_at.replace(tzinfo=server_timezone()) < server_now():
        raise ConflictError("SURVEY_EXPIRED", "This satisfaction link has expired.")
    return survey


@router.get("")
def read_survey(token: str, db: Session = Depends(get_db)) -> dict[str, object]:
    survey = _survey(db, token)
    ticket = db.get(Ticket, survey.ticket_id)
    return {
        "ticket_number": ticket.ticket_number if ticket else None,
        "subject": ticket.subject if ticket else None,
        "submitted": survey.submitted_at is not None,
        "service_rating": survey.service_rating,
        "engineer_rating": survey.engineer_rating,
        "ticket_rating": survey.ticket_rating,
        "comments": survey.comments,
        "submitted_at": survey.submitted_at,
        "source": survey.feedback_source,
    }


@router.post("")
def submit_survey(
    data: SatisfactionSubmit, token: str, db: Session = Depends(get_db)
) -> dict[str, object]:
    survey = _survey(db, token)
    return submit_satisfaction(db, survey, data, source="CUSTOMER_LINK")
