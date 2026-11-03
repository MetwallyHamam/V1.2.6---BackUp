from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class TicketCommercialDecision(Base):
    __tablename__ = "ticket_commercial_decisions"
    __table_args__ = (
        UniqueConstraint("ticket_id", "sequence", name="uq_ticket_commercial_decision_sequence"),
        Index("ix_ticket_commercial_decision_ticket_created", "ticket_id", "created_at"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    sequence: Mapped[int] = mapped_column(Integer)
    chargeability: Mapped[str] = mapped_column(String(30))
    approval_status: Mapped[str] = mapped_column(String(30))
    estimated_amount: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    quoted_amount: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    currency: Mapped[str] = mapped_column(String(3))
    reason: Mapped[str] = mapped_column(String(1000))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TicketFinanceLedgerEntry(Base):
    __tablename__ = "ticket_finance_ledger_entries"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_ticket_finance_ledger_idempotency"),
        Index("ix_ticket_finance_ledger_ticket_occurred", "ticket_id", "occurred_at"),
        Index("ix_ticket_finance_ledger_type_status", "entry_type", "status"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    idempotency_key: Mapped[str] = mapped_column(String(200))
    entry_type: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30))
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    currency: Mapped[str] = mapped_column(String(3))
    payment_method: Mapped[str | None] = mapped_column(String(30))
    external_reference: Mapped[str | None] = mapped_column(String(200))
    reason: Mapped[str] = mapped_column(String(1000))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reversal_of_entry_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("ticket_finance_ledger_entries.id"))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ContractFinanceProfile(Base):
    __tablename__ = "contract_finance_profiles"
    contract_id: Mapped[int] = mapped_column(IdType, ForeignKey("contracts.id"), primary_key=True)
    currency: Mapped[str] = mapped_column(String(3))
    contract_value: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(9, 6), default=Decimal())
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), default=Decimal())
    billing_model: Mapped[str] = mapped_column(String(30))
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=0)
    billing_frequency: Mapped[str] = mapped_column(String(20), default="ANNUAL")
    billing_day: Mapped[int] = mapped_column(Integer, default=1)
    invoice_amount: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    purchase_order_reference: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(String(1000))
    updated_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ContractBillingSchedule(Base):
    __tablename__ = "contract_billing_schedules"
    __table_args__ = (UniqueConstraint("contract_id", "installment_number", name="uq_contract_billing_installment"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(IdType, ForeignKey("contracts.id"))
    installment_number: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String(300))
    due_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(30), default="PLANNED")
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ContractInvoice(Base):
    __tablename__ = "contract_invoices"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_contract_invoice_idempotency"), Index("ix_contract_invoice_due", "contract_id", "due_date", "status"))
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(IdType, ForeignKey("contracts.id"))
    schedule_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contract_billing_schedules.id"))
    idempotency_key: Mapped[str] = mapped_column(String(200))
    document_type: Mapped[str] = mapped_column(String(20))
    invoice_number: Mapped[str] = mapped_column(String(100))
    issued_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(30))
    reversal_of_invoice_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contract_invoices.id"))
    reason: Mapped[str] = mapped_column(String(1000))
    imported_unverified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ContractReceipt(Base):
    __tablename__ = "contract_receipts"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_contract_receipt_idempotency"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(IdType, ForeignKey("contracts.id"))
    idempotency_key: Mapped[str] = mapped_column(String(200))
    receipt_reference: Mapped[str] = mapped_column(String(200))
    received_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(30))
    reversal_of_receipt_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contract_receipts.id"))
    reason: Mapped[str] = mapped_column(String(1000))
    imported_unverified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ContractReceiptAllocation(Base):
    __tablename__ = "contract_receipt_allocations"
    __table_args__ = (UniqueConstraint("receipt_id", "invoice_id", name="uq_contract_receipt_invoice_allocation"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    receipt_id: Mapped[int] = mapped_column(IdType, ForeignKey("contract_receipts.id"))
    invoice_id: Mapped[int] = mapped_column(IdType, ForeignKey("contract_invoices.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    currency: Mapped[str] = mapped_column(String(3))
    is_reversal: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str] = mapped_column(String(1000))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FinanceAdjustmentReason(Base):
    __tablename__ = "finance_adjustment_reasons"
    __table_args__ = (UniqueConstraint("code", name="uq_finance_adjustment_reason_code"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(150))
    adjustment_type: Mapped[str] = mapped_column(String(20), default="DISCOUNT")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ContractCollection(Base):
    __tablename__ = "contract_collections"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_contract_collection_idempotency"),
        Index("ix_contract_collection_invoice_date", "invoice_id", "collected_date"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(IdType, ForeignKey("contracts.id"))
    invoice_id: Mapped[int] = mapped_column(IdType, ForeignKey("contract_invoices.id"))
    idempotency_key: Mapped[str] = mapped_column(String(200))
    reference: Mapped[str | None] = mapped_column(String(200))
    collected_date: Mapped[date] = mapped_column(Date)
    invoice_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    actual_payment: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), default=Decimal())
    additional_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), default=Decimal())
    adjustment_reason_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("finance_adjustment_reasons.id"))
    adjustment_notes: Mapped[str | None] = mapped_column(String(1000))
    currency: Mapped[str] = mapped_column(String(3))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
