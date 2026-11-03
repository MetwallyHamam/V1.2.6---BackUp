from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.core.clock import server_timezone
from app.modules.shifts.schemas import AssignmentStrategy, ScheduleRecurrence

OperationStatus = Literal["PLANNED", "PENDING_APPROVAL", "CHANGE_REQUESTED", "APPROVED", "SCHEDULED", "CONFIRMED", "IN_PROGRESS", "COMPLETED", "CANCELLED", "REJECTED"]


class OperationCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    operation_type: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,29}$")
    starts_at: datetime
    ends_at: datetime
    location: str | None = Field(default=None, max_length=300)
    client_id: int | None = None
    description: str | None = Field(default=None, max_length=5000)
    assignee_user_ids: list[int] = Field(min_length=1, max_length=100)
    template_id: int | None = None
    status: Literal["PLANNED", "SCHEDULED"] = "SCHEDULED"
    planned_window_start: datetime | None = None
    planned_window_end: datetime | None = None
    timezone: str = Field(default="Africa/Cairo", min_length=1, max_length=64)

    @model_validator(mode="after")
    def valid_period(self) -> "OperationCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("End time must be after start time.")
        self.starts_at = self.starts_at.astimezone(server_timezone())
        self.ends_at = self.ends_at.astimezone(server_timezone())
        self.assignee_user_ids = list(dict.fromkeys(self.assignee_user_ids))
        return self


class OperationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    status: OperationStatus | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = Field(default=None, max_length=300)
    client_id: int | None = None
    description: str | None = Field(default=None, max_length=5000)
    assignee_user_ids: list[int] | None = Field(default=None, min_length=1, max_length=100)


class PersonRead(BaseModel):
    id: int
    full_name: str
    department: str | None = None
    job_title: str | None = None


class ClientOptionRead(BaseModel):
    id: int
    code: str
    name: str


class CommentCreate(BaseModel):
    comment_type: Literal["COMMENT", "MOM", "MEETING_SUMMARY"] = "COMMENT"
    body: str = Field(min_length=2, max_length=10000)


class CommentRead(BaseModel):
    id: int
    author_user_id: int
    author_name: str
    comment_type: str
    body: str
    created_at: datetime


class DocumentRead(BaseModel):
    id: int
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_by_user_id: int
    uploaded_by_name: str
    created_at: datetime


class OperationRead(BaseModel):
    id: int
    title: str
    operation_type: str
    status: str
    starts_at: datetime
    ends_at: datetime
    location: str | None
    client_id: int | None
    client_code: str | None
    client_name: str | None
    description: str | None
    created_by_user_id: int
    created_by_name: str
    created_at: datetime
    updated_at: datetime
    assignees: list[PersonRead]
    comments: list[CommentRead] = []
    documents: list[DocumentRead] = []
    template_id: int | None = None
    visit_occurrence_id: int | None = None
    planned_window_start: datetime | None = None
    planned_window_end: datetime | None = None
    timezone: str = "Africa/Cairo"
    version: int = 1


class OperationTransitionWrite(BaseModel):
    to_status: OperationStatus
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=1000)


class OperationScheduleWrite(BaseModel):
    starts_at: datetime
    ends_at: datetime
    timezone: str = Field(min_length=1, max_length=64)
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=1000)

    @model_validator(mode="after")
    def valid_schedule(self) -> "OperationScheduleWrite":
        if self.ends_at <= self.starts_at:
            raise ValueError("End time must be after start time.")
        self.starts_at = self.starts_at.astimezone(server_timezone())
        self.ends_at = self.ends_at.astimezone(server_timezone())
        return self


class OperationTemplateWrite(BaseModel):
    name: str = Field(min_length=3, max_length=150)
    operation_type: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,29}$")
    department_id: int | None = None
    start_time: time
    end_time: time
    default_week_numbers: list[int] = Field(default_factory=lambda:[1,2,3,4], min_length=1, max_length=4)
    default_weekdays: list[int] = Field(default_factory=lambda:[6,0,1,2,3,4], min_length=1, max_length=7)
    week_start_day: int = Field(default=6, ge=0, le=6)
    effective_from: date | None = None
    effective_to: date | None = None
    location: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    is_active: bool = True
    default_duration_minutes: int | None = Field(default=None, ge=1, le=10080)
    default_status: Literal["PLANNED", "SCHEDULED"] = "SCHEDULED"
    recurrence_rule_json: str | None = Field(default=None, max_length=10000)
    required_fields_json: str | None = Field(default=None, max_length=10000)

    @model_validator(mode="after")
    def valid_defaults(self) -> "OperationTemplateWrite":
        if any(value not in range(1,5) for value in self.default_week_numbers) or any(value not in range(7) for value in self.default_weekdays):
            raise ValueError("Template week/day defaults are invalid.")
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("Date To must be on or after Date From.")
        self.default_week_numbers=list(dict.fromkeys(self.default_week_numbers));self.default_weekdays=list(dict.fromkeys(self.default_weekdays))
        return self


class OperationTemplateRead(OperationTemplateWrite):
    id: int
    code: str
    crosses_midnight: bool


class OperationTemplateApply(BaseModel):
    selection_mode: Literal["MONTHLY_PATTERN", "SPECIFIC_DATES", "DATE_RANGE"] = "MONTHLY_PATTERN"
    month: date | None = None
    user_ids: list[int] = Field(min_length=1,max_length=100)
    week_numbers: list[int] | None = None
    weekdays: list[int] | None = None
    week_start_day: int | None = Field(default=None,ge=0,le=6)
    specific_dates: list[date] = Field(default_factory=list, max_length=366)
    date_from: date | None = None
    date_to: date | None = None
    client_id: int | None = None

    @model_validator(mode="after")
    def valid_selection(self) -> "OperationTemplateApply":
        self.user_ids = list(dict.fromkeys(self.user_ids))
        self.specific_dates = sorted(set(self.specific_dates))
        if self.selection_mode == "MONTHLY_PATTERN" and self.month is None:
            raise ValueError("Monthly pattern requires a month.")
        if self.selection_mode == "SPECIFIC_DATES" and not self.specific_dates:
            raise ValueError("Select at least one specific date.")
        if self.selection_mode == "DATE_RANGE":
            if self.date_from is None or self.date_to is None or self.date_to < self.date_from:
                raise ValueError("Date range requires valid From and To dates.")
            if (self.date_to - self.date_from).days >= 366:
                raise ValueError("Date range cannot exceed 366 days.")
        return self


class OperationTemplateApplyResult(BaseModel):
    created: int
    skipped: int
    dates: list[date]


class OperationTypeWrite(BaseModel):
    name:str=Field(min_length=2,max_length=100)
    name_ar:str|None=Field(default=None,min_length=2,max_length=100)
    description:str|None=Field(default=None,max_length=1000)
    description_ar:str|None=Field(default=None,max_length=1000)
    color:str=Field(default="#7b1fa2",pattern=r"^#[0-9A-Fa-f]{6}$")
    supports_client:bool=False
    default_duration_minutes:int|None=Field(default=None,ge=1,le=10080)
    requires_client:bool=False
    visit_behavior:Literal["NONE","OPTIONAL","REQUIRED"]="NONE"
    completion_evidence_required:bool=False
    approval_policy:Literal["NEVER","WHEN_ALLOWANCE_EXHAUSTED","ALWAYS"]="NEVER"
    approver_profile_id:int|None=None
    is_active:bool=True


class OperationTypeRead(OperationTypeWrite):
    id:int
    code:str


class OperationGeneratorRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    operation_type: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,29}$")
    client_id: int | None = None
    start_time: time
    end_time: time
    recurrence: ScheduleRecurrence
    timezone: str = Field(default="Africa/Cairo", min_length=1, max_length=64)
    department_id: int | None = None
    required_headcount: int = Field(default=1, ge=1, le=100)
    assignment_strategy: AssignmentStrategy = "AUTO_BALANCE"
    rotation_id: int | None = None
    fixed_user_ids: list[int] = Field(default_factory=list, max_length=100)
    location: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    status: Literal["PLANNED", "SCHEDULED"] = "PLANNED"

    @model_validator(mode="after")
    def valid_assignment(self) -> "OperationGeneratorRequest":
        self.fixed_user_ids = list(dict.fromkeys(self.fixed_user_ids))
        if self.assignment_strategy == "FIXED" and not self.fixed_user_ids:
            raise ValueError("Fixed assignment requires employees.")
        if self.assignment_strategy == "ROTATION" and self.rotation_id is None:
            raise ValueError("Rotation assignment requires a rotation.")
        return self


class OperationGeneratorCandidateRead(BaseModel):
    employee_id: int
    employee_name: str
    assigned: bool
    available: bool
    shift_minutes: int
    operation_minutes: int
    visit_minutes: int
    reason: str


class OperationGeneratorSlotRead(BaseModel):
    slot_key: str
    date: date
    starts_at: datetime
    ends_at: datetime
    assigned_user_ids: list[int]
    assigned_user_names: list[str]
    unassigned_positions: int
    candidates: list[OperationGeneratorCandidateRead]
    entitlement_status: Literal["NOT_REQUIRED", "COVERED", "NO_ACTIVE_ENTITLEMENT", "ALLOWANCE_EXHAUSTED"]
    entitlement_id: int | None = None
    entitlement_sequence: int | None = None


class OperationGeneratorPreviewRead(BaseModel):
    preview_hash: str
    slot_count: int
    required_positions: int
    assigned_positions: int
    unassigned_positions: int
    conflict_count: int
    entitlement_issue_count: int
    workload_balance_percent: float
    slots: list[OperationGeneratorSlotRead]


class OperationGeneratorApply(BaseModel):
    request: OperationGeneratorRequest
    preview_hash: str = Field(min_length=64, max_length=64)


class OperationGeneratorApplyResult(BaseModel):
    batch_id: int
    created_operations: int
    created_visit_occurrences: int
    unassigned_positions: int
