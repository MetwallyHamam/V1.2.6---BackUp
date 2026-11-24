"""Store reusable project templates and immutable plan versions."""

import sqlalchemy as sa

from alembic import op

revision = "0296_project_templates"
down_revision = "0295_project_lifecycle"
branch_labels = None
depends_on = None
ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "project_templates",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("owner_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_project_templates_owner", "project_templates", ["owner_user_id"])
    op.create_table(
        "project_template_versions",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("template_id", ID, sa.ForeignKey("project_templates.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("template_id", "version_number"),
    )


def downgrade() -> None:
    op.drop_table("project_template_versions")
    op.drop_index("ix_project_templates_owner", table_name="project_templates")
    op.drop_table("project_templates")
