from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class MonitoringEvent(BaseModel):
    event_id: str = Field(min_length=1, max_length=150)
    alert_key: str = Field(min_length=1, max_length=200)
    client_id: int
    subject: str = Field(min_length=5, max_length=300)
    description: str = Field(min_length=10, max_length=20000)
    severity: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    occurred_at: datetime | None = None


class MonitoringResult(BaseModel):
    event_id: str
    ticket_id: int
    ticket_number: str
    duplicate: bool


class InboundEmailEvent(BaseModel):
    message_id: str = Field(min_length=1, max_length=150)
    from_address: EmailStr
    client_id: int
    subject: str = Field(min_length=5, max_length=300)
    body: str = Field(min_length=1, max_length=20000)
    ticket_number: str | None = Field(default=None, max_length=40)
    received_at: datetime | None = None


class InboundEmailResult(BaseModel):
    message_id: str
    ticket_id: int
    ticket_number: str
    action: str
    duplicate: bool


class ItopTicketImport(BaseModel):
    external_id: str = Field(min_length=1, max_length=150)
    client_id: int
    subject: str = Field(min_length=5, max_length=300)
    description: str = Field(min_length=1, max_length=20000)
    ticket_type_code: str = Field(default="INCIDENT", max_length=30)
    impact: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    urgency: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    original_status: str | None = Field(default=None, max_length=100)
    created_at: datetime | None = None


class ItopImportBatch(BaseModel):
    items: list[ItopTicketImport] = Field(min_length=1, max_length=500)


class ItopImportItemResult(BaseModel):
    external_id: str
    ticket_id: int
    ticket_number: str
    imported: bool


class ItopImportResult(BaseModel):
    imported: int
    skipped: int
    items: list[ItopImportItemResult]


class ApiClientCreate(BaseModel):
    name: str = Field(min_length=3, max_length=150)
    client_id: int | None = None
    provider_key: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9_-]{1,39}$")
    auth_type: str = Field(default="API_KEY", pattern="^(API_KEY|BASIC)$")
    username: str | None = Field(default=None, min_length=3, max_length=100, pattern=r"^[A-Za-z0-9._@-]+$")
    password: str | None = Field(default=None, min_length=12, max_length=128)

    @model_validator(mode="after")
    def basic_credentials_required(self) -> "ApiClientCreate":
        if self.auth_type == "BASIC" and (not self.username or not self.password):
            raise ValueError("Username and password are required for Basic authentication.")
        return self


class ApiClientCreated(BaseModel):
    id: int
    name: str
    client_id: int | None
    provider_key: str | None
    auth_type: str
    username: str | None = None
    api_key: str | None = None


class ApiTicketCreate(BaseModel):
    event_id: str = Field(min_length=1, max_length=120)
    client_id: int
    subject: str = Field(min_length=5, max_length=300)
    description: str = Field(min_length=10, max_length=20000)
    ticket_type_code: str = Field(default="INCIDENT", max_length=30)
    impact: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    urgency: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")


class ApiTicketResult(BaseModel):
    event_id: str
    ticket_id: int
    ticket_number: str
    duplicate: bool


class InboundFieldConfiguration(BaseModel):
    enabled: bool = True
    required: bool = False
    path: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def disabled_is_not_required(self) -> "InboundFieldConfiguration":
        if not self.enabled:
            self.required = False
        return self


def _default_inbound_fields() -> dict[str, InboundFieldConfiguration]:
    return {
        key: InboundFieldConfiguration(
            path=key,
            required=key in {"event_id", "request_type", "title"},
        )
        for key in ("event_id", "request_type", "client", "ticket_type", "title", "description", "caller_name", "caller_number")
    }


class InboundVendorProfile(BaseModel):
    name: str = Field(default="WhatsApp Business", min_length=2, max_length=100)
    provider_key: str = Field(default="whatsapp", pattern=r"^[a-z0-9][a-z0-9_-]{1,39}$")
    enabled: bool = False
    source_type: str = Field(default="WHATSAPP", pattern="^(WHATSAPP|MONITORING|EMAIL|API|OTHER)$")
    processing_mode: str = Field(default="PRE_TICKET", pattern="^(PRE_TICKET|DIRECT_TICKET)$")
    default_priority: str = Field(default="P3", pattern="^(P1|P2|P3|P4)$")
    default_ticket_type_code: str = Field(default="WHATSAPP", min_length=1, max_length=30)
    client_match_mode: str = Field(default="CODE_OR_EXACT_NAME", pattern="^(CODE|EXACT_NAME|CODE_OR_EXACT_NAME)$")
    fields: dict[str, InboundFieldConfiguration] = Field(default_factory=_default_inbound_fields)
    request_type_mapping: dict[str, str] = Field(default_factory=lambda: {
        "CREATE_TICKET": "CREATE_TICKET", "REQUEST_CALL": "REQUEST_CALL",
    })

    @field_validator("fields")
    @classmethod
    def valid_fields(cls, value: dict[str, InboundFieldConfiguration]) -> dict[str, InboundFieldConfiguration]:
        essential = {"event_id", "request_type", "title"}
        allowed = essential | {"client", "ticket_type", "description", "caller_name", "caller_number"}
        if not essential <= set(value) or not set(value) <= allowed:
            raise ValueError("Inbound field mapping is incomplete or contains unsupported fields.")
        for key in essential:
            value[key].enabled = True
            value[key].required = True
        return value

    @field_validator("request_type_mapping")
    @classmethod
    def valid_request_types(cls, value: dict[str, str]) -> dict[str, str]:
        normalized = {key.strip().upper(): mapped.strip().upper() for key, mapped in value.items() if key.strip()}
        if not normalized or any(mapped not in {"CREATE_TICKET", "REQUEST_CALL"} for mapped in normalized.values()):
            raise ValueError("Request type mappings must target CREATE_TICKET or REQUEST_CALL.")
        return normalized


class InboundPreTicketSettings(BaseModel):
    profiles: list[InboundVendorProfile] = Field(default_factory=lambda: [InboundVendorProfile()])

    @model_validator(mode="before")
    @classmethod
    def migrate_single_profile_settings(cls, value: object) -> object:
        if not isinstance(value, dict) or "profiles" in value:
            return value
        legacy = dict(value)
        expected_version = legacy.pop("expected_version", None)
        mapping = dict(legacy.pop("field_mapping", {}))
        if "customer_name" in mapping and "caller_name" not in mapping:
            mapping["caller_name"] = mapping.pop("customer_name")
        if "phone_number" in mapping and "caller_number" not in mapping:
            mapping["caller_number"] = mapping.pop("phone_number")
        required = {"event_id", "request_type", "client", "title"}
        legacy["fields"] = {
            key: {"path": path, "enabled": True, "required": key in required}
            for key, path in mapping.items()
        }
        legacy.setdefault("name", "WhatsApp Business")
        migrated: dict[str, object] = {"profiles": [legacy]}
        if expected_version is not None:
            migrated["expected_version"] = expected_version
        return migrated

    @field_validator("profiles")
    @classmethod
    def unique_profiles(cls, value: list[InboundVendorProfile]) -> list[InboundVendorProfile]:
        keys = [profile.provider_key for profile in value]
        if not value or len(keys) != len(set(keys)):
            raise ValueError("At least one uniquely keyed vendor profile is required.")
        return value


class InboundPreTicketSettingsUpdate(InboundPreTicketSettings):
    expected_version: int = Field(ge=1)


class InboundPreTicketResult(BaseModel):
    event_id: str
    pre_ticket_id: int | None = None
    pre_ticket_number: str | None = None
    ticket_id: int | None = None
    ticket_number: str | None = None
    request_type: str
    client_id: int | None
    client_match: str
    duplicate: bool


class InboundClientResult(BaseModel):
    code: str
    name: str
    is_active: bool


class InboundRequestStatus(BaseModel):
    event_id: str
    pre_ticket_id: int | None = None
    pre_ticket_number: str | None = None
    request_type: str
    status: str
    ticket_id: int | None
    ticket_number: str | None
    ticket_status_code: str | None = None
    ticket_status_name: str | None = None
    resolution_summary: str | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    ticket_updated_at: datetime | None = None
    updated_at: datetime


class ApiClientRead(BaseModel):
    id: int
    name: str
    key_prefix: str
    client_id: int | None
    provider_key: str | None
    auth_type: str = "API_KEY"
    username: str | None = None
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None
