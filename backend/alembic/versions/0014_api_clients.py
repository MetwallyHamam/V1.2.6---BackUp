"""Application API clients.

Revision ID: 0014_api_clients
Revises: 0013_itop_import
"""
from alembic import op
from app.db.migration_helpers import create_frozen_tables
from app.modules.integrations import models  # noqa: F401

revision = "0014_api_clients"
down_revision = "0013_itop_import"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_frozen_tables(op.get_bind(), ("integration_api_clients",))


def downgrade() -> None:
    op.drop_table("integration_api_clients")
