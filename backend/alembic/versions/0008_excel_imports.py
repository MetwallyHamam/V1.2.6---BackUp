"""Staged Excel imports.

Revision ID: 0008_excel_imports
Revises: 0007_knowledge_base
"""
from alembic import op
from app.db.migration_helpers import create_frozen_tables
from app.modules.iam import models as iam_models  # noqa: F401
from app.modules.imports import models  # noqa: F401

revision = "0008_excel_imports"
down_revision = "0007_knowledge_base"
branch_labels = None
depends_on = None
def upgrade() -> None:
    create_frozen_tables(op.get_bind(), ("import_jobs", "import_rows", "import_errors"))
def downgrade() -> None:
    op.drop_table("import_errors"); op.drop_table("import_rows"); op.drop_table("import_jobs")
