"""Add program and task-level onboarding mentors."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0229_onboarding_mentors"
down_revision: str | None = "0228_user_theme_presets"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_onboardings", sa.Column("mentor_user_id", sa.BigInteger(), nullable=True))
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key("fk_user_onboardings_mentor", "user_onboardings", "users", ["mentor_user_id"], ["id"])
    op.add_column("user_onboarding_items", sa.Column("mentor_mode", sa.String(length=20), nullable=False, server_default="INHERIT"))
    op.add_column("user_onboarding_items", sa.Column("mentor_user_id", sa.BigInteger(), nullable=True))
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key("fk_user_onboarding_items_mentor", "user_onboarding_items", "users", ["mentor_user_id"], ["id"])


def downgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_user_onboarding_items_mentor", "user_onboarding_items", type_="foreignkey")
    op.drop_column("user_onboarding_items", "mentor_user_id")
    op.drop_column("user_onboarding_items", "mentor_mode")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_user_onboardings_mentor", "user_onboardings", type_="foreignkey")
    op.drop_column("user_onboardings", "mentor_user_id")
