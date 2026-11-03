"""add ticket internal escalation assignment

Revision ID: 0034_ticket_internal_escalation
Revises: 0033_ticket_form_default_value
"""

import sqlalchemy as sa

from alembic import op

revision = "0034_ticket_internal_escalation"
down_revision = "0033_ticket_form_default_value"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("escalation_assignee_user_id", sa.BigInteger(), nullable=True))
    op.add_column("tickets", sa.Column("escalation_level", sa.String(length=30), nullable=True))
    op.add_column("tickets", sa.Column("escalation_reason", sa.String(length=1000), nullable=True))
    op.add_column("tickets", sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True))
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_tickets_escalation_assignee_user_id_users",
            "tickets", "users", ["escalation_assignee_user_id"], ["id"],
        )
    op.create_index("ix_tickets_escalation_assignee", "tickets", ["escalation_assignee_user_id"])


def downgrade() -> None:
    op.drop_index("ix_tickets_escalation_assignee", table_name="tickets")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_tickets_escalation_assignee_user_id_users", "tickets", type_="foreignkey")
    op.drop_column("tickets", "escalated_at")
    op.drop_column("tickets", "escalation_reason")
    op.drop_column("tickets", "escalation_level")
    op.drop_column("tickets", "escalation_assignee_user_id")
