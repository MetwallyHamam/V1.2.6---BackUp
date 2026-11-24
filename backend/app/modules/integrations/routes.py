import base64
import hashlib
import hmac
import json
import secrets

from fastapi import APIRouter, Body, Depends, Header, Request, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
)
from app.db.session import get_db
from app.modules.clients.models import Client, Contact
from app.modules.configuration.models import SiteSetting
from app.modules.contracts.models import TicketSlaClock, TicketSlaInterval
from app.modules.iam.models import AuditLog, User
from app.modules.iam.security import hash_password, verify_password
from app.modules.iam.service import effective_permissions, normalize
from app.modules.integrations.models import (
    IntegrationApiClient,
    IntegrationDelivery,
    LegacyTicketMap,
)
from app.modules.integrations.schemas import (
    ApiClientCreate,
    ApiClientCreated,
    ApiClientRead,
    ApiTicketCreate,
    ApiTicketResult,
    ApiTicketStatusResult,
    ApiTicketStatusUpdate,
    InboundClientResult,
    InboundEmailEvent,
    InboundEmailResult,
    InboundPreTicketResult,
    InboundPreTicketSettings,
    InboundPreTicketSettingsUpdate,
    InboundRequestStatus,
    InboundVendorProfile,
    ItopImportBatch,
    ItopImportItemResult,
    ItopImportResult,
    MonitoringEvent,
    MonitoringResult,
)
from app.modules.notifications.models import Notification
from app.modules.pre_tickets.models import EngineerPreTicket
from app.modules.tickets.models import (
    Ticket,
    TicketComment,
    TicketFlag,
    TicketFlagAssignment,
    TicketStatus,
    TicketType,
)
from app.modules.tickets.schemas import TicketCreate, TicketTransition
from app.modules.tickets.service import create_ticket, transition_ticket

router = APIRouter(prefix="/integrations", tags=["integrations"])
INBOUND_SETTINGS_KEY = "inbound_pre_ticket_configuration"
INBOUND_SETTINGS_VERSION_KEY = "_inbound_pre_ticket_configuration_version"


def _key_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _api_client(db: Session, api_key: str) -> IntegrationApiClient:
    if not api_key.startswith("msh_") or len(api_key) < 20:
        raise AuthenticationError("INVALID_API_KEY", "Invalid API key.")
    prefix = api_key[:16]
    client = db.scalar(
        select(IntegrationApiClient).where(
            IntegrationApiClient.key_prefix == prefix,
            IntegrationApiClient.is_active.in_([True]),
        )
    )
    if not client or not hmac.compare_digest(client.key_hash, _key_hash(api_key)):
        raise AuthenticationError("INVALID_API_KEY", "Invalid API key.")
    return client


def _vendor_client(db: Session, api_key: str, authorization: str) -> IntegrationApiClient:
    if api_key:
        return _api_client(db, api_key)
    if not authorization.startswith("Basic "):
        raise AuthenticationError(
            "INVALID_API_CREDENTIALS", "API key or Basic credentials are required."
        )
    try:
        decoded = base64.b64decode(authorization[6:], validate=True).decode("utf-8")
        username, password = decoded.split(":", 1)
    except (ValueError, UnicodeDecodeError):
        raise AuthenticationError("INVALID_API_CREDENTIALS", "Invalid Basic credentials.") from None
    client = db.scalar(
        select(IntegrationApiClient).where(
            func.lower(IntegrationApiClient.api_username) == username.strip().lower(),
            IntegrationApiClient.auth_type == "BASIC",
            IntegrationApiClient.is_active.in_([True]),
        )
    )
    if (
        not client
        or not client.password_hash
        or not verify_password(password, client.password_hash)
    ):
        raise AuthenticationError("INVALID_API_CREDENTIALS", "Invalid Basic credentials.")
    return client


def _integration_actor(db: Session, settings: Settings) -> User:
    actor = db.scalar(
        select(User).where(
            User.username_normalized == normalize(settings.integration_actor_username),
            User.is_active.in_([True]),
        )
    )
    if not actor:
        raise NotFoundError("The configured integration actor is unavailable.")
    return actor


def _inbound_settings(db: Session) -> InboundPreTicketSettings:
    row = db.get(SiteSetting, INBOUND_SETTINGS_KEY)
    return (
        InboundPreTicketSettings.model_validate_json(row.value)
        if row
        else InboundPreTicketSettings()
    )


def _inbound_version(db: Session) -> int:
    row = db.get(SiteSetting, INBOUND_SETTINGS_VERSION_KEY)
    return max(1, int(row.value)) if row else 1


def _inbound_profile(db: Session, integration_key: str) -> InboundVendorProfile:
    profile = next(
        (
            item
            for item in _inbound_settings(db).profiles
            if item.provider_key == integration_key.lower()
        ),
        None,
    )
    if not profile or not profile.enabled:
        raise NotFoundError("Inbound integration is unavailable.")
    return profile


def _mapped(payload: dict[str, object], path: str) -> object | None:
    value: object = payload
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


@router.get("/inbound-pre-ticket/settings")
def get_inbound_pre_ticket_settings(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("configuration.manage")),
) -> dict[str, object]:
    return {"version": _inbound_version(db), "values": _inbound_settings(db).model_dump()}


@router.put("/inbound-pre-ticket/settings")
def update_inbound_pre_ticket_settings(
    data: InboundPreTicketSettingsUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> dict[str, object]:
    current = _inbound_version(db)
    if data.expected_version != current:
        raise ConflictError(
            "INBOUND_SETTINGS_VERSION_CONFLICT",
            "Inbound integration settings changed. Reload and try again.",
        )
    values = InboundPreTicketSettings.model_validate(data.model_dump(exclude={"expected_version"}))
    row = db.get(SiteSetting, INBOUND_SETTINGS_KEY)
    encoded = values.model_dump_json()
    if row:
        row.value = encoded
    else:
        db.add(SiteSetting(key=INBOUND_SETTINGS_KEY, value=encoded))
    version_row = db.get(SiteSetting, INBOUND_SETTINGS_VERSION_KEY)
    if version_row:
        version_row.value = str(current + 1)
    else:
        db.add(SiteSetting(key=INBOUND_SETTINGS_VERSION_KEY, value=str(current + 1)))
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="SiteSetting",
            entity_id=INBOUND_SETTINGS_KEY,
            action="integration.inbound_pre_ticket.updated",
        )
    )
    db.commit()
    return {"version": current + 1, "values": values.model_dump()}


@router.post(
    "/inbound/{integration_key}/requests",
    response_model=InboundPreTicketResult,
    status_code=201,
    include_in_schema=False,
)
@router.post(
    "/inbound/v1/{integration_key}/requests", response_model=InboundPreTicketResult, status_code=201
)
def receive_inbound_pre_ticket(
    integration_key: str,
    request: Request,
    payload: dict[str, object] = Body(...),
    x_api_key: str = Header(default=""),
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
    app_settings: Settings = Depends(get_settings),
) -> InboundPreTicketResult:
    api_client = _vendor_client(db, x_api_key, authorization)
    configuration = _inbound_profile(db, integration_key)
    if api_client.provider_key and api_client.provider_key != configuration.provider_key:
        raise AuthorizationError("This API credential belongs to another vendor profile.")
    values = {
        key: _mapped(payload, field.path)
        for key, field in configuration.fields.items()
        if field.enabled
    }
    missing = {
        key: f"{key.replace('_', ' ').title()} is required for {configuration.name}."
        for key, field in configuration.fields.items()
        if field.enabled and field.required and not str(values.get(key) or "").strip()
    }
    if missing:
        raise ConflictError(
            "REQUIRED_FIELDS_MISSING",
            "Required request information is missing.",
            {"fields": missing, "provider": configuration.provider_key},
        )
    event_id = str(values.get("event_id") or "").strip()
    raw_type = str(values.get("request_type") or "").strip().upper()
    request_type = configuration.request_type_mapping.get(raw_type, "")
    if not event_id or len(event_id) > 150:
        raise ConflictError(
            "INBOUND_EVENT_ID_INVALID",
            "A valid external event ID is required.",
            {"fields": {"event_id": "Missing, empty, or longer than 150 characters."}},
        )
    if request_type not in {"CREATE_TICKET", "REQUEST_CALL"}:
        raise ConflictError(
            "INBOUND_REQUEST_TYPE_INVALID",
            "The request type is not configured.",
            {"fields": {"request_type": "Use one of the configured request values."}},
        )
    provider = f"INBOUND_{configuration.provider_key.upper()}_{api_client.id}"
    existing = db.scalar(
        select(IntegrationDelivery).where(
            IntegrationDelivery.provider == provider, IntegrationDelivery.event_id == event_id
        )
    )
    if existing:
        if existing.ticket_id:
            ticket = db.get(Ticket, existing.ticket_id)
            if not ticket:
                raise ConflictError(
                    "INTEGRATION_EVENT_INCOMPLETE", "The prior event did not complete."
                )
            return InboundPreTicketResult(
                event_id=event_id,
                ticket_id=ticket.id,
                ticket_number=ticket.ticket_number,
                request_type=request_type,
                client_id=ticket.client_id,
                client_match="EXISTING",
                duplicate=True,
            )
        item = db.scalar(
            select(EngineerPreTicket).where(
                EngineerPreTicket.idempotency_key == f"{provider}:{event_id}"
            )
        )
        if not item:
            raise ConflictError("INTEGRATION_EVENT_INCOMPLETE", "The prior event did not complete.")
        return InboundPreTicketResult(
            event_id=event_id,
            pre_ticket_id=item.id,
            pre_ticket_number=item.pre_ticket_number or "",
            request_type=request_type,
            client_id=item.client_id,
            client_match="EXISTING",
            duplicate=True,
        )
    client_value = str(values.get("client") or "").strip()
    normalized_client = client_value.lower()
    predicates = []
    if configuration.client_match_mode in {"CODE", "CODE_OR_EXACT_NAME"}:
        predicates.append(func.lower(Client.code) == normalized_client)
    if configuration.client_match_mode in {"EXACT_NAME", "CODE_OR_EXACT_NAME"}:
        predicates.append(func.lower(Client.name) == normalized_client)
    matches = (
        list(db.scalars(select(Client).where(or_(*predicates))))
        if predicates and client_value
        else []
    )
    matched_client = matches[0] if len(matches) == 1 else None
    if api_client.client_id and (not matched_client or matched_client.id != api_client.client_id):
        raise AuthorizationError("The inbound API client is restricted to another client.")
    title = " ".join(str(values.get("title") or "").split())
    if len(title) < 5 or len(title) > 300:
        raise ConflictError(
            "INBOUND_TITLE_INVALID",
            "Issue title must contain 5 to 300 characters.",
            {"fields": {"title": "Enter between 5 and 300 characters."}},
        )
    if len(title) < 10:
        title = f"{title} request"
    ticket_type = (
        str(values.get("ticket_type") or configuration.default_ticket_type_code).strip().upper()
    )
    valid_ticket_type = db.scalar(
        select(TicketType).where(
            func.upper(TicketType.code) == ticket_type, TicketType.is_active.in_([True])
        )
    )
    if not valid_ticket_type:
        raise ConflictError(
            "INBOUND_TICKET_TYPE_INVALID",
            "The ticket type is unavailable.",
            {
                "fields": {
                    "ticket_type": "Use an active Ticket Type returned by the lookup endpoint."
                }
            },
        )
    caller_name = str(values.get("caller_name") or "").strip()
    caller_number = str(values.get("caller_number") or "").strip()
    description = str(values.get("description") or title).strip()
    initial_description = f"Request type: {request_type}\nRequested ticket type: {ticket_type}\nClient supplied: {client_value}\nCaller name: {caller_name or 'Not supplied'}\nCaller number: {caller_number or 'Not supplied'}\nExternal event: {event_id}\n\n{description}"
    delivery = IntegrationDelivery(
        provider=provider,
        event_id=event_id,
        external_key=client_value or caller_number or api_client.name,
        correlation_id=request.state.correlation_id,
        payload_json=json.dumps(payload, default=str, separators=(",", ":")),
    )
    db.add(delivery)
    db.flush()
    if configuration.processing_mode == "DIRECT_TICKET":
        if not matched_client:
            raise ConflictError(
                "INBOUND_CLIENT_REQUIRED", "Direct ticket creation requires an exact client match."
            )
        actor = _integration_actor(db, app_settings)
        source_channel = "MONITORING" if configuration.source_type == "MONITORING" else "API"
        ticket = create_ticket(
            db,
            TicketCreate(
                ticket_type_id=valid_ticket_type.id,
                client_id=matched_client.id,
                source_channel=source_channel,
                creation_idempotency_key=f"{provider}:{event_id}",
                impact="MEDIUM",
                urgency="MEDIUM",
                subject=title,
                description=initial_description,
            ),
            actor,
        )
        delivery.ticket_id = ticket.id
        delivery.status = "PROCESSED"
        delivery.processed_at = server_now()
        delivery.external_key = ticket.ticket_number or event_id
        api_client.last_used_at = server_now()
        db.commit()
        return InboundPreTicketResult(
            event_id=event_id,
            ticket_id=ticket.id,
            ticket_number=ticket.ticket_number,
            request_type=request_type,
            client_id=ticket.client_id,
            client_match="MATCHED",
            duplicate=False,
        )
    item = EngineerPreTicket(
        pre_ticket_number=f"PENDING-{secrets.token_hex(16)}",
        status="SUBMITTED",
        request_kind="TICKET_REQUEST" if request_type == "CREATE_TICKET" else "CALL_REQUEST",
        source_provider=configuration.provider_key.upper(),
        external_event_id=event_id,
        external_caller_name=caller_name or None,
        external_caller_number=caller_number or None,
        requested_ticket_type_code=ticket_type,
        client_id=matched_client.id if matched_client else None,
        proposed_priority=configuration.default_priority,
        title=title,
        initial_description=initial_description,
        submitted_by_user_id=_integration_actor(db, app_settings).id,
        idempotency_key=f"{provider}:{event_id}",
        request_fingerprint=_key_hash(json.dumps(payload, sort_keys=True, default=str)),
    )
    db.add(item)
    db.flush()
    item.pre_ticket_number = f"PRE-{item.id:06d}"
    delivery.status = "PROCESSED"
    delivery.processed_at = server_now()
    delivery.external_key = item.pre_ticket_number
    api_client.last_used_at = server_now()
    for recipient in db.scalars(
        select(User).where(User.is_active.in_([True]), User.user_type == "EMPLOYEE")
    ):
        if "ticket.pre_ticket.queue.process" in set(
            effective_permissions(db, recipient).permissions
        ):
            db.add(
                Notification(
                    recipient_user_id=recipient.id,
                    notification_type="PRE_TICKET",
                    severity="INFO",
                    title=f"Inbound {request_type.replace('_', ' ').title()}",
                    message=f"{item.pre_ticket_number}: {item.title}",
                    deep_link="/tickets?tab=pre-tickets",
                    deduplication_key=f"inbound-pre-ticket:{item.id}:user:{recipient.id}",
                )
            )
    db.add(
        AuditLog(
            actor_user_id=item.submitted_by_user_id,
            entity_type="EngineerPreTicket",
            entity_id=str(item.id),
            action="integration.inbound_pre_ticket.received",
            correlation_id=request.state.correlation_id,
            new_values_json=json.dumps(
                {
                    "request_type": request_type,
                    "client_match": "MATCHED" if matched_client else "REVIEW_REQUIRED",
                }
            ),
        )
    )
    db.commit()
    return InboundPreTicketResult(
        event_id=event_id,
        pre_ticket_id=item.id,
        pre_ticket_number=item.pre_ticket_number,
        request_type=request_type,
        client_id=item.client_id,
        client_match="MATCHED" if matched_client else "REVIEW_REQUIRED",
        duplicate=False,
    )


def _inbound_context(
    integration_key: str, x_api_key: str, authorization: str, db: Session
) -> tuple[IntegrationApiClient, InboundVendorProfile, str]:
    api_client = _vendor_client(db, x_api_key, authorization)
    configuration = _inbound_profile(db, integration_key)
    if api_client.provider_key and api_client.provider_key != configuration.provider_key:
        raise AuthorizationError("This API credential belongs to another vendor profile.")
    return (
        api_client,
        configuration,
        f"INBOUND_{configuration.provider_key.upper()}_{api_client.id}",
    )


@router.get("/inbound/v1/{integration_key}/clients", response_model=list[InboundClientResult])
def inbound_clients(
    integration_key: str,
    search: str = "",
    x_api_key: str = Header(default=""),
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> list[Client]:
    api_client, _, _ = _inbound_context(integration_key, x_api_key, authorization, db)
    query = select(Client)
    if api_client.client_id:
        query = query.where(Client.id == api_client.client_id)
    elif search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.where(
            or_(func.lower(Client.code).like(term), func.lower(Client.name).like(term))
        )
    else:
        query = query.where(Client.is_active.in_([True]))
    return list(db.scalars(query.order_by(Client.name).limit(25)))


@router.get("/inbound/v1/{integration_key}/ticket-types")
def inbound_ticket_types(
    integration_key: str,
    x_api_key: str = Header(default=""),
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    _inbound_context(integration_key, x_api_key, authorization, db)
    return [
        {"code": item.code, "name": item.name, "is_active": item.is_active}
        for item in db.scalars(
            select(TicketType).where(TicketType.is_active.in_([True])).order_by(TicketType.name)
        )
    ]


@router.get(
    "/inbound/v1/{integration_key}/requests/{event_id}", response_model=InboundRequestStatus
)
def inbound_request_status(
    integration_key: str,
    event_id: str,
    x_api_key: str = Header(default=""),
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> InboundRequestStatus:
    api_client, _, provider = _inbound_context(integration_key, x_api_key, authorization, db)
    delivery = db.scalar(
        select(IntegrationDelivery).where(
            IntegrationDelivery.provider == provider, IntegrationDelivery.event_id == event_id
        )
    )
    item = db.scalar(
        select(EngineerPreTicket).where(
            EngineerPreTicket.idempotency_key == f"{provider}:{event_id}"
        )
    )
    if not item and not (delivery and delivery.ticket_id):
        raise NotFoundError("Inbound request does not exist.")
    ticket_id = item.resulting_ticket_id if item else (delivery.ticket_id if delivery else None)
    ticket = db.get(Ticket, ticket_id) if ticket_id else None
    if ticket and api_client.client_id and ticket.client_id != api_client.client_id:
        raise AuthorizationError("This API credential cannot access the resulting ticket.")
    ticket_status = db.get(TicketStatus, ticket.status_id) if ticket else None
    return InboundRequestStatus(
        event_id=event_id,
        pre_ticket_id=item.id if item else None,
        pre_ticket_number=(item.pre_ticket_number or "") if item else None,
        request_type="REQUEST_CALL"
        if item and item.request_kind == "CALL_REQUEST"
        else "CREATE_TICKET",
        status=item.status if item else (ticket_status.code if ticket_status else "PROCESSED"),
        ticket_id=ticket.id if ticket else None,
        ticket_number=ticket.ticket_number if ticket else None,
        ticket_status_code=ticket_status.code if ticket_status else None,
        ticket_status_name=ticket_status.name if ticket_status else None,
        resolution_summary=ticket.resolution_summary if ticket else None,
        resolved_at=ticket.resolved_at if ticket else None,
        closed_at=ticket.closed_at if ticket else None,
        ticket_updated_at=ticket.updated_at if ticket else None,
        updated_at=item.updated_at
        if item
        else (ticket.updated_at if ticket else delivery.processed_at if delivery else server_now()),
    )


@router.get("/api-clients", response_model=list[ApiClientRead])
def list_api_clients(
    db: Session = Depends(get_db), _: User = Depends(require_permission("configuration.manage"))
) -> list[IntegrationApiClient]:
    return list(
        db.scalars(select(IntegrationApiClient).order_by(IntegrationApiClient.created_at.desc()))
    )


@router.post(
    "/monitoring/events",
    response_model=MonitoringResult,
    status_code=status.HTTP_201_CREATED,
)
def receive_monitoring_event(
    data: MonitoringEvent,
    request: Request,
    x_integration_key: str = Header(default=""),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MonitoringResult:
    if not hmac.compare_digest(x_integration_key, settings.monitoring_webhook_key):
        raise AuthenticationError("INVALID_INTEGRATION_KEY", "Invalid integration key.")

    existing = db.scalar(
        select(IntegrationDelivery).where(
            IntegrationDelivery.provider == "MONITORING",
            IntegrationDelivery.event_id == data.event_id,
        )
    )
    if existing:
        ticket = db.get(Ticket, existing.ticket_id) if existing.ticket_id else None
        if not ticket:
            raise ConflictError("INTEGRATION_EVENT_INCOMPLETE", "The prior event did not complete.")
        return MonitoringResult(
            event_id=data.event_id,
            ticket_id=ticket.id,
            ticket_number=ticket.ticket_number or "",
            duplicate=True,
        )

    actor = _integration_actor(db, settings)
    ticket_type = db.scalar(select(TicketType).where(TicketType.code == "INCIDENT"))
    if not ticket_type:
        raise NotFoundError("The incident type is unavailable.")

    delivery = IntegrationDelivery(
        provider="MONITORING",
        event_id=data.event_id,
        external_key=data.alert_key,
        correlation_id=request.state.correlation_id,
        payload_json=json.dumps(data.model_dump(mode="json"), separators=(",", ":")),
    )
    db.add(delivery)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "INTEGRATION_EVENT_CONFLICT", "The event is already being processed."
        ) from None

    ticket = create_ticket(
        db,
        TicketCreate(
            ticket_type_id=ticket_type.id,
            client_id=data.client_id,
            source_channel="MONITORING",
            creation_idempotency_key=f"monitoring:{data.event_id}",
            impact=data.severity,
            urgency=data.severity,
            subject=data.subject,
            description=data.description,
            first_occurred_at=data.occurred_at,
        ),
        actor,
    )
    delivery.ticket_id = ticket.id
    delivery.status = "PROCESSED"
    delivery.processed_at = server_now()
    db.add(delivery)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="IntegrationDelivery",
            entity_id=str(delivery.id),
            action="monitoring.ticket.created",
            correlation_id=request.state.correlation_id,
        )
    )
    db.commit()
    return MonitoringResult(
        event_id=data.event_id,
        ticket_id=ticket.id,
        ticket_number=ticket.ticket_number or "",
        duplicate=False,
    )


@router.post(
    "/email/events",
    response_model=InboundEmailResult,
    status_code=status.HTTP_201_CREATED,
)
def receive_email_event(
    data: InboundEmailEvent,
    request: Request,
    x_integration_key: str = Header(default=""),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> InboundEmailResult:
    if not hmac.compare_digest(x_integration_key, settings.inbound_email_webhook_key):
        raise AuthenticationError("INVALID_INTEGRATION_KEY", "Invalid integration key.")
    existing = db.scalar(
        select(IntegrationDelivery).where(
            IntegrationDelivery.provider == "INBOUND_EMAIL",
            IntegrationDelivery.event_id == data.message_id,
        )
    )
    if existing:
        ticket = db.get(Ticket, existing.ticket_id) if existing.ticket_id else None
        if not ticket:
            raise ConflictError("INTEGRATION_EVENT_INCOMPLETE", "The prior event did not complete.")
        return InboundEmailResult(
            message_id=data.message_id,
            ticket_id=ticket.id,
            ticket_number=ticket.ticket_number or "",
            action="DUPLICATE",
            duplicate=True,
        )

    actor = _integration_actor(db, settings)
    ticket = (
        db.scalar(select(Ticket).where(Ticket.ticket_number == data.ticket_number))
        if data.ticket_number
        else None
    )
    if data.ticket_number and not ticket:
        raise NotFoundError("The referenced ticket does not exist.")
    if ticket and ticket.client_id != data.client_id:
        raise ConflictError(
            "EMAIL_CLIENT_MISMATCH", "The referenced ticket belongs to another client."
        )
    delivery = IntegrationDelivery(
        provider="INBOUND_EMAIL",
        event_id=data.message_id,
        external_key=str(data.from_address),
        correlation_id=request.state.correlation_id,
        payload_json=json.dumps(data.model_dump(mode="json"), separators=(",", ":")),
    )
    db.add(delivery)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "INTEGRATION_EVENT_CONFLICT", "The email is already being processed."
        ) from None

    action = "COMMENTED"
    if ticket:
        db.add(
            TicketComment(
                ticket_id=ticket.id,
                author_user_id=actor.id,
                is_internal=False,
                body=f"Email from {data.from_address}:\n\n{data.body}",
            )
        )
        ticket.last_activity_at = server_now()
        ticket.version += 1
    else:
        ticket_type = db.scalar(select(TicketType).where(TicketType.code == "INCIDENT"))
        if not ticket_type:
            raise NotFoundError("The incident type is unavailable.")
        ticket = create_ticket(
            db,
            TicketCreate(
                ticket_type_id=ticket_type.id,
                client_id=data.client_id,
                source_channel="EMAIL",
                creation_idempotency_key=f"inbound-email:{data.message_id}",
                impact="MEDIUM",
                urgency="MEDIUM",
                subject=data.subject,
                description=f"Email from {data.from_address}:\n\n{data.body}",
                first_occurred_at=data.received_at,
            ),
            actor,
        )
        action = "CREATED"
    delivery.ticket_id = ticket.id
    delivery.status = "PROCESSED"
    delivery.processed_at = server_now()
    db.add(delivery)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="IntegrationDelivery",
            entity_id=str(delivery.id),
            action=f"inbound_email.ticket.{action.lower()}",
            correlation_id=request.state.correlation_id,
        )
    )
    db.commit()
    return InboundEmailResult(
        message_id=data.message_id,
        ticket_id=ticket.id,
        ticket_number=ticket.ticket_number or "",
        action=action,
        duplicate=False,
    )


@router.post("/itop/tickets/import", response_model=ItopImportResult)
def import_itop_tickets(
    data: ItopImportBatch,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> ItopImportResult:
    results: list[ItopImportItemResult] = []
    imported = 0
    skipped = 0
    for item in data.items:
        mapping = db.scalar(
            select(LegacyTicketMap).where(
                LegacyTicketMap.source_system == "ITOP",
                LegacyTicketMap.external_id == item.external_id,
            )
        )
        if mapping:
            ticket = db.get(Ticket, mapping.ticket_id)
            if not ticket:
                raise ConflictError("LEGACY_MAPPING_BROKEN", "A legacy ticket mapping is invalid.")
            results.append(
                ItopImportItemResult(
                    external_id=item.external_id,
                    ticket_id=ticket.id,
                    ticket_number=ticket.ticket_number or "",
                    imported=False,
                )
            )
            skipped += 1
            continue
        ticket_type = db.scalar(
            select(TicketType).where(TicketType.code == item.ticket_type_code.upper())
        )
        if not ticket_type:
            raise NotFoundError(f"Ticket type {item.ticket_type_code} does not exist.")
        provenance = f"Imported from iTop record {item.external_id}."
        if item.original_status:
            provenance += f" Original status: {item.original_status}."
        ticket = create_ticket(
            db,
            TicketCreate(
                ticket_type_id=ticket_type.id,
                client_id=item.client_id,
                source_channel="ITOP_IMPORT",
                creation_idempotency_key=f"itop:{item.external_id}",
                impact=item.impact,
                urgency=item.urgency,
                subject=item.subject,
                description=f"{item.description[:19500]}\n\n{provenance}",
                first_occurred_at=item.created_at,
            ),
            actor,
        )
        db.add(
            LegacyTicketMap(
                source_system="ITOP",
                external_id=item.external_id,
                ticket_id=ticket.id,
                original_status=item.original_status,
                imported_by_user_id=actor.id,
            )
        )
        db.add(
            AuditLog(
                actor_user_id=actor.id,
                entity_type="Ticket",
                entity_id=str(ticket.id),
                action="itop.ticket.imported",
                reason=f"Legacy iTop ID: {item.external_id}",
            )
        )
        db.commit()
        results.append(
            ItopImportItemResult(
                external_id=item.external_id,
                ticket_id=ticket.id,
                ticket_number=ticket.ticket_number or "",
                imported=True,
            )
        )
        imported += 1
    return ItopImportResult(imported=imported, skipped=skipped, items=results)


@router.post(
    "/api-clients",
    response_model=ApiClientCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_api_client(
    data: ApiClientCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> ApiClientCreated:
    if db.scalar(select(IntegrationApiClient.id).where(IntegrationApiClient.name == data.name)):
        raise ConflictError("DUPLICATE_API_CLIENT", "An API client with that name exists.")
    if data.client_id:
        from app.modules.clients.models import Client

        target_client = db.get(Client, data.client_id)
        if not target_client or not target_client.is_active:
            raise NotFoundError("The scoped client does not exist or is inactive.")
    if data.provider_key and not any(
        profile.provider_key == data.provider_key for profile in _inbound_settings(db).profiles
    ):
        raise NotFoundError("The selected vendor profile does not exist.")
    if data.username and db.scalar(
        select(IntegrationApiClient.id).where(
            func.lower(IntegrationApiClient.api_username) == data.username.lower()
        )
    ):
        raise ConflictError("DUPLICATE_API_USERNAME", "This API username already exists.")
    api_key = f"msh_{secrets.token_urlsafe(32)}" if data.auth_type == "API_KEY" else None
    item = IntegrationApiClient(
        name=data.name,
        key_prefix=api_key[:16] if api_key else f"basic_{secrets.token_hex(5)}",
        key_hash=_key_hash(api_key) if api_key else _key_hash(secrets.token_urlsafe(32)),
        client_id=data.client_id,
        provider_key=data.provider_key,
        auth_type=data.auth_type,
        api_username=data.username.lower() if data.username else None,
        password_hash=hash_password(data.password) if data.password else None,
        created_by_user_id=actor.id,
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="IntegrationApiClient",
            entity_id=str(item.id),
            action="api_client.created",
        )
    )
    db.commit()
    return ApiClientCreated(
        id=item.id,
        name=item.name,
        client_id=item.client_id,
        provider_key=item.provider_key,
        auth_type=item.auth_type,
        username=item.api_username,
        api_key=api_key,
    )


@router.delete("/api-clients/{api_client_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_client(
    api_client_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> Response:
    item = db.get(IntegrationApiClient, api_client_id)
    if not item:
        raise NotFoundError()
    item.is_active = False
    item.revoked_at = server_now()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="IntegrationApiClient",
            entity_id=str(item.id),
            action="api_client.revoked",
        )
    )
    db.commit()
    return Response(status_code=204)


def _monitoring_contact(db: Session, client_id: int) -> Contact:
    contact = db.scalar(
        select(Contact).where(
            Contact.client_id == client_id,
            func.lower(Contact.full_name) == "mimonitoringservice",
        )
    )
    if contact is None:
        contact = Contact(
            code=f"MIMONITORING_{client_id}",
            client_id=client_id,
            full_name="MiMonitoringService",
            email=f"mimonitoringservice+{client_id}@local.invalid",
            job_title="Monitoring integration",
            contact_role="SYSTEM",
            is_active=True,
        )
        db.add(contact)
        db.flush()
    return contact


def _apply_system_maintenance_flag(
    db: Session, ticket: Ticket, actor: User
) -> None:
    flag = db.scalar(
        select(TicketFlag).where(
            or_(
                TicketFlag.code == "SYSTEM_MAINTENANCE",
                func.lower(TicketFlag.name) == "system maintenance",
            )
        )
    )
    if flag is None:
        flag = TicketFlag(
            code="SYSTEM_MAINTENANCE",
            name="System Maintenance",
            description="Monitoring-detected system maintenance; resolution SLA is paused.",
            color="#ED6C02",
            pauses_sla=True,
            is_active=True,
            sort_order=10,
        )
        db.add(flag)
        db.flush()
    else:
        flag.pauses_sla = True
        flag.is_active = True

    clock = db.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket.id,
            TicketSlaClock.clock_type == "RESOLUTION",
        )
    )
    interval = None
    if clock is not None:
        interval = TicketSlaInterval(
            ticket_id=ticket.id,
            interval_type="FLAG_PAUSE",
            responsible_party="AUTHORIZED_EXCLUSION",
            comment="Automatically paused for MiMonitoringService system maintenance.",
            started_at=server_now(),
            created_by_user_id=actor.id,
        )
        db.add(interval)
        db.flush()
        clock.state = "PAUSED"

    db.add(
        TicketFlagAssignment(
            ticket_id=ticket.id,
            flag_id=flag.id,
            interval_id=interval.id if interval else None,
            flag_code_snapshot=flag.code,
            flag_name_snapshot=flag.name,
            flag_color_snapshot=flag.color,
            pauses_sla_snapshot=True,
            apply_reason="Applied automatically by MiMonitoringService.",
            applied_by_user_id=actor.id,
        )
    )


@router.post("/api/tickets", response_model=ApiTicketResult, status_code=status.HTTP_201_CREATED)
def create_api_ticket(
    data: ApiTicketCreate,
    request: Request,
    x_api_key: str = Header(default=""),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ApiTicketResult:
    api_client = _api_client(db, x_api_key)
    if api_client.client_id and api_client.client_id != data.client_id:
        raise AuthorizationError("This API client is restricted to another client.")
    provider = f"API_CLIENT_{api_client.id}"
    existing = db.scalar(
        select(IntegrationDelivery).where(
            IntegrationDelivery.provider == provider,
            IntegrationDelivery.event_id == data.event_id,
        )
    )
    if existing:
        ticket = db.get(Ticket, existing.ticket_id) if existing.ticket_id else None
        if not ticket:
            raise ConflictError("INTEGRATION_EVENT_INCOMPLETE", "The prior event did not complete.")
        return ApiTicketResult(
            event_id=data.event_id,
            ticket_id=ticket.id,
            ticket_number=ticket.ticket_number or "",
            duplicate=True,
        )
    ticket_type = db.scalar(
        select(TicketType).where(TicketType.code == data.ticket_type_code.upper())
    )
    if not ticket_type:
        raise NotFoundError("The requested ticket type does not exist.")
    actor = _integration_actor(db, settings)
    requester = _monitoring_contact(db, data.client_id)
    delivery = IntegrationDelivery(
        provider=provider,
        event_id=data.event_id,
        external_key=api_client.name,
        correlation_id=request.state.correlation_id,
        payload_json=json.dumps(data.model_dump(mode="json"), separators=(",", ":")),
    )
    db.add(delivery)
    db.flush()
    ticket = create_ticket(
        db,
        TicketCreate(
            ticket_type_id=ticket_type.id,
            client_id=data.client_id,
            requester_contact_id=requester.id,
            source_channel="API",
            creation_idempotency_key=f"api:{provider}:{data.event_id}",
            impact=data.impact,
            urgency=data.urgency,
            subject=data.subject,
            description=data.description,
        ),
        actor,
        commit=False,
        enforce_configured_required_fields=False,
    )
    _apply_system_maintenance_flag(db, ticket, actor)
    delivery.ticket_id = ticket.id
    delivery.status = "PROCESSED"
    delivery.processed_at = server_now()
    api_client.last_used_at = server_now()
    db.commit()
    return ApiTicketResult(
        event_id=data.event_id,
        ticket_id=ticket.id,
        ticket_number=ticket.ticket_number or "",
        duplicate=False,
    )


def _api_ticket(
    db: Session, api_client: IntegrationApiClient, ticket_id: int
) -> Ticket:
    provider = f"API_CLIENT_{api_client.id}"
    ticket = db.scalar(
        select(Ticket)
        .join(IntegrationDelivery, IntegrationDelivery.ticket_id == Ticket.id)
        .where(
            Ticket.id == ticket_id,
            IntegrationDelivery.provider == provider,
        )
    )
    if ticket is None:
        raise NotFoundError("Ticket does not exist or was not created by this API client.")
    return ticket


def _api_ticket_status_result(
    db: Session,
    ticket: Ticket,
    *,
    event_id: str | None = None,
    duplicate: bool = False,
) -> ApiTicketStatusResult:
    ticket_status = db.get(TicketStatus, ticket.status_id)
    if ticket_status is None:
        raise NotFoundError("Ticket status does not exist.")
    return ApiTicketStatusResult(
        event_id=event_id,
        ticket_id=ticket.id,
        ticket_number=ticket.ticket_number or "",
        status_code=ticket_status.code,
        version=ticket.version,
        resolution_summary=ticket.resolution_summary,
        duplicate=duplicate,
    )


@router.get("/api/tickets/{ticket_id}", response_model=ApiTicketStatusResult)
def get_api_ticket_status(
    ticket_id: int,
    x_api_key: str = Header(default=""),
    db: Session = Depends(get_db),
) -> ApiTicketStatusResult:
    api_client = _api_client(db, x_api_key)
    ticket = _api_ticket(db, api_client, ticket_id)
    api_client.last_used_at = server_now()
    db.commit()
    return _api_ticket_status_result(db, ticket)


@router.patch("/api/tickets/{ticket_id}/status", response_model=ApiTicketStatusResult)
def update_api_ticket_status(
    ticket_id: int,
    data: ApiTicketStatusUpdate,
    request: Request,
    x_api_key: str = Header(default=""),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ApiTicketStatusResult:
    api_client = _api_client(db, x_api_key)
    ticket = _api_ticket(db, api_client, ticket_id)
    provider = f"API_CLIENT_{api_client.id}_STATUS"
    previous = db.scalar(
        select(IntegrationDelivery).where(
            IntegrationDelivery.provider == provider,
            IntegrationDelivery.event_id == data.event_id,
        )
    )
    if previous:
        if previous.ticket_id != ticket.id:
            raise ConflictError(
                "INTEGRATION_EVENT_CONFLICT",
                "This status event ID was already used for another ticket.",
            )
        return _api_ticket_status_result(
            db, ticket, event_id=data.event_id, duplicate=True
        )
    actor = _integration_actor(db, settings)
    current_status = db.get(TicketStatus, ticket.status_id)
    close_through_resolution = (
        data.status_code == "CLOSED"
        and current_status is not None
        and current_status.code not in {"RESOLVED", "CLIENT_CONFIRMATION"}
    )
    transition_ticket(
        db,
        ticket,
        TicketTransition(
            to_status_code="RESOLVED" if close_through_resolution else data.status_code,
            reason=data.reason,
            resolution_summary=data.resolution_summary,
            root_cause_summary=data.root_cause_summary,
            version=ticket.version,
            close_after_resolve=close_through_resolution,
        ),
        actor,
        commit=False,
        additional_permissions={
            "ticket.change.status",
            "ticket.start.progress",
            "ticket.resolve",
            "ticket.resolve.any",
            "ticket.close",
            "ticket.cancel",
            "ticket.reopen",
        },
        source="MONITORING_API",
    )
    db.add(
        IntegrationDelivery(
            provider=provider,
            event_id=data.event_id,
            external_key=str(ticket.id),
            correlation_id=request.state.correlation_id,
            payload_json=json.dumps(data.model_dump(mode="json"), separators=(",", ":")),
            ticket_id=ticket.id,
            status="PROCESSED",
            processed_at=server_now(),
        )
    )
    api_client.last_used_at = server_now()
    db.commit()
    db.refresh(ticket)
    return _api_ticket_status_result(db, ticket, event_id=data.event_id)
