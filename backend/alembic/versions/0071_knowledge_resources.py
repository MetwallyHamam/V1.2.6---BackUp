"""knowledge article downloadable resources

Revision ID: 0071_knowledge_resources
Revises: 0070_dedicated_sla
"""

import sqlalchemy as sa

from alembic import op

revision = "0071_knowledge_resources"
down_revision = "0070_dedicated_sla"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_article_resources",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("article_id", sa.BigInteger(), sa.ForeignKey("knowledge_articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000)),
        sa.Column("external_url", sa.String(2000)),
        sa.Column("original_filename", sa.String(255)),
        sa.Column("stored_filename", sa.String(100)),
        sa.Column("content_type", sa.String(150)),
        sa.Column("size_bytes", sa.BigInteger()),
        sa.Column("sha256", sa.String(64)),
        sa.Column("created_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_knowledge_resources_article", "knowledge_article_resources", ["article_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_resources_article", table_name="knowledge_article_resources")
    op.drop_table("knowledge_article_resources")
