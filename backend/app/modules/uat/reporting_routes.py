"""Read-only UAT portfolio and export views."""

import csv
import io
import json
from collections import Counter
from datetime import datetime
from html import escape
from typing import cast

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.modules.clients.models import Client
from app.modules.iam.models import AuditLog, User
from app.modules.tickets.models import Ticket
from app.modules.uat.models import (
    UatClientSignoff,
    UatComment,
    UatCycle,
    UatCycleTest,
    UatEvidence,
    UatSignoff,
    UatTestAttempt,
)
from app.modules.uat.routes import cycle_dashboard

router = APIRouter(prefix="/uat", tags=["uat reporting"])


def _csv_safe(value: object) -> object:
    return "'" + value if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")) else value


def _xlsx_safe(value: object) -> object:
    return _csv_safe(value.isoformat() if isinstance(value, datetime) else value)


def _portfolio(db: Session, actor: User) -> list[dict[str, object]]:
    cycles = list(db.scalars(select(UatCycle).order_by(UatCycle.created_at.desc())))
    clients = {row.id: row.name for row in db.scalars(select(Client).where(Client.id.in_([cycle.client_id for cycle in cycles])))} if cycles else {}
    rows: list[dict[str, object]] = []
    today = server_now().date()
    for cycle in cycles:
        metrics = cycle_dashboard(cycle.id, db, actor)["metrics"]
        assert isinstance(metrics, dict)
        tests = list(db.scalars(select(UatCycleTest).where(UatCycleTest.cycle_id == cycle.id)))
        client_tests = [test for test in tests if test.client_tester_user_id]
        client_signoff = db.scalar(select(UatClientSignoff).where(UatClientSignoff.cycle_id == cycle.id).order_by(UatClientSignoff.decision_number.desc()))
        internal_signoff = db.scalar(select(UatSignoff).where(UatSignoff.cycle_id == cycle.id).order_by(UatSignoff.request_number.desc()))
        attention: list[str] = []
        if metrics["critical_failures"]:
            attention.append("Critical failures present")
        if metrics["open_defects"]:
            attention.append("Open defects")
        if cycle.due_date and cycle.status != "COMPLETED":
            if cycle.due_date < today:
                attention.append("Overdue")
            elif (cycle.due_date - today).days <= 3:
                attention.append("Due soon")
        if cycle.status == "ACTIVE" and metrics["not_tested"]:
            attention.append("Testing incomplete")
        if internal_signoff and internal_signoff.status == "PENDING":
            attention.append("Awaiting sign-off")
        rows.append({"id": cycle.id, "code": cycle.code, "title": cycle.title,
                     "client_id": cycle.client_id, "client_name": clients.get(cycle.client_id, "Unknown"),
                     "release_version": cycle.release_version, "status": cycle.status,
                     "due_date": cycle.due_date, "metrics": metrics,
                     "client_total": len(client_tests),
                     "client_passed": sum(test.client_test_result == "PASS" for test in client_tests),
                     "client_failed": sum(test.client_test_result == "FAIL" for test in client_tests),
                     "client_signoff": client_signoff.decision if client_signoff else "NOT_REQUESTED",
                     "internal_signoff": internal_signoff.status if internal_signoff else "NOT_REQUESTED",
                     "attention": attention})
    return rows


@router.get("/portfolio")
def uat_portfolio(db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.view"))) -> list[dict[str, object]]:
    return _portfolio(db, actor)


@router.get("/cycles/{cycle_id}/activity")
def uat_cycle_activity(cycle_id: int, db: Session = Depends(get_db), _actor: User = Depends(require_permission("uat.view"))) -> list[dict[str, object]]:
    if not db.get(UatCycle, cycle_id):
        raise NotFoundError("UAT cycle does not exist.")
    test_ids = list(db.scalars(select(UatCycleTest.id).where(UatCycleTest.cycle_id == cycle_id)))
    attempt_ids = list(db.scalars(select(UatTestAttempt.id).where(UatTestAttempt.cycle_test_id.in_(test_ids)))) if test_ids else []
    comment_ids = list(db.scalars(select(UatComment.id).where(UatComment.cycle_test_id.in_(test_ids)))) if test_ids else []
    evidence_ids = list(db.scalars(select(UatEvidence.id).where(UatEvidence.attempt_id.in_(attempt_ids)))) if attempt_ids else []
    signoff_ids = list(db.scalars(select(UatSignoff.id).where(UatSignoff.cycle_id == cycle_id)))
    conditions = [("UatCycle", [str(cycle_id)]), ("UatCycleTest", [str(value) for value in test_ids]),
                  ("UatComment", [str(value) for value in comment_ids]),
                  ("UatEvidence", [str(value) for value in evidence_ids]),
                  ("UatSignoff", [str(value) for value in signoff_ids]),
                  ("UatClientSignoff", [str(cycle_id)])]
    clauses = [and_(AuditLog.entity_type == entity, AuditLog.entity_id.in_(ids)) for entity, ids in conditions if ids]
    logs = list(db.scalars(select(AuditLog).where(or_(*clauses)).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(100)))
    actor_ids = {log.actor_user_id for log in logs if log.actor_user_id}
    names = {user.id: user.full_name for user in db.scalars(select(User).where(User.id.in_(actor_ids)))} if actor_ids else {}
    return [{"id": log.id, "action": log.action, "entity_type": log.entity_type,
             "entity_id": log.entity_id, "actor_name": names.get(log.actor_user_id, "System") if log.actor_user_id else "System",
             "created_at": log.created_at} for log in logs]


@router.get("/portfolio.csv")
def export_uat_portfolio(db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.view"))) -> StreamingResponse:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Cycle", "Client", "Release", "Status", "Due date", "Completion %", "Pass rate %", "Failed", "Critical failures", "Open defects", "Client passed", "Client total", "Client sign-off", "Internal sign-off", "Attention"])
    for row in _portfolio(db, actor):
        metrics = row["metrics"]
        assert isinstance(metrics, dict)
        writer.writerow([_csv_safe(row["code"]), _csv_safe(row["client_name"]), _csv_safe(row["release_version"]), row["status"], row["due_date"],
                         metrics["completion_percent"], metrics["pass_rate"], metrics["failed"], metrics["critical_failures"],
                         metrics["open_defects"], row["client_passed"], row["client_total"], row["client_signoff"],
                         row["internal_signoff"], "; ".join(cast(list[str], row["attention"]))])
    return StreamingResponse(iter(["\ufeff" + output.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": 'attachment; filename="uat-portfolio.csv"'})


def _cycle_results(db: Session, cycle_id: int) -> dict[str, object]:
    cycle = db.get(UatCycle, cycle_id)
    if not cycle:
        raise NotFoundError("UAT cycle does not exist.")
    tests = list(db.scalars(select(UatCycleTest).where(UatCycleTest.cycle_id == cycle_id).order_by(UatCycleTest.display_order, UatCycleTest.id)))
    ticket_ids = [test.linked_ticket_id for test in tests if test.linked_ticket_id]
    tickets = {ticket.id: ticket.ticket_number for ticket in db.scalars(select(Ticket).where(Ticket.id.in_(ticket_ids)))} if ticket_ids else {}
    users_ids = {user_id for test in tests for user_id in (test.owner_user_id, test.client_tester_user_id) if user_id}
    users = {user.id: user.full_name for user in db.scalars(select(User).where(User.id.in_(users_ids)))} if users_ids else {}
    rows: list[dict[str, object]] = []
    for test in tests:
        snapshot = json.loads(test.snapshot_json)
        rows.append({"test_id": test.id, "code": snapshot.get("code", ""), "title": snapshot.get("title", ""),
                     "priority": test.priority_override or snapshot.get("priority", "MEDIUM"),
                     "feature": snapshot.get("feature_name", ""), "expected_result": snapshot.get("expected_result", ""),
                     "internal_owner": users.get(test.owner_user_id, "") if test.owner_user_id else "", "internal_result": test.test_result,
                     "internal_status": test.workflow_status, "internal_attempts": test.attempt_count,
                     "internal_tested_at": test.tested_at,
                     "client_tester": users.get(test.client_tester_user_id, "") if test.client_tester_user_id else "", "client_result": test.client_test_result,
                     "client_status": test.client_workflow_status, "client_attempts": test.client_attempt_count,
                     "client_tested_at": test.client_tested_at,
                     "due_date": test.due_date, "linked_ticket": tickets.get(test.linked_ticket_id, "") if test.linked_ticket_id else ""})
    assigned = [test for test in tests if test.client_tester_user_id is not None]
    return {"cycle_id": cycle.id, "code": cycle.code, "title": cycle.title,
            "release_version": cycle.release_version, "status": cycle.status, "tests": rows,
            "summary": {"total": len(rows), "internal_passed": sum(test.test_result == "PASS" for test in tests),
                        "internal_failed": sum(test.test_result == "FAIL" for test in tests),
                        "internal_blocked": sum(test.test_result == "BLOCKED" for test in tests),
                        "internal_unexecuted": sum(test.attempt_count == 0 for test in tests),
                        "client_assigned": len(assigned),
                        "client_passed": sum(test.client_test_result == "PASS" for test in tests),
                        "client_failed": sum(test.client_test_result == "FAIL" for test in tests),
                        "client_blocked": sum(test.client_test_result == "BLOCKED" for test in tests),
                        "client_unexecuted": sum(test.client_attempt_count == 0 for test in assigned),
                        "linked_defects": sum(test.linked_ticket_id is not None for test in tests),
                        "internal_retests": sum(max(0, test.attempt_count - 1) for test in tests),
                        "client_retests": sum(max(0, test.client_attempt_count - 1) for test in assigned)},
            "by_priority": dict(Counter(str(row["priority"]) for row in rows)),
            "by_feature": dict(Counter(str(row["feature"]) or "Unspecified" for row in rows))}


@router.get("/cycles/{cycle_id}/results-report")
def cycle_results_report(cycle_id: int, db: Session = Depends(get_db), _actor: User = Depends(require_permission("uat.view"))) -> dict[str, object]:
    return _cycle_results(db, cycle_id)


@router.get("/cycles/{cycle_id}/results-report.xlsx")
def export_cycle_results(cycle_id: int, db: Session = Depends(get_db), _actor: User = Depends(require_permission("uat.view"))) -> StreamingResponse:
    report = _cycle_results(db, cycle_id)
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "UAT results"
    sheet.append(["Cycle", _csv_safe(report["code"]), "Release", _csv_safe(report["release_version"]), "Status", report["status"]])
    headers = ["Test ID", "Code", "Title", "Priority", "Feature", "Expected result", "Internal owner", "Internal result", "Internal status", "Internal attempts", "Internal tested at", "Client tester", "Client result", "Client status", "Client attempts", "Client tested at", "Due date", "Linked ticket"]
    keys = ["test_id", "code", "title", "priority", "feature", "expected_result", "internal_owner", "internal_result", "internal_status", "internal_attempts", "internal_tested_at", "client_tester", "client_result", "client_status", "client_attempts", "client_tested_at", "due_date", "linked_ticket"]
    sheet.append(headers)
    for row in cast(list[dict[str, object]], report["tests"]):
        sheet.append([_xlsx_safe(row[key]) for key in keys])
    sheet.freeze_panes = "A3"
    sheet.auto_filter.ref = f"A2:R{sheet.max_row}"
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f'attachment; filename="uat-cycle-{cycle_id}-results.xlsx"'})


@router.get("/cycles/{cycle_id}/results-report.pdf")
def export_cycle_results_pdf(cycle_id: int, db: Session = Depends(get_db),
                             _actor: User = Depends(require_permission("uat.view"))) -> StreamingResponse:
    report = _cycle_results(db, cycle_id)
    output = io.BytesIO()
    document = SimpleDocTemplate(output, pagesize=(11.7 * inch, 8.3 * inch),
                                 leftMargin=32, rightMargin=32, topMargin=32, bottomMargin=32)
    styles = getSampleStyleSheet()
    def para(value: object) -> Paragraph:
        return Paragraph(escape(str(value if value is not None else "")), styles["BodyText"])
    summary = cast(dict[str, int], report["summary"])
    story: list[object] = [Paragraph("UAT combined results", styles["Title"]),
                           para(f'{report["code"]} - {report["title"]} | Release {report["release_version"]} | {report["status"]}'),
                           Spacer(1, 12)]
    for label, keys in (("Internal", ("internal_passed", "internal_failed", "internal_blocked", "internal_unexecuted", "internal_retests")),
                        ("Client", ("client_passed", "client_failed", "client_blocked", "client_unexecuted", "client_retests"))):
        story.append(para(label + ": " + " | ".join(f"{key.split('_')[-1].title()} {summary[key]}" for key in keys)))
    story.extend([para(f'Linked defects: {summary["linked_defects"]} | Client assigned: {summary["client_assigned"]}'), Spacer(1, 12)])
    headers = ["Case", "Priority", "Internal owner", "Internal result", "Client tester", "Client result", "Ticket"]
    data = [[para(value) for value in headers]]
    for row in cast(list[dict[str, object]], report["tests"]):
        data.append([para(f'{row["code"]}: {row["title"]}'), para(row["priority"]), para(row["internal_owner"]),
                     para(row["internal_result"]), para(row["client_tester"]), para(row["client_result"]),
                     para(row["linked_ticket"])])
    table = Table(data, colWidths=[180, 65, 110, 82, 110, 82, 75], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF5")),
                               ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CDD5DF")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]))
    story.append(table)
    document.build(story)
    output.seek(0)
    return StreamingResponse(output, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="uat-cycle-{cycle_id}-results.pdf"'})
