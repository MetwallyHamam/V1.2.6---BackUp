"""Add the default category for ticket-generated knowledge.

Revision ID: 0274_ticket_knowledge_category
Revises: 0273_knowledge_downloads
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0274_ticket_knowledge_category"
down_revision: str | None = "0273_knowledge_downloads"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    categories = sa.table(
        "knowledge_categories",
        sa.column("id", sa.BigInteger),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    articles = sa.table(
        "knowledge_articles",
        sa.column("category_id", sa.BigInteger),
        sa.column("category", sa.String),
        sa.column("tags", sa.String),
    )
    category_id = connection.scalar(
        sa.select(categories.c.id).where(categories.c.code == "TICKETS_KNOWLEDGE_BASE")
    )
    if category_id is None:
        connection.execute(
            categories.insert().values(
                code="TICKETS_KNOWLEDGE_BASE",
                name="Tickets Knowledge Base",
                is_active=True,
            )
        )
        category_id = connection.scalar(
            sa.select(categories.c.id).where(categories.c.code == "TICKETS_KNOWLEDGE_BASE")
        )
    connection.execute(
        articles.update()
        .where(
            sa.or_(
                articles.c.category == "Resolved tickets",
                articles.c.tags.like("ticket,%"),
            )
        )
        .values(category_id=category_id, category="Tickets Knowledge Base")
    )


def downgrade() -> None:
    connection = op.get_bind()
    categories = sa.table(
        "knowledge_categories",
        sa.column("id", sa.BigInteger),
        sa.column("code", sa.String),
    )
    articles = sa.table(
        "knowledge_articles",
        sa.column("category_id", sa.BigInteger),
        sa.column("category", sa.String),
    )
    category_id = connection.scalar(
        sa.select(categories.c.id).where(categories.c.code == "TICKETS_KNOWLEDGE_BASE")
    )
    if category_id is not None:
        connection.execute(
            articles.update()
            .where(articles.c.category_id == category_id)
            .values(category_id=None, category="Resolved tickets")
        )
        connection.execute(categories.delete().where(categories.c.id == category_id))
