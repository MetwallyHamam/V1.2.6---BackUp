"""Add Customer Success analytics permissions.

Revision ID: 0138_customer_success
Revises: 0137_closed_ticket_polling
"""

import sqlalchemy as sa

from alembic import op

revision = "0138_customer_success"
down_revision = "0137_closed_ticket_polling"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for code, description in (("customer_success.view", "View governed Customer Success analytics"), ("customer_success.export", "Export governed Customer Success results")):
        bind.execute(sa.text("INSERT INTO permissions (code,module,description,is_high_risk,is_active) SELECT :code,'customer_success',:description,0,1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code=:code)"), {"code":code,"description":description})
    bind.execute(sa.text("INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,q.id,'NONE' FROM profiles p CROSS JOIN permissions q WHERE p.code IN ('ADMINISTRATOR','SUPPORT_MANAGER') AND q.code LIKE 'customer_success.%' AND NOT EXISTS (SELECT 1 FROM profile_permissions x WHERE x.profile_id=p.id AND x.permission_id=q.id)"))


def downgrade() -> None:
    op.execute("DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code LIKE 'customer_success.%')")
    op.execute("DELETE FROM permissions WHERE code LIKE 'customer_success.%'")
