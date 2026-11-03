import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.entitlements.models import (
    ApprovalGroup,
    ApprovalGroupMember,
    EntitlementApproval,
    EntitlementApprovalHistory,
)
from app.modules.entitlements.schemas import (
    ApprovalConsumeWrite,
    ApprovalCreate,
    ApprovalDecisionWrite,
    ApprovalGroupRead,
    ApprovalGroupWrite,
    ApprovalHistoryRead,
    ApprovalRead,
    ApprovalRevokeWrite,
)
from app.modules.iam.models import AuditLog, Profile, User, UserProfile
from app.modules.iam.service import effective_permissions
from app.modules.notifications.models import Notification
from app.modules.tickets.models import Ticket

router = APIRouter(prefix="/entitlement-approvals", tags=["entitlement approvals"])


def serialize_approval(db: Session, item: EntitlementApproval) -> ApprovalRead:
    history = list(db.scalars(select(EntitlementApprovalHistory).where(
        EntitlementApprovalHistory.approval_id == item.id
    ).order_by(EntitlementApprovalHistory.created_at, EntitlementApprovalHistory.id)))
    return ApprovalRead(
        **{column.name: getattr(item, column.name) for column in EntitlementApproval.__table__.columns
           if column.name not in {"request_payload_json", "evidence_json"}},
        request_payload=json.loads(item.request_payload_json),
        evidence=json.loads(item.evidence_json),
        history=[ApprovalHistoryRead.model_validate(row) for row in history],
    )


@router.post("", response_model=ApprovalRead, status_code=201)
def create_approval(
    data: ApprovalCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("entitlement_approval.request")),
) -> ApprovalRead:
    existing = db.scalar(select(EntitlementApproval).where(
        EntitlementApproval.idempotency_key == data.idempotency_key
    ))
    if existing:
        return serialize_approval(db, existing)
    item = EntitlementApproval(
        **data.model_dump(exclude={"request_payload", "evidence", "operation_scope"}),
        request_payload_json=json.dumps(data.request_payload, separators=(",", ":"), sort_keys=True),
        evidence_json=json.dumps(data.evidence, separators=(",", ":"), sort_keys=True),
        requested_by_user_id=actor.id,
        operation_scope=data.operation_scope or f"CLIENT:{data.client_id}:{data.requested_action}",
        version=1,
    )
    db.add(item)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(EntitlementApproval).where(
            EntitlementApproval.idempotency_key == data.idempotency_key
        ))
        if not existing:
            raise
        return serialize_approval(db, existing)
    db.add(EntitlementApprovalHistory(
        approval_id=item.id, from_status=None, to_status="PENDING",
        actor_user_id=actor.id, comment=data.justification,
    ))
    db.add(AuditLog(
        actor_user_id=actor.id, entity_type="EntitlementApproval", entity_id=str(item.id),
        action="entitlement_approval.requested",
        new_values_json=json.dumps({"reason_code": item.reason_code, "policy_version": item.policy_version}),
    ))
    db.commit()
    db.refresh(item)
    return serialize_approval(db, item)


@router.get("", response_model=list[ApprovalRead])
def list_approvals(
    request_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("entitlement_approval.view")),
) -> list[ApprovalRead]:
    statement = select(EntitlementApproval)
    if request_status:
        statement = statement.where(EntitlementApproval.status == request_status)
    items = list(db.scalars(statement.order_by(EntitlementApproval.created_at.desc()).limit(limit)))
    return [serialize_approval(db, item) for item in items]


@router.post("/{approval_id}/decision", response_model=ApprovalRead)
def decide_approval(
    approval_id: int, data: ApprovalDecisionWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("entitlement_approval.decide")),
) -> ApprovalRead:
    item = db.get(EntitlementApproval, approval_id)
    if not item:
        raise NotFoundError("The entitlement approval request does not exist.")
    if item.status != "PENDING":
        raise ConflictError("APPROVAL_ALREADY_DECIDED", "Only pending requests can be decided.")
    permissions = set(effective_permissions(db, actor).permissions)
    if actor.id == item.requested_by_user_id and "configuration.manage" not in permissions:
        raise ConflictError("APPROVAL_SEPARATION_REQUIRED", "The requester cannot approve their own exception.")
    if item.approval_group_id and "configuration.manage" not in permissions and not db.scalar(select(ApprovalGroupMember.id).where(ApprovalGroupMember.group_id == item.approval_group_id, ApprovalGroupMember.user_id == actor.id)):
        raise ConflictError("APPROVER_OUT_OF_SCOPE", "This request belongs to a different approval group.")
    if item.approval_deadline and item.approval_deadline < server_now():
        item.status = "EXPIRED"
        db.add(EntitlementApprovalHistory(
            approval_id=item.id, from_status="PENDING", to_status="EXPIRED",
            actor_user_id=actor.id, comment="Approval deadline elapsed.",
        ))
        db.commit()
        raise ConflictError("APPROVAL_EXPIRED", "The approval deadline has elapsed.")
    previous = item.status
    item.status = data.decision
    item.decided_by_user_id = actor.id
    item.decision_comment = data.comment
    item.decided_at = server_now()
    item.version += 1
    if item.ticket_id:
        ticket = db.get(Ticket, item.ticket_id)
        if ticket and ticket.entitlement_status == "PENDING_APPROVAL":
            ticket.entitlement_status = "OVERRIDDEN" if data.decision == "APPROVED" else "EXCLUDED"
            ticket.entitlement_override_reason = data.comment
            if data.decision == "APPROVED":
                item.consumed_by_user_id = actor.id
                item.consumed_at = item.decided_at
    db.add(EntitlementApprovalHistory(
        approval_id=item.id, from_status=previous, to_status=data.decision,
        actor_user_id=actor.id, comment=data.comment,
    ))
    db.add(AuditLog(
        actor_user_id=actor.id, entity_type="EntitlementApproval", entity_id=str(item.id),
        action=f"entitlement_approval.{data.decision.lower()}",
        new_values_json=json.dumps({"status": data.decision, "comment": data.comment}),
    ))
    db.add(Notification(
        recipient_user_id=item.requested_by_user_id,
        notification_type="ENTITLEMENT_APPROVAL_DECIDED",
        severity="INFO" if data.decision == "APPROVED" else "WARNING",
        title=f"Exception request {data.decision.lower()}",
        message=data.comment,
        deep_link=f"/tickets/{item.ticket_id}" if item.ticket_id else f"/tickets?tab=approvals&approval_id={item.id}",
        deduplication_key=f"approval-decision:{item.id}:{data.decision}",
    ))
    db.commit()
    db.refresh(item)
    return serialize_approval(db, item)


@router.post("/{approval_id}/consume", response_model=ApprovalRead)
def consume_approval(approval_id: int, data: ApprovalConsumeWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("entitlement_approval.request"))) -> ApprovalRead:
    item = db.get(EntitlementApproval, approval_id)
    if not item: raise NotFoundError("The entitlement approval request does not exist.")
    if item.status != "APPROVED" or item.revoked_at or item.consumed_at:
        raise ConflictError("APPROVAL_NOT_CONSUMABLE", "The approval is not approved, was revoked, or was already consumed.")
    if item.version != data.version: raise ConflictError("STALE_APPROVAL", "The approval changed; refresh and retry.")
    if item.operation_scope != data.operation_scope: raise ConflictError("APPROVAL_SCOPE_MISMATCH", "The approval cannot be used for this operation.")
    if item.approval_deadline and item.approval_deadline < server_now(): raise ConflictError("APPROVAL_EXPIRED", "The approval deadline has elapsed.")
    item.consumed_by_user_id = actor.id; item.consumed_at = server_now(); item.version += 1
    db.add(EntitlementApprovalHistory(approval_id=item.id, from_status="APPROVED", to_status="COMPLETED", actor_user_id=actor.id, comment=data.comment))
    db.add(AuditLog(actor_user_id=actor.id, entity_type="EntitlementApproval", entity_id=str(item.id), action="entitlement_approval.consumed", reason=data.comment, new_values_json=json.dumps({"operation_scope": data.operation_scope})))
    db.commit(); db.refresh(item)
    return serialize_approval(db, item)


@router.post("/{approval_id}/revoke", response_model=ApprovalRead)
def revoke_approval(approval_id: int, data: ApprovalRevokeWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("entitlement_approval.decide"))) -> ApprovalRead:
    item = db.get(EntitlementApproval, approval_id)
    if not item: raise NotFoundError("The entitlement approval request does not exist.")
    if item.status != "APPROVED" or item.consumed_at or item.revoked_at: raise ConflictError("APPROVAL_NOT_REVOCABLE", "Only an unconsumed approval can be revoked.")
    if item.version != data.version: raise ConflictError("STALE_APPROVAL", "The approval changed; refresh and retry.")
    item.status = "CANCELLED"; item.revoked_by_user_id = actor.id; item.revoked_at = server_now(); item.version += 1
    db.add(EntitlementApprovalHistory(approval_id=item.id, from_status="APPROVED", to_status="CANCELLED", actor_user_id=actor.id, comment=data.comment))
    db.add(AuditLog(actor_user_id=actor.id, entity_type="EntitlementApproval", entity_id=str(item.id), action="entitlement_approval.revoked", reason=data.comment))
    db.commit(); db.refresh(item)
    return serialize_approval(db, item)


@router.post("/expire-overdue")
def expire_overdue_approvals(db: Session = Depends(get_db), actor: User = Depends(require_permission("entitlement_approval.decide"))) -> dict[str, int]:
    now = server_now()
    items = list(db.scalars(select(EntitlementApproval).where(EntitlementApproval.status == "PENDING", EntitlementApproval.approval_deadline.is_not(None), EntitlementApproval.approval_deadline < now)))
    for item in items:
        item.status = "EXPIRED"; item.version += 1
        db.add(EntitlementApprovalHistory(approval_id=item.id, from_status="PENDING", to_status="EXPIRED", actor_user_id=actor.id, comment="Approval deadline elapsed."))
        db.add(Notification(recipient_user_id=item.requested_by_user_id, notification_type="ENTITLEMENT_APPROVAL_EXPIRED", severity="WARNING", title="Exception request expired", message="The exception was not approved before its deadline.", deep_link=f"/tickets?tab=approvals&approval_id={item.id}", deduplication_key=f"approval-expired:{item.id}"))
    if items:
        db.add(AuditLog(actor_user_id=actor.id, entity_type="EntitlementApproval", entity_id="overdue", action="entitlement_approval.expired_batch", new_values_json=json.dumps({"count": len(items)})))
    db.commit()
    return {"expired": len(items)}


@router.post("/{approval_id}/reminder", response_model=ApprovalRead)
def remind_approvers(
    approval_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("entitlement_approval.view")),
) -> ApprovalRead:
    item = db.get(EntitlementApproval, approval_id)
    if not item:
        raise NotFoundError("The entitlement approval request does not exist.")
    if item.status != "PENDING":
        raise ConflictError("APPROVAL_ALREADY_DECIDED", "Only pending requests can receive reminders.")
    recipients = set(db.scalars(
        select(UserProfile.user_id).join(Profile, Profile.id == UserProfile.profile_id).where(
            UserProfile.is_active.in_([True]), Profile.code == "SUPPORT_MANAGER"
        )
    ))
    if item.approval_group_id:
        recipients.update(db.scalars(select(ApprovalGroupMember.user_id).where(
            ApprovalGroupMember.group_id == item.approval_group_id
        )))
    ticket = db.get(Ticket, item.ticket_id) if item.ticket_id else None
    now = server_now()
    for recipient_id in recipients - {actor.id}:
        db.add(Notification(
            recipient_user_id=recipient_id,
            notification_type="ENTITLEMENT_APPROVAL_REMINDER",
            severity="WARNING",
            title=f"Approval reminder: {ticket.ticket_number if ticket else f'Request #{item.id}'}",
            message=f"{actor.full_name} requested a decision for an out-of-contract ticket.",
            deep_link=f"/tickets?tab=approvals&approval_id={item.id}",
            deduplication_key=f"approval-reminder:{item.id}:{recipient_id}:{now.strftime('%Y%m%d%H%M')}",
        ))
    db.add(EntitlementApprovalHistory(
        approval_id=item.id, from_status="PENDING", to_status="PENDING",
        actor_user_id=actor.id, comment="Approval reminder sent to the responsible managers.",
    ))
    db.add(AuditLog(
        actor_user_id=actor.id, entity_type="EntitlementApproval", entity_id=str(item.id),
        action="entitlement_approval.reminder_sent",
        new_values_json=json.dumps({"recipient_count": len(recipients - {actor.id})}),
    ))
    db.commit()
    db.refresh(item)
    return serialize_approval(db, item)


@router.get("/groups", response_model=list[ApprovalGroupRead])
def list_groups(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("entitlement_approval.manage")),
) -> list[ApprovalGroupRead]:
    groups = list(db.scalars(select(ApprovalGroup).order_by(ApprovalGroup.name)))
    members = list(db.scalars(select(ApprovalGroupMember)))
    return [ApprovalGroupRead(
        id=group.id, code=group.code, name=group.name, is_active=group.is_active,
        member_user_ids=[member.user_id for member in members if member.group_id == group.id],
    ) for group in groups]


@router.post("/groups", response_model=ApprovalGroupRead, status_code=201)
def create_group(
    data: ApprovalGroupWrite, db: Session = Depends(get_db),
    actor: User = Depends(require_permission("entitlement_approval.manage")),
) -> ApprovalGroupRead:
    if data.code and db.scalar(select(ApprovalGroup.id).where(ApprovalGroup.code == data.code)):
        raise ConflictError("DUPLICATE_APPROVAL_GROUP", "An approval group with this code already exists.")
    group = ApprovalGroup(code=data.code or f"PENDING-AGR-{server_now().timestamp()}", name=data.name, is_active=data.is_active)
    db.add(group); db.flush()
    if not data.code:
        group.code = f"AGR-{group.id:06d}"
    for user_id in set(data.member_user_ids):
        if not db.get(User, user_id):
            raise NotFoundError("An approval-group member does not exist.")
        db.add(ApprovalGroupMember(group_id=group.id, user_id=user_id))
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ApprovalGroup", entity_id=str(group.id), action="approval_group.created", new_values_json=json.dumps(data.model_dump())))
    db.commit(); db.refresh(group)
    return ApprovalGroupRead(id=group.id, code=group.code, name=group.name, is_active=group.is_active, member_user_ids=list(set(data.member_user_ids)))
