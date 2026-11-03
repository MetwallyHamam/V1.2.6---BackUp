"""Link deployment issue resolutions to Knowledge Base drafts.

Revision ID: 0270_deployment_knowledge
Revises: 0269_deployment_ticket_types
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0270_deployment_knowledge"
down_revision: str | None = "0269_deployment_ticket_types"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _columns() -> set[str]:
    return {
        str(column["name"])
        for column in sa.inspect(op.get_bind()).get_columns("deployment_issues")
    }


def upgrade() -> None:
    if "knowledge_article_id" not in _columns():
        with op.batch_alter_table("deployment_issues") as batch:
            batch.add_column(
                sa.Column(
                    "knowledge_article_id",
                    sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                )
            )
            batch.create_foreign_key(
                "fk_deployment_issues_knowledge_article",
                "knowledge_articles",
                ["knowledge_article_id"],
                ["id"],
            )


def downgrade() -> None:
    if "knowledge_article_id" in _columns():
        with op.batch_alter_table("deployment_issues") as batch:
            batch.drop_constraint(
                "fk_deployment_issues_knowledge_article", type_="foreignkey"
            )
            batch.drop_column("knowledge_article_id")
