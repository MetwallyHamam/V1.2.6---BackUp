import json
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import authenticated_user, require_permission
from app.core.clock import server_now, server_timezone, server_today
from app.core.config import Settings, get_settings
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.dashboards.models import SavedView
from app.modules.iam.models import (
    AuditLog,
    AuthenticationEvent,
    Department,
    DepartmentHierarchyAssignment,
    DepartmentMembership,
    OrganizationChartNode,
    PasswordResetToken,
    Permission,
    Profile,
    ProfilePermission,
    RefreshToken,
    User,
    UserPermissionOverride,
    UserProfile,
    UserReportingLine,
)
from app.modules.iam.organization import (
    active_on,
    add_department_assignment,
    assign_user_department,
    assign_user_manager,
    department_assignment,
    department_descendant_ids,
    department_path,
)
from app.modules.iam.schemas import (
    AdminPasswordReset,
    CurrentUserRead,
    DepartmentCreate,
    DepartmentHierarchyAssignmentCreate,
    DepartmentHierarchyPublishRequest,
    DepartmentRead,
    DepartmentUpdate,
    EffectivePermissions,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LanguagePreferenceUpdate,
    LoginRequest,
    LogoutRequest,
    OrganizationChartNodeUpdate,
    OrganizationChartNodeWrite,
    PasswordChangeRequest,
    PasswordResetConfirm,
    PermissionRead,
    ProfileAssignment,
    ProfileCreate,
    ProfilePermissionsUpdate,
    ProfilePreferencesUpdate,
    ProfileRead,
    ProfileUpdate,
    RefreshRequest,
    ResolvePreferenceUpdate,
    TokenPair,
    UserCreate,
    UserDepartmentAssignmentCreate,
    UserManagerAssignmentCreate,
    UserProfileAssignmentRead,
    UserRead,
    UserUpdate,
)
from app.modules.iam.security import hash_password, hash_refresh_token, verify_password
from app.modules.iam.service import (
    change_password,
    create_user,
    effective_permissions,
    login,
    rotate_refresh,
)
from app.modules.notifications.email_service import process_email_outbox
from app.modules.notifications.models import EventOutbox

auth_router = APIRouter(prefix="/auth", tags=["authentication"])
users_router = APIRouter(prefix="/users", tags=["users"])
departments_router = APIRouter(prefix="/departments", tags=["departments"])
profiles_router = APIRouter(prefix="/profiles", tags=["profiles"])
permissions_router = APIRouter(prefix="/permissions", tags=["permissions"])


@departments_router.get("", response_model=list[DepartmentRead])
def list_departments(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(authenticated_user),
) -> list[Department]:
    statement = select(Department)
    if not include_inactive:
        statement = statement.where(Department.is_active.in_([True]))
    return list(db.scalars(statement.order_by(Department.name)))


@departments_router.post("", response_model=DepartmentRead, status_code=201)
def create_department(
    data: DepartmentCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("user.manage")),
) -> Department:
    hierarchy = data.model_dump(include={"parent_department_id", "head_user_id", "effective_from", "effective_until"})
    values = data.model_dump(exclude={"parent_department_id", "head_user_id", "effective_from", "effective_until"})
    requested_code = values.pop("code", None)
    item = Department(
        code=requested_code or f"PENDING-DEP-{server_now().timestamp()}",
        **values,
        effective_from=data.effective_from,
        effective_until=data.effective_until,
    )
    db.add(item)
    try:
        db.flush()
        if not requested_code:
            item.code = f"DEP-{item.id:06d}"
        add_department_assignment(db, item.id, actor_id=actor.id, **hierarchy)
        queue_presets = (
            ("Escalations Received", {"my_department_requests": "true", "department_requests_only": "true"}),
            ("New Department Requests", {"my_department_requests": "true", "department_requests_only": "true", "routing_status": "NEW"}),
            ("Department Work In Progress", {"my_department_requests": "true", "department_requests_only": "true", "routing_status": "IN_PROGRESS"}),
            ("Escalations Sent", {"escalations_sent_only": "true"}),
            ("Resolved / Returned", {"my_department_requests": "true", "department_requests_only": "true", "routing_status": "RETURNED"}),
        )
        for queue_name, filters in queue_presets:
            db.add(SavedView(
                owner_user_id=actor.id,
                department_id=item.id,
                name=f"{item.name} — {queue_name}",
                scope="DEPARTMENT",
                filter_json=json.dumps(filters),
                columns_json="[]",
                sort_json='[{"field":"updated_at","direction":"desc"}]',
                is_active=True,
            ))
        db.add(AuditLog(actor_user_id=actor.id, entity_type="Department", entity_id=str(item.id), action="department.created", new_values_json=json.dumps(data.model_dump(mode="json"))))
        db.add(AuditLog(actor_user_id=actor.id, entity_type="Department", entity_id=str(item.id), action="department.collaboration.provisioned", new_values_json=json.dumps({"saved_view_count": len(queue_presets), "permission_model": "GENERIC_DEPARTMENT_SCOPE"})))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("DUPLICATE_DEPARTMENT", "That department code or name already exists.") from exc
    db.refresh(item)
    return item


@departments_router.patch("/{department_id}", response_model=DepartmentRead)
def update_department(
    department_id: int,
    data: DepartmentUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("user.manage")),
) -> Department:
    item = db.get(Department, department_id)
    if not item:
        raise NotFoundError("Department does not exist.")
    old_name = item.name
    before = {"name": item.name, "description": item.description, "is_active": item.is_active}
    if data.is_active is False and item.is_active:
        active_children = department_descendant_ids(db, item.id, server_today())
        active_members = db.scalar(select(User.id).where(User.department_id == item.id, User.is_active.in_([True])).limit(1))
        if active_children or active_members is not None:
            raise ConflictError("DEPARTMENT_IN_USE", "Move active child departments and employees before deactivating this department.")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    if item.name != old_name:
        db.query(User).filter(User.department_id == item.id).update({User.department: item.name})
    db.add(AuditLog(actor_user_id=actor.id, entity_type="Department", entity_id=str(item.id), action="department.updated", old_values_json=json.dumps(before), new_values_json=json.dumps(data.model_dump(exclude_unset=True))))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("DUPLICATE_DEPARTMENT", "That department name already exists.") from exc
    db.refresh(item)
    return item


def _department_hierarchy_read(db: Session, item: Department, as_of: date) -> dict[str, object]:
    assignment = department_assignment(db, item.id, as_of)
    head = db.get(User, assignment.head_user_id) if assignment and assignment.head_user_id else None
    headcount = db.scalar(
        select(func.count(func.distinct(DepartmentMembership.user_id))).where(
            DepartmentMembership.department_id == item.id,
            DepartmentMembership.is_primary.in_([True]),
            active_on(DepartmentMembership, as_of),
        )
    ) or 0
    return {
        "id": item.id,
        "code": item.code,
        "name": item.name,
        "name_ar": item.name_ar,
        "description": item.description,
        "is_active": item.is_active,
        "parent_department_id": assignment.parent_department_id if assignment else None,
        "head_user_id": assignment.head_user_id if assignment else None,
        "effective_from": assignment.effective_from if assignment else item.effective_from,
        "effective_until": assignment.effective_until if assignment else item.effective_until,
        "path": [node.name for node in department_path(db, item.id, as_of)],
        "path_ar": [node.name_ar or node.name for node in department_path(db, item.id, as_of)],
        "descendant_count": len(department_descendant_ids(db, item.id, as_of)),
        "headcount": headcount,
        "head_name": head.full_name if head and head.is_active else None,
        "head_job_title": head.job_title if head and head.is_active else None,
        "head_profile_picture_url": head.profile_picture_url if head and head.is_active else None,
    }


@departments_router.get("/organization/tree")
def department_organization_tree(
    as_of: date = Query(default_factory=date.today),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(authenticated_user),
) -> list[dict[str, object]]:
    statement = select(Department)
    if not include_inactive:
        statement = statement.where(Department.is_active.in_([True]))
    return [_department_hierarchy_read(db, item, as_of) for item in db.scalars(statement.order_by(Department.name))]


@departments_router.get("/organization/vacancies")
def department_vacancies(
    as_of: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("user.manage")),
) -> list[dict[str, object]]:
    result = []
    for item in db.scalars(select(Department).where(Department.is_active.in_([True])).order_by(Department.name)):
        assignment = department_assignment(db, item.id, as_of)
        if not assignment or assignment.head_user_id is None:
            result.append({"department_id": item.id, "code": item.code, "name": item.name, "reason": "HEAD_VACANT"})
    return result


@departments_router.get("/{department_id}/organization-history")
def department_organization_history(
    department_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("user.manage")),
) -> list[dict[str, object]]:
    if not db.get(Department, department_id):
        raise NotFoundError("Department does not exist.")
    return [
        {"id": row.id, "parent_department_id": row.parent_department_id, "head_user_id": row.head_user_id, "effective_from": row.effective_from, "effective_until": row.effective_until}
        for row in db.scalars(select(DepartmentHierarchyAssignment).where(DepartmentHierarchyAssignment.department_id == department_id).order_by(DepartmentHierarchyAssignment.effective_from.desc()))
    ]


@departments_router.post("/{department_id}/organization-history", status_code=201)
def create_department_organization_assignment(
    department_id: int,
    data: DepartmentHierarchyAssignmentCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("user.manage")),
) -> dict[str, object]:
    current = department_assignment(db, department_id, data.effective_from)
    if current:
        if current.effective_from == data.effective_from:
            from app.modules.iam.organization import validate_department_assignment

            validate_department_assignment(db, department_id, data.parent_department_id, data.head_user_id, data.effective_from, data.effective_until, ignore_assignment_id=current.id)
            current.parent_department_id = data.parent_department_id
            current.head_user_id = data.head_user_id
            current.effective_until = data.effective_until
            department = db.get(Department, department_id)
            assert department is not None
            department.parent_department_id = data.parent_department_id
            department.head_user_id = data.head_user_id
            department.effective_from = data.effective_from
            department.effective_until = data.effective_until
            db.add(AuditLog(actor_user_id=actor.id, entity_type="DepartmentHierarchy", entity_id=str(department_id), action="department.hierarchy.corrected", new_values_json=json.dumps(data.model_dump(mode="json"))))
            db.commit()
            return {"id": current.id, **data.model_dump(mode="json")}
        if current.effective_from >= data.effective_from:
            raise ConflictError("DEPARTMENT_HIERARCHY_OVERLAP", "Choose an effective date after the current assignment starts.")
        current.effective_until = data.effective_from - timedelta(days=1)
    row = add_department_assignment(db, department_id, data.parent_department_id, data.head_user_id, data.effective_from, data.effective_until, actor.id)
    db.flush()
    db.add(AuditLog(actor_user_id=actor.id, entity_type="DepartmentHierarchy", entity_id=str(department_id), action="department.hierarchy.assigned", new_values_json=json.dumps(data.model_dump(mode="json"))))
    db.commit()
    return {"id": row.id, **data.model_dump(mode="json")}


@departments_router.post("/organization/drafts/publish", status_code=201)
def publish_department_organization_draft(
    data: DepartmentHierarchyPublishRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("user.manage")),
) -> dict[str, int]:
    if len({change.department_id for change in data.changes}) != len(data.changes):
        raise ConflictError("DUPLICATE_DEPARTMENT_CHANGE", "Each department can appear only once in a hierarchy draft.")
    published = 0
    for change in data.changes:
        if not db.get(Department, change.department_id):
            raise NotFoundError(f"Department {change.department_id} does not exist.")
        current = department_assignment(db, change.department_id, change.effective_from)
        if current:
            if current.effective_from == change.effective_from:
                from app.modules.iam.organization import validate_department_assignment

                validate_department_assignment(
                    db,
                    change.department_id,
                    change.parent_department_id,
                    change.head_user_id,
                    change.effective_from,
                    change.effective_until,
                    ignore_assignment_id=current.id,
                )
                current.parent_department_id = change.parent_department_id
                current.head_user_id = change.head_user_id
                current.effective_until = change.effective_until
                department = db.get(Department, change.department_id)
                assert department is not None
                department.parent_department_id = change.parent_department_id
                department.head_user_id = change.head_user_id
                department.effective_from = change.effective_from
                department.effective_until = change.effective_until
            else:
                if current.effective_from >= change.effective_from:
                    raise ConflictError("DEPARTMENT_HIERARCHY_OVERLAP", "Choose an effective date after the current assignment starts.")
                current.effective_until = change.effective_from - timedelta(days=1)
                add_department_assignment(
                    db,
                    change.department_id,
                    change.parent_department_id,
                    change.head_user_id,
                    change.effective_from,
                    change.effective_until,
                    actor.id,
                )
        else:
            add_department_assignment(
                db,
                change.department_id,
                change.parent_department_id,
                change.head_user_id,
                change.effective_from,
                change.effective_until,
                actor.id,
            )
        db.flush()
        db.add(
            AuditLog(
                actor_user_id=actor.id,
                entity_type="DepartmentHierarchy",
                entity_id=str(change.department_id),
                action="department.hierarchy.published",
                new_values_json=json.dumps(change.model_dump(mode="json")),
            )
        )
        published += 1
    db.commit()
    return {"published": published}


@users_router.get("/organization-chart")
def organization_chart(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(authenticated_user),
) -> list[dict[str, object]]:
    statement = select(OrganizationChartNode)
    if not include_inactive:
        statement = statement.where(OrganizationChartNode.is_active.in_([True]))
    return [{"id": row.id, "parent_id": row.parent_id, "name": row.name, "node_type": row.node_type, "title": row.title, "image_url": row.image_url, "email": row.email, "phone_number": row.phone_number, "notes": row.notes, "sort_order": row.sort_order, "is_active": row.is_active} for row in db.scalars(statement.order_by(OrganizationChartNode.sort_order, OrganizationChartNode.name))]


def _validate_chart_parent(db: Session, node_id: int | None, parent_id: int | None) -> None:
    if parent_id is None:
        return
    if node_id == parent_id or not db.get(OrganizationChartNode, parent_id):
        raise ConflictError("INVALID_ORGANIZATION_PARENT", "Choose a valid parent node.")
    current: int | None = parent_id
    seen = {node_id} if node_id is not None else set()
    while current is not None:
        if current in seen:
            raise ConflictError("ORGANIZATION_CHART_CYCLE", "This parent would create a cycle.")
        seen.add(current)
        parent = db.get(OrganizationChartNode, current)
        current = parent.parent_id if parent else None


@users_router.post("/organization-chart", status_code=201)
def create_organization_chart_node(data: OrganizationChartNodeWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("user.manage"))) -> dict[str, object]:
    _validate_chart_parent(db, None, data.parent_id)
    row = OrganizationChartNode(**data.model_dump(), created_by_user_id=actor.id)
    db.add(row); db.flush()
    db.add(AuditLog(actor_user_id=actor.id, entity_type="OrganizationChartNode", entity_id=str(row.id), action="organization_chart.created", new_values_json=json.dumps(data.model_dump(mode="json"))))
    db.commit(); db.refresh(row)
    return {"id": row.id, **data.model_dump(mode="json")}


@users_router.patch("/organization-chart/{node_id}")
def update_organization_chart_node(node_id: int, data: OrganizationChartNodeUpdate, db: Session = Depends(get_db), actor: User = Depends(require_permission("user.manage"))) -> dict[str, object]:
    row = db.get(OrganizationChartNode, node_id)
    if not row: raise NotFoundError("Organization chart node does not exist.")
    changes = data.model_dump(exclude_unset=True)
    if "parent_id" in changes: _validate_chart_parent(db, node_id, changes["parent_id"])
    for key, value in changes.items(): setattr(row, key, value)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="OrganizationChartNode", entity_id=str(row.id), action="organization_chart.updated", new_values_json=json.dumps(data.model_dump(mode="json", exclude_unset=True))))
    db.commit(); db.refresh(row)
    return {"id": row.id, "parent_id": row.parent_id, "name": row.name, "node_type": row.node_type, "title": row.title, "image_url": row.image_url, "email": row.email, "phone_number": row.phone_number, "notes": row.notes, "sort_order": row.sort_order, "is_active": row.is_active}


@users_router.delete("/organization-chart/{node_id}", status_code=204)
def delete_organization_chart_node(node_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("user.manage"))) -> Response:
    row = db.get(OrganizationChartNode, node_id)
    if not row: raise NotFoundError("Organization chart node does not exist.")
    if db.scalar(select(OrganizationChartNode.id).where(OrganizationChartNode.parent_id == node_id).limit(1)) is not None:
        raise ConflictError("ORGANIZATION_NODE_HAS_CHILDREN", "Move or remove child nodes first.")
    db.delete(row); db.add(AuditLog(actor_user_id=actor.id, entity_type="OrganizationChartNode", entity_id=str(node_id), action="organization_chart.deleted")); db.commit()
    return Response(status_code=204)


@users_router.get("/{user_id}/organization-history")
def user_organization_history(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("user.manage")),
) -> dict[str, object]:
    if not db.get(User, user_id):
        raise NotFoundError("User does not exist.")
    memberships = list(db.scalars(select(DepartmentMembership).where(DepartmentMembership.user_id == user_id).order_by(DepartmentMembership.effective_from.desc())))
    reporting = list(db.scalars(select(UserReportingLine).where(UserReportingLine.user_id == user_id).order_by(UserReportingLine.effective_from.desc())))
    return {
        "memberships": [{"id": row.id, "department_id": row.department_id, "effective_from": row.effective_from, "effective_until": row.effective_until, "is_primary": row.is_primary} for row in memberships],
        "reporting_lines": [{"id": row.id, "manager_user_id": row.manager_user_id, "effective_from": row.effective_from, "effective_until": row.effective_until} for row in reporting],
    }


@users_router.post("/{user_id}/department-memberships", status_code=201)
def create_user_department_membership(
    user_id: int,
    data: UserDepartmentAssignmentCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("user.manage")),
) -> dict[str, object]:
    row = assign_user_department(db, user_id, data.department_id, data.effective_from, actor.id)
    db.flush()
    db.add(AuditLog(actor_user_id=actor.id, entity_type="DepartmentMembership", entity_id=str(row.id), action="user.department.assigned", new_values_json=json.dumps(data.model_dump(mode="json"))))
    db.commit()
    return {"id": row.id, **data.model_dump(mode="json")}


@users_router.post("/{user_id}/reporting-lines", status_code=201)
def create_user_reporting_line(
    user_id: int,
    data: UserManagerAssignmentCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("user.manage")),
) -> dict[str, object]:
    row = assign_user_manager(db, user_id, data.manager_user_id, data.effective_from, actor.id)
    db.flush()
    db.add(AuditLog(actor_user_id=actor.id, entity_type="UserReportingLine", entity_id=str(row.id), action="user.manager.assigned", new_values_json=json.dumps(data.model_dump(mode="json"))))
    db.commit()
    return {"id": row.id, **data.model_dump(mode="json")}


@auth_router.post("/login", response_model=TokenPair)
def login_endpoint(
    data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenPair:
    return login(
        db, data.login, data.password, settings, request.client.host if request.client else None
    )


@auth_router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ForgotPasswordResponse:
    normalized = data.login.strip().casefold()
    user = db.scalar(
        select(User).where(
            (User.username_normalized == normalized) | (User.email_normalized == normalized)
        )
    )
    raw_token: str | None = None
    allowed_domains = {
        item.strip().casefold().lstrip("@")
        for item in settings.password_reset_allowed_domains.split(",")
        if item.strip()
    }
    user_domain = user.email.rsplit("@", 1)[-1].casefold() if user else ""
    if user and user.is_active and (not allowed_domains or user_domain in allowed_domains):
        now = server_now()
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        ).update({PasswordResetToken.used_at: now})
        raw_token = secrets.token_urlsafe(48)
        expires_at = now + timedelta(minutes=settings.password_reset_minutes)
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_refresh_token(raw_token),
                expires_at=expires_at,
                requested_ip=request.client.host if request.client else None,
            )
        )
        db.add(
            AuthenticationEvent(
                user_id=user.id,
                event_type="PASSWORD_RESET_REQUESTED",
                ip_address=request.client.host if request.client else None,
            )
        )
        # Queue every eligible request even while SMTP is temporarily disabled. This
        # keeps recovery requests observable and lets the worker deliver them after
        # configuration is corrected, provided the token is still valid.
        reset_link = f"{settings.frontend_base_url}/reset-password?token={raw_token}"
        db.add(
            EventOutbox(
                event_type="PASSWORD_RESET_EMAIL",
                aggregate_type="User",
                aggregate_id=str(user.id),
                deduplication_key=f"password-reset:{hash_refresh_token(raw_token)}",
                payload_json=json.dumps({"user_id": user.id, "expires_at": expires_at.isoformat(), "subject": "Millensys Support Hub password reset", "body": f"Username: {user.username}\n\nUse this secure one-time link within {settings.password_reset_minutes} minutes to set a new password:\n\n{reset_link}\n\nIf you did not request this, ignore this email."}),
            )
        )
        db.commit()
        # Do not make users wait for the periodic scheduler. When SMTP is
        # configured, attempt delivery now; transient failures remain queued
        # with the email service's normal retry/dead-letter diagnostics.
        if settings.smtp_enabled:
            process_email_outbox(db, settings, limit=50)
    return ForgotPasswordResponse(
        message="If an active account matches, password reset instructions will be sent.",
        reset_token=raw_token if settings.app_env in {"local", "test"} else None,
    )


@auth_router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    data: PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    now = server_now()
    token = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_refresh_token(data.token),
            PasswordResetToken.used_at.is_(None),
        )
    )
    if not token or token.expires_at.replace(tzinfo=server_timezone()) <= now:
        raise ConflictError("RESET_TOKEN_INVALID", "The reset link is invalid or expired.")
    user = db.get(User, token.user_id)
    if not user or not user.is_active:
        raise ConflictError("RESET_TOKEN_INVALID", "The reset link is invalid or expired.")
    if verify_password(data.new_password, user.password_hash):
        raise ConflictError(
            "PASSWORD_REUSE", "Choose a password different from the current password."
        )
    user.password_hash = hash_password(data.new_password)
    user.password_changed_at = now
    user.require_password_change = False
    user.failed_login_count = 0
    user.locked_until = None
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).update({PasswordResetToken.used_at: now})
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked_at.is_(None),
    ).update({RefreshToken.revoked_at: now})
    db.add(
        AuthenticationEvent(
            user_id=user.id,
            event_type="PASSWORD_RESET_COMPLETED",
            ip_address=request.client.host if request.client else None,
        )
    )
    db.commit()
    return Response(status_code=204)


@auth_router.post("/refresh", response_model=TokenPair)
def refresh_endpoint(
    data: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenPair:
    return rotate_refresh(db, data.refresh_token, settings, request.client.host if request.client else None)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_endpoint(data: LogoutRequest, request: Request, db: Session = Depends(get_db)) -> Response:
    token = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(data.refresh_token)
        )
    )
    if token and token.revoked_at is None:
        token.revoked_at = server_now()
        db.add(AuthenticationEvent(user_id=token.user_id,event_type="LOGOUT_EXPLICIT",ip_address=request.client.host if request.client else None))
        db.commit()
    return Response(status_code=204)


def _available_landing_pages(user: User, permissions: set[str]) -> list[str]:
    if user.user_type == "CLIENT_PORTAL":
        return ["portal"]
    pages: list[str] = ["home", "my-workspace"]
    if {"dashboard.agent", "dashboard.manager"} & permissions:
        pages.append("dashboard")
    if "topmanagementdashboard.view" in permissions:
        pages.append("top-management")
    if "ticket.create" in permissions:
        pages.append("ticket-create")
    if {"ticket.view.all", "ticket.view.team", "ticket.view.own"} & permissions:
        pages.extend(["tickets", "saved-views"])
    if "client.view" in permissions:
        pages.append("clients")
    if "knowledge.view" in permissions:
        pages.append("knowledge")
    if {
        "internal_operation.workspace.view",
        "internal_operation.view",
        "shift.view",
        "visit.entitlement.view",
        "dashboard.manager",
    } & permissions:
        pages.append("internal-operations")
    return list(dict.fromkeys(pages))


@auth_router.get("/me", response_model=CurrentUserRead)
def me_endpoint(
    user: User = Depends(authenticated_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    access = effective_permissions(db, user)
    primary_profile = db.scalar(
        select(Profile)
        .join(UserProfile, UserProfile.profile_id == Profile.id)
        .where(
            UserProfile.user_id == user.id,
            UserProfile.is_primary.in_([True]),
            UserProfile.is_active.in_([True]),
            Profile.is_active.in_([True]),
        )
    )
    available_pages = _available_landing_pages(user, set(access.permissions))
    profile_page = (
        "dashboard"
        if not primary_profile or primary_profile.default_dashboard_code == "agent"
        else primary_profile.default_dashboard_code
    )
    requested_page = user.default_page or profile_page
    default_page = requested_page if requested_page in available_pages else (
        available_pages[0] if available_pages else "home"
    )
    return {
        **UserRead.model_validate(user).model_dump(),
        "permissions": access.permissions,
        "client_scope_ids": access.client_scope_ids,
        "branch_scope_ids": access.branch_scope_ids,
        "auto_close_on_resolve": user.auto_close_on_resolve,
        "default_page": default_page,
        "default_dashboard_scope": user.default_dashboard_scope,
        "default_saved_view_id": user.default_saved_view_id,
        "theme_mode": user.theme_mode,
        "theme_preset": user.theme_preset,
        "preferred_language": user.preferred_language,
    }


@auth_router.post("/presence", status_code=status.HTTP_204_NO_CONTENT)
def presence_heartbeat(
    user: User = Depends(authenticated_user),
    db: Session = Depends(get_db),
) -> Response:
    # Presence is best-effort telemetry, not a business-record edit. A direct
    # atomic update avoids ORM stale-row conflicts when several tabs heartbeat
    # for the same user at nearly the same time.
    db.execute(
        update(User).where(User.id == user.id).values(last_seen_at=server_now())
    )
    db.commit()
    return Response(status_code=204)


@auth_router.put("/me/profile-preferences", response_model=CurrentUserRead)
def update_profile_preferences(
    data: ProfilePreferencesUpdate,
    user: User = Depends(authenticated_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    from app.modules.dashboards.models import SavedView

    permissions = set(effective_permissions(db, user).permissions)
    if data.default_page not in _available_landing_pages(user, permissions):
        raise ConflictError(
            "DEFAULT_PAGE_NOT_AVAILABLE",
            "The selected default page is not available to this user.",
        )
    if data.default_saved_view_id is not None:
        view = db.get(SavedView, data.default_saved_view_id)
        if not view or not view.is_active or view.owner_user_id != user.id:
            raise NotFoundError("The selected saved view is unavailable.")
        db.query(SavedView).filter(SavedView.owner_user_id == user.id).update({SavedView.is_default: False})
        view.is_default = True
    else:
        db.query(SavedView).filter(SavedView.owner_user_id == user.id).update({SavedView.is_default: False})
    user.default_page = data.default_page
    user.default_dashboard_scope = data.default_dashboard_scope
    user.default_saved_view_id = data.default_saved_view_id
    user.theme_mode = data.theme_mode
    user.theme_preset = data.theme_preset
    user.profile_picture_url = data.profile_picture_url
    if data.preferred_language is not None:
        user.preferred_language = data.preferred_language
    db.commit()
    return me_endpoint(user, db)


@auth_router.put("/me/language", response_model=CurrentUserRead)
def update_language_preference(
    data: LanguagePreferenceUpdate,
    user: User = Depends(authenticated_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    user.preferred_language = data.preferred_language
    db.commit()
    return me_endpoint(user, db)


@auth_router.post("/me/profile-picture", response_model=CurrentUserRead)
async def upload_my_profile_picture(
    upload: UploadFile = File(...),
    user: User = Depends(authenticated_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    allowed_types = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    extension = allowed_types.get(upload.content_type or "")
    if extension is None:
        raise HTTPException(status_code=415, detail="Use a JPG, PNG, or WebP profile picture.")
    content = await upload.read(5 * 1024 * 1024 + 1)
    if not content or len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="The profile picture must be smaller than 5 MB.")
    directory = Path(settings.attachment_storage_path).expanduser().resolve() / "profile-pictures"
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"user-{user.id}-{uuid4().hex}{extension}"
    (directory / filename).write_bytes(content)
    user.profile_picture_url = f"{settings.application_path_base.rstrip('/')}/api/v1/users/{user.id}/profile-picture"
    db.commit()
    return me_endpoint(user, db)


@users_router.get("/{user_id}/profile-picture", include_in_schema=False)
def get_profile_picture(
    user_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    user = db.get(User, user_id)
    directory = Path(settings.attachment_storage_path).expanduser().resolve() / "profile-pictures"
    matches = sorted(directory.glob(f"user-{user_id}-*"), key=lambda item: item.stat().st_mtime, reverse=True) if directory.exists() else []
    if not user or not matches:
        raise NotFoundError("Profile picture not found.")
    content_types = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    return FileResponse(matches[0], media_type=content_types.get(matches[0].suffix.lower(), "application/octet-stream"))


@users_router.post("/{user_id}/profile-picture", response_model=UserRead)
async def upload_user_profile_picture(
    user_id: int,
    upload: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("user.manage")),
    settings: Settings = Depends(get_settings),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError("User does not exist.")
    allowed_types = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    extension = allowed_types.get(upload.content_type or "")
    if extension is None:
        raise HTTPException(status_code=415, detail="Use a JPG, PNG, or WebP profile picture.")
    content = await upload.read(5 * 1024 * 1024 + 1)
    if not content or len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="The profile picture must be smaller than 5 MB.")
    directory = Path(settings.attachment_storage_path).expanduser().resolve() / "profile-pictures"
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"user-{user.id}-{uuid4().hex}{extension}"
    (directory / filename).write_bytes(content)
    user.profile_picture_url = f"{settings.application_path_base.rstrip('/')}/api/v1/users/{user.id}/profile-picture"
    db.add(AuditLog(actor_user_id=actor.id, entity_type="User", entity_id=str(user.id), action="user.profile_picture.uploaded"))
    db.commit()
    db.refresh(user)
    return user


@auth_router.put("/me/resolve-preference", response_model=CurrentUserRead)
def update_resolve_preference(
    data: ResolvePreferenceUpdate,
    user: User = Depends(authenticated_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    permissions = set(effective_permissions(db, user).permissions)
    if "ticket.auto_close_on_resolve" not in permissions:
        raise AuthorizationError("You do not have permission to save an automatic close preference.")
    user.auto_close_on_resolve = data.auto_close_on_resolve
    db.commit()
    return me_endpoint(user, db)


@auth_router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password_endpoint(
    data: PasswordChangeRequest,
    user: User = Depends(authenticated_user),
    db: Session = Depends(get_db),
) -> Response:
    change_password(db, user, data.current_password, data.new_password)
    return Response(status_code=204)


@users_router.get("", response_model=list[UserRead])
def list_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=200),
    is_active: bool | None = None,
    department_id: int | None = None,
    include_department_descendants: bool = False,
    organization_as_of: date | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("user.manage")),
) -> list[User]:
    statement = select(User)
    if search and (term := search.strip()):
        pattern = f"%{term}%"
        statement = statement.where(
            User.full_name.ilike(pattern) | User.email.ilike(pattern) | User.username.ilike(pattern)
        )
    if is_active is not None:
        statement = statement.where(User.is_active == is_active)
    if department_id is not None:
        department_ids = department_descendant_ids(db, department_id, organization_as_of or server_today(), include_self=True) if include_department_descendants else [department_id]
        if organization_as_of is not None:
            statement = statement.where(User.id.in_(select(DepartmentMembership.user_id).where(DepartmentMembership.department_id.in_(department_ids), DepartmentMembership.is_primary.in_([True]), active_on(DepartmentMembership, organization_as_of))))
        else:
            statement = statement.where(User.department_id.in_(department_ids))
    return list(db.scalars(statement.order_by(User.full_name).offset(offset).limit(limit)))


@users_router.post("", response_model=UserRead, status_code=201)
def create_user_endpoint(
    data: UserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("user.manage")),
) -> User:
    return create_user(db, data, actor.id)


@users_router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("user.manage")),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError()
    return user


@users_router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("user.manage")),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError()
    changes = data.model_dump(exclude_unset=True)
    if "department_id" in changes:
        department = db.get(Department, changes["department_id"]) if changes["department_id"] else None
        if changes["department_id"] and (not department or not department.is_active):
            raise ConflictError("INVALID_DEPARTMENT", "Select an active department from master data.")
        changes["department"] = department.name if department else None
    if user.id == actor.id and changes.get("is_active") is False:
        raise ConflictError("SELF_DEACTIVATION", "You cannot deactivate your own account.")
    if "reports_to_user_id" in changes and changes["reports_to_user_id"] is not None:
        if changes["reports_to_user_id"] == user.id:
            raise ConflictError("SELF_REPORTING", "A user cannot report to themselves.")
        manager = db.get(User, changes["reports_to_user_id"])
        if not manager or not manager.is_active or manager.user_type != "EMPLOYEE":
            raise ConflictError("INVALID_REPORTS_TO", "Reports To must be an active employee.")
        ancestor: User | None = manager
        visited: set[int] = set()
        while ancestor and ancestor.id not in visited:
            if ancestor.id == user.id:
                raise ConflictError("REPORTING_CYCLE", "This manager selection would create a reporting cycle.")
            visited.add(ancestor.id)
            ancestor = db.get(User, ancestor.reports_to_user_id) if ancestor.reports_to_user_id else None
    if "department_id" in changes and user.user_type == "EMPLOYEE":
        if changes["department_id"] is not None:
            assign_user_department(db, user.id, int(changes["department_id"]), server_today(), actor.id)
        else:
            current_memberships = list(db.scalars(select(DepartmentMembership).where(DepartmentMembership.user_id == user.id, active_on(DepartmentMembership, server_today()))))
            for membership in current_memberships:
                if membership.effective_from == server_today():
                    db.delete(membership)
                else:
                    membership.effective_until = server_today() - timedelta(days=1)
    if "reports_to_user_id" in changes and user.user_type == "EMPLOYEE":
        if changes["reports_to_user_id"] is not None:
            assign_user_manager(db, user.id, int(changes["reports_to_user_id"]), server_today(), actor.id)
        else:
            current_lines = list(db.scalars(select(UserReportingLine).where(UserReportingLine.user_id == user.id, active_on(UserReportingLine, server_today()))))
            for line in current_lines:
                if line.effective_from == server_today():
                    db.delete(line)
                else:
                    line.effective_until = server_today() - timedelta(days=1)
    if "email" in changes:
        email = str(changes["email"])
        duplicate = db.scalar(
            select(User.id).where(User.email_normalized == email.casefold(), User.id != user_id)
        )
        if duplicate:
            raise ConflictError("DUPLICATE_EMAIL", "That email is already in use.")
        changes["email"] = email
        user.email_normalized = email.casefold()
    if "employee_code" in changes and changes["employee_code"]:
        duplicate_code = db.scalar(
            select(User.id).where(
                User.employee_code == changes["employee_code"], User.id != user_id
            )
        )
        if duplicate_code:
            raise ConflictError("DUPLICATE_EMPLOYEE_CODE", "That employee code is already in use.")
    old_values = {key: getattr(user, key) for key in changes}
    for key, value in changes.items():
        setattr(user, key, value)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="User",
            entity_id=str(user.id),
            action="user.updated",
            old_values_json=json.dumps(old_values, default=str),
            new_values_json=json.dumps(changes, default=str),
        )
    )
    participation_changes = {key: value for key, value in changes.items() if key in {"participates_in_shifts", "participates_in_operations"}}
    if participation_changes:
        db.add(AuditLog(actor_user_id=actor.id, entity_type="User", entity_id=str(user.id), action="user.scheduling_participation.updated", old_values_json=json.dumps({key: old_values[key] for key in participation_changes}), new_values_json=json.dumps(participation_changes)))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "DUPLICATE_USER_VALUE",
            "The email or employee code is already in use.",
        ) from exc
    db.refresh(user)
    return user


@users_router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_user_password(
    user_id: int,
    data: AdminPasswordReset,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("user.manage")),
) -> Response:
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError()
    now = server_now()
    user.password_hash = hash_password(data.temporary_password)
    user.password_changed_at = now
    user.require_password_change = True
    user.failed_login_count = 0
    user.locked_until = None
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
    ).update({RefreshToken.revoked_at: now})
    db.add(
        AuthenticationEvent(
            user_id=user.id,
            username_attempted=user.username,
            event_type="ADMIN_PASSWORD_RESET",
            detail=data.reason,
        )
    )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="User",
            entity_id=str(user.id),
            action="user.password.reset",
            reason=data.reason,
            new_values_json=json.dumps({"sessions_revoked": True, "require_password_change": True}),
        )
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@users_router.get("/{user_id}/profiles", response_model=list[UserProfileAssignmentRead])
def user_profiles(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("profile.manage")),
) -> list[dict[str, object]]:
    if not db.get(User, user_id):
        raise NotFoundError()
    rows = db.execute(
        select(UserProfile, Profile)
        .join(Profile, Profile.id == UserProfile.profile_id)
        .where(UserProfile.user_id == user_id)
        .order_by(UserProfile.is_primary.desc(), Profile.name)
    )
    return [
        {
            "id": assignment.id,
            "profile_id": profile.id,
            "profile_code": profile.code,
            "profile_name": profile.name,
            "is_primary": assignment.is_primary,
            "valid_to": assignment.valid_to,
        }
        for assignment, profile in rows
    ]


@users_router.get("/{user_id}/permission-access")
def user_permission_access(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("profile.manage")),
) -> dict[str, object]:
    target = db.get(User, user_id)
    if not target:
        raise NotFoundError()
    now = server_now()
    profile_rows = db.execute(
        select(UserProfile, Profile, Permission)
        .join(Profile, Profile.id == UserProfile.profile_id)
        .join(ProfilePermission, ProfilePermission.profile_id == Profile.id)
        .join(Permission, Permission.id == ProfilePermission.permission_id)
        .where(UserProfile.user_id == user_id)
        .order_by(Profile.name, Permission.code)
    ).all()
    overrides = db.execute(
        select(UserPermissionOverride, Permission)
        .join(Permission, Permission.id == UserPermissionOverride.permission_id)
        .where(UserPermissionOverride.user_id == user_id)
        .order_by(UserPermissionOverride.valid_from.desc(), UserPermissionOverride.id.desc())
    ).all()
    actor_ids = {actor_id for row, _ in overrides for actor_id in (row.approved_by_user_id, row.created_by_user_id) if actor_id is not None}
    actor_names = {row.id: row.full_name for row in db.scalars(select(User).where(User.id.in_(actor_ids or {-1})))}
    def active_window(valid_from: datetime, valid_to: datetime | None) -> bool:
        comparison_now = now if valid_from.tzinfo is not None else now.replace(tzinfo=None)
        return valid_from <= comparison_now and (valid_to is None or valid_to > comparison_now)

    return {
        "effective_permissions": effective_permissions(db, target, now).permissions,
        "profile_permissions": [
            {
                "permission_code": permission.code,
                "profile_id": profile.id,
                "profile_code": profile.code,
                "profile_name": profile.name,
                "is_primary": assignment.is_primary,
                "valid_from": assignment.valid_from,
                "valid_to": assignment.valid_to,
                "active": assignment.is_active and profile.is_active and permission.is_active and active_window(assignment.valid_from, assignment.valid_to),
            }
            for assignment, profile, permission in profile_rows
        ],
        "overrides": [
            {
                "id": row.id,
                "permission_code": permission.code,
                "effect": row.effect,
                "scope_type": row.scope_type,
                "scope_reference_id": row.scope_reference_id,
                "valid_from": row.valid_from,
                "valid_to": row.valid_to,
                "reason": row.reason,
                "approved_by_user_id": row.approved_by_user_id,
                "approved_by_name": actor_names.get(row.approved_by_user_id),
                "created_by_user_id": row.created_by_user_id,
                "created_by_name": actor_names.get(row.created_by_user_id),
                "active": active_window(row.valid_from, row.valid_to),
            }
            for row, permission in overrides
        ],
    }


@users_router.post("/{user_id}/profiles", status_code=201)
def assign_profile(
    user_id: int,
    data: ProfileAssignment,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("profile.manage")),
) -> dict[str, int]:
    if not db.get(User, user_id) or not db.get(Profile, data.profile_id):
        raise NotFoundError()
    existing_assignment = db.scalar(
        select(UserProfile).where(
            UserProfile.user_id == user_id, UserProfile.profile_id == data.profile_id
        )
    )
    if existing_assignment:
        if not data.is_primary:
            raise ConflictError("PROFILE_ALREADY_ASSIGNED", "The profile is already assigned.")
        for existing in db.scalars(select(UserProfile).where(UserProfile.user_id == user_id)).all():
            existing.is_primary = existing.id == existing_assignment.id
        existing_assignment.assignment_reason = data.reason
        db.add(
            AuditLog(
                actor_user_id=actor.id,
                entity_type="User",
                entity_id=str(user_id),
                action="user.profile.primary_changed",
                reason=data.reason,
                new_values_json=json.dumps({"profile_id": data.profile_id}),
            )
        )
        db.commit()
        return {"id": existing_assignment.id}
    if data.is_primary:
        for existing in db.scalars(select(UserProfile).where(UserProfile.user_id == user_id)).all():
            existing.is_primary = False
    assignment = UserProfile(
        user_id=user_id,
        profile_id=data.profile_id,
        is_primary=data.is_primary,
        valid_to=data.valid_to,
        assignment_reason=data.reason,
        assigned_by_user_id=actor.id,
    )
    db.add(assignment)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="User",
            entity_id=str(user_id),
            action="user.profile.assigned",
            reason=data.reason,
            new_values_json=json.dumps(
                {"profile_id": data.profile_id, "is_primary": data.is_primary}
            ),
        )
    )
    db.commit()
    return {"id": assignment.id}


@users_router.delete("/{user_id}/profiles/{profile_id}", status_code=204)
def remove_profile(
    user_id: int,
    profile_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("profile.manage")),
) -> Response:
    assignment = db.scalar(
        select(UserProfile).where(
            UserProfile.user_id == user_id, UserProfile.profile_id == profile_id
        )
    )
    if not assignment:
        raise NotFoundError()
    if assignment.is_primary:
        raise ConflictError(
            "PRIMARY_PROFILE_REQUIRED",
            "Assign another primary profile before removing this one.",
        )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="User",
            entity_id=str(user_id),
            action="user.profile.removed",
            old_values_json=json.dumps({"profile_id": profile_id}),
        )
    )
    db.delete(assignment)
    db.commit()
    return Response(status_code=204)


@users_router.get("/{user_id}/effective-permissions", response_model=EffectivePermissions)
def get_effective(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("profile.manage")),
) -> EffectivePermissions:
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError()
    return effective_permissions(db, user)


@profiles_router.get("", response_model=list[ProfileRead])
def list_profiles(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("profile.manage")),
) -> list[dict[str, object]]:
    return [_profile_with_dashboard_source(db, profile) for profile in db.scalars(select(Profile).order_by(Profile.name))]


def _profile_with_dashboard_source(db: Session, profile: Profile) -> dict[str, object]:
    from app.modules.dashboards.models import Dashboard, DashboardAssignment

    now = server_now()
    rows = db.execute(
        select(DashboardAssignment, Dashboard)
        .join(Dashboard, Dashboard.id == DashboardAssignment.dashboard_id)
        .where(
            DashboardAssignment.is_active.in_([True]),
            DashboardAssignment.is_personal.in_([False]),
            DashboardAssignment.dashboard_type == "EXECUTIVE",
            Dashboard.is_active.in_([True]),
            DashboardAssignment.user_id.is_(None),
            DashboardAssignment.department_id.is_(None),
            or_(DashboardAssignment.profile_id == profile.id, DashboardAssignment.profile_id.is_(None)),
            or_(DashboardAssignment.effective_from.is_(None), DashboardAssignment.effective_from <= now),
            or_(DashboardAssignment.effective_until.is_(None), DashboardAssignment.effective_until > now),
        )
    ).all()
    ranked = sorted(
        rows,
        key=lambda row: (1 if row[0].profile_id == profile.id else 0, row[0].priority, row[0].id),
        reverse=True,
    )
    values = ProfileRead.model_validate(profile).model_dump()
    if not ranked:
        return values
    assignment, dashboard = ranked[0]
    return {
        **values,
        "effective_dashboard_source": "PROFILE" if assignment.profile_id else "SYSTEM",
        "effective_dashboard_id": dashboard.id,
        "effective_dashboard_name": dashboard.name,
    }


@profiles_router.post("", response_model=ProfileRead, status_code=201)
def create_profile(
    data: ProfileCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("profile.manage")),
) -> Profile:
    if data.code and db.scalar(select(Profile.id).where(Profile.code == data.code)):
        raise ConflictError("DUPLICATE_PROFILE", "That profile code is already in use.")
    allowed_pages = {"dashboard", "top-management", "ticket-create", "tickets", "saved-views", "clients", "knowledge", "portal"}
    if data.default_dashboard_code not in allowed_pages:
        raise ConflictError("INVALID_DEFAULT_PAGE", "The selected default page is invalid.")
    if data.profile_type == "CLIENT_PORTAL" and data.default_dashboard_code != "portal":
        raise ConflictError("INVALID_DEFAULT_PAGE", "Client portal profiles must open the portal.")
    profile = Profile(
        code=data.code or f"PENDING-PRF-{server_now().timestamp()}",
        name=data.name,
        description=data.description,
        profile_type=data.profile_type,
        is_system=False,
        default_dashboard_code=data.default_dashboard_code,
    )
    db.add(profile)
    db.flush()
    if not data.code:
        profile.code = f"PRF-{profile.id:06d}"
    db.add_all(
        ProfilePermission(profile_id=profile.id, permission_id=permission_id)
        for permission_id in set(data.permission_ids)
    )
    db.commit()
    db.refresh(profile)
    return profile


@profiles_router.get("/{profile_id}", response_model=ProfileRead)
def get_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("profile.manage")),
) -> dict[str, object]:
    profile = db.get(Profile, profile_id)
    if not profile:
        raise NotFoundError()
    return _profile_with_dashboard_source(db, profile)


@profiles_router.patch("/{profile_id}", response_model=ProfileRead)
def update_profile(
    profile_id: int,
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("profile.manage")),
) -> Profile:
    profile = db.get(Profile, profile_id)
    if not profile:
        raise NotFoundError()
    changes = data.model_dump(exclude_unset=True)
    if "default_dashboard_code" in changes and changes["default_dashboard_code"] not in {
        "dashboard",
        "home",
        "top-management",
        "ticket-create",
        "tickets",
        "saved-views",
        "clients",
        "knowledge",
        "portal",
    }:
        raise ConflictError("INVALID_DEFAULT_PAGE", "The selected default page is invalid.")
    if profile.profile_type == "CLIENT_PORTAL" and changes.get("default_dashboard_code") not in {
        None,
        "home",
        "portal",
    }:
        raise ConflictError("INVALID_DEFAULT_PAGE", "Client portal profiles must open the portal.")
    landing_page = changes.get("default_dashboard_code")
    if landing_page is not None:
        primary_user_ids = select(UserProfile.user_id).where(
            UserProfile.profile_id == profile.id,
            UserProfile.is_primary.in_([True]),
            UserProfile.is_active.in_([True]),
        )
        db.query(User).filter(User.id.in_(primary_user_ids)).update(
            {User.default_page: landing_page}, synchronize_session=False
        )
    for key, value in changes.items():
        setattr(profile, key, value)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Profile",
            entity_id=str(profile.id),
            action="profile.updated",
            new_values_json=json.dumps(changes),
        )
    )
    db.commit()
    db.refresh(profile)
    return profile


@profiles_router.post("/{profile_id}/clone", response_model=ProfileRead, status_code=201)
def clone_profile(
    profile_id: int,
    name: str,
    code: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("profile.manage")),
) -> Profile:
    source = db.get(Profile, profile_id)
    if not source:
        raise NotFoundError()
    if code and db.scalar(select(Profile.id).where(Profile.code == code)):
        raise ConflictError("DUPLICATE_PROFILE", "That profile code is already in use.")
    clone = Profile(
        code=code or f"PENDING-PRF-{server_now().timestamp()}",
        name=name,
        description=f"Cloned from {source.name}",
        profile_type=source.profile_type,
        is_system=False,
        risk_level=source.risk_level,
        default_dashboard_code=source.default_dashboard_code,
    )
    db.add(clone)
    db.flush()
    if not code:
        clone.code = f"PRF-{clone.id:06d}"
    ids = db.scalars(
        select(ProfilePermission.permission_id).where(ProfilePermission.profile_id == profile_id)
    )
    db.add_all(ProfilePermission(profile_id=clone.id, permission_id=x) for x in ids)
    db.commit()
    db.refresh(clone)
    return clone


@profiles_router.get("/{profile_id}/permissions", response_model=list[PermissionRead])
def profile_permissions(
    profile_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("profile.manage")),
) -> list[Permission]:
    if not db.get(Profile, profile_id):
        raise NotFoundError()
    return list(
        db.scalars(
            select(Permission)
            .join(ProfilePermission)
            .where(ProfilePermission.profile_id == profile_id)
            .order_by(Permission.code)
        )
    )


@profiles_router.put("/{profile_id}/permissions", response_model=list[PermissionRead])
def update_profile_permissions(
    profile_id: int,
    data: ProfilePermissionsUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("profile.manage")),
) -> list[Permission]:
    profile = db.get(Profile, profile_id)
    if not profile:
        raise NotFoundError()
    requested_ids = set(data.permission_ids)
    permissions = list(
        db.scalars(select(Permission).where(Permission.id.in_(requested_ids or {-1})))
    )
    if len(permissions) != len(requested_ids):
        raise NotFoundError("One or more permissions do not exist.")
    previous_ids = set(
        db.scalars(
            select(ProfilePermission.permission_id).where(
                ProfilePermission.profile_id == profile_id
            )
        )
    )
    db.query(ProfilePermission).filter(ProfilePermission.profile_id == profile_id).delete()
    db.add_all(
        ProfilePermission(profile_id=profile_id, permission_id=permission_id)
        for permission_id in requested_ids
    )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Profile",
            entity_id=str(profile_id),
            action="profile.permissions.updated",
            reason=data.reason,
            old_values_json=json.dumps({"permission_ids": sorted(previous_ids)}),
            new_values_json=json.dumps({"permission_ids": sorted(requested_ids)}),
        )
    )
    db.commit()
    return sorted(permissions, key=lambda item: item.code)


@permissions_router.get("", response_model=list[PermissionRead])
def list_permissions(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("profile.manage")),
) -> list[Permission]:
    return list(
        db.scalars(
            select(Permission).where(Permission.is_active.in_([True])).order_by(Permission.code)
        )
    )
