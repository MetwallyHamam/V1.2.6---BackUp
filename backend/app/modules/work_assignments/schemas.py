from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.tickets.schemas import TicketCreate


class AssigneeWrite(BaseModel):
    user_id: int
    role: Literal["OWNER", "PRIMARY_EXECUTOR", "CONTRIBUTOR", "REVIEWER"] = "CONTRIBUTOR"
    contribution_percent: int = Field(default=0, ge=0, le=100)


class AssignmentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3, max_length=10000)
    assignment_type: Literal["GENERAL", "TICKET_FOLLOW_UP", "CLIENT_REQUEST", "SYSTEM_UPGRADE", "CHECKLIST", "REMOTE_ACTIVITY", "VISIT_CANDIDATE", "TICKET_CANDIDATE", "INTERNAL_OPERATION"] = "GENERAL"
    activity_classification: Literal["INTERNAL", "EXTERNAL", "MIXED", "NOT_APPLICABLE"] = "EXTERNAL"
    context: dict[str, str] = Field(default_factory=dict, max_length=20)
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    complexity: Literal["SIMPLE", "STANDARD", "COMPLEX", "CRITICAL"] = "STANDARD"
    department_id: int | None = None
    owner_user_id: int | None = None
    planned_start_at: datetime | None = None
    due_at: datetime | None = None
    estimated_minutes: int | None = Field(default=None, ge=1, le=100000)
    requires_review: bool = False
    assignees: list[AssigneeWrite] = Field(default_factory=list, max_length=100)
    client_ids: list[int] = Field(default_factory=list, max_length=500)
    related_ticket_ids: list[int] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def validate_dates_and_owner(self) -> "AssignmentCreate":
        if self.planned_start_at and self.due_at and self.due_at <= self.planned_start_at:
            raise ValueError("Due date must be after the planned start.")
        if self.owner_user_id and self.owner_user_id not in {row.user_id for row in self.assignees}:
            self.assignees.append(AssigneeWrite(user_id=self.owner_user_id, role="OWNER", contribution_percent=100))
        if len({row.user_id for row in self.assignees}) != len(self.assignees):
            raise ValueError("Each engineer can be assigned only once.")
        owners = [row for row in self.assignees if row.role == "OWNER"]
        if len(owners) > 1:
            raise ValueError("A task can have multiple engineers but only one accountable owner.")
        execution_credit = sum(row.contribution_percent for row in self.assignees if row.role != "REVIEWER")
        if self.assignees and execution_credit != 100:
            raise ValueError("Engineer execution contribution percentages must total 100.")
        return self


class AssignmentUpdate(AssignmentCreate):
    expected_version: int


class TransitionWrite(BaseModel):
    action: Literal["ACCEPT", "START", "BLOCK", "RESUME", "SUBMIT", "APPROVE", "RETURN", "COMPLETE", "CANCEL", "REOPEN"]
    expected_version: int
    detail: str | None = Field(default=None, max_length=1000)
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    actual_minutes: int | None = Field(default=None, ge=0, le=100000)


class ConversionWrite(BaseModel):
    target_type: Literal["TICKET", "VISIT", "INTERNAL_OPERATION"]
    target_id: int
    expected_version: int


class TicketConversionWrite(BaseModel):
    expected_version: int
    ticket: TicketCreate


class AssignmentRead(BaseModel):
    id: int
    title: str
    description: str
    assignment_type: str
    activity_classification: str
    status: str
    priority: str
    complexity: str
    department_id: int | None
    owner_user_id: int | None
    created_by_user_id: int
    planned_start_at: datetime | None
    due_at: datetime | None
    estimated_minutes: int | None
    actual_minutes: int | None
    progress_percent: int
    completion_summary: str | None
    kpi_source_type: str
    kpi_source_id: int | None
    requires_review: bool
    accepted_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime
    assignees: list[dict[str, object]]
    clients: list[dict[str, object]]
    links: list[dict[str, object]]
    evidence: list[dict[str, object]]
    context: dict[str, str]


class ShareCreate(BaseModel):
    expires_at: datetime | None = None


class ShareRead(BaseModel):
    url_token: str
    expires_at: datetime | None
