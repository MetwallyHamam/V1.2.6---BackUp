"""Add optional likes, comments, polls and mentions to news posts."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0225_news_engagement"
down_revision: str | None = "0224_news_center"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None
id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "news_likes",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("news_post_id", id_type, sa.ForeignKey("news_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", id_type, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("news_post_id", "user_id"),
    )
    op.create_table(
        "news_comments",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("news_post_id", id_type, sa.ForeignKey("news_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_user_id", id_type, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.String(2000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_news_comments_post_created", "news_comments", ["news_post_id", "created_at"])
    op.create_table("news_mentions", sa.Column("id", id_type, primary_key=True, autoincrement=True), sa.Column("news_post_id", id_type, sa.ForeignKey("news_posts.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", id_type, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.UniqueConstraint("news_post_id", "user_id"))
    op.create_table("news_poll_options", sa.Column("id", id_type, primary_key=True, autoincrement=True), sa.Column("news_post_id", id_type, sa.ForeignKey("news_posts.id", ondelete="CASCADE"), nullable=False), sa.Column("label", sa.String(300), nullable=False), sa.Column("position", sa.Integer(), nullable=False))
    op.create_table("news_poll_votes", sa.Column("id", id_type, primary_key=True, autoincrement=True), sa.Column("news_post_id", id_type, sa.ForeignKey("news_posts.id"), nullable=False), sa.Column("option_id", id_type, sa.ForeignKey("news_poll_options.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", id_type, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("news_post_id", "user_id"))


def downgrade() -> None:
    op.drop_table("news_poll_votes")
    op.drop_table("news_poll_options")
    op.drop_table("news_mentions")
    op.drop_index("ix_news_comments_post_created", table_name="news_comments")
    op.drop_table("news_comments")
    op.drop_table("news_likes")
