"""add controlled data migration permission"""

import sqlalchemy as sa

from alembic import op

revision = "0046_data_migration_permission"
down_revision = "0045_flag_portal_tickets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("INSERT INTO permissions (code, module, description, is_high_risk, is_active) SELECT 'data_migration.manage', 'data_migration', 'Data Migration Manage', 1, 1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='data_migration.manage')"))
    op.execute(sa.text("INSERT INTO profile_permissions (profile_id, permission_id, scope_type) SELECT p.id, pm.id, 'NONE' FROM profiles p CROSS JOIN permissions pm WHERE p.code='ADMINISTRATOR' AND pm.code='data_migration.manage' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=pm.id)"))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code='data_migration.manage')"))
    op.execute(sa.text("DELETE FROM permissions WHERE code='data_migration.manage'"))
