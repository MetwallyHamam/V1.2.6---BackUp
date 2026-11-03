from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.clock import as_server_time


class VisitTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    internal_operation_type_id: int | None = None
    operation_type_code: str | None = None
    is_active: bool


class VisitTypeWrite(BaseModel):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,49}$")
    name: str = Field(min_length=2, max_length=150)
    internal_operation_type_id: int | None = None
    is_active: bool = True


class EntitlementCreate(BaseModel):
    contract_id: int
    client_id: int
    service_id: int | None = None
    visit_type_id: int | None = None
    service_period_start: date
    service_period_end: date
    allowed_visits: int = Field(ge=0, le=1000)
    recurrence: Literal["MONTHLY", "QUARTERLY", "SEMIANNUAL", "ANNUAL", "CUSTOM"]
    scheduling_mode: Literal["EXACT_DATE", "DATE_WINDOW", "ON_DEMAND"] = "DATE_WINDOW"
    default_duration_minutes: int = Field(default=120, ge=15, le=1440)
    department_id: int | None = None
    preferred_location_id: int | None = None
    carry_forward_limit: int = Field(default=0, ge=0, le=1000)

    @model_validator(mode="after")
    def valid_period(self) -> "EntitlementCreate":
        if self.service_period_end < self.service_period_start:
            raise ValueError("Service period end must not precede its start.")
        return self


class EntitlementBulkCreate(BaseModel):
    contract_id: int
    client_ids: list[int] = Field(min_length=1, max_length=200)
    service_id: int | None = None
    visit_type_id: int | None = None
    service_period_start: date
    service_period_end: date
    allowed_visits: int = Field(ge=0, le=1000)
    recurrence: Literal["MONTHLY", "QUARTERLY", "SEMIANNUAL", "ANNUAL", "CUSTOM"]
    scheduling_mode: Literal["EXACT_DATE", "DATE_WINDOW", "ON_DEMAND"] = "DATE_WINDOW"
    default_duration_minutes: int = Field(default=120, ge=15, le=1440)
    department_id: int | None = None
    preferred_location_id: int | None = None
    carry_forward_limit: int = Field(default=0, ge=0, le=1000)

    @model_validator(mode="after")
    def valid_period(self) -> "EntitlementBulkCreate":
        if self.service_period_end < self.service_period_start:
            raise ValueError("Service period end must not precede its start.")
        return self


class EntitlementRead(EntitlementCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    source_version: int
    version: int
    created_by_user_id: int
    created_at: datetime
    updated_at: datetime
    client_code: str | None = None
    client_name: str | None = None


class LedgerEntryCreate(BaseModel):
    entry_type: Literal[
        "ADJUSTMENT", "CARRY_FORWARD", "RESERVATION", "RELEASE", "EXPIRY", "OVERAGE", "REVERSAL"
    ]
    quantity: int = Field(ge=-1000, le=1000)
    idempotency_key: str = Field(min_length=8, max_length=200)
    source_type: str = Field(default="MANUAL", min_length=2, max_length=50)
    source_id: str | None = Field(default=None, max_length=100)
    reason: str = Field(min_length=5, max_length=1000)
    reversal_of_entry_id: int | None = None

    @model_validator(mode="after")
    def nonzero_quantity(self) -> "LedgerEntryCreate":
        if self.quantity == 0:
            raise ValueError("Ledger quantity cannot be zero.")
        return self


class LedgerEntryRead(LedgerEntryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entitlement_id: int
    created_by_user_id: int
    created_at: datetime


class OccurrenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entitlement_id: int
    contract_id: int
    client_id: int
    visit_type_id: int
    sequence_number: int
    window_start: date
    window_end: date
    due_date: date
    scheduled_visit_date: date | None
    actual_visit_date: date | None
    actual_started_at: datetime | None
    actual_ended_at: datetime | None
    status: str
    duration_minutes: int
    generation_key: str
    source_version: int
    source_type: str = "CONTRACT_RECURRING"
    ticket_id: int | None = None
    internal_operation_id: int | None = None
    notes: str | None
    result: str | None
    next_action: str | None
    outcome_code: str | None
    customer_acknowledged: bool
    customer_acknowledged_by: str | None
    customer_acknowledged_at: datetime | None
    completion_version: int
    completion_ledger_entry_id: int | None
    version: int
    client_code: str | None = None
    client_name: str | None = None


class OccurrenceComplete(BaseModel):
    actual_visit_date: date
    actual_started_at: datetime
    actual_ended_at: datetime
    outcome_code: Literal[
        "SUCCESSFUL", "UNSUCCESSFUL", "NO_SHOW", "CLIENT_CANCELLED", "SUPPORT_CANCELLED"
    ]
    result: str = Field(min_length=5, max_length=1000)
    next_action: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=2000)
    expected_version: int = Field(ge=1)
    allow_overage: bool = False
    customer_acknowledged: bool = False
    customer_acknowledged_by: str | None = Field(default=None, max_length=200)
    customer_acknowledged_at: datetime | None = None

    @model_validator(mode="after")
    def valid_completion(self) -> "OccurrenceComplete":
        if (
            self.actual_started_at.tzinfo is None
            or self.actual_ended_at.tzinfo is None
            or self.actual_ended_at <= self.actual_started_at
        ):
            raise ValueError("Actual visit timestamps require offsets and a positive duration.")
        if self.customer_acknowledged and (
            not self.customer_acknowledged_by or not self.customer_acknowledged_at
        ):
            raise ValueError("Customer acknowledgement requires a name and timestamp.")
        return self


class OccurrenceReverse(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)
    expected_version: int = Field(ge=1)


class OccurrenceStart(BaseModel):
    started_at: datetime
    expected_version: int = Field(ge=1)

    @model_validator(mode="after")
    def offset_required(self) -> "OccurrenceStart":
        if self.started_at.tzinfo is None:
            raise ValueError("Start timestamp requires an explicit offset.")
        return self


class OccurrenceCancel(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)
    expected_version: int = Field(ge=1)


class VisitDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    occurrence_id: int
    document_type: str
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    scan_status: str
    retention_until: date | None
    is_superseded: bool
    uploaded_by_user_id: int
    created_at: datetime


class EntitlementSummary(BaseModel):
    entitlement_id: int
    entitled: int
    planned: int
    scheduled: int
    completed: int
    consumed: int
    reserved: int
    remaining: int
    unplanned: int
    overdue: int


class GenerationExceptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entitlement_id: int
    exception_code: str
    detail: str
    source_version: int
    status: str
    created_at: datetime


class VisitScheduleWrite(BaseModel):
    starts_at: datetime
    ends_at: datetime
    timezone: str = Field(min_length=2, max_length=100)
    user_ids: list[int] = Field(min_length=1, max_length=50)
    expected_version: int = Field(ge=1)
    override_reason: str | None = Field(default=None, min_length=5, max_length=1000)
    shift_action: Literal["KEEP_AND_CREATE", "TRANSFER_AND_CREATE"] | None = None
    existing_shift_id: int | None = None
    replacement_user_id: int | None = None
    shift_decision_reason: str | None = Field(default=None, min_length=5, max_length=500)

    @model_validator(mode="after")
    def valid_schedule(self) -> "VisitScheduleWrite":
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("Planner timestamps require explicit timezone offsets.")
        self.starts_at = as_server_time(self.starts_at)
        self.ends_at = as_server_time(self.ends_at)
        if self.ends_at <= self.starts_at:
            raise ValueError("Visit end must follow its start.")
        if self.shift_action and not self.shift_decision_reason:
            raise ValueError("A reason is required for the shift decision.")
        if self.shift_action == "TRANSFER_AND_CREATE" and (
            not self.existing_shift_id or not self.replacement_user_id
        ):
            raise ValueError("Select the existing shift and its replacement engineer.")
        return self


class VisitAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    occurrence_id: int
    user_id: int
    starts_at: datetime
    ends_at: datetime
    timezone: str
    status: str
    stable_key: str
    conflict_codes: str | None
    override_reason: str | None
    version: int
    user_name: str | None = None


class PlannerOccurrenceRead(OccurrenceRead):
    assignments: list[VisitAssignmentRead]
    entitlement_remaining: int | None = None


class PlannerWorkloadRead(BaseModel):
    user_id: int
    user_name: str
    shift_count: int
    scheduled_shift_minutes: int
    visit_count: int
    scheduled_visit_minutes: int
    conflict_count: int


class BulkVisitRow(BaseModel):
    client_id: int
    contract_id: int
    entitlement_id: int | None = None
    visit_type_id: int | None = None
    starts_at: datetime
    ends_at: datetime
    timezone: str = Field(default="Africa/Cairo", min_length=2, max_length=100)
    user_ids: list[int] = Field(min_length=1, max_length=50)
    ticket_id: int | None = None
    internal_operation_id: int | None = None
    source_type: Literal["CONTRACT_RECURRING", "AD_HOC", "INTERNAL_OPERATION"] = "AD_HOC"
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def valid_period(self) -> "BulkVisitRow":
        if (
            self.starts_at.tzinfo is None
            or self.ends_at.tzinfo is None
            or self.ends_at <= self.starts_at
        ):
            raise ValueError("Visit timestamps require offsets and a positive duration.")
        self.user_ids = list(dict.fromkeys(self.user_ids))
        return self


class BulkVisitCreate(BaseModel):
    rows: list[BulkVisitRow] = Field(min_length=1, max_length=200)
    override_reason: str | None = Field(default=None, min_length=5, max_length=1000)


class BulkVisitResult(BaseModel):
    created: int
    occurrence_ids: list[int]


class SelfFieldVisitCreate(BaseModel):
    client_id: int
    starts_at: datetime
    ends_at: datetime
    timezone: str = Field(default="Africa/Cairo", min_length=2, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def valid_period(self) -> "SelfFieldVisitCreate":
        if (
            self.starts_at.tzinfo is None
            or self.ends_at.tzinfo is None
            or self.ends_at <= self.starts_at
        ):
            raise ValueError("Visit timestamps require offsets and a positive duration.")
        return self


class FieldVisitClientOption(BaseModel):
    id: int
    code: str
    name: str
