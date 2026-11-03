"""Add targeted SLA escalation work queue.

Revision ID: 0237_escalation_work_queue
Revises: 0236_client_contract_status
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0237_escalation_work_queue"
down_revision: str | None = "0236_client_contract_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "escalation_work_items",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("ticket_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("ticket_sla_clock_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("ticket_sla_clocks.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("next_evaluation_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_started_at", sa.DateTime(timezone=True)),
        sa.Column("last_completed_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(500)),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint("ticket_sla_clock_id", name="uq_escalation_work_clock"),
    )
    op.create_index("ix_escalation_work_due", "escalation_work_items", ["status", "next_evaluation_at", "id"])
    op.create_index("ix_escalation_work_ticket", "escalation_work_items", ["ticket_id", "status"])
    op.execute(
        sa.text(
            """
            INSERT INTO escalation_work_items
                (ticket_id, ticket_sla_clock_id, status, next_evaluation_at,
                 attempt_count, processed_count, created_at, updated_at)
            SELECT ticket_id, id, 'PENDING', CURRENT_TIMESTAMP, 0, 0,
                   CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM ticket_sla_clocks
            WHERE state = 'RUNNING' AND completed_at IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_escalation_work_ticket", table_name="escalation_work_items")
    op.drop_index("ix_escalation_work_due", table_name="escalation_work_items")
    op.drop_table("escalation_work_items")
