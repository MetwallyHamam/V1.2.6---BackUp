from datetime import date
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Client, ClientStatus
from app.modules.iam.models import User
from app.modules.notifications.models import Notification
from app.modules.uat.models import UatChecklistVersion, UatChecklistVersionItem, UatCycle
from app.modules.uat.service import queue_due_reminders


def test_template_can_be_assigned_to_multiple_clients(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status = database.scalar(select(ClientStatus).where(ClientStatus.code == "ACTIVE"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert status and admin
    allowed = Client(code="UAT-ALLOWED", name="Allowed", status_id=status.id)
    other = Client(code="UAT-OTHER", name="Other", status_id=status.id)
    database.add_all([allowed, other])
    database.commit()
    case = client.post(
        "/api/v1/uat/test-cases",
        headers=admin_headers,
        json={
            "code": "ASSIGNED-CASE",
            "title": "Assigned case",
            "expected_result": "Done",
            "steps": [{"action": "Run", "expected_result": "Done"}],
        },
    ).json()
    template = client.post(
        "/api/v1/uat/templates",
        headers=admin_headers,
        json={
            "code": "ASSIGNED-TEMPLATE",
            "name": "Assigned template",
            "client_ids": [allowed.id],
            "test_case_ids": [case["id"]],
        },
    )
    assert template.status_code == 201, template.text
    assert template.json()["client_ids"] == [allowed.id]
    allowed_cycle = client.post(
        "/api/v1/uat/cycles",
        headers=admin_headers,
        json={
            "code": "ALLOWED-CYCLE",
            "title": "Allowed",
            "client_id": allowed.id,
            "release_version": "1",
            "coordinator_user_id": admin.id,
            "template_ids": [template.json()["id"]],
        },
    )
    assert allowed_cycle.status_code == 201, allowed_cycle.text
    denied_cycle = client.post(
        "/api/v1/uat/cycles",
        headers=admin_headers,
        json={
            "code": "OTHER-CYCLE",
            "title": "Other",
            "client_id": other.id,
            "release_version": "1",
            "coordinator_user_id": admin.id,
            "template_ids": [template.json()["id"]],
        },
    )
    assert denied_cycle.status_code == 403


def test_uat_library_duplicate_and_archive_keep_versions(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    case = client.post(
        "/api/v1/uat/test-cases",
        headers=admin_headers,
        json={
            "code": "LIBRARY-SOURCE",
            "title": "Source test",
            "expected_result": "Done",
            "steps": [{"action": "Step one", "expected_result": "Done"}],
        },
    )
    assert case.status_code == 201, case.text
    copy = client.post(
        f"/api/v1/uat/test-cases/{case.json()['id']}/duplicate",
        headers=admin_headers,
        json={"code": "LIBRARY-COPY", "name": "Copied test"},
    )
    assert copy.status_code == 201, copy.text
    assert copy.json()["steps"][0]["action"] == "Step one"
    category = client.post(
        "/api/v1/uat/checklist-categories",
        headers=admin_headers,
        json={"code": "CUSTOM_REGRESSION", "name": "Custom Regression"},
    )
    assert category.status_code == 201, category.text
    template = client.post(
        "/api/v1/uat/templates",
        headers=admin_headers,
        json={
            "code": "LIBRARY-CHECKLIST",
            "name": "Source checklist",
            "category_id": category.json()["id"],
            "test_case_ids": [case.json()["id"], copy.json()["id"]],
            "section_names": {
                str(case.json()["id"]): "Reception",
                str(copy.json()["id"]): "Nursing",
            },
        },
    )
    assert template.status_code == 201, template.text
    assert template.json()["section_names"][str(case.json()["id"])] == "Reception"
    assert template.json()["category_id"] == category.json()["id"]
    duplicated = client.post(
        f"/api/v1/uat/templates/{template.json()['id']}/duplicate",
        headers=admin_headers,
        json={"code": "LIBRARY-CHECKLIST-COPY", "name": "Copied checklist"},
    )
    assert duplicated.status_code == 201, duplicated.text
    assert duplicated.json()["test_case_ids"] == [case.json()["id"], copy.json()["id"]]
    assert duplicated.json()["section_names"] == template.json()["section_names"]
    edited = client.put(
        f"/api/v1/uat/templates/{template.json()['id']}",
        headers=admin_headers,
        json={
            "code": "LIBRARY-CHECKLIST",
            "name": "Source checklist",
            "category_id": category.json()["id"],
            "test_case_ids": [copy.json()["id"], case.json()["id"]],
            "section_names": {
                str(copy.json()["id"]): "Reception",
                str(case.json()["id"]): "Reception",
            },
        },
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["current_version"] == 1
    assert edited.json()["test_case_ids"] == [copy.json()["id"], case.json()["id"]]
    revised = client.post(
        f"/api/v1/uat/templates/{template.json()['id']}/versions",
        headers=admin_headers,
        json={
            "code": "LIBRARY-CHECKLIST",
            "name": "Source checklist",
            "category_id": category.json()["id"],
            "test_case_ids": [case.json()["id"], copy.json()["id"]],
            "section_names": {
                str(case.json()["id"]): "Reception",
                str(copy.json()["id"]): "Nursing",
            },
        },
    )
    assert revised.status_code == 201, revised.text
    assert revised.json()["current_version"] == 2
    versions = list(
        database.scalars(
            select(UatChecklistVersion).where(
                UatChecklistVersion.template_id == template.json()["id"]
            )
        )
    )
    original = next(version for version in versions if version.version == 1)
    original_sections = list(
        database.scalars(
            select(UatChecklistVersionItem.section_name)
            .where(UatChecklistVersionItem.version_id == original.id)
            .order_by(UatChecklistVersionItem.display_order)
        )
    )
    assert original_sections == ["Reception", "Reception"]
    status = database.scalar(select(ClientStatus).where(ClientStatus.code == "ACTIVE"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert status and admin
    customer = Client(code="UAT-SECTIONS", name="Section Customer", status_id=status.id)
    database.add(customer)
    database.commit()
    cycle = client.post(
        "/api/v1/uat/cycles",
        headers=admin_headers,
        json={
            "code": "SECTIONS-CYCLE",
            "title": "Section cycle",
            "client_id": customer.id,
            "release_version": "1.0",
            "coordinator_user_id": admin.id,
            "template_ids": [duplicated.json()["id"]],
        },
    )
    assert cycle.status_code == 201, cycle.text
    assert [test["snapshot"]["checklist_section"] for test in cycle.json()["tests"]] == [
        "Reception",
        "Nursing",
    ]
    archived = client.post(
        f"/api/v1/uat/templates/{template.json()['id']}/archive", headers=admin_headers
    )
    assert archived.status_code == 200 and archived.json()["is_active"] is False
    removal = client.delete(f"/api/v1/uat/test-cases/{case.json()['id']}", headers=admin_headers)
    assert removal.status_code == 200 and removal.json()["archived"] is True
    assert any(
        row["id"] == case.json()["id"] and not row["is_active"]
        for row in client.get("/api/v1/uat/test-cases", headers=admin_headers).json()
    )
    unused = client.post(
        "/api/v1/uat/test-cases",
        headers=admin_headers,
        json={
            "code": "LIBRARY-UNUSED",
            "title": "Unused case",
            "expected_result": "Done",
            "steps": [{"action": "Run", "expected_result": "Done"}],
        },
    )
    assert unused.status_code == 201
    removed = client.delete(f"/api/v1/uat/test-cases/{unused.json()['id']}", headers=admin_headers)
    assert removed.status_code == 200 and removed.json()["deleted"] is True
    assert (
        client.delete(
            f"/api/v1/uat/test-cases/{unused.json()['id']}", headers=admin_headers
        ).status_code
        == 404
    )
    assert client.get("/api/v1/uat/templates", headers=admin_headers).status_code == 200
    saved = client.post(
        "/api/v1/uat/saved-views",
        headers=admin_headers,
        json={
            "name": "Failed tests",
            "filters": {"search": "", "status": "FAILED", "my_tests": False, "sort": "priority"},
        },
    )
    assert saved.status_code == 201, saved.text
    assert (
        client.get("/api/v1/uat/saved-views", headers=admin_headers).json()[0]["name"]
        == "Failed tests"
    )
    assert (
        client.post(
            "/api/v1/uat/saved-views",
            headers=admin_headers,
            json={
                "name": "Failed tests",
                "filters": {"status": "FAILED"},
            },
        ).status_code
        == 409
    )
    assert (
        client.delete(
            f"/api/v1/uat/saved-views/{saved.json()['id']}", headers=admin_headers
        ).status_code
        == 204
    )


def test_uat_bulk_planning_checks_cycle_membership(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status = database.scalar(select(ClientStatus).where(ClientStatus.code == "ACTIVE"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert status and admin
    customer = Client(code="UAT-BULK", name="UAT Bulk", status_id=status.id)
    database.add(customer)
    database.commit()
    case = client.post(
        "/api/v1/uat/test-cases",
        headers=admin_headers,
        json={
            "code": "BULK-CASE",
            "title": "Bulk test",
            "expected_result": "Done",
            "steps": [{"action": "Run", "expected_result": "Done"}],
        },
    )
    assert case.status_code == 201
    cycle = client.post(
        "/api/v1/uat/cycles",
        headers=admin_headers,
        json={
            "code": "BULK-CYCLE",
            "title": "Bulk cycle",
            "client_id": customer.id,
            "release_version": "1.0",
            "coordinator_user_id": admin.id,
            "test_case_ids": [case.json()["id"]],
        },
    )
    assert cycle.status_code == 201, cycle.text
    cycle_id, test_id = cycle.json()["id"], cycle.json()["tests"][0]["id"]
    invalid = client.post(
        f"/api/v1/uat/cycles/{cycle_id}/bulk-tests",
        headers=admin_headers,
        json={"test_ids": [test_id, test_id + 9999], "action": "SET_PRIORITY", "priority": "HIGH"},
    )
    assert invalid.status_code == 404
    updated = client.post(
        f"/api/v1/uat/cycles/{cycle_id}/bulk-tests",
        headers=admin_headers,
        json={"test_ids": [test_id], "action": "SET_PRIORITY", "priority": "HIGH"},
    )
    assert updated.status_code == 200, updated.text
    assert (
        client.get(f"/api/v1/uat/cycles/{cycle_id}", headers=admin_headers).json()["tests"][0][
            "priority"
        ]
        == "HIGH"
    )
    due = client.post(
        f"/api/v1/uat/cycles/{cycle_id}/bulk-tests",
        headers=admin_headers,
        json={"test_ids": [test_id], "action": "SET_DUE_DATE", "due_date": "2026-10-01"},
    )
    assert due.status_code == 200
    assert (
        client.get(f"/api/v1/uat/cycles/{cycle_id}", headers=admin_headers).json()["tests"][0][
            "due_date"
        ]
        == "2026-10-01"
    )
    report = client.get(f"/api/v1/uat/cycles/{cycle_id}/results-report", headers=admin_headers)
    assert report.status_code == 200, report.text
    assert report.json()["summary"]["total"] == 1
    assert report.json()["tests"][0]["priority"] == "HIGH"
    assert report.json()["tests"][0]["internal_result"] == "NOT_TESTED"
    exported = client.get(
        f"/api/v1/uat/cycles/{cycle_id}/results-report.xlsx", headers=admin_headers
    )
    assert exported.status_code == 200
    sheet = load_workbook(BytesIO(exported.content), read_only=True).active
    assert sheet is not None
    assert sheet["B3"].value == "BULK-CASE"
    assert (
        client.get("/api/v1/uat/cycles/999999/results-report", headers=admin_headers).status_code
        == 404
    )
    assert (
        client.post(f"/api/v1/uat/cycles/{cycle_id}/activate", headers=admin_headers).status_code
        == 200
    )
    cycle_row = database.get(UatCycle, cycle_id)
    assert cycle_row is not None
    cycle_row.due_date = date(2026, 9, 27)
    database.commit()
    assert queue_due_reminders(database, date(2026, 9, 28)) == 2
    assert queue_due_reminders(database, date(2026, 9, 28)) == 0
    assert queue_due_reminders(database, date(2026, 10, 2)) == 1
    assert (
        len(
            list(
                database.scalars(
                    select(Notification).where(
                        Notification.notification_type.in_(["UAT_DUE_SOON", "UAT_OVERDUE"])
                    )
                )
            )
        )
        == 3
    )
