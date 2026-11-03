import io
import json
import re
from datetime import date, datetime
from typing import Any, Literal, cast

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from pydantic import BaseModel, Field
from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import (
    Client,
    Environment,
    Product,
    ProductModule,
    ServiceCatalogItem,
    SupportTeam,
    TicketCategory,
    TicketSubcategory,
)
from app.modules.contracts.models import Contract, ContractClientLink
from app.modules.iam.models import AuditLog, User
from app.modules.tickets.models import Ticket, TicketStatus, TicketType
from app.modules.tickets.service import visible_ticket_query

from .models import DynamicReportDefinition
from .routes import safe_cell, style_hr_sheet

router = APIRouter(prefix="/reports-center", tags=["reports center"])
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PROCEDURE = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9_]*\.)?[A-Za-z_][A-Za-z0-9_]*$")
PAGE_SIZES = {25, 50, 100, 250}
MAX_REPORT_DATE_RANGE_DAYS = 366
RESERVED_PARAMETERS = {"page", "page_size", "sort_by", "sort_direction", "requesting_user_id"}
LOOKUP_SOURCES = {
    "clients", "users", "products", "modules", "environments", "services",
    "categories", "subcategories", "teams", "contracts", "ticket_types", "ticket_statuses",
}


class FilterDefinition(BaseModel):
    name: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$", max_length=80)
    label: str = Field(min_length=1, max_length=120)
    type: Literal["text", "date", "number", "select", "boolean", "lookup"]
    required: bool = False
    default: str | int | bool | None = None
    options: list[dict[str, str | int]] = Field(default_factory=list, max_length=500)
    lookup_source: str | None = Field(default=None, max_length=40)
    depends_on: str | None = Field(default=None, max_length=80)


class ReportDefinitionIn(BaseModel):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$", min_length=3, max_length=80)
    name: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    category: str = Field(default="General", min_length=2, max_length=80)
    stored_procedure: str = Field(min_length=3, max_length=200)
    filters: list[FilterDefinition] = Field(default_factory=list, max_length=30)
    default_page_size: int = 25
    default_sort_column: str | None = Field(default=None, max_length=120)
    default_sort_direction: Literal["ASC", "DESC"] = "DESC"
    is_active: bool = True


class RunReportIn(BaseModel):
    filters: dict[str, Any] = Field(default_factory=dict)
    page: int = Field(default=1, ge=1, le=100000)
    page_size: int = Field(default=25)
    sort_by: str | None = Field(default=None, max_length=120)
    sort_direction: Literal["ASC", "DESC"] = "DESC"


def definition_payload(row: DynamicReportDefinition) -> dict[str, object]:
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "description": row.description,
        "category": row.category,
        "stored_procedure": row.stored_procedure,
        "filters": json.loads(row.filters_json or "[]"),
        "default_page_size": row.default_page_size,
        "default_sort_column": row.default_sort_column,
        "default_sort_direction": row.default_sort_direction,
        "is_active": row.is_active,
        "is_system": row.is_system,
    }


def validated_definition(data: ReportDefinitionIn) -> None:
    if not PROCEDURE.fullmatch(data.stored_procedure):
        raise ConflictError(
            "INVALID_REPORT_PROCEDURE",
            "Use a stored procedure name such as dbo.usp_SupportHub_Report_Name.",
        )
    if data.default_page_size not in PAGE_SIZES:
        raise ConflictError("INVALID_REPORT_PAGE_SIZE", "Choose 25, 50, 100, or 250 rows.")
    if data.default_sort_column and not IDENTIFIER.fullmatch(data.default_sort_column):
        raise ConflictError("INVALID_REPORT_SORT", "The default sort column is invalid.")
    if {item.name for item in data.filters}.intersection(RESERVED_PARAMETERS):
        raise ConflictError(
            "RESERVED_REPORT_FILTER", "The filter schema uses a reserved paging or security parameter."
        )
    invalid_lookups = {
        item.lookup_source
        for item in data.filters
        if item.type == "lookup" and item.lookup_source not in LOOKUP_SOURCES
    }
    if invalid_lookups:
        raise ConflictError("INVALID_REPORT_LOOKUP", "The report uses an unsupported lookup source.")


@router.get("/filter-options/{source}")
def report_filter_options(
    source: str,
    q: str | None = Query(default=None, max_length=100),
    parent_value: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("report.view")),
) -> list[dict[str, str | int]]:
    """Return a small, permission-protected lookup list from approved master data."""
    if source not in LOOKUP_SOURCES:
        raise NotFoundError("Report lookup source does not exist.")
    term = f"%{q.strip()}%" if q and q.strip() else None
    visible_client_ids = visible_ticket_query(db, actor).with_only_columns(Ticket.client_id).distinct()
    rows: list[Any]
    statement: Any
    if source == "clients":
        statement = select(Client.id, Client.name, Client.code).where(
            Client.is_active.in_([True]), Client.id.in_(visible_client_ids)
        )
        if term:
            statement = statement.where(or_(Client.name.ilike(term), Client.code.ilike(term)))
        rows = list(db.execute(statement.order_by(Client.name).limit(100)))
    elif source == "users":
        statement = select(User.id, User.full_name, User.username).where(User.is_active.in_([True]))
        if term:
            statement = statement.where(or_(User.full_name.ilike(term), User.username.ilike(term)))
        rows = list(db.execute(statement.order_by(User.full_name).limit(100)))
    elif source == "products":
        statement = select(Product.id, Product.name, Product.code).where(Product.is_active.in_([True]))
        if term:
            statement = statement.where(or_(Product.name.ilike(term), Product.code.ilike(term)))
        rows = list(db.execute(statement.order_by(Product.name).limit(100)))
    elif source == "modules":
        statement = select(ProductModule.id, ProductModule.name, ProductModule.code).where(ProductModule.is_active.in_([True]))
        if parent_value is not None:
            statement = statement.where(ProductModule.product_id == parent_value)
        if term:
            statement = statement.where(or_(ProductModule.name.ilike(term), ProductModule.code.ilike(term)))
        rows = list(db.execute(statement.order_by(ProductModule.name).limit(100)))
    elif source == "environments":
        statement = select(Environment.id, Environment.name, Environment.code).where(Environment.is_active.in_([True]))
        if term:
            statement = statement.where(or_(Environment.name.ilike(term), Environment.code.ilike(term)))
        rows = list(db.execute(statement.order_by(Environment.name).limit(100)))
    elif source == "services":
        statement = select(ServiceCatalogItem.id, ServiceCatalogItem.name, ServiceCatalogItem.code).where(ServiceCatalogItem.is_active.in_([True]))
        if term:
            statement = statement.where(or_(ServiceCatalogItem.name.ilike(term), ServiceCatalogItem.code.ilike(term)))
        rows = list(db.execute(statement.order_by(ServiceCatalogItem.name).limit(100)))
    elif source == "categories":
        statement = select(TicketCategory.id, TicketCategory.name, TicketCategory.code).where(TicketCategory.is_active.in_([True]))
        if term:
            statement = statement.where(or_(TicketCategory.name.ilike(term), TicketCategory.code.ilike(term)))
        rows = list(db.execute(statement.order_by(TicketCategory.name).limit(100)))
    elif source == "subcategories":
        statement = select(TicketSubcategory.id, TicketSubcategory.name, TicketSubcategory.code).where(TicketSubcategory.is_active.in_([True]))
        if parent_value is not None:
            statement = statement.where(TicketSubcategory.category_id == parent_value)
        if term:
            statement = statement.where(or_(TicketSubcategory.name.ilike(term), TicketSubcategory.code.ilike(term)))
        rows = list(db.execute(statement.order_by(TicketSubcategory.name).limit(100)))
    elif source == "teams":
        statement = select(SupportTeam.name, SupportTeam.name, SupportTeam.code).where(SupportTeam.is_active.in_([True]))
        if term:
            statement = statement.where(or_(SupportTeam.name.ilike(term), SupportTeam.code.ilike(term)))
        rows = list(db.execute(statement.order_by(SupportTeam.name).limit(100)))
    elif source == "contracts":
        statement = select(Contract.id, Contract.name, Contract.contract_number).where(
            or_(Contract.applies_to_all_clients.in_([True]), Contract.client_id.in_(visible_client_ids), Contract.client_links.any(ContractClientLink.client_id.in_(visible_client_ids)))
        )
        if parent_value is not None:
            statement = statement.where(or_(Contract.applies_to_all_clients.in_([True]), Contract.client_id == parent_value, Contract.client_links.any(ContractClientLink.client_id == parent_value)))
        if term:
            statement = statement.where(or_(Contract.name.ilike(term), Contract.contract_number.ilike(term)))
        rows = list(db.execute(statement.order_by(Contract.name).limit(100)))
    elif source == "ticket_types":
        statement = select(TicketType.name, TicketType.name, TicketType.code).where(TicketType.is_active.in_([True]))
        if term:
            statement = statement.where(or_(TicketType.name.ilike(term), TicketType.code.ilike(term)))
        rows = list(db.execute(statement.order_by(TicketType.name).limit(100)))
    else:
        statement = select(TicketStatus.code, TicketStatus.name, TicketStatus.code)
        if term:
            statement = statement.where(or_(TicketStatus.name.ilike(term), TicketStatus.code.ilike(term)))
        rows = list(db.execute(statement.order_by(TicketStatus.name).limit(100)))
    return [
        {"value": value, "label": str(label), "code": str(code or "")}
        for value, label, code in rows
    ]


def convert_filter(definition: FilterDefinition, raw: Any) -> Any:
    if raw in (None, ""):
        if definition.required:
            raise ConflictError("REPORT_FILTER_REQUIRED", f"{definition.label} is required.")
        return None
    try:
        if definition.type == "number":
            return int(raw)
        if definition.type == "boolean":
            return raw if isinstance(raw, bool) else str(raw).lower() in {"1", "true", "yes"}
        if definition.type == "date":
            return date.fromisoformat(str(raw))
        return str(raw)[:1000]
    except (TypeError, ValueError) as exc:
        raise ConflictError("INVALID_REPORT_FILTER", f"{definition.label} has an invalid value.") from exc


def validate_report_scope(
    definitions: list[FilterDefinition], parameters: dict[str, Any]
) -> None:
    """Prevent an accidental unbounded report from reaching SQL Server."""
    date_filters = [item for item in definitions if item.type == "date"]
    mandatory_dates = [item for item in date_filters if item.required or item.default != ""]
    if mandatory_dates:
        missing = [item.label for item in mandatory_dates if parameters.get(item.name) is None]
        if missing:
            raise ConflictError(
                "REPORT_DATE_RANGE_REQUIRED",
                "Select the complete report date range before running the report.",
            )
    for date_from_definition in (item for item in date_filters if item.name.endswith("_from")):
        prefix = date_from_definition.name.removesuffix("_from")
        date_to_definition = next(
            (item for item in date_filters if item.name == f"{prefix}_to"), None
        )
        if date_to_definition is None:
            continue
        date_from = parameters.get(date_from_definition.name)
        date_to = parameters.get(date_to_definition.name)
        if (date_from is None) != (date_to is None):
            raise ConflictError(
                "REPORT_DATE_RANGE_REQUIRED",
                f"Select both {date_from_definition.label} and {date_to_definition.label}.",
            )
        if isinstance(date_from, date) and isinstance(date_to, date):
            if date_to < date_from:
                raise ConflictError("INVALID_REPORT_DATE_RANGE", "Date to cannot be before Date from.")
            if (date_to - date_from).days > MAX_REPORT_DATE_RANGE_DAYS:
                raise ConflictError(
                    "REPORT_DATE_RANGE_TOO_LARGE",
                    f"Choose a report period of {MAX_REPORT_DATE_RANGE_DAYS} days or less.",
                )
    if not any(value not in (None, "", False) for value in parameters.values()):
        raise ConflictError(
            "REPORT_FILTER_REQUIRED",
            "Select at least one filter before running a report without a date range.",
        )


def execute_report(
    db: Session,
    definition: DynamicReportDefinition,
    data: RunReportIn,
    actor: User,
    export: bool = False,
) -> dict[str, object]:
    if data.page_size not in PAGE_SIZES:
        raise ConflictError("INVALID_REPORT_PAGE_SIZE", "Choose 25, 50, 100, or 250 rows.")
    filters = [FilterDefinition.model_validate(item) for item in json.loads(definition.filters_json)]
    declared = {item.name: item for item in filters}
    unknown = set(data.filters) - set(declared)
    if unknown:
        raise ConflictError("UNKNOWN_REPORT_FILTER", "The request contains an undeclared report filter.")
    parameters = {
        item.name: convert_filter(item, data.filters.get(item.name, item.default)) for item in filters
    }
    validate_report_scope(filters, parameters)
    sort_by = data.sort_by or definition.default_sort_column
    if sort_by and not IDENTIFIER.fullmatch(sort_by):
        raise ConflictError("INVALID_REPORT_SORT", "The selected sort column is invalid.")
    parameters.update(
        page=1 if export else data.page,
        page_size=10000 if export else data.page_size,
        sort_by=sort_by,
        sort_direction=data.sort_direction,
        requesting_user_id=actor.id,
    )
    if db.bind is None or db.bind.dialect.name != "mssql":
        raise ConflictError(
            "REPORT_PROCEDURE_REQUIRES_SQL_SERVER",
            "Dynamic stored-procedure reports require the SQL Server database provider.",
        )
    procedure = ".".join(f"[{part}]" for part in definition.stored_procedure.split("."))
    assignments = ", ".join(f"@{name}=:{name}" for name in parameters)
    result = db.execute(text(f"EXEC {procedure} {assignments}"), parameters)
    result_columns = [key for key in result.keys() if not key.startswith("__")]
    raw_rows = [dict(row) for row in result.mappings().all()]
    total = int(raw_rows[0].get("__total_count", len(raw_rows))) if raw_rows else 0
    summary = {
        key.removeprefix("__summary_"): value
        for key, value in (raw_rows[0].items() if raw_rows else [])
        if key.startswith("__summary_")
    }
    rows = [
        {key: value for key, value in row.items() if not key.startswith("__")}
        for row in raw_rows
    ]
    columns = [
        {
            "field": key,
            "label": key.replace("_", " ").title(),
            "type": type(rows[0].get(key)).__name__ if rows else "unknown",
        }
        for key in result_columns
    ]
    return {
        "definition": definition_payload(definition),
        "columns": columns,
        "rows": rows,
        "summary": summary,
        "pagination": {
            "page": data.page,
            "page_size": data.page_size,
            "total_records": total,
            "total_pages": (total + data.page_size - 1) // data.page_size,
        },
    }


@router.get("")
def report_catalog(
    db: Session = Depends(get_db), _: User = Depends(require_permission("report.view"))
) -> list[dict[str, object]]:
    return [
        definition_payload(row)
        for row in db.query(DynamicReportDefinition)
        .filter(DynamicReportDefinition.is_active.in_([True]))
        .order_by(DynamicReportDefinition.category, DynamicReportDefinition.name)
    ]


@router.get("/definitions")
def report_definitions(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("dashboard.manage_widgets")),
) -> list[dict[str, object]]:
    return [definition_payload(row) for row in db.query(DynamicReportDefinition).order_by(DynamicReportDefinition.name)]


@router.post("/definitions", status_code=201)
def create_report_definition(
    data: ReportDefinitionIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("dashboard.manage_widgets")),
) -> dict[str, object]:
    validated_definition(data)
    row = DynamicReportDefinition(
        **data.model_dump(exclude={"filters"}), filters_json=json.dumps([item.model_dump() for item in data.filters])
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return definition_payload(row)


@router.patch("/definitions/{report_id}")
def update_report_definition(
    report_id: int,
    data: ReportDefinitionIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("dashboard.manage_widgets")),
) -> dict[str, object]:
    validated_definition(data)
    row = db.get(DynamicReportDefinition, report_id)
    if not row:
        raise NotFoundError()
    for key, value in data.model_dump(exclude={"filters"}).items():
        setattr(row, key, value)
    row.filters_json = json.dumps([item.model_dump() for item in data.filters])
    db.commit()
    return definition_payload(row)


@router.post("/{code}/run")
def run_report(
    code: str,
    data: RunReportIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("report.view")),
) -> dict[str, object]:
    definition = db.query(DynamicReportDefinition).filter_by(code=code, is_active=True).first()
    if not definition:
        raise NotFoundError()
    return execute_report(db, definition, data, actor)


@router.post("/{code}/export.xlsx")
def export_report(
    code: str,
    data: RunReportIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("report.export")),
) -> StreamingResponse:
    definition = db.query(DynamicReportDefinition).filter_by(code=code, is_active=True).first()
    if not definition:
        raise NotFoundError()
    report = execute_report(db, definition, data, actor, export=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Report"
    report_columns = cast(list[dict[str, Any]], report["columns"])
    report_rows = cast(list[dict[str, Any]], report["rows"])
    columns = [item["field"] for item in report_columns]
    sheet.append([item["label"] for item in report_columns])
    for row in report_rows:
        sheet.append([safe_cell(row.get(column)) for column in columns])
    style_hr_sheet(sheet)
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="DynamicReport", entity_id=code, action="report.exported", new_values_json=json.dumps({"filters": data.filters})))
    db.commit()
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{code}-{datetime.now().date()}.xlsx"'})
