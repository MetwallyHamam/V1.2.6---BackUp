"""Add governed project KPI dictionary.

Revision ID: 0291_project_kpi_dictionary
Revises: 0290_project_support_handover
"""

from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision = "0291_project_kpi_dictionary"
down_revision = "0290_project_support_handover"
branch_labels = None
depends_on = None
ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

PERMISSIONS = {
    "analytics.dictionary.view": "View governed KPI definitions and scope rules",
    "analytics.project.view": "View authorized Project Management analytics",
    "analytics.implementation.view": "View authorized Implementation analytics",
    "analytics.support_readiness.view": "View authorized Support readiness analytics",
    "analytics.executive.view": "View authorized executive aggregate analytics",
}

DEFINITIONS = [
    ("PROJECT_ON_TIME_RATE", "Projects on time", "PROJECT", "Projects not overdue / eligible active projects * 100", "COUNT(projects not overdue)", "COUNT(eligible active projects)", "PERCENT", "HIGHER_IS_BETTER", "PROJECT_PORTFOLIO", "analytics.project.view", "/api/v1/projects", "PROJECT_MANAGEMENT"),
    ("MILESTONE_ON_TIME_RATE", "Milestones on time", "PROJECT", "Milestones completed by due date / completed milestones * 100", "COUNT(on-time completed milestones)", "COUNT(completed milestones with due date)", "PERCENT", "HIGHER_IS_BETTER", "PROJECT_PORTFOLIO", "analytics.project.view", "/api/v1/projects/{project_id}/execution", "PROJECT_MANAGEMENT"),
    ("TASK_ON_TIME_RATE", "Tasks on time", "IMPLEMENTATION", "Tasks completed by planned end / completed planned tasks * 100", "COUNT(on-time planned tasks)", "COUNT(completed planned tasks)", "PERCENT", "HIGHER_IS_BETTER", "DEPARTMENT", "analytics.implementation.view", "/api/v1/projects/{project_id}/execution", "IMPLEMENTATION"),
    ("UNPLANNED_EFFORT_PERCENT", "Unplanned effort", "IMPLEMENTATION", "Approved unplanned work minutes / all work minutes * 100", "SUM(approved unplanned minutes)", "SUM(all eligible work minutes)", "PERCENT", "LOWER_IS_BETTER", "DEPARTMENT", "analytics.implementation.view", "/api/v1/project-tasks/my-work", "IMPLEMENTATION"),
    ("ESTIMATE_ACCURACY_PERCENT", "Estimate accuracy", "IMPLEMENTATION", "MIN(planned, actual) / MAX(planned, actual) * 100", "Comparable planned and actual minutes", "Eligible completed tasks with planned and actual minutes", "PERCENT", "HIGHER_IS_BETTER", "DEPARTMENT", "analytics.implementation.view", "/api/v1/projects/{project_id}/execution", "IMPLEMENTATION"),
    ("BLOCKED_TASK_AGING_HOURS", "Blocked task aging", "IMPLEMENTATION", "Current time - blocker creation time for open blockers", "SUM(open blocker age hours)", "COUNT(open blockers)", "HOURS", "LOWER_IS_BETTER", "DEPARTMENT", "analytics.implementation.view", "/api/v1/projects/{project_id}/execution", "IMPLEMENTATION"),
    ("FIRST_PASS_REVIEW_RATE", "First-pass review rate", "IMPLEMENTATION", "Tasks accepted on first review / reviewed tasks * 100", "COUNT(first-review accepted tasks)", "COUNT(tasks with a review)", "PERCENT", "HIGHER_IS_BETTER", "DEPARTMENT", "analytics.implementation.view", "/api/v1/projects/{project_id}/execution", "IMPLEMENTATION"),
    ("HANDOVER_READINESS_PERCENT", "Handover readiness", "SUPPORT_READINESS", "Ready required handover items / required handover items * 100", "COUNT(required ready items)", "COUNT(required items)", "PERCENT", "HIGHER_IS_BETTER", "CUSTOMER", "analytics.support_readiness.view", "/api/v1/projects/{project_id}/handover", "SUPPORT"),
    ("HANDOVER_CYCLE_HOURS", "Handover cycle time", "SUPPORT_READINESS", "Support activation time - first submission time", "SUM(handover cycle hours)", "COUNT(activated handovers)", "HOURS", "LOWER_IS_BETTER", "CUSTOMER", "analytics.support_readiness.view", "/api/v1/projects/{project_id}/handover", "SUPPORT"),
    ("OPEN_RESIDUAL_ITEM_COUNT", "Open residual items", "SUPPORT_READINESS", "Count of handover residual items not closed", "COUNT(open residual items)", None, "COUNT", "LOWER_IS_BETTER", "CUSTOMER", "analytics.support_readiness.view", "/api/v1/projects/{project_id}/handover", "SUPPORT"),
    ("AT_RISK_PROJECT_COUNT", "At-risk projects", "EXECUTIVE", "Count of active projects with AT_RISK or CRITICAL health", "COUNT(at-risk active projects)", None, "COUNT", "LOWER_IS_BETTER", "ACCOUNT", "analytics.executive.view", "/api/v1/projects", "EXECUTIVE_MANAGEMENT"),
    ("CROSS_DEPARTMENT_RESPONSE_HOURS", "Cross-department response time", "EXECUTIVE", "First response time - request creation time", "SUM(first-response hours)", "COUNT(responded requests)", "HOURS", "LOWER_IS_BETTER", "ACCOUNT", "analytics.executive.view", "/api/v1/cross-department-requests", "EXECUTIVE_MANAGEMENT"),
]


def upgrade() -> None:
    op.create_table(
        "project_kpi_definitions",
        sa.Column("id", ID, primary_key=True),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("domain", sa.String(40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("formula", sa.Text(), nullable=False),
        sa.Column("numerator_definition", sa.Text()),
        sa.Column("denominator_definition", sa.Text()),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("target_direction", sa.String(20), nullable=False),
        sa.Column("zero_denominator_policy", sa.String(20), nullable=False, server_default="NULL"),
        sa.Column("time_basis", sa.String(30), nullable=False, server_default="EVENT_TIME"),
        sa.Column("allowed_scopes", sa.JSON(), nullable=False),
        sa.Column("eligibility_rules", sa.JSON(), nullable=False),
        sa.Column("exclusions", sa.JSON(), nullable=False),
        sa.Column("required_permission", sa.String(100), nullable=False),
        sa.Column("drilldown_resource", sa.String(200), nullable=False),
        sa.Column("owner_role", sa.String(80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_project_kpi_definitions_domain", "project_kpi_definitions", ["domain"])
    bind = op.get_bind()
    for code, description in PERMISSIONS.items():
        bind.execute(sa.text("INSERT INTO permissions (code,module,description,is_high_risk,is_active) SELECT :code,'analytics',:description,0,1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code=:code)"), {"code": code, "description": description})
    grants = {
        "ADMINISTRATOR": tuple(PERMISSIONS),
        "PROJECT_HANDOVER": ("analytics.dictionary.view", "analytics.project.view", "analytics.implementation.view", "analytics.support_readiness.view"),
        "SUPPORT_MANAGER": ("analytics.dictionary.view", "analytics.support_readiness.view"),
        "TOP_MANAGEMENT": ("analytics.dictionary.view", "analytics.project.view", "analytics.support_readiness.view", "analytics.executive.view"),
    }
    for profile, codes in grants.items():
        for code in codes:
            bind.execute(sa.text("INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,pm.id,'NONE' FROM profiles p CROSS JOIN permissions pm WHERE p.code=:profile AND pm.code=:code AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=pm.id)"), {"profile": profile, "code": code})
    now = datetime.now(UTC)
    table = sa.table(
        "project_kpi_definitions",
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("domain", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("formula", sa.Text()),
        sa.column("numerator_definition", sa.Text()),
        sa.column("denominator_definition", sa.Text()),
        sa.column("unit", sa.String()),
        sa.column("target_direction", sa.String()),
        sa.column("zero_denominator_policy", sa.String()),
        sa.column("time_basis", sa.String()),
        sa.column("allowed_scopes", sa.JSON()),
        sa.column("eligibility_rules", sa.JSON()),
        sa.column("exclusions", sa.JSON()),
        sa.column("required_permission", sa.String()),
        sa.column("drilldown_resource", sa.String()),
        sa.column("owner_role", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    rows = []
    for item in DEFINITIONS:
        code, name, domain, formula, numerator, denominator, unit, direction, scope, permission, drilldown, owner = item
        rows.append({"code": code, "name": name, "domain": domain, "description": name + " governed metric.", "formula": formula, "numerator_definition": numerator, "denominator_definition": denominator, "unit": unit, "target_direction": direction, "zero_denominator_policy": "NULL", "time_basis": "EVENT_TIME", "allowed_scopes": [scope], "eligibility_rules": ["Record is active or completed in the selected period", "Record is visible in the caller's effective customer and department scope"], "exclusions": ["Deleted or test records", "Records outside the selected reporting period"], "required_permission": permission, "drilldown_resource": drilldown, "owner_role": owner, "version": 1, "is_active": True, "created_at": now, "updated_at": now})
    op.bulk_insert(table, rows)


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code IN :codes)").bindparams(sa.bindparam("codes", expanding=True)), {"codes": tuple(PERMISSIONS)})
    bind.execute(sa.text("DELETE FROM permissions WHERE code IN :codes").bindparams(sa.bindparam("codes", expanding=True)), {"codes": tuple(PERMISSIONS)})
    op.drop_index("ix_project_kpi_definitions_domain", table_name="project_kpi_definitions")
    op.drop_table("project_kpi_definitions")
