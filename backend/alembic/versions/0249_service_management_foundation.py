"""Add Problem, Major Incident, and Change Request foundations.

Revision ID: 0249_service_management
Revises: 0248_portal_client_profile
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0249_service_management"
down_revision: str | None = "0248_portal_client_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _timestamps() -> list[sa.Column]:
    return [sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False)]


def upgrade() -> None:
    op.create_table("problems",
        sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("problem_number", sa.String(40), nullable=False, unique=True),
        sa.Column("title", sa.Unicode(250), nullable=False), sa.Column("description", sa.UnicodeText(), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("owner_user_id", ID, sa.ForeignKey("users.id")), sa.Column("owner_team_id", ID, sa.ForeignKey("support_teams.id")),
        sa.Column("product_id", ID, sa.ForeignKey("products.id")), sa.Column("product_module_id", ID, sa.ForeignKey("product_modules.id")), sa.Column("environment_id", ID, sa.ForeignKey("environments.id")),
        sa.Column("business_impact", sa.UnicodeText()), sa.Column("symptoms", sa.UnicodeText()), sa.Column("workaround", sa.UnicodeText()), sa.Column("known_error_summary", sa.UnicodeText()), sa.Column("root_cause_summary", sa.UnicodeText()), sa.Column("permanent_fix_summary", sa.UnicodeText()),
        sa.Column("target_resolution_date", sa.DateTime(timezone=True)), sa.Column("resolved_at", sa.DateTime(timezone=True)), sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("created_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False), sa.Column("version", sa.Integer(), nullable=False), *_timestamps())
    op.create_index("ix_problems_number", "problems", ["problem_number"], unique=True)
    op.create_index("ix_problems_status_owner", "problems", ["status", "owner_user_id", "owner_team_id"])
    op.create_table("problem_ticket_links",
        sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("problem_id", ID, sa.ForeignKey("problems.id", ondelete="CASCADE"), nullable=False), sa.Column("ticket_id", ID, sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False), sa.Column("link_type", sa.String(30), nullable=False), sa.Column("linked_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False), sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("problem_id", "ticket_id", "link_type"))
    op.create_index("ix_problem_ticket_problem", "problem_ticket_links", ["problem_id"]); op.create_index("ix_problem_ticket_ticket", "problem_ticket_links", ["ticket_id"])
    op.create_table("problem_root_causes", sa.Column("problem_id", ID, sa.ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True), sa.Column("root_cause_id", ID, sa.ForeignKey("root_causes.id"), primary_key=True))
    op.create_table("problem_change_links",
        sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("problem_id", ID, sa.ForeignKey("problems.id", ondelete="CASCADE"), nullable=False), sa.Column("change_ticket_id", ID, sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False), sa.Column("link_type", sa.String(30), nullable=False), sa.Column("linked_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False), sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("problem_id", "change_ticket_id", "link_type"))
    op.create_index("ix_problem_change_problem", "problem_change_links", ["problem_id"]); op.create_index("ix_problem_change_ticket", "problem_change_links", ["change_ticket_id"])
    op.create_table("problem_status_history", sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("problem_id", ID, sa.ForeignKey("problems.id", ondelete="CASCADE"), nullable=False), sa.Column("from_status", sa.String(40), nullable=False), sa.Column("to_status", sa.String(40), nullable=False), sa.Column("reason", sa.Unicode(2000)), sa.Column("changed_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False), sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_problem_history_problem", "problem_status_history", ["problem_id"])

    op.create_table("major_incidents",
        sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("major_incident_number", sa.String(40), nullable=False, unique=True), sa.Column("primary_ticket_id", ID, sa.ForeignKey("tickets.id"), nullable=False, unique=True),
        sa.Column("severity", sa.String(20), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("incident_commander_user_id", ID, sa.ForeignKey("users.id"), nullable=False), sa.Column("technical_owner_user_id", ID, sa.ForeignKey("users.id")), sa.Column("communication_owner_user_id", ID, sa.ForeignKey("users.id")),
        sa.Column("declared_at", sa.DateTime(timezone=True), nullable=False), sa.Column("detected_at", sa.DateTime(timezone=True)), sa.Column("service_restored_at", sa.DateTime(timezone=True)), sa.Column("monitoring_started_at", sa.DateTime(timezone=True)), sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("business_impact", sa.UnicodeText(), nullable=False), sa.Column("affected_users", sa.Unicode(500)), sa.Column("current_status_summary", sa.UnicodeText(), nullable=False), sa.Column("next_update_at", sa.DateTime(timezone=True)), sa.Column("resolution_summary", sa.UnicodeText()), sa.Column("post_incident_review", sa.UnicodeText()),
        sa.Column("created_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False), sa.Column("version", sa.Integer(), nullable=False), *_timestamps())
    op.create_index("ix_major_incident_number", "major_incidents", ["major_incident_number"], unique=True); op.create_index("ix_major_incident_status", "major_incidents", ["status"])
    op.create_table("major_incident_ticket_links", sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("major_incident_id", ID, sa.ForeignKey("major_incidents.id", ondelete="CASCADE"), nullable=False), sa.Column("ticket_id", ID, sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False), sa.Column("link_type", sa.String(20), nullable=False), sa.Column("linked_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False), sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("major_incident_id", "ticket_id"))
    op.create_index("ix_major_link_incident", "major_incident_ticket_links", ["major_incident_id"]); op.create_index("ix_major_link_ticket", "major_incident_ticket_links", ["ticket_id"])
    op.create_table("major_incident_updates", sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("major_incident_id", ID, sa.ForeignKey("major_incidents.id", ondelete="CASCADE"), nullable=False), sa.Column("update_type", sa.String(20), nullable=False), sa.Column("internal_message", sa.UnicodeText()), sa.Column("client_message", sa.UnicodeText()), sa.Column("published_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False), sa.Column("published_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_major_update_incident", "major_incident_updates", ["major_incident_id"])

    op.create_table("change_request_details",
        sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("ticket_id", ID, sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("request_kind", sa.String(40), nullable=False),
        sa.Column("purpose", sa.UnicodeText(), nullable=False), sa.Column("detailed_description", sa.UnicodeText(), nullable=False), sa.Column("business_impact", sa.UnicodeText(), nullable=False), sa.Column("expected_result", sa.UnicodeText(), nullable=False),
        sa.Column("affected_product_id", ID, sa.ForeignKey("products.id")), sa.Column("affected_module_id", ID, sa.ForeignKey("product_modules.id")), sa.Column("required_permissions", sa.UnicodeText()), sa.Column("requested_priority", sa.String(20), nullable=False), sa.Column("change_status", sa.String(40), nullable=False), sa.Column("assessment_owner_user_id", ID, sa.ForeignKey("users.id")),
        sa.Column("technical_impact", sa.UnicodeText()), sa.Column("security_impact", sa.UnicodeText()), sa.Column("data_impact", sa.UnicodeText()), sa.Column("downtime_required", sa.Boolean(), nullable=False), sa.Column("risk_level", sa.String(20)), sa.Column("estimated_effort", sa.Unicode(200)), sa.Column("target_release", sa.Unicode(100)),
        sa.Column("planned_start_at", sa.DateTime(timezone=True)), sa.Column("planned_end_at", sa.DateTime(timezone=True)), sa.Column("implementation_plan", sa.UnicodeText()), sa.Column("rollback_plan", sa.UnicodeText()), sa.Column("test_plan", sa.UnicodeText()), sa.Column("validation_result", sa.UnicodeText()), sa.Column("version", sa.Integer(), nullable=False), *_timestamps())
    op.create_index("ix_change_detail_ticket", "change_request_details", ["ticket_id"], unique=True); op.create_index("ix_change_detail_status", "change_request_details", ["change_status"])
    op.create_table("change_request_approvals", sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("change_request_id", ID, sa.ForeignKey("change_request_details.id", ondelete="CASCADE"), nullable=False), sa.Column("approval_stage", sa.String(50), nullable=False), sa.Column("cycle_number", sa.Integer(), nullable=False), sa.Column("approver_user_id", ID, sa.ForeignKey("users.id"), nullable=False), sa.Column("decision", sa.String(20), nullable=False), sa.Column("comment", sa.Unicode(2000)), sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False), sa.Column("decided_at", sa.DateTime(timezone=True)), sa.Column("version", sa.Integer(), nullable=False))
    op.create_index("ix_change_approvals_request_stage", "change_request_approvals", ["change_request_id", "approval_stage"])
    op.create_table("change_request_status_history", sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("change_request_id", ID, sa.ForeignKey("change_request_details.id", ondelete="CASCADE"), nullable=False), sa.Column("from_status", sa.String(40), nullable=False), sa.Column("to_status", sa.String(40), nullable=False), sa.Column("reason", sa.Unicode(2000)), sa.Column("changed_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False), sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_change_history_request", "change_request_status_history", ["change_request_id"])

    bind = op.get_bind()
    permissions = ["problem.view","problem.create","problem.edit","problem.assign","problem.link_ticket","problem.identify_root_cause","problem.publish_known_error","problem.close","problem.reopen","major_incident.view","major_incident.declare","major_incident.command","major_incident.link_ticket","major_incident.publish_update","major_incident.restore_service","major_incident.close","change_request.view","change_request.create","change_request.assess","change_request.approve","change_request.plan","change_request.implement","change_request.validate","change_request.complete","change_request.rollback"]
    for code in permissions:
        if bind.execute(sa.text("SELECT id FROM permissions WHERE code=:code"), {"code": code}).scalar() is None:
            bind.execute(sa.text("INSERT INTO permissions (code,module,description,is_high_risk,is_active) VALUES (:code,:module,:description,:risk,:active)"), {"code": code, "module": code.split(".")[0], "description": code.replace(".", " ").title(), "risk": False, "active": True})
    for profile_code in ("SUPPORT_MANAGER", "ADMINISTRATOR"):
        profile_id = bind.execute(sa.text("SELECT id FROM profiles WHERE code=:code"), {"code": profile_code}).scalar()
        if profile_id:
            for code in permissions:
                permission_id = bind.execute(sa.text("SELECT id FROM permissions WHERE code=:code"), {"code": code}).scalar_one()
                if bind.execute(sa.text("SELECT 1 FROM profile_permissions WHERE profile_id=:p AND permission_id=:q"), {"p": profile_id, "q": permission_id}).first() is None:
                    bind.execute(sa.text("INSERT INTO profile_permissions (profile_id,permission_id,scope_type) VALUES (:p,:q,'NONE')"), {"p": profile_id, "q": permission_id})


def downgrade() -> None:
    for table in ("change_request_status_history", "change_request_approvals", "change_request_details", "major_incident_updates", "major_incident_ticket_links", "major_incidents", "problem_status_history", "problem_change_links", "problem_root_causes", "problem_ticket_links", "problems"):
        op.drop_table(table)
