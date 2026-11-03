"""Per-user notification preferences.

Revision ID: 0020_notification_preferences
Revises: 0019_ticket_knowledge_links
"""

import sqlalchemy as sa

from alembic import op

revision = "0020_notification_preferences"
down_revision = "0019_ticket_knowledge_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("sound_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("desktop_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("notification_preferences")
