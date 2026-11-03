from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class KpiEmployeeRead(BaseModel):
    id: int
    full_name: str
    employee_code: str | None
    department: str | None
    job_title: str | None
    engineer_level: str


class KpiTemplateRead(BaseModel):
    id: int
    code: str
    name: str
    engineer_level: str
    version: int
    definitions: list[dict[str, Any]]


class KpiReviewWrite(BaseModel):
    ratings: dict[str, int | None] = Field(default_factory=dict)
    comments: str | None = Field(default=None, max_length=5000)
    action_plan: list[dict[str, str]] = Field(default_factory=list)
    status: Literal["DRAFT", "REVIEWED", "APPROVED", "FINALIZED", "SUBMITTED"] | None = None
    lock_values: bool = False


class KpiReviewRead(BaseModel):
    id: int
    user_id: int
    employee: str
    employee_code: str | None
    department: str | None
    job_title: str | None
    manager: str | None
    engineer_level: str
    template_id: int
    template_code: str
    template_version: int
    period_start: datetime
    period_end: datetime
    status: str
    is_locked: bool
    definitions: list[dict[str, Any]]
    metrics: dict[str, Any]
    ratings: dict[str, int | None]
    weighted_score_percent: float
    comments: str | None
    action_plan: list[dict[str, str]]
    created_at: datetime
    updated_at: datetime
    submission_version: int
    submitted_at: datetime | None
    submitted_by_user_id: int | None
    hr_viewed_at: datetime | None
    hr_viewed_by_user_id: int | None


class KpiTrendPoint(BaseModel):
    review_id: int
    period_start: datetime
    period_end: datetime
    score: float
    status: str
    submission_version: int
    hr_viewed_at: datetime | None


class KpiComparisonRead(BaseModel):
    user_id: int
    employee: str
    review_count: int
    average_score: float
    minimum_score: float
    maximum_score: float
    latest_score: float
    change_from_first: float
    trend: list[KpiTrendPoint]
