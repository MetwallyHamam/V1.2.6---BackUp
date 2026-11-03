import hashlib
import json
import secrets
from datetime import timedelta
from difflib import SequenceMatcher
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now, server_timezone
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
)
from app.db.session import get_db
from app.modules.clients.models import Branch, Client, Product
from app.modules.iam.models import AuditLog, AuthenticationEvent, User, UserClientScope
from app.modules.iam.security import (
    create_integration_access_token,
    decode_integration_access_token,
    verify_login_password,
)
from app.modules.iam.service import effective_permissions, normalize
from app.modules.integrations.vendor_models import ExternalFormSession, IntegrationTransaction
from app.modules.integrations.vendor_schemas import (
    ExternalPreTicketCreate,
    FormSessionCreate,
    IntegrationLogin,
    IntegrationToken,
    PublicFormSubmit,
)
from app.modules.pre_tickets.models import EngineerPreTicket

router = APIRouter(prefix="/integrations", tags=["vendor integrations"])
bearer = HTTPBearer(auto_error=False)

_ARABIC_LATIN = str.maketrans({
    "ا":"a","أ":"a","إ":"a","آ":"a","ب":"b","ت":"t","ث":"s","ج":"g","ح":"h",
    "خ":"kh","د":"d","ذ":"z","ر":"r","ز":"z","س":"s","ش":"sh","ص":"s","ض":"d",
    "ط":"t","ظ":"z","ع":"","غ":"gh","ف":"f","ق":"k","ك":"k","ل":"l","م":"m",
    "ن":"n","ه":"h","ة":"a","و":"o","ي":"i","ى":"a","ئ":"i","ؤ":"o",
})


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _phonetic_tokens(value: str) -> set[str]:
    transliterated = value.casefold().translate(_ARABIC_LATIN).replace("ch", "k").replace("ph", "f")
    raw_tokens = ["".join(character for character in token if character.isalnum())
                  for token in transliterated.replace("-", " ").split()]
    return {"".join(character for character in token if character not in "aeiou")
            for token in raw_tokens if len(token) >= 2}


def _nearest_client(value: str, clients: list[Client]) -> Client | None:
    wanted = _phonetic_tokens(value)
    if not wanted:
        return None
    ranked: list[tuple[float, Client]] = []
    for client in clients:
        candidate_tokens = _phonetic_tokens(f"{client.code} {client.name}")
        score = max((SequenceMatcher(None, left, right).ratio()
                     for left in wanted for right in candidate_tokens), default=0.0)
        ranked.append((score, client))
    ranked.sort(key=lambda item: item[0], reverse=True)
    if not ranked or ranked[0][0] < 0.82:
        return None
    if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < 0.12:
        return None
    return ranked[0][1]


def _api_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    if not credentials:
        raise AuthenticationError("AUTHENTICATION_REQUIRED", "Integration authentication is required.")
    user = db.get(User, decode_integration_access_token(credentials.credentials, settings))
    if not user or not user.is_active or user.user_type != "API_USER":
        raise AuthenticationError("ACCOUNT_INACTIVE", "The API account is inactive or invalid.")
    return user


def _authorize_client(db: Session, actor: User, client_id: int | None, branch_id: int | None) -> None:
    if client_id is None:
        if branch_id is not None:
            raise ConflictError("CLIENT_REQUIRED_FOR_BRANCH", "A branch cannot be selected without a client.")
        return
    scopes = set(db.scalars(select(UserClientScope.client_id).where(UserClientScope.user_id == actor.id)))
    if scopes and client_id not in scopes:
        raise AuthorizationError("This API user is not authorized for the requested client.")
    client = db.get(Client, client_id)
    if not client or not client.is_active:
        raise NotFoundError("Client does not exist or is inactive.")
    if branch_id is not None:
        branch = db.get(Branch, branch_id)
        if not branch or not branch.is_active or branch.client_id != client_id:
            raise ConflictError("INVALID_BRANCH", "The optional branch does not belong to the client.")


def _create_pre_ticket(
    db: Session,
    actor: User,
    data: ExternalPreTicketCreate,
    idempotency_key: str,
) -> tuple[EngineerPreTicket, str, bool]:
    client_id = data.client_id
    if client_id is None:
        scopes = set(db.scalars(select(UserClientScope.client_id).where(UserClientScope.user_id == actor.id)))
        candidates = list(db.scalars(select(Client).where(Client.is_active.in_([True]))))
        if scopes:
            candidates = [candidate for candidate in candidates if candidate.id in scopes]
        supplied_name = (data.client_name or "").strip()
        normalized = normalize(supplied_name)
        exact = [candidate for candidate in candidates
                 if normalize(candidate.code) == normalized or normalize(candidate.name) == normalized]
        matched = exact[0] if len(exact) == 1 else _nearest_client(supplied_name or data.description, candidates)
        client_id = matched.id if matched else None
    _authorize_client(db, actor, client_id, data.branch_id)
    if data.product_id is not None:
        product = db.get(Product, data.product_id)
        if not product or not product.is_active:
            raise NotFoundError("Product does not exist or is inactive.")
    canonical = data.model_dump(mode="json")
    fingerprint = _hash(json.dumps(canonical, sort_keys=True))
    previous = db.scalar(select(IntegrationTransaction).where(
        IntegrationTransaction.api_user_id == actor.id,
        IntegrationTransaction.idempotency_key == idempotency_key,
    ))
    if previous:
        if previous.request_fingerprint != fingerprint:
            raise ConflictError("IDEMPOTENCY_CONFLICT", "This Idempotency-Key was already used with different data.")
        item = db.get(EngineerPreTicket, previous.pre_ticket_id)
        if not item:
            raise ConflictError("TRANSACTION_INCOMPLETE", "The previous transaction could not be recovered.")
        return item, previous.transaction_token, False
    item = EngineerPreTicket(
        pre_ticket_number=f"PENDING-{uuid4().hex}",
        client_id=client_id,
        branch_id=data.branch_id,
        product_id=data.product_id,
        proposed_priority=data.priority,
        title=" ".join(data.subject.split()),
        initial_description=data.description.strip(),
        submitted_by_user_id=actor.id,
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
        source_provider=data.source,
        external_event_id=data.external_reference,
        external_caller_name=data.requester_name,
        external_caller_number=data.requester_phone,
    )
    db.add(item)
    db.flush()
    item.pre_ticket_number = f"PRE-{item.id:06d}"
    transaction_token = secrets.token_urlsafe(24)
    db.add(IntegrationTransaction(
        api_user_id=actor.id,
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
        transaction_token=transaction_token,
        pre_ticket_id=item.id,
        source=data.source,
        request_json=json.dumps(canonical),
    ))
    db.add(AuditLog(
        actor_user_id=actor.id,
        entity_type="EngineerPreTicket",
        entity_id=str(item.id),
        action="integration.pre_ticket.created",
        new_values_json=json.dumps({"source": data.source, "external_reference": data.external_reference}),
    ))
    db.commit()
    db.refresh(item)
    return item, transaction_token, True


@router.post("/auth/token", response_model=IntegrationToken)
def integration_token(
    data: IntegrationLogin,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> IntegrationToken:
    user = db.scalar(select(User).where(or_(
        User.username_normalized == normalize(data.username),
        User.email_normalized == normalize(data.username),
    )))
    ip = request.client.host if request.client else None
    now = server_now()
    if user and user.locked_until and user.locked_until.replace(tzinfo=server_timezone()) > now:
        raise AuthenticationError("ACCOUNT_LOCKED", "The API account is temporarily locked.")
    if not user or user.user_type != "API_USER" or not user.is_active or not verify_login_password(data.password, user.password_hash, settings):
        if user:
            user.failed_login_count += 1
            if user.failed_login_count >= settings.login_max_failures:
                user.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
        db.add(AuthenticationEvent(user_id=user.id if user else None, username_attempted=data.username, event_type="INTEGRATION_LOGIN_FAILED", ip_address=ip))
        db.commit()
        raise AuthenticationError()
    if "integration.pre_ticket.create" not in effective_permissions(db, user).permissions:
        raise AuthorizationError("The API profile does not allow Pre-Ticket creation.")
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    db.add(AuthenticationEvent(user_id=user.id, event_type="INTEGRATION_LOGIN_SUCCEEDED", ip_address=ip))
    db.commit()
    return IntegrationToken(
        access_token=create_integration_access_token(user.id, settings),
        expires_in=settings.access_token_minutes * 60,
    )


@router.get("/api-users/{user_id}/documentation", response_class=PlainTextResponse)
def api_user_documentation(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("configuration.manage")),
) -> str:
    user = db.get(User, user_id)
    if not user or user.user_type != "API_USER":
        raise NotFoundError("API user does not exist.")
    client_ids = list(db.scalars(select(UserClientScope.client_id).where(UserClientScope.user_id == user.id)))
    clients = list(db.scalars(select(Client).where(Client.id.in_(client_ids)).order_by(Client.name))) if client_ids else []
    base_url = str(request.base_url).rstrip("/")
    scope_text = ", ".join(f"{item.code} ({item.name})" for item in clients) or "Unrestricted intake; client may be omitted for manual matching"
    return f"""# SupportHub Vendor API — {user.full_name}

Base URL: `{base_url}/api/v1`
Username: `{user.username}`
Password: supplied separately and never included in regenerated documentation.
Client scope: {scope_text}

## Authenticate
`POST /integrations/auth/token`

```json
{{"username":"{user.username}","password":"YOUR_PASSWORD"}}
```

Use the returned token as `Authorization: Bearer ACCESS_TOKEN`.

## Create an automated Pre-Ticket
`POST /integrations/pre-tickets`

Required headers: `Authorization`, `Content-Type: application/json`, and a unique `Idempotency-Key`.

```json
{{"client_name":"Techno Scan","subject":"PACS images are not transferring","description":"Images are not transferring from the local server to the central server.","priority":"P3","source":"WHATSAPP"}}
```

`client_id`, `client_name`, and `branch_id` are optional for WhatsApp/email intake. An unmatched request is created for manual review. Branch is always optional.

## Create a hosted form link
`POST /integrations/form-sessions`

Hosted forms require `client_id`. The returned URL is single-use and expires after 15 minutes.

## Transaction status
`GET /integrations/transactions/{{transaction_token}}`

Access tokens expire after a short period. Authenticate again when a token expires. Use HTTPS in production.
"""


@router.post("/pre-tickets", status_code=status.HTTP_201_CREATED)
def create_external_pre_ticket(
    data: ExternalPreTicketCreate,
    idempotency_key: str = Header(min_length=8, max_length=200, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    actor: User = Depends(_api_user),
) -> dict[str, object]:
    item, token, created = _create_pre_ticket(db, actor, data, idempotency_key)
    return {"pre_ticket_id": item.id, "pre_ticket_number": item.pre_ticket_number,
            "status": item.status, "transaction_token": token, "created": created,
            "client_id": item.client_id,
            "client_match": "MATCHED" if item.client_id else "REVIEW_REQUIRED"}


@router.get("/transactions/{transaction_token}")
def transaction_status(transaction_token: str, db: Session = Depends(get_db), actor: User = Depends(_api_user)) -> dict[str, object]:
    transaction = db.scalar(select(IntegrationTransaction).where(
        IntegrationTransaction.transaction_token == transaction_token,
        IntegrationTransaction.api_user_id == actor.id,
    ))
    if not transaction:
        raise NotFoundError("Integration transaction does not exist.")
    item = db.get(EngineerPreTicket, transaction.pre_ticket_id)
    return {"transaction_token": transaction.transaction_token, "pre_ticket_id": transaction.pre_ticket_id,
            "pre_ticket_number": item.pre_ticket_number if item else None, "status": item.status if item else "UNKNOWN"}


@router.post("/form-sessions", status_code=status.HTTP_201_CREATED)
def create_form_session(
    data: FormSessionCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(_api_user),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    _authorize_client(db, actor, data.client_id, data.branch_id)
    raw_token = secrets.token_urlsafe(32)
    db.add(ExternalFormSession(
        token_hash=_hash(raw_token), api_user_id=actor.id, expires_at=server_now() + timedelta(minutes=15),
        **data.model_dump(mode="json"),
    ))
    db.commit()
    return {"form_url": f"{settings.frontend_base_url}/external/pre-ticket/{raw_token}", "expires_in": 900}


def _form_session(db: Session, token: str) -> ExternalFormSession:
    session = db.scalar(select(ExternalFormSession).where(ExternalFormSession.token_hash == _hash(token)))
    if not session or session.expires_at.replace(tzinfo=server_now().tzinfo) <= server_now():
        raise NotFoundError("This form link is invalid or expired.")
    if session.used_at is not None:
        raise ConflictError("FORM_ALREADY_USED", "This form link has already been submitted.")
    return session


@router.get("/public/forms/{token}")
def public_form(token: str, db: Session = Depends(get_db)) -> dict[str, object]:
    session = _form_session(db, token)
    client = db.get(Client, session.client_id)
    product = db.get(Product, session.product_id) if session.product_id else None
    branch = db.get(Branch, session.branch_id) if session.branch_id else None
    return {"client_name": client.name if client else "", "branch_name": branch.name if branch else None,
            "product_name": product.name if product else None, "requester_name": session.requester_name,
            "requester_email": session.requester_email, "requester_phone": session.requester_phone,
            "external_reference": session.external_reference}


@router.post("/public/forms/{token}", status_code=status.HTTP_201_CREATED)
def submit_public_form(token: str, data: PublicFormSubmit, db: Session = Depends(get_db)) -> dict[str, object]:
    session = _form_session(db, token)
    actor = db.get(User, session.api_user_id)
    if not actor or not actor.is_active:
        raise AuthenticationError("ACCOUNT_INACTIVE", "The integration account is inactive.")
    payload = ExternalPreTicketCreate(
        client_id=session.client_id, branch_id=session.branch_id, product_id=session.product_id,
        requester_name=data.requester_name or session.requester_name,
        requester_email=data.requester_email or session.requester_email,
        requester_phone=data.requester_phone or session.requester_phone,
        subject=data.subject, description=data.description, priority=data.priority,
        source="EXTERNAL_FORM", external_reference=session.external_reference,
    )
    item, transaction_token, _ = _create_pre_ticket(db, actor, payload, f"form:{session.id}")
    session.used_at = server_now()
    db.commit()
    return {"pre_ticket_id": item.id, "pre_ticket_number": item.pre_ticket_number,
            "status": item.status, "transaction_token": transaction_token, "return_url": session.return_url}
