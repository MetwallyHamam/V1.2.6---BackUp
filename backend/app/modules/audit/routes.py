from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_timezone
from app.db.session import get_db
from app.modules.iam.models import AuditLog, User

router = APIRouter(prefix="/audit-logs", tags=["audit"])


class AuditLogRead(BaseModel):
    id: int
    actor_user_id: int | None
    actor_name: str
    entity_type: str
    entity_id: str
    action: str
    reason: str | None
    correlation_id: str | None
    old_values_json: str | None
    new_values_json: str | None
    created_at: datetime


@router.get("", response_model=list[AuditLogRead])
def audit_logs(
    search: str | None = Query(default=None, max_length=100),
    entity_type: str | None = Query(default=None, max_length=100),
    action: str | None = Query(default=None, max_length=100),
    actor_user_id: int | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("audit.view")),
) -> list[dict[str, object]]:
    statement = select(AuditLog, User).outerjoin(User, User.id == AuditLog.actor_user_id)
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                AuditLog.entity_id.like(term),
                AuditLog.action.like(term),
                AuditLog.reason.like(term),
                User.full_name.like(term),
            )
        )
    if entity_type:
        statement = statement.where(AuditLog.entity_type == entity_type)
    if action:
        statement = statement.where(AuditLog.action == action)
    if actor_user_id:
        statement = statement.where(AuditLog.actor_user_id == actor_user_id)
    if created_from:
        statement = statement.where(
            AuditLog.created_at >= datetime.combine(created_from, time.min, tzinfo=server_timezone())
        )
    if created_to:
        statement = statement.where(
            AuditLog.created_at
            < datetime.combine(created_to + timedelta(days=1), time.min, tzinfo=server_timezone())
        )
    rows = db.execute(
        statement.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    )
    return [
        {
            "id": item.id,
            "actor_user_id": item.actor_user_id,
            "actor_name": actor.full_name if actor else "System",
            "entity_type": item.entity_type,
            "entity_id": item.entity_id,
            "action": item.action,
            "reason": item.reason,
            "correlation_id": item.correlation_id,
            "old_values_json": item.old_values_json,
            "new_values_json": item.new_values_json,
            "created_at": item.created_at,
        }
        for item, actor in rows
    ]
