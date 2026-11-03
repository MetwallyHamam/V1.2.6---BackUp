"""add personal pre-ticket queue views.

Revision ID: 0181_pre_ticket_queue_views
Revises: 0180_pre_ticket_messages
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0181_pre_ticket_queue_views"
down_revision: str | None = "0180_pre_ticket_messages"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pre_ticket_queue_views",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("owner_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("search_text", sa.String(length=100)),
        sa.Column("status_filter", sa.String(length=30)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_pre_ticket_queue_views_owner_user_id", "pre_ticket_queue_views", ["owner_user_id"])
    op.create_index("uq_pre_ticket_queue_view_owner_name", "pre_ticket_queue_views", ["owner_user_id", "name"], unique=True)


def downgrade() -> None:
    op.drop_table("pre_ticket_queue_views")
