from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.clients.models import ClientStatus
from app.modules.contracts.models import BusinessCalendar
from app.modules.iam.models import (
    AuditLog,
    Permission,
    Profile,
    ProfilePermission,
    User,
    UserClientScope,
    UserProfile,
)
from app.modules.iam.security import hash_password
from app.modules.knowledge_base.models import Article
from app.modules.service_management.models import ChangeRequestDetail, Problem, ProblemTicketLink
from app.modules.tickets.models import (
    Ticket,
    TicketSatisfaction,
    TicketStatus,
    TicketStatusHistory,
    TicketType,
)
from app.modules.tickets.satisfaction_tokens import decrypt_satisfaction_token


def create_client_record(
    client: TestClient,
    headers: dict[str, str],
    database: Session,
    code: str,
) -> int:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    response = client.post(
        "/api/v1/clients",
        headers=headers,
        json={"code": code, "name": f"{code} Client", "status_id": status_id},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_portal_user(database: Session, client_id: int) -> User:
    profile = database.scalar(select(Profile).where(Profile.code == "CLIENT_PORTAL"))
    assert profile is not None
    user = User(
        full_name="Portal User",
        username="portal",
        username_normalized="portal",
        email="portal@example.com",
        email_normalized="portal@example.com",
        password_hash=hash_password("PortalPassword!123"),
        user_type="CLIENT_PORTAL",
    )
    database.add(user)
    database.flush()
    database.add(
        UserProfile(
            user_id=user.id,
            profile_id=profile.id,
            is_primary=True,
            assigned_by_user_id=user.id,
            assignment_reason="Portal test",
        )
    )
    database.add(UserClientScope(user_id=user.id, client_id=client_id))
    database.commit()
    return user


def test_service_dashboard_cards_scope_portal_records_and_hide_problem_notes(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    own_client = create_client_record(client, admin_headers, database, "CARDS-OWN")
    other_client = create_client_record(client, admin_headers, database, "CARDS-OTHER")
    portal = create_portal_user(database, own_client)
    type_ids = dict(database.execute(select(TicketType.code, TicketType.id)).all())
    created = []
    for client_id, code in (
        (own_client, "INCIDENT"),
        (own_client, "CHANGE_REQUEST"),
        (other_client, "CHANGE_REQUEST"),
    ):
        response = client.post(
            "/api/v1/tickets",
            headers=admin_headers,
            json={
                "ticket_type_id": type_ids[code],
                "client_id": client_id,
                "impact": "LOW",
                "urgency": "LOW",
                "subject": "Dashboard scope test",
                "description": "Dashboard scope test ticket description.",
            },
        )
        assert response.status_code == 201, response.text
        created.append(response.json())
    problem = Problem(
        problem_number="PRB-CARDS",
        title="Private investigation",
        description="Secret internal notes",
        created_by_user_id=portal.id,
    )
    database.add(problem)
    database.flush()
    database.add(
        ProblemTicketLink(
            problem_id=problem.id, ticket_id=created[0]["id"], linked_by_user_id=portal.id
        )
    )
    database.commit()
    login = client.post(
        "/api/v1/auth/login", json={"login": "portal", "password": "PortalPassword!123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = client.get("/api/v1/service-management/dashboard-cards", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["incidents"]["count"] == 1
    assert data["changes"]["count"] == 1
    assert data["problems"]["count"] == 1
    assert data["changes"]["records"][0]["id"] == created[1]["id"]
    assert data["problems"]["records"][0]["route"] == f"/portal/tickets/{created[0]['id']}"
    assert "Private investigation" not in response.text
    assert "Secret internal notes" not in response.text
    outside = client.get(
        "/api/v1/service-management/dashboard-cards",
        headers=headers,
        params={"client_id": other_client},
    ).json()
    assert all(value["count"] == 0 for value in outside.values())


def test_portal_client_profile_uses_independent_permission_and_client_scope(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    own_client = create_client_record(client, admin_headers, database, "PORTAL-PROFILE")
    other_client = create_client_record(client, admin_headers, database, "OTHER-PROFILE")
    create_portal_user(database, own_client)
    login = client.post(
        "/api/v1/auth/login",
        json={"login": "portal", "password": "PortalPassword!123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    own = client.get("/api/v1/portal/client-profile", headers=headers)
    assert own.status_code == 200, own.text
    assert own.json()["client"]["id"] == own_client
    assert set(own.json()["lifecycle"]) == {
        "uat",
        "deployments",
        "incidents",
        "changes",
        "problems",
    }
    assert all(area["count"] == 0 for area in own.json()["lifecycle"].values())
    assert {item["id"] for item in own.json()["clients"]} == {own_client}
    assert "notes" not in own.json()["client"]
    assert "access_credentials" not in own.json()["client"]
    assert (
        client.get(
            "/api/v1/portal/client-profile",
            headers=headers,
            params={"client_id": other_client},
        ).status_code
        == 404
    )

    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert "portal.client_profile.view" in me["permissions"]
    assert "client.profile.view" not in me["permissions"]

    portal_profile = database.scalar(select(Profile).where(Profile.code == "CLIENT_PORTAL"))
    portal_permission = database.scalar(
        select(Permission).where(Permission.code == "portal.client_profile.view")
    )
    assert portal_profile is not None and portal_permission is not None
    database.execute(
        delete(ProfilePermission).where(
            ProfilePermission.profile_id == portal_profile.id,
            ProfilePermission.permission_id == portal_permission.id,
        )
    )
    database.commit()
    denied = client.get("/api/v1/portal/client-profile", headers=headers)
    assert denied.status_code == 403


def test_portal_user_can_create_change_request(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    portal_client = create_client_record(client, admin_headers, database, "PORTAL-CHANGE")
    create_portal_user(database, portal_client)
    login = client.post(
        "/api/v1/auth/login",
        json={"login": "portal", "password": "PortalPassword!123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    change_type = database.scalar(select(TicketType).where(TicketType.code == "CHANGE_REQUEST"))
    assert change_type is not None

    response = client.post(
        "/api/v1/portal/tickets",
        headers=headers,
        json={
            "ticket_type_id": change_type.id,
            "client_id": portal_client,
            "impact": "MEDIUM",
            "urgency": "LOW",
            "priority": "P3",
            "creation_method": "PORTAL",
            "subject": "Request a controlled configuration change",
            "description": "Please assess and schedule this configuration change.",
            "change_request": {
                "request_kind": "UPDATE_EXISTING_FEATURE",
                "purpose": "Improve the controlled client configuration.",
                "detailed_description": "Apply the requested configuration behavior to the affected product.",
                "business_impact": "Reduces manual processing for the client team.",
                "expected_result": "The configuration behaves as described after implementation.",
                "required_permissions": "Configuration administrator access",
                "requested_priority": "MEDIUM",
            },
        },
    )

    assert response.status_code == 201, response.text
    created = database.get(Ticket, response.json()["id"])
    assert created is not None
    assert created.ticket_type_id == change_type.id
    assert created.ticket_number.startswith("CHG-")
    detail = database.scalar(
        select(ChangeRequestDetail).where(ChangeRequestDetail.ticket_id == created.id)
    )
    assert detail is not None
    assert detail.change_status == "SUBMITTED"
    assert detail.purpose == "Improve the controlled client configuration."


def test_portal_service_advisories_expose_only_client_safe_content(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    portal_client = create_client_record(client, admin_headers, database, "PORTAL-ADVISORY")
    create_portal_user(database, portal_client)
    login = client.post(
        "/api/v1/auth/login", json={"login": "portal", "password": "PortalPassword!123"}
    )
    portal_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    incident_type = database.scalar(select(TicketType).where(TicketType.code == "INCIDENT"))
    assert incident_type is not None
    ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": incident_type.id,
            "client_id": portal_client,
            "impact": "HIGH",
            "urgency": "HIGH",
            "subject": "Client-visible service disruption",
            "description": "The service disruption is being coordinated.",
        },
    ).json()
    declared = client.post(
        f"/api/v1/tickets/{ticket['id']}/major-incident",
        headers=admin_headers,
        json={
            "severity": "SEV1",
            "incident_commander_user_id": ticket["created_by_user_id"],
            "business_impact": "Service is unavailable.",
            "current_status_summary": "Internal diagnostic summary.",
        },
    ).json()
    internal = client.post(
        f"/api/v1/major-incidents/{declared['id']}/updates",
        headers=admin_headers,
        json={"update_type": "INTERNAL", "internal_message": "Sensitive infrastructure details."},
    )
    assert internal.status_code == 201, internal.text
    public = client.post(
        f"/api/v1/major-incidents/{declared['id']}/updates",
        headers=admin_headers,
        json={"update_type": "CLIENT", "client_message": "Our response team is restoring service."},
    )
    assert public.status_code == 201, public.text
    problem = client.post(
        "/api/v1/problems",
        headers=admin_headers,
        json={
            "title": "Service disruption investigation",
            "description": "Internal investigation details must remain private.",
            "source_ticket_id": ticket["id"],
        },
    ).json()
    updated = client.patch(
        f"/api/v1/problems/{problem['id']}",
        headers=admin_headers,
        json={
            "workaround": "Use the approved alternate service path.",
            "version": problem["version"],
        },
    ).json()
    draft = client.post(
        f"/api/v1/problems/{problem['id']}/knowledge/draft",
        headers=admin_headers,
        json={"content_type": "WORKAROUND", "version": updated["version"]},
    ).json()

    before_publish = client.get(
        f"/api/v1/portal/tickets/{ticket['id']}/service-advisories", headers=portal_headers
    )
    assert before_publish.status_code == 200, before_publish.text
    assert [item["message"] for item in before_publish.json()["major_incidents"][0]["updates"]] == [
        "Our response team is restoring service."
    ]
    assert before_publish.json()["knowledge"] == []
    payload = str(before_publish.json())
    assert "Sensitive infrastructure" not in payload
    assert "Internal diagnostic" not in payload

    article = database.get(Article, draft["article_id"])
    assert article is not None
    article.status = "PUBLISHED"
    article.client_visible = True
    article.visibility = "BOTH"
    database.commit()
    after_publish = client.get(
        f"/api/v1/portal/tickets/{ticket['id']}/service-advisories", headers=portal_headers
    )
    assert after_publish.status_code == 200, after_publish.text
    assert (
        after_publish.json()["knowledge"][0]["body"] == "Use the approved alternate service path."
    )


def test_portal_rating_is_authoritative_and_public_link_is_read_only(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    portal_client = create_client_record(client, admin_headers, database, "PORTAL-RATING")
    create_portal_user(database, portal_client)
    login = client.post(
        "/api/v1/auth/login",
        json={"login": "portal", "password": "PortalPassword!123"},
    )
    portal_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    created = client.post(
        "/api/v1/portal/tickets",
        headers=portal_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": portal_client,
            "impact": "LOW",
            "urgency": "LOW",
            "priority": "P4",
            "creation_method": "PORTAL",
            "subject": "Portal satisfaction ownership",
            "description": "Verify the authenticated portal owns the first final rating.",
        },
    )
    assert created.status_code == 201, created.text
    ticket = database.get(Ticket, created.json()["id"])
    closed_id = database.scalar(select(TicketStatus.id).where(TicketStatus.code == "CLOSED"))
    assert ticket is not None and closed_id is not None
    ticket.status_id = closed_id
    database.commit()

    available = client.get(
        f"/api/v1/portal/tickets/{ticket.id}/satisfaction", headers=portal_headers
    )
    assert available.status_code == 200, available.text
    assert available.json() == {"state": "AVAILABLE"}
    submitted = client.post(
        f"/api/v1/portal/tickets/{ticket.id}/satisfaction",
        headers=portal_headers,
        json={
            "ticket_rating": 5,
            "service_rating": 4,
            "engineer_rating": 5,
            "comments": "Handled professionally.",
        },
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["source"] == "CLIENT_PORTAL"

    survey = database.scalar(
        select(TicketSatisfaction).where(TicketSatisfaction.ticket_id == ticket.id)
    )
    assert survey is not None and survey.token_ciphertext
    raw_token = decrypt_satisfaction_token(survey.token_ciphertext)
    assert raw_token
    shared = client.get("/api/v1/public/satisfaction", params={"token": raw_token})
    assert shared.status_code == 200, shared.text
    assert shared.json()["submitted"] is True
    assert shared.json()["ticket_rating"] == 5
    overwrite = client.post(
        "/api/v1/public/satisfaction",
        params={"token": raw_token},
        json={
            "ticket_rating": 1,
            "service_rating": 1,
            "engineer_rating": 1,
            "comments": "Attempted overwrite.",
        },
    )
    assert overwrite.status_code == 200
    assert overwrite.json()["already_submitted"] is True
    database.refresh(survey)
    assert (survey.ticket_rating, survey.service_rating, survey.engineer_rating) == (5, 4, 5)


def test_portal_user_cannot_select_support_now_as_landing_page(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    portal_client = create_client_record(client, admin_headers, database, "PORTAL-HOME")
    create_portal_user(database, portal_client)
    login = client.post(
        "/api/v1/auth/login", json={"login": "portal", "password": "PortalPassword!123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).json()["default_page"] == "portal"
    response = client.put(
        "/api/v1/auth/me/profile-preferences",
        headers=headers,
        json={
            "default_page": "home",
            "default_dashboard_scope": "GENERAL",
            "default_saved_view_id": None,
            "theme_mode": "SYSTEM",
            "profile_picture_url": None,
        },
    )
    assert response.status_code == 409


def test_mosaic_creation_requires_visible_linked_product_module_service_path(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    portal_client = create_client_record(client, admin_headers, database, "MOSAIC")
    create_portal_user(database, portal_client)
    portal_login = client.post(
        "/api/v1/auth/login", json={"login": "portal", "password": "PortalPassword!123"}
    )
    portal_headers = {"Authorization": f"Bearer {portal_login.json()['access_token']}"}
    product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "MOSAIC-P", "name": "Mosaic Product"},
    ).json()
    linked_module = client.post(
        f"/api/v1/products/{product['id']}/modules",
        headers=admin_headers,
        json={"code": "MOSAIC-M1", "name": "Linked Module"},
    ).json()
    other_module = client.post(
        f"/api/v1/products/{product['id']}/modules",
        headers=admin_headers,
        json={"code": "MOSAIC-M2", "name": "Other Module"},
    ).json()
    service = client.post(
        "/api/v1/services",
        headers=admin_headers,
        json={"code": "MOSAIC-S", "name": "Linked Service", "module_ids": [linked_module["id"]]},
    ).json()
    calendar_id = database.scalar(select(BusinessCalendar.id))
    contract = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "MOSAIC-CONTRACT",
            "client_id": portal_client,
            "name": "Mosaic blanket contract",
            "start_date": str(date.today() - timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=30)),
            "calendar_id": calendar_id,
        },
    )
    assert contract.status_code == 201, contract.text
    catalog = client.get("/api/v1/portal/catalog", headers=portal_headers)
    assert catalog.status_code == 200, catalog.text
    assert catalog.json()["selected_client_id"] == portal_client
    catalog_service = next(
        item for item in catalog.json()["services"] if item["id"] == service["id"]
    )
    assert catalog_service["module_ids"] == [linked_module["id"]]
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    base = {
        "ticket_type_id": ticket_type_id,
        "client_id": portal_client,
        "product_id": product["id"],
        "service_id": service["id"],
        "impact": "MEDIUM",
        "urgency": "MEDIUM",
        "priority": "P2",
        "creation_method": "MOSAIC",
        "subject": "Guided Mosaic request",
        "description": "The governed Mosaic relationship must be persisted.",
    }
    incomplete = client.post("/api/v1/portal/tickets", headers=portal_headers, json=base)
    assert (
        incomplete.status_code == 409
        and incomplete.json()["error"]["code"] == "MOSAIC_SELECTION_INCOMPLETE"
    )
    standard_incomplete = client.post(
        "/api/v1/portal/tickets",
        headers=portal_headers,
        json={**base, "creation_method": "PORTAL"},
    )
    assert standard_incomplete.status_code == 409
    assert standard_incomplete.json()["error"]["code"] == "SERVICE_MODULE_REQUIRED"
    assert standard_incomplete.json()["error"]["details"]["allowed_module_ids"] == [
        linked_module["id"]
    ]
    mismatch = client.post(
        "/api/v1/portal/tickets",
        headers=portal_headers,
        json={**base, "product_module_id": other_module["id"]},
    )
    assert (
        mismatch.status_code == 409
        and mismatch.json()["error"]["code"] == "MOSAIC_SERVICE_MODULE_MISMATCH"
    )
    created = client.post(
        "/api/v1/portal/tickets",
        headers=portal_headers,
        json={**base, "product_module_id": linked_module["id"]},
    )
    assert created.status_code == 201, created.text
    stored = database.get(Ticket, created.json()["id"])
    assert stored is not None
    assert (
        stored.source_channel,
        stored.product_id,
        stored.product_module_id,
        stored.service_id,
    ) == ("MOSAIC", product["id"], linked_module["id"], service["id"])


def test_portal_training_material_publication_is_safe_and_server_enforced(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    client_id = create_client_record(client, admin_headers, database, "TRAINING")
    create_portal_user(database, client_id)
    login = client.post(
        "/api/v1/auth/login", json={"login": "portal", "password": "PortalPassword!123"}
    )
    portal_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    material_payload = {
        "title": "Portal safe training",
        "description": "Published guidance",
        "is_required": False,
        "display_order": 1,
        "is_active": True,
        "show_in_client_portal": False,
    }
    material = client.post(
        "/api/v1/onboarding/materials", headers=admin_headers, json=material_payload
    )
    assert material.status_code == 201
    material_id = material.json()["id"]
    unsafe = client.post(
        f"/api/v1/onboarding/materials/{material_id}/resources",
        headers=admin_headers,
        json={
            "name": "Internal",
            "resource_type": "WEBSITE",
            "url": "https://intranet.local/guide",
            "is_active": True,
        },
    )
    assert unsafe.status_code == 201  # Internal resources remain valid internally.
    blocked = client.patch(
        f"/api/v1/onboarding/materials/{material_id}",
        headers=admin_headers,
        json={**material_payload, "show_in_client_portal": True},
    )
    assert blocked.status_code == 409
    client.patch(
        f"/api/v1/onboarding/material-resources/{unsafe.json()['id']}",
        headers=admin_headers,
        json={
            "name": "Internal",
            "resource_type": "WEBSITE",
            "url": "https://intranet.local/guide",
            "is_active": False,
        },
    )
    client.post(
        f"/api/v1/onboarding/materials/{material_id}/resources",
        headers=admin_headers,
        json={
            "name": "Public guide",
            "resource_type": "WEBSITE",
            "url": "https://docs.example.com/guide",
            "is_active": True,
        },
    )
    published = client.patch(
        f"/api/v1/onboarding/materials/{material_id}",
        headers=admin_headers,
        json={**material_payload, "show_in_client_portal": True},
    )
    assert published.status_code == 200
    portal = client.get("/api/v1/portal/training-materials", headers=portal_headers)
    assert portal.status_code == 200
    assert [row["title"] for row in portal.json()] == ["Portal safe training"]
    assert [resource["url"] for resource in portal.json()[0]["resources"]] == [
        "https://docs.example.com/guide"
    ]
    assert client.get("/api/v1/portal/training-materials", headers=admin_headers).status_code == 403
    audit = database.scalar(select(AuditLog).where(AuditLog.action == "PORTAL_PUBLICATION_CHANGED"))
    assert audit is not None


def test_portal_client_isolation_and_safe_comments(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    own_client = create_client_record(client, admin_headers, database, "PORTALOWN")
    other_client = create_client_record(client, admin_headers, database, "PORTALOTHER")
    create_portal_user(database, own_client)
    login = client.post(
        "/api/v1/auth/login",
        json={"login": "portal", "password": "PortalPassword!123"},
    )
    portal_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    ticket_type = database.scalar(select(TicketType).where(TicketType.code == "INCIDENT"))
    assert ticket_type is not None
    own_ticket = client.post(
        "/api/v1/portal/tickets",
        headers=portal_headers,
        json={
            "ticket_type_id": ticket_type.id,
            "client_id": own_client,
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "priority": "P2",
            "creation_method": "PORTAL",
            "subject": "Portal ticket subject",
            "description": "Portal user reports a reproducible service problem.",
        },
    )
    assert own_ticket.status_code == 201, own_ticket.text
    assert database.get(Ticket, own_ticket.json()["id"]).source_channel == "CLIENT_PORTAL"
    cross_create = client.post(
        "/api/v1/portal/tickets",
        headers=portal_headers,
        json={
            "ticket_type_id": ticket_type.id,
            "client_id": other_client,
            "impact": "LOW",
            "urgency": "LOW",
            "priority": "P1",
            "subject": "Unauthorized ticket",
            "description": "This request targets another client organization.",
        },
    )
    assert cross_create.status_code == 403
    cross_entitlement = client.get(
        "/api/v1/entitlements/check",
        headers=portal_headers,
        params={"client_id": other_client, "ticket_type_id": ticket_type.id},
    )
    assert cross_entitlement.status_code == 404
    other_ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type.id,
            "client_id": other_client,
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Other client ticket",
            "description": "This ticket must not be visible to the portal user.",
        },
    )
    assert other_ticket.status_code == 201
    internal_own_ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type.id,
            "client_id": own_client,
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Employee-created client ticket",
            "description": "This client ticket was logged internally and must appear in the portal.",
        },
    )
    assert internal_own_ticket.status_code == 201, internal_own_ticket.text
    portal_list = client.get("/api/v1/portal/tickets", headers=portal_headers)
    assert portal_list.status_code == 200, portal_list.text
    assert {item["id"] for item in portal_list.json()} == {
        own_ticket.json()["id"],
        internal_own_ticket.json()["id"],
    }
    stored_ticket = database.get(Ticket, own_ticket.json()["id"])
    assert stored_ticket is not None
    stored_ticket.created_at = datetime(2026, 8, 25, 22, 30, tzinfo=UTC)
    database.commit()
    local_date = client.get(
        "/api/v1/portal/tickets",
        headers=portal_headers,
        params={
            "date_from": "2026-08-26",
            "date_to": "2026-08-26",
            "timezone_offset_minutes": 180,
        },
    )
    assert local_date.status_code == 200, local_date.text
    assert own_ticket.json()["id"] in {item["id"] for item in local_date.json()}
    own_number = own_ticket.json()["ticket_number"]
    by_full_number = client.get(
        "/api/v1/portal/tickets",
        headers=portal_headers,
        params={"ticket_number": f"  {own_number.lower()}  "},
    )
    assert [item["id"] for item in by_full_number.json()] == [own_ticket.json()["id"]]
    numeric_portion = own_number.rsplit("-", 1)[-1]
    by_numeric_portion = client.get(
        "/api/v1/portal/tickets",
        headers=portal_headers,
        params={"ticket_number": numeric_portion},
    )
    assert own_ticket.json()["id"] in {item["id"] for item in by_numeric_portion.json()}
    hidden_number = other_ticket.json()["ticket_number"]
    hidden_search = client.get(
        "/api/v1/portal/tickets",
        headers=portal_headers,
        params={"ticket_number": hidden_number},
    )
    assert hidden_search.status_code == 200
    assert hidden_search.json() == []
    internal_number_search = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"ticket_number": hidden_number.lower()},
    )
    assert [item["id"] for item in internal_number_search.json()] == [other_ticket.json()["id"]]
    internal_detail = client.get(
        f"/api/v1/portal/tickets/{internal_own_ticket.json()['id']}",
        headers=portal_headers,
    )
    assert internal_detail.status_code == 200, internal_detail.text
    guessed = client.get(
        f"/api/v1/portal/tickets/{other_ticket.json()['id']}",
        headers=portal_headers,
    )
    assert guessed.status_code == 403
    guessed_attachments = client.get(
        f"/api/v1/tickets/{other_ticket.json()['id']}/attachments",
        headers=portal_headers,
    )
    assert guessed_attachments.status_code == 403
    contracts = client.get("/api/v1/contracts", headers=portal_headers)
    assert contracts.status_code == 403
    internal = client.post(
        f"/api/v1/tickets/{own_ticket.json()['id']}/comments",
        headers=admin_headers,
        json={"body": "Internal diagnostic details.", "is_internal": True},
    )
    assert internal.status_code == 201
    comments = client.get(
        f"/api/v1/portal/tickets/{own_ticket.json()['id']}/comments",
        headers=portal_headers,
    )
    assert comments.status_code == 200
    assert comments.json() == []


def test_portal_can_confirm_resolved_ticket_atomically(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_client_record(client, admin_headers, database, "PORTALCONFIRM")
    create_portal_user(database, client_id)
    login = client.post(
        "/api/v1/auth/login",
        json={"login": "portal", "password": "PortalPassword!123"},
    )
    portal_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    ticket_type = database.scalar(select(TicketType).where(TicketType.code == "INCIDENT"))
    assert ticket_type is not None
    created = client.post(
        "/api/v1/portal/tickets",
        headers=portal_headers,
        json={
            "ticket_type_id": ticket_type.id,
            "client_id": client_id,
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "priority": "P2",
            "subject": "Confirm a completed portal incident",
            "description": "The customer will confirm this incident after engineering resolves it.",
        },
    )
    assert created.status_code == 201, created.text
    ticket = created.json()
    started = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        headers=admin_headers,
        json={"to_status_code": "IN_PROGRESS", "version": ticket["version"]},
    )
    assert started.status_code == 200, started.text
    resolved = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "RESOLVED",
            "version": started.json()["version"],
            "resolution_summary": "The service was restored and verified.",
            "root_cause_summary": "A stale application configuration caused the interruption.",
        },
    )
    assert resolved.status_code == 200, resolved.text
    confirmed = client.post(
        f"/api/v1/portal/tickets/{ticket['id']}/confirm",
        headers=portal_headers,
        json={"version": resolved.json()["version"], "reason": "Service is working now."},
    )
    assert confirmed.status_code == 200, confirmed.text
    closed_status_id = database.scalar(select(TicketStatus.id).where(TicketStatus.code == "CLOSED"))
    assert confirmed.json()["status_id"] == closed_status_id
    histories = list(
        database.scalars(
            select(TicketStatusHistory)
            .where(TicketStatusHistory.ticket_id == ticket["id"])
            .order_by(TicketStatusHistory.id)
        )
    )
    status_codes = dict(database.execute(select(TicketStatus.id, TicketStatus.code)).all())
    assert [status_codes[item.to_status_id] for item in histories[-2:]] == [
        "CLIENT_CONFIRMATION",
        "CLOSED",
    ]
    assert [item.source for item in histories[-2:]] == ["CLIENT_PORTAL", "CLIENT_PORTAL"]


def test_portal_catalog_uses_contract_coverage_and_exclusions(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    own_client = create_client_record(client, admin_headers, database, "PORTALCATALOG")
    contract_owner = create_client_record(client, admin_headers, database, "SHAREDOWNER")
    create_portal_user(database, own_client)
    login = client.post(
        "/api/v1/auth/login",
        json={"login": "portal", "password": "PortalPassword!123"},
    )
    portal_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    included_product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "PORTAL-IN", "name": "Portal Included Product"},
    ).json()
    excluded_product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "PORTAL-OUT", "name": "Portal Excluded Product"},
    ).json()
    shared_product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "PORTAL-SHARED-PRODUCT", "name": "Portal Shared Product"},
    ).json()
    shared_module = client.post(
        f"/api/v1/products/{shared_product['id']}/modules",
        headers=admin_headers,
        json={"code": "PORTAL-SHARED-MODULE", "name": "Portal Shared Module"},
    ).json()
    shared_service = client.post(
        "/api/v1/services",
        headers=admin_headers,
        json={"code": "PORTAL-SVC", "name": "Portal Shared Service"},
    ).json()
    calendar_id = database.scalar(select(BusinessCalendar.id))
    shared = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "PORTAL-SHARED",
            "client_id": contract_owner,
            "linked_client_ids": [contract_owner, own_client],
            "is_shared_default": True,
            "name": "Linked portal shared contract",
            "start_date": str(date.today() - timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=30)),
            "calendar_id": calendar_id,
        },
    ).json()
    shared_coverage = client.post(
        f"/api/v1/contracts/{shared['id']}/coverage",
        headers=admin_headers,
        json={
            "product_id": excluded_product["id"],
            "service_id": shared_service["id"],
            "is_covered": True,
        },
    )
    assert shared_coverage.status_code == 201, shared_coverage.text
    shared_product_coverage = client.post(
        f"/api/v1/contracts/{shared['id']}/coverage",
        headers=admin_headers,
        json={
            "product_id": shared_product["id"],
            "product_module_id": shared_module["id"],
            "is_covered": True,
        },
    )
    assert shared_product_coverage.status_code == 201, shared_product_coverage.text
    specific = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "PORTAL-SPECIFIC",
            "client_id": own_client,
            "name": "Portal customer-specific contract",
            "start_date": str(date.today() - timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=30)),
            "calendar_id": calendar_id,
        },
    ).json()
    include = client.post(
        f"/api/v1/contracts/{specific['id']}/coverage",
        headers=admin_headers,
        json={"product_id": included_product["id"], "is_covered": True},
    )
    exclude = client.post(
        f"/api/v1/contracts/{specific['id']}/coverage",
        headers=admin_headers,
        json={"product_id": excluded_product["id"], "is_covered": False},
    )
    assert include.status_code == 201, include.text
    assert exclude.status_code == 201, exclude.text
    catalog = client.get("/api/v1/portal/catalog", headers=portal_headers)
    assert catalog.status_code == 200, catalog.text
    assert {item["id"] for item in catalog.json()["products"]} == {
        included_product["id"],
        shared_product["id"],
    }
    assert {item["id"] for item in catalog.json()["modules"]} == {
        shared_module["id"],
    }
    # The customer-specific exclusion still wins for the paired product, while
    # the service remains discoverable through the linked shared-default rule.
    assert {item["id"] for item in catalog.json()["services"]} == {shared_service["id"]}


def test_portal_catalog_honors_client_scoped_bulk_assignments(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    portal_client = create_client_record(client, admin_headers, database, "PORTALSCOPE")
    other_client = create_client_record(client, admin_headers, database, "PORTALOTHER")
    create_portal_user(database, portal_client)
    login = client.post(
        "/api/v1/auth/login",
        json={"login": "portal", "password": "PortalPassword!123"},
    )
    portal_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    visible_product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "PORTAL-SCOPE-IN", "name": "Portal Scoped Product"},
    ).json()
    hidden_product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "PORTAL-SCOPE-OUT", "name": "Other Client Product"},
    ).json()
    shared_service = client.post(
        "/api/v1/services",
        headers=admin_headers,
        json={"code": "PORTAL-SCOPE-SVC", "name": "All Client Service"},
    ).json()
    calendar_id = database.scalar(select(BusinessCalendar.id))
    contract = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "PORTAL-SCOPED-ALL",
            "client_id": portal_client,
            "name": "Portal scoped all-client contract",
            "applies_to_all_clients": True,
            "is_shared_default": True,
            "start_date": str(date.today() - timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=30)),
            "calendar_id": calendar_id,
            "included_request_limit": 1,
        },
    )
    assert contract.status_code == 201, contract.text
    contract_id = contract.json()["id"]
    for product_id, client_id in (
        (visible_product["id"], portal_client),
        (hidden_product["id"], other_client),
    ):
        assignment = client.post(
            f"/api/v1/contracts/{contract_id}/assignments/bulk",
            headers=admin_headers,
            json={
                "products": [{"product_id": product_id, "module_ids": []}],
                "applies_to_all_clients": False,
                "client_ids": [client_id],
            },
        )
        assert assignment.status_code == 200, assignment.text
    all_clients_service = client.post(
        f"/api/v1/contracts/{contract_id}/assignments/bulk",
        headers=admin_headers,
        json={
            "service_ids": [shared_service["id"]],
            "applies_to_all_clients": True,
        },
    )
    assert all_clients_service.status_code == 200, all_clients_service.text

    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    used_allowance = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": portal_client,
            "product_id": visible_product["id"],
            "impact": "LOW",
            "urgency": "LOW",
            "subject": "Use the shared contract allowance",
            "description": "This covered request exhausts the shared contract quota.",
        },
    )
    assert used_allowance.status_code == 201, used_allowance.text
    assert used_allowance.json()["entitlement_status"] == "COVERED"

    catalog = client.get("/api/v1/portal/catalog", headers=portal_headers)
    assert catalog.status_code == 200, catalog.text
    assert {item["id"] for item in catalog.json()["products"]} == {
        visible_product["id"],
    }
    assert {item["id"] for item in catalog.json()["services"]} == {shared_service["id"]}
    legacy_ticket = database.get(Ticket, used_allowance.json()["id"])
    assert legacy_ticket is not None
    legacy_ticket.contract_id = None
    database.commit()
    ticket_date = legacy_ticket.created_at.replace(tzinfo=UTC).date().isoformat()
    insights = client.get(
        "/api/v1/portal/contract-insights",
        headers=portal_headers,
        params={"date_from": ticket_date, "date_to": ticket_date},
    )
    assert insights.status_code == 200, insights.text
    assert insights.json()["contracts"][0]["number"] == "PORTAL-SCOPED-ALL"
    assert insights.json()["coverage"]["products"] == ["Portal Scoped Product"]
    assert insights.json()["coverage"]["services"] == ["All Client Service"]
    assert insights.json()["metrics"]["total_requests"] == 1
    assert insights.json()["metrics"]["incident_count"] == 1
    # NEW/RESOLVED/open tickets are not "pending"; only PENDING_* workflow states count.
    assert insights.json()["metrics"]["pending_count"] == 0
    assert insights.json()["metrics"]["total_working_hours"] >= 0
