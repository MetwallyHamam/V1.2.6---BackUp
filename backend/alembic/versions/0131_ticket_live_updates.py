"""Add secure public live ticket-update links.

Revision ID: 0131_ticket_live_updates
Revises: 0130_shift_type_defaults
"""

import sqlalchemy as sa

from alembic import op

revision = "0131_ticket_live_updates"
down_revision = "0130_shift_type_defaults"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ticket_live_updates",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True),
        sa.Column("ticket_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_ticket_live_updates_token", "ticket_live_updates", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_ticket_live_updates_token", table_name="ticket_live_updates")
    op.drop_table("ticket_live_updates")
