from datetime import datetime
from io import BytesIO
from zipfile import ZipFile
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.configuration.models import SiteSetting
from app.modules.iam.models import User
from app.modules.notifications.models import EventOutbox


def test_admin_can_generate_monthly_and_quarterly_kpi_reviews(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    employees = client.get("/api/v1/kpis/employees", headers=admin_headers)
    assert employees.status_code == 200, employees.text
    admin = employees.json()[0]

    monthly = client.post(
        "/api/v1/kpis/reviews/generate",
        params={"user_id": admin["id"], "period": "2026-08"},
        headers=admin_headers,
    )
    assert monthly.status_code == 200, monthly.text
    assert monthly.json()["template_code"] in {"SUPPORT_JUNIOR", "SUPPORT_SENIOR"}
    assert monthly.json()["engineer_level"] == admin["engineer_level"]
    assert sum(item["weight"] for item in monthly.json()["definitions"]) == 1

    quarterly = client.post(
        "/api/v1/kpis/reviews/generate",
        params={"user_id": admin["id"], "period": "2026-Q3"},
        headers=admin_headers,
    )
    assert quarterly.status_code == 200, quarterly.text


def test_kpi_employee_picker_excludes_engineers_without_tickets_in_period(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get(
        "/api/v1/kpis/employees",
        params={"date_from": "2199-01-01", "date_to": "2199-01-31"},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json() == []


def test_ratings_are_editable_until_saved_then_locked(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    employee = client.get("/api/v1/kpis/employees", headers=admin_headers).json()[0]
    review = client.post(
        "/api/v1/kpis/reviews/generate",
        params={"user_id": employee["id"], "period": "2026-08"},
        headers=admin_headers,
    ).json()
    system_key = next(item["key"] for item in review["definitions"] if item["source"] == "SYSTEM")
    saved = client.patch(
        f"/api/v1/kpis/reviews/{review['id']}",
        json={"ratings": {system_key: 5}, "action_plan": [], "lock_values": True},
        headers=admin_headers,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["is_locked"] is True

    locked = client.patch(
        f"/api/v1/kpis/reviews/{review['id']}",
        json={"ratings": {system_key: 4}},
        headers=admin_headers,
    )
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "KPI_REVIEW_LOCKED"

def test_custom_date_range_includes_calculation_guides(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    employee = client.get("/api/v1/kpis/employees", headers=admin_headers).json()[0]
    response = client.post(
        "/api/v1/kpis/reviews/generate",
        params={"user_id": employee["id"], "date_from": "2026-08-01", "date_to": "2026-08-14"},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    assert all(item["calculation_guide"] for item in response.json()["definitions"])


def test_never_submitted_draft_can_be_deleted_but_submission_history_cannot(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    employee = client.get("/api/v1/kpis/employees", headers=admin_headers).json()[0]
    draft = client.post("/api/v1/kpis/reviews/generate", params={"user_id": employee["id"], "period": "2026-06"}, headers=admin_headers).json()
    deleted = client.delete(f"/api/v1/kpis/reviews/{draft['id']}", headers=admin_headers)
    assert deleted.status_code == 204, deleted.text
    assert draft["id"] not in {item["id"] for item in client.get("/api/v1/kpis/reviews", headers=admin_headers).json()}

    submitted = client.post("/api/v1/kpis/reviews/generate", params={"user_id": employee["id"], "period": "2026-05"}, headers=admin_headers).json()
    manual = {item["key"]: 4 for item in submitted["definitions"] if item["source"] == "MANUAL"}
    client.patch(f"/api/v1/kpis/reviews/{submitted['id']}", json={"ratings": manual}, headers=admin_headers)
    sent = client.patch(f"/api/v1/kpis/reviews/{submitted['id']}", json={"status": "SUBMITTED"}, headers=admin_headers)
    assert sent.status_code == 200, sent.text
    blocked = client.delete(f"/api/v1/kpis/reviews/{submitted['id']}", headers=admin_headers)
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "KPI_DRAFT_DELETE_FORBIDDEN"


def test_kpi_excel_export_contains_summary_and_employee_evidence(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    response = client.get(
        "/api/v1/kpis/reports.xlsx", params={"period": "2026-08"}, headers=admin_headers
    )
    assert response.status_code == 200, response.text
    workbook = load_workbook(BytesIO(response.content))
    assert workbook.sheetnames[0] == "KPI Summary"
    assert len(workbook.sheetnames) >= 2
    assert workbook["KPI Summary"]["F1"].value == "Final Score %"

    employee = client.get("/api/v1/kpis/employees", headers=admin_headers).json()[0]
    user = database.get(User, employee["id"])
    assert user is not None
    user.job_title = "Technical Support Engineer"
    user.reports_to_user_id = user.id
    database.commit()
    selected = client.get(
        "/api/v1/kpis/reports.xlsx",
        params={"period": "2026-08", "user_id": employee["id"]},
        headers=admin_headers,
    )
    assert selected.status_code == 200, selected.text
    selected_book = load_workbook(BytesIO(selected.content))
    assert selected_book.sheetnames == [f"{employee['full_name']} KPI"[:31]]
    sheet = selected_book[selected_book.sheetnames[0]]
    assert sheet["A4"].value == "Performance Indicators & Scoring"
    assert sheet["B3"].value == "Technical Support Engineer"
    assert sheet["F2"].value == employee["full_name"]
    assert [sheet.cell(5, column).value for column in range(1, 8)] == [
        "Category", "KPI Name", "Description Of KPI", "Weight", "Rating (1-5)",
        "Weighted Score", "Measurement Criteria",
    ]
    assert sheet["F6"].value == '=IF(E6="","",E6/5*D6)'
    assert sheet["F16"].value == "=SUM(F6:F15)"
    assert sheet["A19"].value == "Action Plan for Next Period"
    assert sheet.max_column == 7
    assert "SupportHub-KPI-" in selected.headers["content-disposition"]
    assert "2026-08-01-2026-08-31.xlsx" in selected.headers["content-disposition"]


def test_bulk_download_contains_only_finalized_kpi_reports(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    employee = client.get("/api/v1/kpis/employees", headers=admin_headers).json()[0]
    finalized = client.post(
        "/api/v1/kpis/reviews/generate",
        params={"user_id": employee["id"], "period": "2026-04"},
        headers=admin_headers,
    ).json()
    manual = {
        item["key"]: 4 for item in finalized["definitions"] if item["source"] == "MANUAL"
    }
    saved = client.patch(
        f"/api/v1/kpis/reviews/{finalized['id']}",
        json={"ratings": manual},
        headers=admin_headers,
    )
    assert saved.status_code == 200, saved.text
    for status_code in ("REVIEWED", "APPROVED", "FINALIZED"):
        progressed = client.patch(
            f"/api/v1/kpis/reviews/{finalized['id']}",
            json={"status": status_code},
            headers=admin_headers,
        )
        assert progressed.status_code == 200, progressed.text

    submitted = client.post(
        "/api/v1/kpis/reviews/generate",
        params={"user_id": employee["id"], "period": "2026-07"},
        headers=admin_headers,
    ).json()
    submitted_manual = {
        item["key"]: 4 for item in submitted["definitions"] if item["source"] == "MANUAL"
    }
    saved_submission = client.patch(
        f"/api/v1/kpis/reviews/{submitted['id']}",
        json={"ratings": submitted_manual},
        headers=admin_headers,
    )
    assert saved_submission.status_code == 200, saved_submission.text
    submitted_response = client.patch(
        f"/api/v1/kpis/reviews/{submitted['id']}",
        json={"status": "SUBMITTED"},
        headers=admin_headers,
    )
    assert submitted_response.status_code == 200, submitted_response.text
    overlapping = client.post(
        "/api/v1/kpis/reviews/generate",
        params={
            "user_id": employee["id"],
            "date_from": "2026-09-01",
            "date_to": "2026-10-31",
        },
        headers=admin_headers,
    ).json()
    overlapping_manual = {
        item["key"]: 4 for item in overlapping["definitions"] if item["source"] == "MANUAL"
    }
    assert client.patch(
        f"/api/v1/kpis/reviews/{overlapping['id']}",
        json={"ratings": overlapping_manual},
        headers=admin_headers,
    ).status_code == 200
    assert client.patch(
        f"/api/v1/kpis/reviews/{overlapping['id']}",
        json={"status": "SUBMITTED"},
        headers=admin_headers,
    ).status_code == 200
    response = client.get(
        "/api/v1/kpis/finalized-reports.zip",
        params=[
            ("user_ids", str(employee["id"])),
            ("date_from", "2026-01-01"),
            ("date_to", "2026-12-31"),
        ],
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/zip"
    with ZipFile(BytesIO(response.content)) as archive:
        names = archive.namelist()
        assert names == [
            f"{employee['full_name']}-Q2-2026.xlsx",
            f"{employee['full_name']}-Q3-2026.xlsx",
            f"{employee['full_name']}-Q4-2026.xlsx",
        ]
        workbook = load_workbook(BytesIO(archive.read(names[0])))
        assert workbook.active["B1"].value == employee["full_name"]

    q3_response = client.get(
        "/api/v1/kpis/finalized-reports.zip",
        params=[
            ("user_ids", str(employee["id"])),
            ("date_from", "2026-07-01"),
            ("date_to", "2026-09-30"),
        ],
        headers=admin_headers,
    )
    assert q3_response.status_code == 200, q3_response.text
    with ZipFile(BytesIO(q3_response.content)) as archive:
        assert archive.namelist() == [f"{employee['full_name']}-Q3-2026.xlsx"]


def test_team_submission_hr_acknowledgement_reopen_and_comparison(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    employee = client.get("/api/v1/kpis/employees", headers=admin_headers).json()[0]
    review = client.post(
        "/api/v1/kpis/reviews/generate",
        params={"user_id": employee["id"], "period": "2026-07"},
        headers=admin_headers,
    ).json()
    manual = {item["key"]: 4 for item in review["definitions"] if item["source"] == "MANUAL"}
    saved = client.patch(
        f"/api/v1/kpis/reviews/{review['id']}",
        json={"ratings": manual, "comments": "Team Leader evidence"},
        headers=admin_headers,
    )
    assert saved.status_code == 200, saved.text
    submitted = client.patch(
        f"/api/v1/kpis/reviews/{review['id']}",
        json={"status": "SUBMITTED"},
        headers=admin_headers,
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["submission_version"] == 1
    assert submitted.json()["is_locked"] is True

    queue = client.get("/api/v1/kpis/reviews/submitted", headers=admin_headers)
    assert queue.status_code == 200
    assert review["id"] in {item["id"] for item in queue.json()}
    viewed = client.post(
        f"/api/v1/kpis/reviews/{review['id']}/hr-viewed", headers=admin_headers
    )
    assert viewed.status_code == 200
    assert viewed.json()["hr_viewed_at"] is not None

    reopened = client.post(
        f"/api/v1/kpis/reviews/{review['id']}/reopen", headers=admin_headers
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["status"] == "DRAFT"
    assert reopened.json()["is_locked"] is False
    resubmitted = client.patch(
        f"/api/v1/kpis/reviews/{review['id']}",
        json={"status": "SUBMITTED"},
        headers=admin_headers,
    )
    assert resubmitted.status_code == 200, resubmitted.text
    assert resubmitted.json()["submission_version"] == 2
    assert resubmitted.json()["hr_viewed_at"] is None

    comparison = client.get(
        "/api/v1/kpis/comparisons",
        params={"user_ids": employee["id"], "date_from": "2026-01-01", "date_to": "2026-12-31"},
        headers=admin_headers,
    )
    assert comparison.status_code == 200, comparison.text
    assert comparison.json()[0]["user_id"] == employee["id"]
    report = client.get(
        f"/api/v1/kpis/reviews/{review['id']}/report.xlsx", headers=admin_headers
    )
    assert report.status_code == 200


def test_quarter_cutoff_uses_cairo_and_requires_documented_override(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.modules.kpis.routes.server_now",
        lambda: datetime(2026, 4, 15, 12, 0, tzinfo=ZoneInfo("Africa/Cairo")),
    )
    database.merge(SiteSetting(key="kpi_cutoff_enabled", value="true"))
    database.merge(SiteSetting(key="kpi_cutoff_mode", value="QUARTER_LAST_WEEK"))
    database.merge(SiteSetting(key="kpi_cutoff_timezone", value="Africa/Cairo"))
    database.commit()
    policy = client.get("/api/v1/kpis/cutoff", headers=admin_headers)
    assert policy.status_code == 200
    assert policy.json()["timezone"] == "Africa/Cairo"
    assert policy.json()["mode"] == "QUARTER_LAST_WEEK"
    employee = client.get("/api/v1/kpis/employees", headers=admin_headers).json()[0]
    blocked = client.post(
        "/api/v1/kpis/reviews/generate",
        params={"user_id": employee["id"], "period": "2026-Q2"},
        headers=admin_headers,
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "KPI_CUTOFF_CLOSED"
    overridden = client.post(
        "/api/v1/kpis/reviews/generate",
        params={"user_id": employee["id"], "period": "2026-Q2", "override_reason": "Approved late quarterly KPI correction"},
        headers=admin_headers,
    )
    assert overridden.status_code == 200, overridden.text
    monthly = client.put(
        "/api/v1/kpis/cutoff",
        json={"enabled": True, "mode": "MONTH_LAST_WEEK"},
        headers=admin_headers,
    )
    assert monthly.status_code == 200
    assert monthly.json()["mode"] == "MONTH_LAST_WEEK"


def test_manager_bulk_submits_quarter_container_and_queues_email(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    employee = client.get("/api/v1/kpis/employees", headers=admin_headers).json()[0]
    user = database.get(User, employee["id"])
    assert user is not None
    user.reports_to_user_id = user.id
    database.commit()
    review = client.post(
        "/api/v1/kpis/reviews/generate",
        params={"user_id": user.id, "period": "2026-Q3", "override_reason": "Authorized test quarter generation"},
        headers=admin_headers,
    ).json()
    manual = {item["key"]: 4 for item in review["definitions"] if item["source"] == "MANUAL"}
    saved = client.patch(
        f"/api/v1/kpis/reviews/{review['id']}",
        json={"ratings": manual, "comments": "Quarterly evidence complete"},
        headers=admin_headers,
    )
    assert saved.status_code == 200, saved.text
    submitted = client.post(
        "/api/v1/kpis/batches/submit",
        json={"year": 2026, "quarter": 3, "review_ids": [review["id"]], "override_reason": "Authorized test container submission"},
        headers=admin_headers,
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["name"] == "Support KPIs Quarter 3_2026"
    assert submitted.json()["employee_count"] == 1
    assert user.email in submitted.json()["recipient_emails"]
    outbox = database.scalar(
        select(EventOutbox).where(EventOutbox.event_type == "KPI_BATCH_SUBMITTED")
    )
    assert outbox is not None
    assert outbox.deduplication_key == "kpi-batch:2026:q3:v1"
