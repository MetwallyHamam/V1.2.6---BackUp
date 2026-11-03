"""add reporting manager and support team leader

Revision ID: 0025_team_leadership
Revises: 0024_support_teams_skills
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0025_team_leadership"
down_revision: str | None = "0024_support_teams_skills"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("reports_to_user_id", sa.BigInteger(), nullable=True))
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_users_reports_to_user_id",
            "users",
            "users",
            ["reports_to_user_id"],
            ["id"],
        )
    op.add_column(
        "support_teams", sa.Column("leader_user_id", sa.BigInteger(), nullable=True)
    )
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_support_teams_leader_user_id",
            "support_teams",
            "users",
            ["leader_user_id"],
            ["id"],
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint(
            "fk_support_teams_leader_user_id", "support_teams", type_="foreignkey"
        )
    op.drop_column("support_teams", "leader_user_id")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_users_reports_to_user_id", "users", type_="foreignkey")
    op.drop_column("users", "reports_to_user_id")
