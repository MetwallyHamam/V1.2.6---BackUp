import re
from collections.abc import Sequence
from difflib import SequenceMatcher
from typing import Any, Protocol, cast

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, require_permission
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import Client, ClientStatus, Product, ProductModule
from app.modules.configuration.models import SiteSetting
from app.modules.iam.models import User
from app.modules.local_ai.retrieval import similar_resolved_tickets
from app.modules.local_ai.schemas import (
    IntakeAssistRequest,
    IntakeAssistResult,
    ResolutionAssistRequest,
    ResolutionAssistResult,
)
from app.modules.tickets.models import RootCause, Ticket, TicketComment, TicketType, TicketWorklog
from app.modules.tickets.service import ensure_ticket_access

router = APIRouter(prefix="/tickets/ai", tags=["ticket local AI"])


def _key(value: str | None) -> str:
    return "".join(character for character in (value or "").casefold() if character.isalnum())


class NamedCatalog(Protocol):
    id: int
    name: str
    code: str


def _match[CatalogT: NamedCatalog](
    value: str | None, rows: Sequence[CatalogT]
) -> CatalogT | None:
    wanted = _key(value)
    if not wanted:
        return None
    for row in rows:
        if wanted in {_key(getattr(row, "name", "")), _key(getattr(row, "code", ""))}:
            return row
    return None


def _client_candidates(text: str, clients: Sequence[Client], selected: Client | None) -> list[Client]:
    """Keep the 3B prompt small while retaining explicit and plausible client matches."""
    normalized = " ".join(text.casefold().split())
    tokens = {token for token in re.findall(r"[^\W_]+", normalized) if len(token) >= 2}

    def score(item: Client) -> tuple[float, str]:
        name = " ".join(item.name.casefold().split())
        code = item.code.casefold().strip()
        exact = 10.0 if (name and name in normalized) or (code and code in tokens) else 0.0
        item_tokens = {
            token for token in re.findall(r"[^\W_]+", f"{name} {code}") if len(token) >= 2
        }
        overlap = len(tokens & item_tokens) / max(len(item_tokens), 1)
        similarity = SequenceMatcher(None, normalized[:300], name).ratio()
        selected_bonus = 20.0 if selected and item.id == selected.id else 0.0
        return selected_bonus + exact + overlap + similarity, item.name.casefold()

    ranked = sorted(clients, key=score, reverse=True)
    return ranked[:20]


def _match_client(value: str | None, rows: Sequence[Client]) -> Client | None:
    wanted = _key(value)
    if not wanted:
        return None
    for row in rows:
        if wanted in {
            _key(row.name),
            _key(row.code),
            _key(f"{row.code} — {row.name}"),
        }:
            return row
    return None


def _fallback_title(description: str) -> str:
    compact = " ".join(description.split())
    first_sentence = re.split(r"(?<=[.!?])\s+", compact, maxsplit=1)[0]
    return first_sentence[:160].rstrip(" .")


async def _post(
    settings: Settings,
    db: Session,
    path: str,
    payload: dict[str, object],
) -> dict[str, object]:
    if not settings.local_ai_enabled:
        raise ConflictError("LOCAL_AI_DISABLED", "The local AI assistant is disabled.")
    configured = db.get(SiteSetting, "local_ai_base_url")
    base_url = configured.value.strip() if configured and configured.value.strip() else settings.local_ai_base_url
    url = f"{base_url.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=settings.local_ai_timeout_seconds) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return cast(dict[str, Any], response.json())
    except (httpx.HTTPError, ValueError) as exc:
        raise ConflictError(
            "LOCAL_AI_UNAVAILABLE",
            "The local AI assistant is unavailable. Ensure Ollama and the local AI service are running.",
        ) from exc


@router.post("/intake", response_model=IntakeAssistResult)
async def assist_intake(
    data: IntakeAssistRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.create")),
    settings: Settings = Depends(get_settings),
) -> IntakeAssistResult:
    client = db.get(Client, data.client_id) if data.client_id else None
    clients = list(
        db.scalars(
            select(Client)
            .join(ClientStatus, ClientStatus.id == Client.status_id)
            .where(
                Client.is_active.in_([True]),
                ClientStatus.is_active.in_([True]),
                ClientStatus.ticket_creation_allowed.in_([True]),
            )
            .order_by(Client.name)
        )
    )
    client_candidates = _client_candidates(data.description, clients, client)
    products = list(db.scalars(select(Product).where(Product.is_active.in_([True])).order_by(Product.name)))
    modules = list(db.scalars(select(ProductModule).where(ProductModule.is_active.in_([True])).order_by(ProductModule.name)))
    ticket_types = list(db.scalars(select(TicketType).where(TicketType.is_active.in_([True])).order_by(TicketType.name)))
    examples = similar_resolved_tickets(
        db, client_id=data.client_id, text=data.description, limit=3
    ) if data.client_id else []
    instruction_setting = db.get(SiteSetting, "local_ai_intake_instructions")
    result = await _post(settings, db, "/api/ai/tickets/intake", {
        "client_id": data.client_id,
        "client_name": client.name if client else None,
        "source": data.source,
        "description": data.description,
        "custom_instructions": instruction_setting.value if instruction_setting else "",
        "allowed_clients": [f"{row.code} — {row.name}" for row in client_candidates],
        "allowed_products": [row.name for row in products],
        "allowed_modules": [row.name for row in modules],
        "allowed_ticket_types": [row.name for row in ticket_types],
        "allowed_priorities": ["P1", "P2", "P3", "P4"],
        "similar_resolved_tickets": examples,
    })
    detected_client = _match_client(str(result.get("client", "")), client_candidates)
    if detected_client is None and client is not None:
        detected_client = client
    if not str(result.get("title", "")).strip():
        result["title"] = _fallback_title(data.description)
    if not str(result.get("professional_description", "")).strip():
        result["professional_description"] = data.description.strip()
    unique_actions: list[str] = []
    seen_actions: set[str] = set()
    raw_actions = result.get("suggested_actions", [])
    actions = raw_actions if examples and isinstance(raw_actions, list) else []
    for action in actions:
        action_text = str(action).strip()
        action_key = _key(action_text)
        if action_text and action_key not in seen_actions:
            seen_actions.add(action_key)
            unique_actions.append(action_text)
    result["suggested_actions"] = unique_actions[:3]
    product = _match(str(result.get("product", "")), products)
    eligible_modules = [row for row in modules if not product or row.product_id == product.id]
    module = _match(str(result.get("module", "")), eligible_modules)
    ticket_type = _match(str(result.get("ticket_type", "")), ticket_types)
    return IntakeAssistResult(**result, client_id=getattr(detected_client, "id", None),
                              ticket_type_id=getattr(ticket_type, "id", None),
                              product_id=getattr(product, "id", None),
                              product_module_id=getattr(module, "id", None))


@router.post("/{ticket_id}/resolution", response_model=ResolutionAssistResult)
async def assist_resolution(
    ticket_id: int,
    data: ResolutionAssistRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> ResolutionAssistResult:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, actor, ticket)
    product = db.get(Product, ticket.product_id) if ticket.product_id else None
    module = db.get(ProductModule, ticket.product_module_id) if ticket.product_module_id else None
    comments = list(db.scalars(select(TicketComment).where(TicketComment.ticket_id == ticket.id).order_by(TicketComment.created_at.desc()).limit(20)))
    worklogs = list(db.scalars(select(TicketWorklog).where(TicketWorklog.ticket_id == ticket.id).order_by(TicketWorklog.created_at.desc()).limit(20)))
    root_causes = list(db.scalars(select(RootCause).where(RootCause.is_active.in_([True])).order_by(RootCause.name)))
    notes = [row.body for row in comments if row.is_internal]
    if data.draft_resolution.strip():
        notes.insert(0, data.draft_resolution.strip())
    examples = similar_resolved_tickets(
        db,
        client_id=ticket.client_id,
        text=f"{ticket.subject} {ticket.description}",
        product_id=ticket.product_id,
        product_module_id=ticket.product_module_id,
        exclude_ticket_id=ticket.id,
    )
    result = await _post(settings, db, "/api/ai/tickets/resolution", {
        "ticket_id": ticket.id,
        "title": ticket.subject,
        "description": ticket.description,
        "product": product.name if product else None,
        "module": module.name if module else None,
        "priority": ticket.priority,
        "engineer_notes": notes,
        "actions_performed": [row.notes for row in worklogs if row.notes],
        "relevant_logs": [],
        "similar_resolved_tickets": examples,
        "allowed_root_causes": [row.name for row in root_causes],
    })
    root_cause = _match(str(result.get("suggested_root_cause", "")), root_causes)
    return ResolutionAssistResult(**result, root_cause_id=getattr(root_cause, "id", None))
