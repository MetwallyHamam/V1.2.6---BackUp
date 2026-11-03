"""explicit escalation parent link

Revision ID: 0056_escalation_parent
Revises: 0055_terminal_timestamps
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists, foreign_key_for_column_exists, index_exists

revision = "0056_escalation_parent"
down_revision = "0055_terminal_timestamps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not column_exists(bind, "tickets", "escalation_parent_ticket_id"):
        op.add_column(
            "tickets",
            sa.Column("escalation_parent_ticket_id", sa.BigInteger(), nullable=True),
        )
    if bind.dialect.name != "sqlite" and not foreign_key_for_column_exists(bind, "tickets", "escalation_parent_ticket_id"):
        op.create_foreign_key(
            "fk_tickets_escalation_parent_ticket_id",
            "tickets",
            "tickets",
            ["escalation_parent_ticket_id"],
            ["id"],
        )
    if not index_exists(bind, "tickets", "ix_tickets_escalation_parent_ticket_id"):
        op.create_index(
            "ix_tickets_escalation_parent_ticket_id",
            "tickets",
            ["escalation_parent_ticket_id"],
        )


def downgrade() -> None:
    op.drop_index("ix_tickets_escalation_parent_ticket_id", table_name="tickets")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint(
            "fk_tickets_escalation_parent_ticket_id", "tickets", type_="foreignkey"
        )
    op.drop_column("tickets", "escalation_parent_ticket_id")
