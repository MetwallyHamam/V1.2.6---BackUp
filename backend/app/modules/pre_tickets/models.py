from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class EngineerPreTicket(Base):
    __tablename__ = "engineer_pre_tickets"
    __table_args__ = (
        CheckConstraint("status IN ('SUBMITTED','CLAIMED','NEEDS_INFORMATION','REJECTED','CANCELLED','CONVERTED')"),
        CheckConstraint("proposed_priority IN ('P1','P2','P3','P4')"),
        CheckConstraint("conversion_mode IS NULL OR conversion_mode IN ('CALL_CENTER','SELF_SERVICE')"),
        CheckConstraint("request_kind IN ('TICKET_REQUEST','CALL_REQUEST')"),
        Index("ix_engineer_pre_tickets_queue", "status", "submitted_at"),
        Index("ix_engineer_pre_tickets_submitter", "submitted_by_user_id", "submitted_at"),
        Index("uq_engineer_pre_ticket_result", "resulting_ticket_id", unique=True, mssql_where=text("resulting_ticket_id IS NOT NULL"), sqlite_where=text("resulting_ticket_id IS NOT NULL")),
        Index("uq_engineer_pre_ticket_submit_idempotency", "submitted_by_user_id", "idempotency_key", unique=True, mssql_where=text("idempotency_key IS NOT NULL"), sqlite_where=text("idempotency_key IS NOT NULL")),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    pre_ticket_number: Mapped[str | None] = mapped_column(String(40), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="SUBMITTED")
    request_kind: Mapped[str] = mapped_column(String(30), default="TICKET_REQUEST")
    source_provider: Mapped[str | None] = mapped_column(String(50))
    external_event_id: Mapped[str | None] = mapped_column(String(150))
    external_caller_name: Mapped[str | None] = mapped_column("external_requester_name", String(200))
    external_caller_number: Mapped[str | None] = mapped_column("external_phone_number", String(50))
    requested_ticket_type_code: Mapped[str | None] = mapped_column(String(30))
    client_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("clients.id"))
    branch_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("branches.id"))
    requester_contact_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contacts.id"))
    product_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("products.id"))
    product_module_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("product_modules.id"))
    service_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("service_catalog_items.id"))
    proposed_priority: Mapped[str] = mapped_column(String(5))
    title: Mapped[str] = mapped_column(String(300))
    initial_description: Mapped[str] = mapped_column(Text)
    enriched_description: Mapped[str | None] = mapped_column(Text)
    submitted_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    claimed_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    information_request: Mapped[str | None] = mapped_column(Text)
    engineer_response: Mapped[str | None] = mapped_column(Text)
    terminal_reason: Mapped[str | None] = mapped_column(String(1000))
    converted_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resulting_ticket_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("tickets.id"))
    conversion_mode: Mapped[str | None] = mapped_column(String(30))
    idempotency_key: Mapped[str | None] = mapped_column(String(200))
    request_fingerprint: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class PreTicketQueueView(Base):
    __tablename__ = "pre_ticket_queue_views"
    __table_args__ = (Index("uq_pre_ticket_queue_view_owner_name", "owner_user_id", "name", unique=True),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    search_text: Mapped[str | None] = mapped_column(String(100))
    status_filter: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
