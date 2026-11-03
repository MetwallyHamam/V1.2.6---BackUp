"""Link CRM services to product modules.

Revision ID: 0132_service_module_links
Revises: 0131_ticket_live_updates
"""

import sqlalchemy as sa

from alembic import op

revision = "0132_service_module_links"
down_revision = "0131_ticket_live_updates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_module_links",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True),
        sa.Column("service_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("product_module_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["service_catalog_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_module_id"], ["product_modules.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("service_id", "product_module_id"),
    )


def downgrade() -> None:
    op.drop_table("service_module_links")
