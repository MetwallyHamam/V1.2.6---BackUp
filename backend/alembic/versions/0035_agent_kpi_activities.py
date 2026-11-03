"""add agent KPI activity evidence

Revision ID: 0035_agent_kpi_activities
Revises: 0034_ticket_internal_escalation
"""

import sqlalchemy as sa

from alembic import op

revision = "0035_agent_kpi_activities"
down_revision = "0034_ticket_internal_escalation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_activities",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("activity_type", sa.String(length=30), nullable=False),
        sa.Column("participation_role", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("logged_by_user_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["logged_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_activities_user_occurred", "agent_activities", ["user_id", "occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_agent_activities_user_occurred", table_name="agent_activities")
    op.drop_table("agent_activities")
