import hashlib
import json
import secrets
from typing import Any, cast

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import case, delete, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.api.dependencies import current_user
from app.core.clock import server_now
from app.core.config import Settings, get_settings
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import Client
from app.modules.iam.models import AuditLog, Department, User
from app.modules.iam.service import effective_permissions
from app.modules.internal_operations.models import InternalOperation
from app.modules.notifications.models import EventOutbox, Notification
from app.modules.tickets.models import Ticket
from app.modules.tickets.service import create_ticket
from app.modules.visits.models import ClientVisitOccurrence
from app.modules.work_assignments.attachments import store_evidence
from app.modules.work_assignments.models import (
    WorkAssignment,
    WorkAssignmentAssignee,
    WorkAssignmentClient,
    WorkAssignmentEvent,
    WorkAssignmentEvidence,
    WorkAssignmentLink,
    WorkAssignmentShare,
)
from app.modules.work_assignments.schemas import (
    AssignmentCreate,
    AssignmentRead,
    AssignmentUpdate,
    ConversionWrite,
    ShareCreate,
    ShareRead,
    TicketConversionWrite,
    TransitionWrite,
)

router = APIRouter(prefix="/work-assignments", tags=["work assignments"])
public_router = APIRouter(prefix="/public/work-assignments", tags=["public work assignments"])
OPEN_STATUSES = {"ASSIGNED", "ACCEPTED", "IN_PROGRESS", "BLOCKED", "AWAITING_REVIEW", "RETURNED"}
TRANSITIONS = {
    "ACCEPT": ({"ASSIGNED"}, "ACCEPTED"),
    "START": ({"ASSIGNED", "ACCEPTED", "RETURNED"}, "IN_PROGRESS"),
    "BLOCK": ({"ACCEPTED", "IN_PROGRESS", "RETURNED"}, "BLOCKED"),
    "RESUME": ({"BLOCKED"}, "IN_PROGRESS"),
    "SUBMIT": ({"IN_PROGRESS", "RETURNED"}, "AWAITING_REVIEW"),
    "APPROVE": ({"AWAITING_REVIEW"}, "COMPLETED"),
    "RETURN": ({"AWAITING_REVIEW"}, "RETURNED"),
    "COMPLETE": ({"IN_PROGRESS", "RETURNED"}, "COMPLETED"),
    "CANCEL": (OPEN_STATUSES, "CANCELLED"),
    "REOPEN": ({"COMPLETED", "CANCELLED"}, "ASSIGNED"),
}


def _permissions(db: Session, actor: User) -> set[str]:
    return set(effective_permissions(db, actor).permissions)


def _assignee_ids(db: Session, assignment_id: int) -> set[int]:
    return set(db.scalars(select(WorkAssignmentAssignee.user_id).where(WorkAssignmentAssignee.assignment_id == assignment_id)))


def _can_view(db: Session, actor: User, row: WorkAssignment) -> bool:
    permissions = _permissions(db, actor)
    if "work_assignment.view.all" in permissions:
        return True
    if row.created_by_user_id == actor.id or row.owner_user_id == actor.id or actor.id in _assignee_ids(db, row.id):
        return True
    return bool("work_assignment.view.department" in permissions and actor.department_id and actor.department_id == row.department_id)


def _get(db: Session, actor: User, assignment_id: int) -> WorkAssignment:
    row = db.get(WorkAssignment, assignment_id)
    if not row or not _can_view(db, actor, row):
        raise NotFoundError("Work assignment was not found in your scope.")
    return row


def _serialize(db: Session, row: WorkAssignment) -> AssignmentRead:
    assignees = db.execute(select(WorkAssignmentAssignee, User.full_name).join(User, User.id == WorkAssignmentAssignee.user_id).where(WorkAssignmentAssignee.assignment_id == row.id)).all()
    clients = db.execute(select(WorkAssignmentClient, Client.name).join(Client, Client.id == WorkAssignmentClient.client_id).where(WorkAssignmentClient.assignment_id == row.id)).all()
    links = list(db.scalars(select(WorkAssignmentLink).where(WorkAssignmentLink.assignment_id == row.id)))
    evidence = list(db.scalars(select(WorkAssignmentEvidence).where(WorkAssignmentEvidence.assignment_id == row.id).order_by(WorkAssignmentEvidence.created_at.desc())))
    ticket_ids = [item.target_id for item in links if item.target_type == "TICKET"]
    ticket_labels: dict[int, str | None] = {
        ticket_id: ticket_number
        for ticket_id, ticket_number in db.execute(
            select(Ticket.id, Ticket.ticket_number).where(Ticket.id.in_(ticket_ids or [-1]))
        ).all()
    }
    payload = {column.name: getattr(row, column.name) for column in WorkAssignment.__table__.columns}
    payload["context"] = json.loads(row.context_json or "{}")
    payload.update(
        assignees=[{"user_id": item.user_id, "name": name, "role": item.role, "contribution_percent": item.contribution_percent} for item, name in assignees],
        clients=[{"client_id": item.client_id, "name": name, "status": item.status, "result_summary": item.result_summary} for item, name in clients],
        links=[{"target_type": item.target_type, "target_id": item.target_id, "relation_type": item.relation_type, "label": ticket_labels.get(item.target_id)} for item in links],
        evidence=[{"id": item.id, "evidence_type": item.evidence_type, "note": item.note, "original_filename": item.original_filename, "content_type": item.content_type, "size_bytes": item.size_bytes, "uploaded_by_user_id": item.uploaded_by_user_id, "created_at": item.created_at} for item in evidence],
    )
    return AssignmentRead.model_validate(payload)


def _event(db: Session, row: WorkAssignment, actor_id: int | None, event_type: str, old_status: str | None = None, detail: str | None = None) -> None:
    db.add(WorkAssignmentEvent(assignment_id=row.id, actor_user_id=actor_id, event_type=event_type, from_status=old_status, to_status=row.status, detail=detail))
    db.add(AuditLog(actor_user_id=actor_id, entity_type="work_assignment", entity_id=str(row.id), action=f"work_assignment.{event_type.casefold()}", new_values_json=f'{{"status":"{row.status}","version":{row.version}}}'))


def _notify(db: Session, user_id: int, row: WorkAssignment, event: str) -> None:
    db.add(Notification(recipient_user_id=user_id, notification_type="WORK_ASSIGNMENT", severity="WARNING" if row.priority in {"HIGH", "CRITICAL"} else "INFO", title=row.title, message=f"Work assignment {event}.", deep_link=f"/work-assignments?assignment_id={row.id}", deduplication_key=f"work-assignment:{row.id}:{event}:{row.version}:{user_id}"))


def _queue_assignment_email(db: Session, row: WorkAssignment, user_ids: set[int], event: str) -> None:
    if not user_ids:
        return
    db.add(EventOutbox(
        event_type="WORK_ASSIGNMENT_EMAIL",
        aggregate_type="WorkAssignment",
        aggregate_id=str(row.id),
        deduplication_key=f"work-assignment-email:{row.id}:{event}:{row.version}",
        payload_json=json.dumps({
            "recipient_user_ids": sorted(user_ids),
            "subject": f"[Support Hub] Task {event}: {row.title}",
            "body": f"You have been assigned a Support Hub task.\n\nTask: {row.title}\nPriority: {row.priority}\nInstructions: {row.description}",
            "deep_link": f"/work-assignments?assignment_id={row.id}",
        }),
    ))


@router.get("", response_model=list[AssignmentRead])
def list_assignments(
    scope: str = Query(default="MINE", pattern="^(MINE|CREATED|TEAM|QUEUE|ALL)$"),
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> list[AssignmentRead]:
    permissions = _permissions(db, actor)
    assigned = select(WorkAssignmentAssignee.assignment_id).where(WorkAssignmentAssignee.user_id == actor.id)
    query = select(WorkAssignment)
    if scope == "MINE":
        query = query.where(or_(WorkAssignment.owner_user_id == actor.id, WorkAssignment.id.in_(assigned)))
    elif scope == "CREATED":
        query = query.where(WorkAssignment.created_by_user_id == actor.id)
    elif scope in {"TEAM", "QUEUE"}:
        if "work_assignment.view.department" not in permissions:
            raise AuthorizationError()
        query = query.where(WorkAssignment.department_id == actor.department_id)
        if scope == "QUEUE":
            query = query.where(WorkAssignment.owner_user_id.is_(None), WorkAssignment.status == "ASSIGNED")
    elif "work_assignment.view.all" not in permissions:
        raise AuthorizationError()
    if status:
        query = query.where(WorkAssignment.status == status)
    due_date_rank = case((WorkAssignment.due_at.is_(None), 1), else_=0)
    rows = list(
        db.scalars(
            query.order_by(
                due_date_rank,
                WorkAssignment.due_at,
                WorkAssignment.created_at.desc(),
            ).limit(limit)
        )
    )
    return [_serialize(db, row) for row in rows]


@router.get("/eligible-assignees")
def eligible_assignees(
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> list[dict[str, object]]:
    if "work_assignment.create" not in _permissions(db, actor):
        raise AuthorizationError()
    support_departments = select(Department.id).where(
        Department.is_active.in_([True]),
        or_(Department.code.ilike("SUPPORT"), Department.name.ilike("SUPPORT")),
    )
    users = db.scalars(
        select(User)
        .where(
            User.is_active.in_([True]),
            User.user_type == "EMPLOYEE",
            or_(User.department_id.in_(support_departments), User.department.ilike("SUPPORT")),
        )
        .order_by(User.full_name)
    )
    return [{"id": user.id, "full_name": user.full_name} for user in users]


@router.get("/{assignment_id}", response_model=AssignmentRead)
def get_assignment(assignment_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> AssignmentRead:
    return _serialize(db, _get(db, actor, assignment_id))


@router.post("", response_model=AssignmentRead)
def create_assignment(data: AssignmentCreate, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> AssignmentRead:
    if "work_assignment.create" not in _permissions(db, actor):
        raise AuthorizationError()
    user_ids = {item.user_id for item in data.assignees}
    if data.owner_user_id:
        user_ids.add(data.owner_user_id)
    active_users = set(db.scalars(select(User.id).where(User.id.in_(user_ids or [-1]), User.is_active.in_([True]), User.user_type == "EMPLOYEE")))
    if active_users != user_ids:
        raise ConflictError("INVALID_ASSIGNEE", "Every assignee must be an active employee.")
    valid_clients = set(db.scalars(select(Client.id).where(Client.id.in_(set(data.client_ids) or [-1]))))
    if valid_clients != set(data.client_ids):
        raise ConflictError("INVALID_CLIENT", "One or more selected clients do not exist.")
    valid_tickets = set(db.scalars(select(Ticket.id).where(Ticket.id.in_(set(data.related_ticket_ids) or [-1]))))
    if valid_tickets != set(data.related_ticket_ids):
        raise ConflictError("INVALID_TICKET", "One or more selected tickets do not exist.")
    if data.assignment_type == "TICKET_FOLLOW_UP" and not data.related_ticket_ids:
        raise ConflictError("TICKET_REQUIRED", "Select at least one ticket for a ticket follow-up task.")
    values = data.model_dump(exclude={"assignees", "client_ids", "related_ticket_ids", "context"})
    row = WorkAssignment(**values, context_json=json.dumps(data.context), created_by_user_id=actor.id)
    db.add(row); db.flush()
    for item in data.assignees:
        db.add(WorkAssignmentAssignee(assignment_id=row.id, **item.model_dump()))
    for client_id in dict.fromkeys(data.client_ids):
        db.add(WorkAssignmentClient(assignment_id=row.id, client_id=client_id))
    for ticket_id in dict.fromkeys(data.related_ticket_ids):
        db.add(WorkAssignmentLink(assignment_id=row.id, target_type="TICKET", target_id=ticket_id, relation_type="RELATED", created_by_user_id=actor.id))
    _event(db, row, actor.id, "CREATED")
    for user_id in user_ids:
        _notify(db, user_id, row, "assigned")
    _queue_assignment_email(db, row, user_ids, "assigned")
    db.commit(); db.refresh(row)
    return _serialize(db, row)


@router.put("/{assignment_id}", response_model=AssignmentRead)
def update_assignment(
    assignment_id: int,
    data: AssignmentUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> AssignmentRead:
    row = _get(db, actor, assignment_id)
    permissions = _permissions(db, actor)
    if row.created_by_user_id != actor.id and "work_assignment.manage" not in permissions:
        raise AuthorizationError()
    if row.status in {"COMPLETED", "CANCELLED"}:
        raise ConflictError("TERMINAL_ASSIGNMENT", "Completed or cancelled assignments cannot be edited.")
    if row.version != data.expected_version:
        raise ConflictError("WORK_ASSIGNMENT_CONFLICT", "The assignment changed. Refresh and try again.")
    previous_user_ids = _assignee_ids(db, row.id)
    user_ids = {item.user_id for item in data.assignees}
    active_users = set(db.scalars(select(User.id).where(User.id.in_(user_ids or [-1]), User.is_active.in_([True]), User.user_type == "EMPLOYEE")))
    if active_users != user_ids:
        raise ConflictError("INVALID_ASSIGNEE", "Every assignee must be an active employee.")
    valid_clients = set(db.scalars(select(Client.id).where(Client.id.in_(set(data.client_ids) or [-1]))))
    if valid_clients != set(data.client_ids):
        raise ConflictError("INVALID_CLIENT", "One or more selected clients do not exist.")
    valid_tickets = set(db.scalars(select(Ticket.id).where(Ticket.id.in_(set(data.related_ticket_ids) or [-1]))))
    if valid_tickets != set(data.related_ticket_ids):
        raise ConflictError("INVALID_TICKET", "One or more selected tickets do not exist.")
    if data.assignment_type == "TICKET_FOLLOW_UP" and not data.related_ticket_ids:
        raise ConflictError("TICKET_REQUIRED", "Select at least one ticket for a ticket follow-up task.")
    values = data.model_dump(exclude={"expected_version", "assignees", "client_ids", "related_ticket_ids", "context"})
    for key, value in values.items():
        setattr(row, key, value)
    row.context_json = json.dumps(data.context)
    row.version += 1
    db.execute(delete(WorkAssignmentAssignee).where(WorkAssignmentAssignee.assignment_id == row.id))
    db.execute(delete(WorkAssignmentClient).where(WorkAssignmentClient.assignment_id == row.id))
    db.execute(delete(WorkAssignmentLink).where(WorkAssignmentLink.assignment_id == row.id, WorkAssignmentLink.relation_type == "RELATED"))
    for item in data.assignees:
        db.add(WorkAssignmentAssignee(assignment_id=row.id, **item.model_dump()))
    for client_id in dict.fromkeys(data.client_ids):
        db.add(WorkAssignmentClient(assignment_id=row.id, client_id=client_id))
    for ticket_id in dict.fromkeys(data.related_ticket_ids):
        db.add(WorkAssignmentLink(assignment_id=row.id, target_type="TICKET", target_id=ticket_id, relation_type="RELATED", created_by_user_id=actor.id))
    _event(db, row, actor.id, "UPDATED", detail="Assignment details and participants updated.")
    added_user_ids = user_ids - previous_user_ids
    for user_id in added_user_ids:
        _notify(db, user_id, row, "assigned")
    _queue_assignment_email(db, row, added_user_ids, "assigned")
    db.commit(); db.refresh(row)
    return _serialize(db, row)


@router.post("/{assignment_id}/claim", response_model=AssignmentRead)
def claim_assignment(assignment_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> AssignmentRead:
    if "work_assignment.claim" not in _permissions(db, actor):
        raise AuthorizationError()
    row = db.get(WorkAssignment, assignment_id)
    if not row or row.department_id != actor.department_id:
        raise NotFoundError("Queue assignment was not found in your department.")
    result = cast(CursorResult[Any], db.execute(update(WorkAssignment).where(WorkAssignment.id == assignment_id, WorkAssignment.owner_user_id.is_(None), WorkAssignment.status == "ASSIGNED", WorkAssignment.version == row.version).values(owner_user_id=actor.id, accepted_at=server_now(), status="ACCEPTED", version=row.version + 1)))
    if result.rowcount != 1:
        db.rollback()
        raise ConflictError("ASSIGNMENT_ALREADY_CLAIMED", "Another engineer already claimed this assignment.")
    db.add(WorkAssignmentAssignee(assignment_id=row.id, user_id=actor.id, role="OWNER", contribution_percent=100))
    db.flush(); db.refresh(row); _event(db, row, actor.id, "CLAIMED", "ASSIGNED"); db.commit(); db.refresh(row)
    return _serialize(db, row)


@router.post("/{assignment_id}/transition", response_model=AssignmentRead)
def transition_assignment(assignment_id: int, data: TransitionWrite, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> AssignmentRead:
    row = _get(db, actor, assignment_id)
    permissions = _permissions(db, actor)
    assignees = _assignee_ids(db, row.id)
    reviewer_action = data.action in {"APPROVE", "RETURN", "CANCEL", "REOPEN"}
    if reviewer_action and "work_assignment.manage" not in permissions and row.created_by_user_id != actor.id:
        raise AuthorizationError()
    if not reviewer_action and actor.id not in assignees and row.owner_user_id != actor.id and "work_assignment.manage" not in permissions:
        raise AuthorizationError()
    if row.version != data.expected_version:
        raise ConflictError("WORK_ASSIGNMENT_CONFLICT", "The assignment changed. Refresh and try again.")
    if data.action in {"BLOCK", "COMPLETE", "APPROVE"} and not (data.detail or "").strip():
        raise ConflictError("EVIDENCE_REQUIRED", "Written evidence is required to block or close an assignment.")
    allowed, target = TRANSITIONS[data.action]
    if row.status not in allowed:
        raise ConflictError("INVALID_WORK_ASSIGNMENT_TRANSITION", f"{data.action} is not allowed from {row.status}.")
    if data.action == "COMPLETE" and row.requires_review:
        raise ConflictError("REVIEW_REQUIRED", "Submit this assignment for review instead of completing it directly.")
    old = row.status; row.status = target; row.version += 1
    if data.progress_percent is not None: row.progress_percent = data.progress_percent
    if data.actual_minutes is not None: row.actual_minutes = data.actual_minutes
    if data.action == "ACCEPT": row.accepted_at = server_now()
    if data.action in {"START", "RESUME"}: row.started_at = row.started_at or server_now()
    if target == "COMPLETED": row.completed_at, row.progress_percent, row.completion_summary = server_now(), 100, data.detail
    if target == "CANCELLED": row.cancelled_at = server_now()
    _event(db, row, actor.id, data.action, old, data.detail); db.commit(); db.refresh(row)
    return _serialize(db, row)


@router.post("/{assignment_id}/transition-with-evidence", response_model=AssignmentRead)
async def transition_with_evidence(
    assignment_id: int,
    action: str = Form(...),
    expected_version: int = Form(...),
    detail: str = Form(...),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> AssignmentRead:
    normalized_detail = detail.strip()
    if action not in {"BLOCK", "COMPLETE", "APPROVE"}:
        raise ConflictError("INVALID_EVIDENCE_TRANSITION", "Evidence submission is supported for blocked or closed tasks only.")
    if len(normalized_detail) < 3:
        raise ConflictError("EVIDENCE_REQUIRED", "Enter meaningful written evidence before changing the task status.")
    transition_assignment(
        assignment_id,
        TransitionWrite(action=action, expected_version=expected_version, detail=normalized_detail),
        db,
        actor,
    )
    event = db.scalar(select(WorkAssignmentEvent).where(WorkAssignmentEvent.assignment_id == assignment_id, WorkAssignmentEvent.event_type == action).order_by(WorkAssignmentEvent.id.desc()))
    if event is None:
        raise ConflictError("EVIDENCE_EVENT_MISSING", "The task changed, but its evidence event could not be resolved.")
    original = stored = content_type = None
    size = None
    if file and file.filename:
        original, stored, content_type, size = await store_evidence(file, assignment_id, settings)
    db.add(WorkAssignmentEvidence(
        assignment_id=assignment_id,
        event_id=event.id,
        evidence_type="BLOCK" if action == "BLOCK" else "CLOSURE",
        note=normalized_detail,
        original_filename=original,
        stored_filename=stored,
        content_type=content_type,
        size_bytes=size,
        uploaded_by_user_id=actor.id,
    ))
    db.commit()
    row = _get(db, actor, assignment_id)
    return _serialize(db, row)


@router.post("/{assignment_id}/conversion", response_model=AssignmentRead)
def register_conversion(assignment_id: int, data: ConversionWrite, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> AssignmentRead:
    row = _get(db, actor, assignment_id)
    if actor.id not in _assignee_ids(db, row.id) and row.owner_user_id != actor.id and "work_assignment.manage" not in _permissions(db, actor):
        raise AuthorizationError()
    if row.version != data.expected_version:
        raise ConflictError("WORK_ASSIGNMENT_CONFLICT", "The assignment changed. Refresh and try again.")
    target_model = {"TICKET": Ticket, "VISIT": ClientVisitOccurrence, "INTERNAL_OPERATION": InternalOperation}[data.target_type]
    if db.get(target_model, data.target_id) is None:
        raise NotFoundError(f"The target {data.target_type.casefold()} does not exist.")
    db.add(WorkAssignmentLink(assignment_id=row.id, target_type=data.target_type, target_id=data.target_id, relation_type="CONVERTED_TO", created_by_user_id=actor.id))
    row.kpi_source_type, row.kpi_source_id, row.version = data.target_type, data.target_id, row.version + 1
    _event(db, row, actor.id, "CONVERTED", detail=f"{data.target_type}:{data.target_id}"); db.commit(); db.refresh(row)
    return _serialize(db, row)


@router.post("/{assignment_id}/convert-to-ticket", status_code=201)
def convert_assignment_to_ticket(
    assignment_id: int,
    data: TicketConversionWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> dict[str, object]:
    row = _get(db, actor, assignment_id)
    if "ticket.create" not in _permissions(db, actor):
        raise AuthorizationError("You do not have permission to create tickets.")
    if actor.id not in _assignee_ids(db, row.id) and row.owner_user_id != actor.id and "work_assignment.manage" not in _permissions(db, actor):
        raise AuthorizationError()
    if row.version != data.expected_version:
        raise ConflictError("WORK_ASSIGNMENT_CONFLICT", "The assignment changed. Refresh and try again.")
    if row.kpi_source_type != "ASSIGNMENT" or row.kpi_source_id is not None:
        raise ConflictError("WORK_ASSIGNMENT_ALREADY_CONVERTED", "This assignment was already converted.")
    ticket = create_ticket(db, data.ticket, actor, commit=False)
    db.add(WorkAssignmentLink(assignment_id=row.id, target_type="TICKET", target_id=ticket.id, relation_type="CONVERTED_TO", created_by_user_id=actor.id))
    row.kpi_source_type, row.kpi_source_id, row.version = "TICKET", ticket.id, row.version + 1
    _event(db, row, actor.id, "CONVERTED", detail=f"TICKET:{ticket.id}")
    db.commit()
    db.refresh(ticket)
    return {"id": ticket.id, "ticket_number": ticket.ticket_number, "assignment_id": row.id}


@router.post("/{assignment_id}/shares", response_model=ShareRead)
def create_share(assignment_id: int, data: ShareCreate, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> ShareRead:
    row = _get(db, actor, assignment_id)
    if "work_assignment.share" not in _permissions(db, actor) and row.created_by_user_id != actor.id:
        raise AuthorizationError()
    token = secrets.token_urlsafe(32)
    db.add(WorkAssignmentShare(assignment_id=row.id, token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=data.expires_at, created_by_user_id=actor.id))
    _event(db, row, actor.id, "SHARED"); db.commit()
    return ShareRead(url_token=token, expires_at=data.expires_at)


@public_router.get("/{token}")
def public_assignment(token: str, db: Session = Depends(get_db)) -> dict[str, object]:
    share = db.scalar(select(WorkAssignmentShare).where(WorkAssignmentShare.token_hash == hashlib.sha256(token.encode()).hexdigest(), WorkAssignmentShare.revoked_at.is_(None), or_(WorkAssignmentShare.expires_at.is_(None), WorkAssignmentShare.expires_at > server_now())))
    if not share:
        raise NotFoundError("This work-assignment link is invalid or expired.")
    row = db.get(WorkAssignment, share.assignment_id)
    if not row:
        raise NotFoundError()
    return {"id": row.id, "title": row.title, "status": row.status, "priority": row.priority, "progress_percent": row.progress_percent, "planned_start_at": row.planned_start_at, "due_at": row.due_at, "completed_at": row.completed_at, "updated_at": row.updated_at}
