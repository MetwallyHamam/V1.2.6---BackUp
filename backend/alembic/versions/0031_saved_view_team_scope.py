"""add team scope to saved views

Revision ID: 0031_saved_view_team_scope
Revises: 0030_contract_coverage_context
"""

import sqlalchemy as sa

from alembic import op

revision = "0031_saved_view_team_scope"
down_revision = "0030_contract_coverage_context"
branch_labels = None
depends_on = None
id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.add_column("saved_views", sa.Column("team_id", id_type, nullable=True))
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_saved_views_team_id", "saved_views", "support_teams", ["team_id"], ["id"]
        )
    op.create_index("ix_saved_views_team_scope", "saved_views", ["team_id", "scope"])


def downgrade() -> None:
    op.drop_index("ix_saved_views_team_scope", table_name="saved_views")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_saved_views_team_id", "saved_views", type_="foreignkey")
    op.drop_column("saved_views", "team_id")
