"""scope dashboard assignments to their destination

Revision ID: 0166_dashboard_assignment_types
Revises: 0165_kpi_submission_batches
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0166_dashboard_assignment_types"
down_revision: str | None = "0165_kpi_submission_batches"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "dashboard_assignments",
        sa.Column("dashboard_type", sa.String(30), nullable=False, server_default="EXECUTIVE"),
    )
    op.drop_index("ix_dashboard_assignments_target", table_name="dashboard_assignments")
    op.create_index(
        "ix_dashboard_assignments_target",
        "dashboard_assignments",
        ["dashboard_type", "user_id", "profile_id", "department_id", "priority"],
    )


def downgrade() -> None:
    op.drop_index("ix_dashboard_assignments_target", table_name="dashboard_assignments")
    op.create_index(
        "ix_dashboard_assignments_target",
        "dashboard_assignments",
        ["user_id", "profile_id", "department_id", "priority"],
    )
    op.drop_column("dashboard_assignments", "dashboard_type")
