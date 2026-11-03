"""Add a dedicated Client Profile view permission.

Revision ID: 0119_client_profile_permission
Revises: 0118_top_mgmt_finance
"""

import sqlalchemy as sa

from alembic import op

revision = "0119_client_profile_permission"
down_revision = "0118_top_mgmt_finance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO permissions (code,module,description,is_high_risk,is_active) "
            "SELECT :code,'clients',:description,0,1 WHERE NOT EXISTS "
            "(SELECT 1 FROM permissions WHERE code=:code)"
        ),
        {
            "code": "client.profile.view",
            "description": "Open the interactive Client Profile and its governed insights.",
        },
    )
    bind.execute(
        sa.text(
            "INSERT INTO profile_permissions (profile_id,permission_id,scope_type) "
            "SELECT profile.id,permission.id,'NONE' FROM profiles profile "
            "CROSS JOIN permissions permission "
            "WHERE profile.code IN ('L2_SUPPORT','L3_SUPPORT','SUPPORT_MANAGER','TOP_MANAGEMENT','ADMINISTRATOR') "
            "AND permission.code='client.profile.view' "
            "AND NOT EXISTS (SELECT 1 FROM profile_permissions existing "
            "WHERE existing.profile_id=profile.id AND existing.permission_id=permission.id)"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM profile_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code='client.profile.view')"
        )
    )
    op.execute(sa.text("DELETE FROM permissions WHERE code='client.profile.view'"))
