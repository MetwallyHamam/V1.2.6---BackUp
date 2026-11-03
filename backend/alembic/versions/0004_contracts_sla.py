"""Contracts and SLA.

Revision ID: 0004_contracts_sla
Revises: 0003_internal_ticketing
"""
from alembic import op
from app.db.migration_helpers import create_frozen_tables
from app.modules.clients import models as client_models  # noqa: F401
from app.modules.contracts import models  # noqa: F401
from app.modules.iam import models as iam_models  # noqa: F401
from app.modules.tickets import models as ticket_models  # noqa: F401

revision = "0004_contracts_sla"
down_revision = "0003_internal_ticketing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_frozen_tables(op.get_bind(), ("business_calendars", "business_calendar_days", "holidays", "contracts", "contract_coverages", "sla_policies", "sla_targets", "ticket_sla_clocks"))


def downgrade() -> None:
    for table in ("ticket_sla_clocks", "sla_targets", "sla_policies", "contract_coverages", "contracts", "holidays", "business_calendar_days", "business_calendars"):
        op.drop_table(table)
