from datetime import datetime, time

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.clock import server_now, server_timezone, server_today
from app.core.exceptions import ConflictError
from app.modules.contracts.access import can_access_contract, can_receive_renewal
from app.modules.contracts.lifecycle import recalculate_client_contract_service_status
from app.modules.contracts.models import (
    Contract,
    ContractCoverage,
    ContractRenewalLine,
    ContractRenewalOpportunity,
    ContractRenewalTask,
    SlaPolicy,
    SlaTarget,
)
from app.modules.contracts.schemas import RenewalOpportunityUpdate
from app.modules.contracts.service import CONTEXT_FIELDS
from app.modules.iam.models import User
from app.modules.notifications.models import Notification
from app.modules.visits.models import ClientVisitEntitlement


def validate_renewal_owner(db: Session, owner_id: int, contract: Contract) -> User:
    owner = db.get(User, owner_id)
    if not owner or not can_receive_renewal(db, owner, contract):
        raise ConflictError(
            "INVALID_RENEWAL_OWNER",
            "Renewal owner must be an active employee with contract access and permission.",
        )
    return owner


def validate_successor(
    db: Session, source: Contract, successor_id: int, actor: User, *, require_sla_ready: bool = True
) -> Contract:
    successor = db.get(Contract, successor_id)
    if (
        not successor
        or not can_access_contract(db, actor, successor)
        or successor.id == source.id
        or successor.start_date <= source.end_date
        or successor.end_date < server_today()
        or not successor.is_active
        or successor.status not in {"DRAFT", "ACTIVE"}
    ):
        raise ConflictError(
            "INVALID_SUCCESSOR_CONTRACT",
            "Select an active or draft successor starting after the source ends.",
        )
    source_clients = {source.client_id, *source.linked_client_ids}
    successor_clients = {successor.client_id, *successor.linked_client_ids}
    if not successor.applies_to_all_clients and (
        source.applies_to_all_clients or not source_clients.issubset(successor_clients)
    ):
        raise ConflictError(
            "INVALID_SUCCESSOR_CLIENTS",
            "The successor must retain the source contract's customer scope.",
        )
    if require_sla_ready and successor.has_sla:
        policy = db.get(SlaPolicy, successor.sla_policy_id) if successor.sla_policy_id else None
        if not policy or not policy.is_active or policy.contract_id not in {None, successor.id}:
            raise ConflictError(
                "SUCCESSOR_SLA_NOT_READY",
                "Configure an active SLA for the successor before completing renewal.",
            )
        if not db.scalar(select(SlaTarget.id).where(SlaTarget.policy_id == policy.id).limit(1)):
            raise ConflictError(
                "SUCCESSOR_SLA_NOT_READY",
                "The successor SLA requires targets before completing renewal.",
            )
    return successor


def apply_renewal_update(
    db: Session,
    contract: Contract,
    item: ContractRenewalOpportunity,
    data: RenewalOpportunityUpdate,
    actor: User,
) -> None:
    """Validate and apply both workspace and board changes in the caller's transaction."""
    if item.version != data.version:
        raise ConflictError("STALE_RENEWAL", "The renewal changed; refresh and retry.")
    if item.stage == "CLOSED":
        raise ConflictError(
            "RENEWAL_CLOSED", "A closed renewal cannot be edited. Start a new opportunity."
        )
    claimed = db.execute(
        update(ContractRenewalOpportunity)
        .where(
            ContractRenewalOpportunity.id == item.id,
            ContractRenewalOpportunity.version == data.version,
            ContractRenewalOpportunity.stage != "CLOSED",
        )
        .values(version=data.version + 1)
        .returning(ContractRenewalOpportunity.id),
        execution_options={"synchronize_session": False},
    ).scalar_one_or_none()
    if claimed is None:
        raise ConflictError("STALE_RENEWAL", "The renewal changed; refresh and retry.")
    closing = data.stage == "CLOSED"
    if closing and not data.outcome:
        raise ConflictError("RENEWAL_OUTCOME_REQUIRED", "A closed renewal requires an outcome.")
    if not closing and data.outcome:
        raise ConflictError(
            "INVALID_RENEWAL_OUTCOME", "Only a closed renewal can have a final outcome."
        )
    retained_outcomes = {"RENEWED", "CHANGED"}
    success = data.outcome in {"RENEWED", "PARTIAL"}
    if closing and success and not data.successor_contract_id:
        raise ConflictError("SUCCESSOR_REQUIRED", "Select a successor before completing renewal.")
    if closing and not success and data.successor_contract_id:
        raise ConflictError(
            "INVALID_SUCCESSOR_CONTRACT", "Lost or cancelled renewals cannot select a successor."
        )
    successor = (
        validate_successor(db, contract, data.successor_contract_id, actor, require_sla_ready=closing)
        if data.successor_contract_id
        else None
    )
    owner = validate_renewal_owner(db, data.owner_user_id or item.owner_user_id, contract)
    lines = {
        line.coverage_id: line
        for line in db.scalars(
            select(ContractRenewalLine).where(ContractRenewalLine.opportunity_id == item.id)
        )
    }
    if len({line.coverage_id for line in data.lines}) != len(data.lines):
        raise ConflictError("INVALID_RENEWAL_LINE", "Each coverage line may appear only once.")
    for change in data.lines:
        line = lines.get(change.coverage_id)
        if not line:
            raise ConflictError(
                "INVALID_RENEWAL_LINE", "The coverage line is not part of this opportunity."
            )
        line.outcome, line.successor_coverage_id, line.reason = (
            change.outcome,
            change.successor_coverage_id,
            change.reason,
        )
    for line in lines.values():
        mapped = (
            db.get(ContractCoverage, line.successor_coverage_id)
            if line.successor_coverage_id
            else None
        )
        if line.successor_coverage_id and (
            not mapped
            or not successor
            or mapped.contract_id != successor.id
            or mapped.retired_at is not None
            or not mapped.is_covered
            or (mapped.effective_from is not None and mapped.effective_from > successor.start_date)
            or (
                mapped.effective_until is not None and mapped.effective_until < successor.start_date
            )
        ):
            raise ConflictError(
                "INVALID_SUCCESSOR_COVERAGE",
                "Select covered, non-retired coverage from the successor contract.",
            )
        if closing and (
            line.outcome == "PENDING" or (line.outcome in retained_outcomes and not mapped)
        ):
            raise ConflictError(
                "RENEWAL_LINES_INCOMPLETE",
                "Resolve every line and map retained coverage to the successor.",
            )
        source_coverage = db.get(ContractCoverage, line.coverage_id)
        if (
            line.outcome == "RENEWED"
            and mapped
            and source_coverage
            and any(
                getattr(source_coverage, field) != getattr(mapped, field)
                for field in CONTEXT_FIELDS
            )
        ):
            raise ConflictError(
                "INVALID_SUCCESSOR_COVERAGE",
                "Use Changed when the successor coverage has different products or services.",
            )
        if line.outcome in {"LOST", "EXCLUDED"} and line.successor_coverage_id:
            raise ConflictError(
                "INVALID_SUCCESSOR_COVERAGE",
                "Lost or excluded lines cannot retain successor coverage.",
            )
    outcomes = {line.outcome for line in lines.values()}
    if closing and (
        (data.outcome == "RENEWED" and bool(outcomes - retained_outcomes))
        or (data.outcome in {"LOST", "CANCELLED"} and bool(outcomes & retained_outcomes))
        or (
            data.outcome == "PARTIAL"
            and not (outcomes & retained_outcomes and outcomes & {"LOST", "EXCLUDED"})
        )
    ):
        raise ConflictError(
            "INVALID_RENEWAL_OUTCOME",
            "The final outcome must agree with all coverage-line outcomes.",
        )
    previous_owner_id = item.owner_user_id
    item.stage, item.outcome, item.successor_contract_id = (
        data.stage,
        data.outcome,
        data.successor_contract_id,
    )
    item.owner_user_id = owner.id
    item.target_close_date = data.target_close_date or item.target_close_date
    item.reason, item.version = data.reason, item.version + 1
    item.closed_at = server_now() if closing else None
    for task in db.scalars(
        select(ContractRenewalTask).where(ContractRenewalTask.opportunity_id == item.id)
    ):
        task.assigned_user_id = owner.id
        task.due_at = datetime.combine(item.target_close_date, time(17), tzinfo=server_timezone())
        task.status = "COMPLETED" if closing else "OPEN"
        task.completed_at = item.closed_at
    # Signing a future renewal must not remove the current term's entitlement.
    if closing and successor:
        successor.status = "ACTIVE"
    if closing and contract.end_date < server_today():
        contract.status, contract.is_active = "EXPIRED", False
        for entitlement in db.scalars(
            select(ClientVisitEntitlement).where(
                ClientVisitEntitlement.contract_id == contract.id,
                ClientVisitEntitlement.status == "ACTIVE",
            )
        ):
            entitlement.status = "EXPIRED"
    for recipient_id in {owner.id, previous_owner_id, item.created_by_user_id}:
        recipient = db.get(User, recipient_id)
        if recipient and can_receive_renewal(db, recipient, contract):
            db.add(
                Notification(
                    recipient_user_id=recipient.id,
                    notification_type="CONTRACT_RENEWAL_UPDATED",
                    severity="WARNING" if data.outcome == "LOST" else "INFO",
                    title=f"Renewal {data.outcome or data.stage}: {contract.contract_number}",
                    message=data.reason,
                    deep_link=f"/contracts?section=contracts&contract_id={contract.id}&tab=renewals",
                    deduplication_key=f"renewal-update:{item.id}:v{item.version}:u{recipient.id}",
                )
            )
    recalculate_client_contract_service_status(
        db, {contract.client_id, *contract.linked_client_ids}
    )
