"""Widen project status for governed publication states.

Revision ID: 0294_project_status_capacity
Revises: 0293_project_creation_wizard
"""

import sqlalchemy as sa

from alembic import op

revision = "0294_project_status_capacity"
down_revision = "0293_project_creation_wizard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("company_projects") as batch:
        batch.alter_column(
            "status",
            existing_type=sa.String(length=30),
            type_=sa.String(length=50),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("company_projects") as batch:
        batch.alter_column(
            "status",
            existing_type=sa.String(length=50),
            type_=sa.String(length=30),
            existing_nullable=False,
        )
