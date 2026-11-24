from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.clients.models import Client, ClientStatus
from app.modules.iam.models import Profile, User, UserClientScope, UserProfile
from app.modules.iam.security import hash_password
from app.modules.notifications.models import Notification
from app.modules.tickets.models import Ticket
from app.modules.uat.models import UatCycleTest
from app.modules.uat.service import queue_due_reminders, sync_ticket_to_uat


def _portal_user(db: Session, username: str, client_id: int) -> User:
    profile = db.scalar(select(Profile).where(Profile.code == "CLIENT_PORTAL"))
    assert profile
    user = User(full_name=username, username=username, username_normalized=username,
                email=f"{username}@example.com", email_normalized=f"{username}@example.com",
                password_hash=hash_password("PortalPassword!123"), user_type="CLIENT_PORTAL")
    db.add(user)
    db.flush()
    db.add(UserProfile(user_id=user.id, profile_id=profile.id, is_primary=True,
                       assigned_by_user_id=user.id, assignment_reason="UAT portal test"))
    db.add(UserClientScope(user_id=user.id, client_id=client_id))
    db.commit()
    return user


def _headers(client: TestClient, username: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"login": username, "password": "PortalPassword!123"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_portal_uat_scope_and_separate_results(client: TestClient, admin_headers: dict[str, str], database: Session, tmp_path: Path) -> None:
    existing_settings = client.app.dependency_overrides[get_settings]()
    client.app.dependency_overrides[get_settings] = lambda: existing_settings.model_copy(update={"attachment_storage_path": str(tmp_path)})
    status = database.scalar(select(ClientStatus).where(ClientStatus.code == "ACTIVE"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert status and admin
    first = Client(code="UAT-PORTAL-A", name="Portal A", status_id=status.id)
    second = Client(code="UAT-PORTAL-B", name="Portal B", status_id=status.id)
    database.add_all([first, second])
    database.commit()
    assigned = _portal_user(database, "uatportalassigned", first.id)
    other = _portal_user(database, "uatportalother", second.id)
    assigned_headers = _headers(client, assigned.username)
    other_headers = _headers(client, other.username)
    case = client.post("/api/v1/uat/test-cases", headers=admin_headers, json={
        "code": "PORTAL-CASE", "title": "Portal acceptance", "expected_result": "Accepted",
        "steps": [{"action": "Review", "expected_result": "Accepted"}],
    })
    assert case.status_code == 201, case.text
    cycle = client.post("/api/v1/uat/cycles", headers=admin_headers, json={
        "code": "PORTAL-CYCLE", "title": "Portal cycle", "client_id": first.id,
        "release_version": "1.0", "coordinator_user_id": admin.id, "test_case_ids": [case.json()["id"]],
    })
    assert cycle.status_code == 201, cycle.text
    cycle_id = cycle.json()["id"]
    test_id = cycle.json()["tests"][0]["id"]
    assert client.get("/api/v1/portal/uat/cycles", headers=assigned_headers).json() == []
    assert client.post(f"/api/v1/uat/cycles/{cycle_id}/activate", headers=admin_headers).status_code == 200
    assert client.put(f"/api/v1/uat/cycles/{cycle_id}/portal-settings", headers=admin_headers, json={
        "portal_visible": False, "client_coordinator_user_id": assigned.id,
    }).status_code == 200
    availability = client.get("/api/v1/portal/uat/availability", headers=assigned_headers)
    assert availability.status_code == 200
    assert availability.json()["code"] == "UNPUBLISHED"
    coordinator_settings = client.put(f"/api/v1/uat/cycles/{cycle_id}/portal-settings", headers=admin_headers, json={
        "portal_visible": True, "client_coordinator_user_id": assigned.id,
    })
    assert coordinator_settings.status_code == 200, coordinator_settings.text
    coordinator_cycles = client.get("/api/v1/portal/uat/cycles", headers=assigned_headers).json()
    assert len(coordinator_cycles) == 1
    assert [row["id"] for row in coordinator_cycles[0]["tests"]] == [test_id]
    assert coordinator_cycles[0]["tests"][0]["assigned_to_me"] is False
    assigned_response = client.put(f"/api/v1/uat/cycle-tests/{test_id}/client-tester", headers=admin_headers, json={"user_id": assigned.id})
    assert assigned_response.status_code == 200, assigned_response.text
    invalid_assignment = client.put(f"/api/v1/uat/cycle-tests/{test_id}/client-tester", headers=admin_headers, json={"user_id": other.id})
    assert invalid_assignment.status_code == 409
    settings = client.put(f"/api/v1/uat/cycles/{cycle_id}/portal-settings", headers=admin_headers, json={
        "portal_visible": True, "allow_client_testing": True,
        "allow_client_pass": True, "allow_client_fail": True, "allow_client_blocked": True,
    })
    assert settings.status_code == 200, settings.text
    assert len(client.get("/api/v1/portal/uat/cycles", headers=assigned_headers).json()) == 1
    assert client.get("/api/v1/portal/uat/cycles", headers=other_headers).json() == []
    started = client.put(f"/api/v1/portal/uat/tests/{test_id}/workflow", headers=assigned_headers,
                         json={"workflow_status": "IN_PROGRESS"})
    assert started.status_code == 200, started.text
    assert started.json()["client_workflow_status"] == "IN_PROGRESS"
    reset = client.put(f"/api/v1/portal/uat/tests/{test_id}/workflow", headers=assigned_headers,
                       json={"workflow_status": "READY"})
    assert reset.status_code == 200, reset.text
    assert reset.json()["client_workflow_status"] == "READY"
    assert client.put(f"/api/v1/portal/uat/tests/{test_id}/workflow", headers=other_headers,
                      json={"workflow_status": "IN_PROGRESS"}).status_code == 404
    assert client.get(f"/api/v1/portal/uat/cycles/{cycle_id}", headers=other_headers).status_code == 404
    assert client.get(f"/api/v1/portal/uat/tests/{test_id}/attempts", headers=other_headers).status_code == 404
    failed = client.post(f"/api/v1/portal/uat/tests/{test_id}/attempts", headers=assigned_headers, json={
        "result": "FAIL", "actual_result": "Rejected", "failure_reason": "Validation failed", "severity": "HIGH",
    })
    assert failed.status_code == 201, failed.text
    internal = client.get(f"/api/v1/uat/cycles/{cycle_id}", headers=admin_headers).json()["tests"][0]
    assert internal["test_result"] == "NOT_TESTED" and internal["attempt_count"] == 0
    assert internal["client_test_result"] == "FAIL" and internal["client_attempt_count"] == 1
    passed = client.post(f"/api/v1/uat/cycle-tests/{test_id}/attempts", headers=admin_headers, json={
        "result": "PASS", "actual_result": "Accepted",
    })
    assert passed.status_code == 201, passed.text
    internal_attempts = client.get(f"/api/v1/uat/cycle-tests/{test_id}/attempts", headers=admin_headers).json()
    assert [(row["attempt_number"], row["execution_source"]) for row in internal_attempts] == [(1, "CLIENT_PORTAL"), (2, "INTERNAL")]
    portal_attempts = client.get(f"/api/v1/portal/uat/tests/{test_id}/attempts", headers=assigned_headers).json()
    assert len(portal_attempts) == 1 and portal_attempts[0]["result"] == "FAIL"
    signoff_settings = client.put(f"/api/v1/uat/cycles/{cycle_id}/portal-settings", headers=admin_headers, json={
        "portal_visible": True, "allow_client_testing": True,
        "allow_client_pass": True, "allow_client_fail": True, "allow_client_blocked": True,
        "allow_client_signoff": True, "client_approver_user_id": assigned.id,
        "allow_client_comments": True, "allow_client_attachments": True,
    })
    assert signoff_settings.status_code == 200, signoff_settings.text
    internal_only = client.post(f"/api/v1/uat/cycle-tests/{test_id}/comments", headers=admin_headers,
                                json={"body": "Internal note", "visibility": "INTERNAL_ONLY"})
    assert internal_only.status_code == 201, internal_only.text
    visible = client.post(f"/api/v1/uat/cycle-tests/{test_id}/comments", headers=admin_headers,
                          json={"body": "Client note", "visibility": "CLIENT_VISIBLE"})
    assert visible.status_code == 201, visible.text
    portal_comments = client.get(f"/api/v1/portal/uat/tests/{test_id}/comments", headers=assigned_headers)
    assert [row["body"] for row in portal_comments.json()] == ["Client note"]
    assert client.get(f"/api/v1/portal/uat/tests/{test_id}/comments", headers=other_headers).status_code == 404
    client_comment = client.post(f"/api/v1/portal/uat/tests/{test_id}/comments", headers=assigned_headers,
                                 json={"body": "Please review"})
    assert client_comment.status_code == 201, client_comment.text
    assert client_comment.json()["visibility"] == "CLIENT_VISIBLE"
    assert len(client.get(f"/api/v1/uat/cycle-tests/{test_id}/comments", headers=admin_headers).json()) == 3
    activity = client.get(f"/api/v1/uat/cycles/{cycle_id}/activity", headers=admin_headers)
    assert activity.status_code == 200, activity.text
    assert any(row["action"] == "uat.client_comment.created" for row in activity.json())
    client_attempt_id = portal_attempts[0]["id"]
    uploaded = client.post(f"/api/v1/portal/uat/tests/{test_id}/attempts/{client_attempt_id}/evidence",
                           headers=assigned_headers, files={"upload": ("proof.txt", b"proof", "text/plain")})
    assert uploaded.status_code == 201, uploaded.text
    evidence_id = uploaded.json()["id"]
    assert client.get(f"/api/v1/portal/uat/tests/{test_id}/evidence/{evidence_id}/download", headers=assigned_headers).content == b"proof"
    assert client.get(f"/api/v1/portal/uat/tests/{test_id}/evidence/{evidence_id}/download", headers=other_headers).status_code == 404
    hidden = client.post(f"/api/v1/uat/cycle-tests/{test_id}/attempts/{client_attempt_id}/evidence",
                         headers=admin_headers, data={"visibility": "INTERNAL_ONLY"},
                         files={"upload": ("internal.txt", b"private", "text/plain")})
    assert hidden.status_code == 201, hidden.text
    assert [row["id"] for row in client.get(f"/api/v1/portal/uat/tests/{test_id}/attempts/{client_attempt_id}/evidence", headers=assigned_headers).json()] == [evidence_id]
    assert client.get(f"/api/v1/portal/uat/cycles/{cycle_id}/signoff", headers=other_headers).status_code == 404
    assert client.post(f"/api/v1/portal/uat/cycles/{cycle_id}/signoff", headers=other_headers,
                       json={"decision": "APPROVED"}).status_code == 404
    assert client.post(f"/api/v1/portal/uat/cycles/{cycle_id}/signoff", headers=assigned_headers,
                       json={"decision": "APPROVED"}).status_code == 409
    assert client.post(f"/api/v1/portal/uat/cycles/{cycle_id}/signoff", headers=assigned_headers,
                       json={"decision": "REJECTED"}).status_code == 409
    rejected = client.post(f"/api/v1/portal/uat/cycles/{cycle_id}/signoff", headers=assigned_headers,
                           json={"decision": "REJECTED", "comment": "Failure needs fixing"})
    assert rejected.status_code == 201, rejected.text
    additional = client.post(f"/api/v1/portal/uat/cycles/{cycle_id}/signoff", headers=assigned_headers,
                             json={"decision": "ADDITIONAL_TESTING", "comment": "Please retest"})
    assert additional.status_code == 201, additional.text
    assert client.post(f"/api/v1/uat/cycles/{cycle_id}/signoff/request", headers=admin_headers,
                       json={"comment": "Ready"}).status_code == 409
    retest = client.post(f"/api/v1/portal/uat/tests/{test_id}/attempts", headers=assigned_headers,
                         json={"result": "PASS", "actual_result": "Accepted"})
    assert retest.status_code == 201, retest.text
    decided = client.post(f"/api/v1/portal/uat/cycles/{cycle_id}/signoff", headers=assigned_headers,
                          json={"decision": "APPROVED", "comment": "Accepted"})
    assert decided.status_code == 201, decided.text
    assert decided.json()["decision_number"] == 3
    assert decided.json()["summary_snapshot"]["passed"] == 1
    assert client.post(f"/api/v1/portal/uat/tests/{test_id}/attempts", headers=assigned_headers,
                       json={"result": "FAIL", "actual_result": "Regression", "failure_reason": "Bad", "severity": "LOW"}).status_code == 409
    added = client.post(f"/api/v1/uat/cycles/{cycle_id}/tests", headers=admin_headers, json={
        "ad_hoc_tests": [{"title": "Additional client check", "expected_result": "Accepted", "steps": [{"action": "Check", "expected_result": "Accepted"}]}],
    })
    assert added.status_code == 201, added.text
    added_test = next(row for row in added.json()["tests"] if row["id"] != test_id)
    assert client.put(f"/api/v1/uat/cycle-tests/{added_test['id']}/client-tester", headers=admin_headers,
                      json={"user_id": assigned.id}).status_code == 200
    assert client.post(f"/api/v1/uat/cycles/{cycle_id}/signoff/request", headers=admin_headers,
                       json={"comment": "Ready"}).status_code == 409
    assert client.post(f"/api/v1/portal/uat/tests/{added_test['id']}/attempts", headers=assigned_headers,
                       json={"result": "PASS", "actual_result": "Accepted"}).status_code == 201
    assert client.post(f"/api/v1/uat/cycle-tests/{added_test['id']}/attempts", headers=admin_headers,
                       json={"result": "PASS", "actual_result": "Accepted"}).status_code == 201
    renewed = client.post(f"/api/v1/portal/uat/cycles/{cycle_id}/signoff", headers=assigned_headers,
                          json={"decision": "APPROVED", "comment": "Additional check accepted"})
    assert renewed.status_code == 201, renewed.text
    assert renewed.json()["decision_number"] == 4
    assert client.post(f"/api/v1/uat/cycles/{cycle_id}/signoff/request", headers=admin_headers,
                       json={"comment": "Ready"}).status_code == 201
    portfolio = client.get("/api/v1/uat/portfolio", headers=admin_headers)
    assert portfolio.status_code == 200, portfolio.text
    assert portfolio.json()[0]["code"] == "PORTAL-CYCLE"
    assert portfolio.json()[0]["client_signoff"] == "APPROVED"
    assert client.get("/api/v1/uat/portfolio", headers=assigned_headers).status_code == 403
    exported = client.get("/api/v1/uat/portfolio.csv", headers=admin_headers)
    assert exported.status_code == 200 and "PORTAL-CYCLE" in exported.text
    share = client.post(f"/api/v1/uat/cycles/{cycle_id}/share-links", headers=admin_headers,
                        json={"expires_in_hours": 2})
    assert share.status_code == 201, share.text
    token = share.json()["token"]
    public = client.get(f"/api/v1/public/uat-shares/{token}")
    assert public.status_code == 200, public.text
    assert public.json()["passed"] == 2
    assert "tests" not in public.json() and "comments" not in public.json()
    assert client.post(f"/api/v1/uat/cycles/{cycle_id}/share-links/{share.json()['id']}/revoke",
                       headers=admin_headers).status_code == 200
    assert client.get(f"/api/v1/public/uat-shares/{token}").status_code == 404


def test_client_can_create_one_defect_ticket_from_own_failed_test(client: TestClient, admin_headers: dict[str, str], database: Session, tmp_path: Path) -> None:
    existing_settings = client.app.dependency_overrides[get_settings]()
    client.app.dependency_overrides[get_settings] = lambda: existing_settings.model_copy(update={"attachment_storage_path": str(tmp_path)})
    status = database.scalar(select(ClientStatus).where(ClientStatus.code == "ACTIVE"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert status and admin
    customer = Client(code="UAT-CLIENT-DEFECT", name="UAT Defect Client", status_id=status.id)
    database.add(customer)
    database.commit()
    portal_user = _portal_user(database, "uatdefectportal", customer.id)
    portal_headers = _headers(client, portal_user.username)
    case = client.post("/api/v1/uat/test-cases", headers=admin_headers, json={
        "code": "CLIENT-DEFECT", "title": "Validate client workflow", "expected_result": "Works",
        "steps": [{"action": "Run workflow", "expected_result": "Works"}],
    })
    assert case.status_code == 201, case.text
    cycle = client.post("/api/v1/uat/cycles", headers=admin_headers, json={
        "code": "CLIENT-DEFECT-CYCLE", "title": "Client defect cycle", "client_id": customer.id,
        "release_version": "1.0", "coordinator_user_id": admin.id, "test_case_ids": [case.json()["id"]],
    })
    assert cycle.status_code == 201, cycle.text
    cycle_id = cycle.json()["id"]
    test_id = cycle.json()["tests"][0]["id"]
    assert client.post(f"/api/v1/uat/cycles/{cycle_id}/activate", headers=admin_headers).status_code == 200
    assert client.put(f"/api/v1/uat/cycle-tests/{test_id}/client-tester", headers=admin_headers,
                      json={"user_id": portal_user.id}).status_code == 200
    assert client.put(f"/api/v1/uat/cycles/{cycle_id}/portal-settings", headers=admin_headers, json={
        "portal_visible": True, "allow_client_testing": True, "allow_client_fail": True,
        "allow_client_create_ticket_from_failure": True, "allow_client_view_linked_ticket": True,
        "allow_client_attachments": True,
    }).status_code == 200
    due_test = database.get(UatCycleTest, test_id)
    assert due_test is not None
    due_test.due_date = date(2026, 10, 1)
    database.commit()
    assert queue_due_reminders(database, date(2026, 9, 28)) == 2
    assert database.scalar(select(Notification.id).where(Notification.notification_type == "UAT_DUE_SOON",
                                                         Notification.recipient_user_id == portal_user.id))
    assert client.post(f"/api/v1/portal/uat/tests/{test_id}/attempts", headers=portal_headers, json={
        "result": "FAIL", "actual_result": "Error", "failure_reason": "Client workflow failed", "severity": "HIGH",
    }).status_code == 201
    attempt_id = client.get(f"/api/v1/portal/uat/tests/{test_id}/attempts", headers=portal_headers).json()[0]["id"]
    uploaded = client.post(f"/api/v1/portal/uat/tests/{test_id}/attempts/{attempt_id}/evidence",
                           headers=portal_headers, files={"upload": ("failure.txt", b"failure proof", "text/plain")})
    assert uploaded.status_code == 201, uploaded.text
    draft = client.get(f"/api/v1/portal/uat/tests/{test_id}/defect-ticket-draft", headers=portal_headers)
    assert draft.status_code == 200, draft.text
    created = client.post(f"/api/v1/portal/uat/tests/{test_id}/defect-ticket", headers=portal_headers, json=draft.json())
    assert created.status_code == 201, created.text
    assert created.json()["ticket_number"]
    assert database.scalar(select(Notification.id).where(Notification.notification_type == "UAT_TICKET_CREATED"))
    assert client.post(f"/api/v1/portal/uat/tests/{test_id}/defect-ticket", headers=portal_headers, json=draft.json()).status_code == 409
    assert client.post(f"/api/v1/portal/uat/tests/{test_id}/attempts", headers=portal_headers,
                       json={"result": "FAIL", "actual_result": "Still failing", "failure_reason": "Still broken", "severity": "HIGH"}).status_code == 409
    ticket = database.get(Ticket, created.json()["ticket_id"])
    assert ticket is not None
    database.expire_all()
    sync_ticket_to_uat(database, ticket, admin, target_status_code="ASSIGNED")
    database.commit()
    database.expire_all()
    test = database.get(UatCycleTest, test_id)
    assert test and test.client_workflow_status == "FIX_IN_PROGRESS"
    sync_ticket_to_uat(database, ticket, admin, target_status_code="RESOLVED")
    database.commit()
    database.expire_all()
    test = database.get(UatCycleTest, test_id)
    assert test and test.client_workflow_status == "READY_FOR_RETEST"
    assert database.scalar(select(Notification.id).where(Notification.notification_type == "UAT_READY_FOR_RETEST",
                                                         Notification.recipient_user_id == portal_user.id))
    portal_cycle = client.get(f"/api/v1/portal/uat/cycles/{cycle_id}", headers=portal_headers).json()
    assert portal_cycle["tests"][0]["linked_ticket"]["id"] == created.json()["ticket_id"]
    linked_evidence = client.get(f"/api/v1/tickets/{created.json()['ticket_id']}/uat-evidence", headers=admin_headers)
    assert linked_evidence.status_code == 200, linked_evidence.text
    assert linked_evidence.json()[0]["id"] == uploaded.json()["id"]
    assert client.get(f"/api/v1/tickets/{created.json()['ticket_id']}/uat-evidence", headers=portal_headers).status_code == 404
    assert client.put(f"/api/v1/uat/cycles/{cycle_id}/portal-settings", headers=admin_headers, json={
        "portal_visible": True, "allow_client_testing": True, "allow_client_pass": True,
        "allow_client_fail": True, "allow_client_create_ticket_from_failure": True,
    }).status_code == 200
    retest = client.post(f"/api/v1/portal/uat/tests/{test_id}/attempts", headers=portal_headers,
                         json={"result": "PASS", "actual_result": "Workflow works now"})
    assert retest.status_code == 201, retest.text
    assert database.scalar(select(Notification.id).where(Notification.notification_type == "UAT_CLIENT_RETEST_PASS"))
    assert database.scalar(select(Notification.id).where(Notification.notification_type == "UAT_TICKET_READY_FOR_CLOSURE"))


def test_client_coordinator_reviews_without_tester_or_approver_rights(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    status = database.scalar(select(ClientStatus).where(ClientStatus.code == "ACTIVE"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert status and admin
    customer = Client(code="UAT-ROLES", name="UAT Roles Client", status_id=status.id)
    other_customer = Client(code="UAT-ROLES-OTHER", name="Other Client", status_id=status.id)
    database.add_all([customer, other_customer])
    database.commit()
    tester = _portal_user(database, "uatroles_tester", customer.id)
    coordinator = _portal_user(database, "uatroles_coordinator", customer.id)
    approver = _portal_user(database, "uatroles_approver", customer.id)
    bystander = _portal_user(database, "uatroles_bystander", customer.id)
    foreign = _portal_user(database, "uatroles_foreign", other_customer.id)
    tester_headers = _headers(client, tester.username)
    coordinator_headers = _headers(client, coordinator.username)
    approver_headers = _headers(client, approver.username)
    bystander_headers = _headers(client, bystander.username)
    case = client.post("/api/v1/uat/test-cases", headers=admin_headers, json={
        "code": "ROLE-CASE", "title": "Review release", "expected_result": "Accepted",
        "steps": [{"action": "Review", "expected_result": "Accepted"}],
    })
    assert case.status_code == 201, case.text
    cycle = client.post("/api/v1/uat/cycles", headers=admin_headers, json={
        "code": "ROLE-CYCLE", "title": "Client review", "client_id": customer.id,
        "release_version": "1.0", "coordinator_user_id": admin.id, "test_case_ids": [case.json()["id"]],
    })
    assert cycle.status_code == 201, cycle.text
    cycle_id, test_id = cycle.json()["id"], cycle.json()["tests"][0]["id"]
    assert client.post(f"/api/v1/uat/cycles/{cycle_id}/activate", headers=admin_headers).status_code == 200
    assert client.put(f"/api/v1/uat/cycle-tests/{test_id}/client-tester", headers=admin_headers,
                      json={"user_id": tester.id}).status_code == 200
    settings = {"portal_visible": True, "allow_client_testing": True, "allow_client_pass": True,
                "allow_client_signoff": True, "client_approver_user_id": approver.id,
                "client_coordinator_user_id": coordinator.id}
    invalid = client.put(f"/api/v1/uat/cycles/{cycle_id}/portal-settings", headers=admin_headers,
                         json={**settings, "client_coordinator_user_id": foreign.id})
    assert invalid.status_code == 409
    assert client.put(f"/api/v1/uat/cycles/{cycle_id}/portal-settings", headers=admin_headers,
                      json=settings).status_code == 200
    assert client.get("/api/v1/portal/uat/cycles", headers=bystander_headers).json() == []
    assert client.get(f"/api/v1/portal/uat/cycles/{cycle_id}", headers=bystander_headers).status_code == 404
    review = client.get(f"/api/v1/portal/uat/cycles/{cycle_id}", headers=coordinator_headers)
    assert review.status_code == 200 and review.json()["role"] == "COORDINATOR"
    assert review.json()["client_summary"]["total"] == 1
    assert review.json()["tests"][0]["assigned_to_me"] is False
    assert client.get(f"/api/v1/portal/uat/tests/{test_id}/attempts", headers=coordinator_headers).status_code == 200
    assert client.post(f"/api/v1/portal/uat/tests/{test_id}/attempts", headers=coordinator_headers,
                       json={"result": "PASS", "actual_result": "Accepted"}).status_code == 404
    assert client.post(f"/api/v1/portal/uat/cycles/{cycle_id}/signoff", headers=coordinator_headers,
                       json={"decision": "APPROVED"}).status_code == 403
    additional = client.post(f"/api/v1/portal/uat/cycles/{cycle_id}/signoff", headers=coordinator_headers,
                             json={"decision": "ADDITIONAL_TESTING", "comment": "Please check the release."})
    assert additional.status_code == 201, additional.text
    assert client.get(f"/api/v1/portal/uat/cycles/{cycle_id}/signoff", headers=coordinator_headers).json()["history"][0]["decision"] == "ADDITIONAL_TESTING"
    assert client.get(f"/api/v1/portal/uat/cycles/{cycle_id}", headers=approver_headers).json()["role"] == "APPROVER"
    assert client.get(f"/api/v1/portal/uat/cycles/{cycle_id}/signoff", headers=tester_headers).status_code == 404
    assert client.post(f"/api/v1/uat/cycle-tests/{test_id}/comments", headers=admin_headers,
                       json={"body": "Private investigation", "visibility": "INTERNAL_ONLY"}).status_code == 201
    assert client.post(f"/api/v1/uat/cycle-tests/{test_id}/comments", headers=admin_headers,
                       json={"body": "Please verify the fix", "visibility": "CLIENT_VISIBLE"}).status_code == 201
    activity = client.get(f"/api/v1/portal/uat/cycles/{cycle_id}/activity", headers=coordinator_headers)
    assert activity.status_code == 200
    assert "Please verify the fix" in [event["detail"] for event in activity.json()]
    assert "ADDITIONAL_TESTING" in [event["detail"] for event in activity.json()]
    assert "Private investigation" not in [event["detail"] for event in activity.json()]
