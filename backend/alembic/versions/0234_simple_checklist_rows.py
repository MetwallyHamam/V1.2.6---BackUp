"""Add simple service-checklist row fields.

Revision ID: 0234_simple_checklist_rows
Revises: 0233_ticket_reports
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0234_simple_checklist_rows"
down_revision: str | None = "0233_ticket_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.add_column("service_checklist_template_items", sa.Column("resource_type", sa.String(30), nullable=False, server_default="CUSTOM"))
    op.add_column("service_checklist_template_items", sa.Column("resource_path", sa.Unicode(1000)))
    op.add_column("service_checklist_occurrence_items", sa.Column("resource_type", sa.String(30), nullable=False, server_default="CUSTOM"))
    op.add_column("service_checklist_occurrence_items", sa.Column("resource_path", sa.Unicode(1000)))
    op.add_column("service_checklist_occurrence_items", sa.Column("check_date", sa.DateTime(timezone=True)))
    op.execute("UPDATE service_checklist_occurrence_items SET state='COMPLETE' WHERE state='COMPLETED'")
    op.execute("UPDATE service_checklist_occurrence_items SET state='CLIENT_RESPONSIBILITY' WHERE state='CLIENT_RESPONSIBLE'")

def downgrade() -> None:
    op.drop_column("service_checklist_occurrence_items", "check_date")
    op.drop_column("service_checklist_occurrence_items", "resource_path")
    op.drop_column("service_checklist_occurrence_items", "resource_type")
    op.drop_column("service_checklist_template_items", "resource_path")
    op.drop_column("service_checklist_template_items", "resource_type")
