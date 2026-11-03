from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class ProductLine(BaseModel):
    product_id: int
    product_module_id: int | None = None
    service_id: int | None = None
    delivery_status: Literal["DELIVERED", "PENDING", "HOLD"]
    delivered_version: str | None = Field(default=None, max_length=100)
    delivery_percent: float | None = Field(default=None, ge=0, le=100)
    delivery_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class PendingPointLine(BaseModel):
    product_id: int
    product_module_id: int | None = None
    service_id: int | None = None
    description: str = Field(min_length=2, max_length=2000)
    status: Literal["OPEN", "RESOLVED"] = "OPEN"


class SourceTemplateLine(BaseModel):
    template_id: int
    template_version: int = Field(ge=1)


class HandoverCreate(BaseModel):
    project_number: str | None = Field(default=None, min_length=2, max_length=50)
    project_name: str = Field(min_length=3, max_length=200)
    client_id: int
    source_template_id: int | None = None
    source_template_version: int | None = None
    source_templates: list[SourceTemplateLine] = Field(default_factory=list, max_length=20)
    recipient_user_ids: list[int] = Field(default_factory=list, max_length=50)
    project_manager_id: int | None = None
    project_manager_user_id: int | None = None
    project_manager_name: str | None = Field(default=None, max_length=200)
    project_manager_email: str | None = Field(default=None, max_length=320)
    project_manager_phone: str | None = Field(default=None, max_length=50)
    warranty_months: int | None = Field(default=None, ge=0, le=120)
    warranty_start_date: date | None = None
    acceptance_date: date | None = None
    pending_points: str | None = Field(default=None, max_length=10000)
    current_status: Literal["DRAFT", "READY", "DELIVERED", "ACCEPTED", "ON_HOLD"] = "DRAFT"
    notes: str | None = Field(default=None, max_length=10000)
    products: list[ProductLine] = Field(default_factory=list, max_length=100)
    structured_pending_points: list[PendingPointLine] = Field(default_factory=list, max_length=200)


class HandoverUpdate(HandoverCreate):
    project_number: None = None


class ProjectManagerWrite(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone_number: str | None = Field(default=None, max_length=50)
    organization: str | None = Field(default=None, max_length=200)


class ProjectManagerRead(ProjectManagerWrite):
    id: int
    is_active: bool


class CommentCreate(BaseModel):
    body: str = Field(min_length=2, max_length=10000)


class HandoverRead(BaseModel):
    id: int
    project_number: str
    project_name: str
    client_id: int
    client_name: str
    source_template_id: int | None
    source_template_version: int | None
    source_templates: list[dict[str, object]]
    delivered_by_user_id: int
    delivered_by_name: str
    project_manager_user_id: int | None
    project_manager_id: int | None
    project_manager_name: str | None
    project_manager_email: str | None
    project_manager_phone: str | None
    warranty_months: int | None
    warranty_start_date: date | None
    acceptance_date: date | None
    pending_points: str | None
    current_status: str
    notes: str | None
    created_at: datetime
    recipients: list[dict[str, object]]
    products: list[dict[str, object]]
    structured_pending_points: list[dict[str, object]]
    comments: list[dict[str, object]]
    documents: list[dict[str, object]]
