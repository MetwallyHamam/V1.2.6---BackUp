"""Add ticket-level satisfaction rating for portal and public feedback.

Revision ID: 0247_portal_ticket_satisfaction
Revises: 0246_contract_portfolio_report
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0247_portal_ticket_satisfaction"
down_revision: str | None = "0246_contract_portfolio_report"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ticket_satisfaction", sa.Column("ticket_rating", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("ticket_satisfaction", "ticket_rating")
