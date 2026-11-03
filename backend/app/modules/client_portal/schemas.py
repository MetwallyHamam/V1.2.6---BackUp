from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PortalTicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_number: str
    ticket_type_id: int
    client_id: int
    branch_id: int | None
    product_id: int | None
    product_module_id: int | None
    service_id: int | None
    status_id: int
    entitlement_status: str | None
    priority: str
    subject: str
    description: str
    resolution_summary: str | None
    created_at: datetime
    updated_at: datetime
    version: int
    sla_first_response_target_minutes: int | None = None
    sla_first_response_actual_minutes: int | None = None
    sla_resolution_target_minutes: int | None = None
    sla_actual_business_minutes: int | None = None
    sla_saved_minutes: int | None = None
    sla_overrun_minutes: int | None = None
    sla_resolution_state: str | None = None


class PortalResolutionAction(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
    version: int


class PortalAnnouncement(BaseModel):
    id: str
    severity: str
    title: str
    message: str
