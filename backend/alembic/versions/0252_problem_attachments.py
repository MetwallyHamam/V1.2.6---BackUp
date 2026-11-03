"""Add protected Problem attachment metadata.

Revision ID: 0252_problem_attachments
Revises: 0251_problem_collab
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0252_problem_attachments"
down_revision: str | None = "0251_problem_collab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "problem_attachments",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("problem_id", ID, sa.ForeignKey("problems.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("original_filename", sa.Unicode(255), nullable=False),
        sa.Column("stored_filename", sa.String(100), nullable=False),
        sa.Column("content_type", sa.String(150), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("scan_status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_problem_attachments_problem", "problem_attachments", ["problem_id"])


def downgrade() -> None:
    op.drop_table("problem_attachments")
