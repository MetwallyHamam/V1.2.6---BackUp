import csv
import io
from calendar import monthrange
from collections.abc import Callable
from datetime import date, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now, server_timezone, server_today
from app.db.session import get_db
from app.modules.clients.models import (
    Branch,
    Client,
    Contact,
    Environment,
    Product,
    ProductModule,
    ServiceCatalogItem,
    TicketCategory,
    TicketSubcategory,
)
from app.modules.contracts.models import Contract
from app.modules.dashboards.models import AgentActivity
from app.modules.dashboards.routes import summary as dashboard_summary
from app.modules.iam.models import Department, User
from app.modules.iam.organization import department_descendant_ids
from app.modules.internal_operations.models import InternalOperation, InternalOperationAssignee
from app.modules.sla.service import attach_ticket_sla_evidence
from app.modules.tickets.models import Ticket, TicketStatus, TicketType
from app.modules.tickets.service import apply_ticket_filters, visible_ticket_query

router = APIRouter(prefix="/reports", tags=["reports"])

NAVY = "17365D"
BLUE = "2F75B5"
LIGHT_BLUE = "D9EAF7"
LIGHT_GREY = "E7E6E6"
WHITE = "FFFFFF"
GREEN = "E2F0D9"


def style_hr_sheet(sheet: Any, freeze: str = "A2") -> None:
    sheet.freeze_panes = freeze
    sheet.auto_filter.ref = sheet.dimensions
    sheet.sheet_view.showGridLines = False
    thin = Side(style="thin", color="B7C9DC")
    for cell in sheet[1]:
        cell.fill = PatternFill("solid", fgColor=NAVY)
        cell.font = Font(color=WHITE, bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(bottom=thin)
    sheet.row_dimensions[1].height = 34
    for column in sheet.columns:
        width = min(max(len(str(cell.value or "")) for cell in column) + 3, 42)
        sheet.column_dimensions[get_column_letter(column[0].column)].width = max(width, 12)
        for cell in column[1:]:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(bottom=Side(style="hair", color="D9E2F3"))


def report_bounds(
    month: str | None,
    quarter: str | None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[datetime, datetime, str]:
    now = server_now()
    if date_from and date_to:
        return (
            datetime.combine(date_from, datetime.min.time(), tzinfo=server_timezone()),
            datetime.combine(date_to, datetime.max.time(), tzinfo=server_timezone()),
            f"{date_from.isoformat()}-to-{date_to.isoformat()}",
        )
    if quarter:
        year, number = int(quarter[:4]), int(quarter[-1])
        first, last = (number - 1) * 3 + 1, (number - 1) * 3 + 3
        return (
            datetime(year, first, 1, tzinfo=server_timezone()),
            datetime(year, last, monthrange(year, last)[1], 23, 59, 59, 999999, tzinfo=server_timezone()),
            quarter,
        )
    selected = month or now.strftime("%Y-%m")
    year, number = (int(item) for item in selected.split("-"))
    return (
        datetime(year, number, 1, tzinfo=server_timezone()),
        datetime(year, number, monthrange(year, number)[1], 23, 59, 59, 999999, tzinfo=server_timezone()),
        selected,
    )


def safe_cell(value: object) -> str:
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


@router.get("/agent-kpis.xlsx")
def export_agent_kpis(
    kpi_month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    kpi_quarter: str | None = Query(default=None, pattern=r"^\d{4}-Q[1-4]$"),
    date_from: date | None = None,
    date_to: date | None = None,
    date_basis: Literal["CREATION", "RESOLUTION", "ASSIGNMENT"] = "CREATION",
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("report.export")),
) -> StreamingResponse:
    if kpi_month and kpi_quarter:
        from app.core.exceptions import ConflictError

        raise ConflictError("INVALID_KPI_PERIOD", "Choose either a month or a quarter.")
    report = dashboard_summary(
        kpi_month=kpi_month,
        kpi_quarter=kpi_quarter,
        date_from=date_from,
        date_to=date_to,
        date_basis=date_basis,
        db=db,
        user=user,
    )
    period_start, period_end, period_label = report_bounds(kpi_month, kpi_quarter, date_from, date_to)
    workbook = Workbook()
    overview = workbook.active
    overview.title = "HR KPI Summary"
    overview.sheet_view.showGridLines = False
    overview.merge_cells("A1:N1")
    overview["A1"] = "MILLENSYS SUPPORT DEPARTMENT — AGENT PERFORMANCE REPORT"
    overview["A1"].fill = PatternFill("solid", fgColor=NAVY)
    overview["A1"].font = Font(color=WHITE, bold=True, size=16)
    overview["A1"].alignment = Alignment(horizontal="center")
    overview.row_dimensions[1].height = 30
    overview["A3"] = "Reporting period"
    overview["B3"] = period_label
    overview["D3"] = "Period start"
    overview["E3"] = period_start.date().isoformat()
    overview["G3"] = "Period end"
    overview["H3"] = period_end.date().isoformat()
    overview["J3"] = "Generated"
    overview["K3"] = server_now().strftime("%Y-%m-%d %H:%M %z")
    for cell in ("A3", "D3", "G3", "J3"):
        overview[cell].font = Font(bold=True, color=NAVY)
    headers = [
        "Employee", "Tickets handled", "Open workload", "Resolved / closed",
        "Escalation assignments", "Avg response (hours)", "Reopened tickets",
        "External activities", "After-shift operations", "After-shift hours",
        "Training attended", "Training delivered", "Meetings",
        "Tasks added", "Knowledge shared", "Follower assignments", "Dedicated clients",
        "Dedicated-client tickets", "SLA compliance %", "Avg resolution (hours)",
    ]
    overview.append([])
    overview.append(headers)
    header_row = overview.max_row
    for cell in overview[header_row]:
        cell.fill = PatternFill("solid", fgColor=NAVY)
        cell.font = Font(color=WHITE, bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    overview.freeze_panes = f"A{header_row + 1}"
    for index, item in enumerate(report.agent_kpis, start=header_row + 1):
        overview.append([
            safe_cell(item.agent), item.assigned, item.open, item.resolved,
            item.escalation_assignments, item.average_response_hours, item.reopened_tickets,
            item.external_activities, item.after_shift_work, item.after_shift_hours,
            item.training_attended, item.training_delivered,
            item.meetings, item.tasks_created, item.knowledge_articles,
            item.follower_assignments, item.dedicated_clients, item.dedicated_client_tickets,
            item.sla_compliance_percent, item.average_resolution_hours,
        ])
        if index % 2 == 0:
            for cell in overview[index]:
                cell.fill = PatternFill("solid", fgColor="F3F6FA")
    overview.auto_filter.ref = f"A{header_row}:T{overview.max_row}"
    overview.sheet_view.showGridLines = False
    overview.row_dimensions[header_row].height = 45
    overview.column_dimensions["A"].width = 28
    for column in range(2, 21):
        overview.column_dimensions[get_column_letter(column)].width = 17
    for row in overview.iter_rows(min_row=header_row, max_row=overview.max_row):
        for cell in row:
            cell.alignment = Alignment(vertical="center", wrap_text=True)

    status_sheet = workbook.create_sheet("Ticket Status Detail")
    statuses = sorted({code for item in report.agent_kpis for code in item.tickets_by_status})
    status_sheet.append(["Employee", "Total handled", *[code.replace("_", " ").title() for code in statuses]])
    for item in report.agent_kpis:
        status_sheet.append([safe_cell(item.agent), item.assigned, *[item.tickets_by_status.get(code, 0) for code in statuses]])
    style_hr_sheet(status_sheet)

    definitions = workbook.create_sheet("KPI Definitions")
    definitions.append(["KPI", "HR measurement definition", "System evidence"])
    definition_rows = [
        ("Tickets Handled", "Tickets assigned to the employee and created during the selected period, grouped by status.", "Ticket assignment and current status"),
        ("Escalation Handling Efficiency", "Number of internal escalation assignments received during the period.", "Ticket escalation audit history"),
        ("Response Time", "Average elapsed hours from ASSIGNED to IN PROGRESS.", "Ticket status history"),
        ("Reopened Tickets", "Distinct assigned tickets moved to REOPENED during the period.", "Ticket status history"),
        ("External Activities", "Training, meetings, knowledge articles, and completed after-shift operations during the period.", "KPI activity log, knowledge base, and Internal Operations"),
        ("After-Shift Work", "Count and scheduled hours of completed AFTER SHIFT operations assigned to the employee.", "Completed Internal Operations assignments"),
        ("Leadership Support", "Training sessions delivered as facilitator or presenter.", "KPI activity log"),
        ("Decision Making", "Ticket tasks created by the employee.", "Ticket task audit data"),
        ("Knowledge Share", "Knowledge-base articles created by the employee.", "Knowledge article ownership"),
        ("Cross-Team Collaboration", "Tickets where the employee was added as a follower.", "Ticket follower history"),
        ("Accountability", "Dedicated client scopes and tickets handled for those clients.", "User client scope and ticket assignment"),
    ]
    for row in definition_rows:
        definitions.append(row)
    style_hr_sheet(definitions)

    evidence = workbook.create_sheet("Activity Evidence")
    evidence.append(["Employee", "Activity", "Role", "Title", "Duration (minutes)", "Occurred at", "Notes"])
    users = {item.id: item.full_name for item in db.scalars(select(User)).all()}
    report_user_ids = {item.user_id for item in report.agent_kpis if item.user_id is not None}
    activities = db.scalars(
        select(AgentActivity)
        .where(
            AgentActivity.occurred_at >= period_start,
            AgentActivity.occurred_at <= period_end,
            AgentActivity.user_id.in_(report_user_ids or [-1]),
        )
        .order_by(AgentActivity.occurred_at, AgentActivity.user_id)
    ).all()
    for activity in activities:
        evidence.append([
            safe_cell(users.get(activity.user_id, f"User {activity.user_id}")),
            activity.activity_type, activity.participation_role, safe_cell(activity.title),
            activity.duration_minutes,
            activity.occurred_at.replace(tzinfo=server_timezone()).strftime("%Y-%m-%d %H:%M"),
            safe_cell(activity.notes),
        ])
    style_hr_sheet(evidence)

    after_shift_evidence = workbook.create_sheet("After-Shift Evidence")
    after_shift_evidence.append(["Employee", "Operation", "Client", "Starts", "Ends", "Hours", "Status"])
    # Materialize this result before issuing another query. SQL Server without
    # MARS enabled permits only one active result set per connection.
    rows = db.execute(
        select(InternalOperation, InternalOperationAssignee.user_id)
        .join(InternalOperationAssignee, InternalOperationAssignee.operation_id == InternalOperation.id)
        .where(
            InternalOperation.operation_type == "AFTER_SHIFT",
            InternalOperation.status == "COMPLETED",
            InternalOperation.ends_at >= period_start,
            InternalOperation.ends_at <= period_end,
            InternalOperationAssignee.user_id.in_(report_user_ids or [-1]),
        )
        .order_by(InternalOperation.ends_at, InternalOperationAssignee.user_id)
    ).all()
    clients = {item.id: item.name for item in db.scalars(select(Client)).all()}
    for operation, user_id in rows:
        after_shift_evidence.append([
            safe_cell(users.get(user_id, f"User {user_id}")), safe_cell(operation.title),
            safe_cell(clients.get(operation.client_id, "") if operation.client_id else ""),
            operation.starts_at.replace(tzinfo=server_timezone()).strftime("%Y-%m-%d %H:%M"),
            operation.ends_at.replace(tzinfo=server_timezone()).strftime("%Y-%m-%d %H:%M"),
            round((operation.ends_at - operation.starts_at).total_seconds() / 3600, 1),
            operation.status,
        ])
    style_hr_sheet(after_shift_evidence)

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    filename = f"Millensys-Agent-KPI-{period_label}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/tickets.csv")
def export_tickets(
    search: str | None = Query(default=None, max_length=100),
    status_code: str | None = None,
    priority: str | None = None,
    client_id: str | None = None,
    assigned_user_id: str | None = None,
    created_by_user_id: str | None = None,
    department_id: str | None = None,
    parent_department_id: str | None = None,
    product_id: str | None = None,
    product_module_id: str | None = None,
    ticket_type_id: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    columns: str | None = Query(default=None, max_length=2000),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("report.export")),
) -> StreamingResponse:
    def selected_ids(value: str | None) -> set[int]:
        return {int(part) for part in (value or "").split(",") if part.strip().isdigit()}

    parent_scope_ids: set[int] = set()
    for selected_parent_id in selected_ids(parent_department_id):
        parent_scope_ids.update(department_descendant_ids(db, selected_parent_id, server_today(), include_self=True))
    statement = apply_ticket_filters(
        visible_ticket_query(db, user),
        search=search,
        status_code=status_code,
        priority=priority,
        client_id=client_id,
        assigned_user_id=assigned_user_id,
        created_by_user_id=created_by_user_id,
        department_ids=selected_ids(department_id),
        parent_department_ids=parent_scope_ids,
        product_id=product_id,
        product_module_id=product_module_id,
        ticket_type_id=ticket_type_id,
        created_from=created_from,
        created_to=created_to,
    )
    tickets = list(
        db.scalars(statement.order_by(Ticket.created_at.desc()).limit(10000))
    )
    tickets = attach_ticket_sla_evidence(db, tickets)
    clients = {item.id: item.name for item in db.scalars(select(Client)).all()}
    statuses = {item.id: item.name for item in db.scalars(select(TicketStatus)).all()}
    ticket_types = {item.id: item.name for item in db.scalars(select(TicketType)).all()}
    products = {item.id: item.name for item in db.scalars(select(Product)).all()}
    modules = {item.id: item.name for item in db.scalars(select(ProductModule)).all()}
    assignees = {item.id: item.full_name for item in db.scalars(select(User)).all()}
    user_departments = {item.id: item.department_id for item in db.scalars(select(User)).all()}
    departments = {item.id: item for item in db.scalars(select(Department)).all()}
    def ticket_department_id(item: Ticket) -> int | None:
        return item.routed_department_id or user_departments.get(item.assigned_user_id or item.created_by_user_id)
    def ticket_department_name(item: Ticket) -> str:
        department_id = ticket_department_id(item)
        department = departments.get(department_id) if department_id is not None else None
        return department.name if department else ""
    def ticket_parent_department_name(item: Ticket) -> str:
        department_id = ticket_department_id(item)
        department = departments.get(department_id) if department_id is not None else None
        parent = departments.get(department.parent_department_id) if department and department.parent_department_id is not None else None
        return parent.name if parent else ""
    branches = {item.id: item.name for item in db.scalars(select(Branch)).all()}
    contacts = {item.id: item.full_name for item in db.scalars(select(Contact)).all()}
    environments = {item.id: item.name for item in db.scalars(select(Environment)).all()}
    services = {item.id: item.name for item in db.scalars(select(ServiceCatalogItem)).all()}
    categories = {item.id: item.name for item in db.scalars(select(TicketCategory)).all()}
    subcategories = {item.id: item.name for item in db.scalars(select(TicketSubcategory)).all()}
    contracts = {item.id: item.contract_number for item in db.scalars(select(Contract)).all()}
    column_definitions: dict[str, tuple[str, Callable[[Ticket], object]]] = {
        "ticket_number": ("Ticket Number", lambda item: item.ticket_number), "subject": ("Subject", lambda item: item.subject),
        "created_by": ("Created By", lambda item: assignees.get(item.created_by_user_id, "")),
        "department": ("Department", ticket_department_name),
        "parent_department": ("Parent Department", ticket_parent_department_name),
        "ticket_type": ("Ticket Type", lambda item: ticket_types.get(item.ticket_type_id, "")),
        "status": ("Status", lambda item: statuses.get(item.status_id, "")), "priority": ("Priority", lambda item: item.priority),
        "client": ("Client", lambda item: clients.get(item.client_id, "")), "branch": ("Branch", lambda item: branches.get(item.branch_id, "") if item.branch_id else ""),
        "requester": ("Requester", lambda item: contacts.get(item.requester_contact_id, "") if item.requester_contact_id else ""), "contract": ("Contract", lambda item: contracts.get(item.contract_id, "") if item.contract_id else ""),
        "entitlement_status": ("Entitlement", lambda item: item.entitlement_status), "assigned_engineer": ("Assigned Engineer", lambda item: assignees.get(item.assigned_user_id, "") if item.assigned_user_id else ""),
        "assigned_team": ("Assigned Team", lambda item: item.assigned_team), "escalation_engineer": ("Escalation Engineer", lambda item: assignees.get(item.escalation_assignee_user_id, "") if item.escalation_assignee_user_id else ""),
        "product": ("Product", lambda item: products.get(item.product_id, "") if item.product_id else ""), "module": ("Module", lambda item: modules.get(item.product_module_id, "") if item.product_module_id else ""),
        "environment": ("Environment", lambda item: environments.get(item.environment_id, "") if item.environment_id else ""), "service": ("Service", lambda item: services.get(item.service_id, "") if item.service_id else ""),
        "category": ("Category", lambda item: categories.get(item.category_id, "") if item.category_id else item.category), "subcategory": ("Subcategory", lambda item: subcategories.get(item.subcategory_id, "") if item.subcategory_id else item.subcategory),
        "source_channel": ("Source", lambda item: item.source_channel), "impact": ("Impact", lambda item: item.impact), "urgency": ("Urgency", lambda item: item.urgency),
        "description": ("Description", lambda item: item.description), "affected_users": ("Affected Users", lambda item: item.affected_users), "first_occurred_at": ("First Occurred", lambda item: item.first_occurred_at.isoformat() if item.first_occurred_at else ""),
        "patient_safety_flag": ("Patient Safety", lambda item: item.patient_safety_flag), "security_incident_flag": ("Security Incident", lambda item: item.security_incident_flag),
        "resolution_summary": ("Resolution", lambda item: item.resolution_summary), "root_cause_summary": ("Root Cause", lambda item: item.root_cause_summary),
        "sla_resolution_target": ("SLA Resolution Target Minutes", lambda item: getattr(item, "sla_resolution_target_minutes", None)),
        "sla_actual_business_time": ("Actual SLA Business Minutes", lambda item: getattr(item, "sla_actual_business_minutes", None)),
        "sla_time_balance": ("SLA Saved / Overrun Minutes", lambda item: getattr(item, "sla_saved_minutes", None)),
        "sla_resolution_state": ("Resolution SLA State", lambda item: getattr(item, "sla_resolution_state", None)),
        "sla_match_reason": ("SLA Match Reason", lambda item: getattr(item, "sla_match_reason", None)),
        "sla_target_id": ("SLA Target ID", lambda item: getattr(item, "sla_target_id", None)),
        "sla_policy_version": ("SLA Policy Version", lambda item: getattr(item, "sla_policy_version", None)),
        "sla_calendar_id": ("SLA Calendar ID", lambda item: getattr(item, "sla_calendar_id", None)),
        "created_at": ("Created At", lambda item: item.created_at.isoformat()), "updated_at": ("Updated At", lambda item: item.updated_at.isoformat()),
        "resolved_at": ("Resolved At", lambda item: item.resolved_at.isoformat() if item.resolved_at else ""), "closed_at": ("Closed At", lambda item: item.closed_at.isoformat() if item.closed_at else ""),
    }
    selected_columns = [key for key in (columns.split(",") if columns else column_definitions) if key in column_definitions]
    if not selected_columns:
        selected_columns = list(column_definitions)
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow([column_definitions[key][0] for key in selected_columns])
    for item in tickets:
        writer.writerow([safe_cell(column_definitions[key][1](item)) for key in selected_columns])
    content = io.BytesIO(stream.getvalue().encode("utf-8-sig"))
    return StreamingResponse(content, media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="tickets.csv"'})
