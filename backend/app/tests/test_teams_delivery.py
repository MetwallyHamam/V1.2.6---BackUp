import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.notifications.models import EventOutbox, TeamsDelivery
from app.modules.notifications.teams_service import process_teams_outbox


def teams_settings(max_attempts: int = 5) -> Settings:
    return Settings(
        app_env="test",
        secret_key="test-secret-key-with-more-than-thirty-two-characters",
        teams_enabled=True,
        teams_webhook_url="https://example.invalid/webhook",
        teams_max_attempts=max_attempts,
    )


def add_event(database: Session) -> EventOutbox:
    item = EventOutbox(
        event_type="SLA_ESCALATED",
        aggregate_type="Ticket",
        aggregate_id="999",
        payload_json=json.dumps(
            {"ticket_id": 999, "clock_id": 50, "rule_id": 60, "threshold": 80}
        ),
    )
    database.add(item)
    database.commit()
    database.refresh(item)
    return item


def test_teams_delivery_sends_adaptive_card_once(database: Session) -> None:
    item = add_event(database)
    cards: list[dict[str, object]] = []
    result = process_teams_outbox(database, teams_settings(), sender=cards.append)
    assert result["sent"] == 1
    assert len(cards) == 1
    assert cards[0]["type"] == "message"
    delivery = database.scalar(
        select(TeamsDelivery).where(TeamsDelivery.outbox_id == item.id)
    )
    assert delivery.status == "SENT"
    assert process_teams_outbox(database, teams_settings(), sender=cards.append)["sent"] == 0
    assert len(cards) == 1


def test_teams_delivery_dead_letters(database: Session) -> None:
    item = add_event(database)

    def fail(_: dict[str, object]) -> None:
        raise OSError("Webhook unavailable")

    result = process_teams_outbox(database, teams_settings(max_attempts=1), sender=fail)
    assert result["dead"] == 1
    delivery = database.scalar(
        select(TeamsDelivery).where(TeamsDelivery.outbox_id == item.id)
    )
    assert delivery.status == "DEAD"
    assert delivery.last_error == "Webhook unavailable"
