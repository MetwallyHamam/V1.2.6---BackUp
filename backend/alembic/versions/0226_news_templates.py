"""Add reusable News post templates."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0226_news_templates"
down_revision: str | None = "0225_news_engagement"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("news_posts", sa.Column("is_template", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("news_posts", "is_template")
