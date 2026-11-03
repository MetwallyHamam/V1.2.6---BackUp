from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

JobTitle = Literal["Fresh Technical Support", "Technical Support", "Junior Technical Support", "Senior Technical Support", "Team Leader", "Manager"]


class LoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=8, max_length=200)


class ForgotPasswordRequest(BaseModel):
    login: str = Field(min_length=1, max_length=320)


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str | None = None


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=32, max_length=500)
    new_password: str = Field(min_length=12, max_length=200)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    session_expires_at: datetime
    require_password_change: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=200)
    new_password: str = Field(min_length=12, max_length=200)

    @model_validator(mode="after")
    def passwords_must_differ(self) -> "PasswordChangeRequest":
        if self.current_password == self.new_password:
            raise ValueError("The new password must be different from the current password.")
        return self


class AdminPasswordReset(BaseModel):
    temporary_password: str = Field(min_length=12, max_length=200)
    reason: str = Field(min_length=5, max_length=500)


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    username: str = Field(pattern=r"^[A-Za-z0-9._@+-]+$", min_length=3, max_length=150)
    email: EmailStr
    support_notification_email: EmailStr | None = None
    password: str = Field(min_length=12, max_length=200)
    employee_code: str | None = Field(default=None, max_length=80)
    phone_number: str | None = Field(default=None, max_length=50)
    department: str | None = Field(default=None, max_length=150)
    department_id: int | None = None
    job_title: JobTitle | None = None
    hire_date: date | None = None
    profile_picture_url: str | None = Field(default=None, max_length=1000)
    reports_to_user_id: int | None = None
    user_type: str = "EMPLOYEE"
    primary_profile_id: int
    additional_profile_ids: list[int] = []
    client_scope_ids: list[int] = []
    client_scope_modes: dict[int, Literal["CLIENT_ONLY", "CLIENT_AND_DIRECT_CHILDREN", "CLIENT_AND_ALL_DESCENDANTS"]] = {}
    branch_scope_ids: list[int] = []
    is_active: bool = True
    participates_in_shifts: bool = True
    participates_in_operations: bool = True
    require_password_change: bool = True
    administrator_reason: str | None = None

    @field_validator("employee_code", "phone_number", "department", "job_title", "profile_picture_url", "support_notification_email", mode="before")
    @classmethod
    def blank_optional_values_are_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @model_validator(mode="after")
    def validate_portal_scope(self) -> "UserCreate":
        if self.user_type == "CLIENT_PORTAL" and (
            not self.client_scope_ids or not self.branch_scope_ids
        ):
            raise ValueError("Client Portal users require client and branch scope.")
        return self


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None
    support_notification_email: EmailStr | None = None
    employee_code: str | None = Field(default=None, max_length=80)
    phone_number: str | None = Field(default=None, max_length=50)
    department: str | None = Field(default=None, max_length=150)
    department_id: int | None = None
    job_title: JobTitle | None = None
    hire_date: date | None = None
    profile_picture_url: str | None = Field(default=None, max_length=1000)
    reports_to_user_id: int | None = None
    is_active: bool | None = None
    participates_in_shifts: bool | None = None
    participates_in_operations: bool | None = None
    require_password_change: bool | None = None

    @field_validator("employee_code", "phone_number", "department", "job_title", mode="before")
    @classmethod
    def blank_update_values_are_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value


class ProfileAssignment(BaseModel):
    profile_id: int
    is_primary: bool = False
    valid_to: datetime | None = None
    reason: str | None = Field(default=None, max_length=500)


class UserProfileAssignmentRead(BaseModel):
    id: int
    profile_id: int
    profile_code: str
    profile_name: str
    is_primary: bool
    valid_to: datetime | None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    username: str
    email: str
    support_notification_email: str | None
    employee_code: str | None
    phone_number: str | None
    department: str | None
    department_id: int | None
    job_title: str | None
    hire_date: date | None
    profile_picture_url: str | None
    reports_to_user_id: int | None
    user_type: str
    is_active: bool
    participates_in_shifts: bool
    participates_in_operations: bool
    require_password_change: bool
    last_login_at: datetime | None
    last_seen_at: datetime | None


class DepartmentCreate(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]+$", min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=150)
    name_ar: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    description_ar: str | None = Field(default=None, max_length=1000)
    is_active: bool = True
    parent_department_id: int | None = None
    head_user_id: int | None = None
    effective_from: date = Field(default_factory=date.today)
    effective_until: date | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    name_ar: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    description_ar: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None


class DepartmentRead(DepartmentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class DepartmentHierarchyAssignmentCreate(BaseModel):
    parent_department_id: int | None = None
    head_user_id: int | None = None
    effective_from: date
    effective_until: date | None = None
    change_reason: str | None = Field(default=None, min_length=3, max_length=500)


class DepartmentHierarchyPublishItem(DepartmentHierarchyAssignmentCreate):
    department_id: int


class DepartmentHierarchyPublishRequest(BaseModel):
    changes: list[DepartmentHierarchyPublishItem] = Field(min_length=1, max_length=200)


class UserDepartmentAssignmentCreate(BaseModel):
    department_id: int
    effective_from: date


class UserManagerAssignmentCreate(BaseModel):
    manager_user_id: int
    effective_from: date


class OrganizationChartNodeWrite(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    node_type: Literal["EXECUTIVE", "MANAGER", "TEAM", "TEAM_MEMBER", "ROLE"]
    title: str | None = Field(default=None, max_length=150)
    image_url: str | None = Field(default=None, max_length=1000)
    parent_id: int | None = None
    email: str | None = Field(default=None, max_length=320)
    phone_number: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=1000)
    sort_order: int = Field(default=0, ge=0, le=100000)
    is_active: bool = True


class OrganizationChartNodeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    node_type: Literal["EXECUTIVE", "MANAGER", "TEAM", "TEAM_MEMBER", "ROLE"] | None = None
    title: str | None = Field(default=None, max_length=150)
    image_url: str | None = Field(default=None, max_length=1000)
    parent_id: int | None = None
    email: str | None = Field(default=None, max_length=320)
    phone_number: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=1000)
    sort_order: int | None = Field(default=None, ge=0, le=100000)
    is_active: bool | None = None


class CurrentUserRead(UserRead):
    permissions: list[str]
    client_scope_ids: list[int]
    branch_scope_ids: list[int]
    default_page: str
    auto_close_on_resolve: bool
    default_dashboard_scope: str
    default_saved_view_id: int | None
    theme_mode: str
    theme_preset: str
    preferred_language: str


class ProfilePreferencesUpdate(BaseModel):
    default_page: Literal["home", "my-workspace", "dashboard", "top-management", "ticket-create", "tickets", "saved-views", "clients", "knowledge", "internal-operations", "portal"]
    default_dashboard_scope: Literal["GENERAL", "MY"]
    default_saved_view_id: int | None = None
    theme_mode: Literal["LIGHT", "DARK", "SYSTEM"] = "SYSTEM"
    theme_preset: Literal[
        "CLASSIC", "OCEAN", "FOREST", "SUNSET", "PLUM",
        "COBALT", "MIDNIGHT", "TERRACOTTA", "GRAPHITE", "NORDIC",
        "AURORA", "SAKURA", "NEON", "MOCHA", "ARCTIC", "OBSIDIAN_GOLD",
        "MILLENSYS",
    ] = "CLASSIC"
    profile_picture_url: str | None = Field(default=None, max_length=1000)
    preferred_language: Literal["en", "ar"] | None = None


class LanguagePreferenceUpdate(BaseModel):
    preferred_language: Literal["en", "ar"]


class ResolvePreferenceUpdate(BaseModel):
    auto_close_on_resolve: bool


class PermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    module: str
    description: str
    is_high_risk: bool


class ProfileCreate(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[A-Z0-9_-]+$", min_length=3, max_length=80)
    name: str = Field(min_length=3, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    profile_type: str
    permission_ids: list[int] = []
    default_dashboard_code: str = Field(default="dashboard", max_length=80)


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None
    default_dashboard_code: str | None = Field(default=None, max_length=80)


class ProfilePermissionsUpdate(BaseModel):
    permission_ids: list[int]
    reason: str = Field(min_length=5, max_length=500)


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    description: str | None
    profile_type: str
    is_system: bool
    is_active: bool
    risk_level: str
    default_dashboard_code: str | None
    effective_dashboard_source: str = "SYSTEM"
    effective_dashboard_id: int | None = None
    effective_dashboard_name: str | None = None


class EffectivePermissions(BaseModel):
    user_id: int
    permissions: list[str]
    client_scope_ids: list[int]
    branch_scope_ids: list[int]
