import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.configuration.models import SiteSetting
from app.modules.iam.models import User
from app.modules.notifications.email_service import process_email_outbox
from app.modules.notifications.models import EmailDelivery, EventOutbox, Notification
from app.modules.tickets.models import TicketType


def add_email_event(database: Session) -> EventOutbox:
    admin = database.scalar(select(User).where(User.username_normalized == "admin"))
    assert admin
    notification = Notification(
        recipient_user_id=admin.id,
        notification_type="SLA_ESCALATION",
        severity="WARNING",
        title="SLA warning",
        message="A ticket needs attention.",
        deep_link="/tickets/99",
        deduplication_key="sla:10:rule:20:user:1",
    )
    item = EventOutbox(
        event_type="SLA_ESCALATED",
        aggregate_type="Ticket",
        aggregate_id="99",
        payload_json=json.dumps({"ticket_id": 99, "clock_id": 10, "rule_id": 20}),
    )
    database.add_all([notification, item])
    database.commit()
    database.refresh(item)
    return item


def test_email_outbox_sends_once(database: Session) -> None:
    item = add_email_event(database)
    sent: list[tuple[str, str, str]] = []
    settings = Settings(
        app_env="test",
        secret_key="test-secret-key-with-more-than-thirty-two-characters",
        smtp_enabled=True,
        frontend_origin="https://millensysonline.net",
        application_path_base="/SupportHub/backend",
    )
    result = process_email_outbox(
        database,
        settings,
        sender=lambda recipient, subject, body: sent.append((recipient, subject, body)),
    )
    assert result["sent"] == 1
    assert len(sent) == 1
    assert "https://millensysonline.net/SupportHub/tickets/99" in sent[0][2]
    assert database.get(EventOutbox, item.id).status == "SENT"
    assert database.scalar(select(EmailDelivery).where(EmailDelivery.outbox_id == item.id)).status == "SENT"

    repeated = process_email_outbox(database, settings, sender=lambda *_: None)
    assert repeated["sent"] == 0


def test_email_outbox_dead_letters_after_max_attempts(database: Session) -> None:
    item = add_email_event(database)
    settings = Settings(
        app_env="test",
        secret_key="test-secret-key-with-more-than-thirty-two-characters",
        smtp_enabled=True,
        email_max_attempts=1,
    )

    def fail(_: str, __: str, ___: str) -> None:
        raise OSError("SMTP unavailable")

    result = process_email_outbox(database, settings, sender=fail)
    assert result["dead"] == 1
    assert database.get(EventOutbox, item.id).status == "DEAD"
    delivery = database.scalar(select(EmailDelivery).where(EmailDelivery.outbox_id == item.id))
    assert delivery.status == "DEAD"
    assert delivery.last_error == "SMTP unavailable"


def test_queued_sla_warning_email_is_skipped_after_delivery_is_disabled(
    database: Session,
) -> None:
    item = EventOutbox(
        event_type="SLA_WARNING",
        aggregate_type="Ticket",
        aggregate_id="99",
        deduplication_key="sla-warning:99:response:10:email",
        payload_json=json.dumps({
            "ticket_id": 99,
            "clock_id": 10,
            "recipient_emails": ["alerts@example.com"],
            "subject": "SLA warning",
            "body": "A ticket needs attention.",
            "deep_link": "/tickets/99",
        }),
    )
    database.add_all([item, SiteSetting(key="sla_warning_enabled", value="false")])
    database.commit()
    sent: list[tuple[str, str, str]] = []

    result = process_email_outbox(
        database,
        Settings(
            app_env="test",
            secret_key="test-secret-key-with-more-than-thirty-two-characters",
            smtp_enabled=True,
        ),
        sender=lambda recipient, subject, body: sent.append((recipient, subject, body)),
    )

    assert result["skipped"] >= 1
    assert sent == []
    assert database.get(EventOutbox, item.id).status == "SKIPPED"
    assert database.scalar(
        select(EmailDelivery).where(EmailDelivery.outbox_id == item.id)
    ) is None


def test_queued_sla_escalation_email_is_skipped_when_sla_email_delivery_is_disabled(
    database: Session,
) -> None:
    item = add_email_event(database)
    database.add(SiteSetting(key="sla_warning_enabled", value="false"))
    database.commit()
    sent: list[tuple[str, str, str]] = []

    result = process_email_outbox(
        database,
        Settings(
            app_env="test",
            secret_key="test-secret-key-with-more-than-thirty-two-characters",
            smtp_enabled=True,
        ),
        sender=lambda recipient, subject, body: sent.append((recipient, subject, body)),
    )

    assert result["skipped"] == 1
    assert sent == []
    assert database.get(EventOutbox, item.id).status == "SKIPPED"
    assert database.scalar(
        select(EmailDelivery).where(EmailDelivery.outbox_id == item.id)
    ) is None


def test_queued_ticket_email_is_skipped_when_recipient_loses_access(
    client, admin_headers: dict[str, str], database: Session
) -> None:
    from app.tests.test_tickets import create_test_client

    admin = database.scalar(select(User).where(User.username_normalized == "admin"))
    assert admin is not None
    ticket = client.post("/api/v1/tickets", headers=admin_headers, json={
        "client_id": create_test_client(client, admin_headers, database),
        "ticket_type_id": database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT")),
        "subject": "Delayed recipient revocation", "description": "Do not send after revocation.",
        "impact": "LOW", "urgency": "LOW",
    })
    assert ticket.status_code == 201, ticket.text
    item = EventOutbox(
        event_type="TICKET_CREATION_EMAIL", aggregate_type="Ticket",
        aggregate_id=str(ticket.json()["id"]), deduplication_key="delivery-revocation-test",
        payload_json=json.dumps({
            "to": [admin.email], "cc": [], "subject": "Ticket notice",
            "body": "Ticket reference only.", "deep_link": f"/tickets/{ticket.json()['id']}",
        }),
    )
    database.add(item)
    admin.is_active = False
    database.commit()
    sent: list[tuple[str, str, str]] = []
    result = process_email_outbox(
        database,
        Settings(app_env="test", secret_key="test-secret-key-with-more-than-thirty-two-characters", smtp_enabled=True),
        sender=lambda recipient, subject, body: sent.append((recipient, subject, body)),
    )
    assert result["skipped"] >= 1
    assert sent == []
    assert database.get(EventOutbox, item.id).status == "SKIPPED"


def test_password_reset_email_targets_registered_user_email(database: Session) -> None:
    admin = database.scalar(select(User).where(User.username_normalized == "admin"))
    assert admin is not None
    item = EventOutbox(
        event_type="PASSWORD_RESET_EMAIL",
        aggregate_type="User",
        aggregate_id=str(admin.id),
        deduplication_key="password-reset:test-delivery",
        payload_json=json.dumps({
            "user_id": admin.id,
            "subject": "Millensys Support Hub password reset",
            "body": f"Username: {admin.username}\n\nUse this secure one-time link: https://example.test/reset-password?token=secret",
        }),
    )
    database.add(item)
    database.commit()
    sent: list[tuple[str, str, str]] = []
    result = process_email_outbox(
        database,
        Settings(app_env="test", secret_key="test-secret-key-with-more-than-thirty-two-characters", smtp_enabled=True),
        sender=lambda recipient, subject, body: sent.append((recipient, subject, body)),
    )
    assert result["sent"] == 1
    assert sent[0][0] == admin.email
    assert f"Username: {admin.username}" in sent[0][2]
