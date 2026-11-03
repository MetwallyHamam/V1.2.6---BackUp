import json
import os
import re
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy import update as sql_update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.api.dependencies import authenticated_user, require_permission
from app.core.clock import configure_server_clock, server_now
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, ConflictError
from app.db.session import get_db
from app.modules.clients.models import SupportTeam, SupportTeamMember
from app.modules.configuration.models import SiteSetting, TicketFormFieldSetting
from app.modules.configuration.service import (
    create_verified_backup,
    list_backups,
    read_smtp_configuration,
    read_storage_configuration,
    system_status,
    update_smtp_configuration,
    update_storage_configuration,
)
from app.modules.configuration.ticket_form import (
    DEFINITIONS_BY_KEY,
    PRE_TICKET_DEFINITIONS_BY_KEY,
    PRE_TICKET_FIELD_DEFINITIONS,
    TICKET_FIELD_DEFINITIONS,
)
from app.modules.iam.models import AuditLog, Profile, User
from app.modules.notifications.email_service import smtp_sender
from app.modules.notifications.models import EmailDelivery, EventOutbox, TicketNotificationRule
from app.modules.tickets.models import TicketType

router = APIRouter(prefix="/system", tags=["system operations"])


class TicketFormFieldRead(BaseModel):
    field_key: str
    label: str
    section: str
    display_order: int
    is_visible: bool
    is_required: bool
    can_hide: bool
    can_require: bool
    can_default: bool
    default_value: str | None
    permission: str | None


class StorageConfigurationUpdate(BaseModel):
    attachment_storage_path: str = Field(min_length=3, max_length=1000)


class LocalAiConfigurationUpdate(BaseModel):
    mode: str = Field(pattern="^(LOCAL|REMOTE)$")
    local_folder: str | None = Field(default=None, max_length=1000)
    remote_base_url: str | None = Field(default=None, max_length=500)
    intake_instructions: str = Field(default="", max_length=8000)
    provider: str = Field(default="OLLAMA", pattern="^(OLLAMA|OPENAI)$")
    model: str = Field(default="qwen2.5:3b", min_length=1, max_length=100)
    api_key: str | None = Field(default=None, max_length=500)

    @field_validator("api_key")
    @classmethod
    def valid_api_key(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip()
        if len(normalized) < 20 or any(character.isspace() for character in normalized):
            raise ValueError("Enter a valid API key without spaces.")
        return normalized

    @field_validator("model")
    @classmethod
    def valid_model(cls, value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9._:/-]+", normalized):
            raise ValueError("Enter a valid model name.")
        return normalized

    @field_validator("remote_base_url")
    @classmethod
    def valid_base_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip().rstrip("/")
        parsed = urlsplit(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Enter a valid HTTP or HTTPS Local AI service URL.")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("The Local AI URL cannot contain credentials, query parameters, or fragments.")
        return normalized

    @model_validator(mode="after")
    def validate_mode(self) -> "LocalAiConfigurationUpdate":
        if self.mode == "LOCAL":
            if not self.local_folder:
                raise ValueError("Choose the Local AI installation folder.")
            folder = Path(self.local_folder).expanduser()
            if not folder.is_absolute() or not folder.is_dir():
                raise ValueError("The Local AI folder must be an existing absolute server directory.")
            if not (folder / "app" / "main.py").is_file() or not (folder / "run.bat").is_file():
                raise ValueError("The selected folder is not a valid Local AI installation.")
            self.local_folder = str(folder.resolve())
        elif not self.remote_base_url:
            raise ValueError("Enter the remote Local AI service URL.")
        return self


def _local_ai_environment(folder: str) -> dict[str, str]:
    path = Path(folder) / ".env"
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip().upper()] = value.strip()
    return values


def _update_local_ai_environment(
    folder: str, *, provider: str, model: str, api_key: str | None
) -> None:
    path = Path(folder) / ".env"
    if path.is_file():
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    else:
        example = Path(folder) / ".env.example"
        lines = example.read_text(encoding="utf-8-sig").splitlines() if example.is_file() else []
    replacements = {
        "AI_PROVIDER": provider,
        "OLLAMA_MODEL": model if provider == "OLLAMA" else None,
        "OPENAI_MODEL": model if provider == "OPENAI" else None,
        "OPENAI_API_KEY": api_key,
    }
    found: set[str] = set()
    updated: list[str] = []
    for line in lines:
        if "=" not in line or line.lstrip().startswith("#"):
            updated.append(line)
            continue
        key = line.split("=", 1)[0].strip().upper()
        if key not in replacements or replacements[key] is None:
            updated.append(line)
            continue
        updated.append(f"{key}={replacements[key]}")
        found.add(key)
    for key, value in replacements.items():
        if value is not None and key not in found:
            updated.append(f"{key}={value}")
    temporary = path.with_suffix(".env.tmp")
    try:
        temporary.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")
        temporary.replace(path)
    except PermissionError as exc:
        raise AppError(
            "LOCAL_AI_ENV_ACCESS_DENIED",
            "The backend service account cannot update the Local AI .env file.",
            500,
        ) from exc

class SmtpConfigurationUpdate(BaseModel):
    enabled: bool; host: str = Field(min_length=1, max_length=255); port: int = Field(ge=1, le=65535)
    username: str | None = Field(default=None, max_length=320); password: str | None = Field(default=None, max_length=500)
    from_address: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"); use_tls: bool = True
    from_name: str = Field(default="Millensys Support Hub", min_length=2, max_length=100)


class SiteSettingsUpdate(BaseModel):
    server_timezone: str = Field(default="Africa/Cairo", min_length=3, max_length=100)
    daylight_saving_enabled: bool = True
    default_theme: str = Field(pattern="^(SYSTEM|LIGHT|DARK)$")
    default_sound: bool
    default_assignee_user_id: int | None = None
    assign_available_only: bool
    assign_online_only: bool
    resolution_details_required_on_close: bool = False
    first_response_start_mode: str | None = Field(default=None, pattern="^(TICKET_CREATED|FIRST_DEDICATED_ASSIGNMENT)$")
    live_ticket_update_enabled: bool = True
    live_ticket_update_closed_poll_seconds: int = Field(default=300, ge=60, le=3600)
    satisfaction_manual_enabled: bool = False
    satisfaction_whatsapp_enabled: bool = True
    satisfaction_email_enabled: bool = True
    satisfaction_token_expiry_days: int = Field(default=30, ge=1, le=365)
    satisfaction_whatsapp_template: str = Field(default="Dear {client_name},\n\nPlease rate the service for ticket {ticket_number}:\n{rating_url}\n\nThis link expires on {expires_at}.", min_length=5, max_length=4000)
    satisfaction_email_subject: str = Field(default="Rate support ticket {ticket_number}", min_length=2, max_length=300)
    satisfaction_email_body: str = Field(default="Dear {client_name},\n\nPlease rate the service for ticket {ticket_number}:\n{rating_url}\n\nThis link expires on {expires_at}.", min_length=5, max_length=10000)
    sla_warning_enabled: bool = True
    sla_response_warning_minutes: list[int] = Field(default_factory=lambda: [60], max_length=10)
    sla_resolution_warning_minutes: list[int] = Field(default_factory=lambda: [240], max_length=10)
    sla_warning_recipient_emails: list[EmailStr] = Field(default_factory=list, max_length=100)
    sla_warning_support_team_ids: list[int] = Field(default_factory=list, max_length=100)

    @field_validator("first_response_start_mode", mode="before")
    @classmethod
    def empty_first_response_mode(cls, value: object) -> object:
        return None if value in {None, "", "null"} else value

    @field_validator("server_timezone")
    @classmethod
    def valid_server_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Enter a valid IANA server timezone.") from exc
        return value

    @model_validator(mode="after")
    def validate_sla_warning_configuration(self) -> "SiteSettingsUpdate":
        self.sla_response_warning_minutes = sorted(set(self.sla_response_warning_minutes), reverse=True)
        self.sla_resolution_warning_minutes = sorted(set(self.sla_resolution_warning_minutes), reverse=True)
        if any(value < 1 or value > 525_600 for value in [*self.sla_response_warning_minutes, *self.sla_resolution_warning_minutes]):
            raise ValueError("SLA warning thresholds must be between 1 and 525600 minutes.")
        self.sla_warning_recipient_emails = list(dict.fromkeys(str(value).strip().lower() for value in self.sla_warning_recipient_emails))
        self.sla_warning_support_team_ids = list(dict.fromkeys(self.sla_warning_support_team_ids))
        if self.sla_warning_enabled and not (self.sla_response_warning_minutes or self.sla_resolution_warning_minutes):
            raise ValueError("At least one SLA warning threshold is required when warnings are enabled.")
        return self


class GeneralSiteSettingsUpdate(SiteSettingsUpdate):
    expected_version: int = Field(ge=1)


class SiteSettingsCategoryRead(BaseModel):
    category: str
    version: int
    values: dict[str, object]


class SupportAssistantSettings(BaseModel):
    queue_refresh_seconds: int = Field(default=30, ge=10, le=300)
    count_refresh_seconds: int = Field(default=30, ge=10, le=300)
    unreceived_warning_minutes: int = Field(default=9, ge=1, le=1440)
    queue_tab_attention_enabled: bool = True
    overdue_card_animation_enabled: bool = True
    mine_show_resolved: bool = True
    mine_show_closed: bool = True
    backlog_default_period: str = Field(
        default="THIS_MONTH",
        pattern="^(TODAY|THIS_WEEK|LAST_WEEK|THIS_MONTH|CUSTOM)$",
    )
    page_size: int = Field(default=12, ge=6, le=50)
    allow_user_overrides: bool = True
    tab_sorting: dict[str, str] = Field(
        default_factory=lambda: {
            "queue": "created_at:asc",
            "mine": "updated_at:desc",
            "backlog": "created_at:asc",
            "follow-up": "updated_at:desc",
            "sla-risk": "updated_at:desc",
            "pre-tickets": "submitted_at:asc",
        }
    )

    @field_validator("tab_sorting")
    @classmethod
    def validate_tab_sorting(cls, value: dict[str, str]) -> dict[str, str]:
        tabs = {"queue", "mine", "backlog", "follow-up", "sla-risk", "pre-tickets"}
        fields = {"created_at", "updated_at", "priority", "ticket_number", "submitted_at"}
        directions = {"asc", "desc"}
        if set(value) != tabs:
            raise ValueError("Sorting must be supplied for every Support Assistant tab.")
        for setting in value.values():
            field, separator, direction = setting.partition(":")
            if not separator or field not in fields or direction not in directions:
                raise ValueError("Invalid Support Assistant sorting configuration.")
        return value


class SupportAssistantSettingsUpdate(SupportAssistantSettings):
    expected_version: int = Field(ge=1)


class FirstResponseStartModeUpdate(BaseModel):
    mode: str = Field(pattern="^(TICKET_CREATED|FIRST_DEDICATED_ASSIGNMENT)$")


SITE_SETTING_CATEGORIES: dict[str, tuple[str, ...]] = {
    "general": (
        "server_timezone",
        "daylight_saving_enabled",
        "default_theme",
        "default_sound",
        "default_assignee_user_id",
        "assign_available_only",
        "assign_online_only",
        "resolution_details_required_on_close",
        "first_response_start_mode",
        "live_ticket_update_enabled",
        "live_ticket_update_closed_poll_seconds",
        "satisfaction_manual_enabled",
        "satisfaction_whatsapp_enabled",
        "satisfaction_email_enabled",
        "satisfaction_token_expiry_days",
        "satisfaction_whatsapp_template",
        "satisfaction_email_subject",
        "satisfaction_email_body",
        "sla_warning_enabled",
        "sla_response_warning_minutes",
        "sla_resolution_warning_minutes",
        "sla_warning_recipient_emails",
        "sla_warning_support_team_ids",
    ),
    "ticket-notifications": (
        "portal_ticket_email_*",
        "ticket_notification_template_*",
    ),
    "ticket-forms": ("ticket_form_field_settings",),
    "third-party-integrations": ("SMTP_*", "outlook_email_configuration", "inbound_pre_ticket_configuration"),
    "attachments-storage": ("ATTACHMENT_STORAGE_PATH",),
    "security-access": ("feature_policies",),
    "support-assistant": ("support_assistant_*",),
    "advanced": ("system_status", "database_backups"),
}


def category_version_key(category: str) -> str:
    return f"_site_settings_category_version_{category}"


def category_version(db: Session, category: str) -> int:
    row = db.get(SiteSetting, category_version_key(category))
    try:
        return max(1, int(row.value)) if row else 1
    except ValueError:
        return 1


def support_assistant_settings_values(db: Session) -> dict[str, object]:
    values = {
        row.key: row.value
        for row in db.scalars(
            select(SiteSetting).where(SiteSetting.key.like("support_assistant_%"))
        )
    }
    defaults = SupportAssistantSettings()
    return {
        "queue_refresh_seconds": int(
            values.get(
                "support_assistant_queue_refresh_seconds",
                defaults.queue_refresh_seconds,
            )
        ),
        "count_refresh_seconds": int(
            values.get(
                "support_assistant_count_refresh_seconds",
                defaults.count_refresh_seconds,
            )
        ),
        "unreceived_warning_minutes": int(
            values.get(
                "support_assistant_unreceived_warning_minutes",
                defaults.unreceived_warning_minutes,
            )
        ),
        "queue_tab_attention_enabled": values.get(
            "support_assistant_queue_tab_attention_enabled", "true"
        )
        == "true",
        "overdue_card_animation_enabled": values.get(
            "support_assistant_overdue_card_animation_enabled", "true"
        )
        == "true",
        "mine_show_resolved": values.get(
            "support_assistant_mine_show_resolved", "true"
        )
        == "true",
        "mine_show_closed": values.get(
            "support_assistant_mine_show_closed", "true"
        )
        == "true",
        "backlog_default_period": values.get(
            "support_assistant_backlog_default_period",
            defaults.backlog_default_period,
        ),
        "page_size": int(
            values.get("support_assistant_page_size", defaults.page_size)
        ),
        "allow_user_overrides": values.get(
            "support_assistant_allow_user_overrides", "true"
        )
        == "true",
        "tab_sorting": json.loads(
            values.get(
                "support_assistant_tab_sorting",
                json.dumps(defaults.tab_sorting),
            )
        ),
    }


@router.get("/site-settings/support-assistant", response_model=SiteSettingsCategoryRead)
def get_support_assistant_settings(
    db: Session = Depends(get_db),
    _: User = Depends(authenticated_user),
) -> SiteSettingsCategoryRead:
    return SiteSettingsCategoryRead(
        category="support-assistant",
        version=category_version(db, "support-assistant"),
        values=support_assistant_settings_values(db),
    )


@router.put("/site-settings/support-assistant", response_model=SiteSettingsCategoryRead)
def update_support_assistant_settings(
    data: SupportAssistantSettingsUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> SiteSettingsCategoryRead:
    current_version = category_version(db, "support-assistant")
    if data.expected_version != current_version:
        raise ConflictError(
            "SITE_SETTINGS_VERSION_CONFLICT",
            "Support Assistant settings changed after this page was loaded.",
        )
    before = support_assistant_settings_values(db)
    values = data.model_dump(exclude={"expected_version"})
    for key, value in values.items():
        stored = (
            json.dumps(value)
            if isinstance(value, dict)
            else str(value).lower()
            if isinstance(value, bool)
            else str(value)
        )
        setting_key = f"support_assistant_{key}"
        row = db.get(SiteSetting, setting_key)
        if row:
            row.value = stored
        else:
            db.add(SiteSetting(key=setting_key, value=stored))
    next_version = current_version + 1
    version_key = category_version_key("support-assistant")
    version_row = db.get(SiteSetting, version_key)
    if version_row:
        version_row.value = str(next_version)
    else:
        db.add(SiteSetting(key=version_key, value=str(next_version)))
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="SiteSettingsCategory",
            entity_id="support-assistant",
            action="site.settings.support_assistant.updated",
            old_values_json=json.dumps(before),
            new_values_json=json.dumps(values),
        )
    )
    db.commit()
    return SiteSettingsCategoryRead(
        category="support-assistant",
        version=next_version,
        values=support_assistant_settings_values(db),
    )


def persist_site_settings(data: SiteSettingsUpdate, db: Session) -> dict[str, object]:
    from app.modules.escalations.models import reschedule_escalation_work

    if data.default_assignee_user_id is not None:
        assignee = db.get(User, data.default_assignee_user_id)
        if not assignee or not assignee.is_active or assignee.user_type != "EMPLOYEE":
            raise ConflictError(
                "INVALID_DEFAULT_ASSIGNEE",
                "The default assignee must be an active employee.",
            )
    if data.sla_warning_support_team_ids:
        active_team_ids = set(db.scalars(select(SupportTeam.id).where(SupportTeam.id.in_(data.sla_warning_support_team_ids), SupportTeam.is_active.in_([True]))))
        if active_team_ids != set(data.sla_warning_support_team_ids):
            raise ConflictError("INVALID_SLA_WARNING_TEAM", "Every SLA warning recipient team must be active.")
        deliverable_team_ids = set(db.scalars(select(SupportTeamMember.team_id).join(User, User.id == SupportTeamMember.user_id).where(SupportTeamMember.team_id.in_(data.sla_warning_support_team_ids), User.is_active.in_([True]), User.support_notification_email.is_not(None))))
        if data.sla_warning_enabled and deliverable_team_ids != set(data.sla_warning_support_team_ids):
            raise ConflictError("SLA_WARNING_TEAM_WITHOUT_RECIPIENTS", "Every selected SLA warning team must have an active member with a Support Notification Email.")
    for key, value in data.model_dump().items():
        if key == "first_response_start_mode" and value is None:
            continue
        stored = "" if value is None else json.dumps(value) if isinstance(value, list) else str(value).lower() if isinstance(value, bool) else str(value)
        row = db.get(SiteSetting, key)
        if row:
            row.value = stored
        else:
            db.add(SiteSetting(key=key, value=stored))
    db.flush()
    reschedule_escalation_work(db)
    configure_server_clock(data.server_timezone, data.daylight_saving_enabled)
    if not data.sla_warning_enabled:
        db.execute(
            sql_update(EventOutbox)
            .where(
                EventOutbox.event_type.in_(["SLA_WARNING", "SLA_ESCALATED"]),
                EventOutbox.status.in_(["PENDING", "RETRY"]),
            )
            .values(status="SKIPPED", next_attempt_at=None)
        )
    return site_settings_values(db)

class PortalTicketEmailSettings(BaseModel):
    enabled: bool = False
    to: list[EmailStr] = Field(default_factory=lambda: ["support@millensys.com"])
    cc: list[EmailStr] = Field(default_factory=list)
    @model_validator(mode="after")
    def validate_enabled(self) -> "PortalTicketEmailSettings":
        if self.enabled and not self.to: raise ValueError("At least one To recipient is required when enabled.")
        normalized_to = list(dict.fromkeys(str(value).strip().lower() for value in self.to)); to_set = set(normalized_to)
        self.to = normalized_to
        self.cc = [value for value in dict.fromkeys(str(value).strip().lower() for value in self.cc) if value not in to_set]
        return self

class TicketNotificationTest(PortalTicketEmailSettings):
    subject_template: str = Field(default="[Support Hub] Test ticket notification", min_length=2, max_length=300)
    body_template: str = Field(default="This is a test of the ticket creation notification configuration.", min_length=2, max_length=10000)

class TicketNotificationTemplates(BaseModel):
    subject_template: str = Field(default="[Support Hub] New ticket {{ticket_number}} — {{ticket_title}}", min_length=2, max_length=300)
    body_template: str = Field(default="Ticket: {{ticket_number}}\nTitle: {{ticket_title}}\nDescription: {{description}}\nClient: {{client_name}}\nSource: {{source}}\nCreator: {{creator_name}}\nCreated: {{created_at}}", min_length=2, max_length=10000)
    version: int = Field(default=1, ge=1)

class TicketNotificationRuleWrite(BaseModel):
    name: str = Field(min_length=2, max_length=150); is_enabled: bool = False
    creator_profile_ids: list[int] = []; assigned_engineer_ids: list[int] = []
    match_mode: str = Field(default="ANY", pattern="^(ANY|ALL)$")
    to: list[EmailStr] = []; cc: list[EmailStr] = []
    include_matched_engineer_email: bool = False; evaluate_initial_assignment: bool = True; evaluate_later_reassignment: bool = False
    @model_validator(mode="after")
    def valid_rule(self) -> "TicketNotificationRuleWrite":
        if self.is_enabled and (not self.creator_profile_ids and not self.assigned_engineer_ids): raise ValueError("An enabled rule requires a profile or engineer condition.")
        if self.is_enabled and not self.to: raise ValueError("An enabled rule requires a To recipient.")
        return self

class TicketNotificationRuleRead(TicketNotificationRuleWrite):
    id: int; version: int


class TicketNotificationRuleUpdate(TicketNotificationRuleWrite):
    expected_version: int = Field(ge=1)


class VersionedDelete(BaseModel):
    expected_version: int = Field(ge=1)


def validate_notification_rule(db: Session, data: TicketNotificationRuleWrite, *, exclude_rule_id: int | None = None) -> None:
    duplicate = select(TicketNotificationRule.id).where(func.lower(TicketNotificationRule.name) == data.name.strip().lower(), TicketNotificationRule.is_deleted.in_([False]))
    if exclude_rule_id is not None:
        duplicate = duplicate.where(TicketNotificationRule.id != exclude_rule_id)
    if db.scalar(duplicate):
        raise ConflictError("NOTIFICATION_RULE_NAME_EXISTS", "An active ticket-notification rule already uses this name.")
    profile_ids = set(data.creator_profile_ids)
    if profile_ids != set(db.scalars(select(Profile.id).where(Profile.id.in_(profile_ids or {-1}), Profile.is_active.in_([True])))):
        raise ConflictError("INVALID_NOTIFICATION_RULE_PROFILE", "Every creator profile must be active.")
    engineer_ids = set(data.assigned_engineer_ids)
    if engineer_ids != set(db.scalars(select(User.id).where(User.id.in_(engineer_ids or {-1}), User.is_active.in_([True]), User.user_type == "EMPLOYEE"))):
        raise ConflictError("INVALID_NOTIFICATION_RULE_ENGINEER", "Every assigned engineer must be an active employee.")


def site_settings_values(db: Session) -> dict[str, object]:
    values = {row.key: row.value for row in db.scalars(select(SiteSetting))}
    return {
        "server_timezone": values.get("server_timezone", "Africa/Cairo"),
        "daylight_saving_enabled": values.get("daylight_saving_enabled", "true") == "true",
        "server_datetime": server_now().isoformat(),
        "default_theme": values.get("default_theme", "SYSTEM"),
        "default_sound": values.get("default_sound", "true") == "true",
        "default_assignee_user_id": int(values["default_assignee_user_id"]) if values.get("default_assignee_user_id") else None,
        "assign_available_only": values.get("assign_available_only", "false") == "true",
        "assign_online_only": values.get("assign_online_only", "false") == "true",
        "resolution_details_required_on_close": values.get(
            "resolution_details_required_on_close", "false"
        ) == "true",
        "first_response_start_mode": values.get("first_response_start_mode", "TICKET_CREATED"),
        "live_ticket_update_enabled": values.get("live_ticket_update_enabled", "true") == "true",
        "live_ticket_update_closed_poll_seconds": int(values.get("live_ticket_update_closed_poll_seconds", "300")),
        "satisfaction_manual_enabled": values.get("satisfaction_manual_enabled", "false") == "true",
        "satisfaction_whatsapp_enabled": values.get("satisfaction_whatsapp_enabled", "true") == "true",
        "satisfaction_email_enabled": values.get("satisfaction_email_enabled", "true") == "true",
        "satisfaction_token_expiry_days": int(values.get("satisfaction_token_expiry_days", "30")),
        "satisfaction_whatsapp_template": values.get("satisfaction_whatsapp_template", "Dear {client_name},\n\nPlease rate the service for ticket {ticket_number}:\n{rating_url}\n\nThis link expires on {expires_at}."),
        "satisfaction_email_subject": values.get("satisfaction_email_subject", "Rate support ticket {ticket_number}"),
        "satisfaction_email_body": values.get("satisfaction_email_body", "Dear {client_name},\n\nPlease rate the service for ticket {ticket_number}:\n{rating_url}\n\nThis link expires on {expires_at}."),
        "sla_warning_enabled": values.get("sla_warning_enabled", "true") == "true",
        "sla_response_warning_minutes": json.loads(values.get("sla_response_warning_minutes", "[60]")),
        "sla_resolution_warning_minutes": json.loads(values.get("sla_resolution_warning_minutes", "[240]")),
        "sla_warning_recipient_emails": json.loads(values.get("sla_warning_recipient_emails", "[]")),
        "sla_warning_support_team_ids": json.loads(values.get("sla_warning_support_team_ids", "[]")),
    }


@router.get("/site-settings")
def get_site_settings(db: Session = Depends(get_db), _: User = Depends(authenticated_user)) -> dict[str, object]:
    return site_settings_values(db)


@router.get("/time-settings")
def get_time_settings(db: Session = Depends(get_db)) -> dict[str, object]:
    """Expose the non-sensitive central clock to every UI, including public pages."""
    values = site_settings_values(db)
    return {
        "server_timezone": values["server_timezone"],
        "daylight_saving_enabled": values["daylight_saving_enabled"],
        "server_datetime": values["server_datetime"],
    }


@router.put("/site-settings/first-response-start-mode")
def update_first_response_start_mode(
    data: FirstResponseStartModeUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> dict[str, str]:
    key = "first_response_start_mode"
    row = db.get(SiteSetting, key)
    previous = row.value if row else "TICKET_CREATED"
    if row:
        row.value = data.mode
    else:
        db.add(SiteSetting(key=key, value=data.mode))
    db.add(AuditLog(
        actor_user_id=actor.id,
        entity_type="SiteSetting",
        entity_id=key,
        action="site.settings.first_response_start_mode.updated",
        old_values_json=json.dumps({"mode": previous}),
        new_values_json=json.dumps({"mode": data.mode}),
    ))
    db.commit()
    return {"mode": data.mode}


@router.get("/site-settings/categories")
def list_site_settings_categories(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("configuration.manage")),
) -> list[dict[str, object]]:
    persisted_keys = [
        row.key
        for row in db.scalars(select(SiteSetting).order_by(SiteSetting.key))
        if not row.key.startswith("_site_settings_category_version_")
    ]
    owned_keys: dict[str, list[str]] = {category: [] for category in SITE_SETTING_CATEGORIES}
    general_keys = set(SITE_SETTING_CATEGORIES["general"])
    for key in persisted_keys:
        if key in general_keys:
            owner = "general"
        elif key.startswith("portal_ticket_email_") or key.startswith("ticket_notification_template_"):
            owner = "ticket-notifications"
        elif key in {"outlook_email_configuration", "inbound_pre_ticket_configuration"}:
            owner = "third-party-integrations"
        elif key.startswith("support_assistant_"):
            owner = "support-assistant"
        else:
            owner = "advanced"
        owned_keys[owner].append(key)
    return [
        {
            "key": key,
            "managed_resources": list(setting_keys),
            "persisted_setting_keys": owned_keys[key],
        }
        for key, setting_keys in SITE_SETTING_CATEGORIES.items()
    ]


@router.get("/site-settings/categories/{category}", response_model=SiteSettingsCategoryRead)
def get_site_settings_category(
    category: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("configuration.manage")),
) -> SiteSettingsCategoryRead:
    if category not in SITE_SETTING_CATEGORIES:
        raise AppError("SITE_SETTINGS_CATEGORY_NOT_FOUND", "Site settings category does not exist.", 404)
    values = (
        site_settings_values(db)
        if category == "general"
        else support_assistant_settings_values(db)
        if category == "support-assistant"
        else {}
    )
    return SiteSettingsCategoryRead(category=category, version=category_version(db, category), values=values)


@router.put("/site-settings/categories/general", response_model=SiteSettingsCategoryRead)
def update_general_site_settings(
    data: GeneralSiteSettingsUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> SiteSettingsCategoryRead:
    current_version = category_version(db, "general")
    if data.expected_version != current_version:
        raise ConflictError(
            "SITE_SETTINGS_VERSION_CONFLICT",
            "General settings changed after this page was loaded. Reload and review the latest values.",
        )
    values = SiteSettingsUpdate.model_validate(data.model_dump(exclude={"expected_version"}))
    result = persist_site_settings(values, db)
    next_version = current_version + 1
    version_row = db.get(SiteSetting, category_version_key("general"))
    if version_row:
        version_row.value = str(next_version)
    else:
        db.add(SiteSetting(key=category_version_key("general"), value=str(next_version)))
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="SiteSettingsCategory",
            entity_id="general",
            action="site.settings.general.updated",
            old_values_json=json.dumps({"version": current_version}),
            new_values_json=json.dumps({"version": next_version, "values": result}),
        )
    )
    db.commit()
    return SiteSettingsCategoryRead(category="general", version=next_version, values=result)

@router.get("/ticket-notifications/portal", response_model=PortalTicketEmailSettings)
def get_portal_ticket_email(db: Session = Depends(get_db), _: User = Depends(require_permission("configuration.manage"))) -> PortalTicketEmailSettings:
    values = {row.key: row.value for row in db.scalars(select(SiteSetting).where(SiteSetting.key.like("portal_ticket_email_%")))}
    return PortalTicketEmailSettings(enabled=values.get("portal_ticket_email_enabled", "false") == "true", to=[x for x in values.get("portal_ticket_email_to", "support@millensys.com").split(",") if x], cc=[x for x in values.get("portal_ticket_email_cc", "").split(",") if x])

@router.put("/ticket-notifications/portal", response_model=PortalTicketEmailSettings)
def put_portal_ticket_email(data: PortalTicketEmailSettings, db: Session = Depends(get_db), actor: User = Depends(require_permission("configuration.manage"))) -> PortalTicketEmailSettings:
    before = get_portal_ticket_email(db, actor).model_dump(mode="json")
    values = {"portal_ticket_email_enabled": str(data.enabled).lower(), "portal_ticket_email_to": ",".join(map(str, data.to)), "portal_ticket_email_cc": ",".join(map(str, data.cc))}
    for key, value in values.items():
        row = db.get(SiteSetting, key)
        if row: row.value = value
        else: db.add(SiteSetting(key=key, value=value))
    db.add(AuditLog(actor_user_id=actor.id, entity_type="TicketNotifications", entity_id="portal", action="ticket.notifications.portal.updated", old_values_json=json.dumps(before), new_values_json=json.dumps(data.model_dump(mode="json"))))
    db.commit(); return data

@router.post("/ticket-notifications/test", status_code=202)
def test_ticket_notification(data: TicketNotificationTest, db: Session = Depends(get_db), actor: User = Depends(require_permission("configuration.manage"))) -> dict[str, object]:
    recipients = [str(value) for value in data.to]; cc = [str(value) for value in data.cc]
    db.add(EventOutbox(event_type="TICKET_CREATION_EMAIL", aggregate_type="TicketNotificationTest", aggregate_id=str(actor.id), deduplication_key=f"ticket-notification-test:{actor.id}:{server_now().isoformat()}", payload_json=json.dumps({"to": recipients, "cc": cc, "subject": data.subject_template, "body": data.body_template, "deep_link": "/tickets", "template_version": 1, "test": True})))
    db.commit(); return {"queued": True, "recipient_count": len(recipients) + len(cc)}

@router.get("/ticket-notifications/templates", response_model=TicketNotificationTemplates)
def get_ticket_notification_templates(db: Session = Depends(get_db), _: User = Depends(require_permission("configuration.manage"))) -> TicketNotificationTemplates:
    values = {row.key: row.value for row in db.scalars(select(SiteSetting).where(SiteSetting.key.like("ticket_notification_template_%")))}
    return TicketNotificationTemplates(subject_template=values.get("ticket_notification_template_subject", TicketNotificationTemplates().subject_template), body_template=values.get("ticket_notification_template_body", TicketNotificationTemplates().body_template), version=int(values.get("ticket_notification_template_version", "1")))

@router.put("/ticket-notifications/templates", response_model=TicketNotificationTemplates)
def put_ticket_notification_templates(data: TicketNotificationTemplates, db: Session = Depends(get_db), actor: User = Depends(require_permission("configuration.manage"))) -> TicketNotificationTemplates:
    before = get_ticket_notification_templates(db, actor); result = data.model_copy(update={"version": before.version + 1})
    for key, value in {"ticket_notification_template_subject": result.subject_template, "ticket_notification_template_body": result.body_template, "ticket_notification_template_version": str(result.version)}.items():
        row = db.get(SiteSetting, key)
        if row: row.value = value
        else: db.add(SiteSetting(key=key, value=value))
    db.add(AuditLog(actor_user_id=actor.id, entity_type="TicketNotificationTemplate", entity_id="creation", action="ticket.notification_template.updated", old_values_json=json.dumps(before.model_dump()), new_values_json=json.dumps(result.model_dump()))); db.commit(); return result

def rule_read(row: TicketNotificationRule) -> TicketNotificationRuleRead:
    return TicketNotificationRuleRead(id=row.id, version=row.version, name=row.name, is_enabled=row.is_enabled, creator_profile_ids=json.loads(row.creator_profile_ids_json), assigned_engineer_ids=json.loads(row.assigned_engineer_ids_json), match_mode=row.match_mode, to=json.loads(row.to_json), cc=json.loads(row.cc_json), include_matched_engineer_email=row.include_matched_engineer_email, evaluate_initial_assignment=row.evaluate_initial_assignment, evaluate_later_reassignment=row.evaluate_later_reassignment)

@router.get("/ticket-notifications/rules", response_model=list[TicketNotificationRuleRead])
def list_ticket_notification_rules(db: Session = Depends(get_db), _: User = Depends(require_permission("configuration.manage"))) -> list[TicketNotificationRuleRead]:
    return [rule_read(row) for row in db.scalars(select(TicketNotificationRule).where(TicketNotificationRule.is_deleted.in_([False])).order_by(TicketNotificationRule.name))]

@router.post("/ticket-notifications/rules", response_model=TicketNotificationRuleRead, status_code=201)
def create_ticket_notification_rule(data: TicketNotificationRuleWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("configuration.manage"))) -> TicketNotificationRuleRead:
    validate_notification_rule(db, data)
    values = data.model_dump(exclude={"name", "creator_profile_ids", "assigned_engineer_ids", "to", "cc"}); row = TicketNotificationRule(**values, name=data.name.strip(), creator_profile_ids_json=json.dumps(data.creator_profile_ids), assigned_engineer_ids_json=json.dumps(data.assigned_engineer_ids), to_json=json.dumps([str(x).lower() for x in data.to]), cc_json=json.dumps([str(x).lower() for x in data.cc]))
    db.add(row); db.flush(); db.add(AuditLog(actor_user_id=actor.id, entity_type="TicketNotificationRule", entity_id=str(row.id), action="ticket.notification_rule.created", new_values_json=json.dumps(data.model_dump(mode="json")))); db.commit(); db.refresh(row); return rule_read(row)

@router.put("/ticket-notifications/rules/{rule_id}", response_model=TicketNotificationRuleRead)
def update_ticket_notification_rule(rule_id: int, data: TicketNotificationRuleUpdate, db: Session = Depends(get_db), actor: User = Depends(require_permission("configuration.manage"))) -> TicketNotificationRuleRead:
    row = db.get(TicketNotificationRule, rule_id)
    if not row or row.is_deleted: raise ConflictError("NOTIFICATION_RULE_NOT_FOUND", "Ticket notification rule does not exist.")
    if row.version != data.expected_version: raise ConflictError("NOTIFICATION_RULE_VERSION_CONFLICT", "The notification rule changed after it was loaded. Reload and review the latest values.")
    validate_notification_rule(db, data, exclude_rule_id=rule_id)
    before = rule_read(row).model_dump(mode="json"); values = data.model_dump(exclude={"creator_profile_ids", "assigned_engineer_ids", "to", "cc", "expected_version"})
    for key, value in values.items(): setattr(row, key, value)
    row.name=data.name.strip(); row.creator_profile_ids_json=json.dumps(data.creator_profile_ids); row.assigned_engineer_ids_json=json.dumps(data.assigned_engineer_ids); row.to_json=json.dumps([str(x).lower() for x in data.to]); row.cc_json=json.dumps([str(x).lower() for x in data.cc]); row.version += 1
    db.add(AuditLog(actor_user_id=actor.id, entity_type="TicketNotificationRule", entity_id=str(row.id), action="ticket.notification_rule.updated", old_values_json=json.dumps(before), new_values_json=json.dumps(data.model_dump(mode="json")))); db.commit(); db.refresh(row); return rule_read(row)


@router.delete("/ticket-notifications/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket_notification_rule(rule_id: int, data: VersionedDelete, db: Session = Depends(get_db), actor: User = Depends(require_permission("configuration.manage"))) -> None:
    row = db.get(TicketNotificationRule, rule_id)
    if not row or row.is_deleted: raise ConflictError("NOTIFICATION_RULE_NOT_FOUND", "Ticket notification rule does not exist.")
    if row.version != data.expected_version: raise ConflictError("NOTIFICATION_RULE_VERSION_CONFLICT", "The notification rule changed after it was loaded. Reload and review the latest values.")
    before = rule_read(row).model_dump(mode="json")
    row.is_enabled = False; row.is_deleted = True; row.deleted_at = server_now(); row.deleted_by_user_id = actor.id; row.version += 1
    db.add(AuditLog(actor_user_id=actor.id, entity_type="TicketNotificationRule", entity_id=str(row.id), action="ticket.notification_rule.archived", old_values_json=json.dumps(before), new_values_json=json.dumps({"is_deleted": True, "version": row.version})))
    db.commit()


@router.put("/site-settings")
def update_site_settings(
    data: SiteSettingsUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> dict[str, object]:
    before = site_settings_values(db)
    result = persist_site_settings(data, db)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="SiteSettings", entity_id="public", action="site.settings.updated", old_values_json=json.dumps(before), new_values_json=json.dumps(data.model_dump())))
    db.commit()
    return result


@router.get("/configuration/storage")
def get_storage_configuration(
    _: User = Depends(require_permission("configuration.manage")),
) -> dict[str, object]:
    return read_storage_configuration()


@router.get("/configuration/local-ai")
def get_local_ai_configuration(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: User = Depends(require_permission("configuration.manage")),
) -> dict[str, object]:
    rows = {
        row.key: row.value
        for row in db.scalars(
            select(SiteSetting).where(
                SiteSetting.key.in_([
                    "local_ai_mode", "local_ai_folder", "local_ai_remote_base_url",
                    "local_ai_base_url", "local_ai_intake_instructions",
                    "local_ai_provider", "local_ai_model"
                ])
            )
        )
    }
    mode = rows.get("local_ai_mode", "LOCAL")
    remote_url = rows.get("local_ai_remote_base_url", "")
    local_folder = rows.get("local_ai_folder", "")
    environment = _local_ai_environment(local_folder) if mode == "LOCAL" and local_folder else {}
    provider = environment.get("AI_PROVIDER", rows.get("local_ai_provider", "OLLAMA")).upper()
    default_model = "gpt-6-luna" if provider == "OPENAI" else "qwen2.5:3b"
    model_key = "OPENAI_MODEL" if provider == "OPENAI" else "OLLAMA_MODEL"
    effective = "http://127.0.0.1:8090" if mode == "LOCAL" else (remote_url or settings.local_ai_base_url)
    return {
        "mode": mode,
        "local_folder": local_folder,
        "remote_base_url": remote_url,
        "intake_instructions": rows.get("local_ai_intake_instructions", ""),
        "provider": provider,
        "model": environment.get(model_key, rows.get("local_ai_model", default_model)),
        "api_key_configured": bool(environment.get("OPENAI_API_KEY")),
        "base_url": effective,
        "source": "SITE_SETTING" if rows else "ENVIRONMENT",
    }


@router.put("/configuration/local-ai")
def put_local_ai_configuration(
    data: LocalAiConfigurationUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> dict[str, object]:
    before = get_local_ai_configuration(db, get_settings(), actor)
    effective = "http://127.0.0.1:8090" if data.mode == "LOCAL" else str(data.remote_base_url)
    values = {
        "local_ai_mode": data.mode,
        "local_ai_folder": data.local_folder or "",
        "local_ai_remote_base_url": data.remote_base_url or "",
        "local_ai_base_url": effective,
        "local_ai_intake_instructions": data.intake_instructions.strip(),
        "local_ai_provider": data.provider,
        "local_ai_model": data.model,
    }
    if data.mode == "LOCAL" and data.local_folder:
        environment = _local_ai_environment(data.local_folder)
        saved_key = environment.get("OPENAI_API_KEY")
        if data.provider == "OPENAI" and not (data.api_key or saved_key):
            raise ConflictError("OPENAI_API_KEY_REQUIRED", "Enter an OpenAI API key.")
        _update_local_ai_environment(
            data.local_folder,
            provider=data.provider,
            model=data.model,
            api_key=data.api_key,
        )
    for key, value in values.items():
        row = db.get(SiteSetting, key)
        if row:
            row.value = value
        else:
            db.add(SiteSetting(key=key, value=value))
    db.add(AuditLog(actor_user_id=actor.id, entity_type="SiteSetting", entity_id="local_ai", action="local_ai.configuration.updated", old_values_json=json.dumps(before), new_values_json=json.dumps({**values, "api_key_changed": bool(data.api_key)})))
    db.commit()
    return {
        "mode": data.mode,
        "local_folder": data.local_folder or "",
        "remote_base_url": data.remote_base_url or "",
        "intake_instructions": data.intake_instructions.strip(),
        "provider": data.provider,
        "model": data.model,
        "api_key_configured": bool(data.api_key) or bool(before.get("api_key_configured")),
        "base_url": effective,
        "source": "SITE_SETTING",
    }


@router.get("/configuration/local-ai/folders")
def browse_local_ai_folders(
    path: str | None = Query(default=None, max_length=1000),
    _: User = Depends(require_permission("configuration.manage")),
) -> dict[str, object]:
    if not path:
        roots = [f"{letter}:\\" for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if Path(f"{letter}:\\").exists()] if os.name == "nt" else ["/"]
        return {"path": None, "parent": None, "directories": roots, "is_local_ai_folder": False}
    current = Path(path).expanduser()
    if not current.is_absolute() or not current.is_dir():
        raise ConflictError("INVALID_SERVER_FOLDER", "The selected server folder does not exist.")
    resolved = current.resolve()
    try:
        directories = sorted(str(item) for item in resolved.iterdir() if item.is_dir() and not item.name.startswith("."))
    except OSError as exc:
        raise ConflictError("SERVER_FOLDER_UNAVAILABLE", "The selected server folder cannot be browsed.") from exc
    return {
        "path": str(resolved),
        "parent": str(resolved.parent) if resolved.parent != resolved else None,
        "directories": directories[:500],
        "is_local_ai_folder": (resolved / "app" / "main.py").is_file() and (resolved / "run.bat").is_file(),
    }


@router.post("/configuration/local-ai/test")
async def test_local_ai_configuration(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: User = Depends(require_permission("configuration.manage")),
) -> dict[str, object]:
    configured = get_local_ai_configuration(db, settings, _)
    base_url = str(configured["base_url"]).rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{base_url}/ready")
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ConflictError("LOCAL_AI_CONNECTION_FAILED", "The configured Local AI service could not be reached.") from exc
    return {
        "connected": True,
        "base_url": base_url,
        "service": payload.get("service", "AI Gateway"),
        "provider": payload.get("provider"),
        "model": payload.get("model"),
    }


@router.put("/configuration/storage")
def put_storage_configuration(
    data: StorageConfigurationUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> dict[str, object]:
    before = read_storage_configuration()
    result = update_storage_configuration(data.attachment_storage_path)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ApplicationConfiguration", entity_id="ATTACHMENT_STORAGE_PATH", action="application.storage_path.updated", old_values_json=json.dumps({"attachment_storage_path": before["attachment_storage_path"]}), new_values_json=json.dumps({"attachment_storage_path": result["attachment_storage_path"]})))
    db.commit()
    return result

@router.get("/configuration/smtp")
def get_smtp_configuration(_: User = Depends(require_permission("configuration.manage"))) -> dict[str, object]:
    return read_smtp_configuration()

@router.put("/configuration/smtp")
def put_smtp_configuration(data: SmtpConfigurationUpdate, db: Session = Depends(get_db), actor: User = Depends(require_permission("configuration.manage"))) -> dict[str, object]:
    before = read_smtp_configuration(); result = update_smtp_configuration(data.model_dump())
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ApplicationConfiguration", entity_id="SMTP", action="application.smtp.updated", old_values_json=json.dumps(before), new_values_json=json.dumps({**data.model_dump(exclude={"password"}), "password_changed": bool(data.password)}))); db.commit(); return result

@router.post("/configuration/smtp/test")
def test_smtp_connection(actor: User = Depends(require_permission("configuration.manage")), settings: Settings = Depends(get_settings)) -> dict[str, object]:
    smtp_sender(settings)(actor.email, "SupportHub SMTP test", "SMTP delivery from Millensys SupportHub is working.")
    return {"sent": True, "recipient": actor.email}


@router.get("/configuration/email-delivery-status")
def email_delivery_status(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("configuration.manage")),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    outbox_counts: dict[str, int] = {status: count for status, count in db.execute(select(EventOutbox.status, func.count(EventOutbox.id)).group_by(EventOutbox.status)).tuples()}
    delivery_counts: dict[str, int] = {status: count for status, count in db.execute(select(EmailDelivery.status, func.count(EmailDelivery.id)).group_by(EmailDelivery.status)).tuples()}
    recent = db.execute(select(EmailDelivery, EventOutbox.created_at).join(EventOutbox, EventOutbox.id == EmailDelivery.outbox_id).order_by(EventOutbox.created_at.desc()).limit(20)).all()
    return {
        "smtp_enabled": settings.smtp_enabled,
        "frontend_base_url": settings.frontend_base_url,
        "allowed_domains_configured": bool(settings.password_reset_allowed_domains.strip()),
        "outbox": outbox_counts,
        "deliveries": delivery_counts,
        "recent": [{"recipient": row.recipient_email, "status": row.status, "attempt_count": row.attempt_count, "last_error": row.last_error, "requested_at": created_at, "sent_at": row.sent_at, "next_attempt_at": row.next_attempt_at} for row, created_at in recent],
    }


class TicketFormFieldUpdate(BaseModel):
    field_key: str
    is_visible: bool
    is_required: bool
    default_value: str | None = Field(default=None, max_length=150)


def serialize_ticket_field(setting: TicketFormFieldSetting) -> TicketFormFieldRead:
    definition = DEFINITIONS_BY_KEY[setting.field_key]
    return TicketFormFieldRead(
        field_key=setting.field_key,
        label=definition.label,
        section=definition.section,
        display_order=definition.order,
        is_visible=setting.is_visible if definition.can_hide else True,
        is_required=setting.is_required if definition.can_require else not definition.can_require and not definition.can_hide,
        can_hide=definition.can_hide,
        can_require=definition.can_require,
        can_default=definition.can_default,
        default_value=setting.default_value if definition.can_default else None,
        permission=definition.permission,
    )


def serialize_pre_ticket_field(setting: TicketFormFieldSetting) -> TicketFormFieldRead:
    definition = PRE_TICKET_DEFINITIONS_BY_KEY[setting.field_key]
    return TicketFormFieldRead(field_key=setting.field_key, label=definition.label, section=definition.section, display_order=definition.order, is_visible=True, is_required=setting.is_required, can_hide=False, can_require=True, can_default=False, default_value=None, permission=None)


@router.get("/pre-ticket-form-fields", response_model=list[TicketFormFieldRead])
def get_pre_ticket_form_fields(db: Session = Depends(get_db), _: User = Depends(require_permission("ticket.pre_ticket.create"))) -> list[TicketFormFieldRead]:
    rows = {item.field_key: item for item in db.scalars(select(TicketFormFieldSetting).where(TicketFormFieldSetting.field_key.like("pre_ticket.%")))}
    return [serialize_pre_ticket_field(rows[item.key]) for item in PRE_TICKET_FIELD_DEFINITIONS]


@router.put("/pre-ticket-form-fields", response_model=list[TicketFormFieldRead])
def update_pre_ticket_form_fields(updates: list[TicketFormFieldUpdate], db: Session = Depends(get_db), actor: User = Depends(require_permission("configuration.manage"))) -> list[TicketFormFieldRead]:
    if {item.field_key for item in updates} != set(PRE_TICKET_DEFINITIONS_BY_KEY):
        raise AppError("INVALID_PRE_TICKET_FORM_CONFIGURATION", "Submit every supported Pre-Ticket field exactly once.", 422)
    rows = {item.field_key: item for item in db.scalars(select(TicketFormFieldSetting).where(TicketFormFieldSetting.field_key.like("pre_ticket.%")))}
    old_values = {key: {"is_required": row.is_required} for key, row in rows.items()}
    for update in updates:
        rows[update.field_key].is_visible = True
        rows[update.field_key].is_required = update.is_required
    db.add(AuditLog(actor_user_id=actor.id, entity_type="PreTicketFormConfiguration", entity_id="global", action="pre_ticket_form.configuration.updated", old_values_json=json.dumps(old_values), new_values_json=json.dumps({key: {"is_required": row.is_required} for key, row in rows.items()})))
    db.commit()
    return [serialize_pre_ticket_field(rows[item.key]) for item in PRE_TICKET_FIELD_DEFINITIONS]


@router.get("/ticket-form-fields", response_model=list[TicketFormFieldRead])
def get_ticket_form_fields(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("ticket.create")),
) -> list[TicketFormFieldRead]:
    rows = {item.field_key: item for item in db.scalars(select(TicketFormFieldSetting))}
    return [serialize_ticket_field(rows[item.key]) for item in TICKET_FIELD_DEFINITIONS]


@router.put("/ticket-form-fields", response_model=list[TicketFormFieldRead])
def update_ticket_form_fields(
    updates: list[TicketFormFieldUpdate],
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> list[TicketFormFieldRead]:
    if {item.field_key for item in updates} != set(DEFINITIONS_BY_KEY):
        raise AppError(
            "INVALID_TICKET_FORM_CONFIGURATION",
            "Submit every supported ticket field exactly once.",
            422,
        )
    rows = {item.field_key: item for item in db.scalars(select(TicketFormFieldSetting))}
    requested_ticket_type = next(
        item.default_value for item in updates if item.field_key == "ticket_type_id"
    )
    if requested_ticket_type and not db.scalar(
        select(TicketType.id).where(
            TicketType.code == requested_ticket_type, TicketType.is_active.in_([True])
        )
    ):
        raise AppError(
            "INVALID_DEFAULT_TICKET_TYPE",
            "The default ticket type must be active.",
            422,
        )
    old_values: dict[str, dict[str, object]] = {}
    new_values: dict[str, dict[str, object]] = {}
    for update in updates:
        definition = DEFINITIONS_BY_KEY[update.field_key]
        row = rows[update.field_key]
        old_values[update.field_key] = {
            "is_visible": row.is_visible,
            "is_required": row.is_required,
            "default_value": row.default_value,
        }
        row.is_visible = update.is_visible if definition.can_hide else True
        row.is_required = update.is_required if definition.can_require else False
        if row.is_required:
            row.is_visible = True
        row.default_value = update.default_value if definition.can_default else None
        new_values[update.field_key] = {
            "is_visible": row.is_visible,
            "is_required": row.is_required,
            "default_value": row.default_value,
        }
    for child_key, parent_key in (
        ("product_module_id", "product_id"),
        ("subcategory_id", "category_id"),
    ):
        child = rows[child_key]
        parent = rows[parent_key]
        if child.is_visible:
            parent.is_visible = True
            new_values[parent_key]["is_visible"] = True
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketFormConfiguration",
            entity_id="global",
            action="ticket_form.configuration.updated",
            old_values_json=json.dumps(old_values),
            new_values_json=json.dumps(new_values),
        )
    )
    db.commit()
    return [serialize_ticket_field(rows[item.key]) for item in TICKET_FIELD_DEFINITIONS]


@router.get("/status")
def get_system_status(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: User = Depends(require_permission("configuration.manage")),
) -> dict[str, object]:
    return system_status(db, cast(Engine, db.get_bind()), settings)


@router.get("/backups")
def get_backups(
    settings: Settings = Depends(get_settings),
    _: User = Depends(require_permission("configuration.manage")),
) -> list[dict[str, object]]:
    return list_backups(settings)


@router.post("/backups", status_code=status.HTTP_201_CREATED)
def create_backup(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(require_permission("configuration.manage")),
) -> dict[str, object]:
    result = create_verified_backup(cast(Engine, db.get_bind()), settings)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="DatabaseBackup",
            entity_id=str(result["filename"]),
            action="database.backup.created",
            new_values_json=json.dumps(
                {"filename": result["filename"], "size_bytes": result["size_bytes"]}
            ),
        )
    )
    db.commit()
    return result
