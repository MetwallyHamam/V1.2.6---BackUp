"""add persisted first-response SLA actual minutes

Revision ID: 0153_response_sla_snapshot
Revises: 0152_financial_profile
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists

revision: str = "0153_response_sla_snapshot"
down_revision: str | None = "0152_financial_profile"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if not column_exists(bind, "ticket_sla_clocks", "actual_response_minutes"):
        op.add_column(
            "ticket_sla_clocks",
            sa.Column("actual_response_minutes", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if column_exists(bind, "ticket_sla_clocks", "actual_response_minutes"):
        op.drop_column("ticket_sla_clocks", "actual_response_minutes")
