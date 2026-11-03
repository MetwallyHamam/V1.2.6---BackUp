"""Add saved ticket reports and secure sharing.

Revision ID: 0233_ticket_reports
Revises: 0232_manual_org_chart
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0233_ticket_reports"
down_revision: str | None = "0232_manual_org_chart"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
Id = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "ticket_reports",
        sa.Column("id", Id, primary_key=True, autoincrement=True),
        sa.Column("report_number", sa.String(40), nullable=False, unique=True),
        sa.Column("ticket_id", Id, sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("report_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("title", sa.Unicode(300), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", Id, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("updated_by_user_id", Id, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("published_version_id", Id),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
    )
    op.create_index("ix_ticket_reports_ticket", "ticket_reports", ["ticket_id"])
    op.create_index("ix_ticket_reports_status", "ticket_reports", ["status"])
    op.create_table(
        "ticket_report_versions",
        sa.Column("id", Id, primary_key=True, autoincrement=True),
        sa.Column(
            "report_id", Id, sa.ForeignKey("ticket_reports.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.Unicode(300), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("published_by_user_id", Id, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.UniqueConstraint("report_id", "version_number", name="uq_ticket_report_version"),
    )
    op.create_index(
        "ix_ticket_report_versions_report",
        "ticket_report_versions",
        ["report_id", "version_number"],
    )
    op.create_table(
        "ticket_report_share_links",
        sa.Column("id", Id, primary_key=True, autoincrement=True),
        sa.Column(
            "version_id",
            Id,
            sa.ForeignKey("ticket_report_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("recipient_name", sa.Unicode(200)),
        sa.Column("recipient_email", sa.String(320)),
        sa.Column("allow_download", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", Id, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_ticket_report_share_version", "ticket_report_share_links", ["version_id"])


def downgrade() -> None:
    op.drop_table("ticket_report_share_links")
    op.drop_table("ticket_report_versions")
    op.drop_table("ticket_reports")
