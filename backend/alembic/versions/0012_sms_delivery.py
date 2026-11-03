"""SMS delivery tracking.

Revision ID: 0012_sms_delivery
Revises: 0011_outbound_email
"""
from alembic import op
from app.db.migration_helpers import create_frozen_tables
from app.modules.notifications import models  # noqa: F401

revision = "0012_sms_delivery"
down_revision = "0011_outbound_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_frozen_tables(op.get_bind(), ("sms_deliveries",))


def downgrade() -> None:
    op.drop_table("sms_deliveries")
