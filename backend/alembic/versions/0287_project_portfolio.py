"""Project portfolio foundation.

Revision ID: 0287_project_portfolio
Revises: 0286_department_policies
"""

import sqlalchemy as sa

from alembic import op

revision = "0287_project_portfolio"
down_revision = "0286_department_policies"
branch_labels = None
depends_on = None

ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "company_projects",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("project_number", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("account_id", ID, sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("organization_id", ID, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("client_id", ID, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("primary_branch_id", ID, sa.ForeignKey("branches.id")),
        sa.Column("owning_department_id", ID, sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("project_manager_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="INTAKE"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="NORMAL"),
        sa.Column("health", sa.String(20), nullable=False, server_default="NOT_ASSESSED"),
        sa.Column("planned_start_date", sa.Date()),
        sa.Column("planned_end_date", sa.Date()),
        sa.Column("actual_start_date", sa.Date()),
        sa.Column("actual_end_date", sa.Date()),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_number"),
    )
    op.create_index(
        "ix_company_projects_portfolio",
        "company_projects",
        ["status", "health", "owning_department_id"],
    )
    op.create_table(
        "company_project_branch_scopes",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "project_id",
            ID,
            sa.ForeignKey("company_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("branch_id", ID, sa.ForeignKey("branches.id"), nullable=False),
        sa.UniqueConstraint("project_id", "branch_id"),
    )
    op.create_table(
        "company_project_departments",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "project_id",
            ID,
            sa.ForeignKey("company_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("department_id", ID, sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("role", sa.String(40), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("project_id", "department_id", "role"),
    )
    op.create_table(
        "company_project_teams",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "project_id",
            ID,
            sa.ForeignKey("company_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("team_id", ID, sa.ForeignKey("support_teams.id"), nullable=False),
        sa.Column("role", sa.String(40), nullable=False),
        sa.UniqueConstraint("project_id", "team_id", "role"),
    )
    op.create_table(
        "company_project_phases",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "project_id",
            ID,
            sa.ForeignKey("company_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PLANNED"),
        sa.Column("planned_start_date", sa.Date()),
        sa.Column("planned_end_date", sa.Date()),
        sa.UniqueConstraint("project_id", "sequence"),
    )
    op.create_table(
        "company_project_milestones",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "project_id",
            ID,
            sa.ForeignKey("company_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phase_id", ID, sa.ForeignKey("company_project_phases.id")),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("due_date", sa.Date()),
        sa.Column("status", sa.String(30), nullable=False, server_default="PLANNED"),
        sa.Column("is_gate", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "company_project_assignment_requests",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "project_id",
            ID,
            sa.ForeignKey("company_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requested_department_id", ID, sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("requested_team_id", ID, sa.ForeignKey("support_teams.id")),
        sa.Column("requested_start_date", sa.Date()),
        sa.Column("requested_end_date", sa.Date()),
        sa.Column("capability_notes", sa.Text()),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("requested_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("responded_by_user_id", ID, sa.ForeignKey("users.id")),
        sa.Column("response_notes", sa.Text()),
        sa.Column("responded_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for table in [
        "company_project_assignment_requests",
        "company_project_milestones",
        "company_project_phases",
        "company_project_teams",
        "company_project_departments",
        "company_project_branch_scopes",
    ]:
        op.drop_table(table)
    op.drop_index("ix_company_projects_portfolio", table_name="company_projects")
    op.drop_table("company_projects")
