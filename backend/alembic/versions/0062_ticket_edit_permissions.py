"""Granular ticket editing permissions."""

import sqlalchemy as sa

from alembic import op

revision = "0062_ticket_edit_permissions"
down_revision = "0061_ticket_progress_started"
branch_labels = None
depends_on = None

PERMISSIONS = ("ticket.edit.own", "ticket.edit.assigned", "ticket.edit.team", "ticket.edit.all", "ticket.edit.subject", "ticket.edit.description", "ticket.edit.classification")
PROFILE_PERMISSIONS = {
    "CALL_CENTER": ("ticket.edit.own", "ticket.edit.subject", "ticket.edit.description"),
    "L1_SUPPORT": ("ticket.edit.assigned", "ticket.edit.subject", "ticket.edit.description", "ticket.edit.classification"),
    "L2_SUPPORT": ("ticket.edit.assigned", "ticket.edit.subject", "ticket.edit.description", "ticket.edit.classification"),
    "L3_SUPPORT": ("ticket.edit.assigned", "ticket.edit.team", "ticket.edit.subject", "ticket.edit.description", "ticket.edit.classification"),
    "SUPPORT_MANAGER": ("ticket.edit.all", "ticket.edit.subject", "ticket.edit.description", "ticket.edit.classification"),
}


def upgrade() -> None:
    for code in PERMISSIONS:
        op.execute(sa.text(f"INSERT INTO permissions (code,module,description,is_high_risk,is_active) SELECT '{code}','ticket','{code.replace('.', ' ').title()}',0,1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='{code}')"))
    for profile, codes in {**PROFILE_PERMISSIONS, "ADMINISTRATOR": PERMISSIONS}.items():
        for code in codes:
            op.execute(sa.text(f"INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,pm.id,'NONE' FROM profiles p CROSS JOIN permissions pm WHERE p.code='{profile}' AND pm.code='{code}' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=pm.id)"))


def downgrade() -> None:
    joined = "','".join(PERMISSIONS)
    op.execute(sa.text(f"DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code IN ('{joined}'))"))
    op.execute(sa.text(f"DELETE FROM permissions WHERE code IN ('{joined}')"))
