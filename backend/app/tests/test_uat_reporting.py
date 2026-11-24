from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.modules.clients.models import Client, ClientStatus
from app.modules.iam.models import User
from app.modules.uat.models import UatCycle, UatCycleTest


def test_results_report_analysis_and_pdf(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    status = database.scalar(select(ClientStatus))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert status and admin
    customer = Client(code="REPORT-CUSTOMER", name="Report Customer", status_id=status.id)
    database.add(customer)
    database.commit()
    case = client.post("/api/v1/uat/test-cases", headers=admin_headers, json={
        "code": "REPORT-CASE", "title": "Report case", "expected_result": "Done", "priority": "HIGH",
        "steps": [{"action": "Run", "expected_result": "Done"}],
    })
    assert case.status_code == 201, case.text
    cycle = client.post("/api/v1/uat/cycles", headers=admin_headers, json={
        "code": "REPORT-CYCLE", "title": "Report cycle", "client_id": customer.id,
        "release_version": "1.0", "coordinator_user_id": admin.id,
        "test_case_ids": [case.json()["id"]],
    })
    assert cycle.status_code == 201, cycle.text
    cycle_id = cycle.json()["id"]
    report = client.get(f"/api/v1/uat/cycles/{cycle_id}/results-report", headers=admin_headers)
    assert report.status_code == 200, report.text
    assert report.json()["summary"]["internal_unexecuted"] == 1
    assert report.json()["by_priority"] == {"HIGH": 1}
    pdf = client.get(f"/api/v1/uat/cycles/{cycle_id}/results-report.pdf", headers=admin_headers)
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-") and len(pdf.content) > 1000


def test_portfolio_prioritizes_actionable_cycles_and_reports_phase_one_attention(
    client: TestClient, admin_headers: dict[str, str], database: Session,
) -> None:
    status = database.scalar(select(ClientStatus))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert status and admin
    customer = Client(code="PORTFOLIO-CUSTOMER", name="Portfolio Customer", status_id=status.id)
    database.add(customer)
    database.commit()
    case = client.post("/api/v1/uat/test-cases", headers=admin_headers, json={
        "code": "PORTFOLIO-CASE", "title": "Portfolio case", "expected_result": "Done",
        "priority": "HIGH", "steps": [{"action": "Run", "expected_result": "Done"}],
    })
    assert case.status_code == 201, case.text
    cycle_response = client.post("/api/v1/uat/cycles", headers=admin_headers, json={
        "code": "PORTFOLIO-CYCLE", "title": "Portfolio cycle", "client_id": customer.id,
        "release_version": "2.0", "environment": "UAT", "coordinator_user_id": admin.id,
        "test_case_ids": [case.json()["id"]],
    })
    assert cycle_response.status_code == 201, cycle_response.text
    cycle = database.get(UatCycle, cycle_response.json()["id"])
    assert cycle
    cycle.status = "ACTIVE"
    cycle.portal_visible = True
    cycle.allow_client_testing = True
    cycle.client_access_end_at = server_now() - timedelta(hours=1)
    cycle.due_date = server_now().date() - timedelta(days=1)
    test = database.scalar(select(UatCycleTest).where(UatCycleTest.cycle_id == cycle.id))
    assert test
    test.test_result = "FAIL"
    test.workflow_status = "WAITING_FIX"
    test.due_date = server_now().date() - timedelta(days=1)
    database.commit()

    response = client.get("/api/v1/uat/portfolio", headers=admin_headers)
    assert response.status_code == 200, response.text
    row = next(item for item in response.json() if item["id"] == cycle.id)
    assert row["environment"] == "UAT"
    assert row["coordinator_name"] == admin.full_name
    assert row["next_action"] == "Review Failures"
    assert row["due_state"] == "OVERDUE"
    assert row["attention"] == [
        "Overdue tests", "Failures without tickets", "Missing client assignments",
        "Expired portal access",
    ]
    assert response.json()[0]["id"] == cycle.id
