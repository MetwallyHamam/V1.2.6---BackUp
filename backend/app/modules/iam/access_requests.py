import hashlib
import json
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, require_permission
from app.core.clock import server_now, server_timezone
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.modules.iam.models import (
    AccessRequest,
    AccessRequestDecision,
    AuditLog,
    AuthenticationEvent,
    Effect,
    Permission,
    PermissionStepUpChallenge,
    Profile,
    ProfilePermission,
    User,
    UserPermissionOverride,
    UserProfile,
)
from app.modules.iam.security import verify_password
from app.modules.iam.service import effective_permissions, normalize
from app.modules.notifications.models import Notification

router = APIRouter(prefix="/access-requests", tags=["access requests"])

HIGH_RISK_PREFIXES = ("profile.", "user.", "audit.", "financial.", "configuration.", "integration.", "import.", "permission.")
RESOURCE_PERMISSIONS = {
    "/access-requests": "permission.grant.in_context",
    "/profiles": "profile.manage",
    "/users": "user.manage",
    "/audit": "audit.view",
    "/financial": "finance.view",
    "/tickets/create": "ticket.create",
    "/clients": "client.view",
}

class RequestCreate(BaseModel):
    permission_code: str = Field(min_length=3, max_length=150)
    resource: str = Field(min_length=1, max_length=300)
    return_path: str | None = Field(default=None, max_length=500)
    justification: str = Field(min_length=10, max_length=1000)

    @field_validator("resource")
    @classmethod
    def safe_resource(cls, value: str) -> str:
        if not value.startswith(("/", "action:")) or "://" in value or ".." in value:
            raise ValueError("Resource must be a local route or registered action.")
        return value

    @field_validator("return_path")
    @classmethod
    def safe_return_path(cls, value: str | None) -> str | None:
        if value and (not value.startswith("/") or value.startswith("//") or "://" in value):
            raise ValueError("Return path must be local.")
        return value

class DecisionBody(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)
    challenge_token: str | None = Field(default=None, min_length=32, max_length=200)
    grant_days: int = Field(default=30, ge=1, le=90)

class ChallengeBody(BaseModel):
    password: str = Field(min_length=8, max_length=200)

class DirectProfileGrantBody(BaseModel):
    permission_code: str = Field(min_length=3, max_length=150)
    resource: str = Field(min_length=1, max_length=300)
    return_path: str | None = Field(default=None, max_length=500)
    reason: str = Field(min_length=10, max_length=1000)
    approver_login: str = Field(min_length=2, max_length=320)
    approver_password: str = Field(min_length=8, max_length=200)

    @field_validator("resource")
    @classmethod
    def safe_resource(cls, value: str) -> str:
        if not value.startswith(("/", "action:")) or "://" in value or ".." in value:
            raise ValueError("Resource must be a local route or registered action.")
        return value

    @field_validator("return_path")
    @classmethod
    def safe_return_path(cls, value: str | None) -> str | None:
        if value and (not value.startswith("/") or value.startswith("//") or "://" in value):
            raise ValueError("Return path must be local.")
        return value

def _expire(row: AccessRequest, now: datetime) -> None:
    expires_at = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=server_timezone())
    if row.status == "PENDING" and expires_at <= now:
        row.status = "EXPIRED"

def _read(row: AccessRequest, db: Session) -> dict[str, object]:
    requester = db.get(User, row.requester_user_id)
    decisions = list(db.scalars(select(AccessRequestDecision).where(AccessRequestDecision.access_request_id == row.id).order_by(AccessRequestDecision.id)))
    return {"id":row.id,"requester_user_id":row.requester_user_id,"requester_name":requester.full_name if requester else None,"permission_code":row.permission.code,"capability":row.permission.description,"module":row.permission.module,"resource":row.resource,"return_path":row.return_path,"justification":row.justification,"status":row.status,"source_action":decisions[0].action if decisions else None,"latest_action":decisions[-1].action if decisions else None,"latest_actor_user_id":decisions[-1].actor_user_id if decisions else None,"expires_at":row.expires_at,"created_at":row.created_at,"decided_at":row.decided_at}

def _permission(db: Session, code: str, resource: str) -> Permission:
    permission = db.scalar(select(Permission).where(Permission.code == code, Permission.is_active.in_([True])))
    if not permission: raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown or inactive capability.")
    registered = RESOURCE_PERMISSIONS.get(resource)
    if registered != permission.code and resource != f"action:{permission.code}": raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "The resource and capability are not registered together.")
    if permission.is_high_risk or permission.code.startswith(HIGH_RISK_PREFIXES): raise HTTPException(status.HTTP_409_CONFLICT, "High-risk access is managed only in Profiles & Privileges.")
    return permission

def _primary_profile(db: Session, user: User, now: datetime) -> Profile:
    assignment = db.scalar(select(UserProfile).join(Profile, Profile.id == UserProfile.profile_id).where(UserProfile.user_id == user.id, UserProfile.is_active.in_([True]), UserProfile.valid_from <= now, or_(UserProfile.valid_to.is_(None), UserProfile.valid_to > now), Profile.is_active.in_([True])).order_by(UserProfile.is_primary.desc(), UserProfile.id))
    if not assignment: raise HTTPException(status.HTTP_409_CONFLICT, "The user has no active permission profile.")
    return assignment.profile

def _profile_impact(db: Session, actor: User, now: datetime) -> tuple[Profile, int]:
    profile = _primary_profile(db, actor, now)
    affected = db.scalar(select(func.count(func.distinct(UserProfile.user_id))).where(UserProfile.profile_id == profile.id, UserProfile.is_active.in_([True]), UserProfile.valid_from <= now, or_(UserProfile.valid_to.is_(None), UserProfile.valid_to > now))) or 0
    return profile, affected

@router.post("", status_code=201)
def create_request(data: RequestCreate, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> dict[str, object]:
    permission = _permission(db, data.permission_code, data.resource)
    if permission.code in effective_permissions(db, actor).permissions:
        raise HTTPException(status.HTTP_409_CONFLICT, "Access is already available.")
    now = server_now()
    pending = db.scalar(select(AccessRequest).where(AccessRequest.requester_user_id == actor.id, AccessRequest.permission_id == permission.id, AccessRequest.resource == data.resource, AccessRequest.status == "PENDING"))
    if pending:
        _expire(pending, now)
        if pending.status == "PENDING":
            return _read(pending, db)
    row = AccessRequest(requester_user_id=actor.id, permission_id=permission.id, resource=data.resource, return_path=data.return_path, justification=data.justification.strip(), expires_at=now + timedelta(days=14))
    db.add(row); db.flush()
    db.add(AccessRequestDecision(access_request_id=row.id, actor_user_id=actor.id, action="REQUESTED", reason=data.justification.strip()))
    db.add(AuditLog(actor_user_id=actor.id, entity_type="AccessRequest", entity_id=str(row.id), action="ACCESS_REQUESTED", reason=data.justification.strip(), new_values_json=f'{{"permission":"{permission.code}","resource":"{data.resource}"}}'))
    for approver in db.scalars(select(User).where(User.is_active.in_([True]), User.id != actor.id)):
        grants = effective_permissions(db, approver).permissions
        if "permission.grant.in_context" in grants and permission.code in grants:
            db.add(Notification(recipient_user_id=approver.id, notification_type="ACCESS_REQUEST", severity="INFO", title="Access request awaiting review", message=f"{actor.full_name} requested {permission.description}.", deep_link="/access-requests", deduplication_key=f"access-request:{row.id}:approver:{approver.id}"))
    db.commit(); db.refresh(row)
    return _read(row, db)

@router.get("")
def list_requests(db: Session = Depends(get_db), actor: User = Depends(current_user)) -> list[dict[str, object]]:
    can_review = "permission.grant.in_context" in effective_permissions(db, actor).permissions
    statement = select(AccessRequest).order_by(AccessRequest.created_at.desc())
    if not can_review: statement = statement.where(AccessRequest.requester_user_id == actor.id)
    rows = list(db.scalars(statement.limit(200)))
    now = server_now()
    for row in rows: _expire(row, now)
    db.commit()
    return [_read(row, db) for row in rows]

@router.get("/grant-impact")
def grant_impact(permission_code: str, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> dict[str, object]:
    permission = db.scalar(select(Permission).where(Permission.code == permission_code, Permission.is_active.in_([True])))
    if not permission: raise HTTPException(status.HTTP_404_NOT_FOUND, "Capability not found.")
    profile, affected = _profile_impact(db, actor, server_now())
    already_assigned = db.get(ProfilePermission, {"profile_id":profile.id,"permission_id":permission.id}) is not None
    return {"profile_id":profile.id,"profile_name":profile.name,"affected_user_count":affected,"permission_code":permission.code,"capability":permission.description,"already_assigned":already_assigned,"eligible":not permission.is_high_risk and not permission.code.startswith(HIGH_RISK_PREFIXES)}

@router.post("/direct-profile-grant", status_code=201)
def direct_profile_grant(data: DirectProfileGrantBody, db: Session = Depends(get_db), settings: Settings = Depends(get_settings), requester: User = Depends(current_user)) -> dict[str, object]:
    permission = _permission(db, data.permission_code, data.resource); now = server_now()
    if permission.code in effective_permissions(db, requester).permissions: raise HTTPException(status.HTTP_409_CONFLICT, "Access is already available.")
    approver = db.scalar(select(User).where(or_(User.username_normalized == normalize(data.approver_login), User.email_normalized == normalize(data.approver_login))))
    if approver and approver.locked_until and approver.locked_until.replace(tzinfo=server_timezone()) > now: raise HTTPException(status.HTTP_423_LOCKED, "Approver account is temporarily locked.")
    if not approver or not approver.is_active or not verify_password(data.approver_password, approver.password_hash):
        if approver:
            approver.failed_login_count += 1
            if approver.failed_login_count >= settings.login_max_failures: approver.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
        db.add(AuthenticationEvent(user_id=approver.id if approver else None,username_attempted=data.approver_login[:320],event_type="IN_CONTEXT_GRANT_FAILED"));db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Approver credentials are invalid.")
    grants = effective_permissions(db, approver).permissions
    if "permission.grant.in_context" not in grants or permission.code not in grants: raise HTTPException(status.HTTP_403_FORBIDDEN, "This approver cannot grant the required capability.")
    if approver.id == requester.id: raise HTTPException(status.HTTP_403_FORBIDDEN, "Self-grant is not allowed.")
    profile, affected = _profile_impact(db, requester, now)
    if not db.get(ProfilePermission, {"profile_id":profile.id,"permission_id":permission.id}): db.add(ProfilePermission(profile_id=profile.id, permission_id=permission.id))
    pending = db.scalar(select(AccessRequest).where(AccessRequest.requester_user_id == requester.id, AccessRequest.permission_id == permission.id, AccessRequest.resource == data.resource, AccessRequest.status == "PENDING"))
    row = pending or AccessRequest(requester_user_id=requester.id,permission_id=permission.id,resource=data.resource,return_path=data.return_path,justification=data.reason.strip(),status="APPROVED",expires_at=now + timedelta(days=14))
    if not pending: db.add(row);db.flush()
    row.status="APPROVED";row.decided_at=now
    approver.failed_login_count=0;approver.locked_until=None
    db.add(AccessRequestDecision(access_request_id=row.id,actor_user_id=approver.id,action="DIRECT_GRANTED",reason=data.reason.strip()))
    evidence={"permission":permission.code,"profile_id":profile.id,"profile_name":profile.name,"affected_user_count":affected,"source_action":"DIRECT_GRANTED"}
    db.add(AuditLog(actor_user_id=approver.id,entity_type="AccessRequest",entity_id=str(row.id),action="ACCESS_DIRECT_PROFILE_GRANTED",reason=data.reason.strip(),new_values_json=json.dumps(evidence)))
    db.add(AuthenticationEvent(user_id=approver.id,username_attempted=approver.username,event_type="IN_CONTEXT_GRANT_SUCCEEDED",detail=f"request={row.id};profile={profile.id};permission={permission.code}"))
    db.add(Notification(recipient_user_id=requester.id,notification_type="ACCESS_REQUEST_APPROVED",severity="INFO",title="Profile access granted",message=f"{permission.description} was added to profile {profile.name}.",deep_link=data.return_path,deduplication_key=f"access-request:{row.id}:direct-granted"))
    db.commit();db.refresh(row)
    result=_read(row,db);result.update({"profile_id":profile.id,"profile_name":profile.name,"affected_user_count":affected})
    return result

@router.post("/step-up")
def step_up(data: ChallengeBody, db: Session = Depends(get_db), settings: Settings = Depends(get_settings), actor: User = Depends(require_permission("permission.grant.in_context"))) -> dict[str, object]:
    now = server_now()
    if actor.locked_until and actor.locked_until > now:
        raise HTTPException(status.HTTP_423_LOCKED, "Account is temporarily locked.")
    if not verify_password(data.password, actor.password_hash):
        actor.failed_login_count += 1
        if actor.failed_login_count >= settings.login_max_failures: actor.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Password confirmation failed.")
    actor.failed_login_count = 0
    raw = secrets.token_urlsafe(36)
    db.add(PermissionStepUpChallenge(actor_user_id=actor.id, token_hash=hashlib.sha256(raw.encode()).hexdigest(), expires_at=now + timedelta(minutes=5)))
    db.commit()
    return {"challenge_token":raw,"expires_at":now + timedelta(minutes=5)}

def _request_for_decision(request_id: int, db: Session) -> AccessRequest:
    row = db.get(AccessRequest, request_id)
    if not row: raise HTTPException(status.HTTP_404_NOT_FOUND, "Access request not found.")
    _expire(row, server_now())
    if row.status != "PENDING": raise HTTPException(status.HTTP_409_CONFLICT, "This request is no longer pending.")
    return row

@router.post("/{request_id}/approve")
def approve(request_id: int, data: DecisionBody, db: Session = Depends(get_db), actor: User = Depends(require_permission("permission.grant.in_context"))) -> dict[str, object]:
    row = _request_for_decision(request_id, db); now = server_now()
    if row.requester_user_id == actor.id: raise HTTPException(status.HTTP_403_FORBIDDEN, "Self-approval is not allowed.")
    if row.permission.is_high_risk or row.permission.code.startswith(HIGH_RISK_PREFIXES): raise HTTPException(status.HTTP_409_CONFLICT, "High-risk access must be granted in Profiles & Privileges.")
    if row.permission.code not in effective_permissions(db, actor).permissions: raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot grant a capability you do not hold.")
    token_hash = hashlib.sha256((data.challenge_token or "").encode()).hexdigest()
    challenge = db.scalar(select(PermissionStepUpChallenge).where(PermissionStepUpChallenge.actor_user_id == actor.id, PermissionStepUpChallenge.token_hash == token_hash, PermissionStepUpChallenge.consumed_at.is_(None), PermissionStepUpChallenge.expires_at > now))
    if not challenge: raise HTTPException(status.HTTP_401_UNAUTHORIZED, "A valid password confirmation is required.")
    target = db.get(User, row.requester_user_id)
    if not target or not target.is_active: raise HTTPException(status.HTTP_409_CONFLICT, "The requester is inactive.")
    challenge.consumed_at = now
    grant_expiry = now + timedelta(days=data.grant_days)
    db.add(UserPermissionOverride(user_id=target.id, permission_id=row.permission_id, effect=Effect.ALLOW, valid_from=now, valid_to=grant_expiry, reason=data.reason.strip(), approved_by_user_id=actor.id, created_by_user_id=actor.id))
    row.status="APPROVED"; row.decided_at=now
    db.add(AccessRequestDecision(access_request_id=row.id, actor_user_id=actor.id, action="APPROVED", reason=data.reason.strip(), grant_expires_at=grant_expiry))
    db.add(AuditLog(actor_user_id=actor.id, entity_type="AccessRequest", entity_id=str(row.id), action="ACCESS_APPROVED", reason=data.reason.strip(), new_values_json=f'{{"user_id":{target.id},"permission":"{row.permission.code}","expires_at":"{grant_expiry.isoformat()}"}}'))
    db.add(Notification(recipient_user_id=target.id, notification_type="ACCESS_REQUEST_APPROVED", severity="INFO", title="Access request approved", message=f"Your access to {row.permission.description} was approved until {grant_expiry.date().isoformat()}.", deep_link=row.return_path, deduplication_key=f"access-request:{row.id}:approved"))
    db.commit()
    return _read(row, db)

@router.post("/{request_id}/deny")
def deny(request_id: int, data: DecisionBody, db: Session = Depends(get_db), actor: User = Depends(require_permission("permission.grant.in_context"))) -> dict[str, object]:
    row=_request_for_decision(request_id,db)
    if row.requester_user_id == actor.id: raise HTTPException(status.HTTP_403_FORBIDDEN,"Self-decision is not allowed.")
    row.status="DENIED"; row.decided_at=server_now()
    db.add(AccessRequestDecision(access_request_id=row.id,actor_user_id=actor.id,action="DENIED",reason=data.reason.strip()))
    db.add(Notification(recipient_user_id=row.requester_user_id, notification_type="ACCESS_REQUEST_DENIED", severity="INFO", title="Access request denied", message=f"Your request for {row.permission.description} was denied.", deep_link="/notifications", deduplication_key=f"access-request:{row.id}:denied"))
    db.commit(); return _read(row, db)

@router.post("/{request_id}/cancel")
def cancel(request_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> dict[str, object]:
    row=_request_for_decision(request_id,db)
    if row.requester_user_id != actor.id: raise HTTPException(status.HTTP_403_FORBIDDEN,"Only the requester can cancel this request.")
    row.status="CANCELLED"; row.decided_at=server_now()
    db.add(AccessRequestDecision(access_request_id=row.id,actor_user_id=actor.id,action="CANCELLED",reason="Cancelled by requester"))
    db.commit(); return _read(row, db)

@router.get("/effective-permissions")
def refreshed_permissions(db: Session = Depends(get_db), actor: User = Depends(current_user)) -> dict[str, object]:
    return effective_permissions(db, actor).model_dump()
