from datetime import datetime

from pydantic import BaseModel, Field


class CollaborationRequestCreate(BaseModel):
    task_id: int | None = None
    requesting_department_id: int
    requested_department_id: int
    request_type: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=3, max_length=4000)
    priority: str = "NORMAL"
    due_at: datetime | None = None


class CollaborationRequestResponse(BaseModel):
    decision: str
    owner_user_id: int | None = None
    notes: str | None = Field(default=None, max_length=4000)


class CollaborationEventCreate(BaseModel):
    task_id: int | None = None
    ticket_id: int | None = None
    event_type: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=2, max_length=200)
    summary: str = Field(min_length=3, max_length=4000)
    visibility: str = "PROJECT_PRIVATE"


class TicketProjectLinkCreate(BaseModel):
    ticket_id: int
    task_id: int | None = None
    link_type: str
    shared_summary: str = Field(min_length=3, max_length=4000)
