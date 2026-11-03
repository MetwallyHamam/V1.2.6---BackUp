"""add durable ticket creation idempotency evidence

Revision ID: 0173_ticket_creation_idempotency
Revises: 0172_resolution_history
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0173_ticket_creation_idempotency"
down_revision: str | None = "0172_resolution_history"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {item["name"] for item in inspector.get_columns("tickets")}
    if "creation_idempotency_key" not in columns:
        op.add_column("tickets", sa.Column("creation_idempotency_key", sa.String(200)))
    if "creation_request_fingerprint" not in columns:
        op.add_column("tickets", sa.Column("creation_request_fingerprint", sa.String(64)))
    indexes = {item["name"] for item in inspector.get_indexes("tickets")}
    if "uq_ticket_creation_idempotency" not in indexes:
        op.create_index(
            "uq_ticket_creation_idempotency",
            "tickets",
            ["created_by_user_id", "source_channel", "creation_idempotency_key"],
            unique=True,
            mssql_where=sa.text("creation_idempotency_key IS NOT NULL"),
            sqlite_where=sa.text("creation_idempotency_key IS NOT NULL"),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {item["name"] for item in inspector.get_indexes("tickets")}
    if "uq_ticket_creation_idempotency" in indexes:
        op.drop_index("uq_ticket_creation_idempotency", table_name="tickets")
    columns = {item["name"] for item in inspector.get_columns("tickets")}
    if "creation_request_fingerprint" in columns:
        op.drop_column("tickets", "creation_request_fingerprint")
    if "creation_idempotency_key" in columns:
        op.drop_column("tickets", "creation_idempotency_key")
