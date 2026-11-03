import json
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_now, server_timezone
from app.core.config import Settings
from app.modules.notifications.models import EventOutbox, TeamsDelivery
from app.modules.tickets.models import Ticket

TeamsSender = Callable[[dict[str, object]], None]


def webhook_sender(settings: Settings) -> TeamsSender:
    def send(card: dict[str, object]) -> None:
        if not settings.teams_webhook_url:
            raise OSError("Teams webhook URL is not configured.")
        request = urllib.request.Request(
            settings.teams_webhook_url,
            data=json.dumps(card).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20):  # noqa: S310
            return

    return send


def _card(item: EventOutbox, ticket: Ticket | None) -> dict[str, object]:
    payload = json.loads(item.payload_json)
    number = ticket.ticket_number if ticket else f"Ticket {item.aggregate_id}"
    subject = ticket.subject if ticket else "Support ticket escalation"
    threshold = payload.get("threshold", "unknown")
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.4",
                    "body": [
                        {"type": "TextBlock", "weight": "Bolder", "text": f"SLA escalation: {number}"},
                        {"type": "TextBlock", "wrap": True, "text": subject},
                        {"type": "TextBlock", "text": f"Threshold: {threshold}%"},
                    ],
                },
            }
        ],
    }


def process_teams_outbox(
    db: Session,
    settings: Settings,
    sender: TeamsSender | None = None,
    now: datetime | None = None,
    limit: int = 50,
) -> dict[str, int]:
    if not settings.teams_enabled and sender is None:
        return {"sent": 0, "retried": 0, "dead": 0}
    now = now or server_now()
    sender = sender or webhook_sender(settings)
    counts = {"sent": 0, "retried": 0, "dead": 0}
    items = list(
        db.scalars(
            select(EventOutbox)
            .where(EventOutbox.event_type == "SLA_ESCALATED")
            .order_by(EventOutbox.created_at)
            .limit(limit)
        )
    )
    for item in items:
        delivery = db.scalar(select(TeamsDelivery).where(TeamsDelivery.outbox_id == item.id))
        if delivery and delivery.status in {"SENT", "DEAD"}:
            continue
        if delivery and delivery.next_attempt_at:
            retry_at = delivery.next_attempt_at
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=server_timezone())
            if retry_at > now:
                continue
        delivery = delivery or TeamsDelivery(
            outbox_id=item.id, status="PENDING", attempt_count=0
        )
        delivery.attempt_count += 1
        try:
            sender(_card(item, db.get(Ticket, int(item.aggregate_id))))
            delivery.status = "SENT"
            delivery.sent_at = now
            delivery.last_error = None
            delivery.next_attempt_at = None
            counts["sent"] += 1
        except (OSError, urllib.error.URLError) as exc:
            delivery.last_error = str(exc)[:1000]
            if delivery.attempt_count >= settings.teams_max_attempts:
                delivery.status = "DEAD"
                counts["dead"] += 1
            else:
                delivery.status = "RETRY"
                delivery.next_attempt_at = now + timedelta(minutes=2 ** delivery.attempt_count)
                counts["retried"] += 1
        db.add(delivery)
    db.commit()
    return counts
