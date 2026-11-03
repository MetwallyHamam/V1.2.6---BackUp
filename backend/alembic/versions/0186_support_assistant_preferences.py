"""add per-user Support Assistant preferences.

Revision ID: 0186_support_assistant_prefs
Revises: 0185_ticket_delete_approval
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0186_support_assistant_prefs"
down_revision: str | None = "0185_ticket_delete_approval"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "support_assistant_preferences",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pinned_ticket_ids_json", sa.UnicodeText(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint("user_id", name="uq_support_assistant_preferences_user"),
    )


def downgrade() -> None:
    op.drop_table("support_assistant_preferences")
