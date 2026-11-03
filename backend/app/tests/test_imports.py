import io

from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.modules.clients.models import City, Client, ClientLocation, ClientStatus, Contact, Country
from app.modules.contracts.models import BusinessCalendar
from app.modules.iam.models import User
from app.modules.imports.service import EXTERNAL_USER_REQUEST_HEADERS, template_bytes
from app.modules.tickets.models import Ticket, TicketAssignmentHistory, TicketComment


def workbook_with_row(values: list[str], template_type: str = "CLIENTS") -> bytes:
    book = load_workbook(io.BytesIO(template_bytes(template_type)))
    book["Data"].append(values)
    output = io.BytesIO()
    book.save(output)
    return output.getvalue()


def external_user_request_workbook(values: list[object]) -> bytes:
    book = Workbook()
    sheet = book.active
    sheet.title = "Sheet1"
    sheet.append(EXTERNAL_USER_REQUEST_HEADERS)
    sheet.append(values)
    output = io.BytesIO()
    book.save(output)
    return output.getvalue()


def itop_workbook(values: list[object]) -> bytes:
    headers = [
        "Ref", "Title", "Organization->Name", "Organization->Code", "Caller->Full name",
        "Caller->Email", "Agent->Full name", "Agent->Email", "Agent->Employee number",
        "Start date", "Assignment date", "Resolution date", "Close date", "Last update",
        "Status", "Priority", "Impact", "Urgency", "Description", "Solution", "Public log",
        "Private log", "Team->Name", "id (Primary Key)",
    ]
    book = Workbook(); sheet = book.active; sheet.append(headers); sheet.append(values)
    output = io.BytesIO(); book.save(output); return output.getvalue()


def test_native_itop_import_previews_and_creates_confirmed_relationships(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    content = itop_workbook([
        "R-099001", "Imported ITOP request", "New ITOP Client", "N-991", "New Caller",
        "caller@example.com", "New Engineer", "engineer@example.com", "E991",
        "2026-10-01 08:00:00", "2026-10-01 08:15:00", "2026-10-01 10:00:00", "",
        "2026-10-01 10:05:00", "Resolved", "High", "High", "Medium",
        "The imported request description.", "The imported resolution.", "Caller updated.",
        "Internal diagnostic.", "Support Team", "99001",
    ])
    staged = client.post(
        "/api/v1/imports/ITOP_TICKETS/upload", headers=admin_headers,
        files={"workbook": ("itop.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert staged.status_code == 201, staged.text
    assert staged.json()["status"] == "READY_FOR_CONFIRMATION"
    preview = client.get(f"/api/v1/imports/{staged.json()['id']}/itop-preview", headers=admin_headers)
    assert preview.status_code == 200, preview.text
    assert preview.json()["missing_clients"] == ["New ITOP Client"]
    assert preview.json()["missing_engineers"] == ["New Engineer"]
    assert preview.json()["missing_callers"] == ["New Caller · New ITOP Client"]

    confirmed = client.post(
        f"/api/v1/imports/{staged.json()['id']}/confirm", headers=admin_headers,
        json={"reason": "Approved native ITOP migration", "create_missing_clients": True,
              "create_missing_engineers": True, "create_missing_callers": True},
    )
    assert confirmed.status_code == 200, confirmed.text
    ticket = database.scalar(select(Ticket).where(Ticket.ticket_number == "R-099001"))
    assert ticket is not None and ticket.product_id is None
    assert ticket.requester_contact_id is not None and ticket.assigned_user_id is not None
    assert ticket.resolution_summary == "The imported resolution."
    assert database.scalar(select(TicketAssignmentHistory).where(TicketAssignmentHistory.ticket_id == ticket.id)) is not None
    assert len(list(database.scalars(select(TicketComment).where(TicketComment.ticket_id == ticket.id)))) == 2


def test_external_user_request_import_matches_organization_to_client_name(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status = database.scalar(select(ClientStatus).where(ClientStatus.code == "ACTIVE"))
    admin = database.scalar(select(User).order_by(User.id))
    assert status is not None and admin is not None
    imported_client = Client(code="ALFA", name="Alfa Scan", status_id=status.id, is_active=True)
    database.add(imported_client)
    database.flush()
    caller = Contact(client_id=imported_client.id, full_name="Mohamed Ali", is_active=True)
    database.add(caller)
    database.commit()

    content = external_user_request_workbook([
        "R-024701", "Integration issue", admin.full_name, "Alfa Scan", "Mohamed Ali",
        "2026-08-01 15:39:12", "Low", "2026-08-01 15:39:36", "27394", "Resolved",
        "1156", "agent", "agent", "115", "Support. Team", "24690",
        "2026-08-01 23:15:46",
    ])
    staged = client.post(
        "/api/v1/imports/TICKETS/upload",
        headers=admin_headers,
        files={"workbook": ("user-requests.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert staged.status_code == 201, staged.text
    assert staged.json()["status"] == "READY_FOR_CONFIRMATION", staged.text
    confirmed = client.post(
        f"/api/v1/imports/{staged.json()['id']}/confirm",
        headers=admin_headers,
        json={"reason": "Approved external user request migration"},
    )
    assert confirmed.status_code == 200, confirmed.text
    ticket = database.scalar(select(Ticket).where(Ticket.ticket_number == "R-024701"))
    assert ticket is not None
    assert ticket.client_id == imported_client.id
    assert ticket.requester_contact_id == caller.id
    assert ticket.assigned_user_id == admin.id
    assert ticket.priority == "P4"
    assert ticket.status.code == "RESOLVED"


def test_large_ticket_validation_preloads_references_instead_of_querying_per_row(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status = database.scalar(select(ClientStatus).where(ClientStatus.code == "ACTIVE"))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert status is not None and admin is not None
    imported_client = Client(code="LOADCLIENT", name="Load Test Client", status_id=status.id, is_active=True)
    database.add(imported_client)
    database.commit()
    book = load_workbook(io.BytesIO(template_bytes("TICKETS", database)))
    for number in range(500):
        book["Data"].append([
            f"LOAD-{number:05d}", "SERVICE_REQUEST", imported_client.code, "NEW", admin.username,
            "", "", "", "", "", "", "", "", "P3", "MEDIUM", "MEDIUM",
            f"Load validation ticket {number}", "Bulk migration validation", "OTHER",
            "2026-08-01 10:00:00", "", "", "",
        ])
    output = io.BytesIO()
    book.save(output)
    select_count = 0

    def count_selects(
        _connection: object, _cursor: object, statement: str, _parameters: object,
        _context: object, _executemany: bool,
    ) -> None:
        nonlocal select_count
        if statement.lstrip().upper().startswith("SELECT"):
            select_count += 1

    event.listen(database.get_bind(), "before_cursor_execute", count_selects)
    try:
        staged = client.post(
            "/api/v1/imports/TICKETS/upload",
            headers=admin_headers,
            files={"workbook": ("bulk-tickets.xlsx", output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    finally:
        event.remove(database.get_bind(), "before_cursor_execute", count_selects)
    assert staged.status_code == 201, staged.text
    assert staged.json()["valid_rows"] == 500
    assert select_count < 40
    confirm_select_count = 0

    def count_confirm_selects(
        _connection: object, _cursor: object, statement: str, _parameters: object,
        _context: object, _executemany: bool,
    ) -> None:
        nonlocal confirm_select_count
        if statement.lstrip().upper().startswith("SELECT"):
            confirm_select_count += 1

    event.listen(database.get_bind(), "before_cursor_execute", count_confirm_selects)
    try:
        confirmed = client.post(
            f"/api/v1/imports/{staged.json()['id']}/confirm",
            headers=admin_headers,
            json={"reason": "Approved bulk ticket load test"},
        )
    finally:
        event.remove(database.get_bind(), "before_cursor_execute", count_confirm_selects)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "IMPORTING"
    completed = client.get(f"/api/v1/imports/{staged.json()['id']}", headers=admin_headers)
    assert completed.json()["status"] == "COMPLETED"
    assert completed.json()["inserted_rows"] == 500
    assert confirm_select_count < 30


def test_client_import_validate_confirm_and_replay(client: TestClient, admin_headers: dict[str, str]) -> None:
    content = workbook_with_row(["IMPORTED", "Imported Client", "ACTIVE", "Africa/Cairo", "", "import@example.com", "Cairo"])
    staged = client.post("/api/v1/imports/CLIENTS/upload", headers=admin_headers, files={"workbook": ("clients.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert staged.status_code == 201, staged.text
    assert staged.json()["status"] == "READY_FOR_CONFIRMATION"
    confirmed = client.post(f"/api/v1/imports/{staged.json()['id']}/confirm", headers=admin_headers, json={"reason": "Approved initial client import"})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "IMPORTING"
    completed = client.get(f"/api/v1/imports/{staged.json()['id']}", headers=admin_headers)
    assert completed.json()["inserted_rows"] == 1
    replay = client.post("/api/v1/imports/CLIENTS/upload", headers=admin_headers, files={"workbook": ("clients.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert replay.status_code == 409


def test_client_import_accepts_optional_geography_and_creates_primary_location(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    country = Country(iso_alpha2="EG", iso_alpha3="EGY", name="Egypt", is_active=True)
    database.add(country)
    database.flush()
    database.add(City(country_id=country.id, code="CAI", name="Cairo", is_active=True))
    database.commit()
    content = workbook_with_row([
        "GEOCLIENT", "Geographic Client", "ACTIVE", "Africa/Cairo", "", "", "Cairo address", "",
        "2026-08-01", "EGY", "CAI", "HQ", "Cairo Head Office", "Cairo", "30.0444", "31.2357", "Yes",
    ])
    staged = client.post("/api/v1/imports/CLIENTS/upload", headers=admin_headers, files={"workbook": ("clients.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert staged.status_code == 201 and staged.json()["status"] == "READY_FOR_CONFIRMATION", staged.text
    confirmed = client.post(f"/api/v1/imports/{staged.json()['id']}/confirm", headers=admin_headers, json={"reason": "Approved geographic client import"})
    assert confirmed.status_code == 200, confirmed.text
    imported = database.scalar(select(Client).where(Client.code == "GEOCLIENT"))
    assert imported is not None and imported.country_id == country.id and imported.city_id is not None
    location = database.get(ClientLocation, imported.primary_location_id)
    assert location is not None and location.code == "HQ" and location.name == "Cairo Head Office"


def test_master_data_import_supports_parent_and_child_catalog_rows(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    book = load_workbook(io.BytesIO(template_bytes("MASTER_DATA", database)))
    data = book["Data"]
    blank = [""] * 20
    country = blank.copy(); country[0:3] = ["COUNTRY", "JOR", "Jordan"]; country[5:8] = ["JO", "JOR", "Asia/Amman"]; country[19] = "Yes"
    city = blank.copy(); city[0:4] = ["CITY", "AMM", "Amman", "JOR"]; city[19] = "Yes"
    product = blank.copy(); product[0:3] = ["PRODUCT", "RISX", "RIS X"]; product[4] = "Radiology information"; product[19] = "Yes"
    module = blank.copy(); module[0:4] = ["PRODUCT_MODULE", "WORKLIST", "Worklist", "RISX"]; module[19] = "Yes"
    for row in (country, city, product, module): data.append(row)
    output = io.BytesIO(); book.save(output)
    staged = client.post("/api/v1/imports/MASTER_DATA/upload", headers=admin_headers, files={"workbook": ("master.xlsx", output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert staged.status_code == 201 and staged.json()["status"] == "READY_FOR_CONFIRMATION", staged.text
    confirmed = client.post(f"/api/v1/imports/{staged.json()['id']}/confirm", headers=admin_headers, json={"reason": "Approved master data import"})
    assert confirmed.status_code == 200, confirmed.text
    assert database.scalar(select(Country.id).where(Country.iso_alpha3 == "JOR")) is not None


def test_import_rejects_formula_cells(client: TestClient, admin_headers: dict[str, str]) -> None:
    content = workbook_with_row(["FORMULA", "=HYPERLINK(\"http://invalid\")", "ACTIVE", "Africa/Cairo", "", "", ""])
    staged = client.post("/api/v1/imports/CLIENTS/upload", headers=admin_headers, files={"workbook": ("formula.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert staged.status_code == 201
    assert staged.json()["status"] == "VALIDATION_FAILED"
    errors = client.get(f"/api/v1/imports/{staged.json()['id']}/errors", headers=admin_headers)
    assert any(item["error_code"] == "FORMULA_REJECTED" for item in errors.json())


def test_product_module_import_populates_dependent_catalog(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    content = workbook_with_row(
        ["PACS", "Millensys PACS", "Imaging archive", "VIEWER", "Diagnostic Viewer"],
        "PRODUCTS_MODULES",
    )
    staged = client.post(
        "/api/v1/imports/PRODUCTS_MODULES/upload",
        headers=admin_headers,
        files={"workbook": ("products_modules.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert staged.status_code == 201, staged.text
    assert staged.json()["status"] == "READY_FOR_CONFIRMATION"
    confirmed = client.post(
        f"/api/v1/imports/{staged.json()['id']}/confirm",
        headers=admin_headers,
        json={"reason": "Approved product catalog import"},
    )
    assert confirmed.status_code == 200, confirmed.text
    products = client.get("/api/v1/products", headers=admin_headers).json()
    product = next(item for item in products if item["code"] == "PACS")
    modules = client.get(
        f"/api/v1/products/{product['id']}/modules", headers=admin_headers
    )
    assert modules.status_code == 200
    assert modules.json()[0]["code"] == "VIEWER"


def test_service_and_central_sla_imports(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    service_content = workbook_with_row(["REMOTE", "Remote Support", "Remote assistance", "Yes"], "SERVICES")
    staged = client.post("/api/v1/imports/SERVICES/upload", headers=admin_headers, files={"workbook": ("services.xlsx", service_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert staged.status_code == 201 and staged.json()["status"] == "READY_FOR_CONFIRMATION", staged.text
    confirmed = client.post(f"/api/v1/imports/{staged.json()['id']}/confirm", headers=admin_headers, json={"reason": "Approved service import"})
    assert confirmed.status_code == 200, confirmed.text
    calendar_name = database.scalar(select(BusinessCalendar.name))
    sla_content = workbook_with_row(["REMOTE_GOLD", "Remote Gold", calendar_name, "REMOTE", "P1", "15", "60", "75", "Yes"], "SLA_POLICIES")
    sla_staged = client.post("/api/v1/imports/SLA_POLICIES/upload", headers=admin_headers, files={"workbook": ("sla.xlsx", sla_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert sla_staged.status_code == 201 and sla_staged.json()["status"] == "READY_FOR_CONFIRMATION", sla_staged.text
    sla_confirmed = client.post(f"/api/v1/imports/{sla_staged.json()['id']}/confirm", headers=admin_headers, json={"reason": "Approved SLA import"})
    assert sla_confirmed.status_code == 200, sla_confirmed.text
    policies = client.get("/api/v1/sla-policies", headers=admin_headers)
    imported = next(item for item in policies.json() if item["code"] == "REMOTE_GOLD")
    assert imported["targets"][0]["resolution_minutes"] == 60
