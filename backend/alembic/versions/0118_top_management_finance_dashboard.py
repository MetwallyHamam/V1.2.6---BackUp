"""Grant top management read-only financial dashboard access.

Revision ID: 0118_top_mgmt_finance
Revises: 0117_contract_template_types
"""

import sqlalchemy as sa

from alembic import op

revision = "0118_top_mgmt_finance"
down_revision = "0117_contract_template_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text(
        "INSERT INTO profile_permissions (profile_id,permission_id,scope_type) "
        "SELECT profile.id,permission.id,'NONE' FROM profiles profile CROSS JOIN permissions permission "
        "WHERE profile.code='TOP_MANAGEMENT' AND permission.code='finance.dashboard.view' "
        "AND NOT EXISTS (SELECT 1 FROM profile_permissions existing WHERE existing.profile_id=profile.id AND existing.permission_id=permission.id)"
    ))


def downgrade() -> None:
    op.execute(sa.text(
        "DELETE FROM profile_permissions WHERE profile_id IN (SELECT id FROM profiles WHERE code='TOP_MANAGEMENT') "
        "AND permission_id IN (SELECT id FROM permissions WHERE code='finance.dashboard.view')"
    ))
