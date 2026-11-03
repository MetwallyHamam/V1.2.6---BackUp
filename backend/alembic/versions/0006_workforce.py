"""Workforce shifts.

Revision ID: 0006_workforce
Revises: 0005_escalations_notifications
"""
from alembic import op
from app.db.migration_helpers import create_frozen_tables
from app.modules.iam import models as iam_models  # noqa: F401
from app.modules.shifts import models  # noqa: F401

revision = "0006_workforce"
down_revision = "0005_escalations_notifications"
branch_labels = None
depends_on = None
def upgrade() -> None:
    create_frozen_tables(op.get_bind(), ("shift_types", "shifts", "handovers"))
def downgrade() -> None:
    op.drop_table("handovers"); op.drop_table("shifts"); op.drop_table("shift_types")
