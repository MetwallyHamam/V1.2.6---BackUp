"""Add effective dates to reusable operation and roster templates.

Revision ID: 0124_template_effective_dates
Revises: 0123_onboarding_programs
"""

import sqlalchemy as sa

from alembic import op

revision = "0124_template_effective_dates"
down_revision = "0123_onboarding_programs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("shift_roster_templates", "internal_operation_templates"):
        op.add_column(table, sa.Column("effective_from", sa.Date()))
        op.add_column(table, sa.Column("effective_to", sa.Date()))


def downgrade() -> None:
    for table in ("internal_operation_templates", "shift_roster_templates"):
        op.drop_column(table, "effective_to")
        op.drop_column(table, "effective_from")
