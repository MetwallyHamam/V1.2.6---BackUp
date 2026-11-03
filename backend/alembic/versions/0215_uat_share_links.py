"""Add revocable expiring UAT tracking links."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0215_uat_share_links"
down_revision: str | None = "0214_uat_comments_evidence"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table("uat_share_links",
                    sa.Column("id", id_type, primary_key=True, autoincrement=True),
                    sa.Column("cycle_id", id_type, sa.ForeignKey("uat_cycles.id", ondelete="CASCADE"), nullable=False),
                    sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
                    sa.Column("created_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
                    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
                    sa.Column("revoked_at", sa.DateTime(timezone=True)))
    op.create_index("ix_uat_share_links_cycle", "uat_share_links", ["cycle_id"])
    op.execute("UPDATE uat_implementation_progress SET overall_status='IN_PROGRESS' WHERE feature_area IN ('Secure Share Link','Live Tracking','UAT Portfolio Dashboard','Reports','Excel Export') AND overall_status='NOT_STARTED'")


def downgrade() -> None:
    op.drop_index("ix_uat_share_links_cycle", table_name="uat_share_links")
    op.drop_table("uat_share_links")
