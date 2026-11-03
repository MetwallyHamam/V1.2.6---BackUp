from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    Unicode,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class ShiftType(Base):
    __tablename__ = "shift_types"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    name_ar: Mapped[str | None] = mapped_column(Unicode(100))
    description: Mapped[str | None] = mapped_column(String(1000))
    description_ar: Mapped[str | None] = mapped_column(Unicode(1000))
    color: Mapped[str] = mapped_column(String(20), default="#145da0")
    is_on_call: Mapped[bool] = mapped_column(Boolean, default=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    enforce_employee_eligibility: Mapped[bool] = mapped_column(Boolean, default=False)
    default_start_time: Mapped[time] = mapped_column(Time, default=time(9, 0))
    default_end_time: Mapped[time] = mapped_column(Time, default=time(17, 0))
    default_required_headcount: Mapped[int] = mapped_column(Integer, default=1)

    @property
    def crosses_midnight(self) -> bool:
        return self.default_end_time <= self.default_start_time


class ShiftPattern(Base):
    __tablename__ = "shift_patterns"
    __table_args__ = (UniqueConstraint("department_id", "code", name="uq_shift_pattern_department_code"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    department_id: Mapped[int] = mapped_column(IdType, ForeignKey("departments.id"))
    shift_type_id: Mapped[int] = mapped_column(IdType, ForeignKey("shift_types.id"))
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(150))
    start_time: Mapped[object] = mapped_column(Time)
    end_time: Mapped[object] = mapped_column(Time)
    crosses_midnight: Mapped[bool] = mapped_column(Boolean, default=False)
    default_week_numbers_json: Mapped[str] = mapped_column(String(30), default="1,2,3,4")
    default_weekdays_json: Mapped[str] = mapped_column(String(30), default="6,0,1,2,3,4")
    week_start_day: Mapped[int] = mapped_column(Integer, default=6)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)

    @property
    def default_week_numbers(self) -> list[int]:
        return [int(value) for value in self.default_week_numbers_json.split(",") if value]

    @property
    def default_weekdays(self) -> list[int]:
        return [int(value) for value in self.default_weekdays_json.split(",") if value]


class ShiftRosterTemplate(Base):
    __tablename__ = "shift_roster_templates"
    __table_args__ = (UniqueConstraint("department_id", "code", name="uq_shift_roster_department_code"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    department_id: Mapped[int] = mapped_column(IdType, ForeignKey("departments.id"))
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(150))
    week_start_day: Mapped[int] = mapped_column(Integer, default=6)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ShiftRosterRow(Base):
    __tablename__ = "shift_roster_rows"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(IdType, ForeignKey("shift_roster_templates.id", ondelete="CASCADE"))
    shift_type_id: Mapped[int] = mapped_column(IdType, ForeignKey("shift_types.id"))
    weekday: Mapped[int] = mapped_column(Integer)
    week_numbers_json: Mapped[str] = mapped_column(String(30), default="1,2,3,4")
    start_time: Mapped[object] = mapped_column(Time)
    end_time: Mapped[object] = mapped_column(Time)
    crosses_midnight: Mapped[bool] = mapped_column(Boolean, default=False)
    work_location: Mapped[str] = mapped_column(String(20), default="OFFICE")
    notes: Mapped[str | None] = mapped_column(String(1000))
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    @property
    def week_numbers(self) -> list[int]:
        return [int(value) for value in self.week_numbers_json.split(",") if value]


class ShiftRosterRowAssignee(Base):
    __tablename__ = "shift_roster_row_assignees"
    __table_args__ = (UniqueConstraint("row_id", "user_id", name="uq_shift_roster_row_user"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    row_id: Mapped[int] = mapped_column(IdType, ForeignKey("shift_roster_rows.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))


class EmployeeShiftEligibility(Base):
    __tablename__ = "employee_shift_eligibilities"
    __table_args__ = (
        UniqueConstraint("employee_id", "shift_type_id", name="uq_employee_shift_eligibility"),
        Index("ix_employee_shift_eligibility_lookup", "employee_id", "shift_type_id"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    shift_type_id: Mapped[int] = mapped_column(IdType, ForeignKey("shift_types.id", ondelete="CASCADE"))
    is_eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ShiftCoverageSlot(Base):
    __tablename__ = "shift_coverage_slots"
    __table_args__ = (
        UniqueConstraint("shift_type_id", "department_id", "team", "starts_at", "ends_at", name="uq_shift_coverage_slot_scope_period"),
        Index("ix_shift_coverage_slots_period", "starts_at", "ends_at"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    shift_type_id: Mapped[int] = mapped_column(IdType, ForeignKey("shift_types.id"))
    department_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("departments.id"))
    team: Mapped[str | None] = mapped_column(String(150))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(64), default="Africa/Cairo")
    required_headcount: Mapped[int] = mapped_column(Integer, default=1)
    source_type: Mapped[str] = mapped_column(String(30), default="MANUAL")
    source_id: Mapped[int | None] = mapped_column(IdType)
    notes: Mapped[str | None] = mapped_column(String(1000))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class AssignmentRotation(Base):
    __tablename__ = "assignment_rotations"
    __table_args__ = (UniqueConstraint("code", name="uq_assignment_rotation_code"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(150))
    department_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("departments.id"))
    team: Mapped[str | None] = mapped_column(String(150))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class AssignmentRotationMember(Base):
    __tablename__ = "assignment_rotation_members"
    __table_args__ = (UniqueConstraint("rotation_id", "employee_id", name="uq_assignment_rotation_member"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    rotation_id: Mapped[int] = mapped_column(IdType, ForeignKey("assignment_rotations.id", ondelete="CASCADE"))
    employee_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    sort_order: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ScheduleRecipe(Base):
    __tablename__ = "schedule_recipes"
    __table_args__ = (UniqueConstraint("code", name="uq_schedule_recipe_code"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(150))
    department_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("departments.id"))
    team: Mapped[str | None] = mapped_column(String(150))
    timezone: Mapped[str] = mapped_column(String(64), default="Africa/Cairo")
    assignment_strategy: Mapped[str] = mapped_column(String(30), default="AUTO_BALANCE")
    rotation_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("assignment_rotations.id"))
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ScheduleRecipeRow(Base):
    __tablename__ = "schedule_recipe_rows"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    recipe_id: Mapped[int] = mapped_column(IdType, ForeignKey("schedule_recipes.id", ondelete="CASCADE"))
    weekday: Mapped[int] = mapped_column(Integer)
    shift_type_id: Mapped[int] = mapped_column(IdType, ForeignKey("shift_types.id"))
    start_time: Mapped[object] = mapped_column(Time)
    end_time: Mapped[object] = mapped_column(Time)
    crosses_midnight: Mapped[bool] = mapped_column(Boolean, default=False)
    required_headcount: Mapped[int] = mapped_column(Integer, default=1)
    assignment_strategy: Mapped[str | None] = mapped_column(String(30))
    rotation_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("assignment_rotations.id"))
    work_location: Mapped[str] = mapped_column(String(20), default="OFFICE")
    notes: Mapped[str | None] = mapped_column(String(1000))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ScheduleGenerationBatch(Base):
    __tablename__ = "schedule_generation_batches"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    module: Mapped[str] = mapped_column(String(30))
    source_type: Mapped[str] = mapped_column(String(30))
    source_id: Mapped[int | None] = mapped_column(IdType)
    date_from: Mapped[date] = mapped_column(Date)
    date_to: Mapped[date] = mapped_column(Date)
    recurrence_json: Mapped[str] = mapped_column(Text)
    assignment_mode: Mapped[str] = mapped_column(String(30))
    required_positions: Mapped[int] = mapped_column(Integer, default=0)
    created_assignments: Mapped[int] = mapped_column(Integer, default=0)
    unassigned_positions: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    conflict_count: Mapped[int] = mapped_column(Integer, default=0)
    preview_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="APPLIED")
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Shift(Base):
    __tablename__ = "shifts"
    __table_args__ = (Index("ix_shifts_user_start_end", "user_id", "starts_at", "ends_at"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    shift_type_id: Mapped[int] = mapped_column(IdType, ForeignKey("shift_types.id"))
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    team: Mapped[str | None] = mapped_column(String(150))
    on_call_role: Mapped[str | None] = mapped_column(String(20))
    work_location: Mapped[str] = mapped_column(String(20), default="OFFICE")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(String(1000))
    overlap_override_reason: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    generation_batch_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("schedule_generation_batches.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Handover(Base):
    __tablename__ = "handovers"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    shift_id: Mapped[int] = mapped_column(IdType, ForeignKey("shifts.id", ondelete="CASCADE"))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
