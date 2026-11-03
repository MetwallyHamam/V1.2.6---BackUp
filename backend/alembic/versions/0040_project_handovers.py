"""add implementation project handovers

Revision ID: 0040_project_handovers
Revises: 0039_user_preferences
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import create_frozen_tables
from app.modules.project_handovers import models  # noqa: F401

revision = "0040_project_handovers"
down_revision = "0039_user_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_frozen_tables(op.get_bind(), ("project_handovers", "project_handover_recipients", "project_handover_products", "project_handover_comments"))
    permissions = sa.table("permissions", sa.column("code", sa.String), sa.column("module", sa.String), sa.column("description", sa.String), sa.column("is_high_risk", sa.Boolean), sa.column("is_active", sa.Boolean))
    op.bulk_insert(permissions, [
        {"code":"project_handover.view","module":"project_handovers","description":"View assigned project handovers","is_high_risk":False,"is_active":True},
        {"code":"project_handover.manage","module":"project_handovers","description":"Create and manage implementation project handovers","is_high_risk":False,"is_active":True},
    ])
    op.execute(sa.text("INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,x.id,'NONE' FROM profiles p CROSS JOIN permissions x WHERE x.code='project_handover.view' AND p.profile_type IN ('EMPLOYEE','ADMINISTRATOR')"))
    op.execute(sa.text("INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,x.id,'NONE' FROM profiles p CROSS JOIN permissions x WHERE x.code='project_handover.manage' AND (p.code IN ('SUPPORT_MANAGER','ADMINISTRATOR') OR p.profile_type='ADMINISTRATOR')"))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code LIKE 'project_handover.%')"))
    op.execute(sa.text("DELETE FROM permissions WHERE code LIKE 'project_handover.%'"))
    for table in ("project_handover_comments","project_handover_products","project_handover_recipients","project_handovers"):
        op.drop_table(table)
