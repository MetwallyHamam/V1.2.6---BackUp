"""Add manual satisfaction delivery permission and recoverable tokens.

Revision ID: 0134_satisfaction_delivery
Revises: 0133_live_update_permission
"""

import sqlalchemy as sa

from alembic import op

revision = "0134_satisfaction_delivery"
down_revision = "0133_live_update_permission"
branch_labels = None
depends_on = None

PERMISSION_CODE = "ticket.satisfaction.send"


def upgrade() -> None:
    op.add_column("ticket_satisfaction", sa.Column("token_ciphertext", sa.Text(), nullable=True))
    bind = op.get_bind()
    bind.execute(sa.text("INSERT INTO permissions (code,module,description,is_high_risk,is_active) SELECT :code,'ticket',:description,0,1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code=:code)"), {"code": PERMISSION_CODE, "description": "Send ticket satisfaction links by WhatsApp or email"})
    bind.execute(sa.text("INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT existing.profile_id,target.id,'NONE' FROM profile_permissions existing JOIN permissions source ON source.id=existing.permission_id CROSS JOIN permissions target WHERE source.code='ticket.comment.public' AND target.code=:code AND NOT EXISTS (SELECT 1 FROM profile_permissions assigned WHERE assigned.profile_id=existing.profile_id AND assigned.permission_id=target.id)"), {"code": PERMISSION_CODE})


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code=:code)"), {"code": PERMISSION_CODE})
    bind.execute(sa.text("DELETE FROM permissions WHERE code=:code"), {"code": PERMISSION_CODE})
    op.drop_column("ticket_satisfaction", "token_ciphertext")
