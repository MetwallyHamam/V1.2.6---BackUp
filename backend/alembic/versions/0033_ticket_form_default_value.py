"""add ticket form default values

Revision ID: 0033_ticket_form_default_value
Revises: 0032_ticket_form_settings
"""

import sqlalchemy as sa

from alembic import op

revision = "0033_ticket_form_default_value"
down_revision = "0032_ticket_form_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ticket_form_field_settings",
        sa.Column("default_value", sa.String(length=150), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE ticket_form_field_settings SET default_value = 'SERVICE_REQUEST' "
            "WHERE field_key = 'ticket_type_id'"
        )
    )


def downgrade() -> None:
    op.drop_column("ticket_form_field_settings", "default_value")
