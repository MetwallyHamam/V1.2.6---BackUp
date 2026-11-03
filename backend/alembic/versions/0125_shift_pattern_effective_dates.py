"""Add the omitted effective dates to shift patterns.

Revision ID: 0125_shift_pattern_dates
Revises: 0124_template_effective_dates
"""

import sqlalchemy as sa

from alembic import op

revision = "0125_shift_pattern_dates"
down_revision = "0124_template_effective_dates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shift_patterns", sa.Column("effective_from", sa.Date()))
    op.add_column("shift_patterns", sa.Column("effective_to", sa.Date()))


def downgrade() -> None:
    op.drop_column("shift_patterns", "effective_to")
    op.drop_column("shift_patterns", "effective_from")
