from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Responsibility = Literal["MILLENSYS", "CLIENT", "SHARED"]
EvidenceType = Literal["NONE", "COMMENT", "FILE", "VALUE", "CONFIRMATION", "LINK"]
ScheduleMode = Literal["SCHEDULED", "CLIENT_MANAGED_UNSCHEDULED"]


class TemplateItemWrite(BaseModel):
    item_code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    title: str = Field(min_length=2, max_length=200)
    resource_type: Literal[
        "DATABASE", "SYSTEM_FOLDER", "SERVICE", "REPORT", "PROFILE", "CUSTOM"
    ] = "CUSTOM"
    resource_path: str | None = Field(default=None, max_length=1000)
    instructions: str | None = Field(default=None, max_length=4000)
    display_order: int = Field(default=0, ge=0, le=10000)
    is_required: bool = True
    responsibility: Responsibility = "MILLENSYS"
    evidence_type: EvidenceType = "NONE"
    evidence_required: bool = False
    expected_duration_minutes: int | None = Field(default=None, ge=1, le=10080)

    @model_validator(mode="after")
    def validate_client_evidence(self) -> "TemplateItemWrite":
        if self.responsibility in {"CLIENT", "SHARED"} and (
            not self.evidence_required or self.evidence_type == "NONE"
        ):
            raise ValueError("Client or shared responsibility requires evidence.")
        return self


class TemplateCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    schedule_mode: ScheduleMode = "SCHEDULED"
    is_default: bool = False
    items: list[TemplateItemWrite] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def unique_codes(self) -> "TemplateCreate":
        codes = [item.item_code.upper() for item in self.items]
        if len(codes) != len(set(codes)):
            raise ValueError("Checklist item codes must be unique.")
        return self


class TemplateUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    schedule_mode: ScheduleMode
    is_default: bool = False
    items: list[TemplateItemWrite] = Field(min_length=1, max_length=200)
    version: int = Field(ge=1)

    @model_validator(mode="after")
    def unique_codes(self) -> "TemplateUpdate":
        codes = [item.item_code.upper() for item in self.items]
        if len(codes) != len(set(codes)):
            raise ValueError("Checklist item codes must be unique.")
        return self


class TemplateItemRead(TemplateItemWrite):
    id: int


class TemplateRead(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    schedule_mode: str
    version: int
    publication_status: str
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    items: list[TemplateItemRead]


class OccurrenceCreate(BaseModel):
    template_id: int
    client_id: int
    assigned_user_id: int | None = None
    scheduled_at: datetime
    due_at: datetime
    recurrence_days: int | None = Field(default=None, ge=1, le=366)

    @model_validator(mode="after")
    def valid_window(self) -> "OccurrenceCreate":
        if self.due_at <= self.scheduled_at:
            raise ValueError("Due time must be after the scheduled time.")
        return self


class OccurrenceItemRead(BaseModel):
    id: int
    item_code: str
    title: str
    resource_type: str
    resource_path: str | None
    check_date: datetime | None
    instructions: str | None
    display_order: int
    is_required: bool
    original_responsibility: str
    responsibility: str
    evidence_type: str
    evidence_required: bool
    state: str
    result_note: str | None
    evidence_reference: str | None
    evidence_id: int | None
    client_contact: str | None
    client_expected_at: datetime | None
    version: int


class OccurrenceRead(BaseModel):
    id: int
    occurrence_number: str
    template_id: int
    template_version: int
    template_name: str
    schedule_id: int | None
    ticket_id: int | None
    client_id: int
    client_name: str
    assigned_user_id: int | None
    assigned_user_name: str | None
    scheduled_at: datetime
    due_at: datetime
    recurrence_days: int | None
    status: str
    workflow_status: str
    effective_lane: str
    blocked_party: str | None
    blocked_reason: str | None
    follow_up_at: datetime | None
    completion_summary: str | None
    service_provided: str | None
    version: int
    required_complete: int
    required_total: int
    evidence_gaps: int
    items: list[OccurrenceItemRead] | None = None


class VersionAction(BaseModel):
    version: int = Field(ge=1)


class BlockAction(VersionAction):
    blocked_party: Literal["INTERNAL", "CLIENT"]
    reason: str = Field(min_length=3, max_length=2000)
    follow_up_at: datetime


class ItemCompleteAction(VersionAction):
    note: str | None = Field(default=None, max_length=4000)
    evidence_reference: str | None = Field(default=None, max_length=1000)
    evidence_id: int | None = None


class OccurrenceItemWrite(VersionAction):
    resource_type: Literal["DATABASE", "SYSTEM_FOLDER", "SERVICE", "REPORT", "PROFILE", "CUSTOM"]
    title: str = Field(min_length=2, max_length=200)
    resource_path: str | None = Field(default=None, max_length=1000)
    check_date: datetime
    status: Literal["PENDING", "COMPLETE", "NEED_ATTENTION", "CLIENT_RESPONSIBILITY"]


class OccurrenceItemDetailsUpdate(VersionAction):
    resource_type: Literal["DATABASE", "SYSTEM_FOLDER", "SERVICE", "REPORT", "PROFILE", "CUSTOM"]
    title: str = Field(min_length=2, max_length=200)
    resource_path: str | None = Field(default=None, max_length=1000)
    check_date: datetime


class OccurrenceItemCreate(BaseModel):
    resource_type: Literal["DATABASE", "SYSTEM_FOLDER", "SERVICE", "REPORT", "PROFILE", "CUSTOM"]
    title: str = Field(min_length=2, max_length=200)
    resource_path: str | None = Field(default=None, max_length=1000)
    check_date: datetime


class ClientHandoffAction(VersionAction):
    client_contact: str = Field(min_length=2, max_length=200)
    handoff_note: str = Field(min_length=3, max_length=4000)
    evidence_id: int
    evidence_reference: str | None = Field(default=None, max_length=1000)
    expected_at: datetime | None = None


class CompleteOccurrenceAction(VersionAction):
    service_provided: str = Field(min_length=3, max_length=4000)
    completion_summary: str = Field(min_length=3, max_length=4000)
    complete_eligible_remaining: bool = False


class CompletionPreview(BaseModel):
    can_complete: bool
    eligible_item_ids: list[int]
    blocking_items: list[str]
    client_handoffs: list[str]
    evidence_gaps: list[str]


class CompleteOccurrenceResult(BaseModel):
    occurrence: OccurrenceRead
    next_occurrence_id: int | None = None
    next_occurrence_number: str | None = None
    next_scheduled_at: datetime | None = None


class QuickCompleteItem(BaseModel):
    item_id: int
    choice: Literal["DONE", "NEEDS_ATTENTION", "CLIENT_ACTION"]
    resource_path: str | None = Field(default=None, max_length=1000)
    check_date: datetime
    note: str | None = Field(default=None, max_length=4000)
    evidence_reference: str | None = Field(default=None, max_length=1000)
    evidence_id: int | None = None
    client_contact: str | None = Field(default=None, max_length=200)
    create_follow_up_ticket: bool = False


class QuickCompleteAction(VersionAction):
    items: list[QuickCompleteItem] = Field(min_length=1, max_length=200)
    service_provided: str = Field(min_length=3, max_length=4000)
    completion_summary: str = Field(min_length=3, max_length=4000)
    complete: bool = True


class QuickCompleteResult(BaseModel):
    occurrence: OccurrenceRead
    follow_up_ticket_numbers: list[str] = Field(default_factory=list)
    next_occurrence_id: int | None = None
    next_occurrence_number: str | None = None
    next_scheduled_at: datetime | None = None


class EvidenceRead(BaseModel):
    id: int
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


class ReassignAction(VersionAction):
    assigned_user_id: int
    reason: str = Field(min_length=3, max_length=2000)


class CancelAction(VersionAction):
    reason: str = Field(min_length=3, max_length=2000)


class ScheduleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    template_id: int
    client_id: int
    assigned_user_id: int | None = None
    starts_at: datetime
    interval_days: int = Field(ge=1, le=366)
    duration_minutes: int = Field(ge=15, le=43200)
    timezone: str = Field(default="Africa/Cairo", min_length=3, max_length=100)


class ScheduleRead(ScheduleCreate):
    id: int
    next_generate_at: datetime
    is_active: bool
    is_paused: bool
    version: int
    client_name: str = ""
    template_name: str = ""
    assigned_user_name: str | None = None
    last_occurrence_id: int | None = None
    last_occurrence_number: str | None = None
    last_status: str | None = None
    last_workflow_status: str | None = None
    last_due_at: datetime | None = None
    last_completed_at: datetime | None = None
    last_required_complete: int = 0
    last_required_total: int = 0
    last_evidence_gaps: int = 0


class ScheduleStateAction(VersionAction):
    paused: bool


class ScheduleCadenceAction(VersionAction):
    interval_days: int = Field(ge=1, le=366)


class ScheduleReassignAction(VersionAction):
    assigned_user_id: int
    reason: str = Field(min_length=3, max_length=1000)


class BulkScheduleAssignAction(BaseModel):
    client_ids: list[int] = Field(min_length=1, max_length=500)
    assigned_user_id: int
    template_id: int
    starts_at: datetime
    interval_days: int = Field(ge=1, le=366)
    duration_minutes: int = Field(default=120, ge=15, le=43200)


class ScheduleTransferItem(BaseModel):
    schedule_id: int
    version: int


class BulkScheduleTransferAction(BaseModel):
    items: list[ScheduleTransferItem] = Field(min_length=1, max_length=500)
    assigned_user_id: int
    reason: str = Field(min_length=3, max_length=1000)


class BulkScheduleReminderAction(BaseModel):
    schedule_ids: list[int] = Field(min_length=1, max_length=500)


class SchedulePreview(BaseModel):
    scheduled_at: datetime
    due_at: datetime
    already_exists: bool


class ChecklistReport(BaseModel):
    total: int
    scheduled: int
    in_progress: int
    blocked: int
    overdue: int
    completed: int
    cancelled: int
    on_time_completed: int
    late_completed: int
    client_responsible_items: int
    evidence_gaps: int
