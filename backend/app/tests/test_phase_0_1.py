from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.modules.iam.models import (
    AuthenticationEvent,
    Effect,
    Permission,
    Profile,
    ProfilePermission,
    User,
    UserPermissionOverride,
    UserProfile,
)
from app.modules.iam.security import hash_password, verify_password
from app.modules.iam.service import effective_permissions
from app.modules.notifications.models import EventOutbox


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_database_health(client: TestClient) -> None:
    assert client.get("/api/v1/health/database").status_code == 200


def test_user_permission_access_lists_profile_sources_and_override_history(
    client: TestClient, database: Session, admin_headers: dict[str, str]
) -> None:
    admin = database.scalar(select(User).where(User.username == "admin"))
    permission = database.scalar(select(Permission).where(Permission.code == "contract.view"))
    assert admin is not None and permission is not None
    database.add(UserPermissionOverride(
        user_id=admin.id,
        permission_id=permission.id,
        effect=Effect.DENY,
        valid_from=server_now() - timedelta(minutes=1),
        valid_to=server_now() + timedelta(hours=1),
        reason="Temporary separation-of-duties test",
        approved_by_user_id=admin.id,
        created_by_user_id=admin.id,
    ))
    database.commit()

    response = client.get(f"/api/v1/users/{admin.id}/permission-access", headers=admin_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert any(row["permission_code"] == "profile.manage" and row["active"] for row in payload["profile_permissions"])
    override = next(row for row in payload["overrides"] if row["permission_code"] == "contract.view")
    assert override["effect"] == "DENY"
    assert override["active"] is True
    assert override["approved_by_name"] == admin.full_name
    assert "contract.view" not in payload["effective_permissions"]


def test_login_success_and_failure(client: TestClient) -> None:
    success = client.post(
        "/api/v1/auth/login", json={"login": "admin", "password": "DevelopmentPassword!123"}
    )
    assert success.status_code == 200
    failure = client.post(
        "/api/v1/auth/login", json={"login": "admin", "password": "incorrect-password"}
    )
    assert failure.status_code == 401
    assert failure.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_inactive_user_denied(client: TestClient, database: Session) -> None:
    user = database.scalar(select(User).where(User.username == "admin"))
    user.is_active = False
    database.commit()
    response = client.post(
        "/api/v1/auth/login", json={"login": "admin", "password": "DevelopmentPassword!123"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCOUNT_INACTIVE"


def test_refresh_rotation_and_logout(client: TestClient, database: Session) -> None:
    login = client.post(
        "/api/v1/auth/login", json={"login": "admin", "password": "DevelopmentPassword!123"}
    ).json()
    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != login["refresh_token"]
    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert reuse.status_code == 401
    logout = client.post(
        "/api/v1/auth/logout", json={"refresh_token": rotated.json()["refresh_token"]}
    )
    assert logout.status_code == 204
    events=set(database.scalars(select(AuthenticationEvent.event_type)))
    assert {"REFRESH_SUCCEEDED","REFRESH_REJECTED_REVOKED"} <= events


def test_explicit_logout_is_recorded_without_token_material(client: TestClient,database:Session)->None:
    login=client.post("/api/v1/auth/login",json={"login":"admin","password":"DevelopmentPassword!123"}).json()
    assert client.post("/api/v1/auth/logout",json={"refresh_token":login["refresh_token"]}).status_code==204
    event=database.scalar(select(AuthenticationEvent).where(AuthenticationEvent.event_type=="LOGOUT_EXPLICIT").order_by(AuthenticationEvent.id.desc()))
    assert event is not None and event.user_id is not None and event.detail is None


def test_required_password_change_blocks_application_until_completed(
    client: TestClient, database: Session
) -> None:
    user = database.scalar(select(User).where(User.username == "admin"))
    user.require_password_change = True
    database.commit()
    login_response = client.post(
        "/api/v1/auth/login",
        json={"login": "admin", "password": "DevelopmentPassword!123"},
    )
    assert login_response.json()["require_password_change"] is True
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
    blocked = client.get("/api/v1/dashboards/summary", headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"

    incorrect = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "WrongPassword!123", "new_password": "NewPassword!12345"},
        headers=headers,
    )
    assert incorrect.status_code == 401
    changed = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "DevelopmentPassword!123",
            "new_password": "NewPassword!12345",
        },
        headers=headers,
    )
    assert changed.status_code == 204
    database.refresh(user)
    assert user.require_password_change is False
    assert client.get("/api/v1/dashboards/summary", headers=headers).status_code == 200


def test_forgot_password_uses_single_use_token_and_revokes_sessions(
    client: TestClient,
    database: Session,
) -> None:
    missing = client.post("/api/v1/auth/forgot-password", json={"login": "missing@example.com"})
    assert missing.status_code == 200
    assert missing.json()["reset_token"] is None

    requested = client.post("/api/v1/auth/forgot-password", json={"login": "admin"})
    assert requested.status_code == 200, requested.text
    token = requested.json()["reset_token"]
    assert token
    assert (
        database.scalar(select(EventOutbox).where(EventOutbox.event_type == "PASSWORD_RESET_EMAIL"))
        is not None
    )
    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "RecoveredPassword!456"},
    )
    assert reset.status_code == 204, reset.text
    reused = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "AnotherPassword!789"},
    )
    assert reused.status_code == 409
    login = client.post(
        "/api/v1/auth/login",
        json={"login": "admin", "password": "RecoveredPassword!456"},
    )
    assert login.status_code == 200, login.text


def test_permission_enforcement(client: TestClient, database: Session) -> None:
    user = User(
        full_name="No Privileges",
        username="plain",
        username_normalized="plain",
        email="plain@example.com",
        email_normalized="plain@example.com",
        password_hash=hash_password("DevelopmentPassword!123"),
        user_type="EMPLOYEE",
    )
    database.add(user)
    database.commit()
    token = client.post(
        "/api/v1/auth/login", json={"login": "plain", "password": "DevelopmentPassword!123"}
    ).json()["access_token"]
    assert (
        client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"}).status_code == 403
    )


def test_presence_heartbeat_updates_timestamp_without_business_conflict(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    admin = database.scalar(select(User).where(User.username_normalized == "admin"))
    assert admin is not None
    previous = admin.last_seen_at

    first = client.post("/api/v1/auth/presence", headers=admin_headers)
    second = client.post("/api/v1/auth/presence", headers=admin_headers)

    assert first.status_code == 204
    assert second.status_code == 204
    database.refresh(admin)
    assert admin.last_seen_at is not None
    assert previous is None or admin.last_seen_at >= previous


def test_call_center_can_read_products_for_ticket_creation(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    profile = database.scalar(select(Profile).where(Profile.code == "CALL_CENTER"))
    user = User(
        full_name="Call Center Catalog User",
        username="callcenter.catalog",
        username_normalized="callcenter.catalog",
        email="callcenter.catalog@example.com",
        email_normalized="callcenter.catalog@example.com",
        password_hash=hash_password("DevelopmentPassword!123"),
        user_type="EMPLOYEE",
    )
    database.add(user)
    database.flush()
    database.add(UserProfile(user_id=user.id, profile_id=profile.id, is_primary=True))
    database.commit()
    created = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "CALLCENTER-PRODUCT", "name": "Call Center Product"},
    )
    assert created.status_code == 201, created.text
    login = client.post(
        "/api/v1/auth/login",
        json={"login": "callcenter.catalog", "password": "DevelopmentPassword!123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    products = client.get("/api/v1/products", headers=headers)
    assert products.status_code == 200, products.text
    assert created.json()["id"] in {item["id"] for item in products.json()}


def test_deny_override_wins_and_expired_profile_ignored(database: Session) -> None:
    user = database.scalar(select(User).where(User.username == "admin"))
    permission = database.scalar(select(Permission).where(Permission.code == "user.manage"))
    database.add(
        UserPermissionOverride(
            user_id=user.id,
            permission_id=permission.id,
            effect=Effect.DENY,
            reason="test",
            created_by_user_id=user.id,
        )
    )
    database.commit()
    assert "user.manage" not in effective_permissions(database, user).permissions
    for assignment in database.scalars(select(UserProfile).where(UserProfile.user_id == user.id)):
        assignment.valid_from = server_now() - timedelta(days=2)
        assignment.valid_to = server_now() - timedelta(days=1)
    database.commit()
    assert "profile.manage" not in effective_permissions(database, user).permissions


def test_user_creation_and_duplicates(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    profile = database.scalar(select(Profile).where(Profile.code == "L1_SUPPORT"))
    payload = {
        "full_name": "Test Agent",
        "username": "agent@example.com",
        "email": "agent@example.com",
        "password": "TemporaryPassword!123",
        "primary_profile_id": profile.id,
        "additional_profile_ids": [],
        "client_scope_ids": [],
        "branch_scope_ids": [],
        "user_type": "EMPLOYEE",
        "employee_code": "",
        "department": "Support",
        "job_title": "Junior Technical Support",
        "hire_date": "2026-08-05",
    }
    created_user = client.post("/api/v1/users", json=payload, headers=admin_headers)
    assert created_user.status_code == 201
    assert created_user.json()["employee_code"].startswith("EMP-")
    duplicate_username = {**payload, "email": "other@example.com"}
    assert (
        client.post("/api/v1/users", json=duplicate_username, headers=admin_headers).json()[
            "error"
        ]["code"]
        == "DUPLICATE_USERNAME"
    )
    duplicate_email = {**payload, "username": "other"}
    assert (
        client.post("/api/v1/users", json=duplicate_email, headers=admin_headers).json()["error"][
            "code"
        ]
        == "DUPLICATE_EMAIL"
    )
    another_without_code = {
        **payload,
        "username": "agent2",
        "email": "agent2@example.com",
    }
    assert (
        client.post("/api/v1/users", json=another_without_code, headers=admin_headers).status_code
        == 201
    )
    second_user = database.scalar(select(User).where(User.username == "agent2"))
    assert second_user is not None
    assert second_user.employee_code is not None
    assert second_user.employee_code.startswith("EMP-")
    assert second_user.employee_code != created_user.json()["employee_code"]
    with_code = {
        **payload,
        "username": "agent3",
        "email": "agent3@example.com",
        "employee_code": "EMP-100",
    }
    assert client.post("/api/v1/users", json=with_code, headers=admin_headers).status_code == 201
    duplicate_code = {
        **with_code,
        "username": "agent4",
        "email": "agent4@example.com",
    }
    duplicate_response = client.post("/api/v1/users", json=duplicate_code, headers=admin_headers)
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["error"]["code"] == "DUPLICATE_EMPLOYEE_CODE"
    agent = database.scalar(select(User).where(User.username == "agent@example.com"))
    assert agent is not None
    assert agent.job_title == "Junior Technical Support"
    assert str(agent.hire_date) == "2026-08-05"
    updated = client.patch(
        f"/api/v1/users/{agent.id}",
        headers=admin_headers,
        json={
            "full_name": "Updated Test Agent",
            "department": "Support L1",
            "employee_code": "EMP-101",
            "require_password_change": False,
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["full_name"] == "Updated Test Agent"
    assert updated.json()["department"] == "Support L1"
    self_profile = client.put(
        "/api/v1/auth/me/profile-preferences",
        headers=admin_headers,
        json={
            "default_page": "dashboard",
            "default_dashboard_scope": "GENERAL",
            "default_saved_view_id": None,
            "theme_mode": "SYSTEM",
            "theme_preset": "MIDNIGHT",
            "profile_picture_url": "https://example.com/profile/admin.png",
        },
    )
    assert self_profile.status_code == 200, self_profile.text
    assert self_profile.json()["profile_picture_url"] == "https://example.com/profile/admin.png"
    assert self_profile.json()["theme_preset"] == "MIDNIGHT"
    l2_profile = database.scalar(select(Profile).where(Profile.code == "L2_SUPPORT"))
    assert l2_profile is not None
    assigned_profile = client.post(
        f"/api/v1/users/{agent.id}/profiles",
        headers=admin_headers,
        json={
            "profile_id": l2_profile.id,
            "is_primary": False,
            "reason": "Temporary L2 support responsibilities.",
        },
    )
    assert assigned_profile.status_code == 201, assigned_profile.text
    profile_listing = client.get(f"/api/v1/users/{agent.id}/profiles", headers=admin_headers)
    assert {item["profile_code"] for item in profile_listing.json()} == {
        "L1_SUPPORT",
        "L2_SUPPORT",
    }
    primary_removal = client.delete(
        f"/api/v1/users/{agent.id}/profiles/{profile.id}", headers=admin_headers
    )
    assert primary_removal.status_code == 409
    promoted = client.post(
        f"/api/v1/users/{agent.id}/profiles",
        headers=admin_headers,
        json={
            "profile_id": l2_profile.id,
            "is_primary": True,
            "reason": "L2 is now the primary assignment.",
        },
    )
    assert promoted.status_code == 201, promoted.text
    assert (
        client.delete(
            f"/api/v1/users/{agent.id}/profiles/{profile.id}", headers=admin_headers
        ).status_code
        == 204
    )
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    self_deactivate = client.patch(
        f"/api/v1/users/{admin.id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert self_deactivate.status_code == 409
    assert self_deactivate.json()["error"]["code"] == "SELF_DEACTIVATION"
    reset = client.post(
        f"/api/v1/users/{agent.id}/reset-password",
        headers=admin_headers,
        json={
            "temporary_password": "ResetTemporaryPassword!456",
            "reason": "User requested an administrator password reset.",
        },
    )
    assert reset.status_code == 204, reset.text
    database.expire_all()
    reset_agent = database.get(User, agent.id)
    assert reset_agent is not None
    assert reset_agent.require_password_change is True
    assert verify_password("ResetTemporaryPassword!456", reset_agent.password_hash)


def test_system_profiles_are_managed(database: Session) -> None:
    profiles = list(database.scalars(select(Profile).where(Profile.is_system.in_([True]))))
    assert {p.code for p in profiles} == {
        "CALL_CENTER",
        "L1_SUPPORT",
        "L2_SUPPORT",
        "L3_SUPPORT",
        "SUPPORT_MANAGER",
        "HR",
        "TOP_MANAGEMENT",
        "FINANCIAL_MANAGEMENT",
        "PROJECT_HANDOVER",
        "ADMINISTRATOR",
            "CLIENT_PORTAL",
            "VENDOR_PRE_TICKET_API",
        }
    call_center = next(profile for profile in profiles if profile.code == "CALL_CENTER")
    caller_permission = database.scalar(
        select(Permission)
        .join(ProfilePermission, ProfilePermission.permission_id == Permission.id)
        .where(
            Permission.code == "contact.manage",
            ProfilePermission.profile_id == call_center.id,
        )
    )
    assert caller_permission is not None


def test_custom_profile_permissions_and_clone(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    ticket_create = database.scalar(select(Permission).where(Permission.code == "ticket.create"))
    ticket_view = database.scalar(select(Permission).where(Permission.code == "ticket.view.own"))
    assert ticket_create is not None and ticket_view is not None
    created = client.post(
        "/api/v1/profiles",
        headers=admin_headers,
        json={
            "name": "Custom Agent",
            "description": "Custom test profile",
            "profile_type": "EMPLOYEE",
            "permission_ids": [ticket_create.id],
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["code"].startswith("PRF-")
    profile_id = created.json()["id"]
    landing_page = client.patch(
        f"/api/v1/profiles/{profile_id}",
        headers=admin_headers,
        json={"default_dashboard_code": "tickets"},
    )
    assert landing_page.status_code == 200, landing_page.text
    assert landing_page.json()["default_dashboard_code"] == "tickets"
    top_management_landing = client.patch(
        f"/api/v1/profiles/{profile_id}",
        headers=admin_headers,
        json={"default_dashboard_code": "top-management"},
    )
    assert top_management_landing.status_code == 200, top_management_landing.text
    assert top_management_landing.json()["default_dashboard_code"] == "top-management"
    assigned = client.get(f"/api/v1/profiles/{profile_id}/permissions", headers=admin_headers)
    assert [item["code"] for item in assigned.json()] == ["ticket.create"]
    updated = client.put(
        f"/api/v1/profiles/{profile_id}/permissions",
        headers=admin_headers,
        json={
            "permission_ids": [ticket_create.id, ticket_view.id],
            "reason": "Expand the custom agent ticket scope.",
        },
    )
    assert {item["code"] for item in updated.json()} == {
        "ticket.create",
        "ticket.view.own",
    }
    cloned = client.post(
        f"/api/v1/profiles/{profile_id}/clone",
        headers=admin_headers,
        params={"name": "Custom Agent Copy"},
    )
    assert cloned.status_code == 201, cloned.text
    assert cloned.json()["code"].startswith("PRF-")
    assert cloned.json()["code"] != created.json()["code"]
