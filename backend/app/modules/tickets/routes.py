import hashlib
import json
import re
from datetime import datetime, time, timedelta
from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import String, and_, case, cast, func, literal_column, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, require_any_permission, require_permission
from app.core.clock import server_now, server_timezone, server_today
from app.core.config import Settings, get_settings
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.contact_access import contact_belongs_to_client
from app.modules.clients.models import (
    Branch,
    Client,
    ClientLocation,
    Contact,
    ContactClientLink,
    Product,
    ProductModule,
    ServiceCatalogItem,
    SupportTeam,
    SupportTeamMember,
)
from app.modules.complaints.models import Complaint
from app.modules.configuration.models import SiteSetting
from app.modules.contracts.models import (
    Contract,
    ContractClientLink,
    ContractCoverage,
    ContractCoverageClient,
    TicketSlaClock,
    TicketSlaInterval,
)
from app.modules.contracts.service import evaluate_entitlement
from app.modules.iam.models import AuditLog, Department, DepartmentHierarchyAssignment, User
from app.modules.iam.organization import active_on, department_descendant_ids
from app.modules.iam.service import effective_permissions
from app.modules.notifications.models import EventOutbox, Notification
from app.modules.notifications.ticket_creation import queue_ticket_reassignment_email
from app.modules.sla.service import attach_ticket_sla_evidence, resolution_sla_results
from app.modules.tickets.attachments import attachment_path, save_attachment
from app.modules.tickets.models import (
    ResolutionOutcome,
    RootCause,
    SupportAssistantPreference,
    Ticket,
    TicketAssignmentHistory,
    TicketAttachment,
    TicketChecklistItem,
    TicketComment,
    TicketDeletionRequest,
    TicketFlagAssignment,
    TicketFollower,
    TicketRelation,
    TicketResolutionHistory,
    TicketResolutionService,
    TicketRootCause,
    TicketSatisfaction,
    TicketShiftHandover,
    TicketStatus,
    TicketStatusHistory,
    TicketTask,
    TicketTemplate,
    TicketType,
    TicketWorklog,
)
from app.modules.tickets.satisfaction import enqueue_satisfaction_invitation
from app.modules.tickets.schemas import (
    ChecklistItemCreate,
    ChecklistItemRead,
    ChecklistItemUpdate,
    PersonalWorkspaceItem,
    PersonalWorkspaceRead,
    PersonalWorkspaceRecentCreate,
    PersonalWorkspaceUpdate,
    ResolutionOutcomeCreate,
    ResolutionOutcomeRead,
    RootCauseCreate,
    RootCauseRead,
    RootCauseUpdate,
    SupportAssistantPreferenceRead,
    SupportAssistantPreferenceUpdate,
    SupportFollowUpUpdate,
    TicketAdvancedSearch,
    TicketArchiveRestore,
    TicketAssigneeRead,
    TicketAssignment,
    TicketAttachmentRead,
    TicketBulkAssignment,
    TicketBulkDelete,
    TicketBulkStatus,
    TicketCatalogRead,
    TicketCommentCreate,
    TicketCommentRead,
    TicketCreate,
    TicketDeletionDecision,
    TicketDeletionRequestRead,
    TicketEdit,
    TicketEscalation,
    TicketFollowerRead,
    TicketFollowersUpdate,
    TicketHelpReturn,
    TicketMentionCandidateRead,
    TicketMentionCreate,
    TicketMentionResult,
    TicketRead,
    TicketRelationCreate,
    TicketRelationRead,
    TicketRequesterUpdate,
    TicketResolutionHistoryRead,
    TicketShiftHandoverComplete,
    TicketShiftHandoverCreate,
    TicketSlaPreviewRead,
    TicketSlaPreviewRequest,
    TicketStatusUpdate,
    TicketTaskCreate,
    TicketTaskRead,
    TicketTaskUpdate,
    TicketTemplateCreate,
    TicketTemplateRead,
    TicketTemplateUpdate,
    TicketTimelineRead,
    TicketTransition,
    TicketTypeCreate,
    TicketTypeUpdate,
    TicketWorklogCreate,
    TicketWorklogDecision,
    TicketWorklogRead,
    TicketWorklogUpdate,
)
from app.modules.tickets.service import (
    DateTimeBoundary,
    apply_first_dedicated_assignment,
    apply_ticket_filters,
    compile_advanced_filter,
    create_ticket,
    derive_priority,
    ensure_assignment_eligibility,
    ensure_ticket_access,
    preview_ticket_sla,
    queue_ticket_workflow_transition,
    record_first_response,
    reevaluate_ticket_sla,
    synchronize_escalation_children,
    synchronize_escalation_parent,
    ticket_filter_lower_bound,
    ticket_filter_upper_bound,
    transition_ticket,
    validate_ticket_context,
    visible_ticket_query,
)
from app.modules.tickets.timeline import ticket_timeline
from app.modules.tickets.workflow import allowed_transition_codes, authorize_transition_actor
from app.modules.uat.models import UatCycleTest, UatDefectLink

router = APIRouter(prefix="/tickets", tags=["tickets"])
catalog_router = APIRouter(tags=["ticket catalogs"])


@router.get("/support-assistant/preferences", response_model=SupportAssistantPreferenceRead)
def get_support_assistant_preferences(
    db: Session = Depends(get_db), user: User = Depends(current_user)
) -> SupportAssistantPreferenceRead:
    preference = db.scalar(
        select(SupportAssistantPreference).where(SupportAssistantPreference.user_id == user.id)
    )
    if not preference:
        return SupportAssistantPreferenceRead()
    try:
        pinned_ids = [int(value) for value in json.loads(preference.pinned_ticket_ids_json or "[]")]
        workspace_state = json.loads(preference.workspace_state_json or "{}")
        custom_tabs = json.loads(preference.custom_tabs_json or "[]")
    except (TypeError, ValueError, json.JSONDecodeError):
        pinned_ids, workspace_state, custom_tabs = [], {}, []
    return SupportAssistantPreferenceRead.model_validate(
        {
            "pinned_ticket_ids": pinned_ids,
            "default_tab": preference.default_tab,
            "workspace_state": workspace_state,
            "custom_tabs": custom_tabs,
        }
    )


@router.put("/support-assistant/preferences", response_model=SupportAssistantPreferenceRead)
def update_support_assistant_preferences(
    data: SupportAssistantPreferenceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> SupportAssistantPreferenceRead:
    requested_ids = list(dict.fromkeys(data.pinned_ticket_ids))
    ordered_ids: list[int] = []
    for ticket_id in requested_ids:
        ticket = db.get(Ticket, ticket_id)
        if not ticket:
            # Pins are preferences, not business records. A ticket may have
            # been removed since the preference was last loaded, so discard
            # stale IDs rather than blocking unrelated preference changes.
            continue
        ensure_ticket_access(db, user, ticket)
        ordered_ids.append(ticket_id)
    preference = db.scalar(
        select(SupportAssistantPreference).where(SupportAssistantPreference.user_id == user.id)
    )
    if not preference:
        preference = SupportAssistantPreference(user_id=user.id)
        db.add(preference)
    old_value = json.dumps(
        {
            "pinned_ticket_ids": json.loads(preference.pinned_ticket_ids_json or "[]"),
            "default_tab": preference.default_tab,
            "workspace_state": json.loads(preference.workspace_state_json or "{}"),
            "custom_tabs": json.loads(preference.custom_tabs_json or "[]"),
        }
    )
    preference.pinned_ticket_ids_json = json.dumps(ordered_ids)
    preference.default_tab = data.default_tab
    preference.workspace_state_json = json.dumps(data.workspace_state.model_dump())
    preference.custom_tabs_json = json.dumps([tab.model_dump() for tab in data.custom_tabs])
    new_value = json.dumps(
        {
            "pinned_ticket_ids": ordered_ids,
            "default_tab": data.default_tab,
            "workspace_state": data.workspace_state.model_dump(),
            "custom_tabs": [tab.model_dump() for tab in data.custom_tabs],
        }
    )
    db.add(
        AuditLog(
            actor_user_id=user.id,
            entity_type="SupportAssistantPreference",
            entity_id=str(user.id),
            action="support_assistant.preferences.updated",
            old_values_json=old_value,
            new_values_json=new_value,
        )
    )
    db.commit()
    return SupportAssistantPreferenceRead(
        pinned_ticket_ids=ordered_ids,
        default_tab=data.default_tab,
        workspace_state=data.workspace_state,
        custom_tabs=data.custom_tabs,
    )


def _workspace_preference(db: Session, user_id: int) -> SupportAssistantPreference:
    preference = db.scalar(
        select(SupportAssistantPreference).where(SupportAssistantPreference.user_id == user_id)
    )
    if not preference:
        preference = SupportAssistantPreference(user_id=user_id)
        db.add(preference)
    return preference


def _workspace_items(raw: str) -> list[dict[str, object]]:
    try:
        value = json.loads(raw or "[]")
        return value if isinstance(value, list) else []
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


def _workspace_settings(raw: str) -> dict[str, object]:
    try:
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


@router.get("/my-workspace", response_model=PersonalWorkspaceRead)
def get_personal_workspace(
    db: Session = Depends(get_db), user: User = Depends(current_user)
) -> PersonalWorkspaceRead:
    preference = db.scalar(
        select(SupportAssistantPreference).where(SupportAssistantPreference.user_id == user.id)
    )
    if not preference:
        return PersonalWorkspaceRead()
    return PersonalWorkspaceRead.model_validate(
        {
            "favorites": _workspace_items(preference.workspace_favorites_json),
            "recent": _workspace_items(preference.workspace_recent_json),
            **_workspace_settings(preference.workspace_settings_json),
        }
    )


@router.put("/my-workspace", response_model=PersonalWorkspaceRead)
def update_personal_workspace(
    data: PersonalWorkspaceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> PersonalWorkspaceRead:
    preference = _workspace_preference(db, user.id)
    favorites = list(dict((item.id, item) for item in data.favorites).values())
    preference.workspace_favorites_json = json.dumps(
        [item.model_dump(mode="json") for item in favorites]
    )
    settings = _workspace_settings(preference.workspace_settings_json)
    settings["hidden_widgets"] = data.hidden_widgets
    preference.workspace_settings_json = json.dumps(settings)
    db.commit()
    return PersonalWorkspaceRead(
        favorites=favorites,
        recent=_workspace_items(preference.workspace_recent_json),
        hidden_widgets=data.hidden_widgets,
    )


@router.post("/my-workspace/recent", response_model=PersonalWorkspaceRead)
def record_personal_workspace_visit(
    data: PersonalWorkspaceRecentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> PersonalWorkspaceRead:
    preference = _workspace_preference(db, user.id)
    item = PersonalWorkspaceItem(
        id=f"page:{hashlib.sha256(data.path.encode('utf-8')).hexdigest()[:24]}",
        label=data.label,
        path=data.path,
        item_type=data.item_type,
        visited_at=server_now(),
    )
    recent = [
        existing
        for existing in _workspace_items(preference.workspace_recent_json)
        if existing.get("path") != data.path
    ]
    recent.insert(0, item.model_dump(mode="json"))
    preference.workspace_recent_json = json.dumps(recent[:20])
    db.commit()
    return PersonalWorkspaceRead(
        favorites=_workspace_items(preference.workspace_favorites_json),
        recent=recent[:20],
        **_workspace_settings(preference.workspace_settings_json),
    )


@router.put("/{ticket_id}/support-follow-up", response_model=TicketRead)
def update_support_follow_up(
    ticket_id: int,
    data: SupportFollowUpUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("support_assistant.follow_up.view")),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError("Ticket does not exist.")
    ensure_ticket_access(db, actor, ticket)
    if ticket.version != data.version:
        raise ConflictError("TICKET_VERSION_CONFLICT", "The ticket changed. Refresh and try again.")
    previous = ticket.support_follow_up_flag
    ticket.support_follow_up_flag = data.marked
    ticket.version += 1
    ticket.updated_at = server_now()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket.id),
            action="ticket.support_follow_up.updated",
            old_values_json=json.dumps({"marked": previous}),
            new_values_json=json.dumps({"marked": data.marked}),
        )
    )
    db.commit()
    db.refresh(ticket)
    return attach_ticket_queue_evidence(db, attach_ticket_sla_evidence(db, [ticket]))[0]


@router.get("/feedback-metrics")
def feedback_metrics(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("dashboard.manager")),
) -> dict[str, object]:
    eligible = (
        db.scalar(
            select(func.count())
            .select_from(TicketSatisfaction)
            .where(
                TicketSatisfaction.feedback_source == "CUSTOMER",
                TicketSatisfaction.metric_eligible.in_([True]),
                TicketSatisfaction.eligibility_status == "ELIGIBLE",
            )
        )
        or 0
    )
    responses = (
        db.scalar(
            select(func.count())
            .select_from(TicketSatisfaction)
            .where(
                TicketSatisfaction.feedback_source == "CUSTOMER",
                TicketSatisfaction.metric_eligible.in_([True]),
                TicketSatisfaction.eligibility_status == "ELIGIBLE",
                TicketSatisfaction.submitted_at.is_not(None),
            )
        )
        or 0
    )
    average = db.scalar(
        select(func.avg(TicketSatisfaction.service_rating)).where(
            TicketSatisfaction.feedback_source == "CUSTOMER",
            TicketSatisfaction.metric_eligible.in_([True]),
            TicketSatisfaction.eligibility_status == "ELIGIBLE",
            TicketSatisfaction.submitted_at.is_not(None),
        )
    )
    minimum_sample = 10
    return {
        "source": "CUSTOMER",
        "eligible_requests": eligible,
        "response_count": responses,
        "response_rate_percent": round(responses * 100 / eligible, 2) if eligible else 0.0,
        "minimum_sample": minimum_sample,
        "status": "AVAILABLE" if eligible >= minimum_sample else "INSUFFICIENT_DATA",
        "average_service_rating": round(float(average), 2)
        if average is not None and eligible >= minimum_sample
        else None,
        "individual_engineer_score_enabled": False,
    }


@catalog_router.get("/root-causes", response_model=list[RootCauseRead])
def list_root_causes(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
) -> list[RootCause]:
    statement = select(RootCause)
    if not include_inactive:
        statement = statement.where(RootCause.is_active.in_([True]))
    return list(db.scalars(statement.order_by(RootCause.name)))


@catalog_router.post("/root-causes", response_model=RootCauseRead, status_code=201)
def create_root_cause(
    data: RootCauseCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> RootCause:
    values = data.model_dump()
    requested_code = values.pop("code", None)
    item = RootCause(code=requested_code or f"PENDING-RCA-{server_now().timestamp()}", **values)
    db.add(item)
    try:
        db.flush()
        if not requested_code:
            item.code = f"RCA-{item.id:06d}"
        db.commit()
    except Exception as exc:
        db.rollback()
        raise ConflictError(
            "DUPLICATE_ROOT_CAUSE", "That root-cause code or name already exists."
        ) from exc
    db.refresh(item)
    return item


@catalog_router.patch("/root-causes/{root_cause_id}", response_model=RootCauseRead)
def update_root_cause(
    root_cause_id: int,
    data: RootCauseUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("configuration.manage")),
) -> RootCause:
    item = db.get(RootCause, root_cause_id)
    if not item:
        raise NotFoundError("Root cause does not exist.")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@catalog_router.delete("/root-causes/{root_cause_id}", status_code=204)
def delete_root_cause(
    root_cause_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("configuration.manage")),
) -> Response:
    item = db.get(RootCause, root_cause_id)
    if not item:
        raise NotFoundError("Root cause does not exist.")
    if db.scalar(
        select(TicketRootCause.ticket_id)
        .where(TicketRootCause.root_cause_id == root_cause_id)
        .limit(1)
    ):
        item.is_active = False
    else:
        db.delete(item)
    db.commit()
    return Response(status_code=204)


@catalog_router.get("/resolution-outcomes", response_model=list[ResolutionOutcomeRead])
def list_resolution_outcomes(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
) -> list[ResolutionOutcome]:
    statement = select(ResolutionOutcome)
    if not include_inactive:
        statement = statement.where(ResolutionOutcome.is_active.in_([True]))
    return list(db.scalars(statement.order_by(ResolutionOutcome.name)))


@catalog_router.post("/resolution-outcomes", response_model=ResolutionOutcomeRead, status_code=201)
def create_resolution_outcome(
    data: ResolutionOutcomeCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> ResolutionOutcome:
    values = data.model_dump()
    requested_code = values.pop("code", None)
    item = ResolutionOutcome(
        code=requested_code or f"PENDING-OUT-{server_now().timestamp()}", **values
    )
    db.add(item)
    try:
        db.flush()
        if not requested_code:
            item.code = f"OUT-{item.id:06d}"
    except Exception as exc:
        db.rollback()
        raise ConflictError(
            "DUPLICATE_RESOLUTION_OUTCOME", "That outcome code or name already exists."
        ) from exc
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ResolutionOutcome",
            entity_id=str(item.id),
            action="resolution.outcome.created",
        )
    )
    db.commit()
    db.refresh(item)
    return item


@catalog_router.get("/ticket-contract-catalog")
def ticket_contract_catalog(
    client_id: int,
    pre_ticket: bool = False,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_any_permission(
            "ticket.create",
            "ticket.pre_ticket.create",
            "ticket.pre_ticket.queue.process",
            "ticket.pre_ticket.convert_assign",
            "ticket.view.own",
            "ticket.view.team",
            "ticket.view.department",
            "ticket.view.all",
        )
    ),
) -> dict[str, object]:
    if pre_ticket and {
        "ticket.pre_ticket.create",
        "ticket.pre_ticket.queue.process",
        "ticket.pre_ticket.convert_assign",
    }.isdisjoint(effective_permissions(db, actor).permissions):
        raise AuthorizationError(
            details={
                "required_permissions": [
                    "ticket.pre_ticket.create",
                    "ticket.pre_ticket.queue.process",
                    "ticket.pre_ticket.convert_assign",
                ]
            }
        )
    if not db.get(Client, client_id):
        raise NotFoundError("Client does not exist.")
    today = server_today()
    contracts = list(
        db.scalars(
            select(Contract).where(
                or_(
                    Contract.applies_to_all_clients.in_([True]),
                    Contract.client_id == client_id,
                    Contract.client_links.any(ContractClientLink.client_id == client_id),
                ),
                Contract.is_active.in_([True]),
                Contract.status == "ACTIVE",
                Contract.start_date <= today,
                Contract.end_date >= today,
            )
        )
    )
    rows = list(
        db.scalars(
            select(ContractCoverage).where(
                ContractCoverage.contract_id.in_([contract.id for contract in contracts]),
                or_(
                    ~ContractCoverage.client_links.any(),
                    ContractCoverage.client_links.any(
                        ContractCoverageClient.client_id == client_id
                    ),
                ),
            )
        )
    )
    products = list(
        db.scalars(select(Product).where(Product.is_active.in_([True])).order_by(Product.name))
    )
    modules = list(
        db.scalars(
            select(ProductModule)
            .where(ProductModule.is_active.in_([True]))
            .order_by(ProductModule.name)
        )
    )
    services = list(
        db.scalars(
            select(ServiceCatalogItem)
            .where(ServiceCatalogItem.is_active.in_([True]))
            .order_by(ServiceCatalogItem.name)
        )
    )
    contracts_with_rows = {row.contract_id for row in rows}
    blanket = any(contract.id not in contracts_with_rows for contract in contracts) or any(
        row.is_covered
        and all(
            getattr(row, field) is None
            for field in (
                "product_id",
                "product_module_id",
                "branch_id",
                "environment_id",
                "service_id",
                "ticket_type_id",
            )
        )
        for row in rows
    )
    product_ids = {row.product_id for row in rows if row.is_covered and row.product_id}
    module_ids = {row.product_module_id for row in rows if row.is_covered and row.product_module_id}
    service_ids = {row.service_id for row in rows if row.is_covered and row.service_id}
    excluded_product_ids = {row.product_id for row in rows if not row.is_covered and row.product_id}
    excluded_module_ids = {
        row.product_module_id for row in rows if not row.is_covered and row.product_module_id
    }
    excluded_service_ids = {row.service_id for row in rows if not row.is_covered and row.service_id}
    for row in rows:
        if row.is_covered and row.product_id and row.product_module_id is None:
            module_ids.update(item.id for item in modules if item.product_id == row.product_id)
    show_all = pre_ticket or any(
        contract.ticket_catalog_visibility == "ALL_WITH_COVERAGE_STATUS" for contract in contracts
    )
    return {
        "visibility_mode": "ALL_WITH_COVERAGE_STATUS" if show_all else "CONTRACT_ONLY",
        "products": [
            {
                "id": value.id,
                "name": value.name,
                "name_ar": value.name_ar,
                "covered": (blanket or value.id in product_ids)
                and value.id not in excluded_product_ids,
            }
            for value in products
            if show_all
            or ((blanket or value.id in product_ids) and value.id not in excluded_product_ids)
        ],
        "modules": [
            {
                "id": value.id,
                "name": value.name,
                "name_ar": value.name_ar,
                "product_id": value.product_id,
                "covered": (blanket or value.id in module_ids)
                and value.id not in excluded_module_ids,
            }
            for value in modules
            if show_all
            or ((blanket or value.id in module_ids) and value.id not in excluded_module_ids)
        ],
        "services": [
            {
                "id": value.id,
                "name": value.name,
                "name_ar": value.name_ar,
                "is_default_resolution_service": value.is_default_resolution_service,
                "covered": (blanket or value.id in service_ids)
                and value.id not in excluded_service_ids,
            }
            for value in services
            if show_all
            or ((blanket or value.id in service_ids) and value.id not in excluded_service_ids)
        ],
    }


def _is_shared_support_assignee(db: Session, user_id: int | None) -> bool:
    """Return whether an assignment is the configured/shared Support queue account."""
    if user_id is None:
        return True
    configured = db.get(SiteSetting, "default_assignee_user_id")
    if configured and configured.value.isdigit() and int(configured.value) == user_id:
        return True
    assignee = db.get(User, user_id)
    return bool(assignee and assignee.username_normalized == "support")


def attach_ticket_queue_evidence(db: Session, tickets: list[Ticket]) -> list[Ticket]:
    if not tickets:
        return tickets
    user_ids = {
        user_id
        for ticket in tickets
        for user_id in (ticket.created_by_user_id, ticket.assigned_user_id)
        if user_id is not None
    }
    users = (
        {item.id: item for item in db.scalars(select(User).where(User.id.in_(user_ids)))}
        if user_ids
        else {}
    )
    client_ids = {ticket.client_id for ticket in tickets}
    clients = {
        item.id: item for item in db.scalars(select(Client).where(Client.id.in_(client_ids)))
    }
    uat_links = {
        item.ticket_id: item
        for item in db.scalars(
            select(UatDefectLink).where(UatDefectLink.ticket_id.in_({ticket.id for ticket in tickets}))
        )
    }
    uat_tests = {
        item.id: item
        for item in db.scalars(
            select(UatCycleTest).where(
                UatCycleTest.id.in_({item.cycle_test_id for item in uat_links.values()})
            )
        )
    } if uat_links else {}
    requester_ids = {item.requester_contact_id for item in tickets if item.requester_contact_id}
    contacts = (
        {item.id: item for item in db.scalars(select(Contact).where(Contact.id.in_(requester_ids)))}
        if requester_ids
        else {}
    )
    active_flag_rows = (
        list(
            db.scalars(
                select(TicketFlagAssignment).where(
                    TicketFlagAssignment.ticket_id.in_({item.id for item in tickets}),
                    TicketFlagAssignment.removed_at.is_(None),
                )
            )
        )
        if tickets
        else []
    )
    flags_by_ticket: dict[int, list[dict[str, object]]] = {}
    for flag in active_flag_rows:
        flags_by_ticket.setdefault(flag.ticket_id, []).append(
            {
                "id": flag.id,
                "flag_id": flag.flag_id,
                "code": flag.flag_code_snapshot,
                "name": flag.flag_name_snapshot,
                "color": flag.flag_color_snapshot,
                "pauses_sla": flag.pauses_sla_snapshot,
            }
        )
    ticket_department_ids: dict[int, int] = {}
    for ticket in tickets:
        owner = users.get(ticket.assigned_user_id or ticket.created_by_user_id)
        department_id = ticket.routed_department_id or (owner.department_id if owner else None)
        if department_id is not None:
            ticket_department_ids[ticket.id] = department_id
    department_ids = set(ticket_department_ids.values())
    today = server_today()
    assignments = {
        item.department_id: item
        for item in db.scalars(
            select(DepartmentHierarchyAssignment)
            .where(
                DepartmentHierarchyAssignment.department_id.in_(department_ids),
                active_on(DepartmentHierarchyAssignment, today),
            )
            .order_by(
                DepartmentHierarchyAssignment.effective_from,
                DepartmentHierarchyAssignment.id,
            )
        )
    }
    parent_ids = {
        item.parent_department_id
        for item in assignments.values()
        if item.parent_department_id is not None
    }
    all_department_ids = department_ids | parent_ids
    departments = (
        {
            item.id: item
            for item in db.scalars(select(Department).where(Department.id.in_(all_department_ids)))
        }
        if all_department_ids
        else {}
    )
    configured = db.get(SiteSetting, "default_assignee_user_id")
    shared_user_id = int(configured.value) if configured and configured.value.isdigit() else None
    for ticket in tickets:
        creator = users.get(ticket.created_by_user_id)
        client = clients.get(ticket.client_id)
        requester = (
            contacts.get(ticket.requester_contact_id) if ticket.requester_contact_id else None
        )
        department = (
            departments.get(ticket_department_ids[ticket.id])
            if ticket.id in ticket_department_ids
            else None
        )
        assignment = assignments.get(department.id) if department else None
        parent = (
            departments.get(assignment.parent_department_id)
            if assignment and assignment.parent_department_id is not None
            else None
        )
        ticket.__dict__["created_by_name"] = creator.full_name if creator else None
        ticket.__dict__["client_name"] = client.name if client else None
        ticket.__dict__["requester_name"] = requester.full_name if requester else None
        ticket.__dict__["requester_phone_number"] = requester.phone_number if requester else None
        ticket.__dict__["requester_email"] = requester.email if requester else None
        ticket.__dict__["requester_job_title"] = requester.job_title if requester else None
        ticket.__dict__["active_flags"] = flags_by_ticket.get(ticket.id, [])
        ticket.__dict__["department_id"] = department.id if department else None
        ticket.__dict__["department_name"] = department.name if department else None
        ticket.__dict__["parent_department_id"] = parent.id if parent else None
        ticket.__dict__["parent_department_name"] = parent.name if parent else None
        assignee = users.get(ticket.assigned_user_id) if ticket.assigned_user_id else None
        ticket.__dict__["assigned_user_name"] = assignee.full_name if assignee else None
        ticket.__dict__["is_shared_assignment"] = (
            ticket.assigned_user_id is None
            or ticket.assigned_user_id == shared_user_id
            or bool(assignee and assignee.username_normalized == "support")
        )
        uat_link = uat_links.get(ticket.id)
        ticket.__dict__["is_uat_defect"] = uat_link is not None
        ticket.__dict__["uat_cycle_id"] = uat_link.cycle_id if uat_link else None
        ticket.__dict__["uat_cycle_test_id"] = uat_link.cycle_test_id if uat_link else None
        ticket.__dict__["uat_attempt_id"] = uat_link.attempt_id if uat_link else None
        ticket.__dict__["uat_cycle_code"] = uat_link.cycle_code if uat_link else None
        ticket.__dict__["uat_test_code"] = uat_link.test_code if uat_link else None
        ticket.__dict__["uat_release_version"] = uat_link.release_version if uat_link else None
        uat_test = uat_tests.get(uat_link.cycle_test_id) if uat_link else None
        ticket.__dict__["uat_workflow_status"] = (
            uat_test.workflow_status
            if uat_test and uat_test.test_result != "NOT_TESTED"
            else (uat_test.client_workflow_status if uat_test else None)
        )
        ticket.__dict__["uat_ready_for_closure"] = bool(
            uat_test
            and (
                (uat_test.retest_count > 0 and uat_test.test_result == "PASS")
                or (
                    uat_test.client_attempt_count > 1
                    and uat_test.client_test_result == "PASS"
                )
            )
        )
        ticket.__dict__["uat_closure_warning"] = bool(
            uat_test
            and ticket.closed_at
            and (
                uat_test.test_result == "FAIL" or uat_test.client_test_result == "FAIL"
            )
        )
    return tickets


def _trusted_database_id_literals(values: list[int]) -> list[object]:
    """Create bind-free integer literals only for IDs obtained from our database."""
    return [literal_column(str(value)) for value in values]


@router.get("", response_model=list[TicketRead])
def list_tickets(
    response: Response,
    search: str | None = Query(default=None, max_length=100),
    ticket_number: str | None = Query(default=None, max_length=100),
    subject: str | None = Query(default=None, max_length=300),
    description: str | None = Query(default=None, max_length=500),
    impact: str | None = None,
    urgency: str | None = None,
    affected_users: str | None = Query(default=None, max_length=300),
    patient_safety_flag: bool | None = None,
    security_incident_flag: bool | None = None,
    resolution_summary: str | None = Query(default=None, max_length=500),
    status_code: str | None = None,
    priority: str | None = None,
    client_id: str | None = None,
    country_id: int | None = None,
    zone: str | None = Query(default=None, max_length=150),
    location_id: int | None = None,
    team_id: int | None = None,
    engineer_id: int | None = None,
    assigned_user_id: str | None = None,
    created_by_user_id: str | None = None,
    department_id: str | None = None,
    parent_department_id: str | None = None,
    requester_contact_id: str | None = None,
    branch_id: str | None = None,
    assigned_team: str | None = None,
    my_teams_only: bool = False,
    my_department_requests: bool = False,
    routed_department_id: str | None = None,
    routed_team_id: str | None = None,
    routing_status: str | None = Query(default=None, max_length=100),
    department_requests_only: bool = False,
    escalations_sent_only: bool = False,
    product_id: str | None = None,
    product_module_id: str | None = None,
    ticket_type_id: str | None = None,
    exclude_ticket_type_code: str | None = Query(default=None, max_length=30),
    environment_id: str | None = None,
    service_id: str | None = None,
    category_id: str | None = None,
    subcategory_id: str | None = None,
    root_cause_id: str | None = None,
    entitlement_status: str | None = None,
    source_channel: str | None = Query(default=None, max_length=30),
    uat_defect_only: bool = False,
    uat_cycle_code: str | None = Query(default=None, max_length=80),
    uat_release_version: str | None = Query(default=None, max_length=100),
    sla_state: str | None = Query(default=None, max_length=100),
    open_only: bool = False,
    unassigned_only: bool = False,
    strictly_unassigned_only: bool = False,
    due_soon: bool = False,
    needs_attention: bool = False,
    breached_only: bool = False,
    resolved_only: bool = False,
    incomplete_resolution_only: bool = False,
    without_product: bool = False,
    assistant_module: str | None = Query(
        default=None,
        pattern="^(queue|mine|resolved|backlog|sla-risk|follow-up|missing-resolution)$",
    ),
    shift_handover_only: bool = False,
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
    assigned_from: DateTimeBoundary | None = None,
    assigned_to: DateTimeBoundary | None = None,
    timezone_offset_minutes: int = Query(default=180, ge=-840, le=840),
    sort_by: str = Query(
        default="updated_at",
        pattern="^(updated_at|created_at|resolved_at|priority|ticket_number)$",
    ),
    sort_direction: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[Ticket]:
    def query_ids(value: str | None) -> set[int]:
        return {int(part) for part in (value or "").split(",") if part.strip().isdigit()}

    parent_scope_ids: set[int] = set()
    for selected_parent_id in query_ids(parent_department_id):
        parent_scope_ids.update(
            department_descendant_ids(db, selected_parent_id, server_today(), include_self=True)
        )
    assigned_teams = None
    routed_team_ids = None
    if my_teams_only:
        my_teams = list(
            db.execute(
                select(SupportTeam.id, SupportTeam.name)
                .outerjoin(SupportTeamMember, SupportTeamMember.team_id == SupportTeam.id)
                .where(
                    SupportTeam.is_active.in_([True]),
                    or_(
                        SupportTeamMember.user_id == user.id,
                        SupportTeam.leader_user_id == user.id,
                    ),
                )
            ).all()
        )
        assigned_teams = {row.name for row in my_teams}
        routed_team_ids = {row.id for row in my_teams}
    base_statement = visible_ticket_query(db, user)
    if uat_defect_only or uat_cycle_code or uat_release_version:
        uat_ticket_ids = select(UatDefectLink.ticket_id)
        if uat_cycle_code:
            uat_ticket_ids = uat_ticket_ids.where(UatDefectLink.cycle_code == uat_cycle_code)
        if uat_release_version:
            uat_ticket_ids = uat_ticket_ids.where(UatDefectLink.release_version == uat_release_version)
        base_statement = base_statement.where(Ticket.id.in_(uat_ticket_ids))
    assistant_queue_default_scope = False
    if assistant_module:
        required = {
            "queue": "support_assistant.queue.view",
            "mine": "support_assistant.mine.view",
            "resolved": "support_assistant.mine.view",
            "backlog": "support_assistant.backlog.view",
            "sla-risk": "support_assistant.sla_risk.view",
            "follow-up": "support_assistant.follow_up.view",
            "missing-resolution": "support_assistant.mine.view",
        }[assistant_module]
        if required not in set(effective_permissions(db, user).permissions):
            raise AuthorizationError()
        if assistant_module == "queue":
            if not status_code:
                # The normal queue is today's work, but an older reopened ticket
                # must return to the queue instead of being hidden by its original
                # creation date.
                assistant_queue_default_scope = True
            open_only = True
            unassigned_only = True
        elif assistant_module == "mine":
            if not status_code:
                created_from = created_from or server_today()
                created_to = created_to or server_today()
            assigned_user_id = str(user.id)
        elif assistant_module == "resolved":
            # Support Now is a shared operational exception queue. Visibility
            # remains governed by visible_ticket_query; do not narrow it to the
            # current assignee as the Support App shortcut does that explicitly.
            status_code = "RESOLVED"
        elif assistant_module == "backlog":
            assigned_user_id = str(user.id)
            open_only = not status_code
        elif assistant_module == "follow-up":
            open_only = True
            base_statement = base_statement.where(Ticket.support_follow_up_flag.in_([True]))
        elif assistant_module == "sla-risk":
            open_only = True
            now = server_now()
            if db.bind is not None and db.bind.dialect.name == "mssql":
                halfway = func.dateadd(
                    literal_column("minute"),
                    TicketSlaClock.target_minutes / 2,
                    TicketSlaClock.started_at,
                )
            else:
                modifier = "+" + cast(TicketSlaClock.target_minutes / 2, String) + " minutes"
                halfway = func.datetime(TicketSlaClock.started_at, modifier)
            at_risk_ids = select(TicketSlaClock.ticket_id).where(
                TicketSlaClock.clock_type == "RESOLUTION",
                TicketSlaClock.state == "RUNNING",
                halfway <= now,
            )
            base_statement = base_statement.where(Ticket.id.in_(at_risk_ids))
        elif assistant_module == "missing-resolution":
            assigned_user_id = str(user.id)
            resolved_status_ids = select(TicketStatus.id).where(TicketStatus.code == "RESOLVED")
            has_service = (
                select(TicketResolutionService.ticket_id)
                .where(TicketResolutionService.ticket_id == Ticket.id)
                .exists()
            )
            has_root_cause = (
                select(TicketRootCause.ticket_id)
                .where(TicketRootCause.ticket_id == Ticket.id)
                .exists()
            )
            base_statement = base_statement.where(
                Ticket.status_id.in_(resolved_status_ids),
                or_(
                    Ticket.resolution_summary.is_(None),
                    func.trim(Ticket.resolution_summary) == "",
                    ~has_service,
                    and_(
                        Ticket.root_cause_summary.is_(None),
                        ~has_root_cause,
                    ),
                ),
            )
    # Dashboard drill-through filters use the effective location (ticket branch,
    # then client primary location) and support-team membership, exactly as the
    # dashboard summary does. Keep these filters in SQL so counts and paging stay
    # correct for large queues.
    if any((country_id, zone, location_id)):
        base_statement = (
            base_statement.join(Client, Client.id == Ticket.client_id)
            .outerjoin(Branch, Branch.id == Ticket.branch_id)
            .outerjoin(
                ClientLocation,
                ClientLocation.id == func.coalesce(Branch.location_id, Client.primary_location_id),
            )
        )
        if country_id:
            base_statement = base_statement.where(
                func.coalesce(ClientLocation.country_id, Client.country_id) == country_id
            )
        if zone:
            base_statement = base_statement.where(
                func.coalesce(ClientLocation.zone, Client.zone) == zone
            )
        if location_id:
            base_statement = base_statement.where(ClientLocation.id == location_id)
    if engineer_id:
        base_statement = base_statement.where(Ticket.assigned_user_id == engineer_id)
    if team_id:
        team_user_ids = select(SupportTeamMember.user_id).where(
            SupportTeamMember.team_id == team_id
        )
        base_statement = base_statement.where(
            or_(
                Ticket.routed_team_id == team_id,
                Ticket.assigned_user_id.in_(team_user_ids),
            )
        )
    if assigned_from or assigned_to:
        assignment_ids = select(TicketAssignmentHistory.ticket_id)
        if assigned_from:
            assignment_ids = assignment_ids.where(
                TicketAssignmentHistory.created_at >= ticket_filter_lower_bound(assigned_from)
            )
        if assigned_to:
            upper, exclusive = ticket_filter_upper_bound(assigned_to)
            assignment_ids = assignment_ids.where(
                TicketAssignmentHistory.created_at < upper
                if exclusive
                else TicketAssignmentHistory.created_at <= upper
            )
        base_statement = base_statement.where(Ticket.id.in_(assignment_ids))
    if my_department_requests:
        base_statement = base_statement.where(
            Ticket.routed_department_id
            == (user.department_id if user.department_id is not None else -1)
        )
    if shift_handover_only:
        base_statement = base_statement.where(Ticket.shift_handover_status == "PENDING")
    if exclude_ticket_type_code and not ticket_type_id:
        excluded_type_ids = select(TicketType.id).where(TicketType.code == exclude_ticket_type_code)
        base_statement = base_statement.where(Ticket.ticket_type_id.not_in(excluded_type_ids))
    statement = apply_ticket_filters(
        base_statement,
        search=search,
        ticket_number=ticket_number,
        subject=subject,
        description=description,
        impact=impact,
        urgency=urgency,
        affected_users=affected_users,
        patient_safety_flag=patient_safety_flag,
        security_incident_flag=security_incident_flag,
        resolution_summary=resolution_summary,
        status_code=status_code,
        priority=priority,
        client_id=client_id,
        assigned_user_id=assigned_user_id,
        created_by_user_id=created_by_user_id,
        department_ids=query_ids(department_id),
        parent_department_ids=parent_scope_ids,
        requester_contact_id=requester_contact_id,
        branch_id=branch_id,
        assigned_team=assigned_team,
        assigned_teams=assigned_teams,
        routed_team_ids=routed_team_ids,
        routed_department_id=routed_department_id,
        routed_team_id=routed_team_id,
        routing_status=routing_status,
        department_requests_only=department_requests_only,
        escalations_sent_only=escalations_sent_only,
        product_id=product_id,
        product_module_id=product_module_id,
        ticket_type_id=ticket_type_id,
        environment_id=environment_id,
        service_id=service_id,
        category_id=category_id,
        subcategory_id=subcategory_id,
        root_cause_id=root_cause_id,
        entitlement_status=entitlement_status,
        source_channel=source_channel,
        sla_state=sla_state,
        open_only=open_only,
        include_pending_approval_in_open=uat_defect_only,
        unassigned_only=unassigned_only,
        strictly_unassigned_only=strictly_unassigned_only,
        due_soon=due_soon,
        needs_attention=needs_attention,
        # Apply the authoritative accountable-business-time SLA calculation
        # below. The former clock-state shortcut could disagree with the
        # dashboard card when pauses, calendars, or completed clocks applied.
        breached_only=False,
        resolved_only=resolved_only,
        without_product=without_product,
        created_from=created_from,
        created_to=created_to,
        updated_from=updated_from,
        updated_to=updated_to,
        resolved_from=resolved_from,
        resolved_to=resolved_to,
        first_occurred_from=first_occurred_from,
        first_occurred_to=first_occurred_to,
        closed_from=closed_from,
        closed_to=closed_to,
        timezone_offset_minutes=timezone_offset_minutes,
    )
    if incomplete_resolution_only:
        resolved_status_ids = select(TicketStatus.id).where(TicketStatus.code == "RESOLVED")
        has_service = (
            select(TicketResolutionService.ticket_id)
            .where(TicketResolutionService.ticket_id == Ticket.id)
            .exists()
        )
        has_root_cause = (
            select(TicketRootCause.ticket_id).where(TicketRootCause.ticket_id == Ticket.id).exists()
        )
        statement = statement.where(
            Ticket.status_id.in_(resolved_status_ids),
            or_(
                Ticket.resolution_summary.is_(None),
                func.trim(Ticket.resolution_summary) == "",
                ~has_service,
                and_(
                    or_(
                        Ticket.root_cause_summary.is_(None),
                        func.trim(Ticket.root_cause_summary) == "",
                    ),
                    ~has_root_cause,
                ),
            ),
        )
    if assistant_queue_default_scope:
        today = server_today()
        start_of_today = datetime.combine(today, time.min, tzinfo=server_timezone())
        start_of_tomorrow = start_of_today + timedelta(days=1)
        reopened_status_ids = select(TicketStatus.id).where(TicketStatus.code == "REOPENED")
        statement = statement.where(
            or_(
                and_(Ticket.created_at >= start_of_today, Ticket.created_at < start_of_tomorrow),
                Ticket.status_id.in_(reopened_status_ids),
            )
        )
    if breached_only:
        # Completed clocks with a complete persisted outcome and no overrun can
        # never become breached later. Exclude them in SQL before running the
        # authoritative business-calendar calculation, which is substantially
        # more expensive than the list query on large ticket portfolios.
        breach_candidate_ids = select(TicketSlaClock.ticket_id).where(
            TicketSlaClock.clock_type == "RESOLUTION",
            or_(
                TicketSlaClock.completed_at.is_(None),
                TicketSlaClock.overrun_minutes > 0,
                TicketSlaClock.accountable_minutes.is_(None),
                TicketSlaClock.customer_pending_minutes.is_(None),
                TicketSlaClock.millensys_pending_minutes.is_(None),
                TicketSlaClock.escalation_minutes.is_(None),
                TicketSlaClock.saved_minutes.is_(None),
                TicketSlaClock.overrun_minutes.is_(None),
            ),
        )
        statement = statement.where(Ticket.id.in_(breach_candidate_ids))
        breach_candidates = list(db.scalars(statement.order_by(None)))
        breached_ids = [
            ticket_id
            for ticket_id, result in resolution_sla_results(
                db, breach_candidates, as_of=server_now()
            ).items()
            if not result.met
        ]
        # These IDs are produced from rows already returned by this database,
        # not from request input. Render them as integer SQL literals so large
        # SLA result sets do not exceed SQL Server's 2,100-parameter limit when
        # another list-page filter is applied.
        trusted_breached_ids = breached_ids or [-1]
        statement = statement.where(
            Ticket.id.in_(_trusted_database_id_literals(trusted_breached_ids))
        )
    response.headers["X-Total-Count"] = str(
        db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    )
    sort_column = {
        "updated_at": Ticket.updated_at,
        "created_at": Ticket.created_at,
        "resolved_at": Ticket.resolved_at,
        "priority": Ticket.priority,
        "ticket_number": Ticket.ticket_number,
    }[sort_by]
    ordering = sort_column.asc() if sort_direction == "asc" else sort_column.desc()
    if assistant_module in {"queue", "mine", "resolved"}:
        reopened_status_ids = select(TicketStatus.id).where(TicketStatus.code == "REOPENED")
        reopened_first = case((Ticket.status_id.in_(reopened_status_ids), 0), else_=1)
        statement = statement.order_by(reopened_first, ordering)
    else:
        statement = statement.order_by(ordering)
    tickets = list(db.scalars(statement.offset(offset).limit(limit)))
    return attach_ticket_queue_evidence(db, attach_ticket_sla_evidence(db, tickets))


@router.get("/filter-options")
def ticket_filter_options(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, list[dict[str, object]]]:
    visible_ids = visible_ticket_query(db, user).with_only_columns(Ticket.id)
    creator_ids = select(Ticket.created_by_user_id).where(Ticket.id.in_(visible_ids)).distinct()
    creators = list(
        db.scalars(select(User).where(User.id.in_(creator_ids)).order_by(User.full_name))
    )
    departments = list(
        db.scalars(
            select(Department).where(Department.is_active.in_([True])).order_by(Department.name)
        )
    )
    return {
        "creators": [{"id": item.id, "name": item.full_name} for item in creators],
        "departments": [
            {"id": item.id, "name": item.name, "parent_department_id": item.parent_department_id}
            for item in departments
        ],
    }


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket_endpoint(
    data: TicketCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.create")),
) -> Ticket:
    if data.source_channel == "CLIENT_PORTAL":
        raise ConflictError(
            "INVALID_TICKET_ORIGIN", "Client Portal origin is assigned only by the portal."
        )
    return create_ticket(db, data, actor)


@router.post("/advanced-search", response_model=list[TicketRead])
def advanced_ticket_search(
    data: TicketAdvancedSearch,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[Ticket]:
    statement = visible_ticket_query(db, user).where(compile_advanced_filter(data.filter))
    response.headers["X-Total-Count"] = str(
        db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    )
    sort_column = {
        "updated_at": Ticket.updated_at,
        "created_at": Ticket.created_at,
        "priority": Ticket.priority,
        "ticket_number": Ticket.ticket_number,
    }[data.sort_by]
    ordering = sort_column.asc() if data.sort_direction == "asc" else sort_column.desc()
    tickets = list(db.scalars(statement.order_by(ordering).offset(data.offset).limit(data.limit)))
    return attach_ticket_sla_evidence(db, tickets)


@router.post("/bulk-assignment")
def bulk_assign_tickets(
    data: TicketBulkAssignment,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.assign.team")),
) -> dict[str, int]:
    expected_versions = {item.ticket_id: item.expected_version for item in data.items}
    if len(expected_versions) != len(data.items):
        raise ConflictError(
            "DUPLICATE_BULK_TICKET", "A ticket may only be included once in a bulk action."
        )
    ticket_ids = set(expected_versions)
    tickets = list(db.scalars(select(Ticket).where(Ticket.id.in_(ticket_ids))))
    if len(tickets) != len(ticket_ids):
        raise NotFoundError("One or more tickets do not exist.")
    for ticket in tickets:
        if ticket.version != expected_versions[ticket.id]:
            raise ConflictError(
                "CONCURRENT_UPDATE",
                f"{ticket.ticket_number} was updated by another user. Refresh and try again.",
            )
        ensure_ticket_access(db, actor, ticket)
        if ticket.entitlement_status == "PENDING_APPROVAL":
            raise ConflictError(
                "TICKET_AWAITING_ENTITLEMENT_APPROVAL",
                f"{ticket.ticket_number} is awaiting contract approval and cannot be assigned.",
            )
    assigned_user = db.get(User, data.assigned_user_id) if data.assigned_user_id else None
    if data.assigned_user_id:
        assigned_user = ensure_assignment_eligibility(db, assigned_user)
    if data.assigned_team and not db.scalar(
        select(SupportTeam.id).where(
            SupportTeam.name == data.assigned_team, SupportTeam.is_active.in_([True])
        )
    ):
        raise NotFoundError("Assigned support team does not exist or is inactive.")
    assigned_status = db.scalar(select(TicketStatus).where(TicketStatus.code == "ASSIGNED"))
    for ticket in tickets:
        previous_status = db.get(TicketStatus, ticket.status_id)
        previous_assigned_user_id = ticket.assigned_user_id
        ticket.assigned_user_id = data.assigned_user_id
        ticket.assigned_team = data.assigned_team
        if (
            assigned_status
            and previous_status
            and previous_status.code in {"NEW", "TRIAGED"}
            and (data.assigned_user_id or data.assigned_team)
        ):
            ticket.status_id = assigned_status.id
            db.add(
                TicketStatusHistory(
                    ticket_id=ticket.id,
                    from_status_id=previous_status.id,
                    to_status_id=assigned_status.id,
                    changed_by_user_id=actor.id,
                    reason=f"Bulk assignment: {data.reason}" if data.reason else "Bulk assignment",
                )
            )
        ticket.version += 1
        assigned_at = server_now()
        ticket.last_activity_at = assigned_at
        if (
            assigned_status
            and previous_status
            and previous_status.code in {"NEW", "TRIAGED"}
            and (data.assigned_user_id or data.assigned_team)
        ):
            queue_ticket_workflow_transition(
                db,
                ticket,
                actor,
                from_status_code=previous_status.code,
                to_status_code="ASSIGNED",
                source="BULK_ASSIGNMENT",
            )
        apply_first_dedicated_assignment(db, ticket, data.assigned_user_id, assigned_at)
        db.add(
            TicketAssignmentHistory(
                ticket_id=ticket.id,
                assigned_user_id=data.assigned_user_id,
                assigned_team=data.assigned_team,
                assigned_by_user_id=actor.id,
                reason=data.reason,
                created_at=assigned_at,
            )
        )
        db.add(
            AuditLog(
                actor_user_id=actor.id,
                entity_type="Ticket",
                entity_id=str(ticket.id),
                action="ticket.bulk_assigned",
                reason=data.reason,
                correlation_id=request.state.correlation_id,
                new_values_json=json.dumps(
                    {"assigned_user_id": data.assigned_user_id, "assigned_team": data.assigned_team}
                ),
            )
        )
        if assigned_user:
            db.add(
                Notification(
                    recipient_user_id=assigned_user.id,
                    notification_type="TICKET_ASSIGNED",
                    severity="INFO",
                    title=f"Ticket assigned: {ticket.ticket_number}",
                    message=f"{actor.full_name} assigned you: {ticket.subject}",
                    deep_link=f"/tickets/{ticket.id}",
                    deduplication_key=f"ticket-bulk-assigned:{ticket.id}:version:{ticket.version}:user:{assigned_user.id}",
                )
            )
        queue_ticket_reassignment_email(db, ticket, previous_assigned_user_id, actor)
        from app.modules.uat.service import sync_ticket_to_uat

        sync_ticket_to_uat(
            db,
            ticket,
            actor,
            target_status_code=(
                "ASSIGNED"
                if data.assigned_user_id or data.assigned_team
                else (previous_status.code if previous_status else None)
            ),
        )
    db.commit()
    return {"updated": len(tickets)}


@router.post("/bulk-status")
def bulk_change_ticket_status(
    data: TicketBulkStatus,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.bulk.status")),
) -> dict[str, int]:
    expected_versions = {item.ticket_id: item.expected_version for item in data.items}
    if len(expected_versions) != len(data.items):
        raise ConflictError(
            "DUPLICATE_BULK_TICKET", "A ticket may only be included once in a bulk action."
        )
    ticket_ids = set(expected_versions)
    tickets = list(db.scalars(select(Ticket).where(Ticket.id.in_(ticket_ids))))
    if len(tickets) != len(ticket_ids):
        raise NotFoundError("One or more tickets do not exist.")
    target = db.scalar(select(TicketStatus).where(TicketStatus.code == data.to_status_code))
    if not target:
        raise NotFoundError("Ticket status does not exist.")
    permissions = set(effective_permissions(db, actor).permissions)
    for ticket in tickets:
        if ticket.version != expected_versions[ticket.id]:
            raise ConflictError(
                "CONCURRENT_UPDATE",
                f"{ticket.ticket_number} was updated by another user. Refresh and try again.",
            )
        ensure_ticket_access(db, actor, ticket)
        authorize_transition_actor(
            target_code=data.to_status_code,
            assigned_user_id=ticket.assigned_user_id,
            actor_user_id=actor.id,
            permissions=permissions,
        )
        transition_ticket(
            db,
            ticket,
            TicketTransition(
                to_status_code=data.to_status_code,
                reason=f"Bulk status: {data.reason}" if data.reason else None,
                resolution_summary=data.resolution_summary,
                root_cause_summary=data.root_cause_summary,
                pending_owner_user_id=data.pending_owner_user_id,
                pending_follow_up_at=data.pending_follow_up_at,
                pending_responsible_party=data.pending_responsible_party,
                version=expected_versions[ticket.id],
            ),
            actor,
            commit=False,
        )
        if data.to_status_code == "CLOSED":
            synchronize_escalation_parent(db, ticket, actor)
            for child in synchronize_escalation_children(db, ticket, actor):
                enqueue_satisfaction_invitation(db, child, get_settings())
        db.add(
            AuditLog(
                actor_user_id=actor.id,
                entity_type="Ticket",
                entity_id=str(ticket.id),
                action="ticket.bulk_status_changed",
                reason=data.reason,
                correlation_id=request.state.correlation_id,
                new_values_json=json.dumps({"status_code": target.code}),
            )
        )
    db.commit()
    return {"updated": len(tickets)}


@router.get("/trash", response_model=list[TicketRead])
def trash_tickets(
    response: Response,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.trash.view")),
) -> list[Ticket]:
    statement = visible_ticket_query(db, actor, include_archived=True).where(
        Ticket.archived_at.is_not(None)
    )
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    response.headers["X-Total-Count"] = str(total)
    tickets = list(
        db.scalars(statement.order_by(Ticket.archived_at.desc()).offset(offset).limit(limit))
    )
    return attach_ticket_queue_evidence(db, attach_ticket_sla_evidence(db, tickets))


@router.get("/deletion-requests", response_model=list[TicketDeletionRequestRead])
def deletion_requests(
    request_status: str = Query(
        default="PENDING", alias="status", pattern="^(PENDING|APPROVED|REJECTED|CANCELLED)$"
    ),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("ticket.delete.approve")),
) -> list[TicketDeletionRequest]:
    items = list(
        db.scalars(
            select(TicketDeletionRequest)
            .where(TicketDeletionRequest.status == request_status)
            .order_by(TicketDeletionRequest.created_at.desc())
        )
    )
    for item in items:
        ticket = db.get(Ticket, item.ticket_id)
        requester = db.get(User, item.requested_by_user_id)
        item.__dict__["ticket_number"] = ticket.ticket_number if ticket else None
        item.__dict__["ticket_subject"] = ticket.subject if ticket else None
        item.__dict__["requested_by_name"] = requester.full_name if requester else None
    return items


@router.post(
    "/deletion-requests/{deletion_request_id}/decision", response_model=TicketDeletionRequestRead
)
def decide_deletion_request(
    deletion_request_id: int,
    data: TicketDeletionDecision,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.delete.approve")),
) -> TicketDeletionRequest:
    item = db.get(TicketDeletionRequest, deletion_request_id)
    if not item:
        raise NotFoundError("Deletion request does not exist.")
    if item.status != "PENDING":
        raise ConflictError(
            "DELETION_ALREADY_DECIDED", "This deletion request has already been decided."
        )
    if item.requested_by_user_id == actor.id:
        raise AuthorizationError(
            "The requester cannot approve or reject their own deletion request."
        )
    ticket = db.get(Ticket, item.ticket_id)
    if not ticket:
        raise NotFoundError("Ticket does not exist.")
    ensure_ticket_access(db, actor, ticket)
    now = server_now()
    item.status = data.decision
    item.decided_by_user_id = actor.id
    item.decision_comment = data.comment
    item.decided_at = now
    item.version += 1
    if data.decision == "APPROVED":
        if ticket.archived_at is not None:
            raise ConflictError("TICKET_ALREADY_ARCHIVED", "The ticket is already in Trash.")
        ticket.archived_at = now
        ticket.archived_by_user_id = actor.id
        ticket.archive_reason = item.reason
        ticket.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket.id),
            action=f"ticket.deletion_{data.decision.lower()}",
            reason=data.comment,
            correlation_id=request.state.correlation_id,
            new_values_json=json.dumps(
                {"deletion_request_id": item.id, "archive_reason": item.reason}
            ),
        )
    )
    db.add(
        Notification(
            recipient_user_id=item.requested_by_user_id,
            notification_type="TICKET_DELETION_DECIDED",
            severity="WARNING" if data.decision == "REJECTED" else "INFO",
            title=f"Ticket deletion {data.decision.lower()}",
            message=f"Deletion of {ticket.ticket_number} was {data.decision.lower()}. {data.comment}",
            deep_link=(
                "/tickets?tab=trash" if data.decision == "APPROVED" else f"/tickets/{ticket.id}"
            ),
            deduplication_key=f"ticket-deletion-decision:{item.id}:{data.decision}",
        )
    )
    db.commit()
    db.refresh(item)
    requester = db.get(User, item.requested_by_user_id)
    item.__dict__["ticket_number"] = ticket.ticket_number
    item.__dict__["ticket_subject"] = ticket.subject
    item.__dict__["requested_by_name"] = requester.full_name if requester else None
    return item


@router.post("/bulk-delete", response_model=list[TicketDeletionRequestRead])
def bulk_delete_tickets(
    data: TicketBulkDelete,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.delete.request")),
) -> list[TicketDeletionRequest]:
    ticket_ids = set(data.ticket_ids)
    tickets = list(db.scalars(select(Ticket).where(Ticket.id.in_(ticket_ids))))
    if len(tickets) != len(ticket_ids):
        raise NotFoundError("One or more tickets do not exist.")
    created: list[TicketDeletionRequest] = []
    for ticket in tickets:
        ensure_ticket_access(db, actor, ticket)
        if ticket.archived_at is not None:
            raise ConflictError(
                "TICKET_ALREADY_ARCHIVED", "An archived ticket cannot be submitted for deletion."
            )
        pending = db.scalar(
            select(TicketDeletionRequest).where(
                TicketDeletionRequest.ticket_id == ticket.id,
                TicketDeletionRequest.status == "PENDING",
            )
        )
        if pending:
            if pending.requested_by_user_id == actor.id and pending.reason == data.reason:
                created.append(pending)
                continue
            raise ConflictError(
                "DELETION_ALREADY_PENDING",
                f"Ticket {ticket.ticket_number} already has a pending deletion request.",
            )
        deletion_request = TicketDeletionRequest(
            ticket_id=ticket.id, requested_by_user_id=actor.id, reason=data.reason
        )
        db.add(deletion_request)
        created.append(deletion_request)
        db.add(
            AuditLog(
                actor_user_id=actor.id,
                entity_type="Ticket",
                entity_id=str(ticket.id),
                action="ticket.deletion_requested",
                reason=data.reason,
                correlation_id=request.state.correlation_id,
                old_values_json=json.dumps(
                    {"ticket_number": ticket.ticket_number, "subject": ticket.subject}
                ),
            )
        )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        existing = list(
            db.scalars(
                select(TicketDeletionRequest).where(
                    TicketDeletionRequest.ticket_id.in_(ticket_ids),
                    TicketDeletionRequest.status == "PENDING",
                    TicketDeletionRequest.requested_by_user_id == actor.id,
                    TicketDeletionRequest.reason == data.reason,
                )
            )
        )
        if {item.ticket_id for item in existing} != ticket_ids:
            raise ConflictError(
                "DELETION_ALREADY_PENDING",
                "One or more tickets already have another pending deletion request.",
            ) from error
        created = existing
    for item in created:
        db.refresh(item)
        requested_ticket = db.get(Ticket, item.ticket_id)
        item.__dict__["ticket_number"] = (
            requested_ticket.ticket_number if requested_ticket else None
        )
        item.__dict__["ticket_subject"] = requested_ticket.subject if requested_ticket else None
        item.__dict__["requested_by_name"] = actor.full_name
    return created


@router.post("/{ticket_id}/restore", response_model=TicketRead)
def restore_ticket(
    ticket_id: int,
    data: TicketArchiveRestore,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.trash.restore")),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    if ticket.version != data.version:
        raise ConflictError("CONCURRENT_UPDATE", "The ticket was updated by another user.")
    if ticket.archived_at is None:
        raise ConflictError("TICKET_NOT_ARCHIVED", "Only archived tickets can be restored.")
    archived_at = ticket.archived_at
    archived_by = ticket.archived_by_user_id
    ticket.archived_at = None
    ticket.archived_by_user_id = None
    ticket.archive_reason = None
    ticket.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket.id),
            action="ticket.restored",
            reason=data.reason,
            old_values_json=json.dumps(
                {"archived_at": archived_at.isoformat(), "archived_by_user_id": archived_by}
            ),
        )
    )
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/templates", response_model=list[TicketTemplateRead])
def ticket_templates(
    query: str | None = Query(default=None, max_length=300),
    client_id: int | None = None,
    product_id: int | None = None,
    product_module_id: int | None = None,
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[TicketTemplate]:
    statement = select(TicketTemplate).where(TicketTemplate.is_active.in_([True]))
    if user.user_type == "CLIENT_PORTAL":
        client_scope_ids = effective_permissions(db, user).client_scope_ids
        statement = statement.where(
            TicketTemplate.portal_visible.in_([True]),
            or_(TicketTemplate.client_id.is_(None), TicketTemplate.client_id.in_(client_scope_ids)),
        )
    elif client_id:
        statement = statement.where(
            or_(TicketTemplate.client_id.is_(None), TicketTemplate.client_id == client_id)
        )
    if product_id:
        statement = statement.where(
            or_(TicketTemplate.product_id.is_(None), TicketTemplate.product_id == product_id)
        )
    if product_module_id:
        statement = statement.where(
            or_(
                TicketTemplate.product_module_id.is_(None),
                TicketTemplate.product_module_id == product_module_id,
            )
        )
    rows = list(db.scalars(statement.order_by(TicketTemplate.updated_at.desc()).limit(200)))
    normalized = " ".join((query or "").casefold().split())
    if not normalized:
        return rows[:limit]
    tokens = {token for token in re.findall(r"[a-z0-9]+", normalized) if len(token) >= 2}

    def template_score(item: TicketTemplate) -> float:
        text_value = f"{item.name} {item.keywords} {item.subject} {item.description}".casefold()
        template_tokens = set(re.findall(r"[a-z0-9]+", text_value))
        matches = sum(
            any(
                query_token == template_token
                or (
                    len(query_token) >= 3
                    and len(template_token) >= 3
                    and (
                        template_token.startswith(query_token)
                        or query_token.startswith(template_token)
                    )
                )
                for template_token in template_tokens
            )
            for query_token in tokens
        )
        # Fuzzy similarity ranks genuine keyword/title candidates; it must never
        # make an unrelated template eligible by itself.
        if matches == 0:
            return 0
        return (
            matches / max(len(tokens), 1)
            + SequenceMatcher(None, normalized, item.subject.casefold()).ratio()
        )

    return [
        item for item in sorted(rows, key=template_score, reverse=True) if template_score(item) > 0
    ][:limit]


@router.get("/templates/manage", response_model=list[TicketTemplateRead])
def managed_ticket_templates(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.template.manage")),
) -> list[TicketTemplate]:
    return list(db.scalars(select(TicketTemplate).order_by(TicketTemplate.updated_at.desc())))


@router.patch("/templates/{template_id}", response_model=TicketTemplateRead)
def update_ticket_template(
    template_id: int,
    data: TicketTemplateUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.template.manage")),
) -> TicketTemplate:
    template = db.get(TicketTemplate, template_id)
    if not template:
        raise NotFoundError()
    if template.version != data.expected_version:
        raise ConflictError(
            "TEMPLATE_VERSION_CONFLICT", "The ticket template was changed by another user."
        )
    old_values = {
        "name": template.name,
        "subject": template.subject,
        "is_active": template.is_active,
        "version": template.version,
    }
    for field, value in data.model_dump(exclude={"expected_version"}).items():
        setattr(template, field, value.strip() if isinstance(value, str) else value)
    template.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketTemplate",
            entity_id=str(template.id),
            action="ticket.template.updated",
            old_values_json=json.dumps(old_values),
            new_values_json=json.dumps(
                {
                    "name": template.name,
                    "subject": template.subject,
                    "is_active": template.is_active,
                    "version": template.version,
                }
            ),
        )
    )
    db.commit()
    db.refresh(template)
    return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket_template(
    template_id: int,
    expected_version: int = Query(ge=1),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.template.manage")),
) -> Response:
    template = db.get(TicketTemplate, template_id)
    if not template:
        raise NotFoundError()
    if template.version != expected_version:
        raise ConflictError(
            "TEMPLATE_VERSION_CONFLICT", "The ticket template was changed by another user."
        )
    template.is_active = False
    template.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketTemplate",
            entity_id=str(template.id),
            action="ticket.template.deleted",
            old_values_json=json.dumps({"is_active": True}),
            new_values_json=json.dumps({"is_active": False}),
        )
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{ticket_id}/template", response_model=TicketTemplateRead, status_code=status.HTTP_201_CREATED
)
def create_ticket_template(
    ticket_id: int,
    data: TicketTemplateCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.template.create")),
) -> TicketTemplate:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    template = TicketTemplate(
        name=data.name.strip(),
        keywords=data.keywords.strip(),
        source_ticket_id=ticket.id,
        ticket_type_id=ticket.ticket_type_id,
        client_id=ticket.client_id if data.scope == "CLIENT" else None,
        product_id=ticket.product_id if data.scope in {"PRODUCT", "MODULE"} else None,
        product_module_id=ticket.product_module_id if data.scope == "MODULE" else None,
        environment_id=ticket.environment_id,
        service_id=ticket.service_id,
        category_id=ticket.category_id,
        subcategory_id=ticket.subcategory_id,
        subject=ticket.subject,
        description=ticket.description,
        priority=ticket.priority,
        impact=ticket.impact,
        urgency=ticket.urgency,
        assigned_team=ticket.assigned_team,
        portal_visible=data.portal_visible,
        created_by_user_id=actor.id,
    )
    db.add(template)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketTemplate",
            entity_id=str(template.id),
            action="ticket.template.created",
            new_values_json=json.dumps(
                {
                    "source_ticket_id": ticket.id,
                    "scope": data.scope,
                    "portal_visible": data.portal_visible,
                }
            ),
        )
    )
    db.commit()
    db.refresh(template)
    return template


@router.get("/similar", response_model=list[TicketRead])
def similar_tickets(
    subject: str = Query(min_length=3, max_length=300),
    client_id: int | None = None,
    limit: int = Query(default=5, ge=1, le=10),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[Ticket]:
    normalized = " ".join(subject.casefold().split())
    tokens = {token for token in re.findall(r"[a-z0-9]+", normalized) if len(token) >= 3}
    statement = visible_ticket_query(db, user)
    if client_id:
        statement = statement.where(Ticket.client_id == client_id)
    if tokens:
        statement = statement.where(or_(*(Ticket.subject.ilike(f"%{token}%") for token in tokens)))
    else:
        statement = statement.where(Ticket.subject.ilike(f"%{normalized}%"))
    candidates = list(db.scalars(statement.order_by(Ticket.updated_at.desc()).limit(100)))

    def score(ticket: Ticket) -> float:
        candidate = " ".join(ticket.subject.casefold().split())
        candidate_tokens = set(re.findall(r"[a-z0-9]+", candidate))
        union = tokens | candidate_tokens
        overlap = len(tokens & candidate_tokens) / len(union) if union else 0
        direct_match = 1.0 if normalized in candidate else 0.0
        return max(
            direct_match,
            0.65 * overlap + 0.35 * SequenceMatcher(None, normalized, candidate).ratio(),
        )

    return [item for item in sorted(candidates, key=score, reverse=True) if score(item) >= 0.2][
        :limit
    ]


@router.get("/{ticket_id}/department-requests", response_model=list[TicketRead])
def department_requests(
    ticket_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> list[Ticket]:
    parent = db.get(Ticket, ticket_id)
    if not parent:
        raise NotFoundError()
    ensure_ticket_access(db, actor, parent)
    children = list(
        db.scalars(
            select(Ticket)
            .where(
                Ticket.escalation_parent_ticket_id == parent.id,
                Ticket.routed_department_id.is_not(None),
            )
            .order_by(Ticket.created_at.desc())
        )
    )
    return attach_ticket_sla_evidence(db, children)


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    return attach_ticket_queue_evidence(db, attach_ticket_sla_evidence(db, [ticket]))[0]


@router.post("/{ticket_id}/sla-preview", response_model=TicketSlaPreviewRead)
def ticket_sla_preview(
    ticket_id: int,
    data: TicketSlaPreviewRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> dict[str, object]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    changes = data.model_dump(exclude_unset=True, exclude={"version"})
    permissions = set(effective_permissions(db, actor).permissions)
    field_permissions = {
        "client_id": "ticket.change.client",
        "branch_id": "ticket.change.client",
        "requester_contact_id": "ticket.change.client",
        "contract_id": "ticket.change.contract",
        "priority": "ticket.change.priority",
        "ticket_type_id": "ticket.edit.classification",
        "product_id": "ticket.edit.classification",
        "product_module_id": "ticket.edit.classification",
        "environment_id": "ticket.edit.classification",
        "service_id": "ticket.edit.classification",
    }
    denied = [field for field in changes if field_permissions[field] not in permissions]
    if denied:
        raise AuthorizationError(f"You do not have permission to preview: {', '.join(denied)}.")
    return {
        "version": ticket.version,
        **preview_ticket_sla(db, ticket, changes, server_now()),
    }


@router.patch("/{ticket_id}", response_model=TicketRead)
def edit_ticket(
    ticket_id: int,
    data: TicketEdit,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    if ticket.entitlement_status == "PENDING_APPROVAL":
        raise ConflictError(
            "TICKET_AWAITING_ENTITLEMENT_APPROVAL",
            "This ticket is awaiting contract approval and cannot be edited.",
        )
    if ticket.version != data.version:
        raise ConflictError("CONCURRENT_UPDATE", "The ticket was updated by another user.")
    permissions = set(effective_permissions(db, actor).permissions)
    scope_allowed = "ticket.edit.all" in permissions
    scope_allowed = scope_allowed or (
        "ticket.edit.own" in permissions and ticket.created_by_user_id == actor.id
    )
    scope_allowed = scope_allowed or (
        "ticket.edit.assigned" in permissions and ticket.assigned_user_id == actor.id
    )
    if not scope_allowed and "ticket.edit.team" in permissions and ticket.assigned_team:
        scope_allowed = bool(
            db.scalar(
                select(SupportTeamMember.user_id)
                .join(SupportTeam, SupportTeam.id == SupportTeamMember.team_id)
                .where(
                    SupportTeamMember.user_id == actor.id, SupportTeam.name == ticket.assigned_team
                )
            )
        )
    if not scope_allowed:
        raise AuthorizationError("You do not have permission to edit this ticket.")
    changes = data.model_dump(
        exclude_unset=True, exclude={"reason", "version", "sla_reevaluation_reason"}
    )
    field_permissions = {
        "client_id": "ticket.change.client",
        "contract_id": "ticket.change.contract",
        "due_at": "ticket.edit.due_date",
        "subject": "ticket.edit.subject",
        "description": "ticket.edit.description",
        "priority": "ticket.change.priority",
        "impact": "ticket.edit.classification",
        "urgency": "ticket.edit.classification",
        "ticket_type_id": "ticket.edit.classification",
        "product_id": "ticket.edit.classification",
        "product_module_id": "ticket.edit.classification",
        "environment_id": "ticket.edit.classification",
        "service_id": "ticket.edit.classification",
        "category_id": "ticket.edit.classification",
        "subcategory_id": "ticket.edit.classification",
        "affected_users": "ticket.edit.classification",
        "patient_safety_flag": "ticket.edit.classification",
        "security_incident_flag": "ticket.edit.classification",
    }
    denied = [field for field in changes if field_permissions[field] not in permissions]
    if denied:
        raise AuthorizationError(f"You do not have permission to edit: {', '.join(denied)}.")
    if {"impact", "urgency"}.intersection(changes) and "priority" not in changes:
        changes["priority"] = derive_priority(
            str(changes.get("impact", ticket.impact)),
            str(changes.get("urgency", ticket.urgency)),
        )
    if changes.get("client_id") in {None, ticket.client_id}:
        changes.pop("client_id", None)
    if changes.get("contract_id") in {None, ticket.contract_id}:
        changes.pop("contract_id", None)
    selected_client_id = changes.get("client_id", ticket.client_id)
    if "client_id" in changes:
        selected_client = db.get(Client, selected_client_id)
        if not selected_client:
            raise NotFoundError("Client does not exist.")
    selected_branch_id = changes.get("branch_id", ticket.branch_id)
    selected_requester_id = changes.get("requester_contact_id", ticket.requester_contact_id)
    context_fields = {
        "client_id",
        "contract_id",
        "product_id",
        "product_module_id",
        "environment_id",
        "service_id",
        "ticket_type_id",
    }
    # Only fields consumed by the current entitlement/target resolvers are guarded.
    # Category, impact, and urgency remain editable until priority derivation is
    # centralized under TWF-005.
    sla_material_fields = context_fields | {"priority"}
    actual_sla_changes = {
        field
        for field in sla_material_fields.intersection(changes)
        if changes[field] != getattr(ticket, field)
    }
    has_sla_clocks = (
        actual_sla_changes
        and db.scalar(
            select(TicketSlaClock.id).where(TicketSlaClock.ticket_id == ticket.id).limit(1)
        )
        is not None
    )
    if has_sla_clocks:
        if not data.sla_reevaluation_reason:
            raise ConflictError(
                "SLA_REEVALUATION_REASON_REQUIRED",
                "Explain why this SLA-relevant ticket context is changing.",
            )
    if context_fields.intersection(changes):
        entitlement_status, entitled_contract, entitlement_reason = evaluate_entitlement(
            db,
            client_id=selected_client_id,
            branch_id=selected_branch_id,
            product_id=changes.get("product_id", ticket.product_id),
            product_module_id=changes.get("product_module_id", ticket.product_module_id),
            environment_id=changes.get("environment_id", ticket.environment_id),
            service_id=changes.get("service_id", ticket.service_id),
            ticket_type_id=changes.get("ticket_type_id", ticket.ticket_type_id),
            preferred_contract_id=changes.get("contract_id", ticket.contract_id),
        )
        requested_contract_id = changes.get("contract_id")
        if requested_contract_id is not None:
            requested_contract = db.get(Contract, requested_contract_id)
            linked = requested_contract and (
                requested_contract.client_id == selected_client_id
                or bool(
                    db.scalar(
                        select(ContractClientLink.id).where(
                            ContractClientLink.contract_id == requested_contract_id,
                            ContractClientLink.client_id == selected_client_id,
                        )
                    )
                )
            )
            if not requested_contract or not linked:
                raise ConflictError(
                    "INVALID_TICKET_CONTRACT",
                    "The selected contract is not linked to the ticket customer.",
                )
            if not entitled_contract or requested_contract.id != entitled_contract.id:
                raise ConflictError("INVALID_TICKET_CONTRACT", entitlement_reason)
        if entitlement_status not in {"COVERED", "NO_CONTRACT"}:
            raise ConflictError("TICKET_NOT_ENTITLED", entitlement_reason)
        changes["contract_id"] = entitled_contract.id if entitled_contract else None
        changes["entitlement_status"] = entitlement_status
        changes["entitlement_override_reason"] = None
    context_validation_fields = context_fields | {"category_id", "subcategory_id"}
    actual_context_validation_changes = {
        field
        for field in context_validation_fields.intersection(changes)
        if changes[field] != getattr(ticket, field)
    }
    if actual_context_validation_changes:
        validate_ticket_context(
            db,
            client_id=selected_client_id,
            ticket_type_id=changes.get("ticket_type_id", ticket.ticket_type_id),
            product_id=changes.get("product_id", ticket.product_id),
            product_module_id=changes.get("product_module_id", ticket.product_module_id),
            environment_id=changes.get("environment_id", ticket.environment_id),
            service_id=changes.get("service_id", ticket.service_id),
            category_id=changes.get("category_id", ticket.category_id),
            subcategory_id=changes.get("subcategory_id", ticket.subcategory_id),
            branch_id=selected_branch_id,
            requester_contact_id=selected_requester_id,
        )
    old_values = {field: getattr(ticket, field) for field in changes}
    for field, value in changes.items():
        setattr(ticket, field, value)
    edit_time = server_now()
    if has_sla_clocks:
        reevaluate_ticket_sla(
            db,
            ticket,
            actor,
            data.sla_reevaluation_reason or "",
            actual_sla_changes,
            edit_time,
        )
    ticket.version += 1
    ticket.last_activity_at = edit_time
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket.id),
            action="ticket.edited",
            reason=data.reason,
            old_values_json=json.dumps(old_values, default=str),
            new_values_json=json.dumps(changes, default=str),
        )
    )
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/{ticket_id}/send-actions")
def ticket_send_actions(
    ticket_id: int,
    contact_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> dict[str, object]:
    """Return permission-filtered, server-authoritative communication eligibility."""
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    permissions = set(effective_permissions(db, actor).permissions)
    status_row = db.get(TicketStatus, ticket.status_id)
    selected_contact_id = contact_id or ticket.requester_contact_id
    contact = db.get(Contact, selected_contact_id) if selected_contact_id else None
    if contact and not contact_belongs_to_client(db, contact, ticket.client_id):
        raise ConflictError(
            "CONTACT_CLIENT_MISMATCH", "The selected contact does not belong to this client."
        )
    client = db.get(Client, ticket.client_id)

    def setting(key: str, default: str = "true") -> bool:
        row = db.get(SiteSetting, key)
        return (row.value if row else default).lower() == "true"

    actions: list[dict[str, object]] = []
    if "ticket.live_update.send" in permissions:
        enabled = setting("live_ticket_update_enabled")
        actions.append(
            {
                "code": "LIVE_TRACKING",
                "label": "Send live-tracking link",
                "eligible": enabled,
                "reason": None if enabled else "Live tracking is disabled in Site Settings.",
                "channels": {
                    "COPY": True,
                    "WHATSAPP": bool(contact and contact.phone_number),
                    "EMAIL": bool(contact and contact.email),
                },
                "whatsapp_recipient": contact.phone_number if contact else None,
            }
        )
    if "ticket.satisfaction.send" in permissions:
        enabled = setting("satisfaction_manual_enabled")
        closed = bool(status_row and status_row.code == "CLOSED")
        email = (contact.email if contact and contact.email else None) or (
            client.email if client else None
        )
        eligible = enabled and closed
        reason = (
            None
            if eligible
            else "Manual rating delivery is disabled."
            if not enabled
            else "Rating links are available only for closed tickets."
        )
        actions.append(
            {
                "code": "SATISFACTION",
                "label": "Send rating link",
                "eligible": eligible,
                "reason": reason,
                "channels": {
                    "COPY": True,
                    "EMAIL": setting("satisfaction_email_enabled") and bool(email),
                    "WHATSAPP": setting("satisfaction_whatsapp_enabled")
                    and bool(contact and contact.phone_number),
                },
            }
        )
    if "complaint.tracking.send" in permissions:
        statement = (
            select(Complaint)
            .where(Complaint.linked_ticket_id == ticket.id)
            .order_by(Complaint.created_at.desc())
        )
        if not any(code in permissions for code in {"complaint.manage", "complaint.view.all"}):
            teams = select(SupportTeamMember.team_id).where(SupportTeamMember.user_id == actor.id)
            statement = statement.where(
                or_(Complaint.assigned_user_id == actor.id, Complaint.assigned_team_id.in_(teams))
            )
        complaints = list(db.scalars(statement))
        tracking_enabled = setting("complaint_tracking_enabled")
        complaint_options = []
        for complaint in complaints:
            caller = (
                db.get(Contact, complaint.requester_contact_id)
                if complaint.requester_contact_id
                else None
            )
            complaint_options.append(
                {
                    "id": complaint.id,
                    "number": complaint.complaint_number,
                    "status": complaint.status,
                    "channels": {
                        "EMAIL": setting("complaint_email_enabled")
                        and bool(caller and caller.email),
                        "WHATSAPP": setting("complaint_whatsapp_enabled")
                        and bool(caller and caller.phone_number),
                    },
                }
            )
        actions.append(
            {
                "code": "COMPLAINT_TRACKING",
                "label": "Send complaint-tracking link",
                "eligible": tracking_enabled and bool(complaint_options),
                "reason": None
                if tracking_enabled and complaint_options
                else "Complaint tracking is disabled."
                if not tracking_enabled
                else "No accessible linked complaint is available.",
                "complaints": complaint_options,
            }
        )
    return {"ticket_id": ticket.id, "ticket_number": ticket.ticket_number, "actions": actions}


@router.get("/{ticket_id}/whatsapp-contact")
def ticket_whatsapp_contact(
    ticket_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> dict[str, str]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    contact = db.get(Contact, ticket.requester_contact_id) if ticket.requester_contact_id else None
    phone_number = contact.phone_number if contact and contact.phone_number else ""
    digits = re.sub(r"\D", "", phone_number)
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("0"):
        digits = f"20{digits[1:]}"
    if not digits:
        raise ConflictError(
            "CALLER_PHONE_UNAVAILABLE", "This ticket caller does not have a mobile number."
        )
    return {"url": f"https://wa.me/{digits}", "phone_number": phone_number}


@router.get("/{ticket_id}/allowed-transitions", response_model=list[TicketCatalogRead])
def allowed_ticket_transitions(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[TicketStatus]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    current = db.get(TicketStatus, ticket.status_id)
    if not current:
        raise NotFoundError("Ticket status does not exist.")
    permissions = set(effective_permissions(db, user).permissions)
    codes = allowed_transition_codes(current.code, permissions)
    try:
        authorize_transition_actor(
            target_code="RESOLVED",
            assigned_user_id=ticket.assigned_user_id,
            actor_user_id=user.id,
            permissions=permissions,
        )
    except ConflictError:
        codes = codes - {"RESOLVED"}
    if not codes:
        return []
    return list(
        db.scalars(
            select(TicketStatus).where(TicketStatus.code.in_(codes)).order_by(TicketStatus.id)
        )
    )


@router.get("/{ticket_id}/timeline", response_model=list[TicketTimelineRead])
def get_ticket_timeline(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[dict[str, object]]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    permissions = set(effective_permissions(db, user).permissions)
    return ticket_timeline(
        db,
        ticket,
        include_internal=(
            user.user_type != "CLIENT_PORTAL" and "ticket.comment.internal" in permissions
        ),
    )


@router.post("/{ticket_id}/transition", response_model=TicketRead)
def transition(
    ticket_id: int,
    data: TicketTransition,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    permissions = set(effective_permissions(db, actor).permissions)
    authorize_transition_actor(
        target_code=data.to_status_code,
        assigned_user_id=ticket.assigned_user_id,
        actor_user_id=actor.id,
        permissions=permissions,
    )
    if data.to_status_code == "IN_PROGRESS" and ticket.assigned_user_id != actor.id:
        shared_assignment = _is_shared_support_assignee(db, ticket.assigned_user_id)
        if shared_assignment and "ticket.assign.self" not in permissions:
            raise AuthorizationError(
                "You do not have permission to assign this ticket to yourself."
            )
        if not shared_assignment and "ticket.start_progress_any" not in permissions:
            raise ConflictError(
                "TICKET_ASSIGNED_TO_ANOTHER_USER",
                "Only the assigned engineer can start progress on this ticket.",
            )
        ticket.assigned_user_id = actor.id
        ticket.assigned_team = actor.department
        assigned_at = server_now()
        apply_first_dedicated_assignment(db, ticket, actor.id, assigned_at)
        db.add(
            TicketAssignmentHistory(
                ticket_id=ticket.id,
                assigned_user_id=actor.id,
                assigned_team=actor.department,
                assigned_by_user_id=actor.id,
                reason="Automatically claimed when progress started",
                created_at=assigned_at,
            )
        )
    if data.to_status_code == "IN_PROGRESS" and ticket.progress_started_at is None:
        ticket.progress_started_at = server_now()
    closes_ticket = data.to_status_code == "CLOSED" or (
        data.to_status_code == "RESOLVED" and data.close_after_resolve
    )
    result = transition_ticket(db, ticket, data, actor, commit=not closes_ticket)
    if closes_ticket:
        synchronize_escalation_parent(db, result, actor)
        for child in synchronize_escalation_children(db, result, actor):
            enqueue_satisfaction_invitation(db, child, get_settings())
        enqueue_satisfaction_invitation(db, result, get_settings())
        db.commit()
        db.refresh(result)
    return result


@router.patch("/{ticket_id}/requester", response_model=TicketRead)
def update_ticket_requester(
    ticket_id: int,
    data: TicketRequesterUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.change.status")),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    if ticket.version != data.version:
        raise ConflictError("CONCURRENT_UPDATE", "The ticket was updated by another user.")
    if data.requester_contact_id is not None:
        contact = db.get(Contact, data.requester_contact_id)
        linked = contact and db.scalar(
            select(ContactClientLink.id).where(
                ContactClientLink.contact_id == contact.id,
                ContactClientLink.client_id == ticket.client_id,
            )
        )
        if (
            not contact
            or (contact.client_id != ticket.client_id and not linked)
            or not contact.is_active
        ):
            raise ConflictError(
                "INVALID_REQUESTER", "The caller must be an active contact for this client."
            )
    previous_contact_id = ticket.requester_contact_id
    ticket.requester_contact_id = data.requester_contact_id
    ticket.version += 1
    ticket.last_activity_at = server_now()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket.id),
            action="ticket.requester.updated",
            reason=data.reason,
            old_values_json=json.dumps({"requester_contact_id": previous_contact_id}),
            new_values_json=json.dumps({"requester_contact_id": data.requester_contact_id}),
        )
    )
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/{ticket_id}/followers", response_model=list[TicketFollowerRead])
def list_ticket_followers(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[dict[str, object]]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    rows = db.execute(
        select(TicketFollower, User)
        .join(User, User.id == TicketFollower.user_id)
        .where(TicketFollower.ticket_id == ticket_id)
        .order_by(User.full_name)
    ).all()
    return [
        {
            "user_id": follower.user_id,
            "full_name": follower_user.full_name,
            "username": follower_user.username,
            "created_at": follower.created_at,
        }
        for follower, follower_user in rows
    ]


@router.put("/{ticket_id}/followers", response_model=list[TicketFollowerRead])
def update_ticket_followers(
    ticket_id: int,
    data: TicketFollowersUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.assign.team")),
) -> list[dict[str, object]]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    if ticket.version != data.version:
        raise ConflictError("CONCURRENT_UPDATE", "The ticket was updated by another user.")
    requested = set(data.user_ids)
    valid = set(
        db.scalars(
            select(User.id).where(
                User.id.in_(requested),
                User.is_active.in_([True]),
                User.user_type == "EMPLOYEE",
            )
        )
    )
    if requested != valid:
        raise ConflictError("INVALID_FOLLOWERS", "All followers must be active employees.")
    previous = set(
        db.scalars(select(TicketFollower.user_id).where(TicketFollower.ticket_id == ticket_id))
    )
    db.query(TicketFollower).filter(TicketFollower.ticket_id == ticket_id).delete()
    db.add_all(
        TicketFollower(ticket_id=ticket_id, user_id=user_id, added_by_user_id=actor.id)
        for user_id in requested
    )
    ticket.version += 1
    ticket.last_activity_at = server_now()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket.id),
            action="ticket.followers.updated",
            reason=data.reason,
            old_values_json=json.dumps({"user_ids": sorted(previous)}),
            new_values_json=json.dumps({"user_ids": sorted(requested)}),
        )
    )
    db.commit()
    return list_ticket_followers(ticket_id, db, actor)


@router.get("/{ticket_id}/tasks", response_model=list[TicketTaskRead])
def list_ticket_tasks(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[TicketTask]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    return list(
        db.scalars(
            select(TicketTask)
            .where(TicketTask.ticket_id == ticket_id)
            .order_by(TicketTask.created_at)
        )
    )


@router.post("/{ticket_id}/tasks", response_model=TicketTaskRead, status_code=201)
def create_ticket_task(
    ticket_id: int,
    data: TicketTaskCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.change.status")),
) -> TicketTask:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    if data.assigned_user_id:
        assignee = db.get(User, data.assigned_user_id)
        if not assignee or not assignee.is_active or assignee.user_type != "EMPLOYEE":
            raise ConflictError("INVALID_TASK_ASSIGNEE", "Task assignee must be active.")
    task = TicketTask(ticket_id=ticket_id, created_by_user_id=actor.id, **data.model_dump())
    db.add(task)
    db.flush()
    ticket.version += 1
    ticket.last_activity_at = server_now()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket_id),
            action="ticket.task.created",
            new_values_json=json.dumps(data.model_dump(), default=str),
        )
    )
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{ticket_id}/tasks/{task_id}", response_model=TicketTaskRead)
def update_ticket_task(
    ticket_id: int,
    task_id: int,
    data: TicketTaskUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.change.status")),
) -> TicketTask:
    ticket = db.get(Ticket, ticket_id)
    task = db.scalar(
        select(TicketTask).where(TicketTask.id == task_id, TicketTask.ticket_id == ticket_id)
    )
    if not ticket or not task:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("assigned_user_id"):
        assignee = db.get(User, changes["assigned_user_id"])
        if not assignee or not assignee.is_active or assignee.user_type != "EMPLOYEE":
            raise ConflictError("INVALID_TASK_ASSIGNEE", "Task assignee must be active.")
    old = {key: getattr(task, key) for key in changes}
    for field, value in changes.items():
        setattr(task, field, value)
    if changes.get("status") == "COMPLETED" and task.completed_at is None:
        task.completed_at = server_now()
    elif "status" in changes and changes["status"] != "COMPLETED":
        task.completed_at = None
    ticket.version += 1
    ticket.last_activity_at = server_now()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket_id),
            action="ticket.task.updated",
            old_values_json=json.dumps(old, default=str),
            new_values_json=json.dumps(changes, default=str),
        )
    )
    db.commit()
    db.refresh(task)
    return task


def _validate_worklog(
    db: Session,
    *,
    ticket_id: int,
    user_id: int,
    started_at: datetime,
    ended_at: datetime,
    task_id: int | None,
    exclude_id: int | None = None,
) -> int:
    if ended_at <= started_at:
        raise ConflictError("INVALID_WORKLOG_RANGE", "Worklog end must be after its start.")
    duration = int((ended_at - started_at).total_seconds() // 60)
    if duration < 1:
        raise ConflictError(
            "INVALID_WORKLOG_DURATION", "Worklog duration must be at least one minute."
        )
    if task_id is not None and not db.scalar(
        select(TicketTask.id).where(TicketTask.id == task_id, TicketTask.ticket_id == ticket_id)
    ):
        raise ConflictError(
            "INVALID_WORKLOG_TASK", "The selected task does not belong to this ticket."
        )
    overlap = select(TicketWorklog.id).where(
        TicketWorklog.user_id == user_id,
        TicketWorklog.status != "REJECTED",
        TicketWorklog.started_at < ended_at,
        TicketWorklog.ended_at > started_at,
    )
    if exclude_id is not None:
        overlap = overlap.where(TicketWorklog.id != exclude_id)
    if db.scalar(overlap.limit(1)):
        raise ConflictError(
            "WORKLOG_OVERLAP", "This worklog overlaps another active worklog for the same owner."
        )
    return duration


@router.get("/{ticket_id}/worklogs", response_model=list[TicketWorklogRead])
def list_ticket_worklogs(
    ticket_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)
) -> list[TicketWorklog]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    return list(
        db.scalars(
            select(TicketWorklog)
            .where(TicketWorklog.ticket_id == ticket_id)
            .order_by(TicketWorklog.started_at.desc())
        )
    )


@router.post("/{ticket_id}/worklogs", response_model=TicketWorklogRead, status_code=201)
def create_ticket_worklog(
    ticket_id: int,
    data: TicketWorklogCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> TicketWorklog:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    if actor.user_type != "EMPLOYEE":
        raise AuthorizationError("Only employees can record worklogs.")
    duration = _validate_worklog(
        db,
        ticket_id=ticket_id,
        user_id=actor.id,
        started_at=data.started_at,
        ended_at=data.ended_at,
        task_id=data.task_id,
    )
    item = TicketWorklog(
        ticket_id=ticket_id,
        user_id=actor.id,
        duration_minutes=duration,
        status="DRAFT",
        version=1,
        **data.model_dump(),
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketWorklog",
            entity_id=str(item.id),
            action="ticket.worklog.created",
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{ticket_id}/worklogs/{worklog_id}", response_model=TicketWorklogRead)
def update_ticket_worklog(
    ticket_id: int,
    worklog_id: int,
    data: TicketWorklogUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> TicketWorklog:
    item = db.scalar(
        select(TicketWorklog).where(
            TicketWorklog.id == worklog_id, TicketWorklog.ticket_id == ticket_id
        )
    )
    if not item:
        raise NotFoundError("Worklog does not exist.")
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    if item.user_id != actor.id or item.status != "DRAFT":
        raise AuthorizationError("Only the owner can edit a draft worklog.")
    if item.version != data.version:
        raise ConflictError("STALE_WORKLOG", "The worklog changed; refresh and retry.")
    changes = data.model_dump(exclude_unset=True, exclude={"version"})
    started = changes.get("started_at", item.started_at)
    ended = changes.get("ended_at", item.ended_at)
    changes["duration_minutes"] = _validate_worklog(
        db,
        ticket_id=ticket_id,
        user_id=item.user_id,
        started_at=started,
        ended_at=ended,
        task_id=changes.get("task_id", item.task_id),
        exclude_id=item.id,
    )
    for field, value in changes.items():
        setattr(item, field, value)
    item.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketWorklog",
            entity_id=str(item.id),
            action="ticket.worklog.updated",
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.post("/{ticket_id}/worklogs/{worklog_id}/submit", response_model=TicketWorklogRead)
def submit_ticket_worklog(
    ticket_id: int,
    worklog_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> TicketWorklog:
    item = db.scalar(
        select(TicketWorklog).where(
            TicketWorklog.id == worklog_id, TicketWorklog.ticket_id == ticket_id
        )
    )
    if not item:
        raise NotFoundError("Worklog does not exist.")
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    if item.user_id != actor.id or item.status != "DRAFT":
        raise AuthorizationError("Only the owner can submit a draft worklog.")
    item.status = "SUBMITTED"
    item.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketWorklog",
            entity_id=str(item.id),
            action="ticket.worklog.submitted",
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.post("/{ticket_id}/worklogs/{worklog_id}/decision", response_model=TicketWorklogRead)
def decide_ticket_worklog(
    ticket_id: int,
    worklog_id: int,
    data: TicketWorklogDecision,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> TicketWorklog:
    item = db.scalar(
        select(TicketWorklog).where(
            TicketWorklog.id == worklog_id, TicketWorklog.ticket_id == ticket_id
        )
    )
    if not item:
        raise NotFoundError("Worklog does not exist.")
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    permissions = set(effective_permissions(db, actor).permissions)
    if "ticket.resolve.any" not in permissions and "configuration.manage" not in permissions:
        raise AuthorizationError("Worklog approval requires manager authority.")
    if item.status != "SUBMITTED" or item.version != data.version:
        raise ConflictError(
            "INVALID_WORKLOG_DECISION", "Only the current submitted worklog can be decided."
        )
    if not data.approved and not data.reason:
        raise ConflictError("WORKLOG_REJECTION_REASON_REQUIRED", "A rejection reason is required.")
    item.status = "APPROVED" if data.approved else "REJECTED"
    item.approved_by_user_id = actor.id
    item.approved_at = server_now()
    item.rejection_reason = None if data.approved else data.reason
    item.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketWorklog",
            entity_id=str(item.id),
            action=f"ticket.worklog.{item.status.lower()}",
            reason=data.reason,
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/{ticket_id}/checklist", response_model=list[ChecklistItemRead])
def list_ticket_checklist(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[TicketChecklistItem]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    return list(
        db.scalars(
            select(TicketChecklistItem)
            .where(TicketChecklistItem.ticket_id == ticket_id)
            .order_by(TicketChecklistItem.sort_order, TicketChecklistItem.id)
        )
    )


@router.post("/{ticket_id}/checklist", response_model=ChecklistItemRead, status_code=201)
def create_checklist_item(
    ticket_id: int,
    data: ChecklistItemCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.change.status")),
) -> TicketChecklistItem:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    item = TicketChecklistItem(
        ticket_id=ticket_id, created_by_user_id=actor.id, **data.model_dump()
    )
    db.add(item)
    ticket.version += 1
    ticket.last_activity_at = server_now()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket_id),
            action="ticket.checklist.created",
            new_values_json=json.dumps(data.model_dump(), default=str),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{ticket_id}/checklist/{item_id}", response_model=ChecklistItemRead)
def update_checklist_item(
    ticket_id: int,
    item_id: int,
    data: ChecklistItemUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.change.status")),
) -> TicketChecklistItem:
    ticket = db.get(Ticket, ticket_id)
    item = db.scalar(
        select(TicketChecklistItem).where(
            TicketChecklistItem.id == item_id, TicketChecklistItem.ticket_id == ticket_id
        )
    )
    if not ticket or not item:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(item, field, value)
    if changes.get("is_completed") is True:
        item.completed_by_user_id = actor.id
        item.completed_at = server_now()
    elif changes.get("is_completed") is False:
        item.completed_by_user_id = None
        item.completed_at = None
    ticket.version += 1
    ticket.last_activity_at = server_now()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket_id),
            action="ticket.checklist.updated",
            new_values_json=json.dumps(changes, default=str),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/{ticket_id}/resolution-history", response_model=list[TicketResolutionHistoryRead])
def list_resolution_history(
    ticket_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> list[TicketResolutionHistory]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    return list(
        db.scalars(
            select(TicketResolutionHistory)
            .where(TicketResolutionHistory.ticket_id == ticket_id)
            .order_by(TicketResolutionHistory.resolution_sequence.desc())
        )
    )


@router.get("/{ticket_id}/comments", response_model=list[TicketCommentRead])
def list_comments(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[TicketComment]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    statement = select(TicketComment).where(TicketComment.ticket_id == ticket_id)
    permissions = set(effective_permissions(db, user).permissions)
    if "ticket.comment.internal" not in permissions:
        statement = statement.where(TicketComment.is_internal.in_([False]))
    return list(db.scalars(statement.order_by(TicketComment.created_at)))


@router.post(
    "/{ticket_id}/comments",
    response_model=TicketCommentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    ticket_id: int,
    data: TicketCommentCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.comment.public")),
) -> TicketComment:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    if data.is_internal:
        permissions = set(effective_permissions(db, actor).permissions)
        if "ticket.comment.internal" not in permissions:
            raise AuthorizationError()
    if data.operation_key:
        previous = db.scalar(
            select(TicketComment).where(
                TicketComment.ticket_id == ticket.id,
                TicketComment.author_user_id == actor.id,
                TicketComment.operation_key == data.operation_key,
            )
        )
        if previous:
            if previous.body == data.body and previous.is_internal == data.is_internal:
                return previous
            raise ConflictError(
                "COMMENT_IDEMPOTENCY_CONFLICT",
                "This comment key was already used with different content.",
            )
    responded_at = server_now()
    comment = TicketComment(
        ticket_id=ticket.id,
        author_user_id=actor.id,
        body=data.body,
        is_internal=data.is_internal,
        operation_key=data.operation_key,
        created_at=responded_at,
    )
    if not data.is_internal and actor.user_type == "EMPLOYEE":
        record_first_response(db, ticket, responded_at)
    ticket.last_activity_at = responded_at
    ticket.version += 1
    db.add(comment)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketComment",
            entity_id=str(ticket.id),
            action="ticket.comment.internal" if data.is_internal else "ticket.comment.public",
        )
    )
    db.commit()
    db.refresh(comment)
    return comment


@router.get("/{ticket_id}/mention-candidates", response_model=list[TicketMentionCandidateRead])
def list_mention_candidates(
    ticket_id: int,
    is_internal: bool = False,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.mention")),
) -> list[TicketMentionCandidateRead]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    if is_internal and "ticket.comment.internal" not in set(
        effective_permissions(db, actor).permissions
    ):
        raise AuthorizationError()
    result: list[TicketMentionCandidateRead] = []
    for candidate in db.scalars(
        select(User).where(User.is_active.in_([True]), User.id != actor.id).order_by(User.full_name)
    ):
        if is_internal and candidate.user_type == "CLIENT_PORTAL":
            continue
        try:
            ensure_ticket_access(db, candidate, ticket)
        except AuthorizationError:
            continue
        result.append(
            TicketMentionCandidateRead(
                id=candidate.id,
                full_name=candidate.full_name,
                email=candidate.email,
                user_type=candidate.user_type,
            )
        )
    return result


@router.post(
    "/{ticket_id}/mentions", response_model=TicketMentionResult, status_code=status.HTTP_201_CREATED
)
def create_mention(
    ticket_id: int,
    data: TicketMentionCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.mention")),
) -> TicketMentionResult:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    actor_permissions = set(effective_permissions(db, actor).permissions)
    required_comment_permission = (
        "ticket.comment.internal" if data.is_internal else "ticket.comment.public"
    )
    if required_comment_permission not in actor_permissions:
        raise AuthorizationError()
    recipient_ids = list(dict.fromkeys(data.recipient_user_ids))
    recipients = list(
        db.scalars(select(User).where(User.id.in_(recipient_ids), User.is_active.in_([True])))
    )
    if len(recipients) != len(recipient_ids) or actor.id in recipient_ids:
        raise ConflictError(
            "INVALID_MENTION_RECIPIENT", "One or more mention recipients are invalid."
        )
    for recipient in recipients:
        if data.is_internal and recipient.user_type == "CLIENT_PORTAL":
            raise ConflictError(
                "INVALID_INTERNAL_MENTION", "Client Portal users cannot receive internal mentions."
            )
        try:
            ensure_ticket_access(db, recipient, ticket)
        except AuthorizationError as exc:
            raise ConflictError(
                "MENTION_RECIPIENT_NO_ACCESS", f"{recipient.full_name} cannot access this ticket."
            ) from exc
    if data.operation_key:
        previous = db.scalar(
            select(TicketComment).where(
                TicketComment.ticket_id == ticket.id,
                TicketComment.author_user_id == actor.id,
                TicketComment.operation_key == data.operation_key,
            )
        )
        if previous:
            notified = list(
                db.scalars(
                    select(Notification.recipient_user_id).where(
                        Notification.deduplication_key.like(f"ticket-mention:{previous.id}:user:%")
                    )
                )
            )
            return TicketMentionResult(
                comment=previous, notified_user_ids=notified, followers_added=[]
            )
    now = server_now()
    names = ", ".join(f"@{recipient.full_name}" for recipient in recipients)
    comment = TicketComment(
        ticket_id=ticket.id,
        author_user_id=actor.id,
        body=f"{names}\n\n{data.message.strip()}",
        is_internal=data.is_internal,
        operation_key=data.operation_key,
        created_at=now,
    )
    db.add(comment)
    db.flush()
    followers_added: list[int] = []
    for recipient in recipients:
        notification_message = f"{actor.full_name}: {data.message.strip()}"[:1000]
        db.add(
            Notification(
                recipient_user_id=recipient.id,
                notification_type="TICKET_MENTION",
                severity="INFO",
                title=f"Mentioned on {ticket.ticket_number or f'Ticket {ticket.id}'}",
                message=notification_message,
                deep_link=f"/tickets/{ticket.id}",
                deduplication_key=f"ticket-mention:{comment.id}:user:{recipient.id}",
            )
        )
        if data.add_as_followers and not db.get(
            TicketFollower, {"ticket_id": ticket.id, "user_id": recipient.id}
        ):
            db.add(
                TicketFollower(
                    ticket_id=ticket.id,
                    user_id=recipient.id,
                    added_by_user_id=actor.id,
                    created_at=now,
                )
            )
            followers_added.append(recipient.id)
    subject = f"You were mentioned on {ticket.ticket_number or f'Ticket {ticket.id}'}"
    db.add(
        EventOutbox(
            event_type="TICKET_MENTION_EMAIL",
            aggregate_type="Ticket",
            aggregate_id=str(ticket.id),
            deduplication_key=f"ticket-mention-email:{comment.id}",
            payload_json=json.dumps(
                {
                    "recipient_user_ids": recipient_ids,
                    "subject": subject,
                    "body": f"{actor.full_name} mentioned you:\n\n{data.message.strip()}",
                    "deep_link": f"/tickets/{ticket.id}",
                }
            ),
            status="PENDING",
            created_at=now,
        )
    )
    ticket.last_activity_at = now
    ticket.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketMention",
            entity_id=str(comment.id),
            action="ticket.mention",
        )
    )
    db.commit()
    db.refresh(comment)
    return TicketMentionResult(
        comment=comment, notified_user_ids=recipient_ids, followers_added=followers_added
    )


@router.get("/{ticket_id}/attachments", response_model=list[TicketAttachmentRead])
def list_attachments(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[TicketAttachment]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    statement = select(TicketAttachment).where(TicketAttachment.ticket_id == ticket_id)
    if user.user_type == "CLIENT_PORTAL":
        statement = statement.where(TicketAttachment.portal_visible.in_([True]))
    return list(
        db.scalars(
            statement.order_by(TicketAttachment.created_at)
        )
    )


@router.post(
    "/{ticket_id}/attachments",
    response_model=TicketAttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    operation_key: str | None = Form(default=None, min_length=8, max_length=200),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(current_user),
) -> TicketAttachment:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    permissions = set(effective_permissions(db, actor).permissions)
    if not permissions.intersection({"ticket.comment.public", "ticket.change.status"}):
        raise AuthorizationError("You do not have permission to upload ticket attachments.")
    return await save_attachment(db, ticket, actor, file, settings, operation_key=operation_key)


@router.get("/{ticket_id}/attachments/{attachment_id}/download")
def download_attachment(
    ticket_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(current_user),
) -> FileResponse:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    attachment = db.scalar(
        select(TicketAttachment).where(
            TicketAttachment.id == attachment_id,
            TicketAttachment.ticket_id == ticket_id,
        )
    )
    if not attachment:
        raise NotFoundError()
    if user.user_type == "CLIENT_PORTAL" and not attachment.portal_visible:
        raise NotFoundError()
    return FileResponse(
        attachment_path(attachment, settings),
        media_type=attachment.content_type,
        filename=attachment.original_filename,
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.get("/{ticket_id}/relations", response_model=list[TicketRelationRead])
def list_relations(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[dict[str, object]]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    relations = db.scalars(
        select(TicketRelation)
        .where(
            or_(
                TicketRelation.source_ticket_id == ticket_id,
                TicketRelation.target_ticket_id == ticket_id,
            )
        )
        .order_by(TicketRelation.created_at)
    )
    result: list[dict[str, object]] = []
    for relation in relations:
        outgoing = relation.source_ticket_id == ticket_id
        related = db.get(
            Ticket,
            relation.target_ticket_id if outgoing else relation.source_ticket_id,
        )
        if not related:
            continue
        try:
            ensure_ticket_access(db, user, related)
        except AuthorizationError:
            continue
        result.append(
            {
                "id": relation.id,
                "relation_type": relation.relation_type,
                "direction": "OUTGOING" if outgoing else "INCOMING",
                "related_ticket_id": related.id,
                "related_ticket_number": related.ticket_number,
                "related_subject": related.subject,
                "related_priority": related.priority,
                "created_at": relation.created_at,
            }
        )
    return result


@router.post(
    "/{ticket_id}/relations",
    response_model=TicketRelationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_relation(
    ticket_id: int,
    data: TicketRelationCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.relate")),
) -> dict[str, object]:
    ticket = db.get(Ticket, ticket_id)
    related = db.get(Ticket, data.related_ticket_id)
    if not ticket or not related:
        raise NotFoundError()
    if ticket.id == related.id:
        raise ConflictError("SELF_RELATION", "A ticket cannot be related to itself.")
    ensure_ticket_access(db, actor, ticket)
    ensure_ticket_access(db, actor, related)
    source_id, target_id = ticket.id, related.id
    if data.relation_type in {"RELATED", "DUPLICATE"}:
        source_id, target_id = sorted((source_id, target_id))
    duplicate = db.scalar(
        select(TicketRelation.id).where(
            TicketRelation.source_ticket_id == source_id,
            TicketRelation.target_ticket_id == target_id,
            TicketRelation.relation_type == data.relation_type,
        )
    )
    if duplicate:
        raise ConflictError("RELATION_EXISTS", "This ticket relationship already exists.")
    relation = TicketRelation(
        source_ticket_id=source_id,
        target_ticket_id=target_id,
        relation_type=data.relation_type,
        created_by_user_id=actor.id,
        reason=data.reason,
    )
    ticket.version += 1
    ticket.last_activity_at = server_now()
    db.add(relation)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketRelation",
            entity_id=str(ticket.id),
            action="ticket.relation.created",
            reason=data.reason,
            new_values_json=json.dumps(
                {
                    "related_ticket_id": related.id,
                    "relation_type": data.relation_type,
                }
            ),
        )
    )
    db.commit()
    db.refresh(relation)
    return {
        "id": relation.id,
        "relation_type": relation.relation_type,
        "direction": "OUTGOING" if relation.source_ticket_id == ticket.id else "INCOMING",
        "related_ticket_id": related.id,
        "related_ticket_number": related.ticket_number,
        "related_subject": related.subject,
        "related_priority": related.priority,
        "created_at": relation.created_at,
    }


@router.delete("/{ticket_id}/relations/{relation_id}", status_code=204)
def delete_relation(
    ticket_id: int,
    relation_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.relate")),
) -> Response:
    ticket = db.get(Ticket, ticket_id)
    relation = db.get(TicketRelation, relation_id)
    if (
        not ticket
        or not relation
        or ticket_id
        not in {
            relation.source_ticket_id,
            relation.target_ticket_id,
        }
    ):
        raise NotFoundError()
    related_id = (
        relation.target_ticket_id
        if relation.source_ticket_id == ticket_id
        else relation.source_ticket_id
    )
    related = db.get(Ticket, related_id)
    ensure_ticket_access(db, actor, ticket)
    if related:
        ensure_ticket_access(db, actor, related)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketRelation",
            entity_id=str(ticket.id),
            action="ticket.relation.deleted",
            old_values_json=json.dumps(
                {"related_ticket_id": related_id, "relation_type": relation.relation_type}
            ),
        )
    )
    db.delete(relation)
    ticket.version += 1
    ticket.last_activity_at = server_now()
    db.commit()
    return Response(status_code=204)


@router.post("/{ticket_id}/shift-handover", response_model=TicketRead)
def create_shift_handover(
    ticket_id: int,
    data: TicketShiftHandoverCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    permissions = set(effective_permissions(db, actor).permissions)
    if ticket.assigned_user_id != actor.id and "ticket.assign.team" not in permissions:
        raise AuthorizationError(
            "Only the assigned engineer or an authorized dispatcher can hand over this ticket."
        )
    if ticket.version != data.version:
        raise ConflictError("CONCURRENT_UPDATE", "The ticket was updated by another user.")
    recipient = db.get(User, data.to_user_id) if data.to_user_id else None
    if data.to_user_id:
        recipient = ensure_assignment_eligibility(db, recipient)
    now = server_now()
    if data.follow_up_at <= now:
        raise ConflictError(
            "HANDOVER_FOLLOW_UP_INVALID",
            "The receiving shift follow-up time must be in the future.",
        )
    current_status = db.get(TicketStatus, ticket.status_id)
    if current_status and current_status.code == "PENDING_INTERNAL":
        ticket.pending_reason = f"Shift handover: {data.reason.strip()}"
        ticket.pending_owner_user_id = recipient.id if recipient else actor.id
        ticket.pending_follow_up_at = data.follow_up_at
        ticket.version += 1
        ticket.last_activity_at = now
    else:
        transition_ticket(
            db,
            ticket,
            TicketTransition(
                to_status_code="PENDING_INTERNAL",
                reason=f"Shift handover: {data.reason.strip()}",
                version=ticket.version,
                pending_owner_user_id=recipient.id if recipient else actor.id,
                pending_follow_up_at=data.follow_up_at,
                pending_responsible_party="MILLENSYS",
            ),
            actor,
            commit=False,
            source="SHIFT_HANDOVER",
        )
    previous_assignee = ticket.assigned_user_id
    if data.reassign and recipient:
        ticket.assigned_user_id = recipient.id
        db.add(
            TicketAssignmentHistory(
                ticket_id=ticket.id,
                assigned_user_id=recipient.id,
                assigned_team=ticket.assigned_team,
                assigned_by_user_id=actor.id,
                reason=f"Shift handover: {data.reason.strip()}",
                created_at=now,
            )
        )
    ticket.shift_handover_status = "PENDING"
    ticket.shift_handover_reason = data.reason.strip()
    ticket.shift_handover_by_user_id = actor.id
    ticket.shift_handover_to_user_id = recipient.id if recipient else None
    ticket.shift_handover_at = now
    ticket.shift_handover_completed_at = None
    db.add(
        TicketShiftHandover(
            ticket_id=ticket.id,
            from_user_id=actor.id,
            to_user_id=recipient.id if recipient else None,
            status="PENDING",
            reason=data.reason.strip(),
            follow_up_at=data.follow_up_at,
            created_at=now,
        )
    )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket.id),
            action="ticket.shift_handover.created",
            reason=data.reason.strip(),
            correlation_id=request.state.correlation_id,
            old_values_json=json.dumps({"assigned_user_id": previous_assignee}),
            new_values_json=json.dumps(
                {
                    "assigned_user_id": ticket.assigned_user_id,
                    "handover_to_user_id": data.to_user_id,
                    "follow_up_at": data.follow_up_at.isoformat(),
                }
            ),
        )
    )
    if recipient and recipient.id != actor.id:
        db.add(
            Notification(
                recipient_user_id=recipient.id,
                notification_type="SHIFT_HANDOVER",
                severity="WARNING",
                title=f"Shift handover: {ticket.ticket_number}",
                message=f"{actor.full_name} handed over this ticket: {data.reason.strip()}",
                deep_link=f"/tickets/{ticket.id}",
                deduplication_key=f"shift-handover:{ticket.id}:version:{ticket.version}:user:{recipient.id}",
            )
        )
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/shift-handover/complete", response_model=TicketRead)
def complete_shift_handover(
    ticket_id: int,
    data: TicketShiftHandoverComplete,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    permissions = set(effective_permissions(db, actor).permissions)
    if (
        actor.id not in {ticket.assigned_user_id, ticket.shift_handover_to_user_id}
        and "ticket.assign.team" not in permissions
    ):
        raise AuthorizationError(
            "Only the receiving engineer or an authorized dispatcher can complete this handover."
        )
    if ticket.version != data.version:
        raise ConflictError("CONCURRENT_UPDATE", "The ticket was updated by another user.")
    if ticket.shift_handover_status != "PENDING":
        raise ConflictError(
            "HANDOVER_NOT_PENDING", "This ticket does not have a pending shift handover."
        )
    now = server_now()
    handover = db.scalar(
        select(TicketShiftHandover)
        .where(TicketShiftHandover.ticket_id == ticket.id, TicketShiftHandover.status == "PENDING")
        .order_by(TicketShiftHandover.created_at.desc())
    )
    if handover:
        handover.status = "HANDED_OVER"
        handover.completed_by_user_id = actor.id
        handover.completed_at = now
    ticket.shift_handover_status = "HANDED_OVER"
    ticket.shift_handover_completed_at = now
    ticket.version += 1
    ticket.last_activity_at = now
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket.id),
            action="ticket.shift_handover.completed",
            reason=data.note,
            correlation_id=request.state.correlation_id,
        )
    )
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/assignment", response_model=TicketRead)
def assign_ticket(
    ticket_id: int,
    data: TicketAssignment,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    if ticket.entitlement_status == "PENDING_APPROVAL":
        raise ConflictError(
            "TICKET_AWAITING_ENTITLEMENT_APPROVAL",
            "This ticket is awaiting contract approval and cannot be assigned.",
        )
    if ticket.version != data.version:
        raise ConflictError("CONCURRENT_UPDATE", "The ticket was updated by another user.")
    permissions = set(effective_permissions(db, actor).permissions)
    may_assign_team = "ticket.assign.team" in permissions
    may_assign_self = (
        "ticket.assign.self" in permissions
        and data.assigned_user_id == actor.id
        and data.assigned_team is None
    )
    if not may_assign_team and not may_assign_self:
        raise AuthorizationError()
    assigned_user = db.get(User, data.assigned_user_id) if data.assigned_user_id else None
    if data.assigned_user_id:
        assigned_user = ensure_assignment_eligibility(db, assigned_user)
    if data.assigned_team and not db.scalar(
        select(SupportTeam.id).where(
            SupportTeam.name == data.assigned_team, SupportTeam.is_active.in_([True])
        )
    ):
        raise NotFoundError("Assigned support team does not exist or is inactive.")
    old_values = {
        "assigned_user_id": ticket.assigned_user_id,
        "assigned_team": ticket.assigned_team,
    }
    ticket.assigned_user_id = data.assigned_user_id
    ticket.assigned_team = data.assigned_team
    current_status = db.get(TicketStatus, ticket.status_id)
    if assigned_user and current_status and current_status.code in {"NEW", "TRIAGED", "REOPENED"}:
        assigned_status = db.scalar(select(TicketStatus).where(TicketStatus.code == "ASSIGNED"))
        if not assigned_status:
            raise NotFoundError("Assigned ticket status is not configured.")
        ticket.status_id = assigned_status.id
        db.add(
            TicketStatusHistory(
                ticket_id=ticket.id,
                from_status_id=current_status.id,
                to_status_id=assigned_status.id,
                changed_by_user_id=actor.id,
                reason=f"Engineer assignment: {data.reason}"
                if data.reason
                else "Engineer assignment",
            )
        )
    ticket.version += 1
    assigned_at = server_now()
    ticket.last_activity_at = assigned_at
    if assigned_user and current_status and current_status.code in {"NEW", "TRIAGED", "REOPENED"}:
        queue_ticket_workflow_transition(
            db,
            ticket,
            actor,
            from_status_code=current_status.code,
            to_status_code="ASSIGNED",
            source="ASSIGNMENT",
        )
    apply_first_dedicated_assignment(db, ticket, data.assigned_user_id, assigned_at)
    db.add(
        TicketAssignmentHistory(
            ticket_id=ticket.id,
            assigned_user_id=data.assigned_user_id,
            assigned_team=data.assigned_team,
            assigned_by_user_id=actor.id,
            reason=data.reason,
            created_at=assigned_at,
        )
    )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket.id),
            action="ticket.assigned",
            reason=data.reason,
            correlation_id=request.state.correlation_id,
            old_values_json=json.dumps(old_values),
            new_values_json=json.dumps(
                {"assigned_user_id": data.assigned_user_id, "assigned_team": data.assigned_team}
            ),
        )
    )
    if assigned_user:
        db.add(
            Notification(
                recipient_user_id=assigned_user.id,
                notification_type="TICKET_ASSIGNED",
                severity="INFO",
                title=f"Ticket assigned: {ticket.ticket_number}",
                message=f"{actor.full_name} assigned you: {ticket.subject}",
                deep_link=f"/tickets/{ticket.id}",
                deduplication_key=(
                    f"ticket-assigned:{ticket.id}:version:{ticket.version}:user:{assigned_user.id}"
                ),
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
                correlation_id=request.state.correlation_id,
            )
        )
    from app.modules.uat.service import sync_ticket_to_uat

    sync_ticket_to_uat(
        db,
        ticket,
        actor,
        target_status_code=(
            "ASSIGNED"
            if data.assigned_user_id or data.assigned_team
            else (current_status.code if current_status else None)
        ),
    )
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/claim", response_model=TicketRead)
def claim_ticket(
    ticket_id: int,
    data: TicketAssignment,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> Ticket:
    """Assign a visible ticket directly to the logged-in employee."""
    if actor.user_type != "EMPLOYEE" or not actor.is_active:
        raise NotFoundError("An active employee account is required to claim a ticket.")
    if "ticket.assign.self" not in set(effective_permissions(db, actor).permissions):
        raise AuthorizationError("You do not have permission to assign tickets to yourself.")
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    if ticket.assigned_user_id != actor.id and not _is_shared_support_assignee(
        db, ticket.assigned_user_id
    ):
        raise ConflictError(
            "TICKET_ASSIGNED_TO_ANOTHER_USER",
            "This ticket is already assigned to another engineer.",
        )
    result = assign_ticket(
        ticket_id,
        TicketAssignment(
            assigned_user_id=actor.id,
            assigned_team=actor.department,
            reason="Self-assigned using Assign to me",
            version=data.version,
        ),
        request,
        db,
        actor,
    )
    if result.routed_department_id is not None and result.routing_status == "NEW":
        result.routing_status = "IN_PROGRESS"
        db.commit()
        db.refresh(result)
    return result


@router.post("/{ticket_id}/help-request", response_model=TicketRead, status_code=201)
def request_department_help(
    ticket_id: int,
    data: TicketEscalation,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.help.request")),
) -> Ticket:
    """Create one controlled departmental work item while Support retains the parent."""
    parent = db.get(Ticket, ticket_id)
    if not parent:
        raise NotFoundError()
    ensure_ticket_access(db, actor, parent)
    if parent.entitlement_status == "PENDING_APPROVAL":
        raise ConflictError(
            "TICKET_AWAITING_ENTITLEMENT_APPROVAL",
            "Approval is required before requesting departmental help.",
        )
    if parent.assigned_user_id != actor.id:
        raise ConflictError(
            "TICKET_NOT_ASSIGNED_TO_ACTOR",
            "Assign the ticket to yourself before requesting departmental help.",
        )
    if parent.version != data.version:
        raise ConflictError("CONCURRENT_UPDATE", "The ticket was updated by another user.")
    department = db.get(Department, data.department_id) if data.department_id else None
    if not department or not department.is_active:
        raise ConflictError("INVALID_ROUTING_DEPARTMENT", "Select an active department.")
    team = db.get(SupportTeam, data.team_id) if data.team_id else None
    if team and (not team.is_active or team.department_id != department.id):
        raise ConflictError(
            "INVALID_ROUTING_TEAM", "The selected team does not belong to that department."
        )
    assignee = (
        db.get(User, data.escalation_assignee_user_id) if data.escalation_assignee_user_id else None
    )
    if assignee and (
        not assignee.is_active
        or assignee.user_type != "EMPLOYEE"
        or assignee.department_id != department.id
    ):
        raise ConflictError(
            "INVALID_ROUTING_ASSIGNEE",
            "The engineer must be active and belong to the routed department.",
        )
    if (
        assignee
        and team
        and not db.get(SupportTeamMember, (team.id, assignee.id))
        and team.leader_user_id != assignee.id
    ):
        raise ConflictError(
            "INVALID_ROUTING_ASSIGNEE", "The engineer does not belong to the selected team."
        )
    assigned_status = db.scalar(select(TicketStatus).where(TicketStatus.code == "ASSIGNED"))
    ticket_type = db.get(TicketType, parent.ticket_type_id)
    if not assigned_status or not ticket_type:
        raise ConflictError(
            "TICKET_CATALOG_INCOMPLETE", "Ticket status or type configuration is incomplete."
        )
    child = Ticket(
        ticket_type_id=parent.ticket_type_id,
        client_id=parent.client_id,
        branch_id=parent.branch_id,
        requester_contact_id=parent.requester_contact_id,
        created_by_user_id=actor.id,
        status_id=assigned_status.id,
        contract_id=parent.contract_id,
        entitlement_status=parent.entitlement_status,
        assigned_user_id=assignee.id if assignee else None,
        assigned_team=team.name if team else None,
        routed_department_id=department.id,
        routed_team_id=team.id if team else None,
        routing_status="NEW",
        escalation_parent_ticket_id=parent.id,
        product_id=parent.product_id,
        product_module_id=parent.product_module_id,
        environment_id=parent.environment_id,
        service_id=parent.service_id,
        source_channel="INTERNAL",
        impact=parent.impact,
        urgency=parent.urgency,
        priority=parent.priority,
        subject=f"Help request: {parent.subject}",
        description=f"Department request from {parent.ticket_number}.\n\nHelp required: {data.reason}",
    )
    db.add(child)
    db.flush()
    child.ticket_number = f"{ticket_type.number_prefix}-{server_now().year}-{child.id:06d}"
    parent.escalation_level = "OTHER_DEPARTMENT"
    parent.escalation_reason = data.reason
    parent.escalated_at = server_now()
    parent.version += 1
    db.add(
        TicketRelation(
            source_ticket_id=parent.id,
            target_ticket_id=child.id,
            relation_type="PARENT_CHILD",
            created_by_user_id=actor.id,
            reason=data.reason,
        )
    )
    db.add(
        TicketStatusHistory(
            ticket_id=child.id,
            to_status_id=assigned_status.id,
            changed_by_user_id=actor.id,
            reason=f"Routed to {department.name}",
        )
    )
    recipients = (
        {assignee.id}
        if assignee
        else set(
            db.scalars(
                select(User.id).where(
                    User.is_active.in_([True]), User.department_id == department.id
                )
            )
        )
    )
    if team:
        team_people = set(
            db.scalars(
                select(SupportTeamMember.user_id).where(SupportTeamMember.team_id == team.id)
            )
        )
        if team.leader_user_id:
            team_people.add(team.leader_user_id)
        recipients &= team_people
    for recipient_id in recipients:
        db.add(
            Notification(
                recipient_user_id=recipient_id,
                notification_type="DEPARTMENT_HELP_REQUEST",
                severity="INFO",
                title=f"New {department.name} request: {child.ticket_number}",
                message=data.reason,
                deep_link=f"/tickets/{child.id}",
                deduplication_key=f"department-help:{child.id}:user:{recipient_id}",
            )
        )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(parent.id),
            action="ticket.help.requested",
            reason=data.reason,
            correlation_id=request.state.correlation_id,
            new_values_json=json.dumps(
                {
                    "child_ticket_id": child.id,
                    "department_id": department.id,
                    "team_id": team.id if team else None,
                    "assigned_user_id": assignee.id if assignee else None,
                }
            ),
        )
    )
    db.commit()
    db.refresh(child)
    return child


@router.post("/{ticket_id}/return-result", response_model=TicketRead)
def return_department_result(
    ticket_id: int,
    data: TicketHelpReturn,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.help.return")),
) -> Ticket:
    child = db.get(Ticket, ticket_id)
    if not child or child.escalation_parent_ticket_id is None:
        raise NotFoundError("Department help request does not exist.")
    ensure_ticket_access(db, actor, child)
    if child.version != data.version:
        raise ConflictError("CONCURRENT_UPDATE", "The request was updated by another user.")
    now = server_now()
    child.help_request_result = data.result.strip()
    child.routing_status = "RETURNED"
    child.returned_at = now
    child.returned_by_user_id = actor.id
    child.version += 1
    parent = db.get(Ticket, child.escalation_parent_ticket_id)
    if parent:
        parent.last_activity_at = now
        db.add(
            Notification(
                recipient_user_id=parent.assigned_user_id or parent.created_by_user_id,
                notification_type="DEPARTMENT_HELP_RETURNED",
                severity="SUCCESS",
                title=f"Result returned for {parent.ticket_number}",
                message=data.result.strip(),
                deep_link=f"/tickets/{parent.id}",
                deduplication_key=f"department-return:{child.id}:version:{child.version}",
            )
        )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(child.id),
            action="ticket.help.returned",
            reason=data.result.strip(),
            correlation_id=request.state.correlation_id,
        )
    )
    db.commit()
    db.refresh(child)
    return child


@router.post("/{ticket_id}/escalation", response_model=TicketRead)
def escalate_ticket(
    ticket_id: int,
    data: TicketEscalation,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.escalate")),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    if ticket.entitlement_status == "PENDING_APPROVAL":
        raise ConflictError(
            "TICKET_AWAITING_ENTITLEMENT_APPROVAL",
            "Approval is required before escalating this ticket.",
        )
    if ticket.assigned_user_id != actor.id:
        raise ConflictError(
            "TICKET_NOT_ASSIGNED_TO_ACTOR", "Assign the ticket to yourself before escalating it."
        )
    if ticket.version != data.version:
        raise ConflictError("CONCURRENT_UPDATE", "The ticket was updated by another user.")
    assignee = (
        db.get(User, data.escalation_assignee_user_id) if data.escalation_assignee_user_id else None
    )
    if data.escalation_assignee_user_id and (
        not assignee or not assignee.is_active or assignee.user_type != "EMPLOYEE"
    ):
        raise NotFoundError("Escalation assignee does not exist or is inactive.")
    if data.escalation_level == "OTHER_DEPARTMENT":
        raise ConflictError(
            "DEPARTMENT_HELP_REQUEST_REQUIRED",
            "Use Request another department for cross-department work.",
        )
    if assignee and assignee.department_id != actor.department_id:
        raise ConflictError(
            "CROSS_DEPARTMENT_ESCALATION_REQUIRES_HELP_REQUEST",
            "Internal escalation is limited to your department. Use Request another department instead.",
        )
    old_values = {
        "escalation_assignee_user_id": ticket.escalation_assignee_user_id,
        "escalation_level": ticket.escalation_level,
        "escalation_reason": ticket.escalation_reason,
    }
    now = server_now()
    active_escalation = db.scalar(
        select(TicketSlaInterval)
        .where(
            TicketSlaInterval.ticket_id == ticket.id,
            TicketSlaInterval.interval_type == "ESCALATION",
            TicketSlaInterval.ended_at.is_(None),
        )
        .order_by(TicketSlaInterval.started_at.desc())
    )
    if active_escalation and (
        not assignee or old_values["escalation_assignee_user_id"] != assignee.id
    ):
        active_escalation.ended_at = now
    if assignee and old_values["escalation_assignee_user_id"] != assignee.id:
        db.add(
            TicketSlaInterval(
                ticket_id=ticket.id,
                interval_type="ESCALATION",
                comment=data.reason,
                started_at=now,
                created_by_user_id=actor.id,
            )
        )
    ticket.escalation_assignee_user_id = data.escalation_assignee_user_id
    ticket.escalation_level = data.escalation_level if assignee else None
    ticket.escalation_reason = data.reason
    ticket.escalated_at = now if assignee else None
    ticket.version += 1
    ticket.last_activity_at = now
    action = "ticket.escalated" if assignee else "ticket.escalation.cleared"
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket.id),
            action=action,
            reason=data.reason,
            correlation_id=request.state.correlation_id,
            old_values_json=json.dumps(old_values),
            new_values_json=json.dumps(
                {
                    "escalation_assignee_user_id": data.escalation_assignee_user_id,
                    "escalation_level": ticket.escalation_level,
                }
            ),
        )
    )
    if assignee:
        db.add(
            Notification(
                recipient_user_id=assignee.id,
                notification_type="TICKET_ESCALATED",
                severity="WARNING",
                title=f"Ticket escalated to you: {ticket.ticket_number}",
                message=f"{actor.full_name}: {data.reason}",
                deep_link=f"/tickets/{ticket.id}",
                deduplication_key=(
                    f"ticket-escalated:{ticket.id}:version:{ticket.version}:user:{assignee.id}"
                ),
            )
        )
        if old_values["escalation_assignee_user_id"] != assignee.id:
            assigned_status = db.scalar(select(TicketStatus).where(TicketStatus.code == "ASSIGNED"))
            ticket_type = db.get(TicketType, ticket.ticket_type_id)
            if assigned_status and ticket_type:
                child = Ticket(
                    ticket_type_id=ticket.ticket_type_id,
                    client_id=ticket.client_id,
                    branch_id=ticket.branch_id,
                    requester_contact_id=ticket.requester_contact_id,
                    created_by_user_id=actor.id,
                    status_id=assigned_status.id,
                    contract_id=ticket.contract_id,
                    entitlement_status=ticket.entitlement_status,
                    assigned_user_id=assignee.id,
                    escalation_parent_ticket_id=ticket.id,
                    product_id=ticket.product_id,
                    product_module_id=ticket.product_module_id,
                    environment_id=ticket.environment_id,
                    service_id=ticket.service_id,
                    source_channel="WEB",
                    impact=ticket.impact,
                    urgency=ticket.urgency,
                    priority=ticket.priority,
                    subject=f"Escalation support: {ticket.subject}",
                    description=f"Child ticket created from {ticket.ticket_number}.\n\nEscalation request: {data.reason}",
                )
                db.add(child)
                db.flush()
                child.ticket_number = (
                    f"{ticket_type.number_prefix}-{server_now().year}-{child.id:06d}"
                )
                db.add(
                    TicketRelation(
                        source_ticket_id=ticket.id,
                        target_ticket_id=child.id,
                        relation_type="PARENT_CHILD",
                        created_by_user_id=actor.id,
                        reason=data.reason,
                    )
                )
                db.add(
                    TicketStatusHistory(
                        ticket_id=child.id,
                        to_status_id=assigned_status.id,
                        changed_by_user_id=actor.id,
                        reason="Created automatically from internal escalation",
                    )
                )
                db.add(
                    Notification(
                        recipient_user_id=assignee.id,
                        notification_type="TICKET_ASSIGNED",
                        severity="WARNING",
                        title=f"Escalation child ticket assigned: {child.ticket_number}",
                        message=data.reason,
                        deep_link=f"/tickets/{child.id}",
                        deduplication_key=f"escalation-child:{child.id}:user:{assignee.id}",
                    )
                )
    db.commit()
    db.refresh(ticket)
    return ticket


@catalog_router.get("/ticket-types", response_model=list[TicketCatalogRead])
def list_ticket_types(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
) -> list[TicketType]:
    statement = select(TicketType)
    if not include_inactive:
        statement = statement.where(TicketType.is_active.in_([True]))
    return list(db.scalars(statement.order_by(TicketType.name)))


@catalog_router.post(
    "/ticket-types", response_model=TicketCatalogRead, status_code=status.HTTP_201_CREATED
)
def create_ticket_type(
    data: TicketTypeCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> TicketType:
    item = TicketType(
        code=data.code.strip().upper() if data.code else f"PENDING-TYP-{server_now().timestamp()}",
        name=data.name.strip(),
        name_ar=data.name_ar.strip() if data.name_ar else None,
        number_prefix=data.number_prefix.strip().upper(),
        color=data.color.upper(),
        is_active=data.is_active,
        available_for_deployment_issue=data.available_for_deployment_issue,
    )
    db.add(item)
    db.flush()
    if not data.code:
        item.code = f"TYP-{item.id:06d}"
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketType",
            entity_id=str(item.id),
            action="ticket_type.created",
        )
    )
    db.commit()
    db.refresh(item)
    return item


@catalog_router.patch("/ticket-types/{type_id}", response_model=TicketCatalogRead)
def update_ticket_type(
    type_id: int,
    data: TicketTypeUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> TicketType:
    item = db.get(TicketType, type_id)
    if not item:
        raise NotFoundError()
    item.name = data.name.strip()
    item.name_ar = data.name_ar.strip() if data.name_ar else None
    item.number_prefix = data.number_prefix.strip().upper()
    item.color = data.color.upper()
    item.is_active = data.is_active
    item.available_for_deployment_issue = data.available_for_deployment_issue
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketType",
            entity_id=str(item.id),
            action="ticket_type.updated",
        )
    )
    db.commit()
    db.refresh(item)
    return item


@catalog_router.get("/ticket-statuses", response_model=list[TicketCatalogRead])
def list_ticket_statuses(
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
) -> list[TicketStatus]:
    return list(db.scalars(select(TicketStatus).order_by(TicketStatus.sort_order)))


@catalog_router.patch("/ticket-statuses/{status_id}", response_model=TicketCatalogRead)
def update_ticket_status(
    status_id: int,
    data: TicketStatusUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> TicketStatus:
    item = db.get(TicketStatus, status_id)
    if not item:
        raise NotFoundError()
    old = {"name": item.name, "color": item.color}
    item.name = data.name.strip()
    item.name_ar = data.name_ar.strip() if data.name_ar else None
    item.color = data.color.upper()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketStatus",
            entity_id=str(item.id),
            action="ticket_status.updated",
            old_values_json=json.dumps(old),
            new_values_json=json.dumps({"name": item.name, "color": item.color}),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@catalog_router.get("/ticket-assignees", response_model=list[TicketAssigneeRead])
def list_ticket_assignees(
    q: str | None = Query(default=None, max_length=150),
    limit: int = Query(default=100, ge=1, le=200),
    include_user_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("ticket.assign.team")),
) -> list[User]:
    today_start = datetime.combine(server_now().date(), time.min, tzinfo=server_timezone())
    recent_use = (
        select(func.max(TicketAssignmentHistory.created_at))
        .where(
            TicketAssignmentHistory.assigned_user_id == User.id,
            TicketAssignmentHistory.created_at >= today_start,
        )
        .correlate(User)
        .scalar_subquery()
    )
    statement = select(User).where(User.is_active.in_([True]), User.user_type == "EMPLOYEE")
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        statement = statement.where(
            or_(
                User.full_name.ilike(pattern),
                User.username.ilike(pattern),
                User.email.ilike(pattern),
                User.department.ilike(pattern),
                User.job_title.ilike(pattern),
            )
        )
    settings = {
        row.key: row.value
        for row in db.scalars(
            select(SiteSetting).where(
                SiteSetting.key.in_(["assign_available_only", "assign_online_only"])
            )
        )
    }
    if settings.get("assign_online_only") == "true":
        online = User.last_seen_at >= server_now() - timedelta(minutes=2)
        statement = (
            statement.where(or_(online, User.id == include_user_id))
            if include_user_id
            else statement.where(online)
        )
    if settings.get("assign_available_only") == "true":
        in_progress_id = db.scalar(
            select(TicketStatus.id).where(TicketStatus.code == "IN_PROGRESS")
        )
        busy_ids = select(Ticket.assigned_user_id).where(Ticket.status_id == in_progress_id)
        available = User.id.not_in(busy_ids)
        statement = (
            statement.where(or_(available, User.id == include_user_id))
            if include_user_id
            else statement.where(available)
        )
    rows = list(
        db.execute(
            statement.add_columns(recent_use.label("last_assigned_at"))
            .order_by(recent_use.desc(), User.full_name)
            .limit(limit)
        )
    )
    result: list[User] = []
    for user, last_assigned_at in rows:
        user.last_assigned_at = last_assigned_at
        result.append(user)
    return result
