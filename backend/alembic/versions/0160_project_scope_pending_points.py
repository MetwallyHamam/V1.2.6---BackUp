"""add template project scope and structured pending points

Revision ID: 0160_project_scope_points
Revises: 0159_pending_handover_editing
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0160_project_scope_points"
down_revision: str | None = "0159_pending_handover_editing"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

def upgrade() -> None:
    ident=sa.BigInteger().with_variant(sa.Integer(),"sqlite")
    op.add_column("project_handovers",sa.Column("source_template_id",ident))
    op.add_column("project_handovers",sa.Column("source_template_version",sa.Integer()))
    op.add_column("project_handover_products",sa.Column("service_id",ident))
    op.add_column("project_handover_products",sa.Column("delivery_date",sa.Date()))
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key("fk_project_handover_template","project_handovers","contract_templates",["source_template_id"],["id"])
        op.create_foreign_key("fk_project_handover_product_service","project_handover_products","service_catalog_items",["service_id"],["id"])
    op.create_table("project_handover_pending_points",sa.Column("id",ident,primary_key=True,autoincrement=True),sa.Column("handover_id",ident,sa.ForeignKey("project_handovers.id",ondelete="CASCADE"),nullable=False),sa.Column("product_id",ident,sa.ForeignKey("products.id"),nullable=False),sa.Column("product_module_id",ident,sa.ForeignKey("product_modules.id")),sa.Column("service_id",ident,sa.ForeignKey("service_catalog_items.id")),sa.Column("description",sa.String(2000),nullable=False),sa.Column("status",sa.String(20),nullable=False,server_default="OPEN"),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_handover_pending_status","project_handover_pending_points",["handover_id","status"])
    op.execute("UPDATE dashboard_widgets SET widget_code='project_pending_points', title='Open pending points' WHERE widget_code='project_pending_points_unavailable'")

def downgrade() -> None:
    op.execute("UPDATE dashboard_widgets SET widget_code='project_pending_points_unavailable', title='Pending points unavailable' WHERE widget_code='project_pending_points'")
    op.drop_index("ix_handover_pending_status",table_name="project_handover_pending_points");op.drop_table("project_handover_pending_points")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_project_handover_product_service","project_handover_products",type_="foreignkey")
        op.drop_constraint("fk_project_handover_template","project_handovers",type_="foreignkey")
    op.drop_column("project_handover_products","delivery_date");op.drop_column("project_handover_products","service_id")
    op.drop_column("project_handovers","source_template_version");op.drop_column("project_handovers","source_template_id")
