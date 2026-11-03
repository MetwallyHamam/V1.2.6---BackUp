"""allow governed editing of pending project handovers

Revision ID: 0159_pending_handover_editing
Revises: 0158_shared_caller_links
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0159_pending_handover_editing"
down_revision: str | None = "0158_shared_caller_links"
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
    op.bulk_insert(permissions, [{
        "code": "project_handover.edit_pending",
        "module": "PROJECT_HANDOVER",
        "description": "Edit saved project handovers while draft, ready, or on hold",
        "is_high_risk": False,
        "is_active": True,
    }])
    op.execute(
        "INSERT INTO profile_permissions (profile_id, permission_id, scope_type) "
        "SELECT p.id, q.id, 'NONE' FROM profiles p CROSS JOIN permissions q "
        "WHERE p.code IN ('PROJECT_HANDOVER','ADMINISTRATOR') AND q.code = 'project_handover.edit_pending' "
        "AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id = p.id AND pp.permission_id = q.id)"
    )


def downgrade() -> None:
    op.execute("DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code = 'project_handover.edit_pending')")
    op.execute("DELETE FROM permissions WHERE code = 'project_handover.edit_pending'")
