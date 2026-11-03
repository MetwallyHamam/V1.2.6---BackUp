"""Add editable weekly shift roster templates.

Revision ID: 0109_shift_rosters
Revises: 0108_visit_operation_type
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import table_exists

revision = "0109_shift_rosters"
down_revision = "0108_visit_operation_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind(); ident = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    if not table_exists(bind, "shift_roster_templates"):
        op.create_table("shift_roster_templates", sa.Column("id", ident, primary_key=True, autoincrement=True), sa.Column("department_id", ident, sa.ForeignKey("departments.id"), nullable=False), sa.Column("code", sa.String(50), nullable=False), sa.Column("name", sa.String(150), nullable=False), sa.Column("week_start_day", sa.Integer(), nullable=False, server_default="6"), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.UniqueConstraint("department_id", "code", name="uq_shift_roster_department_code"))
    if not table_exists(bind, "shift_roster_rows"):
        op.create_table("shift_roster_rows", sa.Column("id", ident, primary_key=True, autoincrement=True), sa.Column("template_id", ident, sa.ForeignKey("shift_roster_templates.id", ondelete="CASCADE"), nullable=False), sa.Column("shift_type_id", ident, sa.ForeignKey("shift_types.id"), nullable=False), sa.Column("weekday", sa.Integer(), nullable=False), sa.Column("week_numbers_json", sa.String(30), nullable=False, server_default="1,2,3,4"), sa.Column("start_time", sa.Time(), nullable=False), sa.Column("end_time", sa.Time(), nullable=False), sa.Column("crosses_midnight", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("work_location", sa.String(20), nullable=False, server_default="OFFICE"), sa.Column("notes", sa.String(1000)), sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"))
    if not table_exists(bind, "shift_roster_row_assignees"):
        op.create_table("shift_roster_row_assignees", sa.Column("id", ident, primary_key=True, autoincrement=True), sa.Column("row_id", ident, sa.ForeignKey("shift_roster_rows.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", ident, sa.ForeignKey("users.id"), nullable=False), sa.UniqueConstraint("row_id", "user_id", name="uq_shift_roster_row_user"))


def downgrade() -> None:
    op.drop_table("shift_roster_row_assignees"); op.drop_table("shift_roster_rows"); op.drop_table("shift_roster_templates")
