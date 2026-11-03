import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import server_now, server_timezone
from app.core.config import Settings, get_settings
from app.modules.clients.models import (
    ClientStatus,
    ServiceCatalogItem,
    SupportTeam,
    TicketCategory,
)
from app.modules.configuration.models import SiteSetting
from app.modules.contracts.models import TicketSlaClock, TicketSlaInterval
from app.modules.entitlements.models import EntitlementApproval
from app.modules.escalations.service import evaluate_escalations
from app.modules.iam.models import (
    AuditLog,
    Department,
    Effect,
    Permission,
    Profile,
    ProfilePermission,
    User,
    UserPermissionOverride,
    UserProfile,
)
from app.modules.iam.security import hash_password
from app.modules.knowledge_base.models import Article, KnowledgeCategory, TicketArticleLink
from app.modules.notifications.models import EventOutbox, Notification
from app.modules.tickets.models import (
    RootCause,
    SupportAssistantPreference,
    Ticket,
    TicketAssignmentHistory,
    TicketAttachment,
    TicketDeletionRequest,
    TicketRelation,
    TicketSatisfaction,
    TicketStatus,
    TicketStatusHistory,
    TicketTemplate,
    TicketType,
)
from app.modules.tickets.service import derive_priority


def create_test_client(
    client: TestClient,
    headers: dict[str, str],
    database: Session,
) -> int:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    response = client.post(
        "/api/v1/clients",
        headers=headers,
        json={"code": "TICKETCLIENT", "name": "Ticket Client", "status_id": status_id},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_priority_derivation() -> None:
    assert derive_priority("CRITICAL", "CRITICAL") == "P1"
    assert derive_priority("HIGH", "MEDIUM") == "P2"
    assert derive_priority("MEDIUM", "LOW") == "P3"
    assert derive_priority("LOW", "LOW") == "P4"


def test_ticket_search_matches_client_name_and_code(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    created_client = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={
            "code": "NORTHSTAR-CLINIC",
            "name": "Northstar Diagnostic Center",
            "status_id": status_id,
        },
    )
    assert created_client.status_code == 201, created_client.text
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    created_ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": created_client.json()["id"],
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Unrelated workstation configuration issue",
            "description": "Verify that the queue search resolves the owning client.",
        },
    )
    assert created_ticket.status_code == 201, created_ticket.text

    by_name = client.get(
        "/api/v1/tickets", headers=admin_headers, params={"search": "diagnostic center"}
    )
    assert by_name.status_code == 200, by_name.text
    assert created_ticket.json()["id"] in {item["id"] for item in by_name.json()}

    by_code = client.get(
        "/api/v1/tickets", headers=admin_headers, params={"search": "northstar-clinic"}
    )
    assert by_code.status_code == 200, by_code.text
    assert created_ticket.json()["id"] in {item["id"] for item in by_code.json()}


def test_ticket_list_can_exclude_change_requests_until_type_is_selected(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    incident_type_id = database.scalar(
        select(TicketType.id).where(TicketType.code == "INCIDENT")
    )
    change_type_id = database.scalar(
        select(TicketType.id).where(TicketType.code == "CHANGE_REQUEST")
    )
    assert incident_type_id and change_type_id

    def create_ticket(ticket_type_id: int, subject: str) -> int:
        response = client.post(
            "/api/v1/tickets",
            headers=admin_headers,
            json={
                "ticket_type_id": ticket_type_id,
                "client_id": client_id,
                "impact": "LOW",
                "urgency": "LOW",
                "subject": subject,
                "description": "Verify the standard ticket queue type boundary.",
            },
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    incident_id = create_ticket(incident_type_id, "Visible standard ticket")
    change_id = create_ticket(change_type_id, "Dedicated change request")

    standard_queue = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"exclude_ticket_type_code": "CHANGE_REQUEST"},
    )
    assert standard_queue.status_code == 200, standard_queue.text
    standard_ids = {item["id"] for item in standard_queue.json()}
    assert incident_id in standard_ids
    assert change_id not in standard_ids

    explicit_change_search = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={
            "exclude_ticket_type_code": "CHANGE_REQUEST",
            "ticket_type_id": change_type_id,
        },
    )
    assert explicit_change_search.status_code == 200, explicit_change_search.text
    assert change_id in {item["id"] for item in explicit_change_search.json()}


def test_ticket_list_includes_caller_contact_details(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    caller = client.post(
        "/api/v1/contacts",
        headers=admin_headers,
        json={
            "client_id": client_id,
            "full_name": "Mona Caller",
            "phone_number": "+201001234567",
            "email": "mona.caller@example.com",
            "job_title": "IT Manager",
            "is_active": True,
        },
    )
    assert caller.status_code == 201, caller.text
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "requester_contact_id": caller.json()["id"],
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Caller grid details",
            "description": "Verify caller actions can render without extra row requests.",
        },
    )
    assert created.status_code == 201, created.text
    flag = client.post(
        "/api/v1/ticket-flags",
        headers=admin_headers,
        json={"name": "Awaiting vendor", "color": "#7C3AED", "pauses_sla": False},
    )
    assert flag.status_code == 201, flag.text
    applied = client.post(
        f"/api/v1/ticket-flags/ticket/{created.json()['id']}",
        headers=admin_headers,
        json={"flag_id": flag.json()["id"], "reason": "Vendor response required"},
    )
    assert applied.status_code == 201, applied.text
    listed = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"ticket_number": created.json()["ticket_number"]},
    )
    assert listed.status_code == 200, listed.text
    row = next(item for item in listed.json() if item["id"] == created.json()["id"])
    assert row["requester_name"] == "Mona Caller"
    assert row["requester_phone_number"] == "+201001234567"
    assert row["requester_email"] == "mona.caller@example.com"
    assert row["requester_job_title"] == "IT Manager"
    assert row["active_flags"] == [
        {
            "id": applied.json()["id"],
            "flag_id": flag.json()["id"],
            "code": flag.json()["code"],
            "name": "Awaiting vendor",
            "color": "#7C3AED",
            "pauses_sla": False,
        }
    ]
    other = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Different caller ticket",
            "description": "Must not appear in caller-filtered results.",
        },
    )
    assert other.status_code == 201, other.text
    caller_tickets = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"requester_contact_id": caller.json()["id"]},
    )
    assert caller_tickets.status_code == 200, caller_tickets.text
    assert {item["id"] for item in caller_tickets.json()} == {created.json()["id"]}


def test_ticket_can_be_saved_and_found_as_keyword_template(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "HIGH",
            "urgency": "MEDIUM",
            "subject": "DICOM routing queue failure",
            "description": "Images remain queued when routing to the archive.",
        },
    )
    assert created.status_code == 201, created.text
    saved = client.post(
        f"/api/v1/tickets/{created.json()['id']}/template",
        headers=admin_headers,
        json={
            "name": "DICOM queue recovery",
            "keywords": "dicom, routing, queue",
            "scope": "CLIENT",
            "portal_visible": True,
        },
    )
    assert saved.status_code == 201, saved.text
    assert saved.json()["client_id"] == client_id
    assert database.scalar(select(TicketTemplate).where(TicketTemplate.id == saved.json()["id"]))
    matches = client.get(
        "/api/v1/tickets/templates",
        headers=admin_headers,
        params={"query": "routing queue", "client_id": client_id},
    )
    assert matches.status_code == 200, matches.text
    assert [item["id"] for item in matches.json()] == [saved.json()["id"]]
    short_keyword_matches = client.get(
        "/api/v1/tickets/templates",
        headers=admin_headers,
        params={"query": "dic", "client_id": client_id},
    )
    assert short_keyword_matches.status_code == 200, short_keyword_matches.text
    assert [item["id"] for item in short_keyword_matches.json()] == [saved.json()["id"]]
    unrelated = client.get(
        "/api/v1/tickets/templates",
        headers=admin_headers,
        params={"query": "workstations system slow", "client_id": client_id},
    )
    assert unrelated.status_code == 200, unrelated.text
    assert unrelated.json() == []
    short_similar_search = client.get(
        "/api/v1/tickets/similar",
        headers=admin_headers,
        params={"subject": "dic", "client_id": client_id},
    )
    assert short_similar_search.status_code == 200, short_similar_search.text
    assert created.json()["id"] in {item["id"] for item in short_similar_search.json()}


def test_support_assistant_preferences_are_user_scoped_and_audited(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Support Assistant preference ticket",
            "description": "This ticket verifies durable personal queue preferences.",
        },
    )
    assert created.status_code == 201, created.text
    ticket_id = created.json()["id"]

    marked = client.put(
        f"/api/v1/tickets/{ticket_id}/support-follow-up",
        headers=admin_headers,
        json={"marked": True, "version": created.json()["version"]},
    )
    assert marked.status_code == 200, marked.text
    assert marked.json()["support_follow_up_flag"] is True
    follow_up_queue = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"assistant_module": "follow-up"},
    )
    assert follow_up_queue.status_code == 200, follow_up_queue.text
    assert ticket_id in {item["id"] for item in follow_up_queue.json()}
    assert (
        database.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action == "ticket.support_follow_up.updated")
        )
        == 1
    )

    ticket = database.get(Ticket, ticket_id)
    in_progress = database.scalar(select(TicketStatus).where(TicketStatus.code == "IN_PROGRESS"))
    new_status = database.scalar(select(TicketStatus).where(TicketStatus.code == "NEW"))
    assert ticket is not None and in_progress is not None and new_status is not None
    ticket.support_follow_up_flag = False
    ticket.assigned_user_id = database.scalar(select(User.id).where(User.username == "admin"))
    ticket.status_id = in_progress.id
    database.commit()
    in_progress_follow_up = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"assistant_module": "follow-up"},
    )
    assert ticket_id not in {item["id"] for item in in_progress_follow_up.json()}
    backlog = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"assistant_module": "backlog"},
    )
    assert backlog.status_code == 200, backlog.text
    assert ticket_id in {item["id"] for item in backlog.json()}
    resolved_status = database.scalar(select(TicketStatus).where(TicketStatus.code == "RESOLVED"))
    assert resolved_status is not None
    ticket.status_id = resolved_status.id
    ticket.created_at = server_now() - timedelta(days=3)
    database.commit()
    default_mine = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"assistant_module": "mine"},
    )
    assert ticket_id not in {item["id"] for item in default_mine.json()}
    filtered_mine = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"assistant_module": "mine", "status_code": "RESOLVED,CLOSED"},
    )
    assert filtered_mine.status_code == 200, filtered_mine.text
    assert ticket_id in {item["id"] for item in filtered_mine.json()}
    other_engineer_id = database.scalar(
        select(User.id).where(User.username != "admin", User.user_type == "EMPLOYEE")
    )
    assert other_engineer_id is not None
    ticket.assigned_user_id = other_engineer_id
    database.commit()
    resolved_queue = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"assistant_module": "resolved"},
    )
    assert resolved_queue.status_code == 200, resolved_queue.text
    assert ticket_id in {item["id"] for item in resolved_queue.json()}
    ticket.assigned_user_id = database.scalar(select(User.id).where(User.username == "admin"))
    database.commit()
    filtered_backlog = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"assistant_module": "backlog", "status_code": "RESOLVED,CLOSED"},
    )
    assert filtered_backlog.status_code == 200, filtered_backlog.text
    assert ticket_id in {item["id"] for item in filtered_backlog.json()}

    reopened_status = database.scalar(select(TicketStatus).where(TicketStatus.code == "REOPENED"))
    assert reopened_status is not None
    ticket.status_id = reopened_status.id
    ticket.assigned_user_id = None
    ticket.created_at = server_now() - timedelta(days=30)
    database.commit()
    reopened_queue = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"assistant_module": "queue", "sort_by": "created_at", "sort_direction": "desc"},
    )
    assert reopened_queue.status_code == 200, reopened_queue.text
    assert reopened_queue.json()[0]["id"] == ticket_id

    ticket.assigned_user_id = database.scalar(select(User.id).where(User.username == "admin"))
    database.commit()
    reopened_mine = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"assistant_module": "mine", "status_code": "REOPENED,IN_PROGRESS"},
    )
    assert reopened_mine.status_code == 200, reopened_mine.text
    assert reopened_mine.json()[0]["id"] == ticket_id

    ticket.status_id = new_status.id
    ticket.created_at = server_now()
    database.commit()
    unrelated_open = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"assistant_module": "follow-up"},
    )
    assert ticket_id not in {item["id"] for item in unrelated_open.json()}

    saved = client.put(
        "/api/v1/tickets/support-assistant/preferences",
        headers=admin_headers,
        json={
            "pinned_ticket_ids": [ticket_id, ticket_id],
            "default_tab": "mine",
            "workspace_state": {
                "compact": True,
                "width": 520,
                "page_size": 20,
                "hidden_card_fields": ["created"],
                "tab_sorting": {"mine": "priority:asc"},
                "tab_filters": {"mine": {"priority": "P1"}},
            },
            "custom_tabs": [
                {
                    "id": "urgent-mine",
                    "name": "Urgent Mine",
                    "source_module": "mine",
                    "filters": {"priority": "P1"},
                    "sorting": "updated_at:desc",
                }
            ],
        },
    )
    assert saved.status_code == 200, saved.text
    saved_preferences = saved.json()
    assert saved_preferences["pinned_ticket_ids"] == [ticket_id]
    assert saved_preferences["default_tab"] == "mine"
    assert saved_preferences["workspace_state"]["page_size"] == 20
    assert saved_preferences["workspace_state"]["hidden_card_fields"] == ["created"]
    assert saved_preferences["custom_tabs"][0]["name"] == "Urgent Mine"
    assert (
        client.get("/api/v1/tickets/support-assistant/preferences", headers=admin_headers).json()
        == saved_preferences
    )
    assert database.scalar(select(func.count()).select_from(SupportAssistantPreference)) == 1
    assert (
        database.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action == "support_assistant.preferences.updated")
        )
        == 1
    )

    stale_pin_save = client.put(
        "/api/v1/tickets/support-assistant/preferences",
        headers=admin_headers,
        json={
            **saved_preferences,
            "pinned_ticket_ids": [ticket_id, 999_999_999],
            "default_tab": "backlog",
        },
    )
    assert stale_pin_save.status_code == 200, stale_pin_save.text
    assert stale_pin_save.json()["pinned_ticket_ids"] == [ticket_id]
    assert stale_pin_save.json()["default_tab"] == "backlog"

    workspace = client.put(
        "/api/v1/tickets/my-workspace",
        headers=admin_headers,
        json={
            "favorites": [
                {
                    "id": "ticket:important",
                    "label": "Important ticket",
                    "path": f"/tickets/{ticket_id}",
                    "item_type": "ticket",
                }
            ],
            "hidden_widgets": ["approvals"],
        },
    )
    assert workspace.status_code == 200, workspace.text
    assert workspace.json()["favorites"][0]["path"] == f"/tickets/{ticket_id}"
    assert workspace.json()["hidden_widgets"] == ["approvals"]

    recent = client.post(
        "/api/v1/tickets/my-workspace/recent",
        headers=admin_headers,
        json={"label": "Tickets", "path": "/tickets", "item_type": "page"},
    )
    assert recent.status_code == 200, recent.text
    assert recent.json()["recent"][0]["path"] == "/tickets"
    assert client.get(
        "/api/v1/tickets/my-workspace", headers=admin_headers
    ).json() == recent.json()


def test_ticket_creation_idempotency_returns_original_or_rejects_conflict(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    payload = {
        "ticket_type_id": ticket_type_id,
        "client_id": client_id,
        "impact": "LOW",
        "urgency": "LOW",
        "subject": "Idempotent creation verification",
        "description": "This request verifies durable creation retry handling.",
        "creation_idempotency_key": "ticket-create-retry-001",
    }
    first = client.post("/api/v1/tickets", headers=admin_headers, json=payload)
    second = client.post("/api/v1/tickets", headers=admin_headers, json=payload)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    conflict = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={**payload, "subject": "A different request using the same key"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "TICKET_CREATION_IDEMPOTENCY_CONFLICT"


def test_ticket_comment_idempotency_replays_once_and_rejects_changed_content(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Comment retry",
            "description": "Verify a retried comment remains one logical comment.",
        },
    ).json()
    payload = {
        "body": "Customer-facing retry-safe update.",
        "is_internal": False,
        "operation_key": "comment-retry-001",
    }
    first = client.post(
        f"/api/v1/tickets/{ticket['id']}/comments", headers=admin_headers, json=payload
    )
    second = client.post(
        f"/api/v1/tickets/{ticket['id']}/comments", headers=admin_headers, json=payload
    )
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    conflict = client.post(
        f"/api/v1/tickets/{ticket['id']}/comments",
        headers=admin_headers,
        json={**payload, "body": "Different content"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "COMMENT_IDEMPOTENCY_CONFLICT"


def test_ticket_details_include_persisted_client_name(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Persisted client-name details",
            "description": "Verify client name after creation and direct loading.",
        },
    )
    assert created.status_code == 201, created.text

    details = client.get(f"/api/v1/tickets/{created.json()['id']}", headers=admin_headers)
    assert details.status_code == 200, details.text
    assert details.json()["client_id"] == client_id
    assert details.json()["client_name"] == "Ticket Client"


def test_bulk_delete_removes_ticket_with_dependent_history(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "assigned_user_id": admin_id,
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "Ticket to delete with history",
            "description": "This ticket verifies ordered deletion of dependent records.",
        },
    )
    assert created.status_code == 201, created.text
    ticket_id = created.json()["id"]
    assert (
        database.scalar(
            select(TicketStatusHistory.id).where(TicketStatusHistory.ticket_id == ticket_id)
        )
        is not None
    )

    deletion_request = client.post(
        "/api/v1/tickets/bulk-delete",
        headers=admin_headers,
        json={"ticket_ids": [ticket_id], "reason": "Regression test cleanup"},
    )

    assert deletion_request.status_code == 200, deletion_request.text
    assert deletion_request.json()[0]["status"] == "PENDING"
    retried = client.post(
        "/api/v1/tickets/bulk-delete",
        headers=admin_headers,
        json={"ticket_ids": [ticket_id], "reason": "Regression test cleanup"},
    )
    assert retried.status_code == 200, retried.text
    assert retried.json()[0]["id"] == deletion_request.json()[0]["id"]
    assert database.scalar(select(func.count()).select_from(TicketDeletionRequest)) == 1
    database.expire_all()
    archived = database.get(Ticket, ticket_id)
    assert archived is not None
    assert archived.archived_at is None
    # A different authorized actor must make the deletion decision.
    approver = User(
        username="delete-approver",
        email="delete-approver@example.com",
        username_normalized="delete-approver",
        email_normalized="delete-approver@example.com",
        full_name="Delete Approver",
        user_type="EMPLOYEE",
        is_active=True,
        password_hash=hash_password("DeleteApprover!123"),
        require_password_change=False,
    )
    database.add(approver)
    database.flush()
    administrator = database.scalar(select(Profile).where(Profile.code == "ADMINISTRATOR"))
    assert administrator is not None
    database.add(UserProfile(user_id=approver.id, profile_id=administrator.id))
    database.commit()
    login = client.post(
        "/api/v1/auth/login", json={"login": "delete-approver", "password": "DeleteApprover!123"}
    )
    approver_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    approved = client.post(
        f"/api/v1/tickets/deletion-requests/{deletion_request.json()[0]['id']}/decision",
        headers=approver_headers,
        json={"decision": "APPROVED", "comment": "Approved after confirming duplicate evidence."},
    )
    assert approved.status_code == 200, approved.text
    database.expire_all()
    archived = database.get(Ticket, ticket_id)
    assert archived is not None and archived.archived_at is not None
    assert archived.archive_reason == "Regression test cleanup"
    assert (
        database.scalar(
            select(Notification.id).where(
                Notification.recipient_user_id == admin_id,
                Notification.notification_type == "TICKET_DELETION_DECIDED",
            )
        )
        is not None
    )
    assert (
        database.scalar(
            select(TicketStatusHistory.id).where(TicketStatusHistory.ticket_id == ticket_id)
        )
        is not None
    )
    assert ticket_id not in [
        row["id"] for row in client.get("/api/v1/tickets", headers=admin_headers).json()
    ]
    restored = client.post(
        f"/api/v1/tickets/{ticket_id}/restore",
        headers=admin_headers,
        json={
            "version": archived.version,
            "reason": "Archive was created during a duplicate review.",
        },
    )
    assert restored.status_code == 200, restored.text
    database.expire_all()
    assert database.get(Ticket, ticket_id).archived_at is None
    assert ticket_id in [
        row["id"] for row in client.get("/api/v1/tickets", headers=admin_headers).json()
    ]
    assert (
        database.scalar(
            select(AuditLog.id).where(
                AuditLog.entity_id == str(ticket_id),
                AuditLog.action == "ticket.restored",
            )
        )
        is not None
    )


def test_internal_escalation_assignment_and_clear(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "HIGH",
            "urgency": "HIGH",
            "subject": "Internal escalation workflow",
            "description": "Requires assistance from a senior internal engineer.",
            "assigned_user_id": admin.id,
        },
    ).json()
    escalated = client.post(
        f"/api/v1/tickets/{ticket['id']}/escalation",
        headers=admin_headers,
        json={
            "escalation_assignee_user_id": admin.id,
            "escalation_level": "SENIOR_ENGINEER",
            "reason": "Advanced investigation and technical guidance required",
            "version": ticket["version"],
        },
    )
    assert escalated.status_code == 200, escalated.text
    assert escalated.json()["escalation_assignee_user_id"] == admin.id
    assert escalated.json()["escalation_level"] == "SENIOR_ENGINEER"
    assert escalated.json()["escalated_at"] is not None
    cleared = client.post(
        f"/api/v1/tickets/{ticket['id']}/escalation",
        headers=admin_headers,
        json={
            "escalation_assignee_user_id": None,
            "escalation_level": None,
            "reason": "Senior review completed and ticket returned to normal handling",
            "version": escalated.json()["version"],
        },
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["escalation_assignee_user_id"] is None
    assert cleared.json()["escalated_at"] is None
    actions = set(
        database.scalars(
            select(AuditLog.action).where(
                AuditLog.entity_type == "Ticket", AuditLog.entity_id == str(ticket["id"])
            )
        )
    )
    assert {"ticket.escalated", "ticket.escalation.cleared"} <= actions


def test_department_help_request_is_linked_audited_and_returnable(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    department = Department(code="FINHELP", name="Finance Help", is_active=True)
    database.add(department)
    database.flush()
    admin.department_id = department.id
    admin.department = department.name
    team = SupportTeam(
        code="FINHELP",
        name="Finance Help Team",
        department_id=department.id,
        leader_user_id=admin.id,
        is_active=True,
    )
    database.add(team)
    database.commit()
    parent = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "Department collaboration request",
            "description": "Support needs a governed response from Finance.",
            "assigned_user_id": admin.id,
        },
    ).json()

    requested = client.post(
        f"/api/v1/tickets/{parent['id']}/help-request",
        headers=admin_headers,
        json={
            "department_id": department.id,
            "team_id": team.id,
            "escalation_assignee_user_id": admin.id,
            "escalation_level": "OTHER_DEPARTMENT",
            "reason": "Confirm the customer payment allocation",
            "version": parent["version"],
        },
    )
    assert requested.status_code == 201, requested.text
    child = requested.json()
    assert child["escalation_parent_ticket_id"] == parent["id"]
    assert child["routed_department_id"] == department.id
    assert child["routed_team_id"] == team.id
    assert child["routing_status"] == "NEW"

    returned = client.post(
        f"/api/v1/tickets/{child['id']}/return-result",
        headers=admin_headers,
        json={
            "result": "Payment allocation confirmed against the invoice.",
            "version": child["version"],
        },
    )
    assert returned.status_code == 200, returned.text
    assert returned.json()["routing_status"] == "RETURNED"
    assert (
        returned.json()["help_request_result"]
        == "Payment allocation confirmed against the invoice."
    )
    parent_requests = client.get(
        f"/api/v1/tickets/{parent['id']}/department-requests", headers=admin_headers
    )
    assert parent_requests.status_code == 200, parent_requests.text
    assert [(row["id"], row["routing_status"]) for row in parent_requests.json()] == [
        (child["id"], "RETURNED")
    ]
    returned_queue = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"department_requests_only": True, "routing_status": "RETURNED"},
    )
    assert returned_queue.status_code == 200, returned_queue.text
    assert [row["id"] for row in returned_queue.json()] == [child["id"]]
    assert (
        database.scalar(
            select(Notification.id).where(
                Notification.notification_type == "DEPARTMENT_HELP_RETURNED"
            )
        )
        is not None
    )
    actions = set(database.scalars(select(AuditLog.action).where(AuditLog.entity_type == "Ticket")))
    assert {"ticket.help.requested", "ticket.help.returned"} <= actions


def test_closing_escalation_child_closes_parent_as_parent_engineer(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    parent = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "HIGH",
            "urgency": "HIGH",
            "subject": "Parent escalation closure",
            "description": "Verify escalation child completion closes its parent.",
            "assigned_user_id": admin.id,
        },
    ).json()
    escalated = client.post(
        f"/api/v1/tickets/{parent['id']}/escalation",
        headers=admin_headers,
        json={
            "escalation_assignee_user_id": admin.id,
            "escalation_level": "SENIOR_ENGINEER",
            "reason": "Specialist investigation is required",
            "version": parent["version"],
        },
    )
    assert escalated.status_code == 200, escalated.text
    relation = database.scalar(
        select(TicketRelation).where(
            TicketRelation.source_ticket_id == parent["id"],
            TicketRelation.relation_type == "PARENT_CHILD",
        )
    )
    child = client.get(f"/api/v1/tickets/{relation.target_ticket_id}", headers=admin_headers).json()
    assert child["escalation_parent_ticket_id"] == parent["id"]
    started = client.post(
        f"/api/v1/tickets/{child['id']}/transition",
        headers=admin_headers,
        json={"to_status_code": "IN_PROGRESS", "version": child["version"]},
    )
    assert started.status_code == 200, started.text
    closed = client.post(
        f"/api/v1/tickets/{child['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "RESOLVED",
            "version": started.json()["version"],
            "close_after_resolve": True,
            "resolution_summary": "Specialist correction completed.",
            "root_cause_summary": "Escalated technical cause corrected.",
        },
    )
    assert closed.status_code == 200, closed.text
    database.expire_all()
    parent_row = database.get(Ticket, parent["id"])
    closed_status_id = database.scalar(select(TicketStatus.id).where(TicketStatus.code == "CLOSED"))
    assert parent_row.status_id == closed_status_id
    assert parent_row.resolution_summary == "Specialist correction completed."
    parent_events = list(
        database.scalars(
            select(EventOutbox).where(
                EventOutbox.aggregate_id == str(parent_row.id),
                EventOutbox.event_type == "TICKET_WORKFLOW_TRANSITION",
            )
        )
    )
    assert {json.loads(event.payload_json)["to_status_code"] for event in parent_events} >= {
        "RESOLVED",
        "CLOSED",
    }
    attributed = set(
        database.scalars(
            select(TicketStatusHistory.changed_by_user_id).where(
                TicketStatusHistory.ticket_id == parent_row.id
            )
        )
    )
    assert parent_row.assigned_user_id in attributed


def test_closing_escalation_parent_closes_active_children_as_parent_engineer(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    parent = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "HIGH",
            "urgency": "HIGH",
            "subject": "Parent-driven escalation closure",
            "description": "Closing the main ticket must close its escalation workstream.",
            "assigned_user_id": admin.id,
        },
    ).json()
    escalated = client.post(
        f"/api/v1/tickets/{parent['id']}/escalation",
        headers=admin_headers,
        json={
            "escalation_assignee_user_id": admin.id,
            "escalation_level": "SENIOR_ENGINEER",
            "reason": "Specialist investigation is required",
            "version": parent["version"],
        },
    )
    assert escalated.status_code == 200, escalated.text
    child = database.scalar(
        select(Ticket).where(Ticket.escalation_parent_ticket_id == parent["id"])
    )
    assert child is not None
    closed_parent = client.post(
        f"/api/v1/tickets/{parent['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "RESOLVED",
            "version": escalated.json()["version"],
            "close_after_resolve": True,
            "resolution_summary": "The main engineer verified the complete correction.",
            "root_cause_summary": "The escalated technical cause was corrected.",
        },
    )
    assert closed_parent.status_code == 200, closed_parent.text
    database.expire_all()
    child_row = database.get(Ticket, child.id)
    closed_status_id = database.scalar(select(TicketStatus.id).where(TicketStatus.code == "CLOSED"))
    assert child_row is not None and child_row.status_id == closed_status_id
    assert child_row.resolution_summary == "The main engineer verified the complete correction."
    child_histories = list(
        database.scalars(
            select(TicketStatusHistory)
            .where(TicketStatusHistory.ticket_id == child.id)
            .order_by(TicketStatusHistory.id)
        )
    )
    assert [item.source for item in child_histories[-2:]] == [
        "ESCALATION_PARENT",
        "ESCALATION_PARENT",
    ]
    audit = database.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "Ticket",
            AuditLog.entity_id == str(child.id),
            AuditLog.action == "ticket.closed_from_escalation_parent",
        )
    )
    assert audit is not None


def test_escalation_parent_waits_for_every_open_child(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    parent = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "HIGH",
            "urgency": "HIGH",
            "subject": "Parent with two escalation workstreams",
            "description": "The parent must remain open until both escalation children close.",
            "assigned_user_id": admin.id,
        },
    ).json()
    escalated = client.post(
        f"/api/v1/tickets/{parent['id']}/escalation",
        headers=admin_headers,
        json={
            "escalation_assignee_user_id": admin.id,
            "escalation_level": "SENIOR_ENGINEER",
            "reason": "Two specialist workstreams are required",
            "version": parent["version"],
        },
    )
    assert escalated.status_code == 200, escalated.text
    first_child = database.scalar(
        select(Ticket).where(Ticket.escalation_parent_ticket_id == parent["id"])
    )
    assert first_child is not None
    second_created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "Second escalation workstream",
            "description": "A second explicitly linked escalation child remains open.",
        },
    ).json()
    second_child = database.get(Ticket, second_created["id"])
    assert second_child is not None
    second_child.escalation_parent_ticket_id = parent["id"]
    database.commit()

    first_started = client.post(
        f"/api/v1/tickets/{first_child.id}/transition",
        headers=admin_headers,
        json={"to_status_code": "IN_PROGRESS", "version": first_child.version},
    )
    first_closed = client.post(
        f"/api/v1/tickets/{first_child.id}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "RESOLVED",
            "version": first_started.json()["version"],
            "close_after_resolve": True,
            "resolution_summary": "The first specialist workstream completed.",
            "root_cause_summary": "The first contributing cause was corrected.",
        },
    )
    assert first_closed.status_code == 200, first_closed.text
    database.expire_all()
    parent_row = database.get(Ticket, parent["id"])
    closed_status_id = database.scalar(select(TicketStatus.id).where(TicketStatus.code == "CLOSED"))
    assert parent_row is not None and parent_row.status_id != closed_status_id

    second_started = client.post(
        f"/api/v1/tickets/{second_child.id}/transition",
        headers=admin_headers,
        json={"to_status_code": "IN_PROGRESS", "version": second_created["version"]},
    )
    second_closed = client.post(
        f"/api/v1/tickets/{second_child.id}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "RESOLVED",
            "version": second_started.json()["version"],
            "close_after_resolve": True,
            "resolution_summary": "The final specialist workstream completed.",
            "root_cause_summary": "The remaining contributing cause was corrected.",
        },
    )
    assert second_closed.status_code == 200, second_closed.text
    database.expire_all()
    parent_row = database.get(Ticket, parent["id"])
    assert parent_row is not None and parent_row.status_id == closed_status_id
    parent_histories = list(
        database.scalars(
            select(TicketStatusHistory)
            .where(TicketStatusHistory.ticket_id == parent["id"])
            .order_by(TicketStatusHistory.id)
        )
    )
    assert [item.source for item in parent_histories[-2:]] == [
        "ESCALATION_CHILD",
        "ESCALATION_CHILD",
    ]


def test_escalation_parent_sync_failure_rolls_back_child_close(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    parent = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "HIGH",
            "urgency": "HIGH",
            "subject": "Atomic escalation closure",
            "description": "A parent synchronization failure must roll back the child close.",
            "assigned_user_id": admin.id,
        },
    ).json()
    escalated = client.post(
        f"/api/v1/tickets/{parent['id']}/escalation",
        headers=admin_headers,
        json={
            "escalation_assignee_user_id": admin.id,
            "escalation_level": "SENIOR_ENGINEER",
            "reason": "Specialist resolution requires atomic parent synchronization",
            "version": parent["version"],
        },
    )
    assert escalated.status_code == 200, escalated.text
    child = database.scalar(
        select(Ticket).where(Ticket.escalation_parent_ticket_id == parent["id"])
    )
    assert child is not None
    started = client.post(
        f"/api/v1/tickets/{child.id}/transition",
        headers=admin_headers,
        json={"to_status_code": "IN_PROGRESS", "version": child.version},
    )
    assert started.status_code == 200, started.text

    def fail_parent_sync(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("simulated parent synchronization failure")

    monkeypatch.setattr(
        "app.modules.tickets.routes.synchronize_escalation_parent",
        fail_parent_sync,
    )
    with pytest.raises(RuntimeError, match="simulated parent synchronization failure"):
        client.post(
            f"/api/v1/tickets/{child.id}/transition",
            headers=admin_headers,
            json={
                "to_status_code": "RESOLVED",
                "version": started.json()["version"],
                "close_after_resolve": True,
                "resolution_summary": "This close must be rolled back.",
                "root_cause_summary": "The test deliberately failed parent synchronization.",
            },
        )
    database.expire_all()
    child_row = database.get(Ticket, child.id)
    parent_row = database.get(Ticket, parent["id"])
    in_progress_status_id = database.scalar(
        select(TicketStatus.id).where(TicketStatus.code == "IN_PROGRESS")
    )
    closed_status_id = database.scalar(select(TicketStatus.id).where(TicketStatus.code == "CLOSED"))
    assert child_row is not None and child_row.status_id == in_progress_status_id
    assert parent_row is not None and parent_row.status_id != closed_status_id


def test_advanced_filter_ast_supports_nested_and_or(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    for subject, impact in (
        ("Nested filter critical case", "CRITICAL"),
        ("Nested filter routine case", "LOW"),
    ):
        created = client.post(
            "/api/v1/tickets",
            headers=admin_headers,
            json={
                "ticket_type_id": ticket_type_id,
                "client_id": client_id,
                "impact": impact,
                "urgency": impact,
                "subject": subject,
                "description": "Advanced filter test ticket details.",
            },
        )
        assert created.status_code == 201, created.text
    response = client.post(
        "/api/v1/tickets/advanced-search",
        headers=admin_headers,
        json={
            "filter": {
                "logic": "AND",
                "rules": [
                    {"field": "client_id", "operator": "eq", "value": client_id},
                    {
                        "logic": "OR",
                        "rules": [
                            {"field": "priority", "operator": "eq", "value": "P1"},
                            {"field": "subject", "operator": "contains", "value": "routine"},
                        ],
                    },
                ],
            }
        },
    )
    assert response.status_code == 200, response.text
    assert {item["subject"] for item in response.json()} == {
        "Nested filter critical case",
        "Nested filter routine case",
    }
    assert response.headers["x-total-count"] == "2"
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    bulk = client.post(
        "/api/v1/tickets/bulk-assignment",
        headers=admin_headers,
        json={
            "items": [
                {"ticket_id": item["id"], "expected_version": item["version"]}
                for item in response.json()
            ],
            "assigned_user_id": admin_id,
            "reason": "Assign filtered incidents to the duty engineer",
        },
    )
    assert bulk.status_code == 200, bulk.text
    assert bulk.json()["updated"] == 2


def test_ticket_tasks_and_checklist_lifecycle_are_audited(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "Task and checklist lifecycle",
            "description": "Verify task ownership, completion, checklist evidence, and audit history.",
            "follower_user_ids": [admin_id],
        },
    ).json()
    followers = client.get(f"/api/v1/tickets/{ticket['id']}/followers", headers=admin_headers)
    assert followers.status_code == 200
    assert [item["user_id"] for item in followers.json()] == [admin_id]
    cleared_followers = client.put(
        f"/api/v1/tickets/{ticket['id']}/followers",
        headers=admin_headers,
        json={
            "user_ids": [],
            "version": ticket["version"],
            "reason": "Follower verification completed",
        },
    )
    assert cleared_followers.status_code == 200, cleared_followers.text
    assert cleared_followers.json() == []
    task = client.post(
        f"/api/v1/tickets/{ticket['id']}/tasks",
        headers=admin_headers,
        json={"title": "Collect diagnostic logs", "assigned_user_id": admin_id},
    )
    assert task.status_code == 201, task.text
    completed_task = client.patch(
        f"/api/v1/tickets/{ticket['id']}/tasks/{task.json()['id']}",
        headers=admin_headers,
        json={"status": "COMPLETED"},
    )
    assert completed_task.status_code == 200, completed_task.text
    assert completed_task.json()["completed_at"] is not None
    tasks = client.get(f"/api/v1/tickets/{ticket['id']}/tasks", headers=admin_headers)
    assert [item["id"] for item in tasks.json()] == [task.json()["id"]]

    checklist = client.post(
        f"/api/v1/tickets/{ticket['id']}/checklist",
        headers=admin_headers,
        json={"label": "Backup confirmed", "sort_order": 1},
    )
    assert checklist.status_code == 201, checklist.text
    checked = client.patch(
        f"/api/v1/tickets/{ticket['id']}/checklist/{checklist.json()['id']}",
        headers=admin_headers,
        json={"is_completed": True},
    )
    assert checked.status_code == 200, checked.text
    assert checked.json()["completed_by_user_id"] == admin_id
    assert checked.json()["completed_at"] is not None
    actions = set(
        database.scalars(
            select(AuditLog.action).where(
                AuditLog.entity_type == "Ticket", AuditLog.entity_id == str(ticket["id"])
            )
        )
    )
    assert {
        "ticket.task.created",
        "ticket.task.updated",
        "ticket.checklist.created",
        "ticket.checklist.updated",
        "ticket.followers.updated",
    } <= actions


def test_required_work_blocks_resolution_unless_audited_override_is_authorized(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Resolution readiness",
            "description": "Required work must block resolution.",
        },
    ).json()
    task = client.post(
        f"/api/v1/tickets/{ticket['id']}/tasks",
        headers=admin_headers,
        json={"title": "Validate recovery"},
    )
    assert task.status_code == 201
    blocked = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "RESOLVED",
            "version": task.json()["ticket_id"] and ticket["version"] + 1,
            "resolution_summary": "Recovery is ready for review.",
            "root_cause_summary": "A configuration issue was corrected.",
        },
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "RESOLUTION_READINESS_BLOCKED"
    overridden = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "RESOLVED",
            "version": ticket["version"] + 1,
            "resolution_summary": "Recovery is ready for review.",
            "root_cause_summary": "A configuration issue was corrected.",
            "readiness_override_reason": "Customer-impacting service must be restored before remaining validation.",
        },
    )
    assert overridden.status_code == 200, overridden.text
    assert (
        database.scalar(
            select(AuditLog.id).where(
                AuditLog.entity_id == str(ticket["id"]),
                AuditLog.action == "ticket.resolution_readiness.overridden",
            )
        )
        is not None
    )


def test_ticket_create_comment_and_controlled_transition(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    users = client.get("/api/v1/users?limit=200", headers=admin_headers)
    admin_user_id = next(user["id"] for user in users.json() if user["username"] == "admin")
    caller = client.post(
        "/api/v1/contacts",
        headers=admin_headers,
        json={
            "client_id": client_id,
            "full_name": "Primary Caller",
            "phone_number": "+201001234567",
            "email": "caller@example.com",
        },
    )
    assert caller.status_code == 201, caller.text
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "requester_contact_id": caller.json()["id"],
            "assigned_user_id": admin_user_id,
            "impact": "CRITICAL",
            "urgency": "CRITICAL",
            "subject": "تعطل نظام الإنتاج الرئيسي",
            "description": "جميع المستخدمين غير قادرين على الوصول إلى نظام الإنتاج الرئيسي.",
        },
    )
    assert created.status_code == 201, created.text
    ticket = created.json()
    assert ticket["ticket_number"].startswith("INC-")
    assert ticket["priority"] == "P1"
    assert ticket["assigned_user_id"] == admin_user_id
    assert ticket["subject"] == "تعطل نظام الإنتاج الرئيسي"
    assert (
        ticket["description"] == "جميع المستخدمين غير قادرين على الوصول إلى نظام الإنتاج الرئيسي."
    )
    edited = client.patch(
        f"/api/v1/tickets/{ticket['id']}",
        headers=admin_headers,
        json={
            "subject": "تعطل نظام الإنتاج والخادم SQLSERVER01",
            "description": "تم تحديث الوصف العربي مع عنوان IP 192.168.1.10 بدون فقدان النص.",
            "reason": "التحقق من تحديث النص العربي",
            "version": ticket["version"],
        },
    )
    assert edited.status_code == 200, edited.text
    ticket = edited.json()
    reread = client.get(f"/api/v1/tickets/{ticket['id']}", headers=admin_headers)
    assert reread.status_code == 200, reread.text
    assert reread.json()["subject"] == "تعطل نظام الإنتاج والخادم SQLSERVER01"
    assert (
        reread.json()["description"]
        == "تم تحديث الوصف العربي مع عنوان IP 192.168.1.10 بدون فقدان النص."
    )
    assigned_status_id = database.scalar(
        select(TicketStatus.id).where(TicketStatus.code == "ASSIGNED")
    )
    assert ticket["status_id"] == assigned_status_id
    allowed = client.get(
        f"/api/v1/tickets/{ticket['id']}/allowed-transitions",
        headers=admin_headers,
    )
    assert allowed.status_code == 200, allowed.text
    allowed_codes = {item["code"] for item in allowed.json()}
    assert {"IN_PROGRESS", "RESOLVED", "CANCELLED"} <= allowed_codes
    comment = client.post(
        f"/api/v1/tickets/{ticket['id']}/comments",
        headers=admin_headers,
        json={"body": "جارٍ فحص حالة الخدمة على الخادم SQLSERVER01.", "is_internal": True},
    )
    assert comment.status_code == 201, comment.text
    comments = client.get(f"/api/v1/tickets/{ticket['id']}/comments", headers=admin_headers)
    assert comments.status_code == 200, comments.text
    assert comments.json()[-1]["body"] == "جارٍ فحص حالة الخدمة على الخادم SQLSERVER01."
    timeline = client.get(f"/api/v1/tickets/{ticket['id']}/timeline", headers=admin_headers)
    assert timeline.status_code == 200
    assert {item["event_type"] for item in timeline.json()} >= {
        "CREATED",
        "INTERNAL_NOTE",
        "STATUS_CHANGED",
    }
    stale_transition = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        headers=admin_headers,
        json={"to_status_code": "RESOLVED", "version": ticket["version"]},
    )
    assert stale_transition.status_code == 409
    current = client.get(f"/api/v1/tickets/{ticket['id']}", headers=admin_headers).json()
    invalid = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        headers=admin_headers,
        json={"to_status_code": "CLOSED", "version": current["version"]},
    )
    assert invalid.status_code == 409


def test_ticket_catalogs_are_seeded(database: Session) -> None:
    assert database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    assert database.scalar(select(TicketStatus.id).where(TicketStatus.code == "NEW"))


def test_start_progress_records_actor_and_rejects_repeat_submission(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "assigned_user_id": admin_id,
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Start progress exact once verification",
            "description": "This ticket verifies the dedicated start progress action audit.",
        },
    ).json()
    payload = {
        "to_status_code": "IN_PROGRESS",
        "reason": "Work started from ticket action",
        "version": created["version"],
    }
    started = client.post(
        f"/api/v1/tickets/{created['id']}/transition",
        headers=admin_headers,
        json=payload,
    )
    assert started.status_code == 200, started.text
    repeated = client.post(
        f"/api/v1/tickets/{created['id']}/transition",
        headers=admin_headers,
        json=payload,
    )
    assert repeated.status_code == 409
    in_progress_id = database.scalar(
        select(TicketStatus.id).where(TicketStatus.code == "IN_PROGRESS")
    )
    histories = list(
        database.scalars(
            select(TicketStatusHistory).where(
                TicketStatusHistory.ticket_id == created["id"],
                TicketStatusHistory.to_status_id == in_progress_id,
            )
        )
    )
    assert len(histories) == 1
    assert histories[0].changed_by_user_id == admin_id
    assert histories[0].created_at is not None
    assert histories[0].reason == "Work started from ticket action"


def test_pending_follow_up_is_owned_reminded_and_cleared_on_resume(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "assigned_user_id": admin_id,
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Pending follow-up workflow verification",
            "description": "This ticket verifies pending ownership, reminders, and resume cleanup.",
        },
    ).json()
    started = client.post(
        f"/api/v1/tickets/{created['id']}/transition",
        headers=admin_headers,
        json={"to_status_code": "IN_PROGRESS", "version": created["version"]},
    ).json()
    follow_up = server_now() + timedelta(hours=1)
    pending = client.post(
        f"/api/v1/tickets/{created['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "PENDING_INTERNAL",
            "reason": "Waiting for infrastructure confirmation",
            "pending_owner_user_id": admin_id,
            "pending_follow_up_at": follow_up.isoformat(),
            "version": started["version"],
        },
    )
    assert pending.status_code == 200, pending.text
    assert pending.json()["pending_owner_user_id"] == admin_id
    assert pending.json()["pending_reason"] == "Waiting for infrastructure confirmation"
    assert evaluate_escalations(database, now=follow_up + timedelta(minutes=1)) >= 1
    reminders = list(
        database.scalars(
            select(Notification).where(
                Notification.recipient_user_id == admin_id,
                Notification.notification_type == "PENDING_FOLLOW_UP_DUE",
            )
        )
    )
    assert len(reminders) == 1
    evaluate_escalations(database, now=follow_up + timedelta(minutes=2))
    assert (
        len(
            list(
                database.scalars(
                    select(Notification).where(
                        Notification.recipient_user_id == admin_id,
                        Notification.notification_type == "PENDING_FOLLOW_UP_DUE",
                    )
                )
            )
        )
        == 1
    )
    resumed = client.post(
        f"/api/v1/tickets/{created['id']}/transition",
        headers=admin_headers,
        json={"to_status_code": "IN_PROGRESS", "version": pending.json()["version"]},
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["pending_reason"] is None
    assert resumed.json()["pending_owner_user_id"] is None
    assert resumed.json()["pending_follow_up_at"] is None


def test_ticket_queue_advanced_filters(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    parent = client.post(
        "/api/v1/departments",
        headers=admin_headers,
        json={"code": "QUEUE_PARENT", "name": "Queue Parent", "is_active": True},
    ).json()
    child = client.post(
        "/api/v1/departments",
        headers=admin_headers,
        json={
            "code": "QUEUE_CHILD",
            "name": "Queue Child",
            "parent_department_id": parent["id"],
            "is_active": True,
        },
    ).json()
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    admin.department_id = child["id"]
    admin.department = child["name"]
    database.commit()
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "assigned_user_id": admin.id,
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Advanced queue filtering",
            "description": "Verify combined ticket queue filters and date range.",
        },
    )
    assert created.status_code == 201, created.text
    today = date.today()
    filtered = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={
            "client_id": client_id,
            "ticket_type_id": ticket_type_id,
            "priority": "P4",
            "created_by_user_id": admin.id,
            "department_id": child["id"],
            "parent_department_id": parent["id"],
            "created_from": today.isoformat(),
            "created_to": today.isoformat(),
        },
    )
    assert filtered.status_code == 200, filtered.text
    assert [item["id"] for item in filtered.json()] == [created.json()["id"]]
    assert filtered.json()[0]["created_by_name"] == admin.full_name
    assert filtered.json()[0]["department_name"] == "Queue Child"
    assert filtered.json()[0]["parent_department_name"] == "Queue Parent"
    ticket = database.get(Ticket, created.json()["id"])
    assert ticket is not None
    ticket.created_at = datetime.combine(today, time(12, 30), tzinfo=server_timezone())
    database.commit()
    before_exact_time = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"created_to": f"{today.isoformat()}T12:29"},
    )
    assert before_exact_time.status_code == 200, before_exact_time.text
    assert created.json()["id"] not in [item["id"] for item in before_exact_time.json()]
    within_exact_time = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={
            "created_from": f"{today.isoformat()}T12:30",
            "created_to": f"{today.isoformat()}T12:30",
        },
    )
    assert within_exact_time.status_code == 200, within_exact_time.text
    assert created.json()["id"] in [item["id"] for item in within_exact_time.json()]
    options = client.get("/api/v1/tickets/filter-options", headers=admin_headers)
    assert options.status_code == 200, options.text
    assert any(item["id"] == admin.id for item in options.json()["creators"])
    assert any(
        item["id"] == child["id"] and item["parent_department_id"] == parent["id"]
        for item in options.json()["departments"]
    )
    similar = client.get(
        "/api/v1/tickets/similar",
        headers=admin_headers,
        params={"subject": "Filtering the advanced support queue"},
    )
    assert similar.status_code == 200, similar.text
    assert similar.json()[0]["id"] == created.json()["id"]
    excluded = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"created_from": (today + timedelta(days=1)).isoformat()},
    )
    assert excluded.status_code == 200
    assert excluded.json() == []
    exported = client.get(
        "/api/v1/reports/tickets.csv",
        headers=admin_headers,
        params={
            "client_id": client_id,
            "priority": "P4",
            "created_by_user_id": admin.id,
            "department_id": child["id"],
            "parent_department_id": parent["id"],
            "columns": "ticket_number,created_by,department,parent_department",
        },
    )
    assert exported.status_code == 200, exported.text
    csv_text = exported.content.decode("utf-8-sig")
    assert "Ticket Number,Created By,Department,Parent Department" in csv_text
    assert "Queue Child,Queue Parent" in csv_text


def test_unassigned_filter_includes_shared_support_queue(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    support = User(
        full_name="Shared Support Queue",
        username="support-queue",
        username_normalized="support-queue",
        email="support-queue@example.com",
        email_normalized="support-queue@example.com",
        password_hash="not-used",
        user_type="EMPLOYEE",
        is_active=True,
    )
    database.add(support)
    database.flush()
    database.add(SiteSetting(key="default_assignee_user_id", value=str(support.id)))
    database.commit()

    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "assigned_user_id": support.id,
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Waiting in shared support queue",
            "description": "A shared queue assignment is not dedicated ownership.",
        },
    )
    assert created.status_code == 201, created.text

    unassigned = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"unassigned_only": True},
    )
    assert unassigned.status_code == 200, unassigned.text
    listed = next(item for item in unassigned.json() if item["id"] == created.json()["id"])
    assert listed["is_shared_assignment"] is True

    actor = database.scalar(select(User).where(User.username == "admin"))
    assert actor is not None
    claimed = client.post(
        f"/api/v1/tickets/{created.json()['id']}/claim",
        headers=admin_headers,
        json={"version": created.json()["version"]},
    )
    assert claimed.status_code == 200, claimed.text
    assert claimed.json()["assigned_user_id"] == actor.id
    assigned_status_id = database.scalar(
        select(TicketStatus.id).where(TicketStatus.code == "ASSIGNED")
    )
    assert claimed.json()["status_id"] == assigned_status_id

    refreshed = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"ticket_number": created.json()["ticket_number"]},
    )
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()[0]["is_shared_assignment"] is False


def test_live_update_link_exposes_only_public_comments(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Public live tracking",
            "description": "Verify secure customer-visible ticket updates.",
        },
    )
    assert created.status_code == 201, created.text
    ticket_id = created.json()["id"]
    assert (
        client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            headers=admin_headers,
            json={"body": "Visible customer update", "is_internal": False},
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            headers=admin_headers,
            json={"body": "Private engineering note", "is_internal": True},
        ).status_code
        == 201
    )

    issued = client.post(f"/api/v1/tickets/{ticket_id}/live-update-link", headers=admin_headers)
    assert issued.status_code == 200, issued.text
    token = parse_qs(urlparse(issued.json()["url"]).query)["token"][0]
    public = client.get("/api/v1/public/ticket-updates", params={"token": token})
    assert public.status_code == 200, public.text
    assert public.json()["ticket_number"] == created.json()["ticket_number"]
    assert public.json()["client_name"]
    assert public.json()["subject"] == "Public live tracking"
    assert public.json()["description"] == "Verify secure customer-visible ticket updates."
    assert public.json()["status"]
    assert public.json()["status_flow"]
    assert public.json()["resolution_seconds"] >= 0
    assert [item["body"] for item in public.json()["comments"]] == ["Visible customer update"]


def test_live_update_link_requires_dedicated_send_permission(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Permission-protected live tracking",
            "description": "Verify the dedicated live-update permission.",
        },
    )
    assert created.status_code == 201, created.text

    administrator = database.scalar(select(Profile).where(Profile.code == "ADMINISTRATOR"))
    permission = database.scalar(
        select(Permission).where(Permission.code == "ticket.live_update.send")
    )
    assert administrator is not None
    assert permission is not None
    assignment = database.scalar(
        select(ProfilePermission).where(
            ProfilePermission.profile_id == administrator.id,
            ProfilePermission.permission_id == permission.id,
        )
    )
    assert assignment is not None
    database.delete(assignment)
    database.commit()

    denied = client.post(
        f"/api/v1/tickets/{created.json()['id']}/live-update-link",
        headers=admin_headers,
    )
    assert denied.status_code == 403, denied.text


def test_live_update_exposes_redacted_escalation_and_idempotent_inline_satisfaction(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Public B-46 workflow",
            "description": "Verify safe escalation and inline rating.",
        },
    )
    assert created.status_code == 201, created.text
    ticket = database.get(Ticket, created.json()["id"])
    closed_id = database.scalar(select(TicketStatus.id).where(TicketStatus.code == "CLOSED"))
    assert ticket is not None and closed_id is not None
    open_id = database.scalar(select(TicketStatus.id).where(TicketStatus.code == "NEW"))
    assert open_id is not None
    ticket.status_id = open_id
    ticket.escalation_reason = "PRIVATE routing discussion must never be public"
    ticket.escalation_level = "TEAM_LEADER"
    database.add(
        TicketSlaInterval(
            ticket_id=ticket.id,
            interval_type="ESCALATION",
            comment="PRIVATE interval note",
            started_at=server_now(),
            created_by_user_id=ticket.created_by_user_id,
        )
    )
    survey_record = TicketSatisfaction(
        ticket_id=ticket.id,
        engineer_user_id=None,
        recipient_email="client@example.com",
        token_hash="a" * 64,
        token_ciphertext=None,
        expires_at=server_now() - timedelta(minutes=1),
    )
    database.add(survey_record)
    database.commit()

    issued = client.post(f"/api/v1/tickets/{ticket.id}/live-update-link", headers=admin_headers)
    token = parse_qs(urlparse(issued.json()["url"]).query)["token"][0]
    unavailable = client.get("/api/v1/public/ticket-updates", params={"token": token})
    assert unavailable.json()["satisfaction"] == {"state": "UNAVAILABLE"}
    ticket.status_id = closed_id
    database.commit()
    expired = client.get("/api/v1/public/ticket-updates", params={"token": token})
    assert expired.json()["satisfaction"] == {"state": "EXPIRED"}
    survey_record.expires_at = server_now() + timedelta(days=2)
    database.commit()
    public = client.get("/api/v1/public/ticket-updates", params={"token": token})
    assert public.status_code == 200, public.text
    payload = public.json()
    assert payload["satisfaction"] == {"state": "AVAILABLE"}
    assert payload["escalation"]["state"] == "ACTIVE"
    assert any(item["code"] == "ESCALATED" for item in payload["status_flow"])
    assert "PRIVATE" not in public.text
    assert "escalation_reason" not in public.text
    assert "assignee" not in public.text
    ticket.escalation_level = None
    database.commit()
    historical = client.get("/api/v1/public/ticket-updates", params={"token": token})
    assert historical.json()["escalation"]["state"] == "HISTORICAL"

    rating = {
        "ticket_rating": 5,
        "service_rating": 5,
        "engineer_rating": 4,
        "comments": "Resolved well.",
    }
    first = client.post(
        "/api/v1/public/ticket-updates/satisfaction", params={"token": token}, json=rating
    )
    second = client.post(
        "/api/v1/public/ticket-updates/satisfaction", params={"token": token}, json=rating
    )
    assert first.status_code == 200 and first.json()["already_submitted"] is False
    assert second.status_code == 200 and second.json()["already_submitted"] is True
    refreshed = client.get("/api/v1/public/ticket-updates", params={"token": token})
    assert refreshed.json()["satisfaction"] == {
        "state": "SUBMITTED",
        "ticket_rating": 5,
        "service_rating": 5,
        "engineer_rating": 4,
        "comments": "Resolved well.",
        "submitted_at": refreshed.json()["satisfaction"]["submitted_at"],
        "source": "LIVE_UPDATE",
    }
    ticket.status_id = open_id
    database.commit()
    reopened = client.get("/api/v1/public/ticket-updates", params={"token": token})
    assert reopened.json()["satisfaction"]["state"] == "SUBMITTED"
    assert reopened.json()["satisfaction"]["ticket_rating"] == 5
    database.expire_all()
    survey = database.scalar(
        select(TicketSatisfaction).where(TicketSatisfaction.ticket_id == ticket.id)
    )
    assert (
        survey is not None
        and survey.feedback_source == "LIVE_UPDATE"
        and survey.submitted_at is not None
    )


def test_manual_satisfaction_delivery_reuses_link_and_queues_email(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    caller = client.post(
        "/api/v1/contacts",
        headers=admin_headers,
        json={
            "client_id": client_id,
            "full_name": "Rating Caller",
            "phone_number": "+201001234567",
            "email": "rating@example.com",
        },
    )
    assert caller.status_code == 201, caller.text
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "requester_contact_id": caller.json()["id"],
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Manual satisfaction delivery",
            "description": "Verify channel delivery and secure token reuse.",
        },
    )
    assert created.status_code == 201, created.text
    ticket = database.get(Ticket, created.json()["id"])
    closed_id = database.scalar(select(TicketStatus.id).where(TicketStatus.code == "CLOSED"))
    assert ticket is not None and closed_id is not None
    ticket.status_id = closed_id
    database.add(SiteSetting(key="satisfaction_manual_enabled", value="true"))
    database.commit()

    first = client.post(
        f"/api/v1/tickets/{ticket.id}/satisfaction-delivery",
        headers=admin_headers,
        json={"channel": "WHATSAPP"},
    )
    second = client.post(
        f"/api/v1/tickets/{ticket.id}/satisfaction-delivery",
        headers=admin_headers,
        json={"channel": "WHATSAPP"},
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["url"] == second.json()["url"]
    assert first.json()["recipient"] == "+201001234567"

    copied = client.post(
        f"/api/v1/tickets/{ticket.id}/satisfaction-delivery",
        headers=admin_headers,
        json={"channel": "COPY", "contact_id": caller.json()["id"]},
    )
    assert copied.status_code == 200, copied.text
    assert copied.json()["message"] and copied.json()["url"] == first.json()["url"]

    manifest = client.get(
        f"/api/v1/tickets/{ticket.id}/send-actions",
        headers=admin_headers,
        params={"contact_id": caller.json()["id"]},
    )
    assert manifest.status_code == 200, manifest.text
    actions = {item["code"]: item for item in manifest.json()["actions"]}
    assert actions["LIVE_TRACKING"]["channels"] == {
        "COPY": True,
        "WHATSAPP": True,
        "EMAIL": True,
    }
    assert actions["SATISFACTION"]["channels"]["COPY"] is True

    email = client.post(
        f"/api/v1/tickets/{ticket.id}/satisfaction-delivery",
        headers=admin_headers,
        json={"channel": "EMAIL"},
    )
    assert email.status_code == 200, email.text
    assert email.json()["delivery_status"] == "QUEUED"
    assert (
        database.scalar(
            select(EventOutbox.id).where(EventOutbox.event_type == "SATISFACTION_INVITATION")
        )
        is not None
    )

    client_status_id = database.scalar(
        select(ClientStatus.id).where(ClientStatus.code == "ACTIVE")
    )
    other_client = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={
            "code": "SHARED-RATING-CLIENT",
            "name": "Shared Rating Client",
            "status_id": client_status_id,
        },
    )
    assert other_client.status_code == 201, other_client.text
    other_client_id = other_client.json()["id"]
    shared_caller = client.post(
        "/api/v1/contacts",
        headers=admin_headers,
        json={
            "client_id": other_client_id,
            "full_name": "Shared Rating Caller",
            "phone_number": "+201009876543",
            "email": "shared-rating@example.com",
        },
    )
    assert shared_caller.status_code == 201, shared_caller.text
    linked = client.post(
        f"/api/v1/clients/{client_id}/contacts/link",
        headers=admin_headers,
        json={"contact_id": shared_caller.json()["id"]},
    )
    assert linked.status_code == 200, linked.text

    shared_manifest = client.get(
        f"/api/v1/tickets/{ticket.id}/send-actions",
        headers=admin_headers,
        params={"contact_id": shared_caller.json()["id"]},
    )
    assert shared_manifest.status_code == 200, shared_manifest.text
    shared_copy = client.post(
        f"/api/v1/tickets/{ticket.id}/satisfaction-delivery",
        headers=admin_headers,
        json={"channel": "COPY", "contact_id": shared_caller.json()["id"]},
    )
    assert shared_copy.status_code == 200, shared_copy.text


def test_ticket_edit_updates_classification_and_audits_changes(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    category = client.post(
        "/api/v1/ticket-categories",
        headers=admin_headers,
        json={"code": "EDIT-CLASS", "name": "Editable classification"},
    ).json()
    subcategory = client.post(
        f"/api/v1/ticket-categories/{category['id']}/subcategories",
        headers=admin_headers,
        json={"code": "EDIT-SUB", "name": "Editable subcategory"},
    ).json()
    ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Classification editing verification",
            "description": "This ticket verifies audited classification editing.",
        },
    ).json()
    due_at = server_now() + timedelta(days=3)

    edited = client.patch(
        f"/api/v1/tickets/{ticket['id']}",
        headers=admin_headers,
        json={
            "category_id": category["id"],
            "subcategory_id": subcategory["id"],
            "affected_users": "Finance department",
            "patient_safety_flag": True,
            "security_incident_flag": True,
            "due_at": due_at.isoformat(),
            "reason": "Complete the incident classification",
            "version": ticket["version"],
        },
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["category_id"] == category["id"]
    assert edited.json()["subcategory_id"] == subcategory["id"]
    assert edited.json()["affected_users"] == "Finance department"
    assert edited.json()["patient_safety_flag"] is True
    assert edited.json()["due_at"] is not None
    audit = database.scalar(
        select(AuditLog)
        .where(AuditLog.entity_type == "Ticket", AuditLog.action == "ticket.edited")
        .order_by(AuditLog.id.desc())
    )
    assert audit is not None
    assert '"category_id"' in (audit.new_values_json or "")

    invalid = client.patch(
        f"/api/v1/tickets/{ticket['id']}",
        headers=admin_headers,
        json={
            "category_id": 999999,
            "reason": "Verify invalid category handling",
            "version": edited.json()["version"],
        },
    )
    assert invalid.status_code == 404
    inactive_category = client.post(
        "/api/v1/ticket-categories",
        headers=admin_headers,
        json={"code": "EDIT-INACTIVE", "name": "Inactive edit category"},
    ).json()
    category_row = database.get(TicketCategory, inactive_category["id"])
    assert category_row is not None
    category_row.is_active = False
    database.commit()
    inactive = client.patch(
        f"/api/v1/tickets/{ticket['id']}",
        headers=admin_headers,
        json={
            "category_id": inactive_category["id"],
            "reason": "Verify inactive category handling",
            "version": edited.json()["version"],
        },
    )
    assert inactive.status_code == 404
    assert "inactive" in inactive.json()["error"]["message"].lower()


def test_ticket_attachment_upload_list_and_secure_download(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
    tmp_path: Path,
) -> None:
    attachment_settings = Settings(
        app_env="test",
        secret_key="test-secret-key-with-more-than-thirty-two-characters",
        database_url="sqlite+pysqlite://",
        attachment_storage_path=str(tmp_path),
    )
    original_override = client.app.dependency_overrides[get_settings]
    client.app.dependency_overrides[get_settings] = lambda: attachment_settings
    try:
        client_id = create_test_client(client, admin_headers, database)
        ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
        ticket = client.post(
            "/api/v1/tickets",
            headers=admin_headers,
            json={
                "ticket_type_id": ticket_type_id,
                "client_id": client_id,
                "impact": "MEDIUM",
                "urgency": "MEDIUM",
                "subject": "Attachment workflow verification",
                "description": "This ticket verifies secure attachment upload and download.",
            },
        ).json()
        upload_payload = {"operation_key": "attachment-retry-001"}
        uploaded = client.post(
            f"/api/v1/tickets/{ticket['id']}/attachments",
            headers=admin_headers,
            files={"file": ("diagnostic.pdf", b"%PDF-1.7\ntest", "application/pdf")},
            data=upload_payload,
        )
        assert uploaded.status_code == 201, uploaded.text
        replay = client.post(
            f"/api/v1/tickets/{ticket['id']}/attachments",
            headers=admin_headers,
            files={"file": ("diagnostic.pdf", b"%PDF-1.7\ntest", "application/pdf")},
            data=upload_payload,
        )
        assert replay.status_code == 201, replay.text
        assert replay.json()["id"] == uploaded.json()["id"]
        changed = client.post(
            f"/api/v1/tickets/{ticket['id']}/attachments",
            headers=admin_headers,
            files={"file": ("different.pdf", b"%PDF-1.7\ndifferent", "application/pdf")},
            data=upload_payload,
        )
        assert changed.status_code == 409
        assert changed.json()["error"]["code"] == "ATTACHMENT_IDEMPOTENCY_CONFLICT"
        assert uploaded.json()["original_filename"] == "diagnostic.pdf"
        metadata = database.get(TicketAttachment, uploaded.json()["id"])
        assert metadata.stored_filename != "diagnostic.pdf"
        assert (tmp_path / str(ticket["id"]) / metadata.stored_filename).is_file()

        listed = client.get(f"/api/v1/tickets/{ticket['id']}/attachments", headers=admin_headers)
        assert [item["id"] for item in listed.json()] == [uploaded.json()["id"]]
        downloaded = client.get(
            f"/api/v1/tickets/{ticket['id']}/attachments/{uploaded.json()['id']}/download",
            headers=admin_headers,
        )
        assert downloaded.status_code == 200
        assert downloaded.content == b"%PDF-1.7\ntest"
        assert database.scalar(
            select(AuditLog.id).where(AuditLog.action == "ticket.attachment.uploaded")
        )

        rejected = client.post(
            f"/api/v1/tickets/{ticket['id']}/attachments",
            headers=admin_headers,
            files={"file": ("unsafe.html", b"<script></script>", "text/html")},
        )
        assert rejected.status_code == 415
        disguised = client.post(
            f"/api/v1/tickets/{ticket['id']}/attachments",
            headers=admin_headers,
            files={"file": ("disguised.pdf", b"MZ executable", "application/pdf")},
        )
        assert disguised.status_code == 415
        assert disguised.json()["error"]["code"] == "ATTACHMENT_CONTENT_INVALID"
    finally:
        client.app.dependency_overrides[get_settings] = original_override


def test_related_ticket_create_prevents_duplicates_and_can_be_removed(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))

    def create_ticket(subject: str) -> dict[str, object]:
        response = client.post(
            "/api/v1/tickets",
            headers=admin_headers,
            json={
                "ticket_type_id": ticket_type_id,
                "client_id": client_id,
                "impact": "MEDIUM",
                "urgency": "MEDIUM",
                "subject": subject,
                "description": "Related ticket workflow verification details.",
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    first = create_ticket("Primary incident for relationship")
    second = create_ticket("Related incident for relationship")
    created = client.post(
        f"/api/v1/tickets/{first['id']}/relations",
        headers=admin_headers,
        json={
            "related_ticket_id": second["id"],
            "relation_type": "RELATED",
            "reason": "Same underlying service interruption",
        },
    )
    assert created.status_code == 201, created.text
    reverse_duplicate = client.post(
        f"/api/v1/tickets/{second['id']}/relations",
        headers=admin_headers,
        json={"related_ticket_id": first["id"], "relation_type": "RELATED"},
    )
    assert reverse_duplicate.status_code == 409
    assert reverse_duplicate.json()["error"]["code"] == "RELATION_EXISTS"
    second_relations = client.get(
        f"/api/v1/tickets/{second['id']}/relations", headers=admin_headers
    ).json()
    assert second_relations[0]["related_ticket_id"] == first["id"]
    assert second_relations[0]["direction"] == "INCOMING"
    removed = client.delete(
        f"/api/v1/tickets/{first['id']}/relations/{created.json()['id']}",
        headers=admin_headers,
    )
    assert removed.status_code == 204
    assert (
        client.get(f"/api/v1/tickets/{first['id']}/relations", headers=admin_headers).json() == []
    )


def test_inactive_client_is_preserved_as_pending_approval(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "SUSPENDED"))
    inactive = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={
            "code": "INACTIVE-TICKET",
            "name": "Inactive Ticket Client",
            "status_id": status_id,
            "is_active": True,
        },
    )
    assert inactive.status_code == 201, inactive.text
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    payload = {
        "ticket_type_id": ticket_type_id,
        "client_id": inactive.json()["id"],
        "impact": "MEDIUM",
        "urgency": "MEDIUM",
        "subject": "Inactive client support request",
        "description": "An internal agent is recording a request for an inactive client.",
    }
    response = client.post("/api/v1/tickets", headers=admin_headers, json=payload)
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["entitlement_status"] == "PENDING_APPROVAL"
    assert created["assigned_user_id"] is None
    assert created["contract_id"] is None
    assert (
        database.scalar(select(TicketSlaClock.id).where(TicketSlaClock.ticket_id == created["id"]))
        is None
    )
    approval = database.scalar(
        select(EntitlementApproval).where(EntitlementApproval.ticket_id == created["id"])
    )
    assert approval is not None and approval.status == "PENDING"


def test_admin_can_choose_ticket_priority(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    response = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "LOW",
            "urgency": "LOW",
            "priority": "P1",
            "subject": "Explicit priority support request",
            "description": "An authorized user explicitly classified this request as priority one.",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["priority"] == "P1"


def test_resolve_requires_root_cause_and_can_then_close(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    original_service = ServiceCatalogItem(
        code="RESOLUTION-ORIGINAL-SERVICE", name="Original Recorded Service"
    )
    provided_service = ServiceCatalogItem(
        code="RESOLUTION-PROVIDED-SERVICE",
        name="Service Actually Provided",
        is_default_resolution_service=True,
    )
    additional_service = ServiceCatalogItem(
        code="RESOLUTION-ADDITIONAL-SERVICE", name="Additional Service Provided"
    )
    database.add_all([original_service, provided_service, additional_service])
    database.commit()
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "assigned_user_id": admin_id,
            "service_id": original_service.id,
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "Resolution workflow verification",
            "description": "This ticket verifies resolution and root-cause workflow fields.",
        },
    ).json()
    missing_root_cause = client.post(
        f"/api/v1/tickets/{created['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "RESOLVED",
            "version": created["version"],
            "resolution_summary": "Service restored successfully.",
        },
    )
    assert missing_root_cause.status_code == 409
    resolved = client.post(
        f"/api/v1/tickets/{created['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "RESOLVED",
            "version": created["version"],
            "reason": "Technical work completed",
            "resolution_summary": "Restarted the failed application service.",
            "root_cause_summary": "A stale service credential prevented startup.",
        },
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["root_cause_summary"].startswith("A stale")
    assert resolved.json()["service_id"] == original_service.id
    assert resolved.json()["resolution_service_ids"] == [provided_service.id]
    service_audit = database.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "Ticket",
            AuditLog.entity_id == str(created["id"]),
            AuditLog.action == "ticket.resolution_services.changed",
        )
    )
    assert service_audit is not None
    database.expire_all()
    assert (
        database.scalar(
            select(TicketArticleLink.id).where(TicketArticleLink.ticket_id == created["id"])
        )
        is None
    )
    closed = client.post(
        f"/api/v1/tickets/{created['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "CLOSED",
            "version": resolved.json()["version"],
            "resolution_service_ids": [provided_service.id, additional_service.id],
        },
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["resolution_service_ids"] == [
        provided_service.id,
        additional_service.id,
    ]


def test_site_setting_defers_resolution_details_to_close_and_exposes_missing_queue(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    service = ServiceCatalogItem(
        code="DEFERRED-CLOSE-SERVICE",
        name="Deferred closure service",
        is_default_resolution_service=True,
    )
    database.add_all(
        [
            service,
            SiteSetting(key="resolution_details_required_on_close", value="true"),
        ]
    )
    database.commit()
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "assigned_user_id": admin_id,
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "Deferred resolution evidence",
            "description": "Resolve first, then require closure evidence.",
        },
    ).json()

    resolved = client.post(
        f"/api/v1/tickets/{created['id']}/transition",
        headers=admin_headers,
        json={"to_status_code": "RESOLVED", "version": created["version"]},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["resolution_summary"] is None

    awaiting_close = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"incomplete_resolution_only": True},
    )
    assert awaiting_close.status_code == 200, awaiting_close.text
    assert created["id"] in {item["id"] for item in awaiting_close.json()}

    missing = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"assistant_module": "missing-resolution"},
    )
    assert missing.status_code == 200, missing.text
    assert created["id"] in {item["id"] for item in missing.json()}

    blocked_close = client.post(
        f"/api/v1/tickets/{created['id']}/transition",
        headers=admin_headers,
        json={"to_status_code": "CLOSED", "version": resolved.json()["version"]},
    )
    assert blocked_close.status_code == 409
    assert blocked_close.json()["error"]["code"] == "RESOLUTION_REQUIRED"

    closed = client.post(
        f"/api/v1/tickets/{created['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "CLOSED",
            "version": resolved.json()["version"],
            "resolution_summary": "Restored and verified the affected service.",
            "root_cause_summary": "A stale service credential prevented startup.",
            "resolution_service_ids": [service.id],
            "create_knowledge_article": True,
        },
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["resolution_summary"].startswith("Restored")
    assert closed.json()["resolution_service_ids"] == [service.id]
    assert database.scalar(
        select(TicketArticleLink.id).where(
            TicketArticleLink.ticket_id == created["id"],
            TicketArticleLink.reason == "AUTO_RESOLUTION_DRAFT",
        )
    ) is not None

    after_close = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"assistant_module": "missing-resolution"},
    )
    assert created["id"] not in {item["id"] for item in after_close.json()}


def test_root_cause_conditionally_requires_permanent_fix_and_creates_kb_draft(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    cause = RootCause(
        code="RECURRING-CONFIG",
        name="Recurring configuration fault",
        is_active=True,
        requires_permanent_fix=True,
    )
    database.add(cause)
    database.commit()
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "assigned_user_id": admin_id,
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "Conditional resolution fields",
            "description": "Verify root-cause-driven resolution UX and knowledge draft.",
        },
    ).json()
    payload = {
        "to_status_code": "RESOLVED",
        "version": created["version"],
        "resolution_summary": "Restored the configuration.",
        "root_cause_ids": [cause.id],
    }
    missing = client.post(
        f"/api/v1/tickets/{created['id']}/transition", headers=admin_headers, json=payload
    )
    assert (
        missing.status_code == 409 and missing.json()["error"]["code"] == "PERMANENT_FIX_REQUIRED"
    )
    resolved = client.post(
        f"/api/v1/tickets/{created['id']}/transition",
        headers=admin_headers,
        json={
            **payload,
            "permanent_fix_status": "PLANNED",
            "permanent_fix_summary": "Deploy the governed configuration next maintenance window.",
            "create_knowledge_article": True,
        },
    )
    assert resolved.status_code == 200, resolved.text
    database.expire_all()
    link = database.scalar(
        select(TicketArticleLink).where(
            TicketArticleLink.ticket_id == created["id"],
            TicketArticleLink.reason == "AUTO_RESOLUTION_DRAFT",
        )
    )
    assert link is not None
    article = database.get(Article, link.article_id)
    assert article is not None and article.status == "DRAFT" and article.visibility == "INTERNAL"
    ticket_category = database.scalar(
        select(KnowledgeCategory).where(
            KnowledgeCategory.code == "TICKETS_KNOWLEDGE_BASE"
        )
    )
    assert ticket_category is not None
    assert article.category_id == ticket_category.id
    assert article.category == "Tickets Knowledge Base"
    assert article.client_ids == [created["client_id"]]
    assert article.root_cause_ids == [cause.id]
    assert article.resolution_summary_template == payload["resolution_summary"]
    assert article.permanent_fix_status == "PLANNED"
    assert article.permanent_fix_summary_template == (
        "Deploy the governed configuration next maintenance window."
    )


def test_resolve_can_close_immediately_and_save_user_default(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    preference = client.put(
        "/api/v1/auth/me/resolve-preference",
        headers=admin_headers,
        json={"auto_close_on_resolve": True},
    )
    assert preference.status_code == 200, preference.text
    assert preference.json()["auto_close_on_resolve"] is True
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "assigned_user_id": admin_id,
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "Immediate closure after resolution",
            "description": "Verify the optional combined resolved and closed workflow.",
        },
    ).json()
    result = client.post(
        f"/api/v1/tickets/{created['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "RESOLVED",
            "version": created["version"],
            "resolution_summary": "Issue corrected and validated with the requester.",
            "root_cause_summary": "Incorrect application configuration caused the issue.",
            "close_after_resolve": True,
        },
    )
    assert result.status_code == 200, result.text
    closed_status_id = database.scalar(select(TicketStatus.id).where(TicketStatus.code == "CLOSED"))
    assert result.json()["status_id"] == closed_status_id
    database.expire_all()
    histories = list(
        database.scalars(
            select(TicketStatusHistory)
            .where(TicketStatusHistory.ticket_id == created["id"])
            .order_by(TicketStatusHistory.id)
        )
    )
    status_codes = dict(database.execute(select(TicketStatus.id, TicketStatus.code)).all())
    assert [status_codes[item.to_status_id] for item in histories[-2:]] == [
        "RESOLVED",
        "CLOSED",
    ]
    stored = database.get(User, database.scalar(select(User.id).where(User.username == "admin")))
    assert stored is not None and stored.auto_close_on_resolve is True


def test_cancel_and_reopen_manage_terminal_timestamps(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Cancellation and reopen timestamp policy",
            "description": "Verify terminal lifecycle timestamps are mutually consistent.",
        },
    ).json()
    cancelled = client.post(
        f"/api/v1/tickets/{created['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "CANCELLED",
            "version": created["version"],
            "reason": "The requester confirmed that this ticket is no longer required.",
        },
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["cancelled_at"] is not None
    assert cancelled.json()["resolved_at"] is None
    assert cancelled.json()["closed_at"] is None
    reopened = client.post(
        f"/api/v1/tickets/{created['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "REOPENED",
            "version": cancelled.json()["version"],
            "reason": "The requester reproduced the issue and needs engineering work again.",
        },
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["reopened_at"] is not None
    assert reopened.json()["cancelled_at"] is None
    assert reopened.json()["resolved_at"] is None
    assert reopened.json()["closed_at"] is None


def test_reopened_ticket_can_return_to_progress_then_resolve_or_close(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "assigned_user_id": admin_id,
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "Reopened ticket second resolution",
            "description": "Verify reopened work can complete through the normal workflow again.",
        },
    ).json()
    first_resolution = client.post(
        f"/api/v1/tickets/{created['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "RESOLVED",
            "version": created["version"],
            "resolution_summary": "Applied and verified the first correction.",
            "root_cause_summary": "Initial configuration fault.",
        },
    )
    assert first_resolution.status_code == 200, first_resolution.text
    reopened = client.post(
        f"/api/v1/tickets/{created['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "REOPENED",
            "version": first_resolution.json()["version"],
            "reason": "The problem occurred again during customer verification.",
        },
    )
    assert reopened.status_code == 200, reopened.text
    in_progress = client.post(
        f"/api/v1/tickets/{created['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "IN_PROGRESS",
            "version": reopened.json()["version"],
            "reason": "Engineering resumed work on the reopened ticket.",
        },
    )
    assert in_progress.status_code == 200, in_progress.text

    allowed = client.get(
        f"/api/v1/tickets/{created['id']}/allowed-transitions",
        headers=admin_headers,
    )
    assert allowed.status_code == 200, allowed.text
    assert {item["code"] for item in allowed.json()} >= {"RESOLVED", "CLOSED"}

    second_resolution = client.post(
        f"/api/v1/tickets/{created['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "RESOLVED",
            "version": in_progress.json()["version"],
            "resolution_summary": "Applied and verified the permanent correction.",
            "root_cause_summary": "A stale configuration value survived the first correction.",
        },
    )
    assert second_resolution.status_code == 200, second_resolution.text
    assert second_resolution.json()["resolved_at"] is not None


def test_engineer_assignment_creates_visible_ticket_and_notification(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    profile = database.scalar(select(Profile).where(Profile.code == "L1_SUPPORT"))
    engineer = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "full_name": "Assigned Engineer",
            "username": "assigned.engineer",
            "email": "assigned.engineer@example.com",
            "password": "TemporaryPassword!123",
            "primary_profile_id": profile.id,
            "additional_profile_ids": [],
            "client_scope_ids": [],
            "branch_scope_ids": [],
            "user_type": "EMPLOYEE",
            "department": "Support",
            "require_password_change": False,
        },
    )
    assert engineer.status_code == 201, engineer.text
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "Engineer assignment verification",
            "description": "This ticket verifies assignment visibility and UI notifications.",
        },
    ).json()
    assigned = client.post(
        f"/api/v1/tickets/{ticket['id']}/assignment",
        headers=admin_headers,
        json={
            "assigned_user_id": engineer.json()["id"],
            "assigned_team": "Support",
            "reason": "Assign to available engineer",
            "version": ticket["version"],
        },
    )
    assert assigned.status_code == 200, assigned.text
    database.expire_all()
    history = database.scalar(
        select(TicketAssignmentHistory).where(TicketAssignmentHistory.ticket_id == ticket["id"])
    )
    assert history is not None
    assert history.assigned_user_id == engineer.json()["id"]
    recent = client.get(
        "/api/v1/ticket-assignees",
        headers=admin_headers,
        params={"q": "assigned.engineer"},
    )
    assert recent.status_code == 200, recent.text
    assert [item["id"] for item in recent.json()] == [engineer.json()["id"]]
    assert recent.json()[0]["last_assigned_at"] is not None
    login = client.post(
        "/api/v1/auth/login",
        json={"login": "assigned.engineer", "password": "TemporaryPassword!123"},
    )
    engineer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    visible = client.get("/api/v1/tickets", headers=engineer_headers)
    assert any(item["id"] == ticket["id"] for item in visible.json())
    notifications = client.get("/api/v1/notifications", headers=engineer_headers)
    assert notifications.json()[0]["notification_type"] == "TICKET_ASSIGNED"
    assert notifications.json()[0]["deep_link"] == f"/tickets/{ticket['id']}"
    assert {item["notification_type"] for item in notifications.json()} >= {"TICKET_ASSIGNED"}


def test_self_assignment_requires_only_self_permission_and_moves_ticket_to_assigned(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_test_client(client, admin_headers, database)
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "Board self-assignment verification",
            "description": "Dropping this card into Assigned should claim it for the actor.",
        },
    ).json()
    actor = database.scalar(select(User).where(User.username == "admin"))
    team_permission = database.scalar(
        select(Permission).where(Permission.code == "ticket.assign.team")
    )
    assert actor is not None and team_permission is not None
    database.add(
        UserPermissionOverride(
            user_id=actor.id,
            permission_id=team_permission.id,
            effect=Effect.DENY,
            reason="Verify independent ticket.assign.self permission",
            created_by_user_id=actor.id,
        )
    )
    database.commit()

    assigned = client.post(
        f"/api/v1/tickets/{ticket['id']}/claim",
        headers=admin_headers,
        json={"version": ticket["version"]},
    )

    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["assigned_user_id"] == actor.id
    status_code = database.scalar(
        select(TicketStatus.code).where(TicketStatus.id == assigned.json()["status_id"])
    )
    assert status_code == "ASSIGNED"
    forbidden = client.post(
        f"/api/v1/tickets/{ticket['id']}/assignment",
        headers=admin_headers,
        json={
            "assigned_user_id": actor.id + 99999,
            "assigned_team": None,
            "reason": "Self permission must not assign another engineer",
            "version": assigned.json()["version"],
        },
    )
    assert forbidden.status_code == 403, forbidden.text
