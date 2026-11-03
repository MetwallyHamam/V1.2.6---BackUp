import hashlib
import json
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError
from app.db.session import get_db
from app.modules.configuration.models import SiteSetting
from app.modules.configuration.policy_service import resolve_feature_policy
from app.modules.iam.models import AuditLog, User
from app.modules.outlook_email.graph_client import (
    GraphConfigurationError,
    GraphRequestError,
    MicrosoftGraphClient,
)
from app.modules.outlook_email.models import (
    OutlookEmailTemplate,
    OutlookMessage,
    OutlookNotification,
    OutlookOutboundDelivery,
    OutlookSubscription,
)

router = APIRouter(prefix="/system/outlook-email", tags=["Outlook email integration"])

SETTING_KEY = "outlook_email_configuration"


class OutlookConfigurationWrite(BaseModel):
    mailbox_address: EmailStr = "Support@millensys.com"
    allowed_domains: list[str] = Field(default_factory=list, max_length=100)
    allowed_addresses: list[EmailStr] = Field(default_factory=list, max_length=200)
    blocked_senders: list[EmailStr] = Field(default_factory=list, max_length=200)
    unknown_sender_action: str = Field(default="QUARANTINE", pattern="^(QUARANTINE|IGNORE)$")
    attachment_max_bytes: int = Field(default=8_388_608, ge=1024, le=52_428_800)
    allowed_attachment_extensions: list[str] = Field(default_factory=lambda: ["pdf", "png", "jpg", "jpeg", "txt", "log", "zip"], max_length=100)
    default_ticket_type_id: int | None = None
    default_product_id: int | None = None
    default_service_id: int | None = None
    default_impact: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH)$")
    default_urgency: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH)$")

    @field_validator("allowed_domains")
    @classmethod
    def normalize_domains(cls, values: list[str]) -> list[str]:
        normalized = sorted({value.strip().lower().lstrip("@") for value in values if value.strip()})
        if any("@" in value or "." not in value for value in normalized):
            raise ValueError("Allowed domains must be domain names such as alfascan.com.")
        return normalized


class OutlookConfigurationRead(OutlookConfigurationWrite):
    credentials_configured: bool
    client_state_configured: bool


class OutlookTemplateWrite(BaseModel):
    event_key: str = Field(pattern="^(CREATED|IN_PROGRESS|PENDING|RESOLVED|CLOSED|REOPENED)$")
    subject_template: str = Field(min_length=3, max_length=300)
    body_template: str = Field(min_length=3, max_length=10000)
    is_enabled: bool = False
    expected_version: int | None = Field(default=None, ge=1)


class OutlookTemplateRead(BaseModel):
    id: int
    event_key: str
    subject_template: str
    body_template: str
    is_enabled: bool
    version: int


class OutlookHealthRead(BaseModel):
    credentials_configured: bool
    client_state_configured: bool
    subscription_status: str
    subscription_expires_at: str | None
    last_notification_at: str | None
    last_sync_at: str | None
    last_error: str | None


def graph_expiration() -> datetime:
    return server_now() + timedelta(hours=70)


def graph_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def queue_graph_notification(db: Session, value: dict[str, object]) -> bool:
    subscription_id = str(value.get("subscriptionId", ""))
    resource = str(value.get("resource", ""))
    change_type = str(value.get("changeType", "updated"))
    resource_data = value.get("resourceData")
    resource_id = str(resource_data.get("id", "")) if isinstance(resource_data, dict) else ""
    canonical = f"{subscription_id}|{change_type}|{resource}|{resource_id}"
    deduplication_key = hashlib.sha256(canonical.encode()).hexdigest()
    if db.scalar(select(OutlookNotification.id).where(OutlookNotification.deduplication_key == deduplication_key)):
        return False
    try:
        with db.begin_nested():
            db.add(OutlookNotification(
                deduplication_key=deduplication_key, subscription_id=subscription_id,
                resource=resource, change_type=change_type,
                payload_json=json.dumps(value, separators=(",", ":"), sort_keys=True),
            ))
            db.flush()
    except IntegrityError:
        return False
    return True


def load_configuration(db: Session) -> OutlookConfigurationWrite:
    row = db.get(SiteSetting, SETTING_KEY)
    if not row:
        return OutlookConfigurationWrite()
    return OutlookConfigurationWrite.model_validate(json.loads(row.value))


@router.get("/configuration", response_model=OutlookConfigurationRead)
def get_configuration(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings),
    _: User = Depends(require_permission("configuration.manage")),
) -> OutlookConfigurationRead:
    value = load_configuration(db)
    graph = MicrosoftGraphClient(settings)
    return OutlookConfigurationRead(
        **value.model_dump(), credentials_configured=graph.configured(),
        client_state_configured=bool(settings.microsoft_graph_client_state),
    )


@router.put("/configuration", response_model=OutlookConfigurationRead)
def put_configuration(
    data: OutlookConfigurationWrite, db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(require_permission("configuration.manage")),
) -> OutlookConfigurationRead:
    serialized = json.dumps(data.model_dump(mode="json"), separators=(",", ":"), sort_keys=True)
    row = db.get(SiteSetting, SETTING_KEY)
    previous = row.value if row else None
    if row:
        row.value = serialized
    else:
        db.add(SiteSetting(key=SETTING_KEY, value=serialized))
    db.add(AuditLog(
        actor_user_id=actor.id, entity_type="SiteSetting", entity_id=SETTING_KEY,
        action="outlook_email.configuration.updated", old_values_json=previous,
        new_values_json=serialized,
    ))
    db.commit()
    graph = MicrosoftGraphClient(settings)
    return OutlookConfigurationRead(
        **data.model_dump(), credentials_configured=graph.configured(),
        client_state_configured=bool(settings.microsoft_graph_client_state),
    )


@router.get("/templates", response_model=list[OutlookTemplateRead])
def list_templates(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("configuration.manage")),
) -> list[OutlookEmailTemplate]:
    return list(db.scalars(select(OutlookEmailTemplate).order_by(OutlookEmailTemplate.event_key)))


@router.put("/templates/{event_key}", response_model=OutlookTemplateRead)
def put_template(
    event_key: str, data: OutlookTemplateWrite, db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> OutlookEmailTemplate:
    if event_key != data.event_key:
        raise ConflictError("OUTLOOK_TEMPLATE_EVENT_MISMATCH", "The template event does not match the URL.")
    item = db.scalar(select(OutlookEmailTemplate).where(OutlookEmailTemplate.event_key == event_key))
    if item:
        if data.expected_version is not None and item.version != data.expected_version:
            raise ConflictError("OUTLOOK_TEMPLATE_CHANGED", "The template changed. Refresh and try again.")
        item.version += 1
    else:
        item = OutlookEmailTemplate(event_key=event_key, updated_by_user_id=actor.id)
        db.add(item)
    item.subject_template = data.subject_template
    item.body_template = data.body_template
    item.is_enabled = data.is_enabled
    item.updated_by_user_id = actor.id
    db.commit(); db.refresh(item)
    return item


@router.get("/health", response_model=OutlookHealthRead)
def outlook_health(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings),
    _: User = Depends(require_permission("configuration.manage")),
) -> OutlookHealthRead:
    subscription = db.scalar(select(OutlookSubscription).order_by(OutlookSubscription.expires_at.desc()))
    return OutlookHealthRead(
        credentials_configured=MicrosoftGraphClient(settings).configured(),
        client_state_configured=bool(settings.microsoft_graph_client_state),
        subscription_status=subscription.status if subscription else "NOT_CREATED",
        subscription_expires_at=subscription.expires_at.isoformat() if subscription else None,
        last_notification_at=subscription.last_notification_at.isoformat() if subscription and subscription.last_notification_at else None,
        last_sync_at=subscription.last_sync_at.isoformat() if subscription and subscription.last_sync_at else None,
        last_error=subscription.last_error if subscription else None,
    )


@router.post("/connection-test")
def test_connection(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings),
    _: User = Depends(require_permission("configuration.manage")),
) -> dict[str, object]:
    configuration = load_configuration(db)
    graph = MicrosoftGraphClient(settings)
    mailbox = str(configuration.mailbox_address).replace("'", "''")
    try:
        result = graph.request("GET", f"users/{mailbox}?$select=id,displayName,mail,userPrincipalName")
    except GraphConfigurationError as exc:
        raise ConflictError("OUTLOOK_CREDENTIALS_REQUIRED", str(exc)) from exc
    except GraphRequestError as exc:
        raise ConflictError("OUTLOOK_CONNECTION_FAILED", str(exc)) from exc
    return {"connected": True, "mailbox": configuration.mailbox_address, "graph_identity": result}


@router.post("/subscription")
def create_subscription(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings),
    _: User = Depends(require_permission("configuration.manage")),
) -> dict[str, object]:
    if not settings.microsoft_graph_notification_url or not settings.microsoft_graph_client_state:
        raise ConflictError("OUTLOOK_WEBHOOK_CONFIGURATION_REQUIRED", "Notification URL and client state are required.")
    configuration = load_configuration(db)
    mailbox = str(configuration.mailbox_address)
    expiration = graph_expiration()
    payload: dict[str, object] = {
        "changeType": "created,updated",
        "notificationUrl": settings.microsoft_graph_notification_url,
        "resource": f"users/{mailbox}/mailFolders('Inbox')/messages",
        "expirationDateTime": expiration.isoformat().replace("+00:00", "Z"),
        "clientState": settings.microsoft_graph_client_state,
    }
    if settings.microsoft_graph_lifecycle_url:
        payload["lifecycleNotificationUrl"] = settings.microsoft_graph_lifecycle_url
    try:
        result = MicrosoftGraphClient(settings).request("POST", "subscriptions", payload)
    except (GraphConfigurationError, GraphRequestError) as exc:
        raise ConflictError("OUTLOOK_SUBSCRIPTION_FAILED", str(exc)) from exc
    graph_id = str(result.get("id", ""))
    graph_expiry = str(result.get("expirationDateTime", payload["expirationDateTime"]))
    if not graph_id:
        raise ConflictError("OUTLOOK_SUBSCRIPTION_FAILED", "Graph did not return a subscription ID.")
    for previous in db.scalars(select(OutlookSubscription).where(OutlookSubscription.status == "ACTIVE")):
        previous.status = "SUPERSEDED"
    item = OutlookSubscription(
        graph_subscription_id=graph_id, mailbox_address=mailbox,
        resource=str(payload["resource"]), status="ACTIVE", expires_at=graph_datetime(graph_expiry),
    )
    db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id, "graph_subscription_id": graph_id, "status": item.status, "expires_at": item.expires_at}


@router.post("/subscription/renew")
def renew_subscription(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings),
    _: User = Depends(require_permission("configuration.manage")),
) -> dict[str, object]:
    item = db.scalar(select(OutlookSubscription).where(OutlookSubscription.status == "ACTIVE").order_by(OutlookSubscription.expires_at.desc()))
    if not item:
        raise ConflictError("OUTLOOK_SUBSCRIPTION_NOT_FOUND", "Create the Outlook subscription first.")
    expiration = graph_expiration()
    try:
        result = MicrosoftGraphClient(settings).request("PATCH", f"subscriptions/{item.graph_subscription_id}", {"expirationDateTime": expiration.isoformat().replace("+00:00", "Z")})
    except (GraphConfigurationError, GraphRequestError) as exc:
        item.status = "REAUTHORIZE_REQUIRED"; item.last_error = str(exc); db.commit()
        raise ConflictError("OUTLOOK_SUBSCRIPTION_RENEWAL_FAILED", str(exc)) from exc
    item.expires_at = graph_datetime(str(result.get("expirationDateTime", expiration.isoformat())))
    item.status = "ACTIVE"; item.last_error = None; db.commit()
    return {"status": item.status, "expires_at": item.expires_at}


@router.get("/webhook", response_class=PlainTextResponse)
def validate_webhook(validation_token: str = Query(alias="validationToken")) -> str:
    return validation_token


@router.post("/webhook", status_code=202)
async def receive_webhook(request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> dict[str, int]:
    payload = await request.json()
    values = payload.get("value", []) if isinstance(payload, dict) else []
    accepted = 0
    for value in values if isinstance(values, list) else []:
        if not isinstance(value, dict):
            continue
        supplied_state = str(value.get("clientState", ""))
        expected_state = settings.microsoft_graph_client_state or ""
        if not expected_state or not secrets.compare_digest(supplied_state, expected_state):
            continue
        subscription = db.scalar(select(OutlookSubscription).where(OutlookSubscription.graph_subscription_id == str(value.get("subscriptionId", ""))))
        if not subscription:
            continue
        mode = resolve_feature_policy(db, "outlook_inbound_email").mode
        if mode == "OFF":
            continue
        if queue_graph_notification(db, value):
            accepted += 1
        subscription.last_notification_at = server_now()
    db.commit()
    return {"accepted": accepted}


@router.get("/lifecycle", response_class=PlainTextResponse)
def validate_lifecycle(validation_token: str = Query(alias="validationToken")) -> str:
    return validation_token


@router.post("/lifecycle", status_code=202)
async def receive_lifecycle(request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> dict[str, int]:
    payload = await request.json(); values = payload.get("value", []) if isinstance(payload, dict) else []
    updated = 0
    for value in values if isinstance(values, list) else []:
        if not isinstance(value, dict) or not settings.microsoft_graph_client_state or not secrets.compare_digest(str(value.get("clientState", "")), settings.microsoft_graph_client_state):
            continue
        item = db.scalar(select(OutlookSubscription).where(OutlookSubscription.graph_subscription_id == str(value.get("subscriptionId", ""))))
        if not item:
            continue
        event = str(value.get("lifecycleEvent", "reauthorizationRequired"))
        item.status = "MISSED_EVENTS" if event == "missed" else "REAUTHORIZE_REQUIRED"
        item.last_error = f"Microsoft Graph lifecycle event: {event}."
        updated += 1
    db.commit()
    return {"updated": updated}


@router.post("/sync")
def synchronize_mailbox(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings),
    _: User = Depends(require_permission("configuration.manage")),
) -> dict[str, int]:
    configuration = load_configuration(db)
    subscription = db.scalar(select(OutlookSubscription).where(OutlookSubscription.status == "ACTIVE").order_by(OutlookSubscription.expires_at.desc()))
    mailbox = str(configuration.mailbox_address)
    path: str | None = subscription.delta_link if subscription and subscription.delta_link else f"users/{mailbox}/mailFolders('Inbox')/messages/delta?$select=id,internetMessageId,conversationId,receivedDateTime"
    graph = MicrosoftGraphClient(settings); queued = 0; pages = 0; delta_link: str | None = None
    try:
        while path and pages < 20:
            result = graph.request("GET", path); pages += 1
            for message in result.get("value", []):
                if isinstance(message, dict) and message.get("id") and queue_graph_notification(db, {"subscriptionId": subscription.graph_subscription_id if subscription else "DELTA", "changeType": "delta", "resource": f"users/{mailbox}/messages/{message['id']}", "resourceData": {"id": message["id"]}}):
                    queued += 1
            next_link = result.get("@odata.nextLink"); delta = result.get("@odata.deltaLink")
            path = str(next_link) if next_link else None
            if delta:
                delta_link = str(delta)
    except (GraphConfigurationError, GraphRequestError) as exc:
        if subscription:
            subscription.last_error = str(exc); db.commit()
        raise ConflictError("OUTLOOK_SYNC_FAILED", str(exc)) from exc
    if subscription:
        subscription.delta_link = delta_link or subscription.delta_link
        subscription.last_sync_at = server_now(); subscription.last_error = None
    db.commit()
    return {"queued": queued, "pages": pages}


@router.post("/process-queue")
def process_queue(
    limit: int = Query(default=25, ge=1, le=100), db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: User = Depends(require_permission("configuration.manage")),
) -> dict[str, int]:
    from app.modules.outlook_email.processor import process_notification

    items = list(db.scalars(select(OutlookNotification).where(
        OutlookNotification.status == "PENDING"
    ).order_by(OutlookNotification.received_at).limit(limit)))
    processed = 0; failed = 0
    for item in items:
        item.attempt_count += 1
        try:
            process_notification(db, item, settings)
            processed += 1
        except GraphRequestError as exc:
            item.status = "DEAD_LETTER" if item.attempt_count >= 5 else "PENDING"
            item.last_error = str(exc); item.next_attempt_at = server_now() + timedelta(minutes=min(2 ** item.attempt_count, 60))
            db.commit(); failed += 1
    return {"processed": processed, "failed": failed}


@router.get("/messages")
def list_processed_messages(
    message_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db),
    _: User = Depends(require_permission("configuration.manage")),
) -> list[dict[str, object]]:
    statement = select(OutlookMessage)
    if message_status:
        statement = statement.where(OutlookMessage.status == message_status)
    return [{
        "id": item.id, "sender_address": item.sender_address,
        "subject": item.normalized_subject, "status": item.status,
        "client_id": item.client_id, "contact_id": item.contact_id,
        "ticket_id": item.ticket_id, "comment_id": item.comment_id,
        "last_error": item.last_error, "received_at": item.received_at,
    } for item in db.scalars(statement.order_by(OutlookMessage.received_at.desc()).limit(limit))]


@router.post("/process-outbound")
def process_outbound_queue(
    limit: int = Query(default=25, ge=1, le=100), db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: User = Depends(require_permission("configuration.manage")),
) -> dict[str, int]:
    from app.modules.outlook_email.outbound import process_outbound
    return process_outbound(db, settings, limit)


@router.get("/outbound")
def list_outbound(
    limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db),
    _: User = Depends(require_permission("configuration.manage")),
) -> list[dict[str, object]]:
    return [{column.name: getattr(item, column.name) for column in OutlookOutboundDelivery.__table__.columns} for item in db.scalars(select(OutlookOutboundDelivery).order_by(OutlookOutboundDelivery.created_at.desc()).limit(limit))]


@router.post("/outbound/{delivery_id}/replay")
def replay_outbound(
    delivery_id: int, db: Session = Depends(get_db),
    _: User = Depends(require_permission("configuration.manage")),
) -> dict[str, object]:
    item = db.get(OutlookOutboundDelivery, delivery_id)
    if not item:
        raise ConflictError("OUTLOOK_DELIVERY_NOT_FOUND", "The outbound delivery does not exist.")
    item.status = "PENDING"; item.next_attempt_at = None; item.last_error = None; db.commit()
    return {"id": item.id, "status": item.status}
