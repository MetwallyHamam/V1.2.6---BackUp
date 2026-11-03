"""Outlook outbound delivery queue

Revision ID: 0079_outlook_outbound
Revises: 0078_outlook_email_foundation
"""
import sqlalchemy as sa

from alembic import op

revision = "0079_outlook_outbound"
down_revision = "0078_outlook_email_foundation"
branch_labels = None
depends_on = None
id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table("outlook_outbound_deliveries",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("deduplication_key", sa.String(200), nullable=False),
        sa.Column("ticket_id", id_type, sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_key", sa.String(40), nullable=False), sa.Column("recipient_email", sa.String(320), nullable=False),
        sa.Column("reply_graph_message_id", sa.String(500)), sa.Column("subject", sa.String(300), nullable=False), sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False), sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)), sa.Column("last_error", sa.String(1000)), sa.Column("graph_message_id", sa.String(500)),
        sa.Column("sent_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("deduplication_key", name="uq_outlook_outbound_dedup"),
    )
    op.create_index("ix_outlook_outbound_queue", "outlook_outbound_deliveries", ["status", "next_attempt_at", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_outlook_outbound_queue", table_name="outlook_outbound_deliveries")
    op.drop_table("outlook_outbound_deliveries")
