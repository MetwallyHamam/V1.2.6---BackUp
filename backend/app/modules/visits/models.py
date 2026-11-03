from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class VisitType(Base):
    __tablename__ = "visit_types"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    internal_operation_type_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("internal_operation_types.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ClientVisitEntitlement(Base):
    __tablename__ = "client_visit_entitlements"
    __table_args__ = (Index("ix_visit_entitlement_scope_period", "contract_id", "client_id", "visit_type_id", "service_period_start", "service_period_end"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(IdType, ForeignKey("contracts.id"))
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id"))
    service_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("service_catalog_items.id"))
    visit_type_id: Mapped[int] = mapped_column(IdType, ForeignKey("visit_types.id"))
    service_period_start: Mapped[date] = mapped_column(Date)
    service_period_end: Mapped[date] = mapped_column(Date)
    allowed_visits: Mapped[int] = mapped_column(Integer)
    recurrence: Mapped[str] = mapped_column(String(30))
    scheduling_mode: Mapped[str] = mapped_column(String(20))
    default_duration_minutes: Mapped[int] = mapped_column(Integer)
    department_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("departments.id"))
    preferred_location_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("client_locations.id"))
    carry_forward_limit: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    source_version: Mapped[int] = mapped_column(Integer, default=1)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class VisitEntitlementLedgerEntry(Base):
    __tablename__ = "visit_entitlement_ledger_entries"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_visit_ledger_idempotency"), Index("ix_visit_ledger_entitlement_created", "entitlement_id", "created_at"))
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    entitlement_id: Mapped[int] = mapped_column(IdType, ForeignKey("client_visit_entitlements.id"))
    entry_type: Mapped[str] = mapped_column(String(30))
    quantity: Mapped[int] = mapped_column(Integer)
    idempotency_key: Mapped[str] = mapped_column(String(200))
    source_type: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[str | None] = mapped_column(String(100))
    reason: Mapped[str] = mapped_column(String(1000))
    reversal_of_entry_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("visit_entitlement_ledger_entries.id"))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ClientVisitOccurrence(Base):
    __tablename__ = "client_visit_occurrences"
    __table_args__ = (UniqueConstraint("generation_key", name="uq_visit_occurrence_generation"), Index("ix_visit_occurrence_window_status", "window_end", "status"))
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    entitlement_id: Mapped[int] = mapped_column(IdType, ForeignKey("client_visit_entitlements.id"))
    contract_id: Mapped[int] = mapped_column(IdType, ForeignKey("contracts.id"))
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id"))
    visit_type_id: Mapped[int] = mapped_column(IdType, ForeignKey("visit_types.id"))
    sequence_number: Mapped[int] = mapped_column(Integer)
    window_start: Mapped[date] = mapped_column(Date)
    window_end: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    scheduled_visit_date: Mapped[date | None] = mapped_column(Date)
    actual_visit_date: Mapped[date | None] = mapped_column(Date)
    actual_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="PLANNED")
    duration_minutes: Mapped[int] = mapped_column(Integer)
    generation_key: Mapped[str] = mapped_column(String(200))
    source_version: Mapped[int] = mapped_column(Integer)
    source_type: Mapped[str] = mapped_column(String(30), default="CONTRACT_RECURRING")
    ticket_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("tickets.id"))
    internal_operation_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("internal_operations.id"))
    notes: Mapped[str | None] = mapped_column(String(2000))
    result: Mapped[str | None] = mapped_column(String(1000))
    next_action: Mapped[str | None] = mapped_column(String(1000))
    outcome_code: Mapped[str | None] = mapped_column(String(30))
    customer_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    customer_acknowledged_by: Mapped[str | None] = mapped_column(String(200))
    customer_acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completion_version: Mapped[int] = mapped_column(Integer, default=0)
    completion_ledger_entry_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("visit_entitlement_ledger_entries.id"))
    superseded_by_occurrence_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("client_visit_occurrences.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class VisitGenerationException(Base):
    __tablename__ = "visit_generation_exceptions"
    __table_args__ = (UniqueConstraint("entitlement_id", "exception_code", "source_version", name="uq_visit_generation_exception"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    entitlement_id: Mapped[int] = mapped_column(IdType, ForeignKey("client_visit_entitlements.id"))
    exception_code: Mapped[str] = mapped_column(String(50))
    detail: Mapped[str] = mapped_column(String(1000))
    source_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ClientVisitAssignment(Base):
    __tablename__ = "client_visit_assignments"
    __table_args__ = (
        UniqueConstraint("occurrence_id", "user_id", name="uq_visit_assignment_user"),
        Index("ix_visit_assignment_user_period", "user_id", "starts_at", "ends_at"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    occurrence_id: Mapped[int] = mapped_column(IdType, ForeignKey("client_visit_occurrences.id"))
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="ASSIGNED")
    stable_key: Mapped[str] = mapped_column(String(200), unique=True)
    conflict_codes: Mapped[str | None] = mapped_column(String(1000))
    override_reason: Mapped[str | None] = mapped_column(String(1000))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class VisitCompletionEvidence(Base):
    __tablename__ = "visit_completion_evidence"
    __table_args__ = (UniqueConstraint("occurrence_id", "completion_version", name="uq_visit_completion_version"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    occurrence_id: Mapped[int] = mapped_column(IdType, ForeignKey("client_visit_occurrences.id"))
    completion_version: Mapped[int] = mapped_column(Integer)
    actual_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actual_ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    outcome_code: Mapped[str] = mapped_column(String(30))
    result: Mapped[str] = mapped_column(String(1000))
    next_action: Mapped[str | None] = mapped_column(String(1000))
    notes: Mapped[str | None] = mapped_column(String(2000))
    customer_acknowledged: Mapped[bool] = mapped_column(Boolean)
    customer_acknowledged_by: Mapped[str | None] = mapped_column(String(200))
    customer_acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class VisitDocument(Base):
    __tablename__ = "visit_documents"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    occurrence_id: Mapped[int] = mapped_column(IdType, ForeignKey("client_visit_occurrences.id"))
    document_type: Mapped[str] = mapped_column(String(30))
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(150))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    scan_status: Mapped[str] = mapped_column(String(30), default="NOT_SCANNED")
    retention_until: Mapped[date | None] = mapped_column(Date)
    is_superseded: Mapped[bool] = mapped_column(Boolean, default=False)
    uploaded_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
