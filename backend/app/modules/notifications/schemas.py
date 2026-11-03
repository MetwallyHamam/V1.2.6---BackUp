from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    notification_type: str
    severity: str
    title: str
    message: str
    deep_link: str | None
    is_read: bool
    read_at: datetime | None
    acknowledged_at: datetime | None
    dismissed_at: datetime | None
    created_at: datetime


class NotificationBulkAction(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=100)


class RealtimeTicketRead(BaseModel):
    ticket: str
    expires_in: int


class NotificationPreferenceRead(BaseModel):
    sound_enabled: bool
    desktop_enabled: bool
    sound_code: str
    volume_percent: int


class NotificationPreferenceUpdate(BaseModel):
    sound_enabled: bool
    desktop_enabled: bool = False
    sound_code: Literal["CHIME", "BELL", "SOFT", "ALERT"] = "CHIME"
    volume_percent: int = Field(default=70, ge=0, le=100)


class NotificationViewCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    filters: dict[str, object]
    is_default: bool = False


class NotificationViewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    filters_json: str
    is_default: bool


class EscalationRuleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    clock_type: Literal["FIRST_RESPONSE", "RESOLUTION"]
    threshold_percent: int = Field(ge=1, le=100)
    priority: Literal["P1", "P2", "P3", "P4"] | None = None
    severity: Literal["INFO", "WARNING", "CRITICAL"]
    notify_assignee: bool = True
    notify_managers: bool = False
    is_active: bool = True


class EscalationRuleUpdate(EscalationRuleCreate):
    expected_version: int = Field(ge=1)


class EscalationRuleRead(EscalationRuleCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    version: int
    created_at: datetime
    updated_at: datetime
