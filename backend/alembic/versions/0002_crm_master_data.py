"""CRM master data.

Revision ID: 0002_crm_master_data
Revises: 0001_phase_0_1
"""
from alembic import op
from app.db.migration_helpers import create_frozen_tables
from app.modules.clients import models  # noqa: F401

revision = "0002_crm_master_data"
down_revision = "0001_phase_0_1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_frozen_tables(op.get_bind(), ("client_statuses", "clients", "branches", "contacts", "products", "product_modules", "environments", "client_installations", "service_catalog_items", "vendors"))


def downgrade() -> None:
    for table_name in (
        "vendors",
        "service_catalog_items",
        "client_installations",
        "environments",
        "product_modules",
        "products",
        "contacts",
        "branches",
        "clients",
        "client_statuses",
    ):
        op.drop_table(table_name)
