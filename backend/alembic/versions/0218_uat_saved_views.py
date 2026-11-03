"""Persist personal UAT test views."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0218_uat_saved_views"
down_revision: str | None = "0217_uat_bulk_fields"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table("uat_saved_views",
                    sa.Column("id", id_type, primary_key=True, autoincrement=True),
                    sa.Column("user_id", id_type, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
                    sa.Column("name", sa.Unicode(100), nullable=False),
                    sa.Column("filters_json", sa.UnicodeText(), nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
                    sa.UniqueConstraint("user_id", "name"))
    op.execute("UPDATE uat_implementation_progress SET overall_status='IN_PROGRESS' WHERE feature_area='Search' AND overall_status='NOT_STARTED'")


def downgrade() -> None:
    op.drop_table("uat_saved_views")
