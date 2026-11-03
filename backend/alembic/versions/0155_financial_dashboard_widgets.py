"""add dedicated financial dashboard widgets

Revision ID: 0155_financial_widgets
Revises: 0154_dashboard_override_base
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0155_financial_widgets"
down_revision: str | None = "0154_dashboard_override_base"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

WIDGETS = (
    ("financial_contract_value", "Contract value", "STACKED_BAR", 2),
    ("financial_contract_expiry", "Contract expiry", "STACKED_BAR", 3),
    ("financial_discounts", "Discounts", "STACKED_BAR", 4),
    ("financial_adjustments", "Additional adjustments", "STACKED_BAR", 5),
)


def upgrade() -> None:
    for code, title, widget_type, position in WIDGETS:
        op.execute(sa.text(f"""
            INSERT INTO dashboard_widgets
                (dashboard_id,widget_code,title,widget_type,query_code,position,width,
                 refresh_seconds,config_json,is_active)
            SELECT d.id,'{code}','{title}','{widget_type}','{code}',{position},6,300,'{{}}',1
            FROM dashboards d WHERE d.code='FINANCIAL_MANAGEMENT_DEFAULT'
              AND NOT EXISTS (
                SELECT 1 FROM dashboard_widgets w
                WHERE w.dashboard_id=d.id AND w.widget_code='{code}'
              )
        """))
    op.execute(sa.text("""
        UPDATE dashboards SET version=version+1, updated_at=CURRENT_TIMESTAMP
        WHERE code='FINANCIAL_MANAGEMENT_DEFAULT'
    """))


def downgrade() -> None:
    codes = ",".join(f"'{item[0]}'" for item in WIDGETS)
    op.execute(sa.text(f"""
        DELETE FROM dashboard_widgets
        WHERE dashboard_id IN (
            SELECT id FROM dashboards WHERE code='FINANCIAL_MANAGEMENT_DEFAULT'
        ) AND widget_code IN ({codes})
    """))
    op.execute(sa.text("""
        UPDATE dashboards SET version=CASE WHEN version > 1 THEN version-1 ELSE 1 END,
            updated_at=CURRENT_TIMESTAMP
        WHERE code='FINANCIAL_MANAGEMENT_DEFAULT'
    """))
