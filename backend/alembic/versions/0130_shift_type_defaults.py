"""Add canonical Shift Type time and headcount defaults.

Revision ID: 0130_shift_type_defaults
Revises: 0129_operation_generation
"""

from datetime import time

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists

revision = "0130_shift_type_defaults"
down_revision = "0129_operation_generation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not column_exists(bind, "shift_types", "default_start_time"):
        op.add_column("shift_types", sa.Column("default_start_time", sa.Time(), nullable=False, server_default=str(time(9, 0))))
    if not column_exists(bind, "shift_types", "default_end_time"):
        op.add_column("shift_types", sa.Column("default_end_time", sa.Time(), nullable=False, server_default=str(time(17, 0))))
    if not column_exists(bind, "shift_types", "default_required_headcount"):
        op.add_column("shift_types", sa.Column("default_required_headcount", sa.Integer(), nullable=False, server_default="1"))
    op.execute(sa.text("UPDATE shift_types SET default_start_time='09:00:00', default_end_time='17:00:00' WHERE code='DAY'"))
    op.execute(sa.text("UPDATE shift_types SET default_start_time='16:00:00', default_end_time='00:00:00' WHERE code='NIGHT'"))
    op.execute(sa.text("UPDATE shift_types SET default_start_time='00:00:00', default_end_time='00:00:00' WHERE code='ON_CALL'"))


def downgrade() -> None:
    op.drop_column("shift_types", "default_required_headcount")
    op.drop_column("shift_types", "default_end_time")
    op.drop_column("shift_types", "default_start_time")
