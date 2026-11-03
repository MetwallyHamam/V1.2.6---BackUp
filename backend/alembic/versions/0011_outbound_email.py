"""Outbound email delivery tracking.

Revision ID: 0011_outbound_email
Revises: 0010_integrations
"""
from alembic import op
from app.db.migration_helpers import create_frozen_tables
from app.modules.notifications import models  # noqa: F401

revision = "0011_outbound_email"
down_revision = "0010_integrations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_frozen_tables(op.get_bind(), ("email_deliveries",))


def downgrade() -> None:
    op.drop_table("email_deliveries")
