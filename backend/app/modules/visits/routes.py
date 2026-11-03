import calendar
import json
import uuid
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import false, func, select, true, update
from sqlalchemy.orm import Session

from app.api.dependencies import authenticated_user, require_permission
from app.core.clock import server_today
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import Client, ClientLocation, ServiceCatalogItem
from app.modules.contracts.models import Contract
from app.modules.iam.models import AuditLog, Department, User
from app.modules.iam.service import effective_permissions
from app.modules.internal_operations.models import InternalOperation, InternalOperationType
from app.modules.notifications.models import Notification
from app.modules.shifts.models import Shift, ShiftType
from app.modules.tickets.models import Ticket
from app.modules.visits.attachments import store_visit_document, visit_document_path
from app.modules.visits.models import (
    ClientVisitAssignment,
    ClientVisitEntitlement,
    ClientVisitOccurrence,
    VisitCompletionEvidence,
    VisitDocument,
    VisitEntitlementLedgerEntry,
    VisitGenerationException,
    VisitType,
)
from app.modules.visits.schemas import (
    BulkVisitCreate,
    BulkVisitResult,
    EntitlementBulkCreate,
    EntitlementCreate,
    EntitlementRead,
    EntitlementSummary,
    FieldVisitClientOption,
    GenerationExceptionRead,
    LedgerEntryCreate,
    LedgerEntryRead,
    OccurrenceCancel,
    OccurrenceComplete,
    OccurrenceRead,
    OccurrenceReverse,
    OccurrenceStart,
    PlannerOccurrenceRead,
    PlannerWorkloadRead,
    SelfFieldVisitCreate,
    VisitAssignmentRead,
    VisitDocumentRead,
    VisitScheduleWrite,
    VisitTypeRead,
    VisitTypeWrite,
)

router = APIRouter(prefix="/visits", tags=["visits"])


@router.get("/field-request/clients", response_model=list[FieldVisitClientOption])
def field_visit_clients(
    db: Session = Depends(get_db), _: User = Depends(require_permission("visit.field.create.self"))
) -> list[dict[str, object]]:
    today = server_today()
    rows = db.execute(
        select(Client.id, Client.code, Client.name)
        .join(ClientVisitEntitlement, ClientVisitEntitlement.client_id == Client.id)
        .where(
            ClientVisitEntitlement.status == "ACTIVE",
            ClientVisitEntitlement.service_period_end >= today,
        )
        .distinct()
        .order_by(Client.name)
        .limit(300)
    )
    return [{"id": row.id, "code": row.code, "name": row.name} for row in rows]


@router.post("/field-request", response_model=OccurrenceRead, status_code=201)
def create_self_field_visit(
    data: SelfFieldVisitCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("visit.field.create.self")),
) -> ClientVisitOccurrence:
    visit_type = shared_outdoor_visit_type(db)
    entitlement = db.scalar(
        select(ClientVisitEntitlement)
        .where(
            ClientVisitEntitlement.client_id == data.client_id,
            ClientVisitEntitlement.visit_type_id == visit_type.id,
            ClientVisitEntitlement.status == "ACTIVE",
            ClientVisitEntitlement.service_period_start <= data.starts_at.date(),
            ClientVisitEntitlement.service_period_end >= data.starts_at.date(),
        )
        .order_by(ClientVisitEntitlement.service_period_end)
        .limit(1)
    )
    if not entitlement:
        raise ConflictError(
            "VISIT_ENTITLEMENT_REQUIRED",
            "The selected client has no active visit entitlement covering this date.",
        )
    sequence = (
        db.scalar(
            select(func.max(ClientVisitOccurrence.sequence_number)).where(
                ClientVisitOccurrence.entitlement_id == entitlement.id
            )
        )
        or 0
    ) + 1
    occurrence = ClientVisitOccurrence(
        entitlement_id=entitlement.id,
        contract_id=entitlement.contract_id,
        client_id=data.client_id,
        visit_type_id=visit_type.id,
        sequence_number=sequence,
        window_start=data.starts_at.date(),
        window_end=data.starts_at.date(),
        due_date=data.starts_at.date(),
        scheduled_visit_date=None,
        status="PENDING_APPROVAL",
        duration_minutes=int((data.ends_at - data.starts_at).total_seconds() // 60),
        generation_key=f"self-field-visit:{uuid.uuid4()}",
        source_version=entitlement.source_version,
        source_type="AD_HOC",
        notes=data.notes,
        version=1,
        created_by_user_id=actor.id,
    )
    db.add(occurrence)
    db.flush()
    db.add(
        ClientVisitAssignment(
            occurrence_id=occurrence.id,
            user_id=actor.id,
            starts_at=data.starts_at,
            ends_at=data.ends_at,
            timezone=data.timezone,
            status="REQUESTED",
            stable_key=f"visit-assignment:{occurrence.id}:{actor.id}",
            version=1,
            created_by_user_id=actor.id,
        )
    )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ClientVisitOccurrence",
            entity_id=str(occurrence.id),
            action="visit.field_requested",
            new_values_json=json.dumps(
                {
                    "client_id": data.client_id,
                    "starts_at": data.starts_at.isoformat(),
                    "ends_at": data.ends_at.isoformat(),
                }
            ),
        )
    )
    db.add(
        Notification(
            recipient_user_id=actor.id,
            notification_type="VISIT_REQUESTED",
            severity="INFO",
            title="Field visit submitted for approval",
            message=f"Visit request #{occurrence.id}",
            deep_link="/visit-operations",
            deduplication_key=f"field-visit-request:{occurrence.id}",
        )
    )
    db.commit()
    db.refresh(occurrence)
    return occurrence


@router.get("/field-request/mine", response_model=list[PlannerOccurrenceRead])
def my_field_visits(
    db: Session = Depends(get_db),
    actor: User = Depends(authenticated_user),
) -> list[PlannerOccurrenceRead]:
    rows = list(
        db.scalars(
            select(ClientVisitOccurrence)
            .join(ClientVisitAssignment)
            .where(
                ClientVisitAssignment.user_id == actor.id,
            )
            .order_by(ClientVisitOccurrence.created_at.desc())
            .limit(100)
        )
    )
    clients = (
        {
            row.id: row
            for row in db.scalars(
                select(Client).where(Client.id.in_({item.client_id for item in rows}))
            )
        }
        if rows
        else {}
    )
    result = []
    for row in rows:
        assignments = list(
            db.scalars(
                select(ClientVisitAssignment).where(
                    ClientVisitAssignment.occurrence_id == row.id,
                    ClientVisitAssignment.user_id == actor.id,
                )
            )
        )
        client = clients.get(row.client_id)
        values = occurrence_read(db, row).model_dump()
        values.update(
            client_code=client.code if client else None, client_name=client.name if client else None
        )
        result.append(
            PlannerOccurrenceRead(
                **values, assignments=[assignment_read(db, item) for item in assignments]
            )
        )
    return result


def shared_outdoor_visit_type(db: Session) -> VisitType:
    operation_type_id = db.scalar(
        select(InternalOperationType.id).where(InternalOperationType.code == "OUTDOOR_VISIT")
    )
    if operation_type_id is None:
        operation_type = InternalOperationType(
            code="OUTDOOR_VISIT",
            name="Outdoor / field visit",
            description="Client-site or field work that consumes visit entitlement.",
            color="#2e7d32",
            supports_client=True,
            is_active=True,
        )
        db.add(operation_type)
        db.flush()
        operation_type_id = operation_type.id
    visit_type_row = db.execute(
        select(VisitType.id, VisitType.internal_operation_type_id, VisitType.is_active).where(
            VisitType.code == "OUTDOOR_VISIT"
        )
    ).one_or_none()
    if visit_type_row is None:
        visit_type = VisitType(
            code="OUTDOOR_VISIT",
            name="Outdoor / field visit",
            internal_operation_type_id=operation_type_id,
            is_active=True,
        )
        db.add(visit_type)
        db.flush()
        return visit_type
    if (
        visit_type_row.internal_operation_type_id != operation_type_id
        or not visit_type_row.is_active
    ):
        db.execute(
            update(VisitType)
            .where(VisitType.id == visit_type_row.id)
            .values(
                internal_operation_type_id=operation_type_id,
                name="Outdoor / field visit",
                is_active=True,
            )
        )
        db.flush()
    loaded_visit_type = db.get(VisitType, visit_type_row.id)
    if loaded_visit_type is None:
        raise NotFoundError("Outdoor visit type could not be loaded.")
    return loaded_visit_type


def entitlement_read(db: Session, item: ClientVisitEntitlement) -> EntitlementRead:
    client = db.get(Client, item.client_id)
    values = EntitlementRead.model_validate(item).model_dump()
    values.update(
        client_code=client.code if client else None, client_name=client.name if client else None
    )
    return EntitlementRead(**values)


def occurrence_read(db: Session, item: ClientVisitOccurrence) -> OccurrenceRead:
    client = db.get(Client, item.client_id)
    values = OccurrenceRead.model_validate(item).model_dump()
    values.update(
        client_code=client.code if client else None, client_name=client.name if client else None
    )
    return OccurrenceRead(**values)


def assignment_read(db: Session, item: ClientVisitAssignment) -> VisitAssignmentRead:
    user = db.get(User, item.user_id)
    values = VisitAssignmentRead.model_validate(item).model_dump()
    values.update(user_name=user.full_name if user else None)
    return VisitAssignmentRead(**values)


def add_months(value: date, months: int) -> date:
    index = value.month - 1 + months
    year, month = value.year + index // 12, index % 12 + 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def ledger_balance(db: Session, entitlement_id: int) -> int:
    return int(
        db.scalar(
            select(func.coalesce(func.sum(VisitEntitlementLedgerEntry.quantity), 0)).where(
                VisitEntitlementLedgerEntry.entitlement_id == entitlement_id
            )
        )
        or 0
    )


def recurrence_windows(item: ClientVisitEntitlement) -> list[tuple[date, date]]:
    month_step = {"MONTHLY": 1, "QUARTERLY": 3, "SEMIANNUAL": 6, "ANNUAL": 12}.get(item.recurrence)
    if not month_step:
        count = max(item.allowed_visits, 1)
        days = (item.service_period_end - item.service_period_start).days + 1
        return [
            (
                item.service_period_start + timedelta(days=(days * i) // count),
                item.service_period_start + timedelta(days=(days * (i + 1)) // count - 1),
            )
            for i in range(count)
        ]
    windows: list[tuple[date, date]] = []
    start = item.service_period_start
    while start <= item.service_period_end:
        end = min(add_months(start, month_step) - timedelta(days=1), item.service_period_end)
        windows.append((start, end))
        start = end + timedelta(days=1)
    return windows


def summary(db: Session, item: ClientVisitEntitlement) -> EntitlementSummary:
    entries = list(
        db.scalars(
            select(VisitEntitlementLedgerEntry).where(
                VisitEntitlementLedgerEntry.entitlement_id == item.id
            )
        )
    )
    occurrences = list(
        db.scalars(
            select(ClientVisitOccurrence).where(
                ClientVisitOccurrence.entitlement_id == item.id,
                ClientVisitOccurrence.superseded_by_occurrence_id.is_(None),
            )
        )
    )
    entitled = sum(
        row.quantity
        for row in entries
        if row.entry_type in {"GRANT", "ADJUSTMENT", "CARRY_FORWARD"}
    )
    consumed = -sum(row.quantity for row in entries if row.entry_type in {"CONSUMPTION", "OVERAGE"})
    reserved = -sum(row.quantity for row in entries if row.entry_type in {"RESERVATION", "RELEASE"})
    planned = sum(row.status != "CANCELLED" for row in occurrences)
    completed = sum(row.status == "COMPLETED" for row in occurrences)
    scheduled = sum(
        row.scheduled_visit_date is not None and row.status not in {"CANCELLED", "COMPLETED"}
        for row in occurrences
    )
    overdue = sum(
        row.status not in {"CANCELLED", "COMPLETED"} and row.window_end < server_today()
        for row in occurrences
    )
    return EntitlementSummary(
        entitlement_id=item.id,
        entitled=entitled,
        planned=planned,
        scheduled=scheduled,
        completed=completed,
        consumed=consumed,
        reserved=max(reserved, 0),
        remaining=max(ledger_balance(db, item.id), 0),
        unplanned=max(entitled - planned, 0),
        overdue=overdue,
    )


@router.get("/types", response_model=list[VisitTypeRead])
def list_visit_types(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("visit.entitlement.view")),
) -> list[VisitTypeRead]:
    shared_outdoor_visit_type(db)
    statement = (
        select(
            VisitType.id,
            VisitType.code,
            VisitType.name,
            VisitType.internal_operation_type_id,
            InternalOperationType.code.label("operation_type_code"),
            VisitType.is_active,
        )
        .outerjoin(
            InternalOperationType, InternalOperationType.id == VisitType.internal_operation_type_id
        )
    )
    if include_inactive:
        if "visit.entitlement.manage" not in effective_permissions(db, actor).permissions:
            include_inactive = False
    if not include_inactive:
        statement = statement.where(VisitType.is_active == true())
    rows = db.execute(statement.order_by(VisitType.name)).mappings()
    return [VisitTypeRead(**row) for row in rows]


@router.post("/types", response_model=VisitTypeRead, status_code=201)
def create_visit_type(
    data: VisitTypeWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("visit.entitlement.manage")),
) -> VisitTypeRead:
    if db.scalar(select(VisitType.id).where(VisitType.code == data.code)):
        raise ConflictError("VISIT_TYPE_CODE_EXISTS", "A visit type already uses this code.")
    operation_type = (
        db.get(InternalOperationType, data.internal_operation_type_id)
        if data.internal_operation_type_id
        else None
    )
    if data.internal_operation_type_id and not operation_type:
        raise NotFoundError("Internal operation type does not exist.")
    item = VisitType(**data.model_dump())
    db.add(item)
    db.flush()
    db.add(AuditLog(actor_user_id=actor.id, entity_type="VisitType", entity_id=str(item.id), action="visit.type.created", new_values_json=json.dumps(data.model_dump())))
    db.commit()
    operation_code = operation_type.code if operation_type else None
    return VisitTypeRead.model_validate(item).model_copy(update={"operation_type_code": operation_code})


@router.put("/types/{visit_type_id}", response_model=VisitTypeRead)
def update_visit_type(
    visit_type_id: int,
    data: VisitTypeWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("visit.entitlement.manage")),
) -> VisitTypeRead:
    item = db.get(VisitType, visit_type_id)
    if not item:
        raise NotFoundError()
    duplicate = db.scalar(select(VisitType.id).where(VisitType.code == data.code, VisitType.id != item.id))
    if duplicate:
        raise ConflictError("VISIT_TYPE_CODE_EXISTS", "A visit type already uses this code.")
    operation_type = db.get(InternalOperationType, data.internal_operation_type_id) if data.internal_operation_type_id else None
    if data.internal_operation_type_id and not operation_type:
        raise NotFoundError("Internal operation type does not exist.")
    old = {"code": item.code, "name": item.name, "internal_operation_type_id": item.internal_operation_type_id, "is_active": item.is_active}
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="VisitType", entity_id=str(item.id), action="visit.type.updated", old_values_json=json.dumps(old), new_values_json=json.dumps(data.model_dump())))
    db.commit()
    return VisitTypeRead.model_validate(item).model_copy(update={"operation_type_code": operation_type.code if operation_type else None})


def _create_entitlement(
    data: EntitlementCreate, db: Session, actor: User
) -> ClientVisitEntitlement:
    if data.visit_type_id is None:
        data = data.model_copy(update={"visit_type_id": shared_outdoor_visit_type(db).id})
    contract = db.get(Contract, data.contract_id)
    client = db.get(Client, data.client_id)
    if not contract or not client or not db.get(VisitType, data.visit_type_id):
        raise NotFoundError()
    eligible_clients = set(contract.linked_client_ids) | {contract.client_id}
    if data.client_id not in eligible_clients:
        raise ConflictError(
            "VISIT_CLIENT_NOT_CONTRACTED", "The exact client is not linked to this contract."
        )
    if (
        data.service_period_start < contract.start_date
        or data.service_period_end > contract.end_date
    ):
        raise ConflictError(
            "VISIT_PERIOD_OUTSIDE_CONTRACT", "Visit period must be within contract dates."
        )
    if data.service_id and not db.get(ServiceCatalogItem, data.service_id):
        raise NotFoundError()
    if data.department_id and not db.get(Department, data.department_id):
        raise NotFoundError()
    location = (
        db.get(ClientLocation, data.preferred_location_id) if data.preferred_location_id else None
    )
    if location and location.client_id != data.client_id:
        raise ConflictError(
            "VISIT_LOCATION_CLIENT_MISMATCH", "Preferred location must belong to the exact client."
        )
    overlap = db.scalar(
        select(ClientVisitEntitlement.id)
        .where(
            ClientVisitEntitlement.contract_id == data.contract_id,
            ClientVisitEntitlement.client_id == data.client_id,
            ClientVisitEntitlement.visit_type_id == data.visit_type_id,
            ClientVisitEntitlement.service_id == data.service_id,
            ClientVisitEntitlement.status.in_(("ACTIVE", "SUSPENDED")),
            ClientVisitEntitlement.service_period_start <= data.service_period_end,
            ClientVisitEntitlement.service_period_end >= data.service_period_start,
        )
        .limit(1)
    )
    if overlap:
        raise ConflictError(
            "VISIT_ENTITLEMENT_OVERLAP",
            "An active entitlement already overlaps this exact scope and period.",
        )
    item = ClientVisitEntitlement(
        status="ACTIVE",
        source_version=1,
        version=1,
        created_by_user_id=actor.id,
        **data.model_dump(),
    )
    db.add(item)
    db.flush()
    db.add(
        VisitEntitlementLedgerEntry(
            entitlement_id=item.id,
            entry_type="GRANT",
            quantity=data.allowed_visits,
            idempotency_key=f"entitlement-grant:{item.id}:v1",
            source_type="ENTITLEMENT",
            source_id=str(item.id),
            reason="Opening contractual visit allowance",
            created_by_user_id=actor.id,
        )
    )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ClientVisitEntitlement",
            entity_id=str(item.id),
            action="visit.entitlement.created",
            new_values_json=json.dumps(data.model_dump(), default=str),
        )
    )
    return item


@router.post("/entitlements", response_model=EntitlementRead, status_code=201)
def create_entitlement(
    data: EntitlementCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("visit.entitlement.manage")),
) -> ClientVisitEntitlement:
    item = _create_entitlement(data, db, actor)
    db.commit()
    db.refresh(item)
    return item


@router.post("/entitlements/bulk", response_model=list[EntitlementRead], status_code=201)
def create_entitlements_bulk(
    data: EntitlementBulkCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("visit.entitlement.manage")),
) -> list[ClientVisitEntitlement]:
    client_ids = list(dict.fromkeys(data.client_ids))
    common = data.model_dump(exclude={"client_id", "client_ids"})
    try:
        items = [
            _create_entitlement(EntitlementCreate(**common, client_id=client_id), db, actor)
            for client_id in client_ids
        ]
        db.commit()
    except Exception:
        db.rollback()
        raise
    for item in items:
        db.refresh(item)
    return items


@router.get("/entitlements", response_model=list[EntitlementRead])
def list_entitlements(
    contract_id: int | None = None,
    client_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("visit.entitlement.view")),
) -> list[EntitlementRead]:
    statement = select(ClientVisitEntitlement)
    if contract_id is not None:
        statement = statement.where(ClientVisitEntitlement.contract_id == contract_id)
    if client_id is not None:
        statement = statement.where(ClientVisitEntitlement.client_id == client_id)
    return [
        entitlement_read(db, item)
        for item in db.scalars(
            statement.order_by(
                ClientVisitEntitlement.service_period_start.desc(), ClientVisitEntitlement.id.desc()
            )
        )
    ]


@router.get("/entitlements/{entitlement_id}", response_model=EntitlementRead)
def read_entitlement(
    entitlement_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("visit.entitlement.view")),
) -> ClientVisitEntitlement:
    item = db.get(ClientVisitEntitlement, entitlement_id)
    if not item:
        raise NotFoundError()
    return item


@router.post(
    "/entitlements/{entitlement_id}/ledger", response_model=LedgerEntryRead, status_code=201
)
def add_ledger_entry(
    entitlement_id: int,
    data: LedgerEntryCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("visit.entitlement.manage")),
) -> VisitEntitlementLedgerEntry:
    if not db.get(ClientVisitEntitlement, entitlement_id):
        raise NotFoundError()
    existing = db.scalar(
        select(VisitEntitlementLedgerEntry).where(
            VisitEntitlementLedgerEntry.idempotency_key == data.idempotency_key
        )
    )
    if existing:
        return existing
    if data.entry_type in {"RESERVATION", "EXPIRY", "OVERAGE"} and data.quantity > 0:
        raise ConflictError(
            "INVALID_VISIT_LEDGER_SIGN", "This entry type requires a negative quantity."
        )
    if data.entry_type in {"CARRY_FORWARD", "RELEASE", "REVERSAL"} and data.quantity < 0:
        raise ConflictError(
            "INVALID_VISIT_LEDGER_SIGN", "This entry type requires a positive quantity."
        )
    if data.reversal_of_entry_id:
        original = db.get(VisitEntitlementLedgerEntry, data.reversal_of_entry_id)
        if (
            not original
            or original.entitlement_id != entitlement_id
            or data.quantity != -original.quantity
        ):
            raise ConflictError(
                "INVALID_VISIT_LEDGER_REVERSAL",
                "Reversal must exactly compensate an entry in this entitlement.",
            )
    item = VisitEntitlementLedgerEntry(
        entitlement_id=entitlement_id, created_by_user_id=actor.id, **data.model_dump()
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="VisitEntitlementLedgerEntry",
            entity_id=str(item.id),
            action="visit.entitlement.adjusted",
            reason=data.reason,
            new_values_json=json.dumps(data.model_dump(), default=str),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.post("/entitlements/{entitlement_id}/generate", response_model=list[OccurrenceRead])
def generate_occurrences(
    entitlement_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("visit.occurrence.generate")),
) -> list[ClientVisitOccurrence]:
    item = db.get(ClientVisitEntitlement, entitlement_id)
    if not item:
        raise NotFoundError()
    if item.status != "ACTIVE":
        raise ConflictError(
            "VISIT_ENTITLEMENT_NOT_ACTIVE", "Only active entitlements can generate occurrences."
        )
    if item.scheduling_mode == "ON_DEMAND":
        raise ConflictError(
            "ON_DEMAND_VISIT_NOT_GENERATED",
            "On-demand allowances are consumed when a visit is requested and do not generate planned occurrences.",
        )
    windows = recurrence_windows(item)
    if not windows or item.allowed_visits < 0:
        exception = VisitGenerationException(
            entitlement_id=item.id,
            exception_code="IMPOSSIBLE_SCHEDULE",
            detail="No valid recurrence windows could be generated.",
            source_version=item.source_version,
            status="OPEN",
        )
        db.add(exception)
        db.commit()
        raise ConflictError("IMPOSSIBLE_VISIT_SCHEDULE", exception.detail)
    result: list[ClientVisitOccurrence] = []
    for index in range(item.allowed_visits):
        window_index = min((index * len(windows)) // item.allowed_visits, len(windows) - 1)
        window_start, window_end = windows[window_index]
        sequence = index + 1
        key = f"visit:{item.id}:v{item.source_version}:seq{sequence}"
        occurrence = db.scalar(
            select(ClientVisitOccurrence).where(ClientVisitOccurrence.generation_key == key)
        )
        if not occurrence:
            occurrence = ClientVisitOccurrence(
                entitlement_id=item.id,
                contract_id=item.contract_id,
                client_id=item.client_id,
                visit_type_id=item.visit_type_id,
                sequence_number=sequence,
                window_start=window_start,
                window_end=window_end,
                due_date=window_end,
                status="PLANNED",
                duration_minutes=item.default_duration_minutes,
                generation_key=key,
                source_version=item.source_version,
                version=1,
                created_by_user_id=actor.id,
            )
            db.add(occurrence)
            db.flush()
        result.append(occurrence)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ClientVisitEntitlement",
            entity_id=str(item.id),
            action="visit.occurrences.generated",
            new_values_json=json.dumps(
                {"source_version": item.source_version, "count": len(result)}
            ),
        )
    )
    db.commit()
    for row in result:
        db.refresh(row)
    return result


@router.get("/entitlements/{entitlement_id}/occurrences", response_model=list[OccurrenceRead])
def list_occurrences(
    entitlement_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("visit.entitlement.view")),
) -> list[ClientVisitOccurrence]:
    if not db.get(ClientVisitEntitlement, entitlement_id):
        raise NotFoundError()
    return list(
        db.scalars(
            select(ClientVisitOccurrence)
            .where(ClientVisitOccurrence.entitlement_id == entitlement_id)
            .order_by(ClientVisitOccurrence.sequence_number, ClientVisitOccurrence.source_version)
        )
    )


@router.post("/occurrences/{occurrence_id}/complete", response_model=OccurrenceRead)
def complete_occurrence(
    occurrence_id: int,
    data: OccurrenceComplete,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("visit.occurrence.complete")),
) -> ClientVisitOccurrence:
    occurrence = db.scalar(
        select(ClientVisitOccurrence)
        .where(ClientVisitOccurrence.id == occurrence_id)
        .with_for_update()
    )
    if not occurrence:
        raise NotFoundError()
    if occurrence.version != data.expected_version:
        raise ConflictError("STALE_VISIT_OCCURRENCE", "The visit changed; refresh and retry.")
    if occurrence.status == "COMPLETED":
        return occurrence
    if occurrence.status == "CANCELLED":
        raise ConflictError(
            "CANCELLED_VISIT_CANNOT_COMPLETE", "A cancelled visit cannot be completed."
        )
    if not db.scalar(
        select(VisitDocument.id)
        .where(
            VisitDocument.occurrence_id == occurrence.id,
            VisitDocument.is_superseded == false(),
            VisitDocument.scan_status != "REJECTED",
        )
        .limit(1)
    ):  # noqa: E712
        raise ConflictError(
            "VISIT_DOCUMENT_REQUIRED", "Upload at least one valid visit document before completion."
        )
    balance = ledger_balance(db, occurrence.entitlement_id)
    entry_type = "CONSUMPTION" if balance > 0 else "OVERAGE"
    if balance <= 0 and not data.allow_overage:
        raise ConflictError(
            "VISIT_ENTITLEMENT_EXHAUSTED", "No remaining visit entitlement is available."
        )
    ledger = VisitEntitlementLedgerEntry(
        entitlement_id=occurrence.entitlement_id,
        entry_type=entry_type,
        quantity=-1,
        idempotency_key=f"visit-completion:{occurrence.id}",
        source_type="VISIT_OCCURRENCE",
        source_id=str(occurrence.id),
        reason="Visit completed with required outcome evidence",
        created_by_user_id=actor.id,
    )
    db.add(ledger)
    db.flush()
    occurrence.completion_version += 1
    evidence = VisitCompletionEvidence(
        occurrence_id=occurrence.id,
        completion_version=occurrence.completion_version,
        actual_started_at=data.actual_started_at,
        actual_ended_at=data.actual_ended_at,
        outcome_code=data.outcome_code,
        result=data.result,
        next_action=data.next_action,
        notes=data.notes,
        customer_acknowledged=data.customer_acknowledged,
        customer_acknowledged_by=data.customer_acknowledged_by,
        customer_acknowledged_at=data.customer_acknowledged_at,
        completed_by_user_id=actor.id,
    )
    db.add(evidence)
    occurrence.status = "COMPLETED"
    occurrence.actual_visit_date = data.actual_visit_date
    occurrence.actual_started_at = data.actual_started_at
    occurrence.actual_ended_at = data.actual_ended_at
    occurrence.outcome_code = data.outcome_code
    occurrence.result = data.result
    occurrence.next_action = data.next_action
    occurrence.notes = data.notes
    occurrence.customer_acknowledged = data.customer_acknowledged
    occurrence.customer_acknowledged_by = data.customer_acknowledged_by
    occurrence.customer_acknowledged_at = data.customer_acknowledged_at
    occurrence.completion_ledger_entry_id = ledger.id
    occurrence.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ClientVisitOccurrence",
            entity_id=str(occurrence.id),
            action="visit.completed",
            new_values_json=json.dumps(data.model_dump(), default=str),
        )
    )
    db.commit()
    db.refresh(occurrence)
    return occurrence


@router.post("/occurrences/{occurrence_id}/reopen", response_model=OccurrenceRead)
def reopen_occurrence(
    occurrence_id: int,
    data: OccurrenceReverse,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("visit.occurrence.complete")),
) -> ClientVisitOccurrence:
    occurrence = db.scalar(
        select(ClientVisitOccurrence)
        .where(ClientVisitOccurrence.id == occurrence_id)
        .with_for_update()
    )
    if not occurrence:
        raise NotFoundError()
    if (
        occurrence.version != data.expected_version
        or occurrence.status != "COMPLETED"
        or not occurrence.completion_ledger_entry_id
    ):
        raise ConflictError(
            "VISIT_REOPEN_CONFLICT", "Only the current completed visit can be reopened."
        )
    original = db.get(VisitEntitlementLedgerEntry, occurrence.completion_ledger_entry_id)
    reversal = VisitEntitlementLedgerEntry(
        entitlement_id=occurrence.entitlement_id,
        entry_type="REVERSAL",
        quantity=1,
        idempotency_key=f"visit-reopen:{occurrence.id}:v{occurrence.version}",
        source_type="VISIT_OCCURRENCE",
        source_id=str(occurrence.id),
        reason=data.reason,
        reversal_of_entry_id=original.id if original else None,
        created_by_user_id=actor.id,
    )
    db.add(reversal)
    occurrence.status = "REOPENED"
    occurrence.completion_ledger_entry_id = None
    occurrence.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ClientVisitOccurrence",
            entity_id=str(occurrence.id),
            action="visit.reopened",
            reason=data.reason,
        )
    )
    db.commit()
    db.refresh(occurrence)
    return occurrence


@router.post("/occurrences/{occurrence_id}/start", response_model=OccurrenceRead)
def start_occurrence(
    occurrence_id: int,
    data: OccurrenceStart,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("visit.occurrence.complete")),
) -> ClientVisitOccurrence:
    occurrence = db.scalar(
        select(ClientVisitOccurrence)
        .where(ClientVisitOccurrence.id == occurrence_id)
        .with_for_update()
    )
    if not occurrence:
        raise NotFoundError()
    if occurrence.version != data.expected_version:
        raise ConflictError("STALE_VISIT_OCCURRENCE", "The visit changed; refresh and retry.")
    if occurrence.status not in {"SCHEDULED", "RESCHEDULED", "REOPENED"}:
        raise ConflictError("VISIT_NOT_STARTABLE", "Only a scheduled or reopened visit can start.")
    occurrence.status = "IN_PROGRESS"
    occurrence.actual_started_at = data.started_at
    occurrence.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ClientVisitOccurrence",
            entity_id=str(occurrence.id),
            action="visit.started",
            new_values_json=json.dumps(data.model_dump(), default=str),
        )
    )
    db.commit()
    db.refresh(occurrence)
    return occurrence


@router.post("/occurrences/{occurrence_id}/cancel", response_model=OccurrenceRead)
def cancel_occurrence(
    occurrence_id: int,
    data: OccurrenceCancel,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("visit.schedule")),
) -> ClientVisitOccurrence:
    occurrence = db.scalar(
        select(ClientVisitOccurrence)
        .where(ClientVisitOccurrence.id == occurrence_id)
        .with_for_update()
    )
    if not occurrence:
        raise NotFoundError()
    if occurrence.version != data.expected_version:
        raise ConflictError("STALE_VISIT_OCCURRENCE", "The visit changed; refresh and retry.")
    if occurrence.status == "COMPLETED":
        raise ConflictError(
            "COMPLETED_VISIT_CANNOT_CANCEL", "Reopen a completed visit before cancellation."
        )
    occurrence.status = "CANCELLED"
    occurrence.version += 1
    for assignment in db.scalars(
        select(ClientVisitAssignment).where(
            ClientVisitAssignment.occurrence_id == occurrence.id,
            ClientVisitAssignment.status == "ASSIGNED",
        )
    ):
        assignment.status = "CANCELLED"
        assignment.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ClientVisitOccurrence",
            entity_id=str(occurrence.id),
            action="visit.cancelled",
            reason=data.reason,
        )
    )
    db.commit()
    db.refresh(occurrence)
    return occurrence


@router.get("/occurrences/{occurrence_id}/documents", response_model=list[VisitDocumentRead])
def list_visit_documents(
    occurrence_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("visit.document.download")),
) -> list[VisitDocument]:
    if not db.get(ClientVisitOccurrence, occurrence_id):
        raise NotFoundError()
    return list(
        db.scalars(
            select(VisitDocument)
            .where(VisitDocument.occurrence_id == occurrence_id)
            .order_by(VisitDocument.created_at.desc())
        )
    )


@router.post(
    "/occurrences/{occurrence_id}/documents", response_model=VisitDocumentRead, status_code=201
)
async def upload_visit_document(
    occurrence_id: int,
    upload: UploadFile = File(...),
    document_type: str = Query(
        default="VISIT_REPORT", pattern="^(VISIT_REPORT|SIGNED_FORM|SCREENSHOT|PDF|IMAGE|OTHER)$"
    ),
    retention_until: date | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(authenticated_user),
    settings: Settings = Depends(get_settings),
) -> VisitDocument:
    if not db.get(ClientVisitOccurrence, occurrence_id):
        raise NotFoundError()
    permissions = set(effective_permissions(db, actor).permissions)
    is_own_field_visit = (
        "visit.field.create.self" in permissions
        and db.scalar(
            select(ClientVisitAssignment.id)
            .where(
                ClientVisitAssignment.occurrence_id == occurrence_id,
                ClientVisitAssignment.user_id == actor.id,
            )
            .limit(1)
        )
        is not None
    )
    if "visit.document.upload" not in permissions and not is_own_field_visit:
        raise ConflictError(
            "VISIT_DOCUMENT_UPLOAD_FORBIDDEN",
            "You may only upload documents to your own field visits.",
        )
    document = await store_visit_document(upload, occurrence_id, document_type, settings)
    document.retention_until = retention_until
    document.uploaded_by_user_id = actor.id
    db.add(document)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="VisitDocument",
            entity_id=str(document.id),
            action="visit.document.uploaded",
            new_values_json=json.dumps(
                {
                    "filename": document.original_filename,
                    "document_type": document_type,
                    "sha256": document.sha256,
                    "retention_until": retention_until,
                },
                default=str,
            ),
        )
    )
    db.commit()
    db.refresh(document)
    return document


@router.get("/occurrences/{occurrence_id}/documents/{document_id}/download")
def download_visit_document(
    occurrence_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("visit.document.download")),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    document = db.get(VisitDocument, document_id)
    if not document or document.occurrence_id != occurrence_id:
        raise NotFoundError()
    path = visit_document_path(document, settings)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="VisitDocument",
            entity_id=str(document.id),
            action="visit.document.downloaded",
        )
    )
    db.commit()
    return FileResponse(path, media_type=document.content_type, filename=document.original_filename)


@router.get("/entitlements/{entitlement_id}/summary", response_model=EntitlementSummary)
def entitlement_summary(
    entitlement_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("visit.entitlement.view")),
) -> EntitlementSummary:
    item = db.get(ClientVisitEntitlement, entitlement_id)
    if not item:
        raise NotFoundError()
    return summary(db, item)


@router.get("/generation-exceptions", response_model=list[GenerationExceptionRead])
def list_generation_exceptions(
    db: Session = Depends(get_db), _: User = Depends(require_permission("visit.entitlement.manage"))
) -> list[VisitGenerationException]:
    return list(
        db.scalars(
            select(VisitGenerationException)
            .where(VisitGenerationException.status == "OPEN")
            .order_by(VisitGenerationException.created_at)
        )
    )


def assignment_conflicts(
    db: Session,
    occurrence: ClientVisitOccurrence,
    user: User,
    starts_at: datetime,
    ends_at: datetime,
) -> list[str]:
    codes: list[str] = []
    if starts_at.date() < occurrence.window_start or starts_at.date() > occurrence.window_end:
        codes.append("OUTSIDE_WINDOW")
    if db.scalar(
        select(ClientVisitAssignment.id)
        .where(
            ClientVisitAssignment.user_id == user.id,
            ClientVisitAssignment.occurrence_id != occurrence.id,
            ClientVisitAssignment.status == "ASSIGNED",
            ClientVisitAssignment.starts_at < ends_at,
            ClientVisitAssignment.ends_at > starts_at,
        )
        .limit(1)
    ):
        codes.append("VISIT_OVERLAP")
    if db.scalar(
        select(Shift.id)
        .join(ShiftType, ShiftType.id == Shift.shift_type_id)
        .where(
            Shift.user_id == user.id,
            ShiftType.code == "LEAVE",
            Shift.status != "CANCELLED",
            Shift.starts_at < ends_at,
            Shift.ends_at > starts_at,
        )
        .limit(1)
    ):
        codes.append("EMPLOYEE_ON_LEAVE")
    entitlement = db.get(ClientVisitEntitlement, occurrence.entitlement_id)
    if (
        entitlement
        and entitlement.department_id
        and user.department_id != entitlement.department_id
    ):
        codes.append("DEPARTMENT_MISMATCH")
    return codes


def _same_day_shifts(
    db: Session, occurrence: ClientVisitOccurrence, user_id: int, starts_at: datetime
) -> list[Shift]:
    day_start = datetime.combine(starts_at.date(), time.min, tzinfo=starts_at.tzinfo)
    day_end = day_start + timedelta(days=1)
    auto_note = f"Auto-created for visit occurrence #{occurrence.id}."
    return list(
        db.scalars(
            select(Shift)
            .join(ShiftType, ShiftType.id == Shift.shift_type_id)
            .where(
                Shift.user_id == user_id,
                Shift.status.in_(("DRAFT", "PUBLISHED", "APPROVED")),
                ShiftType.code != "LEAVE",
                Shift.starts_at < day_end,
                Shift.ends_at > day_start,
                (Shift.notes.is_(None)) | (Shift.notes != auto_note),
            )
            .order_by(Shift.starts_at)
        )
    )


def _create_visit_shift(
    db: Session,
    occurrence: ClientVisitOccurrence,
    user: User,
    data: VisitScheduleWrite,
    actor: User,
) -> Shift:
    shift_type = db.scalar(
        select(ShiftType).where(ShiftType.code == "OUTDOOR_VISIT", ShiftType.is_active == true())
    )
    if not shift_type:
        shift_type = ShiftType(
            code="OUTDOOR_VISIT",
            name="Outdoor / field visit",
            description="Automatically created coverage for a scheduled client visit.",
            color="#ef6c00",
            is_on_call=False,
            is_active=True,
        )
        db.add(shift_type)
        db.flush()
    shift = Shift(
        shift_type_id=shift_type.id,
        user_id=user.id,
        team=user.department,
        work_location="OFFICE",
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        notes=f"Auto-created for visit occurrence #{occurrence.id}.",
        overlap_override_reason=data.shift_decision_reason,
        status="APPROVED",
        created_by_user_id=actor.id,
    )
    db.add(shift)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Shift",
            entity_id=str(shift.id),
            action="shift.visit_auto_created",
            reason=data.shift_decision_reason,
            new_values_json=json.dumps({"occurrence_id": occurrence.id, "user_id": user.id}),
        )
    )
    return shift


@router.post("/occurrences/{occurrence_id}/schedule", response_model=PlannerOccurrenceRead)
def schedule_occurrence(
    occurrence_id: int,
    data: VisitScheduleWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("visit.schedule")),
) -> PlannerOccurrenceRead:
    occurrence = db.scalar(
        select(ClientVisitOccurrence)
        .where(ClientVisitOccurrence.id == occurrence_id)
        .with_for_update()
    )
    if not occurrence:
        raise NotFoundError()
    if occurrence.version != data.expected_version:
        raise ConflictError("STALE_VISIT_OCCURRENCE", "The visit changed; refresh and retry.")
    if occurrence.status in {"COMPLETED", "CANCELLED", "SUPERSEDED"}:
        raise ConflictError(
            "VISIT_NOT_SCHEDULABLE", "This visit is not schedulable in its current state."
        )
    users = list(
        db.scalars(
            select(User).where(
                User.id.in_(set(data.user_ids)), User.is_active == true()
            )
        )
    )
    if len(users) != len(set(data.user_ids)):
        raise ConflictError("INVALID_VISIT_ASSIGNEE", "Every assignee must be an active employee.")
    same_day = {
        user.id: _same_day_shifts(db, occurrence, user.id, data.starts_at) for user in users
    }
    shifts_requiring_decision = [shift for values in same_day.values() for shift in values]
    if shifts_requiring_decision and not data.shift_action:
        raise ConflictError(
            "VISIT_SHIFT_DECISION_REQUIRED",
            "The selected engineer already has a shift on this day. Choose how to handle it before scheduling the visit.",
            {
                "existing_shifts": [
                    {
                        "id": row.id,
                        "user_id": row.user_id,
                        "starts_at": row.starts_at.isoformat(),
                        "ends_at": row.ends_at.isoformat(),
                        "status": row.status,
                    }
                    for row in shifts_requiring_decision
                ]
            },
        )
    if data.shift_action == "TRANSFER_AND_CREATE":
        permissions = set(effective_permissions(db, actor).permissions)
        if not ({"shift.assign_employee", "shift.manage"} & permissions):
            raise ConflictError(
                "SHIFT_TRANSFER_FORBIDDEN",
                "You do not have permission to transfer the existing shift.",
            )
        shift = db.get(Shift, data.existing_shift_id)
        replacement = db.get(User, data.replacement_user_id)
        if (
            not shift
            or shift not in shifts_requiring_decision
            or not replacement
            or not replacement.is_active
            or replacement.user_type != "EMPLOYEE"
        ):
            raise ConflictError(
                "INVALID_SHIFT_TRANSFER",
                "Select a valid same-day shift and active replacement engineer.",
            )
        overlap = db.scalar(
            select(Shift.id)
            .where(
                Shift.user_id == replacement.id,
                Shift.id != shift.id,
                Shift.status != "CANCELLED",
                Shift.starts_at < shift.ends_at,
                Shift.ends_at > shift.starts_at,
            )
            .limit(1)
        )
        if overlap:
            raise ConflictError(
                "REPLACEMENT_SHIFT_OVERLAP",
                "The replacement engineer already has an overlapping shift.",
            )
        old_user_id = shift.user_id
        shift.user_id = replacement.id
        shift.overlap_override_reason = data.shift_decision_reason
        db.add(
            AuditLog(
                actor_user_id=actor.id,
                entity_type="Shift",
                entity_id=str(shift.id),
                action="shift.visit_transferred",
                reason=data.shift_decision_reason,
                old_values_json=json.dumps({"user_id": old_user_id}),
                new_values_json=json.dumps(
                    {"user_id": replacement.id, "occurrence_id": occurrence.id}
                ),
            )
        )
    for user in users:
        _create_visit_shift(db, occurrence, user, data, actor)
    conflicts = {
        user.id: assignment_conflicts(db, occurrence, user, data.starts_at, data.ends_at)
        for user in users
    }
    active_conflicts = sorted({code for values in conflicts.values() for code in values})
    if active_conflicts and (
        not data.override_reason
        or "visit.override_conflict" not in set(effective_permissions(db, actor).permissions)
    ):
        raise ConflictError(
            "VISIT_PLANNER_CONFLICT",
            f"Resolve or authorize these conflicts: {', '.join(active_conflicts)}.",
        )
    existing = {
        row.user_id: row
        for row in db.scalars(
            select(ClientVisitAssignment).where(
                ClientVisitAssignment.occurrence_id == occurrence.id
            )
        )
    }
    selected = set(data.user_ids)
    for user_id, existing_row in existing.items():
        if user_id not in selected and existing_row.status == "ASSIGNED":
            existing_row.status = "CANCELLED"
            existing_row.version += 1
    assignments: list[ClientVisitAssignment] = []
    for user in users:
        row = existing.get(user.id)
        if not row:
            row = ClientVisitAssignment(
                occurrence_id=occurrence.id,
                user_id=user.id,
                stable_key=f"visit-assignment:{occurrence.id}:{user.id}",
                created_by_user_id=actor.id,
                version=0,
            )
            db.add(row)
        row.starts_at = data.starts_at
        row.ends_at = data.ends_at
        row.timezone = data.timezone
        row.status = "ASSIGNED"
        row.conflict_codes = ",".join(conflicts[user.id]) or None
        row.override_reason = data.override_reason
        row.version += 1
        assignments.append(row)
        db.add(
            Notification(
                recipient_user_id=user.id,
                notification_type="VISIT_ASSIGNED",
                severity="INFO",
                title=f"Visit scheduled for {data.starts_at.date()}",
                message=f"Visit occurrence #{occurrence.id}",
                deep_link="/shifts",
                deduplication_key=f"visit-assigned:{occurrence.id}:{user.id}:v{occurrence.version + 1}",
            )
        )
    was_scheduled = occurrence.scheduled_visit_date is not None
    occurrence.scheduled_visit_date = data.starts_at.date()
    occurrence.duration_minutes = int((data.ends_at - data.starts_at).total_seconds() // 60)
    occurrence.status = "RESCHEDULED" if was_scheduled else "SCHEDULED"
    occurrence.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ClientVisitOccurrence",
            entity_id=str(occurrence.id),
            action="visit.rescheduled" if was_scheduled else "visit.scheduled",
            reason=data.override_reason,
            new_values_json=json.dumps(
                {
                    "starts_at": data.starts_at.isoformat(),
                    "ends_at": data.ends_at.isoformat(),
                    "user_ids": data.user_ids,
                    "conflicts": conflicts,
                }
            ),
        )
    )
    db.commit()
    db.refresh(occurrence)
    return PlannerOccurrenceRead(
        **occurrence_read(db, occurrence).model_dump(),
        assignments=[assignment_read(db, row) for row in assignments],
    )


@router.post("/bulk", response_model=BulkVisitResult, status_code=201)
def create_bulk_visits(
    data: BulkVisitCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("visit.schedule")),
) -> BulkVisitResult:
    permissions = set(effective_permissions(db, actor).permissions)
    created: list[int] = []
    for request_row in data.rows:
        entitlement = (
            db.get(ClientVisitEntitlement, request_row.entitlement_id)
            if request_row.entitlement_id
            else db.scalar(
                select(ClientVisitEntitlement)
                .where(
                    ClientVisitEntitlement.contract_id == request_row.contract_id,
                    ClientVisitEntitlement.client_id == request_row.client_id,
                    ClientVisitEntitlement.status == "ACTIVE",
                    ClientVisitEntitlement.service_period_start <= request_row.starts_at.date(),
                    ClientVisitEntitlement.service_period_end >= request_row.starts_at.date(),
                )
                .order_by(ClientVisitEntitlement.service_period_end)
                .limit(1)
            )
        )
        if (
            not entitlement
            or entitlement.contract_id != request_row.contract_id
            or entitlement.client_id != request_row.client_id
        ):
            raise ConflictError(
                "VISIT_ENTITLEMENT_REQUIRED",
                "Every visit row requires an active exact-client contract entitlement covering its date.",
            )
        if request_row.ticket_id:
            ticket = db.get(Ticket, request_row.ticket_id)
            if not ticket or ticket.client_id != request_row.client_id:
                raise ConflictError(
                    "VISIT_TICKET_CLIENT_MISMATCH",
                    "The linked ticket must belong to the visit client.",
                )
        if request_row.internal_operation_id:
            operation = db.get(InternalOperation, request_row.internal_operation_id)
            if not operation or operation.client_id != request_row.client_id:
                raise ConflictError(
                    "VISIT_OPERATION_CLIENT_MISMATCH",
                    "The linked internal operation must belong to the visit client.",
                )
        users = list(
            db.scalars(
                select(User).where(User.id.in_(request_row.user_ids), User.is_active.in_([True]))
            )
        )
        if len(users) != len(request_row.user_ids):
            raise ConflictError("INVALID_VISIT_ASSIGNEE", "Every visit engineer must be active.")
        sequence = (
            db.scalar(
                select(func.max(ClientVisitOccurrence.sequence_number)).where(
                    ClientVisitOccurrence.entitlement_id == entitlement.id
                )
            )
            or 0
        ) + 1
        occurrence = ClientVisitOccurrence(
            entitlement_id=entitlement.id,
            contract_id=entitlement.contract_id,
            client_id=entitlement.client_id,
            visit_type_id=request_row.visit_type_id or entitlement.visit_type_id,
            sequence_number=sequence,
            window_start=request_row.starts_at.date(),
            window_end=request_row.starts_at.date(),
            due_date=request_row.starts_at.date(),
            scheduled_visit_date=request_row.starts_at.date(),
            status="SCHEDULED",
            duration_minutes=int(
                (request_row.ends_at - request_row.starts_at).total_seconds() // 60
            ),
            generation_key=f"bulk-visit:{uuid.uuid4()}",
            source_version=entitlement.source_version,
            source_type=request_row.source_type,
            ticket_id=request_row.ticket_id,
            internal_operation_id=request_row.internal_operation_id,
            notes=request_row.notes,
            version=1,
            created_by_user_id=actor.id,
        )
        db.add(occurrence)
        db.flush()
        visit_client = db.get(Client, request_row.client_id)
        for user in users:
            conflicts = assignment_conflicts(
                db, occurrence, user, request_row.starts_at, request_row.ends_at
            )
            if conflicts and (
                not data.override_reason or "visit.override_conflict" not in permissions
            ):
                raise ConflictError(
                    "VISIT_PLANNER_CONFLICT", f"{user.full_name}: {', '.join(conflicts)}"
                )
            db.add(
                ClientVisitAssignment(
                    occurrence_id=occurrence.id,
                    user_id=user.id,
                    starts_at=request_row.starts_at,
                    ends_at=request_row.ends_at,
                    timezone=request_row.timezone,
                    status="ASSIGNED",
                    stable_key=f"visit-assignment:{occurrence.id}:{user.id}",
                    conflict_codes=",".join(conflicts) or None,
                    override_reason=data.override_reason,
                    version=1,
                    created_by_user_id=actor.id,
                )
            )
            db.add(
                Notification(
                    recipient_user_id=user.id,
                    notification_type="VISIT_ASSIGNED",
                    severity="INFO",
                    title=f"Visit scheduled for {request_row.starts_at.date()}",
                    message=visit_client.name if visit_client else "Client visit",
                    deep_link="/visit-operations",
                    deduplication_key=f"bulk-visit:{occurrence.id}:{user.id}",
                )
            )
        created.append(occurrence.id)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ClientVisitOccurrence",
            entity_id=",".join(map(str, created)),
            action="visit.bulk_created",
            reason=data.override_reason,
            new_values_json=json.dumps({"count": len(created)}),
        )
    )
    db.commit()
    return BulkVisitResult(created=len(created), occurrence_ids=created)


@router.get("/planner", response_model=list[PlannerOccurrenceRead])
def visit_planner(
    starts_before: datetime,
    ends_after: datetime,
    department_id: int | None = None,
    client_id: int | None = None,
    client_ids: str | None = None,
    source_type: str | None = None,
    unassigned_only: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("visit.entitlement.view")),
) -> list[PlannerOccurrenceRead]:
    statement = (
        select(ClientVisitOccurrence)
        .join(
            ClientVisitEntitlement,
            ClientVisitEntitlement.id == ClientVisitOccurrence.entitlement_id,
        )
        .where(
            ClientVisitOccurrence.window_start <= starts_before.date(),
            ClientVisitOccurrence.window_end >= ends_after.date(),
            ClientVisitOccurrence.status.notin_(("CANCELLED", "SUPERSEDED")),
        )
    )
    if department_id is not None:
        statement = statement.where(ClientVisitEntitlement.department_id == department_id)
    if client_id is not None:
        statement = statement.where(ClientVisitOccurrence.client_id == client_id)
    if client_ids:
        selected_ids = {int(value) for value in client_ids.split(",") if value.strip().isdigit()}
        if selected_ids:
            statement = statement.where(ClientVisitOccurrence.client_id.in_(selected_ids))
    if source_type:
        statement = statement.where(
            ClientVisitOccurrence.source_type.in_(
                [value.strip() for value in source_type.split(",") if value.strip()]
            )
        )
    rows = list(
        db.scalars(statement.order_by(ClientVisitOccurrence.due_date, ClientVisitOccurrence.id))
    )
    if not rows:
        return []
    occurrence_ids = [row.id for row in rows]
    entitlement_ids = {row.entitlement_id for row in rows}
    client_ids_in_result = {row.client_id for row in rows}
    assignment_rows = list(
        db.scalars(
            select(ClientVisitAssignment).where(
                ClientVisitAssignment.occurrence_id.in_(occurrence_ids),
                ClientVisitAssignment.status.in_(("ASSIGNED", "REQUESTED")),
            )
        )
    )
    users = (
        {
            row.id: row
            for row in db.scalars(
                select(User).where(User.id.in_({item.user_id for item in assignment_rows}))
            )
        }
        if assignment_rows
        else {}
    )
    clients = {
        row.id: row for row in db.scalars(select(Client).where(Client.id.in_(client_ids_in_result)))
    }
    balances = {
        entitlement_id: int(balance or 0)
        for entitlement_id, balance in db.execute(
            select(
                VisitEntitlementLedgerEntry.entitlement_id,
                func.coalesce(func.sum(VisitEntitlementLedgerEntry.quantity), 0),
            )
            .where(VisitEntitlementLedgerEntry.entitlement_id.in_(entitlement_ids))
            .group_by(VisitEntitlementLedgerEntry.entitlement_id)
        )
    }
    assignments_by_occurrence: dict[int, list[ClientVisitAssignment]] = {}
    for assignment in assignment_rows:
        assignments_by_occurrence.setdefault(assignment.occurrence_id, []).append(assignment)
    result: list[PlannerOccurrenceRead] = []
    for row in rows:
        assignments = assignments_by_occurrence.get(row.id, [])
        if unassigned_only and assignments:
            continue
        client = clients.get(row.client_id)
        occurrence_values = OccurrenceRead.model_validate(row).model_dump()
        occurrence_values.update(
            client_code=client.code if client else None, client_name=client.name if client else None
        )
        assignment_values = []
        for item in assignments:
            values = VisitAssignmentRead.model_validate(item).model_dump()
            user = users.get(item.user_id)
            values.update(user_name=user.full_name if user else None)
            assignment_values.append(VisitAssignmentRead(**values))
        result.append(
            PlannerOccurrenceRead(
                **occurrence_values,
                assignments=assignment_values,
                entitlement_remaining=max(0, balances.get(row.entitlement_id, 0)),
            )
        )
    return result


@router.get("/summary-cards")
def visit_summary_cards(
    date_from: date,
    date_to: date,
    client_id: int | None = None,
    client_ids: str | None = None,
    include_subclients: bool = True,
    source_type: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("visit.entitlement.view")),
) -> dict[str, int]:
    client_scope: set[int] | None = None
    if client_id is not None:
        client_scope = {client_id}
        if include_subclients:
            pending = [client_id]
            while pending:
                children = list(
                    db.scalars(select(Client.id).where(Client.parent_client_id.in_(pending)))
                )
                new_children = [value for value in children if value not in client_scope]
                client_scope.update(new_children)
                pending = new_children
    elif client_ids:
        client_scope = {int(value) for value in client_ids.split(",") if value.strip().isdigit()}
    occurrence_statement = select(ClientVisitOccurrence).where(
        ClientVisitOccurrence.window_start <= date_to,
        ClientVisitOccurrence.window_end >= date_from,
        ClientVisitOccurrence.status.notin_(("CANCELLED", "SUPERSEDED")),
    )
    entitlement_statement = select(ClientVisitEntitlement).where(
        ClientVisitEntitlement.service_period_start <= date_to,
        ClientVisitEntitlement.service_period_end >= date_from,
        ClientVisitEntitlement.status == "ACTIVE",
    )
    if client_scope is not None:
        occurrence_statement = occurrence_statement.where(
            ClientVisitOccurrence.client_id.in_(client_scope)
        )
        entitlement_statement = entitlement_statement.where(
            ClientVisitEntitlement.client_id.in_(client_scope)
        )
    if source_type:
        occurrence_statement = occurrence_statement.where(
            ClientVisitOccurrence.source_type.in_(
                [value.strip() for value in source_type.split(",") if value.strip()]
            )
        )
    occurrences = list(db.scalars(occurrence_statement))
    entitlements = list(db.scalars(entitlement_statement))
    return {
        "visits": len(occurrences),
        "scheduled": sum(
            row.status in {"SCHEDULED", "RESCHEDULED", "IN_PROGRESS"} for row in occurrences
        ),
        "completed": sum(row.status == "COMPLETED" for row in occurrences),
        "pending": sum(
            row.status in {"PLANNED", "SCHEDULED", "RESCHEDULED", "IN_PROGRESS", "REOPENED"}
            for row in occurrences
        ),
        "entitled": sum(row.allowed_visits for row in entitlements),
        "remaining": sum(max(0, ledger_balance(db, row.id)) for row in entitlements),
    }


@router.get("/planner/workload", response_model=list[PlannerWorkloadRead])
def planner_workload(
    starts_before: datetime,
    ends_after: datetime,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("visit.entitlement.view")),
) -> list[PlannerWorkloadRead]:
    shifts = list(
        db.scalars(
            select(Shift).where(
                Shift.starts_at < starts_before,
                Shift.ends_at > ends_after,
                Shift.status != "CANCELLED",
            )
        )
    )
    assignments = list(
        db.scalars(
            select(ClientVisitAssignment).where(
                ClientVisitAssignment.starts_at < starts_before,
                ClientVisitAssignment.ends_at > ends_after,
                ClientVisitAssignment.status == "ASSIGNED",
            )
        )
    )
    result: list[PlannerWorkloadRead] = []
    for user_id in sorted({row.user_id for row in shifts} | {row.user_id for row in assignments}):
        user_shifts = [row for row in shifts if row.user_id == user_id]
        user_visits = [row for row in assignments if row.user_id == user_id]
        user = db.get(User, user_id)
        result.append(
            PlannerWorkloadRead(
                user_id=user_id,
                user_name=user.full_name if user else "Unknown engineer",
                shift_count=len(user_shifts),
                scheduled_shift_minutes=sum(
                    int((row.ends_at - row.starts_at).total_seconds() // 60) for row in user_shifts
                ),
                visit_count=len(user_visits),
                scheduled_visit_minutes=sum(
                    int((row.ends_at - row.starts_at).total_seconds() // 60) for row in user_visits
                ),
                conflict_count=sum(bool(row.conflict_codes) for row in user_visits),
            )
        )
    return result
