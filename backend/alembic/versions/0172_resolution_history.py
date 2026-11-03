"""preserve resolution evidence across reopen cycles

Revision ID: 0172_resolution_history
Revises: 0171_first_response_mode
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0172_resolution_history"
down_revision: str | None = "0171_first_response_mode"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None
ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("ticket_resolution_history"):
        op.create_table(
            "ticket_resolution_history",
            sa.Column("id", ID, primary_key=True, autoincrement=True),
            sa.Column("ticket_id", ID, sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("resolution_sequence", sa.Integer(), nullable=False),
            sa.Column("resolution_summary", sa.UnicodeText()),
            sa.Column("root_cause_summary", sa.UnicodeText()),
            sa.Column("root_cause_ids_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("resolution_outcome_id", ID),
            sa.Column("permanent_fix_summary", sa.UnicodeText()),
            sa.Column("permanent_fix_status", sa.String(30)),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("closed_at", sa.DateTime(timezone=True)),
            sa.Column("sla_snapshot_json", sa.Text()),
            sa.Column("reopened_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
            sa.Column("reopen_reason", sa.Unicode(500), nullable=False),
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        )
        op.create_index(
            "ix_ticket_resolution_history_ticket_sequence",
            "ticket_resolution_history",
            ["ticket_id", "resolution_sequence"],
            unique=True,
        )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("ticket_resolution_history"):
        op.drop_index("ix_ticket_resolution_history_ticket_sequence", table_name="ticket_resolution_history")
        op.drop_table("ticket_resolution_history")
