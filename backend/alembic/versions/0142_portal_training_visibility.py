"""portal training material visibility

Revision ID: 0142_portal_training
Revises: 0141_access_requests
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0142_portal_training"
down_revision: str | None = "0141_access_requests"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

def upgrade() -> None:
    op.add_column("onboarding_materials", sa.Column("show_in_client_portal", sa.Boolean(), nullable=False, server_default=sa.false()))
    permissions=sa.table("permissions",sa.column("id",sa.BigInteger),sa.column("code",sa.String),sa.column("module",sa.String),sa.column("description",sa.String),sa.column("is_high_risk",sa.Boolean),sa.column("is_active",sa.Boolean))
    op.bulk_insert(permissions,[{"code":"portal.training.view","module":"CLIENT_PORTAL","description":"View published training materials in the client portal","is_high_risk":False,"is_active":True}])
    op.execute("INSERT INTO profile_permissions (profile_id, permission_id, scope_type) SELECT p.id, x.id, 'NONE' FROM profiles p CROSS JOIN permissions x WHERE p.profile_type = 'CLIENT_PORTAL' AND p.is_active = 1 AND x.code = 'portal.training.view' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id = p.id AND pp.permission_id = x.id)")

def downgrade() -> None:
    op.execute("DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code = 'portal.training.view')")
    op.execute("DELETE FROM permissions WHERE code = 'portal.training.view'")
    op.drop_column("onboarding_materials", "show_in_client_portal")
