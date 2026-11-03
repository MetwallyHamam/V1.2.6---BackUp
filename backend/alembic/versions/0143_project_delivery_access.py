"""project delivery scoped access

Revision ID: 0143_project_delivery
Revises: 0142_portal_training
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0143_project_delivery"
down_revision: str | None = "0142_portal_training"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

PERMISSIONS = (
    "project_handover.client.lookup",
    "project_handover.client.create",
    "project_handover.contact.create",
    "project_handover.client_access.create",
    "project_handover.engineer.lookup",
    "project_handover.contract_template.apply",
)


def upgrade() -> None:
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.BigInteger),
        sa.column("code", sa.String),
        sa.column("module", sa.String),
        sa.column("description", sa.String),
        sa.column("is_high_risk", sa.Boolean),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(permissions, [
        {"code": code, "module": "PROJECT_HANDOVER", "description": code.replace("project_handover.", "").replace(".", " ").title(), "is_high_risk": False, "is_active": True}
        for code in PERMISSIONS
    ])
    codes = ",".join(f"'{code}'" for code in PERMISSIONS)
    op.execute(
        "INSERT INTO profile_permissions (profile_id, permission_id, scope_type) "
        "SELECT p.id, x.id, 'NONE' FROM profiles p CROSS JOIN permissions x "
        f"WHERE p.code = 'PROJECT_HANDOVER' AND x.code IN ({codes}) "
        "AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id = p.id AND pp.permission_id = x.id)"
    )
    op.execute("DELETE FROM profile_permissions WHERE profile_id IN (SELECT id FROM profiles WHERE code = 'PROJECT_HANDOVER') AND permission_id IN (SELECT id FROM permissions WHERE code IN ('client.view','internal_operation.view'))")


def downgrade() -> None:
    codes = ",".join(f"'{code}'" for code in PERMISSIONS)
    op.execute(f"DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code IN ({codes}))")
    op.execute(f"DELETE FROM permissions WHERE code IN ({codes})")
    op.execute("INSERT INTO profile_permissions (profile_id, permission_id, scope_type) SELECT p.id, x.id, 'NONE' FROM profiles p CROSS JOIN permissions x WHERE p.code = 'PROJECT_HANDOVER' AND x.code IN ('client.view','internal_operation.view') AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id = p.id AND pp.permission_id = x.id)")
