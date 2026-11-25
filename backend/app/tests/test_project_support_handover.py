from datetime import date

from sqlalchemy import select

from app.modules.clients.models import Client, ClientStatus
from app.modules.iam.models import Department, User
from app.modules.projects.models import (
    CompanyProject,
    ProjectDepartment,
    ProjectEvidence,
    ProjectStabilizationPlan,
    ProjectStatusTransition,
)
from app.tests.test_project_portfolio import _scoped_user_headers


def _project(client, headers, database):
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
    department = Department(code="IMP", name="Implementation", is_active=True)
    database.add(department)
    database.commit()
    manager_id = database.scalar(select(User.id).where(User.username == "admin"))
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "project_number": "PRJ-HO",
            "name": "Handover pilot",
            "account_id": account["id"],
            "organization_id": organization["id"],
            "client_id": customer["id"],
            "owning_department_id": department.id,
            "project_manager_user_id": manager_id,
        },
    ).json()
    row = database.get(CompanyProject, project["id"])
    row.status = "DELIVERY_REVIEW"
    database.commit()
    project["status"] = row.status
    return project, customer, department, manager_id


def _ready_all(client, headers, database, project_id, manager_id):
    payload = client.get(f"/api/v1/projects/{project_id}/handover", headers=headers).json()
    evidence = ProjectEvidence(
        project_id=project_id,
        evidence_type="DOCUMENT",
        title="Readiness evidence",
        reference_url="https://example.invalid/readiness",
        visibility="DEPARTMENT_SHARED",
        created_by_user_id=manager_id,
    )
    database.add(evidence)
    database.commit()
    database.refresh(evidence)
    for section in payload["sections"]:
        for item in section["items"]:
            response = client.patch(
                f"/api/v1/handover-items/{item['id']}",
                headers=headers,
                json={
                    "status": "READY",
                    "evidence_id": evidence.id if item["requires_evidence"] else None,
                    "owner_user_id": manager_id,
                    "notes": "Verified",
                },
            )
            assert response.status_code == 200, response.text


def test_handover_requires_readiness_acceptance_and_stabilization(client, admin_headers, database):
    project, customer, _, manager_id = _project(client, admin_headers, database)
    initialized = client.post(
        f"/api/v1/projects/{project['id']}/handover/initialize", headers=admin_headers
    )
    assert initialized.status_code == 201
    early = client.post(f"/api/v1/projects/{project['id']}/handover/submit", headers=admin_headers)
    assert early.status_code == 409
    _ready_all(client, admin_headers, database, project["id"], manager_id)
    submitted = client.post(
        f"/api/v1/projects/{project['id']}/handover/submit", headers=admin_headers
    )
    assert submitted.status_code == 200 and submitted.json()["readiness_percent"] == 100
    observers = Department(code="REVIEW_ONLY", name="Review only", is_active=True)
    database.add(observers)
    database.flush()
    database.add(ProjectDepartment(project_id=project["id"], department_id=observers.id, role="SUPPORT"))
    _, observer_headers = _scoped_user_headers(database, observers, "handover.view", "handover.review")
    for outcome in ("ACCEPT", "CONDITIONAL_ACCEPT"):
        denied_acceptance = client.post(
            f"/api/v1/projects/{project['id']}/handover/support-decision",
            headers=observer_headers,
            json={"decision": outcome, "notes": "Reviewed"},
        )
        assert denied_acceptance.status_code == 403, denied_acceptance.text
    support = Department(code="REVIEW", name="Receiving Support", is_active=True)
    database.add(support)
    database.flush()
    database.add(ProjectDepartment(project_id=project["id"], department_id=support.id, role="SUPPORT"))
    _, reviewer_headers = _scoped_user_headers(database, support, "handover.view", "handover.review", "handover.accept")
    denied = client.post(
        f"/api/v1/projects/{project['id']}/handover/activate-support", headers=reviewer_headers
    )
    assert denied.status_code == 403
    decision = client.post(
        f"/api/v1/projects/{project['id']}/handover/support-decision",
        headers=reviewer_headers,
        json={"decision": "ACCEPT", "notes": "Support readiness verified"},
    )
    assert decision.status_code == 200
    no_plan = client.post(
        f"/api/v1/projects/{project['id']}/handover/activate-support", headers=admin_headers
    )
    assert no_plan.status_code == 409
    plan = client.put(
        f"/api/v1/projects/{project['id']}/handover/stabilization",
        headers=admin_headers,
        json={
            "start_date": "2026-11-24",
            "end_date": "2026-12-08",
            "review_frequency": "DAILY",
            "implementation_owner_user_id": manager_id,
            "support_owner_user_id": manager_id,
            "exit_criteria": "No critical defects for five business days",
        },
    )
    assert plan.status_code == 200
    active = client.post(
        f"/api/v1/projects/{project['id']}/handover/activate-support", headers=admin_headers
    )
    assert active.status_code == 200 and active.json()["status"] == "ACTIVE"
    stabilization = database.scalar(
        select(ProjectStabilizationPlan).where(
            ProjectStabilizationPlan.handover_id == active.json()["id"]
        )
    )
    stabilization.end_date = date(2026, 11, 24)
    database.commit()
    database.expire_all()
    project_row = database.get(CompanyProject, project["id"])
    completed = client.post(
        f"/api/v1/projects/{project['id']}/handover/complete-stabilization",
        headers=admin_headers,
        json={
            "expected_project_version": project_row.row_version,
            "completion_notes": "Exit criteria verified and Support ownership is stable.",
        },
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "COMPLETED"
    database.expire_all()
    assert database.get(Client, customer["id"]).support_started_at is not None
    assert database.get(CompanyProject, project["id"]).status == "COMPLETED"
    transitions = list(
        database.scalars(
            select(ProjectStatusTransition).where(
                ProjectStatusTransition.project_id == project["id"]
            )
        )
    )
    assert [item.to_status for item in transitions] == [
        "HANDOVER_PREPARATION",
        "SUPPORT_REVIEW",
        "STABILIZATION",
        "COMPLETED",
    ]


def test_conditional_acceptance_requires_accountable_residual_work(client, admin_headers, database):
    project, _, department, manager_id = _project(client, admin_headers, database)
    client.post(f"/api/v1/projects/{project['id']}/handover/initialize", headers=admin_headers)
    _ready_all(client, admin_headers, database, project["id"], manager_id)
    client.post(f"/api/v1/projects/{project['id']}/handover/submit", headers=admin_headers)
    client.post(
        f"/api/v1/projects/{project['id']}/handover/support-decision",
        headers=admin_headers,
        json={"decision": "CONDITIONAL_ACCEPT", "notes": "One noncritical item remains"},
    )
    client.put(
        f"/api/v1/projects/{project['id']}/handover/stabilization",
        headers=admin_headers,
        json={
            "start_date": "2026-11-24",
            "end_date": "2026-12-08",
            "review_frequency": "DAILY",
            "implementation_owner_user_id": manager_id,
            "support_owner_user_id": manager_id,
            "exit_criteria": "Residual item closed",
        },
    )
    blocked = client.post(
        f"/api/v1/projects/{project['id']}/handover/activate-support", headers=admin_headers
    )
    assert blocked.status_code == 409
    residual = client.post(
        f"/api/v1/projects/{project['id']}/handover/residual-items",
        headers=admin_headers,
        json={
            "description": "Complete optional monitoring dashboard",
            "severity": "LOW",
            "owner_department_id": department.id,
            "owner_user_id": manager_id,
            "target_date": "2026-12-01",
        },
    )
    assert residual.status_code == 201
    active = client.post(
        f"/api/v1/projects/{project['id']}/handover/activate-support", headers=admin_headers
    )
    assert active.status_code == 200
    closed = client.post(
        f"/api/v1/handover/residual-items/{residual.json()['id']}/close",
        headers=admin_headers,
        json={"notes": "Monitoring dashboard delivered and verified."},
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "CLOSED"
