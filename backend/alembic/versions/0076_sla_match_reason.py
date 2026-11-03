"""persist SLA resolver match reason

Revision ID: 0076_sla_match_reason
Revises: 0075_sla_shadow_evidence
"""

import sqlalchemy as sa

from alembic import op

revision = "0076_sla_match_reason"
down_revision = "0075_sla_shadow_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ticket_sla_clocks", sa.Column("match_reason", sa.String(80)))
    op.execute("UPDATE ticket_sla_clocks SET match_reason='LEGACY_SERVICE_SELECTION' WHERE match_reason IS NULL")


def downgrade() -> None:
    op.drop_column("ticket_sla_clocks", "match_reason")
