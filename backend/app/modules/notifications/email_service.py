import json
import smtplib
from collections.abc import Callable
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import formataddr
from types import SimpleNamespace

from sqlalchemy import or_, select, text, update
from sqlalchemy.orm import Session

from app.core.clock import server_now, server_timezone
from app.core.config import Settings
from app.modules.configuration.models import SiteSetting
from app.modules.contracts.models import ContractExpirationNotificationDelivery
from app.modules.iam.models import User
from app.modules.notifications.email_template import branded_email_html, frontend_url
from app.modules.notifications.models import EmailDelivery, EventOutbox, Notification
from app.modules.notifications.ticket_creation import authorized_ticket_addresses
from app.modules.tickets.models import Ticket

EmailSender = Callable[[str, str, str], None]
GroupEmailSender = Callable[[list[str], list[str], str, str], None]


EmailRecipient = User | SimpleNamespace


def _sla_email_delivery_enabled(db: Session) -> bool:
    row = db.get(SiteSetting, "sla_warning_enabled")
    return row is None or row.value.strip().lower() == "true"


def smtp_sender(settings: Settings) -> EmailSender:
    def send(recipient: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = formataddr((settings.smtp_from_name, settings.smtp_from_address))
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        message.add_alternative(branded_email_html(subject, body), subtype="html")
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password or "")
            smtp.send_message(message)

    return send


def smtp_group_sender(settings: Settings) -> GroupEmailSender:
    def send(to: list[str], cc: list[str], subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = formataddr((settings.smtp_from_name, settings.smtp_from_address))
        message["To"] = ", ".join(to)
        if cc:
            message["Cc"] = ", ".join(cc)
        message["Subject"] = subject
        message.set_content(body)
        message.add_alternative(branded_email_html(subject, body), subtype="html")
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password or "")
            smtp.send_message(message)

    return send


def _recipients(db: Session, item: EventOutbox) -> list[tuple[EmailRecipient, Notification]]:
    if item.event_type == "WORK_ASSIGNMENT_EMAIL":
        payload = json.loads(item.payload_json)
        users = list(db.scalars(select(User).where(User.id.in_(payload["recipient_user_ids"]), User.is_active.in_([True]))))
        return [
            (
                SimpleNamespace(id=user.id, email=user.support_notification_email or user.email),
                Notification(
                    recipient_user_id=user.id,
                    notification_type="WORK_ASSIGNMENT",
                    severity="INFO",
                    title=str(payload["subject"]),
                    message=str(payload["body"]),
                    deep_link=str(payload["deep_link"]),
                    deduplication_key=f"{item.deduplication_key}:user:{user.id}",
                ),
            )
            for user in users
            if user.support_notification_email or user.email
        ]
    if item.event_type == "TICKET_MENTION_EMAIL":
        payload = json.loads(item.payload_json)
        users = list(
            db.scalars(
                select(User).where(
                    User.id.in_(payload["recipient_user_ids"]), User.is_active.in_([True])
                )
            )
        )
        return [
            (
                user,
                Notification(
                    recipient_user_id=user.id,
                    notification_type="TICKET_MENTION",
                    severity="INFO",
                    title=str(payload["subject"]),
                    message=str(payload["body"]),
                    deep_link=str(payload["deep_link"]),
                    deduplication_key=f"{item.deduplication_key}:user:{user.id}",
                ),
            )
            for user in users
        ]
    if item.event_type in {"TICKET_CREATION_EMAIL", "KPI_BATCH_SUBMITTED", "CHECKLIST_REMINDER_EMAIL", "CONTRACT_EXPIRATION_EMAIL"}:
        payload = json.loads(item.payload_json)
        addresses = list(dict.fromkeys([*payload.get("to", []), *payload.get("cc", [])]))
        if item.event_type == "TICKET_CREATION_EMAIL":
            ticket = db.get(Ticket, int(item.aggregate_id))
            if not ticket:
                return []
            # Delivery can occur long after enqueueing; apply the current access
            # policy again so a revoked recipient never receives a delayed email.
            addresses = authorized_ticket_addresses(db, ticket, addresses)
        notification_type = "CHECKLIST_REMINDER" if item.event_type == "CHECKLIST_REMINDER_EMAIL" else ("KPI_BATCH_SUBMITTED" if item.event_type == "KPI_BATCH_SUBMITTED" else ("CONTRACT_RENEWAL" if item.event_type == "CONTRACT_EXPIRATION_EMAIL" else "TICKET_CREATED"))
        return [
            (
                SimpleNamespace(id=None, email=address),
                Notification(
                    recipient_user_id=0,
                    notification_type=notification_type,
                    severity="INFO",
                    title=str(payload["subject"]),
                    message=str(payload["body"]),
                    deep_link=str(payload["deep_link"]),
                    deduplication_key=f"{item.deduplication_key}:{address}",
                ),
            )
            for address in addresses
        ]
    if item.event_type in {"SATISFACTION_INVITATION", "TICKET_LIVE_UPDATE"}:
        payload = json.loads(item.payload_json)
        recipient = SimpleNamespace(id=None, email=str(payload["recipient_email"]))
        notification = Notification(
            recipient_user_id=0,
            notification_type="SATISFACTION"
            if item.event_type == "SATISFACTION_INVITATION"
            else "TICKET_LIVE_UPDATE",
            severity="INFO",
            title=str(payload["subject"]),
            message=str(payload["body"]),
            deduplication_key=str(item.deduplication_key),
        )
        return [(recipient, notification)]
    if item.event_type == "PASSWORD_RESET_EMAIL":
        payload = json.loads(item.payload_json)
        expires_at = payload.get("expires_at")
        if (
            expires_at
            and datetime.fromisoformat(str(expires_at)).astimezone(server_timezone())
            <= server_now()
        ):
            return []
        user = db.get(User, int(payload["user_id"]))
        if not user or not user.is_active:
            return []
        return [
            (
                user,
                Notification(
                    recipient_user_id=user.id,
                    notification_type="PASSWORD_RESET",
                    severity="INFO",
                    title=str(payload["subject"]),
                    message=str(payload["body"]),
                    deep_link=None,
                    deduplication_key=str(item.deduplication_key or f"password-reset:{item.id}"),
                ),
            )
        ]
    if item.event_type not in {"SLA_WARNING", "SLA_ESCALATED"}:
        return []
    payload = json.loads(item.payload_json)
    if item.event_type == "SLA_WARNING" and "recipient_emails" in payload:
        return [
            (
                SimpleNamespace(id=None, email=str(address)),
                Notification(
                    recipient_user_id=0,
                    notification_type="SLA_WARNING",
                    severity="WARNING",
                    title=str(payload["subject"]),
                    message=str(payload["body"]),
                    deep_link=str(payload.get("deep_link") or "/tickets"),
                    deduplication_key=f"{item.deduplication_key}:{address}",
                ),
            )
            for address in payload["recipient_emails"]
        ]
    prefix = (
        f"sla-warning:{payload['clock_id']}:{payload['warning_percent']}:user:"
        if item.event_type == "SLA_WARNING"
        else f"sla:{payload['clock_id']}:rule:{payload['rule_id']}:user:"
    )
    statement = (
        select(User, Notification)
        .join(Notification, Notification.recipient_user_id == User.id)
        .where(Notification.deduplication_key.like(f"{prefix}%"), User.is_active.in_([True]))
    )
    return list(db.execute(statement).tuples())


def _sync_contract_expiration_delivery(
    db: Session, item: EventOutbox, status: str, now: datetime, error: str | None = None
) -> None:
    if item.event_type != "CONTRACT_EXPIRATION_EMAIL":
        return
    delivery = db.scalar(
        select(ContractExpirationNotificationDelivery).where(
            ContractExpirationNotificationDelivery.outbox_id == item.id
        )
    )
    if not delivery:
        return
    delivery.status = status
    delivery.last_error = error[:1000] if error else None
    delivery.updated_at = now
    if status == "SENT":
        delivery.sent_at = now
        delivery.failed_at = None
    elif status in {"FAILED", "SKIPPED"}:
        delivery.failed_at = now


def process_email_outbox(
    db: Session,
    settings: Settings,
    sender: EmailSender | None = None,
    group_sender: GroupEmailSender | None = None,
    now: datetime | None = None,
    limit: int = 50,
) -> dict[str, int]:
    if not settings.smtp_enabled and sender is None:
        return {"sent": 0, "retried": 0, "dead": 0, "skipped": 0}
    # SET options belong to the physical SQL Server connection and survive
    # transaction commit/pool check-in. A connection previously used by a
    # NOCOUNT batch can therefore make pymssql report rowcount=-1; SQLAlchemy
    # treats that as a stale ORM update and strands the claimed email before
    # SMTP. Normalize the actual connection used by every processing entry
    # point (scheduler and manual) before selecting or claiming work.
    if db.bind is not None and db.bind.dialect.name == "mssql":
        db.execute(text("SET NOCOUNT OFF;"))
    now = now or server_now()
    sender_was_injected = sender is not None
    sender = sender or smtp_sender(settings)
    group_sender = group_sender or (
        (lambda to, _cc, subject, body: sender(to[0], subject, body))
        if sender_was_injected
        else smtp_group_sender(settings)
    )
    counts = {"sent": 0, "retried": 0, "dead": 0, "skipped": 0}
    items = list(
        db.scalars(
            select(EventOutbox)
            .where(
                EventOutbox.status.in_(["PENDING", "RETRY"]),
                or_(EventOutbox.next_attempt_at.is_(None), EventOutbox.next_attempt_at <= now),
            )
            .order_by(EventOutbox.created_at)
            .limit(limit)
        )
    )
    for item in items:
        # SQL Server NOCOUNT and driver behavior can report rowcount=-1 even
        # after a successful UPDATE. OUTPUT/RETURNING identifies ownership
        # without abandoning a successfully claimed job in PROCESSING.
        claimed_id = db.execute(
                update(EventOutbox)
                .where(EventOutbox.id == item.id, EventOutbox.status.in_(["PENDING", "RETRY"]))
                .values(status="PROCESSING")
                .returning(EventOutbox.id)
            ).scalar_one_or_none()
        db.commit()
        if claimed_id is None:
            continue
        if item.event_type == "CONTRACT_EXPIRATION_EMAIL" and item.deduplication_key:
            canonical_id = db.scalar(
                select(EventOutbox.id)
                .where(
                    EventOutbox.event_type == "CONTRACT_EXPIRATION_EMAIL",
                    EventOutbox.deduplication_key == item.deduplication_key,
                )
                .order_by(EventOutbox.id)
                .limit(1)
            )
            if canonical_id != item.id:
                item.status = "SENT"
                item.next_attempt_at = None
                _sync_contract_expiration_delivery(
                    db, item, "SENT", now, "Duplicate outbox event suppressed."
                )
                counts["skipped"] += 1
                db.commit()
                continue
        # Recheck the operational switch after claiming. This prevents warning
        # messages queued before an administrator disabled delivery from leaking
        # through a later scheduler run.
        if item.event_type in {"SLA_WARNING", "SLA_ESCALATED"} and not _sla_email_delivery_enabled(
            db
        ):
            item.status = "SKIPPED"
            item.next_attempt_at = None
            counts["skipped"] += 1
            db.commit()
            continue
        recipients = _recipients(db, item)
        if not recipients:
            item.status = "SKIPPED"
            _sync_contract_expiration_delivery(
                db, item, "SKIPPED", now, "No eligible email recipients."
            )
            counts["skipped"] += 1
            continue
        if item.event_type == "CONTRACT_EXPIRATION_EMAIL":
            payload = json.loads(item.payload_json)
            to_addresses = list(dict.fromkeys(str(value) for value in payload.get("to", [])))
            cc_addresses = [
                address
                for address in dict.fromkeys(str(value) for value in payload.get("cc", []))
                if address not in to_addresses
            ]
            addresses = [*to_addresses, *cc_addresses]
            deliveries: list[EmailDelivery] = []
            for address in addresses:
                group_delivery = db.scalar(select(EmailDelivery).where(
                    EmailDelivery.outbox_id == item.id,
                    EmailDelivery.recipient_email == address,
                )) or EmailDelivery(
                    outbox_id=item.id,
                    recipient_user_id=None,
                    recipient_email=address,
                    subject=str(payload["subject"]),
                    status="PENDING",
                    attempt_count=0,
                )
                deliveries.append(group_delivery)
            if deliveries and all(row.status == "SENT" for row in deliveries):
                item.status = "SENT"
                item.next_attempt_at = None
                _sync_contract_expiration_delivery(db, item, "SENT", now)
                continue
            for row in deliveries:
                row.attempt_count += 1
                row.status = "PROCESSING"
                db.add(row)
            item.attempt_count += 1
            _sync_contract_expiration_delivery(db, item, "PROCESSING", now)
            # Persist the attempt before the irreversible SMTP operation.
            db.commit()
            link = frontend_url(settings.frontend_base_url, str(payload.get("deep_link") or "/contracts"))
            body = f"{payload['body']}\n\nOpen the contract workspace:\n{link}"
            try:
                group_sender(to_addresses, cc_addresses, str(payload["subject"]), body)
                for row in deliveries:
                    row.status = "SENT"
                    row.sent_at = now
                    row.last_error = None
                    row.next_attempt_at = None
                    db.add(row)
                item.status = "SENT"
                item.next_attempt_at = None
                counts["sent"] += 1
                _sync_contract_expiration_delivery(db, item, "SENT", now)
            except (OSError, smtplib.SMTPException) as exc:
                error = str(exc)[:1000]
                # A disconnect/timeout may happen AFTER the server accepted
                # DATA. Retrying automatically risks duplicate mail. Explicit
                # SMTP rejection is safe to retry; uncertain outcomes need review.
                uncertain = not isinstance(
                    exc, (smtplib.SMTPResponseException, smtplib.SMTPRecipientsRefused)
                )
                dead = all(
                    row.attempt_count >= settings.email_max_attempts
                    for row in deliveries
                )
                for row in deliveries:
                    row.status = "UNKNOWN" if uncertain else ("DEAD" if dead else "RETRY")
                    row.last_error = error
                    row.next_attempt_at = None if dead or uncertain else now + timedelta(minutes=2**row.attempt_count)
                    db.add(row)
                item.status = "UNKNOWN" if uncertain else ("DEAD" if dead else "RETRY")
                item.next_attempt_at = None if dead or uncertain else now + timedelta(minutes=2**item.attempt_count)
                counts["dead" if dead or uncertain else "retried"] += 1
                _sync_contract_expiration_delivery(
                    db, item, "UNKNOWN" if uncertain else ("FAILED" if dead else "RETRY"), now, error
                )
            db.commit()
            continue
        all_sent = True
        any_retry = False
        for user, notification in recipients:
            delivery = db.scalar(
                select(EmailDelivery).where(
                    EmailDelivery.outbox_id == item.id,
                    EmailDelivery.recipient_email == user.email,
                )
            )
            if delivery and delivery.status == "SENT":
                continue
            delivery = delivery or EmailDelivery(
                outbox_id=item.id,
                recipient_user_id=user.id,
                recipient_email=user.email,
                subject=notification.title,
                status="PENDING",
                attempt_count=0,
            )
            delivery.attempt_count += 1
            try:
                link = frontend_url(settings.frontend_base_url, notification.deep_link)
                if item.event_type in {
                    "PASSWORD_RESET_EMAIL",
                    "SATISFACTION_INVITATION",
                    "TICKET_LIVE_UPDATE",
                }:
                    body = notification.message
                elif item.event_type == "KPI_BATCH_SUBMITTED":
                    body = f"{notification.message}\n\nOpen the KPI workspace:\n{link}"
                elif item.event_type == "CONTRACT_EXPIRATION_EMAIL":
                    body = f"{notification.message}\n\nOpen the contract workspace:\n{link}"
                elif item.event_type == "WORK_ASSIGNMENT_EMAIL":
                    body = f"{notification.message}\n\nOpen the assigned task:\n{link}"
                else:
                    body = f"{notification.message}\n\nOpen the relevant tickets:\n{link}"
                sender(user.email, notification.title, body)
                delivery.status = "SENT"
                delivery.sent_at = now
                delivery.last_error = None
                delivery.next_attempt_at = None
                counts["sent"] += 1
            except (OSError, smtplib.SMTPException) as exc:
                all_sent = False
                delivery.last_error = str(exc)[:1000]
                if delivery.attempt_count >= settings.email_max_attempts:
                    delivery.status = "DEAD"
                    counts["dead"] += 1
                else:
                    delivery.status = "RETRY"
                    delivery.next_attempt_at = now + timedelta(minutes=2**delivery.attempt_count)
                    any_retry = True
                    counts["retried"] += 1
            db.add(delivery)
        item.attempt_count += 1
        item.status = "SENT" if all_sent else ("RETRY" if any_retry else "DEAD")
        item.next_attempt_at = now + timedelta(minutes=2**item.attempt_count) if any_retry else None
        errors = "; ".join(
            value
            for value in db.scalars(
                select(EmailDelivery.last_error).where(
                    EmailDelivery.outbox_id == item.id,
                    EmailDelivery.last_error.is_not(None),
                )
            )
            if value
        )
        _sync_contract_expiration_delivery(
            db,
            item,
            "SENT" if item.status == "SENT" else ("RETRY" if item.status == "RETRY" else "FAILED"),
            now,
            errors or None,
        )
    db.commit()
    return counts
