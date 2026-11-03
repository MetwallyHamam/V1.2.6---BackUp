"""add handover documents"""
from alembic import op
from app.db.migration_helpers import create_frozen_tables
from app.modules.project_handovers import models  # noqa: F401

revision="0041_handover_documents";down_revision="0040_project_handovers";branch_labels=None;depends_on=None
def upgrade()->None: create_frozen_tables(op.get_bind(), ("project_handover_documents",))
def downgrade()->None: op.drop_table("project_handover_documents")
