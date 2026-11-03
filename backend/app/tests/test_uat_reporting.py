from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Client, ClientStatus
from app.modules.iam.models import User


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
