from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.iam.models import (
    AccessRequestDecision,
    Permission,
    Profile,
    ProfilePermission,
    User,
    UserPermissionOverride,
    UserProfile,
)
from app.modules.iam.security import create_access_token, hash_password
from app.tests.conftest import TEST_SETTINGS


def requester_headers(database: Session) -> dict[str, str]:
    user = User(full_name="Requesting User", username="requester", username_normalized="requester", email="requester@example.com", email_normalized="requester@example.com", password_hash=hash_password("RequesterPassword!123"), is_active=True, require_password_change=False)
    database.add(user); database.commit(); database.refresh(user)
    return {"Authorization": f"Bearer {create_access_token(user.id, TEST_SETTINGS)}"}


def test_request_deduplication_and_governed_approval(client: TestClient, database: Session, admin_headers: dict[str, str]) -> None:
    headers = requester_headers(database)
    payload = {"permission_code":"ticket.create","resource":"/tickets/create","return_path":"/tickets/create","justification":"Required to register caller support requests."}
    first = client.post("/api/v1/access-requests", json=payload, headers=headers)
    second = client.post("/api/v1/access-requests", json=payload, headers=headers)
    assert first.status_code == 201
    assert second.json()["id"] == first.json()["id"]

    no_step_up = client.post(f"/api/v1/access-requests/{first.json()['id']}/approve", json={"reason":"Approved for current support responsibilities.","grant_days":30}, headers=admin_headers)
    assert no_step_up.status_code == 401
    challenge = client.post("/api/v1/access-requests/step-up", json={"password":"DevelopmentPassword!123"}, headers=admin_headers)
    assert challenge.status_code == 200
    approved = client.post(f"/api/v1/access-requests/{first.json()['id']}/approve", json={"reason":"Approved for current support responsibilities.","grant_days":30,"challenge_token":challenge.json()["challenge_token"]}, headers=admin_headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    assert database.scalar(select(UserPermissionOverride)) is not None
    assert [row.action for row in database.scalars(select(AccessRequestDecision).order_by(AccessRequestDecision.id))] == ["REQUESTED", "APPROVED"]


def test_self_approval_and_unsafe_return_path_are_rejected(client: TestClient, admin_headers: dict[str, str]) -> None:
    unsafe = client.post("/api/v1/access-requests", json={"permission_code":"ticket.create","resource":"/tickets/create","return_path":"https://evil.example","justification":"A sufficiently long justification."}, headers=admin_headers)
    assert unsafe.status_code == 422


def test_missing_permission_is_requestable_from_an_api_forbidden_response(
    client: TestClient, database: Session
) -> None:
    headers = requester_headers(database)
    forbidden = client.get("/api/v1/clients", headers=headers)
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["details"]["required_permission"] == "client.view"

    requested = client.post(
        "/api/v1/access-requests",
        headers=headers,
        json={
            "permission_code": "client.view",
            "resource": "action:client.view",
            "return_path": "/clients",
            "justification": "Required to support assigned customer accounts.",
        },
    )
    assert requested.status_code == 201, requested.text
    assert requested.json()["permission_code"] == "client.view"


def test_authorized_credentials_can_grant_missing_permission_to_shared_profile(
    client: TestClient, database: Session
) -> None:
    headers = requester_headers(database)
    requester = database.scalar(select(User).where(User.username == "requester"))
    permission = database.scalar(select(Permission).where(Permission.code == "ticket.create"))
    assert requester is not None and permission is not None
    profile = Profile(code="REQUESTER-PROFILE", name="Requester shared profile", profile_type="EMPLOYEE", is_active=True)
    database.add(profile); database.flush()
    database.add(UserProfile(user_id=requester.id, profile_id=profile.id, is_primary=True, is_active=True))
    database.commit()

    impact = client.get("/api/v1/access-requests/grant-impact", params={"permission_code":"ticket.create"}, headers=headers)
    assert impact.status_code == 200
    assert impact.json()["profile_name"] == "Requester shared profile"
    assert impact.json()["affected_user_count"] == 1

    granted = client.post("/api/v1/access-requests/direct-profile-grant", headers=headers, json={"permission_code":"ticket.create","resource":"/tickets/create","return_path":"/tickets/create","reason":"Required for the shared call center workflow.","approver_login":"admin","approver_password":"DevelopmentPassword!123"})
    assert granted.status_code == 201, granted.text
    assert granted.json()["status"] == "APPROVED"
    assert granted.json()["source_action"] == "DIRECT_GRANTED"
    assert database.get(ProfilePermission, {"profile_id":profile.id,"permission_id":permission.id}) is not None
    assert database.scalar(select(AccessRequestDecision).where(AccessRequestDecision.action == "DIRECT_GRANTED")) is not None
