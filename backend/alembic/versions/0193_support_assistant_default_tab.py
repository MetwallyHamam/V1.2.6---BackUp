"""add default tab to per-user Support Assistant preferences.

Revision ID: 0193_assistant_user_state
Revises: 0192_server_local_time
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0193_assistant_user_state"
down_revision: str | None = "0192_server_local_time"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "support_assistant_preferences",
        sa.Column("default_tab", sa.String(length=30), nullable=False, server_default="queue"),
    )
    op.add_column(
        "support_assistant_preferences",
        sa.Column("workspace_state_json", sa.UnicodeText(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "support_assistant_preferences",
        sa.Column("custom_tabs_json", sa.UnicodeText(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("support_assistant_preferences", "custom_tabs_json")
    op.drop_column("support_assistant_preferences", "workspace_state_json")
    op.drop_column("support_assistant_preferences", "default_tab")
