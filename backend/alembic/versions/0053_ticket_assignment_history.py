"""durable ticket assignment history

Revision ID: 0053_assignment_history
Revises: 0052_shared_default_contracts
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import index_exists, table_exists

revision = "0053_assignment_history"
down_revision = "0052_shared_default_contracts"
branch_labels = None
depends_on = None
id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    bind = op.get_bind()
    if not table_exists(bind, "ticket_assignment_history"):
        op.create_table(
        "ticket_assignment_history",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("ticket_id", id_type, nullable=False),
        sa.Column("assigned_user_id", id_type, nullable=True),
        sa.Column("assigned_team", sa.String(150), nullable=True),
        sa.Column("assigned_by_user_id", id_type, nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"]),
        )
    if not index_exists(bind, "ticket_assignment_history", "ix_ticket_assignment_history_user_created"):
        op.create_index(
            "ix_ticket_assignment_history_user_created",
            "ticket_assignment_history",
            ["assigned_user_id", "created_at"],
        )


def downgrade() -> None:
    op.drop_index("ix_ticket_assignment_history_user_created", table_name="ticket_assignment_history")
    op.drop_table("ticket_assignment_history")
