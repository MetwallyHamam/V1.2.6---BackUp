"""Add scheduling participation and shift eligibility foundation.

Revision ID: 0126_smart_schedule_foundation
Revises: 0125_shift_pattern_dates
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists, table_exists

revision = "0126_smart_schedule_foundation"
down_revision = "0125_shift_pattern_dates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not column_exists(bind, "users", "participates_in_shifts"):
        op.add_column("users", sa.Column("participates_in_shifts", sa.Boolean(), nullable=False, server_default=sa.true()))
    if not column_exists(bind, "users", "participates_in_operations"):
        op.add_column("users", sa.Column("participates_in_operations", sa.Boolean(), nullable=False, server_default=sa.true()))
    if not column_exists(bind, "shift_types", "enforce_employee_eligibility"):
        op.add_column("shift_types", sa.Column("enforce_employee_eligibility", sa.Boolean(), nullable=False, server_default=sa.false()))
    if table_exists(bind, "employee_shift_eligibilities"):
        return
    op.create_table(
        "employee_shift_eligibilities",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shift_type_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("shift_types.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_eligible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_by_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("employee_id", "shift_type_id", name="uq_employee_shift_eligibility"),
    )
    op.create_index("ix_employee_shift_eligibility_lookup", "employee_shift_eligibilities", ["employee_id", "shift_type_id"])


def downgrade() -> None:
    op.drop_index("ix_employee_shift_eligibility_lookup", table_name="employee_shift_eligibilities")
    op.drop_table("employee_shift_eligibilities")
    op.drop_column("shift_types", "enforce_employee_eligibility")
    op.drop_column("users", "participates_in_operations")
    op.drop_column("users", "participates_in_shifts")
