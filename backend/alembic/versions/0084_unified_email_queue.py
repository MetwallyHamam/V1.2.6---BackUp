"""Unified durable email queue

Revision ID: 0084_unified_email_queue
Revises: 0083_ticket_type_colors
"""
import sqlalchemy as sa

from alembic import op

revision = "0084_unified_email_queue"
down_revision = "0083_ticket_type_colors"
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "deduplication_key" not in {column["name"] for column in inspector.get_columns("event_outbox")}:
        op.add_column("event_outbox", sa.Column("deduplication_key", sa.String(200), nullable=True))
    indexes = {item["name"] for item in sa.inspect(bind).get_indexes("event_outbox")}
    if "uq_event_outbox_deduplication_key" not in indexes:
        op.create_index(
            "uq_event_outbox_deduplication_key",
            "event_outbox",
            ["deduplication_key"],
            unique=True,
            mssql_where=sa.text("deduplication_key IS NOT NULL"),
            sqlite_where=sa.text("deduplication_key IS NOT NULL"),
        )

def downgrade() -> None:
    op.drop_index("uq_event_outbox_deduplication_key", table_name="event_outbox")
    op.drop_column("event_outbox", "deduplication_key")
