"""Comments and evidence shared by internal and client UAT participants."""

import json
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, require_permission
from app.core.clock import server_now
from app.core.config import Settings, get_settings
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.iam.models import AuditLog, User
from app.modules.iam.service import effective_permissions
from app.modules.tickets.models import Ticket
from app.modules.tickets.service import ensure_ticket_access
from app.modules.uat.evidence import store_uat_evidence, uat_evidence_path
from app.modules.uat.models import UatComment, UatCycle, UatCycleTest, UatEvidence, UatTestAttempt
from app.modules.uat.portal_routes import _assigned_test

internal_router = APIRouter(prefix="/uat", tags=["uat collaboration"])
portal_router = APIRouter(prefix="/portal/uat", tags=["client portal uat collaboration"])
ticket_router = APIRouter(prefix="/tickets", tags=["ticket uat evidence"])


class CommentInput(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    visibility: Literal["INTERNAL_ONLY", "CLIENT_VISIBLE"] = "INTERNAL_ONLY"


class PortalCommentInput(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


def _test_and_cycle(db: Session, test_id: int) -> tuple[UatCycleTest, UatCycle]:
    test = db.get(UatCycleTest, test_id)
    cycle = db.get(UatCycle, test.cycle_id) if test else None
    if not test or not cycle:
        raise NotFoundError("UAT test does not exist.")
    return test, cycle


def _internal_writer(db: Session, actor: User, test: UatCycleTest) -> None:
    if test.owner_user_id != actor.id and "uat.cycle.manage" not in effective_permissions(db, actor).permissions:
        raise AuthorizationError("Only the assigned tester or UAT manager can add UAT material.")


def _comment_read(row: UatComment) -> dict[str, object]:
    return {"id": row.id, "cycle_test_id": row.cycle_test_id, "author_user_id": row.author_user_id,
            "visibility": row.visibility, "body": row.body, "created_at": row.created_at}


def _evidence_read(row: UatEvidence) -> dict[str, object]:
    return {"id": row.id, "attempt_id": row.attempt_id, "uploaded_by_user_id": row.uploaded_by_user_id,
            "visibility": row.visibility, "original_filename": row.original_filename,
            "content_type": row.content_type, "size_bytes": row.size_bytes, "created_at": row.created_at}


@internal_router.get("/cycle-tests/{test_id}/comments")
def list_internal_comments(test_id: int, db: Session = Depends(get_db), _actor: User = Depends(require_permission("uat.view"))) -> list[dict[str, object]]:
    _test_and_cycle(db, test_id)
    return [_comment_read(row) for row in db.scalars(select(UatComment).where(UatComment.cycle_test_id == test_id).order_by(UatComment.created_at, UatComment.id))]


@internal_router.post("/cycle-tests/{test_id}/comments", status_code=status.HTTP_201_CREATED)
def add_internal_comment(test_id: int, data: CommentInput, db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.test.execute"))) -> dict[str, object]:
    test, cycle = _test_and_cycle(db, test_id)
    _internal_writer(db, actor, test)
    if cycle.status not in {"DRAFT", "ACTIVE"}:
        raise ConflictError("INVALID_UAT_STATE", "Completed cycles cannot receive comments.")
    row = UatComment(cycle_test_id=test.id, author_user_id=actor.id, visibility=data.visibility,
                     body=data.body.strip(), created_at=server_now())
    db.add(row)
    db.flush()
    db.add(AuditLog(actor_user_id=actor.id, entity_type="UatComment", entity_id=str(row.id), action="uat.comment.created"))
    db.commit()
    return _comment_read(row)


@portal_router.get("/tests/{test_id}/comments")
def list_portal_comments(test_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.portal.view"))) -> list[dict[str, object]]:
    _assigned_test(db, actor, test_id)
    return [_comment_read(row) for row in db.scalars(select(UatComment).where(UatComment.cycle_test_id == test_id,
                                                                               UatComment.visibility == "CLIENT_VISIBLE")
                                                       .order_by(UatComment.created_at, UatComment.id))]


@portal_router.post("/tests/{test_id}/comments", status_code=status.HTTP_201_CREATED)
def add_portal_comment(test_id: int, data: PortalCommentInput, db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.portal.comment"))) -> dict[str, object]:
    cycle, test = _assigned_test(db, actor, test_id)
    if cycle.status != "ACTIVE" or not cycle.allow_client_comments:
        raise ConflictError("UAT_CLIENT_COMMENTS_DISABLED", "Client comments are not enabled for this active cycle.")
    row = UatComment(cycle_test_id=test.id, author_user_id=actor.id, visibility="CLIENT_VISIBLE",
                     body=data.body.strip(), created_at=server_now())
    db.add(row)
    db.flush()
    db.add(AuditLog(actor_user_id=actor.id, entity_type="UatComment", entity_id=str(row.id), action="uat.client_comment.created"))
    db.commit()
    return _comment_read(row)


def _attempt_for_test(db: Session, test_id: int, attempt_id: int) -> UatTestAttempt:
    attempt = db.get(UatTestAttempt, attempt_id)
    if not attempt or attempt.cycle_test_id != test_id:
        raise NotFoundError("UAT attempt does not exist.")
    return attempt


@internal_router.get("/cycle-tests/{test_id}/attempts/{attempt_id}/evidence")
def list_internal_evidence(test_id: int, attempt_id: int, db: Session = Depends(get_db), _actor: User = Depends(require_permission("uat.view"))) -> list[dict[str, object]]:
    _test_and_cycle(db, test_id)
    _attempt_for_test(db, test_id, attempt_id)
    return [_evidence_read(row) for row in db.scalars(select(UatEvidence).where(UatEvidence.attempt_id == attempt_id).order_by(UatEvidence.id))]


@portal_router.get("/tests/{test_id}/attempts/{attempt_id}/evidence")
def list_portal_evidence(test_id: int, attempt_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.portal.view"))) -> list[dict[str, object]]:
    _assigned_test(db, actor, test_id)
    _attempt_for_test(db, test_id, attempt_id)
    return [_evidence_read(row) for row in db.scalars(select(UatEvidence).where(UatEvidence.attempt_id == attempt_id,
                                                                               UatEvidence.visibility == "CLIENT_VISIBLE").order_by(UatEvidence.id))]


async def _save_evidence(db: Session, actor: User, attempt: UatTestAttempt, upload: UploadFile,
                         visibility: str, settings: Settings) -> dict[str, object]:
    original, stored, content_type, size, digest = await store_uat_evidence(upload, attempt.id, settings)
    row = UatEvidence(attempt_id=attempt.id, uploaded_by_user_id=actor.id, visibility=visibility,
                      original_filename=original, stored_filename=stored, content_type=content_type,
                      size_bytes=size, sha256=digest, created_at=server_now())
    try:
        db.add(row)
        db.flush()
        db.add(AuditLog(actor_user_id=actor.id, entity_type="UatEvidence", entity_id=str(row.id),
                        action="uat.evidence.uploaded", new_values_json=json.dumps({"attempt_id": attempt.id, "visibility": visibility})))
        db.commit()
    except Exception:
        db.rollback()
        uat_evidence_path(row, settings).unlink(missing_ok=True)
        raise
    return _evidence_read(row)


@internal_router.post("/cycle-tests/{test_id}/attempts/{attempt_id}/evidence", status_code=status.HTTP_201_CREATED)
async def upload_internal_evidence(test_id: int, attempt_id: int, upload: UploadFile = File(...),
                                   visibility: Literal["INTERNAL_ONLY", "CLIENT_VISIBLE"] = Form("INTERNAL_ONLY"),
                                   db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.test.execute")),
                                   settings: Settings = Depends(get_settings)) -> dict[str, object]:
    test, cycle = _test_and_cycle(db, test_id)
    _internal_writer(db, actor, test)
    if cycle.status != "ACTIVE":
        raise ConflictError("INVALID_UAT_STATE", "Evidence can only be uploaded to active cycles.")
    attempt = _attempt_for_test(db, test_id, attempt_id)
    return await _save_evidence(db, actor, attempt, upload, visibility, settings)


@portal_router.post("/tests/{test_id}/attempts/{attempt_id}/evidence", status_code=status.HTTP_201_CREATED)
async def upload_portal_evidence(test_id: int, attempt_id: int, upload: UploadFile = File(...),
                                 db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.portal.evidence")),
                                 settings: Settings = Depends(get_settings)) -> dict[str, object]:
    cycle, _test = _assigned_test(db, actor, test_id)
    if cycle.status != "ACTIVE" or not cycle.allow_client_attachments:
        raise ConflictError("UAT_CLIENT_EVIDENCE_DISABLED", "Client evidence is not enabled for this active cycle.")
    attempt = _attempt_for_test(db, test_id, attempt_id)
    if attempt.execution_source != "CLIENT_PORTAL" or attempt.tested_by_user_id != actor.id:
        raise NotFoundError("UAT attempt does not exist.")
    return await _save_evidence(db, actor, attempt, upload, "CLIENT_VISIBLE", settings)


def _download(db: Session, test_id: int, evidence_id: int, settings: Settings, *, portal: bool) -> FileResponse:
    row = db.get(UatEvidence, evidence_id)
    if not row:
        raise NotFoundError("UAT evidence does not exist.")
    _attempt_for_test(db, test_id, row.attempt_id)
    if portal and row.visibility != "CLIENT_VISIBLE":
        raise NotFoundError("UAT evidence does not exist.")
    return FileResponse(uat_evidence_path(row, settings), media_type=row.content_type, filename=row.original_filename)


@internal_router.get("/cycle-tests/{test_id}/evidence/{evidence_id}/download")
def download_internal_evidence(test_id: int, evidence_id: int, db: Session = Depends(get_db),
                               _actor: User = Depends(require_permission("uat.view")), settings: Settings = Depends(get_settings)) -> FileResponse:
    _test_and_cycle(db, test_id)
    return _download(db, test_id, evidence_id, settings, portal=False)


@portal_router.get("/tests/{test_id}/evidence/{evidence_id}/download")
def download_portal_evidence(test_id: int, evidence_id: int, db: Session = Depends(get_db),
                             actor: User = Depends(require_permission("uat.portal.view")), settings: Settings = Depends(get_settings)) -> FileResponse:
    _assigned_test(db, actor, test_id)
    return _download(db, test_id, evidence_id, settings, portal=True)


def _ticket_evidence(db: Session, actor: User, ticket_id: int) -> list[tuple[UatEvidence, int]]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError("Ticket does not exist.")
    ensure_ticket_access(db, actor, ticket)
    if actor.user_type == "CLIENT_PORTAL":
        raise NotFoundError("UAT evidence does not exist.")
    rows = db.execute(select(UatEvidence, UatCycleTest.id)
                      .join(UatTestAttempt, UatTestAttempt.id == UatEvidence.attempt_id)
                      .join(UatCycleTest, UatCycleTest.id == UatTestAttempt.cycle_test_id)
                      .where(UatCycleTest.linked_ticket_id == ticket_id)
                      .order_by(UatEvidence.id))
    return [(evidence, test_id) for evidence, test_id in rows]


@ticket_router.get("/{ticket_id}/uat-evidence")
def list_ticket_uat_evidence(ticket_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> list[dict[str, object]]:
    return [{**_evidence_read(row), "cycle_test_id": test_id} for row, test_id in _ticket_evidence(db, actor, ticket_id)]


@ticket_router.get("/{ticket_id}/uat-evidence/{evidence_id}/download")
def download_ticket_uat_evidence(ticket_id: int, evidence_id: int, db: Session = Depends(get_db),
                                 actor: User = Depends(current_user), settings: Settings = Depends(get_settings)) -> FileResponse:
    row = next((row for row, _test_id in _ticket_evidence(db, actor, ticket_id) if row.id == evidence_id), None)
    if not row:
        raise NotFoundError("UAT evidence does not exist.")
    return FileResponse(uat_evidence_path(row, settings), media_type=row.content_type, filename=row.original_filename)
