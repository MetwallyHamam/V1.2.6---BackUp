"""ticket cancellation and reopen timestamps

Revision ID: 0055_terminal_timestamps
Revises: 0054_pending_follow_up
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists

revision = "0055_terminal_timestamps"
down_revision = "0054_pending_follow_up"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not column_exists(bind, "tickets", "cancelled_at"):
        op.add_column("tickets", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    if not column_exists(bind, "tickets", "reopened_at"):
        op.add_column("tickets", sa.Column("reopened_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("tickets", "reopened_at")
    op.drop_column("tickets", "cancelled_at")
