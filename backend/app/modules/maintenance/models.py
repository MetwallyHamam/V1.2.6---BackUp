from datetime import datetime, time

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer(), "sqlite")


class MaintenanceSchedule(Base):
    __tablename__ = "maintenance_schedules"
    __table_args__ = (Index("ix_maintenance_schedules_due", "is_enabled", "next_run_at"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150))
    job_type: Mapped[str] = mapped_column(String(40))
    frequency: Mapped[str] = mapped_column(String(20), default="DAILY")
    run_time: Mapped[time] = mapped_column(Time)
    weekday: Mapped[int | None] = mapped_column(Integer)
    day_of_month: Mapped[int | None] = mapped_column(Integer)
    retention_days: Mapped[int] = mapped_column(Integer, default=30)
    keep_last: Mapped[int] = mapped_column(Integer, default=7)
    is_enabled: Mapped[bool] = mapped_column(default=False)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(20))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class MaintenanceRun(Base):
    __tablename__ = "maintenance_runs"
    __table_args__ = (Index("ix_maintenance_runs_schedule_started", "schedule_id", "started_at"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    schedule_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("maintenance_schedules.id", ondelete="SET NULL"))
    job_type: Mapped[str] = mapped_column(String(40))
    trigger_type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    artifact_path: Mapped[str | None] = mapped_column(String(1000))
    artifact_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    deleted_items: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    initiated_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
