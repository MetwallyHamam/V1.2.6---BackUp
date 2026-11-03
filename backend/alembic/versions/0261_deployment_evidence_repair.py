"""Repair deployment evidence schema for databases already stamped at 0260.

Revision ID: 0261_deployment_evidence_repair
Revises: 0260_deployment_share_links
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0261_deployment_evidence_repair"
down_revision: str | None = "0260_deployment_share_links"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _column_names(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    return {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes(table_name)
        if index.get("name")
    }


def upgrade() -> None:
    if "approved_software_version" not in _column_names("deployment_plans"):
        op.add_column("deployment_plans", sa.Column("approved_software_version", sa.Unicode(150)))

    tables = _table_names()
    if "deployment_issue_evidence" not in tables:
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
    if "ix_deployment_issue_evidence_issue" not in _index_names("deployment_issue_evidence"):
        op.create_index(
            "ix_deployment_issue_evidence_issue", "deployment_issue_evidence", ["issue_id"]
        )

    tables = _table_names()
    if "deployment_documents" not in tables:
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
    if "ix_deployment_documents_plan" not in _index_names("deployment_documents"):
        op.create_index("ix_deployment_documents_plan", "deployment_documents", ["plan_id"])


def downgrade() -> None:
    # This is a forward-only compatibility repair. Revision 0260 owns the schema
    # and removes it during a complete downgrade.
    pass
