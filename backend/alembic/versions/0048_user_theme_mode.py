"""Add per-user theme preference.

Revision ID: 0048_user_theme_mode
Revises: 0047_ticket_bulk_permissions
"""

import sqlalchemy as sa

from alembic import op

revision = "0048_user_theme_mode"
down_revision = "0047_ticket_bulk_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("theme_mode", sa.String(20), nullable=False, server_default="SYSTEM"),
    )


def downgrade() -> None:
    op.drop_column("users", "theme_mode")
