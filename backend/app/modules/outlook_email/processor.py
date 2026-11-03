import base64
import html
import json
import re
import urllib.parse
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.core.config import Settings
from app.core.exceptions import AppError
from app.modules.clients.models import Client, Contact
from app.modules.configuration.policy_service import resolve_feature_policy
from app.modules.entitlements.approval_service import create_idempotent_approval
from app.modules.iam.models import User
from app.modules.iam.service import normalize
from app.modules.outlook_email.graph_client import MicrosoftGraphClient
from app.modules.outlook_email.models import OutlookMessage, OutlookNotification
from app.modules.outlook_email.outbound import enqueue_ticket_email
from app.modules.outlook_email.routes import OutlookConfigurationWrite, load_configuration
from app.modules.tickets.attachments import save_attachment_bytes
from app.modules.tickets.models import TicketComment, TicketType
from app.modules.tickets.schemas import TicketCreate
from app.modules.tickets.service import create_ticket


@dataclass(frozen=True)
class SenderResolution:
    status: str
    client: Client | None
    contact: Contact | None
    reason: str


def normalize_subject(value: str) -> str:
    subject = value.strip()
    while True:
        reduced = re.sub(r"^\s*(re|fw|fwd)\s*:\s*", "", subject, flags=re.IGNORECASE)
        if reduced == subject:
            return subject[:300] or "Email support request"
        subject = reduced


def plain_body(message: dict[str, object]) -> str:
    body = message.get("body")
    content = str(body.get("content", "")) if isinstance(body, dict) else ""
    content_type = str(body.get("contentType", "text")) if isinstance(body, dict) else "text"
    if content_type.casefold() == "html":
        content = re.sub(r"<\s*br\s*/?\s*>", "\n", content, flags=re.IGNORECASE)
        content = re.sub(r"</\s*p\s*>", "\n", content, flags=re.IGNORECASE)
        content = re.sub(r"<[^>]+>", " ", content)
        content = html.unescape(content)
    return re.sub(r"[ \t]+", " ", content).strip()[:20000]


def sender_address(message: dict[str, object]) -> str:
    sender = message.get("from") or message.get("sender")
    address = sender.get("emailAddress") if isinstance(sender, dict) else None
    return normalize(str(address.get("address", ""))) if isinstance(address, dict) else ""


def is_automatic_or_loop(message: dict[str, object], mailbox: str) -> bool:
    sender = sender_address(message)
    if not sender or sender == normalize(mailbox):
        return True
    subject = str(message.get("subject", ""))
    if re.search(r"(^|\s)(automatic reply|out of office|undeliverable|delivery status notification)", subject, re.IGNORECASE):
        return True
    headers = message.get("internetMessageHeaders", [])
    for header in headers if isinstance(headers, list) else []:
        if not isinstance(header, dict):
            continue
        name = str(header.get("name", "")).casefold()
        value = str(header.get("value", "")).casefold()
        if name == "auto-submitted" and value not in {"", "no"}:
            return True
        if name in {"x-autoreply", "x-autorespond", "x-supporthub-generated"}:
            return True
    return False


def resolve_sender(db: Session, sender: str, configuration: OutlookConfigurationWrite) -> SenderResolution:
    if sender in {normalize(str(item)) for item in configuration.blocked_senders}:
        return SenderResolution("BLOCKED", None, None, "Sender is explicitly blocked.")
    domain = sender.rsplit("@", 1)[-1] if "@" in sender else ""
    allowed = sender in {normalize(str(item)) for item in configuration.allowed_addresses} or domain in set(configuration.allowed_domains)
    if not allowed:
        status = "IGNORED" if configuration.unknown_sender_action == "IGNORE" else "QUARANTINED"
        return SenderResolution(status, None, None, "Sender is not in an allowed address or domain.")
    contacts = list(db.scalars(select(Contact).where(func.lower(Contact.email) == sender, Contact.is_active.in_([True]))))
    client_ids = {item.client_id for item in contacts}
    clients = list(db.scalars(select(Client).where(func.lower(Client.email) == sender, Client.is_active.in_([True]))))
    client_ids.update(item.id for item in clients)
    if len(client_ids) != 1:
        return SenderResolution("QUARANTINED", None, None, "Sender mapping is missing or ambiguous.")
    client_id = next(iter(client_ids)); client = db.get(Client, client_id)
    contact = next((item for item in contacts if item.client_id == client_id), None)
    return SenderResolution("RESOLVED", client, contact, "Sender mapped to one active client.")


def _message_id_from_resource(resource: str) -> str:
    return urllib.parse.unquote(resource.rstrip("/").rsplit("/", 1)[-1])


def ingest_graph_attachments(
    db: Session, graph: MicrosoftGraphClient, *, mailbox: str, graph_id: str,
    ticket_id: int, actor: User, configuration: OutlookConfigurationWrite,
    settings: Settings,
) -> int:
    from app.modules.tickets.models import Ticket

    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        return 0
    result = graph.request("GET", f"users/{urllib.parse.quote(mailbox, safe='')}/messages/{urllib.parse.quote(graph_id, safe='')}/attachments")
    saved = 0
    allowed = {value.casefold().lstrip(".") for value in configuration.allowed_attachment_extensions}
    for item in result.get("value", []):
        if not isinstance(item, dict) or item.get("@odata.type") != "#microsoft.graph.fileAttachment" or item.get("isInline") is True:
            continue
        name = str(item.get("name", "attachment")); extension = name.rsplit(".", 1)[-1].casefold() if "." in name else ""
        if extension not in allowed:
            raise AppError("ATTACHMENT_TYPE_NOT_ALLOWED", f"Email attachment {name} is not allowed.", 415)
        encoded = item.get("contentBytes")
        if not isinstance(encoded, str):
            continue
        try:
            content = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            raise AppError("ATTACHMENT_CONTENT_INVALID", f"Email attachment {name} is invalid.", 415) from exc
        save_attachment_bytes(
            db, ticket, actor, filename=name, content_type=str(item.get("contentType", "application/octet-stream")),
            content=content, settings=settings, maximum_bytes=configuration.attachment_max_bytes,
        ); saved += 1
    return saved


def process_notification(db: Session, notification: OutlookNotification, settings: Settings) -> OutlookMessage | None:
    configuration = load_configuration(db)
    graph_id = _message_id_from_resource(notification.resource)
    existing = db.scalar(select(OutlookMessage).where(OutlookMessage.graph_message_id == graph_id))
    if existing:
        notification.status = "DUPLICATE"; notification.processed_at = server_now(); db.commit()
        return existing
    mailbox = str(configuration.mailbox_address)
    graph = MicrosoftGraphClient(settings)
    message = graph.request("GET", f"users/{urllib.parse.quote(mailbox, safe='')}/messages/{urllib.parse.quote(graph_id, safe='')}?$select=id,internetMessageId,conversationId,subject,body,from,sender,receivedDateTime,internetMessageHeaders,hasAttachments")
    sender = sender_address(message); subject = normalize_subject(str(message.get("subject", "")))
    record = OutlookMessage(
        graph_message_id=graph_id, internet_message_id=str(message.get("internetMessageId")) if message.get("internetMessageId") else None,
        conversation_id=str(message.get("conversationId")) if message.get("conversationId") else None,
        sender_address=sender or "unknown", normalized_subject=subject, status="PROCESSING",
        payload_json=json.dumps(message, separators=(",", ":"), sort_keys=True),
    )
    db.add(record); db.flush()
    if is_automatic_or_loop(message, mailbox):
        record.status = "IGNORED_LOOP"; notification.status = "PROCESSED"; notification.processed_at = server_now(); db.commit(); return record
    resolution = resolve_sender(db, sender, configuration)
    if resolution.status != "RESOLVED" or not resolution.client:
        record.status = resolution.status; record.last_error = resolution.reason
        notification.status = "PROCESSED"; notification.processed_at = server_now(); db.commit(); return record
    record.client_id = resolution.client.id; record.contact_id = resolution.contact.id if resolution.contact else None
    db.commit()  # Durable idempotency claim before any ticket-side commit.
    actor = db.scalar(select(User).where(User.username_normalized == normalize(settings.integration_actor_username), User.is_active.in_([True])))
    if not actor:
        record.status = "FAILED"; record.last_error = "Configured integration actor does not exist."; db.commit(); return record
    conversation_ticket = db.scalar(select(OutlookMessage).where(OutlookMessage.conversation_id == record.conversation_id, OutlookMessage.ticket_id.is_not(None), OutlookMessage.id != record.id).order_by(OutlookMessage.received_at.desc())) if record.conversation_id else None
    body = plain_body(message) or "Email contained no readable message body."
    if conversation_ticket and conversation_ticket.ticket_id:
        comment = TicketComment(ticket_id=conversation_ticket.ticket_id, author_user_id=actor.id, is_internal=False, body=f"Email from {sender}:\n\n{body}")
        db.add(comment); db.flush(); record.ticket_id = conversation_ticket.ticket_id; record.comment_id = comment.id; record.status = "COMMENT_CREATED"
    else:
        ticket_type_id = configuration.default_ticket_type_id
        if ticket_type_id is None:
            ticket_type = db.scalar(select(TicketType).where(TicketType.code == "INCIDENT", TicketType.is_active.in_([True])))
            ticket_type_id = ticket_type.id if ticket_type else None
        if ticket_type_id is None:
            record.status = "QUARANTINED"; record.last_error = "No active default ticket type is configured."; db.commit(); return record
        try:
            ticket = create_ticket(db, TicketCreate(
                ticket_type_id=ticket_type_id, client_id=resolution.client.id,
                requester_contact_id=resolution.contact.id if resolution.contact else None,
                product_id=configuration.default_product_id, service_id=configuration.default_service_id,
                source_channel="EMAIL", impact=configuration.default_impact, urgency=configuration.default_urgency,
                creation_idempotency_key=f"outlook:{record.graph_message_id}",
                subject=subject, description=body,
            ), actor)
        except AppError as exc:
            policy = resolve_feature_policy(
                db, "entitlement_approvals", client_id=resolution.client.id,
                product_id=configuration.default_product_id,
                service_id=configuration.default_service_id,
            )
            if policy.mode in {"SHADOW", "ENFORCED"} and exc.code in {
                "TICKET_NOT_ENTITLED", "ENTITLEMENT_OVERRIDE_REQUIRED",
                "INVALID_TICKET_CONTRACT", "INACTIVE_CLIENT_CONFIRMATION_REQUIRED",
            }:
                approval = create_idempotent_approval(
                    db, idempotency_key=f"outlook-message:{record.graph_message_id}",
                    source_channel="EMAIL", reason_code=exc.code,
                    justification=f"Email ticket requires review: {exc.message}",
                    request_payload={
                        "ticket_type_id": ticket_type_id, "client_id": resolution.client.id,
                        "requester_contact_id": resolution.contact.id if resolution.contact else None,
                        "product_id": configuration.default_product_id,
                        "service_id": configuration.default_service_id,
                        "impact": configuration.default_impact, "urgency": configuration.default_urgency,
                        "subject": subject, "description": body, "source_channel": "EMAIL",
                    },
                    evidence={"graph_message_id": record.graph_message_id, "sender": sender, "error_code": exc.code, "error_message": exc.message},
                    feature_mode=policy.mode, policy_id=policy.policy_id,
                    policy_version=policy.policy_version, policy_scope=policy.source_scope_key,
                    client_id=resolution.client.id, contract_id=None, actor=actor,
                )
                record.status = "PENDING_APPROVAL"; record.last_error = f"Approval #{approval.id}: {exc.message}"
            else:
                record.status = "QUARANTINED"; record.last_error = f"{exc.code}: {exc.message}"
            db.commit(); return record
        record.ticket_id = ticket.id; record.status = "TICKET_CREATED"
        enqueue_ticket_email(db, ticket, "CREATED")
        if message.get("hasAttachments") is True:
            try:
                ingest_graph_attachments(
                    db, graph, mailbox=mailbox, graph_id=graph_id, ticket_id=ticket.id,
                    actor=actor, configuration=configuration, settings=settings,
                )
            except AppError as exc:
                record.last_error = f"Ticket created; attachment quarantined: {exc.code}: {exc.message}"
    notification.status = "PROCESSED"; notification.processed_at = server_now(); record.processed_at = server_now(); db.commit()
    return record
