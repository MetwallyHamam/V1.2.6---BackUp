from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class DynamicReportDefinition(Base):
    __tablename__ = "dynamic_report_definitions"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(1000))
    category: Mapped[str] = mapped_column(String(80), default="General")
    stored_procedure: Mapped[str] = mapped_column(String(200), unique=True)
    filters_json: Mapped[str] = mapped_column(Text, default="[]")
    default_page_size: Mapped[int] = mapped_column(Integer, default=25)
    default_sort_column: Mapped[str | None] = mapped_column(String(120))
    default_sort_direction: Mapped[str] = mapped_column(String(4), default="DESC")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
