"""Reconcile every deployment table after legacy 0260/0261 upgrades.

Revision ID: 0262_deployment_schema_reconcile
Revises: 0261_deployment_evidence_repair
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0262_deployment_schema_reconcile"
down_revision: str | None = "0261_deployment_evidence_repair"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {
        item["name"] for item in sa.inspect(op.get_bind()).get_indexes(table) if item.get("name")
    }


def _add_missing_columns(table: str, definitions: dict[str, sa.Column[object]]) -> None:
    existing = _columns(table)
    for name, column in definitions.items():
        if name not in existing:
            op.add_column(table, column)


def upgrade() -> None:
    _add_missing_columns(
        "deployment_plans",
        {
            "rollback_plan": sa.Column("rollback_plan", sa.UnicodeText()),
            "approved_software_version": sa.Column("approved_software_version", sa.Unicode(150)),
        },
    )

    if "deployment_share_links" not in _tables():
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
    else:
        _add_missing_columns(
            "deployment_share_links",
            {
                "plan_id": sa.Column("plan_id", sa.BigInteger(), nullable=True),
                "token_hash": sa.Column("token_hash", sa.String(64), nullable=True),
                "created_by_user_id": sa.Column(
                    "created_by_user_id", sa.BigInteger(), nullable=True
                ),
                "created_at": sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
                "expires_at": sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
                "revoked_at": sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            },
        )
    if "ix_deployment_share_links_plan" not in _indexes("deployment_share_links"):
        op.create_index("ix_deployment_share_links_plan", "deployment_share_links", ["plan_id"])

    if "deployment_issue_evidence" not in _tables():
        op.create_table(
            "deployment_issue_evidence",
            sa.Column(
                "id",
                sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                primary_key=True,
                autoincrement=True,
            ),
            sa.Column("issue_id", sa.BigInteger(), nullable=False),
            sa.Column("uploaded_by_user_id", sa.BigInteger(), nullable=False),
            sa.Column("evidence_type", sa.String(20), nullable=False),
            sa.Column("label", sa.Unicode(250)),
            sa.Column("external_url", sa.Unicode(2000)),
            sa.Column("original_filename", sa.Unicode(255)),
            sa.Column("stored_filename", sa.String(100)),
            sa.Column("content_type", sa.String(150)),
            sa.Column("size_bytes", sa.BigInteger()),
            sa.Column("sha256", sa.String(64)),
            sa.Column("client_visible", sa.Boolean(), server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )
    else:
        _add_missing_columns(
            "deployment_issue_evidence",
            {
                "issue_id": sa.Column("issue_id", sa.BigInteger()),
                "uploaded_by_user_id": sa.Column("uploaded_by_user_id", sa.BigInteger()),
                "evidence_type": sa.Column("evidence_type", sa.String(20)),
                "label": sa.Column("label", sa.Unicode(250)),
                "external_url": sa.Column("external_url", sa.Unicode(2000)),
                "original_filename": sa.Column("original_filename", sa.Unicode(255)),
                "stored_filename": sa.Column("stored_filename", sa.String(100)),
                "content_type": sa.Column("content_type", sa.String(150)),
                "size_bytes": sa.Column("size_bytes", sa.BigInteger()),
                "sha256": sa.Column("sha256", sa.String(64)),
                "client_visible": sa.Column(
                    "client_visible", sa.Boolean(), server_default=sa.true()
                ),
                "created_at": sa.Column("created_at", sa.DateTime(timezone=True)),
            },
        )
    if "ix_deployment_issue_evidence_issue" not in _indexes("deployment_issue_evidence"):
        op.create_index(
            "ix_deployment_issue_evidence_issue", "deployment_issue_evidence", ["issue_id"]
        )

    if "deployment_documents" not in _tables():
        op.create_table(
            "deployment_documents",
            sa.Column(
                "id",
                sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                primary_key=True,
                autoincrement=True,
            ),
            sa.Column("plan_id", sa.BigInteger(), nullable=False),
            sa.Column("uploaded_by_user_id", sa.BigInteger(), nullable=False),
            sa.Column("original_filename", sa.Unicode(255), nullable=False),
            sa.Column("stored_filename", sa.String(100), nullable=False),
            sa.Column("content_type", sa.String(150)),
            sa.Column("size_bytes", sa.BigInteger(), nullable=False),
            sa.Column("sha256", sa.String(64), nullable=False),
            sa.Column("client_visible", sa.Boolean(), server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )
    else:
        _add_missing_columns(
            "deployment_documents",
            {
                "plan_id": sa.Column("plan_id", sa.BigInteger()),
                "uploaded_by_user_id": sa.Column("uploaded_by_user_id", sa.BigInteger()),
                "original_filename": sa.Column("original_filename", sa.Unicode(255)),
                "stored_filename": sa.Column("stored_filename", sa.String(100)),
                "content_type": sa.Column("content_type", sa.String(150)),
                "size_bytes": sa.Column("size_bytes", sa.BigInteger()),
                "sha256": sa.Column("sha256", sa.String(64)),
                "client_visible": sa.Column(
                    "client_visible", sa.Boolean(), server_default=sa.true()
                ),
                "created_at": sa.Column("created_at", sa.DateTime(timezone=True)),
            },
        )
    if "ix_deployment_documents_plan" not in _indexes("deployment_documents"):
        op.create_index("ix_deployment_documents_plan", "deployment_documents", ["plan_id"])


def downgrade() -> None:
    # Forward-only reconciliation. Earlier revisions own the underlying schema.
    pass
