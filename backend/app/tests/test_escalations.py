import json
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.modules.clients.models import ClientStatus, SupportTeam, SupportTeamMember
from app.modules.configuration.models import SiteSetting
from app.modules.contracts.models import TicketSlaClock
from app.modules.escalations.models import EscalationEvent, EscalationWorkItem
from app.modules.escalations.service import evaluate_escalations
from app.modules.iam.models import AuditLog, User
from app.modules.notifications.models import EventOutbox, Notification
from app.modules.tickets.models import TicketType


def test_escalation_uses_only_due_work_items(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    client_id = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "SLA-QUEUE", "name": "SLA Queue Client", "status_id": status_id},
    ).json()["id"]
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={"ticket_type_id": ticket_type_id, "client_id": client_id, "impact": "HIGH", "urgency": "HIGH", "subject": "Targeted SLA queue", "description": "Prove future queue rows are not scanned."},
    ).json()
    clocks = list(database.scalars(select(TicketSlaClock).where(TicketSlaClock.ticket_id == ticket["id"])))
    running_ids = {clock.id for clock in clocks if clock.state == "RUNNING"}
    work_items = list(database.scalars(select(EscalationWorkItem).where(EscalationWorkItem.ticket_sla_clock_id.in_(running_ids))))
    assert len(work_items) == len(running_ids)
    future = server_now() + timedelta(days=1)
    for item in work_items:
        item.status = "PENDING"
        item.next_evaluation_at = future
    database.commit()
    metrics: dict[str, int] = {}
    assert evaluate_escalations(database, now=server_now(), metrics=metrics) == 0
    assert metrics["due_work_items"] == 0
    assert metrics["running_clocks"] == 0


def test_escalation_evaluation_is_idempotent(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    client_response = client.post("/api/v1/clients", headers=admin_headers, json={"code": "SLA-CLIENT", "name": "SLA Client", "status_id": status_id})
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    ticket_response = client.post("/api/v1/tickets", headers=admin_headers, json={"ticket_type_id": ticket_type_id, "client_id": client_response.json()["id"], "impact": "CRITICAL", "urgency": "CRITICAL", "subject": "Critical SLA test ticket", "description": "Critical service failure used to verify escalation idempotency."})
    assert ticket_response.status_code == 201, ticket_response.text
    ticket_id = ticket_response.json()["id"]
    clocks = list(database.scalars(select(TicketSlaClock).where(TicketSlaClock.ticket_id == ticket_id)))
    assert len(clocks) == 2
    for clock in clocks:
        clock.started_at = server_now() - timedelta(minutes=clock.target_minutes + 1)
        clock.due_at = server_now() - timedelta(minutes=1)
    database.commit()
    first = evaluate_escalations(database)
    second = evaluate_escalations(database)
    assert first > 0
    assert second == 0
    assert database.scalar(select(EscalationEvent.id).where(EscalationEvent.ticket_id == ticket_id))
    warnings = list(
        database.scalars(
            select(Notification).where(
                Notification.notification_type == "SLA_WARNING",
            )
        )
    )
    assert warnings
    assert len({warning.deduplication_key for warning in warnings}) == len(warnings)


def test_sla_minute_warnings_expand_direct_and_team_recipients_once(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    client_id = client.post("/api/v1/clients", headers=admin_headers, json={"code": "SLA-RECIPIENTS", "name": "SLA Recipient Client", "status_id": status_id}).json()["id"]
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    ticket = client.post("/api/v1/tickets", headers=admin_headers, json={"ticket_type_id": ticket_type_id, "client_id": client_id, "impact": "HIGH", "urgency": "HIGH", "subject": "Configured SLA recipients", "description": "Verify minute thresholds and recipient expansion."}).json()
    support = database.scalar(select(User).where(User.username_normalized == "support"))
    assert support is not None
    support.support_notification_email = "team-alerts@example.com"
    team = SupportTeam(name="SLA Notification Team", code="SLA_NOTIFY", is_active=True)
    database.add(team); database.flush(); database.add(SupportTeamMember(team_id=team.id, user_id=support.id))
    settings = {
        "sla_warning_enabled": "true",
        "sla_response_warning_minutes": "[10]",
        "sla_resolution_warning_minutes": "[10]",
        "sla_warning_recipient_emails": '["direct@example.com", "TEAM-ALERTS@example.com"]',
        "sla_warning_support_team_ids": json.dumps([team.id]),
    }
    for key, value in settings.items():
        database.merge(SiteSetting(key=key, value=value))
    now = server_now()
    clocks = list(database.scalars(select(TicketSlaClock).where(TicketSlaClock.ticket_id == ticket["id"])))
    for clock in clocks:
        clock.target_minutes = 5
        clock.started_at = now
        clock.due_at = now + timedelta(minutes=5)
    database.commit()

    first = evaluate_escalations(database, now=now)
    second = evaluate_escalations(database, now=now)
    assert first > 0
    assert second == 0
    events = list(database.scalars(select(EventOutbox).where(EventOutbox.event_type == "SLA_WARNING", EventOutbox.aggregate_id == str(ticket["id"]))))
    assert len(events) == len([clock for clock in clocks if clock.state == "RUNNING"])
    for event in events:
        payload = json.loads(event.payload_json)
        assert payload["threshold_minutes"] == 10
        assert payload["recipient_emails"].count("team-alerts@example.com") == 1
        assert "direct@example.com" in payload["recipient_emails"]


def test_disabled_sla_warnings_do_not_create_warning_delivery(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    client_id = client.post("/api/v1/clients", headers=admin_headers, json={"code": "SLA-DISABLED", "name": "SLA Disabled Client", "status_id": status_id}).json()["id"]
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    ticket = client.post("/api/v1/tickets", headers=admin_headers, json={"ticket_type_id": ticket_type_id, "client_id": client_id, "impact": "HIGH", "urgency": "HIGH", "subject": "Disabled SLA warnings", "description": "Verify the backend master switch."}).json()
    database.merge(SiteSetting(key="sla_warning_enabled", value="false"))
    now = server_now()
    for clock in database.scalars(select(TicketSlaClock).where(TicketSlaClock.ticket_id == ticket["id"])):
        clock.started_at = now - timedelta(minutes=clock.target_minutes + 1)
        clock.due_at = now - timedelta(minutes=1)
    database.commit()

    evaluate_escalations(database, now=now)
    assert database.scalar(select(Notification.id).where(Notification.notification_type == "SLA_WARNING", Notification.title.contains(ticket["ticket_number"]))) is None
    assert database.scalar(select(EventOutbox.id).where(EventOutbox.event_type == "SLA_WARNING", EventOutbox.aggregate_id == str(ticket["id"]))) is None


def test_scheduler_status_is_visible_to_administrators(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get(
        "/api/v1/escalations/scheduler-status", headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["interval_seconds"] == 60
    assert response.json()["running"] is False


def test_escalation_rules_can_be_created_edited_and_deactivated(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    created = client.post(
        "/api/v1/escalation-rules",
        headers=admin_headers,
        json={
            "name": "Priority one response warning",
            "clock_type": "FIRST_RESPONSE",
            "threshold_percent": 65,
            "priority": "P1",
            "severity": "WARNING",
            "notify_assignee": True,
            "notify_managers": True,
            "is_active": True,
        },
    )
    assert created.status_code == 201, created.text
    rule = created.json()
    assert rule["code"].startswith("SLA_RULE_")
    assert rule["version"] == 1

    updated = client.patch(
        f"/api/v1/escalation-rules/{rule['id']}",
        headers=admin_headers,
        json={
            "name": "Priority one response warning",
            "clock_type": "FIRST_RESPONSE",
            "threshold_percent": 65,
            "priority": "P1",
            "severity": "CRITICAL",
            "notify_assignee": True,
            "notify_managers": False,
            "is_active": False,
            "expected_version": 1,
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["severity"] == "CRITICAL"
    assert updated.json()["is_active"] is False
    assert updated.json()["version"] == 2

    stale = client.patch(
        f"/api/v1/escalation-rules/{rule['id']}",
        headers=admin_headers,
        json={**updated.json(), "expected_version": 1},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "STALE_ESCALATION_RULE"
    assert database.scalar(
        select(AuditLog.id).where(
            AuditLog.entity_type == "EscalationRule",
            AuditLog.entity_id == str(rule["id"]),
            AuditLog.action == "escalation_rule.updated",
        )
    ) is not None
