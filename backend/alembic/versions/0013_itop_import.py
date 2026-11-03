"""iTop legacy ticket mappings.

Revision ID: 0013_itop_import
Revises: 0012_sms_delivery
"""
from alembic import op
from app.db.migration_helpers import create_frozen_tables
from app.modules.integrations import models  # noqa: F401

revision = "0013_itop_import"
down_revision = "0012_sms_delivery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_frozen_tables(op.get_bind(), ("legacy_ticket_maps",))


def downgrade() -> None:
    op.drop_table("legacy_ticket_maps")
