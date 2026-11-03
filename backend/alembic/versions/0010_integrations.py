"""Integration delivery tracking.

Revision ID: 0010_integrations
Revises: 0009_dashboards_reporting
"""
from alembic import op
from app.db.migration_helpers import create_frozen_tables
from app.modules.integrations import models  # noqa: F401

revision = "0010_integrations"
down_revision = "0009_dashboards_reporting"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_frozen_tables(op.get_bind(), ("integration_deliveries",))


def downgrade() -> None:
    op.drop_table("integration_deliveries")
