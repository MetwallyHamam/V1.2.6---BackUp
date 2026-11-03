"""personal workspace favorites and recent pages

Revision ID: 0275_personal_workspace
Revises: 0274_ticket_knowledge_category
"""

import sqlalchemy as sa

from alembic import op

revision = "0275_personal_workspace"
down_revision = "0274_ticket_knowledge_category"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "support_assistant_preferences",
        sa.Column("workspace_favorites_json", sa.UnicodeText(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "support_assistant_preferences",
        sa.Column("workspace_recent_json", sa.UnicodeText(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "support_assistant_preferences",
        sa.Column("workspace_settings_json", sa.UnicodeText(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("support_assistant_preferences", "workspace_settings_json")
    op.drop_column("support_assistant_preferences", "workspace_recent_json")
    op.drop_column("support_assistant_preferences", "workspace_favorites_json")
