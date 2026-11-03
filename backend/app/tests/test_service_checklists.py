from datetime import timedelta
from urllib.parse import urlparse

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.modules.clients.models import Client, ClientStatus
from app.modules.iam.models import Effect, Permission, User, UserPermissionOverride
from app.modules.iam.security import create_access_token, hash_password
from app.modules.iam.service import effective_permissions
from app.modules.notifications.models import EventOutbox, Notification
from app.modules.service_checklists.models import (
    ServiceChecklistOccurrence,
    ServiceChecklistSchedule,
    ServiceDeliveryRecord,
)
from app.modules.tickets.models import Ticket, TicketStatus, TicketTask
from app.tests.conftest import TEST_SETTINGS


def payload(*, responsibility: str = "MILLENSYS", evidence_type: str = "NONE") -> dict[str, object]:
    return {
        "code": "MONTHLY_PACS",
        "name": "Monthly PACS health check",
        "description": "Controlled monthly customer service checklist.",
        "schedule_mode": "SCHEDULED",
        "items": [
            {
                "item_code": "VERIFY_BACKUP",
                "title": "Verify the latest backup",
                "display_order": 0,
                "is_required": True,
                "responsibility": responsibility,
                "evidence_type": evidence_type,
                "evidence_required": responsibility in {"CLIENT", "SHARED"},
                "expected_duration_minutes": 20,
            }
        ],
    }


def test_assignee_lookup_uses_checklist_permission_not_user_management(
    client: TestClient, database: Session
) -> None:
    actor = database.scalar(select(User).where(User.username == "admin"))
    permission = database.scalar(
        select(Permission).where(Permission.code == "service_checklist.reassign")
    )
    assert actor is not None and permission is not None
    coordinator = User(
        full_name="Checklist Coordinator",
        username="checklist.coordinator",
        username_normalized="checklist.coordinator",
        email="checklist.coordinator@example.com",
        email_normalized="checklist.coordinator@example.com",
        password_hash=hash_password("ChecklistPassword!123"),
        user_type="EMPLOYEE",
        is_active=True,
        require_password_change=False,
    )
    database.add(coordinator)
    database.flush()
    database.add(
        UserPermissionOverride(
            user_id=coordinator.id,
            permission_id=permission.id,
            effect=Effect.ALLOW,
            reason="Checklist assignee lookup regression",
            created_by_user_id=actor.id,
        )
    )
    database.commit()
    permissions = set(effective_permissions(database, coordinator).permissions)
    assert "service_checklist.reassign" in permissions
    assert "user.manage" not in permissions

    response = client.get(
        "/api/v1/service-checklists/assignees",
        headers={"Authorization": f"Bearer {create_access_token(coordinator.id, TEST_SETTINGS)}"},
    )

    assert response.status_code == 200, response.text
    assert coordinator.id in {item["id"] for item in response.json()}


def test_template_lifecycle_is_versioned_and_published_templates_are_immutable(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    created = client.post(
        "/api/v1/service-checklists/templates", headers=admin_headers, json=payload()
    )
    assert created.status_code == 201, created.text
    template = created.json()
    assert template["publication_status"] == "DRAFT"
    assert template["items"][0]["responsibility"] == "MILLENSYS"

    changed = {**payload(), "name": "Monthly PACS readiness", "version": template["version"]}
    changed.pop("code")
    updated = client.put(
        f"/api/v1/service-checklists/templates/{template['id']}",
        headers=admin_headers,
        json=changed,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["version"] == 2

    published = client.post(
        f"/api/v1/service-checklists/templates/{template['id']}/publish",
        headers=admin_headers,
    )
    assert published.status_code == 200, published.text
    assert published.json()["publication_status"] == "PUBLISHED"

    changed["version"] = published.json()["version"]
    immutable = client.put(
        f"/api/v1/service-checklists/templates/{template['id']}",
        headers=admin_headers,
        json=changed,
    )
    assert immutable.status_code == 409


def test_client_responsibility_requires_evidence(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    invalid = payload(responsibility="CLIENT")
    invalid["items"][0]["evidence_required"] = False  # type: ignore[index]
    rejected = client.post(
        "/api/v1/service-checklists/templates", headers=admin_headers, json=invalid
    )
    assert rejected.status_code == 422

    accepted = client.post(
        "/api/v1/service-checklists/templates",
        headers=admin_headers,
        json=payload(responsibility="CLIENT", evidence_type="FILE"),
    )
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["items"][0]["evidence_required"] is True


def test_operational_completion_records_delivery_and_generates_one_next_occurrence(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    template_payload = payload()
    template_payload["items"].append(  # type: ignore[union-attr]
        {
            "item_code": "CLIENT_ARCHIVE",
            "title": "Client archives the exported study",
            "display_order": 1,
            "is_required": True,
            "responsibility": "CLIENT",
            "evidence_type": "FILE",
            "evidence_required": True,
        }
    )
    template = client.post(
        "/api/v1/service-checklists/templates", headers=admin_headers, json=template_payload
    ).json()
    client.post(
        f"/api/v1/service-checklists/templates/{template['id']}/publish",
        headers=admin_headers,
    )
    status = database.scalar(select(ClientStatus))
    customer = Client(
        code="CHECKLIST-CUSTOMER",
        name="Checklist Customer",
        status_id=status.id,
        timezone="Africa/Cairo",
    )
    database.add(customer)
    database.commit()
    database.refresh(customer)
    now = server_now()
    occurrence = client.post(
        "/api/v1/service-checklists/occurrences",
        headers=admin_headers,
        json={
            "template_id": template["id"],
            "client_id": customer.id,
            "scheduled_at": now.isoformat(),
            "due_at": (now.replace(microsecond=0) + timedelta(hours=2)).isoformat(),
            "recurrence_days": 7,
        },
    )
    assert occurrence.status_code == 201, occurrence.text
    row = occurrence.json()
    assert row["ticket_id"] is not None
    generated_ticket = database.get(Ticket, row["ticket_id"])
    assert generated_ticket is not None
    assert generated_ticket.contract_id is None
    assert (
        database.scalar(
            select(TicketStatus.code).where(TicketStatus.id == generated_ticket.status_id)
        )
        == "PENDING_INTERNAL"
    )
    assert (
        len(
            list(
                database.scalars(
                    select(TicketTask).where(TicketTask.ticket_id == generated_ticket.id)
                )
            )
        )
        == 2
    )
    started = client.post(
        f"/api/v1/service-checklists/occurrences/{row['id']}/start",
        headers=admin_headers,
        json={"version": row["version"]},
    ).json()
    database.expire_all()
    assert (
        database.scalar(
            select(TicketStatus.code)
            .join(Ticket, Ticket.status_id == TicketStatus.id)
            .where(Ticket.id == row["ticket_id"])
        )
        == "IN_PROGRESS"
    )
    client_item = next(item for item in started["items"] if item["responsibility"] == "CLIENT")
    evidence = client.post(
        f"/api/v1/service-checklists/occurrences/{row['id']}/evidence",
        headers=admin_headers,
        files={"upload": ("handoff.png", b"\x89PNG\r\n\x1a\nchecklist-proof", "image/png")},
    )
    assert evidence.status_code == 201, evidence.text
    handed_off = client.post(
        f"/api/v1/service-checklists/occurrences/{row['id']}/items/{client_item['id']}/client-handoff",
        headers=admin_headers,
        json={
            "version": started["version"],
            "client_contact": "Client IT",
            "handoff_note": "Archive ownership transferred to Client IT.",
            "evidence_id": evidence.json()["id"],
        },
    )
    assert handed_off.status_code == 200, handed_off.text
    millensys_item = next(
        item for item in handed_off.json()["items"] if item["responsibility"] != "CLIENT"
    )
    checked = client.put(
        f"/api/v1/service-checklists/occurrences/{row['id']}/items/{millensys_item['id']}",
        headers=admin_headers,
        json={
            "version": handed_off.json()["version"],
            "resource_type": "DATABASE",
            "title": "Database Backup",
            "resource_path": "//server/backup",
            "check_date": server_now().isoformat(),
            "status": "COMPLETE",
        },
    )
    assert checked.status_code == 200, checked.text
    completed = client.post(
        f"/api/v1/service-checklists/occurrences/{row['id']}/complete",
        headers=admin_headers,
        json={
            "version": checked.json()["version"],
            "service_provided": "Weekly PACS verification",
            "completion_summary": "All Millensys tasks completed; archive transferred to Client IT.",
            "complete_eligible_remaining": True,
        },
    )
    assert completed.status_code == 200, completed.text
    result = completed.json()
    assert result["occurrence"]["status"] == "COMPLETED"
    assert result["next_occurrence_number"].startswith("SCL-")
    assert result["next_scheduled_at"] != row["scheduled_at"]
    next_occurrence = client.get(
        f"/api/v1/service-checklists/occurrences/{result['next_occurrence_id']}",
        headers=admin_headers,
    ).json()
    carried = next(item for item in next_occurrence["items"] if item["title"] == "Database Backup")
    assert carried["resource_type"] == "DATABASE"
    assert carried["resource_path"] == "//server/backup"
    assert carried["state"] == "PENDING" and carried["check_date"] is None
    assert database.scalar(select(ServiceDeliveryRecord)) is not None
    database.expire_all()
    linked_ticket = database.get(Ticket, result["occurrence"]["ticket_id"])
    assert database.get(TicketStatus, linked_ticket.status_id).code == "CLOSED"
    assert linked_ticket.resolved_at is not None and linked_ticket.closed_at is not None
    assert {
        task.status
        for task in database.scalars(
            select(TicketTask).where(TicketTask.ticket_id == linked_ticket.id)
        )
    } == {"COMPLETED"}


def test_recurring_schedule_creates_linked_work_and_can_pause(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    template = client.post(
        "/api/v1/service-checklists/templates", headers=admin_headers, json=payload()
    ).json()
    client.post(
        f"/api/v1/service-checklists/templates/{template['id']}/publish",
        headers=admin_headers,
    )
    status = database.scalar(select(ClientStatus))
    customer = Client(code="SCHEDULE-CUSTOMER", name="Schedule Customer", status_id=status.id)
    database.add(customer)
    database.commit()
    database.refresh(customer)
    starts = server_now() + timedelta(days=2)
    schedule = client.post(
        "/api/v1/service-checklists/schedules",
        headers=admin_headers,
        json={
            "name": "Weekly schedule",
            "template_id": template["id"],
            "client_id": customer.id,
            "starts_at": starts.isoformat(),
            "interval_days": 7,
            "duration_minutes": 480,
            "timezone": "Africa/Cairo",
        },
    )
    assert schedule.status_code == 201, schedule.text
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    assert schedule.json()["assigned_user_id"] == admin_id
    listed = client.get("/api/v1/service-checklists/occurrences", headers=admin_headers).json()
    assert len(listed) == 1 and listed[0]["schedule_id"] == schedule.json()["id"]
    assert listed[0]["ticket_id"] is not None
    checklist_ticket = database.get(Ticket, listed[0]["ticket_id"])
    assert checklist_ticket is not None and checklist_ticket.contract_id is None
    assert (
        database.scalar(
            select(TicketStatus.code).where(TicketStatus.id == checklist_ticket.status_id)
        )
        == "PENDING_INTERNAL"
    )
    assignments = client.get("/api/v1/service-checklists/schedules", headers=admin_headers).json()
    assert assignments[0]["client_name"] == customer.name
    assert assignments[0]["template_name"] == template["name"]
    assert assignments[0]["last_occurrence_id"] == listed[0]["id"]
    history = client.get(
        f"/api/v1/service-checklists/schedules/{schedule.json()['id']}/history",
        headers=admin_headers,
        params={
            "date_from": (starts - timedelta(days=1)).isoformat(),
            "date_to": (starts + timedelta(days=1)).isoformat(),
        },
    )
    assert history.status_code == 200, history.text
    assert [event["id"] for event in history.json()] == [listed[0]["id"]]
    ticket_create_permission = database.scalar(
        select(Permission).where(Permission.code == "ticket.create")
    )
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert ticket_create_permission is not None and admin is not None
    database.add(
        UserPermissionOverride(
            user_id=admin.id,
            permission_id=ticket_create_permission.id,
            effect=Effect.DENY,
            reason="Checklist events create system tickets without ticket.create",
            created_by_user_id=admin.id,
        )
    )
    database.commit()
    opened_event = client.post(
        f"/api/v1/service-checklists/schedules/{schedule.json()['id']}/events",
        headers=admin_headers,
    )
    assert opened_event.status_code == 200, opened_event.text
    assert opened_event.json()["id"] == listed[0]["id"]
    assert opened_event.json()["status"] == "IN_PROGRESS"
    assert opened_event.json()["items"]
    exported = client.get(
        f"/api/v1/service-checklists/occurrences/{listed[0]['id']}/export.xlsx",
        headers=admin_headers,
    )
    assert exported.status_code == 200
    assert exported.content.startswith(b"PK")
    shared = client.post(
        f"/api/v1/service-checklists/occurrences/{listed[0]['id']}/share",
        headers=admin_headers,
    )
    assert shared.status_code == 200, shared.text
    token = urlparse(shared.json()["url"]).path.rsplit("/", 1)[-1]
    public = client.get(f"/api/v1/public/service-checklists/{token}")
    assert public.status_code == 200, public.text
    assert public.json()["client_name"] == customer.name
    assert public.json()["tasks"][0]["title"] == "Verify the latest backup"
    paused = client.post(
        f"/api/v1/service-checklists/schedules/{schedule.json()['id']}/state",
        headers=admin_headers,
        json={"version": schedule.json()["version"], "paused": True},
    )
    assert paused.status_code == 200 and paused.json()["is_paused"] is True
    cadence = client.post(
        f"/api/v1/service-checklists/schedules/{schedule.json()['id']}/cadence",
        headers=admin_headers,
        json={"version": paused.json()["version"], "interval_days": 30},
    )
    assert cadence.status_code == 200, cadence.text
    assert cadence.json()["interval_days"] == 30
    report = client.get("/api/v1/service-checklists/reports/summary", headers=admin_headers)
    assert report.status_code == 200 and report.json()["total"] == 1


def test_bulk_assign_and_transfer_preserve_completed_history(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    template = client.post(
        "/api/v1/service-checklists/templates", headers=admin_headers, json=payload()
    ).json()
    client.post(
        f"/api/v1/service-checklists/templates/{template['id']}/publish",
        headers=admin_headers,
    )
    status = database.scalar(select(ClientStatus))
    customers = [
        Client(code=f"BULK-{index}", name=f"Bulk Client {index}", status_id=status.id)
        for index in range(1, 3)
    ]
    database.add_all(customers)
    database.commit()
    for customer in customers:
        database.refresh(customer)
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    support = User(
        full_name="Transfer Engineer",
        username="transfer.engineer",
        username_normalized="transfer.engineer",
        email="transfer.engineer@example.com",
        email_normalized="transfer.engineer@example.com",
        password_hash=hash_password("TransferPassword!123"),
        user_type="EMPLOYEE",
        is_active=True,
        require_password_change=False,
    )
    database.add(support)
    database.commit()
    database.refresh(support)
    assigned = client.post(
        "/api/v1/service-checklists/schedules/bulk-assign",
        headers=admin_headers,
        json={
            "client_ids": [customer.id for customer in customers],
            "assigned_user_id": admin.id,
            "template_id": template["id"],
            "starts_at": (server_now() + timedelta(days=1)).isoformat(),
            "interval_days": 7,
            "duration_minutes": 120,
        },
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json() == {"created": 2, "skipped": 0, "skipped_client_ids": []}
    schedules = list(
        database.scalars(select(ServiceChecklistSchedule).order_by(ServiceChecklistSchedule.id))
    )
    assert len(schedules) == 2
    occurrences = list(
        database.scalars(select(ServiceChecklistOccurrence).order_by(ServiceChecklistOccurrence.id))
    )
    occurrences[0].status = "COMPLETED"
    original_completed_owner = occurrences[0].assigned_user_id
    database.commit()

    transferred = client.post(
        "/api/v1/service-checklists/schedules/bulk-transfer",
        headers=admin_headers,
        json={
            "items": [{"schedule_id": row.id, "version": row.version} for row in schedules],
            "assigned_user_id": support.id,
            "reason": "Redistribute the client portfolio",
        },
    )
    assert transferred.status_code == 200, transferred.text
    assert transferred.json()["transferred"] == 2
    database.expire_all()
    refreshed_occurrences = list(
        database.scalars(select(ServiceChecklistOccurrence).order_by(ServiceChecklistOccurrence.id))
    )
    assert refreshed_occurrences[0].assigned_user_id == original_completed_owner
    assert refreshed_occurrences[1].assigned_user_id == support.id
    schedules[0].assigned_user_id = admin.id
    schedules[1].assigned_user_id = support.id
    for schedule_row in schedules:
        schedule_row.next_generate_at = server_now() - timedelta(days=1)
    database.commit()
    reminded = client.post(
        "/api/v1/service-checklists/schedules/bulk-reminders",
        headers=admin_headers,
        json={"schedule_ids": [row.id for row in schedules]},
    )
    assert reminded.status_code == 200, reminded.text
    assert reminded.json() == {"sent": 2, "deduplicated": 0}
    assert (
        len(
            list(
                database.scalars(
                    select(Notification).where(
                        Notification.notification_type == "SERVICE_CHECKLIST_MANUAL_REMINDER"
                    )
                )
            )
        )
        == 2
    )
    repeated = client.post(
        "/api/v1/service-checklists/schedules/bulk-reminders",
        headers=admin_headers,
        json={"schedule_ids": [row.id for row in schedules]},
    )
    assert repeated.json() == {"sent": 0, "deduplicated": 2}


def test_reminders_send_one_digest_email_per_engineer(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    template = client.post(
        "/api/v1/service-checklists/templates", headers=admin_headers, json=payload()
    ).json()
    client.post(
        f"/api/v1/service-checklists/templates/{template['id']}/publish",
        headers=admin_headers,
    )
    status = database.scalar(select(ClientStatus))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert status is not None and admin is not None
    customers = [
        Client(code=f"DIGEST-{index}", name=f"Digest Client {index}", status_id=status.id)
        for index in range(1, 3)
    ]
    database.add_all(customers)
    database.commit()
    due = server_now() + timedelta(hours=2)
    for customer in customers:
        response = client.post(
            "/api/v1/service-checklists/occurrences",
            headers=admin_headers,
            json={
                "template_id": template["id"],
                "client_id": customer.id,
                "assigned_user_id": admin.id,
                "scheduled_at": server_now().isoformat(),
                "due_at": due.isoformat(),
            },
        )
        assert response.status_code == 201, response.text

    processed = client.post(
        "/api/v1/service-checklists/occurrences/process-reminders",
        headers=admin_headers,
    )

    assert processed.status_code == 200, processed.text
    assert processed.json()["notifications_created"] == 2
    assert processed.json()["digest_emails_created"] == 1
    digests = list(
        database.scalars(
            select(EventOutbox).where(EventOutbox.aggregate_type == "ServiceChecklistDigest")
        )
    )
    assert len(digests) == 1
    assert "Digest Client 1" in digests[0].payload_json
    assert "Digest Client 2" in digests[0].payload_json


def test_monitor_uses_earliest_open_event_after_horizon_generation(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    template = client.post(
        "/api/v1/service-checklists/templates", headers=admin_headers, json=payload()
    ).json()
    client.post(
        f"/api/v1/service-checklists/templates/{template['id']}/publish",
        headers=admin_headers,
    )
    status = database.scalar(select(ClientStatus))
    customer = Client(code="MONITOR-CURRENT", name="Monitor Current", status_id=status.id)
    database.add(customer)
    database.commit()
    starts = server_now() - timedelta(days=2)
    schedule = client.post(
        "/api/v1/service-checklists/schedules",
        headers=admin_headers,
        json={
            "name": "Daily monitor",
            "template_id": template["id"],
            "client_id": customer.id,
            "starts_at": starts.isoformat(),
            "interval_days": 1,
            "duration_minutes": 60,
            "timezone": "Africa/Cairo",
        },
    ).json()
    first_id = schedule["last_occurrence_id"]
    generated = client.post(
        "/api/v1/service-checklists/schedule-generation/run", headers=admin_headers
    )
    assert generated.status_code == 200 and generated.json()["generated"] > 1
    monitored = client.get("/api/v1/service-checklists/schedules", headers=admin_headers).json()[0]
    assert monitored["last_occurrence_id"] == first_id
    assert monitored["last_due_at"] < server_now().isoformat()


def test_evidence_cannot_be_bypassed_and_cancelled_event_is_read_only(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    template_payload = payload()
    template_payload["items"][0]["evidence_type"] = "FILE"  # type: ignore[index]
    template_payload["items"][0]["evidence_required"] = True  # type: ignore[index]
    template = client.post(
        "/api/v1/service-checklists/templates", headers=admin_headers, json=template_payload
    ).json()
    client.post(
        f"/api/v1/service-checklists/templates/{template['id']}/publish", headers=admin_headers
    )
    status = database.scalar(select(ClientStatus))
    customer = Client(code="EVIDENCE-GUARD", name="Evidence Guard", status_id=status.id)
    database.add(customer)
    database.commit()
    created = client.post(
        "/api/v1/service-checklists/occurrences",
        headers=admin_headers,
        json={
            "template_id": template["id"],
            "client_id": customer.id,
            "scheduled_at": server_now().isoformat(),
            "due_at": (server_now() + timedelta(hours=1)).isoformat(),
        },
    ).json()
    item = created["items"][0]
    bypass = client.put(
        f"/api/v1/service-checklists/occurrences/{created['id']}/items/{item['id']}",
        headers=admin_headers,
        json={
            "version": created["version"],
            "resource_type": item["resource_type"],
            "title": item["title"],
            "check_date": server_now().isoformat(),
            "status": "COMPLETE",
        },
    )
    assert bypass.status_code == 409
    cancelled = client.post(
        f"/api/v1/service-checklists/occurrences/{created['id']}/cancel",
        headers=admin_headers,
        json={"version": created["version"], "reason": "Duplicate event"},
    ).json()
    edited = client.put(
        f"/api/v1/service-checklists/occurrences/{created['id']}/items/{item['id']}",
        headers=admin_headers,
        json={
            "version": cancelled["version"],
            "resource_type": item["resource_type"],
            "title": item["title"],
            "check_date": server_now().isoformat(),
            "status": "PENDING",
        },
    )
    assert edited.status_code == 409 and "CHECKLIST_READ_ONLY" in edited.text


def test_manual_event_uses_template_tasks_and_rows_can_be_edited_or_deleted(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    template = client.post(
        "/api/v1/service-checklists/templates", headers=admin_headers, json=payload()
    ).json()
    client.post(
        f"/api/v1/service-checklists/templates/{template['id']}/publish",
        headers=admin_headers,
    )
    status = database.scalar(select(ClientStatus))
    customer = Client(code="TEMPLATE-TASKS", name="Template Tasks", status_id=status.id)
    database.add(customer)
    database.commit()
    schedule = client.post(
        "/api/v1/service-checklists/schedules",
        headers=admin_headers,
        json={
            "name": "Template-only events",
            "template_id": template["id"],
            "client_id": customer.id,
            "starts_at": server_now().isoformat(),
            "interval_days": 30,
            "duration_minutes": 60,
            "timezone": "Africa/Cairo",
        },
    ).json()
    event = client.get(
        f"/api/v1/service-checklists/occurrences/{schedule['last_occurrence_id']}",
        headers=admin_headers,
    ).json()
    item = event["items"][0]
    edited = client.patch(
        f"/api/v1/service-checklists/occurrences/{event['id']}/items/{item['id']}/details",
        headers=admin_headers,
        json={
            "version": event["version"],
            "resource_type": "CUSTOM",
            "title": "Client-specific task title",
            "resource_path": "C:/client-only",
            "check_date": server_now().isoformat(),
        },
    )
    assert edited.status_code == 200, edited.text
    cancelled = client.post(
        f"/api/v1/service-checklists/occurrences/{event['id']}/cancel",
        headers=admin_headers,
        json={"version": edited.json()["version"], "reason": "Start a fresh event"},
    )
    assert cancelled.status_code == 200, cancelled.text
    fresh = client.post(
        f"/api/v1/service-checklists/schedules/{schedule['id']}/events",
        headers=admin_headers,
    )
    assert fresh.status_code == 200, fresh.text
    assert [row["title"] for row in fresh.json()["items"]] == ["Verify the latest backup"]
    deleted = client.delete(
        f"/api/v1/service-checklists/occurrences/{fresh.json()['id']}/items/{fresh.json()['items'][0]['id']}",
        headers=admin_headers,
        params={"expected_version": fresh.json()["version"]},
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["items"] == []


def test_quick_completion_closes_the_linked_ticket(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    template = client.post(
        "/api/v1/service-checklists/templates", headers=admin_headers, json=payload()
    ).json()
    client.post(
        f"/api/v1/service-checklists/templates/{template['id']}/publish",
        headers=admin_headers,
    )
    status = database.scalar(select(ClientStatus))
    customer = Client(code="QUICK-CLOSE", name="Quick Close", status_id=status.id)
    database.add(customer)
    database.commit()
    now = server_now()
    created = client.post(
        "/api/v1/service-checklists/occurrences",
        headers=admin_headers,
        json={
            "template_id": template["id"],
            "client_id": customer.id,
            "scheduled_at": now.isoformat(),
            "due_at": (now + timedelta(hours=1)).isoformat(),
        },
    )
    assert created.status_code == 201, created.text
    event = created.json()
    completed = client.post(
        f"/api/v1/service-checklists/occurrences/{event['id']}/quick-complete",
        headers=admin_headers,
        json={
            "version": event["version"],
            "items": [
                {
                    "item_id": event["items"][0]["id"],
                    "choice": "DONE",
                    "check_date": now.isoformat(),
                }
            ],
            "service_provided": "Checklist service completed",
            "completion_summary": "All checklist tasks completed.",
            "complete": True,
        },
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["occurrence"]["status"] == "COMPLETED"
    database.expire_all()
    ticket = database.get(Ticket, event["ticket_id"])
    assert ticket is not None
    assert database.get(TicketStatus, ticket.status_id).code == "CLOSED"
    assert ticket.resolved_at is not None and ticket.closed_at is not None
    assert {
        task.status
        for task in database.scalars(select(TicketTask).where(TicketTask.ticket_id == ticket.id))
    } == {"COMPLETED"}
