from datetime import UTC, datetime, timedelta
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.iam.models import Profile
from app.modules.shifts.models import ShiftType


def create_employee(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str,
    email: str,
    department: str,
    profile_id: int,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "full_name": name,
            "username": email,
            "email": email,
            "password": "TemporaryPassword!123",
            "primary_profile_id": profile_id,
            "additional_profile_ids": [],
            "client_scope_ids": [],
            "branch_scope_ids": [],
            "user_type": "EMPLOYEE",
            "department": department,
            "job_title": "Technical Support",
            "hire_date": "2026-08-05",
            "require_password_change": False,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_hr_department_scope_shift_reliability_and_export(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    hr_profile = database.scalar(select(Profile).where(Profile.code == "HR"))
    support_profile = database.scalar(select(Profile).where(Profile.code == "L1_SUPPORT"))
    shift_type_id = database.scalar(select(ShiftType.id).where(ShiftType.code == "DAY"))
    assert hr_profile and support_profile and shift_type_id

    hr_user = create_employee(
        client,
        admin_headers,
        name="Support HR",
        email="support.hr@example.com",
        department="Support",
        profile_id=hr_profile.id,
    )
    same_department = create_employee(
        client,
        admin_headers,
        name="Support Employee",
        email="support.employee@example.com",
        department="Support",
        profile_id=support_profile.id,
    )
    other_department = create_employee(
        client,
        admin_headers,
        name="Implementation Employee",
        email="implementation.employee@example.com",
        department="Implementation",
        profile_id=support_profile.id,
    )
    starts_at = datetime(2026, 8, 5, 6, 30, tzinfo=UTC)
    for employee in (same_department, other_department):
        saved = client.post(
            "/api/v1/shifts",
            headers=admin_headers,
            json={
                "shift_type_id": shift_type_id,
                "user_id": employee["id"],
                "starts_at": starts_at.isoformat(),
                "ends_at": (starts_at + timedelta(hours=8)).isoformat(),
            },
        )
        assert saved.status_code == 201, saved.text

    login = client.post(
        "/api/v1/auth/login",
        json={"login": "support.hr@example.com", "password": "TemporaryPassword!123"},
    )
    assert login.status_code == 200, login.text
    hr_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    calendar = client.get(
        "/api/v1/shift-calendar",
        headers=hr_headers,
        params={
            "ends_after": (starts_at - timedelta(minutes=1)).isoformat(),
            "starts_before": (starts_at + timedelta(days=1)).isoformat(),
        },
    )
    assert calendar.status_code == 200, calendar.text
    assert {item["employee_name"] for item in calendar.json()} == {
        "Support Employee",
        "Implementation Employee",
    }
    assert all(
        datetime.fromisoformat(item["starts_at"]).astimezone(UTC) == starts_at
        for item in calendar.json()
    )

    engineers = client.get("/api/v1/internal-operations/engineers", headers=hr_headers)
    assert engineers.status_code == 200, engineers.text
    engineer_names = {item["full_name"] for item in engineers.json()}
    assert {"Support HR", "Support Employee"} <= engineer_names
    assert "Implementation Employee" not in engineer_names

    dashboard = client.get(
        "/api/v1/dashboards/summary",
        headers=hr_headers,
        params={"kpi_month": "2026-08"},
    )
    assert dashboard.status_code == 200, dashboard.text
    dashboard_names = {item["agent"] for item in dashboard.json()["agent_kpis"]}
    assert {"Support HR", "Support Employee"} <= dashboard_names
    assert "Implementation Employee" not in dashboard_names

    exported = client.get(
        "/api/v1/reports/agent-kpis.xlsx",
        headers=hr_headers,
        params={"kpi_month": "2026-08"},
    )
    assert exported.status_code == 200, exported.text
    workbook = load_workbook(BytesIO(exported.content), read_only=True)
    sheet = workbook["HR KPI Summary"]
    exported_names = {
        str(row[0])
        for row in sheet.iter_rows(min_row=6, values_only=True)
        if row and row[0]
    }
    assert dashboard_names <= exported_names
    assert "Implementation Employee" not in exported_names
    assert hr_user["job_title"] == "Technical Support"
