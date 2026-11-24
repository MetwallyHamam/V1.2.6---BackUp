"""Harden unified operations indexes and active timer concurrency.

Revision ID: 0292_unified_ops_hardening
Revises: 0291_project_kpi_dictionary
"""

import sqlalchemy as sa

from alembic import op

revision = "0292_unified_ops_hardening"
down_revision = "0291_project_kpi_dictionary"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_company_projects_hierarchy_active",
        "company_projects",
        ["account_id", "organization_id", "client_id", "is_active"],
    )
    op.create_index(
        "ix_company_project_departments_scope",
        "company_project_departments",
        ["department_id", "project_id"],
    )
    op.create_index(
        "ix_project_support_handovers_queue",
        "project_support_handovers",
        ["status", "updated_at", "project_id"],
    )
    op.create_index(
        "ux_project_work_logs_active_timer_user",
        "project_work_logs",
        ["user_id"],
        unique=True,
        mssql_where=sa.text("is_timer = 1 AND ended_at IS NULL"),
        sqlite_where=sa.text("is_timer = 1 AND ended_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_project_work_logs_active_timer_user", table_name="project_work_logs")
    op.drop_index("ix_project_support_handovers_queue", table_name="project_support_handovers")
    op.drop_index("ix_company_project_departments_scope", table_name="company_project_departments")
    op.drop_index("ix_company_projects_hierarchy_active", table_name="company_projects")
