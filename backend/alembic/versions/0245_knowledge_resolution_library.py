"""Add contextual knowledge and resolution templates.

Revision ID: 0245_knowledge_resolution
Revises: 0244_checklist_default_template
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0245_knowledge_resolution"
down_revision: str | None = "0244_checklist_default_template"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_categories",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(150), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    category_table = sa.table(
        "knowledge_categories",
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        category_table,
        [
            {"code": "TROUBLESHOOTING", "name": "Troubleshooting", "is_active": True},
            {"code": "HOW_TO", "name": "How To", "is_active": True},
            {"code": "KNOWN_ERROR", "name": "Known Error", "is_active": True},
            {"code": "RESOLUTION", "name": "Resolution", "is_active": True},
            {"code": "INSTALLATION", "name": "Installation", "is_active": True},
        ],
    )
    op.add_column("knowledge_articles", sa.Column("category_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True))
    op.add_column("knowledge_articles", sa.Column("resolution_summary_template", sa.Text(), nullable=True))
    op.add_column("knowledge_articles", sa.Column("root_cause_ids_json", sa.Text(), nullable=False, server_default="[]"))
    op.add_column("knowledge_articles", sa.Column("resolution_service_ids_json", sa.Text(), nullable=False, server_default="[]"))
    op.add_column("knowledge_articles", sa.Column("resolution_outcome_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True))
    op.add_column("knowledge_articles", sa.Column("permanent_fix_summary_template", sa.Text(), nullable=True))
    op.add_column("knowledge_articles", sa.Column("permanent_fix_status", sa.String(30), nullable=True))
    with op.batch_alter_table("knowledge_articles") as batch:
        batch.create_foreign_key("fk_knowledge_article_category", "knowledge_categories", ["category_id"], ["id"], ondelete="SET NULL")
        batch.create_foreign_key("fk_knowledge_article_resolution_outcome", "resolution_outcomes", ["resolution_outcome_id"], ["id"], ondelete="SET NULL")
    for table, target, column in (
        ("knowledge_article_products", "products", "product_id"),
        ("knowledge_article_modules", "product_modules", "product_module_id"),
        ("knowledge_article_services", "service_catalog_items", "service_id"),
        ("knowledge_article_clients", "clients", "client_id"),
    ):
        op.create_table(
            table,
            sa.Column("article_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("knowledge_articles.id", ondelete="CASCADE"), primary_key=True),
            sa.Column(column, sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey(f"{target}.id", ondelete="CASCADE"), primary_key=True),
        )
    op.create_table(
        "knowledge_usage",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("article_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("knowledge_articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("article_version", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("clients.id", ondelete="NO ACTION"), nullable=False),
        sa.Column("usage_type", sa.String(30), nullable=False),
        sa.Column("match_score", sa.Integer(), nullable=True),
        sa.Column("match_reasons_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("used_by_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_knowledge_usage_ticket_created", "knowledge_usage", ["ticket_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_usage_ticket_created", table_name="knowledge_usage")
    op.drop_table("knowledge_usage")
    for table in ("knowledge_article_clients", "knowledge_article_services", "knowledge_article_modules", "knowledge_article_products"):
        op.drop_table(table)
    with op.batch_alter_table("knowledge_articles") as batch:
        batch.drop_constraint("fk_knowledge_article_resolution_outcome", type_="foreignkey")
        batch.drop_constraint("fk_knowledge_article_category", type_="foreignkey")
        for column in ("permanent_fix_status", "permanent_fix_summary_template", "resolution_outcome_id", "resolution_service_ids_json", "root_cause_ids_json", "resolution_summary_template", "category_id"):
            batch.drop_column(column)
    op.drop_table("knowledge_categories")
