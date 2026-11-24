import json
import uuid
from datetime import date, datetime, time, timedelta
from hashlib import sha256
from typing import Annotated, Any

from pydantic import BeforeValidator
from sqlalchemy import Integer, and_, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import ColumnElement

from app.core.clock import server_now, server_timezone, server_today
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.modules.clients.models import (
    Branch,
    Client,
    ClientStatus,
    Contact,
    ContactClientLink,
    Environment,
    Product,
    ProductModule,
    ServiceCatalogItem,
    ServiceModuleLink,
    SupportTeam,
    SupportTeamMember,
    TicketCategory,
    TicketSubcategory,
)
from app.modules.configuration.models import SiteSetting
from app.modules.configuration.policy_service import resolve_feature_policy
from app.modules.configuration.ticket_form import validate_required_ticket_fields
from app.modules.contracts.models import (
    Contract,
    ContractCoverage,
    SlaPolicy,
    SlaPolicyVersion,
    SlaShadowComparison,
    SlaTarget,
    SlaTargetVersion,
    TicketSlaClock,
    TicketSlaInterval,
)
from app.modules.contracts.service import (
    calculate_due_at,
    calculate_working_minutes,
    evaluate_entitlement,
    resolve_product_scoped_sla_target,
)
from app.modules.entitlements.models import (
    ApprovalGroupMember,
    EntitlementApproval,
    EntitlementApprovalHistory,
)
from app.modules.iam.models import AuditLog, Profile, User, UserProfile
from app.modules.iam.service import effective_permissions
from app.modules.notifications.models import EventOutbox, Notification
from app.modules.notifications.ticket_creation import queue_ticket_creation_email
from app.modules.tickets.models import (
    ResolutionOutcome,
    RootCause,
    Ticket,
    TicketAssignmentHistory,
    TicketChecklistItem,
    TicketFollower,
    TicketResolutionHistory,
    TicketResolutionService,
    TicketRootCause,
    TicketShiftHandover,
    TicketStatus,
    TicketStatusHistory,
    TicketTask,
    TicketType,
)
from app.modules.tickets.schemas import (
    TicketCreate,
    TicketFilterGroup,
    TicketFilterRule,
    TicketTransition,
)
from app.modules.tickets.workflow import validate_transition
from app.modules.uat.models import UatDefectLink

SLA_EXEMPT_TICKET_TYPE_CODES = {"CHANGE_REQUEST"}


def ticket_type_uses_sla(ticket_type: TicketType | None) -> bool:
    return ticket_type is not None and ticket_type.code not in SLA_EXEMPT_TICKET_TYPE_CODES


def _parse_date_time_boundary(value: object) -> object:
    if not isinstance(value, str):
        return value
    return datetime.fromisoformat(value) if "T" in value or " " in value else date.fromisoformat(value)


DateTimeBoundary = Annotated[date | datetime, BeforeValidator(_parse_date_time_boundary)]


def ticket_filter_lower_bound(value: DateTimeBoundary) -> datetime:
    """Return an exact datetime boundary, or midnight for a legacy date value."""
    if isinstance(value, datetime):
        return (
            value.astimezone(server_timezone())
            if value.tzinfo is not None
            else value.replace(tzinfo=server_timezone())
        )
    return datetime.combine(value, time.min, tzinfo=server_timezone())


def ticket_filter_upper_bound(value: DateTimeBoundary) -> tuple[datetime, bool]:
    """Return the upper boundary and whether it is exclusive."""
    if isinstance(value, datetime):
        boundary = (
            value.astimezone(server_timezone())
            if value.tzinfo is not None
            else value.replace(tzinfo=server_timezone())
        )
        return boundary, False
    return datetime.combine(value + timedelta(days=1), time.min, tzinfo=server_timezone()), True


def current_sla_version_id(db: Session, policy: SlaPolicy) -> int:
    version = db.scalar(select(SlaPolicyVersion).where(
        SlaPolicyVersion.policy_id == policy.id,
        SlaPolicyVersion.version == policy.version,
        SlaPolicyVersion.status == "PUBLISHED",
    ))
    if version is None or db.scalar(select(SlaTargetVersion.id).where(
        SlaTargetVersion.policy_version_id == version.id
    )) is None:
        raise ConflictError(
            "SLA_POLICY_NOT_PUBLISHED",
            "The SLA must have a current published version with targets.",
        )
    return version.id

PRIORITY_SCORE = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
FIRST_RESPONSE_START_TICKET_CREATED = "TICKET_CREATED"
FIRST_RESPONSE_START_DEDICATED_ASSIGNMENT = "FIRST_DEDICATED_ASSIGNMENT"
PENDING_RESPONSIBLE_PARTIES = {
    "PENDING_CLIENT": "CUSTOMER",
    "PENDING_INTERNAL": "MILLENSYS",
    "PENDING_VENDOR": "MILLENSYS",
}


def first_response_start_mode(db: Session) -> str:
    row = db.get(SiteSetting, "first_response_start_mode")
    if row and row.value == FIRST_RESPONSE_START_DEDICATED_ASSIGNMENT:
        return FIRST_RESPONSE_START_DEDICATED_ASSIGNMENT
    return FIRST_RESPONSE_START_TICKET_CREATED


def pending_responsible_party(status_code: str, explicit_party: str | None) -> str:
    """Resolve and validate the contractual owner for a pending lifecycle state."""
    expected = PENDING_RESPONSIBLE_PARTIES.get(status_code)
    if expected is None:
        raise ConflictError(
            "PENDING_STATUS_INVALID", "The requested status is not a supported pending state."
        )
    if explicit_party is not None and explicit_party != expected:
        raise ConflictError(
            "PENDING_RESPONSIBLE_PARTY_MISMATCH",
            f"{status_code} requires responsible party {expected}.",
        )
    return expected


def is_dedicated_assignee(db: Session, user_id: int | None) -> bool:
    """Return whether an employee assignment represents dedicated ownership."""
    if user_id is None:
        return False
    configured = db.get(SiteSetting, "default_assignee_user_id")
    if configured and configured.value.isdigit() and int(configured.value) == user_id:
        return False
    assignee = db.get(User, user_id)
    return bool(
        assignee
        and assignee.is_active
        and assignee.user_type == "EMPLOYEE"
        and assignee.username_normalized != "support"
    )


def apply_first_dedicated_assignment(
    db: Session, ticket: Ticket, user_id: int | None, assigned_at: datetime
) -> bool:
    """Start assignment-anchored SLA clocks once, on dedicated ownership."""
    if not is_dedicated_assignee(db, user_id):
        return False
    configured = db.get(SiteSetting, "default_assignee_user_id")
    configured_id = int(configured.value) if configured and configured.value.isdigit() else None
    previous_query = (
        select(TicketAssignmentHistory.id)
        .join(User, User.id == TicketAssignmentHistory.assigned_user_id)
        .where(
            TicketAssignmentHistory.ticket_id == ticket.id,
            TicketAssignmentHistory.assigned_user_id.is_not(None),
            User.username_normalized != "support",
        )
    )
    if configured_id is not None:
        previous_query = previous_query.where(
            TicketAssignmentHistory.assigned_user_id != configured_id
        )
    previous = db.scalar(previous_query.limit(1))
    if previous is not None:
        return False
    response = db.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket.id,
            TicketSlaClock.clock_type == "FIRST_RESPONSE",
            TicketSlaClock.state == "PAUSED",
            TicketSlaClock.start_mode_snapshot == FIRST_RESPONSE_START_DEDICATED_ASSIGNMENT,
        )
    )
    if response:
        policy = db.get(SlaPolicy, response.policy_id)
        if policy:
            response.started_at = assigned_at
            response.start_anchor_at = assigned_at
            response.due_at = calculate_due_at(
                db, response.calendar_id or policy.calendar_id, assigned_at, response.target_minutes
            )
            response.state = "RUNNING"
    resolution = db.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket.id,
            TicketSlaClock.clock_type == "RESOLUTION",
            TicketSlaClock.state.in_(["PAUSED", "RUNNING"]),
        )
    )
    if resolution:
        policy = db.get(SlaPolicy, resolution.policy_id)
        if policy:
            resolution.started_at = assigned_at
            resolution.start_anchor_at = assigned_at
            resolution.due_at = calculate_due_at(
                db, policy.calendar_id, assigned_at, resolution.target_minutes
            )
            resolution.state = "RUNNING"
            resolution.calculation_version = "3.0"
    return True


def record_first_response(
    db: Session, ticket: Ticket, responded_at: datetime | None = None
) -> bool:
    """Complete the first-response clock exactly once for a qualifying response."""
    completed_at = responded_at or server_now()
    clock = db.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket.id,
            TicketSlaClock.clock_type == "FIRST_RESPONSE",
            TicketSlaClock.state == "RUNNING",
            TicketSlaClock.completed_at.is_(None),
        )
    )
    if clock is None:
        return False
    complete_sla_clocks(db, ticket, {"FIRST_RESPONSE"}, completed_at)
    return True


def preview_ticket_sla(
    db: Session,
    ticket: Ticket,
    changes: dict[str, object],
    effective_at: datetime,
) -> dict[str, object]:
    """Resolve the SLA consequence of an edit without changing persisted state."""
    material_fields = {
        "client_id",
        "contract_id",
        "priority",
        "ticket_type_id",
        "product_id",
        "product_module_id",
        "environment_id",
        "service_id",
    }
    changed_fields = sorted(
        field
        for field in material_fields.intersection(changes)
        if changes[field] != getattr(ticket, field)
    )
    response_clock = db.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket.id,
            TicketSlaClock.clock_type == "FIRST_RESPONSE",
        )
    )
    resolution_clock = db.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket.id,
            TicketSlaClock.clock_type == "RESOLUTION",
        )
    )
    result: dict[str, object] = {
        "changes_sla": bool(changed_fields),
        "changed_fields": changed_fields,
        "effective_at": effective_at,
        "old_contract_id": resolution_clock.contract_id if resolution_clock else ticket.contract_id,
        "old_policy_id": resolution_clock.policy_id if resolution_clock else None,
        "old_target_id": resolution_clock.target_id if resolution_clock else None,
        "old_first_response_minutes": response_clock.target_minutes if response_clock else None,
        "old_resolution_minutes": resolution_clock.target_minutes if resolution_clock else None,
    }
    if not changed_fields:
        result.update(
            {
                "new_contract_id": result["old_contract_id"],
                "new_policy_id": result["old_policy_id"],
                "new_target_id": result["old_target_id"],
                "new_first_response_minutes": result["old_first_response_minutes"],
                "new_resolution_minutes": result["old_resolution_minutes"],
                "match_reason": resolution_clock.match_reason if resolution_clock else None,
            }
        )
        return result

    def proposed_id(field: str, current: int | None) -> int | None:
        value = changes.get(field, current)
        return value if isinstance(value, int) else None

    client_id = proposed_id("client_id", ticket.client_id)
    ticket_type_id = proposed_id("ticket_type_id", ticket.ticket_type_id)
    if client_id is None or ticket_type_id is None:
        raise ConflictError("INVALID_TICKET_CONTEXT", "Client and ticket type are required.")
    proposed_ticket_type = db.get(TicketType, ticket_type_id)
    if not ticket_type_uses_sla(proposed_ticket_type):
        result.update(
            {
                "new_contract_id": proposed_id("contract_id", ticket.contract_id),
                "new_policy_id": None,
                "new_target_id": None,
                "new_first_response_minutes": None,
                "new_resolution_minutes": None,
                "match_reason": "TICKET_TYPE_SLA_EXEMPT",
            }
        )
        return result
    product_id = proposed_id("product_id", ticket.product_id)
    product_module_id = proposed_id("product_module_id", ticket.product_module_id)
    environment_id = proposed_id("environment_id", ticket.environment_id)
    service_id = proposed_id("service_id", ticket.service_id)
    preferred_contract_id = proposed_id("contract_id", ticket.contract_id)
    priority_value = changes.get("priority", ticket.priority)
    priority = priority_value if isinstance(priority_value, str) else ticket.priority
    entitlement_status, contract, entitlement_reason = evaluate_entitlement(
        db,
        client_id=client_id,
        branch_id=ticket.branch_id,
        product_id=product_id,
        product_module_id=product_module_id,
        environment_id=environment_id,
        service_id=service_id,
        ticket_type_id=ticket_type_id,
        preferred_contract_id=preferred_contract_id,
    )
    if entitlement_status not in {"COVERED", "NO_CONTRACT"}:
        raise ConflictError("TICKET_NOT_ENTITLED", entitlement_reason)
    policy = (
        db.get(SlaPolicy, contract.sla_policy_id) if contract and contract.sla_policy_id else None
    )
    if contract and contract.has_sla and contract.sla_policy_id and (
        policy is None or not policy.is_active
    ):
        raise ConflictError("SLA_POLICY_INACTIVE", "The contract's linked SLA is unavailable.")
    if policy is None and (not contract or contract.has_sla):
        policy = db.scalar(
            select(SlaPolicy).where(
                SlaPolicy.code == "DEFAULT_SUPPORT", SlaPolicy.is_active.in_([True])
            )
        )
    target = None
    match_reason = "NO_MATCHING_SLA"
    if policy and policy.is_active:
        target, match_reason = resolve_product_scoped_sla_target(
            db,
            policy_id=policy.id,
            priority=priority,
            product_id=product_id,
            product_module_id=product_module_id,
            service_id=service_id,
            at=effective_at,
        )
    if policy is None or target is None:
        raise ConflictError(
            "SLA_REEVALUATION_TARGET_NOT_FOUND",
            "The edited ticket context has no unambiguous active SLA target.",
        )
    current_sla_version_id(db, policy)
    result.update(
        {
            "new_contract_id": contract.id if contract else None,
            "new_policy_id": policy.id,
            "new_target_id": target.id,
            "new_first_response_minutes": target.first_response_minutes,
            "new_resolution_minutes": target.resolution_minutes,
            "match_reason": match_reason,
        }
    )
    return result


def reevaluate_ticket_sla(
    db: Session,
    ticket: Ticket,
    actor: User,
    reason: str,
    changed_fields: set[str],
    effective_at: datetime,
) -> None:
    """Atomically preserve prior SLA evidence and activate the edited context."""
    clocks = list(db.scalars(select(TicketSlaClock).where(TicketSlaClock.ticket_id == ticket.id)))
    ticket_type = db.get(TicketType, ticket.ticket_type_id)
    if not ticket_type_uses_sla(ticket_type):
        for historical_clock in clocks:
            if historical_clock.state in {"RUNNING", "PAUSED"}:
                historical_clock.state = "NOT_APPLICABLE"
        return
    old_snapshot = [
        {
            key: value.isoformat() if isinstance(value, datetime) else value
            for key in (
                "id",
                "clock_type",
                "contract_id",
                "policy_id",
                "target_id",
                "calendar_id",
                "policy_version",
                "match_reason",
                "target_minutes",
                "warning_percent",
                "started_at",
                "due_at",
                "state",
                "completed_at",
                "accountable_minutes",
                "customer_pending_minutes",
                "millensys_pending_minutes",
                "escalation_minutes",
                "saved_minutes",
                "overrun_minutes",
                "calculation_version",
            )
            if (value := getattr(clock, key)) is not None
        }
        for clock in clocks
    ]
    contract = db.get(Contract, ticket.contract_id) if ticket.contract_id else None
    policy = (
        db.get(SlaPolicy, contract.sla_policy_id) if contract and contract.sla_policy_id else None
    )
    if contract and contract.has_sla and contract.sla_policy_id and (
        policy is None or not policy.is_active
    ):
        raise ConflictError("SLA_POLICY_INACTIVE", "The contract's linked SLA is unavailable.")
    if policy is None and (not contract or contract.has_sla):
        policy = db.scalar(
            select(SlaPolicy).where(
                SlaPolicy.code == "DEFAULT_SUPPORT", SlaPolicy.is_active.in_([True])
            )
        )
    target = None
    match_reason = "NO_MATCHING_SLA"
    if policy and policy.is_active:
        target, match_reason = resolve_product_scoped_sla_target(
            db,
            policy_id=policy.id,
            priority=ticket.priority,
            product_id=ticket.product_id,
            product_module_id=ticket.product_module_id,
            service_id=ticket.service_id,
            at=effective_at,
        )
    if policy is None or target is None:
        raise ConflictError(
            "SLA_REEVALUATION_TARGET_NOT_FOUND",
            "The edited ticket context has no unambiguous active SLA target.",
        )
    published_version_id = current_sla_version_id(db, policy)
    dedicated = is_dedicated_assignee(db, ticket.assigned_user_id)
    for clock_type, minutes in (
        ("FIRST_RESPONSE", target.first_response_minutes),
        ("RESOLUTION", target.resolution_minutes),
    ):
        clock = next((item for item in clocks if item.clock_type == clock_type), None)
        if clock_type == "FIRST_RESPONSE" and clock and clock.completed_at is not None:
            continue
        if clock is None:
            clock = TicketSlaClock(ticket_id=ticket.id, clock_type=clock_type)
            db.add(clock)
        mode = (
            first_response_start_mode(db)
            if clock_type == "FIRST_RESPONSE"
            else FIRST_RESPONSE_START_DEDICATED_ASSIGNMENT
        )
        running = mode == FIRST_RESPONSE_START_TICKET_CREATED or dedicated
        clock.contract_id = contract.id if contract else None
        clock.policy_id = policy.id
        clock.target_id = target.id
        clock.calendar_id = policy.calendar_id
        clock.policy_version = policy.version
        clock.policy_version_id = published_version_id
        clock.policy_code_snapshot = policy.code
        clock.policy_name_snapshot = policy.name
        clock.target_context_snapshot = target.context_key
        clock.match_reason = match_reason
        clock.start_mode_snapshot = mode
        clock.start_anchor_at = effective_at if running else None
        clock.target_minutes = minutes
        clock.warning_percent = target.warning_percent
        clock.started_at = effective_at
        clock.due_at = calculate_due_at(db, policy.calendar_id, effective_at, minutes)
        clock.state = "RUNNING" if running else "PAUSED"
        clock.breached_at = None
        clock.completed_at = None
        clock.accountable_minutes = None
        clock.customer_pending_minutes = None
        clock.millensys_pending_minutes = None
        clock.escalation_minutes = None
        clock.saved_minutes = None
        clock.overrun_minutes = None
        clock.outcome_calculated_at = None
        clock.calculation_version = "3.0"
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketSla",
            entity_id=str(ticket.id),
            action="ticket.sla.reevaluated",
            reason=reason,
            old_values_json=json.dumps(
                {"changed_fields": sorted(changed_fields), "clocks": old_snapshot}
            ),
            new_values_json=json.dumps(
                {
                    "contract_id": ticket.contract_id,
                    "policy_id": policy.id,
                    "target_id": target.id,
                    "match_reason": match_reason,
                    "effective_at": effective_at.isoformat(),
                }
            ),
        )
    )


def compile_advanced_filter(group: TicketFilterGroup):  # type: ignore[no-untyped-def]
    columns = {
        "ticket_number": Ticket.ticket_number,
        "subject": Ticket.subject,
        "priority": Ticket.priority,
        "client_id": Ticket.client_id,
        "branch_id": Ticket.branch_id,
        "assigned_user_id": Ticket.assigned_user_id,
        "assigned_team": Ticket.assigned_team,
        "ticket_type_id": Ticket.ticket_type_id,
        "product_id": Ticket.product_id,
        "product_module_id": Ticket.product_module_id,
        "environment_id": Ticket.environment_id,
        "service_id": Ticket.service_id,
        "category_id": Ticket.category_id,
        "subcategory_id": Ticket.subcategory_id,
        "entitlement_status": Ticket.entitlement_status,
        "created_at": Ticket.created_at,
        "updated_at": Ticket.updated_at,
        "resolved_at": Ticket.resolved_at,
    }

    def compile_rule(rule: TicketFilterRule):  # type: ignore[no-untyped-def]
        column: Any
        value: Any
        if rule.field == "status_code":
            column = Ticket.status_id
            value = select(TicketStatus.id).where(TicketStatus.code == rule.value).scalar_subquery()
        else:
            column, value = columns[rule.field], rule.value
        if rule.operator == "eq":
            return column == value
        if rule.operator == "ne":
            return column != value
        if rule.operator == "in":
            if not isinstance(value, list) or not value:
                raise ConflictError(
                    "INVALID_FILTER_VALUE", "The IN operator requires a non-empty list."
                )
            return column.in_(value)
        if rule.operator == "contains":
            if rule.field not in {"ticket_number", "subject", "assigned_team"} or not isinstance(
                value, str
            ):
                raise ConflictError(
                    "INVALID_FILTER_OPERATOR",
                    "Contains is only allowed for searchable text fields.",
                )
            return column.ilike(f"%{value}%")
        if rule.operator == "gte":
            return column >= value
        if rule.operator == "lte":
            return column <= value
        if rule.operator == "is_null":
            return column.is_(None) if rule.value is not False else column.is_not(None)
        raise ConflictError("INVALID_FILTER_OPERATOR", "The filter operator is invalid.")

    expressions = [
        compile_advanced_filter(item) if isinstance(item, TicketFilterGroup) else compile_rule(item)
        for item in group.rules
    ]
    return and_(*expressions) if group.logic == "AND" else or_(*expressions)


def derive_priority(impact: str, urgency: str) -> str:
    if impact not in PRIORITY_SCORE or urgency not in PRIORITY_SCORE:
        raise ConflictError("INVALID_PRIORITY_INPUT", "Impact and urgency are invalid.")
    score = max(PRIORITY_SCORE[impact], PRIORITY_SCORE[urgency])
    if impact == "CRITICAL" and urgency == "CRITICAL":
        return "P1"
    return {4: "P2", 3: "P2", 2: "P3", 1: "P4"}[score]


def ensure_ticket_access(db: Session, user: User, ticket: Ticket) -> None:
    access = effective_permissions(db, user)
    permissions = set(access.permissions)
    if "ticket.view.all" in permissions:
        return
    if user.user_type == "CLIENT_PORTAL":
        if ticket.client_id in access.client_scope_ids:
            return
        raise AuthorizationError()
    if "ticket.view.own" in permissions and (
        ticket.created_by_user_id == user.id or ticket.assigned_user_id == user.id
    ):
        return
    team_names = set(
        db.scalars(
            select(SupportTeam.name)
            .outerjoin(SupportTeamMember, SupportTeamMember.team_id == SupportTeam.id)
            .where(
                SupportTeam.is_active.in_([True]),
                or_(SupportTeamMember.user_id == user.id, SupportTeam.leader_user_id == user.id),
            )
        )
    )
    if "ticket.view.team" in permissions and ticket.assigned_team in team_names:
        return
    team_ids = set(db.scalars(select(SupportTeam.id).where(SupportTeam.name.in_(team_names))))
    if "ticket.view.team" in permissions and ticket.routed_team_id in team_ids:
        return
    if (
        "ticket.view.department" in permissions
        and user.department_id is not None
        and ticket.routed_department_id == user.department_id
    ):
        return
    raise AuthorizationError()


def queue_ticket_workflow_transition(
    db: Session,
    ticket: Ticket,
    actor: User,
    *,
    from_status_code: str,
    to_status_code: str,
    source: str,
) -> None:
    """Persist a visibility-safe workflow event with its committed ticket change.

    The outbox is deliberately metadata-only.  In-app notices are limited to users
    who can still open the ticket at the time the transition is committed.
    """
    db.add(
        EventOutbox(
            event_type="TICKET_WORKFLOW_TRANSITION",
            aggregate_type="Ticket",
            aggregate_id=str(ticket.id),
            deduplication_key=(
                f"ticket-transition:{ticket.id}:version:{ticket.version}:"
                f"{from_status_code}:{to_status_code}"
            ),
            payload_json=json.dumps(
                {
                    "ticket_id": ticket.id,
                    "ticket_number": ticket.ticket_number,
                    "from_status_code": from_status_code,
                    "to_status_code": to_status_code,
                    "actor_user_id": actor.id,
                    "source": source,
                }
            ),
        )
    )
    candidate_ids = {
        ticket.created_by_user_id,
        ticket.assigned_user_id,
        ticket.pending_owner_user_id,
    }
    candidate_ids.update(
        db.scalars(select(TicketFollower.user_id).where(TicketFollower.ticket_id == ticket.id))
    )
    for recipient_id in sorted(candidate_id for candidate_id in candidate_ids if candidate_id):
        recipient = db.get(User, recipient_id)
        if not recipient or not recipient.is_active:
            continue
        try:
            ensure_ticket_access(db, recipient, ticket)
        except AuthorizationError:
            continue
        db.add(
            Notification(
                recipient_user_id=recipient.id,
                notification_type="TICKET_WORKFLOW_TRANSITION",
                severity="INFO",
                title=f"Ticket status updated: {ticket.ticket_number}",
                message=f"Status changed from {from_status_code} to {to_status_code}.",
                deep_link=f"/tickets/{ticket.id}",
                deduplication_key=(
                    f"ticket-transition:{ticket.id}:version:{ticket.version}:"
                    f"{from_status_code}:{to_status_code}:user:{recipient.id}"
                ),
            )
        )


def ensure_assignment_eligibility(db: Session, user: User | None) -> User:
    if not user or not user.is_active or user.user_type != "EMPLOYEE":
        raise NotFoundError("Assigned engineer does not exist or is inactive.")
    settings = {
        row.key: row.value
        for row in db.scalars(
            select(SiteSetting).where(
                SiteSetting.key.in_(["assign_available_only", "assign_online_only"])
            )
        )
    }
    if settings.get("assign_online_only") == "true" and (
        not user.last_seen_at or user.last_seen_at < server_now() - timedelta(minutes=2)
    ):
        raise ConflictError("ASSIGNEE_OFFLINE", "The selected engineer is not currently online.")
    if settings.get("assign_available_only") == "true":
        in_progress_id = db.scalar(
            select(TicketStatus.id).where(TicketStatus.code == "IN_PROGRESS")
        )
        if in_progress_id and db.scalar(
            select(Ticket.id)
            .where(
                Ticket.assigned_user_id == user.id,
                Ticket.status_id == in_progress_id,
            )
            .limit(1)
        ):
            raise ConflictError(
                "ASSIGNEE_UNAVAILABLE",
                "The selected engineer is already working on an in-progress ticket.",
            )
    return user


def visible_ticket_query(
    db: Session, user: User, *, include_archived: bool = False
) -> Select[tuple[Ticket]]:
    access = effective_permissions(db, user)
    permissions = set(access.permissions)
    statement = select(Ticket)
    if not include_archived:
        statement = statement.where(Ticket.archived_at.is_(None))
    if "ticket.view.all" in permissions:
        return statement
    if user.user_type == "CLIENT_PORTAL":
        if not access.client_scope_ids:
            return statement.where(Ticket.id == -1)
        # Branch scope controls request creation. Portal viewing represents the
        # customer account and therefore includes every ticket for that client.
        return statement.where(Ticket.client_id.in_(access.client_scope_ids))
    predicates = []
    if "ticket.view.own" in permissions:
        predicates.append(
            or_(Ticket.created_by_user_id == user.id, Ticket.assigned_user_id == user.id)
        )
    if "ticket.view.team" in permissions:
        team_names = set(
            db.scalars(
                select(SupportTeam.name)
                .outerjoin(SupportTeamMember, SupportTeamMember.team_id == SupportTeam.id)
                .where(
                    SupportTeam.is_active.in_([True]),
                    or_(
                        SupportTeamMember.user_id == user.id,
                        SupportTeam.leader_user_id == user.id,
                    ),
                )
            )
        )
        if team_names:
            team_ids = select(SupportTeam.id).where(SupportTeam.name.in_(team_names))
            predicates.append(
                or_(Ticket.assigned_team.in_(team_names), Ticket.routed_team_id.in_(team_ids))
            )
    if "ticket.view.department" in permissions and user.department_id is not None:
        # Department access is deliberately limited to routed help requests. It
        # never grants blanket access to the Support-owned client ticket pool.
        predicates.append(Ticket.routed_department_id == user.department_id)
    return statement.where(or_(*predicates)) if predicates else statement.where(Ticket.id == -1)


def apply_ticket_filters(
    statement: Select[tuple[Ticket]],
    *,
    search: str | None = None,
    ticket_number: str | None = None,
    subject: str | None = None,
    description: str | None = None,
    impact: str | None = None,
    urgency: str | None = None,
    affected_users: str | None = None,
    patient_safety_flag: bool | None = None,
    security_incident_flag: bool | None = None,
    resolution_summary: str | None = None,
    status_code: str | None = None,
    priority: str | None = None,
    client_id: int | str | None = None,
    assigned_user_id: int | str | None = None,
    created_by_user_id: int | str | None = None,
    department_ids: set[int] | None = None,
    parent_department_ids: set[int] | None = None,
    requester_contact_id: int | str | None = None,
    branch_id: int | str | None = None,
    assigned_team: str | None = None,
    assigned_teams: set[str] | None = None,
    routed_team_ids: set[int] | None = None,
    routed_department_id: int | str | None = None,
    routed_team_id: int | str | None = None,
    routing_status: str | None = None,
    department_requests_only: bool = False,
    escalations_sent_only: bool = False,
    product_id: int | str | None = None,
    product_module_id: int | str | None = None,
    ticket_type_id: int | str | None = None,
    environment_id: int | str | None = None,
    service_id: int | str | None = None,
    category_id: int | str | None = None,
    subcategory_id: int | str | None = None,
    root_cause_id: int | str | None = None,
    entitlement_status: str | None = None,
    source_channel: str | None = None,
    sla_state: str | None = None,
    open_only: bool = False,
    include_pending_approval_in_open: bool = False,
    unassigned_only: bool = False,
    strictly_unassigned_only: bool = False,
    due_soon: bool = False,
    needs_attention: bool = False,
    breached_only: bool = False,
    resolved_only: bool = False,
    without_product: bool = False,
    created_from: DateTimeBoundary | None = None,
    created_to: DateTimeBoundary | None = None,
    updated_from: DateTimeBoundary | None = None,
    updated_to: DateTimeBoundary | None = None,
    resolved_from: DateTimeBoundary | None = None,
    resolved_to: DateTimeBoundary | None = None,
    first_occurred_from: DateTimeBoundary | None = None,
    first_occurred_to: DateTimeBoundary | None = None,
    closed_from: DateTimeBoundary | None = None,
    closed_to: DateTimeBoundary | None = None,
    timezone_offset_minutes: int = 180,
) -> Select[tuple[Ticket]]:
    def values(value: int | str | None) -> list[str]:
        return (
            [part.strip() for part in str(value).split(",") if part.strip()]
            if value is not None
            else []
        )

    def ids(value: int | str | None) -> list[int]:
        return [int(part) for part in values(value) if part.isdigit()]

    if search:
        normalized_search = search.strip().lower()
        term = f"%{normalized_search}%"
        matching_client_ids = select(Client.id).where(
            or_(
                func.lower(Client.name).like(term),
                func.lower(Client.code).like(term),
            )
        )
        statement = statement.where(
            or_(
                func.lower(Ticket.ticket_number).like(term),
                func.lower(Ticket.subject).like(term),
                Ticket.client_id.in_(matching_client_ids),
                Ticket.id.in_(select(UatDefectLink.ticket_id).where(or_(
                    func.lower(UatDefectLink.cycle_code).like(term),
                    func.lower(UatDefectLink.test_code).like(term),
                    func.lower(UatDefectLink.release_version).like(term),
                ))),
            )
        )
    if ticket_number and (normalized_ticket_number := ticket_number.strip().lower()):
        statement = statement.where(
            func.lower(Ticket.ticket_number).like(f"%{normalized_ticket_number}%")
        )
    for column, value in (
        (Ticket.subject, subject),
        (Ticket.description, description),
        (Ticket.affected_users, affected_users),
        (Ticket.resolution_summary, resolution_summary),
    ):
        if value and value.strip():
            statement = statement.where(func.lower(column).like(f"%{value.strip().lower()}%"))
    if impact:
        statement = statement.where(Ticket.impact.in_(values(impact)))
    if urgency:
        statement = statement.where(Ticket.urgency.in_(values(urgency)))
    if patient_safety_flag is not None:
        statement = statement.where(Ticket.patient_safety_flag == patient_safety_flag)
    if security_incident_flag is not None:
        statement = statement.where(Ticket.security_incident_flag == security_incident_flag)
    if status_code:
        requested_statuses = values(status_code)
        status_predicates: list[ColumnElement[bool]] = [
            TicketStatus.code.in_(requested_statuses)
        ]
        if "IN_PROGRESS" in requested_statuses:
            status_predicates.append(
                and_(
                    TicketStatus.code == "ASSIGNED",
                    Ticket.progress_started_at.is_not(None),
                )
            )
        statement = statement.join(TicketStatus).where(
            or_(*status_predicates)
        )
    if priority:
        statement = statement.where(Ticket.priority.in_(values(priority)))
    if client_id:
        statement = statement.where(Ticket.client_id.in_(ids(client_id)))
    if assigned_user_id:
        statement = statement.where(Ticket.assigned_user_id.in_(ids(assigned_user_id)))
    if created_by_user_id:
        statement = statement.where(Ticket.created_by_user_id.in_(ids(created_by_user_id)))

    def department_predicate(selected_ids: set[int]) -> ColumnElement[bool]:
        department_users = select(User.id).where(User.department_id.in_(selected_ids))
        return or_(
            Ticket.routed_department_id.in_(selected_ids),
            and_(
                Ticket.routed_department_id.is_(None), Ticket.assigned_user_id.in_(department_users)
            ),
            and_(
                Ticket.routed_department_id.is_(None),
                Ticket.assigned_user_id.is_(None),
                Ticket.created_by_user_id.in_(department_users),
            ),
        )

    if department_ids:
        statement = statement.where(department_predicate(department_ids))
    if parent_department_ids:
        statement = statement.where(department_predicate(parent_department_ids))
    if requester_contact_id:
        statement = statement.where(Ticket.requester_contact_id.in_(ids(requester_contact_id)))
    if branch_id:
        statement = statement.where(Ticket.branch_id.in_(ids(branch_id)))
    if assigned_team:
        statement = statement.where(Ticket.assigned_team.in_(values(assigned_team)))
    if assigned_teams is not None:
        team_predicates = []
        if assigned_teams:
            team_predicates.append(Ticket.assigned_team.in_(assigned_teams))
        if routed_team_ids:
            team_predicates.append(Ticket.routed_team_id.in_(routed_team_ids))
        statement = statement.where(or_(*team_predicates) if team_predicates else Ticket.id == -1)
    if routed_department_id:
        statement = statement.where(Ticket.routed_department_id.in_(ids(routed_department_id)))
    if routed_team_id:
        statement = statement.where(Ticket.routed_team_id.in_(ids(routed_team_id)))
    if routing_status:
        statement = statement.where(Ticket.routing_status.in_(values(routing_status)))
    if department_requests_only:
        statement = statement.where(Ticket.routed_department_id.is_not(None))
    if escalations_sent_only:
        statement = statement.where(
            Ticket.escalation_parent_ticket_id.is_(None),
            Ticket.escalation_level == "OTHER_DEPARTMENT",
        )
    if product_id:
        statement = statement.where(Ticket.product_id.in_(ids(product_id)))
    if product_module_id:
        statement = statement.where(Ticket.product_module_id.in_(ids(product_module_id)))
    if ticket_type_id:
        statement = statement.where(Ticket.ticket_type_id.in_(ids(ticket_type_id)))
    if environment_id:
        statement = statement.where(Ticket.environment_id.in_(ids(environment_id)))
    if service_id:
        statement = statement.where(Ticket.service_id.in_(ids(service_id)))
    if category_id:
        statement = statement.where(Ticket.category_id.in_(ids(category_id)))
    if subcategory_id:
        statement = statement.where(Ticket.subcategory_id.in_(ids(subcategory_id)))
    if root_cause_id:
        statement = statement.where(
            Ticket.id.in_(
                select(TicketRootCause.ticket_id).where(
                    TicketRootCause.root_cause_id.in_(ids(root_cause_id))
                )
            )
        )
    if entitlement_status:
        statement = statement.where(Ticket.entitlement_status.in_(values(entitlement_status)))
    if source_channel:
        channels = values(source_channel)
        statement = statement.where(
            Ticket.source_channel.is_not(None)
            if "NON_PORTAL" in channels and "CLIENT_PORTAL" in channels
            else Ticket.source_channel.not_in(["CLIENT_PORTAL"])
            if "NON_PORTAL" in channels
            else Ticket.source_channel.in_([item for item in channels if item != "NON_PORTAL"])
        )
    if sla_state:
        statement = statement.where(
            Ticket.id.in_(
                select(TicketSlaClock.ticket_id).where(TicketSlaClock.state.in_(values(sla_state)))
            )
        )
    if open_only:
        if not include_pending_approval_in_open:
            statement = statement.where(
                func.coalesce(Ticket.entitlement_status, "") != "PENDING_APPROVAL"
            )
        statement = statement.where(
            Ticket.status_id.in_(
                select(TicketStatus.id).where(
                    TicketStatus.code.in_(
                        [
                            "NEW",
                            "TRIAGED",
                            "ASSIGNED",
                            "IN_PROGRESS",
                            "REOPENED",
                        ]
                    )
                )
            )
        )
    if strictly_unassigned_only:
        statement = statement.where(Ticket.assigned_user_id.is_(None))
    elif unassigned_only:
        shared_queue_ids = select(User.id).where(User.username_normalized == "support")
        unassigned_predicates = [
            Ticket.assigned_user_id.is_(None),
            Ticket.assigned_user_id.in_(shared_queue_ids),
            Ticket.assigned_user_id.in_(
                select(cast(SiteSetting.value, Integer)).where(
                    SiteSetting.key == "default_assignee_user_id"
                )
            ),
        ]
        statement = statement.where(or_(*unassigned_predicates))
    if due_soon:
        now = server_now()
        statement = statement.where(
            Ticket.id.in_(
                select(TicketSlaClock.ticket_id).where(
                    TicketSlaClock.state == "RUNNING",
                    TicketSlaClock.due_at > now,
                    TicketSlaClock.due_at <= now + timedelta(hours=4),
                )
            )
        )
    if needs_attention:
        now = server_now()
        tomorrow_start = datetime.combine(
            server_today() + timedelta(days=1), time.min, tzinfo=server_timezone()
        )
        statement = statement.where(
            Ticket.status_id.in_(select(TicketStatus.id).where(
                TicketStatus.code.not_in(["RESOLVED", "CLOSED", "CANCELLED"])
            )),
            Ticket.status_id.not_in(select(TicketStatus.id).where(
                TicketStatus.code.in_(["PENDING_CLIENT", "PENDING_INTERNAL", "PENDING_VENDOR"])
            )),
            func.coalesce(Ticket.entitlement_status, "") != "PENDING_APPROVAL",
            Ticket.due_at.is_not(None),
            Ticket.due_at > now,
            Ticket.due_at < tomorrow_start,
        )
    if breached_only:
        now = server_now()
        statement = statement.where(
            Ticket.id.in_(
                select(TicketSlaClock.ticket_id).where(
                    TicketSlaClock.clock_type == "RESOLUTION",
                    (TicketSlaClock.overrun_minutes > 0)
                    | TicketSlaClock.breached_at.is_not(None)
                    | (TicketSlaClock.state == "BREACHED")
                    | ((TicketSlaClock.state == "RUNNING") & (TicketSlaClock.due_at <= now)),
                )
            )
        )
    if resolved_only:
        statement = statement.where(Ticket.resolved_at.is_not(None))
    if without_product:
        statement = statement.where(Ticket.product_id.is_(None))
    # Date-only values keep whole-day semantics; datetimes use exact boundaries.
    if created_from:
        statement = statement.where(Ticket.created_at >= ticket_filter_lower_bound(created_from))
    if created_to:
        upper, exclusive = ticket_filter_upper_bound(created_to)
        statement = statement.where(Ticket.created_at < upper if exclusive else Ticket.created_at <= upper)
    for datetime_column, lower, upper_value in (
        (Ticket.updated_at, updated_from, updated_to),
        (Ticket.resolved_at, resolved_from, resolved_to),
        (Ticket.first_occurred_at, first_occurred_from, first_occurred_to),
        (Ticket.closed_at, closed_from, closed_to),
    ):
        if lower:
            statement = statement.where(datetime_column >= ticket_filter_lower_bound(lower))
        if upper_value:
            upper_bound, exclusive = ticket_filter_upper_bound(upper_value)
            statement = statement.where(
                datetime_column < upper_bound if exclusive else datetime_column <= upper_bound
            )
    return statement


def validate_ticket_context(
    db: Session,
    *,
    client_id: int,
    ticket_type_id: int,
    product_id: int | None,
    product_module_id: int | None,
    environment_id: int | None,
    service_id: int | None,
    category_id: int | None,
    subcategory_id: int | None,
    branch_id: int | None = None,
    requester_contact_id: int | None = None,
) -> None:
    """Validate context combinations shared by ticket create and edit commands."""
    ticket_type = db.get(TicketType, ticket_type_id)
    if not ticket_type or not ticket_type.is_active:
        raise NotFoundError("Ticket type does not exist or is inactive.")
    if not db.get(Client, client_id):
        raise NotFoundError("Client does not exist.")
    if branch_id:
        branch = db.get(Branch, branch_id)
        if not branch or branch.client_id != client_id:
            raise ConflictError("INVALID_BRANCH", "The branch does not belong to the client.")
    if requester_contact_id:
        contact = db.get(Contact, requester_contact_id)
        linked = contact and db.scalar(
            select(ContactClientLink.id).where(
                ContactClientLink.contact_id == requester_contact_id,
                ContactClientLink.client_id == client_id,
            )
        )
        if not contact or (contact.client_id != client_id and not linked):
            raise ConflictError("INVALID_REQUESTER", "The requester does not belong to the client.")
    if product_id:
        product = db.get(Product, product_id)
        if not product or not product.is_active:
            raise NotFoundError("Product does not exist or is inactive.")
    if product_module_id:
        product_module = db.get(ProductModule, product_module_id)
        if not product_module or not product_module.is_active:
            raise NotFoundError("Product module does not exist or is inactive.")
        if product_module.product_id != product_id:
            raise ConflictError(
                "INVALID_PRODUCT_MODULE", "The module does not belong to the selected product."
            )
    if environment_id:
        environment = db.get(Environment, environment_id)
        if not environment or not environment.is_active:
            raise NotFoundError("Environment does not exist or is inactive.")
    if service_id:
        service = db.get(ServiceCatalogItem, service_id)
        if not service or not service.is_active:
            raise NotFoundError("Service does not exist or is inactive.")
        if (
            product_module_id
            and db.scalar(
                select(ServiceModuleLink.id).where(
                    ServiceModuleLink.service_id == service_id,
                    ServiceModuleLink.product_module_id == product_module_id,
                )
            )
            is None
        ):
            raise ConflictError(
                "INVALID_SERVICE_MODULE",
                "The service is not linked to the selected product module.",
            )
    if category_id:
        category = db.get(TicketCategory, category_id)
        if not category or not category.is_active:
            raise NotFoundError("Ticket category does not exist or is inactive.")
    if subcategory_id:
        subcategory = db.get(TicketSubcategory, subcategory_id)
        if not subcategory or not subcategory.is_active:
            raise NotFoundError("Ticket subcategory does not exist or is inactive.")
        if subcategory.category_id != category_id:
            raise ConflictError(
                "INVALID_SUBCATEGORY", "The subcategory does not belong to the category."
            )


def create_ticket(
    db: Session, data: TicketCreate, actor: User, *, allow_controlled_assignment: bool = False,
    commit: bool = True, enforce_configured_required_fields: bool = True,
) -> Ticket:
    if actor.user_type == "EMPLOYEE" and enforce_configured_required_fields:
        validate_required_ticket_fields(db, data)
    ticket_type = db.get(TicketType, data.ticket_type_id)
    client = db.get(Client, data.client_id)
    if not ticket_type or not ticket_type.is_active:
        raise NotFoundError("Ticket type does not exist.")
    if not client:
        raise NotFoundError("Client does not exist.")
    if data.request_entitlement_approval and data.submission_idempotency_key:
        previous_approval = db.scalar(
            select(EntitlementApproval).where(
                EntitlementApproval.idempotency_key
                == f"portal-ticket:{data.submission_idempotency_key}"
            )
        )
        if previous_approval and previous_approval.ticket_id:
            previous_ticket = db.get(Ticket, previous_approval.ticket_id)
            if previous_ticket:
                return previous_ticket
    client_status = db.get(ClientStatus, client.status_id)
    ticket_creation_restricted = (
        not client.is_active or not client_status or not client_status.ticket_creation_allowed
    )
    if ticket_creation_restricted:
        data.request_entitlement_approval = True
        data.entitlement_approval_justification = (
            data.entitlement_approval_justification
            or "Inactive client requires management approval before support service can begin."
        )
        data.submission_idempotency_key = (
            data.submission_idempotency_key or f"inactive-client-{uuid.uuid4()}"
        )
    if actor.user_type == "CLIENT_PORTAL":
        access = effective_permissions(db, actor)
        if data.client_id not in access.client_scope_ids:
            raise AuthorizationError()
        if data.branch_id and (
            not access.branch_scope_ids or data.branch_id not in access.branch_scope_ids
        ):
            raise AuthorizationError()
        if ticket_type.code not in {"INCIDENT", "SERVICE_REQUEST", "CHANGE_REQUEST"}:
            raise AuthorizationError(
                "Portal users may create incidents, service requests, and change requests only."
            )
        data.source_channel = "MOSAIC" if data.source_channel == "MOSAIC" else "CLIENT_PORTAL"
    creation_fingerprint = None
    if data.creation_idempotency_key:
        creation_fingerprint = sha256(
            json.dumps(
                data.model_dump(exclude={"creation_idempotency_key", "submission_idempotency_key"}),
                default=str,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        previous = db.scalar(
            select(Ticket).where(
                Ticket.created_by_user_id == actor.id,
                Ticket.source_channel == data.source_channel,
                Ticket.creation_idempotency_key == data.creation_idempotency_key,
            )
        )
        if previous:
            if previous.creation_request_fingerprint == creation_fingerprint:
                return previous
            raise ConflictError(
                "TICKET_CREATION_IDEMPOTENCY_CONFLICT",
                "This creation key was already used with a different ticket request.",
            )
    if data.priority:
        if actor.user_type != "CLIENT_PORTAL":
            permissions = set(effective_permissions(db, actor).permissions)
            if "ticket.change.priority" not in permissions:
                raise AuthorizationError("You do not have permission to set ticket priority.")
    if data.branch_id:
        branch = db.get(Branch, data.branch_id)
        if not branch or branch.client_id != data.client_id:
            raise ConflictError("INVALID_BRANCH", "The branch does not belong to the client.")
    if data.requester_contact_id:
        contact = db.get(Contact, data.requester_contact_id)
        linked = contact and db.scalar(
            select(ContactClientLink.id).where(
                ContactClientLink.contact_id == contact.id,
                ContactClientLink.client_id == data.client_id,
            )
        )
        if not contact or (contact.client_id != data.client_id and not linked):
            raise ConflictError("INVALID_REQUESTER", "The requester does not belong to the client.")
    assigned_user = db.get(User, data.assigned_user_id) if data.assigned_user_id else None
    if (
        data.assigned_user_id or data.assigned_team or data.follower_user_ids
    ) and not allow_controlled_assignment:
        permissions = set(effective_permissions(db, actor).permissions)
        if "ticket.assign.team" not in permissions:
            raise AuthorizationError("You do not have permission to assign engineers or teams.")
    if data.assigned_team:
        team = db.scalar(
            select(SupportTeam).where(
                SupportTeam.name == data.assigned_team, SupportTeam.is_active.in_([True])
            )
        )
        if not team:
            raise NotFoundError("Assigned team does not exist or is inactive.")
    if data.assigned_user_id:
        if (
            not assigned_user
            or not assigned_user.is_active
            or assigned_user.user_type != "EMPLOYEE"
        ):
            raise NotFoundError("Assigned engineer does not exist or is inactive.")
    if not assigned_user and not data.assigned_team:
        configured_assignee = db.get(SiteSetting, "default_assignee_user_id")
        assigned_user = (
            db.get(User, int(configured_assignee.value))
            if configured_assignee and configured_assignee.value.isdigit()
            else None
        )
        if not assigned_user:
            assigned_user = db.scalar(
                select(User).where(
                    User.email_normalized == "support@millensys.com", User.is_active.in_([True])
                )
            )
        if assigned_user:
            data.assigned_user_id = assigned_user.id
    followers = []
    for user_id in set(data.follower_user_ids):
        follower = db.get(User, user_id)
        if not follower or not follower.is_active or follower.user_type != "EMPLOYEE":
            raise NotFoundError("A selected follower does not exist or is inactive.")
        followers.append(follower)
    validate_ticket_context(
        db,
        client_id=data.client_id,
        ticket_type_id=data.ticket_type_id,
        product_id=data.product_id,
        product_module_id=data.product_module_id,
        environment_id=data.environment_id,
        service_id=data.service_id,
        category_id=data.category_id,
        subcategory_id=data.subcategory_id,
        branch_id=data.branch_id,
        requester_contact_id=data.requester_contact_id,
    )
    if ticket_creation_restricted:
        entitlement_status, entitled_contract, entitlement_reason = (
            "INACTIVE_CLIENT",
            None,
            "The client is inactive, so its contracts, products, modules, services, and SLA coverage require management approval.",
        )
    else:
        entitlement_status, entitled_contract, entitlement_reason = evaluate_entitlement(
            db,
            client_id=data.client_id,
            branch_id=data.branch_id,
            product_id=data.product_id,
            product_module_id=data.product_module_id,
            environment_id=data.environment_id,
            service_id=data.service_id,
            ticket_type_id=data.ticket_type_id,
            preferred_contract_id=data.contract_id,
        )
    if entitled_contract:
        required_context = (
            ("product", "product_id", entitled_contract.require_product_on_ticket, data.product_id),
            ("module", "product_module_id", entitled_contract.require_module_on_ticket, data.product_module_id),
            ("service", "service_id", entitled_contract.require_service_on_ticket, data.service_id),
        )
        missing = [
            label
            for label, column_name, required, value in required_context
            if required
            and value is None
            and db.scalar(
                select(ContractCoverage.id).where(
                    ContractCoverage.contract_id == entitled_contract.id,
                    getattr(ContractCoverage, column_name).is_not(None),
                    ContractCoverage.retired_at.is_(None),
                ).limit(1)
            )
        ]
        if missing:
            raise ConflictError(
                "CONTRACT_REQUIRED_SELECTION_MISSING",
                f"This contract requires selecting: {', '.join(missing)}.",
            )
    # Contract entitlement failures never discard the request. They create a visible,
    # unassigned ticket and an approval task. Grace-covered requests remain operational.
    pending_approval = False
    approval_reason_code = entitlement_status
    # A genuinely new client with no contract keeps the platform's existing
    # default-support workflow. Once a matching contract exists, expired,
    # inactive and uncovered scopes are governed through approval.
    if entitlement_status not in {"COVERED", "GRACE_COVERAGE", "NO_CONTRACT"}:
        pending_approval = True
        data.request_entitlement_approval = True
        data.entitlement_approval_justification = (
            data.entitlement_approval_justification
            or f"Automatic contract-policy approval request: {entitlement_reason}"
        )
        data.submission_idempotency_key = (
            data.submission_idempotency_key or f"contract-policy-{uuid.uuid4()}"
        )
        entitlement_status = "PENDING_APPROVAL"
        assigned_user = None
        data.assigned_user_id = None
        data.assigned_team = None
    initial_status_code = "ASSIGNED" if assigned_user or data.assigned_team else "NEW"
    initial_status = db.scalar(select(TicketStatus).where(TicketStatus.code == initial_status_code))
    if not initial_status:
        raise RuntimeError(f"{initial_status_code} status is not seeded.")
    ticket = Ticket(
        **data.model_dump(
            exclude={
                "inactive_client_confirmed",
                "priority",
                "follower_user_ids",
                "contract_id",
                "request_entitlement_approval",
                "entitlement_approval_justification",
                "submission_idempotency_key",
                "creation_method",
                "change_request",
            }
        ),
        contract_id=entitled_contract.id if entitled_contract else None,
        entitlement_status=entitlement_status,
        created_by_user_id=actor.id,
        status_id=initial_status.id,
        priority=data.priority or derive_priority(data.impact, data.urgency),
    )
    db.add(ticket)
    db.flush()
    ticket.ticket_number = f"{ticket_type.number_prefix}-{server_now().year}-{ticket.id:06d}"
    for follower in followers:
        db.add(TicketFollower(ticket_id=ticket.id, user_id=follower.id, added_by_user_id=actor.id))
    if assigned_user:
        db.add(
            Notification(
                recipient_user_id=assigned_user.id,
                notification_type="TICKET_ASSIGNED",
                severity="INFO",
                title=f"Ticket assigned: {ticket.ticket_number}",
                message=f"{actor.full_name} assigned you: {ticket.subject}",
                deep_link=f"/tickets/{ticket.id}",
                deduplication_key=f"ticket-created-assigned:{ticket.id}:user:{assigned_user.id}",
            )
        )
        db.add(
            EventOutbox(
                event_type="TICKET_ASSIGNED",
                aggregate_type="Ticket",
                aggregate_id=str(ticket.id),
                payload_json=json.dumps(
                    {
                        "ticket_id": ticket.id,
                        "assigned_user_id": assigned_user.id,
                        "assigned_by_user_id": actor.id,
                    }
                ),
            )
        )
    db.add(
        TicketStatusHistory(
            ticket_id=ticket.id,
            to_status_id=initial_status.id,
            changed_by_user_id=actor.id,
            reason=(
                "Ticket created and assigned"
                if assigned_user or data.assigned_team
                else "Ticket created"
            ),
        )
    )
    ticket.creation_request_fingerprint = creation_fingerprint
    contract = entitled_contract
    policy = None
    if ticket_type_uses_sla(ticket_type) and contract and contract.has_sla and not pending_approval:
        policy = db.get(SlaPolicy, contract.sla_policy_id) if contract.sla_policy_id else None
        if policy and not policy.is_active:
            raise ConflictError("SLA_POLICY_INACTIVE", "The contract's linked SLA is inactive.")
        if not policy:
            policy = db.scalar(
                select(SlaPolicy).where(
                    SlaPolicy.contract_id == contract.id, SlaPolicy.is_active.in_([True])
                )
            )
    if ticket_type_uses_sla(ticket_type) and not pending_approval and not policy and (not contract or contract.has_sla):
        policy = db.scalar(
            select(SlaPolicy).where(
                SlaPolicy.code == "DEFAULT_SUPPORT", SlaPolicy.is_active.in_([True])
            )
        )
    if policy:
        published_version_id = current_sla_version_id(db, policy)
        target_feature = resolve_feature_policy(
            db,
            "product_scoped_sla",
            client_id=ticket.client_id,
            contract_id=contract.id if contract else None,
            product_id=ticket.product_id,
            service_id=ticket.service_id,
        )
        governed_target, match_reason = resolve_product_scoped_sla_target(
            db,
            policy_id=policy.id,
            priority=ticket.priority,
            product_id=ticket.product_id,
            product_module_id=ticket.product_module_id,
            service_id=ticket.service_id,
        )
        target = governed_target
        legacy_target = None
        if target_feature.mode == "SHADOW":
            legacy_target = db.scalar(
                select(SlaTarget)
                .where(
                    SlaTarget.policy_id == policy.id,
                    SlaTarget.priority == ticket.priority,
                    (SlaTarget.service_id == ticket.service_id)
                    if ticket.service_id
                    else SlaTarget.service_id.is_(None),
                )
                .order_by(SlaTarget.service_id.desc())
            )
            if not legacy_target and ticket.service_id:
                has_service_scoped_target = (
                    db.scalar(
                        select(SlaTarget.id).where(
                            SlaTarget.policy_id == policy.id,
                            SlaTarget.priority == ticket.priority,
                            SlaTarget.service_id.is_not(None),
                        )
                    )
                    is not None
                )
                if not has_service_scoped_target:
                    legacy_target = db.scalar(
                        select(SlaTarget).where(
                            SlaTarget.policy_id == policy.id,
                            SlaTarget.priority == ticket.priority,
                            SlaTarget.service_id.is_(None),
                        )
                    )
        if target_feature.mode == "SHADOW":
            outcome = (
                "SAME"
                if legacy_target and governed_target and legacy_target.id == governed_target.id
                else "CHANGED"
                if legacy_target and governed_target
                else "GOVERNED_ONLY"
                if governed_target
                else "LEGACY_ONLY"
                if legacy_target
                else "NO_TARGET"
            )
            db.add(
                SlaShadowComparison(
                    ticket_id=ticket.id,
                    contract_id=contract.id if contract else None,
                    policy_id=policy.id,
                    legacy_target_id=legacy_target.id if legacy_target else None,
                    governed_target_id=governed_target.id if governed_target else None,
                    legacy_response_minutes=legacy_target.first_response_minutes if legacy_target else None,
                    legacy_resolution_minutes=legacy_target.resolution_minutes if legacy_target else None,
                    governed_response_minutes=governed_target.first_response_minutes
                    if governed_target
                    else None,
                    governed_resolution_minutes=governed_target.resolution_minutes
                    if governed_target
                    else None,
                    governed_match_reason=match_reason,
                    outcome=outcome,
                )
            )
        if not target:
            raise ConflictError("SLA_TARGET_NOT_FOUND", f"No unambiguous active SLA target matches this ticket ({match_reason}).")
        if target:
            started = server_now()
            dedicated_at_creation = is_dedicated_assignee(db, ticket.assigned_user_id)
            response_mode = first_response_start_mode(db)
            for clock_type, minutes in (
                ("FIRST_RESPONSE", target.first_response_minutes),
                ("RESOLUTION", target.resolution_minutes),
            ):
                db.add(
                    TicketSlaClock(
                        ticket_id=ticket.id,
                        contract_id=contract.id if contract else None,
                        policy_id=policy.id,
                        target_id=target.id,
                        calendar_id=policy.calendar_id,
                        policy_version=policy.version,
                        policy_version_id=published_version_id,
                        policy_code_snapshot=policy.code,
                        policy_name_snapshot=policy.name,
                        target_context_snapshot=target.context_key,
                        match_reason=match_reason,
                        start_mode_snapshot=(
                            response_mode
                            if clock_type == "FIRST_RESPONSE"
                            else FIRST_RESPONSE_START_DEDICATED_ASSIGNMENT
                        ),
                        start_anchor_at=(
                            started
                            if clock_type == "FIRST_RESPONSE"
                            and (
                                response_mode == FIRST_RESPONSE_START_TICKET_CREATED
                                or dedicated_at_creation
                            )
                            else started
                            if clock_type == "RESOLUTION" and dedicated_at_creation
                            else None
                        ),
                        clock_type=clock_type,
                        target_minutes=minutes,
                        warning_percent=target.warning_percent,
                        started_at=started,
                        due_at=calculate_due_at(db, policy.calendar_id, started, minutes),
                        state=(
                            "RUNNING"
                            if clock_type == "FIRST_RESPONSE"
                            and (
                                response_mode == FIRST_RESPONSE_START_TICKET_CREATED
                                or dedicated_at_creation
                            )
                            else "RUNNING"
                            if clock_type == "RESOLUTION" and dedicated_at_creation
                            else "PAUSED"
                        ),
                        completed_at=None,
                        calculation_version="3.0",
                    )
                )
    if assigned_user and is_dedicated_assignee(db, assigned_user.id):
        db.add(
            TicketAssignmentHistory(
                ticket_id=ticket.id,
                assigned_user_id=assigned_user.id,
                assigned_team=data.assigned_team,
                assigned_by_user_id=actor.id,
                reason="Initial ticket assignment",
                created_at=server_now(),
            )
        )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket.id),
            action=(
                "ticket.created.inactive_client" if ticket_creation_restricted else "ticket.created"
            ),
            reason=(
                "Restricted client creation explicitly confirmed"
                if ticket_creation_restricted
                else None
            ),
        )
    )
    if ticket.entitlement_status == "OVERRIDDEN":
        db.add(
            AuditLog(
                actor_user_id=actor.id,
                entity_type="Ticket",
                entity_id=str(ticket.id),
                action="ticket.entitlement.overridden",
                reason=ticket.entitlement_override_reason,
            )
        )
    if pending_approval:
        approval_justification = (
            data.entitlement_approval_justification or "Out-of-contract portal request"
        )
        approval = EntitlementApproval(
            idempotency_key=f"ticket:{data.submission_idempotency_key}",
            source_channel=data.source_channel,
            status="PENDING",
            reason_code=approval_reason_code,
            requested_action="REQUIRE_APPROVAL",
            justification=approval_justification.strip(),
            request_payload_json=json.dumps({"ticket_id": ticket.id}),
            evidence_json=json.dumps({"entitlement_reason": entitlement_reason}),
            feature_mode="ENFORCED",
            policy_version=0,
            policy_scope="CONTRACT",
            client_id=ticket.client_id,
            contract_id=entitled_contract.id if entitled_contract else None,
            ticket_id=ticket.id,
            approval_group_id=(
                entitled_contract.approval_group_id if entitled_contract else None
            ),
            requested_by_user_id=actor.id,
            operation_scope=f"TICKET:{ticket.id}:REQUIRE_APPROVAL",
            version=1,
        )
        db.add(approval)
        db.flush()
        db.add(
            EntitlementApprovalHistory(
                approval_id=approval.id,
                from_status=None,
                to_status="PENDING",
                actor_user_id=actor.id,
                comment=approval_justification.strip(),
            )
        )
        manager_ids = (
            set(
                db.scalars(
                    select(ApprovalGroupMember.user_id).where(
                        ApprovalGroupMember.group_id == approval.approval_group_id
                    )
                )
            )
            if approval.approval_group_id
            else set(
                db.scalars(
                    select(UserProfile.user_id)
                    .join(Profile, Profile.id == UserProfile.profile_id)
                    .where(
                        UserProfile.is_active.in_([True]),
                        Profile.code == "SUPPORT_MANAGER",
                    )
                )
            )
        )
        for manager_id in manager_ids:
            db.add(
                Notification(
                    recipient_user_id=manager_id,
                    notification_type="ENTITLEMENT_APPROVAL_REQUIRED",
                    severity="WARNING",
                    title=f"Ticket approval required: {ticket.ticket_number}",
                    message=f"{actor.full_name} submitted an out-of-contract ticket for approval.",
                    deep_link=f"/tickets?tab=approvals&approval_id={approval.id}",
                    deduplication_key=f"approval-required:{approval.id}:user:{manager_id}",
                )
            )
    queue_ticket_creation_email(db, ticket, actor)
    if not commit:
        db.flush()
        return ticket
    try:
        db.commit()
    except IntegrityError as err:
        db.rollback()
        if data.creation_idempotency_key:
            concurrent_ticket = db.scalar(
                select(Ticket).where(
                    Ticket.created_by_user_id == actor.id,
                    Ticket.source_channel == data.source_channel,
                    Ticket.creation_idempotency_key == data.creation_idempotency_key,
                )
            )
            if concurrent_ticket:
                if concurrent_ticket.creation_request_fingerprint == creation_fingerprint:
                    return concurrent_ticket
                raise ConflictError(
                    "TICKET_CREATION_IDEMPOTENCY_CONFLICT",
                    "This creation key was already used with different ticket details.",
                ) from err
        raise
    db.refresh(ticket)
    return ticket


def resolution_readiness_blockers(db: Session, ticket: Ticket) -> list[dict[str, object]]:
    """Return UI-ready blockers for required operational work."""
    blockers: list[dict[str, object]] = []
    for task in db.scalars(
        select(TicketTask).where(
            TicketTask.ticket_id == ticket.id,
            TicketTask.is_required.in_([True]),
            TicketTask.status.not_in(["COMPLETED", "CANCELLED"]),
        )
    ):
        blockers.append({"type": "TASK", "id": task.id, "label": task.title, "status": task.status})
    for item in db.scalars(
        select(TicketChecklistItem).where(
            TicketChecklistItem.ticket_id == ticket.id,
            TicketChecklistItem.is_required.in_([True]),
            TicketChecklistItem.is_completed.in_([False]),
        )
    ):
        blockers.append({"type": "CHECKLIST", "id": item.id, "label": item.label, "status": "OPEN"})
    return blockers


def resolution_details_required_on_close(db: Session) -> bool:
    setting = db.get(SiteSetting, "resolution_details_required_on_close")
    return bool(setting and setting.value.lower() == "true")


def validate_change_request_ticket_transition(db: Session, ticket: Ticket, target_code: str) -> None:
    """Prevent a parent ticket from contradicting its structured Change lifecycle."""
    from app.modules.service_management.models import ChangeRequestDetail

    change = db.scalar(select(ChangeRequestDetail).where(ChangeRequestDetail.ticket_id == ticket.id))
    if not change:
        return
    allowed_change_states = {
        "RESOLVED": {"COMPLETED"},
        "CLOSED": {"COMPLETED"},
        "CANCELLED": {"CANCELLED", "REJECTED"},
    }.get(target_code)
    if allowed_change_states and change.change_status not in allowed_change_states:
        raise ConflictError(
            "TICKET_CHANGE_STATUS_MISMATCH",
            f"Ticket status {target_code} requires the Change Request to be in: {sorted(allowed_change_states)}.",
            {"change_status": change.change_status, "allowed_change_statuses": sorted(allowed_change_states)},
        )


def refresh_pending_contract_entitlement(db: Session, ticket: Ticket, actor: User) -> None:
    """Release a stale approval block when the ticket is covered now.

    Contract dates and coverage can legitimately change after ticket creation.  The
    ticket keeps its original approval state for audit purposes, but that snapshot
    must not block workflow once the same context evaluates as covered.
    """
    if ticket.entitlement_status != "PENDING_APPROVAL":
        return
    entitlement_status, contract, reason = evaluate_entitlement(
        db,
        client_id=ticket.client_id,
        branch_id=ticket.branch_id,
        product_id=ticket.product_id,
        product_module_id=ticket.product_module_id,
        environment_id=ticket.environment_id,
        service_id=ticket.service_id,
        ticket_type_id=ticket.ticket_type_id,
        preferred_contract_id=ticket.contract_id,
    )
    if entitlement_status not in {"COVERED", "GRACE_COVERAGE"}:
        return
    previous_status = ticket.entitlement_status
    ticket.entitlement_status = entitlement_status
    ticket.contract_id = contract.id if contract else None
    ticket.entitlement_override_reason = None
    now = server_now()
    pending_approvals = list(
        db.scalars(
            select(EntitlementApproval).where(
                EntitlementApproval.ticket_id == ticket.id,
                EntitlementApproval.status == "PENDING",
            )
        )
    )
    for approval in pending_approvals:
        approval.status = "CANCELLED"
        approval.decided_by_user_id = actor.id
        approval.decision_comment = "Automatically cancelled because the contract now covers the ticket."
        approval.decided_at = now
        approval.version += 1
        db.add(
            EntitlementApprovalHistory(
                approval_id=approval.id,
                from_status="PENDING",
                to_status="CANCELLED",
                actor_user_id=actor.id,
                comment=approval.decision_comment,
            )
        )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket.id),
            action="ticket.entitlement.refreshed",
            old_values_json=json.dumps({"entitlement_status": previous_status}),
            new_values_json=json.dumps(
                {
                    "entitlement_status": entitlement_status,
                    "contract_id": ticket.contract_id,
                    "reason": reason,
                    "cancelled_approval_ids": [item.id for item in pending_approvals],
                }
            ),
        )
    )


def transition_ticket(
    db: Session,
    ticket: Ticket,
    data: TicketTransition,
    actor: User,
    *,
    commit: bool = True,
    additional_permissions: set[str] | None = None,
    source: str = "UI",
) -> Ticket:
    refresh_pending_contract_entitlement(db, ticket, actor)
    if ticket.entitlement_status == "PENDING_APPROVAL":
        raise ConflictError(
            "TICKET_AWAITING_ENTITLEMENT_APPROVAL",
            "This ticket cannot progress until its contract exception is approved.",
        )
    if ticket.version != data.version:
        raise ConflictError("CONCURRENT_UPDATE", "The ticket was updated by another user.")
    current = db.get(TicketStatus, ticket.status_id)
    target = db.scalar(select(TicketStatus).where(TicketStatus.code == data.to_status_code))
    if not current or not target:
        raise NotFoundError("Ticket status does not exist.")
    permissions = set(effective_permissions(db, actor).permissions) | (
        additional_permissions or set()
    )
    ticket_type = db.get(TicketType, ticket.ticket_type_id)
    is_change_request = bool(ticket_type and ticket_type.code == "CHANGE_REQUEST")
    require_details_on_close = resolution_details_required_on_close(db)
    validate_transition(
        current.code,
        target.code,
        data,
        permissions,
        resolution_details_required_on_close=require_details_on_close,
        require_root_cause=not is_change_request,
    )
    effective_target_code = (
        "CLOSED" if target.code == "RESOLVED" and data.close_after_resolve else target.code
    )
    from app.modules.uat.deployment_ticket_sync import validate_linked_ticket_transition

    validate_linked_ticket_transition(db, ticket, effective_target_code, source=source)
    validate_change_request_ticket_transition(db, ticket, effective_target_code)
    if target.code in {"RESOLVED", "CLOSED"}:
        default_resolution_service_id = db.scalar(
            select(ServiceCatalogItem.id).where(
                ServiceCatalogItem.is_active.in_([True]),
                ServiceCatalogItem.is_default_resolution_service.in_([True]),
            )
        )
        provided_service_ids = (
            [] if is_change_request else list(dict.fromkeys(data.resolution_service_ids))
        )
        if not is_change_request and not provided_service_ids and data.service_id is not None:
            provided_service_ids = [data.service_id]
        if not is_change_request and not provided_service_ids and default_resolution_service_id is not None:
            provided_service_ids = [default_resolution_service_id]
        if (
            not is_change_request
            and
            require_details_on_close
            and (target.code == "CLOSED" or data.close_after_resolve)
            and not provided_service_ids
        ):
            raise ConflictError(
                "RESOLUTION_SERVICE_REQUIRED",
                "Select at least one service provided before completing the resolution.",
            )
        provided_services = (
            list(
                db.scalars(
                    select(ServiceCatalogItem).where(
                        ServiceCatalogItem.id.in_(provided_service_ids),
                        ServiceCatalogItem.is_active.in_([True]),
                    )
                )
            )
            if provided_service_ids
            else []
        )
        if len(provided_services) != len(provided_service_ids):
            raise ConflictError(
                "INVALID_RESOLUTION_SERVICE",
                "One or more selected resolution services are unavailable.",
            )
        previous_resolution_service_ids = ticket.resolution_service_ids
        ticket.resolution_service_links = [
            TicketResolutionService(service_id=service_id, created_by_user_id=actor.id)
            for service_id in provided_service_ids
        ]
        if previous_resolution_service_ids != provided_service_ids:
            db.add(
                AuditLog(
                    actor_user_id=actor.id,
                    entity_type="Ticket",
                    entity_id=str(ticket.id),
                    action="ticket.resolution_services.changed",
                    old_values_json=json.dumps(
                        {"resolution_service_ids": previous_resolution_service_ids}
                    ),
                    new_values_json=json.dumps({"resolution_service_ids": provided_service_ids}),
                )
            )
        blockers = resolution_readiness_blockers(db, ticket)
        if blockers:
            if not data.readiness_override_reason:
                raise ConflictError(
                    "RESOLUTION_READINESS_BLOCKED",
                    "Complete required ticket work before resolving or closing.",
                    {"blockers": blockers},
                )
            if "ticket.resolve.override_readiness" not in permissions:
                raise AuthorizationError(
                    "You do not have permission to override resolution readiness."
                )
            db.add(
                AuditLog(
                    actor_user_id=actor.id,
                    entity_type="Ticket",
                    entity_id=str(ticket.id),
                    action="ticket.resolution_readiness.overridden",
                    reason=data.readiness_override_reason,
                    new_values_json=json.dumps({"blockers": blockers}),
                )
            )
    now = server_now()
    previous_id = ticket.status_id
    ticket.status_id = target.id
    ticket.version += 1
    ticket.last_activity_at = now
    db.add(
        TicketStatusHistory(
            ticket_id=ticket.id,
            from_status_id=previous_id,
            to_status_id=target.id,
            changed_by_user_id=actor.id,
            reason=data.reason,
            source=source,
        )
    )
    if target.code.startswith("PENDING_"):
        owner_id = data.pending_owner_user_id or actor.id
        owner = db.get(User, owner_id)
        if not owner or not owner.is_active or owner.user_type != "EMPLOYEE":
            raise NotFoundError("Pending follow-up owner does not exist or is inactive.")
        ticket.pending_reason = data.reason
        ticket.pending_owner_user_id = owner.id
        ticket.pending_follow_up_at = data.pending_follow_up_at
        responsible_party = pending_responsible_party(target.code, data.pending_responsible_party)
        db.add(
            TicketSlaInterval(
                ticket_id=ticket.id,
                interval_type="PENDING",
                responsible_party=responsible_party,
                comment=data.reason,
                started_at=now,
                created_by_user_id=actor.id,
            )
        )
        db.add(
            Notification(
                recipient_user_id=owner.id,
                notification_type="PENDING_FOLLOW_UP_SCHEDULED",
                severity="INFO",
                title=f"Pending follow-up: {ticket.ticket_number}",
                message=data.reason or "Ticket follow-up scheduled.",
                deep_link=f"/tickets/{ticket.id}",
                deduplication_key=f"pending-scheduled:{ticket.id}:version:{ticket.version}:user:{owner.id}",
            )
        )
    elif current.code.startswith("PENDING_"):
        active_pending = db.scalar(
            select(TicketSlaInterval)
            .where(
                TicketSlaInterval.ticket_id == ticket.id,
                TicketSlaInterval.interval_type == "PENDING",
                TicketSlaInterval.ended_at.is_(None),
            )
            .order_by(TicketSlaInterval.started_at.desc())
        )
        if active_pending:
            active_pending.ended_at = now
        ticket.pending_reason = None
        ticket.pending_owner_user_id = None
        ticket.pending_follow_up_at = None
    if target.code == "RESOLVED" or (target.code == "CLOSED" and require_details_on_close):
        causes = (
            list(db.scalars(select(RootCause).where(RootCause.id.in_(data.root_cause_ids))))
            if data.root_cause_ids and not is_change_request
            else []
        )
        if len(causes) != len(set(data.root_cause_ids)) or any(
            not item.is_active for item in causes
        ):
            raise ConflictError(
                "INVALID_ROOT_CAUSE", "One or more selected root causes are unavailable."
            )
        ticket.resolution_summary = data.resolution_summary
        ticket.root_cause_summary = data.root_cause_summary or ", ".join(
            sorted(item.name for item in causes)
        )
        ticket.root_cause_links = [
            TicketRootCause(root_cause_id=item.id, created_by_user_id=actor.id) for item in causes
        ]
        requires_outcome = any(item.requires_resolution_outcome for item in causes)
        requires_permanent_fix = any(item.requires_permanent_fix for item in causes)
        if requires_outcome and data.resolution_outcome_id is None:
            raise ConflictError(
                "RESOLUTION_OUTCOME_REQUIRED",
                "The selected root cause requires a resolution outcome.",
            )
        if requires_permanent_fix and (
            not data.permanent_fix_status or not data.permanent_fix_summary
        ):
            raise ConflictError(
                "PERMANENT_FIX_REQUIRED",
                "The selected root cause requires permanent-fix status and evidence or plan.",
            )
        if data.resolution_outcome_id is not None:
            outcome = db.get(ResolutionOutcome, data.resolution_outcome_id)
            if not outcome or not outcome.is_active:
                raise ConflictError(
                    "INVALID_RESOLUTION_OUTCOME", "The selected resolution outcome is unavailable."
                )
            if outcome.requires_permanent_fix and not data.permanent_fix_status:
                raise ConflictError(
                    "PERMANENT_FIX_STATUS_REQUIRED", "This outcome requires a permanent-fix status."
                )
            ticket.resolution_outcome_id = outcome.id
        ticket.permanent_fix_summary = data.permanent_fix_summary
        ticket.permanent_fix_status = data.permanent_fix_status
        if target.code == "RESOLVED":
            ticket.resolved_at = now
        from app.modules.knowledge_base.models import (
            Article,
            ArticleClientLink,
            ArticleModuleLink,
            ArticleProductLink,
            ArticleServiceLink,
            ArticleVersion,
            KnowledgeCategory,
            TicketArticleLink,
        )

        existing_draft = db.scalar(
            select(TicketArticleLink.id).where(
                TicketArticleLink.ticket_id == ticket.id,
                TicketArticleLink.reason == "AUTO_RESOLUTION_DRAFT",
            )
        )
        if data.create_knowledge_article and not existing_draft:
            ticket_knowledge_category = db.scalar(
                select(KnowledgeCategory).where(
                    KnowledgeCategory.code == "TICKETS_KNOWLEDGE_BASE"
                )
            )
            if ticket_knowledge_category is None:
                ticket_knowledge_category = KnowledgeCategory(
                    code="TICKETS_KNOWLEDGE_BASE",
                    name="Tickets Knowledge Base",
                    is_active=True,
                )
                db.add(ticket_knowledge_category)
                db.flush()
            cause_names = ", ".join(sorted(item.name for item in causes))
            body = f"Ticket: {ticket.ticket_number}\n\nProblem\n{ticket.description}\n\nRoot cause\n{cause_names or data.root_cause_summary}\n\nResolution\n{data.resolution_summary}"
            if data.permanent_fix_summary:
                body += f"\n\nPermanent fix / plan ({data.permanent_fix_status})\n{data.permanent_fix_summary}"
            article = Article(
                title=f"Resolution draft · {ticket.ticket_number} · {ticket.subject}"[:300],
                summary=str(data.resolution_summary)[:1000],
                body=body[:50000],
                category=ticket_knowledge_category.name if ticket_knowledge_category else "Tickets Knowledge Base",
                category_id=ticket_knowledge_category.id if ticket_knowledge_category else None,
                tags=f"ticket,{ticket.ticket_number},auto-draft",
                resolution_summary_template=data.resolution_summary,
                root_cause_ids_json=json.dumps(list(dict.fromkeys(data.root_cause_ids))),
                resolution_service_ids_json=json.dumps(
                    list(dict.fromkeys(data.resolution_service_ids))
                ),
                resolution_outcome_id=data.resolution_outcome_id,
                permanent_fix_summary_template=data.permanent_fix_summary,
                permanent_fix_status=data.permanent_fix_status,
                status="DRAFT",
                client_visible=False,
                visibility="INTERNAL",
                owner_user_id=actor.id,
            )
            db.add(article)
            db.flush()
            if ticket.product_id:
                article.product_links = [ArticleProductLink(product_id=ticket.product_id)]
            if ticket.product_module_id:
                article.module_links = [
                    ArticleModuleLink(product_module_id=ticket.product_module_id)
                ]
            article.client_links = [ArticleClientLink(client_id=ticket.client_id)]
            applicable_service_ids = list(
                dict.fromkeys(
                    [
                        value
                        for value in [ticket.service_id, *data.resolution_service_ids]
                        if value is not None
                    ]
                )
            )
            article.service_links = [
                ArticleServiceLink(service_id=value) for value in applicable_service_ids
            ]
            db.add(
                ArticleVersion(
                    article_id=article.id,
                    version=1,
                    title=article.title,
                    summary=article.summary,
                    body=article.body,
                    status=article.status,
                    changed_by_user_id=actor.id,
                )
            )
            db.add(
                TicketArticleLink(
                    ticket_id=ticket.id,
                    article_id=article.id,
                    linked_by_user_id=actor.id,
                    reason="AUTO_RESOLUTION_DRAFT",
                )
            )
        if data.close_after_resolve:
            closed_status = db.scalar(select(TicketStatus).where(TicketStatus.code == "CLOSED"))
            if not closed_status:
                raise NotFoundError("Closed ticket status is not configured.")
            resolved_id = target.id
            ticket.status_id = closed_status.id
            ticket.closed_at = now
            db.add(
                TicketStatusHistory(
                    ticket_id=ticket.id,
                    from_status_id=resolved_id,
                    to_status_id=closed_status.id,
                    changed_by_user_id=actor.id,
                    reason="Closed immediately after resolution",
                    source=source,
                )
            )
    if target.code == "CLOSED":
        ticket.closed_at = now
    if target.code == "CANCELLED":
        ticket.cancelled_at = server_now()
        ticket.resolved_at = None
        ticket.closed_at = None
    if target.code == "REOPENED":
        archive_resolution_before_reopen(db, ticket, actor, data.reason or "Reopened", now)
        ticket.reopened_at = now
        ticket.resolved_at = None
        ticket.closed_at = None
        ticket.cancelled_at = None
        ticket.resolution_summary = None
        ticket.root_cause_summary = None
        ticket.root_cause_links = []
        ticket.resolution_outcome_id = None
        ticket.permanent_fix_summary = None
        ticket.permanent_fix_status = None
        ticket.resolution_service_links = []
        restart_resolution_sla(db, ticket)
    if target.code == "CLIENT_CONFIRMATION":
        ticket.customer_confirmed_at = now
        ticket.customer_confirmed_by_user_id = actor.id
        ticket.customer_confirmation_channel = data.customer_confirmation_channel
        ticket.customer_confirmation_contact = data.customer_confirmation_contact
        ticket.customer_confirmation_note = data.customer_confirmation_note
    if target.code in {"RESOLVED", "CLOSED", "CANCELLED"}:
        complete_pending_shift_handover(db, ticket, actor, now)
    if target.code in {"RESOLVED", "CLOSED", "CANCELLED"}:
        complete_sla_clocks(db, ticket, {"RESOLUTION"}, now)
    queue_ticket_workflow_transition(
        db,
        ticket,
        actor,
        from_status_code=current.code,
        to_status_code=target.code,
        source=source,
    )
    if target.code == "RESOLVED" and data.close_after_resolve:
        queue_ticket_workflow_transition(
            db,
            ticket,
            actor,
            from_status_code="RESOLVED",
            to_status_code="CLOSED",
            source=source,
        )
    from app.modules.uat.service import sync_ticket_to_uat

    sync_ticket_to_uat(db, ticket, actor, target_status_code=effective_target_code)
    from app.modules.uat.deployment_ticket_sync import sync_ticket_to_issue

    sync_ticket_to_issue(
        db,
        ticket,
        actor,
        previous_ticket_status=current.code,
        target_ticket_status=effective_target_code,
        reason=data.reason,
        source=source,
    )
    if commit:
        db.commit()
        db.refresh(ticket)
    return ticket


def complete_pending_shift_handover(
    db: Session, ticket: Ticket, actor: User, completed_at: datetime
) -> bool:
    """Remove terminal tickets from the live handover queue while retaining history."""
    if ticket.shift_handover_status != "PENDING":
        return False
    handover = db.scalar(
        select(TicketShiftHandover)
        .where(
            TicketShiftHandover.ticket_id == ticket.id,
            TicketShiftHandover.status == "PENDING",
        )
        .order_by(TicketShiftHandover.created_at.desc())
    )
    if handover:
        handover.status = "COMPLETED"
        handover.completed_by_user_id = actor.id
        handover.completed_at = completed_at
    ticket.shift_handover_status = "COMPLETED"
    ticket.shift_handover_completed_at = completed_at
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket.id),
            action="ticket.shift_handover.auto_completed",
            reason="Ticket reached a terminal status",
        )
    )
    return True


def complete_sla_clocks(
    db: Session,
    ticket: Ticket,
    clock_types: set[str],
    completed_at: datetime | None = None,
) -> None:
    completed_at = completed_at or server_now()
    clocks = list(
        db.scalars(
            select(TicketSlaClock).where(
                TicketSlaClock.ticket_id == ticket.id,
                TicketSlaClock.clock_type.in_(clock_types),
                TicketSlaClock.state == "RUNNING",
            )
        )
    )
    for clock in clocks:
        if completed_at >= clock.due_at.replace(tzinfo=server_timezone()):
            clock.state = "BREACHED"
            clock.breached_at = clock.breached_at or completed_at
        else:
            clock.state = "COMPLETED"
        clock.completed_at = completed_at
        if clock.clock_type == "FIRST_RESPONSE":
            policy = db.get(SlaPolicy, clock.policy_id)
            if policy is not None:
                clock.actual_response_minutes = calculate_working_minutes(
                    db,
                    clock.calendar_id or policy.calendar_id,
                    clock.started_at.replace(tzinfo=clock.started_at.tzinfo or server_timezone()),
                    completed_at.replace(tzinfo=completed_at.tzinfo or server_timezone()),
                )
    resolution_clock = next((clock for clock in clocks if clock.clock_type == "RESOLUTION"), None)
    if resolution_clock is not None:
        from app.modules.sla.service import resolution_sla_result

        result = resolution_sla_result(db, ticket, as_of=completed_at)
        if result is not None:
            resolution_clock.accountable_minutes = result.accountable_minutes
            resolution_clock.customer_pending_minutes = result.customer_pending_minutes
            resolution_clock.millensys_pending_minutes = result.millensys_pending_minutes
            resolution_clock.escalation_minutes = result.escalation_minutes
            resolution_clock.saved_minutes = result.saved_minutes
            resolution_clock.overrun_minutes = result.overrun_minutes
            resolution_clock.outcome_calculated_at = completed_at


def restart_resolution_sla(db: Session, ticket: Ticket) -> None:
    clock = db.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket.id,
            TicketSlaClock.clock_type == "RESOLUTION",
        )
    )
    if not clock:
        return
    policy = db.get(SlaPolicy, clock.policy_id)
    if not policy:
        return
    restarted_at = server_now()
    clock.started_at = restarted_at
    clock.due_at = calculate_due_at(db, policy.calendar_id, restarted_at, clock.target_minutes)
    clock.state = "RUNNING"
    clock.breached_at = None
    clock.completed_at = None
    clock.accountable_minutes = None
    clock.customer_pending_minutes = None
    clock.millensys_pending_minutes = None
    clock.escalation_minutes = None
    clock.saved_minutes = None
    clock.overrun_minutes = None
    clock.outcome_calculated_at = None


def archive_resolution_before_reopen(
    db: Session, ticket: Ticket, actor: User, reason: str, archived_at: datetime
) -> None:
    """Preserve the completed resolution and SLA outcome before starting a new attempt."""
    if ticket.resolved_at is None:
        return
    clock = db.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket.id,
            TicketSlaClock.clock_type == "RESOLUTION",
        )
    )
    sequence = (
        int(
            db.scalar(
                select(func.max(TicketResolutionHistory.resolution_sequence)).where(
                    TicketResolutionHistory.ticket_id == ticket.id
                )
            )
            or 0
        )
        + 1
    )
    clock_fields = (
        "contract_id",
        "policy_id",
        "target_id",
        "calendar_id",
        "policy_version",
        "policy_version_id",
        "policy_code_snapshot",
        "policy_name_snapshot",
        "target_context_snapshot",
        "match_reason",
        "start_mode_snapshot",
        "target_minutes",
        "warning_percent",
        "started_at",
        "start_anchor_at",
        "due_at",
        "state",
        "breached_at",
        "completed_at",
        "accountable_minutes",
        "customer_pending_minutes",
        "millensys_pending_minutes",
        "escalation_minutes",
        "saved_minutes",
        "overrun_minutes",
        "outcome_calculated_at",
        "calculation_version",
    )
    snapshot = None
    if clock is not None:
        snapshot = json.dumps(
            {
                field: value.isoformat() if isinstance(value, datetime) else value
                for field in clock_fields
                if (value := getattr(clock, field)) is not None
            }
        )
    db.add(
        TicketResolutionHistory(
            ticket_id=ticket.id,
            resolution_sequence=sequence,
            resolution_summary=ticket.resolution_summary,
            root_cause_summary=ticket.root_cause_summary,
            root_cause_ids_json=json.dumps(ticket.root_cause_ids),
            resolution_service_ids_json=json.dumps(ticket.resolution_service_ids),
            resolution_outcome_id=ticket.resolution_outcome_id,
            permanent_fix_summary=ticket.permanent_fix_summary,
            permanent_fix_status=ticket.permanent_fix_status,
            resolved_at=ticket.resolved_at,
            closed_at=ticket.closed_at,
            sla_snapshot_json=snapshot,
            reopened_by_user_id=actor.id,
            reopen_reason=reason,
            archived_at=archived_at,
        )
    )


def synchronize_escalation_parent(
    db: Session,
    child: Ticket,
    closing_actor: User,
) -> Ticket | None:
    """Close an escalation parent only after its final open escalation child closes.

    The caller owns the transaction so the child and parent lifecycle changes are atomic.
    Parent attribution follows the operational policy requested for SupportHub: the
    parent ticket's assigned engineer receives resolution/closure attribution, with
    the actual child closer retained in the audit payload.
    """
    if child.escalation_parent_ticket_id is None:
        return None
    parent = db.get(Ticket, child.escalation_parent_ticket_id)
    if not parent:
        return None
    other_open_child_id = db.scalar(
        select(Ticket.id)
        .join(TicketStatus, Ticket.status_id == TicketStatus.id)
        .where(
            Ticket.escalation_parent_ticket_id == parent.id,
            Ticket.id != child.id,
            TicketStatus.is_closed_state.in_([False]),
        )
        .limit(1)
    )
    if other_open_child_id is not None:
        return None
    current = db.get(TicketStatus, parent.status_id)
    if not current or current.is_closed_state:
        return None
    resolved = db.scalar(select(TicketStatus).where(TicketStatus.code == "RESOLVED"))
    closed = db.scalar(select(TicketStatus).where(TicketStatus.code == "CLOSED"))
    if not resolved or not closed:
        raise NotFoundError("Resolved and closed ticket statuses must be configured.")
    now = server_now()
    attributed_user_id = parent.assigned_user_id or closing_actor.id
    if current.code != "RESOLVED":
        db.add(
            TicketStatusHistory(
                ticket_id=parent.id,
                from_status_id=parent.status_id,
                to_status_id=resolved.id,
                changed_by_user_id=attributed_user_id,
                reason=(
                    f"Automatically resolved after final escalation child "
                    f"{child.ticket_number} was closed"
                ),
                source="ESCALATION_CHILD",
            )
        )
    db.add(
        TicketStatusHistory(
            ticket_id=parent.id,
            from_status_id=resolved.id,
            to_status_id=closed.id,
            changed_by_user_id=attributed_user_id,
            reason=(
                f"Automatically closed after final escalation child "
                f"{child.ticket_number} was closed"
            ),
            source="ESCALATION_CHILD",
        )
    )
    parent.status_id = closed.id
    parent.resolution_summary = (
        child.resolution_summary or f"Completed through escalation child {child.ticket_number}."
    )
    parent.root_cause_summary = (
        child.root_cause_summary
        or f"Resolution supplied by escalation child {child.ticket_number}."
    )
    parent.resolved_at = parent.resolved_at or now
    parent.closed_at = now
    parent.escalation_assignee_user_id = None
    parent.escalation_level = None
    parent.escalation_reason = None
    parent.escalated_at = None
    parent.last_activity_at = now
    parent.version += 1
    complete_sla_clocks(db, parent, {"FIRST_RESPONSE", "RESOLUTION"}, now)
    if current.code != "RESOLVED":
        queue_ticket_workflow_transition(
            db,
            parent,
            closing_actor,
            from_status_code=current.code,
            to_status_code="RESOLVED",
            source="ESCALATION_CHILD",
        )
    queue_ticket_workflow_transition(
        db,
        parent,
        closing_actor,
        from_status_code="RESOLVED",
        to_status_code="CLOSED",
        source="ESCALATION_CHILD",
    )
    db.add(
        AuditLog(
            actor_user_id=attributed_user_id,
            entity_type="Ticket",
            entity_id=str(parent.id),
            action="ticket.closed_from_escalation_child",
            reason=f"Final escalation child {child.ticket_number} closed",
            new_values_json=json.dumps(
                {
                    "child_ticket_id": child.id,
                    "child_ticket_number": child.ticket_number,
                    "attributed_to_user_id": attributed_user_id,
                    "triggered_by_user_id": closing_actor.id,
                }
            ),
        )
    )
    return parent


def synchronize_escalation_children(
    db: Session,
    parent: Ticket,
    closing_actor: User,
) -> list[Ticket]:
    """Close active escalation children when the parent's dedicated engineer closes it."""
    if parent.escalation_parent_ticket_id is not None:
        return []
    if parent.assigned_user_id != closing_actor.id or not is_dedicated_assignee(
        db, parent.assigned_user_id
    ):
        return []
    children = list(
        db.scalars(
            select(Ticket)
            .join(TicketStatus, Ticket.status_id == TicketStatus.id)
            .where(
                Ticket.escalation_parent_ticket_id == parent.id,
                TicketStatus.is_closed_state.in_([False]),
            )
            .order_by(Ticket.id)
        )
    )
    if not children:
        return []
    resolved = db.scalar(select(TicketStatus).where(TicketStatus.code == "RESOLVED"))
    closed = db.scalar(select(TicketStatus).where(TicketStatus.code == "CLOSED"))
    if not resolved or not closed:
        raise NotFoundError("Resolved and closed ticket statuses must be configured.")
    now = server_now()
    for child in children:
        blockers = resolution_readiness_blockers(db, child)
        if blockers:
            raise ConflictError(
                "ESCALATION_CHILD_RESOLUTION_READINESS_BLOCKED",
                (
                    f"Escalation ticket {child.ticket_number} has required work "
                    "that must be completed before closing the main ticket."
                ),
                {
                    "child_ticket_id": child.id,
                    "child_ticket_number": child.ticket_number,
                    "blockers": blockers,
                },
            )
        current = db.get(TicketStatus, child.status_id)
        if not current or current.is_closed_state:
            continue
        if current.code != "RESOLVED":
            db.add(
                TicketStatusHistory(
                    ticket_id=child.id,
                    from_status_id=child.status_id,
                    to_status_id=resolved.id,
                    changed_by_user_id=closing_actor.id,
                    reason=(
                        f"Automatically resolved when main ticket "
                        f"{parent.ticket_number} was closed"
                    ),
                    source="ESCALATION_PARENT",
                )
            )
            queue_ticket_workflow_transition(
                db,
                child,
                closing_actor,
                from_status_code=current.code,
                to_status_code="RESOLVED",
                source="ESCALATION_PARENT",
            )
            child.resolution_summary = (
                parent.resolution_summary
                or f"Completed when main ticket {parent.ticket_number} was closed."
            )
            child.root_cause_summary = (
                parent.root_cause_summary
                or f"Resolution supplied by main ticket {parent.ticket_number}."
            )
            child.resolution_service_links = [
                TicketResolutionService(
                    service_id=service_id,
                    created_by_user_id=closing_actor.id,
                )
                for service_id in parent.resolution_service_ids
            ]
            child.root_cause_links = [
                TicketRootCause(
                    root_cause_id=root_cause_id,
                    created_by_user_id=closing_actor.id,
                )
                for root_cause_id in parent.root_cause_ids
            ]
            child.resolution_outcome_id = parent.resolution_outcome_id
            child.permanent_fix_summary = parent.permanent_fix_summary
            child.permanent_fix_status = parent.permanent_fix_status
            child.resolved_at = now
        db.add(
            TicketStatusHistory(
                ticket_id=child.id,
                from_status_id=resolved.id,
                to_status_id=closed.id,
                changed_by_user_id=closing_actor.id,
                reason=(
                    f"Automatically closed when main ticket "
                    f"{parent.ticket_number} was closed"
                ),
                source="ESCALATION_PARENT",
            )
        )
        queue_ticket_workflow_transition(
            db,
            child,
            closing_actor,
            from_status_code="RESOLVED",
            to_status_code="CLOSED",
            source="ESCALATION_PARENT",
        )
        child.status_id = closed.id
        child.closed_at = now
        child.last_activity_at = now
        child.version += 1
        complete_pending_shift_handover(db, child, closing_actor, now)
        complete_sla_clocks(db, child, {"FIRST_RESPONSE", "RESOLUTION"}, now)
        db.add(
            AuditLog(
                actor_user_id=closing_actor.id,
                entity_type="Ticket",
                entity_id=str(child.id),
                action="ticket.closed_from_escalation_parent",
                reason=f"Main ticket {parent.ticket_number} closed",
                new_values_json=json.dumps(
                    {
                        "parent_ticket_id": parent.id,
                        "parent_ticket_number": parent.ticket_number,
                        "triggered_by_user_id": closing_actor.id,
                    }
                ),
            )
        )
    return children
