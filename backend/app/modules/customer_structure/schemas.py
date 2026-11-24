from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AccountCreate(BaseModel):
    code: str = Field(pattern=r"^[A-Za-z0-9_-]+$", min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    owner_department_id: int | None = None
    is_active: bool = True


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    owner_department_id: int | None = None
    is_active: bool | None = None


class AccountRead(OrmModel):
    id: int
    code: str
    name: str
    description: str | None
    owner_department_id: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    organization_count: int = 0


class OrganizationCreate(BaseModel):
    account_id: int
    code: str = Field(pattern=r"^[A-Za-z0-9_-]+$", min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=200)
    legal_name: str | None = Field(default=None, max_length=250)
    description: str | None = Field(default=None, max_length=4000)
    owner_department_id: int | None = None
    is_active: bool = True


class OrganizationUpdate(BaseModel):
    account_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=200)
    legal_name: str | None = Field(default=None, max_length=250)
    description: str | None = Field(default=None, max_length=4000)
    owner_department_id: int | None = None
    is_active: bool | None = None


class OrganizationRead(OrmModel):
    id: int
    account_id: int
    code: str
    name: str
    legal_name: str | None
    description: str | None
    owner_department_id: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    client_count: int = 0


class OrganizationClientBulkAssign(BaseModel):
    client_ids: list[int] = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=5, max_length=500)


class OrganizationClientBulkAssignResult(BaseModel):
    organization_id: int
    updated_count: int
    unchanged_count: int
    client_ids: list[int]


PolicyMode = Literal["INHERIT", "EXTEND", "OVERRIDE"]
AssignmentRelationship = Literal[
    "PRIMARY_OWNER", "SHARED_OPERATOR", "VIEWER", "TEMPORARY_OPERATOR"
]
AccessProfile = Literal[
    "CUSTOMER_VIEWER",
    "PROJECT_OPERATOR",
    "IMPLEMENTATION_OPERATOR",
    "SUPPORT_OPERATOR",
    "CUSTOMER_MANAGER",
    "PORTFOLIO_MANAGER",
]


class DepartmentAssignmentWrite(BaseModel):
    department_id: int
    relationship: AssignmentRelationship
    access_profile: AccessProfile
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    reason: str | None = Field(default=None, max_length=500)


class DepartmentPolicyWrite(BaseModel):
    mode: PolicyMode
    assignments: list[DepartmentAssignmentWrite] = Field(default_factory=list, max_length=100)
    change_reason: str = Field(min_length=5, max_length=500)


class EffectiveDepartmentAccessRead(BaseModel):
    department_id: int
    department_name: str
    relationship: str
    access_profile: str
    source_type: str
    source_id: int
    inherited: bool
    visibility_only: bool
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    reason: str | None = None


class DepartmentPolicyRead(BaseModel):
    scope_type: str
    scope_id: int
    mode: str
    effective_at: datetime
    assignments: list[EffectiveDepartmentAccessRead]
    direct_assignments: list[EffectiveDepartmentAccessRead]


class DepartmentPolicyImpactRead(BaseModel):
    scope_type: str
    scope_id: int
    affected_client_count: int
    affected_branch_count: int
    current_department_ids: list[int]
    proposed_department_ids: list[int]
    added_department_ids: list[int]
    retained_visibility_department_ids: list[int]
