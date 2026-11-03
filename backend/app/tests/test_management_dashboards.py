import json
from datetime import UTC, datetime
from io import BytesIO

from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Client, ClientStatus, Country
from app.modules.dashboards.management import _duration_statistics
from app.modules.iam.models import Permission, Profile, ProfilePermission, User
from app.modules.tickets.models import Ticket, TicketStatus, TicketType, TicketWorklog


def test_duration_statistics_exposes_average_median_p90_and_sample() -> None:
    assert _duration_statistics([]) == {
        "average": None, "median": None, "p90": None, "sample_size": 0,
    }
    assert _duration_statistics([1.0, 2.0, 3.0, 40.0]) == {
        "average": 11.5, "median": 2.5, "p90": 40.0, "sample_size": 4,
    }


def test_management_analytics_has_two_focused_sections_and_export(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get("/api/v1/management-dashboards/analytics", headers=admin_headers)
    assert response.status_code == 200, response.text
    assert set(response.json()["dashboards"]) == {"EXECUTIVE_OVERVIEW", "CUSTOMER_SERVICE_SUCCESS"}
    executive_codes = {item["code"] for item in response.json()["dashboards"]["EXECUTIVE_OVERVIEW"]}
    assert {
        "tickets", "sla", "active_incidents", "trend", "countries", "workload",
        "response", "resolution",
    } <= executive_codes
    assert {"response_distribution", "resolution_distribution"}.isdisjoint(executive_codes)
    assert "support_consumption" in executive_codes
    assert "client_hours" in executive_codes
    tickets_widget = next(
        item
        for item in response.json()["dashboards"]["EXECUTIVE_OVERVIEW"]
        if item["code"] == "tickets"
    )
    assert "created_from" in tickets_widget["drilldown"]["params"]
    assert "created_to" in tickets_widget["drilldown"]["params"]
    assert "date_from" not in tickets_widget["drilldown"]["params"]
    assert "period" not in tickets_widget["drilldown"]["params"]
    trend = next(item["value"] for item in response.json()["dashboards"]["EXECUTIVE_OVERVIEW"] if item["code"] == "trend")
    assert len(trend) > 1
    success_codes = {item["code"] for item in response.json()["dashboards"]["CUSTOMER_SERVICE_SUCCESS"]}
    assert {"customer_health", "health_distribution", "client_health_portfolio"} <= success_codes
    exported = client.get("/api/v1/management-dashboards/export", headers=admin_headers)
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-type"].startswith("text/csv")
    assert "Dashboard,Metric,Category,Value" in exported.text
    word = client.get("/api/v1/management-dashboards/export.docx", headers=admin_headers)
    assert word.status_code == 200, word.text if word.status_code != 200 else ""
    report = Document(BytesIO(word.content))
    report_text = " ".join(paragraph.text for paragraph in report.paragraphs)
    assert "Top Management Analysis Report" in report_text
    assert "Customers with the Highest Support Consumption" in report_text
    moved = client.get(
        "/api/v1/management-dashboards/export.docx",
        headers=admin_headers,
        params={
            "widget_tabs": json.dumps({"customer_satisfaction": "EXECUTIVE_OVERVIEW"}),
            "hidden_widgets": json.dumps({"EXECUTIVE_OVERVIEW": ["support_consumption"]}),
        },
    )
    assert moved.status_code == 200, moved.text if moved.status_code != 200 else ""
    moved_text = " ".join(paragraph.text for paragraph in Document(BytesIO(moved.content)).paragraphs)
    assert "Customers with the Highest Support Consumption" not in moved_text


def test_client_profile_dashboard_honors_client_filter(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    selected = Client(code="MGMT-PROFILE", name="Management Profile Client", status_id=status_id, is_active=True)
    database.add(selected)
    database.commit()
    response = client.get(
        "/api/v1/management-dashboards/analytics",
        headers=admin_headers,
        params={"client_id": selected.id},
    )
    assert response.status_code == 200, response.text
    success = response.json()["dashboards"]["CUSTOMER_SERVICE_SUCCESS"]
    portfolio = next(item["value"] for item in success if item["code"] == "client_health_portfolio")
    assert len(portfolio) == 1
    assert portfolio[0]["label"] == selected.name
    assert portfolio[0]["route"] == f"/clients/{selected.id}/profile"
    assert portfolio[0]["sla"] is None
    assert portfolio[0]["satisfaction"] is None
    assert portfolio[0]["health_score"] is None
    assert portfolio[0]["health_status"] == "INSUFFICIENT_DATA"
    assert portfolio[0]["risk_reason"] == "No support activity in the selected period"


def test_top_management_profile_is_read_only(database: Session) -> None:
    codes = set(
        database.scalars(
            select(Permission.code)
            .join(ProfilePermission, ProfilePermission.permission_id == Permission.id)
            .join(Profile, Profile.id == ProfilePermission.profile_id)
            .where(Profile.code == "TOP_MANAGEMENT")
        )
    )
    assert {"dashboard.executive", "finance.dashboard.view", "report.view", "report.export"} <= codes
    assert "finance.payment.collect" not in codes
    assert "finance.manage" not in codes
    assert "dashboard.manager" not in codes
    assert not any(code.endswith((".create", ".edit", ".manage", ".delete")) for code in codes)


def test_countries_supported_only_contains_client_linked_countries(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    linked = Country(iso_alpha2="XZ", iso_alpha3="XZZ", name="Linked Test Country", is_active=True)
    unlinked = Country(iso_alpha2="XY", iso_alpha3="XYY", name="Unlinked Test Country", is_active=True)
    database.add_all([linked, unlinked])
    database.flush()
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    database.add(Client(code="COUNTRY-LINK", name="Country Linked Client", status_id=status_id, country_id=linked.id, is_active=True))
    database.commit()

    response = client.get("/api/v1/management-dashboards/analytics", headers=admin_headers)
    assert response.status_code == 200, response.text
    executive = response.json()["dashboards"]["EXECUTIVE_OVERVIEW"]
    countries = next(widget["value"] for widget in executive if widget["code"] == "countries")
    labels = {row["label"] for row in countries}
    assert "Linked Test Country" in labels
    assert "Unlinked Test Country" not in labels
    assert next(row["value"] for row in countries if row["label"] == "Linked Test Country") == 1


def test_management_trend_evidence_includes_older_ticket_resolved_in_period(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    resolved_status_id = database.scalar(
        select(TicketStatus.id).where(TicketStatus.code == "RESOLVED")
    )
    new_status_id = database.scalar(
        select(TicketStatus.id).where(TicketStatus.code == "NEW")
    )
    ticket_type_id = database.scalar(
        select(TicketType.id).where(TicketType.code == "INCIDENT")
    )
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    linked_client = Client(
        code="MGMT-TREND-EVIDENCE",
        name="Management Trend Evidence",
        status_id=status_id,
    )
    database.add(linked_client)
    database.flush()
    ticket = Ticket(
        ticket_number="MGMT-TREND-OLD-1",
        ticket_type_id=ticket_type_id,
        client_id=linked_client.id,
        created_by_user_id=admin_id,
        status_id=resolved_status_id,
        impact="LOW",
        urgency="LOW",
        priority="P4",
        subject="Created before period and resolved inside it",
        description="Ensures capped evidence preserves resolution-side trend rows.",
        created_at=datetime(2026, 5, 15, tzinfo=UTC),
        resolved_at=datetime(2026, 6, 10, tzinfo=UTC),
    )
    current_ticket = Ticket(
        ticket_number="MGMT-HEALTH-CURRENT-1",
        ticket_type_id=ticket_type_id,
        client_id=linked_client.id,
        created_by_user_id=admin_id,
        status_id=new_status_id,
        impact="HIGH",
        urgency="HIGH",
        priority="P1",
        subject="Current open critical health input",
        description="Verifies grouped SQL health inputs preserve the formula.",
        created_at=datetime(2026, 6, 12, tzinfo=UTC),
        reopened_at=datetime(2026, 6, 13, tzinfo=UTC),
    )
    database.add_all([ticket, current_ticket])
    database.flush()
    database.add(TicketWorklog(
        ticket_id=current_ticket.id, user_id=admin_id,
        started_at=datetime(2026, 6, 12, 10, tzinfo=UTC),
        ended_at=datetime(2026, 6, 12, 12, tzinfo=UTC),
        duration_minutes=120, notes="Approved customer work", status="APPROVED",
    ))
    database.commit()

    response = client.get(
        "/api/v1/management-dashboards/analytics",
        headers=admin_headers,
        params={"date_from": "2026-06-01", "date_to": "2026-06-30"},
    )
    assert response.status_code == 200, response.text
    trend = next(
        widget
        for widget in response.json()["dashboards"]["EXECUTIVE_OVERVIEW"]
        if widget["code"] == "trend"
    )
    assert ticket.ticket_number in {row["ticket"] for row in trend["evidence"]}
    executive = response.json()["dashboards"]["EXECUTIVE_OVERVIEW"]
    ticket_total = next(widget["value"] for widget in executive if widget["code"] == "tickets")
    for code in ("status_mix", "priority_mix", "products"):
        breakdown = next(widget["value"] for widget in executive if widget["code"] == code)
        assert sum(row["value"] for row in breakdown) == ticket_total
    product_mix = next(widget["value"] for widget in executive if widget["code"] == "products")
    assert {row["label"]: row["value"] for row in product_mix} == {"Unspecified": 1}
    workload = next(widget["value"] for widget in executive if widget["code"] == "workload")
    assert sum(row["value"] for row in workload) <= ticket_total
    consumption = next(widget["value"] for widget in executive if widget["code"] == "support_consumption")
    assert consumption == [{"key": str(linked_client.id), "label": linked_client.name, "value": 1}]
    workhours = next(widget["value"] for widget in executive if widget["code"] == "customer_workhours")
    assert workhours == [{"key": str(linked_client.id), "label": linked_client.name, "value": 2.0}]
    portfolio = next(
        widget["value"]
        for widget in response.json()["dashboards"]["CUSTOMER_SERVICE_SUCCESS"]
        if widget["code"] == "client_health_portfolio"
    )
    health = next(row for row in portfolio if row["key"] == str(linked_client.id))
    assert {
        key: health[key]
        for key in (
            "tickets",
            "open_tickets",
            "critical_tickets",
            "resolution",
            "health_score",
            "health_status",
        )
    } == {
        "tickets": 1,
        "open_tickets": 1,
        "critical_tickets": 1,
        "resolution": 0.0,
        "health_score": 45.5,
        "health_status": "AT_RISK",
    }
