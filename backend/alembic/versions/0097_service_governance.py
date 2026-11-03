"""Add immutable SLA versions, governed worklogs, feedback evidence, and outcomes.

Revision ID: 0097_service_governance
Revises: 0096_org_hierarchy
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists, table_exists

revision = "0097_service_governance"
down_revision = "0096_org_hierarchy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    if not table_exists(bind, "sla_policy_versions"):
        op.create_table(
            "sla_policy_versions",
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("policy_id", id_type, sa.ForeignKey("sla_policies.id", ondelete="CASCADE"), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("name_snapshot", sa.String(200), nullable=False),
            sa.Column("calendar_id", id_type, sa.ForeignKey("business_calendars.id"), nullable=False),
            sa.Column("calculation_version", sa.String(30), nullable=False),
            sa.Column("include_escalation_time", sa.Boolean(), nullable=False),
            sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
            sa.Column("effective_until", sa.DateTime(timezone=True)),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("created_by_user_id", id_type, sa.ForeignKey("users.id")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("published_at", sa.DateTime(timezone=True)),
            sa.UniqueConstraint("policy_id", "version", name="uq_sla_policy_version"),
        )
    if not table_exists(bind, "sla_target_versions"):
        op.create_table(
            "sla_target_versions",
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("policy_version_id", id_type, sa.ForeignKey("sla_policy_versions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source_target_id", id_type, sa.ForeignKey("sla_targets.id")),
            sa.Column("product_id", id_type, sa.ForeignKey("products.id")),
            sa.Column("product_module_id", id_type, sa.ForeignKey("product_modules.id")),
            sa.Column("service_id", id_type, sa.ForeignKey("service_catalog_items.id")),
            sa.Column("priority", sa.String(5), nullable=False),
            sa.Column("context_key", sa.String(120), nullable=False),
            sa.Column("is_fallback", sa.Boolean(), nullable=False),
            sa.Column("effective_from", sa.DateTime(timezone=True)),
            sa.Column("effective_until", sa.DateTime(timezone=True)),
            sa.Column("first_response_minutes", sa.Integer(), nullable=False),
            sa.Column("resolution_minutes", sa.Integer(), nullable=False),
            sa.Column("warning_percent", sa.Integer(), nullable=False),
            sa.UniqueConstraint("policy_version_id", "context_key", name="uq_sla_target_version_context"),
        )
    policy_result = bind.execute(sa.text("SELECT id, version, name, calendar_id, calculation_version, include_escalation_time FROM sla_policies"))
    # pyodbc without MARS cannot issue another command while a result cursor is open.
    policies = list(policy_result.mappings().all())
    policy_result.close()
    for policy in policies:
        policy_values = dict(policy)
        policy_values["policy_id"] = policy["id"]
        bind.execute(sa.text("INSERT INTO sla_policy_versions (policy_id, version, name_snapshot, calendar_id, calculation_version, include_escalation_time, effective_from, status, created_at, published_at) SELECT :policy_id, :version, :name, :calendar_id, :calculation_version, :include_escalation_time, CURRENT_TIMESTAMP, 'PUBLISHED', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM sla_policy_versions WHERE policy_id=:policy_id AND version=:version)"), policy_values)
        version_id = bind.execute(sa.text("SELECT id FROM sla_policy_versions WHERE policy_id=:policy_id AND version=:version"), policy_values).scalar_one()
        target_result = bind.execute(sa.text("SELECT id, product_id, product_module_id, service_id, priority, context_key, is_fallback, effective_from, effective_until, first_response_minutes, resolution_minutes, warning_percent FROM sla_targets WHERE policy_id=:policy_id"), {"policy_id": policy["id"]})
        targets = list(target_result.mappings().all())
        target_result.close()
        for target in targets:
            values = dict(target); values["policy_version_id"] = version_id
            bind.execute(sa.text("INSERT INTO sla_target_versions (policy_version_id, source_target_id, product_id, product_module_id, service_id, priority, context_key, is_fallback, effective_from, effective_until, first_response_minutes, resolution_minutes, warning_percent) SELECT :policy_version_id, :id, :product_id, :product_module_id, :service_id, :priority, :context_key, :is_fallback, :effective_from, :effective_until, :first_response_minutes, :resolution_minutes, :warning_percent WHERE NOT EXISTS (SELECT 1 FROM sla_target_versions WHERE policy_version_id=:policy_version_id AND context_key=:context_key)"), values)

    for name, kind in (
        ("policy_version_id", id_type), ("policy_code_snapshot", sa.String(80)),
        ("policy_name_snapshot", sa.String(200)), ("target_context_snapshot", sa.String(120)),
    ):
        if not column_exists(bind, "ticket_sla_clocks", name):
            op.add_column("ticket_sla_clocks", sa.Column(name, kind))
    bind.execute(sa.text("UPDATE ticket_sla_clocks SET policy_code_snapshot=(SELECT code FROM sla_policies WHERE sla_policies.id=ticket_sla_clocks.policy_id), policy_name_snapshot=(SELECT name FROM sla_policies WHERE sla_policies.id=ticket_sla_clocks.policy_id), target_context_snapshot=(SELECT context_key FROM sla_targets WHERE sla_targets.id=ticket_sla_clocks.target_id), policy_version_id=(SELECT id FROM sla_policy_versions WHERE sla_policy_versions.policy_id=ticket_sla_clocks.policy_id AND sla_policy_versions.version=ticket_sla_clocks.policy_version)"))

    if not table_exists(bind, "resolution_outcomes"):
        op.create_table("resolution_outcomes", sa.Column("id", id_type, primary_key=True, autoincrement=True), sa.Column("code", sa.String(50), nullable=False, unique=True), sa.Column("name", sa.String(150), nullable=False, unique=True), sa.Column("description", sa.String(1000)), sa.Column("requires_permanent_fix", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        for code, name, requires_fix in (("RESOLVED_PERMANENT", "Permanent resolution", True), ("WORKAROUND", "Workaround supplied", True), ("CONFIGURATION", "Configuration corrected", False), ("USER_GUIDANCE", "User guidance supplied", False), ("DUPLICATE", "Duplicate", False), ("NO_FAULT_FOUND", "No fault found", False)):
            bind.execute(sa.text("INSERT INTO resolution_outcomes (code, name, requires_permanent_fix, is_active) VALUES (:code, :name, :requires_fix, :active)"), {"code": code, "name": name, "requires_fix": requires_fix, "active": True})
    for name, kind in (("resolution_outcome_id", id_type), ("permanent_fix_summary", sa.Text()), ("permanent_fix_status", sa.String(30))):
        if not column_exists(bind, "tickets", name): op.add_column("tickets", sa.Column(name, kind))

    if not table_exists(bind, "ticket_worklogs"):
        op.create_table(
            "ticket_worklogs", sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("ticket_id", id_type, sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("task_id", id_type, sa.ForeignKey("ticket_tasks.id")), sa.Column("user_id", id_type, sa.ForeignKey("users.id"), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False), sa.Column("ended_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("duration_minutes", sa.Integer(), nullable=False), sa.Column("notes", sa.String(2000), nullable=False), sa.Column("status", sa.String(20), nullable=False),
            sa.Column("approved_by_user_id", id_type, sa.ForeignKey("users.id")), sa.Column("approved_at", sa.DateTime(timezone=True)), sa.Column("rejection_reason", sa.String(500)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("version", sa.Integer(), nullable=False),
            sa.CheckConstraint("ended_at > started_at", name="ck_ticket_worklog_dates"), sa.CheckConstraint("duration_minutes > 0", name="ck_ticket_worklog_duration"),
        )
        op.create_index("ix_ticket_worklogs_user_dates", "ticket_worklogs", ["user_id", "started_at", "ended_at"])
        op.create_index("ix_ticket_worklogs_ticket_status", "ticket_worklogs", ["ticket_id", "status"])
    for name, kind, default in (("feedback_source", sa.String(30), "CUSTOMER"), ("eligibility_status", sa.String(30), "ELIGIBLE"), ("eligibility_reason", sa.String(500), None), ("metric_eligible", sa.Boolean(), True)):
        if not column_exists(bind, "ticket_satisfaction", name):
            op.add_column("ticket_satisfaction", sa.Column(name, kind, nullable=True))
            if default is not None:
                bind.execute(sa.text(f"UPDATE ticket_satisfaction SET {name}=:value WHERE {name} IS NULL"), {"value": default})


def downgrade() -> None:
    bind = op.get_bind()
    for name in ("metric_eligible", "eligibility_reason", "eligibility_status", "feedback_source"):
        if column_exists(bind, "ticket_satisfaction", name): op.drop_column("ticket_satisfaction", name)
    if table_exists(bind, "ticket_worklogs"): op.drop_table("ticket_worklogs")
    for name in ("permanent_fix_status", "permanent_fix_summary", "resolution_outcome_id"):
        if column_exists(bind, "tickets", name): op.drop_column("tickets", name)
    if table_exists(bind, "resolution_outcomes"): op.drop_table("resolution_outcomes")
    for name in ("target_context_snapshot", "policy_name_snapshot", "policy_code_snapshot", "policy_version_id"):
        if column_exists(bind, "ticket_sla_clocks", name): op.drop_column("ticket_sla_clocks", name)
    for table in ("sla_target_versions", "sla_policy_versions"):
        if table_exists(bind, table): op.drop_table(table)
