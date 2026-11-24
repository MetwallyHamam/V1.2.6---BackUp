from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ScheduleWrite(BaseModel):
    name: str = Field(min_length=3, max_length=150)
    job_type: Literal["LOG_CLEANUP", "DATABASE_BACKUP", "APPLICATION_BACKUP"]
    frequency: Literal["DAILY", "WEEKLY", "MONTHLY"] = "DAILY"
    run_time: time
    weekday: int | None = Field(default=None, ge=0, le=6)
    day_of_month: int | None = Field(default=None, ge=1, le=28)
    retention_days: int = Field(default=30, ge=1, le=3650)
    keep_last: int = Field(default=7, ge=1, le=1000)
    is_enabled: bool = False
    expected_version: int | None = None

    @model_validator(mode="after")
    def validate_frequency(self) -> "ScheduleWrite":
        if self.frequency == "WEEKLY" and self.weekday is None:
            raise ValueError("Weekly schedules require a weekday.")
        if self.frequency == "MONTHLY" and self.day_of_month is None:
            raise ValueError("Monthly schedules require a day of month.")
        return self


class ScheduleRead(BaseModel):
    id: int
    name: str
    job_type: str
    frequency: str
    run_time: time
    weekday: int | None
    day_of_month: int | None
    retention_days: int
    keep_last: int
    is_enabled: bool
    next_run_at: datetime | None
    last_run_at: datetime | None
    last_status: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class RunRead(BaseModel):
    id: int
    schedule_id: int | None
    job_type: str
    trigger_type: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None
    artifact_path: str | None
    artifact_size_bytes: int | None
    deleted_items: int
    summary: str | None
    error_message: str | None


class ManualRunWrite(BaseModel):
    job_type: Literal["LOG_CLEANUP", "DATABASE_BACKUP", "APPLICATION_BACKUP"]
    retention_days: int = Field(default=30, ge=1, le=3650)
    keep_last: int = Field(default=7, ge=1, le=1000)
