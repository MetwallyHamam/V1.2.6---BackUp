from sqlalchemy import select

from app.modules.clients.models import (
    ClientStatus,
    Product,
    ProductModule,
    SupportTeam,
    SupportTeamMember,
)
from app.modules.iam.models import (
    Department,
    Permission,
    Profile,
    ProfilePermission,
    User,
    UserProfile,
)
from app.modules.iam.security import create_access_token, hash_password
from app.modules.notifications.models import Notification
from app.modules.projects.models import (
    CompanyProject,
    ProjectAssignmentRequest,
    ProjectEvidence,
    ProjectModuleScope,
    ProjectPhase,
    ProjectPhaseModuleScope,
    ProjectProductScope,
    ProjectTask,
)
from app.tests.conftest import TEST_SETTINGS


def _scoped_user_headers(database, department: Department, *permission_codes: str):
    user = User(
        full_name=f"{department.name} scoped user",
        username=f"scope-{department.code.lower()}",
        username_normalized=f"scope-{department.code.lower()}",
        email=f"scope-{department.code.lower()}@example.com",
        email_normalized=f"scope-{department.code.lower()}@example.com",
        password_hash=hash_password("ScopedPassword!123"),
        department_id=department.id,
        is_active=True,
        require_password_change=False,
    )
    profile = Profile(
        code=f"SCOPE-{department.code}",
        name=f"{department.name} scoped profile",
        profile_type="EMPLOYEE",
        is_active=True,
    )
    database.add_all([user, profile])
    database.flush()
    database.add(UserProfile(user_id=user.id, profile_id=profile.id, is_primary=True))
    permission_ids = list(
        database.scalars(select(Permission.id).where(Permission.code.in_(permission_codes)))
    )
    assert len(permission_ids) == len(set(permission_codes))
    database.add_all(
        ProfilePermission(profile_id=profile.id, permission_id=permission_id)
        for permission_id in permission_ids
    )
    database.commit()
    return user, {"Authorization": f"Bearer {create_access_token(user.id, TEST_SETTINGS)}"}


def _scope(client, headers, database):
    account = client.post(
        "/api/v1/accounts", headers=headers, json={"code": "MEG", "name": "Millensys Egypt"}
    ).json()
    organization = client.post(
        "/api/v1/organizations",
        headers=headers,
        json={"account_id": account["id"], "code": "UHIA", "name": "UHIA"},
    ).json()
    status_id = database.scalar(select(ClientStatus.id))
    customer = client.post(
        "/api/v1/clients",
        headers=headers,
        json={"name": "UHIA Luxor", "status_id": status_id, "organization_id": organization["id"]},
    ).json()
    return account, organization, customer


def test_project_intake_plan_and_assignment_workflow(client, admin_headers, database):
    account, organization, customer = _scope(client, admin_headers, database)
    implementation = Department(code="IMP", name="Implementation", is_active=True)
    database.add(implementation)
    database.commit()
    database.refresh(implementation)
    manager_id = database.scalar(select(User.id).where(User.username == "admin"))
    project_response = client.post(
        "/api/v1/projects",
        headers=admin_headers,
        json={
            "project_number": "PRJ-001",
            "name": "UHIA rollout",
            "account_id": account["id"],
            "organization_id": organization["id"],
            "client_id": customer["id"],
            "owning_department_id": implementation.id,
            "project_manager_user_id": manager_id,
            "planned_start_date": "2026-11-24",
            "planned_end_date": "2027-01-31",
        },
    )
    assert project_response.status_code == 201, project_response.text
    project = project_response.json()
    assert project["status"] == "INTAKE"
    phase = client.post(
        f"/api/v1/projects/{project['id']}/phases",
        headers=admin_headers,
        json={"name": "Discovery", "sequence": 1},
    )
    assert phase.status_code == 201, phase.text
    milestone = client.post(
        f"/api/v1/projects/{project['id']}/milestones",
        headers=admin_headers,
        json={"name": "Scope approved", "phase_id": phase.json()["id"], "is_gate": True},
    )
    assert milestone.status_code == 201, milestone.text
    request = client.post(
        f"/api/v1/projects/{project['id']}/request-implementation",
        headers=admin_headers,
        json={
            "requested_department_id": implementation.id,
            "capability_notes": "PACS implementation",
        },
    )
    assert request.status_code == 201, request.text
    response = client.post(
        f"/api/v1/projects/assignment-requests/{request.json()['id']}/respond",
        headers=admin_headers,
        json={
            "decision": "ACCEPTED",
            "expected_version": request.json()["row_version"],
            "response_notes": "Capacity confirmed",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ACCEPTED"
    history = client.get(
        f"/api/v1/projects/{project['id']}/transitions", headers=admin_headers
    )
    assert history.status_code == 200
    assert history.json()[-1]["to_status"] == "READY_FOR_EXECUTION"
    assert history.json()[-1]["source"] == "IMPLEMENTATION_INTAKE"
    duplicate = client.post(
        f"/api/v1/projects/assignment-requests/{request.json()['id']}/respond",
        headers=admin_headers,
        json={
            "decision": "ACCEPTED",
            "expected_version": request.json()["row_version"],
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "ASSIGNMENT_VERSION_CONFLICT"
    plan = client.get(f"/api/v1/projects/{project['id']}/plan", headers=admin_headers).json()
    assert len(plan["phases"]) == len(plan["milestones"]) == len(plan["assignment_requests"]) == 1


def test_project_options_static_route_is_not_parsed_as_project_id(client, admin_headers, database):
    account, organization, customer = _scope(client, admin_headers, database)
    response = client.get("/api/v1/projects/options", headers=admin_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert {item["id"] for item in payload["accounts"]} == {account["id"]}
    assert {item["id"] for item in payload["organizations"]} == {organization["id"]}
    assert {item["id"] for item in payload["clients"]} == {customer["id"]}


def test_project_status_requires_governed_transition_and_version(
    client, admin_headers, database
):
    account, organization, customer = _scope(client, admin_headers, database)
    owner = Department(code="PMO", name="Project Management", is_active=True)
    database.add(owner)
    database.commit()
    manager_id = database.scalar(select(User.id).where(User.username == "admin"))
    created = client.post(
        "/api/v1/projects",
        headers=admin_headers,
        json={
            "project_number": "LIFE-001",
            "name": "Lifecycle contract",
            "account_id": account["id"],
            "organization_id": organization["id"],
            "client_id": customer["id"],
            "owning_department_id": owner.id,
            "project_manager_user_id": manager_id,
        },
    ).json()
    arbitrary = client.patch(
        f"/api/v1/projects/{created['id']}",
        headers=admin_headers,
        json={"status": "COMPLETED"},
    )
    assert arbitrary.status_code == 422
    transitioned = client.post(
        f"/api/v1/projects/{created['id']}/transition",
        headers=admin_headers,
        json={
            "target_status": "READY_FOR_EXECUTION",
            "expected_version": created["row_version"],
        },
    )
    assert transitioned.status_code == 200, transitioned.text
    assert transitioned.json()["status"] == "READY_FOR_EXECUTION"
    stale = client.post(
        f"/api/v1/projects/{created['id']}/transition",
        headers=admin_headers,
        json={
            "target_status": "CANCELLED",
            "expected_version": created["row_version"],
            "reason": "No longer required",
        },
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "PROJECT_VERSION_CONFLICT"
    recipient, _ = _scoped_user_headers(database, owner, "project.portfolio.view")
    row = database.get(CompanyProject, created["id"])
    row.project_manager_user_id = recipient.id
    database.commit()
    held = client.post(
        f"/api/v1/projects/{created['id']}/hold",
        headers=admin_headers,
        json={
            "expected_version": transitioned.json()["row_version"],
            "reason": "Waiting for approved client access",
        },
    )
    assert held.status_code == 200, held.text
    assert held.json()["status"] == "ON_HOLD"
    notification = database.scalar(
        select(Notification).where(
            Notification.recipient_user_id == recipient.id,
            Notification.notification_type == "PROJECT_LIFECYCLE",
        )
    )
    assert notification and notification.severity == "WARNING"
    resumed = client.post(
        f"/api/v1/projects/{created['id']}/resume",
        headers=admin_headers,
        json={"expected_version": held.json()["row_version"]},
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["status"] == "READY_FOR_EXECUTION"


def test_project_wizard_saves_draft_and_publishes_governed_plan(client, admin_headers, database):
    account, organization, customer = _scope(client, admin_headers, database)
    implementation = Department(code="IMP", name="Implementation", is_active=True)
    product = Product(code="PACS", name="PACS", is_active=True)
    database.add_all([implementation, product])
    database.flush()
    module = ProductModule(product_id=product.id, code="RIS", name="RIS", is_active=True)
    manager = database.scalar(select(User).where(User.username == "admin"))
    team = SupportTeam(
        code="IMP-TEAM",
        name="Implementation Team",
        department_id=implementation.id,
        leader_user_id=manager.id,
        is_active=True,
    )
    database.add_all([module, team])
    database.flush()
    database.add(SupportTeamMember(team_id=team.id, user_id=manager.id))
    database.commit()

    payload = {
        "project_number": "WIZ-001",
        "name": "Wizard rollout",
        "account_id": account["id"],
        "organization_id": organization["id"],
        "client_id": customer["id"],
        "branch_ids": [],
        "product_ids": [product.id],
        "module_ids": [module.id],
        "owning_department_id": implementation.id,
        "requested_department_id": implementation.id,
        "requested_team_id": team.id,
        "project_manager_user_id": manager.id,
        "intake_owner_user_id": manager.id,
        "planned_start_date": "2026-12-01",
        "planned_end_date": "2026-12-31",
        "capability_notes": "PACS delivery capacity is required.",
        "phases": [
            {
                "name": "Installation",
                "planned_start_at": "2026-12-01T09:00:00+02:00",
                "planned_end_at": "2026-12-05T17:00:00+02:00",
                "product_ids": [product.id],
                "module_ids": [module.id],
                "tasks": [
                    {
                        "task_number": "WIZ-T1",
                        "title": "Configure RIS",
                        "product_id": product.id,
                        "product_module_id": module.id,
                        "owner_user_id": manager.id,
                        "assignee_user_ids": [manager.id],
                        "planned_start_at": "2026-12-01T09:00:00+02:00",
                        "planned_end_at": "2026-12-01T13:00:00+02:00",
                        "estimate_minutes": 240,
                    }
                ],
            }
        ],
        "documents": [
            {
                "title": "Approved scope",
                "document_type": "SCOPE",
                "reference_url": "https://example.test/scope/1",
            }
        ],
    }
    draft = client.post("/api/v1/projects/wizard", headers=admin_headers, json=payload)
    assert draft.status_code == 201, draft.text
    assert draft.json()["status"] == "DRAFT"
    assert draft.json()["assignment_request_id"] is None

    published_payload = {**payload, "project_number": "WIZ-002", "publish": True}
    published = client.post(
        "/api/v1/projects/wizard", headers=admin_headers, json=published_payload
    )
    assert published.status_code == 201, published.text
    result = published.json()
    assert result["status"] == "AWAITING_IMPLEMENTATION_ACCEPTANCE"
    assert result["phase_count"] == result["task_count"] == 1
    assert result["assignment_request_id"] is not None
    project = database.get(CompanyProject, result["project_id"])
    assert project.published_at is not None
    assert database.scalar(
        select(ProjectAssignmentRequest).where(ProjectAssignmentRequest.project_id == project.id)
    )
    assert database.scalar(
        select(ProjectProductScope).where(ProjectProductScope.project_id == project.id)
    )
    assert database.scalar(
        select(ProjectModuleScope).where(ProjectModuleScope.project_id == project.id)
    )
    phase = database.scalar(select(ProjectPhase).where(ProjectPhase.project_id == project.id))
    assert database.scalar(
        select(ProjectPhaseModuleScope).where(ProjectPhaseModuleScope.phase_id == phase.id)
    )
    task = database.scalar(select(ProjectTask).where(ProjectTask.project_id == project.id))
    assert task.product_id == product.id and task.product_module_id == module.id
    assert database.scalar(select(ProjectEvidence).where(ProjectEvidence.project_id == project.id))


def test_project_rejects_mixed_customer_hierarchy(client, admin_headers, database):
    first_account, first_org, _ = _scope(client, admin_headers, database)
    second_account = client.post(
        "/api/v1/accounts", headers=admin_headers, json={"code": "MKS", "name": "Millensys KSA"}
    ).json()
    second_org = client.post(
        "/api/v1/organizations",
        headers=admin_headers,
        json={"account_id": second_account["id"], "code": "KSA", "name": "KSA"},
    ).json()
    status_id = database.scalar(select(ClientStatus.id))
    other_client = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"name": "Other", "status_id": status_id, "organization_id": second_org["id"]},
    ).json()
    owner = Department(code="PMO", name="Project Management", is_active=True)
    database.add(owner)
    database.commit()
    database.refresh(owner)
    department_id = owner.id
    manager_id = database.scalar(select(User.id).where(User.username == "admin"))
    response = client.post(
        "/api/v1/projects",
        headers=admin_headers,
        json={
            "project_number": "BAD-1",
            "name": "Invalid",
            "account_id": first_account["id"],
            "organization_id": first_org["id"],
            "client_id": other_client["id"],
            "owning_department_id": department_id,
            "project_manager_user_id": manager_id,
        },
    )
    assert response.status_code == 409


def test_project_detail_and_summary_use_the_same_department_scope(
    client, admin_headers, database
):
    account, organization, customer = _scope(client, admin_headers, database)
    implementation = Department(code="IMP", name="Implementation", is_active=True)
    unrelated = Department(code="OTH", name="Other Delivery", is_active=True)
    database.add_all([implementation, unrelated])
    database.commit()
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))

    def create(number: str, department_id: int) -> dict:
        response = client.post(
            "/api/v1/projects",
            headers=admin_headers,
            json={
                "project_number": number,
                "name": number,
                "account_id": account["id"],
                "organization_id": organization["id"],
                "client_id": customer["id"],
                "owning_department_id": department_id,
                "project_manager_user_id": admin_id,
            },
        )
        assert response.status_code == 201
        return response.json()

    visible = create("SCOPE-VISIBLE", implementation.id)
    hidden = create("SCOPE-HIDDEN", unrelated.id)
    scoped_user, scoped_headers = _scoped_user_headers(
        database, implementation, "project.portfolio.view", "project.manage.assigned"
    )

    portfolio = client.get("/api/v1/projects", headers=scoped_headers)
    assert [item["id"] for item in portfolio.json()] == [visible["id"]]
    summary = client.get("/api/v1/projects/portfolio-summary", headers=scoped_headers)
    assert summary.status_code == 200
    assert summary.json()["total"] == 1
    assert client.get(
        f"/api/v1/projects/{visible['id']}", headers=scoped_headers
    ).status_code == 200
    assert client.get(
        f"/api/v1/projects/{hidden['id']}", headers=scoped_headers
    ).status_code == 404
    assert client.get(
        f"/api/v1/projects/{hidden['id']}/plan", headers=scoped_headers
    ).status_code == 404
    visible_url = f"/api/v1/projects/{visible['id']}"
    assert client.patch(
        visible_url, headers=scoped_headers, json={"name": "Unauthorized edit"}
    ).status_code == 404
    managed_project = database.get(CompanyProject, visible["id"])
    managed_project.project_manager_user_id = scoped_user.id
    database.commit()
    edited = client.patch(visible_url, headers=scoped_headers, json={"name": "Managed Project"})
    assert edited.status_code == 200, edited.text
    assert edited.json()["name"] == "Managed Project"

    managed_project.status = "DRAFT"
    database.commit()
    milestone = client.post(
        f"{visible_url}/milestones", headers=scoped_headers, json={"name": "Delivery gate"}
    )
    assert milestone.status_code == 201, milestone.text
    schedule_url = f"{visible_url}/milestones/{milestone.json()['id']}/schedule"
    version = client.get(visible_url, headers=scoped_headers).json()["row_version"]
    saved = client.patch(
        schedule_url, headers=scoped_headers,
        json={"expected_version": version, "due_date": "2026-12-01"},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["due_date"] == "2026-12-01"
    stale = client.patch(
        schedule_url, headers=scoped_headers,
        json={"expected_version": version, "due_date": None},
    )
    assert stale.status_code == 409


def test_assignment_response_is_hidden_from_other_departments(
    client, admin_headers, database
):
    account, organization, customer = _scope(client, admin_headers, database)
    implementation = Department(code="IMP", name="Implementation", is_active=True)
    unrelated = Department(code="OTH", name="Other Delivery", is_active=True)
    database.add_all([implementation, unrelated])
    database.commit()
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    project = client.post(
        "/api/v1/projects",
        headers=admin_headers,
        json={
            "project_number": "RESP-SCOPE",
            "name": "Response scope",
            "account_id": account["id"],
            "organization_id": organization["id"],
            "client_id": customer["id"],
            "owning_department_id": unrelated.id,
            "project_manager_user_id": admin_id,
        },
    ).json()
    request = client.post(
        f"/api/v1/projects/{project['id']}/request-implementation",
        headers=admin_headers,
        json={"requested_department_id": implementation.id},
    ).json()
    _, unrelated_headers = _scoped_user_headers(
        database,
        unrelated,
        "project.portfolio.view",
        "project.assignment.respond",
    )
    _, implementation_headers = _scoped_user_headers(
        database,
        implementation,
        "project.portfolio.view",
        "project.assignment.respond",
    )
    implementation_inbox = client.get(
        "/api/v1/projects/assignment-requests/inbox", headers=implementation_headers
    )
    assert implementation_inbox.status_code == 200
    assert [item["id"] for item in implementation_inbox.json()] == [request["id"]]
    unrelated_inbox = client.get(
        "/api/v1/projects/assignment-requests/inbox", headers=unrelated_headers
    )
    assert unrelated_inbox.status_code == 200
    assert unrelated_inbox.json() == []
    denied = client.post(
        f"/api/v1/projects/assignment-requests/{request['id']}/respond",
        headers=unrelated_headers,
        json={"decision": "ACCEPTED", "expected_version": request["row_version"]},
    )
    assert denied.status_code == 404
    database.refresh(database.get(ProjectAssignmentRequest, request["id"]))
    assert database.get(ProjectAssignmentRequest, request["id"]).status == "PENDING"
