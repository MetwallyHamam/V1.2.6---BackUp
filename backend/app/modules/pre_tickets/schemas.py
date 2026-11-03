from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PreTicketCreate(BaseModel):
    client_id: int | None = None
    requester_contact_id: int | None = None
    product_id: int | None = None
    product_module_id: int | None = None
    service_id: int | None = None
    proposed_priority: Literal["P1", "P2", "P3", "P4"]
    title: str = Field(min_length=10, max_length=300)
    idempotency_key: str = Field(min_length=8, max_length=200)


class PreTicketClaim(BaseModel):
    expected_version: int = Field(ge=1)


class PreTicketConvert(BaseModel):
    expected_version: int = Field(ge=1)
    conversion_idempotency_key: str = Field(min_length=8, max_length=160)
    client_id: int | None = None
    branch_id: int | None = None
    requester_contact_id: int | None = None
    product_id: int | None = None
    product_module_id: int | None = None
    service_id: int | None = None


class PreTicketReasonAction(BaseModel):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=1000)


class PreTicketResponse(BaseModel):
    expected_version: int = Field(ge=1)
    response: str = Field(min_length=5, max_length=4000)


class PreTicketRead(BaseModel):
    id: int
    pre_ticket_number: str
    status: str
    request_kind: str
    source_provider: str | None
    external_event_id: str | None
    external_caller_name: str | None
    external_caller_number: str | None
    requested_ticket_type_code: str | None
    client_id: int | None
    branch_id: int | None
    requester_contact_id: int | None
    product_id: int | None
    product_module_id: int | None
    service_id: int | None
    proposed_priority: str
    title: str
    initial_description: str
    enriched_description: str | None
    submitted_by_user_id: int
    submitted_at: datetime
    claimed_by_user_id: int | None
    claimed_at: datetime | None
    information_request: str | None
    engineer_response: str | None
    terminal_reason: str | None
    converted_by_user_id: int | None
    converted_at: datetime | None
    resulting_ticket_id: int | None
    conversion_mode: str | None
    version: int

    model_config = {"from_attributes": True}


class PreTicketMetricsRead(BaseModel):
    total: int
    by_status: dict[str, int]
    average_minutes_to_claim: float | None
    average_minutes_claim_to_ticket: float | None
    average_minutes_to_ticket: float | None
    by_client: list["PreTicketMetricBucket"]
    by_product: list["PreTicketMetricBucket"]
    by_priority: list["PreTicketMetricBucket"]
    by_submitting_team: list["PreTicketMetricBucket"]
    aging_by_status: list["PreTicketMetricBucket"]


class PreTicketMetricBucket(BaseModel):
    key: str
    label: str
    count: int
    average_age_minutes: float


class PreTicketQueueViewCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    search_text: str | None = Field(default=None, max_length=100)
    status_filter: str | None = Field(default=None, max_length=30)


class PreTicketQueueViewRead(PreTicketQueueViewCreate):
    id: int
    model_config = {"from_attributes": True}
