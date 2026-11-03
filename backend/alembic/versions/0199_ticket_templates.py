"""Add governed reusable ticket templates."""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0199_ticket_templates"
down_revision: str | None = "0198_view_layout_scope"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

def upgrade() -> None:
    op.create_table(
        "ticket_templates",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Unicode(200), nullable=False), sa.Column("keywords", sa.Unicode(1000), nullable=False, server_default=""),
        sa.Column("source_ticket_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("tickets.id", ondelete="SET NULL")),
        sa.Column("ticket_type_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("ticket_types.id"), nullable=False),
        sa.Column("client_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("clients.id")),
        sa.Column("product_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("products.id")),
        sa.Column("product_module_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("product_modules.id")),
        sa.Column("environment_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("environments.id")),
        sa.Column("service_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("service_catalog_items.id")),
        sa.Column("category_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("ticket_categories.id")),
        sa.Column("subcategory_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("ticket_subcategories.id")),
        sa.Column("subject", sa.Unicode(300), nullable=False), sa.Column("description", sa.UnicodeText(), nullable=False),
        sa.Column("priority", sa.String(10), nullable=False), sa.Column("impact", sa.String(20), nullable=False), sa.Column("urgency", sa.String(20), nullable=False),
        sa.Column("assigned_team", sa.Unicode(150)), sa.Column("portal_visible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ticket_templates_active_scope", "ticket_templates", ["is_active", "client_id", "product_id"])

def downgrade() -> None:
    op.drop_index("ix_ticket_templates_active_scope", table_name="ticket_templates")
    op.drop_table("ticket_templates")
