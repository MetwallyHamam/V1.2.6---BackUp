import io
from datetime import UTC, date, datetime

from docx import Document
from docx.enum.section import WD_ORIENT
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Client, ClientStatus
from app.modules.contracts.models import SlaPolicy, TicketSlaClock
from app.modules.iam.models import AuditLog, Permission, Profile, ProfilePermission, User
from app.modules.tickets.models import Ticket, TicketStatus, TicketType


def test_client_hours_matches_profile_for_reopened_ticket(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    open_status = database.scalar(select(TicketStatus).where(TicketStatus.code == "IN_PROGRESS"))
    closed_status = database.scalar(select(TicketStatus).where(TicketStatus.code == "CLOSED"))
    ticket_type_id = database.scalar(select(TicketType.id))
    policy_id = database.scalar(select(SlaPolicy.id))
    actor_id = database.scalar(select(User.id).where(User.username == "admin"))
    customer = Client(code="HOURS-REOPENED", name="Reopened hours client", status_id=status_id)
    database.add(customer)
    database.flush()
    completed_at = datetime(2026, 9, 10, 12, tzinfo=UTC)
    ticket = Ticket(
        ticket_number="HOURS-REOPENED-1",
        ticket_type_id=ticket_type_id,
        client_id=customer.id,
        created_by_user_id=actor_id,
        status_id=open_status.id,
        impact="LOW",
        urgency="LOW",
        priority="P4",
        subject="Reopened ticket",
        description="A completed SLA clock remains after reopening.",
        created_at=completed_at,
        closed_at=completed_at,
    )
    database.add(ticket)
    database.flush()
    database.add(
        TicketSlaClock(
            ticket_id=ticket.id,
            policy_id=policy_id,
            clock_type="RESOLUTION",
            target_minutes=120,
            started_at=completed_at,
            due_at=completed_at,
            completed_at=completed_at,
            accountable_minutes=60,
            customer_pending_minutes=0,
            millensys_pending_minutes=0,
            escalation_minutes=0,
            saved_minutes=60,
            overrun_minutes=0,
            state="COMPLETED",
            calculation_version="2.0",
        )
    )
    database.commit()
    params = {"client_id": customer.id, "date_from": "2026-09-01", "date_to": "2026-09-20"}
    hours = client.get("/api/v1/home/client-hours", headers=admin_headers, params=params)
    profile = client.get("/api/v1/reports/client-profile", headers=admin_headers, params=params)
    assert hours.status_code == 200, hours.text
    assert profile.status_code == 200, profile.text
    assert not hours.json()["clients"]
    assert profile.json()["metrics"]["total_working_hours"] == 0

    ticket.status_id = closed_status.id
    database.commit()
    hours = client.get("/api/v1/home/client-hours", headers=admin_headers, params=params)
    profile = client.get("/api/v1/reports/client-profile", headers=admin_headers, params=params)
    assert (
        hours.json()["clients"][0]["working_hours"]
        == profile.json()["metrics"]["total_working_hours"]
    )
    assert (
        hours.json()["clients"][0]["saved_hours"]
        == profile.json()["metrics"]["saved_business_hours"]
    )


def test_resolved_ticket_completed_sla_appears_in_client_profile(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    resolved_status = database.scalar(select(TicketStatus).where(TicketStatus.code == "RESOLVED"))
    ticket_type_id = database.scalar(select(TicketType.id))
    policy_id = database.scalar(select(SlaPolicy.id))
    actor_id = database.scalar(select(User.id).where(User.username == "admin"))
    customer = Client(code="RESOLVED-SLA", name="Resolved SLA client", status_id=status_id)
    database.add(customer)
    database.flush()
    completed_at = datetime(2026, 9, 17, 17, tzinfo=UTC)
    ticket = Ticket(
        ticket_number="RESOLVED-SLA-1",
        ticket_type_id=ticket_type_id,
        client_id=customer.id,
        created_by_user_id=actor_id,
        status_id=resolved_status.id,
        impact="LOW",
        urgency="LOW",
        priority="P4",
        subject="Resolved ticket",
        description="Completed resolution clock before final closure.",
        created_at=completed_at,
        resolved_at=completed_at,
        closed_at=completed_at,
    )
    database.add(ticket)
    database.flush()
    database.add(
        TicketSlaClock(
            ticket_id=ticket.id,
            policy_id=policy_id,
            clock_type="RESOLUTION",
            target_minutes=30,
            started_at=completed_at,
            due_at=completed_at,
            completed_at=completed_at,
            accountable_minutes=18,
            customer_pending_minutes=0,
            millensys_pending_minutes=0,
            escalation_minutes=0,
            saved_minutes=12,
            overrun_minutes=0,
            state="COMPLETED",
            calculation_version="2.0",
        )
    )
    database.commit()
    response = client.get(
        "/api/v1/reports/client-profile",
        headers=admin_headers,
        params={"client_id": customer.id, "date_from": "2026-09-01", "date_to": "2026-09-20"},
    )
    assert response.status_code == 200, response.text
    metrics = response.json()["metrics"]
    assert metrics["sla_compliance_percent"] == 100
    assert metrics["sla_target_business_hours"] == 0.5
    assert metrics["saved_business_hours"] == 0.2
    assert metrics["total_working_hours"] == 0.3
    assert (
        response.json()["evidence"]["saved_business_hours"]["rows"][0]["reference"]
        == ticket.ticket_number
    )
    hours = client.get(
        "/api/v1/home/client-hours",
        headers=admin_headers,
        params={"client_id": customer.id, "date_from": "2026-09-01", "date_to": "2026-09-20"},
    )
    assert hours.status_code == 200, hours.text
    assert hours.json()["clients"][0]["working_hours"] == 0.3
    assert hours.json()["clients"][0]["target_hours"] == 0.5
    assert hours.json()["clients"][0]["saved_hours"] == 0.2
    analytics = client.get(
        "/api/v1/management-dashboards/analytics",
        headers=admin_headers,
        params={"date_from": "2026-09-01", "date_to": "2026-09-20"},
    )
    assert analytics.status_code == 200, analytics.text
    workhours = next(
        widget["value"]
        for widget in analytics.json()["dashboards"]["EXECUTIVE_OVERVIEW"]
        if widget["code"] == "customer_workhours"
    )
    assert {row["key"]: row["value"] for row in workhours}[str(customer.id)] == 0.3


def test_client_profile_preview_and_branded_word_export(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    created = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "PROFILE", "name": "Profile Report Client", "status_id": status_id},
    )
    assert created.status_code == 201, created.text
    client_id = created.json()["id"]
    updated = client.patch(
        f"/api/v1/clients/{client_id}",
        headers=admin_headers,
        json={"support_started_at": "2025-01-15"},
    )
    assert updated.status_code == 200, updated.text
    engineer_id = client.get("/api/v1/internal-operations/engineers", headers=admin_headers).json()[
        0
    ]["id"]
    operation = client.post(
        "/api/v1/internal-operations",
        headers=admin_headers,
        json={
            "title": "Profile evidence review",
            "operation_type": "MEETING",
            "starts_at": "2026-01-12T08:00:00Z",
            "ends_at": "2026-01-12T10:00:00Z",
            "client_id": client_id,
            "assignee_user_ids": [engineer_id],
        },
    )
    assert operation.status_code == 201, operation.text
    completed = client.patch(
        f"/api/v1/internal-operations/{operation.json()['id']}",
        headers=admin_headers,
        json={"status": "COMPLETED"},
    )
    assert completed.status_code == 200, completed.text
    params = {"client_id": client_id, "date_from": "2026-01-01", "date_to": "2026-01-31"}
    preview = client.get("/api/v1/reports/client-profile", headers=admin_headers, params=params)
    assert preview.status_code == 200, preview.text
    assert preview.json()["client"]["support_started_at"] == "2025-01-15"
    assert len(preview.json()["business_impacts"]) >= 6
    assert preview.json()["metrics"]["out_of_hours_tickets"] == 0
    assert preview.json()["metrics"]["services_provided"] == 1
    assert preview.json()["metrics"]["ticket_working_hours"] == 0
    assert preview.json()["metrics"]["operation_working_hours"] == 2
    assert preview.json()["metrics"]["total_working_hours"] == 2
    assert set(preview.json()["lifecycle"]) == {
        "uat",
        "deployments",
        "incidents",
        "changes",
        "problems",
    }
    assert preview.json()["drilldowns"]["metrics"]["total_working_hours"].startswith(
        f"/clients/{client_id}/evidence?"
    )
    assert preview.json()["evidence"]["total_working_hours"]["total"] == 2
    assert (
        preview.json()["evidence"]["total_working_hours"]["rows"][0]["source"]
        == "Internal operation"
    )
    hours = client.get("/api/v1/home/client-hours", headers=admin_headers, params=params)
    assert hours.status_code == 200, hours.text
    row = next(item for item in hours.json()["clients"] if item["client_id"] == client_id)
    assert row["working_hours"] == 2
    assert row["target_hours"] == 0
    assert row["saved_hours"] == 0
    database.get(Client, client_id).is_active = False
    database.commit()
    inactive_hours = client.get("/api/v1/home/client-hours", headers=admin_headers, params=params)
    assert inactive_hours.status_code == 200, inactive_hours.text
    assert any(item["client_id"] == client_id for item in inactive_hours.json()["clients"])
    assert preview.json()["evidence"]["services_provided"]["total"] == 1
    assert preview.json()["evidence"]["services_provided"]["rows"][0]["service"] == "Meeting"
    assert preview.json()["drilldowns"]["working_time_sources"]["operations"].startswith(
        "/internal-operations?"
    )
    operation_evidence = client.get(
        "/api/v1/internal-operations",
        headers=admin_headers,
        params={
            "client_id": client_id,
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
            "status": "COMPLETED",
        },
    )
    assert [item["id"] for item in operation_evidence.json()] == [operation.json()["id"]]
    assert "ticket_volume" in preview.json()["trends"]
    assert len(preview.json()["trends"]["ticket_volume"]) == 31
    exported = client.get(
        "/api/v1/reports/client-profile.docx", headers=admin_headers, params=params
    )
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert exported.content[:2] == b"PK"
    word = Document(io.BytesIO(exported.content))
    assert word.sections[0].orientation == WD_ORIENT.LANDSCAPE
    exported_text = "\n".join(paragraph.text for paragraph in word.paragraphs)
    exported_text += "\n" + "\n".join(
        cell.text for table in word.tables for row in table.rows for cell in row.cells
    )
    for matching_section in (
        "Profile Report Client",
        "Total tickets",
        "Ticket volume trend",
        "Priority mix",
        "Status distribution",
        "Products",
        "Modules",
        "Services",
        "Total working hours",
        "Business impact and recommended actions",
        "Critical ticket details",
        "Client delivery lifecycle",
        "Deployments",
        "Change Requests",
        "Problems",
    ):
        assert matching_section in exported_text
    assert (
        database.scalar(
            select(AuditLog).where(
                AuditLog.entity_type == "Client",
                AuditLog.entity_id == str(client_id),
                AuditLog.action == "client.profile_report.exported",
            )
        )
        is not None
    )


def test_client_profile_rejects_reversed_period(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    created = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "PROFILE2", "name": "Second Profile Client", "status_id": status_id},
    ).json()
    response = client.get(
        "/api/v1/reports/client-profile",
        headers=admin_headers,
        params={
            "client_id": created["id"],
            "date_from": date(2026, 2, 1),
            "date_to": date(2026, 1, 1),
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_REPORT_PERIOD"


def test_client_profile_uses_dedicated_permission_without_general_report_or_contract_view(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    created = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "PROFILE-PERM", "name": "Profile Permission Client", "status_id": status_id},
    )
    assert created.status_code == 201, created.text
    administrator_id = database.scalar(select(Profile.id).where(Profile.code == "ADMINISTRATOR"))
    broad_permission_ids = set(
        database.scalars(
            select(Permission.id).where(Permission.code.in_({"report.view", "contract.view"}))
        )
    )
    database.query(ProfilePermission).filter(
        ProfilePermission.profile_id == administrator_id,
        ProfilePermission.permission_id.in_(broad_permission_ids),
    ).delete(synchronize_session=False)
    database.commit()

    params = {"client_id": created.json()["id"], "date_from": "2026-01-01", "date_to": "2026-01-31"}
    allowed = client.get("/api/v1/reports/client-profile", headers=admin_headers, params=params)
    assert allowed.status_code == 200, allowed.text

    dedicated_id = database.scalar(
        select(Permission.id).where(Permission.code == "client.profile.view")
    )
    database.query(ProfilePermission).filter(
        ProfilePermission.profile_id == administrator_id,
        ProfilePermission.permission_id == dedicated_id,
    ).delete(synchronize_session=False)
    database.commit()
    forbidden = client.get("/api/v1/reports/client-profile", headers=admin_headers, params=params)
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "FORBIDDEN"
