"""add least-privilege financial management profile and dashboard

Revision ID: 0152_financial_profile
Revises: 0151_dashboard_assignments
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0152_financial_profile"
down_revision: str | None = "0151_dashboard_assignments"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

PERMISSIONS = (
    "finance.view", "finance.dashboard.view", "client.view", "client.profile.view",
    "contract.view", "dashboard.agent", "report.view", "report.export",
)


def upgrade() -> None:
    op.execute(sa.text("""
        INSERT INTO profiles
            (code,name,description,profile_type,is_system,is_active,risk_level,
             default_dashboard_code,dashboard_widgets_json,created_at,updated_at)
        SELECT 'FINANCIAL_MANAGEMENT','Financial Management',
               'Least-privilege financial analytics and reporting profile',
               'EMPLOYEE',1,1,'STANDARD','dashboard',NULL,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP
        WHERE NOT EXISTS (SELECT 1 FROM profiles WHERE code='FINANCIAL_MANAGEMENT')
    """))
    for code in PERMISSIONS:
        op.execute(sa.text(f"""
            INSERT INTO profile_permissions (profile_id,permission_id,scope_type)
            SELECT p.id,pm.id,'NONE' FROM profiles p CROSS JOIN permissions pm
            WHERE p.code='FINANCIAL_MANAGEMENT' AND pm.code='{code}'
              AND NOT EXISTS (
                SELECT 1 FROM profile_permissions pp
                WHERE pp.profile_id=p.id AND pp.permission_id=pm.id
              )
        """))
    op.execute(sa.text("""
        INSERT INTO dashboards
            (name,code,description,version,assignment_type,assignment_id,is_active,created_at,updated_at)
        SELECT 'Financial Management','FINANCIAL_MANAGEMENT_DEFAULT',
               'Governed financial analytics dashboard',1,'TEMPLATE',-152,1,
               CURRENT_TIMESTAMP,CURRENT_TIMESTAMP
        WHERE NOT EXISTS (SELECT 1 FROM dashboards WHERE code='FINANCIAL_MANAGEMENT_DEFAULT')
    """))
    op.execute(sa.text("""
        INSERT INTO dashboard_widgets
            (dashboard_id,widget_code,title,widget_type,query_code,position,width,
             refresh_seconds,config_json,is_active)
        SELECT d.id,'financial_contracts','Income and collection trend','LINE',
               'financial_contracts',0,6,300,'{}',1
        FROM dashboards d WHERE d.code='FINANCIAL_MANAGEMENT_DEFAULT'
          AND NOT EXISTS (SELECT 1 FROM dashboard_widgets w WHERE w.dashboard_id=d.id AND w.widget_code='financial_contracts')
    """))
    op.execute(sa.text("""
        INSERT INTO dashboard_widgets
            (dashboard_id,widget_code,title,widget_type,query_code,position,width,
             refresh_seconds,config_json,is_active)
        SELECT d.id,'financial_invoices','Cash contribution by client','STACKED_BAR',
               'financial_invoices',1,6,300,'{}',1
        FROM dashboards d WHERE d.code='FINANCIAL_MANAGEMENT_DEFAULT'
          AND NOT EXISTS (SELECT 1 FROM dashboard_widgets w WHERE w.dashboard_id=d.id AND w.widget_code='financial_invoices')
    """))
    op.execute(sa.text("""
        INSERT INTO dashboard_assignments
            (dashboard_id,profile_id,department_id,user_id,priority,effective_from,
             effective_until,is_active,version,created_at,updated_at)
        SELECT d.id,p.id,NULL,NULL,80,NULL,NULL,1,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP
        FROM dashboards d CROSS JOIN profiles p
        WHERE d.code='FINANCIAL_MANAGEMENT_DEFAULT' AND p.code='FINANCIAL_MANAGEMENT'
          AND NOT EXISTS (
            SELECT 1 FROM dashboard_assignments a
            WHERE a.dashboard_id=d.id AND a.profile_id=p.id
          )
    """))


def downgrade() -> None:
    op.execute("DELETE FROM dashboard_assignments WHERE dashboard_id IN (SELECT id FROM dashboards WHERE code='FINANCIAL_MANAGEMENT_DEFAULT')")
    op.execute("DELETE FROM dashboard_widgets WHERE dashboard_id IN (SELECT id FROM dashboards WHERE code='FINANCIAL_MANAGEMENT_DEFAULT')")
    op.execute("DELETE FROM dashboards WHERE code='FINANCIAL_MANAGEMENT_DEFAULT'")
    op.execute("DELETE FROM profile_permissions WHERE profile_id IN (SELECT id FROM profiles WHERE code='FINANCIAL_MANAGEMENT')")
    op.execute("DELETE FROM profiles WHERE code='FINANCIAL_MANAGEMENT'")
