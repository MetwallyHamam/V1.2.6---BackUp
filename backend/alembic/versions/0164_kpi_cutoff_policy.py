"""add configurable KPI cutoff policy

Revision ID: 0164_kpi_cutoff_policy
Revises: 0163_kpi_submission_workflow
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0164_kpi_cutoff_policy"
down_revision: str | None = "0163_kpi_submission_workflow"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    for key, value in (
        ("kpi_cutoff_enabled", "true"),
        ("kpi_cutoff_mode", "QUARTER_LAST_WEEK"),
        ("kpi_cutoff_timezone", "Africa/Cairo"),
    ):
        op.execute(
            "INSERT INTO site_settings ([key],[value],updated_at) "
            f"SELECT '{key}','{value}',CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM site_settings WHERE [key]='{key}')"
        )
    permissions = {
        "kpi.cutoff.manage": "Configure the KPI cutoff schedule",
        "kpi.cutoff.override": "Generate KPIs outside the active cutoff window with a documented reason",
    }
    for code, description in permissions.items():
        op.execute(
            "INSERT INTO permissions (code,module,description,is_high_risk,is_active) "
            f"SELECT '{code}','KPI','{description}',1,1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='{code}')"
        )
    for profile_code, code in (
        ("HR", "kpi.cutoff.manage"),
        ("SUPPORT_MANAGER", "kpi.cutoff.override"),
        ("ADMINISTRATOR", "kpi.cutoff.manage"),
        ("ADMINISTRATOR", "kpi.cutoff.override"),
    ):
        op.execute(
            "INSERT INTO profile_permissions (profile_id,permission_id,scope_type) "
            "SELECT p.id,q.id,'NONE' FROM profiles p CROSS JOIN permissions q "
            f"WHERE p.code='{profile_code}' AND q.code='{code}' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=q.id)"
        )


def downgrade() -> None:
    # Preserve policy and grants because administrators may have changed them.
    pass
