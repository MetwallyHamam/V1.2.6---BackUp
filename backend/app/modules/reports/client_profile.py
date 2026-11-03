import io
from collections import Counter
from datetime import date, datetime, time, timedelta
from typing import Any, cast
from zoneinfo import ZoneInfo

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now, server_timezone
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.client_portal.routes import portal_contract_insights
from app.modules.clients.models import (
    Branch,
    City,
    Client,
    ClientInstallation,
    ClientLocation,
    Contact,
    Country,
    Product,
    ProductModule,
    ServiceCatalogItem,
)
from app.modules.contracts.models import BusinessCalendarDay, Contract
from app.modules.iam.models import AuditLog, User
from app.modules.internal_operations.models import InternalOperation, InternalOperationAssignee
from app.modules.service_checklists.models import (
    ServiceChecklistOccurrence,
    ServiceChecklistOccurrenceItem,
)
from app.modules.service_management.models import Problem, ProblemTicketLink
from app.modules.sla.service import resolution_sla_results
from app.modules.tickets.models import Ticket, TicketStatus, TicketType
from app.modules.uat.models import DeploymentPlan, UatCycle

router = APIRouter(prefix="/reports", tags=["reports"])
NAVY = "123B5D"
BLUE = "1677A6"
TEAL = "00A0A8"
LIGHT = "EAF3F7"
WHITE = "FFFFFF"
MUTED = "607D8B"
GREEN = "2E7D32"
AMBER = "ED6C02"
RED = "D32F2F"
PALETTE = (BLUE, TEAL, "7E57C2", AMBER, GREEN, RED, "546E7A")


def _shade(cell: object, color: str) -> None:
    properties = cell._tc.get_or_add_tcPr()  # type: ignore[attr-defined]
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), color)
    properties.append(shading)


def _cell_border(cell: object, color: str = "D7E3EA", size: str = "8") -> None:
    properties = cell._tc.get_or_add_tcPr()  # type: ignore[attr-defined]
    borders = properties.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        properties.append(borders)
    for edge in ("top", "left", "bottom", "right"):
        node = OxmlElement(f"w:{edge}")
        node.set(qn("w:val"), "single")
        node.set(qn("w:sz"), size)
        node.set(qn("w:color"), color)
        borders.append(node)


def _set_cell_text(
    cell: Any, text: object, *, size: int = 10, color: str = NAVY, bold: bool = False
) -> None:
    cell.text = str(text)
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.runs[0]
    run.bold = bold
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)


def _add_panel_title(document: Any, title: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(8)
    paragraph.paragraph_format.space_after = Pt(5)
    run = paragraph.add_run(title)
    run.bold = True
    run.font.size = Pt(15)
    run.font.color.rgb = RGBColor.from_string(NAVY)


def _add_kpi_cards(document: Any, metrics: dict[str, Any]) -> None:
    cards = (
        ("Total tickets", metrics.get("total_requests", 0)),
        (
            "SLA compliance %",
            metrics.get("sla_compliance_percent")
            if metrics.get("sla_compliance_percent") is not None
            else "—",
        ),
        ("SLA breaches", metrics.get("sla_breached", 0)),
        ("Critical incidents", metrics.get("critical_incidents", 0)),
        ("Business hours saved", metrics.get("saved_business_hours", 0)),
        ("Services provided", metrics.get("services_provided", 0)),
        ("Total working hours", metrics.get("total_working_hours", 0)),
    )
    table = document.add_table(rows=3, cols=3)
    for index, (label, value) in enumerate(cards):
        cell = table.cell(index // 3, index % 3)
        _shade(cell, WHITE)
        _cell_border(cell)
        _set_cell_text(cell, value, size=23, color=BLUE, bold=True)
        label_run = cell.add_paragraph().add_run(label)
        label_run.font.size = Pt(9)
        label_run.font.color.rgb = RGBColor.from_string(MUTED)


def _add_distribution_panel(document: Any, title: str, values: dict[str, object]) -> None:
    _add_panel_title(document, title)
    numeric = {label: int(str(value)) for label, value in values.items()}
    maximum = max(numeric.values(), default=1)
    table = document.add_table(rows=0, cols=3)
    for index, (label, value) in enumerate(
        sorted(numeric.items(), key=lambda item: (-item[1], item[0]))
    ):
        cells = table.add_row().cells
        _set_cell_text(cells[0], label, bold=True)
        bar = "■" * max(1, round(value * 24 / maximum)) if value else "—"
        _set_cell_text(cells[1], bar, color=PALETTE[index % len(PALETTE)])
        _set_cell_text(cells[2], value, color=MUTED, bold=True)


def _impact(area: str, level: str, consequence: str, evidence: str, action: str) -> dict[str, str]:
    return {
        "area": area,
        "level": level,
        "consequence": consequence,
        "evidence": evidence,
        "action": action,
    }


def client_profile_data(
    db: Session, client_id: int, date_from: date, date_to: date, actor: User
) -> dict[str, Any]:
    if date_to < date_from:
        raise ConflictError(
            "INVALID_REPORT_PERIOD", "The report end date must be on or after its start date."
        )
    client = db.get(Client, client_id)
    if not client:
        raise NotFoundError("Client does not exist.")
    base = portal_contract_insights(date_from, date_to, client_id, db, actor)
    days = (date_to - date_from).days + 1
    previous_to = date_from - timedelta(days=1)
    previous_from = previous_to - timedelta(days=days - 1)
    previous = portal_contract_insights(previous_from, previous_to, client_id, db, actor)
    metrics = cast(dict[str, Any], base["metrics"])
    previous_metrics = cast(dict[str, Any], previous["metrics"])
    start = datetime.combine(date_from, time.min, server_timezone())
    end = datetime.combine(date_to + timedelta(days=1), time.min, server_timezone())
    tickets = list(
        db.scalars(
            select(Ticket).where(
                Ticket.client_id == client_id, Ticket.created_at >= start, Ticket.created_at < end
            )
        )
    )
    statuses = {item.id: item for item in db.scalars(select(TicketStatus))}
    ticket_types = {item.id: item for item in db.scalars(select(TicketType))}
    incident_tickets = [
        item
        for item in tickets
        if item.ticket_type_id in ticket_types
        and ticket_types[item.ticket_type_id].code == "INCIDENT"
    ]
    change_tickets = [
        item
        for item in tickets
        if item.ticket_type_id in ticket_types
        and ticket_types[item.ticket_type_id].code == "CHANGE_REQUEST"
    ]
    uat_cycles = list(
        db.scalars(
            select(UatCycle)
            .where(
                UatCycle.client_id == client_id,
                UatCycle.created_at >= start,
                UatCycle.created_at < end,
            )
            .order_by(UatCycle.created_at.desc())
        )
    )
    deployments = list(
        db.scalars(
            select(DeploymentPlan)
            .where(
                DeploymentPlan.client_id == client_id,
                DeploymentPlan.created_at >= start,
                DeploymentPlan.created_at < end,
            )
            .order_by(DeploymentPlan.created_at.desc())
        )
    )
    ticket_ids = {item.id for item in tickets}
    problem_ids = (
        set(
            db.scalars(
                select(ProblemTicketLink.problem_id).where(
                    ProblemTicketLink.ticket_id.in_(ticket_ids)
                )
            )
        )
        if ticket_ids
        else set()
    )
    problems = (
        list(
            db.scalars(
                select(Problem)
                .where(Problem.id.in_(problem_ids))
                .order_by(Problem.created_at.desc())
            )
        )
        if problem_ids
        else []
    )
    lifecycle = {
        "uat": {
            "count": len(uat_cycles),
            "active": sum(item.status != "COMPLETED" for item in uat_cycles),
            "records": [
                {
                    "id": item.id,
                    "number": item.code,
                    "title": item.title,
                    "status": item.status,
                    "route": "/uat",
                }
                for item in uat_cycles[:10]
            ],
        },
        "deployments": {
            "count": len(deployments),
            "active": sum(item.status != "COMPLETED" for item in deployments),
            "records": [
                {
                    "id": item.id,
                    "number": item.code,
                    "title": item.name,
                    "status": item.status,
                    "route": "/uat",
                }
                for item in deployments[:10]
            ],
        },
        "incidents": {
            "count": len(incident_tickets),
            "active": sum(item.closed_at is None for item in incident_tickets),
            "records": [
                {
                    "id": item.id,
                    "number": item.ticket_number,
                    "title": item.subject,
                    "status": statuses[item.status_id].name
                    if item.status_id in statuses
                    else "Unknown",
                    "route": f"/tickets/{item.id}",
                }
                for item in sorted(
                    incident_tickets, key=lambda value: value.created_at, reverse=True
                )[:10]
            ],
        },
        "changes": {
            "count": len(change_tickets),
            "active": sum(item.closed_at is None for item in change_tickets),
            "records": [
                {
                    "id": item.id,
                    "number": item.ticket_number,
                    "title": item.subject,
                    "status": statuses[item.status_id].name
                    if item.status_id in statuses
                    else "Unknown",
                    "route": f"/tickets/{item.id}/change-request",
                }
                for item in sorted(
                    change_tickets, key=lambda value: value.created_at, reverse=True
                )[:10]
            ],
        },
        "problems": {
            "count": len(problems),
            "active": sum(item.status not in {"RESOLVED", "CLOSED"} for item in problems),
            "records": [
                {
                    "id": item.id,
                    "number": item.problem_number,
                    "title": item.title,
                    "status": item.status,
                    "route": f"/problems/{item.id}",
                }
                for item in problems[:10]
            ],
        },
    }
    products = {item.id: item.name for item in db.scalars(select(Product))}
    modules = {item.id: item.name for item in db.scalars(select(ProductModule))}
    services = {item.id: item.name for item in db.scalars(select(ServiceCatalogItem))}
    contracts = {
        item.id: item
        for item in db.scalars(
            select(Contract).where(
                Contract.id.in_({item.contract_id for item in tickets if item.contract_id} or {-1})
            )
        )
    }
    calendar_ids = {item.calendar_id for item in contracts.values()}
    calendar_days: dict[tuple[int, int], BusinessCalendarDay] = {}
    if calendar_ids:
        for row in db.scalars(
            select(BusinessCalendarDay).where(BusinessCalendarDay.calendar_id.in_(calendar_ids))
        ):
            calendar_days[(row.calendar_id, row.weekday)] = row
    in_hours = 0
    out_hours = 0
    for ticket in tickets:
        contract = contracts.get(ticket.contract_id) if ticket.contract_id else None
        if not contract:
            out_hours += 1
            continue
        local = ticket.created_at.replace(tzinfo=server_timezone()).astimezone(
            ZoneInfo(contract.timezone)
        )
        schedule = calendar_days.get((contract.calendar_id, local.weekday()))
        if (
            schedule
            and schedule.is_working_day
            and schedule.start_time <= local.time().replace(tzinfo=None) <= schedule.end_time
        ):
            in_hours += 1
        else:
            out_hours += 1
    operations = list(
        db.scalars(
            select(InternalOperation).where(
                InternalOperation.client_id == client_id,
                InternalOperation.starts_at >= start,
                InternalOperation.starts_at < end,
            )
        )
    )
    completed_operations = [item for item in operations if item.status == "COMPLETED"]
    completed_checklists = int(
        db.scalar(
            select(func.count(ServiceChecklistOccurrence.id)).where(
                ServiceChecklistOccurrence.client_id == client_id,
                ServiceChecklistOccurrence.completed_at >= start,
                ServiceChecklistOccurrence.completed_at < end,
            )
        )
        or 0
    )
    checklists_needing_attention = int(
        db.scalar(
            select(func.count(func.distinct(ServiceChecklistOccurrence.id)))
            .outerjoin(
                ServiceChecklistOccurrenceItem,
                ServiceChecklistOccurrenceItem.occurrence_id == ServiceChecklistOccurrence.id,
            )
            .where(
                ServiceChecklistOccurrence.client_id == client_id,
                ServiceChecklistOccurrence.status.not_in(("COMPLETED", "CANCELLED")),
                or_(
                    ServiceChecklistOccurrence.status == "BLOCKED",
                    ServiceChecklistOccurrence.due_at < server_now(),
                    ServiceChecklistOccurrenceItem.state == "NEED_ATTENTION",
                ),
            )
        )
        or 0
    )
    operation_types = Counter(item.operation_type for item in completed_operations)
    operation_ids = {item.id for item in completed_operations}
    assignee_counts = Counter(
        db.scalars(
            select(InternalOperationAssignee.operation_id).where(
                InternalOperationAssignee.operation_id.in_(operation_ids or {-1})
            )
        )
    )
    working_hours = round(
        sum(
            max(0.0, (item.ends_at - item.starts_at).total_seconds() / 3600)
            * max(1, assignee_counts[item.id])
            for item in completed_operations
        ),
        1,
    )
    ticket_working_hours = round(float(metrics.get("spent_business_hours") or 0), 1)
    total_working_hours = round(ticket_working_hours + working_hours, 1)
    delivered_tickets = [
        item
        for item in tickets
        if item.status_id in statuses and statuses[item.status_id].code in {"RESOLVED", "CLOSED"}
    ]
    service_ticket_groups: dict[str, list[Ticket]] = {}
    for item in delivered_tickets:
        service_ticket_groups.setdefault(
            services.get(item.service_id, "Unspecified service")
            if item.service_id
            else "Unspecified service",
            [],
        ).append(item)
    operation_groups: dict[str, list[InternalOperation]] = {}
    for operation in completed_operations:
        operation_groups.setdefault(operation.operation_type.replace("_", " ").title(), []).append(
            operation
        )
    service_evidence = [
        {
            "source": "Ticket service",
            "service": name,
            "deliveries": len(items),
            "working_hours": None,
            "last_delivered": max(
                (item.resolved_at or item.closed_at or item.updated_at) for item in items
            ),
            "route": f"/tickets?client_id={client_id}&service_id={items[0].service_id}&status_code=RESOLVED,CLOSED&created_from={date_from}&created_to={date_to}",
        }
        for name, items in sorted(service_ticket_groups.items())
    ] + [
        {
            "source": "Internal operation",
            "service": name,
            "deliveries": len(items),
            "working_hours": round(
                sum(
                    max(0.0, (item.ends_at - item.starts_at).total_seconds() / 3600)
                    * max(1, assignee_counts[item.id])
                    for item in items
                ),
                1,
            ),
            "last_delivered": max(item.ends_at for item in items),
            "route": f"/internal-operations?client_id={client_id}&operation_type={items[0].operation_type}&status=COMPLETED&date_from={date_from}&date_to={date_to}",
        }
        for name, items in sorted(operation_groups.items())
    ]
    services_provided = len(service_evidence)
    incidents = [
        item
        for item in tickets
        if item.ticket_type_id in ticket_types
        and ticket_types[item.ticket_type_id].code == "INCIDENT"
    ]
    ticket_change = metrics.get("total_requests", 0) - previous_metrics.get("total_requests", 0)
    breach_change = metrics.get("sla_breached", 0) - previous_metrics.get("sla_breached", 0)
    compliance = metrics.get("sla_compliance_percent")
    impacts = [
        _impact(
            "Service demand",
            "HIGH" if ticket_change > 5 else "MEDIUM" if ticket_change > 0 else "POSITIVE",
            "Support demand and engineering capacity requirement.",
            f"{metrics.get('total_requests', 0)} tickets; change of {ticket_change:+} versus the previous period.",
            "Review staffing and recurring demand."
            if ticket_change > 0
            else "Maintain current service capacity.",
        ),
        _impact(
            "SLA performance",
            "CRITICAL"
            if metrics.get("sla_breached", 0) and compliance is not None and compliance < 80
            else "HIGH"
            if metrics.get("sla_breached", 0)
            else "POSITIVE",
            "Contractual performance, confidence and renewal exposure.",
            f"{metrics.get('sla_breached', 0)} breaches ({breach_change:+} period change); compliance {compliance if compliance is not None else 'N/A'}%.",
            "Review breached tickets and corrective actions."
            if metrics.get("sla_breached", 0)
            else "Continue SLA monitoring.",
        ),
        _impact(
            "Incidents",
            "CRITICAL" if incidents else "LOW",
            "Business continuity, patient safety, security and reputation.",
            f"{len(incidents)} incident tickets across all priorities.",
            "Review incident resolution and prevention evidence."
            if incidents
            else "No incident intervention required.",
        ),
        _impact(
            "Out-of-hours support",
            "HIGH"
            if tickets and out_hours / len(tickets) >= 0.4
            else "MEDIUM"
            if out_hours
            else "LOW",
            "On-call dependency, service continuity and support cost pressure.",
            f"{out_hours} out-of-hours and {in_hours} in-hours tickets based on contract calendars.",
            "Review coverage hours and on-call capacity."
            if out_hours
            else "Current coverage aligns with demand.",
        ),
        _impact(
            "Delivered value",
            "POSITIVE" if metrics.get("saved_business_hours", 0) > 0 else "MEDIUM",
            "Operational productivity protected through timely resolution.",
            f"Net {metrics.get('saved_business_hours', 0)} SLA business hours saved.",
            "Highlight value delivered and sustain preventive support.",
        ),
        _impact(
            "Client engagement",
            "POSITIVE" if completed_operations else "MEDIUM",
            "Governance strength, adoption and relationship health.",
            f"{len(completed_operations)} completed meetings, visits, demos or service operations.",
            "Maintain engagement cadence."
            if completed_operations
            else "Schedule a service review meeting.",
        ),
    ]
    country = db.get(Country, client.country_id) if client.country_id else None
    city = db.get(City, client.city_id) if client.city_id else None
    locations = list(
        db.scalars(
            select(ClientLocation).where(
                ClientLocation.client_id == client_id, ClientLocation.is_active.in_([True])
            )
        )
    )
    branches = list(
        db.scalars(
            select(Branch).where(Branch.client_id == client_id, Branch.is_active.in_([True]))
        )
    )
    contacts = list(
        db.scalars(
            select(Contact).where(Contact.client_id == client_id, Contact.is_active.in_([True]))
        )
    )
    installations = list(
        db.scalars(
            select(ClientInstallation).where(
                ClientInstallation.client_id == client_id, ClientInstallation.is_active.in_([True])
            )
        )
    )
    daily_created = Counter(item.created_at.date().isoformat() for item in tickets)
    daily_resolved = Counter(
        item.resolved_at.date().isoformat() for item in tickets if item.resolved_at
    )
    trend = []
    cursor = date_from
    while cursor <= date_to:
        key = cursor.isoformat()
        trend.append({"date": key, "created": daily_created[key], "resolved": daily_resolved[key]})
        cursor += timedelta(days=1)
    ticket_period = f"client_id={client_id}&created_from={date_from}&created_to={date_to}"
    operation_period = f"client_id={client_id}&date_from={date_from}&date_to={date_to}"
    breakdown_links = {
        "status": {
            item.name: f"/tickets?{ticket_period}&status_code={item.code}"
            for item in statuses.values()
        },
        "priority": {
            priority: f"/tickets?{ticket_period}&priority={priority}"
            for priority in {item.priority for item in tickets}
        },
        "product": {
            name: f"/tickets?{ticket_period}&product_id={item_id}"
            for item_id, name in products.items()
        },
        "module": {
            name: f"/tickets?{ticket_period}&product_module_id={item_id}"
            for item_id, name in modules.items()
        },
        "service": {
            name: f"/tickets?{ticket_period}&service_id={item_id}"
            for item_id, name in services.items()
        },
    }
    metric_links = {
        "total_requests": f"/tickets?{ticket_period}",
        "sla_compliance_percent": f"/tickets?{ticket_period}&sla_state=MET",
        "sla_breached": f"/tickets?{ticket_period}&breached_only=true",
        "critical_incidents": f"/tickets?{ticket_period}&ticket_type_id={next((key for key, value in ticket_types.items() if value.code == 'INCIDENT'), '')}",
        "saved_business_hours": f"/clients/{client_id}/evidence?date_from={date_from}&date_to={date_to}&metric=saved_business_hours",
        "sla_target_business_hours": f"/clients/{client_id}/evidence?date_from={date_from}&date_to={date_to}&metric=sla_target_business_hours",
        "services_provided": f"/clients/{client_id}/evidence?date_from={date_from}&date_to={date_to}&metric=services_provided",
        "total_working_hours": f"/clients/{client_id}/evidence?date_from={date_from}&date_to={date_to}&metric=total_working_hours",
    }
    sla_results = resolution_sla_results(db, tickets)
    closed_ticket_ids = {
        item.id
        for item in tickets
        if item.status_id in statuses
        and statuses[item.status_id].code in {"RESOLVED", "CLOSED"}
        and (item.resolved_at or item.closed_at)
    }
    sla_rows = [
        {
            "source": "Ticket SLA",
            "reference": item.ticket_number,
            "description": item.subject,
            "service": services.get(item.service_id, "Unspecified service")
            if item.service_id
            else "Unspecified service",
            "hours": round(sla_results[item.id].accountable_minutes / 60, 2),
            "target_hours": round(sla_results[item.id].target_minutes / 60, 2),
            "saved_hours": round(sla_results[item.id].saved_minutes / 60, 2),
            "route": f"/tickets/{item.id}",
        }
        for item in tickets
        if item.id in closed_ticket_ids and item.id in sla_results
    ]
    operation_work_rows = [
        {
            "source": "Internal operation",
            "reference": f"Operation #{item.id}",
            "description": item.title,
            "service": item.operation_type.replace("_", " ").title(),
            "hours": round(
                max(0.0, (item.ends_at - item.starts_at).total_seconds() / 3600)
                * max(1, assignee_counts[item.id]),
                2,
            ),
            "saved_hours": None,
            "route": f"/internal-operations?client_id={client_id}&date_from={date_from}&date_to={date_to}&status=COMPLETED",
        }
        for item in completed_operations
    ]
    return {
        **base,
        "client": {
            "id": client.id,
            "code": client.code,
            "name": client.name,
            "support_started_at": client.support_started_at,
            "email": client.email,
            "phone": client.phone_number,
            "address": client.address,
            "timezone": client.timezone,
            "country": country.name if country else client.country,
            "city": city.name if city else None,
            "locations": [item.name for item in locations],
            "branches": [item.name for item in branches],
            "contacts": [item.full_name for item in contacts],
            "installations": len(installations),
        },
        "metrics": {
            **metrics,
            "in_hours_tickets": in_hours,
            "out_of_hours_tickets": out_hours,
            "critical_incidents": len(incidents),
            "meetings": operation_types.get("MEETING", 0),
            "services_provided": services_provided,
            "ticket_working_hours": ticket_working_hours,
            "operation_working_hours": working_hours,
            "total_working_hours": total_working_hours,
            "field_visits": sum(
                operation_types.get(key, 0)
                for key in ("OUTDOOR_VISIT", "CLIENT_VISIT", "FIELD_VISIT", "ONSITE", "TRAVEL")
            ),
            "demos": operation_types.get("DEMO", 0),
            "ticket_change": ticket_change,
            "completed_checklists": completed_checklists,
            "checklists_needing_attention": checklists_needing_attention,
        },
        "breakdowns": {
            "status": dict(
                Counter(
                    statuses[item.status_id].name for item in tickets if item.status_id in statuses
                )
            ),
            "priority": dict(Counter(item.priority for item in tickets)),
            "product": dict(
                Counter(
                    products.get(item.product_id, "Unspecified")
                    if item.product_id
                    else "Unspecified"
                    for item in tickets
                )
            ),
            "module": dict(
                Counter(
                    modules.get(item.product_module_id, "Unspecified")
                    if item.product_module_id
                    else "Unspecified"
                    for item in tickets
                )
            ),
            "service": dict(
                Counter(
                    services.get(item.service_id, "Unspecified")
                    if item.service_id
                    else "Unspecified"
                    for item in tickets
                )
            ),
        },
        "trends": {"ticket_volume": trend},
        "lifecycle": lifecycle,
        "business_impacts": impacts,
        "critical_tickets": [
            {
                "id": item.id,
                "number": item.ticket_number,
                "subject": item.subject,
                "priority": item.priority,
                "status": statuses[item.status_id].name
                if item.status_id in statuses
                else "Unknown",
                "business_flags": ", ".join(
                    flag
                    for flag, yes in (
                        ("Patient safety", item.patient_safety_flag),
                        ("Security", item.security_incident_flag),
                    )
                    if yes
                )
                or "Incident",
            }
            for item in incidents
        ],
        "evidence": {
            "services_provided": {
                "title": "Services provided",
                "definition": "Distinct ticket services and completed internal-operation types delivered during the selected period.",
                "total": services_provided,
                "unit": "service types",
                "rows": service_evidence,
            },
            "saved_business_hours": {
                "title": "Business hours saved",
                "definition": "Signed Resolution SLA target minus accountable business time for eligible closed tickets.",
                "total": round(sum(float(row["saved_hours"] or 0) for row in sla_rows), 1),
                "unit": "hours",
                "rows": sla_rows,
            },
            "sla_target_business_hours": {
                "title": "SLA target hours",
                "definition": "Resolution SLA hours allowed for eligible closed tickets.",
                "total": round(sum(float(row["target_hours"] or 0) for row in sla_rows), 1),
                "unit": "hours",
                "rows": sla_rows,
            },
            "total_working_hours": {
                "title": "Total working hours",
                "definition": "Accountable ticket business hours plus completed operation duration multiplied by assigned engineers.",
                "total": round(
                    sum(float(row["hours"] or 0) for row in sla_rows + operation_work_rows), 1
                ),
                "unit": "hours",
                "rows": sla_rows + operation_work_rows,
            },
        },
        "previous_period": {
            "date_from": previous_from,
            "date_to": previous_to,
            "metrics": previous_metrics,
        },
        "drilldowns": {
            "metrics": {
                **metric_links,
                "completed_checklists": f"/service-checklists?view=monitor&filter=COMPLETED&client_id={client_id}",
                "checklists_needing_attention": f"/service-checklists?view=monitor&filter=ATTENTION&client_id={client_id}",
            },
            "breakdowns": breakdown_links,
            "business_impacts": {
                "Service demand": metric_links["total_requests"],
                "SLA performance": metric_links["sla_breached"],
                "Incidents": metric_links["critical_incidents"],
                "Out-of-hours support": metric_links["total_requests"],
                "Delivered value": metric_links["saved_business_hours"],
                "Client engagement": f"/internal-operations?{operation_period}&status=COMPLETED",
            },
            "trend": metric_links["total_requests"],
            "working_time_sources": {
                "tickets": f"/tickets?{ticket_period}&status_code=RESOLVED,CLOSED",
                "operations": f"/internal-operations?{operation_period}&status=COMPLETED",
            },
        },
    }


def _add_title(document: Any, text: str) -> None:
    paragraph = document.add_heading(text, level=1)
    paragraph.runs[0].font.color.rgb = RGBColor.from_string(NAVY)


def _add_key_values(document: Any, rows: list[tuple[str, object]]) -> None:
    table = document.add_table(rows=0, cols=2)
    table.style = "Light Shading Accent 1"
    for label, value in rows:
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = str(value if value is not None else "Not available")
        cells[0].paragraphs[0].runs[0].bold = True


def _add_breakdown_chart(document: Any, title: str, values: dict[str, object]) -> None:
    document.add_heading(title, level=2)
    numeric = {label: int(str(value)) for label, value in values.items()}
    maximum = max(numeric.values(), default=1)
    table = document.add_table(rows=1, cols=3)
    table.style = "Light Shading Accent 1"
    for cell, label in zip(table.rows[0].cells, ("Category", "Distribution", "Count"), strict=True):
        cell.text = label
        _shade(cell, NAVY)
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
    for label, value in sorted(numeric.items(), key=lambda item: (-item[1], item[0])):
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = "█" * max(1, round(value * 20 / maximum)) if value else "—"
        cells[1].paragraphs[0].runs[0].font.color.rgb = RGBColor.from_string(TEAL)
        cells[2].text = str(value)


def build_client_profile_docx(data: dict[str, Any]) -> io.BytesIO:
    document: Any = Document()
    section = document.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width
    section.top_margin = Inches(0.45)
    section.bottom_margin = Inches(0.45)
    section.left_margin = Inches(0.55)
    section.right_margin = Inches(0.55)
    styles = document.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(9)
    header = section.header.paragraphs[0]
    header.text = "MILLENSYS SUPPORT HUB  •  CLIENT SERVICE PROFILE"
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header.runs[0].font.color.rgb = RGBColor.from_string(BLUE)
    footer = section.footer.paragraphs[0]
    footer.text = "MILLENSYS  •  Technology for a Healthier Globe   |   Confidential"
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    client = cast(dict[str, Any], data["client"])
    period = cast(dict[str, Any], data["period"])
    metrics = cast(dict[str, Any], data["metrics"])
    banner = document.add_table(rows=1, cols=2)
    left, right = banner.rows[0].cells
    for cell in (left, right):
        _shade(cell, NAVY)
    _set_cell_text(left, client["name"], size=25, color=WHITE, bold=True)
    meta = f"{client['code']}  ·  {client['country'] or 'Country not specified'}  ·  {client['city'] or 'City not specified'}"
    meta_run = left.add_paragraph().add_run(meta)
    meta_run.font.color.rgb = RGBColor.from_string("D9EEF7")
    _set_cell_text(
        right,
        f"REPORTING PERIOD\n{period['date_from']}  —  {period['date_to']}",
        size=11,
        color=WHITE,
        bold=True,
    )
    right.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT

    document.add_paragraph()
    _add_kpi_cards(document, metrics)
    _add_panel_title(document, "Client delivery lifecycle")
    lifecycle = cast(dict[str, dict[str, Any]], data["lifecycle"])
    lifecycle_table = document.add_table(rows=1, cols=3)
    lifecycle_table.style = "Table Grid"
    for cell, label in zip(
        lifecycle_table.rows[0].cells, ("Area", "Total in period", "Active / open"), strict=True
    ):
        _shade(cell, NAVY)
        _set_cell_text(cell, label, color=WHITE, bold=True)
    for key, label in (
        ("uat", "UAT"),
        ("deployments", "Deployments"),
        ("incidents", "Incidents"),
        ("changes", "Change Requests"),
        ("problems", "Problems"),
    ):
        cells = lifecycle_table.add_row().cells
        _set_cell_text(cells[0], label, bold=True)
        _set_cell_text(cells[1], lifecycle[key]["count"])
        _set_cell_text(cells[2], lifecycle[key]["active"])
    document.add_page_break()

    _add_panel_title(document, "Ticket volume trend")
    trend_table = document.add_table(rows=1, cols=3)
    for cell, label in zip(trend_table.rows[0].cells, ("Date", "Created", "Resolved"), strict=True):
        _shade(cell, NAVY)
        _set_cell_text(cell, label, color=WHITE, bold=True)
    trends = cast(dict[str, list[dict[str, object]]], data["trends"])
    trend_max = max(
        1,
        max(
            (
                max(int(str(point["created"])), int(str(point["resolved"])))
                for point in trends["ticket_volume"]
            ),
            default=0,
        ),
    )
    for point in trends["ticket_volume"]:
        cells = trend_table.add_row().cells
        created = int(str(point["created"]))
        resolved = int(str(point["resolved"]))
        _set_cell_text(cells[0], point["date"], color=MUTED)
        _set_cell_text(cells[1], f"{'■' * round(created * 18 / trend_max)}  {created}", color=BLUE)
        _set_cell_text(
            cells[2], f"{'■' * round(resolved * 18 / trend_max)}  {resolved}", color=TEAL
        )

    breakdowns = cast(dict[str, dict[str, object]], data["breakdowns"])
    _add_distribution_panel(document, "Priority mix", breakdowns["priority"])
    for key, title in (
        ("status", "Status distribution"),
        ("product", "Products"),
        ("module", "Modules"),
        ("service", "Services"),
    ):
        _add_distribution_panel(document, title, breakdowns[key])

    document.add_page_break()
    _add_panel_title(document, "Business impact and recommended actions")
    impacts = cast(list[dict[str, str]], data["business_impacts"])
    impact_colors = {"CRITICAL": RED, "HIGH": AMBER, "POSITIVE": GREEN, "MEDIUM": BLUE, "LOW": TEAL}
    impact_table = document.add_table(rows=0, cols=2)
    for index in range(0, len(impacts), 2):
        cells = impact_table.add_row().cells
        for offset, cell in enumerate(cells):
            if index + offset >= len(impacts):
                continue
            impact = impacts[index + offset]
            _shade(cell, "F8FBFC")
            _cell_border(cell, impact_colors.get(impact["level"], BLUE), "18")
            _set_cell_text(cell, f"{impact['area']}     {impact['level']}", size=12, bold=True)
            consequence = cell.add_paragraph(impact["consequence"])
            consequence.runs[0].font.size = Pt(9)
            evidence = cell.add_paragraph(f"Evidence: {impact['evidence']}")
            evidence.runs[0].font.color.rgb = RGBColor.from_string(MUTED)
            action = cell.add_paragraph(f"Action: {impact['action']}")
            action.runs[0].font.color.rgb = RGBColor.from_string(BLUE)
            action.runs[0].bold = True

    _add_panel_title(document, "Critical ticket details")
    critical = cast(list[dict[str, object]], data["critical_tickets"])
    if not critical:
        document.add_paragraph(
            "No critical, patient-safety or security incidents were recorded in this period."
        )
    else:
        table = document.add_table(rows=1, cols=5)
        table.style = "Table Grid"
        for cell, label in zip(
            table.rows[0].cells,
            ("Ticket", "Subject", "Priority", "Status", "Business flags"),
            strict=True,
        ):
            _shade(cell, NAVY)
            _set_cell_text(cell, label, color=WHITE, bold=True)
        for item in critical:
            row = table.add_row().cells
            for cell, key in zip(
                row, ("number", "subject", "priority", "status", "business_flags"), strict=True
            ):
                _set_cell_text(cell, item[key])

    document.add_page_break()
    _add_title(document, "Supporting client and service details")
    _add_key_values(
        document,
        [
            ("Client code", client["code"]),
            ("Delivered to Support", client["support_started_at"]),
            ("Country / city", f"{client['country'] or '—'} / {client['city'] or '—'}"),
            ("Locations", ", ".join(client["locations"]) or "Not configured"),
            ("Branches", ", ".join(client["branches"]) or "Not configured"),
            ("Contact", f"{client['email'] or '—'} · {client['phone'] or '—'}"),
            ("Active installations", client["installations"]),
            (
                "In-hours / out-of-hours tickets",
                f"{metrics['in_hours_tickets']} / {metrics['out_of_hours_tickets']}",
            ),
            ("Ticket spent business hours", metrics["ticket_working_hours"]),
            ("Operation engineer-hours", metrics["operation_working_hours"]),
            ("Combined working hours", metrics["total_working_hours"]),
        ],
    )
    _add_panel_title(document, "Contracts and coverage")
    for contract in cast(list[dict[str, Any]], data["contracts"]):
        document.add_paragraph(
            f"{contract['number']} — {contract['name']} | {contract['start_date']} to {contract['end_date']} | {contract['days_to_expiry']} days to expiry",
            style="List Bullet",
        )
    coverage = cast(dict[str, list[str]], data["coverage"])
    _add_key_values(
        document,
        [
            ("Covered products", ", ".join(coverage["products"]) or "Not specified"),
            ("Covered modules", ", ".join(coverage["modules"]) or "Not specified"),
            ("Covered services", ", ".join(coverage["services"]) or "Not specified"),
        ],
    )
    _add_title(document, "Calculation guide")
    for method in cast(list[dict[str, str]], data["calculation_methods"]):
        document.add_heading(method["name"], level=2)
        document.add_paragraph(f"Formula: {method['formula']}")
        document.add_paragraph(method["details"])
    document.add_section(WD_SECTION.NEW_PAGE)
    document.add_paragraph(
        f"Generated by MILLENSYS Support Hub on {server_now():%Y-%m-%d %H:%M %z}. All calculations use recorded system evidence; unavailable evidence is not estimated."
    )
    output = io.BytesIO()
    document.save(output)
    output.seek(0)
    return output


@router.get("/client-profile")
def preview_client_profile(
    client_id: int,
    date_from: date,
    date_to: date,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client.profile.view")),
) -> dict[str, object]:
    return client_profile_data(db, client_id, date_from, date_to, actor)


@router.get("/client-profile.docx")
def export_client_profile(
    client_id: int,
    date_from: date,
    date_to: date,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("report.export")),
) -> StreamingResponse:
    data = client_profile_data(db, client_id, date_from, date_to, actor)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Client",
            entity_id=str(client_id),
            action="client.profile_report.exported",
            new_values_json=f'{{"date_from":"{date_from}","date_to":"{date_to}","format":"docx"}}',
        )
    )
    db.commit()
    client = cast(dict[str, object], data["client"])
    filename = f"Millensys-Client-Profile-{client['code']}-{date_from}-{date_to}.docx"
    return StreamingResponse(
        build_client_profile_docx(data),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
