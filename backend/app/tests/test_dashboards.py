import json
import tracemalloc
from datetime import UTC, datetime, timedelta
from io import BytesIO
from time import perf_counter

from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import event, func, insert, select
from sqlalchemy.orm import Session

from app.core.clock import as_server_time, server_now
from app.modules.clients.models import (
    Client,
    ClientDepartmentLink,
    ClientLocation,
    ClientStatus,
    Country,
    Product,
    SupportTeam,
    SupportTeamMember,
)
from app.modules.contracts.models import SlaPolicy, TicketSlaClock
from app.modules.dashboards.models import (
    Dashboard,
    DashboardAssignment,
    DashboardUserPreference,
    DashboardWidget,
)
from app.modules.dashboards.service import (
    DASHBOARD_ASSIGNMENT_IMPACT_MAX_QUERIES,
    DASHBOARD_ASSIGNMENT_IMPACT_MAX_RESPONSE_BYTES,
    DASHBOARD_ASSIGNMENT_IMPACT_MAX_ROWS,
    DASHBOARD_INTERACTIVE_MAX_SECONDS,
    DASHBOARD_SUMMARY_MAX_DETAIL_ROWS,
    DASHBOARD_SUMMARY_MAX_PEAK_BYTES,
    DASHBOARD_SUMMARY_MAX_QUERIES,
    DASHBOARD_SUMMARY_MAX_RESPONSE_BYTES,
)
from app.modules.iam.models import (
    AuditLog,
    Department,
    Permission,
    Profile,
    ProfilePermission,
    User,
    UserProfile,
)
from app.modules.iam.security import create_access_token
from app.modules.reports.routes import safe_cell
from app.modules.tickets.models import Ticket, TicketAssignmentHistory, TicketStatus, TicketType
from app.tests.conftest import TEST_SETTINGS


def test_top_support_agents_has_independent_month_to_date_resolution_ranking(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    client_status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    resolved_status_id = database.scalar(
        select(TicketStatus.id).where(TicketStatus.code == "RESOLVED")
    )
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    support_users = list(
        database.scalars(select(User).where(func.lower(func.trim(User.department)) == "support"))
    )
    assert client_status_id and resolved_status_id and ticket_type_id
    assert support_users
    second_support = User(
        full_name="Second Support Agent",
        username="second-support-agent",
        username_normalized="second-support-agent",
        email="second-support-agent@example.com",
        email_normalized="second-support-agent@example.com",
        department="Support",
        user_type="EMPLOYEE",
        password_hash=support_users[0].password_hash,
        is_active=True,
    )
    database.add(second_support)
    database.flush()
    support_users.append(second_support)
    customer = Client(code="TOP-AGENTS", name="Top agents client", status_id=client_status_id)
    database.add(customer)
    database.flush()
    now = server_now()
    tickets = []
    for index, assignee in enumerate(
        (support_users[0], support_users[0], support_users[1]), start=1
    ):
        tickets.append(
            Ticket(
                ticket_number=f"INC-TOP-{index}",
                ticket_type_id=ticket_type_id,
                client_id=customer.id,
                created_by_user_id=support_users[0].id,
                status_id=resolved_status_id,
                assigned_user_id=assignee.id,
                impact="LOW",
                urgency="LOW",
                priority="P4",
                subject=f"Resolved ranking ticket {index}",
                description="Independent top Support agent ranking evidence.",
                resolved_at=now,
            )
        )
    database.add_all(tickets)
    database.flush()
    policy = database.scalar(select(SlaPolicy).where(SlaPolicy.is_active.in_([True])))
    assert policy is not None
    database.add(
        TicketSlaClock(
            ticket_id=tickets[0].id,
            policy_id=policy.id,
            clock_type="RESOLUTION",
            target_minutes=240,
            started_at=now,
            due_at=now,
            breached_at=now,
            state="BREACHED",
            calculation_version="2.0",
        )
    )
    database.commit()

    response = client.get(
        "/api/v1/dashboards/top-support-agents",
        headers=admin_headers,
        params={"timezone_offset_minutes": 180},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["date_basis"] == "RESOLUTION"
    assert [item["resolved"] for item in payload["agents"][:2]] == [2, 1]
    assert payload["agents"][0]["user_id"] == support_users[0].id
    assert payload["agents"][0]["breached"] == 1


def test_personal_visibility_does_not_replace_governed_assignment(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    saved = client.put(
        "/api/v1/dashboards/config",
        headers=admin_headers,
        json={
            "name": "My governed dashboard",
            "widgets": [
                {
                    "widget_code": "total_open",
                    "title": "Open tickets",
                    "widget_type": "KPI_CARD",
                    "query_code": "total_open",
                    "position": 0,
                    "width": 2,
                    "refresh_seconds": 60,
                    "config": {},
                }
            ],
        },
    )
    assert saved.status_code == 200, saved.text
    admin = database.scalar(select(User).where(User.username == "admin"))
    preference = database.scalar(
        select(DashboardUserPreference).where(DashboardUserPreference.user_id == admin.id)
    )
    assert preference is not None
    assert "total_open" not in preference.hidden_widget_codes_json
    assert (
        database.scalar(select(DashboardAssignment).where(DashboardAssignment.user_id == admin.id))
        is None
    )

    resolved = client.get("/api/v1/dashboards/config", headers=admin_headers)
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["source"] != "USER"
    assert [item["widget_code"] for item in resolved.json()["widgets"]] == ["total_open"]
    assert len(resolved.json()["available_widgets"]) > len(resolved.json()["widgets"])
    reset = client.delete("/api/v1/dashboards/config", headers=admin_headers)
    assert reset.status_code == 200, reset.text
    assert (
        database.scalar(
            select(DashboardUserPreference).where(DashboardUserPreference.user_id == admin.id)
        )
        is None
    )


def test_dashboard_template_assignment_admin_controls(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    created = client.post(
        "/api/v1/dashboards/admin/templates",
        headers=admin_headers,
        json={
            "code": "SUPPORT_DEFAULT",
            "name": "Support default",
            "description": "Governed support layout",
            "widgets": [
                {
                    "widget_code": "total_open",
                    "title": "Open tickets",
                    "widget_type": "KPI_CARD",
                    "query_code": "total_open",
                    "position": 0,
                    "width": 2,
                    "refresh_seconds": 60,
                    "config": {},
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    template = created.json()
    assert template["version"] == 1

    updated = client.patch(
        f"/api/v1/dashboards/admin/templates/{template['id']}",
        headers=admin_headers,
        json={"expected_version": 1, "name": "Support governed default"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["version"] == 2
    stale = client.patch(
        f"/api/v1/dashboards/admin/templates/{template['id']}",
        headers=admin_headers,
        json={"expected_version": 1, "name": "Stale edit"},
    )
    assert stale.status_code == 409

    admin = database.scalar(select(User).where(User.username == "admin"))
    assignment_payload = {"dashboard_id": template["id"], "user_id": admin.id, "priority": 500}
    assignment = client.post(
        "/api/v1/dashboards/admin/assignments", headers=admin_headers, json=assignment_payload
    )
    assert assignment.status_code == 201, assignment.text
    duplicate = client.post(
        "/api/v1/dashboards/admin/assignments", headers=admin_headers, json=assignment_payload
    )
    assert duplicate.status_code == 409
    archived = client.patch(
        f"/api/v1/dashboards/admin/assignments/{assignment.json()['id']}",
        headers=admin_headers,
        json={"expected_version": 1, "is_active": False},
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["version"] == 2
    assert archived.json()["is_active"] is False

    audit_actions = set(
        database.scalars(
            select(AuditLog.action).where(
                AuditLog.entity_type.in_(["Dashboard", "DashboardAssignment"])
            )
        )
    )
    assert {
        "dashboard.template.created",
        "dashboard.template.updated",
        "dashboard.assignment.created",
        "dashboard.assignment.updated",
    } <= audit_actions

    unsafe_config = client.post(
        "/api/v1/dashboards/admin/templates",
        headers=admin_headers,
        json={
            "code": "UNSAFE_CONFIG",
            "name": "Unsafe configuration",
            "widgets": [
                {
                    "widget_code": "total_open",
                    "title": "Open tickets",
                    "widget_type": "KPI_CARD",
                    "query_code": "total_open",
                    "position": 0,
                    "width": 2,
                    "refresh_seconds": 60,
                    "config": {"route": "/users", "permission": "ticket.view.all"},
                }
            ],
        },
    )
    assert unsafe_config.status_code == 409
    assert unsafe_config.json()["error"]["code"] == "INVALID_DASHBOARD_WIDGET_CONFIG"


def test_dashboard_assignments_are_isolated_by_dashboard_type(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    admin = database.scalar(select(User).where(User.username == "admin"))
    executive = Dashboard(
        name="Executive isolated",
        code="EXECUTIVE_ISOLATED",
        assignment_type="TEMPLATE",
        assignment_id=9_999_911,
    )
    top_management = Dashboard(
        name="Top management isolated",
        code="TOP_MANAGEMENT_ISOLATED",
        assignment_type="TEMPLATE",
        assignment_id=9_999_912,
        destination="TOP_MANAGEMENT",
    )
    database.add_all([executive, top_management])
    database.flush()
    database.add_all(
        [
            DashboardWidget(
                dashboard_id=executive.id,
                widget_code="total_open",
                title="Executive open",
                widget_type="KPI_CARD",
                query_code="total_open",
                position=0,
                width=2,
                refresh_seconds=60,
            ),
            DashboardWidget(
                dashboard_id=top_management.id,
                widget_code="critical",
                title="Management critical",
                widget_type="KPI_CARD",
                query_code="critical",
                position=0,
                width=2,
                refresh_seconds=60,
            ),
            DashboardAssignment(
                dashboard_id=executive.id,
                dashboard_type="EXECUTIVE",
                user_id=admin.id,
                priority=950,
            ),
            DashboardAssignment(
                dashboard_id=top_management.id,
                dashboard_type="TOP_MANAGEMENT",
                user_id=admin.id,
                priority=950,
            ),
        ]
    )
    database.commit()

    executive_response = client.get(
        "/api/v1/dashboards/config",
        headers=admin_headers,
        params={"dashboard_type": "EXECUTIVE"},
    )
    management_response = client.get(
        "/api/v1/dashboards/config",
        headers=admin_headers,
        params={"dashboard_type": "TOP_MANAGEMENT"},
    )

    assert executive_response.status_code == 200, executive_response.text
    assert management_response.status_code == 200, management_response.text
    assert executive_response.json()["template_code"] == "EXECUTIVE_ISOLATED"
    assert management_response.json()["template_code"] == "TOP_MANAGEMENT_ISOLATED"
    assert [item["widget_code"] for item in executive_response.json()["widgets"]] == ["total_open"]
    assert [item["widget_code"] for item in management_response.json()["widgets"]] == ["critical"]


def test_new_dashboard_assignment_is_not_suppressed_by_old_hidden_preferences(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    previous = Dashboard(
        name="Previous dashboard",
        code="PREVIOUS_HIDDEN_WIDGET_DASHBOARD",
        assignment_type="TEMPLATE",
        assignment_id=9_999_921,
    )
    assigned = Dashboard(
        name="Assigned top agents dashboard",
        code="ASSIGNED_TOP_AGENTS_DASHBOARD",
        assignment_type="TEMPLATE",
        assignment_id=9_999_922,
    )
    database.add_all([previous, assigned])
    database.flush()
    database.add(
        DashboardWidget(
            dashboard_id=assigned.id,
            widget_code="top_support_agents",
            title="Top 3 Support agents",
            widget_type="KPI_CARD",
            query_code="top_support_agents",
            position=0,
            width=6,
            refresh_seconds=60,
        )
    )
    database.add(
        DashboardAssignment(
            dashboard_id=assigned.id,
            dashboard_type="EXECUTIVE",
            user_id=admin.id,
            priority=999,
        )
    )
    database.add(
        DashboardUserPreference(
            user_id=admin.id,
            dashboard_type="EXECUTIVE",
            hidden_widget_codes_json='["top_support_agents"]',
            assigned_dashboard_id=previous.id,
            assigned_dashboard_version=previous.version,
        )
    )
    database.commit()

    response = client.get("/api/v1/dashboards/config", headers=admin_headers)

    assert response.status_code == 200, response.text
    assert response.json()["template_code"] == "ASSIGNED_TOP_AGENTS_DASHBOARD"
    assert [item["widget_code"] for item in response.json()["widgets"]] == ["top_support_agents"]
    assert response.json()["hidden_widget_codes"] == []


def test_dashboard_assignment_rejects_cross_destination_template(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    template = client.post(
        "/api/v1/dashboards/admin/templates",
        headers=admin_headers,
        json={
            "code": "TOP_MANAGEMENT_DESTINATION_TEST",
            "name": "Top Management destination test",
            "destination": "TOP_MANAGEMENT",
            "widgets": [],
        },
    )
    assert template.status_code == 201, template.text

    assignment = client.post(
        "/api/v1/dashboards/admin/assignments",
        headers=admin_headers,
        json={
            "dashboard_id": template.json()["id"],
            "dashboard_type": "EXECUTIVE",
            "priority": 0,
        },
    )

    assert assignment.status_code == 409, assignment.text
    assert assignment.json()["error"]["code"] == "DASHBOARD_DESTINATION_MISMATCH"


def test_dashboard_administrator_catalog_includes_permission_metadata(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get("/api/v1/dashboards/widget-catalog", headers=admin_headers)

    assert response.status_code == 200, response.text
    catalog = {item["widget_code"]: item for item in response.json()}
    assert catalog["project_total"]["required_permissions"] == ["project_handover.view"]
    assert catalog["financial_contracts"]["required_permissions"] == ["finance.dashboard.view"]
    assert catalog["client_hours"]["widget_type"] == "STACKED_BAR"
    assert catalog["client_hours"]["query_code"] == "client_hours"


def test_dashboard_admin_can_preview_permission_filtered_user_dashboard(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    admin = database.scalar(select(User).where(User.username == "admin"))
    template = Dashboard(
        name="Preview financial dashboard",
        code="PREVIEW_FINANCE",
        assignment_type="TEMPLATE",
        assignment_id=9_999_901,
    )
    database.add(template)
    database.flush()
    database.add_all(
        [
            DashboardWidget(
                dashboard_id=template.id,
                widget_code="total_open",
                title="Open",
                widget_type="KPI_CARD",
                query_code="total_open",
                position=0,
                width=2,
                refresh_seconds=60,
            ),
            DashboardWidget(
                dashboard_id=template.id,
                widget_code="financial_contracts",
                title="Finance",
                widget_type="LINE",
                query_code="financial_contracts",
                position=1,
                width=6,
                refresh_seconds=60,
            ),
        ]
    )
    assignment = DashboardAssignment(dashboard_id=template.id, user_id=admin.id, priority=900)
    database.add(assignment)
    database.commit()

    response = client.get(
        "/api/v1/dashboards/admin/preview",
        headers=admin_headers,
        params={"user_id": admin.id},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "USER"
    assert body["assignment_id"] == assignment.id
    assert body["template_code"] == "PREVIEW_FINANCE"
    assert body["user_id"] == admin.id
    assert "dashboard.manage_widgets" in body["permission_codes"]
    assert {widget["widget_code"] for widget in body["widgets"]} == {
        "total_open",
        "financial_contracts",
    }

    missing = client.get(
        "/api/v1/dashboards/admin/preview",
        headers=admin_headers,
        params={"user_id": 999_999_999},
    )
    assert missing.status_code == 404


def test_financial_dashboard_api_and_catalog_deny_unprivileged_user(
    client: TestClient, database: Session
) -> None:
    user = User(
        full_name="Dashboard Unauthorized Control",
        username="dashboard-unauthorized",
        username_normalized="dashboard-unauthorized",
        email="dashboard-unauthorized@example.com",
        email_normalized="dashboard-unauthorized@example.com",
        password_hash="not-used-by-token-test",
        is_active=True,
        require_password_change=False,
    )
    database.add(user)
    database.commit()
    headers = {"Authorization": f"Bearer {create_access_token(user.id, TEST_SETTINGS)}"}

    financial = client.get("/api/v1/manager-finance/dashboard", headers=headers)
    assert financial.status_code == 403
    catalog = client.get("/api/v1/dashboards/widget-catalog", headers=headers)
    assert catalog.status_code == 200, catalog.text
    assert not any(item["widget_code"].startswith("financial_") for item in catalog.json())


def test_hr_profile_does_not_expand_dashboard_ticket_scope(
    client: TestClient, database: Session
) -> None:
    hr_profile = database.scalar(select(Profile).where(Profile.code == "HR"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    client_status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    ticket_status_id = database.scalar(select(TicketStatus.id).where(TicketStatus.code == "NEW"))
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    hr_user = User(
        full_name="HR Scope Control",
        username="hr-scope-control",
        username_normalized="hr-scope-control",
        email="hr-scope-control@example.com",
        email_normalized="hr-scope-control@example.com",
        password_hash="not-used-by-token-test",
        is_active=True,
        require_password_change=False,
    )
    customer = Client(code="HR-SCOPE-CLIENT", name="HR Hidden Client", status_id=client_status_id)
    database.add_all([hr_user, customer])
    database.flush()
    database.add(UserProfile(user_id=hr_user.id, profile_id=hr_profile.id, is_primary=True))
    database.add(
        Ticket(
            ticket_number="HR-SCOPE-0001",
            ticket_type_id=ticket_type_id,
            client_id=customer.id,
            created_by_user_id=admin.id,
            status_id=ticket_status_id,
            impact="LOW",
            urgency="LOW",
            priority="P4",
            subject="Must remain outside HR ticket scope",
            description="Authorization regression fixture",
            created_at=server_now(),
        )
    )
    database.commit()
    headers = {"Authorization": f"Bearer {create_access_token(hr_user.id, TEST_SETTINGS)}"}

    summary = client.get("/api/v1/dashboards/summary", headers=headers)
    assert summary.status_code == 200, summary.text
    assert summary.json()["total_tickets"] == 0
    metadata = client.get("/api/v1/dashboards/filter-metadata", headers=headers)
    assert metadata.status_code == 200, metadata.text
    assert customer.id not in {row["id"] for row in metadata.json()["clients"]}
    manipulated = client.get(
        "/api/v1/dashboards/summary",
        headers=headers,
        params={"client_id": customer.id},
    )
    assert manipulated.status_code == 403


def test_dashboard_scope_allows_own_routed_department_but_not_shared_client(
    client: TestClient, database: Session
) -> None:
    own_department = Department(code="DASH_SCOPE_OWN", name="Dashboard Scope Own")
    other_department = Department(code="DASH_SCOPE_OTHER", name="Dashboard Scope Other")
    profile = Profile(
        code="DASH_SCOPE_PROFILE",
        name="Dashboard Scope Profile",
        profile_type="EMPLOYEE",
    )
    user = User(
        full_name="Department Dashboard Scope",
        username="department-dashboard-scope",
        username_normalized="department-dashboard-scope",
        email="department-dashboard-scope@example.com",
        email_normalized="department-dashboard-scope@example.com",
        password_hash="not-used-by-token-test",
        is_active=True,
        require_password_change=False,
    )
    database.add_all([own_department, other_department, profile, user])
    database.flush()
    user.department_id = own_department.id
    database.add(UserProfile(user_id=user.id, profile_id=profile.id, is_primary=True))
    permission_ids = list(
        database.scalars(
            select(Permission.id).where(
                Permission.code.in_(["dashboard.agent", "ticket.view.department"])
            )
        )
    )
    assert len(permission_ids) == 2
    database.add_all(
        ProfilePermission(profile_id=profile.id, permission_id=permission_id)
        for permission_id in permission_ids
    )

    client_status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    ticket_status_id = database.scalar(select(TicketStatus.id).where(TicketStatus.code == "NEW"))
    closed_status_id = database.scalar(select(TicketStatus.id).where(TicketStatus.code == "CLOSED"))
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    routed_client = Client(
        code="DASH-SCOPE-ROUTED", name="Routed Department Client", status_id=client_status_id
    )
    shared_client = Client(
        code="DASH-SCOPE-SHARED", name="Shared Only Client", status_id=client_status_id
    )
    hidden_engineer = User(
        full_name="Hidden Scope Engineer",
        username="hidden-scope-engineer",
        username_normalized="hidden-scope-engineer",
        email="hidden-scope-engineer@example.com",
        email_normalized="hidden-scope-engineer@example.com",
        password_hash="not-used-by-token-test",
        is_active=True,
        require_password_change=False,
    )
    hidden_country = Country(iso_alpha2="XZ", iso_alpha3="XZZ", name="Hidden Scope Country")
    hidden_team = SupportTeam(code="DASH_HIDDEN_TEAM", name="Dashboard Hidden Team")
    own_team = SupportTeam(
        code="DASH_OWN_TEAM", name="Dashboard Own Team", department_id=own_department.id
    )
    database.add_all(
        [
            routed_client,
            shared_client,
            hidden_engineer,
            hidden_country,
            hidden_team,
            own_team,
        ]
    )
    database.flush()
    hidden_location = ClientLocation(
        client_id=routed_client.id,
        country_id=hidden_country.id,
        code="HIDDEN",
        name="Hidden Scope Location",
        zone="Hidden Scope Zone",
    )
    database.add(hidden_location)
    database.flush()
    shared_client.country_id = hidden_country.id
    shared_client.zone = hidden_location.zone
    database.add(ClientDepartmentLink(client_id=shared_client.id, department_id=own_department.id))
    database.add(SupportTeamMember(team_id=hidden_team.id, user_id=hidden_engineer.id))
    routed_ticket = Ticket(
        ticket_number="DASH-SCOPE-ROUTED-1",
        ticket_type_id=ticket_type_id,
        client_id=routed_client.id,
        created_by_user_id=admin_id,
        status_id=ticket_status_id,
        routed_department_id=own_department.id,
        routed_team_id=own_team.id,
        routing_status="NEW",
        shift_handover_status="PENDING",
        impact="HIGH",
        urgency="HIGH",
        priority="P1",
        subject="Visible routed request",
        description="Visible by routed department",
        created_at=server_now(),
    )
    breached_ticket = Ticket(
        ticket_number="DASH-SCOPE-BREACHED-1",
        ticket_type_id=ticket_type_id,
        client_id=routed_client.id,
        created_by_user_id=admin_id,
        status_id=ticket_status_id,
        routed_department_id=own_department.id,
        routed_team_id=own_team.id,
        routing_status="IN_PROGRESS",
        assigned_user_id=user.id,
        impact="LOW",
        urgency="LOW",
        priority="P4",
        subject="Visible breached request",
        description="Drilldown SLA invariant",
        created_at=server_now(),
    )
    closed_ticket = Ticket(
        ticket_number="DASH-SCOPE-CLOSED-1",
        ticket_type_id=ticket_type_id,
        client_id=routed_client.id,
        created_by_user_id=admin_id,
        status_id=closed_status_id,
        routed_department_id=own_department.id,
        routed_team_id=own_team.id,
        routing_status="RETURNED",
        impact="LOW",
        urgency="LOW",
        priority="P4",
        subject="Visible closed request",
        description="Closed-today drilldown invariant",
        created_at=server_now(),
        resolved_at=server_now(),
        closed_at=server_now(),
    )
    database.add_all(
        [
            routed_ticket,
            breached_ticket,
            closed_ticket,
            Ticket(
                ticket_number="DASH-SCOPE-SHARED-1",
                ticket_type_id=ticket_type_id,
                client_id=shared_client.id,
                created_by_user_id=admin_id,
                status_id=ticket_status_id,
                routed_department_id=other_department.id,
                routed_team_id=hidden_team.id,
                assigned_user_id=hidden_engineer.id,
                impact="LOW",
                urgency="LOW",
                priority="P4",
                subject="Shared client is not ticket access",
                description="Must remain hidden",
                created_at=server_now(),
            ),
        ]
    )
    database.flush()
    policy = database.scalar(select(SlaPolicy).where(SlaPolicy.is_active.in_([True])))
    assert policy is not None
    now = server_now()
    database.add_all(
        [
            TicketSlaClock(
                ticket_id=routed_ticket.id,
                policy_id=policy.id,
                clock_type="RESOLUTION",
                target_minutes=240,
                started_at=now,
                due_at=now + timedelta(hours=2),
                state="RUNNING",
                calculation_version="2.0",
            ),
            TicketSlaClock(
                ticket_id=breached_ticket.id,
                policy_id=policy.id,
                clock_type="RESOLUTION",
                target_minutes=100,
                started_at=now - timedelta(hours=4),
                due_at=now - timedelta(hours=2),
                # Completed breaches must remain visible in the SLA card drill-down.
                state="COMPLETED",
                breached_at=now - timedelta(hours=2),
                completed_at=now,
                accountable_minutes=200,
                customer_pending_minutes=0,
                millensys_pending_minutes=0,
                escalation_minutes=0,
                saved_minutes=-100,
                overrun_minutes=100,
                outcome_calculated_at=now,
                calculation_version="2.0",
            ),
        ]
    )
    database.commit()
    headers = {"Authorization": f"Bearer {create_access_token(user.id, TEST_SETTINGS)}"}

    summary = client.get("/api/v1/dashboards/summary", headers=headers)
    assert summary.status_code == 200, summary.text
    assert summary.json()["total_tickets"] == 3
    assert summary.json()["backlog_by_client"] == {"Routed Department Client": 2}

    # server_now() is already expressed in the configured server timezone.
    # Adding Cairo's offset again makes this test select tomorrow after 21:00.
    today = server_now().date().isoformat()
    scoped_summary = client.get(
        "/api/v1/dashboards/summary",
        headers=headers,
        params={"date_from": today, "date_to": today, "team_id": own_team.id},
    )
    assert scoped_summary.status_code == 200, scoped_summary.text
    drilldown = client.get(
        "/api/v1/tickets",
        headers=headers,
        params={"created_from": today, "created_to": today, "team_id": own_team.id},
    )
    assert drilldown.status_code == 200, drilldown.text
    assert int(drilldown.headers["X-Total-Count"]) == scoped_summary.json()["total_tickets"] == 3
    for metric, filters in (
        ("total_open", {"open_only": True}),
        ("unassigned", {"open_only": True, "unassigned_only": True}),
        ("critical", {"open_only": True, "priority": "P1"}),
        ("department_new", {"routing_status": "NEW"}),
        ("department_in_progress", {"routing_status": "IN_PROGRESS"}),
        ("department_returned", {"routing_status": "RETURNED"}),
        ("shift_handovers", {"shift_handover_only": True}),
        ("breached", {"breached_only": True}),
        ("due_soon", {"due_soon": True}),
        ("my_open", {"assigned_user_id": user.id, "open_only": True}),
        ("created_today", {"created_from": today, "created_to": today}),
        (
            "closed_today",
            {"status_code": "CLOSED", "resolved_from": today, "resolved_to": today},
        ),
    ):
        destination = client.get(
            "/api/v1/tickets",
            headers=headers,
            params={
                "created_from": today,
                "created_to": today,
                "team_id": own_team.id,
                **filters,
            },
        )
        assert destination.status_code == 200, (metric, destination.text)
        assert int(destination.headers["X-Total-Count"]) == scoped_summary.json()[metric]
    status_destination = client.get(
        "/api/v1/tickets",
        headers=headers,
        params={
            "created_from": today,
            "created_to": today,
            "team_id": own_team.id,
            "status_code": "NEW",
        },
    )
    assert status_destination.status_code == 200, status_destination.text
    assert (
        int(status_destination.headers["X-Total-Count"])
        == scoped_summary.json()["by_status"]["NEW"]
    )
    priority_segment = client.get(
        "/api/v1/tickets",
        headers=headers,
        params={
            "created_from": today,
            "created_to": today,
            "team_id": own_team.id,
            "status_code": "NEW",
            "priority": "P1",
        },
    )
    assert priority_segment.status_code == 200, priority_segment.text
    assert (
        int(priority_segment.headers["X-Total-Count"])
        == scoped_summary.json()["priority_by_status"]["NEW"]["P1"]
    )

    metadata = client.get("/api/v1/dashboards/filter-metadata", headers=headers)
    assert metadata.status_code == 200, metadata.text
    assert {row["id"] for row in metadata.json()["clients"]} == {routed_client.id}
    assert hidden_location.id not in {row["id"] for row in metadata.json()["locations"]}
    assert hidden_country.id not in {row["id"] for row in metadata.json()["countries"]}
    assert hidden_location.zone not in metadata.json()["zones"]

    manipulated = client.get(
        "/api/v1/dashboards/summary",
        headers=headers,
        params={"client_id": shared_client.id},
    )
    assert manipulated.status_code == 403
    for parameter, value in (
        ("engineer_id", hidden_engineer.id),
        ("team_id", hidden_team.id),
        ("country_id", hidden_country.id),
        ("zone", hidden_location.zone),
        ("location_id", hidden_location.id),
    ):
        response = client.get(
            "/api/v1/dashboards/summary",
            headers=headers,
            params={parameter: value},
        )
        assert response.status_code == 403, (parameter, response.text)


def test_effective_dashboard_follows_all_precedence_levels(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    admin = database.scalar(select(User).where(User.username == "admin"))
    profile = database.scalar(
        select(Profile)
        .join(UserProfile)
        .where(UserProfile.user_id == admin.id, UserProfile.is_primary.in_([True]))
    )
    department = Department(code="DASHBOARD_TEST", name="Dashboard Test")
    database.add(department)
    database.flush()
    admin.department_id = department.id

    targets = [
        ("SYSTEM", {}),
        ("DEPARTMENT", {"department_id": department.id}),
        ("PROFILE", {"profile_id": profile.id}),
        ("PROFILE_DEPARTMENT", {"profile_id": profile.id, "department_id": department.id}),
        ("USER", {"user_id": admin.id}),
    ]
    assignments: dict[str, DashboardAssignment] = {}
    for index, (source, target) in enumerate(targets, start=1):
        dashboard = Dashboard(
            name=source, code=f"TEST_{source}", assignment_type="TEMPLATE", assignment_id=index
        )
        database.add(dashboard)
        database.flush()
        database.add(
            DashboardWidget(
                dashboard_id=dashboard.id,
                widget_code="total_open",
                title=source,
                widget_type="KPI_CARD",
                query_code="total_open",
                position=0,
                width=2,
                refresh_seconds=60,
            )
        )
        assignment = DashboardAssignment(dashboard_id=dashboard.id, priority=10, **target)
        database.add(assignment)
        assignments[source] = assignment
    database.commit()

    impact = client.get("/api/v1/dashboards/admin/assignment-impact", headers=admin_headers)
    assert impact.status_code == 200, impact.text
    affected = {row["assignment_id"]: row["affected_user_count"] for row in impact.json()}
    assert affected[assignments["USER"].id] == 1

    scenario = client.get(
        "/api/v1/dashboards/admin/scenario-preview",
        headers=admin_headers,
        params={"profile_id": profile.id, "department_id": department.id},
    )
    assert scenario.status_code == 200, scenario.text
    assert scenario.json()["source"] == "PROFILE_DEPARTMENT"
    assert scenario.json()["name"] == "PROFILE_DEPARTMENT"
    assert scenario.json()["profile_id"] == profile.id
    assert scenario.json()["department_id"] == department.id

    assignments["USER"].effective_from = server_now() + timedelta(days=1)
    database.commit()
    future_ignored = client.get("/api/v1/dashboards/config", headers=admin_headers)
    assert future_ignored.json()["source"] == "PROFILE_DEPARTMENT"
    assignments["USER"].effective_from = None
    database.commit()

    for expected in ("USER", "PROFILE_DEPARTMENT", "PROFILE", "DEPARTMENT", "SYSTEM"):
        response = client.get("/api/v1/dashboards/config", headers=admin_headers)
        assert response.status_code == 200, response.text
        assert response.json()["source"] == expected
        assert response.json()["name"] == expected
        assignments[expected].is_active = False
        database.commit()


def test_dashboard_summary_uses_bounded_query_count(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    statements = 0

    def count_query(*_args: object) -> None:
        nonlocal statements
        statements += 1

    engine = database.get_bind()
    event.listen(engine, "before_cursor_execute", count_query)
    try:
        response = client.get("/api/v1/dashboards/summary", headers=admin_headers)
    finally:
        event.remove(engine, "before_cursor_execute", count_query)
    assert response.status_code == 200, response.text
    assert statements <= DASHBOARD_SUMMARY_MAX_QUERIES


def test_dashboard_interactive_endpoints_stay_within_resource_budgets(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    impact_statements = 0

    def count_impact_query(*_args: object) -> None:
        nonlocal impact_statements
        impact_statements += 1

    tracemalloc.start()
    started = perf_counter()
    summary = client.get("/api/v1/dashboards/summary", headers=admin_headers)
    summary_elapsed = perf_counter() - started
    _, summary_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert summary.status_code == 200, summary.text
    assert summary_elapsed <= DASHBOARD_INTERACTIVE_MAX_SECONDS
    assert len(summary.content) <= DASHBOARD_SUMMARY_MAX_RESPONSE_BYTES
    assert summary_peak <= DASHBOARD_SUMMARY_MAX_PEAK_BYTES
    assert len(summary.json()["agent_kpis"]) <= DASHBOARD_SUMMARY_MAX_DETAIL_ROWS
    assert len(summary.json()["product_kpis"]) <= DASHBOARD_SUMMARY_MAX_DETAIL_ROWS

    engine = database.get_bind()
    event.listen(engine, "before_cursor_execute", count_impact_query)
    started = perf_counter()
    try:
        impact = client.get("/api/v1/dashboards/admin/assignment-impact", headers=admin_headers)
    finally:
        impact_elapsed = perf_counter() - started
        event.remove(engine, "before_cursor_execute", count_impact_query)
    assert impact.status_code == 200, impact.text
    assert impact_elapsed <= DASHBOARD_INTERACTIVE_MAX_SECONDS
    assert impact_statements <= DASHBOARD_ASSIGNMENT_IMPACT_MAX_QUERIES
    assert len(impact.content) <= DASHBOARD_ASSIGNMENT_IMPACT_MAX_RESPONSE_BYTES
    assert len(impact.json()) <= DASHBOARD_ASSIGNMENT_IMPACT_MAX_ROWS


def test_dashboard_large_period_stays_below_sql_server_parameter_limit(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    client_status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    ticket_status_id = database.scalar(select(TicketStatus.id).where(TicketStatus.code == "NEW"))
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    assert all((client_status_id, ticket_status_id, ticket_type_id, admin_id))
    customer = Client(code="DASH-SCALE", name="Dashboard Scale Client", status_id=client_status_id)
    database.add(customer)
    database.flush()
    created_at = datetime(2026, 4, 1, tzinfo=UTC)
    database.execute(
        insert(Ticket),
        [
            {
                "ticket_number": f"SCALE-{index:05d}",
                "ticket_type_id": ticket_type_id,
                "client_id": customer.id,
                "created_by_user_id": admin_id,
                "status_id": ticket_status_id,
                "impact": "LOW",
                "urgency": "LOW",
                "priority": "P4",
                "subject": f"Scale regression {index}",
                "description": "Verifies bounded SQL parameters.",
                "created_at": created_at,
            }
            for index in range(2101)
        ],
    )
    database.commit()

    def enforce_sql_server_parameter_limit(
        _conn: object,
        _cursor: object,
        _statement: str,
        parameters: object,
        _context: object,
        executemany: bool,
    ) -> None:
        if not executemany and hasattr(parameters, "__len__"):
            assert len(parameters) <= 2000  # type: ignore[arg-type]

    engine = database.get_bind()
    event.listen(engine, "before_cursor_execute", enforce_sql_server_parameter_limit)
    try:
        response = client.get(
            "/api/v1/dashboards/summary",
            headers=admin_headers,
            params={"date_from": "2026-01-01", "date_to": "2026-12-31"},
        )
    finally:
        event.remove(engine, "before_cursor_execute", enforce_sql_server_parameter_limit)
    assert response.status_code == 200, response.text
    assert response.json()["total_tickets"] == 2101


def test_dashboard_and_saved_view(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    dashboard = client.get("/api/v1/dashboards/summary", headers=admin_headers)
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["total_open"] == 0
    assert dashboard.json()["backlog_by_client"] == {}
    assert dashboard.json()["backlog_by_product"] == {}
    assert dashboard.json()["backlog_by_module"] == {}
    assert dashboard.json()["workload_by_engineer"] == {}
    assert dashboard.json()["backlog_by_team"] == {}
    assert dashboard.json()["sla_compliance_percent"] is None
    assert sum(dashboard.json()["aging_buckets"].values()) == 0
    assert sum(dashboard.json()["inflow_last_7_days"].values()) == 0
    assert dashboard.json()["average_resolution_hours"] is None
    assert dashboard.json()["reopen_rate_percent"] == 0
    assert dashboard.json()["active_escalations"] == 0
    assert [item["agent"] for item in dashboard.json()["agent_kpis"]] == [
        "Development Administrator",
        "Support",
    ]
    assert dashboard.json()["agent_kpis"][0]["assigned"] == 0
    assert dashboard.json()["product_kpis"] == []
    client_status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    ticket_status_id = database.scalar(select(TicketStatus.id).where(TicketStatus.code == "NEW"))
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert client_status_id is not None
    assert ticket_status_id is not None
    assert ticket_type_id is not None
    assert admin is not None
    customer = Client(code="DASHBOARD", name="Dashboard Client", status_id=client_status_id)
    product = Product(code="DASH-PRODUCT", name="Dashboard Product")
    database.add_all([customer, product])
    database.flush()
    database.add(
        Ticket(
            ticket_number="INC-DASHBOARD",
            ticket_type_id=ticket_type_id,
            client_id=customer.id,
            created_by_user_id=admin.id,
            status_id=ticket_status_id,
            assigned_user_id=admin.id,
            assigned_team="Support",
            product_id=product.id,
            impact="MEDIUM",
            urgency="MEDIUM",
            priority="P3",
            subject="Dashboard aggregation ticket",
            description="Ticket used to validate manager dashboard breakdowns.",
        )
    )
    database.commit()
    populated = client.get("/api/v1/dashboards/summary", headers=admin_headers).json()
    assert populated["backlog_by_client"] == {"Dashboard Client": 1}
    assert populated["backlog_by_product"] == {"Dashboard Product": 1}
    assert populated["backlog_by_module"] == {"No module": 1}
    assert populated["workload_by_engineer"] == {admin.full_name: 1}
    assert populated["backlog_by_team"] == {"Support": 1}
    assert populated["aging_buckets"]["0–1 days"] == 1
    assert sum(populated["inflow_last_7_days"].values()) == 1
    assert populated["average_resolution_hours"] is None
    assert populated["reopen_rate_percent"] == 0
    assert populated["active_escalations"] == 0
    assert populated["top_categories"] == {"Uncategorized": 1}
    assert {
        key: populated["agent_kpis"][0][key]
        for key in ("user_id", "agent", "assigned", "open", "resolved", "breached")
    } == {
        "user_id": admin.id,
        "agent": admin.full_name,
        "assigned": 1,
        "open": 1,
        "resolved": 0,
        "breached": 0,
    }
    assert populated["agent_kpis"][0]["tickets_by_status"] == {"NEW": 1}
    assert populated["agent_kpis"][0]["escalation_assignments"] == 0
    assert populated["agent_kpis"][0]["tasks_created"] == 0
    assert populated["agent_kpis"][0]["knowledge_articles"] == 0
    activity = client.post(
        "/api/v1/agent-activities",
        headers=admin_headers,
        json={
            "user_id": admin.id,
            "activity_type": "TRAINING",
            "participation_role": "FACILITATOR",
            "title": "PACS troubleshooting workshop",
            "duration_minutes": 90,
            "occurred_at": server_now().isoformat(),
            "notes": "Internal knowledge-transfer session",
        },
    )
    assert activity.status_code == 201, activity.text
    refreshed_kpis = client.get("/api/v1/dashboards/summary", headers=admin_headers).json()[
        "agent_kpis"
    ][0]
    assert refreshed_kpis["training_delivered"] == 1
    assert refreshed_kpis["external_activities"] == 1
    quarter = (server_now().month - 1) // 3 + 1
    quarterly = client.get(
        "/api/v1/dashboards/summary",
        headers=admin_headers,
        params={"kpi_quarter": f"{server_now().year}-Q{quarter}"},
    )
    assert quarterly.status_code == 200, quarterly.text
    assert quarterly.json()["kpi_month"].endswith(f"Q{quarter}")
    excel = client.get(
        "/api/v1/reports/agent-kpis.xlsx",
        headers=admin_headers,
        params={"kpi_quarter": f"{server_now().year}-Q{quarter}"},
    )
    assert excel.status_code == 200, excel.text
    assert excel.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    workbook = load_workbook(BytesIO(excel.content))
    assert workbook.sheetnames == [
        "HR KPI Summary",
        "Ticket Status Detail",
        "KPI Definitions",
        "Activity Evidence",
        "After-Shift Evidence",
    ]
    assert populated["product_kpis"][0] == {
        "product": "Dashboard Product",
        "module": "No module",
        "total": 1,
        "open": 1,
        "resolved": 0,
        "breached": 0,
        "average_resolution_hours": None,
    }
    view = client.post(
        "/api/v1/saved-views",
        headers=admin_headers,
        json={
            "name": "Critical open",
            "scope": "PRIVATE",
            "filters": {"priority": "P1", "closed": False},
            "columns": ["ticket_number", "subject", "priority"],
        },
    )
    assert view.status_code == 201, view.text
    defaulted = client.patch(
        f"/api/v1/saved-views/{view.json()['id']}/default", headers=admin_headers
    )
    assert defaulted.status_code == 200, defaulted.text
    assert defaulted.json()["is_default"] is True
    listing = client.get("/api/v1/saved-views", headers=admin_headers)
    assert [item["name"] for item in listing.json()] == ["Critical open"]
    deleted = client.delete(f"/api/v1/saved-views/{view.json()['id']}", headers=admin_headers)
    assert deleted.status_code == 204
    assert client.get("/api/v1/saved-views", headers=admin_headers).json() == []
    recreated = client.post(
        "/api/v1/saved-views",
        headers=admin_headers,
        json={
            "name": "Critical open",
            "scope": "PRIVATE",
            "filters": {"priority": "P2"},
            "columns": ["ticket_number", "subject"],
        },
    )
    assert recreated.status_code == 201, recreated.text
    assert recreated.json()["id"] == view.json()["id"]
    assert json.loads(recreated.json()["filter_json"]) == {"priority": "P2"}
    assert {
        "saved_view.created",
        "saved_view.defaulted",
        "saved_view.deleted",
    } <= set(database.scalars(select(AuditLog.action).where(AuditLog.entity_type == "SavedView")))


def test_export_formula_injection_protection() -> None:
    assert safe_cell("=2+2") == "'=2+2"
    assert safe_cell("normal") == "normal"


def test_ticket_grid_preference_and_saved_view_update(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    preference = {
        "columns": ["ticket_number", "subject", "priority"],
        "column_widths": {"subject": 320},
        "density": "COMPACT",
        "page_size": 50,
        "sort_by": "priority",
        "sort_direction": "asc",
        "group_by": "status",
        "default_view_mode": "CARDS",
        "selected_group_values": ["1", "2"],
        "board_settings": {
            "density": "DETAILED",
            "fields": ["client", "status"],
        },
    }
    saved = client.put(
        "/api/v1/ticket-grid-preference", headers=admin_headers, json=preference
    )
    assert saved.status_code == 200, saved.text
    assert client.get(
        "/api/v1/ticket-grid-preference", headers=admin_headers
    ).json() == preference

    created = client.post(
        "/api/v1/saved-views",
        headers=admin_headers,
        json={"name": "Editable", "filters": {"priority": "P1"}},
    )
    assert created.status_code == 201, created.text
    updated = client.put(
        f"/api/v1/saved-views/{created.json()['id']}",
        headers=admin_headers,
        json={
            "name": "Edited",
            "filters": {"priority": "P2"},
            "sort": [{"field": "updated_at", "direction": "desc"}],
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Edited"
    assert json.loads(updated.json()["filter_json"]) == {"priority": "P2"}


def test_average_resolution_starts_when_dedicated_engineer_starts_progress(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    now = server_now()
    client_status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    resolved_status_id = database.scalar(
        select(TicketStatus.id).where(TicketStatus.code == "RESOLVED")
    )
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert client_status_id and resolved_status_id and ticket_type_id and admin
    engineer = User(
        full_name="Duration Test Engineer",
        username="duration-test-engineer",
        username_normalized="duration-test-engineer",
        email="duration-test-engineer@example.com",
        email_normalized="duration-test-engineer@example.com",
        department="Support",
        user_type="EMPLOYEE",
        password_hash=admin.password_hash,
        is_active=True,
    )
    database.add(engineer)
    customer = Client(code="DURATION", name="Duration Client", status_id=client_status_id)
    database.add(customer)
    database.flush()
    ticket = Ticket(
        ticket_number="INC-DURATION",
        ticket_type_id=ticket_type_id,
        client_id=customer.id,
        created_by_user_id=admin.id,
        status_id=resolved_status_id,
        assigned_user_id=engineer.id,
        assigned_team="Support",
        impact="MEDIUM",
        urgency="MEDIUM",
        priority="P3",
        subject="Dedicated resolution timing",
        description="Verifies that intake time is excluded from average resolution.",
        created_at=now - timedelta(hours=8),
        progress_started_at=now - timedelta(hours=2),
        resolved_at=now,
    )
    database.add(ticket)
    database.flush()
    database.add(
        TicketAssignmentHistory(
            ticket_id=ticket.id,
                assigned_user_id=engineer.id,
            assigned_team="Support",
            assigned_by_user_id=admin.id,
            created_at=now - timedelta(hours=3),
        )
    )
    database.commit()

    ticket_local_date = as_server_time(ticket.created_at).date()
    resolution_local_date = as_server_time(ticket.resolved_at).date()
    summary = client.get(
        "/api/v1/dashboards/summary",
        headers=admin_headers,
        params={
            "date_from": ticket_local_date.isoformat(),
            "date_to": resolution_local_date.isoformat(),
        },
    )

    assert summary.status_code == 200, summary.text
    assert summary.json()["average_resolution_hours"] == 3.0
    assert summary.json()["agent_kpis"][0]["average_resolution_hours"] == 3.0


def test_team_saved_view_is_visible_to_team_members(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    profile = database.scalar(select(Profile).where(Profile.code == "L1_SUPPORT"))
    teammate = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "full_name": "Queue Teammate",
            "username": "queue.teammate",
            "email": "queue.teammate@example.com",
            "password": "TemporaryPassword!123",
            "primary_profile_id": profile.id,
            "user_type": "EMPLOYEE",
            "require_password_change": False,
        },
    )
    assert teammate.status_code == 201, teammate.text
    team = client.post(
        "/api/v1/support-teams",
        headers=admin_headers,
        json={
            "code": "SHARED_QUEUE",
            "name": "Shared Queue",
            "member_user_ids": [teammate.json()["id"]],
        },
    )
    assert team.status_code == 201, team.text
    view = client.post(
        "/api/v1/saved-views",
        headers=admin_headers,
        json={
            "name": "Team priority queue",
            "scope": "TEAM",
            "team_id": team.json()["id"],
            "filters": {"priority": "P1"},
            "columns": ["ticket_number", "subject", "priority"],
        },
    )
    assert view.status_code == 201, view.text
    login = client.post(
        "/api/v1/auth/login",
        json={"login": "queue.teammate", "password": "TemporaryPassword!123"},
    )
    teammate_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    listing = client.get("/api/v1/saved-views", headers=teammate_headers)
    assert listing.status_code == 200, listing.text
    assert [(item["name"], item["scope"], item["team_id"]) for item in listing.json()] == [
        ("Team priority queue", "TEAM", team.json()["id"])
    ]
    cannot_default_shared = client.patch(
        f"/api/v1/saved-views/{view.json()['id']}/default", headers=teammate_headers
    )
    assert cannot_default_shared.status_code == 404


def test_standard_department_queues_and_dashboard_catalog_are_available(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    created = client.post("/api/v1/saved-views/department-defaults", headers=admin_headers)
    assert created.status_code == 200, created.text
    assert {row["name"] for row in created.json()} == {
        "My Tickets",
        "My Team Requests",
        "My Department Requests",
        "New Department Requests",
        "Department Work In Progress",
        "Escalations Sent",
        "Resolved / Returned",
    }
    repeated = client.post("/api/v1/saved-views/department-defaults", headers=admin_headers)
    assert repeated.status_code == 200, repeated.text
    assert len(client.get("/api/v1/saved-views", headers=admin_headers).json()) == 7
    catalog = client.get("/api/v1/dashboards/widget-catalog", headers=admin_headers)
    assert catalog.status_code == 200, catalog.text
    codes = {row["widget_code"] for row in catalog.json()}
    assert {"department_new", "department_in_progress", "department_returned"} <= codes
    assert {
        "financial_contract_value",
        "financial_contract_expiry",
        "financial_discounts",
        "financial_adjustments",
    } <= codes
    assert {
        "hr_total_employees",
        "hr_head_vacancies",
        "hr_kpi_pending",
        "hr_onboarding_in_progress",
        "hr_unscheduled_employees",
    } <= codes
    assert {
        "project_total",
        "project_delivered",
        "project_awaiting_acceptance",
        "project_pending_products",
        "projects_by_status",
        "projects_by_client",
    } <= codes
