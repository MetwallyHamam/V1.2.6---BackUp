"""add indexes for large ticket history and dashboard workloads

Revision ID: 0145_ticket_scale
Revises: 0144_handover_cleanup
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0145_ticket_scale"
down_revision: str | None = "0144_handover_cleanup"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    ticket_indexes = {item["name"] for item in inspector.get_indexes("tickets")}
    if "ix_tickets_created_status" not in ticket_indexes:
        op.create_index("ix_tickets_created_status", "tickets", ["created_at", "status_id"])
    if "ix_tickets_resolved_status" not in ticket_indexes:
        op.create_index("ix_tickets_resolved_status", "tickets", ["resolved_at", "status_id"])
    assignment_indexes = {
        item["name"] for item in inspector.get_indexes("ticket_assignment_history")
    }
    if "ix_ticket_assignment_history_created_ticket" not in assignment_indexes:
        op.create_index(
            "ix_ticket_assignment_history_created_ticket",
            "ticket_assignment_history",
            ["created_at", "ticket_id"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    assignment_indexes = {
        item["name"] for item in inspector.get_indexes("ticket_assignment_history")
    }
    if "ix_ticket_assignment_history_created_ticket" in assignment_indexes:
        op.drop_index(
            "ix_ticket_assignment_history_created_ticket",
            table_name="ticket_assignment_history",
        )
    ticket_indexes = {item["name"] for item in inspector.get_indexes("tickets")}
    if "ix_tickets_resolved_status" in ticket_indexes:
        op.drop_index("ix_tickets_resolved_status", table_name="tickets")
    if "ix_tickets_created_status" in ticket_indexes:
        op.drop_index("ix_tickets_created_status", table_name="tickets")
