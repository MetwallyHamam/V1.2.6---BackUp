"""add recoverable ticket archive metadata.

Revision ID: 0177_ticket_archive
Revises: 0176_workflow_readiness
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0177_ticket_archive"
down_revision: str | None = "0176_workflow_readiness"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("tickets")}
    for name, column in (
        ("archived_at", sa.Column("archived_at", sa.DateTime(timezone=True))),
        ("archived_by_user_id", sa.Column("archived_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id"))),
        ("archive_reason", sa.Column("archive_reason", sa.String(500))),
    ):
        if name not in columns:
            op.add_column("tickets", column)


def downgrade() -> None:
    for name in ("archive_reason", "archived_by_user_id", "archived_at"):
        op.drop_column("tickets", name)
