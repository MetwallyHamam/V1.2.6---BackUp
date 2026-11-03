"""normalize dashboard access, tabs, catalog, and widget placement

Revision ID: 0170_dashboard_engine
Revises: 0169_dashboard_destinations
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0170_dashboard_engine"
down_revision: str | None = "0169_dashboard_destinations"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None
ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

def upgrade() -> None:
    op.create_table("dashboard_profile_access", sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("profile_id", ID, sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False), sa.Column("dashboard_id", ID, sa.ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False), sa.Column("can_view", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.UniqueConstraint("profile_id", "dashboard_id"))
    op.create_index("ix_dashboard_profile_access_profile", "dashboard_profile_access", ["profile_id", "is_active", "is_default"])
    op.create_index("ux_dashboard_profile_default", "dashboard_profile_access", ["profile_id"], unique=True, sqlite_where=sa.text("is_default = 1 AND is_active = 1"), mssql_where=sa.text("is_default = 1 AND is_active = 1"))
    op.create_table("dashboard_tabs", sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("dashboard_id", ID, sa.ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False), sa.Column("code", sa.String(80), nullable=False), sa.Column("name", sa.String(150), nullable=False), sa.Column("description", sa.String(500)), sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.UniqueConstraint("dashboard_id", "code"))
    op.create_index("ix_dashboard_tabs_order", "dashboard_tabs", ["dashboard_id", "display_order"])
    op.create_table("widget_definitions", sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("code", sa.String(80), nullable=False, unique=True), sa.Column("name", sa.String(150), nullable=False), sa.Column("description", sa.String(500)), sa.Column("component_key", sa.String(150), nullable=False), sa.Column("category", sa.String(80), nullable=False, server_default="Operations"), sa.Column("default_width", sa.Integer(), nullable=False, server_default="2"), sa.Column("default_height", sa.Integer(), nullable=False, server_default="1"), sa.Column("source_type", sa.String(30), nullable=False, server_default="REGISTERED"), sa.Column("widget_type", sa.String(30), nullable=False, server_default="KPI_CARD"), sa.Column("query_code", sa.String(80), nullable=False), sa.Column("required_permissions_json", sa.Text(), nullable=False, server_default="[]"), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()))
    op.create_table("dashboard_tab_widgets", sa.Column("id", ID, primary_key=True, autoincrement=True), sa.Column("dashboard_tab_id", ID, sa.ForeignKey("dashboard_tabs.id", ondelete="CASCADE"), nullable=False), sa.Column("widget_id", ID, sa.ForeignKey("widget_definitions.id", ondelete="CASCADE"), nullable=False), sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"), sa.Column("width", sa.Integer(), nullable=False, server_default="2"), sa.Column("height", sa.Integer(), nullable=False, server_default="1"), sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("configuration_json", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.UniqueConstraint("dashboard_tab_id", "widget_id"))
    op.create_index("ix_dashboard_tab_widgets_order", "dashboard_tab_widgets", ["dashboard_tab_id", "display_order"])
    op.execute("INSERT INTO permissions (code,module,description,is_high_risk,is_active) SELECT 'topmanagementdashboard.view','dashboard','View Top Management dashboard navigator',0,1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='topmanagementdashboard.view')")
    # Preserve permission behavior while introducing the dedicated navigator permission.
    op.execute("INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT pp.profile_id,np.id,'NONE' FROM profile_permissions pp JOIN permissions oldp ON oldp.id=pp.permission_id JOIN permissions np ON np.code='topmanagementdashboard.view' WHERE oldp.code='dashboard.executive' AND NOT EXISTS (SELECT 1 FROM profile_permissions x WHERE x.profile_id=pp.profile_id AND x.permission_id=np.id)")
    # Existing templates become real dashboards with configurable tabs.
    op.execute("INSERT INTO dashboard_tabs (dashboard_id,code,name,display_order,is_active) SELECT id,'OVERVIEW','Overview',0,1 FROM dashboards WHERE destination='EXECUTIVE'")
    for code, name, order in (("EXECUTIVE_OVERVIEW","Executive Overview",0),("CUSTOMER_SERVICE_SUCCESS","Customer Service",1),("FINANCIAL_ANALYSIS","Financial",2)):
        op.execute(sa.text("INSERT INTO dashboard_tabs (dashboard_id,code,name,display_order,is_active) SELECT id,:code,:name,:ord,1 FROM dashboards WHERE destination='TOP_MANAGEMENT'").bindparams(code=code,name=name,ord=order))
    # Migrate every registered/hardcoded placement into a central reusable definition.
    op.execute("INSERT INTO widget_definitions (code,name,description,component_key,category,default_width,default_height,source_type,widget_type,query_code,required_permissions_json,is_active,created_at,updated_at) SELECT widget_code,MAX(title),NULL,widget_code,'Operations',MAX(width),1,'MIGRATED',MAX(widget_type),MAX(query_code),'[]',1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP FROM dashboard_widgets GROUP BY widget_code")
    op.execute("INSERT INTO dashboard_tab_widgets (dashboard_tab_id,widget_id,display_order,width,height,is_visible,configuration_json,created_at,updated_at) SELECT t.id,d.id,w.position,w.width,1,w.is_active,w.config_json,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP FROM dashboard_widgets w JOIN dashboard_tabs t ON t.dashboard_id=w.dashboard_id AND t.display_order=0 JOIN widget_definitions d ON d.code=w.widget_code")
    # Convert the winning legacy profile assignment into explicit access; no system dashboard is inherited.
    op.execute("INSERT INTO dashboard_profile_access (profile_id,dashboard_id,can_view,is_default,is_active,created_at,updated_at) SELECT a.profile_id,a.dashboard_id,1,1,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP FROM dashboard_assignments a WHERE a.profile_id IS NOT NULL AND a.user_id IS NULL AND a.department_id IS NULL AND a.is_active=1 AND NOT EXISTS (SELECT 1 FROM dashboard_assignments newer WHERE newer.profile_id=a.profile_id AND newer.user_id IS NULL AND newer.department_id IS NULL AND newer.is_active=1 AND (newer.priority>a.priority OR (newer.priority=a.priority AND newer.id>a.id)))")
    op.execute("INSERT INTO dashboard_profile_access (profile_id,dashboard_id,can_view,is_default,is_active,created_at,updated_at) SELECT p.id,(SELECT MIN(d.id) FROM dashboards d WHERE d.is_active=1 AND d.destination=CASE WHEN p.default_dashboard_code='top-management' THEN 'TOP_MANAGEMENT' ELSE 'EXECUTIVE' END),1,1,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP FROM profiles p WHERE p.is_active=1 AND p.profile_type<>'CLIENT_PORTAL' AND NOT EXISTS (SELECT 1 FROM dashboard_profile_access x WHERE x.profile_id=p.id) AND EXISTS (SELECT 1 FROM dashboards d WHERE d.is_active=1 AND d.destination=CASE WHEN p.default_dashboard_code='top-management' THEN 'TOP_MANAGEMENT' ELSE 'EXECUTIVE' END)")

def downgrade() -> None:
    op.drop_index("ix_dashboard_tab_widgets_order", table_name="dashboard_tab_widgets"); op.drop_table("dashboard_tab_widgets")
    op.drop_table("widget_definitions"); op.drop_index("ix_dashboard_tabs_order", table_name="dashboard_tabs"); op.drop_table("dashboard_tabs")
    op.drop_index("ux_dashboard_profile_default", table_name="dashboard_profile_access"); op.drop_index("ix_dashboard_profile_access_profile", table_name="dashboard_profile_access"); op.drop_table("dashboard_profile_access")
