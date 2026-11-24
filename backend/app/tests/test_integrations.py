from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import ClientStatus, Contact
from app.modules.configuration.models import TicketFormFieldSetting
from app.modules.contracts.models import TicketSlaClock
from app.modules.integrations.models import IntegrationDelivery
from app.modules.integrations.schemas import InboundPreTicketSettings
from app.modules.pre_tickets.models import EngineerPreTicket
from app.modules.tickets.models import Ticket, TicketFlagAssignment


def test_legacy_inbound_caller_mapping_is_migrated() -> None:
    settings = InboundPreTicketSettings.model_validate(
        {
            "field_mapping": {
                "event_id": "id",
                "request_type": "type",
                "client": "client",
                "title": "title",
                "customer_name": "contact.name",
                "phone_number": "contact.phone",
            }
        }
    )
    fields = settings.profiles[0].fields
    assert fields["caller_name"].path == "contact.name"
    assert fields["caller_number"].path == "contact.phone"
    assert "customer_name" not in fields
    assert "phone_number" not in fields


def create_client(client: TestClient, headers: dict[str, str], database: Session) -> int:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    response = client.post(
        "/api/v1/clients",
        headers=headers,
        json={"code": "MONITORED", "name": "Monitored Client", "status_id": status_id},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_monitoring_webhook_is_authenticated_and_idempotent(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_client(client, admin_headers, database)
    payload = {
        "event_id": "evt-1001",
        "alert_key": "server-7/cpu",
        "client_id": client_id,
        "subject": "Server CPU usage is critical",
        "description": "CPU usage has remained above 95 percent for ten minutes.",
        "severity": "CRITICAL",
    }
    rejected = client.post("/api/v1/integrations/monitoring/events", json=payload)
    assert rejected.status_code == 401
    headers = {"X-Integration-Key": "local-monitoring-key-change-me"}
    created = client.post("/api/v1/integrations/monitoring/events", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["duplicate"] is False
    assert created.json()["ticket_number"].startswith("INC-")
    duplicate = client.post("/api/v1/integrations/monitoring/events", headers=headers, json=payload)
    assert duplicate.status_code == 201, duplicate.text
    assert duplicate.json()["duplicate"] is True
    assert duplicate.json()["ticket_id"] == created.json()["ticket_id"]
    assert database.scalar(select(IntegrationDelivery).where(IntegrationDelivery.event_id == "evt-1001"))


def test_vendor_basic_auth_direct_ticket_and_status(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    create_client(client, admin_headers, database)
    configured = client.put(
        "/api/v1/integrations/inbound-pre-ticket/settings", headers=admin_headers,
        json={"expected_version": 1, "profiles": [{
            "name": "Monitoring Vendor", "provider_key": "monitor-one", "enabled": True,
            "source_type": "MONITORING", "processing_mode": "DIRECT_TICKET",
            "default_priority": "P2", "default_ticket_type_code": "INCIDENT", "client_match_mode": "CODE",
            "request_type_mapping": {"ALERT": "CREATE_TICKET"},
            "fields": {key: {"enabled": True, "required": key in {"event_id", "request_type", "title"}, "path": key}
                       for key in ("event_id", "request_type", "client", "ticket_type", "title", "description", "caller_name", "caller_number")},
        }]},
    )
    assert configured.status_code == 200, configured.text
    credential = client.post(
        "/api/v1/integrations/api-clients", headers=admin_headers,
        json={"name": "Monitor Basic", "provider_key": "monitor-one", "auth_type": "BASIC", "username": "monitor.agent", "password": "StrongVendorPassword!123"},
    )
    assert credential.status_code == 201, credential.text
    payload = {"event_id": "alert-9001", "request_type": "ALERT", "client": "MONITORED", "title": "Database service unavailable", "description": "The database health check has failed repeatedly."}
    created = client.post("/api/v1/integrations/inbound/v1/monitor-one/requests", auth=("monitor.agent", "StrongVendorPassword!123"), json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["ticket_number"].startswith("INC-")
    assert created.json()["pre_ticket_id"] is None
    status = client.get("/api/v1/integrations/inbound/v1/monitor-one/requests/alert-9001", auth=("monitor.agent", "StrongVendorPassword!123"))
    assert status.status_code == 200, status.text
    assert status.json()["ticket_number"] == created.json()["ticket_number"]
    assert status.json()["ticket_status_code"]
    rejected = client.get("/api/v1/integrations/inbound/v1/monitor-one/requests/alert-9001", auth=("monitor.agent", "wrong-password"))
    assert rejected.status_code == 401

def test_configurable_inbound_request_creates_idempotent_pre_ticket(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_client(client, admin_headers, database)
    configured = client.put(
        "/api/v1/integrations/inbound-pre-ticket/settings",
        headers=admin_headers,
        json={
            "expected_version": 1,
            "enabled": True,
            "provider_key": "whatsapp",
            "default_priority": "P3",
            "default_ticket_type_code": "INCIDENT",
            "client_match_mode": "CODE_OR_EXACT_NAME",
            "field_mapping": {
                "event_id": "message.id",
                "request_type": "kind",
                "client": "client_name",
                "ticket_type": "ticket_type",
                "title": "issue.title",
                "description": "issue.description",
                "caller_name": "contact.name",
                "caller_number": "contact.phone",
            },
            "request_type_mapping": {
                "CREATE": "CREATE_TICKET",
                "CALL": "REQUEST_CALL",
            },
        },
    )
    assert configured.status_code == 200, configured.text
    credential = client.post(
        "/api/v1/integrations/api-clients",
        headers=admin_headers,
        json={"name": "WhatsApp integration test"},
    )
    assert credential.status_code == 201, credential.text
    payload = {
        "message": {"id": "wamid-1001"},
        "kind": "CALL",
        "client_name": "MONITORED",
        "ticket_type": "INCIDENT",
        "issue": {"title": "Please call about viewer error", "description": "Viewer fails after login."},
        "contact": {"name": "Ahmed", "phone": "+201000000000"},
    }
    headers = {"X-API-Key": credential.json()["api_key"]}
    created = client.post(
        "/api/v1/integrations/inbound/v1/whatsapp/requests", headers=headers, json=payload
    )
    assert created.status_code == 201, created.text
    assert created.json()["request_type"] == "REQUEST_CALL"
    assert created.json()["client_id"] == client_id
    assert created.json()["client_match"] == "MATCHED"
    lookup = client.get(
        "/api/v1/integrations/inbound/v1/whatsapp/clients?search=monit",
        headers=headers,
    )
    assert lookup.status_code == 200, lookup.text
    assert lookup.json()[0]["code"] == "MONITORED"
    request_status = client.get(
        "/api/v1/integrations/inbound/v1/whatsapp/requests/wamid-1001",
        headers=headers,
    )
    assert request_status.status_code == 200, request_status.text
    assert request_status.json()["status"] == "SUBMITTED"
    assert request_status.json()["pre_ticket_number"] == created.json()["pre_ticket_number"]
    duplicate = client.post(
        "/api/v1/integrations/inbound/whatsapp/requests", headers=headers, json=payload
    )
    assert duplicate.status_code == 201, duplicate.text
    assert duplicate.json()["duplicate"] is True
    item = database.get(EngineerPreTicket, created.json()["pre_ticket_id"])
    assert item is not None and item.status == "SUBMITTED"
    assert item.request_kind == "CALL_REQUEST"
    assert item.source_provider == "WHATSAPP"
    assert item.external_event_id == "wamid-1001"
    assert item.external_caller_name == "Ahmed"
    assert item.external_caller_number == "+201000000000"
    assert item.requested_ticket_type_code == "INCIDENT"
    assert "Request type: REQUEST_CALL" in item.initial_description
    assert database.scalar(
        select(IntegrationDelivery).where(
            IntegrationDelivery.event_id == "wamid-1001"
        )
    )


def test_inbound_email_creates_ticket_then_adds_idempotent_reply(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_client(client, admin_headers, database)
    headers = {"X-Integration-Key": "local-email-key-change-me"}
    first = client.post(
        "/api/v1/integrations/email/events",
        headers=headers,
        json={
            "message_id": "mail-1001",
            "from_address": "requester@example.com",
            "client_id": client_id,
            "subject": "Unable to open application",
            "body": "The application displays an error immediately after sign in.",
        },
    )
    assert first.status_code == 201, first.text
    assert first.json()["action"] == "CREATED"
    ticket_number = first.json()["ticket_number"]

    reply_payload = {
        "message_id": "mail-1002",
        "from_address": "requester@example.com",
        "client_id": client_id,
        "subject": f"Re: {ticket_number}",
        "body": "The same error still occurs after clearing the browser cache.",
        "ticket_number": ticket_number,
    }
    reply = client.post(
        "/api/v1/integrations/email/events", headers=headers, json=reply_payload
    )
    assert reply.status_code == 201, reply.text
    assert reply.json()["action"] == "COMMENTED"
    duplicate = client.post(
        "/api/v1/integrations/email/events", headers=headers, json=reply_payload
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["duplicate"] is True
    comments = client.get(
        f"/api/v1/tickets/{first.json()['ticket_id']}/comments", headers=admin_headers
    )
    assert len(comments.json()) == 1


def test_itop_import_maps_legacy_ids_and_skips_rerun(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    client_id = create_client(client, admin_headers, database)
    payload = {
        "items": [
            {
                "external_id": "ITOP-4242",
                "client_id": client_id,
                "subject": "Legacy PACS connectivity incident",
                "description": "Imported historical incident affecting modality connectivity.",
                "ticket_type_code": "INCIDENT",
                "impact": "HIGH",
                "urgency": "MEDIUM",
                "original_status": "assigned",
            }
        ]
    }
    first = client.post(
        "/api/v1/integrations/itop/tickets/import",
        headers=admin_headers,
        json=payload,
    )
    assert first.status_code == 200, first.text
    assert first.json()["imported"] == 1
    assert first.json()["skipped"] == 0
    repeated = client.post(
        "/api/v1/integrations/itop/tickets/import",
        headers=admin_headers,
        json=payload,
    )
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["imported"] == 0
    assert repeated.json()["skipped"] == 1
    assert repeated.json()["items"][0]["ticket_id"] == first.json()["items"][0]["ticket_id"]


def test_scoped_api_client_creates_idempotent_ticket_and_can_be_revoked(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    branch_setting = database.scalar(
        select(TicketFormFieldSetting).where(
            TicketFormFieldSetting.field_key == "branch_id"
        )
    )
    if branch_setting is None:
        branch_setting = TicketFormFieldSetting(
            field_key="branch_id", is_visible=True, is_required=True
        )
        database.add(branch_setting)
    else:
        branch_setting.is_visible = True
        branch_setting.is_required = True
    database.commit()

    client_id = create_client(client, admin_headers, database)
    credential = client.post(
        "/api/v1/integrations/api-clients",
        headers=admin_headers,
        json={"name": "Test monitoring application", "client_id": client_id},
    )
    assert credential.status_code == 201, credential.text
    api_key = credential.json()["api_key"]
    assert api_key.startswith("msh_")
    payload = {
        "event_id": "application-event-1",
        "client_id": client_id,
        "subject": "Application-reported service failure",
        "description": "Another Millensys application reported a service failure through the API.",
        "impact": "HIGH",
        "urgency": "HIGH",
    }
    created = client.post(
        "/api/v1/integrations/api/tickets",
        headers={"X-API-Key": api_key},
        json=payload,
    )
    assert created.status_code == 201, created.text
    assert created.json()["duplicate"] is False
    ticket_id = created.json()["ticket_id"]
    ticket = database.get(Ticket, ticket_id)
    requester = database.get(Contact, ticket.requester_contact_id)
    assert requester.full_name == "MiMonitoringService"
    maintenance_flag = database.scalar(
        select(TicketFlagAssignment).where(
            TicketFlagAssignment.ticket_id == ticket_id,
            TicketFlagAssignment.flag_code_snapshot == "SYSTEM_MAINTENANCE",
            TicketFlagAssignment.removed_at.is_(None),
        )
    )
    assert maintenance_flag is not None
    assert maintenance_flag.pauses_sla_snapshot is True
    resolution_clock = database.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket_id,
            TicketSlaClock.clock_type == "RESOLUTION",
        )
    )
    if resolution_clock is not None:
        assert resolution_clock.state == "PAUSED"
    status_response = client.get(
        f"/api/v1/integrations/api/tickets/{ticket_id}",
        headers={"X-API-Key": api_key},
    )
    assert status_response.status_code == 200, status_response.text
    assert status_response.json()["status_code"] in {"NEW", "ASSIGNED"}
    started = client.patch(
        f"/api/v1/integrations/api/tickets/{ticket_id}/status",
        headers={"X-API-Key": api_key},
        json={"event_id": "application-event-1-start", "status_code": "IN_PROGRESS"},
    )
    assert started.status_code == 200, started.text
    assert started.json()["status_code"] == "IN_PROGRESS"
    repeated_status = client.patch(
        f"/api/v1/integrations/api/tickets/{ticket_id}/status",
        headers={"X-API-Key": api_key},
        json={"event_id": "application-event-1-start", "status_code": "IN_PROGRESS"},
    )
    assert repeated_status.status_code == 200
    assert repeated_status.json()["duplicate"] is True
    closed = client.patch(
        f"/api/v1/integrations/api/tickets/{ticket_id}/status",
        headers={"X-API-Key": api_key},
        json={
            "event_id": "application-event-1-close",
            "status_code": "CLOSED",
            "resolution_summary": "Monitoring confirms that the application service recovered.",
            "root_cause_summary": "The monitored application service stopped unexpectedly.",
        },
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["status_code"] == "CLOSED"
    assert closed.json()["resolution_summary"].startswith("Monitoring confirms")
    duplicate = client.post(
        "/api/v1/integrations/api/tickets",
        headers={"X-API-Key": api_key},
        json=payload,
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["duplicate"] is True
    revoked = client.delete(
        f"/api/v1/integrations/api-clients/{credential.json()['id']}",
        headers=admin_headers,
    )
    assert revoked.status_code == 204
    rejected = client.post(
        "/api/v1/integrations/api/tickets",
        headers={"X-API-Key": api_key},
        json={**payload, "event_id": "application-event-2"},
    )
    assert rejected.status_code == 401
