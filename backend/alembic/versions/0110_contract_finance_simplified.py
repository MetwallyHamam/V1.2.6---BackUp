"""Add simplified contract schedules, collections, and adjustment reasons.

Revision ID: 0110_contract_finance_simplified
Revises: 0109_shift_rosters
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists, table_exists

revision = "0110_contract_finance_simplified"
down_revision = "0109_shift_rosters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    ident = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    if not column_exists(bind, "contract_finance_profiles", "billing_frequency"):
        op.add_column("contract_finance_profiles", sa.Column("billing_frequency", sa.String(20), nullable=False, server_default="ANNUAL"))
    if not column_exists(bind, "contract_finance_profiles", "billing_day"):
        op.add_column("contract_finance_profiles", sa.Column("billing_day", sa.Integer(), nullable=False, server_default="1"))
    if not column_exists(bind, "contract_finance_profiles", "invoice_amount"):
        op.add_column("contract_finance_profiles", sa.Column("invoice_amount", sa.Numeric(19, 4)))
    if not table_exists(bind, "finance_adjustment_reasons"):
        op.create_table(
            "finance_adjustment_reasons",
            sa.Column("id", ident, primary_key=True, autoincrement=True),
            sa.Column("code", sa.String(50), nullable=False),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("adjustment_type", sa.String(20), nullable=False, server_default="DISCOUNT"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by_user_id", ident, sa.ForeignKey("users.id")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
            sa.UniqueConstraint("code", name="uq_finance_adjustment_reason_code"),
        )
        reasons = sa.table("finance_adjustment_reasons", sa.column("code", sa.String), sa.column("name", sa.String), sa.column("adjustment_type", sa.String), sa.column("is_active", sa.Boolean))
        op.bulk_insert(reasons, [
            {"code": "SLA_DEDUCTION", "name": "SLA deduction", "adjustment_type": "DISCOUNT", "is_active": True},
            {"code": "BUSINESS_REQUIRED_DEDUCTION", "name": "Business required deduction", "adjustment_type": "DISCOUNT", "is_active": True},
            {"code": "EXCEPTION", "name": "Exception", "adjustment_type": "BOTH", "is_active": True},
        ])
    if not table_exists(bind, "contract_collections"):
        op.create_table(
            "contract_collections",
            sa.Column("id", ident, primary_key=True, autoincrement=True),
            sa.Column("contract_id", ident, sa.ForeignKey("contracts.id"), nullable=False),
            sa.Column("invoice_id", ident, sa.ForeignKey("contract_invoices.id"), nullable=False),
            sa.Column("idempotency_key", sa.String(200), nullable=False),
            sa.Column("reference", sa.String(200)),
            sa.Column("collected_date", sa.Date(), nullable=False),
            sa.Column("invoice_amount", sa.Numeric(19, 4), nullable=False),
            sa.Column("actual_payment", sa.Numeric(19, 4), nullable=False),
            sa.Column("discount_amount", sa.Numeric(19, 4), nullable=False, server_default="0"),
            sa.Column("additional_amount", sa.Numeric(19, 4), nullable=False, server_default="0"),
            sa.Column("adjustment_reason_id", ident, sa.ForeignKey("finance_adjustment_reasons.id")),
            sa.Column("adjustment_notes", sa.String(1000)),
            sa.Column("currency", sa.String(3), nullable=False),
            sa.Column("created_by_user_id", ident, sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
            sa.UniqueConstraint("idempotency_key", name="uq_contract_collection_idempotency"),
        )
        op.create_index("ix_contract_collection_invoice_date", "contract_collections", ["invoice_id", "collected_date"])


def downgrade() -> None:
    op.drop_table("contract_collections")
    op.drop_table("finance_adjustment_reasons")
    op.drop_column("contract_finance_profiles", "invoice_amount")
    op.drop_column("contract_finance_profiles", "billing_day")
    op.drop_column("contract_finance_profiles", "billing_frequency")
