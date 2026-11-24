from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class WorkAssignment(Base):
    __tablename__ = "work_assignments"
    __table_args__ = (
        Index("ix_work_assignments_status_due", "status", "due_at"),
        Index("ix_work_assignments_owner_status", "owner_user_id", "status"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    assignment_type: Mapped[str] = mapped_column(String(40), default="GENERAL")
    activity_classification: Mapped[str] = mapped_column(String(20), default="EXTERNAL")
    context_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(30), default="ASSIGNED")
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    complexity: Mapped[str] = mapped_column(String(20), default="STANDARD")
    department_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("departments.id"))
    owner_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estimated_minutes: Mapped[int | None] = mapped_column(Integer)
    actual_minutes: Mapped[int | None] = mapped_column(Integer)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    completion_summary: Mapped[str | None] = mapped_column(Text)
    kpi_source_type: Mapped[str] = mapped_column(String(30), default="ASSIGNMENT")
    kpi_source_id: Mapped[int | None] = mapped_column(IdType)
    requires_review: Mapped[bool] = mapped_column(Boolean, default=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class WorkAssignmentAssignee(Base):
    __tablename__ = "work_assignment_assignees"
    __table_args__ = (UniqueConstraint("assignment_id", "user_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(IdType, ForeignKey("work_assignments.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(30), default="CONTRIBUTOR")
    contribution_percent: Mapped[int] = mapped_column(Integer, default=0)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class WorkAssignmentClient(Base):
    __tablename__ = "work_assignment_clients"
    __table_args__ = (UniqueConstraint("assignment_id", "client_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(IdType, ForeignKey("work_assignments.id", ondelete="CASCADE"))
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id"))
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    result_summary: Mapped[str | None] = mapped_column(Text)


class WorkAssignmentLink(Base):
    __tablename__ = "work_assignment_links"
    __table_args__ = (UniqueConstraint("assignment_id", "target_type", "target_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(IdType, ForeignKey("work_assignments.id", ondelete="CASCADE"))
    target_type: Mapped[str] = mapped_column(String(30))
    target_id: Mapped[int] = mapped_column(IdType)
    relation_type: Mapped[str] = mapped_column(String(30), default="RELATED")
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class WorkAssignmentEvent(Base):
    __tablename__ = "work_assignment_events"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(IdType, ForeignKey("work_assignments.id", ondelete="CASCADE"))
    actor_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(60))
    from_status: Mapped[str | None] = mapped_column(String(30))
    to_status: Mapped[str | None] = mapped_column(String(30))
    detail: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class WorkAssignmentShare(Base):
    __tablename__ = "work_assignment_shares"
    __table_args__ = (Index("ix_work_assignment_shares_token", "token_hash", unique=True),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(IdType, ForeignKey("work_assignments.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class WorkAssignmentEvidence(Base):
    __tablename__ = "work_assignment_evidence"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(IdType, ForeignKey("work_assignments.id", ondelete="CASCADE"))
    event_id: Mapped[int] = mapped_column(IdType, ForeignKey("work_assignment_events.id"))
    evidence_type: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(Text)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    stored_filename: Mapped[str | None] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(150))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    uploaded_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
