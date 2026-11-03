from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.iam.models import User


def test_onboarding_admin_creates_material_template_and_snapshot_assignment(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    category = client.post(
        "/api/v1/onboarding/material-categories",
        headers=admin_headers,
        json={"name": "Release Training", "display_order": 20, "is_active": True},
    )
    assert category.status_code == 201, category.text
    material = client.post(
        "/api/v1/onboarding/materials",
        headers=admin_headers,
        json={
            "category_id": category.json()["id"],
            "title": "SupportHub Basics",
            "description": "Introduction",
            "is_required": True,
            "display_order": 1,
            "is_active": True,
        },
    )
    assert material.status_code == 201, material.text
    resource = client.post(
        f"/api/v1/onboarding/materials/{material.json()['id']}/resources",
        headers=admin_headers,
        json={
            "name": "Training portal",
            "resource_type": "WEBSITE",
            "url": "https://example.com/training",
            "display_order": 1,
            "is_active": True,
        },
    )
    assert resource.status_code == 201, resource.text
    edited_resource = client.patch(
        f"/api/v1/onboarding/material-resources/{resource.json()['id']}",
        headers=admin_headers,
        json={"name": "Updated training portal", "resource_type": "WEBSITE", "url": "https://example.com/training-updated", "display_order": 2, "is_active": True},
    )
    assert edited_resource.status_code == 200, edited_resource.text
    template = client.post(
        "/api/v1/onboarding/templates",
        headers=admin_headers,
        json={
            "name": "New Support Engineer",
            "description": "Standard checklist",
            "items": [
                {
                    "title": "Read SupportHub Basics",
                    "description": "Review the linked topic",
                    "required": True,
                    "material_id": material.json()["id"],
                    "due_after_days": 2,
                }
            ],
        },
    )
    assert template.status_code == 201, template.text
    edited_template = client.patch(
        f"/api/v1/onboarding/templates/{template.json()['id']}",
        headers=admin_headers,
        json={"name": "New Support Engineer Updated", "description": "Updated checklist", "items": template.json()["items"]},
    )
    assert edited_template.status_code == 200, edited_template.text
    admin = database.scalar(select(User).where(User.username == "admin"))
    assigned = client.post(
        "/api/v1/onboarding/assign",
        headers=admin_headers,
        json={
            "user_id": admin.id,
            "template_id": template.json()["id"],
            "start_date": str(date.today()),
        },
    )
    assert assigned.status_code == 201, assigned.text
    assert assigned.json()["total"] == 1
    assert assigned.json()["items"][0]["material_id"] == material.json()["id"]
    item = assigned.json()["items"][0]
    completed = client.patch(
        f"/api/v1/onboarding/{assigned.json()['id']}/items/{item['id']}",
        headers=admin_headers,
        json={"status": "COMPLETED", "version": item["version"]},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["completed"] == 1
    assert client.delete(f"/api/v1/onboarding/templates/{template.json()['id']}", headers=admin_headers).status_code == 204
    assert client.delete(f"/api/v1/onboarding/materials/{material.json()['id']}", headers=admin_headers).status_code == 204
    assert client.delete(f"/api/v1/onboarding/material-categories/{category.json()['id']}", headers=admin_headers).status_code == 204


def test_onboarding_admin_can_unassign_an_active_plan_without_deleting_history(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    template = client.post(
        "/api/v1/onboarding/templates",
        headers=admin_headers,
        json={"name": "Temporary onboarding", "items": [{"title": "Pending task", "required": True}]},
    )
    assert template.status_code == 201, template.text
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    assigned = client.post(
        "/api/v1/onboarding/assign",
        headers=admin_headers,
        json={"user_id": admin.id, "template_id": template.json()["id"], "start_date": str(date.today())},
    )
    assert assigned.status_code == 201, assigned.text
    unassigned = client.post(
        f"/api/v1/onboarding/{assigned.json()['id']}/unassign",
        headers=admin_headers,
        json={"version": assigned.json()["version"], "reason": "Assigned to the wrong onboarding program."},
    )
    assert unassigned.status_code == 200, unassigned.text
    assert unassigned.json()["status"] == "UNASSIGNED"
    assert unassigned.json()["items"][0]["title"] == "Pending task"
    employees = client.get("/api/v1/onboarding/employees", headers=admin_headers)
    assert employees.status_code == 200
    employee = next(row for row in employees.json() if row["id"] == admin.id)
    assert employee["has_active_plan"] is False


def test_onboarding_admin_can_replace_an_active_assignment_and_preserve_history(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    first = client.post(
        "/api/v1/onboarding/templates",
        headers=admin_headers,
        json={"name": "First assigned program", "items": [{"title": "Old task", "required": True}]},
    )
    replacement = client.post(
        "/api/v1/onboarding/templates",
        headers=admin_headers,
        json={"name": "Replacement program", "items": [{"title": "New task", "required": True}]},
    )
    assert first.status_code == 201 and replacement.status_code == 201
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    assigned = client.post(
        "/api/v1/onboarding/assign",
        headers=admin_headers,
        json={"user_id": admin.id, "template_id": first.json()["id"], "start_date": str(date.today())},
    )
    assert assigned.status_code == 201, assigned.text
    changed = client.post(
        f"/api/v1/onboarding/{assigned.json()['id']}/replace",
        headers=admin_headers,
        json={
            "user_id": admin.id,
            "template_id": replacement.json()["id"],
            "start_date": str(date.today()),
            "version": assigned.json()["version"],
            "reason": "Engineer moved to the replacement onboarding program.",
        },
    )
    assert changed.status_code == 201, changed.text
    assert changed.json()["template_name"] == "Replacement program"
    assert changed.json()["items"][0]["title"] == "New task"
    history = client.get("/api/v1/onboarding/progress", headers=admin_headers)
    assert history.status_code == 200, history.text
    old = next(row for row in history.json() if row["id"] == assigned.json()["id"])
    assert old["status"] == "REPLACED"
    assert old["items"][0]["title"] == "Old task"


def test_role_program_assignment_and_manager_approval(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    template = client.post(
        "/api/v1/onboarding/templates",
        headers=admin_headers,
        json={
            "code": "TEST-EVALUATION",
            "name": "Approval evaluation",
            "default_duration_days": 5,
            "items": [{
                "title": "Final readiness review",
                "required": True,
                "start_after_days": 0,
                "due_after_days": 5,
                "task_type_code": "EVALUATION",
                "completion_type_code": "MANAGER_APPROVAL",
                "requires_approval": True,
            }],
        },
    )
    assert template.status_code == 201, template.text
    bundle = client.post(
        "/api/v1/onboarding/bundles",
        headers=admin_headers,
        json={
            "code": "TEST-BUNDLE",
            "name": "Test engineer program",
            "default_duration_days": 10,
            "items": [{"template_id": template.json()["id"], "sequence_no": 10, "start_after_days": 0, "required": True}],
        },
    )
    assert bundle.status_code == 201, bundle.text
    admin = database.scalar(select(User).where(User.username == "admin"))
    assigned = client.post(
        "/api/v1/onboarding/assign",
        headers=admin_headers,
        json={"user_id": admin.id, "bundle_id": bundle.json()["id"], "start_date": str(date.today())},
    )
    assert assigned.status_code == 201, assigned.text
    item = assigned.json()["items"][0]
    submitted = client.patch(
        f"/api/v1/onboarding/{assigned.json()['id']}/items/{item['id']}",
        headers=admin_headers,
        json={"status": "COMPLETED", "version": item["version"]},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["items"][0]["approval_status"] == "PENDING"
    pending = client.get("/api/v1/onboarding/approvals", headers=admin_headers)
    assert pending.status_code == 200
    assert len(pending.json()) == 1
    reviewed = client.post(
        f"/api/v1/onboarding/{assigned.json()['id']}/items/{item['id']}/review",
        headers=admin_headers,
        json={"decision": "APPROVED", "comment": "Ready"},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "COMPLETED"


def test_assignment_can_schedule_each_task_from_its_available_date(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    template = client.post(
        "/api/v1/onboarding/templates",
        headers=admin_headers,
        json={
            "name": "Scheduled onboarding tasks",
            "items": [
                {"title": "One-day task", "required": True, "start_after_days": 0},
                {"title": "One-week task", "required": True, "start_after_days": 2},
            ],
        },
    )
    assert template.status_code == 201, template.text
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    start = date(2026, 8, 26)
    assigned = client.post(
        "/api/v1/onboarding/assign",
        headers=admin_headers,
        json={
            "user_id": admin.id,
            "template_id": template.json()["id"],
            "start_date": str(start),
            "task_durations": [
                {"template_item_id": template.json()["items"][0]["id"], "duration_days": 1},
                {"template_item_id": template.json()["items"][1]["id"], "duration_days": 7},
            ],
        },
    )
    assert assigned.status_code == 201, assigned.text
    first, second = assigned.json()["items"]
    assert first["available_date"] == "2026-08-26"
    assert first["due_date"] == "2026-08-27"
    assert second["available_date"] == "2026-08-28"
    assert second["due_date"] == "2026-09-04"
