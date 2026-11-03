"""Knowledge base."""
from alembic import op
from app.db.migration_helpers import create_frozen_tables
from app.modules.iam import models as iam_models  # noqa: F401
from app.modules.knowledge_base import models  # noqa: F401

revision="0007_knowledge_base"; down_revision="0006_workforce"; branch_labels=None; depends_on=None
def upgrade() -> None: create_frozen_tables(op.get_bind(), ("knowledge_articles", "knowledge_article_versions"))
def downgrade() -> None: op.drop_table("knowledge_article_versions"); op.drop_table("knowledge_articles")
