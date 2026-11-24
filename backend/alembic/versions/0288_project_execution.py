"""Project execution foundation.

Revision ID: 0288_project_execution
Revises: 0287_project_portfolio
"""

import sqlalchemy as sa

from alembic import op

revision = "0288_project_execution"
down_revision = "0287_project_portfolio"
branch_labels = None
depends_on = None
ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "project_tasks",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "project_id",
            ID,
            sa.ForeignKey("company_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phase_id", ID, sa.ForeignKey("company_project_phases.id")),
        sa.Column("task_number", sa.String(50), nullable=False),
        sa.Column("title", sa.String(250), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("classification", sa.String(20), nullable=False, server_default="PLANNED"),
        sa.Column("status", sa.String(30), nullable=False, server_default="BACKLOG"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="NORMAL"),
        sa.Column("owner_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("planned_start_date", sa.Date()),
        sa.Column("planned_end_date", sa.Date()),
        sa.Column("estimate_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_summary", sa.Text()),
        sa.Column("baseline_reference", sa.String(150)),
        sa.Column("unplanned_cause", sa.String(500)),
        sa.Column("unplanned_source", sa.String(80)),
        sa.Column("impact_summary", sa.Text()),
        sa.Column("schedule_impact_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("approval_status", sa.String(30), nullable=False, server_default="NOT_REQUIRED"),
        sa.Column("approved_by_user_id", ID, sa.ForeignKey("users.id")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("approval_notes", sa.Text()),
        sa.Column("created_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "task_number"),
    )
    op.create_index(
        "ix_project_tasks_execution", "project_tasks", ["project_id", "status", "classification"]
    )
    op.create_table(
        "project_task_assignees",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "task_id", ID, sa.ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("allocation_percent", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("planned_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_accountable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("task_id", "user_id"),
    )
    op.create_table(
        "project_task_dependencies",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "task_id", ID, sa.ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("depends_on_task_id", ID, sa.ForeignKey("project_tasks.id"), nullable=False),
        sa.Column(
            "dependency_type", sa.String(30), nullable=False, server_default="FINISH_TO_START"
        ),
        sa.UniqueConstraint("task_id", "depends_on_task_id"),
    )
    op.create_table(
        "project_work_logs",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "task_id", ID, sa.ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("duration_minutes", sa.Integer()),
        sa.Column("notes", sa.Text()),
        sa.Column("is_timer", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_project_work_logs_user_time", "project_work_logs", ["user_id", "started_at"]
    )
    op.create_table(
        "project_task_blockers",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "task_id", ID, sa.ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("impact", sa.Text(), nullable=False),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "project_evidence",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "project_id",
            ID,
            sa.ForeignKey("company_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Keep evidence when an optional task is removed and avoid a SQL Server
        # multiple-cascade path (project -> task -> evidence and project -> evidence).
        sa.Column("task_id", ID, sa.ForeignKey("project_tasks.id")),
        sa.Column("evidence_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("reference_url", sa.String(1000)),
        sa.Column("notes", sa.Text()),
        sa.Column("visibility", sa.String(30), nullable=False, server_default="PROJECT_PRIVATE"),
        sa.Column("created_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "project_task_reviews",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "task_id", ID, sa.ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("reviewer_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for table in ["project_task_reviews", "project_evidence", "project_task_blockers"]:
        op.drop_table(table)
    op.drop_index("ix_project_work_logs_user_time", table_name="project_work_logs")
    op.drop_table("project_work_logs")
    op.drop_table("project_task_dependencies")
    op.drop_table("project_task_assignees")
    op.drop_index("ix_project_tasks_execution", table_name="project_tasks")
    op.drop_table("project_tasks")
