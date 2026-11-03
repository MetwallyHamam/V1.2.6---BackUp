import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import SupportTeam, SupportTeamMember
from app.modules.iam.models import (
    AuditLog,
    Department,
    User,
    UserClientScope,
    UserPermissionOverride,
)
from app.modules.notifications.models import TicketNotificationRule
from app.modules.notifications.ticket_creation import (
    authorized_ticket_addresses,
    normalized_addresses,
    queue_ticket_reassignment_email,
)
from app.modules.tickets.models import TicketFollower, TicketType


@pytest.mark.parametrize("portal_source", ["CLIENT_PORTAL", "MOSAIC"])
def test_creation_email_filters_non_visible_and_unknown_recipients(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
    portal_source: str,
) -> None:
    from app.modules.configuration.models import SiteSetting
    from app.modules.iam.models import User
    from app.modules.notifications.models import EventOutbox, Notification
    from app.modules.notifications.ticket_creation import queue_ticket_creation_email
    from app.modules.tickets.models import Ticket, TicketType
    from app.tests.test_tickets import create_test_client

    outsider = User(full_name="Unrelated employee", username="outsider",
                    username_normalized="outsider", email="outsider@example.com",
                    email_normalized="outsider@example.com", password_hash="unused",
                    user_type="EMPLOYEE", is_active=True)
    database.add(outsider)
    database.commit()
    client_id = create_test_client(client, admin_headers, database)
    response = client.post("/api/v1/tickets", headers=admin_headers, json={
        "client_id": client_id,
        "ticket_type_id": database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT")),
        "subject": "Confidential client issue", "description": "Private diagnostic details",
        "impact": "LOW", "urgency": "LOW",
    })
    assert response.status_code == 201, response.text
    ticket = database.get(Ticket, response.json()["id"])
    assert ticket is not None
    assert database.scalar(select(Notification.id).where(Notification.recipient_user_id == outsider.id)) is None
    actor = database.scalar(select(User).where(User.username == "admin"))
    assert actor is not None
    for key, value in {
        "portal_ticket_email_enabled": "true",
        "portal_ticket_email_to": "outsider@example.com,unknown@example.com,ADMIN@example.com",
        "portal_ticket_email_cc": "outsider@example.com,unknown-cc@example.com",
    }.items():
        row = database.get(SiteSetting, key)
        if row:
            row.value = value
        else:
            database.add(SiteSetting(key=key, value=value))
    ticket.source_channel = portal_source
    database.flush()
    queue_ticket_creation_email(database, ticket, actor)
    database.flush()
    event = database.scalar(select(EventOutbox).where(EventOutbox.event_type == "TICKET_CREATION_EMAIL"))
    assert event is not None
    payload = json.loads(event.payload_json)
    assert payload["to"] == ["admin@example.com"]
    assert payload["cc"] == []
    assert ticket.subject not in payload["body"]
    assert ticket.description not in payload["body"]


def test_workflow_transition_outbox_and_notices_are_visibility_scoped(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    from app.modules.iam.models import User
    from app.modules.notifications.models import EventOutbox, Notification
    from app.modules.tickets.models import Ticket
    from app.tests.test_tickets import create_test_client

    outsider = User(full_name="Non-visible follower", username="nonvisible.follower",
                    username_normalized="nonvisible.follower", email="nonvisible@example.com",
                    email_normalized="nonvisible@example.com", password_hash="unused",
                    user_type="EMPLOYEE", is_active=True)
    database.add(outsider)
    database.commit()
    response = client.post("/api/v1/tickets", headers=admin_headers, json={
        "client_id": create_test_client(client, admin_headers, database),
        "ticket_type_id": database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT")),
        "subject": "Workflow confidentiality", "description": "Only visible users may be notified.",
        "impact": "LOW", "urgency": "LOW",
    })
    assert response.status_code == 201, response.text
    ticket = database.get(Ticket, response.json()["id"])
    assert ticket is not None
    database.add(TicketFollower(ticket_id=ticket.id, user_id=outsider.id, added_by_user_id=1))
    database.commit()
    transitioned = client.post(f"/api/v1/tickets/{ticket.id}/transition", headers=admin_headers, json={
        "to_status_code": "IN_PROGRESS", "version": ticket.version,
    })
    assert transitioned.status_code == 200, transitioned.text
    events = list(database.scalars(select(EventOutbox).where(
        EventOutbox.aggregate_id == str(ticket.id),
        EventOutbox.event_type == "TICKET_WORKFLOW_TRANSITION",
    )))
    assert len(events) == 1
    payload = json.loads(events[0].payload_json)
    assert payload["from_status_code"] == "ASSIGNED"
    assert payload["to_status_code"] == "IN_PROGRESS"
    assert "subject" not in payload
    assert database.scalar(select(Notification.id).where(
        Notification.recipient_user_id == outsider.id,
        Notification.notification_type == "TICKET_WORKFLOW_TRANSITION",
    )) is None


def test_reassignment_email_filters_unknown_and_non_visible_rule_addresses(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    from app.modules.iam.models import User
    from app.modules.notifications.models import EventOutbox, TicketNotificationRule
    from app.modules.tickets.models import Ticket
    from app.tests.test_tickets import create_test_client

    admin = database.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    created = client.post("/api/v1/tickets", headers=admin_headers, json={
        "client_id": create_test_client(client, admin_headers, database),
        "ticket_type_id": database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT")),
        "assigned_user_id": admin.id, "subject": "Reassignment recipient scope",
        "description": "Configured recipients must retain access.", "impact": "LOW", "urgency": "LOW",
    })
    assert created.status_code == 201, created.text
    ticket = database.get(Ticket, created.json()["id"])
    assert ticket is not None
    database.add(TicketNotificationRule(
        name="Reassignment scope", is_enabled=True, creator_profile_ids_json="[]",
        assigned_engineer_ids_json=json.dumps([admin.id]), match_mode="ANY",
        to_json=json.dumps([admin.email, "unknown@example.com"]),
        cc_json=json.dumps(["unknown-cc@example.com"]),
        evaluate_initial_assignment=False, evaluate_later_reassignment=True,
    ))
    database.flush()
    queue_ticket_reassignment_email(database, ticket, previous_user_id=None, actor=admin)
    event = database.scalar(select(EventOutbox).where(
        EventOutbox.aggregate_id == str(ticket.id),
        EventOutbox.deduplication_key.like("ticket-assignment-matched:%"),
    ))
    assert event is not None
    payload = json.loads(event.payload_json)
    assert payload["to"] == [admin.email]
    assert payload["cc"] == []


def test_notification_addresses_are_normalized_and_deduplicated() -> None:
    assert normalized_addresses(" Support@Millensys.com;ops@example.com, support@millensys.com ") == [
        "support@millensys.com",
        "ops@example.com",
    ]


def test_ticket_email_recipients_cover_client_department_team_and_shared_addresses(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    from app.modules.iam.models import Effect, Permission
    from app.tests.test_tickets import create_test_client

    client_id = create_test_client(client, admin_headers, database)
    department = Department(code="NOTIFY_SCOPE", name="Notification Scope", is_active=True)
    database.add(department)

    def user(name: str, *, user_type: str = "EMPLOYEE", active: bool = True, department_id: int | None = None, support_email: str | None = None) -> User:
        item = User(full_name=name, username=name.lower().replace(" ", "."),
                    username_normalized=name.lower().replace(" ", "."),
                    email=f"{name.lower().replace(' ', '.')}@example.com",
                    email_normalized=f"{name.lower().replace(' ', '.')}@example.com",
                    support_notification_email=support_email, password_hash="unused",
                    user_type=user_type, is_active=active, department_id=department_id)
        database.add(item)
        database.flush()
        return item

    database.flush()
    client_user = user("Client scoped", user_type="CLIENT_PORTAL")
    department_user = user("Department scoped", department_id=department.id)
    team_user = user("Team scoped")
    user("Inactive shared", active=False, support_email="shared@example.com")
    user("Active shared", support_email="shared@example.com")
    team = SupportTeam(code="NOTIFY_SCOPE", name="Notification scope team", department_id=department.id)
    database.add(team)
    database.flush()
    database.add_all([
        UserClientScope(user_id=client_user.id, client_id=client_id),
        SupportTeamMember(team_id=team.id, user_id=team_user.id),
    ])
    for recipient, permission_code in ((department_user, "ticket.view.department"), (team_user, "ticket.view.team")):
        permission = database.scalar(select(Permission).where(Permission.code == permission_code))
        assert permission is not None
        database.add(UserPermissionOverride(user_id=recipient.id, permission_id=permission.id,
                     effect=Effect.ALLOW, reason="Notification visibility regression"))
    database.commit()
    ticket = SimpleNamespace(client_id=client_id, created_by_user_id=99999,
                             assigned_user_id=None, assigned_team=team.name,
                             routed_team_id=team.id, routed_department_id=department.id)
    addresses = [client_user.email, department_user.email, team_user.email, "shared@example.com", "unknown@example.com"]
    assert authorized_ticket_addresses(database, ticket, addresses) == [
        client_user.email, department_user.email, team_user.email,
    ]


def test_portal_ticket_notification_settings_validate_and_audit(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    invalid = client.put(
        "/api/v1/system/ticket-notifications/portal",
        headers=admin_headers,
        json={"enabled": True, "to": [], "cc": []},
    )
    assert invalid.status_code == 422
    saved = client.put(
        "/api/v1/system/ticket-notifications/portal",
        headers=admin_headers,
        json={
            "enabled": True,
            "to": ["Support@Millensys.com"],
            "cc": ["support@millensys.com", "ops@example.com"],
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json() == {
        "enabled": True,
        "to": ["support@millensys.com"],
        "cc": ["ops@example.com"],
    }
    loaded = client.get(
        "/api/v1/system/ticket-notifications/portal", headers=admin_headers
    )
    assert loaded.json() == saved.json()
    queued = client.post(
        "/api/v1/system/ticket-notifications/test",
        headers=admin_headers,
        json={**saved.json(), "subject_template": "Unsaved test", "body_template": "Queue-only test"},
    )
    assert queued.status_code == 202
    assert queued.json() == {"queued": True, "recipient_count": 2}


def test_internal_notification_rule_create_and_versioned_update(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    profiles = client.get("/api/v1/profiles", headers=admin_headers).json()
    created = client.post(
        "/api/v1/system/ticket-notifications/rules",
        headers=admin_headers,
        json={"name": "Call center route", "is_enabled": True, "creator_profile_ids": [profiles[0]["id"]], "assigned_engineer_ids": [], "match_mode": "ANY", "to": ["ops@example.com"], "cc": [], "include_matched_engineer_email": False, "evaluate_initial_assignment": True, "evaluate_later_reassignment": False},
    )
    assert created.status_code == 201, created.text
    payload = {**created.json(), "name": "Call center route updated", "is_enabled": False, "expected_version": created.json()["version"]}
    payload.pop("id"); payload.pop("version")
    updated = client.put(f"/api/v1/system/ticket-notifications/rules/{created.json()['id']}", headers=admin_headers, json=payload)
    assert updated.status_code == 200, updated.text
    assert updated.json()["version"] == 2
    assert updated.json()["is_enabled"] is False

    stale = client.put(f"/api/v1/system/ticket-notifications/rules/{created.json()['id']}", headers=admin_headers, json={**payload, "name": "Stale update"})
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "NOTIFICATION_RULE_VERSION_CONFLICT"

    archived = client.request("DELETE", f"/api/v1/system/ticket-notifications/rules/{created.json()['id']}", headers=admin_headers, json={"expected_version": updated.json()["version"]})
    assert archived.status_code == 204, archived.text
    assert client.get("/api/v1/system/ticket-notifications/rules", headers=admin_headers).json() == []
    row = database.get(TicketNotificationRule, created.json()["id"])
    assert row is not None and row.is_deleted and not row.is_enabled
    assert row.deleted_at is not None and row.deleted_by_user_id is not None
    assert database.scalar(select(AuditLog.id).where(AuditLog.entity_type == "TicketNotificationRule", AuditLog.entity_id == str(row.id), AuditLog.action == "ticket.notification_rule.archived"))


def test_notification_templates_are_versioned_and_snapshot_safe(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    current = client.get("/api/v1/system/ticket-notifications/templates", headers=admin_headers)
    assert current.status_code == 200
    saved = client.put(
        "/api/v1/system/ticket-notifications/templates",
        headers=admin_headers,
        json={"subject_template": "Ticket {{ticket_number}}", "body_template": "{{ticket_title}} — {{client_name}}", "version": current.json()["version"]},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["version"] == current.json()["version"] + 1
    assert client.get("/api/v1/system/ticket-notifications/templates", headers=admin_headers).json() == saved.json()
