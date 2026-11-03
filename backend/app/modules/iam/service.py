import uuid
from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import server_now, server_timezone, server_today
from app.core.config import Settings
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.modules.clients.hierarchy import get_scope_ids
from app.modules.clients.models import Branch
from app.modules.iam.models import (
    AuthenticationEvent,
    Effect,
    Permission,
    Profile,
    ProfilePermission,
    RefreshToken,
    User,
    UserBranchScope,
    UserClientScope,
    UserPermissionOverride,
    UserProfile,
)
from app.modules.iam.schemas import EffectivePermissions, TokenPair, UserCreate
from app.modules.iam.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_login_password,
    verify_password,
)


def normalize(value: str) -> str:
    return value.strip().casefold()


def effective_permissions(db: Session, user: User, now: datetime | None = None) -> EffectivePermissions:
    now = now or server_now()
    if not user.is_active:
        return EffectivePermissions(user_id=user.id, permissions=[], client_scope_ids=[], branch_scope_ids=[])
    profile_codes = set(
        db.scalars(
            select(Permission.code)
            .join(ProfilePermission, ProfilePermission.permission_id == Permission.id)
            .join(Profile, Profile.id == ProfilePermission.profile_id)
            .join(UserProfile, UserProfile.profile_id == Profile.id)
            .where(
                UserProfile.user_id == user.id,
                UserProfile.is_active.in_([True]),
                UserProfile.valid_from <= now,
                or_(UserProfile.valid_to.is_(None), UserProfile.valid_to > now),
                Profile.is_active.in_([True]),
                Permission.is_active.in_([True]),
            )
        )
    )
    overrides = db.execute(
        select(UserPermissionOverride.effect, Permission.code)
        .join(Permission, Permission.id == UserPermissionOverride.permission_id)
        .where(
            UserPermissionOverride.user_id == user.id,
            UserPermissionOverride.valid_from <= now,
            or_(
                UserPermissionOverride.valid_to.is_(None),
                UserPermissionOverride.valid_to > now,
            ),
        )
    ).all()
    allowed = profile_codes | {code for effect, code in overrides if effect == Effect.ALLOW}
    denied = {code for effect, code in overrides if effect == Effect.DENY}
    branches = list(db.scalars(select(UserBranchScope.branch_id).where(UserBranchScope.user_id == user.id)))
    clients: set[int] = set()
    for row in db.scalars(select(UserClientScope).where(UserClientScope.user_id == user.id)):
        hierarchy_mode = {
            "CLIENT_ONLY": "SELF",
            "CLIENT_AND_DIRECT_CHILDREN": "DIRECT_CHILDREN",
            "CLIENT_AND_ALL_DESCENDANTS": "FULL_HIERARCHY",
        }.get(row.scope_mode, "SELF")
        clients.update(get_scope_ids(db, row.client_id, hierarchy_mode))
    # Older portal accounts can have a valid branch scope but be missing the
    # redundant client-scope row. Recover the owning client from the branch so
    # the portal catalog and ticket isolation remain usable and safely scoped.
    if branches:
        clients.update(
            db.scalars(select(Branch.client_id).where(Branch.id.in_(branches)))
        )
    return EffectivePermissions(
        user_id=user.id,
        permissions=sorted(allowed - denied),
        client_scope_ids=sorted(clients),
        branch_scope_ids=branches,
    )


def issue_tokens(db: Session, user: User, settings: Settings, family_id: str | None = None) -> TokenPair:
    raw_refresh = new_refresh_token()
    now = server_now()
    session_expiry = now + timedelta(days=settings.refresh_token_days)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            family_id=family_id or str(uuid.uuid4()),
            expires_at=session_expiry,
        )
    )
    return TokenPair(
        access_token=create_access_token(user.id, settings),
        refresh_token=raw_refresh,
        expires_in=settings.access_token_minutes * 60,
        session_expires_at=session_expiry,
        require_password_change=user.require_password_change,
    )


def login(db: Session, login_value: str, password: str, settings: Settings, ip: str | None) -> TokenPair:
    normalized = normalize(login_value)
    user = db.scalar(
        select(User).where(
            or_(User.username_normalized == normalized, User.email_normalized == normalized)
        )
    )
    now = server_now()
    if user and user.locked_until and user.locked_until.replace(tzinfo=server_timezone()) > now:
        raise AuthenticationError("ACCOUNT_LOCKED", "The account is temporarily locked.")
    if not user or not verify_login_password(password, user.password_hash, settings):
        if user:
            user.failed_login_count += 1
            if user.failed_login_count >= settings.login_max_failures:
                user.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
        db.add(
            AuthenticationEvent(
                user_id=user.id if user else None,
                username_attempted=login_value[:320],
                event_type="LOGIN_FAILED",
                ip_address=ip,
            )
        )
        db.commit()
        raise AuthenticationError()
    if not user.is_active:
        db.add(AuthenticationEvent(user_id=user.id, event_type="LOGIN_INACTIVE", ip_address=ip))
        db.commit()
        raise AuthenticationError("ACCOUNT_INACTIVE", "The account is inactive.")
    if user.user_type == "API_USER":
        db.add(AuthenticationEvent(user_id=user.id, event_type="INTERACTIVE_LOGIN_REJECTED", ip_address=ip))
        db.commit()
        raise AuthenticationError(
            "INTERACTIVE_LOGIN_DISABLED",
            "API users must use the integration token endpoint.",
        )
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    pair = issue_tokens(db, user, settings)
    db.add(AuthenticationEvent(user_id=user.id, event_type="LOGIN_SUCCEEDED", ip_address=ip))
    db.commit()
    return pair


def rotate_refresh(db: Session, raw_token: str, settings: Settings, ip: str | None = None) -> TokenPair:
    token_hash = hash_refresh_token(raw_token)
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    now = server_now()
    if not stored:
        db.add(AuthenticationEvent(event_type="REFRESH_REJECTED_INVALID", ip_address=ip)); db.commit()
        raise AuthenticationError("INVALID_REFRESH_TOKEN", "The refresh token is invalid.")
    if stored.revoked_at is not None:
        db.query(RefreshToken).filter(RefreshToken.family_id == stored.family_id).update(
            {RefreshToken.revoked_at: now}
        )
        db.add(AuthenticationEvent(user_id=stored.user_id,event_type="REFRESH_REJECTED_REVOKED",ip_address=ip,detail="Token family revoked after reuse detection.")); db.commit()
        raise AuthenticationError("REFRESH_TOKEN_REUSE", "Refresh token reuse was detected.")
    if stored.expires_at.replace(tzinfo=server_timezone()) <= now:
        db.add(AuthenticationEvent(user_id=stored.user_id,event_type="REFRESH_REJECTED_EXPIRED",ip_address=ip)); db.commit()
        raise AuthenticationError("REFRESH_TOKEN_EXPIRED", "The refresh token has expired.")
    user = db.get(User, stored.user_id)
    if not user or not user.is_active:
        db.add(AuthenticationEvent(user_id=stored.user_id,event_type="REFRESH_REJECTED_ACCOUNT_INACTIVE",ip_address=ip)); db.commit()
        raise AuthenticationError("ACCOUNT_INACTIVE", "The account is inactive.")
    pair = issue_tokens(db, user, settings, stored.family_id)
    stored.revoked_at = now
    stored.replaced_by_hash = hash_refresh_token(pair.refresh_token)
    db.add(AuthenticationEvent(user_id=user.id,event_type="REFRESH_SUCCEEDED",ip_address=ip))
    db.commit()
    return pair


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise AuthenticationError("CURRENT_PASSWORD_INVALID", "The current password is incorrect.")
    if verify_password(new_password, user.password_hash):
        raise ConflictError("PASSWORD_REUSE", "The new password must be different.")
    now = server_now()
    user.password_hash = hash_password(new_password)
    user.password_changed_at = now
    user.require_password_change = False
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked_at.is_(None),
    ).update({RefreshToken.revoked_at: now})
    db.add(AuthenticationEvent(user_id=user.id, event_type="PASSWORD_CHANGED"))
    db.commit()


def create_user(db: Session, data: UserCreate, actor_id: int) -> User:
    from app.modules.configuration.models import SiteSetting
    from app.modules.iam.models import Department
    username_normalized = normalize(data.username)
    email_normalized = normalize(str(data.email))
    if db.scalar(select(User.id).where(User.username_normalized == username_normalized)):
        raise ConflictError("DUPLICATE_USERNAME", "That username is already in use.")
    if db.scalar(select(User.id).where(User.email_normalized == email_normalized)):
        raise ConflictError("DUPLICATE_EMAIL", "That email is already in use.")
    if data.employee_code and db.scalar(
        select(User.id).where(User.employee_code == data.employee_code)
    ):
        raise ConflictError(
            "DUPLICATE_EMPLOYEE_CODE", "That employee code is already in use."
        )
    if data.reports_to_user_id is not None:
        manager = db.get(User, data.reports_to_user_id)
        if not manager or not manager.is_active or manager.user_type != "EMPLOYEE":
            raise ConflictError("INVALID_REPORTS_TO", "Reports To must be an active employee.")
    department = db.get(Department, data.department_id) if data.department_id else None
    if data.department_id and (not department or not department.is_active):
        raise ConflictError("INVALID_DEPARTMENT", "Select an active department from master data.")
    profile_ids = [data.primary_profile_id, *data.additional_profile_ids]
    profiles = list(db.scalars(select(Profile).where(Profile.id.in_(profile_ids))))
    if len({p.id for p in profiles}) != len(set(profile_ids)):
        raise NotFoundError("One or more profiles do not exist.")
    if data.user_type == "CLIENT_PORTAL" and any(p.profile_type != "CLIENT_PORTAL" for p in profiles):
        raise ConflictError("PROFILE_TYPE_MISMATCH", "Portal users may only receive portal profiles.")
    if data.user_type == "EMPLOYEE" and any(p.profile_type == "CLIENT_PORTAL" for p in profiles):
        raise ConflictError("PROFILE_TYPE_MISMATCH", "Employees may not receive portal profiles.")
    if data.user_type == "API_USER" and any(p.profile_type != "API_INTEGRATION" for p in profiles):
        raise ConflictError("PROFILE_TYPE_MISMATCH", "API users require API Integration profiles.")
    if data.user_type != "API_USER" and any(p.profile_type == "API_INTEGRATION" for p in profiles):
        raise ConflictError("PROFILE_TYPE_MISMATCH", "API Integration profiles can only be assigned to API users.")
    if any(p.code == "ADMINISTRATOR" for p in profiles) and not data.administrator_reason:
        raise ConflictError("ADMIN_REASON_REQUIRED", "Administrator assignment requires a reason.")
    default_theme = db.get(SiteSetting, "default_theme")
    user = User(
        full_name=data.full_name,
        username=data.username,
        username_normalized=username_normalized,
        email=str(data.email),
        email_normalized=email_normalized,
        support_notification_email=str(data.support_notification_email) if data.support_notification_email else None,
        password_hash=hash_password(data.password),
        employee_code=(data.employee_code or f"PENDING-EMP-{server_now().timestamp()}") if data.user_type == "EMPLOYEE" else None,
        phone_number=data.phone_number,
        department=department.name if department else data.department,
        department_id=data.department_id,
        job_title=data.job_title,
        hire_date=data.hire_date,
        profile_picture_url=data.profile_picture_url,
        reports_to_user_id=data.reports_to_user_id,
        user_type=data.user_type,
        is_active=data.is_active,
        participates_in_shifts=data.participates_in_shifts,
        participates_in_operations=data.participates_in_operations,
        require_password_change=data.require_password_change,
        theme_mode=default_theme.value if default_theme else "SYSTEM",
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "DUPLICATE_USER_VALUE",
            "The username, email, or employee code is already in use.",
        ) from exc
    if data.user_type == "EMPLOYEE" and not data.employee_code:
        user.employee_code = f"EMP-{user.id:06d}"
    if data.user_type == "EMPLOYEE":
        from app.modules.iam.organization import assign_user_department, assign_user_manager

        if data.department_id is not None:
            assign_user_department(db, user.id, data.department_id, server_today(), actor_id)
        if data.reports_to_user_id is not None:
            assign_user_manager(db, user.id, data.reports_to_user_id, server_today(), actor_id)
    for profile_id in dict.fromkeys(profile_ids):
        db.add(
            UserProfile(
                user_id=user.id,
                profile_id=profile_id,
                is_primary=profile_id == data.primary_profile_id,
                assigned_by_user_id=actor_id,
                assignment_reason=data.administrator_reason,
            )
        )
    db.add_all(
        UserClientScope(user_id=user.id, client_id=x, scope_mode=data.client_scope_modes.get(x, "CLIENT_ONLY"))
        for x in set(data.client_scope_ids)
    )
    db.add_all(UserBranchScope(user_id=user.id, branch_id=x) for x in set(data.branch_scope_ids))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "DUPLICATE_USER_VALUE",
            "The username, email, or employee code is already in use.",
        ) from exc
    db.refresh(user)
    return user
