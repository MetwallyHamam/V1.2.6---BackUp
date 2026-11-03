"""Add durable contract expiration notification delivery ledger.

Revision ID: 0239_contract_notify_log
Revises: 0238_contract_notify_perm
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0239_contract_notify_log"
down_revision: str | None = "0238_contract_notify_perm"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contract_expiration_notification_deliveries",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("contract_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("contract_end_date", sa.Date(), nullable=False),
        sa.Column("milestone_key", sa.String(length=100), nullable=False),
        sa.Column("milestone_days", sa.Integer(), nullable=True),
        sa.Column("rule_version", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("recipient_key", sa.String(length=320), nullable=False),
        sa.Column("to_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("cc_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("notification_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
        sa.Column("outbox_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="QUEUED"),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["outbox_id"], ["event_outbox.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("notification_id"),
        sa.UniqueConstraint("outbox_id"),
        sa.UniqueConstraint("contract_id", "contract_end_date", "milestone_key", "channel", "recipient_key", name="uq_contract_expiration_delivery_milestone"),
    )
    op.create_index("ix_contract_expiration_delivery_status", "contract_expiration_notification_deliveries", ["status", "queued_at"])


def downgrade() -> None:
    op.drop_index("ix_contract_expiration_delivery_status", table_name="contract_expiration_notification_deliveries")
    op.drop_table("contract_expiration_notification_deliveries")
