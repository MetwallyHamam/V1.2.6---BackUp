from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.modules.clients.models import Client, ClientStatus
from app.modules.iam.models import Profile, User, UserClientScope, UserProfile
from app.modules.iam.security import hash_password
from app.modules.notifications.models import Notification
from app.modules.tickets.models import Ticket
from app.modules.uat.models import UatCycle, UatCycleTest, UatDefectLink, UatTestAttempt
from app.modules.uat.service import sync_ticket_to_uat


def test_create_uat_in_one_form_generates_identity_and_assigns_multiple_templates(
    client: TestClient, admin_headers: dict[str, str], database: Session,
) -> None:
    status = database.scalar(select(ClientStatus).where(ClientStatus.code == "ACTIVE"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert status and admin
    admin.department = "Support"
    customer = Client(code="UAT-ONE-FORM", name="One Form Customer", status_id=status.id)
    database.add(customer)
    database.flush()
    portal_profile = database.scalar(select(Profile).where(Profile.code == "CLIENT_PORTAL"))
    assert portal_profile
    client_engineer = User(
        full_name="Client UAT Engineer", username="client-uat-engineer",
        username_normalized="client-uat-engineer", email="client-uat-engineer@example.com",
        email_normalized="client-uat-engineer@example.com", password_hash=hash_password("PortalPassword!123"),
        user_type="CLIENT_PORTAL", is_active=True, require_password_change=False,
    )
    database.add(client_engineer)
    database.flush()
    database.add_all([
        UserProfile(user_id=client_engineer.id, profile_id=portal_profile.id, is_primary=True,
                    assigned_by_user_id=admin.id, assignment_reason="UAT one-form test"),
        UserClientScope(user_id=client_engineer.id, client_id=customer.id),
    ])
    database.commit()

    template_ids: list[int] = []
    for number in (1, 2):
        case = client.post("/api/v1/uat/test-cases", headers=admin_headers, json={
            "code": f"ONE-FORM-{number}", "title": f"Scenario {number}",
            "expected_result": "Accepted",
            "steps": [{"action": "Run", "expected_result": "Accepted"}],
        })
        assert case.status_code == 201, case.text
        template = client.post("/api/v1/uat/templates", headers=admin_headers, json={
            "code": f"ONE-FORM-TEMPLATE-{number}", "name": f"Template {number}",
            "test_case_ids": [case.json()["id"]],
        })
        assert template.status_code == 201, template.text
        template_ids.append(template.json()["id"])

    created = client.post("/api/v1/uat/cycles", headers=admin_headers, json={
        "client_id": customer.id, "release_version": "2026.10", "coordinator_user_id": admin.id,
        "engineer_user_ids": [admin.id], "coordinator_user_ids": [admin.id],
        "client_tester_user_ids": [client_engineer.id],
        "portal_visible": True, "allow_client_testing": True,
        "template_ids": template_ids,
    })
    assert created.status_code == 201, created.text
    payload = created.json()
    assert payload["code"].startswith(f"UAT-{customer.id}-")
    assert payload["title"] == "One Form Customer - Template 1 + Template 2"
    assert payload["engineer_user_ids"] == [admin.id]
    assert payload["coordinator_user_ids"] == [admin.id]
    assert payload["client_tester_user_ids"] == [client_engineer.id]
    assert len(payload["tests"]) == 2
    assert {test["comment_count"] for test in payload["tests"]} == {0}
    assert {test["evidence_count"] for test in payload["tests"]} == {0}
    assert {test["owner_user_id"] for test in payload["tests"]} == {admin.id}
    assert {test["client_tester_user_id"] for test in payload["tests"]} == {client_engineer.id}
    assert [test["display_order"] for test in payload["tests"]] == [1, 2]
    updated = client.put(f"/api/v1/uat/cycles/{payload['id']}", headers=admin_headers, json={
        "release_version": "2026.10.1", "coordinator_user_id": admin.id,
        "engineer_user_ids": [admin.id], "coordinator_user_ids": [admin.id],
        "client_tester_user_ids": [client_engineer.id], "start_date": "2026-10-08",
        "due_date": "2026-10-15", "description": "Updated delivery window",
        "portal_visible": True, "allow_client_testing": True,
    })
    assert updated.status_code == 200, updated.text
    assert updated.json()["release_version"] == "2026.10.1"
    assert updated.json()["start_date"] == "2026-10-08"
    assert updated.json()["due_date"] == "2026-10-15"
    reversed_ids = [test["id"] for test in reversed(payload["tests"])]
    reordered = client.put(
        f"/api/v1/uat/cycles/{payload['id']}/test-order",
        headers=admin_headers,
        json={"test_ids": reversed_ids},
    )
    assert reordered.status_code == 200, reordered.text
    assert [test["id"] for test in reordered.json()["tests"]] == reversed_ids
    assert [test["display_order"] for test in reordered.json()["tests"]] == [1, 2]
    assert client.post(f"/api/v1/uat/cycles/{payload['id']}/activate", headers=admin_headers).status_code == 200
    portal_login = client.post("/api/v1/auth/login", json={"login": "client-uat-engineer", "password": "PortalPassword!123"})
    assert portal_login.status_code == 200, portal_login.text
    portal_headers = {"Authorization": f"Bearer {portal_login.json()['access_token']}"}
    portal_cycles = client.get("/api/v1/portal/uat/cycles", headers=portal_headers)
    assert portal_cycles.status_code == 200, portal_cycles.text
    assert [cycle["id"] for cycle in portal_cycles.json()] == [payload["id"]]
    assert [test["id"] for test in portal_cycles.json()[0]["tests"]] == reversed_ids


def test_uat_cycle_snapshots_and_attempt_history(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    status = database.scalar(select(ClientStatus))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert status and admin
    customer = Client(code="UAT-CUSTOMER", name="UAT Customer", status_id=status.id)
    database.add(customer)
    database.commit()

    case_data = {
        "code": "UAT-LOGIN", "title": "Sign in", "expected_result": "Home opens",
        "steps": [{"action": "Enter valid credentials", "expected_result": "Home opens"}],
    }
    created = client.post("/api/v1/uat/test-cases", headers=admin_headers, json=case_data)
    assert created.status_code == 201, created.text
    case_id = created.json()["id"]
    template = client.post("/api/v1/uat/templates", headers=admin_headers, json={
        "code": "UAT-SMOKE", "name": "Smoke tests", "test_case_ids": [case_id],
    })
    assert template.status_code == 201, template.text
    template_id = template.json()["id"]

    cycle = client.post("/api/v1/uat/cycles", headers=admin_headers, json={
        "code": "UAT-1", "title": "Release acceptance", "client_id": customer.id,
        "release_version": "1.0", "coordinator_user_id": admin.id, "template_ids": [template_id],
    })
    assert cycle.status_code == 201, cycle.text
    cycle_id = cycle.json()["id"]
    test_id = cycle.json()["tests"][0]["id"]
    assert cycle.json()["tests"][0]["snapshot"]["title"] == "Sign in"

    changed = client.put(f"/api/v1/uat/test-cases/{case_id}", headers=admin_headers, json={
        **case_data, "title": "Updated sign in",
    })
    assert changed.status_code == 200, changed.text
    old_snapshot = client.get(f"/api/v1/uat/cycles/{cycle_id}", headers=admin_headers)
    assert old_snapshot.json()["tests"][0]["snapshot"]["title"] == "Sign in"

    draft_result = client.post(f"/api/v1/uat/cycle-tests/{test_id}/attempts", headers=admin_headers, json={"result": "FAIL", "actual_result": "Error", "failure_reason": "Login failed", "severity": "MEDIUM"})
    assert draft_result.status_code == 409
    activated = client.post(f"/api/v1/uat/cycles/{cycle_id}/activate", headers=admin_headers)
    assert activated.status_code == 200, activated.text
    moved = client.put(f"/api/v1/uat/cycle-tests/{test_id}/workflow", headers=admin_headers,
                       json={"workflow_status": "IN_PROGRESS"})
    assert moved.status_code == 200 and moved.json()["workflow_status"] == "IN_PROGRESS"
    for result, actual in (("FAIL", "Error"), ("PASS", "Home opens")):
        payload = {"result": result, "actual_result": actual}
        if result == "FAIL":
            payload.update({"failure_reason": "Login failed", "severity": "MEDIUM"})
        response = client.post(f"/api/v1/uat/cycle-tests/{test_id}/attempts", headers=admin_headers, json=payload)
        assert response.status_code == 201, response.text
        if result == "FAIL":
            assert response.json()["workflow_status"] == "NEEDS_INVESTIGATION"
            investigated = client.put(
                f"/api/v1/uat/cycle-tests/{test_id}/workflow",
                headers=admin_headers,
                json={"workflow_status": "READY"},
            )
            assert investigated.status_code == 200, investigated.text
    attempts = client.get(f"/api/v1/uat/cycle-tests/{test_id}/attempts", headers=admin_headers)
    assert [row["result"] for row in attempts.json()] == ["FAIL", "PASS"]
    assert [row["attempt_number"] for row in attempts.json()] == [1, 2]
    assert client.post(f"/api/v1/uat/cycle-tests/{test_id}/attempts", headers=admin_headers, json={"result": "FAIL", "actual_result": "Again"}).status_code == 409


def test_uat_requires_internal_permission(client: TestClient) -> None:
    assert client.get("/api/v1/uat/test-cases").status_code == 401


def test_failed_test_links_one_ticket_and_retests_after_resolution(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    status = database.scalar(select(ClientStatus).where(ClientStatus.code == "ACTIVE"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert status and admin
    customer = Client(code="UAT-DEFECT", name="Defect Customer", status_id=status.id)
    database.add(customer)
    database.commit()
    created = client.post("/api/v1/uat/test-cases", headers=admin_headers, json={
        "code": "DEFECT-1", "title": "Search fails", "expected_result": "Results appear",
        "steps": [{"action": "Search", "expected_result": "Results appear"}],
    })
    assert created.status_code == 201, created.text
    cycle = client.post("/api/v1/uat/cycles", headers=admin_headers, json={
        "code": "DEFECT-CYCLE", "title": "Defect cycle", "client_id": customer.id,
        "release_version": "1.0", "coordinator_user_id": admin.id,
        "test_case_ids": [created.json()["id"]],
    })
    assert cycle.status_code == 201, cycle.text
    cycle_id = cycle.json()["id"]
    test_id = cycle.json()["tests"][0]["id"]
    assert client.post(f"/api/v1/uat/cycles/{cycle_id}/activate", headers=admin_headers).status_code == 200
    failed = client.post(f"/api/v1/uat/cycle-tests/{test_id}/attempts", headers=admin_headers, json={
        "result": "FAIL", "actual_result": "Empty result", "failure_reason": "Search service errors", "severity": "HIGH",
    })
    assert failed.status_code == 201, failed.text
    draft = client.get(f"/api/v1/uat/cycle-tests/{test_id}/defect-ticket-draft", headers=admin_headers)
    assert draft.status_code == 200, draft.text
    assert draft.json()["subject"] == "[UAT][Release 1.0] Search fails — DEFECT-1"
    assert "Attempt: 1" in draft.json()["description"]
    assert "Client-safe evidence: None" in draft.json()["description"]
    assert "Search service errors" in draft.json()["description"]
    linked = client.post(f"/api/v1/uat/cycle-tests/{test_id}/defect-ticket", headers=admin_headers, json=draft.json())
    assert linked.status_code == 201, linked.text
    ticket_id = linked.json()["ticket_id"]
    assert database.get(Ticket, ticket_id)
    defect_link = database.scalar(select(UatDefectLink).where(UatDefectLink.ticket_id == ticket_id))
    assert defect_link
    assert defect_link.cycle_id == cycle_id
    assert defect_link.cycle_test_id == test_id
    assert defect_link.attempt_id == failed.json()["id"]
    assert defect_link.cycle_code == "DEFECT-CYCLE"
    assert defect_link.test_code == "DEFECT-1"
    assert defect_link.release_version == "1.0"
    ticket = database.get(Ticket, ticket_id)
    assert ticket
    original_entitlement_status = ticket.entitlement_status
    ticket.entitlement_status = "PENDING_APPROVAL"
    database.commit()
    uat_open = client.get(
        "/api/v1/tickets?uat_defect_only=true&open_only=true",
        headers=admin_headers,
    )
    assert uat_open.status_code == 200, uat_open.text
    assert ticket_id in {row["id"] for row in uat_open.json()}
    normal_open = client.get("/api/v1/tickets?open_only=true", headers=admin_headers)
    assert normal_open.status_code == 200, normal_open.text
    assert ticket_id not in {row["id"] for row in normal_open.json()}
    ticket.entitlement_status = original_entitlement_status
    database.commit()
    ticket_detail = client.get(f"/api/v1/tickets/{ticket_id}", headers=admin_headers)
    assert ticket_detail.status_code == 200, ticket_detail.text
    assert ticket_detail.json()["is_uat_defect"] is True
    assert ticket_detail.json()["uat_cycle_test_id"] == test_id
    for query in (
        "uat_defect_only=true&uat_cycle_code=DEFECT-CYCLE&uat_release_version=1.0",
        "search=DEFECT-CYCLE",
        "search=DEFECT-1",
        "search=1.0",
    ):
        discovered = client.get(f"/api/v1/tickets?{query}", headers=admin_headers)
        assert discovered.status_code == 200, discovered.text
        assert ticket_id in {row["id"] for row in discovered.json()}
    assert database.scalar(select(Notification.id).where(Notification.notification_type == "UAT_TICKET_CREATED"))
    dashboard = client.get(f"/api/v1/uat/cycles/{cycle_id}/dashboard", headers=admin_headers)
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["metrics"]["failed"] == 1
    assert dashboard.json()["metrics"]["open_defects"] == 1
    assert dashboard.json()["failures_by_severity"]["HIGH"] == 1
    assert client.post(f"/api/v1/uat/cycle-tests/{test_id}/defect-ticket", headers=admin_headers, json=draft.json()).status_code == 409
    assert client.post(f"/api/v1/uat/cycle-tests/{test_id}/attempts", headers=admin_headers, json={"result": "PASS", "actual_result": "Works"}).status_code == 409
    ticket = database.get(Ticket, ticket_id)
    assert ticket
    assigned = client.post(f"/api/v1/tickets/{ticket_id}/assignment", headers=admin_headers, json={
        "assigned_user_id": admin.id, "reason": "Phase 4 UAT fix", "version": ticket.version,
    })
    assert assigned.status_code == 200, assigned.text
    database.expire_all()
    ticket = database.get(Ticket, ticket_id)
    assert ticket
    test = database.get(UatCycleTest, test_id)
    assert test and test.workflow_status == "FIX_IN_PROGRESS"
    sync_ticket_to_uat(database, ticket, admin, target_status_code="IN_PROGRESS")
    database.commit()
    assert test.workflow_status == "FIX_IN_PROGRESS"
    sync_ticket_to_uat(database, ticket, admin, target_status_code="RESOLVED")
    database.commit()
    test = database.get(UatCycleTest, test_id)
    assert test and test.workflow_status == "READY_FOR_RETEST"
    assert database.scalar(select(Notification.id).where(Notification.notification_type == "UAT_TICKET_RESOLVED"))
    resolved_notice_count = len(list(database.scalars(select(Notification.id).where(Notification.notification_type == "UAT_TICKET_RESOLVED"))))
    sync_ticket_to_uat(database, ticket, admin, target_status_code="RESOLVED")
    database.commit()
    assert len(list(database.scalars(select(Notification.id).where(Notification.notification_type == "UAT_TICKET_RESOLVED")))) == resolved_notice_count
    sync_ticket_to_uat(database, ticket, admin, target_status_code="CLOSED")
    database.commit()
    assert test.workflow_status == "READY_FOR_RETEST"
    assert database.scalar(select(Notification.id).where(Notification.notification_type == "UAT_TICKET_CLOSED_BEFORE_PASS"))
    failed_retest = client.post(f"/api/v1/uat/cycle-tests/{test_id}/attempts", headers=admin_headers, json={
        "result": "FAIL", "actual_result": "Still empty", "failure_reason": "Fix incomplete", "severity": "HIGH",
    })
    assert failed_retest.status_code == 201, failed_retest.text
    assert failed_retest.json()["workflow_status"] == "WAITING_FIX"
    assert database.scalar(select(Notification.id).where(Notification.notification_type == "UAT_RETEST_FAILED_TICKET_ACTION"))
    sync_ticket_to_uat(database, ticket, admin, target_status_code="REOPENED")
    database.commit()
    assert test.workflow_status == "FIX_IN_PROGRESS"
    sync_ticket_to_uat(database, ticket, admin, target_status_code="RESOLVED")
    database.commit()
    assert test.workflow_status == "READY_FOR_RETEST"
    passed = client.post(f"/api/v1/uat/cycle-tests/{test_id}/attempts", headers=admin_headers, json={"result": "PASS", "actual_result": "Results appear"})
    assert passed.status_code == 201, passed.text
    database.expire_all()
    test = database.get(UatCycleTest, test_id)
    assert test and test.retest_count == 2 and test.test_result == "PASS"
    assert database.scalar(select(Notification.id).where(Notification.notification_type == "UAT_RETEST_PASS"))
    assert database.scalar(select(Notification.id).where(Notification.notification_type == "UAT_TICKET_READY_FOR_CLOSURE"))
    assert len(list(database.scalars(select(UatTestAttempt).where(UatTestAttempt.cycle_test_id == test_id)))) == 3


def test_blocked_attempt_and_adding_tests_to_active_cycle(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    status = database.scalar(select(ClientStatus).where(ClientStatus.code == "ACTIVE"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert status and admin
    customer = Client(code="UAT-ADD", name="Added Tests Customer", status_id=status.id)
    database.add(customer)
    database.commit()

    def make_case(code: str) -> int:
        result = client.post("/api/v1/uat/test-cases", headers=admin_headers, json={
            "code": code, "title": code, "expected_result": "It works",
            "steps": [{"action": "Run scenario", "expected_result": "It works"}],
        })
        assert result.status_code == 201, result.text
        return result.json()["id"]

    first_id = make_case("UAT-BASE")
    extra_id = make_case("UAT-EXTRA")
    template = client.post("/api/v1/uat/templates", headers=admin_headers, json={
        "code": "UAT-EXTRA-LIST", "name": "Extra tests", "test_case_ids": [extra_id],
    })
    assert template.status_code == 201, template.text
    edited = client.put(f"/api/v1/uat/test-cases/{extra_id}", headers=admin_headers, json={
        "code": "UAT-EXTRA", "title": "Changed after checklist version", "expected_result": "It works",
        "steps": [{"action": "Run scenario", "expected_result": "It works"}],
    })
    assert edited.status_code == 200, edited.text
    cycle = client.post("/api/v1/uat/cycles", headers=admin_headers, json={
        "code": "UAT-ADD-CYCLE", "title": "Add tests", "client_id": customer.id,
        "release_version": "1.0", "coordinator_user_id": admin.id, "test_case_ids": [first_id],
    })
    assert cycle.status_code == 201, cycle.text
    cycle_id = cycle.json()["id"]
    first_test_id = cycle.json()["tests"][0]["id"]
    assert client.post(f"/api/v1/uat/cycles/{cycle_id}/activate", headers=admin_headers).status_code == 200

    missing_reason = client.post(f"/api/v1/uat/cycle-tests/{first_test_id}/attempts", headers=admin_headers, json={"result": "BLOCKED", "comment": "Waiting"})
    assert missing_reason.status_code == 409
    blocked = client.post(f"/api/v1/uat/cycle-tests/{first_test_id}/attempts", headers=admin_headers, json={"result": "BLOCKED", "blocking_reason": "Test data missing", "comment": "Waiting for sample data"})
    assert blocked.status_code == 201, blocked.text
    assert blocked.json()["workflow_status"] == "BLOCKED"
    assert client.post(f"/api/v1/uat/cycle-tests/{first_test_id}/attempts", headers=admin_headers, json={"result": "PASS", "actual_result": "Works"}).status_code == 409

    added = client.post(f"/api/v1/uat/cycles/{cycle_id}/tests", headers=admin_headers, json={
        "template_ids": [template.json()["id"]], "test_case_ids": [extra_id],
        "ad_hoc_tests": [{"title": "One-time check", "expected_result": "Visible", "steps": [{"action": "Look", "expected_result": "Visible"}]}],
    })
    assert added.status_code == 201, added.text
    assert added.json()["total_tests"] == 3
    checklist_test = next(item for item in added.json()["tests"] if item["test_case_id"] == extra_id)
    assert checklist_test["snapshot"]["title"] == "UAT-EXTRA"
    ad_hoc = next(item for item in added.json()["tests"] if item["snapshot"].get("ad_hoc"))
    assert ad_hoc["test_case_id"] is None
    assert ad_hoc["snapshot"]["title"] == "One-time check"
    assert client.post(f"/api/v1/uat/cycles/{cycle_id}/tests", headers=admin_headers, json={"test_case_ids": [extra_id]}).status_code == 409
    dashboard = client.get(f"/api/v1/uat/cycles/{cycle_id}/dashboard", headers=admin_headers)
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["metrics"]["total"] == 3
    assert dashboard.json()["metrics"]["blocked"] == 1
    assert dashboard.json()["by_status"]["BLOCKED"] == 1
    assert client.post(f"/api/v1/uat/cycle-tests/{first_test_id}/unblock", headers=admin_headers).status_code == 200
    passed = client.post(f"/api/v1/uat/cycle-tests/{first_test_id}/attempts", headers=admin_headers, json={"result": "PASS", "actual_result": "Works"})
    assert passed.status_code == 201, passed.text
    history = client.get(f"/api/v1/uat/cycle-tests/{first_test_id}/attempts", headers=admin_headers)
    assert [row["result"] for row in history.json()] == ["BLOCKED", "PASS"]
    assert history.json()[0]["blocking_reason"] == "Test data missing"
    refreshed = client.get(f"/api/v1/uat/cycles/{cycle_id}/dashboard", headers=admin_headers)
    assert refreshed.json()["metrics"]["passed"] == 1
    assert refreshed.json()["metrics"]["completion_percent"] == 33.3


def test_signoff_requires_ready_cycle_and_separate_decision_maker(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    status = database.scalar(select(ClientStatus).where(ClientStatus.code == "ACTIVE"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    profile = database.scalar(select(Profile).where(Profile.code == "TOP_MANAGEMENT"))
    assert status and admin and profile
    approver = User(
        full_name="UAT Approver", username="uat-approver", username_normalized="uat-approver",
        email="uat-approver@example.com", email_normalized="uat-approver@example.com",
        password_hash=hash_password("ApprovalPassword!123"), user_type="EMPLOYEE",
        is_active=True, require_password_change=False,
    )
    customer = Client(code="UAT-SIGNOFF", name="Sign-off Customer", status_id=status.id)
    database.add_all([approver, customer])
    database.flush()
    database.add(UserProfile(user_id=approver.id, profile_id=profile.id, is_primary=True,
                             assigned_by_user_id=admin.id, assignment_reason="UAT sign-off test"))
    database.commit()
    login = client.post("/api/v1/auth/login", json={"login": "uat-approver", "password": "ApprovalPassword!123"})
    assert login.status_code == 200, login.text
    approver_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    case = client.post("/api/v1/uat/test-cases", headers=admin_headers, json={
        "code": "UAT-SIGNOFF-CASE", "title": "Acceptance check", "expected_result": "Accepted",
        "steps": [{"action": "Check", "expected_result": "Accepted"}],
    })
    assert case.status_code == 201, case.text
    cycle = client.post("/api/v1/uat/cycles", headers=admin_headers, json={
        "code": "UAT-SIGNOFF-CYCLE", "title": "Acceptance cycle", "client_id": customer.id,
        "release_version": "1.0", "coordinator_user_id": admin.id, "test_case_ids": [case.json()["id"]],
    })
    assert cycle.status_code == 201, cycle.text
    cycle_id = cycle.json()["id"]
    test_id = cycle.json()["tests"][0]["id"]
    assert client.post(f"/api/v1/uat/cycles/{cycle_id}/activate", headers=admin_headers).status_code == 200
    cycle_row = database.get(UatCycle, cycle_id)
    assert cycle_row
    cycle_row.allow_client_testing = True
    database.commit()
    request_url = f"/api/v1/uat/cycles/{cycle_id}/signoff/request"
    not_ready = client.post(request_url, headers=admin_headers, json={})
    assert not_ready.status_code == 409
    assert not_ready.json()["error"]["details"]["checks"]
    readiness = client.get(f"/api/v1/uat/cycles/{cycle_id}/signoff", headers=admin_headers)
    assert readiness.status_code == 200, readiness.text
    assert readiness.json()["current_summary"]["ready"] is False
    assert next(
        check
        for check in readiness.json()["current_summary"]["checks"]
        if check["code"] == "MANDATORY_TESTS"
    )["test_ids"] == [test_id]
    warning_codes = {
        item["code"]
        for item in readiness.json()["current_summary"]["configuration_warnings"]
    }
    assert {"PORTAL_NOT_PUBLISHED", "NO_CLIENT_TESTER", "NO_CLIENT_RESULT_ACTION"} <= warning_codes
    cycle_row.portal_visible = True
    cycle_row.client_access_end_at = server_now() - timedelta(days=1)
    database.commit()
    expired_readiness = client.get(f"/api/v1/uat/cycles/{cycle_id}/signoff", headers=admin_headers)
    assert "PORTAL_ACCESS_EXPIRED" in {
        item["code"]
        for item in expired_readiness.json()["current_summary"]["configuration_warnings"]
    }
    cycle_row.allow_client_testing = False
    cycle_row.portal_visible = False
    cycle_row.client_access_end_at = None
    database.commit()
    assert client.post(f"/api/v1/uat/cycle-tests/{test_id}/attempts", headers=admin_headers, json={"result": "PASS", "actual_result": "Accepted"}).status_code == 201
    requested = client.post(request_url, headers=admin_headers, json={"comment": "Ready for review"})
    assert requested.status_code == 201, requested.text
    assert requested.json()["summary_snapshot"]["mandatory_incomplete"] == 0
    assert requested.json()["summary_snapshot"]["ready"] is True
    assert client.post(request_url, headers=admin_headers, json={}).status_code == 409
    assert client.post(f"/api/v1/uat/cycles/{cycle_id}/tests", headers=admin_headers, json={"test_case_ids": [case.json()["id"]]}).status_code == 409
    assert client.post(f"/api/v1/uat/cycles/{cycle_id}/signoff/approve", headers=admin_headers, json={}).status_code == 403
    reject_url = f"/api/v1/uat/cycles/{cycle_id}/signoff/reject"
    assert client.post(reject_url, headers=approver_headers, json={}).status_code == 409
    rejected = client.post(reject_url, headers=approver_headers, json={"comment": "Need customer notes"})
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "REJECTED"
    assert client.post(request_url, headers=admin_headers, json={}).status_code == 201
    approved = client.post(f"/api/v1/uat/cycles/{cycle_id}/signoff/approve", headers=approver_headers, json={"acceptance_notes": "Approved for this release"})
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"
    assert client.get(f"/api/v1/uat/cycles/{cycle_id}", headers=admin_headers).json()["status"] == "COMPLETED"
    history = client.get(f"/api/v1/uat/cycles/{cycle_id}/signoff", headers=admin_headers)
    assert history.status_code == 200, history.text
    assert [row["status"] for row in history.json()["history"]] == ["APPROVED", "REJECTED"]
