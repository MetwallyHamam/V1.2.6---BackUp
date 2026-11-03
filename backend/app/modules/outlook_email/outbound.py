from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.core.config import Settings
from app.modules.clients.models import Client
from app.modules.configuration.policy_service import resolve_feature_policy
from app.modules.notifications.email_template import branded_email_html, frontend_url
from app.modules.outlook_email.graph_client import GraphRequestError, MicrosoftGraphClient
from app.modules.outlook_email.models import (
    OutlookEmailTemplate,
    OutlookMessage,
    OutlookOutboundDelivery,
)
from app.modules.tickets.models import Ticket

ALLOWED_VARIABLES = {"ticket_number", "subject", "status", "client_name"}


def render_template(value: str, variables: dict[str, str]) -> str:
    rendered = value
    for key in ALLOWED_VARIABLES:
        rendered = rendered.replace("{{" + key + "}}", variables.get(key, ""))
    return rendered


def enqueue_ticket_email(db: Session, ticket: Ticket, event_key: str) -> OutlookOutboundDelivery | None:
    policy_key = "email_creation_acknowledgement" if event_key == "CREATED" else "email_status_notifications"
    if resolve_feature_policy(db, policy_key, client_id=ticket.client_id, contract_id=ticket.contract_id).mode != "ENFORCED":
        return None
    source = db.scalar(select(OutlookMessage).where(OutlookMessage.ticket_id == ticket.id).order_by(OutlookMessage.received_at))
    template = db.scalar(select(OutlookEmailTemplate).where(OutlookEmailTemplate.event_key == event_key, OutlookEmailTemplate.is_enabled.in_([True])))
    if not source or not template:
        return None
    key = f"outlook-ticket:{ticket.id}:event:{event_key}:version:{ticket.version}"
    existing = db.scalar(select(OutlookOutboundDelivery).where(OutlookOutboundDelivery.deduplication_key == key))
    if existing:
        return existing
    client = db.get(Client, ticket.client_id)
    variables = {"ticket_number": ticket.ticket_number or "", "subject": ticket.subject, "status": ticket.status.code, "client_name": client.name if client else ""}
    item = OutlookOutboundDelivery(
        deduplication_key=key, ticket_id=ticket.id, event_key=event_key,
        recipient_email=source.sender_address, reply_graph_message_id=source.graph_message_id,
        subject=render_template(template.subject_template, variables)[:300],
        body=render_template(template.body_template, variables), status="PENDING",
    )
    db.add(item); db.flush(); return item


def process_outbound(db: Session, settings: Settings, limit: int = 25) -> dict[str, int]:
    now = server_now(); sent = retried = dead = 0; graph = MicrosoftGraphClient(settings)
    items = list(db.scalars(select(OutlookOutboundDelivery).where(
        OutlookOutboundDelivery.status.in_(["PENDING", "RETRY"]),
        or_(OutlookOutboundDelivery.next_attempt_at.is_(None), OutlookOutboundDelivery.next_attempt_at <= now),
    ).order_by(OutlookOutboundDelivery.created_at).limit(limit)))
    mailbox = "Support@millensys.com"
    for item in items:
        item.attempt_count += 1
        try:
            ticket_link = frontend_url(settings.frontend_base_url, f"/tickets/{item.ticket_id}")
            body = f"{item.body}\n\nOpen ticket:\n{ticket_link}"
            html_body = branded_email_html(item.subject, body, ticket_link)
            if item.reply_graph_message_id:
                result = graph.request("POST", f"users/{mailbox}/messages/{item.reply_graph_message_id}/reply", {"comment": html_body})
            else:
                result = graph.request("POST", f"users/{mailbox}/sendMail", {"message": {"subject": item.subject, "body": {"contentType": "HTML", "content": html_body}, "toRecipients": [{"emailAddress": {"address": item.recipient_email}}]}})
            item.status = "SENT"; item.sent_at = now; item.last_error = None; item.graph_message_id = str(result.get("id")) if result.get("id") else None; sent += 1
        except GraphRequestError as exc:
            item.last_error = str(exc)
            if item.attempt_count >= 5:
                item.status = "DEAD_LETTER"; dead += 1
            else:
                item.status = "RETRY"; item.next_attempt_at = now + timedelta(minutes=min(2 ** item.attempt_count, 60)); retried += 1
    db.commit(); return {"sent": sent, "retried": retried, "dead": dead}
