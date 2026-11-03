from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.clients.models import Client, ClientStatus, Contact
from app.modules.outlook_email.models import OutlookNotification
from app.modules.outlook_email.processor import (
    is_automatic_or_loop,
    normalize_subject,
    resolve_sender,
)
from app.modules.outlook_email.routes import OutlookConfigurationWrite, queue_graph_notification


def test_graph_validation_challenge_is_returned_without_authentication(client: TestClient) -> None:
    response = client.get(
        "/api/v1/system/outlook-email/webhook",
        params={"validationToken": "graph-validation-token"},
    )
    assert response.status_code == 200
    assert response.text == "graph-validation-token"
    assert response.headers["content-type"].startswith("text/plain")


def test_graph_notification_queue_is_idempotent(database: Session) -> None:
    notification = {
        "subscriptionId": "subscription-1",
        "changeType": "created",
        "resource": "users/support/messages/message-7",
        "resourceData": {"id": "message-7"},
    }
    assert queue_graph_notification(database, notification) is True
    database.commit()
    assert queue_graph_notification(database, notification) is False
    database.commit()
    assert database.query(OutlookNotification).count() == 1


def test_outlook_configuration_supports_domain_and_sender_policies(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    payload = {
        "mailbox_address": "Support@millensys.com",
        "allowed_domains": ["alfascan.com", "customer.example"],
        "allowed_addresses": ["special@partner.example"],
        "blocked_senders": ["blocked@alfascan.com"],
        "unknown_sender_action": "QUARANTINE",
        "attachment_max_bytes": 8388608,
        "allowed_attachment_extensions": ["pdf", "png", "zip"],
    }
    saved = client.put(
        "/api/v1/system/outlook-email/configuration", json=payload, headers=admin_headers
    )
    assert saved.status_code == 200, saved.text
    loaded = client.get(
        "/api/v1/system/outlook-email/configuration", headers=admin_headers
    )
    assert loaded.status_code == 200
    assert loaded.json()["allowed_domains"] == ["alfascan.com", "customer.example"]
    assert "microsoft_graph_client_secret" not in loaded.json()


def test_sender_resolution_requires_one_unambiguous_active_client(database: Session) -> None:
    status = ClientStatus(code="EMAIL_ACTIVE", name="Email active", portal_allowed=True, ticket_creation_allowed=True, is_active=True)
    database.add(status); database.flush()
    first = Client(code="EMAIL_ONE", name="Email One", status_id=status.id, email="service@one.example", is_active=True)
    second = Client(code="EMAIL_TWO", name="Email Two", status_id=status.id, is_active=True)
    database.add_all([first, second]); database.flush()
    database.add(Contact(client_id=first.id, full_name="Known Sender", email="person@alfascan.com", is_active=True))
    database.commit()
    configuration = OutlookConfigurationWrite(allowed_domains=["alfascan.com"])
    resolved = resolve_sender(database, "person@alfascan.com", configuration)
    assert resolved.status == "RESOLVED"
    assert resolved.client and resolved.client.id == first.id
    blocked = resolve_sender(database, "blocked@alfascan.com", OutlookConfigurationWrite(allowed_domains=["alfascan.com"], blocked_senders=["blocked@alfascan.com"]))
    assert blocked.status == "BLOCKED"
    unknown = resolve_sender(database, "unknown@outside.example", configuration)
    assert unknown.status == "QUARANTINED"


def test_subject_normalization_and_loop_protection() -> None:
    assert normalize_subject("RE: Fwd:  Scanner unavailable") == "Scanner unavailable"
    automatic = {
        "from": {"emailAddress": {"address": "person@alfascan.com"}},
        "subject": "Automatic reply: annual leave",
    }
    assert is_automatic_or_loop(automatic, "Support@millensys.com") is True
    own_message = {"from": {"emailAddress": {"address": "support@millensys.com"}}}
    assert is_automatic_or_loop(own_message, "Support@millensys.com") is True
