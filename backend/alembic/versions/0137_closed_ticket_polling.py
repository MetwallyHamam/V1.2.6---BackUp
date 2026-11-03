"""Configure low-frequency polling for closed public tickets.

Revision ID: 0137_closed_ticket_polling
Revises: 0136_complaint_management
"""

import sqlalchemy as sa

from alembic import op

revision = "0137_closed_ticket_polling"
down_revision = "0136_complaint_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO site_settings ([key], [value], updated_at) "
            "SELECT :key, :value, CURRENT_TIMESTAMP WHERE NOT EXISTS "
            "(SELECT 1 FROM site_settings WHERE [key] = :key)"
        ).bindparams(key="live_ticket_update_closed_poll_seconds", value="300")
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM site_settings WHERE [key] = 'live_ticket_update_closed_poll_seconds'"
    )
