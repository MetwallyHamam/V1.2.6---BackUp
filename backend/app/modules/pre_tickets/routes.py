import hashlib
import json
from csv import writer
from datetime import date, datetime, time
from io import StringIO
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, require_permission
from app.core.clock import server_now, server_timezone
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import (
    Branch,
    Client,
    Contact,
    ContactClientLink,
    Product,
    ProductModule,
    ServiceCatalogItem,
)
from app.modules.configuration.policy_service import resolve_feature_policy
from app.modules.configuration.ticket_form import validate_required_pre_ticket_fields
from app.modules.iam.models import AuditLog, User
from app.modules.iam.service import effective_permissions
from app.modules.notifications.models import Notification
from app.modules.pre_tickets.models import EngineerPreTicket, PreTicketQueueView
from app.modules.pre_tickets.schemas import (
    PreTicketClaim,
    PreTicketConvert,
    PreTicketCreate,
    PreTicketMetricBucket,
    PreTicketMetricsRead,
    PreTicketQueueViewCreate,
    PreTicketQueueViewRead,
    PreTicketRead,
    PreTicketReasonAction,
    PreTicketResponse,
)
from app.modules.tickets.models import TicketType
from app.modules.tickets.schemas import TicketCreate
from app.modules.tickets.service import create_ticket

router = APIRouter(prefix="/pre-tickets", tags=["engineer pre-tickets"])


def _daily_pre_ticket_filters(statement: Select[tuple[EngineerPreTicket]], unconverted_only: bool, submitted_from: date | None, submitted_to: date | None, timezone_offset_minutes: int = 180) -> Select[tuple[EngineerPreTicket]]:
    if unconverted_only:
        statement = statement.where(EngineerPreTicket.resulting_ticket_id.is_(None))
    if submitted_from:
        statement = statement.where(EngineerPreTicket.submitted_at >= datetime.combine(submitted_from, time.min, tzinfo=server_timezone()))
    if submitted_to:
        statement = statement.where(EngineerPreTicket.submitted_at <= datetime.combine(submitted_to, time.max, tzinfo=server_timezone()))
    return statement


def _feature_enabled(db: Session) -> dict[str, object]:
    policy = resolve_feature_policy(db, "engineer_pre_ticket")
    if policy.mode != "ENFORCED":
        raise ConflictError("PRE_TICKET_DISABLED", "Engineer Pre-Tickets are not enabled.")
    return policy.configuration


def _audit(db: Session, actor: User, item: EngineerPreTicket, action: str, values: dict[str, object] | None = None) -> None:
    db.add(AuditLog(actor_user_id=actor.id, entity_type="EngineerPreTicket", entity_id=str(item.id), action=action, new_values_json=json.dumps(values or {}, default=str)))


def _notify(db: Session, item: EngineerPreTicket, recipients: list[User], event: str, message: str) -> None:
    """Create deduplicated in-app notifications only for authorized internal recipients."""
    for recipient in recipients:
        if recipient.is_active and recipient.user_type == "EMPLOYEE":
            db.add(Notification(recipient_user_id=recipient.id, notification_type="PRE_TICKET", severity="INFO", title=f"Pre-Ticket {item.pre_ticket_number}: {event}", message=message, deep_link="/tickets/pre-tickets", deduplication_key=f"pre-ticket:{item.id}:{event}:v{item.version}:user:{recipient.id}"))


def _queue_processors(db: Session) -> list[User]:
    return [user for user in db.scalars(select(User).where(User.is_active.in_([True]), User.user_type == "EMPLOYEE")) if "ticket.pre_ticket.queue.process" in set(effective_permissions(db, user).permissions)]


def _readable(db: Session, actor: User, item: EngineerPreTicket) -> None:
    permissions = set(effective_permissions(db, actor).permissions)
    if item.submitted_by_user_id == actor.id and "ticket.pre_ticket.view.own" in permissions:
        return
    if "ticket.pre_ticket.queue.view" in permissions:
        return
    raise AuthorizationError()


def _normalize_title(value: str) -> str:
    normalized = " ".join(value.split())
    if len(normalized) < 10:
        raise ConflictError("PRE_TICKET_TITLE_INVALID", "Title must contain at least 10 characters.")
    return normalized


@router.post("", response_model=PreTicketRead, status_code=status.HTTP_201_CREATED)
def submit_pre_ticket(data: PreTicketCreate, db: Session = Depends(get_db), actor: User = Depends(require_permission("ticket.pre_ticket.create"))) -> EngineerPreTicket:
    _feature_enabled(db)
    validate_required_pre_ticket_fields(db, data)
    if actor.user_type != "EMPLOYEE":
        raise AuthorizationError()
    title = _normalize_title(data.title)
    fingerprint = hashlib.sha256(json.dumps({**data.model_dump(exclude={"idempotency_key"}), "title": title}, sort_keys=True).encode()).hexdigest()
    previous = db.scalar(select(EngineerPreTicket).where(EngineerPreTicket.submitted_by_user_id == actor.id, EngineerPreTicket.idempotency_key == data.idempotency_key))
    if previous:
        if previous.request_fingerprint == fingerprint:
            return previous
        raise ConflictError("PRE_TICKET_IDEMPOTENCY_CONFLICT", "This submission key was already used with different data.")
    client = db.get(Client, data.client_id) if data.client_id else None
    contact = db.get(Contact, data.requester_contact_id) if data.requester_contact_id else None
    product = db.get(Product, data.product_id) if data.product_id else None
    module = db.get(ProductModule, data.product_module_id) if data.product_module_id else None
    service = db.get(ServiceCatalogItem, data.service_id) if data.service_id else None
    linked = contact and data.client_id and db.scalar(select(ContactClientLink.id).where(ContactClientLink.contact_id == contact.id, ContactClientLink.client_id == data.client_id))
    if data.client_id and (not client or not client.is_active):
        raise NotFoundError("Client does not exist or is inactive.")
    if contact and (not data.client_id or (contact.client_id != data.client_id and not linked)):
        raise ConflictError("INVALID_REQUESTER", "The requester does not belong to the client.")
    if data.product_id and (not product or not product.is_active):
        raise NotFoundError("Product does not exist or is inactive.")
    if data.product_module_id and (not module or not module.is_active or module.product_id != data.product_id):
        raise ConflictError("INVALID_PRODUCT_MODULE", "The selected Module does not belong to the Product.")
    if data.service_id and (not service or not service.is_active):
        raise NotFoundError("Service does not exist or is inactive.")
    if module and service and module not in service.modules:
        raise ConflictError("INVALID_SERVICE_MODULE", "The selected Service is not linked to the Module.")
    # SQL Server unique constraints permit only one NULL.  Insert a temporary
    # unique value, then replace it with the durable ID-derived reference below.
    item = EngineerPreTicket(pre_ticket_number=f"PENDING-{uuid4().hex}", client_id=data.client_id, requester_contact_id=data.requester_contact_id, product_id=data.product_id, product_module_id=data.product_module_id, service_id=data.service_id, proposed_priority=data.proposed_priority, title=title, initial_description=title, submitted_by_user_id=actor.id, idempotency_key=data.idempotency_key, request_fingerprint=fingerprint)
    db.add(item); db.flush()
    item.pre_ticket_number = f"PRE-{item.id:06d}"
    _audit(db, actor, item, "pre_ticket.submitted", {"status": item.status})
    _notify(db, item, _queue_processors(db), "submitted", f"New Pre-Ticket submitted: {item.title}")
    db.commit(); db.refresh(item)
    return item


@router.get("/mine", response_model=list[PreTicketRead])
def my_pre_tickets(response: Response, db: Session = Depends(get_db), actor: User = Depends(require_permission("ticket.pre_ticket.view.own")), unconverted_only: bool = False, submitted_from: date | None = None, submitted_to: date | None = None, sort_direction: str = Query("desc", pattern="^(asc|desc)$"), limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)) -> list[EngineerPreTicket]:
    statement = select(EngineerPreTicket).where(EngineerPreTicket.submitted_by_user_id == actor.id)
    statement = _daily_pre_ticket_filters(statement, unconverted_only, submitted_from, submitted_to)
    response.headers["X-Total-Count"] = str(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    ordering = EngineerPreTicket.submitted_at.asc() if sort_direction == "asc" else EngineerPreTicket.submitted_at.desc()
    return list(db.scalars(statement.order_by(ordering).offset(offset).limit(limit)))


@router.get("/queue", response_model=list[PreTicketRead])
def queue_pre_tickets(response: Response, db: Session = Depends(get_db), _: User = Depends(require_permission("ticket.pre_ticket.queue.view")), status_filter: str | None = Query(None, alias="status"), search: str | None = Query(None, min_length=1, max_length=100), unconverted_only: bool = False, submitted_from: date | None = None, submitted_to: date | None = None, sort_direction: str = Query("asc", pattern="^(asc|desc)$"), limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)) -> list[EngineerPreTicket]:
    statement = select(EngineerPreTicket)
    statement = _daily_pre_ticket_filters(statement, unconverted_only, submitted_from, submitted_to)
    if status_filter:
        statement = statement.where(EngineerPreTicket.status == status_filter.upper())
    if search:
        pattern = f"%{search.strip().lower()}%"
        statement = statement.where(or_(func.lower(EngineerPreTicket.pre_ticket_number).like(pattern), func.lower(EngineerPreTicket.title).like(pattern), func.lower(EngineerPreTicket.status).like(pattern)))
    response.headers["X-Total-Count"] = str(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    ordering = EngineerPreTicket.submitted_at.asc() if sort_direction == "asc" else EngineerPreTicket.submitted_at.desc()
    return list(db.scalars(statement.order_by(ordering).offset(offset).limit(limit)))


@router.get("/queue/export")
def export_queue_pre_tickets(db: Session = Depends(get_db), _: User = Depends(require_permission("ticket.pre_ticket.report")), status_filter: str | None = Query(None, alias="status"), search: str | None = Query(None, min_length=1, max_length=100)) -> StreamingResponse:
    statement = select(EngineerPreTicket)
    if status_filter:
        statement = statement.where(EngineerPreTicket.status == status_filter.upper())
    if search:
        pattern = f"%{search.strip().lower()}%"
        statement = statement.where(or_(func.lower(EngineerPreTicket.pre_ticket_number).like(pattern), func.lower(EngineerPreTicket.title).like(pattern), func.lower(EngineerPreTicket.status).like(pattern)))
    output = StringIO(newline="")
    csv_writer = writer(output)
    csv_writer.writerow(["Pre-Ticket number", "Title", "Proposed priority", "Status", "Submitted at"])
    for item in db.scalars(statement.order_by(EngineerPreTicket.submitted_at)):
        csv_writer.writerow([item.pre_ticket_number, item.title, item.proposed_priority, item.status, item.submitted_at.isoformat()])
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="pre-ticket-queue.csv"'})


@router.get("/queue/views", response_model=list[PreTicketQueueViewRead])
def queue_views(db: Session = Depends(get_db), actor: User = Depends(require_permission("ticket.pre_ticket.queue.view"))) -> list[PreTicketQueueView]:
    return list(db.scalars(select(PreTicketQueueView).where(PreTicketQueueView.owner_user_id == actor.id).order_by(PreTicketQueueView.name)))


@router.post("/queue/views", response_model=PreTicketQueueViewRead, status_code=status.HTTP_201_CREATED)
def create_queue_view(data: PreTicketQueueViewCreate, db: Session = Depends(get_db), actor: User = Depends(require_permission("ticket.pre_ticket.queue.view"))) -> PreTicketQueueView:
    item = PreTicketQueueView(owner_user_id=actor.id, name=data.name.strip(), search_text=data.search_text.strip() if data.search_text else None, status_filter=data.status_filter.upper() if data.status_filter else None)
    db.add(item)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise ConflictError("PRE_TICKET_QUEUE_VIEW_EXISTS", "A queue view with this name already exists.") from None
    db.refresh(item)
    return item


@router.delete("/queue/views/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_queue_view(view_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("ticket.pre_ticket.queue.view"))) -> Response:
    item = db.get(PreTicketQueueView, view_id)
    if not item or item.owner_user_id != actor.id:
        raise NotFoundError("Queue view does not exist.")
    db.delete(item); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{pre_ticket_id}", response_model=PreTicketRead)
def get_pre_ticket(pre_ticket_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> EngineerPreTicket:
    item = db.get(EngineerPreTicket, pre_ticket_id)
    if not item:
        raise NotFoundError("Pre-Ticket does not exist.")
    _readable(db, actor, item)
    return item


@router.post("/{pre_ticket_id}/claim", response_model=PreTicketRead)
def claim_pre_ticket(pre_ticket_id: int, data: PreTicketClaim, db: Session = Depends(get_db), actor: User = Depends(require_permission("ticket.pre_ticket.queue.process"))) -> EngineerPreTicket:
    _feature_enabled(db)
    item = db.get(EngineerPreTicket, pre_ticket_id)
    if not item:
        raise NotFoundError("Pre-Ticket does not exist.")
    if item.status != "SUBMITTED" or item.version != data.expected_version:
        raise ConflictError("PRE_TICKET_CONFLICT", "The Pre-Ticket has changed. Refresh and try again.")
    item.status, item.claimed_by_user_id, item.claimed_at, item.version = "CLAIMED", actor.id, server_now(), item.version + 1
    _audit(db, actor, item, "pre_ticket.claimed")
    submitter = db.get(User, item.submitted_by_user_id)
    _notify(db, item, [submitter] if submitter else [], "claimed", f"Your Pre-Ticket was claimed by {actor.full_name}.")
    db.commit(); db.refresh(item)
    return item


def _processor_owned(item: EngineerPreTicket, actor: User) -> bool:
    return item.status == "CLAIMED" and item.claimed_by_user_id == actor.id


@router.post("/{pre_ticket_id}/needs-information", response_model=PreTicketRead)
def request_information(pre_ticket_id: int, data: PreTicketReasonAction, db: Session = Depends(get_db), actor: User = Depends(require_permission("ticket.pre_ticket.queue.process"))) -> EngineerPreTicket:
    _feature_enabled(db)
    item = db.get(EngineerPreTicket, pre_ticket_id)
    if not item:
        raise NotFoundError("Pre-Ticket does not exist.")
    if not _processor_owned(item, actor) or item.version != data.expected_version:
        raise ConflictError("PRE_TICKET_CONFLICT", "Only the claim owner can request information from the current Pre-Ticket.")
    item.status, item.information_request, item.engineer_response, item.version = "NEEDS_INFORMATION", data.reason.strip(), None, item.version + 1
    _audit(db, actor, item, "pre_ticket.information_requested", {"message": item.information_request})
    submitter = db.get(User, item.submitted_by_user_id)
    _notify(db, item, [submitter] if submitter else [], "information-requested", item.information_request)
    db.commit(); db.refresh(item)
    return item


@router.post("/{pre_ticket_id}/respond", response_model=PreTicketRead)
def respond_to_information_request(pre_ticket_id: int, data: PreTicketResponse, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> EngineerPreTicket:
    _feature_enabled(db)
    item = db.get(EngineerPreTicket, pre_ticket_id)
    if not item:
        raise NotFoundError("Pre-Ticket does not exist.")
    if item.submitted_by_user_id != actor.id or item.status != "NEEDS_INFORMATION" or item.version != data.expected_version:
        raise ConflictError("PRE_TICKET_CONFLICT", "Only the submitting engineer can respond to the current information request.")
    item.status, item.engineer_response, item.claimed_by_user_id, item.claimed_at, item.version = "SUBMITTED", data.response.strip(), None, None, item.version + 1
    _audit(db, actor, item, "pre_ticket.responded", {"message": item.engineer_response})
    _notify(db, item, _queue_processors(db), "responded", f"The submitting engineer responded: {item.title}")
    db.commit(); db.refresh(item)
    return item


@router.post("/{pre_ticket_id}/reject", response_model=PreTicketRead)
def reject_pre_ticket(pre_ticket_id: int, data: PreTicketReasonAction, db: Session = Depends(get_db), actor: User = Depends(require_permission("ticket.pre_ticket.queue.process"))) -> EngineerPreTicket:
    _feature_enabled(db)
    item = db.get(EngineerPreTicket, pre_ticket_id)
    if not item:
        raise NotFoundError("Pre-Ticket does not exist.")
    if item.status not in {"SUBMITTED", "CLAIMED"} or item.version != data.expected_version or (item.status == "CLAIMED" and item.claimed_by_user_id != actor.id):
        raise ConflictError("PRE_TICKET_CONFLICT", "The Pre-Ticket cannot be rejected in its current state.")
    item.status, item.terminal_reason, item.version = "REJECTED", data.reason.strip(), item.version + 1
    _audit(db, actor, item, "pre_ticket.rejected", {"reason": item.terminal_reason})
    submitter = db.get(User, item.submitted_by_user_id)
    _notify(db, item, [submitter] if submitter else [], "rejected", item.terminal_reason)
    db.commit(); db.refresh(item)
    return item


@router.post("/{pre_ticket_id}/cancel", response_model=PreTicketRead)
def cancel_pre_ticket(pre_ticket_id: int, data: PreTicketReasonAction, db: Session = Depends(get_db), actor: User = Depends(require_permission("ticket.pre_ticket.queue.process"))) -> EngineerPreTicket:
    _feature_enabled(db)
    item = db.get(EngineerPreTicket, pre_ticket_id)
    if not item:
        raise NotFoundError("Pre-Ticket does not exist.")
    if item.status not in {"SUBMITTED", "CLAIMED", "NEEDS_INFORMATION"} or item.version != data.expected_version or (item.status == "CLAIMED" and item.claimed_by_user_id != actor.id):
        raise ConflictError("PRE_TICKET_CONFLICT", "The Pre-Ticket cannot be cancelled in its current state.")
    item.status, item.terminal_reason, item.version = "CANCELLED", data.reason.strip(), item.version + 1
    _audit(db, actor, item, "pre_ticket.cancelled", {"reason": item.terminal_reason})
    submitter = db.get(User, item.submitted_by_user_id)
    _notify(db, item, [submitter] if submitter else [], "cancelled", item.terminal_reason)
    db.commit(); db.refresh(item)
    return item


def _complete_conversion_context(db: Session, item: EngineerPreTicket, data: PreTicketConvert) -> dict[str, int | None]:
    values = {
        "client_id": data.client_id if item.client_id is None else item.client_id,
        "branch_id": data.branch_id if item.branch_id is None else item.branch_id,
        "requester_contact_id": data.requester_contact_id if item.requester_contact_id is None else item.requester_contact_id,
        "product_id": data.product_id if item.product_id is None else item.product_id,
        "product_module_id": data.product_module_id if item.product_module_id is None else item.product_module_id,
        "service_id": data.service_id if item.service_id is None else item.service_id,
    }
    for key in values:
        supplied = getattr(data, key)
        current = getattr(item, key)
        if current is not None and supplied is not None and supplied != current:
            raise ConflictError("PRE_TICKET_CONTEXT_IMMUTABLE", f"{key} is already recorded and cannot be replaced during conversion.")
    client = db.get(Client, values["client_id"]) if values["client_id"] else None
    branch = db.get(Branch, values["branch_id"]) if values["branch_id"] else None
    contact = db.get(Contact, values["requester_contact_id"]) if values["requester_contact_id"] else None
    product = db.get(Product, values["product_id"]) if values["product_id"] else None
    module = db.get(ProductModule, values["product_module_id"]) if values["product_module_id"] else None
    service = db.get(ServiceCatalogItem, values["service_id"]) if values["service_id"] else None
    linked = contact and client and db.scalar(select(ContactClientLink.id).where(ContactClientLink.contact_id == contact.id, ContactClientLink.client_id == client.id))
    if not client or not client.is_active:
        raise ConflictError("PRE_TICKET_CONTEXT_INCOMPLETE", "Select an active Client before converting the Pre-Ticket.")
    if branch and (not branch.is_active or branch.client_id != client.id):
        raise ConflictError("INVALID_BRANCH", "The selected Branch does not belong to the Client.")
    if contact and contact.client_id != client.id and not linked:
        raise ConflictError("INVALID_REQUESTER", "The requester does not belong to the client.")
    if values["product_id"] and (not product or not product.is_active):
        raise NotFoundError("Product does not exist or is inactive.")
    if values["product_module_id"] and (not module or not module.is_active or module.product_id != values["product_id"]):
        raise ConflictError("INVALID_PRODUCT_MODULE", "The selected Module does not belong to the Product.")
    if values["service_id"] and (not service or not service.is_active):
        raise NotFoundError("Service does not exist or is inactive.")
    if module and service and module not in service.modules:
        raise ConflictError("INVALID_SERVICE_MODULE", "The selected Service is not linked to the Module.")
    return values


def _profile_ticket_data(db: Session, item: EngineerPreTicket, data: PreTicketConvert, assigned_user_id: int) -> TicketCreate:
    configuration = _feature_enabled(db)
    profile = configuration.get("fast_create_profile") if isinstance(configuration.get("fast_create_profile"), dict) else configuration
    mapping = profile.get("priority_mapping") if isinstance(profile, dict) else None
    ticket_type_id = profile.get("ticket_type_id") if isinstance(profile, dict) else None
    mapped = mapping.get(item.proposed_priority) if isinstance(mapping, dict) else None
    if not isinstance(ticket_type_id, int) or not isinstance(mapped, dict) or mapped.get("impact") not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"} or mapped.get("urgency") not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        raise ConflictError("PRE_TICKET_PROFILE_INCOMPLETE", "The Fast Create profile is incomplete.")
    requested_ticket_type = None
    if item.requested_ticket_type_code:
        requested_ticket_type = db.scalar(
            select(TicketType).where(
                func.upper(TicketType.code) == item.requested_ticket_type_code.upper(),
                TicketType.is_active.in_([True]),
            )
        )
    if requested_ticket_type:
        ticket_type_id = requested_ticket_type.id
    ticket_type = db.get(TicketType, ticket_type_id)
    if not ticket_type or not ticket_type.is_active:
        raise ConflictError("PRE_TICKET_PROFILE_INVALID", "The Fast Create Ticket Type is inactive or missing.")
    context = _complete_conversion_context(db, item, data)
    return TicketCreate(ticket_type_id=ticket_type_id, client_id=context["client_id"], branch_id=context["branch_id"], requester_contact_id=context["requester_contact_id"], product_id=context["product_id"], product_module_id=context["product_module_id"], service_id=context["service_id"], assigned_user_id=assigned_user_id, source_channel="ENGINEER_PRE_TICKET", impact=mapped["impact"], urgency=mapped["urgency"], subject=item.title, description=item.initial_description, request_entitlement_approval=True, entitlement_approval_justification=f"Uncovered Pre-Ticket {item.pre_ticket_number} requires contract entitlement approval before work begins.", submission_idempotency_key=f"pre-ticket-approval:{item.id}:{data.conversion_idempotency_key}", creation_idempotency_key=f"pre-ticket:{item.id}:{data.conversion_idempotency_key}")


@router.post("/{pre_ticket_id}/convert", response_model=PreTicketRead)
def convert_and_assign_to_creator(pre_ticket_id: int, data: PreTicketConvert, db: Session = Depends(get_db), actor: User = Depends(require_permission("ticket.pre_ticket.convert_assign"))) -> EngineerPreTicket:
    item = db.get(EngineerPreTicket, pre_ticket_id)
    if not item:
        raise NotFoundError("Pre-Ticket does not exist.")
    if item.status == "CONVERTED":
        return item
    if item.version != data.expected_version or item.status not in {"SUBMITTED", "CLAIMED"} or (item.status == "CLAIMED" and item.claimed_by_user_id != actor.id):
        raise ConflictError("PRE_TICKET_CONFLICT", "The Pre-Ticket has changed or is owned by another processor.")
    creator = db.get(User, item.submitted_by_user_id)
    if not creator or not creator.is_active:
        raise ConflictError("PRE_TICKET_CREATOR_UNAVAILABLE", "The Pre-Ticket creator is not available for assignment.")
    assignee = creator if creator.user_type == "EMPLOYEE" else actor
    ticket_data = _profile_ticket_data(db, item, data, assignee.id)
    completed_context = {key: getattr(ticket_data, key) for key in ("client_id", "branch_id", "requester_contact_id", "product_id", "product_module_id", "service_id") if getattr(item, key) is None and getattr(ticket_data, key) is not None}
    ticket = create_ticket(db, ticket_data, actor, allow_controlled_assignment=True)
    for key, value in completed_context.items():
        setattr(item, key, value)
    item.status, item.claimed_by_user_id, item.claimed_at = "CONVERTED", actor.id, item.claimed_at or server_now()
    item.converted_by_user_id, item.converted_at, item.resulting_ticket_id, item.conversion_mode, item.version = actor.id, server_now(), ticket.id, "CALL_CENTER", item.version + 1
    _audit(db, actor, item, "pre_ticket.converted", {"ticket_id": ticket.id, "assigned_user_id": assignee.id, "completed_context": completed_context})
    conversion_message = (
        f"Ticket {ticket.ticket_number} was created and is awaiting contract entitlement approval."
        if ticket.entitlement_status == "PENDING_APPROVAL"
        else f"Ticket {ticket.ticket_number} was created and assigned to you."
    )
    _notify(db, item, [assignee], "converted", conversion_message)
    db.commit(); db.refresh(item)
    return item


@router.post("/{pre_ticket_id}/confirm", response_model=PreTicketRead)
def confirm_and_create_ticket(pre_ticket_id: int, data: PreTicketConvert, db: Session = Depends(get_db), actor: User = Depends(require_permission("ticket.pre_ticket.fast_convert.self"))) -> EngineerPreTicket:
    """Create one official ticket for the submitting engineer using the governed profile."""
    item = db.get(EngineerPreTicket, pre_ticket_id)
    if not item:
        raise NotFoundError("Pre-Ticket does not exist.")
    if item.status == "CONVERTED" and item.submitted_by_user_id == actor.id:
        return item
    if any(getattr(data, key) is not None for key in ("client_id", "requester_contact_id", "product_id", "product_module_id", "service_id")):
        raise ConflictError("PRE_TICKET_CONTEXT_SELF_EDIT_FORBIDDEN", "Only Call Center can complete missing context during conversion.")
    permissions = set(effective_permissions(db, actor).permissions)
    if {"ticket.create", "ticket.assign.self"}.difference(permissions):
        raise AuthorizationError(details={"required_permissions": ["ticket.create", "ticket.assign.self"]})
    if item.submitted_by_user_id != actor.id or item.status != "SUBMITTED" or item.version != data.expected_version:
        raise ConflictError("PRE_TICKET_CONFLICT", "Only your unclaimed current Pre-Ticket can be confirmed.")
    ticket = create_ticket(db, _profile_ticket_data(db, item, data, actor.id), actor, allow_controlled_assignment=True)
    item.status = "CONVERTED"
    item.converted_by_user_id = actor.id
    item.converted_at = server_now()
    item.resulting_ticket_id = ticket.id
    item.conversion_mode = "SELF_SERVICE"
    item.version += 1
    _audit(db, actor, item, "pre_ticket.confirmed", {"ticket_id": ticket.id, "assigned_user_id": actor.id})
    db.commit(); db.refresh(item)
    return item


@router.get("/metrics/summary", response_model=PreTicketMetricsRead)
def pre_ticket_metrics(db: Session = Depends(get_db), _: User = Depends(require_permission("ticket.pre_ticket.report"))) -> PreTicketMetricsRead:
    items = list(db.scalars(select(EngineerPreTicket)))
    by_status: dict[str, int] = {}
    claim_minutes: list[float] = []
    claim_to_ticket_minutes: list[float] = []
    ticket_minutes: list[float] = []
    now = server_now()
    clients = {item.id: item.name for item in db.scalars(select(Client))}
    products = {item.id: item.name for item in db.scalars(select(Product))}
    submitters = {item.id: item for item in db.scalars(select(User))}

    def minutes_between(start: datetime, end: datetime) -> float:
        if start.tzinfo is None:
            start = start.replace(tzinfo=server_timezone())
        if end.tzinfo is None:
            end = end.replace(tzinfo=server_timezone())
        return max(0.0, (end - start).total_seconds() / 60)

    def bucket(dimension: str) -> list[PreTicketMetricBucket]:
        grouped: dict[tuple[str, str], list[float]] = {}
        for item in items:
            if dimension == "client":
                key, label = str(item.client_id or "UNSPECIFIED"), clients.get(item.client_id, "Unspecified client") if item.client_id else "Unspecified client"
            elif dimension == "product":
                key, label = str(item.product_id or "UNSPECIFIED"), products.get(item.product_id, "Unspecified product") if item.product_id else "Unspecified product"
            elif dimension == "priority":
                key = label = item.proposed_priority
            elif dimension == "team":
                submitter = submitters.get(item.submitted_by_user_id)
                label = (submitter.department if submitter else None) or "Unspecified team"
                key = label
            else:
                key = label = item.status
            terminal_at = item.converted_at or (item.updated_at if item.status in {"REJECTED", "CANCELLED"} else None)
            grouped.setdefault((key, label), []).append(minutes_between(item.submitted_at, terminal_at or now))
        return [PreTicketMetricBucket(key=key, label=label, count=len(ages), average_age_minutes=round(sum(ages) / len(ages), 2)) for (key, label), ages in sorted(grouped.items(), key=lambda value: value[0][1].lower())]

    for item in items:
        by_status[item.status] = by_status.get(item.status, 0) + 1
        if item.claimed_at:
            claim_minutes.append(minutes_between(item.submitted_at, item.claimed_at))
        if item.converted_at:
            ticket_minutes.append(minutes_between(item.submitted_at, item.converted_at))
            if item.claimed_at:
                claim_to_ticket_minutes.append(minutes_between(item.claimed_at, item.converted_at))
    return PreTicketMetricsRead(total=len(items), by_status=by_status, average_minutes_to_claim=round(sum(claim_minutes) / len(claim_minutes), 2) if claim_minutes else None, average_minutes_claim_to_ticket=round(sum(claim_to_ticket_minutes) / len(claim_to_ticket_minutes), 2) if claim_to_ticket_minutes else None, average_minutes_to_ticket=round(sum(ticket_minutes) / len(ticket_minutes), 2) if ticket_minutes else None, by_client=bucket("client"), by_product=bucket("product"), by_priority=bucket("priority"), by_submitting_team=bucket("team"), aging_by_status=bucket("status"))
