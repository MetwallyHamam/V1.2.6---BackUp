from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Unicode,
    UnicodeText,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class ServiceChecklistTemplate(Base):
    __tablename__ = "service_checklist_templates"
    __table_args__ = (
        Index("ix_service_checklist_templates_active_mode", "is_active", "schedule_mode"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(Unicode(200))
    description: Mapped[str | None] = mapped_column(UnicodeText)
    schedule_mode: Mapped[str] = mapped_column(String(30), default="SCHEDULED")
    version: Mapped[int] = mapped_column(Integer, default=1)
    publication_status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ServiceChecklistTemplateItem(Base):
    __tablename__ = "service_checklist_template_items"
    __table_args__ = (
        UniqueConstraint("template_id", "item_code"),
        Index("ix_service_checklist_items_template_order", "template_id", "display_order"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("service_checklist_templates.id", ondelete="CASCADE")
    )
    item_code: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(Unicode(200))
    resource_type: Mapped[str] = mapped_column(String(30), default="CUSTOM")
    resource_path: Mapped[str | None] = mapped_column(Unicode(1000))
    instructions: Mapped[str | None] = mapped_column(UnicodeText)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    responsibility: Mapped[str] = mapped_column(String(20), default="MILLENSYS")
    evidence_type: Mapped[str] = mapped_column(String(20), default="NONE")
    evidence_required: Mapped[bool] = mapped_column(Boolean, default=False)
    expected_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ServiceChecklistOccurrence(Base):
    __tablename__ = "service_checklist_occurrences"
    __table_args__ = (
        UniqueConstraint("template_id", "client_id", "scheduled_at"),
        Index("ix_service_checklist_occurrence_board", "status", "due_at", "assigned_user_id"),
        Index("ix_service_checklist_occurrence_client", "client_id", "status"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    occurrence_number: Mapped[str] = mapped_column(String(30), unique=True)
    template_id: Mapped[int] = mapped_column(IdType, ForeignKey("service_checklist_templates.id"))
    template_version: Mapped[int] = mapped_column(Integer)
    template_name: Mapped[str] = mapped_column(Unicode(200))
    schedule_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("service_checklist_schedules.id", use_alter=True)
    )
    ticket_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("tickets.id"), unique=True)
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id"))
    assigned_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recurrence_days: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="SCHEDULED")
    blocked_party: Mapped[str | None] = mapped_column(String(20))
    blocked_reason: Mapped[str | None] = mapped_column(UnicodeText)
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completion_summary: Mapped[str | None] = mapped_column(UnicodeText)
    service_provided: Mapped[str | None] = mapped_column(UnicodeText)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ServiceChecklistOccurrenceItem(Base):
    __tablename__ = "service_checklist_occurrence_items"
    __table_args__ = (
        UniqueConstraint("occurrence_id", "item_code"),
        Index("ix_service_checklist_occurrence_items_order", "occurrence_id", "display_order"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    occurrence_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("service_checklist_occurrences.id", ondelete="CASCADE")
    )
    item_code: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(Unicode(200))
    resource_type: Mapped[str] = mapped_column(String(30), default="CUSTOM")
    resource_path: Mapped[str | None] = mapped_column(Unicode(1000))
    check_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    instructions: Mapped[str | None] = mapped_column(UnicodeText)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    original_responsibility: Mapped[str] = mapped_column(String(20))
    responsibility: Mapped[str] = mapped_column(String(20))
    evidence_type: Mapped[str] = mapped_column(String(20), default="NONE")
    evidence_required: Mapped[bool] = mapped_column(Boolean, default=False)
    state: Mapped[str] = mapped_column(String(30), default="PENDING")
    result_note: Mapped[str | None] = mapped_column(UnicodeText)
    evidence_reference: Mapped[str | None] = mapped_column(Unicode(1000))
    evidence_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("service_checklist_evidence.id", use_alter=True)
    )
    client_contact: Mapped[str | None] = mapped_column(Unicode(200))
    client_expected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)


class ServiceDeliveryRecord(Base):
    __tablename__ = "service_delivery_records"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    occurrence_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("service_checklist_occurrences.id"), unique=True
    )
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id"))
    occurrence_number: Mapped[str] = mapped_column(String(30))
    service_provided: Mapped[str] = mapped_column(UnicodeText)
    completion_summary: Mapped[str] = mapped_column(UnicodeText)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))


class ServiceChecklistEvidence(Base):
    __tablename__ = "service_checklist_evidence"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    occurrence_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("service_checklist_occurrences.id", ondelete="CASCADE")
    )
    original_filename: Mapped[str] = mapped_column(Unicode(255))
    stored_filename: Mapped[str] = mapped_column(String(100), unique=True)
    content_type: Mapped[str] = mapped_column(String(150))
    size_bytes: Mapped[int] = mapped_column(Integer)
    uploaded_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ServiceChecklistShareLink(Base):
    __tablename__ = "service_checklist_share_links"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    occurrence_id: Mapped[int] = mapped_column(
        IdType,
        ForeignKey("service_checklist_occurrences.id", ondelete="CASCADE"),
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ServiceChecklistSchedule(Base):
    __tablename__ = "service_checklist_schedules"
    __table_args__ = (
        UniqueConstraint("template_id", "client_id", "starts_at"),
        Index(
            "ix_service_checklist_schedule_generation", "is_active", "is_paused", "next_generate_at"
        ),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Unicode(200))
    template_id: Mapped[int] = mapped_column(IdType, ForeignKey("service_checklist_templates.id"))
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id"))
    assigned_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    next_generate_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    interval_days: Mapped[int] = mapped_column(Integer)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    timezone: Mapped[str] = mapped_column(String(100), default="Africa/Cairo")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
