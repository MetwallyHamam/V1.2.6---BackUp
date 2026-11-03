"""separate reusable dashboard templates from effective assignments

Revision ID: 0151_dashboard_assignments
Revises: 0150_portal_caller_management
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0151_dashboard_assignments"
down_revision: str | None = "0150_portal_caller_management"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.add_column("dashboards", sa.Column("code", sa.String(80), nullable=True))
    op.add_column("dashboards", sa.Column("description", sa.String(500), nullable=True))
    op.add_column("dashboards", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.create_table(
        "dashboard_assignments",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("dashboard_id", ID, sa.ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_id", ID, sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=True),
        sa.Column("department_id", ID, sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("user_id", ID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("ix_dashboard_assignments_effective", "dashboard_assignments", ["is_active", "effective_from", "effective_until"])
    op.create_index("ix_dashboard_assignments_target", "dashboard_assignments", ["user_id", "profile_id", "department_id", "priority"])
    op.execute("UPDATE dashboards SET code = 'DASHBOARD_' || id WHERE code IS NULL" if op.get_bind().dialect.name == "sqlite" else "UPDATE dashboards SET code = 'DASHBOARD_' + CAST(id AS VARCHAR(30)) WHERE code IS NULL")
    op.create_index("ux_dashboards_code", "dashboards", ["code"], unique=True)
    op.execute("INSERT INTO dashboard_assignments (dashboard_id,user_id,priority,is_active,version,created_at,updated_at) SELECT id,assignment_id,100,is_active,1,created_at,updated_at FROM dashboards WHERE assignment_type='USER' AND assignment_id IS NOT NULL")
    op.execute("INSERT INTO dashboard_assignments (dashboard_id,profile_id,priority,is_active,version,created_at,updated_at) SELECT id,assignment_id,80,is_active,1,created_at,updated_at FROM dashboards WHERE assignment_type='PROFILE' AND assignment_id IS NOT NULL")
    op.execute("INSERT INTO dashboard_assignments (dashboard_id,department_id,priority,is_active,version,created_at,updated_at) SELECT id,assignment_id,60,is_active,1,created_at,updated_at FROM dashboards WHERE assignment_type='DEPARTMENT' AND assignment_id IS NOT NULL")
    op.execute("INSERT INTO dashboard_assignments (dashboard_id,priority,is_active,version,created_at,updated_at) SELECT id,0,is_active,1,created_at,updated_at FROM dashboards WHERE assignment_type='SYSTEM'")


def downgrade() -> None:
    op.drop_index("ix_dashboard_assignments_target", table_name="dashboard_assignments")
    op.drop_index("ix_dashboard_assignments_effective", table_name="dashboard_assignments")
    op.drop_table("dashboard_assignments")
    op.drop_index("ux_dashboards_code", table_name="dashboards")
    op.drop_column("dashboards", "version")
    op.drop_column("dashboards", "description")
    op.drop_column("dashboards", "code")
