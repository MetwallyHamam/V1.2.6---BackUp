"""Granular shift authorization and editing lifecycle."""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists

revision = "0059_shift_authorization_editing"
down_revision = "0058_profile_dashboard_widgets"
branch_labels = None
depends_on = None

PERMISSIONS = (
    "shift.view.own", "shift.view.team", "shift.view.department", "shift.view.all",
    "shift.create", "shift.edit.own", "shift.edit.team", "shift.edit.all",
    "shift.edit.published", "shift.delete", "shift.publish", "shift.approve",
    "shift.assign_employee", "shift.export",
)


def upgrade() -> None:
    bind = op.get_bind()
    if not column_exists(bind, "shifts", "status"):
        op.add_column("shifts", sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"))
    if not column_exists(bind, "shifts", "updated_at"):
        op.add_column("shifts", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    for code in PERMISSIONS:
        op.execute(sa.text(f"INSERT INTO permissions (code,module,description,is_high_risk,is_active) SELECT '{code}','shift','{code.replace('.', ' ').title()}',0,1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='{code}')"))
    for profile, codes in {
        "HR": ("shift.view.all", "shift.create", "shift.edit.all", "shift.edit.published", "shift.publish", "shift.assign_employee", "shift.export"),
        "SUPPORT_MANAGER": ("shift.view.all", "shift.create", "shift.edit.all", "shift.edit.published", "shift.publish", "shift.assign_employee", "shift.export"),
        "L1_SUPPORT": ("shift.view.own",), "L2_SUPPORT": ("shift.view.own",), "L3_SUPPORT": ("shift.view.own",),
    }.items():
        for code in codes:
            op.execute(sa.text(f"INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,pm.id,'NONE' FROM profiles p CROSS JOIN permissions pm WHERE p.code='{profile}' AND pm.code='{code}' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=pm.id)"))
    for code in PERMISSIONS:
        op.execute(sa.text(f"INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,pm.id,'NONE' FROM profiles p CROSS JOIN permissions pm WHERE p.code='ADMINISTRATOR' AND pm.code='{code}' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=pm.id)"))


def downgrade() -> None:
    joined = "','".join(PERMISSIONS)
    op.execute(sa.text(f"DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code IN ('{joined}'))"))
    op.execute(sa.text(f"DELETE FROM permissions WHERE code IN ('{joined}')"))
    op.drop_column("shifts", "updated_at")
    op.drop_column("shifts", "status")
