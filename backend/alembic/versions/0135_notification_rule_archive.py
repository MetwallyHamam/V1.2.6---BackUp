"""Archive ticket notification rules safely.

Revision ID: 0135_notification_rule_archive
Revises: 0134_satisfaction_delivery
"""

import sqlalchemy as sa

from alembic import op

revision = "0135_notification_rule_archive"
down_revision = "0134_satisfaction_delivery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ticket_notification_rules") as batch:
        batch.add_column(sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("deleted_by_user_id", sa.BigInteger(), nullable=True))
        batch.create_foreign_key("fk_ticket_notification_rules_deleted_by", "users", ["deleted_by_user_id"], ["id"])
    op.create_index("ix_ticket_notification_rules_active", "ticket_notification_rules", ["is_deleted", "is_enabled"])


def downgrade() -> None:
    op.drop_index("ix_ticket_notification_rules_active", table_name="ticket_notification_rules")
    with op.batch_alter_table("ticket_notification_rules") as batch:
        batch.drop_constraint("fk_ticket_notification_rules_deleted_by", type_="foreignkey")
        batch.drop_column("deleted_by_user_id")
        batch.drop_column("deleted_at")
        batch.drop_column("is_deleted")
