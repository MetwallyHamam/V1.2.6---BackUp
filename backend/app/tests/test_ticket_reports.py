from datetime import UTC, datetime
from urllib.parse import urlparse

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Client, ClientStatus
from app.modules.iam.models import User
from app.modules.tickets.models import Ticket, TicketStatus, TicketType


def _ticket(
    database: Session, *, closed: bool, number: str, type_code: str = "INCIDENT"
) -> Ticket:
    client_status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    ticket_status = database.scalar(
        select(TicketStatus).where(TicketStatus.code == ("CLOSED" if closed else "RESOLVED"))
    )
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == type_code))
    actor_id = database.scalar(select(User.id).where(User.username == "admin"))
    customer = Client(code=f"REPORT-{number}", name="Report Client", status_id=client_status_id)
    database.add(customer)
    database.flush()
    now = datetime(2026, 9, 26, 12, tzinfo=UTC)
    row = Ticket(
        ticket_number=number,
        ticket_type_id=ticket_type_id,
        client_id=customer.id,
        created_by_user_id=actor_id,
        status_id=ticket_status.id,
        impact="HIGH",
        urgency="HIGH",
        priority="P1",
        subject="Production application unavailable",
        description="Users cannot access the production application.",
        resolution_summary="Service was restored.",
        root_cause_summary="Connection pool exhaustion.",
        created_at=now,
        resolved_at=now,
        closed_at=now if closed else None,
    )
    database.add(row)
    database.commit()
    return row


def test_report_requires_closed_ticket(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    ticket = _ticket(database, closed=False, number="RPT-OPEN-1")
    response = client.post(
        f"/api/v1/ticket-reports/tickets/{ticket.id}",
        headers=admin_headers,
        json={"report_type": "TICKET", "title": "Ticket report", "data": {}},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TICKET_NOT_CLOSED"


def test_publish_export_and_mobile_share_flow(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    ticket = _ticket(database, closed=True, number="RPT-CLOSED-1")
    created = client.post(
        f"/api/v1/ticket-reports/tickets/{ticket.id}",
        headers=admin_headers,
        json={"report_type": "INCIDENT", "title": "Production Incident Report", "data": {}},
    )
    assert created.status_code == 201, created.text
    report = created.json()
    assert report["data"]["root_cause"] == "Connection pool exhaustion."
    report["data"]["executive_summary"] = "Service was restored and preventive work was assigned."
    saved = client.patch(
        f"/api/v1/ticket-reports/{report['id']}",
        headers=admin_headers,
        json={"title": report["title"], "data": report["data"]},
    )
    assert saved.status_code == 200, saved.text
    published = client.post(f"/api/v1/ticket-reports/{report['id']}/publish", headers=admin_headers)
    assert published.status_code == 200 and published.json()["published_version"] == 1
    word = client.get(f"/api/v1/ticket-reports/{report['id']}/export.docx", headers=admin_headers)
    pdf = client.get(f"/api/v1/ticket-reports/{report['id']}/export.pdf", headers=admin_headers)
    assert word.content[:2] == b"PK"
    assert pdf.content[:4] == b"%PDF"
    shared = client.post(
        f"/api/v1/ticket-reports/{report['id']}/share-links",
        headers=admin_headers,
        json={"expires_in_days": 7, "allow_download": True},
    )
    assert shared.status_code == 201, shared.text
    assert shared.json()["url"].startswith("http://localhost:5173/shared/reports/")
    token = urlparse(shared.json()["url"]).path.rsplit("/", 1)[-1]
    public = client.get(f"/api/v1/public/ticket-reports/{token}")
    assert public.status_code == 200, public.text
    assert public.json()["title"] == "Production Incident Report"
    assert "executive_summary" not in public.text
    public_pdf = client.get(f"/api/v1/public/ticket-reports/{token}/download.pdf")
    assert public_pdf.status_code == 200 and public_pdf.content[:4] == b"%PDF"


def test_report_template_must_match_ticket_type(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    incident = _ticket(database, closed=True, number="RPT-TYPE-INCIDENT")
    wrong_ticket_report = client.post(
        f"/api/v1/ticket-reports/tickets/{incident.id}",
        headers=admin_headers,
        json={"report_type": "TICKET", "title": "Wrong ticket report", "data": {}},
    )
    assert wrong_ticket_report.status_code == 409
    assert wrong_ticket_report.json()["error"]["code"] == "REPORT_TYPE_MISMATCH"

    service_request = _ticket(
        database,
        closed=True,
        number="RPT-TYPE-SERVICE",
        type_code="SERVICE_REQUEST",
    )
    wrong_incident_report = client.post(
        f"/api/v1/ticket-reports/tickets/{service_request.id}",
        headers=admin_headers,
        json={"report_type": "INCIDENT", "title": "Wrong incident report", "data": {}},
    )
    assert wrong_incident_report.status_code == 409
    assert wrong_incident_report.json()["error"]["code"] == "REPORT_TYPE_MISMATCH"
