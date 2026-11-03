import json
import re
import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_clock_settings, server_timezone
from app.core.config import Settings, get_settings
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import Client
from app.modules.contracts.models import Contract
from app.modules.iam.models import AuditLog, Department, Profile, User, UserProfile
from app.modules.iam.service import effective_permissions
from app.modules.internal_operations.attachments import document_path, store_document
from app.modules.internal_operations.generator import build_operation_preview
from app.modules.internal_operations.lifecycle import transition_operation
from app.modules.internal_operations.models import (
    InternalOperation,
    InternalOperationAssignee,
    InternalOperationComment,
    InternalOperationDocument,
    InternalOperationTemplate,
    InternalOperationType,
)
from app.modules.internal_operations.schemas import (
    ClientOptionRead,
    CommentCreate,
    CommentRead,
    DocumentRead,
    OperationCreate,
    OperationGeneratorApply,
    OperationGeneratorApplyResult,
    OperationGeneratorPreviewRead,
    OperationGeneratorRequest,
    OperationRead,
    OperationScheduleWrite,
    OperationTemplateApply,
    OperationTemplateApplyResult,
    OperationTemplateRead,
    OperationTemplateWrite,
    OperationTransitionWrite,
    OperationTypeRead,
    OperationTypeWrite,
    OperationUpdate,
    PersonRead,
)
from app.modules.shifts.models import ScheduleGenerationBatch
from app.modules.visits.models import (
    ClientVisitAssignment,
    ClientVisitEntitlement,
    ClientVisitOccurrence,
    VisitType,
)

router = APIRouter(prefix="/internal-operations", tags=["internal-operations"])

DEFAULT_OPERATION_TYPES = (
    ("WORK_FROM_HOME", "Work from home", "#1565c0", False),
    ("OUTDOOR_VISIT", "Outdoor / field visit", "#2e7d32", True),
    ("MEETING", "Meeting", "#7b1fa2", False),
    ("DEMO", "Client / sales demo", "#ed6c02", True),
    ("AFTER_SHIFT", "After-shift work", "#c62828", False),
)


def ensure_default_operation_types(db: Session) -> None:
    existing = set(db.scalars(select(InternalOperationType.code)))
    missing = [row for row in DEFAULT_OPERATION_TYPES if row[0] not in existing]
    if not missing:
        return
    db.add_all(
        InternalOperationType(code=code, name=name, color=color, supports_client=supports_client, is_active=True)
        for code, name, color, supports_client in missing
    )
    db.flush()


def resolve_visit_entitlement(
    db: Session, client_id: int, operation_type_code: str, operation_date: date
) -> ClientVisitEntitlement | None:
    """Match the exact visit type and an effective contract for an operation."""
    visit_type_ids = select(VisitType.id).join(
        InternalOperationType,
        InternalOperationType.id == VisitType.internal_operation_type_id,
    ).where(
        InternalOperationType.code == operation_type_code,
        VisitType.is_active.in_([True]),
    )
    return db.scalar(
        select(ClientVisitEntitlement)
        .join(Contract, Contract.id == ClientVisitEntitlement.contract_id)
        .where(
            ClientVisitEntitlement.client_id == client_id,
            ClientVisitEntitlement.visit_type_id.in_(visit_type_ids),
            ClientVisitEntitlement.status == "ACTIVE",
            ClientVisitEntitlement.service_period_start <= operation_date,
            ClientVisitEntitlement.service_period_end >= operation_date,
            Contract.status == "ACTIVE",
            Contract.is_active.in_([True]),
            Contract.start_date <= operation_date,
            Contract.end_date >= operation_date,
        )
        .order_by(ClientVisitEntitlement.service_period_end, ClientVisitEntitlement.id)
        .limit(1)
    )


def template_values(data: OperationTemplateWrite) -> dict[str, object]:
    values=data.model_dump();weeks=values.pop("default_week_numbers");weekdays=values.pop("default_weekdays")
    values["default_week_numbers_json"]=",".join(map(str,weeks));values["default_weekdays_json"]=",".join(map(str,weekdays));values["crosses_midnight"]=data.end_time<=data.start_time
    return values


def template_code(db: Session, name: str) -> str:
    base=re.sub(r"[^A-Z0-9]+","-",name.upper()).strip("-")[:42] or "OPERATION"
    used=set(db.scalars(select(InternalOperationTemplate.code)));sequence=1
    while f"{base}-{sequence:03d}" in used: sequence+=1
    return f"{base}-{sequence:03d}"


def operation_type_code(db:Session,name:str)->str:
    base=re.sub(r"[^A-Z0-9]+","_",name.upper()).strip("_")[:24] or "OPERATION";used=set(db.scalars(select(InternalOperationType.code)));candidate=base;sequence=1
    while candidate in used: sequence+=1;candidate=f"{base[:25]}_{sequence:03d}"
    return candidate


def can_manage(db: Session, actor: User) -> bool:
    return "internal_operation.manage" in effective_permissions(db, actor).permissions


def hr_department(db: Session, actor: User) -> str | None:
    profile = db.scalar(select(UserProfile.id).join(Profile, Profile.id == UserProfile.profile_id).where(UserProfile.user_id == actor.id, UserProfile.is_active.in_([True]), Profile.code == "HR"))
    return actor.department if profile else None


def assigned(db: Session, operation_id: int, user_id: int) -> bool:
    return db.scalar(select(InternalOperationAssignee.id).where(InternalOperationAssignee.operation_id == operation_id, InternalOperationAssignee.user_id == user_id)) is not None


def ensure_access(db: Session, actor: User, operation: InternalOperation) -> None:
    department = hr_department(db, actor)
    if department is not None and db.scalar(select(InternalOperationAssignee.id).join(User, User.id == InternalOperationAssignee.user_id).where(InternalOperationAssignee.operation_id == operation.id, User.department == department)):
        return
    if not can_manage(db, actor) and operation.created_by_user_id != actor.id and not assigned(db, operation.id, actor.id):
        raise AuthorizationError("You can only access internal operations assigned to you.")


def employee_map(db: Session, ids: set[int]) -> dict[int, User]:
    if not ids:
        return {}
    return {row.id: row for row in db.scalars(select(User).where(User.id.in_(ids)))}


def serialize_operation(db: Session, operation: InternalOperation, *, detail: bool = False) -> OperationRead:
    assignment_rows = list(db.scalars(select(InternalOperationAssignee).where(InternalOperationAssignee.operation_id == operation.id)))
    comment_rows = list(db.scalars(select(InternalOperationComment).where(InternalOperationComment.operation_id == operation.id).order_by(InternalOperationComment.created_at))) if detail else []
    document_rows = list(db.scalars(select(InternalOperationDocument).where(InternalOperationDocument.operation_id == operation.id).order_by(InternalOperationDocument.created_at.desc()))) if detail else []
    user_ids = {operation.created_by_user_id, *(row.user_id for row in assignment_rows), *(row.author_user_id for row in comment_rows), *(row.uploaded_by_user_id for row in document_rows)}
    users = employee_map(db, user_ids)
    creator = users[operation.created_by_user_id]
    client = db.get(Client, operation.client_id) if operation.client_id else None
    return OperationRead(
        id=operation.id, title=operation.title, operation_type=operation.operation_type, status=operation.status,
        starts_at=operation.starts_at, ends_at=operation.ends_at, location=operation.location,
        client_id=operation.client_id, client_code=client.code if client else None,
        client_name=client.name if client else operation.client_name, description=operation.description,
        created_by_user_id=operation.created_by_user_id, created_by_name=creator.full_name,
        created_at=operation.created_at, updated_at=operation.updated_at,
        assignees=[PersonRead(id=users[row.user_id].id, full_name=users[row.user_id].full_name, department=users[row.user_id].department, job_title=users[row.user_id].job_title) for row in assignment_rows],
        comments=[CommentRead(id=row.id, author_user_id=row.author_user_id, author_name=users[row.author_user_id].full_name, comment_type=row.comment_type, body=row.body, created_at=row.created_at) for row in comment_rows],
        documents=[DocumentRead(id=row.id, original_filename=row.original_filename, content_type=row.content_type, size_bytes=row.size_bytes, uploaded_by_user_id=row.uploaded_by_user_id, uploaded_by_name=users[row.uploaded_by_user_id].full_name, created_at=row.created_at) for row in document_rows],
        template_id=operation.template_id, visit_occurrence_id=operation.visit_occurrence_id,
        planned_window_start=operation.planned_window_start, planned_window_end=operation.planned_window_end,
        timezone=operation.timezone, version=operation.version,
    )


def validate_assignees(db: Session, user_ids: list[int]) -> None:
    found = set(db.scalars(select(User.id).where(User.id.in_(user_ids), User.is_active.in_([True]), User.user_type == "EMPLOYEE", User.participates_in_operations.in_([True]))))
    if found != set(user_ids):
        raise ConflictError("OPERATION_EMPLOYEE_NOT_PARTICIPANT", "Every assignee must be an active Operation Planning participant.")


def validate_client(db: Session, client_id: int | None) -> None:
    if client_id is not None and not db.scalar(select(Client.id).where(Client.id == client_id, Client.is_active.in_([True]))):
        raise NotFoundError("The selected client is unavailable.")


def validate_operation_type(db:Session,code:str)->InternalOperationType:
    ensure_default_operation_types(db)
    item=db.scalar(select(InternalOperationType).where(InternalOperationType.code==code,InternalOperationType.is_active.in_([True])))
    if not item: raise NotFoundError("The selected internal-operation type is unavailable.")
    return item


@router.get("/engineers", response_model=list[PersonRead])
def engineers(db: Session = Depends(get_db), actor: User = Depends(require_permission("internal_operation.view"))) -> list[PersonRead]:
    query = select(User).where(
        User.is_active.in_([True]),
        User.user_type == "EMPLOYEE",
        User.participates_in_operations.in_([True]),
    )
    department = hr_department(db, actor)
    if department is not None:
        query = query.where(User.department == department)
    rows = db.scalars(query.order_by(User.full_name))
    return [PersonRead(id=row.id, full_name=row.full_name, department=row.department, job_title=row.job_title) for row in rows]


@router.get("/clients", response_model=list[ClientOptionRead])
def operation_clients(db: Session = Depends(get_db), _: User = Depends(require_permission("internal_operation.view"))) -> list[ClientOptionRead]:
    rows = db.scalars(select(Client).where(Client.is_active.in_([True])).order_by(Client.name))
    return [ClientOptionRead(id=row.id, code=row.code, name=row.name) for row in rows]


@router.get("/types",response_model=list[OperationTypeRead])
def operation_types(db:Session=Depends(get_db),_:User=Depends(require_permission("internal_operation.view")))->list[InternalOperationType]:
    ensure_default_operation_types(db)
    return list(db.scalars(select(InternalOperationType).where(InternalOperationType.is_active.in_([True])).order_by(InternalOperationType.name)))


@router.post("/types",response_model=OperationTypeRead,status_code=201)
def create_operation_type(data:OperationTypeWrite,db:Session=Depends(get_db),actor:User=Depends(require_permission("internal_operation.type.manage")))->InternalOperationType:
    item=InternalOperationType(code=operation_type_code(db,data.name),**data.model_dump());db.add(item);db.flush();db.add(AuditLog(actor_user_id=actor.id,entity_type="InternalOperationType",entity_id=str(item.id),action="internal_operation_type.created",new_values_json=json.dumps(data.model_dump())));db.commit();db.refresh(item);return item


@router.patch("/types/{type_id}",response_model=OperationTypeRead)
def update_operation_type(type_id:int,data:OperationTypeWrite,db:Session=Depends(get_db),actor:User=Depends(require_permission("internal_operation.type.manage")))->InternalOperationType:
    item=db.get(InternalOperationType,type_id)
    if not item: raise NotFoundError("Internal-operation type does not exist.")
    old={key:getattr(item,key) for key in data.model_dump()}
    for key,value in data.model_dump().items():setattr(item,key,value)
    db.add(AuditLog(actor_user_id=actor.id,entity_type="InternalOperationType",entity_id=str(item.id),action="internal_operation_type.updated",old_values_json=json.dumps(old),new_values_json=json.dumps(data.model_dump())));db.commit();db.refresh(item);return item


@router.delete("/types/{type_id}",status_code=204)
def delete_operation_type(type_id:int,db:Session=Depends(get_db),actor:User=Depends(require_permission("internal_operation.type.manage")))->None:
    item=db.get(InternalOperationType,type_id)
    if not item: raise NotFoundError("Internal-operation type does not exist.")
    used=db.scalar(select(InternalOperation.id).where(InternalOperation.operation_type==item.code).limit(1)) or db.scalar(select(InternalOperationTemplate.id).where(InternalOperationTemplate.operation_type==item.code).limit(1)) or db.scalar(select(VisitType.id).where(VisitType.internal_operation_type_id==item.id).limit(1))
    if used: raise ConflictError("OPERATION_TYPE_IN_USE","This type is used by schedules or templates and cannot be deleted.")
    db.add(AuditLog(actor_user_id=actor.id,entity_type="InternalOperationType",entity_id=str(item.id),action="internal_operation_type.deleted",old_values_json=json.dumps({"code":item.code,"name":item.name})));db.delete(item);db.commit()


@router.get("/templates", response_model=list[OperationTemplateRead])
def operation_templates(db: Session=Depends(get_db), _:User=Depends(require_permission("internal_operation.view"))) -> list[InternalOperationTemplate]:
    return list(db.scalars(select(InternalOperationTemplate).where(InternalOperationTemplate.is_active.in_([True])).order_by(InternalOperationTemplate.name)))


@router.post("/templates", response_model=OperationTemplateRead, status_code=201)
def create_operation_template(data:OperationTemplateWrite,db:Session=Depends(get_db),actor:User=Depends(require_permission("internal_operation.template.manage"))) -> InternalOperationTemplate:
    operation_type=validate_operation_type(db,data.operation_type)
    if data.department_id and not db.get(Department,data.department_id): raise NotFoundError("Department does not exist.")
    item=InternalOperationTemplate(code=template_code(db,data.name),operation_type_id=operation_type.id,**template_values(data));db.add(item);db.flush()
    db.add(AuditLog(actor_user_id=actor.id,entity_type="InternalOperationTemplate",entity_id=str(item.id),action="internal_operation_template.created",new_values_json=json.dumps(data.model_dump(),default=str)));db.commit();db.refresh(item);return item


@router.patch("/templates/{template_id}",response_model=OperationTemplateRead)
def update_operation_template(template_id:int,data:OperationTemplateWrite,db:Session=Depends(get_db),actor:User=Depends(require_permission("internal_operation.template.manage"))) -> InternalOperationTemplate:
    item=db.get(InternalOperationTemplate,template_id)
    if not item: raise NotFoundError("Internal operation template does not exist.")
    operation_type=validate_operation_type(db,data.operation_type)
    if data.department_id and not db.get(Department,data.department_id): raise NotFoundError("Department does not exist.")
    values=template_values(data);old={key:getattr(item,key) for key in values}
    for key,value in values.items(): setattr(item,key,value)
    item.operation_type_id=operation_type.id
    db.add(AuditLog(actor_user_id=actor.id,entity_type="InternalOperationTemplate",entity_id=str(item.id),action="internal_operation_template.updated",old_values_json=json.dumps(old,default=str),new_values_json=json.dumps(data.model_dump(),default=str)));db.commit();db.refresh(item);return item


@router.delete("/templates/{template_id}",status_code=204)
def delete_operation_template(template_id:int,db:Session=Depends(get_db),actor:User=Depends(require_permission("internal_operation.template.manage"))) -> None:
    item=db.get(InternalOperationTemplate,template_id)
    if not item: raise NotFoundError("Internal operation template does not exist.")
    db.add(AuditLog(actor_user_id=actor.id,entity_type="InternalOperationTemplate",entity_id=str(item.id),action="internal_operation_template.deleted",old_values_json=json.dumps({"code":item.code,"name":item.name})));db.delete(item);db.commit()


@router.post("/templates/{template_id}/apply-month",response_model=OperationTemplateApplyResult)
def apply_operation_template(template_id:int,data:OperationTemplateApply,db:Session=Depends(get_db),actor:User=Depends(require_permission("internal_operation.template.manage"))) -> OperationTemplateApplyResult:
    item=db.get(InternalOperationTemplate,template_id)
    if not item or not item.is_active: raise NotFoundError("Active internal operation template does not exist.")
    validate_assignees(db,data.user_ids);department=db.get(Department,item.department_id) if item.department_id else None
    users=list(db.scalars(select(User).where(User.id.in_(data.user_ids))))
    if department and any(user.department!=department.name for user in users): raise ConflictError("OPERATION_TEMPLATE_DEPARTMENT_MISMATCH","Every selected employee must belong to the template department.")
    weeks=data.week_numbers or item.default_week_numbers;weekdays=data.weekdays or item.default_weekdays;week_start=data.week_start_day if data.week_start_day is not None else item.week_start_day
    if any(value not in range(1,5) for value in weeks) or any(value not in range(7) for value in weekdays): raise ConflictError("INVALID_OPERATION_TEMPLATE_DATES","Week and day selections are invalid.")
    if item.operation_type == "OUTDOOR_VISIT":
        if data.client_id is None:
            raise ConflictError("INTERNAL_OPERATION_CLIENT_REQUIRED", "Outdoor / field visit templates require a client.")
        validate_client(db, data.client_id)
    if data.selection_mode == "SPECIFIC_DATES":
        dates = data.specific_dates
    elif data.selection_mode == "DATE_RANGE":
        assert data.date_from is not None and data.date_to is not None
        selected_weekdays = set(weekdays)
        selected_weeks = set(weeks)
        dates = []
        for offset in range((data.date_to-data.date_from).days+1):
            candidate = data.date_from + timedelta(days=offset)
            month_start = candidate.replace(day=1)
            first_week_start = month_start - timedelta(days=(month_start.weekday()-week_start)%7)
            week_number = ((candidate-first_week_start).days//7)+1
            if candidate.weekday() in selected_weekdays and week_number in selected_weeks:
                dates.append(candidate)
    else:
        assert data.month is not None
        month_start=data.month.replace(day=1);first_start=month_start+timedelta(days=(week_start-month_start.weekday())%7)
        dates=sorted({first_start+timedelta(days=(week-1)*7+(weekday-week_start)%7) for week in weeks for weekday in weekdays});dates=[value for value in dates if value.month==month_start.month]
    timezone=ZoneInfo("Africa/Cairo");created=skipped=0
    for operation_date in dates:
        start_time=item.start_time if isinstance(item.start_time,time) else time.fromisoformat(str(item.start_time));end_time=item.end_time if isinstance(item.end_time,time) else time.fromisoformat(str(item.end_time))
        starts_local=datetime.combine(operation_date,start_time,timezone);end_date=operation_date+timedelta(days=1 if item.crosses_midnight else 0);ends_local=datetime.combine(end_date,end_time,timezone);starts_at=starts_local.astimezone(server_timezone());ends_at=ends_local.astimezone(server_timezone())
        conflicts=set(db.scalars(select(InternalOperationAssignee.user_id).join(InternalOperation,InternalOperation.id==InternalOperationAssignee.operation_id).where(InternalOperationAssignee.user_id.in_(data.user_ids),InternalOperation.status.notin_(("CANCELLED","COMPLETED")),InternalOperation.starts_at<ends_at,InternalOperation.ends_at>starts_at)))
        selected=[user.id for user in users if user.id not in conflicts];skipped+=len(conflicts)
        if not selected: continue
        operation=InternalOperation(title=item.name,operation_type=item.operation_type,status=item.default_status,template_id=item.id,client_id=data.client_id,timezone="Africa/Cairo",starts_at=starts_at,ends_at=ends_at,location=item.location,description=item.description,created_by_user_id=actor.id);db.add(operation);db.flush();db.add_all(InternalOperationAssignee(operation_id=operation.id,user_id=user_id) for user_id in selected)
        if item.operation_type == "OUTDOOR_VISIT":
            assert data.client_id is not None
            entitlement = resolve_visit_entitlement(db, data.client_id, item.operation_type, operation_date)
            if not entitlement:
                raise ConflictError("VISIT_ENTITLEMENT_REQUIRED", f"No active visit entitlement covers {operation_date}.")
            sequence = (db.scalar(select(func.max(ClientVisitOccurrence.sequence_number)).where(ClientVisitOccurrence.entitlement_id == entitlement.id)) or 0) + 1
            occurrence = ClientVisitOccurrence(entitlement_id=entitlement.id,contract_id=entitlement.contract_id,client_id=entitlement.client_id,visit_type_id=entitlement.visit_type_id,sequence_number=sequence,window_start=operation_date,window_end=operation_date,due_date=operation_date,scheduled_visit_date=operation_date,status="SCHEDULED",duration_minutes=int((ends_at-starts_at).total_seconds()//60),generation_key=f"internal-operation-template:{item.id}:{operation.id}",source_version=entitlement.source_version,source_type="INTERNAL_OPERATION",internal_operation_id=operation.id,notes=item.description,version=1,created_by_user_id=actor.id)
            db.add(occurrence);db.flush();operation.visit_occurrence_id=occurrence.id
            db.add_all(ClientVisitAssignment(occurrence_id=occurrence.id,user_id=user_id,starts_at=starts_at,ends_at=ends_at,timezone="Africa/Cairo",status="ASSIGNED",stable_key=f"visit-assignment:{occurrence.id}:{user_id}",version=1,created_by_user_id=actor.id) for user_id in selected)
        created+=1
    db.add(AuditLog(actor_user_id=actor.id,entity_type="InternalOperationTemplate",entity_id=str(item.id),action="internal_operation_template.applied",new_values_json=json.dumps({**data.model_dump(),"created":created,"skipped":skipped},default=str)));db.commit();return OperationTemplateApplyResult(created=created,skipped=skipped,dates=dates)


@router.post("/generator/preview", response_model=OperationGeneratorPreviewRead)
def preview_operation_generator(
    data: OperationGeneratorRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("internal_operation.manage")),
) -> OperationGeneratorPreviewRead:
    ensure_default_operation_types(db)
    return build_operation_preview(db, data)


@router.post("/generator/apply", response_model=OperationGeneratorApplyResult)
def apply_operation_generator(
    data: OperationGeneratorApply,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("internal_operation.manage")),
) -> OperationGeneratorApplyResult:
    ensure_default_operation_types(db)
    preview = build_operation_preview(db, data.request)
    if preview.preview_hash != data.preview_hash:
        raise ConflictError("SCHEDULE_PREVIEW_CHANGED", "Scheduling or entitlement data changed after preview. Review the refreshed plan before applying.")
    if preview.entitlement_issue_count:
        raise ConflictError("VISIT_ENTITLEMENT_PREVIEW_FAILED", "One or more outdoor visits are not covered by an available exact-client entitlement.")
    batch = ScheduleGenerationBatch(
        module="OPERATIONS", source_type="AD_HOC", source_id=None,
        date_from=data.request.recurrence.date_from, date_to=data.request.recurrence.date_to,
        recurrence_json=json.dumps(data.request.recurrence.model_dump(), default=str),
        assignment_mode=data.request.assignment_strategy, required_positions=preview.required_positions,
        created_assignments=0, unassigned_positions=preview.unassigned_positions, skipped_count=0,
        conflict_count=preview.conflict_count, preview_hash=preview.preview_hash, status="APPLIED",
        created_by_user_id=actor.id,
    )
    db.add(batch)
    db.flush()
    created_operations = created_visits = created_assignments = 0
    for slot in preview.slots:
        operation = InternalOperation(
            title=data.request.title, operation_type=data.request.operation_type, status=data.request.status,
            client_id=data.request.client_id, timezone=data.request.timezone, starts_at=slot.starts_at,
            ends_at=slot.ends_at, location=data.request.location, description=data.request.description,
            generation_batch_id=batch.id, created_by_user_id=actor.id,
        )
        db.add(operation)
        db.flush()
        db.add_all(InternalOperationAssignee(operation_id=operation.id, user_id=user_id) for user_id in slot.assigned_user_ids)
        created_assignments += len(slot.assigned_user_ids)
        if data.request.operation_type == "OUTDOOR_VISIT":
            entitlement = db.get(ClientVisitEntitlement, slot.entitlement_id)
            if entitlement is None or slot.entitlement_sequence is None:
                raise ConflictError("VISIT_ENTITLEMENT_PREVIEW_FAILED", f"No entitlement covers {slot.date}.")
            occurrence = ClientVisitOccurrence(
                entitlement_id=entitlement.id, contract_id=entitlement.contract_id, client_id=entitlement.client_id,
                visit_type_id=entitlement.visit_type_id, sequence_number=slot.entitlement_sequence,
                window_start=slot.date, window_end=slot.date, due_date=slot.date, scheduled_visit_date=slot.date,
                status="SCHEDULED", duration_minutes=int((slot.ends_at-slot.starts_at).total_seconds()//60),
                generation_key=f"operation-generator:{batch.id}:{slot.slot_key}", source_version=entitlement.source_version,
                source_type="INTERNAL_OPERATION", internal_operation_id=operation.id,
                notes=data.request.description, version=1, created_by_user_id=actor.id,
            )
            db.add(occurrence)
            db.flush()
            operation.visit_occurrence_id = occurrence.id
            db.add_all(ClientVisitAssignment(occurrence_id=occurrence.id, user_id=user_id, starts_at=slot.starts_at, ends_at=slot.ends_at, timezone=data.request.timezone, status="ASSIGNED", stable_key=f"operation-generator-assignment:{batch.id}:{occurrence.id}:{user_id}", version=1, created_by_user_id=actor.id) for user_id in slot.assigned_user_ids)
            created_visits += 1
        created_operations += 1
    batch.created_assignments = created_assignments
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ScheduleGenerationBatch", entity_id=str(batch.id), action="internal_operation.generator.applied", new_values_json=json.dumps({"preview_hash":preview.preview_hash,"created_operations":created_operations,"created_visit_occurrences":created_visits,"created_assignments":created_assignments,"unassigned_positions":preview.unassigned_positions}, default=str)))
    db.commit()
    return OperationGeneratorApplyResult(batch_id=batch.id, created_operations=created_operations, created_visit_occurrences=created_visits, unassigned_positions=preview.unassigned_positions)


@router.get("", response_model=list[OperationRead])
def list_operations(
    operation_type: str | None = None, status: str | None = None,
    date_from: date | None = None, date_to: date | None = None, client_id: int | None = None,
    db: Session = Depends(get_db), actor: User = Depends(require_permission("internal_operation.view")),
) -> list[OperationRead]:
    query = select(InternalOperation).order_by(InternalOperation.starts_at.desc())
    department = hr_department(db, actor)
    if department is not None:
        department_operation_ids = select(InternalOperationAssignee.operation_id).join(User, User.id == InternalOperationAssignee.user_id).where(User.department == department)
        query = query.where(InternalOperation.id.in_(department_operation_ids))
    elif not can_manage(db, actor):
        own_ids = select(InternalOperationAssignee.operation_id).where(InternalOperationAssignee.user_id == actor.id)
        query = query.where((InternalOperation.created_by_user_id == actor.id) | InternalOperation.id.in_(own_ids))
    if operation_type:
        query = query.where(InternalOperation.operation_type == operation_type)
    if status:
        query = query.where(InternalOperation.status == status)
    if client_id is not None:
        query = query.where(InternalOperation.client_id == client_id)
    if date_from:
        query = query.where(InternalOperation.starts_at >= datetime.combine(date_from, time.min, server_timezone()))
    if date_to:
        query = query.where(InternalOperation.starts_at <= datetime.combine(date_to, time.max, server_timezone()))
    return [serialize_operation(db, row) for row in db.scalars(query)]


@router.post("", response_model=OperationRead, status_code=201)
def create_operation(data: OperationCreate, db: Session = Depends(get_db), actor: User = Depends(require_permission("internal_operation.create"))) -> OperationRead:
    operation_type = validate_operation_type(db,data.operation_type)
    validate_assignees(db, data.assignee_user_ids)
    validate_client(db, data.client_id)
    if operation_type.requires_client and data.client_id is None:
        raise ConflictError("INTERNAL_OPERATION_CLIENT_REQUIRED", "The selected operation type requires a client.")
    if data.template_id is not None:
        template = db.get(InternalOperationTemplate, data.template_id)
        if not template or not template.is_active or template.operation_type != data.operation_type:
            raise ConflictError("INVALID_INTERNAL_OPERATION_TEMPLATE", "The template is unavailable or does not match the operation type.")
    values = data.model_dump(exclude={"assignee_user_ids"})
    # Visits are the sole operation type governed by an approval gate.
    values["status"] = "PENDING_APPROVAL" if data.operation_type == "OUTDOOR_VISIT" else data.status
    operation = InternalOperation(**values, created_by_user_id=actor.id)
    db.add(operation)
    db.flush()
    db.add_all(InternalOperationAssignee(operation_id=operation.id, user_id=user_id) for user_id in data.assignee_user_ids)
    if data.operation_type == "OUTDOOR_VISIT" and data.client_id:
        entitlement = resolve_visit_entitlement(db, data.client_id, data.operation_type, data.starts_at.date())
        if not entitlement:
            raise ConflictError("VISIT_ENTITLEMENT_REQUIRED", "Outdoor client operations require an active exact-client visit entitlement covering the scheduled date.")
        sequence = (db.scalar(select(func.max(ClientVisitOccurrence.sequence_number)).where(ClientVisitOccurrence.entitlement_id == entitlement.id)) or 0) + 1
        occurrence = ClientVisitOccurrence(entitlement_id=entitlement.id, contract_id=entitlement.contract_id, client_id=entitlement.client_id, visit_type_id=entitlement.visit_type_id, sequence_number=sequence, window_start=data.starts_at.date(), window_end=data.starts_at.date(), due_date=data.starts_at.date(), scheduled_visit_date=data.starts_at.date(), status="SCHEDULED", duration_minutes=int((data.ends_at-data.starts_at).total_seconds()//60), generation_key=f"internal-operation:{operation.id}:{uuid.uuid4()}", source_version=entitlement.source_version, source_type="INTERNAL_OPERATION", internal_operation_id=operation.id, notes=data.description, version=1, created_by_user_id=actor.id)
        db.add(occurrence);db.flush();operation.visit_occurrence_id=occurrence.id
        db.add_all(ClientVisitAssignment(occurrence_id=occurrence.id,user_id=user_id,starts_at=data.starts_at,ends_at=data.ends_at,timezone=server_clock_settings()[0],status="ASSIGNED",stable_key=f"visit-assignment:{occurrence.id}:{user_id}",version=1,created_by_user_id=actor.id) for user_id in data.assignee_user_ids)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="InternalOperation", entity_id=str(operation.id), action="internal_operation.created", new_values_json=json.dumps(data.model_dump(), default=str)))
    db.commit()
    db.refresh(operation)
    return serialize_operation(db, operation, detail=True)


@router.get("/{operation_id}", response_model=OperationRead)
def get_operation(operation_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("internal_operation.view"))) -> OperationRead:
    operation = db.get(InternalOperation, operation_id)
    if not operation:
        raise NotFoundError()
    ensure_access(db, actor, operation)
    return serialize_operation(db, operation, detail=True)


@router.patch("/{operation_id}", response_model=OperationRead)
def update_operation(operation_id: int, data: OperationUpdate, db: Session = Depends(get_db), actor: User = Depends(require_permission("internal_operation.transition"))) -> OperationRead:
    operation = db.get(InternalOperation, operation_id)
    if not operation:
        raise NotFoundError()
    ensure_access(db, actor, operation)
    changes = data.model_dump(exclude_unset=True)
    for field in ("starts_at", "ends_at"):
        if changes.get(field) is not None:
            changes[field] = changes[field].astimezone(server_timezone())
    manager = can_manage(db, actor)
    if not manager and set(changes) - {"status"}:
        raise AuthorizationError("Only an operations manager can edit scheduling and assignments.")
    if not manager and changes.get("status") not in {"IN_PROGRESS", "COMPLETED"}:
        raise AuthorizationError("Engineers can only start or complete assigned operations.")
    assignee_ids = changes.pop("assignee_user_ids", None)
    next_status = changes.pop("status", None)
    if "client_id" in changes:
        validate_client(db, changes["client_id"])
    if assignee_ids is not None:
        validate_assignees(db, assignee_ids)
        db.query(InternalOperationAssignee).filter(InternalOperationAssignee.operation_id == operation.id).delete(synchronize_session=False)
        db.add_all(InternalOperationAssignee(operation_id=operation.id, user_id=user_id) for user_id in dict.fromkeys(assignee_ids))
    for key, value in changes.items():
        setattr(operation, key, value)
    if next_status is not None:
        if operation.status == "SCHEDULED" and next_status == "COMPLETED":
            transition_operation(operation, "IN_PROGRESS", actor_user_id=actor.id)
        transition_operation(operation, next_status, actor_user_id=actor.id)
    elif changes or assignee_ids is not None:
        operation.version += 1
    if operation.ends_at <= operation.starts_at:
        raise ValueError("End time must be after start time.")
    db.add(AuditLog(actor_user_id=actor.id, entity_type="InternalOperation", entity_id=str(operation.id), action="internal_operation.updated", new_values_json=json.dumps(data.model_dump(exclude_unset=True), default=str)))
    db.commit()
    db.refresh(operation)
    return serialize_operation(db, operation, detail=True)


@router.post("/{operation_id}/transition", response_model=OperationRead)
def transition_internal_operation(operation_id: int, data: OperationTransitionWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("internal_operation.transition"))) -> OperationRead:
    operation = db.get(InternalOperation, operation_id)
    if not operation:
        raise NotFoundError()
    ensure_access(db, actor, operation)
    if not can_manage(db, actor) and data.to_status not in {"IN_PROGRESS", "COMPLETED"}:
        raise AuthorizationError("Only an operations manager can perform this transition.")
    old_status, new_status = transition_operation(operation, data.to_status, actor_user_id=actor.id, expected_version=data.expected_version)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="InternalOperation", entity_id=str(operation.id), action="internal_operation.transitioned", reason=data.reason, old_values_json=json.dumps({"status": old_status, "version": data.expected_version}), new_values_json=json.dumps({"status": new_status, "version": operation.version})))
    db.commit();db.refresh(operation)
    return serialize_operation(db, operation, detail=True)


@router.patch("/{operation_id}/schedule", response_model=OperationRead)
def schedule_internal_operation(operation_id: int, data: OperationScheduleWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("internal_operation.schedule"))) -> OperationRead:
    operation = db.get(InternalOperation, operation_id)
    if not operation:
        raise NotFoundError()
    ensure_access(db, actor, operation)
    if operation.version != data.expected_version:
        raise ConflictError("STALE_INTERNAL_OPERATION", "The operation changed; refresh and retry.")
    if operation.status in {"COMPLETED", "CANCELLED", "REJECTED"}:
        raise ConflictError("INTERNAL_OPERATION_NOT_SCHEDULABLE", "A terminal operation cannot be rescheduled.")
    assignee_ids=select(InternalOperationAssignee.user_id).where(InternalOperationAssignee.operation_id==operation.id)
    conflict=db.scalar(select(InternalOperation.id).join(InternalOperationAssignee,InternalOperationAssignee.operation_id==InternalOperation.id).where(InternalOperation.id!=operation.id,InternalOperationAssignee.user_id.in_(assignee_ids),InternalOperation.status.notin_(("COMPLETED","CANCELLED","REJECTED")),InternalOperation.starts_at<data.ends_at,InternalOperation.ends_at>data.starts_at).limit(1))
    if conflict:
        raise ConflictError("INTERNAL_OPERATION_SCHEDULE_CONFLICT", "One or more assigned engineers already have an overlapping operation.")
    before={"starts_at":operation.starts_at,"ends_at":operation.ends_at,"timezone":operation.timezone,"version":operation.version}
    operation.starts_at=data.starts_at;operation.ends_at=data.ends_at;operation.timezone=data.timezone;operation.version+=1
    db.add(AuditLog(actor_user_id=actor.id,entity_type="InternalOperation",entity_id=str(operation.id),action="internal_operation.rescheduled",reason=data.reason,old_values_json=json.dumps(before,default=str),new_values_json=json.dumps({"starts_at":operation.starts_at,"ends_at":operation.ends_at,"timezone":operation.timezone,"version":operation.version},default=str)))
    db.commit();db.refresh(operation)
    return serialize_operation(db,operation,detail=True)


@router.post("/{operation_id}/comments", response_model=CommentRead, status_code=201)
def add_comment(operation_id: int, data: CommentCreate, db: Session = Depends(get_db), actor: User = Depends(require_permission("internal_operation.comment"))) -> CommentRead:
    operation = db.get(InternalOperation, operation_id)
    if not operation:
        raise NotFoundError()
    ensure_access(db, actor, operation)
    row = InternalOperationComment(operation_id=operation_id, author_user_id=actor.id, **data.model_dump())
    db.add(row)
    db.flush()
    db.add(AuditLog(actor_user_id=actor.id, entity_type="InternalOperationComment", entity_id=str(row.id), action="internal_operation.comment.added"))
    db.commit()
    db.refresh(row)
    return CommentRead(id=row.id, author_user_id=actor.id, author_name=actor.full_name, comment_type=row.comment_type, body=row.body, created_at=row.created_at)


@router.post("/{operation_id}/documents", response_model=DocumentRead, status_code=201)
async def upload_document(operation_id: int, upload: UploadFile = File(...), db: Session = Depends(get_db), actor: User = Depends(require_permission("internal_operation.document.upload")), settings: Settings = Depends(get_settings)) -> DocumentRead:
    operation = db.get(InternalOperation, operation_id)
    if not operation:
        raise NotFoundError()
    ensure_access(db, actor, operation)
    original, stored, content_type, size = await store_document(upload, operation_id, settings)
    row = InternalOperationDocument(operation_id=operation_id, original_filename=original, stored_filename=stored, content_type=content_type, size_bytes=size, uploaded_by_user_id=actor.id)
    db.add(row)
    db.flush()
    db.add(AuditLog(actor_user_id=actor.id, entity_type="InternalOperationDocument", entity_id=str(row.id), action="internal_operation.document.uploaded", new_values_json=json.dumps({"filename": original, "size_bytes": size})))
    db.commit()
    db.refresh(row)
    return DocumentRead(id=row.id, original_filename=original, content_type=content_type, size_bytes=size, uploaded_by_user_id=actor.id, uploaded_by_name=actor.full_name, created_at=row.created_at)


@router.get("/{operation_id}/documents/{document_id}/download")
def download_document(operation_id: int, document_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("internal_operation.document.download")), settings: Settings = Depends(get_settings)) -> FileResponse:
    operation = db.get(InternalOperation, operation_id)
    document = db.get(InternalOperationDocument, document_id)
    if not operation or not document or document.operation_id != operation_id:
        raise NotFoundError()
    ensure_access(db, actor, operation)
    return FileResponse(document_path(document, settings), media_type=document.content_type, filename=document.original_filename)
