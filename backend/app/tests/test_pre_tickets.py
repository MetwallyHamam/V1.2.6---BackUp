import json
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.modules.clients.models import (
    Client,
    ClientStatus,
    Contact,
    Product,
    ProductModule,
    ServiceCatalogItem,
)
from app.modules.configuration.models import FeaturePolicy
from app.modules.contracts.models import BusinessCalendar, Contract, ContractCoverage
from app.modules.entitlements.models import EntitlementApproval
from app.modules.iam.models import Effect, Permission, User, UserPermissionOverride
from app.modules.iam.security import hash_password
from app.modules.iam.service import effective_permissions
from app.modules.tickets.models import Ticket, TicketType


def enable_pre_tickets(database: Session, actor: User, ticket_type_id: int) -> None:
    database.add(FeaturePolicy(
        feature_key="engineer_pre_ticket", scope_type="SYSTEM", scope_key="SYSTEM", mode="ENFORCED",
        configuration_json=json.dumps({"ticket_type_id": ticket_type_id, "priority_mapping": {
            "P1": {"impact": "CRITICAL", "urgency": "CRITICAL"},
            "P2": {"impact": "HIGH", "urgency": "HIGH"},
            "P3": {"impact": "MEDIUM", "urgency": "MEDIUM"},
            "P4": {"impact": "LOW", "urgency": "LOW"},
        }}),
        effective_from=server_now() - timedelta(minutes=1), version=1,
        created_by_user_id=actor.id, updated_by_user_id=actor.id,
    ))
    database.commit()


def test_pre_ticket_form_fields_are_visible_and_mandatory_by_default(client, admin_headers) -> None:
    response = client.get("/api/v1/system/pre-ticket-form-fields", headers=admin_headers)
    assert response.status_code == 200, response.text
    fields = response.json()
    assert [item["field_key"] for item in fields] == [
        "pre_ticket.client_id",
        "pre_ticket.requester_contact_id",
        "pre_ticket.product_id",
        "pre_ticket.product_module_id",
        "pre_ticket.service_id",
    ]
    assert all(item["is_visible"] and item["is_required"] for item in fields)
    assert all(not item["can_hide"] and item["can_require"] for item in fields)


def test_pre_ticket_create_permission_does_not_require_ticket_create(
    client, database: Session
) -> None:
    actor = database.scalar(select(User).where(User.username == "admin"))
    status = database.scalar(select(ClientStatus).where(ClientStatus.code == "ACTIVE"))
    ticket_type_id = database.scalar(
        select(TicketType.id).where(TicketType.code == "INCIDENT")
    )
    permissions = {
        item.code: item
        for item in database.scalars(
            select(Permission).where(
                Permission.code.in_(
                    ["ticket.pre_ticket.create", "ticket.pre_ticket.view.own"]
                )
            )
        )
    }
    assert actor and status and ticket_type_id and len(permissions) == 2
    user = User(
        full_name="Pre-Ticket Only Engineer",
        username="pre-ticket-only",
        username_normalized="pre-ticket-only",
        email="pre-ticket-only@example.com",
        email_normalized="pre-ticket-only@example.com",
        password_hash=hash_password("PreTicketOnlyPassword!123"),
        is_active=True,
        require_password_change=False,
    )
    database.add(user)
    database.flush()
    database.add_all(
        [
            UserPermissionOverride(
                user_id=user.id,
                permission_id=permission.id,
                effect=Effect.ALLOW,
                reason="Pre-Ticket permission isolation test",
                created_by_user_id=actor.id,
            )
            for permission in permissions.values()
        ]
    )
    client_row = Client(
        code="PRE-ONLY-CLIENT",
        name="Pre-Ticket Only Client",
        status_id=status.id,
    )
    database.add(client_row)
    database.flush()
    contact = Contact(
        client_id=client_row.id,
        full_name="Pre-Ticket Only Caller",
        email="pre-ticket-only-caller@example.com",
    )
    product = Product(code="PRE-ONLY-PRODUCT", name="Pre-Ticket Only Product")
    database.add_all([contact, product])
    database.flush()
    module = ProductModule(
        product_id=product.id,
        code="PRE-ONLY-MODULE",
        name="Pre-Ticket Only Module",
    )
    service = ServiceCatalogItem(
        code="PRE-ONLY-SERVICE", name="Pre-Ticket Only Service"
    )
    service.modules.append(module)
    database.add_all([module, service])
    database.commit()
    enable_pre_tickets(database, actor, ticket_type_id)

    granted = set(effective_permissions(database, user).permissions)
    assert "ticket.pre_ticket.create" in granted
    assert "ticket.create" not in granted
    login = client.post(
        "/api/v1/auth/login",
        json={"login": user.username, "password": "PreTicketOnlyPassword!123"},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    options = client.get("/api/v1/clients/ticket-options", headers=headers)
    assert options.status_code == 200, options.text
    contacts = client.get(
        "/api/v1/contacts", params={"client_id": client_row.id}, headers=headers
    )
    assert contacts.status_code == 200, contacts.text
    catalog = client.get(
        "/api/v1/ticket-contract-catalog",
        params={"client_id": client_row.id},
        headers=headers,
    )
    assert catalog.status_code == 200, catalog.text

    created = client.post(
        "/api/v1/pre-tickets",
        headers=headers,
        json={
            "client_id": client_row.id,
            "requester_contact_id": contact.id,
            "product_id": product.id,
            "product_module_id": module.id,
            "service_id": service.id,
            "proposed_priority": "P3",
            "title": "Permission-isolated Pre-Ticket submission",
            "idempotency_key": "pre-ticket-permission-isolation-001",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["submitted_by_user_id"] == user.id
    official_ticket = client.post("/api/v1/tickets", headers=headers, json={})
    assert official_ticket.status_code == 403, official_ticket.text
    assert official_ticket.json()["error"]["details"]["required_permission"] == "ticket.create"


def test_pre_ticket_form_settings_allow_optional_fields_but_never_hide_them(
    client, admin_headers, database: Session
) -> None:
    updates = [
        {
            "field_key": key,
            "is_visible": False,
            "is_required": False,
            "default_value": None,
        }
        for key in (
            "pre_ticket.client_id",
            "pre_ticket.requester_contact_id",
            "pre_ticket.product_id",
            "pre_ticket.product_module_id",
            "pre_ticket.service_id",
        )
    ]
    updated = client.put(
        "/api/v1/system/pre-ticket-form-fields", headers=admin_headers, json=updates
    )
    assert updated.status_code == 200, updated.text
    assert all(item["is_visible"] and not item["is_required"] for item in updated.json())

    actor = database.scalar(select(User).where(User.username == "admin"))
    ticket_type_id = database.scalar(
        select(TicketType.id).where(TicketType.code == "INCIDENT")
    )
    assert actor and ticket_type_id
    enable_pre_tickets(database, actor, ticket_type_id)
    created = client.post(
        "/api/v1/pre-tickets",
        headers=admin_headers,
        json={
            "proposed_priority": "P3",
            "title": "Optional context pre ticket",
            "idempotency_key": "pre-ticket-optional-context-001",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["client_id"] is None

    client_status = database.scalar(select(ClientStatus).where(ClientStatus.code == "ACTIVE"))
    assert client_status
    client_row = Client(code="PRE-COMPLETE", name="Pre Ticket Completion", status_id=client_status.id)
    product = Product(code="PRE-COMPLETE-PRODUCT", name="Completion Product")
    database.add_all([client_row, product]); database.flush()
    contact = Contact(client_id=client_row.id, full_name="Completion Caller", email="completion@example.com")
    module = ProductModule(product_id=product.id, code="PRE-COMPLETE-MODULE", name="Completion Module")
    service = ServiceCatalogItem(code="PRE-COMPLETE-SERVICE", name="Completion Service")
    service.modules.append(module)
    database.add_all([contact, module, service]); database.commit()

    converted = client.post(
        f"/api/v1/pre-tickets/{created.json()['id']}/convert",
        headers=admin_headers,
        json={
            "expected_version": created.json()["version"],
            "conversion_idempotency_key": "pre-ticket-complete-context-001",
            "client_id": client_row.id,
            "requester_contact_id": contact.id,
            "product_id": product.id,
            "product_module_id": module.id,
            "service_id": service.id,
        },
    )
    assert converted.status_code == 200, converted.text
    completed = converted.json()
    assert completed["client_id"] == client_row.id
    assert completed["product_module_id"] == module.id
    ticket = database.get(Ticket, completed["resulting_ticket_id"])
    assert ticket and ticket.client_id == client_row.id
    assert ticket.product_module_id == module.id and ticket.service_id == service.id


def test_pre_ticket_submit_and_confirm_creates_one_self_assigned_ticket(client, admin_headers, database: Session) -> None:
    actor = database.scalar(select(User).where(User.username == "admin"))
    status = database.scalar(select(ClientStatus).where(ClientStatus.code == "ACTIVE"))
    assert actor and status
    client_row = Client(code="PRE-TEST", name="Pre Ticket Test", status_id=status.id)
    database.add(client_row); database.flush()
    contact = Contact(client_id=client_row.id, full_name="Pre Ticket Caller", email="pre-ticket@example.com")
    product = Product(code="PRE-PRODUCT", name="Pre Ticket Product")
    database.add_all([contact, product]); database.flush()
    module = ProductModule(product_id=product.id, code="PRE-MODULE", name="Pre Ticket Module")
    service = ServiceCatalogItem(code="PRE-SERVICE", name="Pre Ticket Service")
    service.modules.append(module)
    database.add_all([module, service]); database.flush()
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    assert ticket_type_id
    enable_pre_tickets(database, actor, ticket_type_id)
    payload = {"client_id": client_row.id, "requester_contact_id": contact.id, "product_id": product.id, "product_module_id": module.id, "service_id": service.id, "proposed_priority": "P3", "title": "Pre Ticket API confirmation", "idempotency_key": "pre-ticket-submit-001"}
    submitted = client.post("/api/v1/pre-tickets", headers=admin_headers, json=payload)
    assert submitted.status_code == 201, submitted.text
    created = submitted.json()
    assert created["status"] == "SUBMITTED"
    assert created["pre_ticket_number"].startswith("PRE-")
    repeated = client.post("/api/v1/pre-tickets", headers=admin_headers, json=payload)
    assert repeated.status_code == 201
    assert repeated.json()["id"] == created["id"]
    second = client.post("/api/v1/pre-tickets", headers=admin_headers, json={
        **payload,
        "title": "A second unconverted Pre Ticket",
        "idempotency_key": "pre-ticket-submit-002",
    })
    assert second.status_code == 201, second.text
    assert second.json()["id"] != created["id"]
    assert second.json()["resulting_ticket_id"] is None
    confirmed = client.post(f"/api/v1/pre-tickets/{created['id']}/confirm", headers=admin_headers, json={"expected_version": created["version"], "conversion_idempotency_key": "pre-ticket-confirm-001"})
    assert confirmed.status_code == 200, confirmed.text
    converted = confirmed.json()
    assert converted["status"] == "CONVERTED"
    ticket = database.get(Ticket, converted["resulting_ticket_id"])
    assert ticket and ticket.assigned_user_id == actor.id and ticket.source_channel == "ENGINEER_PRE_TICKET"


def test_uncovered_pre_ticket_requests_approval_only_when_converted(
    client, admin_headers, database: Session
) -> None:
    actor = database.scalar(select(User).where(User.username == "admin"))
    status = database.scalar(select(ClientStatus).where(ClientStatus.code == "ACTIVE"))
    calendar = database.scalar(select(BusinessCalendar))
    ticket_type_id = database.scalar(
        select(TicketType.id).where(TicketType.code == "INCIDENT")
    )
    assert actor and status and calendar and ticket_type_id
    client_row = Client(code="PRE-UNCOVERED", name="Pre-Ticket Uncovered", status_id=status.id)
    covered_product = Product(code="PRE-COVERED", name="Covered Product")
    uncovered_product = Product(code="PRE-UNCOVERED-PRODUCT", name="Uncovered Product")
    database.add_all([client_row, covered_product, uncovered_product])
    database.flush()
    contact = Contact(client_id=client_row.id, full_name="Uncovered Caller")
    module = ProductModule(
        product_id=uncovered_product.id,
        code="PRE-UNCOVERED-MODULE",
        name="Uncovered Module",
    )
    service = ServiceCatalogItem(
        code="PRE-UNCOVERED-SERVICE",
        name="Uncovered Service",
        is_default_resolution_service=True,
    )
    service.modules.append(module)
    contract = Contract(
        contract_number="PRE-UNCOVERED-CONTRACT",
        client_id=client_row.id,
        name="Restricted Coverage Contract",
        start_date=date.today() - timedelta(days=1),
        end_date=date.today() + timedelta(days=30),
        calendar_id=calendar.id,
        has_sla=False,
        ticket_catalog_visibility="CONTRACT_ONLY",
    )
    database.add_all([contact, module, service, contract])
    database.flush()
    database.add(
        ContractCoverage(contract_id=contract.id, product_id=covered_product.id, is_covered=True)
    )
    database.commit()
    enable_pre_tickets(database, actor, ticket_type_id)

    catalog = client.get(
        "/api/v1/ticket-contract-catalog",
        params={"client_id": client_row.id, "pre_ticket": True},
        headers=admin_headers,
    )
    assert catalog.status_code == 200, catalog.text
    product_row = next(
        item for item in catalog.json()["products"] if item["id"] == uncovered_product.id
    )
    assert product_row["covered"] is False
    service_row = next(item for item in catalog.json()["services"] if item["id"] == service.id)
    assert service_row["is_default_resolution_service"] is True

    submitted = client.post(
        "/api/v1/pre-tickets",
        headers=admin_headers,
        json={
            "client_id": client_row.id,
            "requester_contact_id": contact.id,
            "product_id": uncovered_product.id,
            "product_module_id": module.id,
            "service_id": service.id,
            "proposed_priority": "P3",
            "title": "Uncovered product requires conversion approval",
            "idempotency_key": "pre-ticket-uncovered-submit-001",
        },
    )
    assert submitted.status_code == 201, submitted.text
    assert database.scalar(select(EntitlementApproval)) is None

    convert_permission = database.scalar(
        select(Permission).where(
            Permission.code == "ticket.pre_ticket.convert_assign"
        )
    )
    assert convert_permission is not None
    converter = User(
        full_name="Dedicated Pre-Ticket Converter",
        username="pre-ticket-converter",
        username_normalized="pre-ticket-converter",
        email="pre-ticket-converter@example.com",
        email_normalized="pre-ticket-converter@example.com",
        password_hash=hash_password("PreTicketConverterPassword!123"),
        is_active=True,
        require_password_change=False,
    )
    database.add(converter)
    database.flush()
    database.add(
        UserPermissionOverride(
            user_id=converter.id,
            permission_id=convert_permission.id,
            effect=Effect.ALLOW,
            reason="Independent conversion permission regression",
            created_by_user_id=actor.id,
        )
    )
    database.commit()
    converter_permissions = set(effective_permissions(database, converter).permissions)
    assert "ticket.pre_ticket.convert_assign" in converter_permissions
    assert "ticket.create" not in converter_permissions
    assert "ticket.pre_ticket.queue.process" not in converter_permissions
    login = client.post(
        "/api/v1/auth/login",
        json={
            "login": converter.username,
            "password": "PreTicketConverterPassword!123",
        },
    )
    assert login.status_code == 200, login.text
    converter_headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }

    converted = client.post(
        f"/api/v1/pre-tickets/{submitted.json()['id']}/convert",
        headers=converter_headers,
        json={
            "expected_version": submitted.json()["version"],
            "conversion_idempotency_key": "pre-ticket-uncovered-convert-001",
        },
    )
    assert converted.status_code == 200, converted.text
    ticket = database.get(Ticket, converted.json()["resulting_ticket_id"])
    assert ticket and ticket.entitlement_status == "PENDING_APPROVAL"
    assert ticket.assigned_user_id is None
    approval = database.scalar(
        select(EntitlementApproval).where(EntitlementApproval.ticket_id == ticket.id)
    )
    assert approval is not None and approval.status == "PENDING"


def test_pre_ticket_call_center_information_cycle_and_conversion(client, admin_headers, database: Session) -> None:
    actor = database.scalar(select(User).where(User.username == "admin"))
    status = database.scalar(select(ClientStatus).where(ClientStatus.code == "ACTIVE"))
    assert actor and status
    client_row = Client(code="PRE-QUEUE", name="Pre Ticket Queue Test", status_id=status.id)
    database.add(client_row); database.flush()
    contact = Contact(client_id=client_row.id, full_name="Queue Caller", email="queue-pre-ticket@example.com")
    product = Product(code="PRE-QUEUE-PRODUCT", name="Queue Pre Ticket Product")
    database.add_all([contact, product]); database.flush()
    module = ProductModule(product_id=product.id, code="PRE-QUEUE-MODULE", name="Queue Module")
    service = ServiceCatalogItem(code="PRE-QUEUE-SERVICE", name="Queue Service")
    service.modules.append(module)
    database.add_all([module, service]); database.flush()
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    assert ticket_type_id
    enable_pre_tickets(database, actor, ticket_type_id)
    submitted = client.post("/api/v1/pre-tickets", headers=admin_headers, json={
        "client_id": client_row.id, "requester_contact_id": contact.id, "product_id": product.id, "product_module_id": module.id, "service_id": service.id,
        "proposed_priority": "P2", "title": "Call Center lifecycle test", "idempotency_key": "pre-ticket-queue-001",
    })
    assert submitted.status_code == 201, submitted.text
    claimed = client.post(f"/api/v1/pre-tickets/{submitted.json()['id']}/claim", headers=admin_headers, json={"expected_version": submitted.json()["version"]})
    assert claimed.status_code == 200, claimed.text
    requested = client.post(f"/api/v1/pre-tickets/{submitted.json()['id']}/needs-information", headers=admin_headers, json={"expected_version": claimed.json()["version"], "reason": "Please confirm the affected workflow."})
    assert requested.status_code == 200, requested.text
    assert requested.json()["status"] == "NEEDS_INFORMATION"
    responded = client.post(f"/api/v1/pre-tickets/{submitted.json()['id']}/respond", headers=admin_headers, json={"expected_version": requested.json()["version"], "response": "The workflow is invoice approval."})
    assert responded.status_code == 200, responded.text
    assert responded.json()["status"] == "SUBMITTED"
    converted = client.post(f"/api/v1/pre-tickets/{submitted.json()['id']}/convert", headers=admin_headers, json={"expected_version": responded.json()["version"], "conversion_idempotency_key": "pre-ticket-queue-convert-001"})
    assert converted.status_code == 200, converted.text
    assert converted.json()["conversion_mode"] == "CALL_CENTER"
    ticket = database.get(Ticket, converted.json()["resulting_ticket_id"])
    assert ticket and ticket.assigned_user_id == actor.id
    metrics = client.get("/api/v1/pre-tickets/metrics/summary", headers=admin_headers)
    assert metrics.status_code == 200, metrics.text
    summary = metrics.json()
    assert summary["average_minutes_to_claim"] is not None
    assert summary["average_minutes_claim_to_ticket"] is not None
    assert summary["average_minutes_to_ticket"] is not None
    assert any(row["label"] == client_row.name and row["count"] == 1 for row in summary["by_client"])
    assert any(row["label"] == product.name and row["count"] == 1 for row in summary["by_product"])
    assert any(row["key"] == "P2" and row["count"] == 1 for row in summary["by_priority"])
    assert any(row["key"] == "CONVERTED" and row["count"] == 1 for row in summary["aging_by_status"])


def test_pre_ticket_policy_cannot_be_enabled_without_a_complete_profile(client, admin_headers, database: Session) -> None:
    incomplete = client.put("/api/v1/system/feature-policies/engineer_pre_ticket/policies", headers=admin_headers, json={
        "scope_type": "SYSTEM", "mode": "ENFORCED", "configuration": {}, "reason": "Attempt to enable without a governed mapping.",
    })
    assert incomplete.status_code == 409, incomplete.text
    assert incomplete.json()["error"]["code"] == "PRE_TICKET_PROFILE_INVALID"
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    assert ticket_type_id
    missing_priority = client.put("/api/v1/system/feature-policies/engineer_pre_ticket/policies", headers=admin_headers, json={
        "scope_type": "SYSTEM", "mode": "ENFORCED", "configuration": {"ticket_type_id": ticket_type_id, "priority_mapping": {"P1": {"impact": "CRITICAL", "urgency": "CRITICAL"}}}, "reason": "Attempt to enable without all priority mappings.",
    })
    assert missing_priority.status_code == 409, missing_priority.text
    assert missing_priority.json()["error"]["code"] == "PRE_TICKET_PROFILE_INCOMPLETE"


def test_pre_ticket_queue_search_returns_paged_rows_and_total(client, admin_headers, database: Session) -> None:
    actor = database.scalar(select(User).where(User.username == "admin"))
    status = database.scalar(select(ClientStatus).where(ClientStatus.code == "ACTIVE"))
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    assert actor and status and ticket_type_id
    client_row = Client(code="PRE-SEARCH", name="Pre Ticket Search", status_id=status.id)
    database.add(client_row); database.flush()
    contact = Contact(client_id=client_row.id, full_name="Search Caller", email="search-pre-ticket@example.com")
    product = Product(code="PRE-SEARCH-PRODUCT", name="Pre Ticket Search Product")
    database.add_all([client_row, contact, product]); database.flush()
    module = ProductModule(product_id=product.id, code="PRE-SEARCH-MODULE", name="Search Module")
    service = ServiceCatalogItem(code="PRE-SEARCH-SERVICE", name="Search Service")
    service.modules.append(module)
    database.add_all([module, service]); database.commit()
    enable_pre_tickets(database, actor, ticket_type_id)
    created = client.post("/api/v1/pre-tickets", headers=admin_headers, json={
        "client_id": client_row.id, "requester_contact_id": contact.id, "product_id": product.id, "product_module_id": module.id, "service_id": service.id,
        "proposed_priority": "P3", "title": "Unique production queue search case", "idempotency_key": "pre-ticket-search-001",
    })
    assert created.status_code == 201, created.text
    found = client.get("/api/v1/pre-tickets/queue", headers=admin_headers, params={"search": "production queue", "limit": 1, "offset": 0})
    assert found.status_code == 200, found.text
    assert found.headers["x-total-count"] == "1"
    assert [item["id"] for item in found.json()] == [created.json()["id"]]
    exported = client.get("/api/v1/pre-tickets/queue/export", headers=admin_headers, params={"search": "production queue"})
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-type"].startswith("text/csv")
    assert "Unique production queue search case" in exported.text


def test_pre_ticket_queue_views_are_personal_and_can_be_removed(client, admin_headers) -> None:
    created = client.post("/api/v1/pre-tickets/queue/views", headers=admin_headers, json={
        "name": "Urgent submitted", "search_text": "gateway", "status_filter": "SUBMITTED",
    })
    assert created.status_code == 201, created.text
    view = created.json()
    assert view["search_text"] == "gateway"
    assert view["status_filter"] == "SUBMITTED"
    listed = client.get("/api/v1/pre-tickets/queue/views", headers=admin_headers)
    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()] == [view["id"]]
    deleted = client.delete(f"/api/v1/pre-tickets/queue/views/{view['id']}", headers=admin_headers)
    assert deleted.status_code == 204, deleted.text
    assert client.get("/api/v1/pre-tickets/queue/views", headers=admin_headers).json() == []
