import math
import re
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.tickets.models import Ticket

TOKEN_PATTERN = re.compile(r"[\w-]{2,}", re.UNICODE)
STOP_WORDS = {
    "and", "are", "for", "from", "has", "have", "the", "this", "that", "was", "were",
    "with", "issue", "ticket", "client", "تم", "في", "من", "على", "الى", "إلى", "هذا", "هذه",
}


def _tokens(value: str) -> Counter[str]:
    return Counter(
        token for token in TOKEN_PATTERN.findall(value.casefold())
        if token not in STOP_WORDS and not token.isdigit()
    )


def _score(query: Counter[str], text: str) -> float:
    candidate = _tokens(text)
    if not query or not candidate:
        return 0.0
    overlap = query.keys() & candidate.keys()
    if not overlap:
        return 0.0
    weighted = sum(1.0 + math.log1p(min(query[token], candidate[token])) for token in overlap)
    return weighted / math.sqrt(max(1, len(candidate)))


def similar_resolved_tickets(
    db: Session,
    *,
    client_id: int,
    text: str,
    product_id: int | None = None,
    product_module_id: int | None = None,
    exclude_ticket_id: int | None = None,
    limit: int = 5,
) -> list[str]:
    """Return client-scoped, evidence-bearing examples without building a separate data copy."""
    statement = (
        select(Ticket.id, Ticket.subject, Ticket.description, Ticket.resolution_summary)
        .where(
            Ticket.client_id == client_id,
            Ticket.resolution_summary.is_not(None),
            Ticket.archived_at.is_(None),
        )
        .order_by(Ticket.updated_at.desc())
        .limit(500)
    )
    if product_module_id:
        statement = statement.where(Ticket.product_module_id == product_module_id)
    elif product_id:
        statement = statement.where(Ticket.product_id == product_id)
    if exclude_ticket_id:
        statement = statement.where(Ticket.id != exclude_ticket_id)

    query = _tokens(text)
    ranked: list[tuple[float, int, str, str]] = []
    for ticket_id, subject, description, resolution_summary in db.execute(statement):
        score = _score(query, f"{subject} {description}")
        if score > 0:
            ranked.append((score, ticket_id, subject, resolution_summary))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [
        f"Previous issue: {subject}\nVerified resolution: {resolution_summary}"
        for _, _, subject, resolution_summary in ranked[:limit]
    ]
