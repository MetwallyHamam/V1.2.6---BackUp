"""protect internal ticket attachments from portal users

Revision ID: 0281_portal_attachment_access
Revises: 0280_maintenance_scheduling
"""

import sqlalchemy as sa

from alembic import op

revision = "0281_portal_attachment_access"
down_revision = "0280_maintenance_scheduling"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ticket_attachments",
        sa.Column(
            "portal_visible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("ticket_attachments", "portal_visible")
