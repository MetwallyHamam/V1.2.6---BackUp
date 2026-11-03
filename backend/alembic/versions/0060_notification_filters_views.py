"""Notification sound preferences and saved filter views."""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists, index_exists, table_exists

revision = "0060_notification_filters_views"
down_revision = "0059_shift_authorization_editing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not column_exists(bind, "notification_preferences", "sound_code"):
        op.add_column("notification_preferences", sa.Column("sound_code", sa.String(40), nullable=False, server_default="CHIME"))
    if not column_exists(bind, "notification_preferences", "volume_percent"):
        op.add_column("notification_preferences", sa.Column("volume_percent", sa.Integer(), nullable=False, server_default="70"))
    if not table_exists(bind, "notification_views"):
        op.create_table(
        "notification_views",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("filters_json", sa.String(2000), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not index_exists(bind, "notification_views", "ix_notification_views_user_default"):
        op.create_index("ix_notification_views_user_default", "notification_views", ["user_id", "is_default"])


def downgrade() -> None:
    op.drop_table("notification_views")
    op.drop_column("notification_preferences", "volume_percent")
    op.drop_column("notification_preferences", "sound_code")
