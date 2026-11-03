from datetime import date, datetime, time
from datetime import date as DateType
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ShiftCreate(BaseModel):
    shift_type_id: int
    user_id: int
    team: str | None = Field(default=None, max_length=150)
    on_call_role: str | None = None
    work_location: str = Field(default="OFFICE", pattern="^(OFFICE|WORK_FROM_HOME|HYBRID)$")
    starts_at: datetime
    ends_at: datetime
    notes: str | None = Field(default=None, max_length=1000)
    overlap_override_reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def valid_period(self) -> "ShiftCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("Shift end must be after start.")
        return self


class ShiftUpdate(BaseModel):
    shift_type_id: int | None = None
    user_id: int | None = None
    team: str | None = Field(default=None, max_length=150)
    on_call_role: str | None = None
    work_location: str | None = Field(default=None, pattern="^(OFFICE|WORK_FROM_HOME|HYBRID)$")
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=1000)
    overlap_override_reason: str | None = Field(default=None, max_length=500)
    change_reason: str = Field(min_length=5, max_length=500)


class ShiftStatusUpdate(BaseModel):
    status: str = Field(pattern="^(DRAFT|PUBLISHED|APPROVED|COMPLETED|CANCELLED)$")
    reason: str = Field(min_length=5, max_length=500)


class ShiftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    shift_type_id: int
    user_id: int
    team: str | None
    on_call_role: str | None
    work_location: str
    starts_at: datetime
    ends_at: datetime
    notes: str | None
    status: str


class ShiftCalendarRead(ShiftRead):
    employee_name: str
    shift_name: str
    shift_color: str
    presence_status: Literal["ACTIVE", "IDLE", "OFFLINE"] | None = None
    last_seen_at: datetime | None = None


class ShiftEmployeeRead(BaseModel):
    id: int
    full_name: str
    department: str | None = None
    participates_in_shifts: bool = True


class ShiftTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    name_ar: str | None = None
    description: str | None = None
    description_ar: str | None = None
    color: str
    is_on_call: bool
    display_order: int = 0
    is_active: bool = True
    enforce_employee_eligibility: bool = False
    default_start_time: time
    default_end_time: time
    default_required_headcount: int = 1
    crosses_midnight: bool = False


class ShiftTypeWrite(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]+$", min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=100)
    name_ar: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    description_ar: str | None = Field(default=None, max_length=1000)
    color: str = Field(default="#145da0", pattern=r"^#[0-9A-Fa-f]{6}$")
    is_on_call: bool = False
    display_order: int = Field(default=0, ge=0, le=10000)
    is_active: bool = True
    enforce_employee_eligibility: bool = False
    default_start_time: time = time(9, 0)
    default_end_time: time = time(17, 0)
    default_required_headcount: int = Field(default=1, ge=1, le=100)


class QuickShiftCreate(BaseModel):
    date: DateType | None = None
    date_from: DateType | None = None
    date_to: DateType | None = None
    shift_type_id: int
    assignment_mode: Literal["MANUAL", "SUGGESTED", "AUTO_BALANCE"] = "MANUAL"
    user_ids: list[int] = Field(default_factory=list, max_length=100)
    timezone: str = Field(default="Africa/Cairo", min_length=2, max_length=100)
    notes: str | None = Field(default=None, max_length=1000)
    override_start_time: time | None = None
    override_end_time: time | None = None
    work_location: str = Field(default="OFFICE", pattern="^(OFFICE|WORK_FROM_HOME|HYBRID)$")
    team: str | None = Field(default=None, max_length=150)
    on_call_role: str | None = None
    overlap_override_reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def manual_selection_required(self) -> "QuickShiftCreate":
        self.date_from = self.date_from or self.date
        self.date_to = self.date_to or self.date_from
        if self.date_from is None or self.date_to is None:
            raise ValueError("Date From and Date To are required.")
        if self.date_to < self.date_from:
            raise ValueError("Date To must be on or after Date From.")
        if (self.date_to - self.date_from).days > 30:
            raise ValueError("Quick Shift date range may not exceed 31 days.")
        self.user_ids = list(dict.fromkeys(self.user_ids))
        if self.assignment_mode in {"MANUAL", "SUGGESTED"} and not self.user_ids:
            raise ValueError("Select at least one engineer.")
        if (self.override_start_time is None) != (self.override_end_time is None):
            raise ValueError("Override start and end times must be supplied together.")
        return self


class QuickShiftCreateResult(BaseModel):
    created: int
    required_headcount: int
    date_from: date
    date_to: date
    starts_at: datetime
    ends_at: datetime
    coverage_slot_id: int
    coverage_slot_ids: list[int]
    shifts: list[ShiftRead]


class ShiftPatternWrite(BaseModel):
    department_id: int
    shift_type_id: int
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]+$", min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=150)
    start_time: time
    end_time: time
    crosses_midnight: bool = False
    default_week_numbers: list[int] = Field(default_factory=lambda: [1, 2, 3, 4], min_length=1, max_length=4)
    default_weekdays: list[int] = Field(default_factory=lambda: [6, 0, 1, 2, 3, 4], min_length=1, max_length=7)
    week_start_day: int = Field(default=6, ge=0, le=6)
    effective_from: date | None = None
    effective_to: date | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def valid_defaults(self) -> "ShiftPatternWrite":
        if any(value not in range(1, 5) for value in self.default_week_numbers):
            raise ValueError("Default weeks must be between 1 and 4.")
        if any(value not in range(7) for value in self.default_weekdays):
            raise ValueError("Default weekdays must use Monday=0 through Sunday=6.")
        self.default_week_numbers = list(dict.fromkeys(self.default_week_numbers))
        self.default_weekdays = list(dict.fromkeys(self.default_weekdays))
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("Date To must be on or after Date From.")
        return self


class ShiftEligibilityRead(BaseModel):
    employee_id: int
    employee_name: str
    department: str | None = None
    shift_type_id: int
    shift_type_name: str
    is_eligible: bool


class ShiftEligibilityWrite(BaseModel):
    employee_id: int
    shift_type_id: int
    is_eligible: bool


class ShiftEligibilityBulkWrite(BaseModel):
    rows: list[ShiftEligibilityWrite] = Field(min_length=1, max_length=5000)


class ShiftCoverageSlotWrite(BaseModel):
    shift_type_id: int
    department_id: int | None = None
    team: str | None = Field(default=None, max_length=150)
    starts_at: datetime
    ends_at: datetime
    timezone: str = Field(default="Africa/Cairo", min_length=1, max_length=64)
    required_headcount: int = Field(default=1, ge=1, le=100)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def valid_slot(self) -> "ShiftCoverageSlotWrite":
        if self.ends_at <= self.starts_at:
            raise ValueError("Coverage slot end must be after start.")
        return self


class ShiftCoverageSlotRead(ShiftCoverageSlotWrite):
    id: int
    shift_type_name: str
    assigned_headcount: int
    coverage_percent: float
    coverage_status: Literal["FULL", "UNDERSTAFFED", "UNASSIGNED", "OVERSTAFFED"]
    assigned_user_ids: list[int]
    assigned_user_names: list[str]


class ShiftCoverageBulkDeleteRequest(BaseModel):
    slot_ids: list[int] = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=5, max_length=500)

    @model_validator(mode="after")
    def unique_slot_ids(self) -> "ShiftCoverageBulkDeleteRequest":
        if len(self.slot_ids) != len(set(self.slot_ids)):
            raise ValueError("A coverage slot may only be selected once.")
        return self


class ShiftCoverageBulkDeleteResult(BaseModel):
    deleted: int


class ShiftCoverageSummaryDay(BaseModel):
    date: date
    required_positions: int
    assigned_positions: int
    coverage_percent: float
    full_slots: int
    understaffed_slots: int
    unassigned_slots: int
    overstaffed_slots: int


AssignmentStrategy = Literal["MANUAL", "FIXED", "ROTATION", "AUTO_BALANCE", "KEEP_EXISTING"]


class AssignmentRotationMemberWrite(BaseModel):
    employee_id: int
    is_active: bool = True


class AssignmentRotationWrite(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    department_id: int | None = None
    team: str | None = Field(default=None, max_length=150)
    is_active: bool = True
    members: list[AssignmentRotationMemberWrite] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def unique_members(self) -> "AssignmentRotationWrite":
        ids = [row.employee_id for row in self.members]
        if len(ids) != len(set(ids)):
            raise ValueError("Rotation employees must be unique.")
        return self


class AssignmentRotationRead(AssignmentRotationWrite):
    id: int
    code: str


class ScheduleRecipeRowWrite(BaseModel):
    weekday: int = Field(ge=0, le=6)
    shift_type_id: int
    start_time: time
    end_time: time
    required_headcount: int = Field(default=1, ge=1, le=100)
    assignment_strategy: AssignmentStrategy | None = None
    rotation_id: int | None = None
    fixed_user_ids: list[int] = Field(default_factory=list, max_length=100)
    work_location: str = Field(default="OFFICE", pattern="^(OFFICE|WORK_FROM_HOME|HYBRID)$")
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def unique_fixed_users(self) -> "ScheduleRecipeRowWrite":
        self.fixed_user_ids = list(dict.fromkeys(self.fixed_user_ids))
        return self


class ScheduleRecipeWrite(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    department_id: int | None = None
    team: str | None = Field(default=None, max_length=150)
    timezone: str = Field(default="Africa/Cairo", min_length=1, max_length=64)
    assignment_strategy: AssignmentStrategy = "AUTO_BALANCE"
    rotation_id: int | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    is_active: bool = True
    rows: list[ScheduleRecipeRowWrite] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def valid_recipe(self) -> "ScheduleRecipeWrite":
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("Date To must be on or after Date From.")
        if self.assignment_strategy == "ROTATION" and self.rotation_id is None:
            raise ValueError("Rotation assignment requires a rotation.")
        if any(row.assignment_strategy == "ROTATION" and row.rotation_id is None and self.rotation_id is None for row in self.rows):
            raise ValueError("Every rotation row requires a row or recipe rotation.")
        return self


class ScheduleRecipeRowRead(ScheduleRecipeRowWrite):
    id: int
    crosses_midnight: bool


class ScheduleRecipeRead(BaseModel):
    id: int
    code: str
    name: str
    department_id: int | None
    team: str | None
    timezone: str
    assignment_strategy: AssignmentStrategy
    rotation_id: int | None
    effective_from: date | None
    effective_to: date | None
    is_active: bool
    rows: list[ScheduleRecipeRowRead]


class ScheduleRecurrence(BaseModel):
    frequency: Literal["ONCE", "DAILY", "WEEKLY", "EVERY_N_WEEKS", "MONTHLY", "QUARTERLY", "SPECIFIC_DATES", "CUSTOM"] = "WEEKLY"
    date_from: date
    date_to: date
    interval: int = Field(default=1, ge=1, le=52)
    weekdays: list[int] = Field(default_factory=list, max_length=7)
    specific_dates: list[date] = Field(default_factory=list, max_length=366)

    @model_validator(mode="after")
    def valid_recurrence(self) -> "ScheduleRecurrence":
        if self.date_to < self.date_from or (self.date_to-self.date_from).days >= 366:
            raise ValueError("Scheduling range must be ordered and cannot exceed 366 days.")
        if any(day not in range(7) for day in self.weekdays):
            raise ValueError("Weekdays must use Monday=0 through Sunday=6.")
        self.weekdays=list(dict.fromkeys(self.weekdays));self.specific_dates=sorted(set(self.specific_dates))
        if self.frequency == "SPECIFIC_DATES" and not self.specific_dates:
            raise ValueError("Specific Dates recurrence requires at least one date.")
        return self


class ShiftGeneratorRequest(BaseModel):
    recipe_id: int | None = None
    rows: list[ScheduleRecipeRowWrite] = Field(default_factory=list, max_length=200)
    recurrence: ScheduleRecurrence
    timezone: str = Field(default="Africa/Cairo", min_length=1, max_length=64)
    department_id: int | None = None
    team: str | None = Field(default=None, max_length=150)
    assignment_strategy: AssignmentStrategy = "AUTO_BALANCE"
    rotation_id: int | None = None
    fixed_user_ids: list[int] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def valid_source(self) -> "ShiftGeneratorRequest":
        if (self.recipe_id is None) == (not self.rows):
            raise ValueError("Select exactly one Schedule Recipe or provide generator rows.")
        if self.assignment_strategy == "ROTATION" and self.rotation_id is None and self.recipe_id is None:
            raise ValueError("Rotation assignment requires a rotation.")
        if self.assignment_strategy in {"FIXED", "MANUAL"} and not self.fixed_user_ids and not any(row.fixed_user_ids for row in self.rows):
            raise ValueError("Manual or fixed assignment requires employees.")
        self.fixed_user_ids=list(dict.fromkeys(self.fixed_user_ids))
        return self


class ShiftGeneratorCandidateRead(BaseModel):
    employee_id: int
    employee_name: str
    assigned: bool
    available: bool
    eligible: bool
    shift_minutes: int
    operation_minutes: int
    visit_minutes: int
    reason: str


class ShiftGeneratorSlotRead(BaseModel):
    slot_key: str
    date: date
    shift_type_id: int
    shift_type_name: str
    starts_at: datetime
    ends_at: datetime
    required_headcount: int
    work_location: str
    notes: str | None = None
    assigned_user_ids: list[int]
    assigned_user_names: list[str]
    unassigned_positions: int
    coverage_status: Literal["FULL", "UNDERSTAFFED", "UNASSIGNED"]
    candidates: list[ShiftGeneratorCandidateRead]


class ShiftGeneratorPreviewRead(BaseModel):
    preview_hash: str
    slot_count: int
    required_positions: int
    assignable_positions: int
    unassigned_positions: int
    conflict_count: int
    coverage_percent: float
    workload_balance_percent: float
    slots: list[ShiftGeneratorSlotRead]


class ShiftGeneratorApply(BaseModel):
    request: ShiftGeneratorRequest
    preview_hash: str = Field(min_length=64, max_length=64)


class ShiftGeneratorApplyResult(BaseModel):
    batch_id: int
    created_shifts: int
    created_coverage_slots: int
    unassigned_positions: int


class SchedulingWorkloadRead(BaseModel):
    employee_id: int
    employee_name: str
    department_id: int | None
    department_name: str | None
    department_name_ar: str | None = None
    shift_count: int
    shift_minutes: int
    operation_count: int
    operation_minutes: int
    visit_count: int
    visit_minutes: int
    total_minutes: int
    conflict_count: int
    participates_in_shifts: bool
    participates_in_operations: bool


class SchedulingAvailabilityRead(BaseModel):
    employee_id: int
    employee_name: str
    eligible: bool
    available: bool
    shift_conflict: bool
    operation_conflict: bool
    visit_conflict: bool
    shift_count: int
    shift_minutes: int
    operation_minutes: int
    visit_minutes: int
    reason: str


class QuickShiftContext(BaseModel):
    date: DateType
    date_to: DateType
    shift_type_id: int
    starts_at: datetime
    ends_at: datetime
    timezone: str
    required_headcount: int
    candidates: list[SchedulingAvailabilityRead]


class ShiftPatternRead(ShiftPatternWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ShiftDuplicateWeek(BaseModel):
    source_week_start: datetime
    target_week_start: datetime | None = None
    target_week_starts: list[datetime] = Field(default_factory=list, max_length=52)
    user_id: int | None = None
    skip_conflicts: bool = True
    assignment_mode: Literal["KEEP_ENGINEERS", "ROTATE_ENGINEERS", "AUTO_BALANCE"] = "KEEP_ENGINEERS"
    rotation_id: int | None = None
    preview_hash: str | None = Field(default=None, min_length=64, max_length=64)

    @model_validator(mode="after")
    def valid_targets(self) -> "ShiftDuplicateWeek":
        targets = [*self.target_week_starts]
        if self.target_week_start is not None:
            targets.append(self.target_week_start)
        self.target_week_starts = sorted(set(targets))
        if not self.target_week_starts:
            raise ValueError("Select at least one target week.")
        if self.assignment_mode == "ROTATE_ENGINEERS" and self.rotation_id is None:
            raise ValueError("Rotating engineers requires an assignment rotation.")
        return self


class ShiftDuplicatePreviewItem(BaseModel):
    source_shift_id: int
    target_week_start: datetime
    starts_at: datetime
    ends_at: datetime
    shift_type_id: int
    source_user_id: int
    assigned_user_id: int | None
    assigned_user_name: str | None
    status: Literal["READY", "CONFLICT", "NO_ELIGIBLE_EMPLOYEE"]
    reason: str


class ShiftDuplicatePreview(BaseModel):
    preview_hash: str
    source_count: int
    target_week_count: int
    ready: int
    conflicts: int
    unassigned: int
    items: list[ShiftDuplicatePreviewItem]


class ShiftDuplicateResult(BaseModel):
    created: int
    skipped: int


class ShiftPatternApply(BaseModel):
    selection_mode: Literal["MONTHLY_PATTERN", "SPECIFIC_DATES", "DATE_RANGE"] = "MONTHLY_PATTERN"
    month: date | None = None
    week_numbers: list[int] = Field(default_factory=list, max_length=4)
    weekdays: list[int] = Field(default_factory=list, max_length=7)
    week_start_day: int = Field(default=6, ge=0, le=6)
    specific_dates: list[date] = Field(default_factory=list, max_length=366)
    date_from: date | None = None
    date_to: date | None = None
    user_ids: list[int] = Field(default_factory=list, max_length=100)
    timezone: str = Field(default="Africa/Cairo", min_length=3, max_length=100)
    work_location: str = Field(default="OFFICE", pattern="^(OFFICE|WORK_FROM_HOME|HYBRID)$")
    skip_conflicts: bool = True

    @model_validator(mode="after")
    def normalize_selection(self) -> "ShiftPatternApply":
        if any(week not in range(1, 5) for week in self.week_numbers):
            raise ValueError("Week numbers must be between 1 and 4.")
        if any(day not in range(7) for day in self.weekdays):
            raise ValueError("Weekdays must use Monday=0 through Sunday=6.")
        self.week_numbers = list(dict.fromkeys(self.week_numbers))
        self.weekdays = list(dict.fromkeys(self.weekdays))
        self.specific_dates = sorted(set(self.specific_dates))
        self.user_ids = list(dict.fromkeys(self.user_ids))
        if self.selection_mode == "MONTHLY_PATTERN":
            if self.month is None or not self.week_numbers or not self.weekdays:
                raise ValueError("Monthly pattern requires a month, weeks, and weekdays.")
        elif self.selection_mode == "SPECIFIC_DATES":
            if not self.specific_dates:
                raise ValueError("Select at least one specific date.")
        else:
            if self.date_from is None or self.date_to is None:
                raise ValueError("Date range requires From and To dates.")
            if self.date_to < self.date_from:
                raise ValueError("Date range To date cannot be before From date.")
            if (self.date_to - self.date_from).days >= 366:
                raise ValueError("Date range cannot exceed 366 days.")
            if not self.weekdays:
                raise ValueError("Select at least one weekday for the date range.")
        return self


class ShiftPatternApplyResult(BaseModel):
    created: int
    skipped: int
    dates: list[date]


class ShiftRosterRowWrite(BaseModel):
    shift_type_id: int
    weekday: int = Field(ge=0, le=6)
    week_numbers: list[int] = Field(default_factory=lambda: [1, 2, 3, 4], min_length=1, max_length=4)
    start_time: time
    end_time: time
    work_location: str = Field(default="OFFICE", pattern="^(OFFICE|WORK_FROM_HOME|HYBRID)$")
    user_ids: list[int] = Field(default_factory=list, max_length=100)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def normalize_row(self) -> "ShiftRosterRowWrite":
        if any(week not in range(1, 5) for week in self.week_numbers):
            raise ValueError("Roster weeks must be between 1 and 4.")
        self.week_numbers = list(dict.fromkeys(self.week_numbers))
        self.user_ids = list(dict.fromkeys(self.user_ids))
        return self


class ShiftRosterTemplateWrite(BaseModel):
    department_id: int
    name: str = Field(min_length=2, max_length=150)
    week_start_day: int = Field(default=6, ge=0, le=6)
    effective_from: date | None = None
    effective_to: date | None = None
    rows: list[ShiftRosterRowWrite] = Field(min_length=1, max_length=100)
    is_active: bool = True

    @model_validator(mode="after")
    def valid_effective_period(self) -> "ShiftRosterTemplateWrite":
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("Date To must be on or after Date From.")
        return self


class ShiftRosterRowRead(ShiftRosterRowWrite):
    id: int


class ShiftRosterTemplateRead(BaseModel):
    id: int
    department_id: int
    code: str
    name: str
    week_start_day: int
    effective_from: date | None
    effective_to: date | None
    is_active: bool
    rows: list[ShiftRosterRowRead]


class ShiftRosterApply(BaseModel):
    month: date | None = None
    date_from: date | None = None
    date_to: date | None = None
    user_ids: list[int] = Field(default_factory=list, max_length=100)
    timezone: str = Field(default="Africa/Cairo", min_length=3, max_length=100)
    skip_conflicts: bool = True

    @model_validator(mode="after")
    def valid_period(self) -> "ShiftRosterApply":
        if self.month is None and (self.date_from is None or self.date_to is None):
            raise ValueError("Date From and Date To are required.")
        if self.date_from is not None and self.date_to is not None and self.date_to < self.date_from:
            raise ValueError("Date To must be on or after Date From.")
        self.user_ids = list(dict.fromkeys(self.user_ids))
        return self


class ShiftBulkDeleteFilter(BaseModel):
    user_id: int
    starts_at: datetime
    ends_at: datetime
    shift_type_id: int | None = None
    status: str | None = Field(default=None, pattern="^(DRAFT|PUBLISHED|APPROVED|COMPLETED|CANCELLED)$")

    @model_validator(mode="after")
    def valid_range(self) -> "ShiftBulkDeleteFilter":
        if self.ends_at <= self.starts_at:
            raise ValueError("Bulk-delete end must be after start.")
        return self


class ShiftBulkDeletePreview(BaseModel):
    matched: int
    protected: int
    deletable: int
    shift_ids: list[int]


class ShiftBulkDeleteRequest(ShiftBulkDeleteFilter):
    reason: str = Field(min_length=5, max_length=500)
    expected_count: int = Field(ge=0)


class ShiftBulkDeleteResult(BaseModel):
    deleted: int
    protected: int
