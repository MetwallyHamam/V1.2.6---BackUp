import json
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import case, select
from sqlalchemy.dialects import mssql
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.core.config import get_settings
from app.modules.clients.models import ClientStatus
from app.modules.iam.models import Permission, ProfilePermission, User, UserProfile
from app.modules.iam.security import hash_password
from app.modules.internal_operations.models import InternalOperation
from app.modules.kpis.service import calculate_metrics
from app.modules.notifications.email_service import process_email_outbox
from app.modules.notifications.models import EventOutbox
from app.modules.tickets.models import Ticket, TicketType
from app.modules.work_assignments.models import (
    WorkAssignment,
    WorkAssignmentEvidence,
    WorkAssignmentLink,
)

PERMISSIONS = {
    "work_assignment.view.department",
    "work_assignment.view.all",
    "work_assignment.create",
    "work_assignment.claim",
    "work_assignment.manage",
    "work_assignment.share",
}


def test_due_date_ordering_compiles_for_sql_server() -> None:
    due_date_rank = case((WorkAssignment.due_at.is_(None), 1), else_=0)
    statement = select(WorkAssignment).order_by(
        due_date_rank,
        WorkAssignment.due_at,
        WorkAssignment.created_at.desc(),
    )
    sql = str(statement.compile(dialect=mssql.dialect()))  # type: ignore[no-untyped-call]
    assert "ORDER BY CASE WHEN" in sql


def _prepare_users(db: Session) -> tuple[User, User]:
    admin = db.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    profile_id = db.scalar(select(UserProfile.profile_id).where(UserProfile.user_id == admin.id))
    assert profile_id is not None
    for code in PERMISSIONS:
        permission = Permission(code=code, module="work_assignment", description=code, is_high_risk=False, is_active=True)
        db.add(permission); db.flush()
        db.add(ProfilePermission(profile_id=profile_id, permission_id=permission.id, scope_type="NONE"))
    engineer = User(full_name="Second Engineer", username="engineer.two", username_normalized="engineer.two", email="engineer.two@example.com", email_normalized="engineer.two@example.com", password_hash=hash_password("EngineerPassword!123"), user_type="EMPLOYEE", is_active=True, require_password_change=False)
    db.add(engineer); db.commit(); db.refresh(admin); db.refresh(engineer)
    return admin, engineer


def test_multiple_engineers_lifecycle_share_and_kpi_credit(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    admin, engineer = _prepare_users(database)
    due = (server_now() + timedelta(days=2)).isoformat()
    created = client.post("/api/v1/work-assignments", headers=admin_headers, json={
        "title": "Upgrade client systems", "description": "Coordinate and complete the approved upgrade.",
        "assignment_type": "SYSTEM_UPGRADE", "activity_classification": "EXTERNAL", "priority": "HIGH", "complexity": "COMPLEX", "due_at": due,
        "owner_user_id": admin.id, "assignees": [
            {"user_id": admin.id, "role": "OWNER", "contribution_percent": 60},
            {"user_id": engineer.id, "role": "CONTRIBUTOR", "contribution_percent": 40},
        ], "requires_review": False,
    })
    assert created.status_code == 200, created.text
    assignment = created.json()
    assert len(assignment["assignees"]) == 2
    started = client.post(f"/api/v1/work-assignments/{assignment['id']}/transition", headers=admin_headers, json={"action": "START", "expected_version": assignment["version"]})
    assert started.status_code == 200, started.text
    completed = client.post(f"/api/v1/work-assignments/{assignment['id']}/transition", headers=admin_headers, json={"action": "COMPLETE", "expected_version": started.json()["version"], "actual_minutes": 90, "detail": "Upgrade verified."})
    assert completed.status_code == 200, completed.text
    shared = client.post(f"/api/v1/work-assignments/{assignment['id']}/shares", headers=admin_headers, json={})
    assert shared.status_code == 200, shared.text
    public = client.get(f"/api/v1/public/work-assignments/{shared.json()['url_token']}")
    assert public.status_code == 200
    assert public.json()["status"] == "COMPLETED"
    metrics = calculate_metrics(database, admin.id, server_now() - timedelta(days=1), server_now() + timedelta(days=1))
    assert metrics["external_assignment_equivalents"] == 0.6


def test_conversion_prevents_duplicate_assignment_kpi_credit(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    admin, _ = _prepare_users(database)
    operation = InternalOperation(title="Follow-up execution", operation_type="NORMAL", status="SCHEDULED", starts_at=server_now(), ends_at=server_now() + timedelta(hours=1), created_by_user_id=admin.id)
    database.add(operation); database.commit(); database.refresh(operation)
    created = client.post("/api/v1/work-assignments", headers=admin_headers, json={"title": "Follow up ticket", "description": "Own this client-facing follow-up.", "activity_classification": "EXTERNAL", "owner_user_id": admin.id, "assignees": [{"user_id": admin.id, "role": "OWNER", "contribution_percent": 100}]})
    assert created.status_code == 200, created.text
    row = created.json()
    converted = client.post(f"/api/v1/work-assignments/{row['id']}/conversion", headers=admin_headers, json={"target_type": "INTERNAL_OPERATION", "target_id": operation.id, "expected_version": row["version"]})
    assert converted.status_code == 200, converted.text
    started = client.post(f"/api/v1/work-assignments/{row['id']}/transition", headers=admin_headers, json={"action": "START", "expected_version": converted.json()["version"]})
    completed = client.post(f"/api/v1/work-assignments/{row['id']}/transition", headers=admin_headers, json={"action": "COMPLETE", "expected_version": started.json()["version"], "detail": "Converted work verified."})
    assert completed.status_code == 200
    metrics = calculate_metrics(database, admin.id, server_now() - timedelta(days=1), server_now() + timedelta(days=1))
    assert metrics["external_assignment_equivalents"] == 0.0


def test_block_transition_requires_and_persists_evidence(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    admin, _ = _prepare_users(database)
    created = client.post(
        "/api/v1/work-assignments",
        headers=admin_headers,
        json={"title": "Diagnose blocked deployment", "description": "Record why deployment cannot proceed.", "owner_user_id": admin.id, "assignees": [{"user_id": admin.id, "role": "OWNER", "contribution_percent": 100}]},
    ).json()
    started = client.post(f"/api/v1/work-assignments/{created['id']}/transition", headers=admin_headers, json={"action": "START", "expected_version": created["version"]}).json()
    rejected = client.post(f"/api/v1/work-assignments/{created['id']}/transition", headers=admin_headers, json={"action": "BLOCK", "expected_version": started["version"]})
    assert rejected.status_code == 409

    blocked = client.post(
        f"/api/v1/work-assignments/{created['id']}/transition-with-evidence",
        headers=admin_headers,
        data={"action": "BLOCK", "expected_version": started["version"], "detail": "Firewall approval is still pending."},
        files={"file": ("firewall.txt", b"Approval request REF-42", "text/plain")},
    )
    assert blocked.status_code == 200, blocked.text
    assert blocked.json()["status"] == "BLOCKED"
    assert blocked.json()["evidence"][0]["original_filename"] == "firewall.txt"
    evidence = database.scalar(select(WorkAssignmentEvidence).where(WorkAssignmentEvidence.assignment_id == created["id"]))
    assert evidence is not None
    assert evidence.note == "Firewall approval is still pending."


def test_assignee_can_create_and_atomically_link_converted_ticket(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    admin, _ = _prepare_users(database)
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    client_response = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "ASSIGNMENT-CONVERSION", "name": "Assignment Conversion Client", "status_id": status_id},
    )
    assert client_response.status_code == 201, client_response.text
    assignment_response = client.post(
        "/api/v1/work-assignments",
        headers=admin_headers,
        json={
            "title": "Investigate client issue",
            "description": "Investigate and convert this task into a governed ticket.",
            "assignment_type": "TICKET_CANDIDATE",
            "client_ids": [client_response.json()["id"]],
            "owner_user_id": admin.id,
            "assignees": [{"user_id": admin.id, "role": "OWNER", "contribution_percent": 100}],
        },
    )
    assert assignment_response.status_code == 200, assignment_response.text
    assignment = assignment_response.json()
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    converted = client.post(
        f"/api/v1/work-assignments/{assignment['id']}/convert-to-ticket",
        headers=admin_headers,
        json={
            "expected_version": assignment["version"],
            "ticket": {
                "ticket_type_id": ticket_type_id,
                "client_id": client_response.json()["id"],
                "impact": "LOW",
                "urgency": "LOW",
                "subject": "Converted client issue",
                "description": "Created atomically from the assigned engineering task.",
            },
        },
    )
    assert converted.status_code == 201, converted.text
    ticket_id = converted.json()["id"]
    assert database.get(Ticket, ticket_id) is not None
    database.expire_all()
    row = database.get(WorkAssignment, assignment["id"])
    assert row is not None
    assert (row.kpi_source_type, row.kpi_source_id) == ("TICKET", ticket_id)
    link = database.scalar(select(WorkAssignmentLink).where(WorkAssignmentLink.assignment_id == row.id, WorkAssignmentLink.target_id == ticket_id))
    assert link is not None
    assert link.relation_type == "CONVERTED_TO"


def test_creator_can_edit_saved_assignment_and_new_assignee_receives_email_link(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    admin, engineer = _prepare_users(database)
    created = client.post(
        "/api/v1/work-assignments",
        headers=admin_headers,
        json={
            "title": "Review saved task",
            "description": "Review the saved assignment before execution.",
            "owner_user_id": admin.id,
            "assignees": [{"user_id": admin.id, "role": "OWNER", "contribution_percent": 100}],
        },
    )
    assert created.status_code == 200, created.text
    row = created.json()
    updated = client.put(
        f"/api/v1/work-assignments/{row['id']}",
        headers=admin_headers,
        json={
            "expected_version": row["version"],
            "title": "Review updated saved task",
            "description": "Review the edited assignment before execution.",
            "activity_classification": "EXTERNAL",
            "owner_user_id": admin.id,
            "assignees": [
                {"user_id": admin.id, "role": "OWNER", "contribution_percent": 50},
                {"user_id": engineer.id, "role": "CONTRIBUTOR", "contribution_percent": 50},
            ],
            "context": {"expected_outcome": "Validated task"},
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "Review updated saved task"
    assert {item["user_id"] for item in updated.json()["assignees"]} == {admin.id, engineer.id}
    events = list(database.scalars(select(EventOutbox).where(EventOutbox.event_type == "WORK_ASSIGNMENT_EMAIL").order_by(EventOutbox.id)))
    assert len(events) == 2
    initial_payload = json.loads(events[0].payload_json)
    edited_payload = json.loads(events[1].payload_json)
    assert initial_payload["recipient_user_ids"] == [admin.id]
    assert edited_payload["recipient_user_ids"] == [engineer.id]
    assert edited_payload["deep_link"] == f"/work-assignments?assignment_id={row['id']}"
    sent: list[tuple[str, str, str]] = []
    counts = process_email_outbox(
        database,
        get_settings(),
        sender=lambda recipient, subject, body: sent.append((recipient, subject, body)),
    )
    assert counts["sent"] == 2
    assert {recipient for recipient, _, _ in sent} == {admin.email, engineer.email}
    assert all(f"work-assignments?assignment_id={row['id']}" in body for _, _, body in sent)
