"""structured ticket pending follow-up

Revision ID: 0054_pending_follow_up
Revises: 0053_assignment_history
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists, foreign_key_for_column_exists, index_exists

revision = "0054_pending_follow_up"
down_revision = "0053_assignment_history"
branch_labels = None
depends_on = None
id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    bind = op.get_bind()
    if not column_exists(bind, "tickets", "pending_reason"):
        op.add_column("tickets", sa.Column("pending_reason", sa.String(500), nullable=True))
    if not column_exists(bind, "tickets", "pending_owner_user_id"):
        op.add_column("tickets", sa.Column("pending_owner_user_id", id_type, nullable=True))
    if not column_exists(bind, "tickets", "pending_follow_up_at"):
        op.add_column("tickets", sa.Column("pending_follow_up_at", sa.DateTime(timezone=True), nullable=True))
    if bind.dialect.name != "sqlite" and not foreign_key_for_column_exists(bind, "tickets", "pending_owner_user_id"):
        op.create_foreign_key(
            "fk_tickets_pending_owner",
            "tickets",
            "users",
            ["pending_owner_user_id"],
            ["id"],
        )
    if not index_exists(bind, "tickets", "ix_tickets_pending_follow_up"):
        op.create_index("ix_tickets_pending_follow_up", "tickets", ["pending_follow_up_at"])


def downgrade() -> None:
    op.drop_index("ix_tickets_pending_follow_up", table_name="tickets")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_tickets_pending_owner", "tickets", type_="foreignkey")
    op.drop_column("tickets", "pending_follow_up_at")
    op.drop_column("tickets", "pending_owner_user_id")
    op.drop_column("tickets", "pending_reason")
