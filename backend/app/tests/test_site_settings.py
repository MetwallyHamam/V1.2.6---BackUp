from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.configuration.models import SiteSetting
from app.modules.iam.models import User
from app.modules.notifications.models import EventOutbox


def test_support_assistant_settings_are_versioned_and_audited(
    client, admin_headers, database
) -> None:
    current = client.get(
        "/api/v1/system/site-settings/support-assistant",
        headers=admin_headers,
    )
    assert current.status_code == 200, current.text
    values = current.json()["values"]
    assert values["unreceived_warning_minutes"] == 9
    values.update(
        {
            "queue_refresh_seconds": 20,
            "count_refresh_seconds": 40,
            "unreceived_warning_minutes": 12,
            "mine_show_closed": False,
        }
    )
    saved = client.put(
        "/api/v1/system/site-settings/support-assistant",
        headers=admin_headers,
        json={**values, "expected_version": current.json()["version"]},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["values"]["queue_refresh_seconds"] == 20
    assert saved.json()["values"]["mine_show_closed"] is False
    assert database.get(
        SiteSetting, "support_assistant_unreceived_warning_minutes"
    ).value == "12"


def test_contract_expiration_notification_settings_are_versioned(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    admin = database.scalar(select(User).where(User.username_normalized == "admin"))
    assert admin
    current = client.get("/api/v1/contracts/notification-settings", headers=admin_headers)
    assert current.status_code == 200, current.text
    assert current.json()["reminder_days"] == [60, 30, 14, 7, 0]
    saved = client.put(
        "/api/v1/contracts/notification-settings",
        headers=admin_headers,
        json={
            **current.json(),
            "enabled": True,
            "reminder_days": [90, 60, 30, 7, 0],
            "to_user_ids": [admin.id],
            "cc_user_ids": [],
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["version"] == current.json()["version"] + 1
    assert database.get(SiteSetting, "contract_expiration_notification_to_user_ids").value == f"[{admin.id}]"


def test_first_response_start_mode_is_validated_and_persisted(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    invalid = client.put(
        "/api/v1/system/site-settings/first-response-start-mode",
        headers=admin_headers,
        json={"mode": "TICKET_ASSIGNED_TO_TEAM"},
    )
    assert invalid.status_code == 422
    saved = client.put(
        "/api/v1/system/site-settings/first-response-start-mode",
        headers=admin_headers,
        json={"mode": "FIRST_DEDICATED_ASSIGNMENT"},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json() == {"mode": "FIRST_DEDICATED_ASSIGNMENT"}
    database.expire_all()
    assert database.get(SiteSetting, "first_response_start_mode").value == "FIRST_DEDICATED_ASSIGNMENT"


def test_site_settings_validate_and_persist_public_defaults(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    invalid = client.put(
        "/api/v1/system/site-settings",
        headers=admin_headers,
        json={
            "default_theme": "DARK",
            "default_sound": False,
            "default_assignee_user_id": 999999,
            "assign_available_only": True,
            "assign_online_only": True,
        },
    )
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "INVALID_DEFAULT_ASSIGNEE"

    support = database.scalar(select(User).where(User.email_normalized == "support@millensys.com"))
    assert support is not None
    saved = client.put(
        "/api/v1/system/site-settings",
        headers=admin_headers,
        json={
            "default_theme": "DARK",
            "default_sound": False,
            "default_assignee_user_id": support.id,
            "assign_available_only": True,
            "assign_online_only": False,
            "first_response_start_mode": "TICKET_CREATED",
        },
    )
    assert saved.status_code == 200, saved.text
    saved_values = saved.json()
    assert saved_values.pop("server_datetime").endswith(("+02:00", "+03:00"))
    assert saved_values == {
        "server_timezone": "Africa/Cairo",
        "daylight_saving_enabled": True,
        "default_theme": "DARK",
        "default_sound": False,
        "default_assignee_user_id": support.id,
        "assign_available_only": True,
        "assign_online_only": False,
        "resolution_details_required_on_close": False,
        "first_response_start_mode": "TICKET_CREATED",
        "live_ticket_update_enabled": True,
        "live_ticket_update_closed_poll_seconds": 300,
        "satisfaction_manual_enabled": False,
        "satisfaction_whatsapp_enabled": True,
        "satisfaction_email_enabled": True,
        "satisfaction_token_expiry_days": 30,
        "satisfaction_whatsapp_template": "Dear {client_name},\n\nPlease rate the service for ticket {ticket_number}:\n{rating_url}\n\nThis link expires on {expires_at}.",
        "satisfaction_email_subject": "Rate support ticket {ticket_number}",
        "satisfaction_email_body": "Dear {client_name},\n\nPlease rate the service for ticket {ticket_number}:\n{rating_url}\n\nThis link expires on {expires_at}.",
        "sla_warning_enabled": True,
        "sla_response_warning_minutes": [60],
        "sla_resolution_warning_minutes": [240],
        "sla_warning_recipient_emails": [],
        "sla_warning_support_team_ids": [],
    }
    assert database.get(SiteSetting, "default_theme").value == "DARK"
    loaded = client.get("/api/v1/system/site-settings", headers=admin_headers).json()
    assert loaded.pop("server_datetime").endswith(("+02:00", "+03:00"))
    assert loaded == saved_values


def test_time_settings_are_available_without_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/system/time-settings")
    assert response.status_code == 200
    assert response.json()["server_timezone"] == "Africa/Cairo"
    assert response.json()["server_datetime"].endswith(("+02:00", "+03:00"))


def test_categorized_site_settings_are_complete_isolated_and_versioned(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    unauthorized = client.get("/api/v1/system/site-settings/categories")
    assert unauthorized.status_code == 401

    inventory = client.get(
        "/api/v1/system/site-settings/categories", headers=admin_headers
    )
    assert inventory.status_code == 200, inventory.text
    categories = {item["key"] for item in inventory.json()}
    assert categories == {
        "general",
        "support-assistant",
        "ticket-notifications",
        "ticket-forms",
        "third-party-integrations",
        "attachments-storage",
        "security-access",
        "advanced",
    }
    setting_keys = [
        key for item in inventory.json() for key in item["persisted_setting_keys"]
    ]
    assert len(setting_keys) == len(set(setting_keys))
    resources = [
        resource for item in inventory.json() for resource in item["managed_resources"]
    ]
    assert "ticket_form_field_settings" in resources
    assert "SMTP_*" in resources
    assert "outlook_email_configuration" in resources
    assert "inbound_pre_ticket_configuration" in resources

    general = client.get(
        "/api/v1/system/site-settings/categories/general", headers=admin_headers
    )
    assert general.status_code == 200, general.text
    assert general.json()["version"] == 1

    support = database.scalar(
        select(User).where(User.email_normalized == "support@millensys.com")
    )
    assert support is not None
    payload = {
        **general.json()["values"],
        "expected_version": general.json()["version"],
        "default_theme": "LIGHT",
        "default_assignee_user_id": support.id,
    }
    saved = client.put(
        "/api/v1/system/site-settings/categories/general",
        headers=admin_headers,
        json=payload,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["version"] == 2
    assert saved.json()["values"]["default_theme"] == "LIGHT"

    stale = client.put(
        "/api/v1/system/site-settings/categories/general",
        headers=admin_headers,
        json={**payload, "default_theme": "DARK"},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "SITE_SETTINGS_VERSION_CONFLICT"
    assert database.get(SiteSetting, "default_theme").value == "LIGHT"
    unknown = client.get(
        "/api/v1/system/site-settings/categories/unknown", headers=admin_headers
    )
    assert unknown.status_code == 404


def test_disabling_sla_warnings_cancels_queued_warning_emails(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    warning = EventOutbox(
        event_type="SLA_WARNING",
        aggregate_type="Ticket",
        aggregate_id="42",
        deduplication_key="sla-warning:disable-transition",
        payload_json="{}",
        status="RETRY",
    )
    escalation = EventOutbox(
        event_type="SLA_ESCALATED",
        aggregate_type="Ticket",
        aggregate_id="43",
        deduplication_key="sla-escalated:disable-transition",
        payload_json="{}",
        status="PENDING",
    )
    database.add_all([warning, escalation])
    database.commit()

    current = client.get(
        "/api/v1/system/site-settings", headers=admin_headers
    ).json()
    response = client.put(
        "/api/v1/system/site-settings",
        headers=admin_headers,
        json={**current, "sla_warning_enabled": False},
    )

    assert response.status_code == 200, response.text
    database.refresh(warning)
    assert warning.status == "SKIPPED"
    assert warning.next_attempt_at is None
    database.refresh(escalation)
    assert escalation.status == "SKIPPED"
    assert escalation.next_attempt_at is None
