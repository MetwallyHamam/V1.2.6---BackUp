"""Expiring, revocable read-only UAT progress links."""

import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now, server_timezone
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.modules.iam.models import AuditLog, User
from app.modules.uat.models import UatCycle, UatCycleTest, UatShareLink

internal_router = APIRouter(prefix="/uat", tags=["uat sharing"])
public_router = APIRouter(prefix="/public/uat-shares", tags=["public uat tracking"])


class CreateShareInput(BaseModel):
    expires_in_hours: int = Field(default=72, ge=1, le=720)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=server_timezone())


def _read(row: UatShareLink) -> dict[str, object]:
    return {"id": row.id, "created_at": row.created_at, "expires_at": row.expires_at,
            "revoked_at": row.revoked_at, "created_by_user_id": row.created_by_user_id}


@internal_router.get("/cycles/{cycle_id}/share-links")
def list_share_links(cycle_id: int, db: Session = Depends(get_db), _actor: User = Depends(require_permission("uat.cycle.manage"))) -> list[dict[str, object]]:
    if not db.get(UatCycle, cycle_id):
        raise NotFoundError("UAT cycle does not exist.")
    return [_read(row) for row in db.scalars(select(UatShareLink).where(UatShareLink.cycle_id == cycle_id).order_by(UatShareLink.id.desc()))]


@internal_router.post("/cycles/{cycle_id}/share-links", status_code=status.HTTP_201_CREATED)
def create_share_link(cycle_id: int, data: CreateShareInput, db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.cycle.manage"))) -> dict[str, object]:
    cycle = db.get(UatCycle, cycle_id)
    if not cycle:
        raise NotFoundError("UAT cycle does not exist.")
    token = secrets.token_urlsafe(32)
    now = server_now()
    row = UatShareLink(cycle_id=cycle.id, token_hash=hashlib.sha256(token.encode()).hexdigest(),
                       created_by_user_id=actor.id, created_at=now,
                       expires_at=now + timedelta(hours=data.expires_in_hours))
    db.add(row)
    db.flush()
    db.add(AuditLog(actor_user_id=actor.id, entity_type="UatShareLink", entity_id=str(row.id), action="uat.share_link.created"))
    db.commit()
    return {**_read(row), "token": token}


@internal_router.post("/cycles/{cycle_id}/share-links/{link_id}/revoke")
def revoke_share_link(cycle_id: int, link_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.cycle.manage"))) -> dict[str, object]:
    row = db.get(UatShareLink, link_id)
    if not row or row.cycle_id != cycle_id:
        raise NotFoundError("UAT share link does not exist.")
    if row.revoked_at is None:
        row.revoked_at = server_now()
        db.add(AuditLog(actor_user_id=actor.id, entity_type="UatShareLink", entity_id=str(row.id), action="uat.share_link.revoked"))
        db.commit()
    return _read(row)


@public_router.get("/{token}")
def public_tracking(token: str, response: Response, db: Session = Depends(get_db)) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    if len(token) < 40 or len(token) > 100:
        raise NotFoundError("UAT tracking link does not exist.")
    digest = hashlib.sha256(token.encode()).hexdigest()
    row = db.scalar(select(UatShareLink).where(UatShareLink.token_hash == digest))
    if not row or row.revoked_at or _aware(row.expires_at) <= server_now():
        raise NotFoundError("UAT tracking link does not exist.")
    cycle = db.get(UatCycle, row.cycle_id)
    if not cycle:
        raise NotFoundError("UAT tracking link does not exist.")
    tests = list(db.scalars(select(UatCycleTest).where(UatCycleTest.cycle_id == cycle.id)))
    total = len(tests)
    passed = sum(test.test_result == "PASS" for test in tests)
    client_tests = [test for test in tests if test.client_tester_user_id]
    return {"code": cycle.code, "title": cycle.title, "release_version": cycle.release_version,
            "status": cycle.status, "due_date": cycle.due_date, "expires_at": row.expires_at,
            "total": total, "passed": passed,
            "failed": sum(test.test_result == "FAIL" for test in tests),
            "blocked": sum(test.test_result == "BLOCKED" for test in tests),
            "completion_percent": round(sum(test.test_result in {"PASS", "FAIL"} for test in tests) * 100 / total, 1) if total else 0,
            "client_total": len(client_tests),
            "client_passed": sum(test.client_test_result == "PASS" for test in client_tests)}
