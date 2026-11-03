"""Harden deployment issue workflow and retain transition history.

Revision ID: 0265_deployment_issue_hardening
Revises: 0264_deployment_issue_workflow
"""

import sqlalchemy as sa

from alembic import op

revision: str = "0265_deployment_issue_hardening"
down_revision: str | None = "0264_deployment_issue_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "deployment_issues",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.execute("UPDATE deployment_issues SET status = 'PENDING' WHERE status = 'PENDING_IMPLEMENTATION'")
    op.execute(
        "UPDATE deployment_issues SET delivered = 1, "
        "delivered_at = COALESCE(delivered_at, resolved_at, updated_at, created_at) "
        "WHERE status = 'CLOSED' AND (delivered = 0 OR delivered_at IS NULL)"
    )
    op.create_table(
        "deployment_issue_transitions",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("issue_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("deployment_issues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("previous_status", sa.String(30), nullable=False),
        sa.Column("new_status", sa.String(30), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("change_summary", sa.UnicodeText(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_deployment_issue_transitions_issue_time",
        "deployment_issue_transitions",
        ["issue_id", "changed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_deployment_issue_transitions_issue_time", table_name="deployment_issue_transitions")
    op.drop_table("deployment_issue_transitions")
    op.drop_column("deployment_issues", "version")
