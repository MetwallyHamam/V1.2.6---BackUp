import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.iam.models import User
from app.modules.notifications.models import EventOutbox, Notification, SmsDelivery
from app.modules.notifications.sms_service import process_sms_outbox


def add_sms_event(database: Session, with_phone: bool = True) -> EventOutbox:
    admin = database.scalar(select(User).where(User.username_normalized == "admin"))
    assert admin
    admin.phone_number = "+201000000000" if with_phone else None
    notification = Notification(
        recipient_user_id=admin.id,
        notification_type="SLA_ESCALATION",
        severity="CRITICAL",
        title="Critical SLA warning",
        message="A critical ticket needs attention.",
        deduplication_key="sla:30:rule:40:user:1",
    )
    item = EventOutbox(
        event_type="SLA_ESCALATED",
        aggregate_type="Ticket",
        aggregate_id="100",
        payload_json=json.dumps({"ticket_id": 100, "clock_id": 30, "rule_id": 40}),
    )
    database.add_all([admin, notification, item])
    database.commit()
    database.refresh(item)
    return item


def sms_settings() -> Settings:
    return Settings(
        app_env="test",
        secret_key="test-secret-key-with-more-than-thirty-two-characters",
        sms_enabled=True,
    )


def test_sms_delivery_sends_once(database: Session) -> None:
    item = add_sms_event(database)
    sent: list[tuple[str, str]] = []
    result = process_sms_outbox(
        database,
        sms_settings(),
        sender=lambda phone, message: sent.append((phone, message)) or "provider-123",
    )
    assert result["sent"] == 1
    assert len(sent) == 1
    delivery = database.scalar(select(SmsDelivery).where(SmsDelivery.outbox_id == item.id))
    assert delivery.status == "SENT"
    assert delivery.provider_message_id == "provider-123"
    assert process_sms_outbox(database, sms_settings(), sender=lambda *_: None)["sent"] == 0


def test_sms_delivery_skips_missing_phone(database: Session) -> None:
    item = add_sms_event(database, with_phone=False)
    result = process_sms_outbox(database, sms_settings(), sender=lambda *_: None)
    assert result["skipped"] == 1
    delivery = database.scalar(select(SmsDelivery).where(SmsDelivery.outbox_id == item.id))
    assert delivery.status == "SKIPPED"
