from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class ImportJob(Base):
    __tablename__ = "import_jobs"
    __table_args__ = (Index("ix_import_jobs_user_created", "uploaded_by_user_id", "created_at"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    template_type: Mapped[str] = mapped_column(String(50))
    template_version: Mapped[str] = mapped_column(String(20))
    original_filename: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(40), default="VALIDATING")
    uploaded_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0)
    inserted_rows: Mapped[int] = mapped_column(Integer, default=0)
    confirmation_reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ImportRow(Base):
    __tablename__ = "import_rows"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    import_job_id: Mapped[int] = mapped_column(IdType, ForeignKey("import_jobs.id", ondelete="CASCADE"))
    row_number: Mapped[int] = mapped_column(Integer)
    normalized_json: Mapped[str] = mapped_column(Text)
    proposed_action: Mapped[str] = mapped_column(String(20), default="INSERT")
    is_valid: Mapped[bool] = mapped_column(default=True)


class ImportError(Base):
    __tablename__ = "import_errors"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    import_job_id: Mapped[int] = mapped_column(IdType, ForeignKey("import_jobs.id", ondelete="CASCADE"))
    row_number: Mapped[int] = mapped_column(Integer)
    column_name: Mapped[str | None] = mapped_column(String(100))
    error_code: Mapped[str] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(String(500))

