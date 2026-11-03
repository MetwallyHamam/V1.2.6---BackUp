"""Database-backed dashboards with assignment priority."""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import table_exists

revision = "0063_dynamic_dashboards"
down_revision = "0062_ticket_edit_permissions"
branch_labels = None
depends_on = None

PERMISSIONS = ("dashboard.customize.own", "dashboard.customize.profile", "dashboard.customize.user", "dashboard.manage_widgets")


def upgrade() -> None:
    bind = op.get_bind()
    if not table_exists(bind, "dashboards"):
        op.create_table("dashboards", sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True), sa.Column("name", sa.String(150), nullable=False), sa.Column("assignment_type", sa.String(20), nullable=False), sa.Column("assignment_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("assignment_type", "assignment_id"))
    if not table_exists(bind, "dashboard_widgets"):
        op.create_table("dashboard_widgets", sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True), sa.Column("dashboard_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False), sa.Column("widget_code", sa.String(80), nullable=False), sa.Column("title", sa.String(150), nullable=False), sa.Column("widget_type", sa.String(30), nullable=False), sa.Column("query_code", sa.String(80), nullable=False), sa.Column("position", sa.Integer(), nullable=False), sa.Column("width", sa.Integer(), nullable=False), sa.Column("refresh_seconds", sa.Integer(), nullable=False), sa.Column("config_json", sa.Text(), nullable=True), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.UniqueConstraint("dashboard_id", "widget_code"))
    for code in PERMISSIONS:
        op.execute(sa.text(f"INSERT INTO permissions (code,module,description,is_high_risk,is_active) SELECT '{code}','dashboard','{code.replace('.', ' ').title()}',0,1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='{code}')"))
    for profile, codes in {"ADMINISTRATOR": PERMISSIONS, "SUPPORT_MANAGER": ("dashboard.customize.profile", "dashboard.customize.user", "dashboard.manage_widgets")}.items():
        for code in codes:
            op.execute(sa.text(f"INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,pm.id,'NONE' FROM profiles p CROSS JOIN permissions pm WHERE p.code='{profile}' AND pm.code='{code}' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=pm.id)"))


def downgrade() -> None:
    joined = "','".join(PERMISSIONS)
    op.execute(sa.text(f"DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code IN ('{joined}'))"))
    op.execute(sa.text(f"DELETE FROM permissions WHERE code IN ('{joined}')"))
    op.drop_table("dashboard_widgets")
    op.drop_table("dashboards")
