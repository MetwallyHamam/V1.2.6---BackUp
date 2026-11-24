"""add recoverable notification dismissal state

Revision ID: 0276_notification_dismissal
Revises: 0275_personal_workspace
"""

import sqlalchemy as sa

from alembic import op

revision = "0276_notification_dismissal"
down_revision = "0275_personal_workspace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("notifications")}
    if "dismissed_at" not in columns:
        op.add_column(
            "notifications", sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("notifications")}
    if "dismissed_at" in columns:
        op.drop_column("notifications", "dismissed_at")
