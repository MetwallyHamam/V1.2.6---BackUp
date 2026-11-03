"""Add optional contract finance ledgers.

Revision ID: 0100_contract_finance
Revises: 0099_coverage_renewals
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import table_exists

revision = "0100_contract_finance"
down_revision = "0099_coverage_renewals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    ident = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    if not table_exists(bind, "contract_finance_profiles"):
        op.create_table("contract_finance_profiles", sa.Column("contract_id", ident, sa.ForeignKey("contracts.id"), primary_key=True), sa.Column("currency", sa.String(3), nullable=False), sa.Column("contract_value", sa.Numeric(19,4)), sa.Column("tax_rate", sa.Numeric(9,6), nullable=False, server_default="0"), sa.Column("discount_amount", sa.Numeric(19,4), nullable=False, server_default="0"), sa.Column("billing_model", sa.String(30), nullable=False), sa.Column("payment_terms_days", sa.Integer(), nullable=False, server_default="0"), sa.Column("purchase_order_reference", sa.String(200)), sa.Column("notes", sa.String(1000)), sa.Column("updated_by_user_id", ident, sa.ForeignKey("users.id"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()))
    if not table_exists(bind, "contract_billing_schedules"):
        op.create_table("contract_billing_schedules", sa.Column("id", ident, primary_key=True, autoincrement=True), sa.Column("contract_id", ident, sa.ForeignKey("contracts.id"), nullable=False), sa.Column("installment_number", sa.Integer(), nullable=False), sa.Column("description", sa.String(300), nullable=False), sa.Column("due_date", sa.Date(), nullable=False), sa.Column("amount", sa.Numeric(19,4), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("created_by_user_id", ident, sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.UniqueConstraint("contract_id", "installment_number", name="uq_contract_billing_installment"))
    if not table_exists(bind, "contract_invoices"):
        op.create_table("contract_invoices", sa.Column("id", ident, primary_key=True, autoincrement=True), sa.Column("contract_id", ident, sa.ForeignKey("contracts.id"), nullable=False), sa.Column("schedule_id", ident, sa.ForeignKey("contract_billing_schedules.id")), sa.Column("idempotency_key", sa.String(200), nullable=False), sa.Column("document_type", sa.String(20), nullable=False), sa.Column("invoice_number", sa.String(100), nullable=False), sa.Column("issued_date", sa.Date(), nullable=False), sa.Column("due_date", sa.Date(), nullable=False), sa.Column("subtotal", sa.Numeric(19,4), nullable=False), sa.Column("tax_amount", sa.Numeric(19,4), nullable=False), sa.Column("total_amount", sa.Numeric(19,4), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("reversal_of_invoice_id", ident, sa.ForeignKey("contract_invoices.id")), sa.Column("reason", sa.String(1000), nullable=False), sa.Column("imported_unverified", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("created_by_user_id", ident, sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.UniqueConstraint("idempotency_key", name="uq_contract_invoice_idempotency"))
        op.create_index("ix_contract_invoice_due", "contract_invoices", ["contract_id", "due_date", "status"])
    if not table_exists(bind, "contract_receipts"):
        op.create_table("contract_receipts", sa.Column("id", ident, primary_key=True, autoincrement=True), sa.Column("contract_id", ident, sa.ForeignKey("contracts.id"), nullable=False), sa.Column("idempotency_key", sa.String(200), nullable=False), sa.Column("receipt_reference", sa.String(200), nullable=False), sa.Column("received_date", sa.Date(), nullable=False), sa.Column("amount", sa.Numeric(19,4), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("reversal_of_receipt_id", ident, sa.ForeignKey("contract_receipts.id")), sa.Column("reason", sa.String(1000), nullable=False), sa.Column("imported_unverified", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("created_by_user_id", ident, sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.UniqueConstraint("idempotency_key", name="uq_contract_receipt_idempotency"))
    if not table_exists(bind, "contract_receipt_allocations"):
        op.create_table("contract_receipt_allocations", sa.Column("id", ident, primary_key=True, autoincrement=True), sa.Column("receipt_id", ident, sa.ForeignKey("contract_receipts.id"), nullable=False), sa.Column("invoice_id", ident, sa.ForeignKey("contract_invoices.id"), nullable=False), sa.Column("amount", sa.Numeric(19,4), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("is_reversal", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("reason", sa.String(1000), nullable=False), sa.Column("created_by_user_id", ident, sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.UniqueConstraint("receipt_id", "invoice_id", name="uq_contract_receipt_invoice_allocation"))


def downgrade() -> None:
    for table in ("contract_receipt_allocations", "contract_receipts", "contract_invoices", "contract_billing_schedules", "contract_finance_profiles"):
        op.drop_table(table)
