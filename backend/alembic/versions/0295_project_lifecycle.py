"""Add governed project lifecycle history and concurrency versions.

Revision ID: 0295_project_lifecycle
Revises: 0294_project_status_capacity
"""

import sqlalchemy as sa

from alembic import op

revision = "0295_project_lifecycle"
down_revision = "0294_project_status_capacity"
branch_labels = None
depends_on = None
ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    with op.batch_alter_table("company_projects") as batch:
        batch.add_column(sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"))
    with op.batch_alter_table("company_project_assignment_requests") as batch:
        batch.add_column(sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"))
    op.create_table(
        "project_status_transitions",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column(
            "project_id",
            ID,
            sa.ForeignKey("company_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(50), nullable=False),
        sa.Column("to_status", sa.String(50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("actor_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_project_status_transitions_project_time",
        "project_status_transitions",
        ["project_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_status_transitions_project_time",
        table_name="project_status_transitions",
    )
    op.drop_table("project_status_transitions")
    with op.batch_alter_table("company_project_assignment_requests") as batch:
        batch.drop_column("row_version")
    with op.batch_alter_table("company_projects") as batch:
        batch.drop_column("row_version")


