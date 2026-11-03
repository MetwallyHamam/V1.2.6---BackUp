import hashlib
import json
import secrets
from datetime import datetime, timedelta
from io import BytesIO

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_any_permission, require_permission
from app.core.clock import as_server_time, server_clock_settings, server_now
from app.core.config import Settings, get_settings
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import Client
from app.modules.iam.models import AuditLog, User
from app.modules.iam.service import effective_permissions
from app.modules.notifications.models import EventOutbox, Notification
from app.modules.service_checklists.attachments import evidence_path, store_evidence
from app.modules.service_checklists.models import (
    ServiceChecklistEvidence,
    ServiceChecklistOccurrence,
    ServiceChecklistOccurrenceItem,
    ServiceChecklistSchedule,
    ServiceChecklistShareLink,
    ServiceChecklistTemplate,
    ServiceChecklistTemplateItem,
    ServiceDeliveryRecord,
)
from app.modules.service_checklists.schemas import (
    BlockAction,
    BulkScheduleAssignAction,
    BulkScheduleReminderAction,
    BulkScheduleTransferAction,
    CancelAction,
    ChecklistReport,
    ClientHandoffAction,
    CompleteOccurrenceAction,
    CompleteOccurrenceResult,
    CompletionPreview,
    EvidenceRead,
    ItemCompleteAction,
    OccurrenceCreate,
    OccurrenceItemCreate,
    OccurrenceItemDetailsUpdate,
    OccurrenceItemRead,
    OccurrenceItemWrite,
    OccurrenceRead,
    QuickCompleteAction,
    QuickCompleteResult,
    ReassignAction,
    ScheduleCadenceAction,
    ScheduleCreate,
    SchedulePreview,
    ScheduleRead,
    ScheduleReassignAction,
    ScheduleStateAction,
    TemplateCreate,
    TemplateItemRead,
    TemplateItemWrite,
    TemplateRead,
    TemplateUpdate,
    VersionAction,
)
from app.modules.tickets.models import (
    Ticket,
    TicketAssignmentHistory,
    TicketStatus,
    TicketStatusHistory,
    TicketTask,
    TicketType,
)

router = APIRouter(prefix="/service-checklists", tags=["service-checklists"])
public_router = APIRouter(prefix="/public/service-checklists", tags=["public service checklists"])


def serialize(db: Session, row: ServiceChecklistTemplate) -> TemplateRead:
    items = list(
        db.scalars(
            select(ServiceChecklistTemplateItem)
            .where(
                ServiceChecklistTemplateItem.template_id == row.id,
                ServiceChecklistTemplateItem.is_active.in_([True]),
            )
            .order_by(ServiceChecklistTemplateItem.display_order, ServiceChecklistTemplateItem.id)
        )
    )
    return TemplateRead(
        id=row.id,
        code=row.code,
        name=row.name,
        description=row.description,
        schedule_mode=row.schedule_mode,
        version=row.version,
        publication_status=row.publication_status,
        is_default=row.is_default,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
        items=[
            TemplateItemRead(
                id=item.id,
                item_code=item.item_code,
                title=item.title,
                instructions=item.instructions,
                display_order=item.display_order,
                is_required=item.is_required,
                responsibility=item.responsibility,
                evidence_type=item.evidence_type,
                evidence_required=item.evidence_required,
                expected_duration_minutes=item.expected_duration_minutes,
            )
            for item in items
        ],
    )


def replace_items(db: Session, template_id: int, items: list[TemplateItemWrite]) -> None:
    db.query(ServiceChecklistTemplateItem).filter(
        ServiceChecklistTemplateItem.template_id == template_id
    ).delete(synchronize_session=False)
    for item in items:
        values = item.model_dump()
        values["item_code"] = str(values["item_code"]).strip().upper()
        values["title"] = str(values["title"]).strip()
        db.add(ServiceChecklistTemplateItem(template_id=template_id, **values))


def occurrence_read(
    db: Session, row: ServiceChecklistOccurrence, *, detail: bool = False
) -> OccurrenceRead:
    client = db.get(Client, row.client_id)
    owner = db.get(User, row.assigned_user_id) if row.assigned_user_id else None
    items = list(
        db.scalars(
            select(ServiceChecklistOccurrenceItem)
            .where(ServiceChecklistOccurrenceItem.occurrence_id == row.id)
            .order_by(ServiceChecklistOccurrenceItem.display_order)
        )
    )
    internal_required = [
        item for item in items if item.is_required and item.responsibility != "CLIENT"
    ]
    complete = [
        item
        for item in internal_required
        if item.state
        in {"COMPLETE", "COMPLETED", "CLIENT_RESPONSIBILITY", "CLIENT_RESPONSIBLE", "WAIVED"}
    ]
    gaps = [
        item
        for item in items
        if item.evidence_required
        and (
            (item.evidence_type == "FILE" and item.evidence_id is None)
            or (item.evidence_type != "FILE" and not item.evidence_reference)
        )
    ]
    states = {item.state for item in items}
    workflow_status = (
        "COMPLETE"
        if row.status == "COMPLETED"
        or (
            items
            and states.issubset(
                {"COMPLETE", "COMPLETED", "CLIENT_RESPONSIBILITY", "CLIENT_RESPONSIBLE", "WAIVED"}
            )
        )
        else "NEED_ATTENTION"
        if "NEED_ATTENTION" in states
        else "PENDING"
        if "PENDING" in states
        else "CLIENT_RESPONSIBILITY"
        if states.intersection({"CLIENT_RESPONSIBILITY", "CLIENT_RESPONSIBLE"})
        else "PENDING"
    )
    now = server_now()
    lane = row.status
    if row.status == "SCHEDULED":
        due_at = as_server_time(row.due_at)
        if due_at.date() == now.date():
            lane = "DUE_TODAY"
        elif due_at < now:
            lane = "OVERDUE"
    elif row.status == "IN_PROGRESS" and as_server_time(row.due_at) < now:
        lane = "OVERDUE"
    return OccurrenceRead(
        id=row.id,
        occurrence_number=row.occurrence_number,
        template_id=row.template_id,
        template_version=row.template_version,
        template_name=row.template_name,
        schedule_id=row.schedule_id,
        ticket_id=row.ticket_id,
        client_id=row.client_id,
        client_name=client.name if client else "",
        assigned_user_id=row.assigned_user_id,
        assigned_user_name=owner.full_name if owner else None,
        scheduled_at=row.scheduled_at,
        due_at=row.due_at,
        recurrence_days=row.recurrence_days,
        status=row.status,
        workflow_status=workflow_status,
        effective_lane=lane,
        blocked_party=row.blocked_party,
        blocked_reason=row.blocked_reason,
        follow_up_at=row.follow_up_at,
        completion_summary=row.completion_summary,
        service_provided=row.service_provided,
        version=row.version,
        required_complete=len(complete),
        required_total=len(internal_required),
        evidence_gaps=len(gaps),
        items=[OccurrenceItemRead.model_validate(item, from_attributes=True) for item in items]
        if detail
        else None,
    )


def get_occurrence(db: Session, occurrence_id: int) -> ServiceChecklistOccurrence:
    row = db.get(ServiceChecklistOccurrence, occurrence_id)
    if not row:
        raise NotFoundError("The service checklist occurrence was not found.")
    return row


def checklist_assignee(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user or not user.is_active or user.user_type != "EMPLOYEE":
        raise NotFoundError("The assigned engineer was not found or is inactive.")
    return user


def require_version(row: ServiceChecklistOccurrence, version: int) -> None:
    if row.version != version:
        raise ConflictError("STALE_DATA", "The checklist changed. Reload it and try again.")


def require_editable_occurrence(row: ServiceChecklistOccurrence) -> None:
    if row.status in {"COMPLETED", "CANCELLED"}:
        raise ConflictError(
            "CHECKLIST_READ_ONLY",
            "Completed and cancelled checklist events are read-only.",
        )


def authorize_occurrence(db: Session, actor: User, row: ServiceChecklistOccurrence) -> None:
    permissions = set(effective_permissions(db, actor).permissions)
    if (
        "service_checklist.view_all" in permissions
        or "service_checklist.schedule.manage" in permissions
    ):
        return
    if row.assigned_user_id == actor.id:
        return
    if "service_checklist.view_team" in permissions and row.assigned_user_id:
        owner = db.get(User, row.assigned_user_id)
        if owner and actor.department_id and owner.department_id == actor.department_id:
            return
    raise AuthorizationError("You cannot access this checklist occurrence.")


def authorize_schedule(db: Session, actor: User, row: ServiceChecklistSchedule) -> None:
    permissions = set(effective_permissions(db, actor).permissions)
    if (
        "service_checklist.view_all" in permissions
        or "service_checklist.schedule.manage" in permissions
    ):
        return
    if row.assigned_user_id == actor.id:
        return
    if "service_checklist.view_team" in permissions and row.assigned_user_id:
        owner = db.get(User, row.assigned_user_id)
        if owner and actor.department_id and owner.department_id == actor.department_id:
            return
    raise AuthorizationError("You cannot access this checklist assignment.")


def audit(
    db: Session,
    actor: User,
    row: ServiceChecklistOccurrence,
    action: str,
    values: dict[str, object] | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ServiceChecklistOccurrence",
            entity_id=str(row.id),
            action=action,
            new_values_json=json.dumps(values) if values else None,
        )
    )


def snapshot_occurrence_items(db: Session, occurrence: ServiceChecklistOccurrence) -> None:
    source = list(
        db.scalars(
            select(ServiceChecklistTemplateItem)
            .where(
                ServiceChecklistTemplateItem.template_id == occurrence.template_id,
                ServiceChecklistTemplateItem.is_active.in_([True]),
            )
            .order_by(ServiceChecklistTemplateItem.display_order)
        )
    )
    for item in source:
        db.add(
            ServiceChecklistOccurrenceItem(
                occurrence_id=occurrence.id,
                item_code=item.item_code,
                title=item.title,
                resource_type=item.resource_type,
                resource_path=item.resource_path,
                instructions=item.instructions,
                display_order=item.display_order,
                is_required=item.is_required,
                original_responsibility=item.responsibility,
                responsibility=item.responsibility,
                evidence_type=item.evidence_type,
                evidence_required=item.evidence_required,
            )
        )


def carry_forward_client_items(db: Session, occurrence: ServiceChecklistOccurrence) -> bool:
    scope = (
        ServiceChecklistOccurrence.schedule_id == occurrence.schedule_id
        if occurrence.schedule_id is not None
        else and_(
            ServiceChecklistOccurrence.template_id == occurrence.template_id,
            ServiceChecklistOccurrence.client_id == occurrence.client_id,
        )
    )
    previous = db.scalar(
        select(ServiceChecklistOccurrence)
        .where(scope, ServiceChecklistOccurrence.id != occurrence.id)
        .order_by(ServiceChecklistOccurrence.scheduled_at.desc())
    )
    if not previous:
        return False
    source = list(
        db.scalars(
            select(ServiceChecklistOccurrenceItem)
            .where(ServiceChecklistOccurrenceItem.occurrence_id == previous.id)
            .order_by(ServiceChecklistOccurrenceItem.display_order)
        )
    )
    for item in source:
        db.add(
            ServiceChecklistOccurrenceItem(
                occurrence_id=occurrence.id,
                item_code=item.item_code,
                title=item.title,
                resource_type=item.resource_type,
                resource_path=item.resource_path,
                instructions=item.instructions,
                display_order=item.display_order,
                is_required=item.is_required,
                original_responsibility="MILLENSYS",
                responsibility="MILLENSYS",
                evidence_type="NONE",
                evidence_required=False,
                state="PENDING",
            )
        )
    return bool(source)


def ensure_occurrence_ticket(
    db: Session, occurrence: ServiceChecklistOccurrence, actor: User
) -> Ticket:
    if occurrence.ticket_id:
        existing = db.get(Ticket, occurrence.ticket_id)
        if existing:
            return existing
    existing = db.scalar(
        select(Ticket).where(
            Ticket.creation_idempotency_key == f"service-checklist:{occurrence.id}"
        )
    )
    if existing:
        occurrence.ticket_id = existing.id
        return existing
    items = list(
        db.scalars(
            select(ServiceChecklistOccurrenceItem)
            .where(ServiceChecklistOccurrenceItem.occurrence_id == occurrence.id)
            .order_by(
                ServiceChecklistOccurrenceItem.display_order, ServiceChecklistOccurrenceItem.id
            )
        )
    )
    completed_states = {
        "COMPLETE",
        "COMPLETED",
        "CLIENT_RESPONSIBILITY",
        "CLIENT_RESPONSIBLE",
        "WAIVED",
    }
    all_complete = bool(items) and all(item.state in completed_states for item in items)
    initial_status_code = "CLOSED" if all_complete else "PENDING_INTERNAL"
    ticket_type = db.scalar(select(TicketType).where(TicketType.code == "SCHEDULED_SERVICE"))
    status = db.scalar(select(TicketStatus).where(TicketStatus.code == initial_status_code))
    if not ticket_type or not status:
        raise ConflictError(
            "SCHEDULED_SERVICE_CONFIGURATION_MISSING",
            "Scheduled Service ticket configuration is missing.",
        )
    now = server_now()
    ticket = Ticket(
        ticket_type_id=ticket_type.id,
        client_id=occurrence.client_id,
        contract_id=None,
        created_by_user_id=actor.id,
        status_id=status.id,
        assigned_user_id=occurrence.assigned_user_id or actor.id,
        source_channel="SCHEDULED_SERVICE",
        creation_idempotency_key=f"service-checklist:{occurrence.id}",
        entitlement_status="PLANNED_SERVICE",
        impact="MEDIUM",
        urgency="MEDIUM",
        priority="P3",
        subject=f"{occurrence.template_name} · {occurrence.occurrence_number}",
        description=f"System-created checklist event {occurrence.occurrence_number}. This ticket does not use SLA.",
        due_at=occurrence.due_at,
        resolution_summary="Checklist event tasks completed." if all_complete else None,
        resolved_at=now if all_complete else None,
        closed_at=now if all_complete else None,
        last_activity_at=now,
    )
    db.add(ticket)
    db.flush()
    ticket.ticket_number = f"{ticket_type.number_prefix}-{server_now().year}-{ticket.id:06d}"
    occurrence.ticket_id = ticket.id
    if ticket.assigned_user_id:
        db.add(
            TicketAssignmentHistory(
                ticket_id=ticket.id,
                assigned_user_id=ticket.assigned_user_id,
                assigned_team=None,
                assigned_by_user_id=actor.id,
                reason="System-created checklist event",
                created_at=now,
            )
        )
    for item in items:
        task_complete = item.state in completed_states
        db.add(
            TicketTask(
                ticket_id=ticket.id,
                title=item.title,
                description=f"Checklist task {item.item_code}\nPath or URL: {item.resource_path or '—'}",
                assigned_user_id=ticket.assigned_user_id,
                status="COMPLETED" if task_complete else "OPEN",
                is_required=item.is_required,
                due_at=occurrence.due_at,
                completed_at=item.completed_at if task_complete else None,
                created_by_user_id=actor.id,
            )
        )
    return ticket


def sync_occurrence_ticket_tasks(db: Session, occurrence: ServiceChecklistOccurrence) -> None:
    if not occurrence.ticket_id:
        return
    items = list(
        db.scalars(
            select(ServiceChecklistOccurrenceItem)
            .where(ServiceChecklistOccurrenceItem.occurrence_id == occurrence.id)
            .order_by(
                ServiceChecklistOccurrenceItem.display_order, ServiceChecklistOccurrenceItem.id
            )
        )
    )
    tasks = list(
        db.scalars(
            select(TicketTask)
            .where(TicketTask.ticket_id == occurrence.ticket_id)
            .order_by(TicketTask.id)
        )
    )
    for item, task in zip(items, tasks, strict=False):
        task.title = item.title
        task.description = (
            f"Checklist task {item.item_code}\nPath or URL: {item.resource_path or '—'}"
        )
        task.assigned_user_id = occurrence.assigned_user_id
        task.status = (
            "COMPLETED"
            if item.state
            in {"COMPLETE", "COMPLETED", "CLIENT_RESPONSIBILITY", "CLIENT_RESPONSIBLE", "WAIVED"}
            else "IN_PROGRESS"
            if item.state == "NEED_ATTENTION"
            else "OPEN"
        )
        task.completed_at = item.completed_at if task.status == "COMPLETED" else None


def sync_ticket_status(
    db: Session, row: ServiceChecklistOccurrence, actor: User, target_code: str, reason: str
) -> None:
    ticket = db.get(Ticket, row.ticket_id) if row.ticket_id else None
    target = db.scalar(select(TicketStatus).where(TicketStatus.code == target_code))
    if not ticket or not target or ticket.status_id == target.id:
        return
    previous = ticket.status_id
    ticket.status_id = target.id
    ticket.version += 1
    ticket.last_activity_at = server_now()
    if target_code == "IN_PROGRESS":
        ticket.progress_started_at = ticket.progress_started_at or server_now()
    if target_code == "RESOLVED":
        ticket.resolved_at = server_now()
        ticket.resolution_summary = row.completion_summary
    if target_code == "CLOSED":
        ticket.resolved_at = ticket.resolved_at or server_now()
        ticket.closed_at = server_now()
        ticket.resolution_summary = row.completion_summary
    if target_code == "CANCELLED":
        ticket.cancelled_at = server_now()
    db.add(
        TicketStatusHistory(
            ticket_id=ticket.id,
            from_status_id=previous,
            to_status_id=target.id,
            changed_by_user_id=actor.id,
            reason=reason,
        )
    )


def create_occurrence_row(
    db: Session,
    data: OccurrenceCreate,
    actor: User,
    *,
    schedule_id: int | None = None,
    carry_forward_items: bool = True,
) -> ServiceChecklistOccurrence:
    template = db.get(ServiceChecklistTemplate, data.template_id)
    if not template or not template.is_active or template.publication_status != "PUBLISHED":
        raise ConflictError(
            "CHECKLIST_TEMPLATE_NOT_PUBLISHED", "Select an active published checklist template."
        )
    if template.schedule_mode == "CLIENT_MANAGED_UNSCHEDULED" and data.recurrence_days:
        raise ConflictError(
            "CLIENT_MANAGED_NOT_RECURRING",
            "Client-managed checklists cannot create recurring work.",
        )
    if not db.get(Client, data.client_id):
        raise NotFoundError("The client was not found.")
    if data.assigned_user_id:
        checklist_assignee(db, data.assigned_user_id)
    row = ServiceChecklistOccurrence(
        occurrence_number="PENDING",
        template_id=template.id,
        template_version=template.version,
        template_name=template.name,
        schedule_id=schedule_id,
        client_id=data.client_id,
        assigned_user_id=data.assigned_user_id,
        scheduled_at=data.scheduled_at,
        due_at=data.due_at,
        recurrence_days=data.recurrence_days,
        created_by_user_id=actor.id,
    )
    db.add(row)
    db.flush()
    row.occurrence_number = f"SCL-{server_now().year}-{row.id:06d}"
    if not carry_forward_items or not carry_forward_client_items(db, row):
        snapshot_occurrence_items(db, row)
    db.flush()
    ensure_occurrence_ticket(db, row, actor)
    return row


@router.get("/assignees")
def list_checklist_assignees(
    db: Session = Depends(get_db),
    _: User = Depends(
        require_any_permission("service_checklist.schedule.manage", "service_checklist.reassign")
    ),
) -> list[dict[str, object]]:
    users = db.scalars(
        select(User)
        .where(User.is_active.in_([True]), User.user_type == "EMPLOYEE")
        .order_by(User.full_name, User.id)
    )
    return [{"id": user.id, "full_name": user.full_name} for user in users]


@router.get("/templates", response_model=list[TemplateRead])
def list_templates(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_any_permission(
            "service_checklist.view_own",
            "service_checklist.template.view",
            "service_checklist.template.manage",
        )
    ),
) -> list[TemplateRead]:
    del actor
    query = select(ServiceChecklistTemplate).order_by(ServiceChecklistTemplate.name)
    if not include_inactive:
        query = query.where(ServiceChecklistTemplate.is_active.in_([True]))
    return [serialize(db, row) for row in db.scalars(query)]


@router.post("/templates", response_model=TemplateRead, status_code=201)
def create_template(
    data: TemplateCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.template.manage")),
) -> TemplateRead:
    code = data.code.strip().upper()
    if db.scalar(select(ServiceChecklistTemplate.id).where(ServiceChecklistTemplate.code == code)):
        raise ConflictError(
            "CHECKLIST_TEMPLATE_CODE_EXISTS", "A service checklist template already uses this code."
        )
    row = ServiceChecklistTemplate(
        code=code,
        name=data.name.strip(),
        description=data.description.strip() if data.description else None,
        schedule_mode=data.schedule_mode,
        is_default=data.is_default,
        created_by_user_id=actor.id,
    )
    db.add(row)
    db.flush()
    if row.is_default:
        db.query(ServiceChecklistTemplate).filter(
            ServiceChecklistTemplate.id != row.id,
            ServiceChecklistTemplate.is_default.in_([True]),
        ).update({"is_default": False}, synchronize_session=False)
    replace_items(db, row.id, data.items)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ServiceChecklistTemplate",
            entity_id=str(row.id),
            action="service_checklist.template.created",
            new_values_json=json.dumps(
                {
                    "code": code,
                    "name": row.name,
                    "schedule_mode": row.schedule_mode,
                    "item_count": len(data.items),
                }
            ),
        )
    )
    db.commit()
    db.refresh(row)
    return serialize(db, row)


@router.put("/templates/{template_id}", response_model=TemplateRead)
def update_template(
    template_id: int,
    data: TemplateUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.template.manage")),
) -> TemplateRead:
    row = db.get(ServiceChecklistTemplate, template_id)
    if not row or not row.is_active:
        raise NotFoundError("The service checklist template was not found.")
    if row.publication_status != "DRAFT":
        raise ConflictError(
            "CHECKLIST_TEMPLATE_IMMUTABLE",
            "Published checklist templates cannot be edited.",
        )
    if row.version != data.version:
        raise ConflictError(
            "STALE_DATA", "The checklist template changed. Reload it and try again."
        )
    old = {"name": row.name, "schedule_mode": row.schedule_mode, "version": row.version}
    row.name = data.name.strip()
    row.description = data.description.strip() if data.description else None
    row.schedule_mode = data.schedule_mode
    row.is_default = data.is_default
    if row.is_default:
        db.query(ServiceChecklistTemplate).filter(
            ServiceChecklistTemplate.id != row.id,
            ServiceChecklistTemplate.is_default.in_([True]),
        ).update({"is_default": False}, synchronize_session=False)
    row.version += 1
    replace_items(db, row.id, data.items)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ServiceChecklistTemplate",
            entity_id=str(row.id),
            action="service_checklist.template.updated",
            old_values_json=json.dumps(old),
            new_values_json=json.dumps(
                {
                    "name": row.name,
                    "schedule_mode": row.schedule_mode,
                    "version": row.version,
                    "item_count": len(data.items),
                }
            ),
        )
    )
    db.commit()
    db.refresh(row)
    return serialize(db, row)


@router.post("/templates/{template_id}/publish", response_model=TemplateRead)
def publish_template(
    template_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.template.manage")),
) -> TemplateRead:
    row = db.get(ServiceChecklistTemplate, template_id)
    if not row or not row.is_active:
        raise NotFoundError("The service checklist template was not found.")
    if row.publication_status != "DRAFT":
        raise ConflictError(
            "CHECKLIST_TEMPLATE_ALREADY_PUBLISHED", "Only a draft template can be published."
        )
    row.publication_status = "PUBLISHED"
    row.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ServiceChecklistTemplate",
            entity_id=str(row.id),
            action="service_checklist.template.published",
            new_values_json=json.dumps({"version": row.version}),
        )
    )
    db.commit()
    db.refresh(row)
    return serialize(db, row)


@router.delete("/templates/{template_id}", status_code=204)
def retire_template(
    template_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.template.manage")),
) -> Response:
    row = db.get(ServiceChecklistTemplate, template_id)
    if not row or not row.is_active:
        raise NotFoundError("The service checklist template was not found.")
    active_schedule = db.scalar(
        select(ServiceChecklistSchedule.id)
        .where(
            ServiceChecklistSchedule.template_id == row.id,
            ServiceChecklistSchedule.is_active.in_([True]),
            ServiceChecklistSchedule.is_paused.in_([False]),
        )
        .limit(1)
    )
    if active_schedule:
        raise ConflictError(
            "CHECKLIST_TEMPLATE_HAS_ACTIVE_SCHEDULES",
            "Pause every active schedule using this template before retiring it.",
        )
    row.is_active = False
    row.publication_status = "RETIRED"
    row.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ServiceChecklistTemplate",
            entity_id=str(row.id),
            action="service_checklist.template.retired",
        )
    )
    db.commit()
    return Response(status_code=204)


@router.get("/occurrences", response_model=list[OccurrenceRead])
def list_occurrences(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_any_permission(
            "service_checklist.view_own",
            "service_checklist.view_team",
            "service_checklist.view_all",
        )
    ),
) -> list[OccurrenceRead]:
    permissions = set(effective_permissions(db, actor).permissions)
    query = select(ServiceChecklistOccurrence).order_by(ServiceChecklistOccurrence.due_at)
    if (
        "service_checklist.view_all" not in permissions
        and "service_checklist.schedule.manage" not in permissions
    ):
        if "service_checklist.view_team" in permissions and actor.department_id:
            query = query.join(User, User.id == ServiceChecklistOccurrence.assigned_user_id).where(
                User.department_id == actor.department_id
            )
        else:
            query = query.where(ServiceChecklistOccurrence.assigned_user_id == actor.id)
    if status_filter:
        query = query.where(ServiceChecklistOccurrence.status == status_filter)
    return [occurrence_read(db, row) for row in db.scalars(query.limit(500))]


@router.get("/occurrences/{occurrence_id}", response_model=OccurrenceRead)
def occurrence_detail(
    occurrence_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_any_permission(
            "service_checklist.view_own",
            "service_checklist.view_team",
            "service_checklist.view_all",
        )
    ),
) -> OccurrenceRead:
    row = get_occurrence(db, occurrence_id)
    authorize_occurrence(db, actor, row)
    return occurrence_read(db, row, detail=True)


@router.get("/occurrences/{occurrence_id}/export.xlsx")
def export_occurrence_tasks(
    occurrence_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_any_permission(
            "service_checklist.view_own",
            "service_checklist.view_team",
            "service_checklist.view_all",
            "service_checklist.export",
        )
    ),
) -> StreamingResponse:
    row = get_occurrence(db, occurrence_id)
    authorize_occurrence(db, actor, row)
    detail = occurrence_read(db, row, detail=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Checklist Event"
    sheet.append(["Client", detail.client_name])
    sheet.append(["Template", detail.template_name])
    sheet.append(["Event", detail.occurrence_number])
    sheet.append(["Status", detail.workflow_status])
    sheet.append(["Due", as_server_time(detail.due_at).isoformat()])
    sheet.append([])
    sheet.append(["Task", "Status", "Type", "Path or URL", "Check Date", "Required"])
    for cell in sheet[7]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
    for item in detail.items or []:
        sheet.append(
            [
                item.title,
                item.state,
                item.resource_type,
                item.resource_path or "",
                as_server_time(item.check_date).isoformat() if item.check_date else "",
                "YES" if item.is_required else "NO",
            ]
        )
    for column, width in zip("ABCDEF", [32, 22, 20, 55, 24, 12], strict=True):
        sheet.column_dimensions[column].width = width
    sheet.freeze_panes = "A8"
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    filename = f"{detail.occurrence_number}-tasks.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/occurrences/{occurrence_id}/share")
def share_occurrence(
    occurrence_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_any_permission(
            "service_checklist.view_own",
            "service_checklist.view_team",
            "service_checklist.view_all",
            "service_checklist.export",
        )
    ),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    row = get_occurrence(db, occurrence_id)
    authorize_occurrence(db, actor, row)
    raw_token = secrets.token_urlsafe(40)
    expires_at = server_now() + timedelta(days=90)
    db.add(
        ServiceChecklistShareLink(
            occurrence_id=row.id,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            expires_at=expires_at,
            created_by_user_id=actor.id,
        )
    )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ServiceChecklistOccurrence",
            entity_id=str(row.id),
            action="service_checklist.event.shared",
        )
    )
    db.commit()
    return {
        "url": f"{settings.frontend_base_url.rstrip('/')}/shared/checklists/{raw_token}",
        "expires_at": expires_at,
    }


@public_router.get("/{token}")
def public_occurrence(
    token: str, response: Response, db: Session = Depends(get_db)
) -> dict[str, object]:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    link = db.scalar(
        select(ServiceChecklistShareLink).where(
            ServiceChecklistShareLink.token_hash == token_hash,
            ServiceChecklistShareLink.is_active.in_([True]),
            ServiceChecklistShareLink.expires_at > server_now(),
        )
    )
    row = db.get(ServiceChecklistOccurrence, link.occurrence_id) if link else None
    if not link or not row:
        raise NotFoundError("The shared checklist event is invalid or expired.")
    detail = occurrence_read(db, row, detail=True)
    response.headers["Cache-Control"] = "private, no-store"
    return {
        "client_name": detail.client_name,
        "template_name": detail.template_name,
        "occurrence_number": detail.occurrence_number,
        "workflow_status": detail.workflow_status,
        "scheduled_at": detail.scheduled_at,
        "due_at": detail.due_at,
        "completed_at": row.completed_at,
        "completion_summary": detail.completion_summary,
        "tasks": [
            {
                "title": item.title,
                "status": item.state,
                "resource_type": item.resource_type,
                "resource_path": None,
                "check_date": item.check_date,
            }
            for item in detail.items or []
        ],
        "expires_at": link.expires_at,
    }


@router.post("/occurrences", response_model=OccurrenceRead, status_code=201)
def create_occurrence(
    data: OccurrenceCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.schedule.manage")),
) -> OccurrenceRead:
    row = create_occurrence_row(db, data, actor)
    audit(db, actor, row, "service_checklist.occurrence.created")
    db.commit()
    db.refresh(row)
    return occurrence_read(db, row, detail=True)


@router.post("/occurrences/{occurrence_id}/start", response_model=OccurrenceRead)
def start_occurrence(
    occurrence_id: int,
    data: VersionAction,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.perform")),
) -> OccurrenceRead:
    row = get_occurrence(db, occurrence_id)
    authorize_occurrence(db, actor, row)
    require_version(row, data.version)
    if row.status not in {"SCHEDULED", "BLOCKED"}:
        raise ConflictError(
            "INVALID_CHECKLIST_TRANSITION", "Only scheduled or blocked checklists can be started."
        )
    row.status = "IN_PROGRESS"
    row.started_at = row.started_at or server_now()
    row.blocked_party = row.blocked_reason = None
    row.follow_up_at = None
    row.version += 1
    sync_ticket_status(db, row, actor, "IN_PROGRESS", "Checklist event started")
    audit(db, actor, row, "service_checklist.occurrence.started")
    db.commit()
    db.refresh(row)
    return occurrence_read(db, row, detail=True)


@router.post("/occurrences/{occurrence_id}/block", response_model=OccurrenceRead)
def block_occurrence(
    occurrence_id: int,
    data: BlockAction,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.perform")),
) -> OccurrenceRead:
    row = get_occurrence(db, occurrence_id)
    authorize_occurrence(db, actor, row)
    require_version(row, data.version)
    if row.status != "IN_PROGRESS":
        raise ConflictError(
            "INVALID_CHECKLIST_TRANSITION", "Only an in-progress checklist can be blocked."
        )
    row.status = "BLOCKED"
    row.blocked_party = data.blocked_party
    row.blocked_reason = data.reason.strip()
    row.follow_up_at = data.follow_up_at
    row.version += 1
    sync_ticket_status(
        db,
        row,
        actor,
        "PENDING_CLIENT" if data.blocked_party == "CLIENT" else "PENDING_INTERNAL",
        data.reason,
    )
    audit(
        db,
        actor,
        row,
        "service_checklist.occurrence.blocked",
        {"party": data.blocked_party, "reason": data.reason},
    )
    db.commit()
    db.refresh(row)
    return occurrence_read(db, row, detail=True)


@router.post("/occurrences/{occurrence_id}/items/{item_id}/complete", response_model=OccurrenceRead)
def complete_item(
    occurrence_id: int,
    item_id: int,
    data: ItemCompleteAction,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.perform")),
) -> OccurrenceRead:
    row = get_occurrence(db, occurrence_id)
    authorize_occurrence(db, actor, row)
    require_version(row, data.version)
    require_editable_occurrence(row)
    item = db.get(ServiceChecklistOccurrenceItem, item_id)
    if not item or item.occurrence_id != row.id:
        raise NotFoundError("The checklist item was not found.")
    if item.responsibility == "CLIENT":
        raise ConflictError(
            "CLIENT_ITEM_REQUIRES_HANDOFF",
            "Use Client Responsible handoff instead of completing this item.",
        )
    evidence = db.get(ServiceChecklistEvidence, data.evidence_id) if data.evidence_id else None
    if evidence and evidence.occurrence_id != row.id:
        evidence = None
    if item.evidence_required and item.evidence_type == "FILE" and not evidence:
        raise ConflictError(
            "CHECKLIST_EVIDENCE_REQUIRED", "Upload a valid evidence file for this checklist item."
        )
    if item.evidence_required and item.evidence_type != "FILE" and not data.evidence_reference:
        raise ConflictError("CHECKLIST_EVIDENCE_REQUIRED", "This item requires evidence.")
    item.state = "COMPLETED"
    item.result_note = data.note
    item.evidence_reference = data.evidence_reference
    item.evidence_id = evidence.id if evidence else None
    item.completed_at = server_now()
    item.completed_by_user_id = actor.id
    item.version += 1
    row.version += 1
    sync_occurrence_ticket_tasks(db, row)
    audit(db, actor, row, "service_checklist.item.completed", {"item_id": item.id})
    db.commit()
    db.refresh(row)
    return occurrence_read(db, row, detail=True)


@router.post("/occurrences/{occurrence_id}/items", response_model=OccurrenceRead, status_code=201)
def add_simple_item(
    occurrence_id: int,
    data: OccurrenceItemCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.perform")),
) -> OccurrenceRead:
    row = get_occurrence(db, occurrence_id)
    authorize_occurrence(db, actor, row)
    require_editable_occurrence(row)
    order = (
        db.scalar(
            select(func.max(ServiceChecklistOccurrenceItem.display_order)).where(
                ServiceChecklistOccurrenceItem.occurrence_id == row.id
            )
        )
        or 0
    )
    item = ServiceChecklistOccurrenceItem(
        occurrence_id=row.id,
        item_code=f"ROW_{server_now().strftime('%Y%m%d%H%M%S%f')}",
        title=data.title.strip(),
        resource_type=data.resource_type,
        resource_path=data.resource_path.strip() if data.resource_path else None,
        check_date=data.check_date,
        display_order=order + 1,
        is_required=True,
        original_responsibility="MILLENSYS",
        responsibility="MILLENSYS",
        evidence_type="NONE",
        evidence_required=False,
        state="PENDING",
    )
    db.add(item)
    db.flush()
    row.version += 1
    if row.ticket_id:
        db.add(
            TicketTask(
                ticket_id=row.ticket_id,
                title=item.title,
                description=f"Checklist task {item.item_code}\nPath or URL: {item.resource_path or '—'}",
                assigned_user_id=row.assigned_user_id,
                status="OPEN",
                is_required=True,
                due_at=row.due_at,
                created_by_user_id=actor.id,
            )
        )
    audit(
        db,
        actor,
        row,
        "service_checklist.item.added",
        {"type": data.resource_type, "label": item.title},
    )
    db.commit()
    db.refresh(row)
    return occurrence_read(db, row, detail=True)


@router.put("/occurrences/{occurrence_id}/items/{item_id}", response_model=OccurrenceRead)
def update_simple_item(
    occurrence_id: int,
    item_id: int,
    data: OccurrenceItemWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.perform")),
) -> OccurrenceRead:
    row = get_occurrence(db, occurrence_id)
    authorize_occurrence(db, actor, row)
    require_version(row, data.version)
    require_editable_occurrence(row)
    item = db.get(ServiceChecklistOccurrenceItem, item_id)
    if not item or item.occurrence_id != row.id:
        raise NotFoundError("The checklist item was not found.")
    if data.status == "CLIENT_RESPONSIBILITY":
        raise ConflictError(
            "CLIENT_ITEM_REQUIRES_HANDOFF",
            "Use the client handoff workflow and attach its evidence.",
        )
    if data.status == "COMPLETE" and item.evidence_required:
        raise ConflictError(
            "CHECKLIST_EVIDENCE_REQUIRED",
            "Use the evidence completion workflow for this required item.",
        )
    item.resource_type = data.resource_type
    item.title = data.title.strip()
    item.resource_path = data.resource_path.strip() if data.resource_path else None
    item.check_date = data.check_date
    item.state = data.status
    item.responsibility = "MILLENSYS"
    item.completed_at = server_now() if data.status == "COMPLETE" else None
    item.completed_by_user_id = actor.id if item.completed_at else None
    item.version += 1
    row.version += 1
    sync_occurrence_ticket_tasks(db, row)
    audit(
        db,
        actor,
        row,
        "service_checklist.item.updated",
        {"item_id": item.id, "status": data.status},
    )
    db.commit()
    db.refresh(row)
    return occurrence_read(db, row, detail=True)


@router.delete("/occurrences/{occurrence_id}/items/{item_id}", response_model=OccurrenceRead)
def delete_simple_item(
    occurrence_id: int,
    item_id: int,
    expected_version: int = Query(ge=1),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.perform")),
) -> OccurrenceRead:
    row = get_occurrence(db, occurrence_id)
    authorize_occurrence(db, actor, row)
    require_version(row, expected_version)
    require_editable_occurrence(row)
    item = db.get(ServiceChecklistOccurrenceItem, item_id)
    if not item or item.occurrence_id != row.id:
        raise NotFoundError("The checklist item was not found.")
    if row.ticket_id:
        task_marker = f"Checklist task {item.item_code}\n"
        task = db.scalar(
            select(TicketTask).where(
                TicketTask.ticket_id == row.ticket_id,
                TicketTask.description.startswith(task_marker),
            )
        )
        if task:
            db.delete(task)
    deleted = {"item_id": item.id, "item_code": item.item_code, "title": item.title}
    db.delete(item)
    row.version += 1
    audit(db, actor, row, "service_checklist.item.deleted", deleted)
    db.commit()
    db.refresh(row)
    return occurrence_read(db, row, detail=True)


@router.patch(
    "/occurrences/{occurrence_id}/items/{item_id}/details", response_model=OccurrenceRead
)
def update_item_details(
    occurrence_id: int,
    item_id: int,
    data: OccurrenceItemDetailsUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.perform")),
) -> OccurrenceRead:
    row = get_occurrence(db, occurrence_id)
    authorize_occurrence(db, actor, row)
    require_version(row, data.version)
    require_editable_occurrence(row)
    item = db.get(ServiceChecklistOccurrenceItem, item_id)
    if not item or item.occurrence_id != row.id:
        raise NotFoundError("The checklist item was not found.")
    item.resource_type = data.resource_type
    item.title = data.title.strip()
    item.resource_path = data.resource_path.strip() if data.resource_path else None
    item.check_date = data.check_date
    item.version += 1
    row.version += 1
    sync_occurrence_ticket_tasks(db, row)
    audit(db, actor, row, "service_checklist.item.details_updated", {"item_id": item.id})
    db.commit()
    db.refresh(row)
    return occurrence_read(db, row, detail=True)


@router.post(
    "/occurrences/{occurrence_id}/items/{item_id}/client-handoff", response_model=OccurrenceRead
)
def client_handoff(
    occurrence_id: int,
    item_id: int,
    data: ClientHandoffAction,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.perform")),
) -> OccurrenceRead:
    row = get_occurrence(db, occurrence_id)
    authorize_occurrence(db, actor, row)
    require_version(row, data.version)
    require_editable_occurrence(row)
    item = db.get(ServiceChecklistOccurrenceItem, item_id)
    if not item or item.occurrence_id != row.id:
        raise NotFoundError("The checklist item was not found.")
    evidence = db.get(ServiceChecklistEvidence, data.evidence_id)
    if not evidence or evidence.occurrence_id != row.id:
        raise ConflictError(
            "CHECKLIST_EVIDENCE_REQUIRED",
            "Upload valid evidence for this checklist before recording the handoff.",
        )
    old = item.responsibility
    item.responsibility = "CLIENT"
    item.state = "CLIENT_RESPONSIBLE"
    item.client_contact = data.client_contact.strip()
    item.client_expected_at = data.expected_at
    item.result_note = data.handoff_note.strip()
    item.evidence_id = evidence.id
    item.evidence_reference = (
        data.evidence_reference.strip() if data.evidence_reference else evidence.original_filename
    )
    item.evidence_required = True
    item.version += 1
    row.version += 1
    sync_occurrence_ticket_tasks(db, row)
    audit(
        db,
        actor,
        row,
        "service_checklist.item.client_handoff",
        {
            "item_id": item.id,
            "original_responsibility": old,
            "client_contact": item.client_contact,
            "evidence_reference": item.evidence_reference,
        },
    )
    db.commit()
    db.refresh(row)
    return occurrence_read(db, row, detail=True)


def completion_preview(db: Session, row: ServiceChecklistOccurrence) -> CompletionPreview:
    items = list(
        db.scalars(
            select(ServiceChecklistOccurrenceItem).where(
                ServiceChecklistOccurrenceItem.occurrence_id == row.id
            )
        )
    )
    eligible = [
        item.id
        for item in items
        if not item.is_required
        and item.responsibility != "CLIENT"
        and item.state == "PENDING"
        and not item.evidence_required
    ]
    blocking = [
        item.title
        for item in items
        if item.is_required
        and item.state
        not in {"COMPLETE", "COMPLETED", "CLIENT_RESPONSIBILITY", "CLIENT_RESPONSIBLE", "WAIVED"}
    ]
    gaps = [
        item.title
        for item in items
        if item.evidence_required
        and (
            (item.evidence_type == "FILE" and item.evidence_id is None)
            or (item.evidence_type != "FILE" and not item.evidence_reference)
        )
    ]
    handoffs = [
        item.title
        for item in items
        if item.state in {"CLIENT_RESPONSIBILITY", "CLIENT_RESPONSIBLE"}
    ]
    return CompletionPreview(
        can_complete=not blocking and not gaps,
        eligible_item_ids=eligible,
        blocking_items=blocking,
        client_handoffs=handoffs,
        evidence_gaps=gaps,
    )


@router.get("/occurrences/{occurrence_id}/completion-preview", response_model=CompletionPreview)
def preview_completion(
    occurrence_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.perform")),
) -> CompletionPreview:
    row = get_occurrence(db, occurrence_id)
    authorize_occurrence(db, actor, row)
    return completion_preview(db, row)


@router.post("/occurrences/{occurrence_id}/complete", response_model=CompleteOccurrenceResult)
def complete_occurrence(
    occurrence_id: int,
    data: CompleteOccurrenceAction,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.perform")),
) -> CompleteOccurrenceResult:
    row = get_occurrence(db, occurrence_id)
    authorize_occurrence(db, actor, row)
    require_version(row, data.version)
    if row.status not in {"IN_PROGRESS", "BLOCKED"}:
        raise ConflictError(
            "INVALID_CHECKLIST_TRANSITION", "Start the checklist before completing it."
        )
    preview = completion_preview(db, row)
    if data.complete_eligible_remaining:
        now = server_now()
        for item in db.scalars(
            select(ServiceChecklistOccurrenceItem).where(
                ServiceChecklistOccurrenceItem.id.in_(preview.eligible_item_ids)
            )
        ):
            item.state = "COMPLETED"
            item.completed_at = now
            item.completed_by_user_id = actor.id
            item.version += 1
        preview = completion_preview(db, row)
    if not preview.can_complete:
        raise ConflictError(
            "CHECKLIST_REQUIREMENTS_INCOMPLETE",
            "Required tasks or evidence still prevent completion.",
            {"blocking_items": preview.blocking_items, "evidence_gaps": preview.evidence_gaps},
        )
    now = server_now()
    row.status = "COMPLETED"
    row.completed_at = now
    row.completed_by_user_id = actor.id
    row.service_provided = data.service_provided.strip()
    row.completion_summary = data.completion_summary.strip()
    row.version += 1
    if not row.ticket_id:
        ensure_occurrence_ticket(db, row, actor)
    sync_occurrence_ticket_tasks(db, row)
    sync_ticket_status(db, row, actor, "CLOSED", "Checklist event completed")
    db.add(
        ServiceDeliveryRecord(
            occurrence_id=row.id,
            client_id=row.client_id,
            occurrence_number=row.occurrence_number,
            service_provided=row.service_provided,
            completion_summary=row.completion_summary,
            completed_at=now,
            completed_by_user_id=actor.id,
        )
    )
    next_row = None
    template = db.get(ServiceChecklistTemplate, row.template_id)
    if (
        row.recurrence_days
        and template
        and template.is_active
        and template.schedule_mode == "SCHEDULED"
    ):
        scheduled_at = row.scheduled_at + timedelta(days=row.recurrence_days)
        due_at = row.due_at + timedelta(days=row.recurrence_days)
        next_row = db.scalar(
            select(ServiceChecklistOccurrence).where(
                ServiceChecklistOccurrence.template_id == row.template_id,
                ServiceChecklistOccurrence.client_id == row.client_id,
                ServiceChecklistOccurrence.scheduled_at == scheduled_at,
            )
        )
        if not next_row:
            next_row = create_occurrence_row(
                db,
                OccurrenceCreate(
                    template_id=row.template_id,
                    client_id=row.client_id,
                    assigned_user_id=row.assigned_user_id,
                    scheduled_at=scheduled_at,
                    due_at=due_at,
                    recurrence_days=row.recurrence_days,
                ),
                actor,
                schedule_id=row.schedule_id,
            )
            audit(db, actor, next_row, "service_checklist.occurrence.next_generated")
    audit(db, actor, row, "service_checklist.occurrence.completed")
    db.commit()
    db.refresh(row)
    if next_row:
        db.refresh(next_row)
    return CompleteOccurrenceResult(
        occurrence=occurrence_read(db, row, detail=True),
        next_occurrence_id=next_row.id if next_row else None,
        next_occurrence_number=next_row.occurrence_number if next_row else None,
        next_scheduled_at=next_row.scheduled_at if next_row else None,
    )


def _create_checklist_follow_up(
    db: Session,
    occurrence: ServiceChecklistOccurrence,
    item: ServiceChecklistOccurrenceItem,
    actor: User,
    note: str,
) -> Ticket:
    key = f"checklist-follow-up:{occurrence.id}:{item.id}"
    existing = db.scalar(select(Ticket).where(Ticket.creation_idempotency_key == key))
    if existing:
        return existing
    ticket_type = db.scalar(select(TicketType).where(TicketType.code == "INCIDENT"))
    if not ticket_type:
        ticket_type = db.scalar(select(TicketType).where(TicketType.is_active.in_([True])))
    status = db.scalar(select(TicketStatus).where(TicketStatus.code == "OPEN"))
    if not status:
        status = db.scalar(select(TicketStatus).where(TicketStatus.code == "PENDING_INTERNAL"))
    if not ticket_type or not status:
        raise ConflictError(
            "FOLLOW_UP_TICKET_CONFIGURATION_MISSING",
            "Follow-up ticket configuration is missing.",
        )
    now = server_now()
    ticket = Ticket(
        ticket_type_id=ticket_type.id,
        client_id=occurrence.client_id,
        created_by_user_id=actor.id,
        status_id=status.id,
        assigned_user_id=occurrence.assigned_user_id or actor.id,
        source_channel="SCHEDULED_SERVICE",
        creation_idempotency_key=key,
        entitlement_status="PLANNED_SERVICE",
        impact="MEDIUM",
        urgency="MEDIUM",
        priority="P3",
        subject=f"Checklist follow-up · {item.title}",
        description=(
            f"Follow-up from checklist {occurrence.occurrence_number}.\n"
            f"Task: {item.title}\nPath or URL: {item.resource_path or '—'}\nNote: {note}"
        ),
        due_at=occurrence.due_at + timedelta(days=1),
        support_follow_up_flag=True,
        escalation_parent_ticket_id=occurrence.ticket_id,
        last_activity_at=now,
    )
    db.add(ticket)
    db.flush()
    ticket.ticket_number = f"{ticket_type.number_prefix}-{now.year}-{ticket.id:06d}"
    if ticket.assigned_user_id:
        db.add(
            TicketAssignmentHistory(
                ticket_id=ticket.id,
                assigned_user_id=ticket.assigned_user_id,
                assigned_team=None,
                assigned_by_user_id=actor.id,
                reason=f"Checklist follow-up from {occurrence.occurrence_number}",
                created_at=now,
            )
        )
    return ticket


@router.post(
    "/occurrences/{occurrence_id}/quick-complete",
    response_model=QuickCompleteResult,
)
def quick_complete_occurrence(
    occurrence_id: int,
    data: QuickCompleteAction,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.perform")),
) -> QuickCompleteResult:
    """Apply the engineer's complete checklist submission in one database transaction."""
    row = get_occurrence(db, occurrence_id)
    authorize_occurrence(db, actor, row)
    require_version(row, data.version)
    require_editable_occurrence(row)
    now = server_now()
    if row.status == "SCHEDULED":
        row.status = "IN_PROGRESS"
        row.started_at = now
    stored_items = {
        item.id: item
        for item in db.scalars(
            select(ServiceChecklistOccurrenceItem).where(
                ServiceChecklistOccurrenceItem.occurrence_id == row.id
            )
        )
    }
    submitted_ids = {entry.item_id for entry in data.items}
    missing_required = [
        item.title for item in stored_items.values() if item.is_required and item.id not in submitted_ids
    ]
    errors: list[dict[str, object]] = []
    follow_up_numbers: list[str] = []
    for entry in data.items:
        item = stored_items.get(entry.item_id)
        if not item:
            errors.append({"item_id": entry.item_id, "field": "item", "message": "Task not found."})
            continue
        note = entry.note.strip() if entry.note else None
        contact = entry.client_contact.strip() if entry.client_contact else None
        evidence = db.get(ServiceChecklistEvidence, entry.evidence_id) if entry.evidence_id else None
        if evidence and evidence.occurrence_id != row.id:
            evidence = None
        if entry.choice == "DONE" and item.evidence_required:
            if item.evidence_type == "FILE" and not evidence:
                errors.append({"item_id": item.id, "field": "evidence", "message": "Attach evidence."})
            elif item.evidence_type != "FILE" and not (entry.evidence_reference or note):
                errors.append({"item_id": item.id, "field": "evidence", "message": "Enter evidence or a result note."})
        if entry.choice == "NEEDS_ATTENTION" and not note:
            errors.append({"item_id": item.id, "field": "note", "message": "Enter a short attention note."})
        if entry.choice == "CLIENT_ACTION":
            if not contact:
                errors.append({"item_id": item.id, "field": "client_contact", "message": "Enter the client contact."})
            if not note:
                errors.append({"item_id": item.id, "field": "note", "message": "Enter the handoff note."})
            if not evidence:
                errors.append({"item_id": item.id, "field": "evidence", "message": "Attach handoff evidence."})
        item.resource_path = entry.resource_path.strip() if entry.resource_path else None
        item.check_date = entry.check_date
        item.result_note = note
        item.evidence_reference = entry.evidence_reference or (evidence.original_filename if evidence else None)
        item.evidence_id = evidence.id if evidence else None
        item.client_contact = contact
    if missing_required:
        errors.extend(
            {"item_id": None, "field": "item", "message": f"Required task is missing: {title}"}
            for title in missing_required
        )
    if errors:
        db.rollback()
        raise ConflictError(
            "CHECKLIST_QUICK_COMPLETE_INVALID",
            "Correct the highlighted checklist tasks and try again.",
            {"items": errors},
        )
    for entry in data.items:
        item = stored_items[entry.item_id]
        note = entry.note.strip() if entry.note else ""
        if entry.choice == "CLIENT_ACTION":
            item.state = "CLIENT_RESPONSIBILITY"
            item.responsibility = "CLIENT"
        elif entry.choice == "NEEDS_ATTENTION":
            if entry.create_follow_up_ticket:
                follow_up = _create_checklist_follow_up(db, row, item, actor, note)
                follow_up_numbers.append(str(follow_up.ticket_number))
                item.state = "COMPLETED" if data.complete else "NEED_ATTENTION"
            else:
                item.state = "NEED_ATTENTION"
        else:
            item.state = "COMPLETED"
            item.responsibility = "MILLENSYS"
        if item.state in {"COMPLETED", "CLIENT_RESPONSIBILITY"}:
            item.completed_at = now
            item.completed_by_user_id = actor.id
        else:
            item.completed_at = None
            item.completed_by_user_id = None
        item.version += 1
    row.version += 1
    if not row.ticket_id:
        ensure_occurrence_ticket(db, row, actor)
    sync_occurrence_ticket_tasks(db, row)
    if not data.complete:
        audit(db, actor, row, "service_checklist.quick_draft_saved")
        db.commit()
        db.refresh(row)
        return QuickCompleteResult(
            occurrence=occurrence_read(db, row, detail=True),
            follow_up_ticket_numbers=follow_up_numbers,
        )
    preview = completion_preview(db, row)
    if not preview.can_complete:
        db.rollback()
        raise ConflictError(
            "CHECKLIST_REQUIREMENTS_INCOMPLETE",
            "Correct the highlighted checklist tasks and try again.",
            {"blocking_items": preview.blocking_items, "evidence_gaps": preview.evidence_gaps},
        )
    row.status = "COMPLETED"
    row.completed_at = now
    row.completed_by_user_id = actor.id
    row.service_provided = data.service_provided.strip()
    row.completion_summary = data.completion_summary.strip()
    sync_ticket_status(db, row, actor, "CLOSED", "Checklist quick completion")
    db.add(
        ServiceDeliveryRecord(
            occurrence_id=row.id,
            client_id=row.client_id,
            occurrence_number=row.occurrence_number,
            service_provided=row.service_provided,
            completion_summary=row.completion_summary,
            completed_at=now,
            completed_by_user_id=actor.id,
        )
    )
    next_row = None
    template = db.get(ServiceChecklistTemplate, row.template_id)
    if row.recurrence_days and template and template.is_active and template.schedule_mode == "SCHEDULED":
        scheduled_at = row.scheduled_at + timedelta(days=row.recurrence_days)
        next_row = db.scalar(
            select(ServiceChecklistOccurrence).where(
                ServiceChecklistOccurrence.template_id == row.template_id,
                ServiceChecklistOccurrence.client_id == row.client_id,
                ServiceChecklistOccurrence.scheduled_at == scheduled_at,
            )
        )
        if not next_row:
            next_row = create_occurrence_row(
                db,
                OccurrenceCreate(
                    template_id=row.template_id,
                    client_id=row.client_id,
                    assigned_user_id=row.assigned_user_id,
                    scheduled_at=scheduled_at,
                    due_at=row.due_at + timedelta(days=row.recurrence_days),
                    recurrence_days=row.recurrence_days,
                ),
                actor,
                schedule_id=row.schedule_id,
            )
    audit(db, actor, row, "service_checklist.quick_completed")
    db.commit()
    db.refresh(row)
    if next_row:
        db.refresh(next_row)
    return QuickCompleteResult(
        occurrence=occurrence_read(db, row, detail=True),
        follow_up_ticket_numbers=follow_up_numbers,
        next_occurrence_id=next_row.id if next_row else None,
        next_occurrence_number=next_row.occurrence_number if next_row else None,
        next_scheduled_at=next_row.scheduled_at if next_row else None,
    )


@router.post("/occurrences/{occurrence_id}/evidence", response_model=EvidenceRead, status_code=201)
async def upload_evidence(
    occurrence_id: int,
    upload: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.perform")),
    settings: Settings = Depends(get_settings),
) -> EvidenceRead:
    occurrence = get_occurrence(db, occurrence_id)
    authorize_occurrence(db, actor, occurrence)
    require_editable_occurrence(occurrence)
    original, stored, content_type, size = await store_evidence(upload, occurrence_id, settings)
    evidence = ServiceChecklistEvidence(
        occurrence_id=occurrence_id,
        original_filename=original,
        stored_filename=stored,
        content_type=content_type,
        size_bytes=size,
        uploaded_by_user_id=actor.id,
    )
    db.add(evidence)
    db.flush()
    audit(
        db,
        actor,
        occurrence,
        "service_checklist.evidence.uploaded",
        {"evidence_id": evidence.id, "filename": original, "size_bytes": size},
    )
    db.commit()
    db.refresh(evidence)
    return EvidenceRead.model_validate(evidence, from_attributes=True)


@router.get("/occurrences/{occurrence_id}/evidence/{evidence_id}/download")
def download_evidence(
    occurrence_id: int,
    evidence_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_any_permission(
            "service_checklist.view_own",
            "service_checklist.view_team",
            "service_checklist.view_all",
        )
    ),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    occurrence = get_occurrence(db, occurrence_id)
    authorize_occurrence(db, actor, occurrence)
    evidence = db.get(ServiceChecklistEvidence, evidence_id)
    if not evidence or evidence.occurrence_id != occurrence.id:
        raise NotFoundError("Checklist evidence was not found.")
    audit(
        db, actor, occurrence, "service_checklist.evidence.downloaded", {"evidence_id": evidence.id}
    )
    db.commit()
    return FileResponse(
        evidence_path(evidence, settings),
        media_type=evidence.content_type,
        filename=evidence.original_filename,
    )


@router.post("/occurrences/{occurrence_id}/reassign", response_model=OccurrenceRead)
def reassign_occurrence(
    occurrence_id: int,
    data: ReassignAction,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.reassign")),
) -> OccurrenceRead:
    row = get_occurrence(db, occurrence_id)
    authorize_occurrence(db, actor, row)
    require_version(row, data.version)
    target = checklist_assignee(db, data.assigned_user_id)
    previous = row.assigned_user_id
    row.assigned_user_id = target.id
    row.version += 1
    ticket = db.get(Ticket, row.ticket_id) if row.ticket_id else None
    if ticket:
        ticket.assigned_user_id = target.id
        ticket.version += 1
        db.add(
            TicketAssignmentHistory(
                ticket_id=ticket.id,
                assigned_user_id=target.id,
                assigned_team=None,
                assigned_by_user_id=actor.id,
                reason=data.reason,
                created_at=server_now(),
            )
        )
        sync_occurrence_ticket_tasks(db, row)
    db.add(
        Notification(
            recipient_user_id=target.id,
            notification_type="SERVICE_CHECKLIST_ASSIGNED",
            severity="INFO",
            title=f"Checklist assigned: {row.occurrence_number}",
            message=data.reason,
            deep_link="/service-checklists",
            deduplication_key=f"checklist-reassigned:{row.id}:version:{row.version}:user:{target.id}",
        )
    )
    audit(
        db,
        actor,
        row,
        "service_checklist.occurrence.reassigned",
        {"from_user_id": previous, "to_user_id": target.id, "reason": data.reason},
    )
    db.commit()
    db.refresh(row)
    return occurrence_read(db, row, detail=True)


@router.post("/occurrences/{occurrence_id}/cancel", response_model=OccurrenceRead)
def cancel_occurrence(
    occurrence_id: int,
    data: CancelAction,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.schedule.manage")),
) -> OccurrenceRead:
    row = get_occurrence(db, occurrence_id)
    require_version(row, data.version)
    if row.status == "COMPLETED":
        raise ConflictError(
            "COMPLETED_CHECKLIST_CANNOT_CANCEL", "A completed checklist cannot be cancelled."
        )
    row.status = "CANCELLED"
    row.cancelled_at = server_now()
    row.version += 1
    sync_ticket_status(db, row, actor, "CANCELLED", data.reason)
    audit(db, actor, row, "service_checklist.occurrence.cancelled", {"reason": data.reason})
    db.commit()
    db.refresh(row)
    return occurrence_read(db, row, detail=True)


def schedule_read(db: Session, row: ServiceChecklistSchedule) -> ScheduleRead:
    client = db.get(Client, row.client_id)
    template = db.get(ServiceChecklistTemplate, row.template_id)
    owner = db.get(User, row.assigned_user_id) if row.assigned_user_id else None
    current = db.scalar(
        select(ServiceChecklistOccurrence)
        .where(
            ServiceChecklistOccurrence.schedule_id == row.id,
            ServiceChecklistOccurrence.status.in_(("SCHEDULED", "IN_PROGRESS", "BLOCKED")),
        )
        .order_by(ServiceChecklistOccurrence.due_at, ServiceChecklistOccurrence.id)
    )
    latest_completed = db.scalar(
        select(ServiceChecklistOccurrence)
        .where(
            ServiceChecklistOccurrence.schedule_id == row.id,
            ServiceChecklistOccurrence.status == "COMPLETED",
        )
        .order_by(
            ServiceChecklistOccurrence.completed_at.desc(), ServiceChecklistOccurrence.id.desc()
        )
    )
    latest = current or latest_completed
    latest_read = occurrence_read(db, latest) if latest else None
    values = ScheduleRead.model_validate(row, from_attributes=True).model_dump()
    values.update(
        client_name=client.name if client else "",
        template_name=template.name if template else "",
        assigned_user_name=owner.full_name if owner else None,
        last_occurrence_id=latest.id if latest else None,
        last_occurrence_number=latest.occurrence_number if latest else None,
        last_status=latest.status if latest else None,
        last_workflow_status=latest_read.workflow_status if latest_read else None,
        last_due_at=current.due_at if current else None,
        last_completed_at=latest_completed.completed_at if latest_completed else None,
        last_required_complete=latest_read.required_complete if latest_read else 0,
        last_required_total=latest_read.required_total if latest_read else 0,
        last_evidence_gaps=latest_read.evidence_gaps if latest_read else 0,
    )
    return ScheduleRead(**values)


@router.get("/schedules", response_model=list[ScheduleRead])
def list_schedules(
    scope: str | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_any_permission(
            "service_checklist.view_own",
            "service_checklist.view_team",
            "service_checklist.view_all",
            "service_checklist.schedule.manage",
        )
    ),
) -> list[ScheduleRead]:
    permissions = set(effective_permissions(db, actor).permissions)
    query = select(ServiceChecklistSchedule).order_by(ServiceChecklistSchedule.next_generate_at)
    if scope == "mine":
        query = query.where(ServiceChecklistSchedule.assigned_user_id == actor.id)
    elif not permissions & {"service_checklist.view_all", "service_checklist.schedule.manage"}:
        if "service_checklist.view_team" in permissions and actor.department_id:
            query = query.join(User, User.id == ServiceChecklistSchedule.assigned_user_id).where(
                User.department_id == actor.department_id
            )
        else:
            query = query.where(ServiceChecklistSchedule.assigned_user_id == actor.id)
    return [schedule_read(db, row) for row in db.scalars(query)]


@router.get("/schedules/{schedule_id}/history", response_model=list[OccurrenceRead])
def schedule_history(
    schedule_id: int,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_any_permission(
            "service_checklist.view_own",
            "service_checklist.view_team",
            "service_checklist.view_all",
        )
    ),
) -> list[OccurrenceRead]:
    schedule = db.get(ServiceChecklistSchedule, schedule_id)
    if not schedule:
        raise NotFoundError("The checklist assignment was not found.")
    authorize_schedule(db, actor, schedule)
    query = select(ServiceChecklistOccurrence).where(
        ServiceChecklistOccurrence.schedule_id == schedule.id
    )
    if date_from:
        query = query.where(ServiceChecklistOccurrence.scheduled_at >= date_from)
    if date_to:
        query = query.where(ServiceChecklistOccurrence.scheduled_at <= date_to)
    query = query.order_by(
        ServiceChecklistOccurrence.scheduled_at.desc(),
        ServiceChecklistOccurrence.id.desc(),
    )
    return [occurrence_read(db, row) for row in db.scalars(query.limit(500))]


@router.post("/schedules/{schedule_id}/events", response_model=OccurrenceRead)
def add_schedule_event(
    schedule_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.perform")),
) -> OccurrenceRead:
    schedule = db.get(ServiceChecklistSchedule, schedule_id)
    if not schedule or not schedule.is_active or schedule.is_paused:
        raise NotFoundError("The active checklist assignment was not found.")
    permissions = set(effective_permissions(db, actor).permissions)
    if schedule.assigned_user_id != actor.id and not permissions & {
        "service_checklist.view_all",
        "service_checklist.schedule.manage",
    }:
        raise AuthorizationError("Only the assigned engineer can add a checklist event.")
    open_event = db.scalar(
        select(ServiceChecklistOccurrence)
        .where(
            ServiceChecklistOccurrence.schedule_id == schedule.id,
            ServiceChecklistOccurrence.status.in_(("SCHEDULED", "IN_PROGRESS", "BLOCKED")),
        )
        .order_by(ServiceChecklistOccurrence.scheduled_at.desc())
    )
    if open_event:
        if open_event.status == "SCHEDULED":
            open_event.status = "IN_PROGRESS"
            open_event.started_at = server_now()
            open_event.version += 1
            audit(db, actor, open_event, "service_checklist.event.opened")
            db.commit()
            db.refresh(open_event)
        return occurrence_read(db, open_event, detail=True)
    now = server_now()
    row = create_occurrence_row(
        db,
        OccurrenceCreate(
            template_id=schedule.template_id,
            client_id=schedule.client_id,
            assigned_user_id=schedule.assigned_user_id or actor.id,
            scheduled_at=now,
            due_at=now + timedelta(minutes=schedule.duration_minutes),
            recurrence_days=schedule.interval_days,
        ),
        actor,
        schedule_id=schedule.id,
        carry_forward_items=False,
    )
    row.status = "IN_PROGRESS"
    row.started_at = now
    row.version += 1
    schedule.next_generate_at = now + timedelta(days=schedule.interval_days)
    schedule.version += 1
    audit(db, actor, row, "service_checklist.event.created", {"schedule_id": schedule.id})
    db.commit()
    db.refresh(row)
    return occurrence_read(db, row, detail=True)


@router.post("/schedules/{schedule_id}/reminder")
def send_assignment_reminder(
    schedule_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_any_permission(
            "service_checklist.view_team",
            "service_checklist.view_all",
            "service_checklist.reassign",
            "service_checklist.schedule.manage",
        )
    ),
) -> dict[str, object]:
    return _send_assignment_reminder(db, actor, schedule_id)


def _send_assignment_reminder(
    db: Session, actor: User, schedule_id: int, *, commit: bool = True
) -> dict[str, object]:
    schedule = db.get(ServiceChecklistSchedule, schedule_id)
    if not schedule or not schedule.assigned_user_id:
        raise NotFoundError("The assigned checklist was not found.")
    if schedule.is_paused or not schedule.is_active:
        raise ConflictError(
            "CHECKLIST_SCHEDULE_PAUSED",
            "A reminder cannot be sent for a paused or inactive checklist schedule.",
        )
    permissions = set(effective_permissions(db, actor).permissions)
    owner = db.get(User, schedule.assigned_user_id)
    if not permissions & {"service_checklist.view_all", "service_checklist.schedule.manage"}:
        if not (
            "service_checklist.view_team" in permissions
            and owner
            and actor.department_id
            and owner.department_id == actor.department_id
        ):
            raise AuthorizationError("You cannot remind an engineer outside your team.")
    latest = db.scalar(
        select(ServiceChecklistOccurrence)
        .where(ServiceChecklistOccurrence.schedule_id == schedule.id)
        .order_by(ServiceChecklistOccurrence.scheduled_at.desc())
    )
    attention_required = bool(
        as_server_time(schedule.next_generate_at) < server_now()
        or (latest and occurrence_read(db, latest).workflow_status == "NEED_ATTENTION")
    )
    if not attention_required:
        raise ConflictError(
            "CHECKLIST_REMINDER_NOT_REQUIRED",
            "A reminder can be sent only for a missed checklist or an event needing attention.",
        )
    client = db.get(Client, schedule.client_id)
    template = db.get(ServiceChecklistTemplate, schedule.template_id)
    key = f"checklist-manual-reminder:{schedule.id}:{server_now().date().isoformat()}"
    existing = db.scalar(select(Notification).where(Notification.deduplication_key == key))
    if existing:
        return {"sent": False, "deduplicated": True}
    db.add(
        Notification(
            recipient_user_id=schedule.assigned_user_id,
            notification_type="SERVICE_CHECKLIST_MANUAL_REMINDER",
            severity="WARNING",
            title=f"Checklist attention: {client.name if client else 'Client checklist'}",
            message=(
                f"{template.name if template else 'Checklist'} needs completion or attention. "
                f"Reminder sent by {actor.full_name}."
            ),
            deep_link="/service-checklists",
            deduplication_key=key,
        )
    )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ServiceChecklistSchedule",
            entity_id=str(schedule.id),
            action="service_checklist.assignment.reminder_sent",
            new_values_json=json.dumps({"recipient_user_id": schedule.assigned_user_id}),
        )
    )
    if commit:
        db.commit()
    return {"sent": True, "deduplicated": False}


@router.post("/schedules/bulk-reminders")
def send_bulk_assignment_reminders(
    data: BulkScheduleReminderAction,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_any_permission(
            "service_checklist.view_team",
            "service_checklist.view_all",
            "service_checklist.reassign",
            "service_checklist.schedule.manage",
        )
    ),
) -> dict[str, int]:
    sent = deduplicated = 0
    for schedule_id in dict.fromkeys(data.schedule_ids):
        result = _send_assignment_reminder(db, actor, schedule_id, commit=False)
        sent += int(bool(result["sent"]))
        deduplicated += int(bool(result["deduplicated"]))
    db.commit()
    return {"sent": sent, "deduplicated": deduplicated}


@router.post("/schedules/preview", response_model=list[SchedulePreview])
def preview_schedule(
    data: ScheduleCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.schedule.manage")),
) -> list[SchedulePreview]:
    del actor
    rows = []
    for index in range(5):
        scheduled_at = data.starts_at + timedelta(days=data.interval_days * index)
        exists = (
            db.scalar(
                select(ServiceChecklistOccurrence.id).where(
                    ServiceChecklistOccurrence.template_id == data.template_id,
                    ServiceChecklistOccurrence.client_id == data.client_id,
                    ServiceChecklistOccurrence.scheduled_at == scheduled_at,
                )
            )
            is not None
        )
        rows.append(
            SchedulePreview(
                scheduled_at=scheduled_at,
                due_at=scheduled_at + timedelta(minutes=data.duration_minutes),
                already_exists=exists,
            )
        )
    return rows


@router.post("/schedules", response_model=ScheduleRead, status_code=201)
def create_schedule(
    data: ScheduleCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.schedule.manage")),
) -> ScheduleRead:
    template = db.get(ServiceChecklistTemplate, data.template_id)
    if (
        not template
        or template.publication_status != "PUBLISHED"
        or template.schedule_mode != "SCHEDULED"
    ):
        raise ConflictError(
            "CHECKLIST_SCHEDULE_TEMPLATE_INVALID",
            "Schedules require an active published Scheduled template.",
        )
    if not db.get(Client, data.client_id):
        raise NotFoundError("The client was not found.")
    assigned_user_id = data.assigned_user_id or actor.id
    checklist_assignee(db, assigned_user_id)
    values = data.model_dump()
    values["assigned_user_id"] = assigned_user_id
    row = ServiceChecklistSchedule(
        **values, next_generate_at=data.starts_at, created_by_user_id=actor.id
    )
    db.add(row)
    db.flush()
    occurrence = create_occurrence_row(
        db,
        OccurrenceCreate(
            template_id=row.template_id,
            client_id=row.client_id,
            assigned_user_id=row.assigned_user_id,
            scheduled_at=row.next_generate_at,
            due_at=row.next_generate_at + timedelta(minutes=row.duration_minutes),
            recurrence_days=row.interval_days,
        ),
        actor,
        schedule_id=row.id,
    )
    row.next_generate_at += timedelta(days=row.interval_days)
    audit(db, actor, occurrence, "service_checklist.schedule.activated", {"schedule_id": row.id})
    db.commit()
    db.refresh(row)
    return schedule_read(db, row)


@router.post("/schedules/{schedule_id}/state", response_model=ScheduleRead)
def set_schedule_state(
    schedule_id: int,
    data: ScheduleStateAction,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_any_permission(
            "service_checklist.view_own",
            "service_checklist.view_team",
            "service_checklist.view_all",
            "service_checklist.schedule.manage",
        )
    ),
) -> ScheduleRead:
    row = db.get(ServiceChecklistSchedule, schedule_id)
    if not row:
        raise NotFoundError("The checklist schedule was not found.")
    authorize_schedule(db, actor, row)
    if row.version != data.version:
        raise ConflictError("STALE_DATA", "The schedule changed. Reload it and try again.")
    if not data.paused:
        template = db.get(ServiceChecklistTemplate, row.template_id)
        if not template or not template.is_active or template.publication_status != "PUBLISHED":
            raise ConflictError(
                "CHECKLIST_SCHEDULE_TEMPLATE_INVALID",
                "This schedule cannot resume because its template is not active and published.",
            )
    row.is_paused = data.paused
    row.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ServiceChecklistSchedule",
            entity_id=str(row.id),
            action="service_checklist.schedule.paused"
            if data.paused
            else "service_checklist.schedule.resumed",
        )
    )
    db.commit()
    db.refresh(row)
    return schedule_read(db, row)


@router.post("/schedules/{schedule_id}/cadence", response_model=ScheduleRead)
def set_schedule_cadence(
    schedule_id: int,
    data: ScheduleCadenceAction,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_any_permission(
            "service_checklist.view_own",
            "service_checklist.view_team",
            "service_checklist.view_all",
            "service_checklist.schedule.manage",
        )
    ),
) -> ScheduleRead:
    row = db.get(ServiceChecklistSchedule, schedule_id)
    if not row:
        raise NotFoundError("The checklist schedule was not found.")
    authorize_schedule(db, actor, row)
    if row.version != data.version:
        raise ConflictError("STALE_DATA", "The schedule changed. Reload it and try again.")
    now = server_now()
    future_rows = list(
        db.scalars(
            select(ServiceChecklistOccurrence).where(
                ServiceChecklistOccurrence.schedule_id == row.id,
                ServiceChecklistOccurrence.status == "SCHEDULED",
                ServiceChecklistOccurrence.scheduled_at > now,
            )
        )
    )
    reason = f"Schedule cadence changed to every {data.interval_days} days"
    for occurrence in future_rows:
        occurrence.status = "CANCELLED"
        occurrence.cancelled_at = now
        occurrence.version += 1
        sync_ticket_status(db, occurrence, actor, "CANCELLED", reason)
    previous_interval = row.interval_days
    row.interval_days = data.interval_days
    row.next_generate_at = now + timedelta(days=data.interval_days)
    row.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ServiceChecklistSchedule",
            entity_id=str(row.id),
            action="service_checklist.schedule.cadence_changed",
            old_values_json=json.dumps({"interval_days": previous_interval}),
            new_values_json=json.dumps(
                {
                    "interval_days": data.interval_days,
                    "cancelled_future_occurrences": len(future_rows),
                }
            ),
        )
    )
    db.commit()
    db.refresh(row)
    return schedule_read(db, row)


@router.post("/schedules/{schedule_id}/reassign", response_model=ScheduleRead)
def reassign_schedule(
    schedule_id: int,
    data: ScheduleReassignAction,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.schedule.manage")),
) -> ScheduleRead:
    row = db.get(ServiceChecklistSchedule, schedule_id)
    if not row:
        raise NotFoundError("The checklist schedule was not found.")
    if row.version != data.version:
        raise ConflictError("STALE_DATA", "The schedule changed. Reload it and try again.")
    assignee = checklist_assignee(db, data.assigned_user_id)
    previous_user_id = row.assigned_user_id
    row.assigned_user_id = assignee.id
    row.version += 1
    open_rows = list(
        db.scalars(
            select(ServiceChecklistOccurrence).where(
                ServiceChecklistOccurrence.schedule_id == row.id,
                ServiceChecklistOccurrence.status.in_(("SCHEDULED", "IN_PROGRESS", "BLOCKED")),
            )
        )
    )
    for occurrence in open_rows:
        occurrence.assigned_user_id = assignee.id
        occurrence.version += 1
        ticket = db.get(Ticket, occurrence.ticket_id) if occurrence.ticket_id else None
        if ticket:
            ticket.assigned_user_id = assignee.id
            ticket.version += 1
            sync_occurrence_ticket_tasks(db, occurrence)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ServiceChecklistSchedule",
            entity_id=str(row.id),
            action="service_checklist.schedule.reassigned",
            reason=data.reason.strip(),
            old_values_json=json.dumps({"assigned_user_id": previous_user_id}),
            new_values_json=json.dumps(
                {"assigned_user_id": assignee.id, "open_occurrences_updated": len(open_rows)}
            ),
        )
    )
    db.commit()
    db.refresh(row)
    return schedule_read(db, row)


def _transfer_schedule(
    db: Session, row: ServiceChecklistSchedule, assigned_user_id: int, actor: User, reason: str
) -> int:
    previous_user_id = row.assigned_user_id
    row.assigned_user_id = assigned_user_id
    row.version += 1
    open_rows = list(
        db.scalars(
            select(ServiceChecklistOccurrence).where(
                ServiceChecklistOccurrence.schedule_id == row.id,
                ServiceChecklistOccurrence.status.in_(("SCHEDULED", "IN_PROGRESS", "BLOCKED")),
            )
        )
    )
    for occurrence in open_rows:
        occurrence.assigned_user_id = assigned_user_id
        occurrence.version += 1
        ticket = db.get(Ticket, occurrence.ticket_id) if occurrence.ticket_id else None
        if ticket:
            ticket.assigned_user_id = assigned_user_id
            ticket.version += 1
            sync_occurrence_ticket_tasks(db, occurrence)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ServiceChecklistSchedule",
            entity_id=str(row.id),
            action="service_checklist.schedule.reassigned",
            reason=reason,
            old_values_json=json.dumps({"assigned_user_id": previous_user_id}),
            new_values_json=json.dumps(
                {"assigned_user_id": assigned_user_id, "open_occurrences_updated": len(open_rows)}
            ),
        )
    )
    return len(open_rows)


@router.post("/schedules/bulk-transfer")
def bulk_transfer_schedules(
    data: BulkScheduleTransferAction,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.schedule.manage")),
) -> dict[str, int]:
    assignee = checklist_assignee(db, data.assigned_user_id)
    transferred = open_occurrences = 0
    for item in data.items:
        row = db.get(ServiceChecklistSchedule, item.schedule_id)
        if not row:
            raise NotFoundError(f"Checklist plan {item.schedule_id} was not found.")
        if row.version != item.version:
            raise ConflictError(
                "STALE_DATA", f"Checklist plan {item.schedule_id} changed. Reload and try again."
            )
        open_occurrences += _transfer_schedule(db, row, assignee.id, actor, data.reason.strip())
        transferred += 1
    db.commit()
    return {"transferred": transferred, "open_occurrences_updated": open_occurrences}


@router.post("/schedules/bulk-assign")
def bulk_assign_schedules(
    data: BulkScheduleAssignAction,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.schedule.manage")),
) -> dict[str, object]:
    assignee = checklist_assignee(db, data.assigned_user_id)
    template = db.get(ServiceChecklistTemplate, data.template_id)
    if (
        not template
        or template.publication_status != "PUBLISHED"
        or template.schedule_mode != "SCHEDULED"
    ):
        raise ConflictError(
            "CHECKLIST_SCHEDULE_TEMPLATE_INVALID",
            "Bulk assignment requires an active published Scheduled template.",
        )
    client_ids = list(dict.fromkeys(data.client_ids))
    clients = {row.id: row for row in db.scalars(select(Client).where(Client.id.in_(client_ids)))}
    if len(clients) != len(client_ids):
        raise ConflictError("CHECKLIST_CLIENT_MISSING", "Every selected client must exist.")
    timezone_name = server_clock_settings()[0]
    created = 0
    skipped: list[int] = []
    for client_id in client_ids:
        existing = db.scalar(
            select(ServiceChecklistSchedule.id).where(
                ServiceChecklistSchedule.client_id == client_id,
                ServiceChecklistSchedule.template_id == template.id,
                ServiceChecklistSchedule.is_active.in_([True]),
            )
        )
        if existing:
            skipped.append(client_id)
            continue
        customer = clients[client_id]
        row = ServiceChecklistSchedule(
            name=f"{customer.name} · {template.name}",
            template_id=template.id,
            client_id=client_id,
            assigned_user_id=assignee.id,
            starts_at=data.starts_at,
            next_generate_at=data.starts_at,
            interval_days=data.interval_days,
            duration_minutes=data.duration_minutes,
            timezone=timezone_name,
            created_by_user_id=actor.id,
        )
        db.add(row)
        db.flush()
        occurrence = create_occurrence_row(
            db,
            OccurrenceCreate(
                template_id=template.id,
                client_id=client_id,
                assigned_user_id=assignee.id,
                scheduled_at=data.starts_at,
                due_at=data.starts_at + timedelta(minutes=data.duration_minutes),
                recurrence_days=data.interval_days,
            ),
            actor,
            schedule_id=row.id,
        )
        row.next_generate_at += timedelta(days=data.interval_days)
        audit(
            db,
            actor,
            occurrence,
            "service_checklist.schedule.bulk_assigned",
            {"schedule_id": row.id},
        )
        created += 1
    db.commit()
    return {"created": created, "skipped": len(skipped), "skipped_client_ids": skipped}


def _frequency_days(value: str) -> int:
    normalized = value.strip().upper()
    mapping = {"DAILY": 1, "WEEKLY": 7, "MONTHLY": 30}
    if normalized not in mapping:
        raise ValueError("Frequency must be DAILY, WEEKLY, or MONTHLY.")
    return mapping[normalized]


@router.get("/assignments/import-template")
def export_assignment_template(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.schedule.manage")),
) -> StreamingResponse:
    del actor
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Assignments"
    headers = [
        "Client Code",
        "Engineer Username",
        "Template Code",
        "Frequency",
        "Start Date",
        "Start Time",
        "Duration Minutes",
        "Active",
    ]
    sheet.append(headers)
    sheet.append(
        [
            "EXAMPLE_CLIENT",
            "engineer.username",
            "EXAMPLE_TEMPLATE",
            "WEEKLY",
            server_now().date(),
            "09:00",
            120,
            "YES",
        ]
    )
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
    for cell in sheet[2]:
        cell.fill = PatternFill("solid", fgColor="FFF2CC")
    sheet["A3"] = (
        "Replace or delete the yellow example row before import. Frequency: DAILY, WEEKLY, or MONTHLY."
    )
    sheet["A3"].font = Font(italic=True, color="7F6000")
    widths = [20, 24, 24, 14, 15, 12, 18, 12]
    for index, width in enumerate(widths, 1):
        sheet.column_dimensions[chr(64 + index)].width = width
    sheet.freeze_panes = "A2"
    clients = workbook.create_sheet("Clients")
    clients.append(["Client Code", "Client Name"])
    for client_row in db.scalars(select(Client).order_by(Client.name)):
        clients.append([client_row.code, client_row.name])
    engineers = workbook.create_sheet("Engineers")
    engineers.append(["Username", "Engineer Name"])
    for engineer_row in db.scalars(
        select(User).where(User.is_active.in_([True])).order_by(User.full_name)
    ):
        engineers.append([engineer_row.username, engineer_row.full_name])
    templates = workbook.create_sheet("Templates")
    templates.append(["Template Code", "Template Name"])
    for template_row in db.scalars(
        select(ServiceChecklistTemplate)
        .where(
            ServiceChecklistTemplate.is_active.in_([True]),
            ServiceChecklistTemplate.publication_status == "PUBLISHED",
            ServiceChecklistTemplate.schedule_mode == "SCHEDULED",
        )
        .order_by(ServiceChecklistTemplate.name)
    ):
        templates.append([template_row.code, template_row.name])
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="service-checklist-assignments.xlsx"'
        },
    )


@router.post("/assignments/import")
async def import_assignments(
    upload: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.schedule.manage")),
) -> dict[str, object]:
    if not (upload.filename or "").lower().endswith(".xlsx"):
        raise ConflictError(
            "CHECKLIST_IMPORT_FILE_INVALID", "Upload the Excel .xlsx assignment template."
        )
    try:
        workbook = load_workbook(BytesIO(await upload.read()), read_only=True, data_only=True)
        sheet = workbook["Assignments"]
    except Exception as exc:
        raise ConflictError(
            "CHECKLIST_IMPORT_FILE_INVALID", "The assignment workbook could not be read."
        ) from exc
    created = 0
    errors: list[dict[str, object]] = []
    for row_number, values in enumerate(sheet.iter_rows(min_row=2, values_only=True), 2):
        if not any(value not in (None, "") for value in values):
            continue
        try:
            (
                client_code,
                username,
                template_code,
                frequency,
                start_date,
                start_time,
                duration,
                active,
            ) = values[:8]
            client = db.scalar(select(Client).where(Client.code == str(client_code).strip()))
            engineer = db.scalar(
                select(User).where(
                    User.username_normalized == str(username).strip().casefold(),
                    User.is_active.in_([True]),
                )
            )
            template = db.scalar(
                select(ServiceChecklistTemplate).where(
                    ServiceChecklistTemplate.code == str(template_code).strip().upper(),
                    ServiceChecklistTemplate.is_active.in_([True]),
                    ServiceChecklistTemplate.publication_status == "PUBLISHED",
                    ServiceChecklistTemplate.schedule_mode == "SCHEDULED",
                )
            )
            if not client or not engineer or not template:
                raise ValueError("Client, engineer, or published template was not found.")
            checklist_assignee(db, engineer.id)
            from datetime import date, datetime, time

            parsed_date = (
                start_date
                if isinstance(start_date, (date, datetime))
                else date.fromisoformat(str(start_date))
            )
            parsed_time = (
                start_time
                if isinstance(start_time, time)
                else time.fromisoformat(str(start_time or "09:00"))
            )
            starts_at = datetime.combine(
                parsed_date.date() if isinstance(parsed_date, datetime) else parsed_date,
                parsed_time,
            )
            interval_days = _frequency_days(str(frequency))
            duplicate = db.scalar(
                select(ServiceChecklistSchedule.id).where(
                    ServiceChecklistSchedule.template_id == template.id,
                    ServiceChecklistSchedule.client_id == client.id,
                    ServiceChecklistSchedule.starts_at == starts_at,
                )
            )
            if duplicate:
                raise ValueError("This client, template, and start date already exist.")
            schedule = ServiceChecklistSchedule(
                name=f"{client.name} · {template.name}",
                template_id=template.id,
                client_id=client.id,
                assigned_user_id=engineer.id,
                starts_at=starts_at,
                next_generate_at=starts_at,
                interval_days=interval_days,
                duration_minutes=int(duration or 120),
                timezone=server_clock_settings()[0],
                is_active=str(active or "YES").strip().upper() not in {"NO", "FALSE", "0"},
                created_by_user_id=actor.id,
            )
            db.add(schedule)
            db.flush()
            if schedule.is_active:
                occurrence = create_occurrence_row(
                    db,
                    OccurrenceCreate(
                        template_id=template.id,
                        client_id=client.id,
                        assigned_user_id=engineer.id,
                        scheduled_at=starts_at,
                        due_at=starts_at + timedelta(minutes=schedule.duration_minutes),
                        recurrence_days=interval_days,
                    ),
                    actor,
                    schedule_id=schedule.id,
                )
                schedule.next_generate_at += timedelta(days=interval_days)
                audit(
                    db,
                    actor,
                    occurrence,
                    "service_checklist.assignment.imported",
                    {"schedule_id": schedule.id, "row": row_number},
                )
            db.commit()
            created += 1
        except Exception as exc:
            db.rollback()
            errors.append({"row": row_number, "error": str(exc)})
    return {"created": created, "failed": len(errors), "errors": errors[:100]}


@router.post("/schedule-generation/run")
def generate_due_schedules(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.schedule.manage")),
) -> dict[str, int]:
    horizon = server_now() + timedelta(days=30)
    generated = 0
    schedules = list(
        db.scalars(
            select(ServiceChecklistSchedule).where(
                ServiceChecklistSchedule.is_active.in_([True]),
                ServiceChecklistSchedule.is_paused.in_([False]),
                ServiceChecklistSchedule.next_generate_at <= horizon,
            )
        )
    )
    for schedule in schedules:
        while as_server_time(schedule.next_generate_at) <= horizon and generated < 500:
            exists = db.scalar(
                select(ServiceChecklistOccurrence.id).where(
                    ServiceChecklistOccurrence.schedule_id == schedule.id,
                    ServiceChecklistOccurrence.scheduled_at == schedule.next_generate_at,
                )
            )
            if not exists:
                create_occurrence_row(
                    db,
                    OccurrenceCreate(
                        template_id=schedule.template_id,
                        client_id=schedule.client_id,
                        assigned_user_id=schedule.assigned_user_id,
                        scheduled_at=schedule.next_generate_at,
                        due_at=schedule.next_generate_at
                        + timedelta(minutes=schedule.duration_minutes),
                        recurrence_days=schedule.interval_days,
                    ),
                    actor,
                    schedule_id=schedule.id,
                )
                generated += 1
            schedule.next_generate_at += timedelta(days=schedule.interval_days)
        schedule.version += 1
    db.commit()
    return {"generated": generated}


@router.post("/occurrences/process-reminders")
def process_reminders(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.schedule.manage")),
) -> dict[str, int]:
    del actor
    now = server_now()
    count = 0
    rows = list(
        db.scalars(
            select(ServiceChecklistOccurrence)
            .outerjoin(
                ServiceChecklistSchedule,
                ServiceChecklistSchedule.id == ServiceChecklistOccurrence.schedule_id,
            )
            .where(
                ServiceChecklistOccurrence.status.in_(("SCHEDULED", "IN_PROGRESS", "BLOCKED")),
                ServiceChecklistOccurrence.assigned_user_id.is_not(None),
                ServiceChecklistOccurrence.due_at <= now + timedelta(hours=24),
                (ServiceChecklistOccurrence.schedule_id.is_(None))
                | (ServiceChecklistSchedule.is_paused.in_([False])),
            )
        )
    )
    attention_by_user: dict[int, list[ServiceChecklistOccurrence]] = {}
    for row in rows:
        key = f"checklist-due:{row.id}:{now.date().isoformat()}"
        if not db.scalar(select(Notification.id).where(Notification.deduplication_key == key)):
            overdue = as_server_time(row.due_at) < now
            title = f"{'Overdue' if overdue else 'Due soon'}: {row.occurrence_number}"
            db.add(
                Notification(
                    recipient_user_id=row.assigned_user_id,
                    notification_type="SERVICE_CHECKLIST_OVERDUE"
                    if overdue
                    else "SERVICE_CHECKLIST_DUE",
                    severity="WARNING" if overdue else "INFO",
                    title=title,
                    message=row.template_name,
                    deep_link="/service-checklists",
                    deduplication_key=key,
                )
            )
            count += 1
        if row.assigned_user_id is not None:
            attention_by_user.setdefault(row.assigned_user_id, []).append(row)
    digests = 0
    for user_id, attention_rows in attention_by_user.items():
        recipient = db.get(User, user_id)
        digest_key = f"checklist-attention-digest:{user_id}:{now.date().isoformat()}"
        if (
            not recipient
            or not recipient.email
            or db.scalar(select(EventOutbox.id).where(EventOutbox.deduplication_key == digest_key))
        ):
            continue
        lines = [
            "Clients requiring checklist attention:",
            "",
        ]
        for row in sorted(attention_rows, key=lambda item: as_server_time(item.due_at)):
            client = db.get(Client, row.client_id)
            overdue_days = max(0, (now.date() - as_server_time(row.due_at).date()).days)
            state = f"overdue {overdue_days} day(s)" if overdue_days else "due within 24 hours"
            lines.append(
                f"- {client.name if client else f'Client #{row.client_id}'} — "
                f"{row.template_name} — {state} — due {as_server_time(row.due_at).isoformat()}"
            )
        lines.extend(["", "Open SupportHub → My Checklists to record the checklist event."])
        db.add(
            EventOutbox(
                event_type="CHECKLIST_REMINDER_EMAIL",
                aggregate_type="ServiceChecklistDigest",
                aggregate_id=f"{user_id}:{now.date().isoformat()}",
                deduplication_key=digest_key,
                payload_json=json.dumps(
                    {
                        "to": [recipient.email],
                        "subject": f"Checklist attention digest — {len(attention_rows)} client(s)",
                        "body": "\n".join(lines),
                        "deep_link": "/service-checklists",
                    }
                ),
            )
        )
        digests += 1
    db.commit()
    return {"notifications_created": count, "digest_emails_created": digests}


@router.get("/reports/summary", response_model=ChecklistReport)
def checklist_report(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("service_checklist.report.view")),
) -> ChecklistReport:
    del actor
    rows = list(db.scalars(select(ServiceChecklistOccurrence)))
    now = server_now()
    client_items = (
        db.scalar(
            select(func.count())
            .select_from(ServiceChecklistOccurrenceItem)
            .where(ServiceChecklistOccurrenceItem.state == "CLIENT_RESPONSIBLE")
        )
        or 0
    )
    evidence_gaps = (
        db.scalar(
            select(func.count())
            .select_from(ServiceChecklistOccurrenceItem)
            .where(
                ServiceChecklistOccurrenceItem.evidence_required.in_([True]),
                ServiceChecklistOccurrenceItem.state != "COMPLETED",
                or_(
                    and_(
                        ServiceChecklistOccurrenceItem.evidence_type == "FILE",
                        ServiceChecklistOccurrenceItem.evidence_id.is_(None),
                    ),
                    and_(
                        ServiceChecklistOccurrenceItem.evidence_type != "FILE",
                        ServiceChecklistOccurrenceItem.evidence_reference.is_(None),
                    ),
                ),
            )
        )
        or 0
    )
    completed = [row for row in rows if row.status == "COMPLETED"]
    return ChecklistReport(
        total=len(rows),
        scheduled=sum(row.status == "SCHEDULED" for row in rows),
        in_progress=sum(row.status == "IN_PROGRESS" for row in rows),
        blocked=sum(row.status == "BLOCKED" for row in rows),
        overdue=sum(
            row.status not in {"COMPLETED", "CANCELLED"} and as_server_time(row.due_at) < now
            for row in rows
        ),
        completed=len(completed),
        cancelled=sum(row.status == "CANCELLED" for row in rows),
        on_time_completed=sum(
            bool(
                row.completed_at and as_server_time(row.completed_at) <= as_server_time(row.due_at)
            )
            for row in completed
        ),
        late_completed=sum(
            bool(row.completed_at and as_server_time(row.completed_at) > as_server_time(row.due_at))
            for row in completed
        ),
        client_responsible_items=client_items,
        evidence_gaps=evidence_gaps,
    )
