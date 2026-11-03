"""Distinguish filter-only saved views from views with layouts."""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0198_view_layout_scope"
down_revision: str | None = "0197_ticket_requirements"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("saved_views")}
    if "has_layout" not in columns:
        op.add_column("saved_views", sa.Column("has_layout", sa.Boolean(), nullable=False, server_default=sa.true()))
    if bind.dialect.name == "mssql":
        bind.execute(sa.text("UPDATE users SET default_saved_view_id = (SELECT TOP 1 id FROM saved_views WHERE saved_views.owner_user_id = users.id AND saved_views.is_default = 1 AND saved_views.is_active = 1 ORDER BY id) WHERE default_saved_view_id IS NULL"))
    else:
        bind.execute(sa.text("UPDATE users SET default_saved_view_id = (SELECT id FROM saved_views WHERE saved_views.owner_user_id = users.id AND saved_views.is_default = 1 AND saved_views.is_active = 1 ORDER BY id LIMIT 1) WHERE default_saved_view_id IS NULL"))

def downgrade() -> None:
    op.drop_column("saved_views", "has_layout")
