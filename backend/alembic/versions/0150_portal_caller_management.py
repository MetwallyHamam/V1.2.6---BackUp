"""allow governed caller management in the client portal

Revision ID: 0150_portal_caller_management
Revises: 0149_client_unicode_text
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0150_portal_caller_management"
down_revision: str | None = "0149_client_unicode_text"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    permissions = sa.table(
        "permissions",
        sa.column("code", sa.String()),
        sa.column("module", sa.String()),
        sa.column("description", sa.String()),
        sa.column("is_high_risk", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        permissions,
        [{
            "code": "portal.caller.manage",
            "module": "CLIENT_PORTAL",
            "description": "View, select, and add callers for authorized portal clients",
            "is_high_risk": False,
            "is_active": True,
        }],
    )
    op.execute(
        "INSERT INTO profile_permissions (profile_id, permission_id, scope_type) "
        "SELECT p.id, x.id, 'NONE' FROM profiles p CROSS JOIN permissions x "
        "WHERE p.profile_type = 'CLIENT_PORTAL' AND p.is_active = 1 "
        "AND x.code = 'portal.caller.manage' AND NOT EXISTS ("
        "SELECT 1 FROM profile_permissions pp WHERE pp.profile_id = p.id "
        "AND pp.permission_id = x.id)"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM profile_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE code = 'portal.caller.manage')"
    )
    op.execute("DELETE FROM permissions WHERE code = 'portal.caller.manage'")
