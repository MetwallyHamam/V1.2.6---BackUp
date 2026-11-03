"""Internal ticketing MVP.

Revision ID: 0003_internal_ticketing
Revises: 0002_crm_master_data
"""
from alembic import op
from app.db.migration_helpers import create_frozen_tables
from app.modules.clients import models as client_models  # noqa: F401
from app.modules.iam import models as iam_models  # noqa: F401
from app.modules.tickets import models  # noqa: F401

revision = "0003_internal_ticketing"
down_revision = "0002_crm_master_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_frozen_tables(op.get_bind(), ("ticket_types", "ticket_statuses", "tickets", "ticket_comments", "ticket_status_history"))


def downgrade() -> None:
    op.drop_table("ticket_status_history")
    op.drop_table("ticket_comments")
    op.drop_table("tickets")
    op.drop_table("ticket_statuses")
    op.drop_table("ticket_types")
