"""assign client access permissions to all internal groups"""

import sqlalchemy as sa

from alembic import op

revision = "0043_client_access_all_internal"
down_revision = "0042_client_access_vault"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO profile_permissions (profile_id, permission_id, scope_type)
            SELECT p.id, permission.id, 'NONE'
            FROM profiles p
            CROSS JOIN permissions permission
            WHERE p.profile_type IN ('EMPLOYEE', 'ADMINISTRATOR')
              AND permission.code IN (
                  'client_access.view',
                  'client_access.manage',
                  'client_access.reveal'
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM profile_permissions existing
                  WHERE existing.profile_id = p.id
                    AND existing.permission_id = permission.id
              )
            """
        )
    )


def downgrade() -> None:
    # Preserve the original restricted assignments from migration 0042.
    op.execute(
        sa.text(
            """
            DELETE FROM profile_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions
                WHERE code IN ('client_access.manage', 'client_access.reveal')
            )
              AND profile_id IN (
                SELECT id FROM profiles WHERE code IN ('CALL_CENTER', 'L1_SUPPORT')
              )
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM profile_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE code = 'client_access.manage'
            )
              AND profile_id IN (
                SELECT id FROM profiles WHERE code IN ('L2_SUPPORT', 'L3_SUPPORT')
              )
            """
        )
    )
