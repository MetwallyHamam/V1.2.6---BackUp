"""Ticket knowledge links.

Revision ID: 0019_ticket_knowledge_links
Revises: 0018_ticket_relations
"""

import sqlalchemy as sa

from alembic import op

revision = "0019_ticket_knowledge_links"
down_revision = "0018_ticket_relations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ticket_article_links",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("article_id", sa.BigInteger(), nullable=False),
        sa.Column("linked_by_user_id", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["knowledge_articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_id", "article_id"),
    )
    op.create_index("ix_ticket_article_links_ticket", "ticket_article_links", ["ticket_id"])


def downgrade() -> None:
    op.drop_index("ix_ticket_article_links_ticket", table_name="ticket_article_links")
    op.drop_table("ticket_article_links")
