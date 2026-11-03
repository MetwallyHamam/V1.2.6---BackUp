"""add engineer pre-ticket workflow.

Revision ID: 0178_engineer_pre_tickets
Revises: 0177_ticket_archive
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0178_engineer_pre_tickets"
down_revision: str | None = "0177_ticket_archive"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "engineer_pre_tickets",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("pre_ticket_number", sa.String(40), unique=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="SUBMITTED"),
        sa.Column("client_id", sa.BigInteger(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("requester_contact_id", sa.BigInteger(), sa.ForeignKey("contacts.id"), nullable=False),
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("proposed_priority", sa.String(5), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("initial_description", sa.Text(), nullable=False),
        sa.Column("enriched_description", sa.Text()),
        sa.Column("submitted_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id")),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("terminal_reason", sa.String(1000)),
        sa.Column("converted_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id")),
        sa.Column("converted_at", sa.DateTime(timezone=True)),
        sa.Column("resulting_ticket_id", sa.BigInteger(), sa.ForeignKey("tickets.id"), unique=True),
        sa.Column("conversion_mode", sa.String(30)),
        sa.Column("idempotency_key", sa.String(200)),
        sa.Column("request_fingerprint", sa.String(64)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('SUBMITTED','CLAIMED','NEEDS_INFORMATION','REJECTED','CANCELLED','CONVERTED')"),
        sa.CheckConstraint("proposed_priority IN ('P1','P2','P3','P4')"),
        sa.CheckConstraint("conversion_mode IS NULL OR conversion_mode IN ('CALL_CENTER','SELF_SERVICE')"),
    )
    op.create_index("ix_engineer_pre_tickets_queue", "engineer_pre_tickets", ["status", "submitted_at"])
    op.create_index("ix_engineer_pre_tickets_submitter", "engineer_pre_tickets", ["submitted_by_user_id", "submitted_at"])
    op.create_index("uq_engineer_pre_ticket_submit_idempotency", "engineer_pre_tickets", ["submitted_by_user_id", "idempotency_key"], unique=True)


def downgrade() -> None:
    op.drop_table("engineer_pre_tickets")
