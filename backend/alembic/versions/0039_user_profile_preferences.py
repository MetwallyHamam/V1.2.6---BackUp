"""add personal landing and dashboard preferences

Revision ID: 0039_user_preferences
Revises: 0038_operation_client
"""

import sqlalchemy as sa

from alembic import op

revision = "0039_user_preferences"
down_revision = "0038_operation_client"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("default_page", sa.String(80), nullable=True))
    op.add_column("users", sa.Column("default_dashboard_scope", sa.String(20), nullable=False, server_default="GENERAL"))
    op.add_column("users", sa.Column("default_saved_view_id", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "default_saved_view_id")
    op.drop_column("users", "default_dashboard_scope")
    op.drop_column("users", "default_page")
