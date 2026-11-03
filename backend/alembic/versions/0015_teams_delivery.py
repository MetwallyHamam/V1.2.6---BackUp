"""Microsoft Teams delivery tracking.

Revision ID: 0015_teams_delivery
Revises: 0014_api_clients
"""
from alembic import op
from app.db.migration_helpers import create_frozen_tables
from app.modules.notifications import models  # noqa: F401

revision = "0015_teams_delivery"
down_revision = "0014_api_clients"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_frozen_tables(op.get_bind(), ("teams_deliveries",))


def downgrade() -> None:
    op.drop_table("teams_deliveries")
