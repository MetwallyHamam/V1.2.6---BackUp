from datetime import datetime

from pydantic import BaseModel, Field


class FlagWrite(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    name_ar: str | None = Field(default=None, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    color: str = Field(default="#607D8B", pattern=r"^#[0-9A-Fa-f]{6}$")
    pauses_sla: bool = False
    is_active: bool = True
    sort_order: int = Field(default=100, ge=0, le=10000)


class FlagRead(FlagWrite):
    id: int
    code: str
    model_config = {"from_attributes": True}


class FlagApply(BaseModel):
    flag_id: int
    reason: str = Field(min_length=3, max_length=1000)


class FlagRemove(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class AssignmentRead(BaseModel):
    id: int
    ticket_id: int
    flag_id: int
    code: str
    name: str
    color: str
    pauses_sla: bool
    apply_reason: str
    applied_by_name: str
    applied_at: datetime
    removed_by_name: str | None = None
    removed_at: datetime | None = None
    removal_reason: str | None = None

