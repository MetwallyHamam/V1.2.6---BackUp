"""Add Problem collaboration and Major-Incident Problem follow-up.

Revision ID: 0251_problem_collab
Revises: 0250_major_incident_scopes
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0251_problem_collab"
down_revision: str | None = "0250_major_incident_scopes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    with op.batch_alter_table("major_incidents") as batch:
        batch.add_column(sa.Column("problem_follow_up_owner_user_id", ID))
        batch.add_column(sa.Column("problem_follow_up_due_at", sa.DateTime(timezone=True)))
        batch.create_foreign_key(
            "fk_major_incidents_problem_follow_up_owner",
            "users", ["problem_follow_up_owner_user_id"], ["id"],
        )
    op.create_table(
        "major_incident_problem_links",
        sa.Column("major_incident_id", ID, sa.ForeignKey("major_incidents.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("problem_id", ID, sa.ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("linked_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "problem_comments",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("problem_id", ID, sa.ForeignKey("problems.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.UnicodeText(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False),
        sa.Column("author_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_problem_comments_problem", "problem_comments", ["problem_id"])
    op.create_table(
        "problem_tasks",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("problem_id", ID, sa.ForeignKey("problems.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.Unicode(250), nullable=False),
        sa.Column("description", sa.UnicodeText()),
        sa.Column("assigned_user_id", ID, sa.ForeignKey("users.id")),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_problem_tasks_problem", "problem_tasks", ["problem_id"])
    op.create_table(
        "problem_knowledge_links",
        sa.Column("problem_id", ID, sa.ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("article_id", ID, sa.ForeignKey("knowledge_articles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("link_type", sa.String(30), nullable=False),
        sa.Column("linked_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("problem_knowledge_links")
    op.drop_table("problem_tasks")
    op.drop_table("problem_comments")
    op.drop_table("major_incident_problem_links")
    with op.batch_alter_table("major_incidents") as batch:
        batch.drop_constraint("fk_major_incidents_problem_follow_up_owner", type_="foreignkey")
        batch.drop_column("problem_follow_up_due_at")
        batch.drop_column("problem_follow_up_owner_user_id")
