"""add pre-ticket information exchange fields.

Revision ID: 0180_pre_ticket_messages
Revises: 0179_pre_ticket_permissions
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0180_pre_ticket_messages"
down_revision: str | None = "0179_pre_ticket_permissions"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("engineer_pre_tickets", sa.Column("information_request", sa.Text()))
    op.add_column("engineer_pre_tickets", sa.Column("engineer_response", sa.Text()))


def downgrade() -> None:
    op.drop_column("engineer_pre_tickets", "engineer_response")
    op.drop_column("engineer_pre_tickets", "information_request")
