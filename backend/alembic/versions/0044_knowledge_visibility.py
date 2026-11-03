"""add three-way knowledge visibility"""

import sqlalchemy as sa

from alembic import op

revision = "0044_knowledge_visibility"
down_revision = "0043_client_access_all_internal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("knowledge_articles", sa.Column("visibility", sa.String(30), nullable=False, server_default="INTERNAL"))
    op.execute(sa.text("UPDATE knowledge_articles SET visibility = CASE WHEN client_visible = 1 THEN 'BOTH' ELSE 'INTERNAL' END"))
    op.create_index("ix_articles_visibility", "knowledge_articles", ["status", "visibility"])


def downgrade() -> None:
    op.drop_index("ix_articles_visibility", table_name="knowledge_articles")
    op.drop_column("knowledge_articles", "visibility")
