from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApprovalCreate(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=200)
    source_channel: str = Field(max_length=30)
    reason_code: str = Field(max_length=60)
    requested_action: Literal["REQUIRE_APPROVAL", "CREATE_INACTIVE_CLIENT_TICKET", "OVERRIDE_COVERAGE", "OVERRIDE_CATALOG"] = "REQUIRE_APPROVAL"
    justification: str = Field(min_length=5, max_length=1000)
    request_payload: dict[str, object]
    evidence: dict[str, object]
    feature_mode: Literal["SHADOW", "ENFORCED"]
    policy_id: int | None = None
    policy_version: int = Field(ge=0)
    policy_scope: str = Field(max_length=200)
    client_id: int
    contract_id: int | None = None
    approval_group_id: int | None = None
    approval_deadline: datetime | None = None
    operation_scope: str | None = Field(default=None, max_length=250)


class ApprovalDecisionWrite(BaseModel):
    decision: Literal["APPROVED", "REJECTED", "CANCELLED"]
    comment: str = Field(min_length=3, max_length=1000)


class ApprovalConsumeWrite(BaseModel):
    operation_scope: str = Field(min_length=3, max_length=250)
    version: int = Field(ge=1)
    comment: str = Field(min_length=3, max_length=1000)


class ApprovalRevokeWrite(BaseModel):
    version: int = Field(ge=1)
    comment: str = Field(min_length=3, max_length=1000)


class ApprovalHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    from_status: str | None
    to_status: str
    actor_user_id: int
    comment: str | None
    created_at: datetime


class ApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    idempotency_key: str
    source_channel: str
    status: str
    reason_code: str
    requested_action: str
    justification: str
    feature_mode: str
    policy_id: int | None
    policy_version: int
    policy_scope: str
    client_id: int
    contract_id: int | None
    ticket_id: int | None
    approval_group_id: int | None
    requested_by_user_id: int
    decided_by_user_id: int | None
    decision_comment: str | None
    approval_deadline: datetime | None
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime
    operation_scope: str | None
    consumed_by_user_id: int | None
    consumed_at: datetime | None
    revoked_by_user_id: int | None
    revoked_at: datetime | None
    version: int
    request_payload: dict[str, object]
    evidence: dict[str, object]
    history: list[ApprovalHistoryRead]


class ApprovalGroupWrite(BaseModel):
    code: str | None = Field(default=None, pattern="^[A-Z][A-Z0-9_-]{1,79}$")
    name: str = Field(min_length=2, max_length=150)
    member_user_ids: list[int] = Field(default_factory=list)
    is_active: bool = True


class ApprovalGroupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    is_active: bool
    member_user_ids: list[int]
