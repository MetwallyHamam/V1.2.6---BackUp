"""Support multiple products and modules per installation.

Revision ID: 0022_installation_components
Revises: 0021_nullable_employee_code
"""

import sqlalchemy as sa

from alembic import op

revision = "0022_installation_components"
down_revision = "0021_nullable_employee_code"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "installation_components",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "installation_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column(
            "product_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column(
            "product_module_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["installation_id"], ["client_installations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["product_module_id"], ["product_modules.id"]),
        sa.UniqueConstraint(
            "installation_id", "product_id", "product_module_id", name="uq_installation_component"
        ),
    )
    op.execute(
        sa.text(
            "INSERT INTO installation_components "
            "(installation_id, product_id, product_module_id) "
            "SELECT id, product_id, product_module_id FROM client_installations"
        )
    )
    op.create_index(
        "ix_installation_components_installation", "installation_components", ["installation_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_installation_components_installation", table_name="installation_components")
    op.drop_table("installation_components")
