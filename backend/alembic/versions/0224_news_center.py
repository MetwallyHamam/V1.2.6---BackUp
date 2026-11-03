"""Add governed News Center publishing and user responses."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0224_news_center"
down_revision: str | None = "0223_vendor_pre_ticket_api"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None
id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "news_posts",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("template", sa.String(40), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("summary", sa.String(1000), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("image_filename", sa.String(120), nullable=True),
        sa.Column("image_content_type", sa.String(100), nullable=True),
        sa.Column("video_url", sa.String(1000), nullable=True),
        sa.Column("audience", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("is_featured", sa.Boolean(), nullable=False),
        sa.Column("requires_confirmation", sa.Boolean(), nullable=False),
        sa.Column("publish_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("publish_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("author_user_id", id_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("published_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_news_posts_publication", "news_posts", ["status", "publish_from", "publish_until"]
    )
    op.create_index("ix_news_posts_audience", "news_posts", ["audience", "is_featured"])
    op.create_table(
        "news_user_actions",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column(
            "news_post_id",
            id_type,
            sa.ForeignKey("news_posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", id_type, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("news_post_id", "user_id"),
    )
    permissions = (
        ("news.view", "View published news", False),
        ("news.create", "Create news drafts", False),
        ("news.publish", "Publish and unpublish news", True),
        ("news.manage", "Manage all news", True),
        ("news.analytics", "View news confirmations", False),
    )
    for code, description, high_risk in permissions:
        risk = 1 if high_risk else 0
        op.execute(
            sa.text(
                f"INSERT INTO permissions (code,module,description,is_high_risk,is_active) SELECT '{code}','news','{description}',{risk},1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='{code}')"
            )
        )
    op.execute(
        sa.text(
            "INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,pm.id,'NONE' FROM profiles p CROSS JOIN permissions pm WHERE pm.code='news.view' AND p.profile_type<>'API_INTEGRATION' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=pm.id)"
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,pm.id,'NONE' FROM profiles p CROSS JOIN permissions pm WHERE pm.code IN ('news.create','news.publish','news.manage','news.analytics') AND p.profile_type='ADMINISTRATOR' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=pm.id)"
        )
    )


def downgrade() -> None:
    op.drop_table("news_user_actions")
    op.drop_table("news_posts")
    op.execute(
        sa.text(
            "DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code LIKE 'news.%')"
        )
    )
    op.execute(sa.text("DELETE FROM permissions WHERE code LIKE 'news.%'"))
