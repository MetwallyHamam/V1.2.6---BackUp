"""add work assignment transition evidence

Revision ID: 0279_work_assignment_evidence
Revises: 0278_work_assignment_context
"""

import sqlalchemy as sa

from alembic import op

revision = "0279_work_assignment_evidence"
down_revision = "0278_work_assignment_context"
branch_labels = None
depends_on = None
ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "work_assignment_evidence",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("assignment_id", ID, sa.ForeignKey("work_assignments.id", ondelete="CASCADE"), nullable=False),
        # Assignment deletion already cascades to both events and evidence. A
        # second cascade from event to evidence creates a SQL Server multiple
        # cascade path, so event deletion is intentionally restricted.
        sa.Column("event_id", ID, sa.ForeignKey("work_assignment_events.id"), nullable=False),
        sa.Column("evidence_type", sa.String(30), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.String(255)),
        sa.Column("stored_filename", sa.String(255)),
        sa.Column("content_type", sa.String(150)),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("uploaded_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
    )


def downgrade() -> None:
    op.drop_table("work_assignment_evidence")
