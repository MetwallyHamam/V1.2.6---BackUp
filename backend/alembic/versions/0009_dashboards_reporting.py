"""Dashboards, saved views, and reporting.

Revision ID: 0009_dashboards_reporting
Revises: 0008_excel_imports
"""
from alembic import op
from app.db.migration_helpers import create_frozen_tables
from app.modules.dashboards import models  # noqa: F401
from app.modules.iam import models as iam_models  # noqa: F401

revision = "0009_dashboards_reporting"
down_revision = "0008_excel_imports"
branch_labels = None
depends_on = None
def upgrade() -> None:
    create_frozen_tables(op.get_bind(), ("saved_views",))
def downgrade() -> None:
    op.drop_table("saved_views")
