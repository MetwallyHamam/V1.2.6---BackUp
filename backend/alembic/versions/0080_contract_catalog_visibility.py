"""Contract ticket catalog visibility

Revision ID: 0080_contract_catalog_visibility
Revises: 0079_outlook_outbound
"""
import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists

revision = "0080_contract_catalog_visibility"
down_revision = "0079_outlook_outbound"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not column_exists(op.get_bind(), "contracts", "ticket_catalog_visibility"):
        op.add_column("contracts", sa.Column("ticket_catalog_visibility", sa.String(30), nullable=False, server_default="CONTRACT_ONLY"))


def downgrade() -> None:
    if column_exists(op.get_bind(), "contracts", "ticket_catalog_visibility"):
        op.drop_column("contracts", "ticket_catalog_visibility")
