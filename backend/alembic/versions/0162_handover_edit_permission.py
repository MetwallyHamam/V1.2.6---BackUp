"""repair pending handover edit permission assignments

Revision ID: 0162_handover_edit_permission
Revises: 0161_multi_handover_templates
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0162_handover_edit_permission"
down_revision: str | None = "0161_multi_handover_templates"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO permissions (code,module,description,is_high_risk,is_active) "
        "SELECT 'project_handover.edit_pending','PROJECT_HANDOVER',"
        "'Edit saved project handovers while draft, ready, or on hold',0,1 "
        "WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='project_handover.edit_pending')"
    )
    op.execute(
        "INSERT INTO profile_permissions (profile_id,permission_id,scope_type) "
        "SELECT profile.id,permission.id,'NONE' FROM profiles profile CROSS JOIN permissions permission "
        "WHERE (UPPER(REPLACE(profile.name,' ','_'))='PROJECT_HANDOVER' "
        "OR UPPER(profile.code) IN ('PROJECT_HANDOVER','ADMINISTRATOR')) "
        "AND permission.code='project_handover.edit_pending' "
        "AND NOT EXISTS (SELECT 1 FROM profile_permissions existing "
        "WHERE existing.profile_id=profile.id AND existing.permission_id=permission.id)"
    )


def downgrade() -> None:
    # Preserve grants because an administrator may have assigned them intentionally.
    pass
