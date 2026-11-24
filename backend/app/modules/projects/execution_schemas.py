from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator


class AssigneeWrite(BaseModel):
    user_id: int
    allocation_percent: int = Field(default=100, ge=1, le=100)
    planned_minutes: int = Field(default=0, ge=0)
    is_accountable: bool = False


class TaskCreate(BaseModel):
    task_number: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=250)
    description: str | None = None
    phase_id: int | None = None
    priority: str = "NORMAL"
    owner_user_id: int
    planned_start_date: date | None = None
    planned_end_date: date | None = None
    estimate_minutes: int = Field(default=0, ge=0)
    weight: int = Field(default=1, ge=1, le=100)
    baseline_reference: str | None = Field(default=None, max_length=150)
    assignees: list[AssigneeWrite] = []
    dependency_ids: list[int] = []

    @model_validator(mode="after")
    def validate_plan(self) -> "TaskCreate":
        if (
            self.planned_start_date
            and self.planned_end_date
            and self.planned_end_date < self.planned_start_date
        ):
            raise ValueError("Planned end date cannot precede planned start date.")
        if len({item.user_id for item in self.assignees}) != len(self.assignees):
            raise ValueError("Each engineer can be assigned only once.")
        return self


class UnplannedTaskCreate(TaskCreate):
    unplanned_cause: str = Field(min_length=3, max_length=500)
    unplanned_source: str = Field(min_length=2, max_length=80)
    impact_summary: str = Field(min_length=3, max_length=4000)
    schedule_impact_minutes: int = Field(ge=0)


class TaskActionWrite(BaseModel):
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    summary: str | None = Field(default=None, max_length=4000)


class ApprovalWrite(BaseModel):
    decision: str
    notes: str | None = Field(default=None, max_length=4000)


class WorkLogWrite(BaseModel):
    started_at: datetime
    ended_at: datetime
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_times(self) -> "WorkLogWrite":
        if self.ended_at <= self.started_at:
            raise ValueError("Work log end must be after its start.")
        return self


class BlockerWrite(BaseModel):
    category: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=3, max_length=4000)
    owner_user_id: int
    impact: str = Field(min_length=3, max_length=4000)
    next_review_at: datetime


class EvidenceWrite(BaseModel):
    evidence_type: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=2, max_length=200)
    reference_url: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=4000)
    visibility: str = "PROJECT_PRIVATE"


class ReviewWrite(BaseModel):
    decision: str
    notes: str | None = Field(default=None, max_length=4000)
