"""store structured inbound pre-ticket request details.

Revision ID: 0190_inbound_pre_ticket
Revises: 0189_support_assistant_backlog
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0190_inbound_pre_ticket"
down_revision: str | None = "0189_support_assistant_backlog"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("engineer_pre_tickets", sa.Column("request_kind", sa.String(30), nullable=False, server_default="TICKET_REQUEST"))
    op.add_column("engineer_pre_tickets", sa.Column("source_provider", sa.String(50)))
    op.add_column("engineer_pre_tickets", sa.Column("external_event_id", sa.String(150)))
    op.add_column("engineer_pre_tickets", sa.Column("external_requester_name", sa.String(200)))
    op.add_column("engineer_pre_tickets", sa.Column("external_phone_number", sa.String(50)))
    op.add_column("engineer_pre_tickets", sa.Column("requested_ticket_type_code", sa.String(30)))
    op.create_index("ix_engineer_pre_tickets_external_event", "engineer_pre_tickets", ["source_provider", "external_event_id"])


def downgrade() -> None:
    op.drop_index("ix_engineer_pre_tickets_external_event", table_name="engineer_pre_tickets")
    for column in ("requested_ticket_type_code", "external_phone_number", "external_requester_name", "external_event_id", "source_provider", "request_kind"):
        op.drop_column("engineer_pre_tickets", column)
