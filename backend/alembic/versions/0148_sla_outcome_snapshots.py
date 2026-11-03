"""add persisted SLA outcome snapshots

Revision ID: 0148_sla_outcome_snapshots
Revises: 0147_multilingual_master_data
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists, index_exists

revision: str = "0148_sla_outcome_snapshots"
down_revision: str | None = "0147_multilingual_master_data"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

SNAPSHOT_COLUMNS = (
    "accountable_minutes",
    "customer_pending_minutes",
    "millensys_pending_minutes",
    "escalation_minutes",
    "saved_minutes",
    "overrun_minutes",
)


def upgrade() -> None:
    bind = op.get_bind()
    for name in SNAPSHOT_COLUMNS:
        if not column_exists(bind, "ticket_sla_clocks", name):
            op.add_column("ticket_sla_clocks", sa.Column(name, sa.Integer(), nullable=True))
    if not column_exists(bind, "ticket_sla_clocks", "outcome_calculated_at"):
        op.add_column(
            "ticket_sla_clocks",
            sa.Column("outcome_calculated_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not index_exists(bind, "ticket_sla_clocks", "ix_sla_clock_outcome_snapshot"):
        op.create_index(
            "ix_sla_clock_outcome_snapshot",
            "ticket_sla_clocks",
            ["clock_type", "completed_at", "ticket_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if index_exists(bind, "ticket_sla_clocks", "ix_sla_clock_outcome_snapshot"):
        op.drop_index("ix_sla_clock_outcome_snapshot", table_name="ticket_sla_clocks")
    if column_exists(bind, "ticket_sla_clocks", "outcome_calculated_at"):
        op.drop_column("ticket_sla_clocks", "outcome_calculated_at")
    for name in reversed(SNAPSHOT_COLUMNS):
        if column_exists(bind, "ticket_sla_clocks", name):
            op.drop_column("ticket_sla_clocks", name)
