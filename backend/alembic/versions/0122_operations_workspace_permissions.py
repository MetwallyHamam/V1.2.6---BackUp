"""Add granular permissions for the unified operations workspace.

Revision ID: 0122_operations_permissions
Revises: 0121_employee_onboarding
"""

import sqlalchemy as sa

from alembic import op

revision = "0122_operations_permissions"
down_revision = "0121_employee_onboarding"
branch_labels = None
depends_on = None


VIEW_PERMISSIONS = (
    ("internal_operation.workspace.view", "Open the unified Operations Workspace"),
    ("internal_operation.calendar.view", "View internal operations on the unified calendar"),
    ("internal_operation.transition", "Progress assigned internal operations through their lifecycle"),
    ("internal_operation.comment", "Add comments to accessible internal operations"),
    ("internal_operation.document.upload", "Upload evidence to accessible internal operations"),
    ("internal_operation.document.download", "Download evidence from accessible internal operations"),
)

MANAGE_PERMISSIONS = (
    ("internal_operation.create", "Create internal operations"),
    ("internal_operation.schedule", "Schedule and reschedule internal operations"),
    ("internal_operation.assign", "Assign engineers to internal operations"),
    ("internal_operation.template.manage", "Manage and apply internal operation templates"),
    ("internal_operation.type.manage", "Manage governed internal operation types"),
    ("internal_operation.override_conflict", "Override internal operation scheduling conflicts"),
)


def _add_and_inherit(code: str, description: str, inherited_from: str, high_risk: bool = False) -> None:
    bind = op.get_bind()
    bind.execute(sa.text(
        "INSERT INTO permissions (code,module,description,is_high_risk,is_active) "
        "SELECT :code,'internal_operations',:description,:high_risk,1 "
        "WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code=:code)"
    ), {"code": code, "description": description, "high_risk": high_risk})
    bind.execute(sa.text(
        "INSERT INTO profile_permissions (profile_id,permission_id,scope_type) "
        "SELECT DISTINCT existing.profile_id,new_permission.id,existing.scope_type "
        "FROM profile_permissions existing "
        "JOIN permissions old_permission ON old_permission.id=existing.permission_id "
        "CROSS JOIN permissions new_permission "
        "WHERE old_permission.code=:inherited_from AND new_permission.code=:code "
        "AND NOT EXISTS (SELECT 1 FROM profile_permissions assigned_permission "
        "WHERE assigned_permission.profile_id=existing.profile_id "
        "AND assigned_permission.permission_id=new_permission.id)"
    ), {"code": code, "inherited_from": inherited_from})


def upgrade() -> None:
    for code, description in VIEW_PERMISSIONS:
        _add_and_inherit(code, description, "internal_operation.view")
    for code, description in MANAGE_PERMISSIONS:
        _add_and_inherit(code, description, "internal_operation.manage", high_risk=code == "internal_operation.override_conflict")


def downgrade() -> None:
    codes = [code for code, _ in VIEW_PERMISSIONS + MANAGE_PERMISSIONS]
    placeholders = ",".join(f"'{code}'" for code in codes)
    op.execute(sa.text(f"DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code IN ({placeholders}))"))
    op.execute(sa.text(f"DELETE FROM permissions WHERE code IN ({placeholders})"))
