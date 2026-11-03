"""Add public deployment live-tracking share links.

Revision ID: 0260_deployment_share_links
Revises: 0259_deployment_follow_up
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0260_deployment_share_links"
down_revision: str | None = "0259_deployment_follow_up"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("deployment_plans", sa.Column("rollback_plan", sa.UnicodeText()))
    op.add_column("deployment_plans", sa.Column("approved_software_version", sa.Unicode(150)))
    op.create_table(
        "deployment_share_links",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "plan_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            sa.ForeignKey("deployment_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "created_by_user_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_deployment_share_links_plan", "deployment_share_links", ["plan_id"])
    op.create_table(
        "deployment_issue_evidence",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "issue_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            sa.ForeignKey("deployment_issues.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "uploaded_by_user_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("evidence_type", sa.String(20), nullable=False),
        sa.Column("label", sa.Unicode(250)),
        sa.Column("external_url", sa.Unicode(2000)),
        sa.Column("original_filename", sa.Unicode(255)),
        sa.Column("stored_filename", sa.String(100), unique=True),
        sa.Column("content_type", sa.String(150)),
        sa.Column("size_bytes", sa.BigInteger()),
        sa.Column("sha256", sa.String(64)),
        sa.Column("client_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_deployment_issue_evidence_issue", "deployment_issue_evidence", ["issue_id"])
    op.create_table(
        "deployment_documents",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "plan_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            sa.ForeignKey("deployment_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "uploaded_by_user_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("original_filename", sa.Unicode(255), nullable=False),
        sa.Column("stored_filename", sa.String(100), nullable=False, unique=True),
        sa.Column("content_type", sa.String(150)),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("client_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_deployment_documents_plan", "deployment_documents", ["plan_id"])


def downgrade() -> None:
    op.drop_index("ix_deployment_documents_plan", table_name="deployment_documents")
    op.drop_table("deployment_documents")
    op.drop_index("ix_deployment_issue_evidence_issue", table_name="deployment_issue_evidence")
    op.drop_table("deployment_issue_evidence")
    op.drop_index("ix_deployment_share_links_plan", table_name="deployment_share_links")
    op.drop_table("deployment_share_links")
    op.drop_column("deployment_plans", "rollback_plan")
    op.drop_column("deployment_plans", "approved_software_version")
