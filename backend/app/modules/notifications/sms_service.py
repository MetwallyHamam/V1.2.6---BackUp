import json
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_now, server_timezone
from app.core.config import Settings
from app.modules.iam.models import User
from app.modules.notifications.models import EventOutbox, Notification, SmsDelivery

SmsSender = Callable[[str, str], str | None]


def gateway_sender(settings: Settings) -> SmsSender:
    def send(phone_number: str, message: str) -> str | None:
        body = json.dumps(
            {"to": phone_number, "message": message, "sender_id": settings.sms_sender_id}
        ).encode()
        headers = {"Content-Type": "application/json"}
        if settings.sms_api_token:
            headers["Authorization"] = f"Bearer {settings.sms_api_token}"
        request = urllib.request.Request(
            settings.sms_gateway_url, data=body, headers=headers, method="POST"
        )
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
            payload = json.loads(response.read().decode() or "{}")
            return str(payload.get("message_id")) if payload.get("message_id") else None

    return send


def _recipients(db: Session, item: EventOutbox) -> list[tuple[User, Notification]]:
    if item.event_type != "SLA_ESCALATED":
        return []
    payload = json.loads(item.payload_json)
    prefix = f"sla:{payload['clock_id']}:rule:{payload['rule_id']}:user:"
    return list(
        db.execute(
            select(User, Notification)
            .join(Notification, Notification.recipient_user_id == User.id)
            .where(Notification.deduplication_key.like(f"{prefix}%"), User.is_active.in_([True]))
        ).tuples()
    )


def process_sms_outbox(
    db: Session,
    settings: Settings,
    sender: SmsSender | None = None,
    now: datetime | None = None,
    limit: int = 50,
) -> dict[str, int]:
    if not settings.sms_enabled and sender is None:
        return {"sent": 0, "retried": 0, "dead": 0, "skipped": 0}
    now = now or server_now()
    sender = sender or gateway_sender(settings)
    counts = {"sent": 0, "retried": 0, "dead": 0, "skipped": 0}
    items = list(
        db.scalars(
            select(EventOutbox)
            .where(EventOutbox.event_type == "SLA_ESCALATED")
            .order_by(EventOutbox.created_at)
            .limit(limit)
        )
    )
    for item in items:
        for user, notification in _recipients(db, item):
            delivery = db.scalar(
                select(SmsDelivery).where(
                    SmsDelivery.outbox_id == item.id,
                    SmsDelivery.recipient_user_id == user.id,
                )
            )
            if delivery and delivery.status in {"SENT", "SKIPPED", "DEAD"}:
                continue
            if delivery and delivery.next_attempt_at:
                retry_at = delivery.next_attempt_at
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=server_timezone())
                if retry_at > now:
                    continue
            delivery = delivery or SmsDelivery(
                outbox_id=item.id,
                recipient_user_id=user.id,
                phone_number=user.phone_number,
                status="PENDING",
                attempt_count=0,
            )
            if not user.phone_number:
                delivery.status = "SKIPPED"
                delivery.last_error = "Recipient has no phone number."
                counts["skipped"] += 1
                db.add(delivery)
                continue
            delivery.attempt_count += 1
            try:
                delivery.provider_message_id = sender(
                    user.phone_number, f"{notification.title}: {notification.message}"
                )
                delivery.status = "SENT"
                delivery.sent_at = now
                delivery.last_error = None
                delivery.next_attempt_at = None
                counts["sent"] += 1
            except (OSError, urllib.error.URLError) as exc:
                delivery.last_error = str(exc)[:1000]
                if delivery.attempt_count >= settings.sms_max_attempts:
                    delivery.status = "DEAD"
                    counts["dead"] += 1
                else:
                    delivery.status = "RETRY"
                    delivery.next_attempt_at = now + timedelta(minutes=2 ** delivery.attempt_count)
                    counts["retried"] += 1
            db.add(delivery)
    db.commit()
    return counts
