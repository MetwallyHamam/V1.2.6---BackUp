import json
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.iam.models import AuditLog, Department, User
from app.modules.iam.service import effective_permissions
from app.modules.notifications.models import Notification
from app.modules.projects.access import authorized_project_ids, require_project_access
from app.modules.projects.collaboration_schemas import (
    CollaborationEventCreate,
    CollaborationRequestCreate,
    CollaborationRequestResponse,
    TicketProjectLinkCreate,
)
from app.modules.projects.models import (
    CompanyProject,
    CrossDepartmentRequest,
    CrossDepartmentRequestEvent,
    ProjectCollaborationEvent,
    ProjectTask,
    TicketProjectLink,
)
from app.modules.tickets.models import Ticket
from app.modules.tickets.service import visible_ticket_query

router = APIRouter(tags=["project collaboration"])
LINK_TYPES = {
    "ORIGINATED_FROM_TICKET",
    "RELATED",
    "REQUIRES_IMPLEMENTATION",
    "REQUIRES_SUPPORT",
    "CAUSED_BY_IMPLEMENTATION",
    "KNOWN_ISSUE",
    "POST_GO_LIVE",
}
VISIBILITIES = {"PROJECT_PRIVATE", "DEPARTMENT_SHARED", "SUPPORT_SHARED"}


def _values(row: Any) -> dict[str, Any]:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def _project(db: Session, actor: User, project_id: int) -> CompanyProject:
    return require_project_access(db, actor, project_id)


def _visible_ticket(db: Session, actor: User, ticket_id: int) -> Ticket:
    ticket = db.scalar(visible_ticket_query(db, actor).where(Ticket.id == ticket_id))
    if not ticket:
        raise NotFoundError("Ticket does not exist.")
    return ticket


def _validate_task(db: Session, project_id: int, task_id: int | None) -> None:
    if task_id is None:
        return
    task = db.get(ProjectTask, task_id)
    if not task or task.project_id != project_id:
        raise ConflictError(
            "INVALID_COLLABORATION_TASK", "Selected task must belong to this project."
        )


def _audit(
    db: Session, actor: User, project_id: int, action: str, values: dict[str, object]
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="project_collaboration",
            entity_id=str(project_id),
            action=action,
            new_values_json=json.dumps(values, default=str),
        )
    )


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "COLLABORATION_CONFLICT",
            "This collaboration record already exists or references invalid data.",
        ) from exc


def _notify_department(db: Session, department_id: int, request: CrossDepartmentRequest) -> None:
    recipients = set(
        db.scalars(
            select(User.id).where(User.is_active == true(), User.department_id == department_id)
        )
    )
    department = db.get(Department, department_id)
    if department and department.head_user_id:
        recipients.add(department.head_user_id)
    for user_id in recipients:
        db.add(
            Notification(
                recipient_user_id=user_id,
                notification_type="PROJECT_COLLABORATION_REQUEST",
                severity="WARNING" if request.priority in {"HIGH", "CRITICAL"} else "INFO",
                title=request.title,
                message="A cross-department project request requires a response.",
                deep_link=f"/projects/{request.project_id}/execution",
                deduplication_key=f"project-collaboration:{request.id}:created:user:{user_id}",
            )
        )


@router.get("/projects/{project_id}/collaboration")
def project_collaboration(
    project_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("cross_department.request.create")),
) -> dict[str, list[dict[str, Any]]]:
    _project(db, actor, project_id)
    requests = list(
        db.scalars(
            select(CrossDepartmentRequest)
            .where(CrossDepartmentRequest.project_id == project_id)
            .order_by(CrossDepartmentRequest.created_at.desc())
        )
    )
    event_statement = select(ProjectCollaborationEvent).where(
        ProjectCollaborationEvent.project_id == project_id
    )
    if "implementation.private_history.view" not in effective_permissions(db, actor).permissions:
        event_statement = event_statement.where(
            ProjectCollaborationEvent.visibility.in_(["DEPARTMENT_SHARED", "SUPPORT_SHARED"])
        )
    events = list(db.scalars(event_statement.order_by(ProjectCollaborationEvent.created_at.desc())))
    links = list(
        db.scalars(
            select(TicketProjectLink)
            .where(TicketProjectLink.project_id == project_id)
            .order_by(TicketProjectLink.created_at.desc())
        )
    )
    return {
        "requests": [_values(x) for x in requests],
        "events": [_values(x) for x in events],
        "ticket_links": [_values(x) for x in links],
    }


@router.post("/projects/{project_id}/collaboration-requests", status_code=status.HTTP_201_CREATED)
def create_request(
    project_id: int,
    data: CollaborationRequestCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("cross_department.request.create")),
) -> dict[str, Any]:
    _project(db, actor, project_id)
    _validate_task(db, project_id, data.task_id)
    if data.requesting_department_id == data.requested_department_id:
        raise ConflictError(
            "SAME_DEPARTMENT_REQUEST",
            "Cross-department requests require two different departments.",
        )
    if (
        "project.manage" not in effective_permissions(db, actor).permissions
        and actor.department_id != data.requesting_department_id
    ):
        raise ConflictError(
            "INVALID_REQUESTING_DEPARTMENT",
            "The requesting department must be your own department.",
        )
    if not db.get(Department, data.requesting_department_id) or not db.get(
        Department, data.requested_department_id
    ):
        raise NotFoundError("A selected department does not exist.")
    row = CrossDepartmentRequest(
        project_id=project_id, requested_by_user_id=actor.id, **data.model_dump()
    )
    db.add(row)
    db.flush()
    db.add(
        CrossDepartmentRequestEvent(
            request_id=row.id,
            event_type="CREATED",
            to_status="PENDING",
            notes=data.description,
            actor_user_id=actor.id,
        )
    )
    _notify_department(db, data.requested_department_id, row)
    _audit(
        db,
        actor,
        project_id,
        "project.collaboration.requested",
        {"request_id": row.id, "requested_department_id": data.requested_department_id},
    )
    _commit(db)
    db.refresh(row)
    return _values(row)


@router.post("/collaboration-requests/{request_id}/respond")
def respond_request(
    request_id: int,
    data: CollaborationRequestResponse,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("cross_department.request.respond")),
) -> dict[str, Any]:
    row = db.get(CrossDepartmentRequest, request_id)
    if not row:
        raise NotFoundError("Collaboration request does not exist.")
    _project(db, actor, row.project_id)
    if (
        "project.manage" not in effective_permissions(db, actor).permissions
        and actor.department_id != row.requested_department_id
    ):
        raise NotFoundError("Collaboration request does not exist.")
    decision = data.decision.upper()
    targets = {
        "ACCEPT": "ACCEPTED",
        "PROPOSE": "PROPOSED",
        "RETURN": "RETURNED",
        "REJECT": "REJECTED",
        "COMPLETE": "COMPLETED",
    }
    target = targets.get(decision, decision)
    allowed = {
        "PENDING": {"ACCEPTED", "PROPOSED", "RETURNED", "REJECTED"},
        "PROPOSED": {"ACCEPTED", "RETURNED", "REJECTED"},
        "ACCEPTED": {"COMPLETED", "RETURNED"},
        "RETURNED": {"PENDING", "REJECTED"},
    }
    if target not in allowed.get(row.status, set()):
        raise ConflictError(
            "INVALID_COLLABORATION_TRANSITION",
            f"Request cannot move from {row.status} to {target}.",
        )
    if data.owner_user_id:
        owner = db.get(User, data.owner_user_id)
        if not owner or owner.department_id != row.requested_department_id:
            raise ConflictError(
                "INVALID_COLLABORATION_OWNER",
                "The request owner must belong to the requested department.",
            )
    previous = row.status
    row.status = target
    row.owner_user_id = data.owner_user_id or row.owner_user_id
    row.response_notes = data.notes
    row.responded_by_user_id = actor.id
    row.responded_at = server_now()
    db.add(
        CrossDepartmentRequestEvent(
            request_id=row.id,
            event_type="RESPONDED",
            from_status=previous,
            to_status=target,
            notes=data.notes,
            actor_user_id=actor.id,
        )
    )
    db.add(
        Notification(
            recipient_user_id=row.requested_by_user_id,
            notification_type="PROJECT_COLLABORATION_RESPONSE",
            severity="INFO",
            title=row.title,
            message=f"Request moved to {target}.",
            deep_link=f"/projects/{row.project_id}/execution",
            deduplication_key=f"project-collaboration:{row.id}:{target}:user:{row.requested_by_user_id}",
        )
    )
    _audit(
        db,
        actor,
        row.project_id,
        "project.collaboration.responded",
        {"request_id": row.id, "from": previous, "to": target},
    )
    _commit(db)
    db.refresh(row)
    return _values(row)


@router.post("/projects/{project_id}/events", status_code=201)
def create_event(
    project_id: int,
    data: CollaborationEventCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("cross_department.event.publish")),
) -> dict[str, Any]:
    project = _project(db, actor, project_id)
    _validate_task(db, project_id, data.task_id)
    visibility = data.visibility.upper()
    if visibility not in VISIBILITIES:
        raise ConflictError(
            "INVALID_EVENT_VISIBILITY",
            "Select PROJECT_PRIVATE, DEPARTMENT_SHARED, or SUPPORT_SHARED.",
        )
    if data.ticket_id:
        ticket = _visible_ticket(db, actor, data.ticket_id)
        if ticket.client_id != project.client_id:
            raise ConflictError(
                "TICKET_PROJECT_CLIENT_MISMATCH",
                "Ticket and project must belong to the same Client.",
            )
    row = ProjectCollaborationEvent(
        project_id=project_id,
        author_user_id=actor.id,
        visibility=visibility,
        **data.model_dump(exclude={"visibility"}),
    )
    db.add(row)
    db.flush()
    _audit(
        db,
        actor,
        project_id,
        "project.collaboration.event_published",
        {"event_id": row.id, "visibility": visibility},
    )
    _commit(db)
    db.refresh(row)
    return _values(row)


@router.post("/projects/{project_id}/ticket-links", status_code=201)
def link_ticket(
    project_id: int,
    data: TicketProjectLinkCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("cross_department.ticket_link.manage")),
) -> dict[str, Any]:
    project = _project(db, actor, project_id)
    ticket = _visible_ticket(db, actor, data.ticket_id)
    _validate_task(db, project_id, data.task_id)
    link_type = data.link_type.upper()
    if link_type not in LINK_TYPES:
        raise ConflictError(
            "INVALID_TICKET_PROJECT_LINK", "Select an approved typed ticket relationship."
        )
    if ticket.client_id != project.client_id:
        raise ConflictError(
            "TICKET_PROJECT_CLIENT_MISMATCH", "Ticket and project must belong to the same Client."
        )
    row = TicketProjectLink(
        project_id=project_id,
        created_by_user_id=actor.id,
        link_type=link_type,
        **data.model_dump(exclude={"link_type"}),
    )
    db.add(row)
    db.flush()
    db.add(
        ProjectCollaborationEvent(
            project_id=project_id,
            task_id=data.task_id,
            ticket_id=ticket.id,
            event_type="TICKET_LINKED",
            title=f"Ticket {ticket.ticket_number or ticket.id} linked",
            summary=data.shared_summary,
            visibility="SUPPORT_SHARED",
            author_user_id=actor.id,
        )
    )
    _audit(
        db,
        actor,
        project_id,
        "project.ticket.linked",
        {"ticket_id": ticket.id, "link_type": link_type},
    )
    _commit(db)
    db.refresh(row)
    return _values(row)


@router.get("/tickets/{ticket_id}/implementation-history")
def ticket_implementation_history(
    ticket_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("cross_department.history.view")),
) -> dict[str, list[dict[str, Any]]]:
    _visible_ticket(db, actor, ticket_id)
    links = list(
        db.scalars(
            select(TicketProjectLink)
            .where(
                TicketProjectLink.ticket_id == ticket_id,
                TicketProjectLink.project_id.in_(authorized_project_ids(db, actor)),
            )
            .order_by(TicketProjectLink.created_at.desc())
        )
    )
    events = list(
        db.scalars(
            select(ProjectCollaborationEvent)
            .where(
                ProjectCollaborationEvent.ticket_id == ticket_id,
                ProjectCollaborationEvent.project_id.in_(authorized_project_ids(db, actor)),
                ProjectCollaborationEvent.visibility == "SUPPORT_SHARED",
            )
            .order_by(ProjectCollaborationEvent.created_at.desc())
        )
    )
    projects = (
        {
            row.id: row
            for row in db.scalars(
                select(CompanyProject).where(
                    CompanyProject.id.in_({link.project_id for link in links})
                )
            )
        }
        if links
        else {}
    )
    link_values = []
    for link in links:
        item = _values(link)
        project = projects.get(link.project_id)
        item["project_number"] = project.project_number if project else None
        item["project_name"] = project.name if project else None
        link_values.append(item)
    return {"links": link_values, "events": [_values(x) for x in events]}
