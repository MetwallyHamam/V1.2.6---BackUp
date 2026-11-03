import io

from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Product, ProductModule


def _workbook(rows: list[list[str]]) -> bytes:
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    for row in rows:
        sheet.append(row)
    output = io.BytesIO()
    book.save(output)
    return output.getvalue()


def test_uat_excel_import_validates_and_skips_duplicates(client: TestClient, admin_headers: dict[str, str]) -> None:
    headers = ["Code", "Title", "Expected Result", "Action", "Step Expected", "Priority"]
    content = _workbook([headers, ["IMPORT-1", "Imported case", "Done", "Run", "Done", "HIGH"],
                         ["IMPORT-1", "Duplicate", "Done", "Run", "Done", "HIGH"]])
    response = client.post("/api/v1/uat/test-cases/import", headers=admin_headers,
                           files={"upload": ("uat.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert response.status_code == 201, response.text
    assert response.json() == {"created": 1, "skipped_duplicates": 1}
    cases = client.get("/api/v1/uat/test-cases", headers=admin_headers).json()
    assert len(cases) == 1 and cases[0]["steps"][0]["action"] == "Run"
    invalid = _workbook([headers, ["IMPORT-2", "Good", "Done", "Run", "Done", "HIGH"],
                         ["IMPORT-3", "Bad", "Done", "Run", "Done", "INVALID"]])
    response = client.post("/api/v1/uat/test-cases/import", headers=admin_headers,
                           files={"upload": ("uat.xlsx", invalid, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert response.status_code == 409
    assert [row["code"] for row in client.get("/api/v1/uat/test-cases", headers=admin_headers).json()] == ["IMPORT-1"]


def test_checklist_import_preserves_sections_and_is_atomic(client: TestClient, admin_headers: dict[str, str]) -> None:
    case_headers = ["Code", "Title", "Expected Result", "Action", "Step Expected"]
    cases = _workbook([case_headers, ["CI-1", "First", "Done", "Run", "Done"],
                       ["CI-2", "Second", "Done", "Run", "Done"]])
    assert client.post("/api/v1/uat/test-cases/import", headers=admin_headers,
                       files={"upload": ("cases.xlsx", cases)}).status_code == 201
    headers = ["Checklist Code", "Checklist Name", "Case Code", "Section"]
    invalid = _workbook([headers, ["CL-1", "Checklist", "CI-1", "Start"],
                         ["CL-1", "Checklist", "MISSING", "Finish"]])
    response = client.post("/api/v1/uat/templates/import", headers=admin_headers,
                           files={"upload": ("checklists.xlsx", invalid)})
    assert response.status_code == 409
    assert client.get("/api/v1/uat/templates", headers=admin_headers).json() == []
    valid = _workbook([headers, ["CL-1", "Checklist", "CI-1", "Start"],
                       ["CL-1", "Checklist", "CI-2", "Finish"]])
    response = client.post("/api/v1/uat/templates/import", headers=admin_headers,
                           files={"upload": ("checklists.xlsx", valid)})
    assert response.status_code == 201, response.text
    assert response.json() == {"created": 1, "skipped_duplicates": 0}
    template = client.get("/api/v1/uat/templates", headers=admin_headers).json()[0]
    assert list(template["section_names"].values()) == ["Start", "Finish"]
    again = client.post("/api/v1/uat/templates/import", headers=admin_headers,
                        files={"upload": ("checklists.xlsx", valid)})
    assert again.json() == {"created": 0, "skipped_duplicates": 1}


def test_portable_checklist_import_creates_embedded_library_cases(client: TestClient, admin_headers: dict[str, str]) -> None:
    book = Workbook()
    template = book.active
    assert template is not None
    template.title = "Template"
    template.append(["Checklist Code", "Checklist Name", "Case Code", "Section"])
    template.append(["PORTABLE", "Portable checklist", "PORTABLE-1", "Smoke"])
    cases = book.create_sheet("Test Cases")
    cases.append(["Code", "Title", "Expected Result", "Action", "Step Expected", "Priority"])
    cases.append(["PORTABLE-1", "Portable case", "Complete", "First", "First complete", "HIGH"])
    cases.append(["PORTABLE-1", "Portable case", "Complete", "Second", "Second complete", "HIGH"])
    output = io.BytesIO()
    book.save(output)
    response = client.post("/api/v1/uat/templates/import", headers=admin_headers,
                           files={"upload": ("portable.xlsx", output.getvalue())})
    assert response.status_code == 201, response.text
    imported = next(row for row in client.get("/api/v1/uat/test-cases", headers=admin_headers).json()
                    if row["code"] == "PORTABLE-1")
    assert [step["action"] for step in imported["steps"]] == ["First", "Second"]
    template_row = next(row for row in client.get("/api/v1/uat/templates", headers=admin_headers).json()
                        if row["code"] == "PORTABLE")
    exported = client.get(f"/api/v1/uat/templates/{template_row['id']}/export.xlsx", headers=admin_headers)
    assert exported.status_code == 200 and exported.content.startswith(b"PK")


def test_named_master_template_import_generates_code_and_stays_client_independent(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    book = Workbook()
    template = book.active
    assert template is not None
    template.title = "Template"
    template.append(["Checklist Code", "Checklist Name", "Product", "Case Code", "Section"])
    template.append(["OLD-CODE", "Old workbook name", "", "MASTER-1", "Core"])
    cases = book.create_sheet("Test Cases")
    cases.append(["Code", "Product", "Module", "Feature", "Title", "Expected Result", "Action", "Step Expected", "Priority"])
    cases.append(["MASTER-1", "", "", "", "Reusable test", "Complete", "Run", "Complete", "MEDIUM"])
    output = io.BytesIO()
    book.save(output)

    response = client.post(
        "/api/v1/uat/templates/import",
        headers=admin_headers,
        data={"template_name": "Imported Master"},
        files={"upload": ("master.xlsx", output.getvalue())},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["template_name"] == "Imported Master"
    assert payload["template_code"].startswith("UAT-TPL-")

    imported = next(row for row in client.get("/api/v1/uat/templates", headers=admin_headers).json()
                    if row["code"] == payload["template_code"])
    assert imported["name"] == "Imported Master"
    assert imported["scope_type"] == "GLOBAL"
    assert imported["client_ids"] == []


def test_simple_business_workbook_download_and_import(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    starter = client.get("/api/v1/uat/templates/import-template.xlsx", headers=admin_headers)
    assert starter.status_code == 200
    starter_book = load_workbook(io.BytesIO(starter.content), read_only=True)
    assert list(next(starter_book.active.iter_rows(values_only=True))) == [
        "Product Code", "Module Code", "Test Scenario", "Expected Result",
    ]
    starter_book.close()

    product = database.scalar(select(Product)) or Product(code="UAT-PRODUCT", name="UAT Product")
    database.add(product)
    database.flush()
    module = database.scalar(select(ProductModule).where(ProductModule.product_id == product.id))
    if module is None:
        module = ProductModule(product_id=product.id, code="CORE", name="Core")
        database.add(module)
        database.commit()
    content = _workbook([
        ["Product Code", "Module Code", "Test Scenario", "Expected Result"],
        [product.code, module.code, "User can save a request", "Request is saved"],
    ])
    response = client.post(
        "/api/v1/uat/templates/import",
        headers=admin_headers,
        data={"template_name": "Single Feature"},
        files={"upload": ("simple.xlsx", content)},
    )
    assert response.status_code == 201, response.text
    assert response.json()["test_cases_created"] == 1
    imported = next(row for row in client.get("/api/v1/uat/templates", headers=admin_headers).json()
                    if row["name"] == "Single Feature")
    assert len(imported["test_case_ids"]) == 1
