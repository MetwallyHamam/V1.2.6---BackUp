import asyncio
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError
from starlette.requests import Request

from app.core.clock import server_now
from app.modules.clients.models import ClientStatus
from app.modules.iam.models import User
from app.modules.tickets.models import Ticket, TicketStatus, TicketType


def create_ticket(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> dict[str, object]:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    client_response = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={
            "code": "CONCURRENCY",
            "name": "Concurrency Client",
            "status_id": status_id,
        },
    )
    assert client_response.status_code == 201, client_response.text
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    response = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_response.json()["id"],
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "Competing ticket mutations",
            "description": "Only the mutation based on the current version may be retained.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def assert_concurrent_update(response: Response) -> None:
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONCURRENT_UPDATE"


def test_sla_preview_uses_current_version_without_conflict(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    ticket = create_ticket(client, admin_headers, database)
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    assigned = client.post(
        f"/api/v1/tickets/{ticket['id']}/assignment",
        headers=admin_headers,
        json={
            "assigned_user_id": admin.id,
            "assigned_team": "Support",
            "reason": "Assignment changed after edit dialog opened",
            "version": ticket["version"],
        },
    )
    assert assigned.status_code == 200, assigned.text

    preview = client.post(
        f"/api/v1/tickets/{ticket['id']}/sla-preview",
        headers=admin_headers,
        json={"version": ticket["version"]},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["version"] == assigned.json()["version"]


def test_stale_workflow_assignment_pending_and_escalation_do_not_lose_data(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    ticket = create_ticket(client, admin_headers, database)
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    original_version = int(ticket["version"])
    assigned = client.post(
        f"/api/v1/tickets/{ticket['id']}/assignment",
        headers=admin_headers,
        json={
            "assigned_user_id": admin.id,
            "assigned_team": "Support",
            "reason": "Current assignment wins",
            "version": original_version,
        },
    )
    assert assigned.status_code == 200, assigned.text
    stale_transition = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        headers=admin_headers,
        json={"to_status_code": "IN_PROGRESS", "version": original_version},
    )
    assert_concurrent_update(stale_transition)
    current = client.get(f"/api/v1/tickets/{ticket['id']}", headers=admin_headers).json()
    assert current["assigned_user_id"] == admin.id

    pre_pending_version = current["version"]
    pending = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "PENDING_INTERNAL",
            "reason": "Waiting for an internal dependency",
            "pending_owner_user_id": admin.id,
            "pending_follow_up_at": (server_now() + timedelta(days=1)).isoformat(),
            "version": pre_pending_version,
        },
    )
    assert pending.status_code == 200, pending.text
    stale_escalation = client.post(
        f"/api/v1/tickets/{ticket['id']}/escalation",
        headers=admin_headers,
        json={
            "escalation_assignee_user_id": admin.id,
            "escalation_level": "SENIOR_ENGINEER",
            "reason": "This stale escalation must not overwrite pending context",
            "version": pre_pending_version,
        },
    )
    assert_concurrent_update(stale_escalation)
    current = client.get(f"/api/v1/tickets/{ticket['id']}", headers=admin_headers).json()
    assert current["pending_reason"] == "Waiting for an internal dependency"
    assert current["escalation_assignee_user_id"] is None
    assert (
        database.scalar(select(Ticket.id).where(Ticket.escalation_parent_ticket_id == ticket["id"]))
        is None
    )

    escalated = client.post(
        f"/api/v1/tickets/{ticket['id']}/escalation",
        headers=admin_headers,
        json={
            "escalation_assignee_user_id": admin.id,
            "escalation_level": "SENIOR_ENGINEER",
            "reason": "The current escalation must remain intact",
            "version": current["version"],
        },
    )
    assert escalated.status_code == 200, escalated.text
    stale_assignment = client.post(
        f"/api/v1/tickets/{ticket['id']}/assignment",
        headers=admin_headers,
        json={
            "assigned_user_id": None,
            "assigned_team": None,
            "reason": "This stale unassignment must be rejected",
            "version": current["version"],
        },
    )
    assert_concurrent_update(stale_assignment)
    final = client.get(f"/api/v1/tickets/{ticket['id']}", headers=admin_headers).json()
    assert final["assigned_user_id"] == admin.id
    assert final["escalation_assignee_user_id"] == admin.id


def test_bulk_assignment_rejects_a_stale_selection_atomically(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    ticket = create_ticket(client, admin_headers, database)
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    current = client.post(
        f"/api/v1/tickets/{ticket['id']}/assignment",
        headers=admin_headers,
        json={
            "assigned_user_id": admin.id,
            "reason": "Advance the version before bulk retry verification",
            "version": ticket["version"],
        },
    )
    assert current.status_code == 200, current.text
    stale_bulk = client.post(
        "/api/v1/tickets/bulk-assignment",
        headers=admin_headers,
        json={
            "items": [{"ticket_id": ticket["id"], "expected_version": ticket["version"]}],
            "assigned_user_id": None,
            "assigned_team": None,
            "reason": "This stale bulk action must not overwrite the assignment",
        },
    )
    assert_concurrent_update(stale_bulk)
    database.expire_all()
    stored = database.get(Ticket, ticket["id"])
    assert stored is not None
    assert stored.assigned_user_id == admin.id


def test_database_compare_and_swap_rejects_simultaneous_ticket_writers(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    ticket = create_ticket(client, admin_headers, database)
    assert database.bind is not None
    with Session(database.bind) as first, Session(database.bind) as second:
        first_copy = first.get(Ticket, ticket["id"])
        second_copy = second.get(Ticket, ticket["id"])
        assert first_copy is not None and second_copy is not None
        first_copy.subject = "First writer committed"
        first_copy.version += 1
        first.commit()
        second_copy.subject = "Second writer must lose"
        second_copy.version += 1
        with pytest.raises(StaleDataError):
            second.commit()
        second.rollback()
    database.expire_all()
    stored = database.get(Ticket, ticket["id"])
    assert stored is not None
    assert stored.subject == "First writer committed"
    assert stored.version == int(ticket["version"]) + 1
    status = database.get(TicketStatus, stored.status_id)
    assert status is not None


def test_database_detected_race_has_controlled_http_conflict(client: TestClient) -> None:
    handler = client.app.exception_handlers[StaleDataError]
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/tickets/1/transition",
            "headers": [],
        }
    )
    request.state.correlation_id = "concurrency-test-correlation"
    response = asyncio.run(handler(request, StaleDataError("simulated competing update")))
    assert response.status_code == 409
    assert b'"code":"CONCURRENT_UPDATE"' in response.body
    assert response.headers["x-correlation-id"] == "concurrency-test-correlation"
