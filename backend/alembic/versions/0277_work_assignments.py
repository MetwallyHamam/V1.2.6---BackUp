"""add governed work assignments and engineer KPI attribution

Revision ID: 0277_work_assignments
Revises: 0276_notification_dismissal
"""

import sqlalchemy as sa

from alembic import op

revision = "0277_work_assignments"
down_revision = "0276_notification_dismissal"
branch_labels = None
depends_on = None
ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table("work_assignments",
        sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("title", sa.String(200), nullable=False), sa.Column("description", sa.Text(), nullable=False),
        sa.Column("assignment_type", sa.String(40), nullable=False, server_default="GENERAL"), sa.Column("activity_classification", sa.String(20), nullable=False, server_default="INTERNAL"),
        sa.Column("status", sa.String(30), nullable=False, server_default="ASSIGNED"), sa.Column("priority", sa.String(20), nullable=False, server_default="MEDIUM"), sa.Column("complexity", sa.String(20), nullable=False, server_default="STANDARD"),
        sa.Column("department_id", ID, sa.ForeignKey("departments.id")), sa.Column("owner_user_id", ID, sa.ForeignKey("users.id")), sa.Column("created_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("planned_start_at", sa.DateTime(timezone=True)), sa.Column("due_at", sa.DateTime(timezone=True)), sa.Column("estimated_minutes", sa.Integer()), sa.Column("actual_minutes", sa.Integer()),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"), sa.Column("completion_summary", sa.Text()), sa.Column("kpi_source_type", sa.String(30), nullable=False, server_default="ASSIGNMENT"), sa.Column("kpi_source_id", ID),
        sa.Column("requires_review", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("accepted_at", sa.DateTime(timezone=True)), sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()))
    op.create_index("ix_work_assignments_status_due", "work_assignments", ["status", "due_at"])
    op.create_index("ix_work_assignments_owner_status", "work_assignments", ["owner_user_id", "status"])
    op.create_table("work_assignment_assignees", sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("assignment_id", ID, sa.ForeignKey("work_assignments.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", ID, sa.ForeignKey("users.id"), nullable=False), sa.Column("role", sa.String(30), nullable=False, server_default="CONTRIBUTOR"), sa.Column("contribution_percent", sa.Integer(), nullable=False, server_default="0"), sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.UniqueConstraint("assignment_id", "user_id"))
    op.create_table("work_assignment_clients", sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("assignment_id", ID, sa.ForeignKey("work_assignments.id", ondelete="CASCADE"), nullable=False), sa.Column("client_id", ID, sa.ForeignKey("clients.id"), nullable=False), sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"), sa.Column("result_summary", sa.Text()), sa.UniqueConstraint("assignment_id", "client_id"))
    op.create_table("work_assignment_links", sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("assignment_id", ID, sa.ForeignKey("work_assignments.id", ondelete="CASCADE"), nullable=False), sa.Column("target_type", sa.String(30), nullable=False), sa.Column("target_id", ID, nullable=False), sa.Column("relation_type", sa.String(30), nullable=False, server_default="RELATED"), sa.Column("created_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.UniqueConstraint("assignment_id", "target_type", "target_id"))
    op.create_table("work_assignment_events", sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("assignment_id", ID, sa.ForeignKey("work_assignments.id", ondelete="CASCADE"), nullable=False), sa.Column("actor_user_id", ID, sa.ForeignKey("users.id")), sa.Column("event_type", sa.String(60), nullable=False), sa.Column("from_status", sa.String(30)), sa.Column("to_status", sa.String(30)), sa.Column("detail", sa.String(1000)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()))
    op.create_table("work_assignment_shares", sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("assignment_id", ID, sa.ForeignKey("work_assignments.id", ondelete="CASCADE"), nullable=False), sa.Column("token_hash", sa.String(64), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True)), sa.Column("revoked_at", sa.DateTime(timezone=True)), sa.Column("created_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()))
    op.create_index("ix_work_assignment_shares_token", "work_assignment_shares", ["token_hash"], unique=True)
    bind = op.get_bind()
    permissions = {
        "work_assignment.view.department": "View department work assignments",
        "work_assignment.view.all": "View all work assignments",
        "work_assignment.create": "Create and assign work assignments",
        "work_assignment.claim": "Claim a department queue assignment",
        "work_assignment.manage": "Manage and review work assignments",
        "work_assignment.share": "Create public work-assignment status links",
    }
    for code, description in permissions.items():
        if bind.execute(sa.text("SELECT id FROM permissions WHERE code=:code"), {"code": code}).scalar() is None:
            bind.execute(sa.text("INSERT INTO permissions (code,module,description,is_high_risk,is_active) VALUES (:code,'work_assignment',:description,:risk,1)"), {"code": code, "description": description, "risk": int(code in {"work_assignment.manage", "work_assignment.share"})})
    bind.execute(sa.text("INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,pm.id,'NONE' FROM profiles p CROSS JOIN permissions pm WHERE pm.code IN ('work_assignment.create','work_assignment.claim','work_assignment.view.department','work_assignment.manage','work_assignment.share') AND p.profile_type='ADMINISTRATOR' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=pm.id)"))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code LIKE 'work_assignment.%')"))
    bind.execute(sa.text("DELETE FROM permissions WHERE code LIKE 'work_assignment.%'"))
    op.drop_table("work_assignment_shares"); op.drop_table("work_assignment_events"); op.drop_table("work_assignment_links"); op.drop_table("work_assignment_clients"); op.drop_table("work_assignment_assignees"); op.drop_table("work_assignments")
