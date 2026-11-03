"""Add complaint management workflow.

Revision ID: 0136_complaint_management
Revises: 0135_notification_rule_archive
"""

import sqlalchemy as sa

from alembic import op

revision = "0136_complaint_management"
down_revision = "0135_notification_rule_archive"
branch_labels = None
depends_on = None
id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table("complaint_reasons", sa.Column("id", id_type, primary_key=True, autoincrement=True), sa.Column("code", sa.String(40), nullable=False, unique=True), sa.Column("name", sa.String(150), nullable=False, unique=True), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table("complaints", sa.Column("id", id_type, primary_key=True, autoincrement=True), sa.Column("complaint_number", sa.String(40), nullable=False, unique=True), sa.Column("client_id", id_type, sa.ForeignKey("clients.id"), nullable=False), sa.Column("reason_id", id_type, sa.ForeignKey("complaint_reasons.id"), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("linked_ticket_id", id_type, sa.ForeignKey("tickets.id")), sa.Column("requester_contact_id", id_type, sa.ForeignKey("contacts.id")), sa.Column("assigned_user_id", id_type, sa.ForeignKey("users.id")), sa.Column("assigned_team_id", id_type, sa.ForeignKey("support_teams.id")), sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"), sa.Column("satisfaction_rating", sa.Integer()), sa.Column("satisfaction_comments", sa.String(2000)), sa.Column("client_closed_at", sa.DateTime(timezone=True)), sa.Column("created_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=False), sa.Column("version", sa.Integer(), nullable=False, server_default="1"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_complaints_number", "complaints", ["complaint_number"], unique=True)
    op.create_index("ix_complaints_status_owner", "complaints", ["status", "assigned_user_id", "assigned_team_id"])
    op.create_table("complaint_activities", sa.Column("id", id_type, primary_key=True, autoincrement=True), sa.Column("complaint_id", id_type, sa.ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False), sa.Column("activity_type", sa.String(50), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("actor_user_id", id_type, sa.ForeignKey("users.id")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_complaint_activities_complaint", "complaint_activities", ["complaint_id"])
    op.create_table("complaint_public_tokens", sa.Column("id", id_type, primary_key=True, autoincrement=True), sa.Column("complaint_id", id_type, sa.ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False), sa.Column("token_hash", sa.String(64), nullable=False, unique=True), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_complaint_tokens_hash", "complaint_public_tokens", ["token_hash"], unique=True)
    permissions = sa.table("permissions", sa.column("code", sa.String), sa.column("module", sa.String), sa.column("description", sa.String), sa.column("is_high_risk", sa.Boolean), sa.column("is_active", sa.Boolean))
    codes = ["complaint.create", "complaint.view.all", "complaint.manage", "complaint.update", "complaint.assign", "complaint.status.change", "complaint.tracking.send", "complaint.ticket.reopen"]
    op.bulk_insert(permissions, [{"code": code, "module": "complaints", "description": code.replace(".", " ").title(), "is_high_risk": code in {"complaint.manage", "complaint.ticket.reopen"}, "is_active": True} for code in codes])
    op.execute("INSERT INTO profile_permissions (profile_id, permission_id, scope_type) SELECT p.id, q.id, 'NONE' FROM profiles p CROSS JOIN permissions q WHERE p.code = 'ADMINISTRATOR' AND q.code LIKE 'complaint.%'")
    op.execute("INSERT INTO profile_permissions (profile_id, permission_id, scope_type) SELECT p.id, q.id, 'NONE' FROM profiles p CROSS JOIN permissions q WHERE p.code = 'SUPPORT_MANAGER' AND q.code LIKE 'complaint.%'")
    op.execute("INSERT INTO profile_permissions (profile_id, permission_id, scope_type) SELECT p.id, q.id, 'NONE' FROM profiles p CROSS JOIN permissions q WHERE p.code = 'CALL_CENTER' AND q.code IN ('complaint.create','complaint.update','complaint.assign','complaint.status.change','complaint.tracking.send')")
    reasons = sa.table("complaint_reasons", sa.column("code", sa.String), sa.column("name", sa.String), sa.column("is_active", sa.Boolean))
    op.bulk_insert(reasons, [{"code": "SERVICE_QUALITY", "name": "Service quality", "is_active": True}, {"code": "DELAY", "name": "Delay", "is_active": True}, {"code": "COMMUNICATION", "name": "Communication", "is_active": True}, {"code": "OTHER", "name": "Other", "is_active": True}])
    for key, value in [("complaint_tracking_enabled", "true"), ("complaint_email_enabled", "true"), ("complaint_whatsapp_enabled", "true"), ("complaint_satisfaction_enabled", "true"), ("complaint_client_closure_enabled", "true"), ("complaint_tracking_expiry_days", "30")]:
        op.execute(sa.text("INSERT INTO site_settings ([key], [value], updated_at) VALUES (:key, :value, CURRENT_TIMESTAMP)").bindparams(key=key, value=value))


def downgrade() -> None:
    op.execute("DELETE FROM site_settings WHERE [key] LIKE 'complaint_%'")
    op.execute("DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code LIKE 'complaint.%')")
    op.execute("DELETE FROM permissions WHERE code LIKE 'complaint.%'")
    op.drop_table("complaint_public_tokens")
    op.drop_table("complaint_activities")
    op.drop_table("complaints")
    op.drop_table("complaint_reasons")
