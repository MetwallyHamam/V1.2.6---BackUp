"""persist the personal default ticket-page view and card layout.

Revision ID: 0195_ticket_default_view
Revises: 0194_ticket_grid_preferences
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0195_ticket_default_view"
down_revision: str | None = "0194_ticket_grid_preferences"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ticket_grid_preferences",
        sa.Column("default_view_mode", sa.String(length=10), nullable=False, server_default="GRID"),
    )
    op.add_column(
        "ticket_grid_preferences",
        sa.Column("selected_group_values_json", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "ticket_grid_preferences",
        sa.Column("board_settings_json", sa.Text(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("ticket_grid_preferences", "board_settings_json")
    op.drop_column("ticket_grid_preferences", "selected_group_values_json")
    op.drop_column("ticket_grid_preferences", "default_view_mode")
