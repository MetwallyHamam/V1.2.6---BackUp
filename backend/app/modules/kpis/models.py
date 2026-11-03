from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer(), "sqlite")


class KpiTemplate(Base):
    __tablename__ = "kpi_templates"
    __table_args__ = (UniqueConstraint("code", "version"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(150))
    engineer_level: Mapped[str] = mapped_column(String(30))
    version: Mapped[int] = mapped_column(Integer)
    definitions_json: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class KpiReview(Base):
    __tablename__ = "kpi_reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "template_id", "period_start", "period_end"),
        Index("ix_kpi_reviews_period_status", "period_start", "period_end", "status"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    template_id: Mapped[int] = mapped_column(IdType, ForeignKey("kpi_templates.id"))
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    metrics_json: Mapped[str] = mapped_column(Text)
    ratings_json: Mapped[str] = mapped_column(Text)
    comments: Mapped[str | None] = mapped_column(Text)
    action_plan_json: Mapped[str | None] = mapped_column(Text)
    generated_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    reviewed_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    approved_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    finalized_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submission_version: Mapped[int] = mapped_column(Integer, default=0)
    submitted_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hr_viewed_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    hr_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class KpiReviewRevision(Base):
    __tablename__ = "kpi_review_revisions"
    __table_args__ = (
        UniqueConstraint("review_id", "submission_version", "snapshot_reason"),
        Index("ix_kpi_revision_review_version", "review_id", "submission_version"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(IdType, ForeignKey("kpi_reviews.id", ondelete="CASCADE"))
    submission_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    metrics_json: Mapped[str] = mapped_column(Text)
    ratings_json: Mapped[str] = mapped_column(Text)
    comments: Mapped[str | None] = mapped_column(Text)
    action_plan_json: Mapped[str | None] = mapped_column(Text)
    weighted_score_percent: Mapped[float] = mapped_column(Float)
    snapshot_reason: Mapped[str] = mapped_column(String(40))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class KpiSubmissionBatch(Base):
    __tablename__ = "kpi_submission_batches"
    __table_args__ = (UniqueConstraint("year", "quarter", "version"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150))
    year: Mapped[int] = mapped_column(Integer)
    quarter: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="SUBMITTED")
    submitted_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    recipient_emails_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class KpiSubmissionBatchItem(Base):
    __tablename__ = "kpi_submission_batch_items"
    __table_args__ = (UniqueConstraint("review_id", "submission_version"),)
    batch_id: Mapped[int] = mapped_column(IdType, ForeignKey("kpi_submission_batches.id", ondelete="CASCADE"), primary_key=True)
    review_id: Mapped[int] = mapped_column(IdType, ForeignKey("kpi_reviews.id"), primary_key=True)
    submission_version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
