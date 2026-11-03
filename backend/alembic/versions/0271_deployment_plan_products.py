"""Add versioned products to deployment plans.

Revision ID: 0271_deployment_products
Revises: 0270_deployment_knowledge
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0271_deployment_products"
down_revision: str | None = "0270_deployment_knowledge"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "deployment_plan_products" not in inspector.get_table_names():
        op.create_table(
            "deployment_plan_products",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True),
            sa.Column("plan_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
            sa.Column("product_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
            sa.Column("approved_version", sa.Unicode(150), nullable=False),
            sa.Column("is_main", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["plan_id"], ["deployment_plans.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="NO ACTION"),
            sa.UniqueConstraint("plan_id", "product_id", name="uq_deployment_plan_product"),
        )
        op.create_index(
            "ix_deployment_plan_products_plan", "deployment_plan_products", ["plan_id"]
        )


def downgrade() -> None:
    if "deployment_plan_products" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("deployment_plan_products")
