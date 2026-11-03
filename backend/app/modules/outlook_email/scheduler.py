from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.core.config import Settings
from app.modules.configuration.policy_service import resolve_feature_policy
from app.modules.outlook_email.graph_client import GraphRequestError, MicrosoftGraphClient
from app.modules.outlook_email.models import (
    OutlookMessage,
    OutlookNotification,
    OutlookSubscription,
)
from app.modules.outlook_email.outbound import enqueue_ticket_email, process_outbound
from app.modules.outlook_email.processor import process_notification
from app.modules.tickets.models import Ticket

STATUS_EVENTS = {"IN_PROGRESS": "IN_PROGRESS", "PENDING": "PENDING", "RESOLVED": "RESOLVED", "CLOSED": "CLOSED", "REOPENED": "REOPENED"}


def run_outlook_cycle(
    db: Session, settings: Settings, ticket_limit: int = 500
) -> dict[str, int]:
    if resolve_feature_policy(db, "outlook_inbound_email").mode == "OFF":
        return {"processed": 0, "sent": 0, "renewed": 0, "ticket_candidates": 0}
    processed = 0
    for item in db.scalars(select(OutlookNotification).where(OutlookNotification.status == "PENDING").order_by(OutlookNotification.received_at).limit(25)):
        item.attempt_count += 1
        try:
            process_notification(db, item, settings); processed += 1
        except GraphRequestError as exc:
            item.last_error = str(exc); item.status = "DEAD_LETTER" if item.attempt_count >= 5 else "PENDING"; db.commit()
    # Historical Outlook messages grow without bound. Query only a bounded set
    # of the most recently changed linked tickets instead of materializing every
    # historical ticket id in Python on every scheduler pass.
    tickets = list(
        db.scalars(
            select(Ticket)
            .join(OutlookMessage, OutlookMessage.ticket_id == Ticket.id)
            .distinct()
            .order_by(Ticket.updated_at.desc(), Ticket.id.desc())
            .limit(ticket_limit)
        )
    )
    for ticket in tickets:
        event_key = STATUS_EVENTS.get(ticket.status.code)
        if event_key:
            enqueue_ticket_email(db, ticket, event_key)
    db.commit()
    sent = process_outbound(db, settings)["sent"]
    renewed = 0
    subscription = db.scalar(select(OutlookSubscription).where(OutlookSubscription.status == "ACTIVE").order_by(OutlookSubscription.expires_at.desc()))
    if subscription and subscription.expires_at <= server_now() + timedelta(hours=12):
        try:
            expiry = server_now() + timedelta(hours=70)
            result = MicrosoftGraphClient(settings).request("PATCH", f"subscriptions/{subscription.graph_subscription_id}", {"expirationDateTime": expiry.isoformat().replace("+00:00", "Z")})
            subscription.expires_at = datetime.fromisoformat(str(result.get("expirationDateTime", expiry.isoformat())).replace("Z", "+00:00")); subscription.last_error = None; renewed = 1
        except GraphRequestError as exc:
            subscription.status = "REAUTHORIZE_REQUIRED"; subscription.last_error = str(exc)
        db.commit()
    return {
        "processed": processed,
        "sent": sent,
        "renewed": renewed,
        "ticket_candidates": len(tickets),
    }
