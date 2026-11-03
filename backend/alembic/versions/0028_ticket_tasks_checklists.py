"""add ticket tasks and checklist items

Revision ID: 0028_ticket_tasks_checklists
Revises: 0027_ticket_crm_context
"""

import sqlalchemy as sa

from alembic import op

revision = "0028_ticket_tasks_checklists"
down_revision = "0027_ticket_crm_context"
branch_labels = None
depends_on = None
id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "ticket_tasks",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("ticket_id", id_type, nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("assigned_user_id", id_type),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_by_user_id", id_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_ticket_tasks_ticket_status_due", "ticket_tasks", ["ticket_id", "status", "due_at"])
    op.create_table(
        "ticket_checklist_items",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("ticket_id", id_type, nullable=False),
        sa.Column("label", sa.String(300), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False),
        sa.Column("completed_by_user_id", id_type),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_by_user_id", id_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["completed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )


def downgrade() -> None:
    op.drop_table("ticket_checklist_items")
    op.drop_index("ix_ticket_tasks_ticket_status_due", table_name="ticket_tasks")
    op.drop_table("ticket_tasks")
