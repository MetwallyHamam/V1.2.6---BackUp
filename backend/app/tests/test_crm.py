from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.clients.models import ClientStatus, Environment
from app.modules.contracts.models import BusinessCalendar, Contract
from app.modules.iam.models import AuditLog, Permission, ProfilePermission, User, UserProfile
from app.modules.iam.service import effective_permissions
from app.modules.tickets.models import Ticket, TicketType


def test_client_human_text_round_trips_arabic(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    created = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={
            "code": "ARABIC-CLIENT",
            "name": "عميل جديد",
            "address": "القاهرة الجديدة",
            "notes": "ملاحظات دعم باللغة العربية",
            "status_id": status_id,
        },
    )
    assert created.status_code == 201, created.text
    client_id = created.json()["id"]
    assert created.json()["name"] == "عميل جديد"
    updated = client.patch(
        f"/api/v1/clients/{client_id}",
        headers=admin_headers,
        json={"name": "عميل جديد محدث"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "عميل جديد محدث"
    loaded = client.get(f"/api/v1/clients/{client_id}", headers=admin_headers)
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["name"] == "عميل جديد محدث"
    assert loaded.json()["address"] == "القاهرة الجديدة"
    assert loaded.json()["notes"] == "ملاحظات دعم باللغة العربية"


def test_password_reveal_audits_click_and_client_delete_cascades(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    created = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "PURGE", "name": "Purge Client", "status_id": status_id},
    )
    assert created.status_code == 201, created.text
    client_id = created.json()["id"]
    access = client.post(
        f"/api/v1/clients/{client_id}/access",
        headers=admin_headers,
        json={"access_type": "VPN", "label": "Main VPN", "password": "Secret123!"},
    )
    assert access.status_code == 201, access.text
    revealed = client.post(
        f"/api/v1/clients/{client_id}/access/{access.json()['id']}/reveal",
        headers=admin_headers,
        json={},
    )
    assert revealed.status_code == 200, revealed.text
    assert revealed.json()["password"] == "Secret123!"
    assert (
        database.scalar(
            select(AuditLog.id).where(
                AuditLog.action == "client_access.password_revealed",
                AuditLog.actor_user_id.is_not(None),
            )
        )
        is not None
    )

    calendar_id = database.scalar(select(BusinessCalendar.id))
    contract = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "PURGE-001",
            "client_id": client_id,
            "name": "Purge Contract",
            "start_date": str(date.today() - timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=30)),
            "calendar_id": calendar_id,
        },
    )
    assert contract.status_code == 201, contract.text
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": client_id,
            "contract_id": contract.json()["id"],
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "Client purge ticket",
            "description": "This ticket is intentionally removed with its owning client.",
        },
    )
    assert ticket.status_code == 201, ticket.text

    removed = client.delete(f"/api/v1/clients/{client_id}", headers=admin_headers)
    assert removed.status_code == 204, removed.text
    assert database.get(Ticket, ticket.json()["id"]) is None
    assert database.get(Contract, contract.json()["id"]) is None
    assert client.get(f"/api/v1/clients/{client_id}", headers=admin_headers).status_code == 404
    assert (
        database.scalar(
            select(AuditLog.id).where(
                AuditLog.entity_type == "Client",
                AuditLog.entity_id == str(client_id),
                AuditLog.action == "client.deleted",
            )
        )
        is not None
    )


def test_crm_catalogs_are_seeded(database: Session) -> None:
    statuses = set(database.scalars(select(ClientStatus.code)))
    environments = set(database.scalars(select(Environment.code)))
    assert statuses == {
        "PROSPECT",
        "IMPLEMENTATION",
        "ACTIVE",
        "ON_HOLD",
        "SUSPENDED",
        "EXPIRED_CONTRACT",
        "TERMINATED",
    }
    assert environments == {"PRODUCTION", "UAT", "DR", "TRAINING", "TEST"}


def test_ticket_user_can_read_environment_catalog_without_installation_permission(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    admin = database.scalar(select(User).where(User.username == "admin"))
    installation_read_id = database.scalar(
        select(Permission.id).where(Permission.code == "installation.read")
    )
    assert admin is not None and installation_read_id is not None
    profile_ids = select(UserProfile.profile_id).where(UserProfile.user_id == admin.id)
    database.execute(
        delete(ProfilePermission).where(
            ProfilePermission.profile_id.in_(profile_ids),
            ProfilePermission.permission_id == installation_read_id,
        )
    )
    database.commit()
    permissions = set(effective_permissions(database, admin).permissions)
    assert "installation.read" not in permissions
    assert "ticket.create" in permissions

    response = client.get("/api/v1/environments", headers=admin_headers)
    assert response.status_code == 200, response.text
    assert {item["code"] for item in response.json()} == {
        "PRODUCTION",
        "UAT",
        "DR",
        "TRAINING",
        "TEST",
    }


def test_client_branch_and_contact_lifecycle(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    created = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={
            "code": "ALFA",
            "name": "Alfa Scan",
            "status_id": status_id,
            "timezone": "Africa/Cairo",
            "is_active": True,
        },
    )
    assert created.status_code == 201, created.text
    client_id = created.json()["id"]
    duplicate = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={
            "code": "ALFA",
            "name": "Duplicate",
            "status_id": status_id,
        },
    )
    assert duplicate.status_code == 409
    branch = client.post(
        f"/api/v1/clients/{client_id}/branches",
        headers=admin_headers,
        json={"code": "CAIRO", "name": "Cairo Branch"},
    )
    assert branch.status_code == 201, branch.text
    automatic_branch = client.post(
        f"/api/v1/clients/{client_id}/branches",
        headers=admin_headers,
        json={"name": "Automatically Numbered Branch"},
    )
    assert automatic_branch.status_code == 201, automatic_branch.text
    assert automatic_branch.json()["code"].startswith("BRA-")
    country = client.post(
        "/api/v1/countries",
        headers=admin_headers,
        json={"name": "Location Test Country", "city_name": "Location Test City"},
    )
    assert country.status_code == 201, country.text
    location = client.post(
        f"/api/v1/clients/{client_id}/locations",
        headers=admin_headers,
        json={"country_id": country.json()["id"], "name": "Automatically Numbered Location"},
    )
    assert location.status_code == 201, location.text
    assert location.json()["code"].startswith("LOC-")
    updated_branch = client.patch(
        f"/api/v1/clients/{client_id}/branches/{branch.json()['id']}",
        headers=admin_headers,
        json={
            "name": "Cairo Support Site",
            "timezone": "Africa/Cairo",
            "address": "New Cairo",
            "is_active": False,
        },
    )
    assert updated_branch.status_code == 200, updated_branch.text
    assert updated_branch.json()["name"] == "Cairo Support Site"
    assert updated_branch.json()["address"] == "New Cairo"
    assert updated_branch.json()["is_active"] is False
    contact = client.post(
        "/api/v1/contacts",
        headers=admin_headers,
        json={
            "client_id": client_id,
            "branch_id": branch.json()["id"],
            "full_name": "Primary Contact",
            "email": "contact@alfa.example",
            "is_primary": True,
        },
    )
    assert contact.status_code == 201, contact.text
    updated_contact = client.patch(
        f"/api/v1/contacts/{contact.json()['id']}",
        headers=admin_headers,
        json={"job_title": "IT Manager", "is_primary": False, "is_active": False},
    )
    assert updated_contact.status_code == 200, updated_contact.text
    assert updated_contact.json()["job_title"] == "IT Manager"
    assert updated_contact.json()["is_active"] is False
    invalid_branch = client.patch(
        f"/api/v1/contacts/{contact.json()['id']}",
        headers=admin_headers,
        json={"client_id": client_id + 999, "branch_id": branch.json()["id"]},
    )
    assert invalid_branch.status_code == 404
    listing = client.get("/api/v1/clients?search=Alfa", headers=admin_headers)
    assert listing.status_code == 200
    assert [item["code"] for item in listing.json()] == ["ALFA"]


def test_crm_requires_permission(client: TestClient) -> None:
    assert client.get("/api/v1/clients").status_code == 401


def test_existing_contact_can_be_searched_and_linked_to_another_client(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    first = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "SHARED-A", "name": "Shared Caller A", "status_id": status_id},
    )
    second = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "SHARED-B", "name": "Shared Caller B", "status_id": status_id},
    )
    assert first.status_code == 201 and second.status_code == 201
    contact = client.post(
        "/api/v1/contacts",
        headers=admin_headers,
        json={
            "client_id": first.json()["id"],
            "full_name": "Shared Hospital Consultant",
            "phone_number": "+201234567890",
        },
    )
    assert contact.status_code == 201, contact.text

    search = client.get(
        "/api/v1/contacts/search-existing",
        headers=admin_headers,
        params={"client_id": second.json()["id"], "query": "Consultant"},
    )
    assert search.status_code == 200, search.text
    assert [item["id"] for item in search.json()] == [contact.json()["id"]]
    linked = client.post(
        f"/api/v1/clients/{second.json()['id']}/contacts/link",
        headers=admin_headers,
        json={"contact_id": contact.json()["id"]},
    )
    assert linked.status_code == 200, linked.text

    listing = client.get(
        "/api/v1/contacts", headers=admin_headers, params={"client_id": second.json()["id"]}
    )
    assert listing.status_code == 200
    assert contact.json()["id"] in {item["id"] for item in listing.json()}
    assert (
        client.get(
            "/api/v1/contacts/search-existing",
            headers=admin_headers,
            params={"client_id": second.json()["id"], "query": "Consultant"},
        ).json()
        == []
    )
    assert (
        database.scalar(select(AuditLog.id).where(AuditLog.action == "contact.client_linked"))
        is not None
    )


def test_status_and_environment_rules_can_be_managed(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    status = client.post(
        "/api/v1/client-statuses",
        headers=admin_headers,
        json={
            "code": "MAINTENANCE",
            "name": "Maintenance",
            "portal_allowed": True,
            "ticket_creation_allowed": False,
        },
    )
    assert status.status_code == 201, status.text
    updated_status = client.patch(
        f"/api/v1/client-statuses/{status.json()['id']}",
        headers=admin_headers,
        json={"ticket_creation_allowed": True, "is_active": False},
    )
    assert updated_status.status_code == 200, updated_status.text
    assert updated_status.json()["ticket_creation_allowed"] is True
    environment = client.post(
        "/api/v1/environments",
        headers=admin_headers,
        json={"code": "STAGING", "name": "Staging", "is_production": False},
    )
    assert environment.status_code == 201, environment.text
    updated_environment = client.patch(
        f"/api/v1/environments/{environment.json()['id']}",
        headers=admin_headers,
        json={"name": "Pre-production", "is_production": True},
    )
    assert updated_environment.status_code == 200, updated_environment.text
    assert updated_environment.json()["is_production"] is True


def test_ticket_categories_and_subcategories_can_be_managed_and_audited(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    category = client.post(
        "/api/v1/ticket-categories",
        headers=admin_headers,
        json={"code": "DATABASE", "name": "Database", "description": "Database issues"},
    )
    assert category.status_code == 201, category.text
    category_id = category.json()["id"]
    subcategory = client.post(
        f"/api/v1/ticket-categories/{category_id}/subcategories",
        headers=admin_headers,
        json={"code": "PERFORMANCE", "name": "Performance"},
    )
    assert subcategory.status_code == 201, subcategory.text
    updated = client.patch(
        f"/api/v1/ticket-categories/{category_id}/subcategories/{subcategory.json()['id']}",
        headers=admin_headers,
        json={"name": "Query Performance", "is_active": False},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Query Performance"
    assert updated.json()["is_active"] is False
    listed = client.get(
        f"/api/v1/ticket-categories/{category_id}/subcategories",
        headers=admin_headers,
    )
    assert [item["id"] for item in listed.json()] == [subcategory.json()["id"]]
    actions = set(
        database.scalars(
            select(AuditLog.action).where(
                AuditLog.entity_type.in_(["TicketCategory", "TicketSubcategory"])
            )
        )
    )
    assert {
        "ticket_category.created",
        "ticket_subcategory.created",
        "ticket_subcategory.updated",
    } <= actions


def test_support_teams_can_be_assigned_skills(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    users = client.get("/api/v1/users?limit=200", headers=admin_headers)
    assert users.status_code == 200, users.text
    admin_user_id = next(user["id"] for user in users.json() if user["username"] == "admin")
    skill = client.post(
        "/api/v1/skills",
        headers=admin_headers,
        json={"code": "PACS", "name": "PACS Support", "description": "PACS expertise"},
    )
    assert skill.status_code == 201, skill.text
    team = client.post(
        "/api/v1/support-teams",
        headers=admin_headers,
        json={
            "code": "L2_PACS",
            "name": "L2 PACS",
            "skill_ids": [skill.json()["id"]],
            "leader_user_id": admin_user_id,
            "member_user_ids": [admin_user_id],
        },
    )
    assert team.status_code == 201, team.text
    assert team.json()["skill_ids"] == [skill.json()["id"]]
    assert team.json()["leader_user_id"] == admin_user_id
    assert team.json()["member_user_ids"] == [admin_user_id]
    updated = client.patch(
        f"/api/v1/support-teams/{team.json()['id']}",
        headers=admin_headers,
        json={
            "name": "Advanced PACS",
            "skill_ids": [],
            "member_user_ids": [],
            "is_active": False,
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["skill_ids"] == []
    assert updated.json()["member_user_ids"] == []


def test_product_and_module_can_be_maintained(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "PACS", "name": "PACS", "description": "Imaging"},
    )
    assert product.status_code == 201, product.text
    product_id = product.json()["id"]
    module = client.post(
        f"/api/v1/products/{product_id}/modules",
        headers=admin_headers,
        json={"code": "VIEWER", "name": "Viewer"},
    )
    assert module.status_code == 201, module.text
    module_id = module.json()["id"]
    creation_actions = set(
        database.scalars(
            select(AuditLog.action).where(
                AuditLog.action.in_(["product.created", "product_module.created"])
            )
        )
    )
    assert creation_actions == {"product.created", "product_module.created"}

    updated_product = client.patch(
        f"/api/v1/products/{product_id}",
        headers=admin_headers,
        json={"name": "Enterprise PACS", "is_active": False},
    )
    assert updated_product.status_code == 200, updated_product.text
    assert updated_product.json()["name"] == "Enterprise PACS"
    assert updated_product.json()["is_active"] is False

    updated_module = client.patch(
        f"/api/v1/products/{product_id}/modules/{module_id}",
        headers=admin_headers,
        json={"name": "Diagnostic Viewer", "is_active": False},
    )
    assert updated_module.status_code == 200, updated_module.text
    assert updated_module.json()["is_active"] is False
    active_modules = client.get(f"/api/v1/products/{product_id}/modules", headers=admin_headers)
    assert active_modules.json() == []
    all_modules = client.get(
        f"/api/v1/products/{product_id}/modules?include_inactive=true",
        headers=admin_headers,
    )
    assert [item["name"] for item in all_modules.json()] == ["Diagnostic Viewer"]


def test_service_and_vendor_catalogs_can_be_maintained(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    service = client.post(
        "/api/v1/services",
        headers=admin_headers,
        json={"code": "REMOTE", "name": "Remote Support", "description": "Remote assistance"},
    )
    assert service.status_code == 201, service.text
    assert service.json()["description"] == "Remote assistance"
    updated_service = client.patch(
        f"/api/v1/services/{service.json()['id']}",
        headers=admin_headers,
        json={"name": "Remote Technical Support", "is_active": False},
    )
    assert updated_service.status_code == 200, updated_service.text
    assert updated_service.json()["is_active"] is False

    vendor = client.post(
        "/api/v1/vendors",
        headers=admin_headers,
        json={
            "code": "ACME",
            "name": "Acme Systems",
            "contact_name": "Support Desk",
            "email": "support@acme.example",
            "phone_number": "+20 100 000 0000",
        },
    )
    assert vendor.status_code == 201, vendor.text
    assert vendor.json()["contact_name"] == "Support Desk"
    updated_vendor = client.patch(
        f"/api/v1/vendors/{vendor.json()['id']}",
        headers=admin_headers,
        json={"contact_name": "Escalation Desk", "is_active": False},
    )
    assert updated_vendor.status_code == 200, updated_vendor.text
    assert updated_vendor.json()["contact_name"] == "Escalation Desk"


def test_only_one_service_is_the_default_resolution_service(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    first = client.post(
        "/api/v1/services",
        headers=admin_headers,
        json={"name": "Support Activity", "is_default_resolution_service": True},
    )
    assert first.status_code == 201, first.text
    assert first.json()["is_default_resolution_service"] is True
    second = client.post(
        "/api/v1/services",
        headers=admin_headers,
        json={"name": "On-site Support", "is_default_resolution_service": True},
    )
    assert second.status_code == 201, second.text
    services = client.get("/api/v1/services", headers=admin_headers).json()
    defaults = [item for item in services if item["is_default_resolution_service"]]
    assert [item["id"] for item in defaults] == [second.json()["id"]]


def test_client_installation_can_be_created_and_updated(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    environment_id = database.scalar(select(Environment.id).where(Environment.code == "PRODUCTION"))
    customer = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "INSTCLIENT", "name": "Installation Client", "status_id": status_id},
    )
    product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "RIS", "name": "RIS"},
    )
    module = client.post(
        f"/api/v1/products/{product.json()['id']}/modules",
        headers=admin_headers,
        json={"code": "SCHED", "name": "Scheduling"},
    )
    second_product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "PACS-INST", "name": "PACS Installation Product"},
    )
    created = client.post(
        "/api/v1/installations",
        headers=admin_headers,
        json={
            "client_id": customer.json()["id"],
            "product_id": product.json()["id"],
            "product_module_id": module.json()["id"],
            "environment_id": environment_id,
            "installation_name": "Primary RIS",
            "version": "1.0",
            "server_name": "RIS-SRV",
            "components": [
                {"product_id": product.json()["id"], "product_module_id": module.json()["id"]},
                {"product_id": second_product.json()["id"], "product_module_id": None},
            ],
        },
    )
    assert created.status_code == 201, created.text
    assert len(created.json()["components"]) == 2
    updated = client.patch(
        f"/api/v1/installations/{created.json()['id']}",
        headers=admin_headers,
        json={
            "version": "1.1",
            "support_owner": "L2 Team",
            "is_active": False,
            "components": [{"product_id": second_product.json()["id"]}],
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["version"] == "1.1"
    assert updated.json()["is_active"] is False
    assert len(updated.json()["components"]) == 1
    assert updated.json()["product_id"] == second_product.json()["id"]


def test_service_can_be_linked_to_multiple_product_modules(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    product = client.post(
        "/api/v1/products", headers=admin_headers, json={"name": "Linked service product"}
    )
    assert product.status_code == 201, product.text
    modules = [
        client.post(
            f"/api/v1/products/{product.json()['id']}/modules",
            headers=admin_headers,
            json={"name": name},
        )
        for name in ("Module One", "Module Two")
    ]
    assert all(response.status_code == 201 for response in modules)
    module_ids = [response.json()["id"] for response in modules]
    service = client.post(
        "/api/v1/services",
        headers=admin_headers,
        json={"name": "Module-aware service", "module_ids": module_ids},
    )
    assert service.status_code == 201, service.text
    assert sorted(service.json()["module_ids"]) == sorted(module_ids)
    updated = client.patch(
        f"/api/v1/services/{service.json()['id']}",
        headers=admin_headers,
        json={"module_ids": [module_ids[1]]},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["module_ids"] == [module_ids[1]]
