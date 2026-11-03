"""Escalations and notifications.

Revision ID: 0005_escalations_notifications
Revises: 0004_contracts_sla
"""
from alembic import op
from app.db.migration_helpers import create_frozen_tables
from app.modules.clients import models as client_models  # noqa: F401
from app.modules.contracts import models as contract_models  # noqa: F401
from app.modules.escalations import models as escalation_models  # noqa: F401
from app.modules.iam import models as iam_models  # noqa: F401
from app.modules.notifications import models  # noqa: F401
from app.modules.tickets import models as ticket_models  # noqa: F401

revision = "0005_escalations_notifications"
down_revision = "0004_contracts_sla"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_frozen_tables(op.get_bind(), ("notifications", "event_outbox", "escalation_rules", "escalation_events"))


def downgrade() -> None:
    for table in ("escalation_events", "escalation_rules", "event_outbox", "notifications"):
        op.drop_table(table)
