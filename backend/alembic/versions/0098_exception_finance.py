"""Add scoped approval consumption and manager ticket finance.

Revision ID: 0098_exception_finance
Revises: 0097_service_governance
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists, table_exists

revision = "0098_exception_finance"
down_revision = "0097_service_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    for name, kind in (
        ("operation_scope", sa.String(250)), ("consumed_by_user_id", id_type),
        ("consumed_at", sa.DateTime(timezone=True)), ("revoked_by_user_id", id_type),
        ("revoked_at", sa.DateTime(timezone=True)), ("version", sa.Integer()),
    ):
        if not column_exists(bind, "entitlement_approvals", name):
            op.add_column("entitlement_approvals", sa.Column(name, kind, nullable=True))
    bind.execute(sa.text("UPDATE entitlement_approvals SET operation_scope = CASE WHEN ticket_id IS NOT NULL THEN 'TICKET:' + CAST(ticket_id AS VARCHAR(30)) + ':' + requested_action ELSE policy_scope END WHERE operation_scope IS NULL") if bind.dialect.name == "mssql" else sa.text("UPDATE entitlement_approvals SET operation_scope = CASE WHEN ticket_id IS NOT NULL THEN 'TICKET:' || ticket_id || ':' || requested_action ELSE policy_scope END WHERE operation_scope IS NULL"))
    bind.execute(sa.text("UPDATE entitlement_approvals SET version=1 WHERE version IS NULL"))

    if not table_exists(bind, "ticket_commercial_decisions"):
        op.create_table(
            "ticket_commercial_decisions",
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("ticket_id", id_type, sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False), sa.Column("chargeability", sa.String(30), nullable=False),
            sa.Column("approval_status", sa.String(30), nullable=False), sa.Column("estimated_amount", sa.Numeric(19, 4)),
            sa.Column("quoted_amount", sa.Numeric(19, 4)), sa.Column("currency", sa.String(3), nullable=False),
            sa.Column("reason", sa.String(1000), nullable=False), sa.Column("created_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
            sa.UniqueConstraint("ticket_id", "sequence", name="uq_ticket_commercial_decision_sequence"),
        )
        op.create_index("ix_ticket_commercial_decision_ticket_created", "ticket_commercial_decisions", ["ticket_id", "created_at"])
    if not table_exists(bind, "ticket_finance_ledger_entries"):
        op.create_table(
            "ticket_finance_ledger_entries",
            sa.Column("id", id_type, primary_key=True, autoincrement=True), sa.Column("ticket_id", id_type, sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("idempotency_key", sa.String(200), nullable=False), sa.Column("entry_type", sa.String(30), nullable=False), sa.Column("status", sa.String(30), nullable=False),
            sa.Column("amount", sa.Numeric(19, 4), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("external_reference", sa.String(200)),
            sa.Column("reason", sa.String(1000), nullable=False), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False), sa.Column("status_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("reversal_of_entry_id", id_type, sa.ForeignKey("ticket_finance_ledger_entries.id")), sa.Column("created_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
            sa.UniqueConstraint("idempotency_key", name="uq_ticket_finance_ledger_idempotency"),
        )
        op.create_index("ix_ticket_finance_ledger_ticket_occurred", "ticket_finance_ledger_entries", ["ticket_id", "occurred_at"])
        op.create_index("ix_ticket_finance_ledger_type_status", "ticket_finance_ledger_entries", ["entry_type", "status"])


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("ticket_finance_ledger_entries", "ticket_commercial_decisions"):
        if table_exists(bind, table): op.drop_table(table)
    for name in ("version", "revoked_at", "revoked_by_user_id", "consumed_at", "consumed_by_user_id", "operation_scope"):
        if column_exists(bind, "entitlement_approvals", name): op.drop_column("entitlement_approvals", name)
