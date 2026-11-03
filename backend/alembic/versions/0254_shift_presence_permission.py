"""Add independent permission for shift presence visibility.

Revision ID: 0254_shift_presence_permission
Revises: 0253_change_deployment_closure
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0254_shift_presence_permission"
down_revision: str | None = "0253_change_deployment_closure"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSION = "shift.presence.view"


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO permissions (code,module,description,is_high_risk,is_active) "
            "SELECT :code,'shift','View engineer presence on shift cards',0,1 "
            "WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code=:code)"
        ).bindparams(code=PERMISSION)
    )
    for profile_code in ("SUPPORT_MANAGER", "ADMINISTRATOR"):
        op.execute(
            sa.text(
                "INSERT INTO profile_permissions (profile_id,permission_id,scope_type) "
                "SELECT p.id,pm.id,'NONE' FROM profiles p CROSS JOIN permissions pm "
                "WHERE p.code=:profile_code AND pm.code=:permission_code "
                "AND NOT EXISTS (SELECT 1 FROM profile_permissions pp "
                "WHERE pp.profile_id=p.id AND pp.permission_id=pm.id)"
            ).bindparams(profile_code=profile_code, permission_code=PERMISSION)
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM profile_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code=:code)"
        ).bindparams(code=PERMISSION)
    )
    op.execute(sa.text("DELETE FROM permissions WHERE code=:code").bindparams(code=PERMISSION))
