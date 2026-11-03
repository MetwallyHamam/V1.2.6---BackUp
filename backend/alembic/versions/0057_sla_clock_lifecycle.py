"""SLA clock warning and completion lifecycle

Revision ID: 0057_sla_clock_lifecycle
Revises: 0056_escalation_parent
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists

revision = "0057_sla_clock_lifecycle"
down_revision = "0056_escalation_parent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not column_exists(bind, "ticket_sla_clocks", "warning_percent"):
        op.add_column(
            "ticket_sla_clocks",
            sa.Column("warning_percent", sa.Integer(), nullable=False, server_default="75"),
        )
    if not column_exists(bind, "ticket_sla_clocks", "completed_at"):
        op.add_column(
            "ticket_sla_clocks",
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("ticket_sla_clocks", "completed_at")
    op.drop_column("ticket_sla_clocks", "warning_percent")
