"""add HR and project delivery dashboard templates

Revision ID: 0156_hr_project_dashboards
Revises: 0155_financial_widgets
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0156_hr_project_dashboards"
down_revision: str | None = "0155_financial_widgets"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

TEMPLATES = {
    "HR": (
        "HR_DEFAULT", "Human Resources", "Governed workforce, KPI, shift, and onboarding overview",
        (
            ("hr_total_employees", "Total employees", "KPI_CARD", 0, 2),
            ("hr_active_employees", "Active employees", "KPI_CARD", 1, 2),
            ("hr_inactive_employees", "Inactive employees", "KPI_CARD", 2, 2),
            ("hr_departments", "Departments", "KPI_CARD", 3, 2),
            ("hr_head_vacancies", "Head vacancies", "KPI_CARD", 4, 2),
            ("hr_reporting_exceptions", "Reporting-line exceptions", "KPI_CARD", 5, 2),
            ("hr_kpi_pending", "KPI reviews pending", "KPI_CARD", 6, 2),
            ("hr_kpi_finalized", "KPI reviews finalized", "KPI_CARD", 7, 2),
            ("hr_onboarding_in_progress", "Onboarding in progress", "KPI_CARD", 8, 2),
            ("hr_unscheduled_employees", "Unscheduled employees", "KPI_CARD", 9, 2),
        ),
    ),
    "PROJECT_HANDOVER": (
        "PROJECT_HANDOVER_DEFAULT", "Project Delivery", "Governed project handover and delivery overview",
        (
            ("project_total", "Total projects", "KPI_CARD", 0, 2),
            ("project_delivered", "Delivered projects", "KPI_CARD", 1, 2),
            ("project_in_progress", "Projects in progress", "KPI_CARD", 2, 2),
            ("project_awaiting_acceptance", "Awaiting acceptance", "KPI_CARD", 3, 2),
            ("project_pending_products", "Pending products", "KPI_CARD", 4, 2),
            ("project_pending_points_unavailable", "Pending points unavailable", "KPI_CARD", 5, 2),
            ("projects_by_status", "Projects by status", "DONUT", 6, 6),
            ("projects_by_client", "Projects by client", "STACKED_BAR", 7, 6),
        ),
    ),
}


def upgrade() -> None:
    for profile_code, (dashboard_code, name, description, widgets) in TEMPLATES.items():
        op.execute(sa.text(f"""
            INSERT INTO profile_permissions (profile_id,permission_id,scope_type)
            SELECT p.id,pm.id,'NONE' FROM profiles p CROSS JOIN permissions pm
            WHERE p.code='{profile_code}' AND pm.code='dashboard.agent'
              AND NOT EXISTS (
                SELECT 1 FROM profile_permissions pp
                WHERE pp.profile_id=p.id AND pp.permission_id=pm.id
              )
        """))
        legacy_assignment_id = -156 if profile_code == "HR" else -157
        op.execute(sa.text(f"""
            INSERT INTO dashboards
                (name,code,description,version,assignment_type,assignment_id,is_active,created_at,updated_at)
            SELECT '{name}','{dashboard_code}','{description}',1,'TEMPLATE',{legacy_assignment_id},1,
                   CURRENT_TIMESTAMP,CURRENT_TIMESTAMP
            WHERE NOT EXISTS (SELECT 1 FROM dashboards WHERE code='{dashboard_code}')
        """))
        for code, title, widget_type, position, width in widgets:
            op.execute(sa.text(f"""
                INSERT INTO dashboard_widgets
                    (dashboard_id,widget_code,title,widget_type,query_code,position,width,
                     refresh_seconds,config_json,is_active)
                SELECT d.id,'{code}','{title}','{widget_type}','{code}',{position},{width},300,'{{}}',1
                FROM dashboards d WHERE d.code='{dashboard_code}'
                  AND NOT EXISTS (SELECT 1 FROM dashboard_widgets w WHERE w.dashboard_id=d.id AND w.widget_code='{code}')
            """))
        op.execute(sa.text(f"""
            INSERT INTO dashboard_assignments
                (dashboard_id,profile_id,department_id,user_id,priority,effective_from,
                 effective_until,is_active,version,created_at,updated_at)
            SELECT d.id,p.id,NULL,NULL,80,NULL,NULL,1,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP
            FROM dashboards d CROSS JOIN profiles p
            WHERE d.code='{dashboard_code}' AND p.code='{profile_code}'
              AND NOT EXISTS (
                SELECT 1 FROM dashboard_assignments a
                WHERE a.dashboard_id=d.id AND a.profile_id=p.id
              )
        """))


def downgrade() -> None:
    codes = "'HR_DEFAULT','PROJECT_HANDOVER_DEFAULT'"
    op.execute(sa.text(f"DELETE FROM dashboard_assignments WHERE dashboard_id IN (SELECT id FROM dashboards WHERE code IN ({codes}))"))
    op.execute(sa.text(f"DELETE FROM dashboard_widgets WHERE dashboard_id IN (SELECT id FROM dashboards WHERE code IN ({codes}))"))
    op.execute(sa.text(f"DELETE FROM dashboards WHERE code IN ({codes})"))
