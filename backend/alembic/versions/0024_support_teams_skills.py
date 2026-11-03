"""Add support teams and skills.

Revision ID: 0024_support_teams_skills
Revises: 0023_password_reset_tokens
"""

import sqlalchemy as sa

from alembic import op

revision = "0024_support_teams_skills"
down_revision = "0023_password_reset_tokens"
branch_labels = None
depends_on = None

id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    for table in ("support_teams", "support_skills"):
        op.create_table(
            table,
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("code", sa.String(50), nullable=False, unique=True),
            sa.Column("name", sa.String(150), nullable=False, unique=True),
            sa.Column("description", sa.String(1000)),
            sa.Column("is_active", sa.Boolean(), nullable=False),
        )
    op.create_table(
        "support_team_skills",
        sa.Column("team_id", id_type, nullable=False),
        sa.Column("skill_id", id_type, nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["support_teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["support_skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("team_id", "skill_id"),
    )


def downgrade() -> None:
    op.drop_table("support_team_skills")
    op.drop_table("support_skills")
    op.drop_table("support_teams")
