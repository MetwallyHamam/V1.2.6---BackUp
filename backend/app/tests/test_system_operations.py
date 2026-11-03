from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.modules.clients.models import ClientStatus
from app.modules.iam.models import AuditLog
from app.modules.tickets.models import TicketType


def test_system_status_backup_history_and_sql_server_guard(
    client: TestClient,
    admin_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    attachment_path = tmp_path / "attachments"
    backup_path = tmp_path / "backups"
    attachment_path.mkdir()
    (attachment_path / "sample.txt").write_text("test", encoding="utf-8")
    backup_path.mkdir()
    (backup_path / "test-20260802.bak").write_bytes(b"backup")
    settings = Settings(
        app_env="test",
        secret_key="test-secret-key-with-more-than-thirty-two-characters",
        database_url="sqlite+pysqlite://",
        attachment_storage_path=str(attachment_path),
        database_backup_path=str(backup_path),
        escalation_scheduler_enabled=False,
    )
    original_override = client.app.dependency_overrides[get_settings]
    client.app.dependency_overrides[get_settings] = lambda: settings
    try:
        status = client.get("/api/v1/system/status", headers=admin_headers)
        assert status.status_code == 200, status.text
        assert status.json()["attachments"]["file_count"] == 1
        history = client.get("/api/v1/system/backups", headers=admin_headers)
        assert history.status_code == 200
        assert history.json()[0]["filename"] == "test-20260802.bak"
        unsupported = client.post("/api/v1/system/backups", headers=admin_headers)
        assert unsupported.status_code == 409
        assert unsupported.json()["error"]["code"] == "BACKUP_NOT_SUPPORTED"
    finally:
        client.app.dependency_overrides[get_settings] = original_override


def test_ticket_form_settings_control_visibility_and_server_required_fields(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    unauthorized = client.get("/api/v1/system/ticket-form-fields")
    assert unauthorized.status_code == 401
    settings = client.get(
        "/api/v1/system/ticket-form-fields", headers=admin_headers
    )
    assert settings.status_code == 200, settings.text
    assert {item["section"] for item in settings.json()} == {"PRIMARY", "ADDITIONAL"}
    assert next(
        item for item in settings.json() if item["field_key"] == "subject"
    )["can_hide"] is False
    ticket_type_setting = next(
        item for item in settings.json() if item["field_key"] == "ticket_type_id"
    )
    assert ticket_type_setting["default_value"] == "SERVICE_REQUEST"

    updates = []
    for item in settings.json():
        updates.append(
            {
                "field_key": item["field_key"],
                "is_visible": item["is_visible"],
                "is_required": item["field_key"] == "branch_id",
                "default_value": item["default_value"],
            }
        )
    saved = client.put(
        "/api/v1/system/ticket-form-fields", headers=admin_headers, json=updates
    )
    assert saved.status_code == 200, saved.text
    branch_setting = next(
        item for item in saved.json() if item["field_key"] == "branch_id"
    )
    assert branch_setting["is_visible"] is True
    assert branch_setting["is_required"] is True
    audit = database.scalar(
        select(AuditLog).where(
            AuditLog.action == "ticket_form.configuration.updated"
        )
    )
    assert audit is not None

    status_id = database.scalar(
        select(ClientStatus.id).where(ClientStatus.code == "ACTIVE")
    )
    customer = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "FORMSET", "name": "Form Settings Client", "status_id": status_id},
    ).json()
    branch = client.post(
        f"/api/v1/clients/{customer['id']}/branches",
        headers=admin_headers,
        json={"code": "HQ", "name": "Head Office"},
    ).json()
    ticket_type_id = database.scalar(
        select(TicketType.id).where(TicketType.code == "INCIDENT")
    )
    payload = {
        "ticket_type_id": ticket_type_id,
        "client_id": customer["id"],
        "impact": "MEDIUM",
        "urgency": "MEDIUM",
        "subject": "Required branch configuration",
        "description": "The configured mandatory field is enforced by the API.",
    }
    missing = client.post("/api/v1/tickets", headers=admin_headers, json=payload)
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "TICKET_REQUIRED_FIELDS_MISSING"
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={**payload, "branch_id": branch["id"]},
    )
    assert created.status_code == 201, created.text
