from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Unicode,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class UserType(StrEnum):
    EMPLOYEE = "EMPLOYEE"
    CLIENT_PORTAL = "CLIENT_PORTAL"
    API_USER = "API_USER"


class Effect(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    name_ar: Mapped[str | None] = mapped_column(Unicode(150))
    description: Mapped[str | None] = mapped_column(String(1000))
    description_ar: Mapped[str | None] = mapped_column(Unicode(1000))
    parent_department_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("departments.id"))
    head_user_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("users.id", name="fk_departments_head_user", use_alter=True)
    )
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_until: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username_normalized"),
        UniqueConstraint("email_normalized"),
        Index(
            "ux_users_employee_code_not_null",
            "employee_code",
            unique=True,
            mssql_where=text("employee_code IS NOT NULL"),
            sqlite_where=text("employee_code IS NOT NULL"),
        ),
        Index("ix_users_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(200))
    username: Mapped[str] = mapped_column(String(150))
    username_normalized: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(320))
    email_normalized: Mapped[str] = mapped_column(String(320))
    support_notification_email: Mapped[str | None] = mapped_column(String(320))
    employee_code: Mapped[str | None] = mapped_column(String(80))
    phone_number: Mapped[str | None] = mapped_column(String(50))
    department: Mapped[str | None] = mapped_column(String(150))
    department_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("departments.id"))
    job_title: Mapped[str | None] = mapped_column(String(150))
    profile_picture_url: Mapped[str | None] = mapped_column(String(1000))
    hire_date: Mapped[date | None] = mapped_column(Date)
    reports_to_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    user_type: Mapped[str] = mapped_column(String(30), default=UserType.EMPLOYEE)
    password_hash: Mapped[str] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    participates_in_shifts: Mapped[bool] = mapped_column(Boolean, default=True)
    participates_in_operations: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    require_password_change: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_close_on_resolve: Mapped[bool] = mapped_column(Boolean, default=False)
    default_page: Mapped[str | None] = mapped_column(String(80), default="home")
    default_dashboard_scope: Mapped[str] = mapped_column(String(20), default="GENERAL")
    default_saved_view_id: Mapped[int | None] = mapped_column(IdType)
    theme_mode: Mapped[str] = mapped_column(String(20), default="SYSTEM")
    theme_preset: Mapped[str] = mapped_column(String(20), default="CLASSIC")
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    profiles: Mapped[list["UserProfile"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", foreign_keys="UserProfile.user_id"
    )
    overrides: Mapped[list["UserPermissionOverride"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="UserPermissionOverride.user_id",
    )


class DepartmentMembership(Base):
    __tablename__ = "department_memberships"
    __table_args__ = (
        Index("ix_department_membership_user_dates", "user_id", "effective_from", "effective_until"),
        Index("ix_department_membership_department_dates", "department_id", "effective_from", "effective_until"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    department_id: Mapped[int] = mapped_column(IdType, ForeignKey("departments.id"))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_until: Mapped[date | None] = mapped_column(Date)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DepartmentHierarchyAssignment(Base):
    __tablename__ = "department_hierarchy_assignments"
    __table_args__ = (
        Index("ix_department_hierarchy_dates", "department_id", "effective_from", "effective_until"),
        Index("ix_department_hierarchy_parent_dates", "parent_department_id", "effective_from", "effective_until"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    department_id: Mapped[int] = mapped_column(IdType, ForeignKey("departments.id", ondelete="CASCADE"))
    parent_department_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("departments.id"))
    head_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_until: Mapped[date | None] = mapped_column(Date)
    created_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UserReportingLine(Base):
    __tablename__ = "user_reporting_lines"
    __table_args__ = (
        Index("ix_user_reporting_line_user_dates", "user_id", "effective_from", "effective_until"),
        Index("ix_user_reporting_line_manager_dates", "manager_user_id", "effective_from", "effective_until"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    manager_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_until: Mapped[date | None] = mapped_column(Date)
    created_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class OrganizationChartNode(Base):
    __tablename__ = "organization_chart_nodes"
    __table_args__ = (
        Index("ix_organization_chart_parent", "parent_id", "sort_order"),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_organization_chart_not_self"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("organization_chart_nodes.id"))
    name: Mapped[str] = mapped_column(Unicode(200))
    node_type: Mapped[str] = mapped_column(String(30))
    title: Mapped[str | None] = mapped_column(Unicode(150))
    image_url: Mapped[str | None] = mapped_column(String(1000))
    email: Mapped[str | None] = mapped_column(String(320))
    phone_number: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Unicode(1000))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        Index("ix_password_reset_token_hash", "token_hash", unique=True),
        Index("ix_password_reset_user_expiry", "user_id", "expires_at"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint("profile_type IN ('EMPLOYEE','CLIENT_PORTAL','ADMINISTRATOR','API_INTEGRATION')"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(String(1000))
    profile_type: Mapped[str] = mapped_column(String(30))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="STANDARD")
    default_dashboard_code: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    permissions: Mapped[list["ProfilePermission"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(150), unique=True)
    module: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(500))
    is_high_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ProfilePermission(Base):
    __tablename__ = "profile_permissions"

    profile_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )
    scope_type: Mapped[str] = mapped_column(String(30), default="NONE")
    profile: Mapped[Profile] = relationship(back_populates="permissions")
    permission: Mapped[Permission] = relationship()


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "profile_id"),
        CheckConstraint("valid_to IS NULL OR valid_to > valid_from"),
        Index("ix_user_profiles_effective", "user_id", "is_active", "valid_from", "valid_to"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    profile_id: Mapped[int] = mapped_column(IdType, ForeignKey("profiles.id"))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assigned_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    assignment_reason: Mapped[str | None] = mapped_column(String(500))
    user: Mapped[User] = relationship(back_populates="profiles", foreign_keys=[user_id])
    profile: Mapped[Profile] = relationship()


class UserPermissionOverride(Base):
    __tablename__ = "user_permission_overrides"
    __table_args__ = (
        CheckConstraint("effect IN ('ALLOW','DENY')"),
        CheckConstraint("valid_to IS NULL OR valid_to > valid_from"),
        Index("ix_overrides_effective", "user_id", "permission_id", "valid_from", "valid_to"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    permission_id: Mapped[int] = mapped_column(IdType, ForeignKey("permissions.id"))
    effect: Mapped[str] = mapped_column(String(10))
    scope_type: Mapped[str] = mapped_column(String(30), default="NONE")
    scope_reference_id: Mapped[int | None] = mapped_column(IdType)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(String(500))
    approved_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    created_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    user: Mapped[User] = relationship(back_populates="overrides", foreign_keys=[user_id])
    permission: Mapped[Permission] = relationship()


class AccessRequest(Base):
    __tablename__ = "access_requests"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING','APPROVED','DENIED','CANCELLED','EXPIRED')"),
        Index("ix_access_requests_requester_status", "requester_user_id", "status"),
        Index("ix_access_requests_permission_status", "permission_id", "status"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    requester_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    permission_id: Mapped[int] = mapped_column(IdType, ForeignKey("permissions.id"))
    resource: Mapped[str] = mapped_column(String(300))
    return_path: Mapped[str | None] = mapped_column(String(500))
    justification: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    permission: Mapped[Permission] = relationship()


class AccessRequestDecision(Base):
    __tablename__ = "access_request_decisions"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    access_request_id: Mapped[int] = mapped_column(IdType, ForeignKey("access_requests.id"))
    actor_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(String(1000))
    grant_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PermissionStepUpChallenge(Base):
    __tablename__ = "permission_step_up_challenges"
    __table_args__ = (Index("ix_permission_step_up_actor_expiry", "actor_user_id", "expires_at"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UserClientScope(Base):
    __tablename__ = "user_client_scopes"
    user_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    client_id: Mapped[int] = mapped_column(IdType, primary_key=True)
    scope_mode: Mapped[str] = mapped_column(String(40), default="CLIENT_ONLY")


class UserBranchScope(Base):
    __tablename__ = "user_branch_scopes"
    user_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    branch_id: Mapped[int] = mapped_column(IdType, primary_key=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("ix_refresh_family", "family_id"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    family_id: Mapped[str] = mapped_column(String(36))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuthenticationEvent(Base):
    __tablename__ = "authentication_events"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    username_attempted: Mapped[str | None] = mapped_column(String(320))
    event_type: Mapped[str] = mapped_column(String(80))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100))
    reason: Mapped[str | None] = mapped_column(String(500))
    correlation_id: Mapped[str | None] = mapped_column(String(36))
    old_values_json: Mapped[str | None] = mapped_column(Text)
    new_values_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
