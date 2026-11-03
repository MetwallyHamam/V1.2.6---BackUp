"""add ticket bulk action permissions"""

import sqlalchemy as sa

from alembic import op

revision = "0047_ticket_bulk_permissions"
down_revision = "0046_data_migration_permission"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for code, description in (("ticket.bulk.status", "Ticket Bulk Status"), ("ticket.bulk.delete", "Ticket Bulk Delete")):
        op.execute(sa.text(f"INSERT INTO permissions (code, module, description, is_high_risk, is_active) SELECT '{code}', 'ticket', '{description}', 1, 1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='{code}')"))
        op.execute(sa.text(f"INSERT INTO profile_permissions (profile_id, permission_id, scope_type) SELECT p.id, pm.id, 'NONE' FROM profiles p CROSS JOIN permissions pm WHERE p.code='ADMINISTRATOR' AND pm.code='{code}' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=pm.id)"))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code IN ('ticket.bulk.status','ticket.bulk.delete'))"))
    op.execute(sa.text("DELETE FROM permissions WHERE code IN ('ticket.bulk.status','ticket.bulk.delete')"))
