"""Lock KPI review values after the reviewer saves them.

Revision ID: 0089_kpi_review_lock
Revises: 0088_shift_handovers
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists

revision = "0089_kpi_review_lock"
down_revision = "0088_shift_handovers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not column_exists(bind, "kpi_reviews", "is_locked"):
        op.add_column("kpi_reviews", sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    bind = op.get_bind()
    if column_exists(bind, "kpi_reviews", "is_locked"):
        op.drop_column("kpi_reviews", "is_locked")
