from datetime import date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import ClientStatus
from app.modules.iam.models import Department, DepartmentMembership, User
from app.modules.tickets.models import TicketComment, TicketType


def test_operational_report_inventory_export_and_period_validation(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    report = client.get(
        "/api/v1/reports/operations?date_from=2026-08-01&date_to=2026-08-31",
        headers=admin_headers,
    )
    assert report.status_code == 200, report.text
    assert report.json()["formula_version"] == "WAVE7-1.0"
    assert {item["code"] for item in report.json()["definitions"]} == {
        "tickets_created",
        "visit_balance",
        "shift_capacity",
        "visit_execution",
    }
    inventory = client.get("/api/v1/reports/operations/dashboard-inventory", headers=admin_headers)
    assert inventory.status_code == 200
    assert inventory.json()["duplicate_metric_codes"] == []
    exported = client.get(
        "/api/v1/reports/operations/export.csv?date_from=2026-08-01&date_to=2026-08-31&report=clients",
        headers=admin_headers,
    )
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    invalid = client.get(
        "/api/v1/reports/operations?date_from=2026-09-01&date_to=2026-08-31",
        headers=admin_headers,
    )
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "INVALID_REPORT_PERIOD"


def test_department_achievement_deduplicates_and_uses_effective_membership(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    department = Department(code="OPS-REPORT", name="Operations Reporting", is_active=True)
    database.add(department)
    database.flush()
    admin.department_id = department.id
    admin.department = department.name
    database.add(
        DepartmentMembership(
            user_id=admin.id,
            department_id=department.id,
            effective_from=date(2026, 1, 1),
            is_primary=True,
            created_by_user_id=admin.id,
        )
    )
    database.commit()
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    created_client = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "REPORT-CLIENT", "name": "Report Client", "status_id": status_id},
    )
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    created_ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": created_client.json()["id"],
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "Reconciled department evidence",
            "description": "Multiple activities must remain one distinct ticket.",
        },
    )
    assert created_ticket.status_code == 201, created_ticket.text
    database.add(
        TicketComment(
            ticket_id=created_ticket.json()["id"],
            author_user_id=admin.id,
            body="Second qualifying event on the same ticket.",
            created_at=datetime(2026, 8, 20, 10),
        )
    )
    database.commit()
    achievements = client.get(
        f"/api/v1/reports/operations/achievements?date_from=2026-01-01&date_to=2026-12-31&department_id={department.id}",
        headers=admin_headers,
    )
    assert achievements.status_code == 200, achievements.text
    assert achievements.json()["individual_ranking"] is False
    assert achievements.json()["rows"][0]["tickets_worked_on"] == 1
    evidence = client.get(
        f"/api/v1/reports/operations/achievements/evidence?date_from=2026-01-01&date_to=2026-12-31&department_id={department.id}",
        headers=admin_headers,
    )
    assert evidence.status_code == 200
    assert evidence.json()["count"] == 1
    structure = client.get(
        "/api/v1/reports/operations/department-structure?as_of=2026-08-20",
        headers=admin_headers,
    )
    assert (
        next(item for item in structure.json()["departments"] if item["id"] == department.id)[
            "headcount"
        ]
        == 1
    )
