from datetime import UTC, datetime

from sqlalchemy import select

from app.modules.clients.models import ClientStatus, SupportTeam, SupportTeamMember
from app.modules.iam.models import (
    Department,
    Permission,
    Profile,
    ProfilePermission,
    User,
    UserProfile,
)
from app.modules.iam.security import hash_password
from app.modules.projects.models import (
    CompanyProject,
    ProjectKpiDefinition,
    ProjectTask,
    ProjectTaskAssignee,
    ProjectTeam,
    ProjectWorkLog,
)
from app.tests.test_project_portfolio import _scoped_user_headers


def _definition(**overrides) -> ProjectKpiDefinition:
    values = {
        "code": "TASK_ON_TIME_RATE",
        "name": "Tasks on time",
        "domain": "IMPLEMENTATION",
        "description": "Completed planned tasks delivered on time.",
        "formula": "on-time completed planned tasks / completed planned tasks * 100",
        "numerator_definition": "COUNT(on-time completed planned tasks)",
        "denominator_definition": "COUNT(completed planned tasks)",
        "unit": "PERCENT",
        "target_direction": "HIGHER_IS_BETTER",
        "zero_denominator_policy": "NULL",
        "time_basis": "EVENT_TIME",
        "allowed_scopes": ["DEPARTMENT"],
        "eligibility_rules": ["Completed in selected period"],
        "exclusions": ["Test records"],
        "required_permission": "analytics.implementation.view",
        "drilldown_resource": "/api/v1/projects/{project_id}/execution",
        "owner_role": "IMPLEMENTATION",
        "version": 1,
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    values.update(overrides)
    return ProjectKpiDefinition(**values)


def test_dictionary_exposes_complete_governance_contract(client, admin_headers, database):
    database.add(_definition())
    database.commit()

    response = client.get(
        "/api/v1/project-analytics/kpi-dictionary?domain=implementation",
        headers=admin_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["code"] == "TASK_ON_TIME_RATE"
    assert payload[0]["zero_denominator_policy"] == "NULL"
    assert payload[0]["allowed_scopes"] == ["DEPARTMENT"]
    assert payload[0]["required_permission"] == "analytics.implementation.view"
    assert payload[0]["drilldown_resource"].endswith("/execution")


def test_dictionary_hides_inactive_by_default(client, admin_headers, database):
    database.add(_definition(code="RETIRED_KPI", is_active=False))
    database.commit()
    normal = client.get("/api/v1/project-analytics/kpi-dictionary", headers=admin_headers)
    expanded = client.get(
        "/api/v1/project-analytics/kpi-dictionary?include_inactive=true",
        headers=admin_headers,
    )
    assert normal.status_code == 200 and normal.json() == []
    assert expanded.status_code == 200 and len(expanded.json()) == 1


def test_scope_policy_separates_dictionary_from_metric_access(client, admin_headers):
    response = client.get("/api/v1/project-analytics/scope-policy", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["domains"]["EXECUTIVE"] == "analytics.executive.view"
    assert any("does not grant" in rule for rule in payload["rules"])
    assert any("narrower scope" in rule for rule in payload["rules"])


def test_seed_grants_are_least_privilege(database):
    support = database.scalar(select(Profile).where(Profile.code == "SUPPORT_MANAGER"))
    permission_codes = set(
        database.scalars(
            select(Permission.code)
            .join(ProfilePermission, ProfilePermission.permission_id == Permission.id)
            .where(ProfilePermission.profile_id == support.id)
        )
    )
    assert "analytics.dictionary.view" in permission_codes
    assert "analytics.support_readiness.view" in permission_codes
    assert "analytics.implementation.view" not in permission_codes
    assert "analytics.executive.view" not in permission_codes


def _project(client, headers, database):
    account = client.post(
        "/api/v1/accounts", headers=headers, json={"code": "ANL", "name": "Analytics Account"}
    ).json()
    organization = client.post(
        "/api/v1/organizations",
        headers=headers,
        json={"account_id": account["id"], "code": "ANL-ORG", "name": "Analytics Org"},
    ).json()
    status_id = database.scalar(select(ClientStatus.id))
    customer = client.post(
        "/api/v1/clients",
        headers=headers,
        json={"name": "Analytics Client", "status_id": status_id, "organization_id": organization["id"]},
    ).json()
    department = Department(code="ANL-IMP", name="Analytics Implementation", is_active=True)
    database.add(department)
    database.commit()
    manager_id = database.scalar(select(User.id).where(User.username == "admin"))
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "project_number": "PRJ-ANL",
            "name": "Analytics project",
            "account_id": account["id"],
            "organization_id": organization["id"],
            "client_id": customer["id"],
            "owning_department_id": department.id,
            "project_manager_user_id": manager_id,
            "planned_end_date": "2026-11-30",
        },
    ).json()
    return project, department, manager_id


def test_projection_and_drilldown_reconcile_exactly(client, admin_headers, database):
    project, _, manager_id = _project(client, admin_headers, database)
    database.add(
        _definition(
            code="UNPLANNED_EFFORT_PERCENT",
            name="Unplanned effort",
            formula="approved unplanned minutes / all minutes * 100",
        )
    )
    planned = ProjectTask(
        project_id=project["id"],
        task_number="T-1",
        title="Planned task",
        classification="PLANNED",
        status="IN_PROGRESS",
        owner_user_id=manager_id,
        created_by_user_id=manager_id,
    )
    unplanned = ProjectTask(
        project_id=project["id"],
        task_number="T-2",
        title="Approved unplanned task",
        classification="UNPLANNED",
        approval_status="APPROVED",
        status="IN_PROGRESS",
        owner_user_id=manager_id,
        created_by_user_id=manager_id,
    )
    database.add_all([planned, unplanned])
    database.flush()
    database.add_all(
        [
            ProjectWorkLog(task_id=planned.id, user_id=manager_id, started_at=datetime(2026, 11, 10, tzinfo=UTC), ended_at=datetime(2026, 11, 10, 1, tzinfo=UTC), duration_minutes=60),
            ProjectWorkLog(task_id=unplanned.id, user_id=manager_id, started_at=datetime(2026, 11, 11, tzinfo=UTC), ended_at=datetime(2026, 11, 11, 0, 20, tzinfo=UTC), duration_minutes=20),
        ]
    )
    database.commit()

    params = "period_start=2026-11-01&period_end=2026-11-30"
    projection = client.get(
        f"/api/v1/project-analytics/projections/IMPLEMENTATION?{params}", headers=admin_headers
    )
    assert projection.status_code == 200, projection.text
    metric = projection.json()["metrics"][0]
    assert metric["value"] == 25.0
    assert metric["numerator"] == 20.0
    assert metric["denominator"] == 80.0

    detail = client.get(
        f"/api/v1/project-analytics/projections/kpi/UNPLANNED_EFFORT_PERCENT/drilldown?{params}",
        headers=admin_headers,
    )
    assert detail.status_code == 200, detail.text
    rows = detail.json()["rows"]
    assert sum(row["numerator_contribution"] for row in rows) == metric["numerator"]
    assert sum(row["denominator_contribution"] for row in rows) == metric["denominator"]
    assert len(rows) == metric["drilldown_count"]


def test_projection_reports_missing_completion_evidence(client, admin_headers, database):
    _project(client, admin_headers, database)
    database.add(
        _definition(
            code="TASK_ON_TIME_RATE",
            name="Tasks on time",
            formula="on-time tasks / completed tasks * 100",
        )
    )
    database.commit()
    response = client.get(
        "/api/v1/project-analytics/projections/IMPLEMENTATION?period_start=2026-11-01&period_end=2026-11-30",
        headers=admin_headers,
    )
    assert response.status_code == 200
    metric = response.json()["metrics"][0]
    assert metric["status"] == "UNAVAILABLE"
    assert "completion timestamp" in metric["unavailable_reason"]
    assert metric["value"] is None


def test_domain_permission_is_enforced_independently(client, database):
    department = Department(code="SUP-ANL", name="Support Analytics", is_active=True)
    database.add(department)
    database.flush()
    support = User(
        full_name="Support analytics user",
        username="support.analytics",
        username_normalized="support.analytics",
        email="support.analytics@example.com",
        email_normalized="support.analytics@example.com",
        password_hash=hash_password("SupportAnalytics!123"),
        department_id=department.id,
        is_active=True,
        require_password_change=False,
    )
    profile = database.scalar(select(Profile).where(Profile.code == "SUPPORT_MANAGER"))
    database.add(support)
    database.flush()
    database.add(UserProfile(user_id=support.id, profile_id=profile.id, is_primary=True))
    database.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"login": "support.analytics", "password": "SupportAnalytics!123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.get(
        "/api/v1/project-analytics/projections/IMPLEMENTATION?period_start=2026-11-01&period_end=2026-11-30",
        headers=headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["details"]["required_permission"] == "analytics.implementation.view"


def test_team_and_engineer_filters_scope_work_evidence(client, admin_headers, database):
    project, department, manager_id = _project(client, admin_headers, database)
    engineer = User(
        full_name="Implementation Engineer",
        username="implementation.engineer",
        username_normalized="implementation.engineer",
        email="implementation.engineer@example.com",
        email_normalized="implementation.engineer@example.com",
        password_hash=hash_password("ImplementationEngineer!123"),
        department_id=department.id,
        is_active=True,
        require_password_change=False,
    )
    database.add(engineer)
    database.flush()
    team = SupportTeam(
        code="IMP-TEAM",
        name="Implementation Team",
        department_id=department.id,
        is_active=True,
    )
    database.add(team)
    database.flush()
    database.add_all(
        [
            SupportTeamMember(team_id=team.id, user_id=engineer.id),
            ProjectTeam(project_id=project["id"], team_id=team.id, role="IMPLEMENTATION"),
            _definition(
                code="UNPLANNED_EFFORT_PERCENT",
                name="Unplanned effort",
                formula="approved unplanned minutes / all minutes * 100",
            ),
        ]
    )
    owned = ProjectTask(
        project_id=project["id"], task_number="ENG-1", title="Engineer task",
        classification="UNPLANNED", approval_status="APPROVED", status="IN_PROGRESS",
        owner_user_id=engineer.id, created_by_user_id=manager_id,
    )
    other = ProjectTask(
        project_id=project["id"], task_number="ENG-2", title="Manager task",
        classification="PLANNED", status="IN_PROGRESS",
        owner_user_id=manager_id, created_by_user_id=manager_id,
    )
    database.add_all([owned, other])
    database.flush()
    database.add(ProjectTaskAssignee(task_id=owned.id, user_id=engineer.id))
    database.add_all(
        [
            ProjectWorkLog(task_id=owned.id, user_id=engineer.id, started_at=datetime(2026, 11, 12, tzinfo=UTC), duration_minutes=30),
            ProjectWorkLog(task_id=other.id, user_id=manager_id, started_at=datetime(2026, 11, 12, tzinfo=UTC), duration_minutes=70),
        ]
    )
    database.commit()

    options = client.get("/api/v1/project-analytics/options/IMPLEMENTATION", headers=admin_headers)
    assert options.status_code == 200
    assert any(row["id"] == team.id for row in options.json()["teams"])
    assert any(row["id"] == engineer.id for row in options.json()["engineers"])

    params = f"period_start=2026-11-01&period_end=2026-11-30&team_id={team.id}&user_id={engineer.id}"
    response = client.get(
        f"/api/v1/project-analytics/projections/IMPLEMENTATION?{params}", headers=admin_headers
    )
    assert response.status_code == 200, response.text
    metric = response.json()["metrics"][0]
    assert metric["numerator"] == 30.0
    assert metric["denominator"] == 30.0
    assert metric["value"] == 100.0
    assert response.json()["scope"]["team_id"] == team.id
    assert response.json()["scope"]["user_id"] == engineer.id


def test_dedicated_implementation_engineer_analytics_is_personal(client, admin_headers, database):
    _, department, _ = _project(client, admin_headers, database)
    engineer, headers = _scoped_user_headers(
        database, department, "analytics.implementation.view", "workspace.implementation.access",
    )
    url = "/api/v1/project-analytics/projections/IMPLEMENTATION?period_start=2026-11-01&period_end=2026-11-30"
    response = client.get(url, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["scope"]["user_id"] == engineer.id
    other_id = database.scalar(select(User.id).where(User.username == "admin"))
    assert client.get(f"{url}&user_id={other_id}", headers=headers).status_code == 403


def test_support_readiness_queue_explains_activation_risk(client, admin_headers, database):
    project, _, _ = _project(client, admin_headers, database)
    database.get(CompanyProject, project["id"]).status = "DELIVERY_REVIEW"
    database.commit()
    initialized = client.post(
        f"/api/v1/projects/{project['id']}/handover/initialize", headers=admin_headers
    )
    assert initialized.status_code == 201

    response = client.get(
        "/api/v1/project-analytics/support-readiness/queue"
        "?period_start=2026-11-01&period_end=2026-11-30",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 1
    assert payload["activation_risk"] == 1
    item = payload["items"][0]
    assert item["project_id"] == project["id"]
    assert item["status"] == "DRAFT"
    assert item["missing_required_items"] > 0
    assert item["missing_evidence_items"] > 0
    assert item["risk_level"] == "HIGH"
    assert any("evidence" in reason for reason in item["risk_reasons"])


def test_executive_portfolio_aggregates_account_and_organization(
    client, admin_headers, database
):
    project, _, _ = _project(client, admin_headers, database)
    update = client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=admin_headers,
        json={"health": "AT_RISK", "progress_percent": 40},
    )
    assert update.status_code == 200
    database.get(CompanyProject, project["id"]).status = "DELIVERY_REVIEW"
    database.commit()
    initialized = client.post(
        f"/api/v1/projects/{project['id']}/handover/initialize", headers=admin_headers
    )
    assert initialized.status_code == 201

    response = client.get(
        "/api/v1/project-analytics/executive/portfolio"
        "?period_start=2026-11-01&period_end=2026-11-30",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total_projects"] == 1
    assert payload["total_at_risk"] == 1
    assert payload["scope"]["global_scope"] is True
    assert payload["rows"] == [
        {
            "account_id": project["account_id"],
            "account_name": "Analytics Account",
            "organization_id": project["organization_id"],
            "organization_name": "Analytics Org",
            "project_count": 1,
            "at_risk_count": 1,
            "average_progress_percent": 40.0,
            "handover_count": 1,
            "average_readiness_percent": 0.0,
        }
    ]
