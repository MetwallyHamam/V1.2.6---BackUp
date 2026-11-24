from sqlalchemy import select

from app.modules.clients.models import Client, ClientStatus
from app.modules.iam.models import Department, User
from app.modules.notifications.models import Notification
from app.modules.tickets.models import Ticket, TicketStatus, TicketType
from app.tests.test_project_portfolio import _scoped_user_headers


def _context(client, headers, database):
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
    pmo = Department(code="PMO", name="Project Management", is_active=True)
    implementation = Department(code="IMP", name="Implementation", is_active=True)
    support = Department(code="SUP", name="Support", is_active=True)
    database.add_all([pmo, implementation, support])
    database.commit()
    manager_id = database.scalar(select(User.id).where(User.username == "admin"))
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "project_number": "PRJ-COL",
            "name": "Collaboration pilot",
            "account_id": account["id"],
            "organization_id": organization["id"],
            "client_id": customer["id"],
            "owning_department_id": pmo.id,
            "project_manager_user_id": manager_id,
        },
    ).json()
    return project, customer, manager_id, pmo, implementation, support


def _ticket(database, customer_id, actor_id):
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    ticket_status_id = database.scalar(select(TicketStatus.id).where(TicketStatus.code == "NEW"))
    row = Ticket(
        ticket_number="INC-COL-1",
        ticket_type_id=ticket_type_id,
        client_id=customer_id,
        created_by_user_id=actor_id,
        status_id=ticket_status_id,
        impact="MEDIUM",
        urgency="MEDIUM",
        priority="P3",
        subject="Implementation configuration question",
        description="Support needs implementation history.",
    )
    database.add(row)
    database.commit()
    database.refresh(row)
    return row


def test_cross_department_request_response_and_notification(client, admin_headers, database):
    project, _, manager_id, pmo, implementation, _ = _context(client, admin_headers, database)
    admin = database.get(User, manager_id)
    admin.department_id = implementation.id
    database.commit()
    created = client.post(
        f"/api/v1/projects/{project['id']}/collaboration-requests",
        headers=admin_headers,
        json={
            "requesting_department_id": pmo.id,
            "requested_department_id": implementation.id,
            "request_type": "TECHNICAL_REVIEW",
            "title": "Review integration scope",
            "description": "Confirm interface ownership.",
            "priority": "HIGH",
        },
    )
    assert created.status_code == 201, created.text
    response = client.post(
        f"/api/v1/collaboration-requests/{created.json()['id']}/respond",
        headers=admin_headers,
        json={"decision": "ACCEPT", "owner_user_id": manager_id, "notes": "Review scheduled"},
    )
    assert response.status_code == 200 and response.json()["status"] == "ACCEPTED"
    notifications = list(
        database.scalars(
            select(Notification).where(
                Notification.notification_type.in_(
                    ["PROJECT_COLLABORATION_REQUEST", "PROJECT_COLLABORATION_RESPONSE"]
                )
            )
        )
    )
    assert len(notifications) >= 2


def test_typed_ticket_link_exposes_only_support_shared_history(client, admin_headers, database):
    project, customer, manager_id, _, _, _ = _context(client, admin_headers, database)
    ticket = _ticket(database, customer["id"], manager_id)
    private = client.post(
        f"/api/v1/projects/{project['id']}/events",
        headers=admin_headers,
        json={
            "event_type": "INTERNAL_NOTE",
            "title": "Private investigation",
            "summary": "Sensitive engineering detail",
            "visibility": "PROJECT_PRIVATE",
        },
    )
    assert private.status_code == 201
    linked = client.post(
        f"/api/v1/projects/{project['id']}/ticket-links",
        headers=admin_headers,
        json={
            "ticket_id": ticket.id,
            "link_type": "REQUIRES_IMPLEMENTATION",
            "shared_summary": "Implementation is reviewing the configuration.",
        },
    )
    assert linked.status_code == 201, linked.text
    history = client.get(
        f"/api/v1/tickets/{ticket.id}/implementation-history", headers=admin_headers
    )
    assert history.status_code == 200
    payload = history.json()
    assert payload["links"][0]["project_number"] == "PRJ-COL"
    assert len(payload["events"]) == 1
    assert payload["events"][0]["visibility"] == "SUPPORT_SHARED"
    assert "Sensitive" not in str(payload)


def test_ticket_link_rejects_different_client(client, admin_headers, database):
    project, _, manager_id, _, _, _ = _context(client, admin_headers, database)
    status_id = database.scalar(select(ClientStatus.id))
    other = Client(code="OTHER", name="Other client", status_id=status_id)
    database.add(other)
    database.commit()
    ticket = _ticket(database, other.id, manager_id)
    response = client.post(
        f"/api/v1/projects/{project['id']}/ticket-links",
        headers=admin_headers,
        json={"ticket_id": ticket.id, "link_type": "RELATED", "shared_summary": "Wrong customer"},
    )
    assert response.status_code == 409


def test_collaboration_request_is_visible_only_to_requested_department(
    client, admin_headers, database
):
    project, _, _, pmo, implementation, support = _context(
        client, admin_headers, database
    )
    created = client.post(
        f"/api/v1/projects/{project['id']}/collaboration-requests",
        headers=admin_headers,
        json={
            "requesting_department_id": pmo.id,
            "requested_department_id": implementation.id,
            "request_type": "TECHNICAL_REVIEW",
            "title": "Validate deployment plan",
            "description": "Implementation must confirm the delivery sequence.",
        },
    )
    assert created.status_code == 201, created.text
    implementation_user, implementation_headers = _scoped_user_headers(
        database,
        implementation,
        "project.portfolio.view",
        "cross_department.request.respond",
    )
    _, unrelated_headers = _scoped_user_headers(
        database,
        support,
        "project.portfolio.view",
        "cross_department.request.respond",
        "cross_department.request.create",
    )
    denied = client.post(
        f"/api/v1/collaboration-requests/{created.json()['id']}/respond",
        headers=unrelated_headers,
        json={"decision": "ACCEPT", "notes": "Must remain hidden"},
    )
    assert denied.status_code == 404
    hidden_project = client.get(
        f"/api/v1/projects/{project['id']}/collaboration", headers=unrelated_headers
    )
    assert hidden_project.status_code == 404
    accepted = client.post(
        f"/api/v1/collaboration-requests/{created.json()['id']}/respond",
        headers=implementation_headers,
        json={
            "decision": "ACCEPT",
            "owner_user_id": implementation_user.id,
            "notes": "Delivery sequence confirmed",
        },
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "ACCEPTED"


def test_project_access_does_not_bypass_ticket_visibility(client, admin_headers, database):
    project, customer, manager_id, pmo, implementation, _ = _context(
        client, admin_headers, database
    )
    ticket = _ticket(database, customer["id"], manager_id)
    created = client.post(
        f"/api/v1/projects/{project['id']}/collaboration-requests",
        headers=admin_headers,
        json={
            "requesting_department_id": pmo.id,
            "requested_department_id": implementation.id,
            "request_type": "TECHNICAL_REVIEW",
            "title": "Review restricted ticket",
            "description": "Project visibility must not grant ticket visibility.",
        },
    )
    assert created.status_code == 201, created.text
    _, implementation_headers = _scoped_user_headers(
        database,
        implementation,
        "project.portfolio.view",
        "cross_department.history.view",
        "cross_department.ticket_link.manage",
        "cross_department.event.publish",
    )
    linked = client.post(
        f"/api/v1/projects/{project['id']}/ticket-links",
        headers=implementation_headers,
        json={
            "ticket_id": ticket.id,
            "link_type": "RELATED",
            "shared_summary": "Must not expose a restricted ticket.",
        },
    )
    assert linked.status_code == 404
    event = client.post(
        f"/api/v1/projects/{project['id']}/events",
        headers=implementation_headers,
        json={
            "ticket_id": ticket.id,
            "event_type": "INTERNAL_NOTE",
            "title": "Should remain hidden",
            "summary": "Unauthorized ticket reference",
            "visibility": "SUPPORT_SHARED",
        },
    )
    assert event.status_code == 404
    history = client.get(
        f"/api/v1/tickets/{ticket.id}/implementation-history",
        headers=implementation_headers,
    )
    assert history.status_code == 404
