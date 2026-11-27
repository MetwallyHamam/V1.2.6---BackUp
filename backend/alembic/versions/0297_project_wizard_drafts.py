"""Persist per-user unfinished project wizard drafts."""

import sqlalchemy as sa

from alembic import op

revision = "0297_project_wizard_drafts"
down_revision = "0296_project_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_wizard_drafts",
        sa.Column("owner_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("checkpoint", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("project_wizard_drafts")
