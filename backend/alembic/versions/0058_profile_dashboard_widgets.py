"""Profile dashboard widget configuration

Revision ID: 0058_profile_dashboard_widgets
Revises: 0057_sla_clock_lifecycle
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists

revision = "0058_profile_dashboard_widgets"
down_revision = "0057_sla_clock_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not column_exists(op.get_bind(), "profiles", "dashboard_widgets_json"):
        op.add_column("profiles", sa.Column("dashboard_widgets_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "dashboard_widgets_json")
