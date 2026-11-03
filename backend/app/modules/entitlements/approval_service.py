import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.entitlements.models import EntitlementApproval, EntitlementApprovalHistory
from app.modules.iam.models import AuditLog, User


def create_idempotent_approval(
    db: Session, *, idempotency_key: str, source_channel: str, reason_code: str,
    justification: str, request_payload: dict[str, object], evidence: dict[str, object],
    feature_mode: str, policy_id: int | None, policy_version: int,
    policy_scope: str, client_id: int, contract_id: int | None, actor: User,
) -> EntitlementApproval:
    existing = db.scalar(select(EntitlementApproval).where(
        EntitlementApproval.idempotency_key == idempotency_key
    ))
    if existing:
        return existing
    item = EntitlementApproval(
        idempotency_key=idempotency_key, source_channel=source_channel, status="PENDING",
        reason_code=reason_code, requested_action="REQUIRE_APPROVAL",
        justification=justification,
        request_payload_json=json.dumps(request_payload, separators=(",", ":"), sort_keys=True),
        evidence_json=json.dumps(evidence, separators=(",", ":"), sort_keys=True),
        feature_mode=feature_mode, policy_id=policy_id, policy_version=policy_version,
        policy_scope=policy_scope, client_id=client_id, contract_id=contract_id,
        requested_by_user_id=actor.id,
        operation_scope=f"CLIENT:{client_id}:REQUIRE_APPROVAL",
        version=1,
    )
    db.add(item); db.flush()
    db.add(EntitlementApprovalHistory(
        approval_id=item.id, from_status=None, to_status="PENDING",
        actor_user_id=actor.id, comment=justification,
    ))
    db.add(AuditLog(
        actor_user_id=actor.id, entity_type="EntitlementApproval", entity_id=str(item.id),
        action="entitlement_approval.requested",
        new_values_json=json.dumps({"reason_code": reason_code, "source_channel": source_channel}),
    ))
    db.commit(); db.refresh(item)
    return item
