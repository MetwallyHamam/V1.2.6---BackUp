"""Add reusable internal-operation templates.

Revision ID: 0106_operation_templates
Revises: 0105_shift_pattern_defaults
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import table_exists

revision = "0106_operation_templates"
down_revision = "0105_shift_pattern_defaults"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not table_exists(bind, "internal_operation_templates"):
        ident = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
        op.create_table(
            "internal_operation_templates",
            sa.Column("id", ident, primary_key=True, autoincrement=True),
            sa.Column("code", sa.String(50), nullable=False, unique=True),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("operation_type", sa.String(30), nullable=False),
            sa.Column("department_id", ident, sa.ForeignKey("departments.id"), nullable=True),
            sa.Column("start_time", sa.Time(), nullable=False),
            sa.Column("end_time", sa.Time(), nullable=False),
            sa.Column("crosses_midnight", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("default_week_numbers_json", sa.String(30), nullable=False, server_default="1,2,3,4"),
            sa.Column("default_weekdays_json", sa.String(30), nullable=False, server_default="6,0,1,2,3,4"),
            sa.Column("week_start_day", sa.Integer(), nullable=False, server_default="6"),
            sa.Column("location", sa.String(300), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade() -> None:
    op.drop_table("internal_operation_templates")
