"""Add coordinated per-user theme presets."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0228_user_theme_presets"
down_revision: str | None = "0227_contract_ticket_policy"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("theme_preset", sa.String(length=20), nullable=False, server_default="CLASSIC"),
    )


def downgrade() -> None:
    op.drop_column("users", "theme_preset")
