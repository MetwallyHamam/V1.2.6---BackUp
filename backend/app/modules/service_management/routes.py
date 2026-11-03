import io
import json
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select, func, or_, select, true
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, require_permission
from app.core.clock import server_now, server_timezone
from app.core.config import Settings, get_settings
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import (
    Branch,
    Client,
    ClientLocation,
    Product,
    ProductModule,
    SupportTeamMember,
)
from app.modules.iam.models import AuditLog, User
from app.modules.iam.service import effective_permissions
from app.modules.knowledge_base.models import (
    Article,
    ArticleModuleLink,
    ArticleProductLink,
    ArticleVersion,
)
from app.modules.notifications.models import Notification
from app.modules.service_management.attachments import (
    problem_attachment_path,
    save_problem_attachment,
)
from app.modules.service_management.lifecycle import (
    CHANGE_TRANSITIONS,
    MAJOR_INCIDENT_TRANSITIONS,
    PROBLEM_TRANSITIONS,
    validate_transition,
)
from app.modules.service_management.models import (
    ChangeRequestApproval,
    ChangeRequestDetail,
    ChangeRequestStatusHistory,
    MajorIncident,
    MajorIncidentClientScope,
    MajorIncidentEnvironmentScope,
    MajorIncidentModuleScope,
    MajorIncidentProblemLink,
    MajorIncidentProductScope,
    MajorIncidentServiceScope,
    MajorIncidentTicketLink,
    MajorIncidentUpdate,
    Problem,
    ProblemAttachment,
    ProblemChangeLink,
    ProblemComment,
    ProblemKnowledgeLink,
    ProblemRootCause,
    ProblemStatusHistory,
    ProblemTask,
    ProblemTicketLink,
)
from app.modules.tickets.models import (
    RootCause,
    Ticket,
    TicketStatus,
    TicketStatusHistory,
    TicketType,
)
from app.modules.tickets.service import visible_ticket_query

router = APIRouter(tags=["service management"])


CHANGE_PARENT_TICKET_STATUS = {
    "SUBMITTED": "IN_PROGRESS",
    "UNDER_ASSESSMENT": "IN_PROGRESS",
    "AWAITING_APPROVAL": "PENDING_INTERNAL",
    "APPROVED": "PENDING_INTERNAL",
    "REJECTED": "PENDING_INTERNAL",
    "PLANNED": "PENDING_INTERNAL",
    "PENDING_DEPLOYMENT": "PENDING_INTERNAL",
    "IMPLEMENTING": "IN_PROGRESS",
    "VALIDATION": "IN_PROGRESS",
    "FAILED": "IN_PROGRESS",
    "ROLLED_BACK": "IN_PROGRESS",
    "COMPLETED": "RESOLVED",
    "CANCELLED": "CANCELLED",
}


def _synchronize_change_parent_ticket(
    db: Session,
    ticket: Ticket,
    change_status: str,
    actor: User,
    reason: str | None,
) -> None:
    """Keep the parent ticket lifecycle aligned with its governed Change lifecycle."""
    target_code = CHANGE_PARENT_TICKET_STATUS.get(change_status)
    if target_code is None:
        return
    current = db.get(TicketStatus, ticket.status_id)
    target = db.scalar(select(TicketStatus).where(TicketStatus.code == target_code))
    if not current or not target:
        raise ConflictError(
            "CHANGE_PARENT_STATUS_NOT_CONFIGURED",
            f"Parent ticket status {target_code} is not configured.",
        )
    if current.id == target.id:
        return

    now = server_now()
    old_status_id = ticket.status_id
    ticket.status_id = target.id
    ticket.version += 1
    ticket.last_activity_at = now
    if target_code == "IN_PROGRESS":
        ticket.progress_started_at = ticket.progress_started_at or now
        ticket.resolved_at = None
        ticket.closed_at = None
        ticket.cancelled_at = None
    elif target_code == "PENDING_INTERNAL":
        ticket.pending_reason = (
            reason or f"Change Request is {change_status.replace('_', ' ').lower()}."
        )
        ticket.pending_owner_user_id = actor.id
        ticket.pending_follow_up_at = None
    elif target_code == "RESOLVED":
        ticket.resolved_at = now
        ticket.pending_reason = None
        ticket.pending_owner_user_id = None
        ticket.pending_follow_up_at = None
    elif target_code == "CANCELLED":
        ticket.cancelled_at = now
        ticket.resolved_at = None
        ticket.closed_at = None
        ticket.pending_reason = None
        ticket.pending_owner_user_id = None
        ticket.pending_follow_up_at = None

    if current.code.startswith("PENDING_") and target_code != "PENDING_INTERNAL":
        ticket.pending_reason = None
        ticket.pending_owner_user_id = None
        ticket.pending_follow_up_at = None
    synchronization_reason = (
        f"Automatically synchronized with Change Request status "
        f"{change_status.replace('_', ' ').title()}."
    )
    db.add(
        TicketStatusHistory(
            ticket_id=ticket.id,
            from_status_id=old_status_id,
            to_status_id=target.id,
            changed_by_user_id=actor.id,
            reason=synchronization_reason,
            source="CHANGE_REQUEST",
        )
    )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Ticket",
            entity_id=str(ticket.id),
            action="ticket.status.synchronized_from_change_request",
            reason=reason,
            old_values_json=json.dumps({"status": current.code}),
            new_values_json=json.dumps(
                {"status": target_code, "change_status": change_status}
            ),
        )
    )


class OrmRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProblemCreate(BaseModel):
    title: str = Field(min_length=3, max_length=250)
    description: str = Field(min_length=5, max_length=20000)
    priority: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    owner_user_id: int | None = None
    owner_team_id: int | None = None
    product_id: int | None = None
    product_module_id: int | None = None
    environment_id: int | None = None
    source_ticket_id: int | None = None


class ProblemRead(OrmRead):
    id: int; problem_number: str; title: str; description: str; status: str; priority: str
    owner_user_id: int | None; owner_team_id: int | None; version: int
    product_id: int | None; product_module_id: int | None; environment_id: int | None
    business_impact: str | None; symptoms: str | None; workaround: str | None
    known_error_summary: str | None; root_cause_summary: str | None
    permanent_fix_summary: str | None; target_resolution_date: datetime | None
    resolved_at: datetime | None; closed_at: datetime | None; created_by_user_id: int
    created_at: datetime; updated_at: datetime


class Transition(BaseModel):
    status: str = Field(min_length=3, max_length=40)
    version: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=2000)
    root_cause_summary: str | None = Field(default=None, max_length=20000)
    permanent_fix_summary: str | None = Field(default=None, max_length=20000)


class VersionedLink(BaseModel):
    ticket_id: int
    link_type: str = Field(min_length=3, max_length=30)
    version: int = Field(ge=1)


class ProblemTicketLinks(BaseModel):
    ticket_id: int | None = None
    ticket_ids: list[int] = Field(default_factory=list, max_length=200)
    link_type: str = Field(min_length=3, max_length=30)
    version: int = Field(ge=1)


class VersionedUnlink(BaseModel):
    version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=2000)


class ProblemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=250)
    description: str | None = Field(default=None, min_length=5, max_length=20000)
    priority: str | None = Field(default=None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    owner_user_id: int | None = None
    owner_team_id: int | None = None
    business_impact: str | None = Field(default=None, max_length=20000)
    symptoms: str | None = Field(default=None, max_length=20000)
    workaround: str | None = Field(default=None, max_length=20000)
    known_error_summary: str | None = Field(default=None, max_length=20000)
    root_cause_summary: str | None = Field(default=None, max_length=20000)
    permanent_fix_summary: str | None = Field(default=None, max_length=20000)
    target_resolution_date: datetime | None = None
    version: int = Field(ge=1)


class RootCauseLinks(BaseModel):
    root_cause_ids: list[int] = Field(min_length=1, max_length=25)
    version: int = Field(ge=1)


class ProblemCommentCreate(BaseModel):
    body: str = Field(min_length=2, max_length=20000)
    is_internal: bool = True


class ProblemTaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=250)
    description: str | None = Field(default=None, max_length=20000)
    assigned_user_id: int | None = None
    due_at: datetime | None = None


class ProblemTaskUpdate(BaseModel):
    status: str = Field(pattern="^(OPEN|IN_PROGRESS|COMPLETED|CANCELLED)$")
    version: int = Field(ge=1)


class ProblemKnowledgeCreate(BaseModel):
    article_id: int
    link_type: str = Field(default="RELATED", pattern="^(WORKAROUND|PERMANENT_FIX|RELATED)$")
    version: int = Field(ge=1)


class ProblemKnowledgeDraftCreate(BaseModel):
    content_type: str = Field(pattern="^(WORKAROUND|PERMANENT_FIX)$")
    title: str | None = Field(default=None, max_length=300)
    version: int = Field(ge=1)


class MajorProblemLinkCreate(BaseModel):
    problem_id: int
    version: int = Field(ge=1)


class MajorProblemCommitment(BaseModel):
    owner_user_id: int
    due_at: datetime
    version: int = Field(ge=1)


class MajorIncidentScopes(BaseModel):
    client_ids: list[int] = Field(default_factory=list, max_length=250)
    product_ids: list[int] = Field(default_factory=list, max_length=100)
    product_module_ids: list[int] = Field(default_factory=list, max_length=200)
    service_ids: list[int] = Field(default_factory=list, max_length=200)
    environment_ids: list[int] = Field(default_factory=list, max_length=100)
    version: int = Field(ge=1)


class MajorIncidentCreate(BaseModel):
    severity: str = Field(pattern="^(SEV1|SEV2|SEV3|SEV4)$")
    incident_commander_user_id: int
    technical_owner_user_id: int | None = None
    communication_owner_user_id: int | None = None
    detected_at: datetime | None = None
    business_impact: str = Field(min_length=5, max_length=20000)
    affected_users: str | None = Field(default=None, max_length=500)
    current_status_summary: str = Field(min_length=5, max_length=20000)
    next_update_at: datetime | None = None


class MajorIncidentRead(OrmRead):
    id: int; major_incident_number: str; primary_ticket_id: int; severity: str; status: str
    incident_commander_user_id: int; business_impact: str; current_status_summary: str
    technical_owner_user_id: int | None; communication_owner_user_id: int | None
    detected_at: datetime | None; service_restored_at: datetime | None
    monitoring_started_at: datetime | None; closed_at: datetime | None
    affected_users: str | None; next_update_at: datetime | None
    resolution_summary: str | None; post_incident_review: str | None
    problem_follow_up_owner_user_id: int | None; problem_follow_up_due_at: datetime | None
    created_by_user_id: int; version: int; declared_at: datetime; created_at: datetime; updated_at: datetime


class MajorIncidentEdit(BaseModel):
    severity: str | None = Field(default=None, pattern="^(SEV1|SEV2|SEV3|SEV4)$")
    incident_commander_user_id: int | None = None
    technical_owner_user_id: int | None = None
    communication_owner_user_id: int | None = None
    business_impact: str | None = Field(default=None, min_length=5, max_length=20000)
    affected_users: str | None = Field(default=None, max_length=500)
    current_status_summary: str | None = Field(default=None, min_length=5, max_length=20000)
    next_update_at: datetime | None = None
    resolution_summary: str | None = Field(default=None, max_length=20000)
    post_incident_review: str | None = Field(default=None, max_length=30000)
    version: int = Field(ge=1)


class MajorUpdateCreate(BaseModel):
    update_type: str = Field(pattern="^(INTERNAL|CLIENT|RESTORATION)$")
    internal_message: str | None = Field(default=None, max_length=20000)
    client_message: str | None = Field(default=None, max_length=20000)


class ChangeWrite(BaseModel):
    request_kind: str = Field(pattern="^(NEW_FEATURE|UPDATE_EXISTING_FEATURE)$")
    purpose: str = Field(min_length=3, max_length=20000)
    detailed_description: str = Field(min_length=5, max_length=30000)
    business_impact: str = Field(min_length=3, max_length=20000)
    expected_result: str = Field(min_length=3, max_length=20000)
    affected_product_id: int | None = None
    affected_module_id: int | None = None
    required_permissions: str | None = Field(default=None, max_length=10000)
    requested_priority: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    assessment_owner_user_id: int | None = None
    technical_impact: str | None = Field(default=None, max_length=20000)
    security_impact: str | None = Field(default=None, max_length=20000)
    data_impact: str | None = Field(default=None, max_length=20000)
    downtime_required: bool = False
    risk_level: str | None = Field(default=None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    estimated_effort: str | None = Field(default=None, max_length=200)
    target_release: str | None = Field(default=None, max_length=100)
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None
    implementation_plan: str | None = Field(default=None, max_length=30000)
    rollback_plan: str | None = Field(default=None, max_length=30000)
    test_plan: str | None = Field(default=None, max_length=30000)
    deployment_environment: str | None = Field(default=None, pattern="^(TEST|STAGING|PRODUCTION)$")
    deployment_requirements: str | None = Field(default=None, max_length=20000)
    permissions_readiness: str = Field(default="PENDING", pattern="^(PENDING|COMPLETED|NOT_REQUIRED)$")
    training_readiness: str = Field(default="PENDING", pattern="^(PENDING|COMPLETED|NOT_REQUIRED)$")
    documentation_readiness: str = Field(default="PENDING", pattern="^(PENDING|COMPLETED|NOT_REQUIRED)$")
    implementation_outcome: str | None = Field(default=None, pattern="^(SUCCESSFUL|FAILED|ROLLED_BACK)$")
    actual_implemented_at: datetime | None = None
    validation_result: str | None = Field(default=None, max_length=30000)
    version: int | None = Field(default=None, ge=1)


class ChangeRead(OrmRead):
    id: int; ticket_id: int; request_kind: str; purpose: str; detailed_description: str
    business_impact: str; expected_result: str; change_status: str; version: int
    affected_product_id: int | None; affected_module_id: int | None
    required_permissions: str | None; requested_priority: str
    assessment_owner_user_id: int | None; technical_impact: str | None
    security_impact: str | None; data_impact: str | None; downtime_required: bool
    risk_level: str | None; estimated_effort: str | None; target_release: str | None
    planned_start_at: datetime | None; planned_end_at: datetime | None
    implementation_plan: str | None; rollback_plan: str | None; test_plan: str | None
    deployment_environment: str | None; deployment_requirements: str | None
    permissions_readiness: str; training_readiness: str; documentation_readiness: str
    implementation_outcome: str | None
    actual_implemented_at: datetime | None; validation_result: str | None
    created_at: datetime; updated_at: datetime


class ApprovalRequest(BaseModel):
    approval_stage: str = Field(default="MANAGER", min_length=2, max_length=50)
    approver_user_id: int
    version: int = Field(ge=1)


class ApprovalDecision(BaseModel):
    decision: str = Field(pattern="^(APPROVED|REJECTED)$")
    comment: str = Field(min_length=2, max_length=2000)
    version: int = Field(ge=1)


def _audit(db: Session, request: Request, actor: User, entity: str, entity_id: int, action: str, *, old: object | None = None, new: object | None = None, reason: str | None = None) -> None:
    db.add(AuditLog(actor_user_id=actor.id, entity_type=entity, entity_id=str(entity_id), action=action, reason=reason, correlation_id=getattr(request.state, "correlation_id", None), old_values_json=json.dumps(old, default=str) if old is not None else None, new_values_json=json.dumps(new, default=str) if new is not None else None))


def _notify_users(db: Session, actor: User, recipient_ids: set[int | None], *, notification_type: str, severity: str, title: str, message: str, deep_link: str, deduplication_key: str) -> None:
    for recipient_id in {item for item in recipient_ids if item is not None and item != actor.id}:
        db.add(Notification(recipient_user_id=recipient_id, notification_type=notification_type, severity=severity, title=title, message=message, deep_link=deep_link, deduplication_key=f"{deduplication_key}:user:{recipient_id}"))


def _visible_ticket(db: Session, actor: User, ticket_id: int) -> Ticket:
    row = db.scalar(visible_ticket_query(db, actor, include_archived=True).where(Ticket.id == ticket_id))
    if not row:
        raise NotFoundError("Ticket not found or is outside your access scope.")
    return row


def _version(actual: int, supplied: int) -> None:
    if actual != supplied:
        raise ConflictError("CONCURRENT_UPDATE", "The record was updated by another request. Refresh and try again.", {"current_version": actual})


def _require(db: Session, actor: User, permission: str) -> None:
    if permission not in effective_permissions(db, actor).permissions:
        raise AuthorizationError(details={"required_permission": permission})


def _problem_statement(db: Session, actor: User) -> Select[tuple[Problem]]:
    access = effective_permissions(db, actor)
    statement = select(Problem)
    if "ticket.view.all" in access.permissions:
        return statement
    visible_ids = visible_ticket_query(db, actor, include_archived=True).with_only_columns(Ticket.id)
    linked_problem_ids = select(ProblemTicketLink.problem_id).where(
        ProblemTicketLink.ticket_id.in_(visible_ids)
    )
    return statement.where(
        (Problem.created_by_user_id == actor.id)
        | (Problem.owner_user_id == actor.id)
        | Problem.id.in_(linked_problem_ids)
    )


def _visible_problem(db: Session, actor: User, problem_id: int) -> Problem:
    row = db.scalar(_problem_statement(db, actor).where(Problem.id == problem_id))
    if not row:
        raise NotFoundError("Problem not found or is outside your access scope.")
    return row


@router.get("/service-management/dashboard-cards")
def service_management_dashboard_cards(
    date_from: date | None = None,
    date_to: date | None = None,
    client_id: int | None = None,
    product_id: int | None = None,
    department_id: int | None = None,
    engineer_id: int | None = None,
    team_id: int | None = None,
    country_id: int | None = None,
    zone: str | None = None,
    location_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> dict[str, object]:
    if date_from and date_to and date_from > date_to:
        raise ConflictError("INVALID_DATE_RANGE", "From date must not be after To date.")
    portal = actor.user_type == "CLIENT_PORTAL"
    access = effective_permissions(db, actor)
    tickets = visible_ticket_query(db, actor)
    if client_id is not None:
        tickets = tickets.where(Ticket.client_id == client_id)
    if product_id is not None:
        tickets = tickets.where(Ticket.product_id == product_id)
    if department_id is not None:
        tickets = tickets.where(Ticket.created_by_user_id.in_(select(User.id).where(User.department_id == department_id)))
    if engineer_id is not None:
        tickets = tickets.where(Ticket.assigned_user_id == engineer_id)
    if team_id is not None:
        tickets = tickets.where(or_(Ticket.routed_team_id == team_id, Ticket.assigned_user_id.in_(
            select(SupportTeamMember.user_id).where(SupportTeamMember.team_id == team_id)
        )))
    if country_id is not None or zone or location_id is not None:
        tickets = tickets.join(Client, Client.id == Ticket.client_id).outerjoin(
            Branch, Branch.id == Ticket.branch_id
        ).outerjoin(ClientLocation, ClientLocation.id == func.coalesce(Branch.location_id, Client.primary_location_id))
        for column, value in (
            (func.coalesce(ClientLocation.country_id, Client.country_id), country_id),
            (func.coalesce(ClientLocation.zone, Client.zone), zone),
            (ClientLocation.id, location_id),
        ):
            if value is not None and value != "":
                tickets = tickets.where(column == value)
    scope_tickets = tickets
    visible_ids = scope_tickets.with_only_columns(Ticket.id)
    if date_from:
        tickets = tickets.where(Ticket.created_at >= datetime.combine(date_from, time.min, server_timezone()))
    if date_to:
        tickets = tickets.where(Ticket.created_at < datetime.combine(date_to + timedelta(days=1), time.min, server_timezone()))
    result: dict[str, object] = {}
    for key, code, permission in (
        ("incidents", "INCIDENT", None),
        ("changes", "CHANGE_REQUEST", "change_request.view"),
    ):
        if not portal and permission and permission not in access.permissions:
            continue
        statement = tickets.where(Ticket.ticket_type_id.in_(select(TicketType.id).where(TicketType.code == code)))
        count = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
        ticket_records = list(db.scalars(statement.order_by(Ticket.created_at.desc()).limit(100)))
        result[key] = {"count": count, "records": [
            {"id": row.id, "number": row.ticket_number, "title": row.subject,
             "route": f"/portal/tickets/{row.id}" if portal else
             f"/tickets/{row.id}/change-request" if key == "changes" else f"/tickets/{row.id}"}
            for row in ticket_records
        ]}
    if portal or "problem.view" in access.permissions:
        linked_ids = select(ProblemTicketLink.problem_id).where(ProblemTicketLink.ticket_id.in_(visible_ids))
        problems = _problem_statement(db, actor)
        if portal or any(value is not None and value != "" for value in (
            client_id, product_id, department_id, engineer_id, team_id, country_id, zone, location_id
        )):
            problems = problems.where(Problem.id.in_(linked_ids))
        if date_from:
            problems = problems.where(Problem.created_at >= datetime.combine(date_from, time.min, server_timezone()))
        if date_to:
            problems = problems.where(Problem.created_at < datetime.combine(date_to + timedelta(days=1), time.min, server_timezone()))
        count = db.scalar(select(func.count()).select_from(problems.subquery())) or 0
        if portal:
            affected = scope_tickets.where(Ticket.id.in_(select(ProblemTicketLink.ticket_id).where(
                ProblemTicketLink.problem_id.in_(problems.with_only_columns(Problem.id))
            )))
            problem_records: list[dict[str, object]] = [
                {"id": row.id, "number": row.ticket_number, "title": row.subject,
                 "route": f"/portal/tickets/{row.id}"}
                for row in db.scalars(affected.order_by(Ticket.created_at.desc()).limit(100))
            ]
        else:
            problem_records = [
                {"id": row.id, "number": row.problem_number, "title": row.title,
                 "route": f"/problems/{row.id}"}
                for row in db.scalars(problems.order_by(Problem.created_at.desc()).limit(100))
            ]
        result["problems"] = {"count": count, "records": problem_records}
    return result


def _major_statement(db: Session, actor: User) -> Select[tuple[MajorIncident]]:
    visible_ids = visible_ticket_query(db, actor, include_archived=True).with_only_columns(Ticket.id)
    return select(MajorIncident).where(MajorIncident.primary_ticket_id.in_(visible_ids))


def _visible_major(db: Session, actor: User, incident_id: int) -> MajorIncident:
    row = db.scalar(_major_statement(db, actor).where(MajorIncident.id == incident_id))
    if not row:
        raise NotFoundError("Major Incident not found or is outside your access scope.")
    return row


@router.post("/problems", response_model=ProblemRead, status_code=201)
def create_problem(data: ProblemCreate, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.create"))) -> Problem:
    if data.source_ticket_id is not None:
        _visible_ticket(db, actor, data.source_ticket_id)
    row = Problem(problem_number="PENDING", title=data.title, description=data.description, priority=data.priority, owner_user_id=data.owner_user_id, owner_team_id=data.owner_team_id, product_id=data.product_id, product_module_id=data.product_module_id, environment_id=data.environment_id, created_by_user_id=actor.id)
    db.add(row); db.flush(); row.problem_number = f"PRB{row.id:08d}"
    if data.source_ticket_id is not None:
        db.add(ProblemTicketLink(problem_id=row.id, ticket_id=data.source_ticket_id, link_type="AFFECTED_INCIDENT", linked_by_user_id=actor.id))
    _notify_users(db, actor, {row.owner_user_id}, notification_type="PROBLEM_ASSIGNED", severity="WARNING", title=f"Problem assigned: {row.problem_number}", message=row.title, deep_link=f"/problems/{row.id}", deduplication_key=f"problem-created:{row.id}")
    _audit(db, request, actor, "Problem", row.id, "problem.created", new=data.model_dump())
    db.commit(); db.refresh(row); return row


@router.get("/problems", response_model=list[ProblemRead])
def list_problems(db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.view"))) -> list[Problem]:
    return list(db.scalars(_problem_statement(db, actor).order_by(Problem.updated_at.desc())).all())


@router.get("/problem-portfolio")
def problem_portfolio(
    search: str | None = None,
    problem_status: str | None = Query(default=None, alias="status"),
    priority: str | None = None,
    owner_user_id: int | None = None,
    limit: int = Query(default=250, ge=1, le=1000),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("problem.view")),
) -> list[dict[str, object]]:
    statement = _problem_statement(db, actor)
    if search and search.strip():
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Problem.problem_number.ilike(term),
                Problem.title.ilike(term),
                Problem.description.ilike(term),
            )
        )
    if problem_status:
        statement = statement.where(Problem.status == problem_status)
    if priority:
        statement = statement.where(Problem.priority == priority)
    if owner_user_id is not None:
        statement = statement.where(Problem.owner_user_id == owner_user_id)
    problems = list(db.scalars(statement.order_by(Problem.updated_at.desc()).limit(limit)).all())
    if not problems:
        return []
    problem_ids = [item.id for item in problems]
    ticket_counts: dict[int, int] = {
        problem_id: count
        for problem_id, count in db.execute(
            select(ProblemTicketLink.problem_id, func.count(ProblemTicketLink.id))
            .where(ProblemTicketLink.problem_id.in_(problem_ids))
            .group_by(ProblemTicketLink.problem_id)
        ).all()
    }
    task_rows = db.execute(
        select(ProblemTask.problem_id, ProblemTask.status, ProblemTask.due_at)
        .where(ProblemTask.problem_id.in_(problem_ids))
    ).all()
    task_counts: dict[int, int] = {}
    overdue_counts: dict[int, int] = {}
    now = server_now()
    for problem_id, task_status, due_at in task_rows:
        if task_status not in {"COMPLETED", "CANCELLED"}:
            task_counts[problem_id] = task_counts.get(problem_id, 0) + 1
            comparable_now = now if due_at is None or due_at.tzinfo else now.replace(tzinfo=None)
            if due_at is not None and due_at < comparable_now:
                overdue_counts[problem_id] = overdue_counts.get(problem_id, 0) + 1
    owner_ids = {item.owner_user_id for item in problems if item.owner_user_id is not None}
    owner_names = {
        user_id: full_name
        for user_id, full_name in db.execute(
            select(User.id, User.full_name).where(User.id.in_(owner_ids))
        ).all()
    } if owner_ids else {}
    return [
        {
            "id": item.id,
            "problem_number": item.problem_number,
            "title": item.title,
            "status": item.status,
            "priority": item.priority,
            "owner_user_id": item.owner_user_id,
            "owner_name": owner_names.get(item.owner_user_id),
            "target_resolution_date": item.target_resolution_date,
            "linked_ticket_count": ticket_counts.get(item.id, 0),
            "open_task_count": task_counts.get(item.id, 0),
            "overdue_task_count": overdue_counts.get(item.id, 0),
            "updated_at": item.updated_at,
        }
        for item in problems
    ]


@router.get("/problem-portfolio/summary")
def problem_portfolio_summary(db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.view"))) -> dict[str, object]:
    rows = list(db.scalars(_problem_statement(db, actor)))
    active_states = {"NEW", "INVESTIGATING", "ROOT_CAUSE_IDENTIFIED", "KNOWN_ERROR", "FIX_PROPOSED", "FIX_IMPLEMENTED", "MONITORING"}
    problem_ids = [item.id for item in rows]
    overdue_problem_ids = set(db.scalars(select(ProblemTask.problem_id).where(ProblemTask.problem_id.in_(problem_ids), ProblemTask.status.not_in(["COMPLETED", "CANCELLED"]), ProblemTask.due_at.is_not(None), ProblemTask.due_at < server_now()))) if problem_ids else set()
    by_status: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    for row in rows:
        by_status[row.status] = by_status.get(row.status, 0) + 1
        by_priority[row.priority] = by_priority.get(row.priority, 0) + 1
    return {"total": len(rows), "active": sum(item.status in active_states for item in rows), "known_errors": by_status.get("KNOWN_ERROR", 0), "overdue": len(overdue_problem_ids), "unassigned": sum(item.owner_user_id is None for item in rows), "by_status": by_status, "by_priority": by_priority}


@router.get("/problem-portfolio/export.xlsx")
def export_problem_portfolio(db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.view"))) -> StreamingResponse:
    rows = list(db.scalars(_problem_statement(db, actor).order_by(Problem.updated_at.desc())))
    owner_ids = {item.owner_user_id for item in rows if item.owner_user_id is not None}
    owners = {item.id: item.full_name for item in db.scalars(select(User).where(User.id.in_(owner_ids)))} if owner_ids else {}
    book = Workbook(); sheet = book.active; sheet.title = "Problems"
    headers = ["Problem", "Title", "Status", "Priority", "Owner", "Business Impact", "Root Cause", "Workaround", "Permanent Fix", "Target Resolution", "Created", "Updated"]
    sheet.append(headers)
    for cell in sheet[1]: cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill("solid", fgColor="AD6800")
    for row in rows: sheet.append([row.problem_number, row.title, row.status, row.priority, owners.get(row.owner_user_id, "") if row.owner_user_id is not None else "", row.business_impact or "", row.root_cause_summary or "", row.workaround or "", row.permanent_fix_summary or "", row.target_resolution_date.replace(tzinfo=None) if row.target_resolution_date else "", row.created_at.replace(tzinfo=None), row.updated_at.replace(tzinfo=None)])
    sheet.freeze_panes = "A2"; sheet.auto_filter.ref = f"A1:L{max(1, sheet.max_row)}"
    for column, width in {"A":18,"B":42,"C":24,"D":12,"E":28,"F":45,"G":45,"H":45,"I":45,"J":21,"K":21,"L":21}.items(): sheet.column_dimensions[column].width = width
    stream = io.BytesIO(); book.save(stream); stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=problems.xlsx"})


@router.get("/tickets/{ticket_id}/problems")
def list_ticket_problems(
    ticket_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("problem.view")),
) -> list[dict[str, object]]:
    _visible_ticket(db, actor, ticket_id)
    rows = db.execute(
        select(ProblemTicketLink, Problem)
        .join(Problem, Problem.id == ProblemTicketLink.problem_id)
        .where(ProblemTicketLink.ticket_id == ticket_id)
        .order_by(Problem.updated_at.desc())
    ).all()
    visible_problem_ids = set(db.scalars(_problem_statement(db, actor).with_only_columns(Problem.id)).all())
    return [
        {
            "id": problem.id,
            "problem_number": problem.problem_number,
            "title": problem.title,
            "status": problem.status,
            "priority": problem.priority,
            "link_type": link.link_type,
            "linked_at": link.linked_at,
        }
        for link, problem in rows
        if problem.id in visible_problem_ids
    ]


@router.get("/problems/{problem_id}", response_model=ProblemRead)
def get_problem(problem_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.view"))) -> Problem:
    return _visible_problem(db, actor, problem_id)


@router.patch("/problems/{problem_id}", response_model=ProblemRead)
def update_problem(problem_id: int, data: ProblemUpdate, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.edit"))) -> Problem:
    row = _visible_problem(db, actor, problem_id)
    _version(row.version, data.version)
    changes = data.model_dump(exclude={"version"}, exclude_unset=True)
    if "owner_user_id" in changes or "owner_team_id" in changes:
        _require(db, actor, "problem.assign")
    old = {key: getattr(row, key) for key in changes}
    for key, value in changes.items():
        setattr(row, key, value)
    row.version += 1
    _audit(db, request, actor, "Problem", row.id, "problem.updated", old=old, new={**changes, "version": row.version})
    db.commit(); db.refresh(row); return row


@router.post("/problems/{problem_id}/transition", response_model=ProblemRead)
def transition_problem(problem_id: int, data: Transition, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.edit"))) -> Problem:
    row = _visible_problem(db, actor, problem_id)
    _version(row.version, data.version); validate_transition(PROBLEM_TRANSITIONS, row.status, data.status, data.reason)
    if data.status == "CLOSED":
        _require(db, actor, "problem.close")
        root_cause_summary = (data.root_cause_summary or row.root_cause_summary or "").strip()
        permanent_fix_summary = (data.permanent_fix_summary or row.permanent_fix_summary or "").strip()
        if not root_cause_summary or not permanent_fix_summary:
            raise ConflictError("PROBLEM_CLOSURE_NOT_READY", "Root cause and permanent-fix summaries are required before closing a Problem.")
        row.root_cause_summary = root_cause_summary
        row.permanent_fix_summary = permanent_fix_summary
    elif row.status in {"CLOSED", "CANCELLED"}:
        _require(db, actor, "problem.reopen")
    elif data.status in {"ROOT_CAUSE_IDENTIFIED", "KNOWN_ERROR"}:
        _require(db, actor, "problem.identify_root_cause")
    old = row.status; row.status = data.status; row.version += 1
    if data.status == "CLOSED": row.closed_at = server_now()
    db.add(ProblemStatusHistory(problem_id=row.id, from_status=old, to_status=data.status, reason=data.reason, changed_by_user_id=actor.id))
    _notify_users(db, actor, {row.created_by_user_id, row.owner_user_id}, notification_type="PROBLEM_STATUS_UPDATED", severity="WARNING" if data.status in {"CANCELLED", "INVESTIGATING"} else "INFO", title=f"Problem status updated: {row.problem_number}", message=f"{old.replace('_', ' ').title()} → {data.status.replace('_', ' ').title()}", deep_link=f"/problems/{row.id}", deduplication_key=f"problem-status:{row.id}:version:{row.version}")
    _audit(db, request, actor, "Problem", row.id, "problem.transitioned", old={"status": old}, new={"status": data.status, "version": row.version}, reason=data.reason)
    db.commit(); db.refresh(row); return row


@router.post("/problems/{problem_id}/tickets", status_code=201)
def link_problem_ticket(problem_id: int, data: ProblemTicketLinks, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.link_ticket"))) -> dict[str, object]:
    row = _visible_problem(db, actor, problem_id); _version(row.version, data.version)
    if data.link_type not in {"AFFECTED_INCIDENT", "EVIDENCE", "RELATED"}: raise ConflictError("INVALID_PROBLEM_LINK_TYPE", "Unsupported Problem ticket link type.")
    ticket_ids = sorted(set(data.ticket_ids + ([data.ticket_id] if data.ticket_id is not None else [])))
    if not ticket_ids: raise ConflictError("PROBLEM_TICKETS_REQUIRED", "Select at least one ticket to link.")
    for ticket_id in ticket_ids: _visible_ticket(db, actor, ticket_id)
    existing_ids = set(db.scalars(select(ProblemTicketLink.ticket_id).where(ProblemTicketLink.problem_id == row.id, ProblemTicketLink.ticket_id.in_(ticket_ids), ProblemTicketLink.link_type == data.link_type)).all())
    if existing_ids: raise ConflictError("PROBLEM_TICKET_ALREADY_LINKED", "One or more selected ticket relationships already exist.")
    links = [ProblemTicketLink(problem_id=row.id, ticket_id=ticket_id, link_type=data.link_type, linked_by_user_id=actor.id) for ticket_id in ticket_ids]
    db.add_all(links); row.version += 1; db.flush()
    _audit(db, request, actor, "Problem", row.id, "problem.tickets_linked", new={"link_ids": [link.id for link in links], "ticket_ids": ticket_ids, "link_type": data.link_type, "version": row.version})
    db.commit(); return {"ids": [link.id for link in links], "problem_version": row.version}


@router.delete("/problems/{problem_id}/tickets/{ticket_id}")
def unlink_problem_ticket(problem_id: int, ticket_id: int, data: VersionedUnlink, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.link_ticket"))) -> dict[str, int]:
    row = _visible_problem(db, actor, problem_id); _version(row.version, data.version); _visible_ticket(db, actor, ticket_id)
    links = list(db.scalars(select(ProblemTicketLink).where(ProblemTicketLink.problem_id == row.id, ProblemTicketLink.ticket_id == ticket_id)).all())
    if not links: raise NotFoundError("Problem ticket link not found.")
    link_types = [link.link_type for link in links]
    for link in links: db.delete(link)
    row.version += 1
    _audit(db, request, actor, "Problem", row.id, "problem.ticket_unlinked", old={"ticket_id": ticket_id, "link_types": link_types}, new={"version": row.version}, reason=data.reason)
    db.commit(); return {"problem_version": row.version}


@router.post("/problems/{problem_id}/root-causes")
def set_problem_root_causes(problem_id: int, data: RootCauseLinks, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.identify_root_cause"))) -> dict[str, object]:
    row = _visible_problem(db, actor, problem_id); _version(row.version, data.version)
    existing = list(db.scalars(select(ProblemRootCause).where(ProblemRootCause.problem_id == row.id)).all())
    old_ids = [item.root_cause_id for item in existing]
    for item in existing: db.delete(item)
    root_cause_ids = sorted(set(data.root_cause_ids))
    for root_cause_id in root_cause_ids: db.add(ProblemRootCause(problem_id=row.id, root_cause_id=root_cause_id))
    row.version += 1
    _audit(db, request, actor, "Problem", row.id, "problem.root_causes_updated", old={"root_cause_ids": old_ids}, new={"root_cause_ids": root_cause_ids, "version": row.version})
    db.commit(); return {"root_cause_ids": root_cause_ids, "problem_version": row.version}


@router.post("/problems/{problem_id}/changes", status_code=201)
def link_problem_change(problem_id: int, data: VersionedLink, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.edit"))) -> dict[str, object]:
    row = _visible_problem(db, actor, problem_id); _version(row.version, data.version); _change_ticket(db, actor, data.ticket_id)
    if data.link_type not in {"PERMANENT_FIX", "RELATED"}: raise ConflictError("INVALID_CHANGE_LINK_TYPE", "Unsupported Problem change link type.")
    existing = db.scalar(select(ProblemChangeLink).where(ProblemChangeLink.problem_id == row.id, ProblemChangeLink.change_ticket_id == data.ticket_id, ProblemChangeLink.link_type == data.link_type))
    if existing: raise ConflictError("PROBLEM_CHANGE_ALREADY_LINKED", "This Change relationship already exists.")
    link = ProblemChangeLink(problem_id=row.id, change_ticket_id=data.ticket_id, link_type=data.link_type, linked_by_user_id=actor.id)
    db.add(link); row.version += 1; db.flush()
    _audit(db, request, actor, "Problem", row.id, "problem.change_linked", new={"link_id": link.id, "ticket_id": data.ticket_id, "link_type": data.link_type, "version": row.version})
    db.commit(); return {"id": link.id, "problem_version": row.version}


@router.get("/problems/{problem_id}/tickets")
def list_problem_tickets(problem_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.view"))) -> list[dict[str, object]]:
    _visible_problem(db, actor, problem_id)
    rows = db.execute(
        select(ProblemTicketLink, Ticket)
        .join(Ticket, Ticket.id == ProblemTicketLink.ticket_id)
        .where(ProblemTicketLink.problem_id == problem_id)
        .order_by(ProblemTicketLink.linked_at.desc())
    ).all()
    return [{"id": link.id, "ticket_id": ticket.id, "ticket_number": ticket.ticket_number, "subject": ticket.subject, "link_type": link.link_type, "linked_at": link.linked_at} for link, ticket in rows]


@router.get("/problems/{problem_id}/root-causes")
def list_problem_root_causes(problem_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.view"))) -> list[dict[str, object]]:
    _visible_problem(db, actor, problem_id)
    rows = db.execute(
        select(RootCause.id, RootCause.name)
        .join(ProblemRootCause, ProblemRootCause.root_cause_id == RootCause.id)
        .where(ProblemRootCause.problem_id == problem_id)
        .order_by(RootCause.name)
    ).all()
    return [{"id": root_cause_id, "name": name} for root_cause_id, name in rows]


@router.get("/problems/{problem_id}/changes")
def list_problem_changes(problem_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.view"))) -> list[dict[str, object]]:
    _visible_problem(db, actor, problem_id)
    rows = db.execute(
        select(ProblemChangeLink, Ticket)
        .join(Ticket, Ticket.id == ProblemChangeLink.change_ticket_id)
        .where(ProblemChangeLink.problem_id == problem_id)
        .order_by(ProblemChangeLink.linked_at.desc())
    ).all()
    return [{"id": link.id, "ticket_id": ticket.id, "ticket_number": ticket.ticket_number, "subject": ticket.subject, "link_type": link.link_type, "linked_at": link.linked_at} for link, ticket in rows]


@router.get("/problems/{problem_id}/knowledge")
def list_problem_knowledge(problem_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.view"))) -> list[dict[str, object]]:
    _visible_problem(db, actor, problem_id)
    rows = db.execute(
        select(ProblemKnowledgeLink, Article)
        .join(Article, Article.id == ProblemKnowledgeLink.article_id)
        .where(ProblemKnowledgeLink.problem_id == problem_id)
        .order_by(ProblemKnowledgeLink.linked_at.desc())
    ).all()
    return [{"article_id": article.id, "title": article.title, "status": article.status, "link_type": link.link_type, "linked_at": link.linked_at} for link, article in rows]


@router.get("/problems/{problem_id}/history")
def list_problem_history(problem_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.view"))) -> list[dict[str, object]]:
    _visible_problem(db, actor, problem_id)
    rows = db.execute(
        select(ProblemStatusHistory, User.full_name)
        .join(User, User.id == ProblemStatusHistory.changed_by_user_id)
        .where(ProblemStatusHistory.problem_id == problem_id)
        .order_by(ProblemStatusHistory.changed_at.desc())
    ).all()
    return [{"id": item.id, "from_status": item.from_status, "to_status": item.to_status, "reason": item.reason, "changed_by_user_id": item.changed_by_user_id, "changed_by_name": full_name, "changed_at": item.changed_at} for item, full_name in rows]


@router.get("/problems/{problem_id}/comments")
def list_problem_comments(problem_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.view"))) -> list[dict[str, object]]:
    _visible_problem(db, actor, problem_id)
    rows = db.scalars(select(ProblemComment).where(ProblemComment.problem_id == problem_id).order_by(ProblemComment.created_at)).all()
    return [{"id": item.id, "body": item.body, "is_internal": item.is_internal, "author_user_id": item.author_user_id, "created_at": item.created_at} for item in rows]


@router.post("/problems/{problem_id}/comments", status_code=201)
def add_problem_comment(problem_id: int, data: ProblemCommentCreate, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.edit"))) -> dict[str, object]:
    row = _visible_problem(db, actor, problem_id)
    comment = ProblemComment(problem_id=row.id, body=data.body.strip(), is_internal=data.is_internal, author_user_id=actor.id)
    db.add(comment); db.flush()
    _audit(db, request, actor, "Problem", row.id, "problem.comment_added", new={"comment_id": comment.id, "is_internal": comment.is_internal})
    db.commit(); return {"id": comment.id, "created_at": comment.created_at}


@router.get("/problems/{problem_id}/tasks")
def list_problem_tasks(problem_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.view"))) -> list[dict[str, object]]:
    _visible_problem(db, actor, problem_id)
    rows = db.scalars(select(ProblemTask).where(ProblemTask.problem_id == problem_id).order_by(ProblemTask.created_at)).all()
    return [{"id": item.id, "title": item.title, "description": item.description, "assigned_user_id": item.assigned_user_id, "status": item.status, "due_at": item.due_at, "completed_at": item.completed_at, "version": item.version} for item in rows]


@router.post("/problems/{problem_id}/tasks", status_code=201)
def create_problem_task(problem_id: int, data: ProblemTaskCreate, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.edit"))) -> dict[str, object]:
    row = _visible_problem(db, actor, problem_id)
    task = ProblemTask(problem_id=row.id, title=data.title.strip(), description=data.description, assigned_user_id=data.assigned_user_id, due_at=data.due_at, created_by_user_id=actor.id)
    db.add(task); db.flush()
    _audit(db, request, actor, "Problem", row.id, "problem.task_created", new={"task_id": task.id, **data.model_dump()})
    db.commit(); return {"id": task.id, "status": task.status, "version": task.version}


@router.patch("/problems/{problem_id}/tasks/{task_id}")
def update_problem_task(problem_id: int, task_id: int, data: ProblemTaskUpdate, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.edit"))) -> dict[str, object]:
    row = _visible_problem(db, actor, problem_id)
    task = db.scalar(select(ProblemTask).where(ProblemTask.id == task_id, ProblemTask.problem_id == row.id))
    if not task: raise NotFoundError("Problem task not found.")
    _version(task.version, data.version); old = task.status; task.status = data.status; task.version += 1
    task.completed_at = server_now() if data.status == "COMPLETED" else None
    _audit(db, request, actor, "ProblemTask", task.id, "problem.task_status_changed", old={"status": old}, new={"status": task.status, "version": task.version})
    db.commit(); return {"id": task.id, "status": task.status, "completed_at": task.completed_at, "version": task.version}


@router.post("/problems/{problem_id}/knowledge", status_code=201)
def link_problem_knowledge(problem_id: int, data: ProblemKnowledgeCreate, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.publish_known_error"))) -> dict[str, object]:
    row = _visible_problem(db, actor, problem_id); _version(row.version, data.version)
    article = db.get(Article, data.article_id)
    if not article: raise NotFoundError("Knowledge article not found.")
    if data.link_type in {"WORKAROUND", "PERMANENT_FIX"} and article.status != "PUBLISHED":
        raise ConflictError("PUBLISHED_KNOWLEDGE_REQUIRED", "Only published Knowledge articles can be used as an approved workaround or permanent fix.")
    existing = db.get(ProblemKnowledgeLink, (row.id, article.id))
    if existing: raise ConflictError("PROBLEM_KNOWLEDGE_ALREADY_LINKED", "This Knowledge article is already linked.")
    db.add(ProblemKnowledgeLink(problem_id=row.id, article_id=article.id, link_type=data.link_type, linked_by_user_id=actor.id)); row.version += 1
    _audit(db, request, actor, "Problem", row.id, "problem.knowledge_linked", new={"article_id": article.id, "link_type": data.link_type, "version": row.version})
    db.commit(); return {"article_id": article.id, "problem_version": row.version}


@router.post("/problems/{problem_id}/knowledge/draft", status_code=201)
def create_problem_knowledge_draft(problem_id: int, data: ProblemKnowledgeDraftCreate, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.publish_known_error"))) -> dict[str, object]:
    _require(db, actor, "knowledge.create")
    row = _visible_problem(db, actor, problem_id); _version(row.version, data.version)
    content = row.workaround if data.content_type == "WORKAROUND" else row.permanent_fix_summary
    if not (content or "").strip():
        raise ConflictError("PROBLEM_KNOWLEDGE_CONTENT_REQUIRED", f"The Problem {data.content_type.lower().replace('_', ' ')} is empty.")
    cause_ids = list(db.scalars(select(ProblemRootCause.root_cause_id).where(ProblemRootCause.problem_id == row.id)).all())
    title = (data.title or f"{data.content_type.replace('_', ' ').title()}: {row.title}").strip()
    article = Article(
        title=title,
        summary=(row.known_error_summary or row.root_cause_summary or content or "")[:1000],
        body=content or "",
        category="Problem Management",
        tags=f"problem,{row.problem_number.lower()}",
        status="DRAFT",
        client_visible=False,
        visibility="INTERNAL",
        owner_user_id=actor.id,
        resolution_summary_template=content if data.content_type == "WORKAROUND" else None,
        root_cause_ids_json=json.dumps(cause_ids),
        resolution_service_ids_json="[]",
        permanent_fix_summary_template=content if data.content_type == "PERMANENT_FIX" else None,
        permanent_fix_status="IMPLEMENTED" if data.content_type == "PERMANENT_FIX" else None,
    )
    db.add(article); db.flush()
    if row.product_id: db.add(ArticleProductLink(article_id=article.id, product_id=row.product_id))
    if row.product_module_id: db.add(ArticleModuleLink(article_id=article.id, product_module_id=row.product_module_id))
    db.add(ArticleVersion(article_id=article.id, version=1, title=article.title, summary=article.summary, body=article.body, status=article.status, changed_by_user_id=actor.id))
    db.add(ProblemKnowledgeLink(problem_id=row.id, article_id=article.id, link_type=data.content_type, linked_by_user_id=actor.id))
    row.version += 1
    _audit(db, request, actor, "Problem", row.id, "problem.knowledge_draft_created", new={"article_id": article.id, "content_type": data.content_type, "version": row.version})
    db.commit(); return {"article_id": article.id, "status": article.status, "problem_version": row.version}


@router.get("/problems/{problem_id}/attachments")
def list_problem_attachments(problem_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.view"))) -> list[dict[str, object]]:
    _visible_problem(db, actor, problem_id)
    rows = db.scalars(select(ProblemAttachment).where(ProblemAttachment.problem_id == problem_id).order_by(ProblemAttachment.created_at)).all()
    return [{"id": item.id, "original_filename": item.original_filename, "content_type": item.content_type, "size_bytes": item.size_bytes, "sha256": item.sha256, "scan_status": item.scan_status, "uploaded_by_user_id": item.uploaded_by_user_id, "created_at": item.created_at} for item in rows]


@router.post("/problems/{problem_id}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_problem_attachment(problem_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), settings: Settings = Depends(get_settings), actor: User = Depends(require_permission("problem.edit"))) -> dict[str, object]:
    row = _visible_problem(db, actor, problem_id)
    attachment = await save_problem_attachment(db, row, actor, file, settings)
    return {"id": attachment.id, "original_filename": attachment.original_filename, "content_type": attachment.content_type, "size_bytes": attachment.size_bytes, "sha256": attachment.sha256, "scan_status": attachment.scan_status, "created_at": attachment.created_at, "problem_version": row.version}


@router.get("/problems/{problem_id}/attachments/{attachment_id}/download")
def download_problem_attachment(problem_id: int, attachment_id: int, db: Session = Depends(get_db), settings: Settings = Depends(get_settings), actor: User = Depends(require_permission("problem.view"))) -> FileResponse:
    _visible_problem(db, actor, problem_id)
    attachment = db.scalar(select(ProblemAttachment).where(ProblemAttachment.id == attachment_id, ProblemAttachment.problem_id == problem_id))
    if not attachment: raise NotFoundError("Problem attachment not found.")
    return FileResponse(problem_attachment_path(attachment, settings), media_type=attachment.content_type, filename=attachment.original_filename, headers={"X-Content-Type-Options": "nosniff"})


@router.post("/tickets/{ticket_id}/major-incident", response_model=MajorIncidentRead, status_code=201)
def declare_major_incident(ticket_id: int, data: MajorIncidentCreate, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("major_incident.declare"))) -> MajorIncident:
    ticket = _visible_ticket(db, actor, ticket_id)
    ticket_type = db.get(TicketType, ticket.ticket_type_id)
    if not ticket_type or ticket_type.code != "INCIDENT": raise ConflictError("INCIDENT_TICKET_REQUIRED", "Only an Incident ticket can be declared as a Major Incident.")
    existing = db.scalar(select(MajorIncident).where(MajorIncident.primary_ticket_id == ticket_id))
    if existing: return existing
    row = MajorIncident(major_incident_number="PENDING", primary_ticket_id=ticket_id, severity=data.severity, incident_commander_user_id=data.incident_commander_user_id, technical_owner_user_id=data.technical_owner_user_id, communication_owner_user_id=data.communication_owner_user_id, detected_at=data.detected_at, business_impact=data.business_impact, affected_users=data.affected_users, current_status_summary=data.current_status_summary, next_update_at=data.next_update_at, created_by_user_id=actor.id)
    db.add(row); db.flush(); row.major_incident_number = f"MI{row.id:08d}"
    db.add(MajorIncidentTicketLink(major_incident_id=row.id, ticket_id=ticket_id, link_type="PRIMARY", linked_by_user_id=actor.id))
    db.add(MajorIncidentClientScope(major_incident_id=row.id, client_id=ticket.client_id))
    if ticket.product_id: db.add(MajorIncidentProductScope(major_incident_id=row.id, product_id=ticket.product_id))
    if ticket.product_module_id: db.add(MajorIncidentModuleScope(major_incident_id=row.id, product_module_id=ticket.product_module_id))
    if ticket.service_id: db.add(MajorIncidentServiceScope(major_incident_id=row.id, service_id=ticket.service_id))
    if ticket.environment_id: db.add(MajorIncidentEnvironmentScope(major_incident_id=row.id, environment_id=ticket.environment_id))
    _notify_users(db, actor, {row.incident_commander_user_id, row.technical_owner_user_id, row.communication_owner_user_id, ticket.created_by_user_id, ticket.assigned_user_id}, notification_type="MAJOR_INCIDENT_DECLARED", severity="CRITICAL" if row.severity == "SEV1" else "WARNING", title=f"Major Incident declared: {row.major_incident_number}", message=f"{row.severity}: {ticket.subject}", deep_link=f"/major-incidents/{row.id}", deduplication_key=f"major-incident-declared:{row.id}")
    _audit(db, request, actor, "MajorIncident", row.id, "major_incident.declared", new={"ticket_id": ticket_id, **data.model_dump()})
    db.commit(); db.refresh(row); return row


@router.get("/major-incidents", response_model=list[MajorIncidentRead])
def list_major_incidents(db: Session = Depends(get_db), actor: User = Depends(require_permission("major_incident.view"))) -> list[MajorIncident]:
    return list(db.scalars(_major_statement(db, actor).order_by(MajorIncident.declared_at.desc())).all())


@router.get("/major-incident-portfolio")
def major_incident_portfolio(
    search: str | None = None,
    incident_status: str | None = Query(default=None, alias="status"),
    severity: str | None = None,
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("major_incident.view")),
) -> list[dict[str, object]]:
    statement = (
        _major_statement(db, actor)
        .join(Ticket, Ticket.id == MajorIncident.primary_ticket_id)
        .join(Client, Client.id == Ticket.client_id)
    )
    if incident_status:
        statement = statement.where(MajorIncident.status == incident_status)
    if severity:
        statement = statement.where(MajorIncident.severity == severity)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        statement = statement.where(or_(MajorIncident.major_incident_number.ilike(pattern), Ticket.ticket_number.ilike(pattern), Ticket.subject.ilike(pattern), Client.name.ilike(pattern)))
    incidents = list(db.scalars(statement.order_by(MajorIncident.declared_at.desc()).limit(limit)).all())
    ticket_ids = [item.primary_ticket_id for item in incidents]
    tickets = {item.id: item for item in db.scalars(select(Ticket).where(Ticket.id.in_(ticket_ids)))} if ticket_ids else {}
    client_ids = {item.client_id for item in tickets.values()}
    clients = {item.id: item.name for item in db.scalars(select(Client).where(Client.id.in_(client_ids)))} if client_ids else {}
    commander_ids = {item.incident_commander_user_id for item in incidents}
    commanders = {item.id: item.full_name for item in db.scalars(select(User).where(User.id.in_(commander_ids)))} if commander_ids else {}
    incident_ids = [item.id for item in incidents]
    affected_counts = dict(db.execute(select(MajorIncidentTicketLink.major_incident_id, func.count(MajorIncidentTicketLink.id)).where(MajorIncidentTicketLink.major_incident_id.in_(incident_ids)).group_by(MajorIncidentTicketLink.major_incident_id)).tuples().all()) if incident_ids else {}
    problem_counts = dict(db.execute(select(MajorIncidentProblemLink.major_incident_id, func.count(MajorIncidentProblemLink.problem_id)).where(MajorIncidentProblemLink.major_incident_id.in_(incident_ids)).group_by(MajorIncidentProblemLink.major_incident_id)).tuples().all()) if incident_ids else {}
    return [{"id": item.id, "major_incident_number": item.major_incident_number, "primary_ticket_id": item.primary_ticket_id, "ticket_number": tickets[item.primary_ticket_id].ticket_number, "subject": tickets[item.primary_ticket_id].subject, "client_name": clients.get(tickets[item.primary_ticket_id].client_id), "severity": item.severity, "status": item.status, "commander_name": commanders.get(item.incident_commander_user_id), "current_status_summary": item.current_status_summary, "next_update_at": item.next_update_at, "declared_at": item.declared_at, "affected_ticket_count": affected_counts.get(item.id, 0), "problem_count": problem_counts.get(item.id, 0)} for item in incidents]


@router.get("/major-incident-portfolio/summary")
def major_incident_portfolio_summary(db: Session = Depends(get_db), actor: User = Depends(require_permission("major_incident.view"))) -> dict[str, object]:
    rows = list(db.scalars(_major_statement(db, actor)))
    active_states = {"DECLARED", "RESPONSE_ACTIVE", "SERVICE_RESTORED", "MONITORING", "POST_INCIDENT_REVIEW"}
    now = server_now(); by_status: dict[str, int] = {}; by_severity: dict[str, int] = {}
    for row in rows:
        by_status[row.status] = by_status.get(row.status, 0) + 1; by_severity[row.severity] = by_severity.get(row.severity, 0) + 1
    return {"total": len(rows), "active": sum(item.status in active_states for item in rows), "active_sev1": sum(item.status in active_states and item.severity == "SEV1" for item in rows), "updates_overdue": sum(item.status in active_states and item.next_update_at is not None and item.next_update_at < now for item in rows), "awaiting_pir": by_status.get("POST_INCIDENT_REVIEW", 0), "by_status": by_status, "by_severity": by_severity}


@router.get("/major-incident-portfolio/export.xlsx")
def export_major_incident_portfolio(db: Session = Depends(get_db), actor: User = Depends(require_permission("major_incident.view"))) -> StreamingResponse:
    rows = list(db.scalars(_major_statement(db, actor).order_by(MajorIncident.declared_at.desc())))
    ticket_ids = [item.primary_ticket_id for item in rows]; tickets = {item.id: item for item in db.scalars(select(Ticket).where(Ticket.id.in_(ticket_ids)))} if ticket_ids else {}
    commander_ids = {item.incident_commander_user_id for item in rows}; commanders = {item.id: item.full_name for item in db.scalars(select(User).where(User.id.in_(commander_ids)))} if commander_ids else {}
    book = Workbook(); sheet = book.active; sheet.title = "Major Incidents"
    headers = ["Major Incident", "Primary Ticket", "Subject", "Severity", "Status", "Commander", "Business Impact", "Affected Users", "Current Status", "Next Update", "Declared", "Restored", "Closed"]
    sheet.append(headers)
    for cell in sheet[1]: cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill("solid", fgColor="C62828")
    for row in rows:
        ticket = tickets.get(row.primary_ticket_id); sheet.append([row.major_incident_number, ticket.ticket_number if ticket else "", ticket.subject if ticket else "", row.severity, row.status, commanders.get(row.incident_commander_user_id, ""), row.business_impact, row.affected_users or "", row.current_status_summary, row.next_update_at.replace(tzinfo=None) if row.next_update_at else "", row.declared_at.replace(tzinfo=None), row.service_restored_at.replace(tzinfo=None) if row.service_restored_at else "", row.closed_at.replace(tzinfo=None) if row.closed_at else ""])
    sheet.freeze_panes = "A2"; sheet.auto_filter.ref = f"A1:M{max(1, sheet.max_row)}"
    for column, width in {"A":18,"B":18,"C":42,"D":12,"E":24,"F":28,"G":45,"H":28,"I":45,"J":21,"K":21,"L":21,"M":21}.items(): sheet.column_dimensions[column].width = width
    stream = io.BytesIO(); book.save(stream); stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=major_incidents.xlsx"})


@router.get("/major-incidents/{incident_id}", response_model=MajorIncidentRead)
def get_major_incident(incident_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("major_incident.view"))) -> MajorIncident:
    return _visible_major(db, actor, incident_id)


@router.patch("/major-incidents/{incident_id}", response_model=MajorIncidentRead)
def update_major_incident(incident_id: int, data: MajorIncidentEdit, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("major_incident.command"))) -> MajorIncident:
    row = _visible_major(db, actor, incident_id); _version(row.version, data.version)
    changes = data.model_dump(exclude={"version"}, exclude_unset=True)
    old = {key: getattr(row, key) for key in changes}
    for key, value in changes.items(): setattr(row, key, value)
    row.version += 1
    _audit(db, request, actor, "MajorIncident", row.id, "major_incident.updated", old=old, new={**changes, "version": row.version})
    db.commit(); db.refresh(row); return row


@router.post("/major-incidents/{incident_id}/transition", response_model=MajorIncidentRead)
def transition_major_incident(incident_id: int, data: Transition, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("major_incident.command"))) -> MajorIncident:
    row = _visible_major(db, actor, incident_id)
    _version(row.version, data.version); validate_transition(MAJOR_INCIDENT_TRANSITIONS, row.status, data.status, data.reason)
    if data.status == "SERVICE_RESTORED": _require(db, actor, "major_incident.restore_service")
    elif data.status == "CLOSED":
        _require(db, actor, "major_incident.close")
        if not row.post_incident_review or not row.resolution_summary:
            raise ConflictError("MAJOR_INCIDENT_CLOSURE_NOT_READY", "Resolution summary and post-incident review are required before closure.")
    linked_problem_count = db.scalar(select(func.count()).select_from(MajorIncidentProblemLink).where(MajorIncidentProblemLink.major_incident_id == row.id)) or 0
    if data.status == "SERVICE_RESTORED" and not linked_problem_count and not (row.problem_follow_up_owner_user_id and row.problem_follow_up_due_at):
        raise ConflictError("MAJOR_INCIDENT_PROBLEM_REQUIRED", "Link a Problem or record a Problem owner and due date before restoring service.")
    if data.status == "POST_INCIDENT_REVIEW" and not linked_problem_count:
        raise ConflictError("MAJOR_INCIDENT_LINKED_PROBLEM_REQUIRED", "A linked Problem is required before completing post-incident review.")
    old = row.status; row.status = data.status; row.version += 1
    now = server_now()
    if data.status == "SERVICE_RESTORED": row.service_restored_at = now
    if data.status == "MONITORING": row.monitoring_started_at = now
    if data.status == "CLOSED": row.closed_at = now
    primary_ticket = db.get(Ticket, row.primary_ticket_id)
    _notify_users(db, actor, {row.incident_commander_user_id, row.technical_owner_user_id, row.communication_owner_user_id, row.created_by_user_id, primary_ticket.created_by_user_id if primary_ticket else None, primary_ticket.assigned_user_id if primary_ticket else None}, notification_type="MAJOR_INCIDENT_STATUS_UPDATED", severity="CRITICAL" if data.status == "RESPONSE_ACTIVE" else "INFO", title=f"Major Incident status: {row.major_incident_number}", message=f"{old.replace('_', ' ').title()} → {data.status.replace('_', ' ').title()}", deep_link=f"/major-incidents/{row.id}", deduplication_key=f"major-incident-status:{row.id}:version:{row.version}")
    _audit(db, request, actor, "MajorIncident", row.id, "major_incident.transitioned", old={"status": old}, new={"status": data.status, "version": row.version}, reason=data.reason)
    db.commit(); db.refresh(row); return row


@router.post("/major-incidents/{incident_id}/updates", status_code=201)
def publish_major_update(incident_id: int, data: MajorUpdateCreate, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("major_incident.publish_update"))) -> dict[str, object]:
    row = _visible_major(db, actor, incident_id)
    if data.update_type == "CLIENT" and not (data.client_message or "").strip(): raise ConflictError("CLIENT_MESSAGE_REQUIRED", "A client-safe message is required for a client update.")
    update = MajorIncidentUpdate(major_incident_id=row.id, update_type=data.update_type, internal_message=data.internal_message, client_message=data.client_message, published_by_user_id=actor.id)
    db.add(update); db.flush()
    primary_ticket = db.get(Ticket, row.primary_ticket_id)
    _notify_users(db, actor, {row.incident_commander_user_id, row.technical_owner_user_id, row.communication_owner_user_id, primary_ticket.created_by_user_id if primary_ticket else None, primary_ticket.assigned_user_id if primary_ticket else None}, notification_type="MAJOR_INCIDENT_UPDATE", severity="CRITICAL" if row.severity == "SEV1" else "WARNING", title=f"Major Incident update: {row.major_incident_number}", message=(data.client_message or data.internal_message or "Status update published")[:1000], deep_link=f"/major-incidents/{row.id}", deduplication_key=f"major-incident-update:{update.id}")
    _audit(db, request, actor, "MajorIncident", row.id, "major_incident.update_published", new={"update_id": update.id, "update_type": update.update_type})
    db.commit(); return {"id": update.id, "published_at": update.published_at}


@router.get("/major-incidents/{incident_id}/updates")
def list_major_updates(incident_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("major_incident.view"))) -> list[dict[str, object]]:
    _visible_major(db, actor, incident_id)
    rows = db.execute(select(MajorIncidentUpdate, User.full_name).join(User, User.id == MajorIncidentUpdate.published_by_user_id).where(MajorIncidentUpdate.major_incident_id == incident_id).order_by(MajorIncidentUpdate.published_at.desc())).all()
    return [{"id": item.id, "update_type": item.update_type, "internal_message": item.internal_message, "client_message": item.client_message, "published_by_user_id": item.published_by_user_id, "published_by_name": full_name, "published_at": item.published_at} for item, full_name in rows]


@router.get("/major-incidents/{incident_id}/tickets")
def list_major_tickets(incident_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("major_incident.view"))) -> list[dict[str, object]]:
    _visible_major(db, actor, incident_id)
    rows = db.execute(select(MajorIncidentTicketLink, Ticket).join(Ticket, Ticket.id == MajorIncidentTicketLink.ticket_id).where(MajorIncidentTicketLink.major_incident_id == incident_id).order_by(MajorIncidentTicketLink.linked_at)).all()
    return [{"id": link.id, "ticket_id": ticket.id, "ticket_number": ticket.ticket_number, "subject": ticket.subject, "link_type": link.link_type, "linked_at": link.linked_at} for link, ticket in rows]


@router.get("/major-incidents/{incident_id}/scopes")
def get_major_scopes(incident_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("major_incident.view"))) -> dict[str, list[int]]:
    _visible_major(db, actor, incident_id)
    return {
        "client_ids": list(db.scalars(select(MajorIncidentClientScope.client_id).where(MajorIncidentClientScope.major_incident_id == incident_id))),
        "product_ids": list(db.scalars(select(MajorIncidentProductScope.product_id).where(MajorIncidentProductScope.major_incident_id == incident_id))),
        "product_module_ids": list(db.scalars(select(MajorIncidentModuleScope.product_module_id).where(MajorIncidentModuleScope.major_incident_id == incident_id))),
        "service_ids": list(db.scalars(select(MajorIncidentServiceScope.service_id).where(MajorIncidentServiceScope.major_incident_id == incident_id))),
        "environment_ids": list(db.scalars(select(MajorIncidentEnvironmentScope.environment_id).where(MajorIncidentEnvironmentScope.major_incident_id == incident_id))),
    }


@router.get("/major-incidents/{incident_id}/problems")
def list_major_problems(incident_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("major_incident.view"))) -> list[dict[str, object]]:
    _visible_major(db, actor, incident_id)
    rows = db.execute(select(MajorIncidentProblemLink, Problem).join(Problem, Problem.id == MajorIncidentProblemLink.problem_id).where(MajorIncidentProblemLink.major_incident_id == incident_id).order_by(MajorIncidentProblemLink.linked_at.desc())).all()
    return [{"id": problem.id, "problem_number": problem.problem_number, "title": problem.title, "status": problem.status, "priority": problem.priority, "linked_at": link.linked_at} for link, problem in rows]


@router.post("/major-incidents/{incident_id}/tickets", status_code=201)
def link_major_ticket(incident_id: int, data: VersionedLink, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("major_incident.link_ticket"))) -> dict[str, object]:
    row = _visible_major(db, actor, incident_id); _version(row.version, data.version); _visible_ticket(db, actor, data.ticket_id)
    if data.link_type not in {"AFFECTED", "DUPLICATE"}: raise ConflictError("INVALID_MAJOR_INCIDENT_LINK_TYPE", "Only affected or duplicate tickets can be added.")
    if data.ticket_id == row.primary_ticket_id: raise ConflictError("PRIMARY_TICKET_IMMUTABLE", "The primary Major Incident ticket cannot be added again.")
    existing = db.scalar(select(MajorIncidentTicketLink).where(MajorIncidentTicketLink.major_incident_id == row.id, MajorIncidentTicketLink.ticket_id == data.ticket_id))
    if existing: raise ConflictError("MAJOR_INCIDENT_TICKET_ALREADY_LINKED", "This ticket is already linked to the Major Incident.")
    link = MajorIncidentTicketLink(major_incident_id=row.id, ticket_id=data.ticket_id, link_type=data.link_type, linked_by_user_id=actor.id)
    db.add(link); row.version += 1; db.flush()
    _audit(db, request, actor, "MajorIncident", row.id, "major_incident.ticket_linked", new={"link_id": link.id, "ticket_id": data.ticket_id, "link_type": data.link_type, "version": row.version})
    db.commit(); return {"id": link.id, "major_incident_version": row.version}


@router.delete("/major-incidents/{incident_id}/tickets/{ticket_id}")
def unlink_major_ticket(incident_id: int, ticket_id: int, data: VersionedUnlink, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("major_incident.link_ticket"))) -> dict[str, int]:
    row = _visible_major(db, actor, incident_id); _version(row.version, data.version); _visible_ticket(db, actor, ticket_id)
    if ticket_id == row.primary_ticket_id: raise ConflictError("PRIMARY_TICKET_IMMUTABLE", "The primary ticket cannot be removed from a Major Incident.")
    link = db.scalar(select(MajorIncidentTicketLink).where(MajorIncidentTicketLink.major_incident_id == row.id, MajorIncidentTicketLink.ticket_id == ticket_id))
    if not link: raise NotFoundError("Major Incident ticket link not found.")
    old_type = link.link_type; db.delete(link); row.version += 1
    _audit(db, request, actor, "MajorIncident", row.id, "major_incident.ticket_unlinked", old={"ticket_id": ticket_id, "link_type": old_type}, new={"version": row.version}, reason=data.reason)
    db.commit(); return {"major_incident_version": row.version}


@router.put("/major-incidents/{incident_id}/scopes")
def replace_major_scopes(incident_id: int, data: MajorIncidentScopes, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("major_incident.command"))) -> dict[str, object]:
    row = _visible_major(db, actor, incident_id); _version(row.version, data.version)
    specifications = (
        (MajorIncidentClientScope, "client_id", data.client_ids),
        (MajorIncidentProductScope, "product_id", data.product_ids),
        (MajorIncidentModuleScope, "product_module_id", data.product_module_ids),
        (MajorIncidentServiceScope, "service_id", data.service_ids),
        (MajorIncidentEnvironmentScope, "environment_id", data.environment_ids),
    )
    old: dict[str, list[int]] = {}
    for model, field, values in specifications:
        current = list(db.scalars(select(model).where(model.major_incident_id == row.id)).all())
        old[field] = [getattr(item, field) for item in current]
        for item in current: db.delete(item)
        for value in sorted(set(values)): db.add(model(major_incident_id=row.id, **{field: value}))
    row.version += 1
    new = {field: sorted(set(values)) for _, field, values in specifications}
    _audit(db, request, actor, "MajorIncident", row.id, "major_incident.scopes_updated", old=old, new={**new, "version": row.version})
    db.commit(); return {**new, "major_incident_version": row.version}


@router.post("/major-incidents/{incident_id}/problem", status_code=201)
def link_major_problem(incident_id: int, data: MajorProblemLinkCreate, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("major_incident.command"))) -> dict[str, object]:
    row = _visible_major(db, actor, incident_id); _version(row.version, data.version)
    problem = _visible_problem(db, actor, data.problem_id)
    existing = db.get(MajorIncidentProblemLink, (row.id, problem.id))
    if existing: raise ConflictError("MAJOR_INCIDENT_PROBLEM_ALREADY_LINKED", "This Problem is already linked to the Major Incident.")
    db.add(MajorIncidentProblemLink(major_incident_id=row.id, problem_id=problem.id, linked_by_user_id=actor.id))
    row.problem_follow_up_owner_user_id = None; row.problem_follow_up_due_at = None; row.version += 1
    _audit(db, request, actor, "MajorIncident", row.id, "major_incident.problem_linked", new={"problem_id": problem.id, "version": row.version})
    db.commit(); return {"problem_id": problem.id, "major_incident_version": row.version}


@router.post("/major-incidents/{incident_id}/problem-commitment")
def set_major_problem_commitment(incident_id: int, data: MajorProblemCommitment, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("major_incident.command"))) -> dict[str, object]:
    row = _visible_major(db, actor, incident_id); _version(row.version, data.version)
    if data.due_at <= server_now(): raise ConflictError("PROBLEM_DUE_DATE_INVALID", "The Problem follow-up due date must be in the future.")
    row.problem_follow_up_owner_user_id = data.owner_user_id; row.problem_follow_up_due_at = data.due_at; row.version += 1
    _audit(db, request, actor, "MajorIncident", row.id, "major_incident.problem_committed", new={"owner_user_id": data.owner_user_id, "due_at": data.due_at, "version": row.version})
    db.commit(); return {"owner_user_id": data.owner_user_id, "due_at": data.due_at, "major_incident_version": row.version}


@router.post("/major-incidents/{incident_id}/problem/create", status_code=201)
def create_major_problem(incident_id: int, data: ProblemCreate, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("problem.create"))) -> dict[str, object]:
    incident = _visible_major(db, actor, incident_id)
    _require(db, actor, "major_incident.command")
    problem = Problem(problem_number="PENDING", title=data.title, description=data.description, priority=data.priority, owner_user_id=data.owner_user_id, owner_team_id=data.owner_team_id, product_id=data.product_id, product_module_id=data.product_module_id, environment_id=data.environment_id, business_impact=incident.business_impact, created_by_user_id=actor.id)
    db.add(problem); db.flush(); problem.problem_number = f"PRB{problem.id:08d}"
    db.add(ProblemTicketLink(problem_id=problem.id, ticket_id=incident.primary_ticket_id, link_type="AFFECTED_INCIDENT", linked_by_user_id=actor.id))
    db.add(MajorIncidentProblemLink(major_incident_id=incident.id, problem_id=problem.id, linked_by_user_id=actor.id))
    incident.problem_follow_up_owner_user_id = None; incident.problem_follow_up_due_at = None; incident.version += 1
    _audit(db, request, actor, "Problem", problem.id, "problem.created_from_major_incident", new={"major_incident_id": incident.id, "primary_ticket_id": incident.primary_ticket_id})
    _audit(db, request, actor, "MajorIncident", incident.id, "major_incident.problem_created", new={"problem_id": problem.id, "version": incident.version})
    db.commit(); return {"problem_id": problem.id, "problem_number": problem.problem_number, "major_incident_version": incident.version}


def _change_ticket(db: Session, actor: User, ticket_id: int) -> Ticket:
    ticket = _visible_ticket(db, actor, ticket_id); kind = db.get(TicketType, ticket.ticket_type_id)
    if not kind or kind.code != "CHANGE_REQUEST": raise ConflictError("CHANGE_REQUEST_TICKET_REQUIRED", "Structured change details can only be attached to a Change Request ticket.")
    return ticket


@router.get("/change-requests")
def list_change_requests(
    change_status: str | None = Query(default=None, max_length=40),
    client_id: int | None = None,
    product_id: int | None = None,
    product_module_id: int | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    search: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=250),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("change_request.view")),
) -> list[dict[str, object]]:
    visible_ids = visible_ticket_query(db, actor, include_archived=True).with_only_columns(Ticket.id)
    query = (
        select(ChangeRequestDetail, Ticket, TicketStatus, Client)
        .select_from(Ticket)
        .join(TicketType, TicketType.id == Ticket.ticket_type_id)
        .outerjoin(ChangeRequestDetail, ChangeRequestDetail.ticket_id == Ticket.id)
        .join(TicketStatus, TicketStatus.id == Ticket.status_id)
        .join(Client, Client.id == Ticket.client_id)
        .where(Ticket.id.in_(visible_ids), TicketType.code == "CHANGE_REQUEST")
        .order_by(func.coalesce(ChangeRequestDetail.updated_at, Ticket.updated_at).desc(), Ticket.id.desc())
        .limit(limit)
    )
    if change_status:
        query = query.where(
            ChangeRequestDetail.id.is_(None)
            if change_status == "DETAILS_REQUIRED"
            else ChangeRequestDetail.change_status == change_status
        )
    if client_id is not None: query = query.where(Ticket.client_id == client_id)
    if product_id is not None: query = query.where(Ticket.product_id == product_id)
    if product_module_id is not None: query = query.where(Ticket.product_module_id == product_module_id)
    if created_from is not None:
        query = query.where(Ticket.created_at >= datetime.combine(created_from, time.min, tzinfo=server_timezone()))
    if created_to is not None:
        query = query.where(Ticket.created_at < datetime.combine(created_to + timedelta(days=1), time.min, tzinfo=server_timezone()))
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.where(or_(Ticket.ticket_number.ilike(pattern), Ticket.subject.ilike(pattern), Client.name.ilike(pattern), ChangeRequestDetail.purpose.ilike(pattern)))
    rows = db.execute(query).all()
    return [{"id": change.id if change else None, "ticket_id": ticket.id, "ticket_number": ticket.ticket_number, "subject": ticket.subject, "client_name": client.name, "ticket_status": ticket_status.code, "change_status": change.change_status if change else "DETAILS_REQUIRED", "request_kind": change.request_kind if change else None, "requested_priority": change.requested_priority if change else ticket.priority, "risk_level": change.risk_level if change else None, "target_release": change.target_release if change else None, "planned_start_at": change.planned_start_at if change else None, "planned_end_at": change.planned_end_at if change else None, "updated_at": change.updated_at if change else ticket.updated_at} for change, ticket, ticket_status, client in rows]


@router.get("/change-requests/filter-options")
def change_request_filter_options(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("change_request.view")),
) -> dict[str, object]:
    visible_ids = visible_ticket_query(db, actor, include_archived=True).with_only_columns(Ticket.id)
    base = select(Ticket).join(TicketType, TicketType.id == Ticket.ticket_type_id).where(
        Ticket.id.in_(visible_ids), TicketType.code == "CHANGE_REQUEST"
    )
    tickets = list(db.scalars(base))
    client_ids = {ticket.client_id for ticket in tickets}
    product_ids = {ticket.product_id for ticket in tickets if ticket.product_id}
    module_ids = {ticket.product_module_id for ticket in tickets if ticket.product_module_id}
    clients = list(db.scalars(select(Client).where(Client.id.in_(client_ids)).order_by(Client.name))) if client_ids else []
    products = list(db.scalars(select(Product).where(Product.id.in_(product_ids)).order_by(Product.name))) if product_ids else []
    modules = list(db.scalars(select(ProductModule).where(ProductModule.id.in_(module_ids)).order_by(ProductModule.name))) if module_ids else []
    return {
        "clients": [{"id": row.id, "name": row.name} for row in clients],
        "products": [{"id": row.id, "name": row.name} for row in products],
        "modules": [{"id": row.id, "product_id": row.product_id, "name": row.name} for row in modules],
    }


@router.get("/change-requests/summary")
def change_request_summary(
    change_status: str | None = Query(default=None, max_length=40),
    client_id: int | None = None,
    product_id: int | None = None,
    product_module_id: int | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    search: str | None = Query(default=None, max_length=200),
    db: Session = Depends(get_db), actor: User = Depends(require_permission("change_request.view")),
) -> dict[str, object]:
    visible_ids = visible_ticket_query(db, actor, include_archived=True).with_only_columns(Ticket.id)
    statement = select(Ticket, ChangeRequestDetail).join(TicketType, TicketType.id == Ticket.ticket_type_id).outerjoin(ChangeRequestDetail, ChangeRequestDetail.ticket_id == Ticket.id).join(Client, Client.id == Ticket.client_id).where(Ticket.id.in_(visible_ids), TicketType.code == "CHANGE_REQUEST")
    if change_status: statement = statement.where(ChangeRequestDetail.id.is_(None) if change_status == "DETAILS_REQUIRED" else ChangeRequestDetail.change_status == change_status)
    if client_id is not None: statement = statement.where(Ticket.client_id == client_id)
    if product_id is not None: statement = statement.where(Ticket.product_id == product_id)
    if product_module_id is not None: statement = statement.where(Ticket.product_module_id == product_module_id)
    if created_from is not None: statement = statement.where(Ticket.created_at >= datetime.combine(created_from, time.min, tzinfo=server_timezone()))
    if created_to is not None: statement = statement.where(Ticket.created_at < datetime.combine(created_to + timedelta(days=1), time.min, tzinfo=server_timezone()))
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        statement = statement.where(or_(Ticket.ticket_number.ilike(pattern), Ticket.subject.ilike(pattern), Client.name.ilike(pattern), ChangeRequestDetail.purpose.ilike(pattern)))
    rows = db.execute(statement).all()
    changes = [change for _, change in rows if change is not None]
    details_required = len(rows) - len(changes)
    active = {"SUBMITTED", "UNDER_ASSESSMENT", "AWAITING_APPROVAL", "APPROVED", "PLANNED", "IMPLEMENTING", "VALIDATION"}
    now = server_now()
    by_status: dict[str, int] = {}
    for row in changes:
        by_status[row.change_status] = by_status.get(row.change_status, 0) + 1
    if details_required:
        by_status["DETAILS_REQUIRED"] = details_required
    return {
        "total": len(rows),
        "active": details_required + sum(row.change_status in active for row in changes),
        "details_required": details_required,
        "awaiting_approval": by_status.get("AWAITING_APPROVAL", 0),
        "implementing": by_status.get("IMPLEMENTING", 0),
        "validation": by_status.get("VALIDATION", 0),
        "overdue": sum(row.change_status in active and row.planned_end_at is not None and row.planned_end_at < now for row in changes),
        "by_status": by_status,
    }


@router.get("/change-requests/export.xlsx")
def export_change_requests(db: Session = Depends(get_db), actor: User = Depends(require_permission("change_request.view"))) -> StreamingResponse:
    visible_ids = visible_ticket_query(db, actor, include_archived=True).with_only_columns(Ticket.id)
    rows = db.execute(select(ChangeRequestDetail, Ticket, TicketStatus, Client).select_from(Ticket).join(TicketType, TicketType.id == Ticket.ticket_type_id).outerjoin(ChangeRequestDetail, ChangeRequestDetail.ticket_id == Ticket.id).join(TicketStatus, TicketStatus.id == Ticket.status_id).join(Client, Client.id == Ticket.client_id).where(Ticket.id.in_(visible_ids), TicketType.code == "CHANGE_REQUEST").order_by(func.coalesce(ChangeRequestDetail.updated_at, Ticket.updated_at).desc())).all()
    book = Workbook(); sheet = book.active; sheet.title = "Change Requests"
    headers = ["Ticket", "Client", "Subject", "Ticket Status", "Change Status", "Request Kind", "Priority", "Risk", "Target Release", "Planned Start", "Planned End", "Purpose"]
    sheet.append(headers)
    for cell in sheet[1]: cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill("solid", fgColor="3949AB")
    for change, ticket, ticket_status, client in rows:
        sheet.append([ticket.ticket_number, client.name, ticket.subject, ticket_status.code, change.change_status if change else "DETAILS_REQUIRED", change.request_kind if change else "", change.requested_priority if change else ticket.priority, change.risk_level or "" if change else "", change.target_release or "" if change else "", change.planned_start_at.replace(tzinfo=None) if change and change.planned_start_at else "", change.planned_end_at.replace(tzinfo=None) if change and change.planned_end_at else "", change.purpose if change else ""])
    sheet.freeze_panes = "A2"; sheet.auto_filter.ref = f"A1:L{max(1, sheet.max_row)}"
    for column, width in {"A":18,"B":28,"C":45,"D":18,"E":22,"F":28,"G":12,"H":12,"I":18,"J":21,"K":21,"L":55}.items(): sheet.column_dimensions[column].width = width
    stream = io.BytesIO(); book.save(stream); stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=change_requests.xlsx"})


@router.get("/tickets/{ticket_id}/change-request", response_model=ChangeRead)
def get_change(ticket_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("change_request.view"))) -> ChangeRequestDetail:
    _change_ticket(db, actor, ticket_id); row = db.scalar(select(ChangeRequestDetail).where(ChangeRequestDetail.ticket_id == ticket_id))
    if not row: raise NotFoundError("This legacy Change Request does not yet have structured details.")
    return row


@router.get("/tickets/{ticket_id}/change-request/history")
def get_change_history(ticket_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("change_request.view"))) -> list[dict[str, object]]:
    _change_ticket(db, actor, ticket_id); change = db.scalar(select(ChangeRequestDetail).where(ChangeRequestDetail.ticket_id == ticket_id))
    if not change: raise NotFoundError("Structured Change Request details were not found.")
    rows = list(db.scalars(select(ChangeRequestStatusHistory).where(ChangeRequestStatusHistory.change_request_id == change.id).order_by(ChangeRequestStatusHistory.changed_at.desc(), ChangeRequestStatusHistory.id.desc())))
    users = {row.id: row for row in db.scalars(select(User).where(User.id.in_({item.changed_by_user_id for item in rows})))} if rows else {}
    result: list[dict[str, object]] = []
    for item in rows:
        changed_by = users.get(item.changed_by_user_id)
        result.append({"id": item.id, "from_status": item.from_status, "to_status": item.to_status, "reason": item.reason, "changed_by_user_id": item.changed_by_user_id, "changed_by_name": changed_by.full_name if changed_by else None, "changed_at": item.changed_at})
    return result


@router.put("/tickets/{ticket_id}/change-request", response_model=ChangeRead)
def put_change(ticket_id: int, data: ChangeWrite, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("change_request.view"))) -> ChangeRequestDetail:
    ticket = _change_ticket(db, actor, ticket_id); row = db.scalar(select(ChangeRequestDetail).where(ChangeRequestDetail.ticket_id == ticket_id))
    _require(db, actor, "change_request.assess" if row else "change_request.create")
    if row and data.version is None: raise ConflictError("VERSION_REQUIRED", "Version is required when updating structured change details.")
    if row: _version(row.version, data.version or 0); old = {"version": row.version, "purpose": row.purpose}
    else: row = ChangeRequestDetail(ticket_id=ticket_id, request_kind=data.request_kind, purpose=data.purpose, detailed_description=data.detailed_description, business_impact=data.business_impact, expected_result=data.expected_result); db.add(row); old = None
    for key, value in data.model_dump(exclude={"version"}).items(): setattr(row, key, value)
    if old is not None: row.version += 1
    db.flush()
    if old is None:
        _synchronize_change_parent_ticket(db, ticket, row.change_status, actor, None)
    _audit(db, request, actor, "ChangeRequestDetail", row.id, "change_request.updated" if old else "change_request.created", old=old, new=data.model_dump(exclude={"version"}))
    db.commit(); db.refresh(row); return row


@router.post("/tickets/{ticket_id}/change-request/transition", response_model=ChangeRead)
def transition_change(ticket_id: int, data: Transition, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("change_request.view"))) -> ChangeRequestDetail:
    ticket = _change_ticket(db, actor, ticket_id); row = db.scalar(select(ChangeRequestDetail).where(ChangeRequestDetail.ticket_id == ticket_id))
    if not row: raise NotFoundError("Structured Change Request details were not found.")
    _version(row.version, data.version); validate_transition(CHANGE_TRANSITIONS, row.change_status, data.status, data.reason)
    permission = {
        "UNDER_ASSESSMENT": "change_request.assess",
        "AWAITING_APPROVAL": "change_request.assess",
        "APPROVED": "change_request.approve",
        "REJECTED": "change_request.approve",
        "PLANNED": "change_request.plan",
        "PENDING_DEPLOYMENT": "change_request.plan",
        "IMPLEMENTING": "change_request.implement",
        "VALIDATION": "change_request.validate",
        "COMPLETED": "change_request.complete",
        "FAILED": "change_request.implement",
        "ROLLED_BACK": "change_request.rollback",
        "CANCELLED": "change_request.assess",
    }.get(data.status, "change_request.assess")
    _require(db, actor, permission)
    if data.status in {"APPROVED", "REJECTED"}:
        latest_approval = db.scalar(select(ChangeRequestApproval).where(ChangeRequestApproval.change_request_id == row.id).order_by(ChangeRequestApproval.cycle_number.desc(), ChangeRequestApproval.id.desc()))
        if not latest_approval or latest_approval.decision != data.status:
            raise ConflictError("APPROVAL_DECISION_REQUIRED", f"The latest approval cycle must have an immutable {data.status} decision.")
    if data.status == "PLANNED" and not all((row.implementation_plan, row.rollback_plan, row.test_plan, row.planned_start_at, row.planned_end_at)):
        raise ConflictError("CHANGE_PLAN_INCOMPLETE", "Implementation, rollback and test plans with planned dates are required before planning.")
    if data.status == "PENDING_DEPLOYMENT" and not row.deployment_environment:
        raise ConflictError("CHANGE_DEPLOYMENT_ENVIRONMENT_REQUIRED", "Select TEST, STAGING or PRODUCTION before waiting for deployment.")
    if data.status == "IMPLEMENTING" and row.planned_start_at and row.planned_end_at and row.planned_end_at <= row.planned_start_at:
        raise ConflictError("INVALID_CHANGE_WINDOW", "The planned end must be after the planned start.")
    if data.status == "COMPLETED":
        if not (row.deployment_requirements or "").strip():
            raise ConflictError("CHANGE_DEPLOYMENT_REQUIREMENTS_REQUIRED", "Document the deployment requirements before completing the Change.")
        pending_readiness = [
            label for label, value in (
                ("permissions/access", row.permissions_readiness),
                ("training/communication", row.training_readiness),
                ("documentation", row.documentation_readiness),
            ) if value == "PENDING"
        ]
        if pending_readiness:
            raise ConflictError("CHANGE_DEPLOYMENT_READINESS_PENDING", f"Complete or mark not required: {', '.join(pending_readiness)}.")
        if row.implementation_outcome != "SUCCESSFUL":
            raise ConflictError("CHANGE_IMPLEMENTATION_OUTCOME_REQUIRED", "A successful implementation outcome is required before completing the Change.")
        if row.actual_implemented_at is None:
            raise ConflictError("CHANGE_IMPLEMENTATION_DATE_REQUIRED", "The actual implementation date is required before completing the Change.")
        if not (row.validation_result or "").strip():
            raise ConflictError("CHANGE_VALIDATION_REQUIRED", "Validation results are required before completing the Change.")
    old = row.change_status; row.change_status = data.status; row.version += 1
    _synchronize_change_parent_ticket(db, ticket, data.status, actor, data.reason)
    db.add(ChangeRequestStatusHistory(change_request_id=row.id, from_status=old, to_status=data.status, reason=data.reason, changed_by_user_id=actor.id))
    recipients = {ticket.created_by_user_id}
    if ticket.assigned_user_id:
        recipients.add(ticket.assigned_user_id)
    recipients.discard(actor.id)
    for recipient_id in recipients:
        db.add(Notification(recipient_user_id=recipient_id, notification_type="CHANGE_STATUS_UPDATED", severity="WARNING" if data.status in {"REJECTED", "FAILED", "ROLLED_BACK", "CANCELLED"} else "INFO", title=f"Change status updated: {ticket.ticket_number}", message=f"{old.replace('_', ' ').title()} → {data.status.replace('_', ' ').title()}", deep_link=f"/tickets/{ticket.id}/change-request", deduplication_key=f"change-status:{row.id}:version:{row.version}:user:{recipient_id}"))
    _audit(db, request, actor, "ChangeRequestDetail", row.id, "change_request.transitioned", old={"status": old}, new={"status": data.status, "version": row.version}, reason=data.reason)
    db.commit(); db.refresh(row); return row


@router.post("/tickets/{ticket_id}/change-request/approvals", status_code=201)
def request_approval(ticket_id: int, data: ApprovalRequest, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("change_request.assess"))) -> dict[str, object]:
    ticket = _change_ticket(db, actor, ticket_id); row = db.scalar(select(ChangeRequestDetail).where(ChangeRequestDetail.ticket_id == ticket_id))
    if not row: raise NotFoundError("Structured Change Request details were not found.")
    _version(row.version, data.version)
    approver = db.get(User, data.approver_user_id)
    if not approver or not approver.is_active or approver.user_type != "EMPLOYEE":
        raise NotFoundError("The selected approver does not exist or is inactive.")
    if "change_request.approve" not in effective_permissions(db, approver).permissions:
        raise ConflictError("INVALID_CHANGE_APPROVER", "The selected user does not have Change Request approval permission.")
    if db.scalar(select(ChangeRequestApproval.id).where(ChangeRequestApproval.change_request_id == row.id, ChangeRequestApproval.decision == "PENDING")):
        raise ConflictError("CHANGE_APPROVAL_PENDING", "Decide the current approval request before creating another cycle.")
    cycle = (db.scalar(select(func.max(ChangeRequestApproval.cycle_number)).where(ChangeRequestApproval.change_request_id == row.id)) or 0) + 1
    approval = ChangeRequestApproval(change_request_id=row.id, approval_stage=data.approval_stage, cycle_number=cycle, approver_user_id=data.approver_user_id)
    db.add(approval); db.flush()
    db.add(Notification(recipient_user_id=approver.id, notification_type="CHANGE_APPROVAL_REQUESTED", severity="WARNING", title=f"Change approval required: {ticket.ticket_number}", message=f"{actor.full_name} requested {data.approval_stage} approval.", deep_link=f"/tickets/{ticket_id}/change-request", deduplication_key=f"change-approval-request:{approval.id}:user:{approver.id}"))
    _audit(db, request, actor, "ChangeRequestDetail", row.id, "change_request.approval_requested", new={"approval_id": approval.id, "cycle": cycle})
    db.commit(); return {"id": approval.id, "cycle_number": cycle, "decision": approval.decision}


@router.get("/tickets/{ticket_id}/change-request/approvals")
def list_change_approvals(ticket_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("change_request.view"))) -> list[dict[str, object]]:
    _change_ticket(db, actor, ticket_id); change = db.scalar(select(ChangeRequestDetail).where(ChangeRequestDetail.ticket_id == ticket_id))
    if not change: raise NotFoundError("Structured Change Request details were not found.")
    rows = list(db.scalars(select(ChangeRequestApproval).where(ChangeRequestApproval.change_request_id == change.id).order_by(ChangeRequestApproval.cycle_number.desc(), ChangeRequestApproval.id.desc())))
    users = {row.id: row for row in db.scalars(select(User).where(User.id.in_({item.approver_user_id for item in rows})))} if rows else {}
    result: list[dict[str, object]] = []
    for item in rows:
        approver = users.get(item.approver_user_id)
        result.append({"id": item.id, "approval_stage": item.approval_stage, "cycle_number": item.cycle_number, "approver_user_id": item.approver_user_id, "approver_name": approver.full_name if approver else None, "decision": item.decision, "comment": item.comment, "requested_at": item.requested_at, "decided_at": item.decided_at, "version": item.version})
    return result


@router.get("/tickets/{ticket_id}/change-request/approval-candidates")
def list_change_approval_candidates(ticket_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("change_request.assess"))) -> list[dict[str, object]]:
    _change_ticket(db, actor, ticket_id)
    users = list(
        db.scalars(
            select(User)
            .where(User.is_active == true(), User.user_type == "EMPLOYEE")
            .order_by(User.full_name)
        )
    )
    return [{"id": user.id, "full_name": user.full_name, "username": user.username} for user in users if "change_request.approve" in effective_permissions(db, user).permissions]


@router.post("/change-request-approvals/{approval_id}/decision")
def decide_approval(approval_id: int, data: ApprovalDecision, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("change_request.approve"))) -> dict[str, object]:
    row = db.get(ChangeRequestApproval, approval_id)
    if not row: raise NotFoundError("Approval request not found.")
    if row.approver_user_id != actor.id: raise ConflictError("APPROVER_MISMATCH", "Only the selected approver can record this decision.")
    _version(row.version, data.version)
    if row.decision != "PENDING": raise ConflictError("APPROVAL_IMMUTABLE", "This approval decision is immutable; request a new approval cycle.")
    row.decision = data.decision; row.comment = data.comment; row.decided_at = server_now(); row.version += 1
    change = db.get(ChangeRequestDetail, row.change_request_id)
    ticket = db.get(Ticket, change.ticket_id) if change else None
    if ticket:
        recipient_id = ticket.assigned_user_id or ticket.created_by_user_id
        if recipient_id != actor.id:
            db.add(Notification(recipient_user_id=recipient_id, notification_type="CHANGE_APPROVAL_DECIDED", severity="INFO" if data.decision == "APPROVED" else "WARNING", title=f"Change approval {data.decision.lower()}: {ticket.ticket_number}", message=data.comment, deep_link=f"/tickets/{ticket.id}/change-request", deduplication_key=f"change-approval-decision:{row.id}:{data.decision}:user:{recipient_id}"))
    _audit(db, request, actor, "ChangeRequestApproval", row.id, "change_request.approval_decided", new={"decision": row.decision}, reason=data.comment)
    db.commit(); return {"id": row.id, "decision": row.decision, "decided_at": row.decided_at, "version": row.version}
