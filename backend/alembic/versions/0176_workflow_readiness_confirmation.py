"""add workflow readiness and customer confirmation evidence.

Revision ID: 0176_workflow_readiness
Revises: 0175_attachment_idempotency
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0176_workflow_readiness"
down_revision: str | None = "0175_attachment_idempotency"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    ticket_columns = {column["name"] for column in inspector.get_columns("tickets")}
    for name, column in (
        ("customer_confirmed_at", sa.Column("customer_confirmed_at", sa.DateTime(timezone=True))),
        ("customer_confirmed_by_user_id", sa.Column("customer_confirmed_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id"))),
        ("customer_confirmation_channel", sa.Column("customer_confirmation_channel", sa.String(30))),
        ("customer_confirmation_contact", sa.Column("customer_confirmation_contact", sa.String(300))),
        ("customer_confirmation_note", sa.Column("customer_confirmation_note", sa.Text())),
    ):
        if name not in ticket_columns:
            op.add_column("tickets", column)
    for table in ("ticket_tasks", "ticket_checklist_items"):
        columns = {column["name"] for column in inspector.get_columns(table)}
        if "is_required" not in columns:
            op.add_column(table, sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    for table in ("ticket_tasks", "ticket_checklist_items"):
        op.drop_column(table, "is_required")
    for name in ("customer_confirmation_note", "customer_confirmation_contact", "customer_confirmation_channel", "customer_confirmed_by_user_id", "customer_confirmed_at"):
        op.drop_column("tickets", name)
