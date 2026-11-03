"""add per-user ticket grid preferences.

Revision ID: 0194_ticket_grid_preferences
Revises: 0193_assistant_user_state
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0194_ticket_grid_preferences"
down_revision: str | None = "0193_assistant_user_state"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ticket_grid_preferences",
        sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("columns_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("column_widths_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("density", sa.String(length=20), nullable=False, server_default="COMPACT"),
        sa.Column("page_size", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("sort_by", sa.String(length=40), nullable=False, server_default="updated_at"),
        sa.Column("sort_direction", sa.String(length=4), nullable=False, server_default="desc"),
        sa.Column("group_by", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("ticket_grid_preferences")
