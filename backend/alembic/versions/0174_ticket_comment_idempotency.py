"""add durable ticket comment idempotency.

Revision ID: 0174_ticket_comment_idempotency
Revises: 0173_ticket_creation_idempotency
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0174_ticket_comment_idempotency"
down_revision: str | None = "0173_ticket_creation_idempotency"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "operation_key" not in {item["name"] for item in inspector.get_columns("ticket_comments")}:
        op.add_column("ticket_comments", sa.Column("operation_key", sa.String(200)))
    if "uq_ticket_comment_operation" not in {item["name"] for item in inspector.get_indexes("ticket_comments")}:
        op.create_index("uq_ticket_comment_operation", "ticket_comments", ["ticket_id", "author_user_id", "operation_key"], unique=True, mssql_where=sa.text("operation_key IS NOT NULL"), sqlite_where=sa.text("operation_key IS NOT NULL"))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "uq_ticket_comment_operation" in {item["name"] for item in inspector.get_indexes("ticket_comments")}:
        op.drop_index("uq_ticket_comment_operation", table_name="ticket_comments")
    if "operation_key" in {item["name"] for item in inspector.get_columns("ticket_comments")}:
        op.drop_column("ticket_comments", "operation_key")
