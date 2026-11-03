import json
from datetime import datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.iam.models import AuditLog, User
from app.modules.tickets.models import (
    Ticket,
    TicketAttachment,
    TicketComment,
    TicketStatus,
    TicketStatusHistory,
)


def actor_name(db: Session, user_id: int | None) -> str | None:
    user = db.get(User, user_id) if user_id else None
    return user.full_name if user else None


def safe_audit_description(item: AuditLog) -> str | None:
    if item.reason:
        return item.reason
    values = item.new_values_json or item.old_values_json
    if not values:
        return None
    try:
        parsed = json.loads(values)
    except (json.JSONDecodeError, TypeError):
        return None
    if "filename" in parsed:
        return str(parsed["filename"])
    if "related_ticket_id" in parsed:
        return f"Related ticket ID {parsed['related_ticket_id']}"
    if "article_id" in parsed:
        return f"Knowledge article ID {parsed['article_id']}"
    return None


def ticket_timeline(
    db: Session, ticket: Ticket, include_internal: bool
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = [
        {
            "id": f"created-{ticket.id}",
            "event_type": "CREATED",
            "title": "Ticket created",
            "description": ticket.subject,
            "actor_name": actor_name(db, ticket.created_by_user_id),
            "is_internal": False,
            "created_at": ticket.created_at,
        }
    ]
    statuses = {item.id: item.name for item in db.scalars(select(TicketStatus))}
    for history in db.scalars(
        select(TicketStatusHistory)
        .where(TicketStatusHistory.ticket_id == ticket.id)
        .order_by(TicketStatusHistory.created_at)
    ):
        events.append(
            {
                "id": f"status-{history.id}",
                "event_type": "STATUS_CHANGED",
                "title": (
                    f"Status changed: {statuses.get(history.from_status_id, 'Unknown') if history.from_status_id is not None else 'Unknown'}"
                    f" → {statuses.get(history.to_status_id, 'Unknown')}"
                ),
                "description": history.reason,
                "actor_name": actor_name(db, history.changed_by_user_id),
                "is_internal": False,
                "created_at": history.created_at,
            }
        )
    for comment in db.scalars(
        select(TicketComment)
        .where(TicketComment.ticket_id == ticket.id)
        .order_by(TicketComment.created_at)
    ):
        if comment.is_internal and not include_internal:
            continue
        events.append(
            {
                "id": f"comment-{comment.id}",
                "event_type": "INTERNAL_NOTE" if comment.is_internal else "COMMENT",
                "title": "Internal note" if comment.is_internal else "Public reply",
                "description": comment.body,
                "actor_name": actor_name(db, comment.author_user_id),
                "is_internal": comment.is_internal,
                "created_at": comment.created_at,
            }
        )
    for attachment in db.scalars(
        select(TicketAttachment)
        .where(TicketAttachment.ticket_id == ticket.id)
        .order_by(TicketAttachment.created_at)
    ):
        events.append(
            {
                "id": f"attachment-{attachment.id}",
                "event_type": "ATTACHMENT",
                "title": "Attachment uploaded",
                "description": attachment.original_filename,
                "actor_name": actor_name(db, attachment.uploaded_by_user_id),
                "is_internal": False,
                "created_at": attachment.created_at,
            }
        )
    if include_internal:
        excluded_actions = {
            "ticket.comment.internal",
            "ticket.comment.public",
            "ticket.attachment.uploaded",
        }
        for audit in db.scalars(
            select(AuditLog)
            .where(
                AuditLog.entity_id == str(ticket.id),
                AuditLog.action.like("ticket.%"),
            )
            .order_by(AuditLog.created_at)
        ):
            if audit.action in excluded_actions:
                continue
            events.append(
                {
                    "id": f"audit-{audit.id}",
                    "event_type": "AUDIT",
                    "title": audit.action.replace("ticket.", "").replace(".", " ").title(),
                    "description": safe_audit_description(audit),
                    "actor_name": actor_name(db, audit.actor_user_id),
                    "is_internal": True,
                    "created_at": audit.created_at,
                }
            )
    events.sort(key=lambda event: cast(datetime, event["created_at"]), reverse=True)
    return events[:200]
