"""clean legacy project handover workspace permissions

Revision ID: 0144_handover_cleanup
Revises: 0143_project_delivery
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0144_handover_cleanup"
down_revision: str | None = "0143_project_delivery"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Some installations renamed or recreated the system profile, so its code
    # is not necessarily PROJECT_HANDOVER. Match the canonical name as well.
    op.execute(
        "INSERT INTO profile_permissions (profile_id, permission_id, scope_type) "
        "SELECT p.id, permission.id, 'NONE' FROM profiles p CROSS JOIN permissions permission "
        "WHERE (UPPER(REPLACE(p.name, ' ', '_')) = 'PROJECT_HANDOVER' OR UPPER(p.code) = 'PROJECT_HANDOVER') "
        "AND permission.code IN ("
        "'project_handover.view','project_handover.manage','project_handover.client.lookup',"
        "'project_handover.client.create','project_handover.contact.create',"
        "'project_handover.client_access.create','project_handover.engineer.lookup',"
        "'project_handover.contract_template.apply'"
        ") AND NOT EXISTS (SELECT 1 FROM profile_permissions existing WHERE "
        "existing.profile_id = p.id AND existing.permission_id = permission.id)"
    )
    op.execute(
        "DELETE FROM profile_permissions "
        "WHERE profile_id IN ("
        "SELECT id FROM profiles WHERE UPPER(REPLACE(name, ' ', '_')) = 'PROJECT_HANDOVER' "
        "OR UPPER(code) = 'PROJECT_HANDOVER'"
        ") AND permission_id IN ("
        "SELECT id FROM permissions WHERE code IN ("
        "'client.view','client.manage','contact.manage','contract.view','contract.manage',"
        "'contract.template.view','contract.template.manage','internal_operation.view',"
        "'internal_operation.manage','internal_operation.workspace.view'"
        "))"
    )
    op.execute(
        "DELETE FROM user_permission_overrides WHERE effect = 'ALLOW' "
        "AND user_id IN (SELECT assignment.user_id FROM user_profiles assignment "
        "JOIN profiles profile ON profile.id = assignment.profile_id "
        "WHERE UPPER(REPLACE(profile.name, ' ', '_')) = 'PROJECT_HANDOVER' "
        "OR UPPER(profile.code) = 'PROJECT_HANDOVER') "
        "AND permission_id IN (SELECT id FROM permissions WHERE code IN ("
        "'client.view','client.manage','contact.manage','contract.view','contract.manage',"
        "'contract.template.view','contract.template.manage','internal_operation.view',"
        "'internal_operation.manage','internal_operation.workspace.view'"
        "))"
    )


def downgrade() -> None:
    # Do not restore broad workspace access automatically. Administrators can
    # grant it independently when it is genuinely required.
    pass
