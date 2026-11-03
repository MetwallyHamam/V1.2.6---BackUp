import hashlib
import io
import json
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, Literal, cast
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now, server_timezone
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import (
    Client,
    Environment,
    Product,
    ProductModule,
    ServiceCatalogItem,
    TicketCategory,
    TicketSubcategory,
)
from app.modules.iam.models import AuditLog, User
from app.modules.ticket_reports.models import (
    TicketReport,
    TicketReportShareLink,
    TicketReportVersion,
)
from app.modules.tickets.models import (
    Ticket,
    TicketAssignmentHistory,
    TicketStatus,
    TicketStatusHistory,
    TicketType,
    TicketWorklog,
)
from app.modules.tickets.service import ensure_ticket_access

router = APIRouter(prefix="/ticket-reports", tags=["ticket reports"])
public_router = APIRouter(prefix="/public/ticket-reports", tags=["public ticket reports"])


class ReportInput(BaseModel):
    report_type: Literal["TICKET", "INCIDENT"]
    title: str = Field(min_length=3, max_length=300)
    data: dict[str, Any] = Field(default_factory=dict)


class ReportUpdate(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    data: dict[str, Any]


class ShareInput(BaseModel):
    expires_in_days: int = Field(default=7, ge=1, le=365)
    recipient_name: str | None = Field(default=None, max_length=200)
    recipient_email: str | None = Field(default=None, max_length=320)
    allow_download: bool = True


class TicketEventInput(BaseModel):
    occurred_at: datetime
    event: str = Field(min_length=3, max_length=2000)
    owner: str | None = Field(default=None, max_length=200)


def _payload(row: TicketReport | TicketReportVersion) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(row.payload_json or "{}"))


def _expected_report_type(db: Session, ticket: Ticket) -> str:
    ticket_type = db.get(TicketType, ticket.ticket_type_id)
    return "INCIDENT" if ticket_type and ticket_type.code == "INCIDENT" else "TICKET"


def _ensure_matching_report_type(db: Session, ticket: Ticket, report_type: str) -> None:
    expected = _expected_report_type(db, ticket)
    if report_type != expected:
        expected_name = "Incident Report" if expected == "INCIDENT" else "Ticket Service Report"
        raise ConflictError(
            "REPORT_TYPE_MISMATCH",
            f"This ticket must use the {expected_name} template.",
        )


def _ticket_context(db: Session, ticket: Ticket) -> dict[str, Any]:
    client = db.get(Client, ticket.client_id)
    ticket_type = db.get(TicketType, ticket.ticket_type_id)
    status_row = db.get(TicketStatus, ticket.status_id)
    assignee = db.get(User, ticket.assigned_user_id) if ticket.assigned_user_id else None
    product = db.get(Product, ticket.product_id) if ticket.product_id else None
    module = db.get(ProductModule, ticket.product_module_id) if ticket.product_module_id else None
    service = db.get(ServiceCatalogItem, ticket.service_id) if ticket.service_id else None
    environment = db.get(Environment, ticket.environment_id) if ticket.environment_id else None
    category = db.get(TicketCategory, ticket.category_id) if ticket.category_id else None
    subcategory = db.get(TicketSubcategory, ticket.subcategory_id) if ticket.subcategory_id else None
    worklogs = list(
        db.scalars(
            select(TicketWorklog)
            .where(TicketWorklog.ticket_id == ticket.id, TicketWorklog.status == "APPROVED")
            .order_by(TicketWorklog.started_at, TicketWorklog.id)
        )
    )
    worklog_users = {
        user_id: db.get(User, user_id) for user_id in {item.user_id for item in worklogs}
    }
    status_history = list(
        db.scalars(
            select(TicketStatusHistory)
            .where(TicketStatusHistory.ticket_id == ticket.id)
            .order_by(TicketStatusHistory.created_at, TicketStatusHistory.id)
        )
    )
    assignment_history = list(
        db.scalars(
            select(TicketAssignmentHistory)
            .where(TicketAssignmentHistory.ticket_id == ticket.id)
            .order_by(TicketAssignmentHistory.created_at, TicketAssignmentHistory.id)
        )
    )
    report_events = list(
        db.scalars(
            select(AuditLog)
            .where(
                AuditLog.entity_type == "Ticket",
                AuditLog.entity_id == str(ticket.id),
                AuditLog.action == "ticket.report_event.added",
            )
            .order_by(AuditLog.created_at, AuditLog.id)
        )
    )
    status_ids = {
        status_id
        for history in status_history
        for status_id in (history.from_status_id, history.to_status_id)
        if status_id
    }
    statuses = {status_id: db.get(TicketStatus, status_id) for status_id in status_ids}
    timeline: list[dict[str, Any]] = [
        {
            "id": "system-created",
            "time": ticket.created_at.isoformat(),
            "event": "Ticket created",
            "owner": (ticket.source_channel or "System").replace("_", " ").title(),
            "source": "SYSTEM",
            "included": True,
        }
    ]
    for status_change in status_history:
        previous = statuses.get(status_change.from_status_id) if status_change.from_status_id else None
        current = statuses.get(status_change.to_status_id)
        previous_name = previous.name if previous else "New"
        current_name = current.name if current else "Updated"
        timeline.append(
            {
                "id": f"system-status-{status_change.id}",
                "time": status_change.created_at.isoformat(),
                "event": f"Status changed from {previous_name} to {current_name}"
                + (f": {status_change.reason}" if status_change.reason else ""),
                "owner": getattr(db.get(User, status_change.changed_by_user_id), "full_name", "")
                or "Support team",
                "source": "SYSTEM",
                "included": True,
            }
        )
    for assignment in assignment_history:
        assigned = db.get(User, assignment.assigned_user_id) if assignment.assigned_user_id else None
        owner = getattr(assigned, "full_name", "") or assignment.assigned_team or "Support team"
        timeline.append(
            {
                "id": f"system-assignment-{assignment.id}",
                "time": assignment.created_at.isoformat(),
                "event": f"Ticket assigned to {owner}"
                + (f": {assignment.reason}" if assignment.reason else ""),
                "owner": owner,
                "source": "SYSTEM",
                "included": True,
            }
        )
    for item in worklogs:
        timeline.append(
            {
                "id": f"system-worklog-{item.id}",
                "time": item.started_at.isoformat(),
                "event": item.notes,
                "owner": getattr(worklog_users.get(item.user_id), "full_name", "")
                or "Support engineer",
                "source": "SYSTEM",
                "included": True,
            }
        )
    for report_event in report_events:
        details = json.loads(report_event.new_values_json or "{}")
        timeline.append(
            {
                "id": f"system-ticket-event-{report_event.id}",
                "time": details.get("occurred_at") or report_event.created_at.isoformat(),
                "event": report_event.reason or details.get("event") or "Ticket event",
                "owner": details.get("owner")
                or getattr(db.get(User, report_event.actor_user_id), "full_name", "")
                or "Support team",
                "source": "SYSTEM",
                "included": True,
            }
        )
    timeline.sort(key=lambda item: str(item["time"]))
    return {
        "ticket_number": ticket.ticket_number,
        "ticket_type": ticket_type.name if ticket_type else "",
        "client": client.name if client else "",
        "status": status_row.name if status_row else "",
        "priority": ticket.priority,
        "subject": ticket.subject,
        "description": ticket.description,
        "impact": ticket.impact,
        "urgency": ticket.urgency,
        "affected_users": ticket.affected_users or "",
        "first_occurred_at": ticket.first_occurred_at.isoformat()
        if ticket.first_occurred_at
        else "",
        "assigned_engineer": getattr(assignee, "full_name", None)
        or getattr(assignee, "username", "")
        if assignee
        else "",
        "assigned_team": ticket.assigned_team or "",
        "source": (ticket.source_channel or "").replace("_", " ").title(),
        "product": product.name if product else "",
        "module": module.name if module else "",
        "service": service.name if service else "",
        "environment": environment.name if environment else "",
        "category": category.name if category else ticket.category or "",
        "subcategory": subcategory.name if subcategory else ticket.subcategory or "",
        "work_performed": [
            {
                "id": f"system-worklog-{item.id}",
                "time": item.started_at.isoformat(),
                "engineer": getattr(worklog_users.get(item.user_id), "full_name", ""),
                "action": item.notes,
                "result": "Completed",
                "source": "SYSTEM",
                "included": True,
            }
            for item in worklogs
        ],
        "resolution_summary": ticket.resolution_summary or "",
        "root_cause": ticket.root_cause_summary or "",
        "permanent_fix": ticket.permanent_fix_summary or "",
        "patient_safety": "Yes" if ticket.patient_safety_flag else "No",
        "security_incident": "Yes" if ticket.security_incident_flag else "No",
        "created_at": ticket.created_at.isoformat(),
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else "",
        "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else "",
        "sla_first_response_target_minutes": getattr(
            ticket, "sla_first_response_target_minutes", None
        ),
        "sla_first_response_actual_minutes": getattr(
            ticket, "sla_first_response_actual_minutes", None
        ),
        "sla_resolution_target_minutes": getattr(ticket, "sla_resolution_target_minutes", None),
        "sla_actual_business_minutes": getattr(ticket, "sla_actual_business_minutes", None),
        "executive_summary": "",
        "incident_owner": "",
        "technical_lead": "",
        "detection_time": "",
        "restoration_time": "",
        "business_impact": "",
        "detection_and_response": "",
        "timeline": timeline,
        "contributing_factors": "",
        "technical_evidence": "",
        "corrective_actions": [],
        "customer_confirmation": ticket.customer_confirmation_note or "",
        "client_communications": "",
        "closure_approval": "",
        "additional_notes": "",
        "attachments_references": "",
    }


def _read(db: Session, row: TicketReport) -> dict[str, Any]:
    ticket = db.get(Ticket, row.ticket_id)
    client = db.get(Client, ticket.client_id) if ticket else None
    version = (
        db.get(TicketReportVersion, row.published_version_id) if row.published_version_id else None
    )
    return {
        "id": row.id,
        "report_number": row.report_number,
        "ticket_id": row.ticket_id,
        "ticket_number": ticket.ticket_number if ticket else "",
        "client": client.name if client else "",
        "report_type": row.report_type,
        "expected_report_type": _expected_report_type(db, ticket) if ticket else row.report_type,
        "template_mismatch": bool(ticket and row.report_type != _expected_report_type(db, ticket)),
        "status": row.status,
        "title": row.title,
        "data": _payload(row),
        "published_version": version.version_number if version else None,
        "created_by_user_id": row.created_by_user_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _get(db: Session, report_id: int) -> TicketReport:
    row = db.get(TicketReport, report_id)
    if not row:
        raise NotFoundError("Report does not exist.")
    return row


def _version(db: Session, row: TicketReport) -> TicketReportVersion:
    version = (
        db.get(TicketReportVersion, row.published_version_id) if row.published_version_id else None
    )
    if not version:
        raise ConflictError(
            "REPORT_NOT_PUBLISHED", "Publish the report before exporting or sharing it."
        )
    return version


@router.get("")
def list_reports(
    search: str | None = Query(None, max_length=100),
    report_type: str | None = None,
    report_status: str | None = None,
    db: Session = Depends(get_db),
    _actor: User = Depends(require_permission("report.export")),
) -> list[dict[str, Any]]:
    stmt = (
        select(TicketReport)
        .join(Ticket, Ticket.id == TicketReport.ticket_id)
        .join(Client, Client.id == Ticket.client_id)
    )
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                TicketReport.report_number.ilike(pattern),
                Ticket.ticket_number.ilike(pattern),
                TicketReport.title.ilike(pattern),
                Client.name.ilike(pattern),
            )
        )
    if report_type:
        stmt = stmt.where(TicketReport.report_type == report_type)
    if report_status:
        stmt = stmt.where(TicketReport.status == report_status)
    return [
        _read(db, row) for row in db.scalars(stmt.order_by(TicketReport.updated_at.desc())).all()
    ]


@router.post("/tickets/{ticket_id}", status_code=status.HTTP_201_CREATED)
def create_report(
    ticket_id: int,
    data: ReportInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("report.export")),
) -> dict[str, Any]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError("Ticket does not exist.")
    ensure_ticket_access(db, actor, ticket)
    ticket_status = db.get(TicketStatus, ticket.status_id)
    if not ticket_status or ticket_status.code != "CLOSED":
        raise ConflictError(
            "TICKET_NOT_CLOSED", "Reports can only be prepared after the ticket is closed."
        )
    _ensure_matching_report_type(db, ticket, data.report_type)
    payload = {**_ticket_context(db, ticket), **data.data}
    row = TicketReport(
        report_number=f"RPT-{server_now():%Y}-{secrets.token_hex(4).upper()}",
        ticket_id=ticket.id,
        report_type=data.report_type,
        status="DRAFT",
        title=data.title,
        payload_json=json.dumps(payload, ensure_ascii=False),
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    db.add(row)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketReport",
            entity_id=str(row.id),
            action="ticket_report.created",
        )
    )
    db.commit()
    db.refresh(row)
    return _read(db, row)


@router.post("/tickets/{ticket_id}/events", status_code=status.HTTP_201_CREATED)
def add_ticket_report_event(
    ticket_id: int,
    data: TicketEventInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.comment.public")),
) -> dict[str, Any]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError("Ticket does not exist.")
    ensure_ticket_access(db, actor, ticket)
    owner = data.owner.strip() if data.owner else actor.full_name
    row = AuditLog(
        actor_user_id=actor.id,
        entity_type="Ticket",
        entity_id=str(ticket.id),
        action="ticket.report_event.added",
        reason=data.event.strip(),
        new_values_json=json.dumps(
            {"occurred_at": data.occurred_at.isoformat(), "owner": owner},
            ensure_ascii=False,
        ),
    )
    ticket.last_activity_at = server_now()
    ticket.version += 1
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "occurred_at": data.occurred_at,
        "event": data.event.strip(),
        "owner": owner,
    }


@router.get("/{report_id}")
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    _actor: User = Depends(require_permission("report.export")),
) -> dict[str, Any]:
    return _read(db, _get(db, report_id))


@router.patch("/{report_id}")
def update_report(
    report_id: int,
    data: ReportUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("report.export")),
) -> dict[str, Any]:
    row = _get(db, report_id)
    row.title, row.payload_json, row.updated_by_user_id, row.status = (
        data.title,
        json.dumps(data.data, ensure_ascii=False),
        actor.id,
        "DRAFT",
    )
    row.updated_at = server_now()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketReport",
            entity_id=str(row.id),
            action="ticket_report.updated",
        )
    )
    db.commit()
    db.refresh(row)
    return _read(db, row)


@router.post("/{report_id}/publish")
def publish_report(
    report_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("report.export")),
) -> dict[str, Any]:
    row = _get(db, report_id)
    ticket = db.get(Ticket, row.ticket_id)
    if not ticket:
        raise NotFoundError("Ticket does not exist.")
    _ensure_matching_report_type(db, ticket, row.report_type)
    number = (
        db.scalar(
            select(func.max(TicketReportVersion.version_number)).where(
                TicketReportVersion.report_id == row.id
            )
        )
        or 0
    ) + 1
    version = TicketReportVersion(
        report_id=row.id,
        version_number=number,
        title=row.title,
        payload_json=row.payload_json,
        published_by_user_id=actor.id,
    )
    db.add(version)
    db.flush()
    row.published_version_id = version.id
    row.status = "PUBLISHED"
    row.updated_at = server_now()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketReport",
            entity_id=str(row.id),
            action="ticket_report.published",
            new_values_json=json.dumps({"version": number}),
        )
    )
    db.commit()
    db.refresh(row)
    return _read(db, row)


NAVY = "071D49"
TEAL = "0E7490"
INK = "172033"
MUTED = "5F6B7A"
PALE = "F2F6F9"
LINE = "D8E1E8"


def _present(value: Any) -> bool:
    return value not in (None, "", [], {}) and str(value).strip().lower() not in {
        "not provided", "none", "null"
    }


def _text(value: Any) -> str:
    if not _present(value):
        return ""
    if isinstance(value, list):
        return "\n".join(
            f"{index}. {item}" for index, item in enumerate(value, 1) if _present(item)
        )
    return str(value).replace("\\\n", "\n").strip()


def _date(value: Any) -> str:
    raw = _text(value)
    if not raw:
        return ""
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed.strftime("%d %b %Y, %I:%M %p")
    except ValueError:
        return raw


def _duration(minutes: Any) -> str:
    if not _present(minutes):
        return ""
    try:
        total = int(float(str(minutes)))
    except ValueError:
        return _text(minutes)
    hours, remainder = divmod(total, 60)
    return f"{hours}h {remainder}m" if hours else f"{remainder}m"


def _structured_rows(value: Any, keys: tuple[str, ...]) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    return [
        {key: _text(item.get(key)) for key in keys}
        for item in value
        if isinstance(item, dict) and item.get("included", True)
    ]


def _report_content(
    version: TicketReportVersion, report_type: str
) -> tuple[dict[str, str], list[tuple[str, list[tuple[str, str]], str]]]:
    data = _payload(version)
    report_type = report_type.upper()
    meta = {
        "ticket_number": _text(data.get("ticket_number")),
        "ticket_type": _text(data.get("ticket_type")),
        "client": _text(data.get("client")),
        "status": _text(data.get("status")),
        "priority": _text(data.get("priority")),
        "subject": _text(data.get("subject")),
        "assigned_engineer": _text(data.get("assigned_engineer")),
        "assigned_team": _text(data.get("assigned_team")),
        "created_at": _date(data.get("created_at")),
        "resolved_at": _date(data.get("resolved_at")),
        "closed_at": _date(data.get("closed_at")),
    }

    def rows(
        items: list[tuple[str, Callable[[Any], str], Any]], *, keep_empty: bool = False
    ) -> list[tuple[str, str]]:
        result = [(label, transform(value)) for label, transform, value in items]
        return result if keep_empty else [(label, value) for label, value in result if value]

    overview = rows(
        [
            ("Ticket number", _text, data.get("ticket_number")),
            ("Ticket type", _text, data.get("ticket_type")),
            ("Client", _text, data.get("client")),
            ("Status", _text, data.get("status")),
            ("Priority", _text, data.get("priority")),
            ("Impact", _text, data.get("impact")),
            ("Urgency", _text, data.get("urgency")),
            ("Affected users", _text, data.get("affected_users")),
            ("Assigned engineer", _text, data.get("assigned_engineer")),
            ("Support team", _text, data.get("assigned_team")),
        ]
    )
    lifecycle = rows(
        [
            ("Created", _date, data.get("created_at")),
            ("First occurrence", _date, data.get("first_occurred_at")),
            ("Resolved", _date, data.get("resolved_at")),
            ("Closed", _date, data.get("closed_at")),
            ("First response target", _duration, data.get("sla_first_response_target_minutes")),
            ("First response actual", _duration, data.get("sla_first_response_actual_minutes")),
            ("Resolution target", _duration, data.get("sla_resolution_target_minutes")),
            ("Resolution actual", _duration, data.get("sla_actual_business_minutes")),
        ]
    )
    classification = rows(
        [
            ("Product", _text, data.get("product")),
            ("Module", _text, data.get("module")),
            ("Service", _text, data.get("service")),
            ("Environment", _text, data.get("environment")),
            ("Category", _text, data.get("category")),
            ("Subcategory", _text, data.get("subcategory")),
            ("Source", _text, data.get("source")),
        ]
    )
    work_performed = [
        (
            _date(item.get("time")),
            " | ".join(
                [
                    _text(item.get("engineer")) or "Support engineer",
                    _text(item.get("action")),
                    _text(item.get("result")) or "Completed",
                ]
            ),
        )
        for item in data.get("work_performed", [])
        if isinstance(item, dict)
    ]
    ticket_resolution = rows(
        [
            ("Resolution summary", _text, data.get("resolution_summary")),
            ("Customer confirmation", _text, data.get("customer_confirmation")),
            ("Additional notes", _text, data.get("additional_notes")),
            ("Attachments and references", _text, data.get("attachments_references")),
        ]
    )
    if report_type == "TICKET":
        return meta, [
            ("Ticket summary", overview, "facts"),
            ("Request details", [("Description", _text(data.get("description")))], "narrative"),
            ("Classification", classification, "facts"),
            ("Work performed", work_performed, "worklog"),
            ("Resolution and outcome", ticket_resolution, "narrative"),
            ("SLA result", lifecycle, "facts"),
        ]

    executive_conclusion = rows(
        [("Executive conclusion", _text, data.get("executive_summary"))]
    )
    impact = rows(
        [
            ("Business and operational impact", _text, data.get("business_impact")),
            ("Affected users", _text, data.get("affected_users")),
            ("Patient safety impact", _text, data.get("patient_safety")),
            ("Security impact", _text, data.get("security_incident")),
        ]
    )
    ownership = rows(
        [
            ("Incident owner", _text, data.get("incident_owner")),
            ("Technical lead", _text, data.get("technical_lead")),
            ("Detection time", _date, data.get("detection_time")),
            ("Service restoration time", _date, data.get("restoration_time")),
        ]
    )
    response = rows(
        [
            ("Detection and response", _text, data.get("detection_and_response")),
            ("Technical evidence", _text, data.get("technical_evidence")),
        ]
    )
    timeline = [
        (
            _date(item.get("time")),
            " | ".join([_text(item.get("event")), _text(item.get("owner"))]),
        )
        for item in _structured_rows(data.get("timeline"), ("time", "event", "owner"))
        if _present(item.get("event"))
    ]
    corrective_actions = [
        (
            _text(item.get("action")),
            " | ".join(
                [
                    _text(item.get("owner")),
                    _date(item.get("due_date")),
                    _text(item.get("status")),
                ]
            ),
        )
        for item in _structured_rows(
            data.get("corrective_actions"), ("action", "owner", "due_date", "status")
        )
        if _present(item.get("action"))
    ]
    analysis = rows(
        [
            ("Root cause", _text, data.get("root_cause")),
            ("Contributing factors", _text, data.get("contributing_factors")),
            ("Resolution and recovery", _text, data.get("resolution_summary")),
            ("Permanent fix", _text, data.get("permanent_fix")),
        ]
    )
    closure = rows(
        [
            ("Client communications", _text, data.get("client_communications")),
            ("Closure approval", _text, data.get("closure_approval")),
            ("Attachments and references", _text, data.get("attachments_references")),
        ]
    )
    return meta, [
        ("Executive conclusion", executive_conclusion, "narrative"),
        ("Incident identification", overview + ownership, "facts"),
        ("Business and safety impact", impact, "narrative"),
        ("Detection and response", response, "narrative"),
        ("Incident timeline", timeline, "timeline"),
        ("Root cause analysis", analysis, "narrative"),
        ("Corrective and preventive actions", corrective_actions, "actions"),
        ("Communication and closure", closure, "narrative"),
        ("SLA and communications", lifecycle, "facts"),
    ]


def _shade_cell(cell: Any, fill: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    shade = properties.find(qn("w:shd"))
    if shade is None:
        shade = OxmlElement("w:shd")
        properties.append(shade)
    shade.set(qn("w:fill"), fill)


def _cell_margins(cell: Any, top: int = 120, start: int = 150, bottom: int = 120, end: int = 150) -> None:
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = tcPr.first_child_found_in("w:tcMar")
    if tcMar is None:
        tcMar = OxmlElement("w:tcMar")
        tcPr.append(tcMar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tcMar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tcMar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def _keep_docx_table_together(table: Any) -> None:
    for row_index, row in enumerate(table.rows):
        row_properties = row._tr.get_or_add_trPr()
        cant_split = OxmlElement("w:cantSplit")
        row_properties.append(cant_split)
        if row_index < len(table.rows) - 1:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.keep_with_next = True


def _docx(version: TicketReportVersion, report_number: str, report_type: str) -> bytes:
    meta, sections = _report_content(version, report_type)
    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Inches(0.72)
    sec.top_margin, sec.bottom_margin = Inches(0.72), Inches(0.68)
    styles = doc.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(10)
    styles["Normal"].font.color.rgb = RGBColor.from_string(INK)
    for style_name, size in (("Title", 25), ("Heading 1", 15), ("Heading 2", 11)):
        style = styles[style_name]
        style.font.name = "Aptos Display"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string("000000")

    header = sec.header
    htable = header.add_table(rows=1, cols=2, width=Inches(6.82))
    htable.columns[0].width, htable.columns[1].width = Inches(4.9), Inches(1.92)
    left, right = htable.rows[0].cells
    _cell_margins(left, 0, 0, 55, 0); _cell_margins(right, 0, 0, 55, 0)
    p = left.paragraphs[0]
    run = p.add_run("MILLENSYS")
    run.bold = True; run.font.size = Pt(11); run.font.color.rgb = RGBColor.from_string(NAVY)
    run = p.add_run("\nSUPPORT HUB")
    run.font.size = Pt(7); run.font.color.rgb = RGBColor.from_string(TEAL)
    p = right.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run("CLIENT REPORT\n")
    run.bold = True; run.font.size = Pt(7.5); run.font.color.rgb = RGBColor.from_string(NAVY)
    run = p.add_run(report_number)
    run.font.size = Pt(7.5); run.font.color.rgb = RGBColor.from_string(MUTED)

    footer = sec.footer
    ftable = footer.add_table(rows=1, cols=3, width=Inches(6.82))
    for cell in ftable.rows[0].cells:
        _cell_margins(cell, 55, 0, 0, 0)
    values = ["MILLENSYS", "Technology for a Healthier Globe", f"{report_number}  |  v{version.version_number}"]
    aligns = [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.RIGHT]
    for cell, value, align in zip(ftable.rows[0].cells, values, aligns, strict=True):
        paragraph = cell.paragraphs[0]; paragraph.alignment = align
        run = paragraph.add_run(value); run.font.size = Pt(7); run.font.color.rgb = RGBColor.from_string(MUTED)

    title = doc.add_paragraph(style="Title")
    title.add_run("Incident Report" if report_type == "INCIDENT" else "Ticket Service Report")
    intro = doc.add_paragraph()
    intro.paragraph_format.space_after = Pt(5)
    run = intro.add_run(version.title); run.bold = True; run.font.size = Pt(13)
    subtitle = doc.add_paragraph()
    subtitle.paragraph_format.space_after = Pt(13)
    run = subtitle.add_run(
        f"Prepared for {meta['client'] or 'the client'}  |  Ticket {meta['ticket_number']}  |  Published {_date(version.published_at)}"
    )
    run.font.size = Pt(9); run.font.color.rgb = RGBColor.from_string(MUTED)

    summary = doc.add_table(rows=2, cols=4)
    summary.autofit = False
    summary_values = [
        ("CLIENT", meta["client"]), ("TICKET", meta["ticket_number"]),
        ("PRIORITY", meta["priority"]), ("STATUS", meta["status"]),
    ]
    for index, (label, value) in enumerate(summary_values):
        cell = summary.cell(index // 2, (index % 2) * 2)
        value_cell = summary.cell(index // 2, (index % 2) * 2 + 1)
        for target in (cell, value_cell):
            target.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            _cell_margins(target, 75, 105, 75, 105)
        _shade_cell(cell, NAVY); _shade_cell(value_cell, "FFFFFF")
        p = cell.paragraphs[0]; r = p.add_run(label); r.bold = True; r.font.size = Pt(8); r.font.color.rgb = RGBColor(255, 255, 255)
        p = value_cell.paragraphs[0]; r = p.add_run(value or "-"); r.bold = True; r.font.size = Pt(9.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)

    if meta["subject"]:
        heading = doc.add_heading("Subject", level=2)
        heading.paragraph_format.space_before = Pt(6); heading.paragraph_format.space_after = Pt(3)
        paragraph = doc.add_paragraph(meta["subject"])
        paragraph.paragraph_format.space_after = Pt(8)

    for heading, rows, layout in sections:
        rows = [(label, value) for label, value in rows if value]
        if not rows:
            continue
        h = doc.add_heading(heading, level=1)
        h.paragraph_format.space_before = Pt(11); h.paragraph_format.space_after = Pt(5)
        if layout == "facts":
            table = doc.add_table(rows=0, cols=2)
            table.autofit = False
            for index, (label, value) in enumerate(rows):
                cells = table.add_row().cells
                _shade_cell(cells[0], PALE if index % 2 == 0 else "FFFFFF")
                _shade_cell(cells[1], PALE if index % 2 == 0 else "FFFFFF")
                for cell in cells:
                    _cell_margins(cell, 65, 105, 65, 105); cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                r = cells[0].paragraphs[0].add_run(label); r.bold = True; r.font.size = Pt(8.25); r.font.color.rgb = RGBColor.from_string(MUTED)
                r = cells[1].paragraphs[0].add_run(value); r.font.size = Pt(8.75)
            _keep_docx_table_together(table)
        elif layout in {"worklog", "timeline", "actions"}:
            columns = {
                "worklog": ["Time", "Engineer", "Action", "Result"],
                "timeline": ["Time", "Event", "Owner"],
                "actions": ["Action", "Owner", "Due", "Status"],
            }[layout]
            table = doc.add_table(rows=1, cols=len(columns))
            headers = columns
            for cell, label in zip(table.rows[0].cells, headers, strict=True):
                _shade_cell(cell, NAVY); _cell_margins(cell, 65, 90, 65, 90)
                r = cell.paragraphs[0].add_run(label); r.bold = True; r.font.size = Pt(7.5); r.font.color.rgb = RGBColor(255, 255, 255)
            for index, (first_value, packed) in enumerate(rows):
                expected = len(columns) - 1
                parts = (packed.split(" | ", expected - 1) + [""] * expected)[:expected]
                cells = table.add_row().cells
                for cell, value in zip(cells, [first_value, *parts], strict=True):
                    _shade_cell(cell, PALE if index % 2 == 0 else "FFFFFF"); _cell_margins(cell, 60, 90, 60, 90)
                    r = cell.paragraphs[0].add_run(value); r.font.size = Pt(8)
            _keep_docx_table_together(table)
        else:
            for label, value in rows:
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(4); p.paragraph_format.space_after = Pt(2)
                r = p.add_run(label.upper()); r.bold = True; r.font.size = Pt(8); r.font.color.rgb = RGBColor.from_string(TEAL)
                for line in value.splitlines() or [value]:
                    p = doc.add_paragraph(line)
                    p.paragraph_format.left_indent = Inches(0.08)
                    p.paragraph_format.space_after = Pt(4)

    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()


def _pdf(version: TicketReportVersion, report_number: str, report_type: str) -> bytes:
    output = io.BytesIO()
    meta, sections = _report_content(version, report_type)
    styles = getSampleStyleSheet()
    body = ParagraphStyle("ReportBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=12.5, textColor=colors.HexColor(f"#{INK}"), spaceAfter=2)
    label_style = ParagraphStyle("ReportLabel", parent=body, fontSize=7.5, leading=9, textColor=colors.HexColor(f"#{MUTED}"), fontName="Helvetica-Bold")
    summary_label_style = ParagraphStyle("SummaryLabel", parent=label_style, fontSize=8.5, leading=11, textColor=colors.white)
    summary_value_style = ParagraphStyle("SummaryValue", parent=body, fontSize=10, leading=12, textColor=colors.HexColor(f"#{NAVY}"), fontName="Helvetica-Bold")
    section_style = ParagraphStyle("ReportSection", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=colors.HexColor(f"#{NAVY}"), spaceBefore=12, spaceAfter=7, keepWithNext=True)
    narrative_label = ParagraphStyle("NarrativeLabel", parent=label_style, textColor=colors.HexColor(f"#{TEAL}"), spaceBefore=5, spaceAfter=2)
    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=25, leading=29, textColor=colors.HexColor(f"#{NAVY}"), alignment=TA_LEFT, spaceAfter=5)
    subtitle_style = ParagraphStyle("ReportSubtitle", parent=body, fontSize=9, textColor=colors.HexColor(f"#{MUTED}"), spaceAfter=12)

    def para(value: str, style: ParagraphStyle = body) -> Paragraph:
        return Paragraph(escape(value).replace("\n", "<br/>"), style)

    story: list[Any] = [
        para("INCIDENT REPORT" if report_type == "INCIDENT" else "TICKET SERVICE REPORT", label_style),
        Paragraph(escape(version.title), title_style),
        para(
            f"Prepared for {meta['client'] or 'the client'}  |  Ticket {meta['ticket_number']}  |  Published {_date(version.published_at)}",
            subtitle_style,
        ),
    ]
    summary_data = [
        [para("CLIENT", summary_label_style), para(meta["client"] or "-", summary_value_style), para("TICKET", summary_label_style), para(meta["ticket_number"] or "-", summary_value_style)],
        [para("PRIORITY", summary_label_style), para(meta["priority"] or "-", summary_value_style), para("STATUS", summary_label_style), para(meta["status"] or "-", summary_value_style)],
    ]
    story.append(Table(summary_data, colWidths=[23 * mm, 59 * mm, 23 * mm, 59 * mm], style=TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(f"#{NAVY}")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor(f"#{NAVY}")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white), ("TEXTCOLOR", (2, 0), (2, -1), colors.white),
        ("BACKGROUND", (1, 0), (1, -1), colors.white), ("BACKGROUND", (3, 0), (3, -1), colors.white),
        ("GRID", (0, 0), (-1, -1), .5, colors.HexColor(f"#{LINE}")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ])))
    if meta["subject"]:
        story.extend([Spacer(1, 5 * mm), para("SUBJECT", narrative_label), para(meta["subject"])])
    for heading, rows, layout in sections:
        rows = [(label, value) for label, value in rows if value]
        if not rows:
            continue
        section_heading = Paragraph(escape(heading), section_style)
        story.append(section_heading)
        if layout == "facts":
            table_rows = [[para(label, label_style), para(value)] for label, value in rows]
            commands: list[tuple[Any, ...]] = [
                ("GRID", (0, 0), (-1, -1), .45, colors.HexColor(f"#{LINE}")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
            for index in range(len(table_rows)):
                if index % 2 == 0:
                    commands.append(("BACKGROUND", (0, index), (-1, index), colors.HexColor(f"#{PALE}")))
            table = Table(table_rows, colWidths=[47 * mm, 117 * mm], style=TableStyle(commands))
            story.pop()
            story.append(KeepTogether([section_heading, table]))
        elif layout in {"worklog", "timeline", "actions"}:
            columns = {
                "worklog": (["TIME", "ENGINEER", "ACTION", "RESULT"], [28, 35, 77, 24]),
                "timeline": (["TIME", "EVENT", "OWNER"], [35, 94, 35]),
                "actions": (["ACTION", "OWNER", "DUE", "STATUS"], [76, 34, 28, 26]),
            }[layout]
            work_rows: list[list[Paragraph]] = [[para(value, label_style) for value in columns[0]]]
            expected = len(columns[0]) - 1
            for first_value, packed in rows:
                parts = (packed.split(" | ", expected - 1) + [""] * expected)[:expected]
                work_rows.append([para(first_value), *[para(part) for part in parts]])
            commands = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(f"#{NAVY}")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), .45, colors.HexColor(f"#{LINE}")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
            for index in range(1, len(work_rows), 2):
                commands.append(("BACKGROUND", (0, index), (-1, index), colors.HexColor(f"#{PALE}")))
            table = Table(work_rows, colWidths=[value * mm for value in columns[1]], repeatRows=1, style=TableStyle(commands))
            story.pop()
            story.append(KeepTogether([section_heading, table]))
        else:
            blocks: list[Any] = []
            for label, value in rows:
                blocks.extend([para(label.upper(), narrative_label), para(value), Spacer(1, 1.5 * mm)])
            story.extend(blocks)

    def decorate(canvas: Any, document: Any) -> None:
        width, height = A4
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(f"#{NAVY}")); canvas.rect(0, height - 20 * mm, width, 20 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white); canvas.setFont("Helvetica-Bold", 12); canvas.drawString(16 * mm, height - 10.5 * mm, "MILLENSYS")
        canvas.setFillColor(colors.HexColor("#BAE6FD")); canvas.setFont("Helvetica", 7); canvas.drawString(16 * mm, height - 14.5 * mm, "SUPPORT HUB")
        canvas.setFillColor(colors.white); canvas.setFont("Helvetica-Bold", 7.5); canvas.drawRightString(width - 16 * mm, height - 11 * mm, "CLIENT REPORT")
        canvas.setFillColor(colors.HexColor(f"#{NAVY}")); canvas.rect(0, 0, width, 13 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white); canvas.setFont("Helvetica", 7); canvas.drawString(16 * mm, 5.3 * mm, "MILLENSYS  |  Technology for a Healthier Globe")
        canvas.drawRightString(width - 16 * mm, 5.3 * mm, f"{report_number}  |  v{version.version_number}  |  Page {document.page}")
        canvas.restoreState()

    SimpleDocTemplate(output, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=27 * mm, bottomMargin=19 * mm, title=version.title, author="Millensys Support Hub").build(story, onFirstPage=decorate, onLaterPages=decorate)
    return output.getvalue()


@router.get("/{report_id}/export.{format}")
def export_report(
    report_id: int,
    format: Literal["docx", "pdf"],
    db: Session = Depends(get_db),
    _actor: User = Depends(require_permission("report.export")),
) -> Response:
    row = _get(db, report_id)
    version = _version(db, row)
    content = (
        _pdf(version, row.report_number, row.report_type)
        if format == "pdf"
        else _docx(version, row.report_number, row.report_type)
    )
    media = (
        "application/pdf"
        if format == "pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return Response(
        content,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="{row.report_number}-v{version.version_number}.{format}"'
        },
    )


@router.get("/{report_id}/share-links")
def list_links(
    report_id: int,
    db: Session = Depends(get_db),
    _actor: User = Depends(require_permission("report.export")),
) -> list[dict[str, Any]]:
    row = _get(db, report_id)
    versions = select(TicketReportVersion.id).where(TicketReportVersion.report_id == row.id)
    return [
        {
            "id": link.id,
            "version_id": link.version_id,
            "recipient_name": link.recipient_name,
            "recipient_email": link.recipient_email,
            "allow_download": link.allow_download,
            "created_at": link.created_at,
            "expires_at": link.expires_at,
            "revoked_at": link.revoked_at,
        }
        for link in db.scalars(
            select(TicketReportShareLink)
            .where(TicketReportShareLink.version_id.in_(versions))
            .order_by(TicketReportShareLink.id.desc())
        )
    ]


@router.post("/{report_id}/share-links", status_code=status.HTTP_201_CREATED)
def create_link(
    report_id: int,
    data: ShareInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("report.export")),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    row = _get(db, report_id)
    version = _version(db, row)
    token = secrets.token_urlsafe(32)
    now = server_now()
    link = TicketReportShareLink(
        version_id=version.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        recipient_name=data.recipient_name,
        recipient_email=data.recipient_email,
        allow_download=data.allow_download,
        created_by_user_id=actor.id,
        created_at=now,
        expires_at=now + timedelta(days=data.expires_in_days),
    )
    db.add(link)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketReportShareLink",
            entity_id=str(link.id),
            action="ticket_report.share.created",
        )
    )
    db.commit()
    return {
        "id": link.id,
        "url": f"{settings.frontend_base_url}/shared/reports/{token}",
        "expires_at": link.expires_at,
        "allow_download": link.allow_download,
    }


@router.post("/{report_id}/share-links/{link_id}/revoke")
def revoke_link(
    report_id: int,
    link_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("report.export")),
) -> dict[str, Any]:
    row = _get(db, report_id)
    link = db.get(TicketReportShareLink, link_id)
    version = db.get(TicketReportVersion, link.version_id) if link else None
    if not link or not version or version.report_id != row.id:
        raise NotFoundError("Share link does not exist.")
    link.revoked_at = link.revoked_at or server_now()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="TicketReportShareLink",
            entity_id=str(link.id),
            action="ticket_report.share.revoked",
        )
    )
    db.commit()
    return {"id": link.id, "revoked_at": link.revoked_at}


def _public(
    db: Session, token: str
) -> tuple[TicketReportShareLink, TicketReportVersion, TicketReport]:
    if not 40 <= len(token) <= 100:
        raise NotFoundError("Shared report does not exist.")
    link = db.scalar(
        select(TicketReportShareLink).where(
            TicketReportShareLink.token_hash == hashlib.sha256(token.encode()).hexdigest()
        )
    )

    def aware(value: Any) -> Any:
        return value if value.tzinfo else value.replace(tzinfo=server_timezone())

    if not link or link.revoked_at or aware(link.expires_at) <= server_now():
        raise NotFoundError("Shared report does not exist.")
    version = db.get(TicketReportVersion, link.version_id)
    report = db.get(TicketReport, version.report_id) if version else None
    if not version or not report:
        raise NotFoundError("Shared report does not exist.")
    return link, version, report


@public_router.get("/{token}")
def public_report(token: str, response: Response, db: Session = Depends(get_db)) -> dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"
    link, version, report = _public(db, token)
    meta, sections = _report_content(version, report.report_type)
    return {
        "report_number": report.report_number,
        "report_type": report.report_type,
        "title": version.title,
        "version": version.version_number,
        "published_at": version.published_at,
        "expires_at": link.expires_at,
        "allow_download": link.allow_download,
        "meta": meta,
        "sections": [
            {
                "title": h,
                "layout": layout,
                "rows": [{"label": k, "value": v} for k, v in rows if v],
            }
            for h, rows, layout in sections
            if rows
        ],
    }


@public_router.get("/{token}/download.pdf")
def public_pdf(token: str, db: Session = Depends(get_db)) -> Response:
    link, version, report = _public(db, token)
    if not link.allow_download:
        raise ConflictError("DOWNLOAD_DISABLED", "Downloading is disabled for this shared report.")
    return Response(
        _pdf(version, report.report_number, report.report_type),
        media_type="application/pdf",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{report.report_number}-v{version.version_number}.pdf"',
        },
    )
