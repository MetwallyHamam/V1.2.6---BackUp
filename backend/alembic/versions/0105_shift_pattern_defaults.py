"""Persist reusable shift-pattern schedule defaults.

Revision ID: 0105_shift_pattern_defaults
Revises: 0104_workflow_templates
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists

revision = "0105_shift_pattern_defaults"
down_revision = "0104_workflow_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not column_exists(bind, "shift_patterns", "default_week_numbers_json"):
        op.add_column("shift_patterns", sa.Column("default_week_numbers_json", sa.String(30), nullable=False, server_default="1,2,3,4"))
    if not column_exists(bind, "shift_patterns", "default_weekdays_json"):
        op.add_column("shift_patterns", sa.Column("default_weekdays_json", sa.String(30), nullable=False, server_default="6,0,1,2,3,4"))
    if not column_exists(bind, "shift_patterns", "week_start_day"):
        op.add_column("shift_patterns", sa.Column("week_start_day", sa.Integer(), nullable=False, server_default="6"))


def downgrade() -> None:
    for name in ("week_start_day", "default_weekdays_json", "default_week_numbers_json"):
        op.drop_column("shift_patterns", name)
