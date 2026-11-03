import hashlib
import io
import json
import re
import secrets
from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

from openpyxl import Workbook, load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_now, server_timezone
from app.core.exceptions import ConflictError, NotFoundError
from app.modules.clients.models import (
    Branch,
    City,
    Client,
    ClientAccessCredential,
    ClientInstallation,
    ClientLocation,
    ClientStatus,
    Contact,
    Country,
    Environment,
    Product,
    ProductModule,
    ServiceCatalogItem,
    SupportSkill,
    SupportTeam,
    TicketCategory,
    TicketSubcategory,
    Vendor,
)
from app.modules.contracts.models import (
    BusinessCalendar,
    Contract,
    ContractCoverage,
    ContractCoverageClient,
    ContractCoverageRevision,
    SlaPolicy,
    SlaTarget,
)
from app.modules.iam.models import Department, Profile, User, UserClientScope, UserProfile
from app.modules.iam.security import hash_password
from app.modules.iam.service import normalize
from app.modules.imports.models import ImportError, ImportJob, ImportRow
from app.modules.project_handovers.models import HandoverRecipient, ProjectHandover
from app.modules.shifts.models import Shift, ShiftType
from app.modules.tickets.models import (
    RootCause,
    Ticket,
    TicketAssignmentHistory,
    TicketComment,
    TicketStatus,
    TicketStatusHistory,
    TicketType,
)

TEMPLATES: dict[str, list[str]] = {
    "MASTER_DATA": ["DataType", "Code", "Name", "ParentCode", "Description", "Alpha2", "Alpha3", "DefaultTimezone", "Color", "NumberPrefix", "ContactName", "Email", "Phone", "IsProduction", "PortalAllowed", "TicketCreationAllowed", "IsClosed", "IsSlaPause", "SortOrder", "IsActive"],
    "INSTALLATIONS": ["ClientCode", "BranchCode", "ProductCode", "ModuleCode", "EnvironmentCode", "InstallationName", "Version", "ServerName", "DatabaseName", "SupportOwner", "IsActive"],
    "CLIENTS": ["ClientCode", "ClientName", "StatusCode", "TimeZone", "Phone", "Email", "Address", "Notes", "SupportStartedAt", "CountryCode", "CityCode", "PrimaryLocationCode", "PrimaryLocationName", "LocationZone", "Latitude", "Longitude", "IsActive"],
    "CLIENT_ACCESS": ["ClientCode", "AccessType", "Label", "ServerOrAddress", "Username", "Notes", "IsActive"],
    "BRANCHES": ["ClientCode", "BranchCode", "BranchName", "TimeZone", "Phone", "Email", "Address"],
    "PRODUCTS_MODULES": [
        "ProductCode",
        "ProductName",
        "ProductDescription",
        "ModuleCode",
        "ModuleName",
    ],
    "SERVICES": ["ServiceCode", "ServiceName", "Description", "IsActive"],
    "SLA_POLICIES": ["PolicyCode", "PolicyName", "CalendarName", "ServiceCode", "Priority", "FirstResponseMinutes", "ResolutionMinutes", "WarningPercent", "IsActive"],
    "CONTACTS": ["ClientCode", "FullName", "Email", "Phone", "JobTitle", "ContactRole", "IsPrimary", "IsEscalation", "IsActive"],
    "USERS": ["Username", "FullName", "Email", "EmployeeCode", "Phone", "Department", "JobTitle", "UserType", "ClientCode", "IsActive"],
    "USER_PROFILES": ["Username", "ProfileCode", "IsPrimary", "AssignmentReason"],
    "CONTRACTS": ["ContractNumber", "ClientCode", "Name", "Status", "StartDate", "EndDate", "TimeZone", "CalendarName", "SlaPolicyCode", "IncludedRequestLimit", "SupportSummary", "Exclusions", "IsActive"],
    "CONTRACT_COVERAGE": ["ContractNumber", "ProductCode", "ModuleCode", "ServiceCode", "TicketTypeCode", "EnvironmentCode", "EffectiveFrom", "EffectiveUntil", "AppliesToAllClients", "ClientCodes", "ExcludedClientCodes", "IsCovered", "Notes", "ChangeReason"],
    "SHIFTS": ["Username", "ShiftTypeCode", "StartsAt", "EndsAt", "WorkLocation", "Team", "OnCallRole", "Notes"],
    "TICKETS": ["LegacyTicketNumber", "TicketTypeCode", "ClientCode", "StatusCode", "CreatedByUsername", "AssignedUsername", "AssignedTeam", "EscalationUsername", "ContractNumber", "ProductCode", "ModuleCode", "EnvironmentCode", "ServiceCode", "Priority", "Impact", "Urgency", "Subject", "Description", "Source", "CreatedAt", "ResolvedAt", "ClosedAt", "ResolutionSummary"],
    "ITOP_TICKETS": ["Ref", "Title", "Organization->Name", "Caller->Full name", "Agent->Full name", "Start date", "Status"],
    "PROJECT_HANDOVERS": ["ProjectNumber", "ProjectName", "ClientCode", "DeliveredByUsername", "RecipientUsernames", "ProjectManagerUsername", "WarrantyMonths", "WarrantyStartDate", "AcceptanceDate", "CurrentStatus", "PendingPoints", "Notes"],
}
EXTERNAL_USER_REQUEST_HEADERS = [
    "Ref", "Title", "Agent->Full name", "Organization->Name", "Caller->Full name",
    "Start date", "Priority", "Assignment date", "Resolution delay", "Status", "Service",
    "Service->Name", "Service->Full name", "Service->Provider", "Service->Provider Name",
    "id (Primary Key)", "Resolution date",
]
MAX_FILE_SIZE = 5 * 1024 * 1024


def _flag(value: str, default: bool = True) -> bool:
    return default if not value else value.casefold() in {"true", "yes", "1"}


def _date(value: str) -> date | None:
    return date.fromisoformat(value[:10]) if value else None


def _datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=server_timezone()) if parsed.tzinfo is None else parsed


def _user(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username_normalized == normalize(username)))


def _unique_normalized_match(items: Iterable[Any], value: str, attribute: str) -> Any | None:
    wanted = normalize(value)
    if not wanted:
        return None
    matches = [item for item in items if normalize(str(getattr(item, attribute, ""))) == wanted]
    return matches[0] if len(matches) == 1 else None


def _external_user_request_record(
    db: Session, values: dict[str, str], importing_user: User | None
) -> tuple[dict[str, str], list[tuple[str | None, str, str]]]:
    errors: list[tuple[str | None, str, str]] = []
    organization = values["Organization->Name"]
    client = _unique_normalized_match(db.scalars(select(Client)), organization, "name")
    if not organization:
        errors.append(("Organization->Name", "REQUIRED", "Organization name is required."))
    elif not client:
        errors.append(("Organization->Name", "REFERENCE_INVALID", "Organization name must match one unique Support Hub client name."))

    agent_name = values["Agent->Full name"]
    agent = _unique_normalized_match(db.scalars(select(User)), agent_name, "full_name")
    if agent_name and not agent:
        errors.append(("Agent->Full name", "REFERENCE_INVALID", "Agent full name must match one unique Support Hub user."))

    status_aliases = {"assigned": "ASSIGNED", "closed": "CLOSED", "resolved": "RESOLVED", "waiting for approval": "CLIENT_CONFIRMATION"}
    status_value = values["Status"]
    status_code = status_aliases.get(normalize(status_value))
    if not status_code:
        status = _unique_normalized_match(db.scalars(select(TicketStatus)), status_value, "name")
        status_code = status.code if status else ""
    if status_value and not status_code:
        errors.append(("Status", "REFERENCE_INVALID", "Status does not match a Support Hub ticket status."))

    priority_aliases = {"critical": "P1", "high": "P2", "medium": "P3", "low": "P4"}
    priority_value = values["Priority"]
    priority = priority_aliases.get(normalize(priority_value), priority_value.upper())
    if priority not in {"P1", "P2", "P3", "P4"}:
        errors.append(("Priority", "VALUE_INVALID", "Priority must be Critical, High, Medium, Low, or P1-P4."))

    service_name = values["Service->Full name"] or values["Service->Name"] or values["Service"]
    service = _unique_normalized_match(db.scalars(select(ServiceCatalogItem)), service_name, "name")
    caller_name = values["Caller->Full name"]
    contact = None
    if client and caller_name:
        contact = _unique_normalized_match(db.scalars(select(Contact).where(Contact.client_id == client.id)), caller_name, "full_name")

    metadata = [f"Imported from legacy user request {values['Ref'] or values['id (Primary Key)']}." ]
    if caller_name:
        metadata.append(f"Legacy caller: {caller_name}.")
    if service_name and not service:
        metadata.append(f"Legacy service: {service_name}.")
    if values["id (Primary Key)"]:
        metadata.append(f"Legacy primary key: {values['id (Primary Key)']}.")

    return {
        "LegacyTicketNumber": values["Ref"], "TicketTypeCode": "SERVICE_REQUEST",
        "ClientCode": client.code if client else "", "StatusCode": status_code or "",
        "CreatedByUsername": importing_user.username if importing_user else "",
        "AssignedUsername": agent.username if agent else "", "AssignedTeam": values["Service->Provider Name"],
        "EscalationUsername": "", "ContractNumber": "", "ProductCode": "", "ModuleCode": "",
        "EnvironmentCode": "", "ServiceCode": service.code if service else "", "Priority": priority,
        "Impact": "MEDIUM", "Urgency": "MEDIUM", "Subject": values["Title"],
        "Description": " ".join(metadata), "Source": "OTHER", "CreatedAt": values["Start date"],
        "ResolvedAt": values["Resolution date"], "ClosedAt": values["Resolution date"] if status_code == "CLOSED" else "",
        "ResolutionSummary": "Imported resolved legacy request." if values["Resolution date"] else "",
        "_RequesterContactId": str(contact.id) if contact else "",
    }, errors


def _itop_ticket_record(
    db: Session, values: dict[str, str], importing_user: User | None
) -> tuple[dict[str, str], list[tuple[str | None, str, str]]]:
    errors: list[tuple[str | None, str, str]] = []
    client_name = values.get("Organization->Name", "").strip()
    client = _unique_normalized_match(db.scalars(select(Client)), client_name, "name")
    engineer_name = values.get("Agent->Full name", "").strip()
    engineer_email = values.get("Agent->Email", "").strip()
    engineer = db.scalar(select(User).where(User.email_normalized == normalize(engineer_email))) if engineer_email else None
    engineer = engineer or _unique_normalized_match(db.scalars(select(User)), engineer_name, "full_name")
    caller_name = values.get("Caller->Full name", "").strip()
    caller_email = values.get("Caller->Email", "").strip()
    caller = None
    if client and caller_email:
        caller = db.scalar(select(Contact).where(Contact.client_id == client.id, Contact.email == caller_email))
    if client and not caller and caller_name:
        caller = _unique_normalized_match(db.scalars(select(Contact).where(Contact.client_id == client.id)), caller_name, "full_name")

    if not values.get("Ref") and not values.get("id (Primary Key)"):
        errors.append(("Ref", "REQUIRED", "ITOP Ref or primary key is required."))
    if len(values.get("Title", "").strip()) < 5:
        errors.append(("Title", "REQUIRED", "Title must contain at least five characters."))
    if not client_name:
        errors.append(("Organization->Name", "REQUIRED", "Organization name is required."))

    status_aliases = {
        "assigned": "ASSIGNED", "ongoing": "IN_PROGRESS", "resolved": "RESOLVED",
        "closed": "CLOSED", "pending": "PENDING_CLIENT", "waiting for approval": "CLIENT_CONFIRMATION",
    }
    status_text = values.get("Status", "")
    status_code = status_aliases.get(normalize(status_text), "ASSIGNED")
    priority = {"critical": "P1", "high": "P2", "medium": "P3", "low": "P4"}.get(normalize(values.get("Priority", "")), "P3")
    level = {"critical": "CRITICAL", "high": "HIGH", "medium": "MEDIUM", "low": "LOW"}
    impact = level.get(normalize(values.get("Impact", "")), "MEDIUM")
    urgency = level.get(normalize(values.get("Urgency", "")), "MEDIUM")
    description = values.get("Description", "").strip() or values.get("Title", "").strip()
    provenance = f"Imported from ITOP record {values.get('Ref') or values.get('id (Primary Key)')}."
    return {
        "LegacyTicketNumber": values.get("Ref", ""), "TicketTypeCode": "SERVICE_REQUEST",
        "ClientCode": client.code if client else "", "StatusCode": status_code,
        "CreatedByUsername": importing_user.username if importing_user else "",
        "AssignedUsername": engineer.username if engineer else "", "AssignedTeam": values.get("Team->Name", "") or values.get("Team", ""),
        "Priority": priority, "Impact": impact, "Urgency": urgency,
        "Subject": values.get("Title", "").strip(), "Description": f"{description[:19000]}\n\n{provenance}",
        "Source": values.get("Origin", "") or "ITOP_IMPORT", "CreatedAt": values.get("Start date", ""),
        "AssignedAt": values.get("Assignment date", ""), "ResolvedAt": values.get("Resolution date", ""),
        "ClosedAt": values.get("Close date", ""), "UpdatedAt": values.get("Last update", ""),
        "ResolutionSummary": values.get("Solution", "").strip(), "PublicLog": values.get("Public log", "").strip(),
        "PrivateLog": values.get("Private log", "").strip(), "ResolutionCode": values.get("Resolution code", "").strip(),
        "_RequesterContactId": str(caller.id) if caller else "", "_ClientName": client_name,
        "_ClientLegacyCode": values.get("Organization->Code", "").strip(), "_EngineerName": engineer_name,
        "_EngineerEmail": engineer_email, "_EngineerEmployeeCode": values.get("Agent->Employee number", "").strip(),
        "_CallerName": caller_name, "_CallerEmail": caller_email,
    }, errors


def template_bytes(template_type: str, db: Session | None = None) -> bytes:
    headers = TEMPLATES.get(template_type)
    if not headers:
        raise NotFoundError("Import template does not exist.")
    book = Workbook()
    instructions = book.active
    instructions.title = "Instructions"
    instructions.append(["Millensys Support Hub controlled import template"])
    instructions.append(["TemplateType", template_type])
    instructions.append(["TemplateVersion", "1.0"])
    instructions.append(["Do not rename sheets or headers. Formulas are rejected."])
    instructions.append(["Workflow", "Import and confirm the parent task before downloading its dependent template."])
    if template_type in {"BRANCHES", "CONTACTS", "CLIENT_ACCESS", "INSTALLATIONS"}:
        instructions.append(["Client relationship", "Use ClientCode from Reference Values. Repeat the same ClientCode on as many rows as needed."])
    data = book.create_sheet("Data")
    data.append(headers)
    reference = book.create_sheet("Reference Values")

    def section(title: str, columns: list[str], rows: Iterable[Any]) -> None:
        if reference.max_row > 1 or reference.cell(1, 1).value is not None:
            reference.append([])
        reference.append([title])
        reference.append(columns)
        for values in rows:
            reference.append(list(values))

    clients = list(db.execute(select(Client.code, Client.name).order_by(Client.name)).all()) if db else []
    users = list(db.execute(select(User.username, User.full_name).order_by(User.full_name)).all()) if db else []
    if template_type == "CLIENTS":
        statuses = list(db.execute(select(ClientStatus.code, ClientStatus.name).order_by(ClientStatus.name)).all()) if db else [(code, code.replace("_", " ").title()) for code in ("PROSPECT", "IMPLEMENTATION", "ACTIVE", "ON_HOLD", "SUSPENDED", "EXPIRED_CONTRACT", "TERMINATED")]
        section("Allowed client statuses", ["StatusCode", "StatusName"], statuses)
        countries = list(db.execute(select(Country.iso_alpha3, Country.name).order_by(Country.name)).all()) if db else []
        cities = list(db.execute(select(Country.iso_alpha3, City.code, City.name).join(Country, Country.id == City.country_id).order_by(Country.name, City.name)).all()) if db else []
        section("Optional countries", ["CountryCode", "CountryName"], countries)
        section("Optional cities", ["CountryCode", "CityCode", "CityName"], cities)
    elif template_type == "MASTER_DATA":
        section("Supported master data", ["DataType", "ParentCode use"], [
            ("COUNTRY", "None"), ("CITY", "Country Alpha3"), ("DEPARTMENT", "None"),
            ("PRODUCT", "None"), ("PRODUCT_MODULE", "Product code"), ("SERVICE", "None"),
            ("VENDOR", "None"), ("CLIENT_STATUS", "None"), ("TICKET_STATUS", "None"),
            ("TICKET_TYPE", "None"), ("ENVIRONMENT", "None"), ("TICKET_CATEGORY", "None"),
            ("TICKET_SUBCATEGORY", "Ticket category code"), ("ROOT_CAUSE", "None"),
            ("SKILL", "None"), ("SUPPORT_TEAM", "None"),
        ])
    elif template_type == "CLIENT_ACCESS":
        section("Existing clients", ["ClientCode", "ClientName"], clients)
        section("Allowed access types", ["AccessType", "Important"], [(code, "Passwords are added securely in the Client Access Vault after import.") for code in ("SERVER", "VPN", "ANYDESK", "SYSTEM_ADMIN", "OTHER")])
    elif template_type in {"BRANCHES", "CONTACTS"}:
        section("Existing clients", ["ClientCode", "ClientName"], clients)
    elif template_type == "INSTALLATIONS":
        section("Existing clients", ["ClientCode", "ClientName"], clients)
        products = list(db.execute(select(Product.code, Product.name).order_by(Product.name)).all()) if db else []
        environments = list(db.execute(select(Environment.code, Environment.name).order_by(Environment.name)).all()) if db else []
        section("Products", ["ProductCode", "ProductName"], products)
        section("Environments", ["EnvironmentCode", "EnvironmentName"], environments)
    elif template_type == "PRODUCTS_MODULES":
        products = list(db.execute(select(Product.code, Product.name).order_by(Product.name)).all()) if db else []
        section("Existing products", ["ProductCode", "ProductName"], products)
    elif template_type == "SERVICES":
        services = list(db.execute(select(ServiceCatalogItem.code, ServiceCatalogItem.name).order_by(ServiceCatalogItem.name)).all()) if db else []
        section("Existing services", ["ServiceCode", "ServiceName"], services)
    elif template_type == "SLA_POLICIES":
        calendars = list(db.execute(select(BusinessCalendar.name, BusinessCalendar.timezone).order_by(BusinessCalendar.name)).all()) if db else []
        services = list(db.execute(select(ServiceCatalogItem.code, ServiceCatalogItem.name).order_by(ServiceCatalogItem.name)).all()) if db else []
        section("Business calendars", ["CalendarName", "TimeZone"], calendars)
        section("Services (blank means default)", ["ServiceCode", "ServiceName"], services)
        section("Allowed priorities", ["Priority"], [(item,) for item in ("P1", "P2", "P3", "P4")])
    elif template_type == "USERS":
        section("Existing clients for portal users", ["ClientCode", "ClientName"], clients)
        section("Allowed user types", ["UserType", "Password handling"], [("EMPLOYEE", "A secure reset-only password is generated."), ("CLIENT_PORTAL", "ClientCode is required; use Forgot Password to activate.")])
    elif template_type == "USER_PROFILES":
        profiles = list(db.execute(select(Profile.code, Profile.name).order_by(Profile.name)).all()) if db else []
        section("Existing users", ["Username", "FullName"], users)
        section("Available groups / profiles", ["ProfileCode", "ProfileName"], profiles)
    elif template_type == "CONTRACTS":
        calendars = list(db.execute(select(BusinessCalendar.name, BusinessCalendar.timezone).order_by(BusinessCalendar.name)).all()) if db else []
        section("Existing clients", ["ClientCode", "ClientName"], clients)
        section("Business calendars", ["CalendarName", "TimeZone"], calendars)
        policies = list(db.execute(select(SlaPolicy.code, SlaPolicy.name).where(SlaPolicy.contract_id.is_(None)).order_by(SlaPolicy.name)).all()) if db else []
        section("Central SLA policies", ["SlaPolicyCode", "SlaPolicyName"], policies)
    elif template_type == "CONTRACT_COVERAGE":
        contracts = list(db.execute(select(Contract.contract_number, Contract.name).order_by(Contract.contract_number)).all()) if db else []
        products = list(db.execute(select(Product.code, Product.name).order_by(Product.name)).all()) if db else []
        modules = list(db.execute(select(Product.code, ProductModule.code, ProductModule.name).join(ProductModule, ProductModule.product_id == Product.id).order_by(Product.code, ProductModule.name)).all()) if db else []
        services = list(db.execute(select(ServiceCatalogItem.code, ServiceCatalogItem.name).order_by(ServiceCatalogItem.name)).all()) if db else []
        section("Existing contracts", ["ContractNumber", "ContractName"], contracts)
        section("Products", ["ProductCode", "ProductName"], products)
        section("Modules (must match product)", ["ProductCode", "ModuleCode", "ModuleName"], modules)
        section("Services", ["ServiceCode", "ServiceName"], services)
    elif template_type == "SHIFTS":
        shift_types = list(db.execute(select(ShiftType.code, ShiftType.name).order_by(ShiftType.name)).all()) if db else []
        section("Existing users", ["Username", "FullName"], users)
        section("Shift types", ["ShiftTypeCode", "ShiftTypeName"], shift_types)
        section("Work locations", ["WorkLocation"], [(item,) for item in ("OFFICE", "WORK_FROM_HOME", "HYBRID")])
    elif template_type == "PROJECT_HANDOVERS":
        section("Existing clients", ["ClientCode", "ClientName"], clients)
        section("Available users", ["Username", "FullName"], users)
    elif template_type == "TICKETS":
        ticket_types = list(db.execute(select(TicketType.code, TicketType.name).order_by(TicketType.name)).all()) if db else []
        statuses = list(db.execute(select(TicketStatus.code, TicketStatus.name).order_by(TicketStatus.sort_order)).all()) if db else []
        section("Existing clients", ["ClientCode", "ClientName"], clients)
        section("Available users", ["Username", "FullName"], users)
        section("Ticket types", ["TicketTypeCode", "TicketTypeName"], ticket_types)
        section("Ticket statuses", ["StatusCode", "StatusName"], statuses)
        section("Allowed values", ["Priority", "Impact/Urgency", "Source"], [("P1/P2/P3/P4", "LOW/MEDIUM/HIGH/CRITICAL", "WEB/PHONE/EMAIL/WALK_IN/MONITORING/OTHER/CLIENT_PORTAL")])
    stream = io.BytesIO()
    book.save(stream)
    return stream.getvalue()


def stage_workbook(db: Session, content: bytes, filename: str, template_type: str, user_id: int) -> ImportJob:
    if len(content) > MAX_FILE_SIZE:
        raise ConflictError("IMPORT_FILE_TOO_LARGE", "Workbook exceeds the 5 MB limit.")
    if not content.startswith(b"PK") or not filename.lower().endswith(".xlsx"):
        raise ConflictError("IMPORT_FILE_INVALID", "Only valid .xlsx workbooks are accepted.")
    digest = hashlib.sha256(content).hexdigest()
    if db.scalar(select(ImportJob.id).where(ImportJob.file_hash == digest)):
        raise ConflictError("IMPORT_REPLAY", "This workbook has already been uploaded.")
    headers = TEMPLATES.get(template_type)
    if not headers:
        raise NotFoundError("Import template does not exist.")
    try:
        book = load_workbook(io.BytesIO(content), data_only=False, read_only=True)
    except Exception as exc:
        raise ConflictError("IMPORT_FILE_INVALID", "The workbook cannot be read.") from exc
    external_user_requests = template_type == "TICKETS" and len(book.sheetnames) == 1
    external_itop = template_type == "ITOP_TICKETS" and len(book.sheetnames) == 1
    if not external_user_requests and not external_itop and set(book.sheetnames) != {"Instructions", "Data", "Reference Values"}:
        raise ConflictError("IMPORT_SHEETS_INVALID", "Workbook sheets do not match the controlled template.")
    declared_type = "" if external_user_requests or external_itop else str(book["Instructions"]["B2"].value or "").strip().upper()
    if declared_type and declared_type != template_type:
        raise ConflictError(
            "IMPORT_TEMPLATE_TYPE_MISMATCH",
            f"This is a {declared_type} workbook, but {template_type} is selected. "
            "Select the matching import task and upload it again.",
        )
    sheet = book[book.sheetnames[0]] if external_user_requests or external_itop else book["Data"]
    actual_headers = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
    # Excel can retain formatted but empty columns after users paste data into the
    # controlled template. They are not real headers and should not invalidate it.
    while actual_headers and (
        actual_headers[-1] is None or str(actual_headers[-1]).strip() == ""
    ):
        actual_headers.pop()
    expected_headers = actual_headers if external_itop else EXTERNAL_USER_REQUEST_HEADERS if external_user_requests else headers
    headers_valid = set(headers).issubset(set(actual_headers)) if external_itop else actual_headers == expected_headers
    if not headers_valid:
        detected = ", ".join(
            "(blank)" if value is None else str(value) for value in actual_headers
        ) or "(none)"
        raise ConflictError(
            "IMPORT_HEADERS_INVALID",
            "Data headers do not match the controlled template. "
            f"Expected required columns: {', '.join(headers)}. Detected: {detected}.",
        )
    job = ImportJob(template_type=template_type, template_version="itop-native-1.0" if external_itop else "external-user-request-1.0" if external_user_requests else "1.0", original_filename=filename[:255], file_hash=digest, uploaded_by_user_id=user_id)
    db.add(job)
    db.flush()
    seen: set[str] = set()
    planned_master_codes = {
        (str(row[0].value or "").strip().upper(), str(row[1].value or "").strip().upper())
        for row in sheet.iter_rows(min_row=2)
    } if template_type == "MASTER_DATA" else set()
    importing_user = db.get(User, user_id) if external_user_requests or external_itop else None
    ticket_clients = {item.code: item for item in db.scalars(select(Client))} if template_type == "TICKETS" else {}
    ticket_users = {item.username_normalized: item for item in db.scalars(select(User))} if template_type == "TICKETS" else {}
    ticket_types = {item.code: item for item in db.scalars(select(TicketType))} if template_type == "TICKETS" else {}
    ticket_statuses = {item.code: item for item in db.scalars(select(TicketStatus))} if template_type == "TICKETS" else {}
    ticket_contracts = {item.contract_number: item for item in db.scalars(select(Contract))} if template_type == "TICKETS" else {}
    ticket_products = {item.code: item for item in db.scalars(select(Product))} if template_type == "TICKETS" else {}
    ticket_services = {item.code: item for item in db.scalars(select(ServiceCatalogItem))} if template_type == "TICKETS" else {}
    ticket_environments = {item.code: item for item in db.scalars(select(Environment))} if template_type == "TICKETS" else {}
    ticket_modules = {(item.product_id, item.code): item for item in db.scalars(select(ProductModule))} if template_type == "TICKETS" else {}
    existing_ticket_numbers = set(db.scalars(select(Ticket.ticket_number))) if template_type in {"TICKETS", "ITOP_TICKETS"} else set()
    for row_number, cells in enumerate(sheet.iter_rows(min_row=2), start=2):
        values = [cell.value for cell in cells]
        if all(value is None or str(value).strip() == "" for value in values):
            continue
        source_record = {header: (str(value).strip() if value is not None else "") for header, value in zip(expected_headers, values, strict=True)}
        errors: list[tuple[str | None, str, str]] = []
        for header, cell in zip(expected_headers, cells, strict=True):
            unsafe_prefixes = ("=", "+", "@") if external_itop else ("=", "+", "-", "@")
            if cell.data_type == "f" or (isinstance(cell.value, str) and cell.value.startswith(unsafe_prefixes)):
                errors.append((header, "FORMULA_REJECTED", "Formulas and executable spreadsheet values are not allowed."))
        if external_user_requests:
            record, conversion_errors = _external_user_request_record(db, source_record, importing_user)
            errors.extend(conversion_errors)
        elif external_itop:
            record, conversion_errors = _itop_ticket_record(db, source_record, importing_user)
            errors.extend(conversion_errors)
        else:
            record = source_record
        required = {
            "MASTER_DATA": ["DataType", "Code", "Name"],
            "INSTALLATIONS": ["ClientCode", "ProductCode", "EnvironmentCode", "InstallationName"],
            "CLIENTS": ["ClientCode", "ClientName", "StatusCode"],
            "CLIENT_ACCESS": ["ClientCode", "AccessType", "Label"],
            "BRANCHES": ["ClientCode", "BranchCode", "BranchName"],
            "PRODUCTS_MODULES": ["ProductCode", "ProductName", "ModuleCode", "ModuleName"],
            "SERVICES": ["ServiceCode", "ServiceName"],
            "SLA_POLICIES": ["PolicyCode", "PolicyName", "CalendarName", "Priority", "FirstResponseMinutes", "ResolutionMinutes"],
            "CONTACTS": ["ClientCode", "FullName"],
            "USERS": ["Username", "FullName", "Email", "UserType"],
            "USER_PROFILES": ["Username", "ProfileCode"],
            "CONTRACTS": ["ContractNumber", "ClientCode", "Name", "StartDate", "EndDate", "CalendarName"],
            "CONTRACT_COVERAGE": ["ContractNumber"],
            "SHIFTS": ["Username", "ShiftTypeCode", "StartsAt", "EndsAt"],
            "TICKETS": ["TicketTypeCode", "ClientCode", "StatusCode", "CreatedByUsername", "Subject", "Description"],
            "ITOP_TICKETS": ["StatusCode", "CreatedByUsername", "Subject", "Description"],
            "PROJECT_HANDOVERS": ["ProjectNumber", "ProjectName", "ClientCode", "DeliveredByUsername"],
        }[template_type]
        for field in required:
            if not record[field]:
                errors.append((field, "REQUIRED", f"{field} is required."))
        if template_type == "MASTER_DATA":
            key = f"{record['DataType'].casefold()}::{record['ParentCode'].casefold()}::{record['Code'].casefold()}"
        elif template_type == "CLIENTS":
            key = record["ClientCode"].casefold()
        elif template_type == "INSTALLATIONS":
            key = f"{record['ClientCode'].casefold()}::{record['ProductCode'].casefold()}::{record['EnvironmentCode'].casefold()}::{record['InstallationName'].casefold()}"
        elif template_type == "CLIENT_ACCESS":
            key = f"{record['ClientCode'].casefold()}::{record['AccessType'].casefold()}::{record['Label'].casefold()}"
        elif template_type == "BRANCHES":
            key = f"{record['ClientCode'].casefold()}::{record['BranchCode'].casefold()}"
        elif template_type == "PRODUCTS_MODULES":
            key = f"{record['ProductCode'].casefold()}::{record['ModuleCode'].casefold()}"
        elif template_type == "SERVICES": key = record["ServiceCode"].casefold()
        elif template_type == "SLA_POLICIES": key = f"{record['PolicyCode'].casefold()}::{record['ServiceCode'].casefold()}::{record['Priority']}"
        elif template_type == "CONTACTS": key = f"{record['ClientCode'].casefold()}::{record['Email'].casefold() or record['FullName'].casefold()}"
        elif template_type == "USERS": key = record["Username"].casefold()
        elif template_type == "USER_PROFILES": key = f"{record['Username'].casefold()}::{record['ProfileCode'].casefold()}"
        elif template_type == "CONTRACTS": key = record["ContractNumber"].casefold()
        elif template_type == "CONTRACT_COVERAGE": key = "::".join(record[x].casefold() for x in ("ContractNumber","ProductCode","ModuleCode","ServiceCode","TicketTypeCode","EnvironmentCode","EffectiveFrom","EffectiveUntil","ClientCodes","ExcludedClientCodes"))
        elif template_type == "SHIFTS": key = f"{record['Username'].casefold()}::{record['StartsAt']}"
        elif template_type in {"TICKETS", "ITOP_TICKETS"}: key = record["LegacyTicketNumber"].casefold() or f"{record.get('ClientCode', '')}::{row_number}"
        else: key = record["ProjectNumber"].casefold()
        if key in seen:
            errors.append((None, "DUPLICATE_IN_WORKBOOK", "The record is duplicated in this workbook."))
        seen.add(key)
        if template_type == "ITOP_TICKETS":
            if record["LegacyTicketNumber"] and record["LegacyTicketNumber"] in existing_ticket_numbers:
                errors.append(("Ref", "DUPLICATE_EXISTING", "This ITOP ticket reference already exists."))
            try:
                for field in ("CreatedAt", "AssignedAt", "ResolvedAt", "ClosedAt", "UpdatedAt"):
                    if record.get(field):
                        _datetime(record[field])
            except ValueError as exc:
                errors.append((None, "VALUE_INVALID", str(exc)))
        elif template_type == "MASTER_DATA":
            supported = {"COUNTRY", "CITY", "DEPARTMENT", "PRODUCT", "PRODUCT_MODULE", "SERVICE", "VENDOR", "CLIENT_STATUS", "TICKET_STATUS", "TICKET_TYPE", "ENVIRONMENT", "TICKET_CATEGORY", "TICKET_SUBCATEGORY", "ROOT_CAUSE", "SKILL", "SUPPORT_TEAM"}
            kind = record["DataType"].upper()
            if kind not in supported:
                errors.append(("DataType", "VALUE_INVALID", "Use a DataType listed in Reference Values."))
            if kind in {"CITY", "PRODUCT_MODULE", "TICKET_SUBCATEGORY"} and not record["ParentCode"]:
                errors.append(("ParentCode", "REQUIRED", f"ParentCode is required for {kind}."))
            if kind == "COUNTRY" and (len(record["Alpha2"]) != 2 or len(record["Alpha3"]) != 3):
                errors.append(("Alpha2", "VALUE_INVALID", "COUNTRY requires two-letter Alpha2 and three-letter Alpha3 codes."))
            model_by_kind: dict[str, type[Any]] = {"DEPARTMENT": Department, "PRODUCT": Product, "SERVICE": ServiceCatalogItem, "VENDOR": Vendor, "CLIENT_STATUS": ClientStatus, "TICKET_STATUS": TicketStatus, "TICKET_TYPE": TicketType, "ENVIRONMENT": Environment, "TICKET_CATEGORY": TicketCategory, "ROOT_CAUSE": RootCause, "SKILL": SupportSkill, "SUPPORT_TEAM": SupportTeam}
            model = model_by_kind.get(kind)
            if model and record["Code"] and db.scalar(select(model).where(model.code == record["Code"])):
                errors.append(("Code", "DUPLICATE_EXISTING", f"{kind} code already exists."))
            if kind == "COUNTRY" and db.scalar(select(Country.id).where(Country.iso_alpha3 == record["Alpha3"])):
                errors.append(("Alpha3", "DUPLICATE_EXISTING", "Country already exists."))
            if kind == "CITY":
                parent_country = db.scalar(select(Country).where(Country.iso_alpha3 == record["ParentCode"]))
                if not parent_country and ("COUNTRY", record["ParentCode"].upper()) not in planned_master_codes: errors.append(("ParentCode", "REFERENCE_INVALID", "Country Alpha3 does not exist."))
            if kind == "PRODUCT_MODULE":
                parent_product = db.scalar(select(Product).where(Product.code == record["ParentCode"]))
                if not parent_product and ("PRODUCT", record["ParentCode"].upper()) not in planned_master_codes: errors.append(("ParentCode", "REFERENCE_INVALID", "Product code does not exist."))
            if kind == "TICKET_SUBCATEGORY":
                parent_category = db.scalar(select(TicketCategory).where(TicketCategory.code == record["ParentCode"]))
                if not parent_category and ("TICKET_CATEGORY", record["ParentCode"].upper()) not in planned_master_codes: errors.append(("ParentCode", "REFERENCE_INVALID", "Ticket category code does not exist."))
        elif template_type == "CLIENTS":
            if record["StatusCode"] and not db.scalar(select(ClientStatus.id).where(ClientStatus.code == record["StatusCode"])):
                errors.append(("StatusCode", "REFERENCE_INVALID", "StatusCode does not exist."))
            if record["ClientCode"] and db.scalar(select(Client.id).where(Client.code == record["ClientCode"])):
                errors.append(("ClientCode", "DUPLICATE_EXISTING", "ClientCode already exists."))
            country = db.scalar(select(Country).where(Country.iso_alpha3 == record["CountryCode"])) if record["CountryCode"] else None
            if record["CountryCode"] and not country:
                errors.append(("CountryCode", "REFERENCE_INVALID", "CountryCode does not exist."))
            city = db.scalar(select(City).where(City.country_id == country.id, City.code == record["CityCode"])) if country and record["CityCode"] else None
            if record["CityCode"] and not record["CountryCode"]:
                errors.append(("CityCode", "COUNTRY_REQUIRED", "CountryCode is required when CityCode is supplied."))
            elif record["CityCode"] and not city:
                errors.append(("CityCode", "REFERENCE_INVALID", "CityCode does not exist in the selected country."))
            location_fields = ("PrimaryLocationCode", "PrimaryLocationName", "LocationZone", "Latitude", "Longitude")
            if any(record[field] for field in location_fields) and not country:
                errors.append(("CountryCode", "COUNTRY_REQUIRED", "CountryCode is required when primary location data is supplied."))
            if any(record[field] for field in location_fields) and not (record["PrimaryLocationCode"] and record["PrimaryLocationName"]):
                errors.append(("PrimaryLocationName", "LOCATION_INCOMPLETE", "PrimaryLocationCode and PrimaryLocationName must be supplied together."))
            try:
                if record["SupportStartedAt"]: _date(record["SupportStartedAt"])
                if record["Latitude"] and not -90 <= float(record["Latitude"]) <= 90: raise ValueError
                if record["Longitude"] and not -180 <= float(record["Longitude"]) <= 180: raise ValueError
            except ValueError:
                errors.append((None, "VALUE_INVALID", "Check SupportStartedAt and latitude/longitude values."))
        elif template_type == "INSTALLATIONS":
            client_row = db.scalar(select(Client).where(Client.code == record["ClientCode"]))
            product_row = db.scalar(select(Product).where(Product.code == record["ProductCode"]))
            environment_row = db.scalar(select(Environment).where(Environment.code == record["EnvironmentCode"]))
            if not client_row: errors.append(("ClientCode", "REFERENCE_INVALID", "ClientCode does not exist."))
            if not product_row: errors.append(("ProductCode", "REFERENCE_INVALID", "ProductCode does not exist."))
            if not environment_row: errors.append(("EnvironmentCode", "REFERENCE_INVALID", "EnvironmentCode does not exist."))
            if record["ModuleCode"] and (not product_row or not db.scalar(select(ProductModule.id).where(ProductModule.product_id == product_row.id, ProductModule.code == record["ModuleCode"]))): errors.append(("ModuleCode", "REFERENCE_INVALID", "ModuleCode does not exist for ProductCode."))
            if record["BranchCode"] and (not client_row or not db.scalar(select(Branch.id).where(Branch.client_id == client_row.id, Branch.code == record["BranchCode"]))): errors.append(("BranchCode", "REFERENCE_INVALID", "BranchCode does not exist for ClientCode."))
        elif template_type == "CLIENT_ACCESS":
            if not db.scalar(select(Client.id).where(Client.code == record["ClientCode"])):
                errors.append(("ClientCode", "REFERENCE_INVALID", "ClientCode does not exist."))
            if record["AccessType"] not in {"SERVER", "VPN", "ANYDESK", "SYSTEM_ADMIN", "OTHER"}:
                errors.append(("AccessType", "REFERENCE_INVALID", "AccessType is not supported."))
            if record["IsActive"].casefold() not in {"", "true", "false", "yes", "no", "1", "0"}:
                errors.append(("IsActive", "VALUE_INVALID", "Use Yes/No or True/False."))
        elif template_type == "BRANCHES":
            client = db.scalar(select(Client).where(Client.code == record["ClientCode"]))
            if not client:
                errors.append(("ClientCode", "REFERENCE_INVALID", "ClientCode does not exist."))
            elif record["BranchCode"] and db.scalar(select(Branch.id).where(Branch.client_id == client.id, Branch.code == record["BranchCode"])):
                errors.append(("BranchCode", "DUPLICATE_EXISTING", "BranchCode already exists for this client."))
        elif template_type == "PRODUCTS_MODULES":
            product = db.scalar(select(Product).where(Product.code == record["ProductCode"]))
            if product and record["ModuleCode"] and db.scalar(
                select(ProductModule.id).where(
                    ProductModule.product_id == product.id,
                    ProductModule.code == record["ModuleCode"],
                )
            ):
                errors.append(
                    ("ModuleCode", "DUPLICATE_EXISTING", "ModuleCode already exists for this product.")
                )
        elif template_type == "SERVICES":
            if db.scalar(select(ServiceCatalogItem.id).where(ServiceCatalogItem.code == record["ServiceCode"])):
                errors.append(("ServiceCode", "DUPLICATE_EXISTING", "ServiceCode already exists."))
        elif template_type == "SLA_POLICIES":
            if not db.scalar(select(BusinessCalendar.id).where(BusinessCalendar.name == record["CalendarName"])):
                errors.append(("CalendarName", "REFERENCE_INVALID", "CalendarName does not exist."))
            if record["ServiceCode"] and not db.scalar(select(ServiceCatalogItem.id).where(ServiceCatalogItem.code == record["ServiceCode"])):
                errors.append(("ServiceCode", "REFERENCE_INVALID", "ServiceCode does not exist."))
            if record["Priority"] not in {"P1", "P2", "P3", "P4"}:
                errors.append(("Priority", "VALUE_INVALID", "Priority must be P1, P2, P3, or P4."))
            try:
                response, resolution = int(record["FirstResponseMinutes"]), int(record["ResolutionMinutes"])
                warning = int(record["WarningPercent"] or "75")
                if response < 1 or resolution < response or not 1 <= warning <= 99:
                    raise ValueError
            except ValueError:
                errors.append((None, "VALUE_INVALID", "SLA durations must be positive, resolution cannot precede response, and warning must be 1-99."))
        else:
            references: list[tuple[str, bool, str]] = []
            if "ClientCode" in record:
                client_exists = record["ClientCode"] in ticket_clients if template_type == "TICKETS" else bool(db.scalar(select(Client.id).where(Client.code == record["ClientCode"])))
                references.append(("ClientCode", client_exists, "ClientCode does not exist."))
            if template_type == "USERS":
                references += [("Username", not bool(db.scalar(select(User.id).where(User.username_normalized == normalize(record["Username"])))), "Username already exists."), ("Email", not bool(db.scalar(select(User.id).where(User.email_normalized == normalize(record["Email"])))), "Email already exists.")]
                if record["UserType"] not in {"EMPLOYEE","CLIENT_PORTAL"}: errors.append(("UserType","VALUE_INVALID","Use EMPLOYEE or CLIENT_PORTAL."))
                if record["UserType"] == "CLIENT_PORTAL" and not record["ClientCode"]:
                    errors.append(("ClientCode", "REQUIRED", "ClientCode is required for client portal users."))
            elif template_type == "USER_PROFILES":
                user = _user(db, record["Username"])
                profile = db.scalar(select(Profile).where(Profile.code == record["ProfileCode"]))
                references += [("Username", bool(user), "Username does not exist."), ("ProfileCode", bool(profile), "ProfileCode does not exist.")]
                if user and profile and db.scalar(select(UserProfile.id).where(UserProfile.user_id == user.id, UserProfile.profile_id == profile.id)):
                    errors.append(("ProfileCode", "DUPLICATE_EXISTING", "This user is already linked to this profile."))
            elif template_type == "CONTRACTS":
                references += [("CalendarName", bool(db.scalar(select(BusinessCalendar.id).where(BusinessCalendar.name == record["CalendarName"]))), "CalendarName does not exist."), ("ContractNumber", not bool(db.scalar(select(Contract.id).where(Contract.contract_number == record["ContractNumber"]))), "ContractNumber already exists.")]
                if record["SlaPolicyCode"] and not db.scalar(select(SlaPolicy.id).where(SlaPolicy.code == record["SlaPolicyCode"], SlaPolicy.contract_id.is_(None))):
                    errors.append(("SlaPolicyCode", "REFERENCE_INVALID", "Central SLA policy does not exist."))
            elif template_type == "CONTRACT_COVERAGE":
                contract = db.scalar(select(Contract).where(Contract.contract_number == record["ContractNumber"]))
                references += [("ContractNumber", bool(contract), "ContractNumber does not exist.")]
                if contract:
                    start=_date(record["EffectiveFrom"]);end=_date(record["EffectiveUntil"])
                    if not start or not end or start<contract.start_date or end>contract.end_date or end<start: errors.append(("EffectiveFrom","DATE_CONFLICT","Coverage dates must be valid and within contract dates."))
                    eligible=set(contract.linked_client_ids)|{contract.client_id}
                    for field in ("ClientCodes","ExcludedClientCodes"):
                        for code in {value.strip() for value in record[field].split(",") if value.strip()}:
                            client=db.scalar(select(Client).where(Client.code==code))
                            if not client or client.id not in eligible: errors.append((field,"CLIENT_SCOPE_INVALID",f"Client {code} is not linked to this contract."))
                if not record["ChangeReason"] or len(record["ChangeReason"])<5: errors.append(("ChangeReason","REQUIRED","A meaningful change reason is required."))
            elif template_type == "SHIFTS":
                references += [("Username", bool(db.scalar(select(User.id).where(User.username_normalized == normalize(record["Username"])))), "Username does not exist."), ("ShiftTypeCode", bool(db.scalar(select(ShiftType.id).where(ShiftType.code == record["ShiftTypeCode"]))), "ShiftTypeCode does not exist.")]
                if (record["WorkLocation"] or "OFFICE") not in {"OFFICE", "WORK_FROM_HOME", "HYBRID"}: errors.append(("WorkLocation", "VALUE_INVALID", "Use OFFICE, WORK_FROM_HOME, or HYBRID."))
            elif template_type == "TICKETS": references += [("CreatedByUsername", normalize(record["CreatedByUsername"]) in ticket_users, "CreatedByUsername does not exist."), ("TicketTypeCode", record["TicketTypeCode"] in ticket_types, "TicketTypeCode does not exist."), ("StatusCode", record["StatusCode"] in ticket_statuses, "StatusCode does not exist.")]
            elif template_type == "PROJECT_HANDOVERS": references += [("DeliveredByUsername", bool(db.scalar(select(User.id).where(User.username_normalized == normalize(record["DeliveredByUsername"])))), "DeliveredByUsername does not exist."), ("ProjectNumber", not bool(db.scalar(select(ProjectHandover.id).where(ProjectHandover.project_number == record["ProjectNumber"]))), "ProjectNumber already exists.")]
            if template_type in {"CONTRACT_COVERAGE", "TICKETS"}:
                for field, model in (("ProductCode", Product), ("ServiceCode", ServiceCatalogItem), ("EnvironmentCode", Environment)):
                    if template_type == "TICKETS":
                        exists = (
                            record[field] in ticket_products
                            if field == "ProductCode"
                            else record[field] in ticket_services
                            if field == "ServiceCode"
                            else record[field] in ticket_environments
                        )
                    else:
                        exists = bool(db.scalar(select(model.id).where(model.code == record[field])))
                    if record.get(field) and not exists:
                        errors.append((field, "REFERENCE_INVALID", f"{field} does not exist."))
                if record.get("ModuleCode"):
                    product = ticket_products.get(record.get("ProductCode", "")) if template_type == "TICKETS" else db.scalar(select(Product).where(Product.code == record.get("ProductCode")))
                    module_exists = bool(product and ((product.id, record["ModuleCode"]) in ticket_modules if template_type == "TICKETS" else db.scalar(select(ProductModule.id).where(ProductModule.product_id == product.id, ProductModule.code == record["ModuleCode"]))))
                    if not module_exists:
                        errors.append(("ModuleCode", "REFERENCE_INVALID", "ModuleCode does not exist for ProductCode."))
                if template_type == "CONTRACT_COVERAGE" and record["TicketTypeCode"] and not db.scalar(select(TicketType.id).where(TicketType.code == record["TicketTypeCode"])):
                    errors.append(("TicketTypeCode", "REFERENCE_INVALID", "TicketTypeCode does not exist."))
            if template_type == "PROJECT_HANDOVERS":
                usernames = [record.get("ProjectManagerUsername", ""), *record.get("RecipientUsernames", "").split(",")]
                for username in {item.strip() for item in usernames if item.strip()}:
                    if not _user(db, username):
                        errors.append(("RecipientUsernames", "REFERENCE_INVALID", f"User {username} does not exist."))
            if template_type == "TICKETS":
                for field in ("AssignedUsername", "EscalationUsername"):
                    if record[field] and normalize(record[field]) not in ticket_users:
                        errors.append((field, "REFERENCE_INVALID", f"{field} does not exist."))
                if record["ContractNumber"] and record["ContractNumber"] not in ticket_contracts:
                    errors.append(("ContractNumber", "REFERENCE_INVALID", "ContractNumber does not exist."))
                for field, allowed in (("Priority", {"P1", "P2", "P3", "P4"}), ("Impact", {"LOW", "MEDIUM", "HIGH", "CRITICAL"}), ("Urgency", {"LOW", "MEDIUM", "HIGH", "CRITICAL"})):
                    if record[field] and record[field] not in allowed:
                        errors.append((field, "VALUE_INVALID", f"Unsupported {field}."))
                if record["LegacyTicketNumber"] and record["LegacyTicketNumber"] in existing_ticket_numbers:
                    errors.append(("LegacyTicketNumber", "DUPLICATE_EXISTING", "Ticket number already exists."))
            try:
                if template_type == "CONTRACTS":
                    start, end = _date(record["StartDate"]), _date(record["EndDate"])
                    if start and end and end < start:
                        raise ValueError("EndDate must be on or after StartDate.")
                    if record["IncludedRequestLimit"]:
                        int(record["IncludedRequestLimit"])
                elif template_type == "SHIFTS":
                    if _datetime(record["EndsAt"]) <= _datetime(record["StartsAt"]):
                        raise ValueError("EndsAt must be after StartsAt.")
                elif template_type == "TICKETS":
                    for field in ("CreatedAt", "ResolvedAt", "ClosedAt"):
                        if record[field]:
                            _datetime(record[field])
                elif template_type == "PROJECT_HANDOVERS":
                    _date(record["WarrantyStartDate"]); _date(record["AcceptanceDate"])
                    if record["WarrantyMonths"]:
                        int(record["WarrantyMonths"])
            except ValueError as exc:
                errors.append((None, "VALUE_INVALID", str(exc)))
            for field, valid, message in references:
                if record.get(field) and not valid: errors.append((field,"REFERENCE_INVALID",message))
        db.add(ImportRow(import_job_id=job.id, row_number=row_number, normalized_json=json.dumps(record), is_valid=not errors))
        for column, code, message in errors:
            db.add(ImportError(import_job_id=job.id, row_number=row_number, column_name=column, error_code=code, message=message))
        job.total_rows += 1
        if errors:
            job.invalid_rows += 1
        else:
            job.valid_rows += 1
    job.status = "VALIDATION_FAILED" if job.invalid_rows else "READY_FOR_CONFIRMATION"
    db.commit()
    db.refresh(job)
    return job


def _unique_code(db: Session, model: type[Any], raw: str, prefix: str, max_length: int = 50) -> str:
    base = re.sub(r"[^A-Z0-9]+", "-", raw.upper()).strip("-") or prefix
    base = base[:max_length]
    candidate, suffix = base, 2
    while db.scalar(select(model).where(model.code == candidate)):
        tail = f"-{suffix}"
        candidate = f"{base[:max_length-len(tail)]}{tail}"
        suffix += 1
    return candidate


def _commit_itop_ticket(
    db: Session,
    data: dict[str, Any],
    actor: User,
    *,
    create_missing_clients: bool,
    create_missing_engineers: bool,
    create_missing_callers: bool,
) -> bool:
    client = db.scalar(select(Client).where(Client.code == data.get("ClientCode"))) if data.get("ClientCode") else _unique_normalized_match(db.scalars(select(Client)), data.get("_ClientName", ""), "name")
    if not client and create_missing_clients:
        active_status = db.scalar(select(ClientStatus).where(ClientStatus.code == "ACTIVE")) or db.scalar(select(ClientStatus).order_by(ClientStatus.id))
        if not active_status:
            raise ConflictError("IMPORT_CLIENT_STATUS_MISSING", "No client status is available for new ITOP clients.")
        client = Client(
            code=_unique_code(db, Client, data.get("_ClientLegacyCode") or data.get("_ClientName", ""), "ITOP-CLIENT"),
            name=data["_ClientName"], status_id=active_status.id, timezone="Africa/Cairo", is_active=True,
            notes="Created during confirmed ITOP ticket migration.",
        )
        db.add(client); db.flush()
    if not client:
        return False

    engineer = _user(db, data.get("AssignedUsername", "")) if data.get("AssignedUsername") else None
    if not engineer and data.get("_EngineerEmail"):
        engineer = db.scalar(select(User).where(User.email_normalized == normalize(data["_EngineerEmail"])))
    if not engineer and create_missing_engineers and data.get("_EngineerName"):
        email = data.get("_EngineerEmail") or f"itop-{secrets.token_hex(6)}@invalid.local"
        username_base = normalize(email.split("@", 1)[0]) or re.sub(r"[^a-z0-9]+", ".", normalize(data["_EngineerName"])).strip(".") or "itop.user"
        username, username_suffix = username_base[:140], 2
        while _user(db, username):
            username = f"{username_base[:135]}.{username_suffix}"
            username_suffix += 1
        engineer = User(
            full_name=data["_EngineerName"], username=username, username_normalized=normalize(username),
            email=email, email_normalized=normalize(email), employee_code=data.get("_EngineerEmployeeCode") or None,
            user_type="EMPLOYEE", password_hash=hash_password(secrets.token_urlsafe(32)), is_active=False,
            require_password_change=True,
        )
        db.add(engineer); db.flush()

    contact = db.get(Contact, int(data["_RequesterContactId"])) if data.get("_RequesterContactId") else None
    if not contact and create_missing_callers and data.get("_CallerName"):
        contact = Contact(
            client_id=client.id, full_name=data["_CallerName"], email=data.get("_CallerEmail") or None,
            contact_role="ITOP caller", is_active=True,
        )
        db.add(contact); db.flush()

    ticket_type = db.scalar(select(TicketType).where(TicketType.code == data.get("TicketTypeCode"))) or db.scalar(select(TicketType).where(TicketType.code == "INCIDENT"))
    status = db.scalar(select(TicketStatus).where(TicketStatus.code == data["StatusCode"])) or db.scalar(select(TicketStatus).where(TicketStatus.code == "ASSIGNED"))
    if not ticket_type or not status:
        raise ConflictError("IMPORT_TICKET_CATALOG_MISSING", "Required ticket type or status is unavailable.")
    created_at = _datetime(data["CreatedAt"]) if data.get("CreatedAt") else server_now()
    assigned_at = _datetime(data["AssignedAt"]) if data.get("AssignedAt") else None
    resolved_at = _datetime(data["ResolvedAt"]) if data.get("ResolvedAt") else None
    closed_at = _datetime(data["ClosedAt"]) if data.get("ClosedAt") else None
    updated_at = _datetime(data["UpdatedAt"]) if data.get("UpdatedAt") else resolved_at or assigned_at or created_at
    ticket = Ticket(
        ticket_number=data.get("LegacyTicketNumber") or None, ticket_type_id=ticket_type.id, client_id=client.id,
        requester_contact_id=contact.id if contact else None, created_by_user_id=actor.id, status_id=status.id,
        assigned_user_id=engineer.id if engineer else None, assigned_team=data.get("AssignedTeam") or None,
        source_channel="ITOP_IMPORT", priority=data["Priority"], impact=data["Impact"], urgency=data["Urgency"],
        subject=data["Subject"][:300], description=data["Description"][:20000], product_id=None,
        resolution_summary=data.get("ResolutionSummary") or None, first_occurred_at=created_at,
        progress_started_at=assigned_at, resolved_at=resolved_at, closed_at=closed_at,
        created_at=created_at, updated_at=updated_at, last_activity_at=updated_at,
    )
    db.add(ticket); db.flush()
    if engineer and assigned_at:
        db.add(TicketAssignmentHistory(ticket_id=ticket.id, assigned_user_id=engineer.id, assigned_team=ticket.assigned_team, assigned_by_user_id=actor.id, reason="Imported ITOP assignment", created_at=assigned_at))
    db.add(TicketStatusHistory(ticket_id=ticket.id, from_status_id=None, to_status_id=status.id, changed_by_user_id=actor.id, reason="Imported ITOP status", source="IMPORT", created_at=resolved_at or closed_at or updated_at))
    for internal, body, log_suffix in ((False, data.get("PublicLog"), "public"), (True, data.get("PrivateLog"), "private")):
        if body:
            db.add(TicketComment(ticket_id=ticket.id, author_user_id=actor.id, is_internal=internal, body=body[:20000], operation_key=f"itop:{data.get('LegacyTicketNumber')}:{log_suffix}", created_at=updated_at))
    return True


def commit_import(
    db: Session,
    job: ImportJob,
    reason: str,
    *,
    create_missing_clients: bool = False,
    create_missing_engineers: bool = False,
    create_missing_callers: bool = False,
) -> ImportJob:
    if job.status not in {"READY_FOR_CONFIRMATION", "IMPORTING"}:
        raise ConflictError("IMPORT_NOT_READY", "Only a fully valid import can be confirmed.")
    rows = list(db.scalars(select(ImportRow).where(ImportRow.import_job_id == job.id, ImportRow.is_valid.in_([True])).order_by(ImportRow.row_number)))
    clients_by_code = {item.code: item for item in db.scalars(select(Client))} if job.template_type == "TICKETS" else {}
    users_by_username = {item.username_normalized: item for item in db.scalars(select(User))} if job.template_type == "TICKETS" else {}
    types_by_code = {item.code: item for item in db.scalars(select(TicketType))} if job.template_type == "TICKETS" else {}
    statuses_by_code = {item.code: item for item in db.scalars(select(TicketStatus))} if job.template_type == "TICKETS" else {}
    contracts_by_number = {item.contract_number: item for item in db.scalars(select(Contract))} if job.template_type == "TICKETS" else {}
    products_by_code = {item.code: item for item in db.scalars(select(Product))} if job.template_type == "TICKETS" else {}
    modules_by_key = {(item.product_id, item.code): item for item in db.scalars(select(ProductModule))} if job.template_type == "TICKETS" else {}
    environments_by_code = {item.code: item for item in db.scalars(select(Environment))} if job.template_type == "TICKETS" else {}
    services_by_code = {item.code: item for item in db.scalars(select(ServiceCatalogItem))} if job.template_type == "TICKETS" else {}
    inserted_rows = 0
    try:
        for row in rows:
            data: dict[str, Any] = json.loads(row.normalized_json)
            if job.template_type == "ITOP_TICKETS":
                actor = db.get(User, job.uploaded_by_user_id)
                if not actor:
                    raise ConflictError("IMPORT_USER_MISSING", "The importing user no longer exists.")
                if _commit_itop_ticket(
                    db, data, actor,
                    create_missing_clients=create_missing_clients,
                    create_missing_engineers=create_missing_engineers,
                    create_missing_callers=create_missing_callers,
                ):
                    inserted_rows += 1
            elif job.template_type == "MASTER_DATA":
                kind = data["DataType"].upper(); active = _flag(data["IsActive"]); common = {"code": data["Code"].upper(), "name": data["Name"], "is_active": active}
                if kind == "COUNTRY": db.add(Country(iso_alpha2=data["Alpha2"].upper(), iso_alpha3=data["Alpha3"].upper(), name=data["Name"], default_timezone=data["DefaultTimezone"] or None, is_active=active))
                elif kind == "CITY":
                    parent_country = db.scalar(select(Country).where(Country.iso_alpha3 == data["ParentCode"])); db.add(City(country_id=parent_country.id, code=data["Code"].upper(), name=data["Name"], is_active=active))  # type: ignore[union-attr]
                elif kind == "DEPARTMENT": db.add(Department(**common, description=data["Description"] or None))
                elif kind == "PRODUCT": db.add(Product(**common, description=data["Description"] or None))
                elif kind == "PRODUCT_MODULE":
                    parent_product = db.scalar(select(Product).where(Product.code == data["ParentCode"])); db.add(ProductModule(product_id=parent_product.id, **common))  # type: ignore[union-attr]
                elif kind == "SERVICE": db.add(ServiceCatalogItem(**common, description=data["Description"] or None))
                elif kind == "VENDOR": db.add(Vendor(**common, contact_name=data["ContactName"] or None, email=data["Email"] or None, phone_number=data["Phone"] or None))
                elif kind == "CLIENT_STATUS": db.add(ClientStatus(**common, portal_allowed=_flag(data["PortalAllowed"]), ticket_creation_allowed=_flag(data["TicketCreationAllowed"])))
                elif kind == "TICKET_STATUS": db.add(TicketStatus(code=common["code"], name=common["name"], color=data["Color"] or "#607D8B", is_closed_state=_flag(data["IsClosed"], False), is_sla_pause_state=_flag(data["IsSlaPause"], False), sort_order=int(data["SortOrder"] or 100)))
                elif kind == "TICKET_TYPE": db.add(TicketType(**common, color=data["Color"] or "#607D8B", number_prefix=data["NumberPrefix"] or data["Code"][:8]))
                elif kind == "ENVIRONMENT": db.add(Environment(**common, is_production=_flag(data["IsProduction"], False)))
                elif kind == "TICKET_CATEGORY": db.add(TicketCategory(**common, description=data["Description"] or None))
                elif kind == "TICKET_SUBCATEGORY":
                    parent_category = db.scalar(select(TicketCategory).where(TicketCategory.code == data["ParentCode"])); db.add(TicketSubcategory(category_id=parent_category.id, **common))  # type: ignore[union-attr]
                elif kind == "ROOT_CAUSE": db.add(RootCause(**common, description=data["Description"] or None))
                elif kind == "SKILL": db.add(SupportSkill(**common, description=data["Description"] or None))
                elif kind == "SUPPORT_TEAM": db.add(SupportTeam(**common, description=data["Description"] or None))
            elif job.template_type == "INSTALLATIONS":
                client_row = db.scalar(select(Client).where(Client.code == data["ClientCode"])); product_row = db.scalar(select(Product).where(Product.code == data["ProductCode"])); environment_row = db.scalar(select(Environment).where(Environment.code == data["EnvironmentCode"]))
                branch_id = db.scalar(select(Branch.id).where(Branch.client_id == client_row.id, Branch.code == data["BranchCode"])) if client_row and data["BranchCode"] else None
                module_id = db.scalar(select(ProductModule.id).where(ProductModule.product_id == product_row.id, ProductModule.code == data["ModuleCode"])) if product_row and data["ModuleCode"] else None
                if not client_row or not product_row or not environment_row: raise ConflictError("IMPORT_REFERENCE_CHANGED", "Installation reference data changed after validation; upload again.")
                db.add(ClientInstallation(client_id=client_row.id, branch_id=branch_id, product_id=product_row.id, product_module_id=module_id, environment_id=environment_row.id, installation_name=data["InstallationName"], version=data["Version"] or None, server_name=data["ServerName"] or None, database_name=data["DatabaseName"] or None, support_owner=data["SupportOwner"] or None, is_active=_flag(data["IsActive"])))
            elif job.template_type == "CLIENTS":
                status_id = db.scalar(select(ClientStatus.id).where(ClientStatus.code == data["StatusCode"]))
                if not status_id or db.scalar(select(Client.id).where(Client.code == data["ClientCode"])):
                    raise ConflictError("IMPORT_REFERENCE_CHANGED", "Client data changed after validation; upload again.")
                active = data["IsActive"].casefold() not in {"false", "no", "0"}
                country = db.scalar(select(Country).where(Country.iso_alpha3 == data["CountryCode"])) if data["CountryCode"] else None
                city = db.scalar(select(City).where(City.country_id == country.id, City.code == data["CityCode"])) if country and data["CityCode"] else None
                imported_client = Client(code=data["ClientCode"], name=data["ClientName"], status_id=status_id, timezone=data["TimeZone"] or "Africa/Cairo", phone_number=data["Phone"] or None, email=data["Email"] or None, address=data["Address"] or None, notes=data["Notes"] or None, support_started_at=_date(data["SupportStartedAt"]), country_id=country.id if country else None, city_id=city.id if city else None, country=country.name if country else None, zone=city.name if city else None, is_active=active)
                db.add(imported_client)
                db.flush()
                if country and data["PrimaryLocationCode"] and data["PrimaryLocationName"]:
                    location = ClientLocation(client_id=imported_client.id, country_id=country.id, code=data["PrimaryLocationCode"], name=data["PrimaryLocationName"], zone=data["LocationZone"] or None, address=data["Address"] or None, timezone=data["TimeZone"] or None, latitude=float(data["Latitude"]) if data["Latitude"] else None, longitude=float(data["Longitude"]) if data["Longitude"] else None, is_active=True)
                    db.add(location)
                    db.flush()
                    imported_client.primary_location_id = location.id
            elif job.template_type == "CLIENT_ACCESS":
                client = db.scalar(select(Client).where(Client.code == data["ClientCode"]))
                if not client:
                    raise ConflictError("IMPORT_REFERENCE_CHANGED", "Client data changed after validation; upload again.")
                active = data["IsActive"].casefold() not in {"false", "no", "0"}
                db.add(ClientAccessCredential(client_id=client.id, access_type=data["AccessType"], label=data["Label"], server_or_address=data["ServerOrAddress"] or None, username=data["Username"] or None, notes=data["Notes"] or None, is_active=active, created_by_user_id=job.uploaded_by_user_id, updated_by_user_id=job.uploaded_by_user_id))
            elif job.template_type == "BRANCHES":
                client = db.scalar(select(Client).where(Client.code == data["ClientCode"]))
                if not client or db.scalar(select(Branch.id).where(Branch.client_id == client.id, Branch.code == data["BranchCode"])):
                    raise ConflictError("IMPORT_REFERENCE_CHANGED", "Branch data changed after validation; upload again.")
                db.add(Branch(client_id=client.id, code=data["BranchCode"], name=data["BranchName"], timezone=data["TimeZone"] or None, phone_number=data["Phone"] or None, email=data["Email"] or None, address=data["Address"] or None))
            elif job.template_type == "PRODUCTS_MODULES":
                product = db.scalar(select(Product).where(Product.code == data["ProductCode"]))
                if not product:
                    product = Product(
                        code=data["ProductCode"],
                        name=data["ProductName"],
                        description=data["ProductDescription"] or None,
                        is_active=True,
                    )
                    db.add(product)
                    db.flush()
                if db.scalar(
                    select(ProductModule.id).where(
                        ProductModule.product_id == product.id,
                        ProductModule.code == data["ModuleCode"],
                    )
                ):
                    raise ConflictError(
                        "IMPORT_REFERENCE_CHANGED",
                        "Product module data changed after validation; upload again.",
                    )
                db.add(
                    ProductModule(
                        product_id=product.id,
                        code=data["ModuleCode"],
                        name=data["ModuleName"],
                        is_active=True,
                    )
                )
            elif job.template_type == "SERVICES":
                if db.scalar(select(ServiceCatalogItem.id).where(ServiceCatalogItem.code == data["ServiceCode"])):
                    raise ConflictError("IMPORT_REFERENCE_CHANGED", "Service data changed after validation; upload again.")
                db.add(ServiceCatalogItem(code=data["ServiceCode"], name=data["ServiceName"], description=data["Description"] or None, is_active=_flag(data["IsActive"])))
            elif job.template_type == "SLA_POLICIES":
                calendar = db.scalar(select(BusinessCalendar).where(BusinessCalendar.name == data["CalendarName"]))
                service = db.scalar(select(ServiceCatalogItem).where(ServiceCatalogItem.code == data["ServiceCode"])) if data["ServiceCode"] else None
                if not calendar:
                    raise ConflictError("IMPORT_REFERENCE_CHANGED", "SLA calendar changed after validation; upload again.")
                policy = db.scalar(select(SlaPolicy).where(SlaPolicy.code == data["PolicyCode"], SlaPolicy.contract_id.is_(None)))
                if not policy:
                    policy = SlaPolicy(code=data["PolicyCode"], name=data["PolicyName"], calendar_id=calendar.id, contract_id=None, is_active=_flag(data["IsActive"])); db.add(policy); db.flush()
                target = db.scalar(select(SlaTarget).where(SlaTarget.policy_id == policy.id, SlaTarget.service_id == (service.id if service else None), SlaTarget.priority == data["Priority"]))
                values = {"first_response_minutes": int(data["FirstResponseMinutes"]), "resolution_minutes": int(data["ResolutionMinutes"]), "warning_percent": int(data["WarningPercent"] or "75")}
                if target:
                    for field, value in values.items(): setattr(target, field, value)
                else:
                    db.add(SlaTarget(policy_id=policy.id, service_id=service.id if service else None, priority=data["Priority"], **values))
            elif job.template_type == "CONTACTS":
                client = db.scalar(select(Client).where(Client.code == data["ClientCode"]))
                if not client:
                    raise ConflictError("IMPORT_REFERENCE_CHANGED", "Client data changed after validation; upload again.")
                db.add(Contact(client_id=client.id, branch_id=None, full_name=data["FullName"], email=data["Email"] or None, phone_number=data["Phone"] or None, job_title=data["JobTitle"] or None, contact_role=data["ContactRole"] or None, is_primary=_flag(data["IsPrimary"], False), is_escalation_contact=_flag(data["IsEscalation"], False), is_active=_flag(data["IsActive"])))
            elif job.template_type == "USERS":
                if _user(db, data["Username"]):
                    raise ConflictError("IMPORT_REFERENCE_CHANGED", "User data changed after validation; upload again.")
                client = db.scalar(select(Client).where(Client.code == data["ClientCode"])) if data["ClientCode"] else None
                new_user = User(full_name=data["FullName"], username=data["Username"], username_normalized=normalize(data["Username"]), email=data["Email"], email_normalized=normalize(data["Email"]), employee_code=data["EmployeeCode"] or None, phone_number=data["Phone"] or None, department=data["Department"] or None, job_title=data["JobTitle"] or None, user_type=data["UserType"], password_hash=hash_password(secrets.token_urlsafe(32)), is_active=_flag(data["IsActive"]), require_password_change=True)
                db.add(new_user)
                db.flush()
                if client:
                    db.add(UserClientScope(user_id=new_user.id, client_id=client.id))
            elif job.template_type == "USER_PROFILES":
                profile_user, profile = _user(db, data["Username"]), db.scalar(select(Profile).where(Profile.code == data["ProfileCode"]))
                if not profile_user or not profile:
                    raise ConflictError("IMPORT_REFERENCE_CHANGED", "User or profile changed after validation; upload again.")
                db.add(UserProfile(user_id=profile_user.id, profile_id=profile.id, is_primary=_flag(data["IsPrimary"], False), assigned_by_user_id=job.uploaded_by_user_id, assignment_reason=data["AssignmentReason"] or reason))
            elif job.template_type == "CONTRACTS":
                client = db.scalar(select(Client).where(Client.code == data["ClientCode"]))
                calendar = db.scalar(select(BusinessCalendar).where(BusinessCalendar.name == data["CalendarName"]))
                if not client or not calendar:
                    raise ConflictError("IMPORT_REFERENCE_CHANGED", "Contract references changed after validation; upload again.")
                policy = db.scalar(select(SlaPolicy).where(SlaPolicy.code == data["SlaPolicyCode"], SlaPolicy.contract_id.is_(None))) if data["SlaPolicyCode"] else None
                db.add(Contract(contract_number=data["ContractNumber"], client_id=client.id, name=data["Name"], status=data["Status"] or "ACTIVE", start_date=_date(data["StartDate"]), end_date=_date(data["EndDate"]), timezone=data["TimeZone"] or "Africa/Cairo", calendar_id=calendar.id, sla_policy_id=policy.id if policy else None, included_request_limit=int(data["IncludedRequestLimit"]) if data["IncludedRequestLimit"] else None, support_summary=data["SupportSummary"] or None, exclusions=data["Exclusions"] or None, is_active=_flag(data["IsActive"])))
            elif job.template_type == "CONTRACT_COVERAGE":
                contract = db.scalar(select(Contract).where(Contract.contract_number == data["ContractNumber"]))
                product = db.scalar(select(Product).where(Product.code == data["ProductCode"])) if data["ProductCode"] else None
                module = db.scalar(select(ProductModule).where(ProductModule.product_id == product.id, ProductModule.code == data["ModuleCode"])) if product and data["ModuleCode"] else None
                service = db.scalar(select(ServiceCatalogItem).where(ServiceCatalogItem.code == data["ServiceCode"])) if data["ServiceCode"] else None
                ticket_type = db.scalar(select(TicketType).where(TicketType.code == data["TicketTypeCode"])) if data["TicketTypeCode"] else None
                environment = db.scalar(select(Environment).where(Environment.code == data["EnvironmentCode"])) if data["EnvironmentCode"] else None
                if not contract:
                    raise ConflictError("IMPORT_REFERENCE_CHANGED", "Contract changed after validation; upload again.")
                eligible_codes={client.code:client.id for client in db.scalars(select(Client).where(Client.id.in_(set(contract.linked_client_ids)|{contract.client_id})))}
                explicit={value.strip() for value in data["ClientCodes"].split(",") if value.strip()};excluded={value.strip() for value in data["ExcludedClientCodes"].split(",") if value.strip()}
                applies_all=_flag(data["AppliesToAllClients"],False)
                selected=((set(eligible_codes)-excluded) if excluded else set()) if applies_all else (explicit-excluded)
                if not selected.issubset(eligible_codes): raise ConflictError("IMPORT_REFERENCE_CHANGED","Coverage client scope changed after validation; upload again.")
                coverage=ContractCoverage(contract_id=contract.id,product_id=product.id if product else None,product_module_id=module.id if module else None,branch_id=None,environment_id=environment.id if environment else None,service_id=service.id if service else None,ticket_type_id=ticket_type.id if ticket_type else None,is_covered=_flag(data["IsCovered"]),notes=data["Notes"] or None,effective_from=_date(data["EffectiveFrom"]),effective_until=_date(data["EffectiveUntil"]),current_revision=1)
                db.add(coverage);db.flush();client_ids=sorted(eligible_codes[code] for code in selected)
                for client_id in client_ids: db.add(ContractCoverageClient(coverage_id=coverage.id,client_id=client_id))
                db.add(ContractCoverageRevision(coverage_id=coverage.id,revision=1,effective_from=coverage.effective_from,effective_until=coverage.effective_until,is_covered=coverage.is_covered,notes=coverage.notes,client_ids_json=json.dumps(client_ids),change_reason=data["ChangeReason"],created_by_user_id=job.uploaded_by_user_id))
            elif job.template_type == "SHIFTS":
                user, shift_type = _user(db, data["Username"]), db.scalar(select(ShiftType).where(ShiftType.code == data["ShiftTypeCode"]))
                if not user or not shift_type:
                    raise ConflictError("IMPORT_REFERENCE_CHANGED", "Shift references changed after validation; upload again.")
                db.add(Shift(user_id=user.id, shift_type_id=shift_type.id, starts_at=_datetime(data["StartsAt"]), ends_at=_datetime(data["EndsAt"]), work_location=data["WorkLocation"] or "OFFICE", team=data["Team"] or None, on_call_role=data["OnCallRole"] or None, notes=data["Notes"] or None, created_by_user_id=job.uploaded_by_user_id))
            elif job.template_type == "TICKETS":
                client = clients_by_code.get(data["ClientCode"]); creator = users_by_username.get(normalize(data["CreatedByUsername"]))
                ticket_type = types_by_code.get(data["TicketTypeCode"]); status = statuses_by_code.get(data["StatusCode"])
                assigned = users_by_username.get(normalize(data["AssignedUsername"])) if data["AssignedUsername"] else None
                escalation = users_by_username.get(normalize(data["EscalationUsername"])) if data["EscalationUsername"] else None
                contract = contracts_by_number.get(data["ContractNumber"]) if data["ContractNumber"] else None
                product = products_by_code.get(data["ProductCode"]) if data["ProductCode"] else None
                module = modules_by_key.get((product.id, data["ModuleCode"])) if product and data["ModuleCode"] else None
                environment = environments_by_code.get(data["EnvironmentCode"]) if data["EnvironmentCode"] else None
                service = services_by_code.get(data["ServiceCode"]) if data["ServiceCode"] else None
                if not all((client, creator, ticket_type, status)):
                    raise ConflictError("IMPORT_REFERENCE_CHANGED", "Ticket references changed after validation; upload again.")
                assert client is not None and creator is not None and ticket_type is not None and status is not None
                created = _datetime(data["CreatedAt"]) if data["CreatedAt"] else server_now()
                db.add(Ticket(ticket_number=data["LegacyTicketNumber"] or f"MIG-{job.id:06d}-{row.row_number:06d}", ticket_type_id=ticket_type.id, client_id=client.id, requester_contact_id=int(data["_RequesterContactId"]) if data.get("_RequesterContactId") else None, created_by_user_id=creator.id, status_id=status.id, assigned_user_id=assigned.id if assigned else None, assigned_team=data["AssignedTeam"] or None, escalation_assignee_user_id=escalation.id if escalation else None, contract_id=contract.id if contract else None, product_id=product.id if product else None, product_module_id=module.id if module else None, environment_id=environment.id if environment else None, service_id=service.id if service else None, source_channel=data["Source"] or "WEB", priority=data["Priority"] or "P3", impact=data["Impact"] or "MEDIUM", urgency=data["Urgency"] or "MEDIUM", subject=data["Subject"], description=data["Description"], resolution_summary=data["ResolutionSummary"] or None, created_at=created, resolved_at=_datetime(data["ResolvedAt"]) if data["ResolvedAt"] else None, closed_at=_datetime(data["ClosedAt"]) if data["ClosedAt"] else None, last_activity_at=created))
            elif job.template_type == "PROJECT_HANDOVERS":
                client = db.scalar(select(Client).where(Client.code == data["ClientCode"])); delivered_by = _user(db, data["DeliveredByUsername"])
                manager = _user(db, data["ProjectManagerUsername"]) if data["ProjectManagerUsername"] else None
                if not client or not delivered_by:
                    raise ConflictError("IMPORT_REFERENCE_CHANGED", "Handover references changed after validation; upload again.")
                handover = ProjectHandover(project_number=data["ProjectNumber"], project_name=data["ProjectName"], client_id=client.id, delivered_by_user_id=delivered_by.id, project_manager_user_id=manager.id if manager else None, warranty_months=int(data["WarrantyMonths"]) if data["WarrantyMonths"] else None, warranty_start_date=_date(data["WarrantyStartDate"]), acceptance_date=_date(data["AcceptanceDate"]), current_status=data["CurrentStatus"] or "DRAFT", pending_points=data["PendingPoints"] or None, notes=data["Notes"] or None)
                db.add(handover); db.flush()
                for username in {x.strip() for x in data["RecipientUsernames"].split(",") if x.strip()}:
                    recipient = _user(db, username)
                    if not recipient:
                        raise ConflictError("IMPORT_REFERENCE_CHANGED", f"Handover recipient {username} no longer exists.")
                    db.add(HandoverRecipient(handover_id=handover.id, user_id=recipient.id))
            else:
                raise ConflictError("IMPORT_TYPE_INVALID", "Import template is not supported.")
        job.status = "COMPLETED"
        job.inserted_rows = inserted_rows if job.template_type == "ITOP_TICKETS" else len(rows)
        job.confirmation_reason = reason
        job.completed_at = server_now()
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(job)
    return job
