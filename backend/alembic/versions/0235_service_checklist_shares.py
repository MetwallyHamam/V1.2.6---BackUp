"""Add secure public service-checklist event shares.

Revision ID: 0235_service_checklist_shares
Revises: 0234_simple_checklist_rows
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0235_service_checklist_shares"
down_revision: str | None = "0234_simple_checklist_rows"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
Id = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "service_checklist_share_links",
        sa.Column("id", Id, primary_key=True, autoincrement=True),
        sa.Column(
            "occurrence_id",
            Id,
            sa.ForeignKey("service_checklist_occurrences.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", Id, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
    )
    op.create_index(
        "ix_service_checklist_share_links_occurrence_id",
        "service_checklist_share_links",
        ["occurrence_id"],
    )
    op.create_index(
        "ix_service_checklist_share_links_token_hash",
        "service_checklist_share_links",
        ["token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_service_checklist_share_links_token_hash",
        table_name="service_checklist_share_links",
    )
    op.drop_index(
        "ix_service_checklist_share_links_occurrence_id",
        table_name="service_checklist_share_links",
    )
    op.drop_table("service_checklist_share_links")
