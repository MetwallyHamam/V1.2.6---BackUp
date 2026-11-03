"""Personal UAT test filters."""

import json
from typing import Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.iam.models import User
from app.modules.uat.models import UatSavedView

router = APIRouter(prefix="/uat", tags=["uat saved views"])


class ViewFilters(BaseModel):
    search: str = Field(default="", max_length=200)
    status: Literal["ALL", "READY", "IN_PROGRESS", "NEEDS_INVESTIGATION", "WAITING_FIX", "READY_FOR_RETEST", "COMPLETED", "BLOCKED", "FAILED", "OVERDUE"] = "ALL"
    my_tests: bool = False
    result: Literal["ALL", "PASS", "FAIL", "BLOCKED", "NOT_TESTED"] = "ALL"
    priority: Literal["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"] = "ALL"
    due: Literal["ALL", "OVERDUE", "TODAY", "NO_DUE_DATE"] = "ALL"
    product_id: int | None = None
    module_id: int | None = None
    sort: Literal["template_order", "code", "title", "priority", "status", "due_date"] = "template_order"
    direction: Literal["asc", "desc"] = "asc"


class SaveViewInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    filters: ViewFilters


def _read(row: UatSavedView) -> dict[str, object]:
    return {"id": row.id, "name": row.name, "filters": json.loads(row.filters_json), "created_at": row.created_at}


@router.get("/saved-views")
def list_uat_views(db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.view"))) -> list[dict[str, object]]:
    return [_read(row) for row in db.scalars(select(UatSavedView).where(UatSavedView.user_id == actor.id).order_by(UatSavedView.name))]


@router.post("/saved-views", status_code=status.HTTP_201_CREATED)
def save_uat_view(data: SaveViewInput, db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.view"))) -> dict[str, object]:
    name = data.name.strip()
    if not name:
        raise ConflictError("UAT_VIEW_NAME_REQUIRED", "Choose a view name.")
    row = UatSavedView(user_id=actor.id, name=name, filters_json=data.filters.model_dump_json(), created_at=server_now())
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("UAT_VIEW_EXISTS", "You already have a UAT view with this name.") from exc
    return _read(row)


@router.delete("/saved-views/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_uat_view(view_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.view"))) -> None:
    row = db.get(UatSavedView, view_id)
    if not row or row.user_id != actor.id:
        raise NotFoundError("UAT saved view does not exist.")
    db.delete(row)
    db.commit()
