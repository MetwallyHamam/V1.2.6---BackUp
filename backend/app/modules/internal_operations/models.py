from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy import (
    BigInteger,
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


class InternalOperationType(Base):
    __tablename__="internal_operation_types"
    id:Mapped[int]=mapped_column(IdType,primary_key=True,autoincrement=True)
    code:Mapped[str]=mapped_column(String(30),unique=True)
    name:Mapped[str]=mapped_column(String(100))
    name_ar:Mapped[str|None]=mapped_column(Unicode(100))
    description:Mapped[str|None]=mapped_column(String(1000))
    description_ar:Mapped[str|None]=mapped_column(Unicode(1000))
    color:Mapped[str]=mapped_column(String(20),default="#7b1fa2")
    supports_client:Mapped[bool]=mapped_column(default=False)
    default_duration_minutes:Mapped[int|None]=mapped_column(Integer)
    requires_client:Mapped[bool]=mapped_column(default=False)
    visit_behavior:Mapped[str]=mapped_column(String(20),default="NONE")
    completion_evidence_required:Mapped[bool]=mapped_column(default=False)
    approval_policy:Mapped[str]=mapped_column(String(40),default="NEVER")
    approver_profile_id:Mapped[int|None]=mapped_column(IdType,ForeignKey("profiles.id"))
    is_active:Mapped[bool]=mapped_column(default=True)


class InternalOperationTemplate(Base):
    __tablename__ = "internal_operation_templates"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    operation_type: Mapped[str] = mapped_column(String(30))
    operation_type_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("internal_operation_types.id"))
    department_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("departments.id"))
    start_time: Mapped[object] = mapped_column(Time)
    end_time: Mapped[object] = mapped_column(Time)
    crosses_midnight: Mapped[bool] = mapped_column(default=False)
    default_week_numbers_json: Mapped[str] = mapped_column(String(30), default="1,2,3,4")
    default_weekdays_json: Mapped[str] = mapped_column(String(30), default="6,0,1,2,3,4")
    week_start_day: Mapped[int] = mapped_column(Integer, default=6)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    location: Mapped[str | None] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    default_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    default_status: Mapped[str] = mapped_column(String(30), default="SCHEDULED")
    recurrence_rule_json: Mapped[str | None] = mapped_column(Text)
    required_fields_json: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)

    @property
    def default_week_numbers(self) -> list[int]:
        return [int(value) for value in self.default_week_numbers_json.split(",") if value]

    @property
    def default_weekdays(self) -> list[int]:
        return [int(value) for value in self.default_weekdays_json.split(",") if value]


class InternalOperation(Base):
    __tablename__ = "internal_operations"
    __table_args__ = (
        Index("ix_internal_operations_schedule", "operation_type", "starts_at", "status"),
        Index(
            "uq_internal_operation_visit_occurrence",
            "visit_occurrence_id",
            unique=True,
            mssql_where=sa.text("visit_occurrence_id IS NOT NULL"),
            sqlite_where=sa.text("visit_occurrence_id IS NOT NULL"),
        ),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    operation_type: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="SCHEDULED")
    template_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("internal_operation_templates.id"))
    visit_occurrence_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("client_visit_occurrences.id", name="fk_internal_operation_visit_occurrence", use_alter=True))
    planned_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planned_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(64), default="Africa/Cairo")
    version: Mapped[int] = mapped_column(Integer, default=1)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location: Mapped[str | None] = mapped_column(String(300))
    client_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("clients.id"))
    client_name: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    generation_batch_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("schedule_generation_batches.id"))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))


class InternalOperationAssignee(Base):
    __tablename__ = "internal_operation_assignees"
    __table_args__ = (UniqueConstraint("operation_id", "user_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    operation_id: Mapped[int] = mapped_column(IdType, ForeignKey("internal_operations.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class InternalOperationComment(Base):
    __tablename__ = "internal_operation_comments"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    operation_id: Mapped[int] = mapped_column(IdType, ForeignKey("internal_operations.id", ondelete="CASCADE"))
    author_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    comment_type: Mapped[str] = mapped_column(String(30), default="COMMENT")
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class InternalOperationDocument(Base):
    __tablename__ = "internal_operation_documents"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    operation_id: Mapped[int] = mapped_column(IdType, ForeignKey("internal_operations.id", ondelete="CASCADE"))
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(100), unique=True)
    content_type: Mapped[str] = mapped_column(String(150))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    uploaded_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
