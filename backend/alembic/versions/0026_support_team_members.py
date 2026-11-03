"""add support team members

Revision ID: 0026_support_team_members
Revises: 0025_team_leadership
"""

import sqlalchemy as sa

from alembic import op

revision = "0026_support_team_members"
down_revision = "0025_team_leadership"
branch_labels = None
depends_on = None

id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "support_team_members",
        sa.Column("team_id", id_type, nullable=False),
        sa.Column("user_id", id_type, nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["support_teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("team_id", "user_id"),
    )
    op.create_index(
        "ix_support_team_members_user_id", "support_team_members", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_support_team_members_user_id", table_name="support_team_members")
    op.drop_table("support_team_members")
