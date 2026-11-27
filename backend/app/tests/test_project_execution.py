from sqlalchemy import select

from app.modules.clients.models import ClientStatus, SupportTeam, SupportTeamMember
from app.modules.iam.models import Department, User
from app.modules.projects.models import (
    CompanyProject,
    ProjectAssignmentRequest,
    ProjectDepartment,
    ProjectStatusTransition,
    ProjectTask,
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
    database.refresh(department)
    manager_id = database.scalar(select(User.id).where(User.username == "admin"))
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "project_number": "PRJ-EX",
            "name": "Execution pilot",
            "account_id": account["id"],
            "organization_id": organization["id"],
            "client_id": customer["id"],
            "owning_department_id": department.id,
            "project_manager_user_id": manager_id,
        },
    ).json()
    row = database.get(CompanyProject, project["id"])
    row.status = "READY_FOR_EXECUTION"
    database.commit()
    project["status"] = row.status
    return project, manager_id


def test_capacity_plan_is_department_scoped_and_flags_overbooking(
    client, admin_headers, database
):
    project, _ = _project(client, admin_headers, database)
    department = database.get(Department, project["owning_department_id"])
    planner, planner_headers = _scoped_user_headers(
        database,
        department,
        "project.assignment.respond",
        "implementation.task.assign",
        "project.portfolio.view",
    )
    team = SupportTeam(
        code="IMP_ALPHA",
        department_id=department.id,
        name="Implementation Alpha",
        leader_user_id=planner.id,
        is_active=True,
    )
    database.add(team)
    database.flush()
    database.add(SupportTeamMember(team_id=team.id, user_id=planner.id))
    database.add(ProjectAssignmentRequest(
        project_id=project["id"],
        requested_department_id=department.id,
        requested_team_id=team.id,
        requested_by_user_id=planner.id,
        status="ACCEPTED",
    ))
    database.add(ProjectTask(
        project_id=project["id"],
        task_number="CAP-001",
        title="Capacity-heavy rollout",
        owner_user_id=planner.id,
        created_by_user_id=planner.id,
        estimate_minutes=2500,
    ))
    database.commit()

    response = client.get(
        "/api/v1/project-tasks/capacity-plan?weeks=2", headers=planner_headers
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert len(result["week_starts"]) == 2
    assert result["unassigned_projects"] == []
    [planned_team] = result["teams"]
    assert planned_team["team_name"] == "Implementation Alpha"
    assert planned_team["member_count"] == 1
    assert planned_team["weeks"][0]["planned_minutes"] == 2500
    assert planned_team["weeks"][0]["capacity_minutes"] == 2400
    assert planned_team["weeks"][0]["overbooked"] is True

    other_department = Department(code="CAP_OTHER", name="Other capacity", is_active=True)
    database.add(other_department)
    database.commit()
    _, outside_headers = _scoped_user_headers(
        database, other_department, "project.assignment.respond"
    )
    outside = client.get("/api/v1/project-tasks/capacity-plan", headers=outside_headers)
    assert outside.status_code == 200
    assert outside.json()["teams"] == []


def test_project_task_dependencies_preserve_predecessor_direction(client, admin_headers, database):
    project, manager_id = _project(client, admin_headers, database)
    url = f"/api/v1/projects/{project['id']}"
    predecessor = client.post(
        f"{url}/tasks", headers=admin_headers,
        json={"task_number": "T-001", "title": "Install", "owner_user_id": manager_id},
    )
    assert predecessor.status_code == 201, predecessor.text
    successor = client.post(
        f"{url}/tasks", headers=admin_headers,
        json={
            "task_number": "T-002", "title": "Verify", "owner_user_id": manager_id,
            "dependency_ids": [predecessor.json()["id"]],
        },
    )
    assert successor.status_code == 201, successor.text
    response = client.get(f"{url}/task-dependencies", headers=admin_headers)
    assert response.status_code == 200, response.text
    [relation] = response.json()
    assert relation["task_id"] == successor.json()["id"]
    assert relation["depends_on_task_id"] == predecessor.json()["id"]
    assert relation["dependency_type"] == "FINISH_TO_START"

    draft = database.get(CompanyProject, project["id"])
    draft.status = "DRAFT"
    database.commit()
    version = draft.row_version
    predecessor_schedule = f"{url}/tasks/{predecessor.json()['id']}/schedule"
    successor_schedule = f"{url}/tasks/{successor.json()['id']}/schedule"
    first_window = {
        "expected_version": version,
        "planned_start_date": "2026-12-01",
        "planned_end_date": "2026-12-03",
    }
    assert client.patch(predecessor_schedule, headers=admin_headers, json=first_window).status_code == 200
    assert client.patch(predecessor_schedule, headers=admin_headers, json=first_window).status_code == 409
    version += 1
    overlap = client.patch(
        successor_schedule, headers=admin_headers,
        json={**first_window, "expected_version": version},
    )
    assert overlap.status_code == 409
    assert overlap.json()["error"]["code"] == "INVALID_TASK_DEPENDENCY_DATES"
    scheduled = client.patch(
        successor_schedule, headers=admin_headers,
        json={"expected_version": version, "planned_start_date": "2026-12-04", "planned_end_date": "2026-12-05"},
    )
    assert scheduled.status_code == 200, scheduled.text
    assert scheduled.json()["planned_end_date"] == "2026-12-05"
    version += 1
    cycle = client.put(
        f"{url}/tasks/{predecessor.json()['id']}/dependencies",
        headers=admin_headers,
        json={"expected_version": version, "predecessor_ids": [successor.json()["id"]]},
    )
    assert cycle.status_code == 409
    edit_url = f"{url}/tasks/{successor.json()['id']}/dependencies"
    removed = client.put(
        edit_url, headers=admin_headers, json={"expected_version": version, "predecessor_ids": []}
    )
    assert removed.status_code == 200, removed.text
    assert client.get(f"{url}/task-dependencies", headers=admin_headers).json() == []
    stale = client.put(
        edit_url, headers=admin_headers,
        json={"expected_version": version, "predecessor_ids": [predecessor.json()["id"]]},
    )
    assert stale.status_code == 409
    database.expire_all()
    draft.status = "READY_FOR_EXECUTION"
    department = database.get(Department, draft.owning_department_id)
    _, reviewer = _scoped_user_headers(database, department, "project.manage", "implementation.task.view")
    version += 1
    revisions_url = f"{url}/milestone-revisions"
    task_revisions_url = f"{url}/tasks/{successor.json()['id']}/revisions"
    for field, proposed in (
        ("schedule", {"planned_start_date": "2026-12-06", "planned_end_date": "2026-12-07"}),
        ("dependencies", {"predecessor_ids": [predecessor.json()["id"]]}),
    ):
        submitted = client.post(task_revisions_url, headers=admin_headers, json={
            "reason": "Updated delivery plan", field: {"expected_version": version, **proposed},
        })
        assert submitted.status_code == 201, submitted.text
        latest = client.get(revisions_url, headers=admin_headers).json()[0]
        assert latest["proposed"] == proposed
        approved = client.post(
            f"{revisions_url}/{latest['id']}/decision", headers=reviewer,
            json={"expected_version": version, "decision": "APPROVED"},
        )
        assert approved.status_code == 200, approved.text
        version += 1
    assert client.get(f"{url}/task-dependencies", headers=admin_headers).json()[0]["depends_on_task_id"] == predecessor.json()["id"]


def test_planned_task_execution_worklog_blocker_evidence_and_review(
    client, admin_headers, database
):
    project, manager_id = _project(client, admin_headers, database)
    created = client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        headers=admin_headers,
        json={
            "task_number": "T-001",
            "title": "Install application",
            "owner_user_id": manager_id,
            "estimate_minutes": 240,
            "weight": 5,
        },
    ).json()
    assert created["classification"] == "PLANNED" and created["approval_status"] == "NOT_REQUIRED"
    ready = client.post(
        f"/api/v1/project-tasks/{created['id']}/actions/ready", headers=admin_headers, json={}
    ).json()
    assert ready["status"] == "READY"
    started = client.post(
        f"/api/v1/project-tasks/{created['id']}/actions/start",
        headers=admin_headers,
        json={"progress_percent": 20},
    ).json()
    assert started["status"] == "IN_PROGRESS"
    database.expire_all()
    assert database.get(CompanyProject, project["id"]).status == "IN_EXECUTION"
    log = client.post(
        f"/api/v1/project-tasks/{created['id']}/work-logs",
        headers=admin_headers,
        json={
            "started_at": "2026-11-23T10:00:00+02:00",
            "ended_at": "2026-11-23T11:30:00+02:00",
            "notes": "Installed services",
        },
    )
    assert log.status_code == 201 and log.json()["duration_minutes"] == 90
    blocker = client.post(
        f"/api/v1/project-tasks/{created['id']}/blockers",
        headers=admin_headers,
        json={
            "category": "CLIENT_ACCESS",
            "description": "VPN unavailable",
            "owner_user_id": manager_id,
            "impact": "Installation paused",
            "next_review_at": "2026-11-24T10:00:00+02:00",
        },
    ).json()
    resolved = client.post(
        f"/api/v1/project-task-blockers/{blocker['id']}/resolve", headers=admin_headers
    )
    assert resolved.status_code == 200
    evidence = client.post(
        f"/api/v1/project-tasks/{created['id']}/evidence",
        headers=admin_headers,
        json={
            "evidence_type": "SCREENSHOT",
            "title": "Installation verified",
            "reference_url": "https://example.invalid/evidence",
            "visibility": "DEPARTMENT_SHARED",
        },
    )
    assert evidence.status_code == 201
    client.post(
        f"/api/v1/project-tasks/{created['id']}/actions/start",
        headers=admin_headers,
        json={"progress_percent": 80},
    )
    submitted = client.post(
        f"/api/v1/project-tasks/{created['id']}/actions/submit-review",
        headers=admin_headers,
        json={"summary": "Ready for review"},
    )
    assert submitted.json()["status"] == "REVIEW"
    department = database.get(Department, project["owning_department_id"])
    database.add(ProjectDepartment(project_id=project["id"], department_id=department.id, role="PRIMARY_IMPLEMENTATION"))
    _, reviewer = _scoped_user_headers(database, department, "implementation.task.review", "project.portfolio.view")
    attention_url = "/api/v1/project-tasks/delivery-attention"
    queue = client.get(attention_url, headers=reviewer)
    assert queue.status_code == 200, queue.text
    assert [item["id"] for item in queue.json()] == [created["id"]]
    unrelated = Department(code="OTHER_REVIEW", name="Other review department", is_active=True)
    database.add(unrelated)
    database.flush()
    _, outside = _scoped_user_headers(database, unrelated, "implementation.task.review")
    assert client.get(attention_url, headers=outside).json() == []
    review = client.post(
        f"/api/v1/project-tasks/{created['id']}/reviews",
        headers=admin_headers,
        json={"decision": "APPROVED", "notes": "Verified"},
    )
    assert review.status_code == 201
    tasks = client.get(f"/api/v1/projects/{project['id']}/tasks", headers=admin_headers).json()
    assert tasks[0]["status"] == "DONE" and tasks[0]["actual_minutes"] == 90
    database.expire_all()
    assert database.get(CompanyProject, project["id"]).status == "DELIVERY_REVIEW"
    transitions = list(
        database.scalars(
            select(ProjectStatusTransition).where(
                ProjectStatusTransition.project_id == project["id"]
            )
        )
    )
    assert [item.to_status for item in transitions] == ["IN_EXECUTION", "DELIVERY_REVIEW"]
    submission = f"/api/v1/projects/{project['id']}/delivery-submission"
    readiness = client.get(f"/api/v1/projects/{project['id']}/delivery-readiness", headers=reviewer)
    assert readiness.status_code == 200, readiness.text
    assert readiness.json() == {
        "in_review": True, "has_tasks": True, "open_tasks": 0,
        "has_shared_evidence": True, "can_submit": True,
    }
    version = database.get(CompanyProject, project["id"]).row_version
    payload = {"expected_version": version, "summary": "Installation and review are complete."}
    assert client.post(submission, headers=outside, json=payload).status_code == 404
    sent = client.post(submission, headers=reviewer, json=payload)
    assert sent.status_code == 201, sent.text
    snapshot = client.get(submission, headers=admin_headers).json()
    assert snapshot["is_current"] and snapshot["task_count"] == snapshot["evidence_count"] == 1
    assert client.post(submission, headers=reviewer, json=payload).status_code == 409


def test_unplanned_work_requires_approval_and_timer_is_single_active(
    client, admin_headers, database
):
    project, manager_id = _project(client, admin_headers, database)
    planned = client.post(
        f"/api/v1/projects/{project['id']}/tasks", headers=admin_headers,
        json={"task_number": f"{project['project_number']}-001", "title": "Planned work", "owner_user_id": manager_id},
    )
    assert planned.status_code == 201, planned.text
    response = client.post(
        f"/api/v1/projects/{project['id']}/unplanned-work",
        headers=admin_headers,
        json={
            "title": "Unexpected network repair",
            "owner_user_id": manager_id,
            "estimate_minutes": 60,
            "unplanned_cause": "Legacy switch failure",
            "unplanned_source": "SITE_DISCOVERY",
            "impact_summary": "Blocks workstation rollout",
            "schedule_impact_minutes": 120,
        },
    )
    assert response.status_code == 201, response.text
    task = response.json()
    assert task["task_number"] == f"{project['project_number']}-002"
    assert task["approval_status"] == "PENDING"
    denied = client.post(
        f"/api/v1/project-tasks/{task['id']}/actions/ready", headers=admin_headers, json={}
    )
    assert denied.status_code == 409
    approved = client.post(
        f"/api/v1/project-tasks/{task['id']}/approve-unplanned",
        headers=admin_headers,
        json={"decision": "APPROVED", "notes": "Urgent dependency"},
    )
    assert approved.json()["approval_status"] == "APPROVED"
    client.post(f"/api/v1/project-tasks/{task['id']}/actions/ready", headers=admin_headers, json={})
    timer = client.post(f"/api/v1/project-tasks/{task['id']}/timer/start", headers=admin_headers)
    assert timer.status_code == 201
    database.expire_all()
    assert database.get(CompanyProject, project["id"]).status == "IN_EXECUTION"
    duplicate = client.post(
        f"/api/v1/project-tasks/{task['id']}/timer/start", headers=admin_headers
    )
    assert duplicate.status_code == 409
    stopped = client.post(
        f"/api/v1/project-tasks/{task['id']}/timer/stop",
        headers=admin_headers,
        params={"notes": "Repair completed"},
    )
    assert stopped.status_code == 200 and stopped.json()["duration_minutes"] >= 1
