"""Client scoped access to published UAT cycles and client attempts."""

import json
from datetime import datetime
from typing import Literal, cast

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now, server_timezone
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.iam.models import AuditLog, User
from app.modules.iam.service import effective_permissions
from app.modules.notifications.models import Notification
from app.modules.tickets.models import Ticket, TicketStatus, TicketType
from app.modules.tickets.schemas import TicketCreate
from app.modules.tickets.service import create_ticket, ensure_ticket_access
from app.modules.uat.models import (
    UatClientSignoff,
    UatComment,
    UatCycle,
    UatCycleTest,
    UatSignoff,
    UatTestAttempt,
)
from app.modules.uat.service import notify_defect_created

router = APIRouter(prefix="/portal/uat", tags=["client portal uat"])


class ClientAttemptInput(BaseModel):
    result: Literal["PASS", "FAIL", "BLOCKED"]
    actual_result: str = Field(default="", max_length=4000)
    failure_reason: str | None = Field(default=None, max_length=4000)
    blocking_reason: str | None = Field(default=None, max_length=4000)
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None
    comment: str | None = Field(default=None, max_length=4000)


class ClientSignoffInput(BaseModel):
    decision: Literal["APPROVED", "REJECTED", "ADDITIONAL_TESTING"]
    comment: str | None = Field(default=None, max_length=4000)


class ClientDefectInput(BaseModel):
    subject: str = Field(min_length=5, max_length=300)
    description: str = Field(min_length=10, max_length=20000)
    impact: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    urgency: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class ClientWorkflowMoveInput(BaseModel):
    workflow_status: Literal["READY", "IN_PROGRESS"]


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=server_timezone())


def _portal_access(db: Session, actor: User, cycle: UatCycle) -> None:
    if actor.user_type != "CLIENT_PORTAL" or cycle.client_id not in effective_permissions(db, actor).client_scope_ids:
        raise NotFoundError("UAT cycle does not exist.")
    if not cycle.portal_visible or cycle.status not in {"ACTIVE", "COMPLETED"}:
        raise NotFoundError("UAT cycle does not exist.")
    now = server_now()
    if cycle.client_access_start_at and now < _aware(cycle.client_access_start_at):
        raise NotFoundError("UAT cycle does not exist.")
    if cycle.client_access_end_at and now > _aware(cycle.client_access_end_at):
        raise NotFoundError("UAT cycle does not exist.")
    if actor.id not in {cycle.client_approver_user_id, cycle.client_coordinator_user_id} and not db.scalar(select(UatCycleTest.id).where(
        UatCycleTest.cycle_id == cycle.id, UatCycleTest.client_tester_user_id == actor.id)):
        raise NotFoundError("UAT cycle does not exist.")


def _test_read(test: UatCycleTest, linked_ticket: dict[str, object] | None = None, assigned_to_me: bool = True) -> dict[str, object]:
    return {"id": test.id, "snapshot": json.loads(test.snapshot_json),
            "client_test_result": test.client_test_result,
            "client_workflow_status": test.client_workflow_status,
            "client_attempt_count": test.client_attempt_count,
            "client_tested_at": test.client_tested_at, "linked_ticket": linked_ticket,
            "has_linked_ticket": test.linked_ticket_id is not None, "assigned_to_me": assigned_to_me}


def _client_summary(db: Session, cycle: UatCycle) -> dict[str, int | float]:
    tests = list(db.scalars(select(UatCycleTest).where(UatCycleTest.cycle_id == cycle.id,
                                                         UatCycleTest.client_tester_user_id.is_not(None))))
    total = len(tests)
    passed = sum(test.client_test_result == "PASS" for test in tests)
    failed = sum(test.client_test_result == "FAIL" for test in tests)
    blocked = sum(test.client_test_result == "BLOCKED" for test in tests)
    linked_ids = [test.linked_ticket_id for test in tests if test.linked_ticket_id]
    tickets = list(db.scalars(select(Ticket).where(Ticket.id.in_(linked_ids)))) if linked_ids else []
    status_ids = {ticket.status_id for ticket in tickets}
    status_codes = {row.id: row.code for row in db.scalars(select(TicketStatus).where(TicketStatus.id.in_(status_ids)))} if status_ids else {}
    return {"total": total, "passed": passed, "failed": failed, "blocked": blocked,
            "not_tested": total - passed - failed - blocked,
            "completion_percent": round((passed + failed) * 100 / total, 1) if total else 0,
            "pass_rate": round(passed * 100 / (passed + failed), 1) if passed + failed else 0,
            "open_defects": sum(status_codes.get(ticket.status_id) not in {"RESOLVED", "CLOSED", "CANCELLED"} for ticket in tickets),
            "mandatory_outstanding": sum(json.loads(test.snapshot_json).get("is_mandatory", True) and test.client_test_result != "PASS" for test in tests)}


def _signoff_read(row: UatClientSignoff) -> dict[str, object]:
    return {"id": row.id, "decision_number": row.decision_number, "decision": row.decision,
            "decided_by_user_id": row.decided_by_user_id, "decided_at": row.decided_at,
            "comment": row.comment, "summary_snapshot": json.loads(row.summary_snapshot_json)}


def _client_test_states(db: Session, cycle_id: int) -> dict[str, str]:
    return {str(test.id): test.client_test_result for test in db.scalars(select(UatCycleTest).where(
        UatCycleTest.cycle_id == cycle_id, UatCycleTest.client_tester_user_id.is_not(None)))}


def _cycle_read(db: Session, cycle: UatCycle, actor: User) -> dict[str, object]:
    is_approver = cycle.client_approver_user_id == actor.id
    is_coordinator = cycle.client_coordinator_user_id == actor.id
    test_query = select(UatCycleTest).where(UatCycleTest.cycle_id == cycle.id)
    if not (is_approver or is_coordinator):
        test_query = test_query.where(UatCycleTest.client_tester_user_id == actor.id)
    tests = list(db.scalars(test_query.order_by(UatCycleTest.display_order, UatCycleTest.id)))
    def visible_ticket(test: UatCycleTest) -> dict[str, object] | None:
        if not cycle.allow_client_view_linked_ticket or not test.linked_ticket_id:
            return None
        ticket = db.get(Ticket, test.linked_ticket_id)
        if not ticket or ticket.client_id != cycle.client_id:
            return None
        try:
            ensure_ticket_access(db, actor, ticket)
        except (AuthorizationError, NotFoundError):
            return None
        return {"id": ticket.id, "ticket_number": ticket.ticket_number}
    return {"id": cycle.id, "code": cycle.code, "title": cycle.title,
            "release_version": cycle.release_version, "environment": cycle.environment,
            "status": cycle.status, "start_date": cycle.start_date, "due_date": cycle.due_date,
            "allow_client_testing": cycle.allow_client_testing and cycle.status == "ACTIVE",
            "allow_client_pass": cycle.allow_client_pass, "allow_client_fail": cycle.allow_client_fail,
            "allow_client_blocked": cycle.allow_client_blocked,
            "role": "APPROVER" if is_approver else "COORDINATOR" if is_coordinator else "TESTER",
            "allow_client_signoff": cycle.allow_client_signoff and is_approver,
            "allow_client_request_testing": cycle.allow_client_signoff and is_coordinator,
            "allow_client_comments": cycle.allow_client_comments and cycle.status == "ACTIVE",
            "allow_client_attachments": cycle.allow_client_attachments and cycle.status == "ACTIVE",
            "allow_client_create_ticket_from_failure": cycle.allow_client_create_ticket_from_failure and cycle.status == "ACTIVE",
            "client_summary": _client_summary(db, cycle) if is_approver or is_coordinator else None,
            "client_signoff": _signoff_read(latest) if (latest := db.scalar(select(UatClientSignoff).where(UatClientSignoff.cycle_id == cycle.id).order_by(UatClientSignoff.decision_number.desc()))) else None,
            "client_signoff_current": bool(latest and latest.decision == "APPROVED" and json.loads(latest.summary_snapshot_json).get("test_states") == _client_test_states(db, cycle.id)),
            "tests": [_test_read(test, visible_ticket(test), test.client_tester_user_id == actor.id) for test in tests]}


@router.get("/cycles")
def list_portal_cycles(db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.portal.view"))) -> list[dict[str, object]]:
    if actor.user_type != "CLIENT_PORTAL":
        raise NotFoundError("UAT cycles do not exist.")
    client_ids = effective_permissions(db, actor).client_scope_ids
    if not client_ids:
        return []
    cycles = db.scalars(select(UatCycle).where(UatCycle.client_id.in_(client_ids), UatCycle.portal_visible == true(),
                                               UatCycle.status.in_(["ACTIVE", "COMPLETED"])).order_by(UatCycle.created_at.desc()))
    result: list[dict[str, object]] = []
    for cycle in cycles:
        try:
            _portal_access(db, actor, cycle)
        except NotFoundError:
            continue
        result.append(_cycle_read(db, cycle, actor))
    return result


@router.get("/cycles/{cycle_id}")
def get_portal_cycle(cycle_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.portal.view"))) -> dict[str, object]:
    cycle = db.get(UatCycle, cycle_id)
    if not cycle:
        raise NotFoundError("UAT cycle does not exist.")
    _portal_access(db, actor, cycle)
    return _cycle_read(db, cycle, actor)


@router.get("/cycles/{cycle_id}/signoff")
def get_client_signoff(cycle_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.portal.view"))) -> dict[str, object]:
    cycle = db.get(UatCycle, cycle_id)
    if not cycle:
        raise NotFoundError("UAT cycle does not exist.")
    _portal_access(db, actor, cycle)
    if not cycle.allow_client_signoff or actor.id not in {cycle.client_approver_user_id, cycle.client_coordinator_user_id}:
        raise NotFoundError("Client UAT sign-off does not exist.")
    decisions = db.scalars(select(UatClientSignoff).where(UatClientSignoff.cycle_id == cycle.id).order_by(UatClientSignoff.decision_number.desc()))
    return {"summary": _client_summary(db, cycle), "history": [_signoff_read(row) for row in decisions]}


@router.get("/cycles/{cycle_id}/activity")
def client_cycle_activity(cycle_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.portal.view"))) -> list[dict[str, object]]:
    cycle = db.get(UatCycle, cycle_id)
    if not cycle:
        raise NotFoundError("UAT cycle does not exist.")
    _portal_access(db, actor, cycle)
    broad_review = actor.id in {cycle.client_approver_user_id, cycle.client_coordinator_user_id}
    tests = list(db.scalars(select(UatCycleTest).where(
        UatCycleTest.cycle_id == cycle_id,
        UatCycleTest.client_tester_user_id.is_not(None) if broad_review else UatCycleTest.client_tester_user_id == actor.id,
    )))
    test_ids = [test.id for test in tests]
    codes = {test.id: json.loads(test.snapshot_json).get("code", str(test.id)) for test in tests}
    attempts = list(db.scalars(select(UatTestAttempt).where(UatTestAttempt.cycle_test_id.in_(test_ids),
                                                            UatTestAttempt.execution_source == "CLIENT_PORTAL")
                               .order_by(UatTestAttempt.tested_at.desc()).limit(100))) if test_ids else []
    comments = list(db.scalars(select(UatComment).where(UatComment.cycle_test_id.in_(test_ids),
                                                        UatComment.visibility == "CLIENT_VISIBLE")
                               .order_by(UatComment.created_at.desc()).limit(100))) if test_ids else []
    decisions = list(db.scalars(select(UatClientSignoff).where(UatClientSignoff.cycle_id == cycle_id)
                                .order_by(UatClientSignoff.decision_number.desc()).limit(50))) if broad_review else []
    user_ids = {item.tested_by_user_id for item in attempts} | {item.author_user_id for item in comments} | {item.decided_by_user_id for item in decisions}
    names = {user.id: user.full_name for user in db.scalars(select(User).where(User.id.in_(user_ids)))} if user_ids else {}
    events = ([{"kind": "TEST_RESULT", "test_code": codes.get(item.cycle_test_id), "actor": names.get(item.tested_by_user_id, "Client"),
                "detail": item.result, "at": item.tested_at} for item in attempts]
              + [{"kind": "COMMENT", "test_code": codes.get(item.cycle_test_id), "actor": names.get(item.author_user_id, "User"),
                  "detail": item.body, "at": item.created_at} for item in comments]
              + [{"kind": "SIGNOFF", "test_code": None, "actor": names.get(item.decided_by_user_id, "Client"),
                  "detail": item.decision, "at": item.decided_at} for item in decisions])
    return sorted(events, key=lambda item: cast(datetime, item["at"]), reverse=True)[:100]


@router.post("/cycles/{cycle_id}/signoff", status_code=status.HTTP_201_CREATED)
def decide_client_signoff(cycle_id: int, data: ClientSignoffInput, db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.portal.signoff"))) -> dict[str, object]:
    cycle = db.get(UatCycle, cycle_id)
    if not cycle:
        raise NotFoundError("UAT cycle does not exist.")
    _portal_access(db, actor, cycle)
    if not cycle.allow_client_signoff or actor.id not in {cycle.client_approver_user_id, cycle.client_coordinator_user_id}:
        raise NotFoundError("Client UAT sign-off does not exist.")
    if actor.id != cycle.client_approver_user_id and data.decision != "ADDITIONAL_TESTING":
        raise AuthorizationError("Only the assigned client approver can approve or reject UAT.")
    if cycle.status != "ACTIVE":
        raise ConflictError("INVALID_UAT_STATE", "Client acceptance requires an active cycle.")
    if db.scalar(select(UatSignoff.id).where(UatSignoff.cycle_id == cycle.id, UatSignoff.status == "PENDING")):
        raise ConflictError("UAT_SIGNOFF_PENDING", "Internal sign-off is pending.")
    if data.decision != "APPROVED" and not (data.comment or "").strip():
        raise ConflictError("UAT_CLIENT_COMMENT_REQUIRED", "Explain the rejection or additional testing request.")
    summary = _client_summary(db, cycle)
    test_states = _client_test_states(db, cycle.id)
    if data.decision == "APPROVED" and (not summary["total"] or summary["mandatory_outstanding"] or summary["failed"] or summary["blocked"] or summary["open_defects"]):
        raise ConflictError("UAT_CLIENT_SIGNOFF_NOT_READY", "Complete mandatory client tests and resolve failures, blocked tests, and open defects before approval.")
    latest = db.scalar(select(UatClientSignoff).where(UatClientSignoff.cycle_id == cycle.id).order_by(UatClientSignoff.decision_number.desc()))
    if latest and latest.decision == "APPROVED" and json.loads(latest.summary_snapshot_json).get("test_states") == test_states:
        raise ConflictError("UAT_CLIENT_ALREADY_APPROVED", "Client UAT is already approved.")
    row = UatClientSignoff(cycle_id=cycle.id, decision_number=(latest.decision_number + 1 if latest else 1),
                           decision=data.decision, decided_by_user_id=actor.id, decided_at=server_now(),
                           comment=data.comment.strip() if data.comment else None,
                           summary_snapshot_json=json.dumps({**summary, "test_states": test_states}))
    db.add(row)
    if data.decision == "ADDITIONAL_TESTING":
        for test in db.scalars(select(UatCycleTest).where(
            UatCycleTest.cycle_id == cycle.id,
            UatCycleTest.client_workflow_status == "NEEDS_INVESTIGATION",
            UatCycleTest.linked_ticket_id.is_(None),
        )):
            test.client_workflow_status = "READY"
    db.add(Notification(recipient_user_id=cycle.coordinator_user_id, notification_type="UAT_CLIENT_SIGNOFF",
                        severity="INFO" if data.decision == "APPROVED" else "WARNING",
                        title=f"Client UAT {data.decision.lower().replace('_', ' ')}: {cycle.code}",
                        message=(data.comment or f"{actor.full_name} recorded a client UAT decision.")[:1000],
                        deep_link="/uat", deduplication_key=f"uat-client-signoff:{cycle.id}:{row.decision_number}"))
    db.add(AuditLog(actor_user_id=actor.id, entity_type="UatClientSignoff", entity_id=str(cycle.id),
                    action=f"uat.client_signoff.{data.decision.lower()}"))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("UAT_CONCURRENT_SIGNOFF", "Another client decision was recorded. Refresh and retry.") from exc
    db.refresh(row)
    return _signoff_read(row)


def _review_test(db: Session, actor: User, test_id: int) -> tuple[UatCycle, UatCycleTest]:
    test = db.get(UatCycleTest, test_id)
    cycle = db.get(UatCycle, test.cycle_id) if test else None
    if not test or not cycle:
        raise NotFoundError("UAT test does not exist.")
    _portal_access(db, actor, cycle)
    if test.client_tester_user_id is None or (test.client_tester_user_id != actor.id and actor.id not in {cycle.client_approver_user_id, cycle.client_coordinator_user_id}):
        raise NotFoundError("UAT test does not exist.")
    return cycle, test


def _assigned_test(db: Session, actor: User, test_id: int) -> tuple[UatCycle, UatCycleTest]:
    cycle, test = _review_test(db, actor, test_id)
    if test.client_tester_user_id != actor.id:
        raise NotFoundError("UAT test does not exist.")
    return cycle, test


@router.put("/tests/{test_id}/workflow")
def move_client_test_workflow(
    test_id: int,
    data: ClientWorkflowMoveInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.portal.execute")),
) -> dict[str, object]:
    cycle, test = _assigned_test(db, actor, test_id)
    if cycle.status != "ACTIVE" or not cycle.allow_client_testing:
        raise ConflictError("UAT_CLIENT_TESTING_DISABLED", "Client testing is not enabled for this cycle.")
    if db.scalar(select(UatSignoff.id).where(UatSignoff.cycle_id == cycle.id, UatSignoff.status == "PENDING")):
        raise ConflictError("UAT_SIGNOFF_PENDING", "Decide the pending sign-off request before testing.")
    latest = db.scalar(select(UatClientSignoff).where(UatClientSignoff.cycle_id == cycle.id).order_by(UatClientSignoff.decision_number.desc()))
    if latest and latest.decision == "APPROVED" and json.loads(latest.summary_snapshot_json).get("test_states") == _client_test_states(db, cycle.id):
        raise ConflictError("UAT_CLIENT_ALREADY_APPROVED", "Client UAT has already been approved.")
    allowed = {
        ("READY", "IN_PROGRESS"),
        ("IN_PROGRESS", "READY"),
        ("READY_FOR_RETEST", "IN_PROGRESS"),
    }
    if (test.client_workflow_status, data.workflow_status) not in allowed:
        raise ConflictError(
            "UAT_CLIENT_WORKFLOW_MOVE_INVALID",
            "Move ready tests into testing, or use the result form to record Pass, Fail, or Blocked.",
        )
    test.client_workflow_status = data.workflow_status
    db.add(AuditLog(
        actor_user_id=actor.id,
        entity_type="UatCycleTest",
        entity_id=str(test.id),
        action="uat.client_test.workflow_moved",
        new_values_json=json.dumps({"workflow_status": data.workflow_status}),
    ))
    db.commit()
    return _test_read(test)


def _client_defect_draft(db: Session, cycle: UatCycle, test: UatCycleTest) -> dict[str, str]:
    if not cycle.allow_client_create_ticket_from_failure:
        raise ConflictError("UAT_CLIENT_TICKET_DISABLED", "Client defect ticket creation is disabled for this cycle.")
    if test.linked_ticket_id:
        raise ConflictError("UAT_TICKET_EXISTS", "This UAT test already has a linked ticket.")
    if test.client_test_result != "FAIL":
        raise ConflictError("UAT_CLIENT_NOT_FAILED", "Record a failed client attempt first.")
    latest = db.scalar(select(UatTestAttempt).where(UatTestAttempt.cycle_test_id == test.id,
                                                    UatTestAttempt.execution_source == "CLIENT_PORTAL",
                                                    UatTestAttempt.result == "FAIL").order_by(UatTestAttempt.attempt_number.desc()))
    if not latest:
        raise ConflictError("UAT_CLIENT_NOT_FAILED", "No failed client attempt was found.")
    snapshot = json.loads(test.snapshot_json)
    subject = f"UAT Failed - {snapshot['title']}"[:300]
    description = f"UAT cycle: {cycle.code} - {cycle.title}\nTest: {snapshot['code']} - {snapshot['title']}\nExpected: {snapshot['expected_result']}\nActual: {latest.actual_result}\nFailure: {latest.failure_reason or latest.actual_result}\nRelease: {cycle.release_version}"
    severity = latest.severity or "MEDIUM"
    return {"subject": subject, "description": description[:20000], "impact": severity, "urgency": severity}


@router.get("/tests/{test_id}/defect-ticket-draft")
def client_defect_draft(test_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.portal.view"))) -> dict[str, str]:
    cycle, test = _assigned_test(db, actor, test_id)
    return _client_defect_draft(db, cycle, test)


@router.post("/tests/{test_id}/defect-ticket", status_code=status.HTTP_201_CREATED)
def create_client_defect_ticket(test_id: int, data: ClientDefectInput, db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.portal.create_ticket"))) -> dict[str, object]:
    cycle, test = _assigned_test(db, actor, test_id)
    if "ticket.create" not in effective_permissions(db, actor).permissions:
        raise AuthorizationError("Ticket creation permission is required.")
    if cycle.status != "ACTIVE":
        raise ConflictError("INVALID_UAT_STATE", "Only active cycles can create defect tickets.")
    _client_defect_draft(db, cycle, test)
    ticket_type = db.scalar(select(TicketType).where(TicketType.code == "INCIDENT"))
    if not ticket_type:
        raise NotFoundError("Incident ticket type is not configured.")
    snapshot = json.loads(test.snapshot_json)
    previous = db.scalar(select(Ticket).where(Ticket.source_channel == "CLIENT_PORTAL", Ticket.creation_idempotency_key == f"uat-client-defect-{test.id}", Ticket.created_by_user_id == actor.id))
    ticket = previous or create_ticket(db, TicketCreate(
        ticket_type_id=ticket_type.id, client_id=cycle.client_id, contract_id=cycle.contract_id,
        product_id=cycle.product_id or snapshot.get("product_id"), product_module_id=snapshot.get("module_id"),
        source_channel="UAT", creation_idempotency_key=f"uat-client-defect-{test.id}", **data.model_dump(),
    ), actor)
    test.linked_ticket_id = ticket.id
    latest = db.scalar(select(UatTestAttempt).where(UatTestAttempt.cycle_test_id == test.id,
                                                    UatTestAttempt.execution_source == "CLIENT_PORTAL",
                                                    UatTestAttempt.result == "FAIL").order_by(UatTestAttempt.attempt_number.desc()))
    if latest:
        latest.linked_ticket_id = ticket.id
    test.client_workflow_status = "WAITING_FIX"
    notify_defect_created(db, cycle, test, ticket)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="UatCycleTest", entity_id=str(test.id), action="uat.client_defect_ticket.linked"))
    db.commit()
    return {"ticket_id": ticket.id, "ticket_number": ticket.ticket_number}


@router.get("/tests/{test_id}/attempts")
def portal_attempts(test_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.portal.view"))) -> list[dict[str, object]]:
    _review_test(db, actor, test_id)
    return [{"id": row.id, "attempt_number": row.attempt_number, "result": row.result,
             "actual_result": row.actual_result, "failure_reason": row.failure_reason,
             "blocking_reason": row.blocking_reason, "comment": row.comment,
             "tested_at": row.tested_at}
            for row in db.scalars(select(UatTestAttempt).where(UatTestAttempt.cycle_test_id == test_id,
                                                               UatTestAttempt.execution_source == "CLIENT_PORTAL")
                                  .order_by(UatTestAttempt.attempt_number))]


@router.post("/tests/{test_id}/attempts", status_code=status.HTTP_201_CREATED)
def execute_client_test(test_id: int, data: ClientAttemptInput, db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.portal.execute"))) -> dict[str, object]:
    cycle, test = _assigned_test(db, actor, test_id)
    if cycle.status != "ACTIVE" or not cycle.allow_client_testing:
        raise ConflictError("UAT_CLIENT_TESTING_DISABLED", "Client testing is not enabled for this cycle.")
    if db.scalar(select(UatSignoff.id).where(UatSignoff.cycle_id == cycle.id, UatSignoff.status == "PENDING")):
        raise ConflictError("UAT_SIGNOFF_PENDING", "Decide the pending sign-off request before testing.")
    latest_client_signoff = db.scalar(select(UatClientSignoff).where(UatClientSignoff.cycle_id == cycle.id).order_by(UatClientSignoff.decision_number.desc()))
    if latest_client_signoff and latest_client_signoff.decision == "APPROVED" and json.loads(latest_client_signoff.summary_snapshot_json).get("test_states") == _client_test_states(db, cycle.id):
        raise ConflictError("UAT_CLIENT_ALREADY_APPROVED", "Client UAT has already been approved.")
    allowed = {"PASS": cycle.allow_client_pass, "FAIL": cycle.allow_client_fail, "BLOCKED": cycle.allow_client_blocked}
    if not allowed[data.result]:
        raise ConflictError("UAT_CLIENT_RESULT_DISABLED", "This result is not enabled for client testing.")
    if test.client_test_result == "PASS":
        raise ConflictError("UAT_CLIENT_ALREADY_PASSED", "A passed client test cannot be executed again.")
    if data.result in {"PASS", "FAIL"} and not data.actual_result.strip():
        raise ConflictError("UAT_ACTUAL_RESULT_REQUIRED", "Actual result is required.")
    if data.result == "FAIL" and (not data.failure_reason or not data.failure_reason.strip() or not data.severity):
        raise ConflictError("UAT_FAILURE_DETAILS_REQUIRED", "Failure description and severity are required.")
    if data.result == "BLOCKED" and (not data.blocking_reason or not data.blocking_reason.strip() or not data.comment or not data.comment.strip()):
        raise ConflictError("UAT_BLOCKING_DETAILS_REQUIRED", "Blocking reason and comment are required.")
    if test.client_workflow_status == "BLOCKED":
        raise ConflictError("UAT_CLIENT_BLOCKED", "Ask the UAT coordinator to unblock this client test.")
    if test.linked_ticket_id and test.client_workflow_status == "WAITING_FIX":
        raise ConflictError("UAT_WAITING_FIX", "The linked ticket must be resolved before retesting.")
    if test.client_workflow_status == "NEEDS_INVESTIGATION":
        raise ConflictError("UAT_NEEDS_INVESTIGATION", "The UAT coordinator must investigate this failure before retesting.")
    when = server_now()
    attempt_number = (db.scalar(select(func.max(UatTestAttempt.attempt_number)).where(UatTestAttempt.cycle_test_id == test.id)) or 0) + 1
    test.client_attempt_count += 1
    test.client_test_result = data.result
    test.client_workflow_status = {"PASS": "COMPLETED", "FAIL": "NEEDS_INVESTIGATION", "BLOCKED": "BLOCKED"}[data.result]
    test.client_tested_at = when
    db.add(UatTestAttempt(cycle_test_id=test.id, attempt_number=attempt_number,
                          execution_source="CLIENT_PORTAL", tested_by_user_id=actor.id, tested_at=when,
                          result=data.result, actual_result=data.actual_result or data.blocking_reason or "",
                          failure_reason=data.failure_reason.strip() if data.failure_reason and data.result == "FAIL" else None,
                          blocking_reason=data.blocking_reason.strip() if data.blocking_reason and data.result == "BLOCKED" else None,
                          severity=data.severity if data.result == "FAIL" else None, comment=data.comment))
    if data.result == "FAIL" and test.client_attempt_count == 1:
        db.add(Notification(recipient_user_id=cycle.coordinator_user_id, notification_type="UAT_CLIENT_TEST_FAILED",
                            severity="CRITICAL" if data.severity == "CRITICAL" else "WARNING",
                            title=f"Client UAT failed: {cycle.code}",
                            message=f"Client test #{test.id} failed. Severity: {data.severity}.",
                            deep_link="/uat", deduplication_key=f"uat-client-failed:{test.id}:attempt:{test.client_attempt_count}"))
    if test.client_attempt_count > 1 and data.result in {"PASS", "FAIL"}:
        db.add(Notification(recipient_user_id=cycle.coordinator_user_id,
                            notification_type=f"UAT_CLIENT_RETEST_{data.result}",
                            severity="WARNING" if data.result == "FAIL" else "INFO",
                            title=f"Client UAT retest {data.result.lower()}: {cycle.code}",
                            message=f"Client test #{test.id} retest {data.result.lower()}.",
                            deep_link="/uat",
                            deduplication_key=f"uat-client-retest-result:{test.id}:attempt:{test.client_attempt_count}"))
    db.add(AuditLog(actor_user_id=actor.id, entity_type="UatCycleTest", entity_id=str(test.id), action="uat.client_test.executed"))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("UAT_CONCURRENT_ATTEMPT", "Another UAT attempt was recorded. Refresh and retry.") from exc
    return _test_read(test)
