"""Ticket root-cause summary.

Revision ID: 0016_ticket_root_cause
Revises: 0015_teams_delivery
"""
import sqlalchemy as sa

from alembic import op

revision = "0016_ticket_root_cause"
down_revision = "0015_teams_delivery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("root_cause_summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tickets", "root_cause_summary")
