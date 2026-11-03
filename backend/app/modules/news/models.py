from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class NewsPost(Base):
    __tablename__ = "news_posts"
    __table_args__ = (
        Index("ix_news_posts_publication", "status", "publish_from", "publish_until"),
        Index("ix_news_posts_audience", "audience", "is_featured"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    template: Mapped[str] = mapped_column(String(40), default="GENERAL")
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(String(1000))
    body: Mapped[str] = mapped_column(Text)
    image_filename: Mapped[str | None] = mapped_column(String(120))
    image_content_type: Mapped[str | None] = mapped_column(String(100))
    video_url: Mapped[str | None] = mapped_column(String(1000))
    audience: Mapped[str] = mapped_column(String(30), default="ALL")
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    publish_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    publish_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    author_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    published_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class NewsUserAction(Base):
    __tablename__ = "news_user_actions"
    __table_args__ = (UniqueConstraint("news_post_id", "user_id"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    news_post_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("news_posts.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class NewsLike(Base):
    __tablename__ = "news_likes"
    __table_args__ = (UniqueConstraint("news_post_id", "user_id"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    news_post_id: Mapped[int] = mapped_column(IdType, ForeignKey("news_posts.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class NewsComment(Base):
    __tablename__ = "news_comments"
    __table_args__ = (Index("ix_news_comments_post_created", "news_post_id", "created_at"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    news_post_id: Mapped[int] = mapped_column(IdType, ForeignKey("news_posts.id", ondelete="CASCADE"))
    author_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    body: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class NewsMention(Base):
    __tablename__ = "news_mentions"
    __table_args__ = (UniqueConstraint("news_post_id", "user_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    news_post_id: Mapped[int] = mapped_column(IdType, ForeignKey("news_posts.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))


class NewsPollOption(Base):
    __tablename__ = "news_poll_options"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    news_post_id: Mapped[int] = mapped_column(IdType, ForeignKey("news_posts.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(300))
    position: Mapped[int] = mapped_column(Integer)


class NewsPollVote(Base):
    __tablename__ = "news_poll_votes"
    __table_args__ = (UniqueConstraint("news_post_id", "user_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    # The option already cascades from the post. Keep this denormalized key
    # non-cascading to avoid SQL Server's multiple-cascade-path restriction.
    news_post_id: Mapped[int] = mapped_column(IdType, ForeignKey("news_posts.id"))
    option_id: Mapped[int] = mapped_column(IdType, ForeignKey("news_poll_options.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
