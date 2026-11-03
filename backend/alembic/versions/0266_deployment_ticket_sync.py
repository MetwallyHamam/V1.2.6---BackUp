"""Synchronize deployment issues with ticket workflow.

Revision ID: 0266_deployment_ticket_sync
Revises: 0265_deployment_issue_hardening
"""

import sqlalchemy as sa

from alembic import op

revision: str = "0266_deployment_ticket_sync"
down_revision: str | None = "0265_deployment_issue_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("deployment_issues", sa.Column("reopen_reason", sa.UnicodeText(), nullable=True))
    op.create_index(
        "uq_deployment_issues_linked_ticket",
        "deployment_issues",
        ["linked_ticket_id"],
        unique=True,
        mssql_where=sa.text("linked_ticket_id IS NOT NULL"),
        sqlite_where=sa.text("linked_ticket_id IS NOT NULL"),
    )
    op.create_table(
        "deployment_issue_root_causes",
        sa.Column("issue_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("deployment_issues.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("root_cause_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("root_causes.id", ondelete="NO ACTION"), primary_key=True),
        sa.Column("created_by_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "deployment_issue_resolution_services",
        sa.Column("issue_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("deployment_issues.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("service_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("service_catalog_items.id", ondelete="NO ACTION"), primary_key=True),
        sa.Column("created_by_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("deployment_issue_resolution_services")
    op.drop_table("deployment_issue_root_causes")
    op.drop_index("uq_deployment_issues_linked_ticket", table_name="deployment_issues")
    op.drop_column("deployment_issues", "reopen_reason")
