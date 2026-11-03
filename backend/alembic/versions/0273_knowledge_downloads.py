"""Add first-class knowledge downloads.

Revision ID: 0273_knowledge_downloads
Revises: 0272_deployment_issue_types
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0273_knowledge_downloads"
down_revision: str | None = "0272_deployment_issue_types"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "knowledge_download_categories" not in inspector.get_table_names():
        op.create_table(
            "knowledge_download_categories",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(150), nullable=False, unique=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        categories = sa.table(
            "knowledge_download_categories",
            sa.column("name", sa.String),
            sa.column("is_active", sa.Boolean),
        )
        op.bulk_insert(categories, [
            {"name": "Clients", "is_active": True},
            {"name": "Tools", "is_active": True},
            {"name": "Materials", "is_active": True},
            {"name": "Office", "is_active": True},
            {"name": "Millensys Products", "is_active": True},
        ])
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("knowledge_articles")}
    if "content_type" not in columns:
        op.add_column(
            "knowledge_articles",
            sa.Column("content_type", sa.String(20), nullable=False, server_default="ARTICLE"),
        )
    if "download_category_id" not in columns:
        op.add_column(
            "knowledge_articles", sa.Column("download_category_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True)
        )
        with op.batch_alter_table("knowledge_articles") as batch:
            batch.create_foreign_key(
                "fk_knowledge_articles_download_category",
                "knowledge_download_categories", ["download_category_id"], ["id"], ondelete="SET NULL"
            )
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("knowledge_articles")}
    if "ix_knowledge_articles_content_type" not in indexes:
        op.create_index(
            "ix_knowledge_articles_content_type",
            "knowledge_articles",
            ["content_type", "download_category_id", "status"],
        )


def downgrade() -> None:
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("knowledge_articles")}
    if "ix_knowledge_articles_content_type" in indexes:
        op.drop_index("ix_knowledge_articles_content_type", table_name="knowledge_articles")
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("knowledge_articles")}
    if "download_category_id" in columns:
        with op.batch_alter_table("knowledge_articles") as batch:
            batch.drop_constraint("fk_knowledge_articles_download_category", type_="foreignkey")
            batch.drop_column("download_category_id")
    if "content_type" in columns:
        op.drop_column("knowledge_articles", "content_type")
    if "knowledge_download_categories" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("knowledge_download_categories")
