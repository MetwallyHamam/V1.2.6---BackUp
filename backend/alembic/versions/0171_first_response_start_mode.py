"""add configurable first-response start snapshots

Revision ID: 0171_first_response_mode
Revises: 0170_dashboard_engine
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0171_first_response_mode"
down_revision: str | None = "0170_dashboard_engine"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("ticket_sla_clocks")}
    if "start_mode_snapshot" not in columns:
        op.add_column("ticket_sla_clocks", sa.Column("start_mode_snapshot", sa.String(40)))
    if "start_anchor_at" not in columns:
        op.add_column("ticket_sla_clocks", sa.Column("start_anchor_at", sa.DateTime(timezone=True)))
    op.execute(
        "UPDATE ticket_sla_clocks SET start_mode_snapshot = "
        "CASE WHEN clock_type = 'FIRST_RESPONSE' THEN 'LEGACY_ASSIGNMENT_COMPLETION' "
        "ELSE 'FIRST_DEDICATED_ASSIGNMENT' END, start_anchor_at = started_at"
    )


def downgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("ticket_sla_clocks")}
    if "start_anchor_at" in columns:
        op.drop_column("ticket_sla_clocks", "start_anchor_at")
    if "start_mode_snapshot" in columns:
        op.drop_column("ticket_sla_clocks", "start_mode_snapshot")
