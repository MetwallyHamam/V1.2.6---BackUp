"""Add governed contract notification-rule permission.

Revision ID: 0238_contract_notify_perm
Revises: 0237_escalation_work_queue
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0238_contract_notify_perm"
down_revision: str | None = "0237_escalation_work_queue"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSION = "contract.notification_rules.manage"


def upgrade() -> None:
    bind = op.get_bind()
    existing = bind.execute(sa.text("SELECT id FROM permissions WHERE code=:code"), {"code": PERMISSION}).scalar()
    if existing is None:
        bind.execute(sa.text("INSERT INTO permissions (code,module,description,is_high_risk,is_active) VALUES (:code,'contract','Configure contract expiration notification rules',1,1)"), {"code": PERMISSION})
    bind.execute(sa.text("""
        INSERT INTO profile_permissions (profile_id,permission_id,scope_type)
        SELECT p.id, q.id, 'NONE'
        FROM profiles p CROSS JOIN permissions q
        WHERE p.code='ADMINISTRATOR' AND q.code=:code
          AND NOT EXISTS (
              SELECT 1 FROM profile_permissions pp
              WHERE pp.profile_id=p.id AND pp.permission_id=q.id
          )
    """), {"code": PERMISSION})


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code=:code)"), {"code": PERMISSION})
    bind.execute(sa.text("DELETE FROM permissions WHERE code=:code"), {"code": PERMISSION})
