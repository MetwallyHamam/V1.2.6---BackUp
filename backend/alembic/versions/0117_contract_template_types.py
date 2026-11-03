"""Add managed contract template types.

Revision ID: 0117_contract_template_types
Revises: 0116_finance_payment_methods
"""

import sqlalchemy as sa

from alembic import op

revision = "0117_contract_template_types"
down_revision = "0116_finance_payment_methods"
branch_labels = None
depends_on = None


def upgrade() -> None:
    id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    table = op.create_table(
        "contract_template_types",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(150), nullable=False, unique=True),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.bulk_insert(table, [
        {"code": "GLOBAL", "name": "Global", "description": "General-purpose contract template.", "is_active": True},
        {"code": "HIS", "name": "HIS", "description": "Hospital Information System template.", "is_active": True},
        {"code": "RIS_PACS", "name": "RIS / PACS", "description": "Radiology and PACS template.", "is_active": True},
        {"code": "WORKSTATION", "name": "Workstation", "description": "Workstation contract template.", "is_active": True},
        {"code": "VISION_TOOLS", "name": "Vision Tools", "description": "Vision tools contract template.", "is_active": True},
    ])


def downgrade() -> None:
    op.drop_table("contract_template_types")
