"""add auto-close after resolve preference

Revision ID: 0036_auto_close_pref
Revises: 0035_agent_kpi_activities
"""

import sqlalchemy as sa

from alembic import op

revision = "0036_auto_close_pref"
down_revision = "0035_agent_kpi_activities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("auto_close_on_resolve", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("users", "auto_close_on_resolve")
