"""Validated Excel import for the reusable UAT test library."""

import io
import uuid
from collections.abc import Sequence
from typing import Protocol

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import StreamingResponse
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.exceptions import ConflictError
from app.db.session import get_db
from app.modules.clients.models import Product, ProductModule
from app.modules.iam.models import AuditLog, User
from app.modules.uat.models import (
    UatChecklistTemplate,
    UatChecklistVersion,
    UatChecklistVersionItem,
    UatTestCase,
    UatTestCaseStep,
)
from app.modules.uat.routes import (
    TemplateInput,
    _new_template_version,
    _validate_template,
)

router = APIRouter(prefix="/uat", tags=["uat import"])
HEADERS = {"code", "title", "expected result", "action", "step expected"}
SIMPLE_TEMPLATE_HEADERS = {"product code", "module code", "test scenario", "expected result"}


def _cell(row: tuple[object, ...], columns: dict[str, int], name: str) -> str:
    index = columns.get(name)
    return str(row[index]).strip() if index is not None and index < len(row) and row[index] is not None else ""


@router.get("/templates/import-template.xlsx")
def download_import_template(
    _actor: User = Depends(require_permission("uat.view")),
) -> StreamingResponse:
    """Download the simple, business-friendly workbook used to create a master template."""
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.title = "UAT Template"
    headers = ["Product Code", "Module Code", "Test Scenario", "Expected Result"]
    sheet.append(headers)
    sheet.append(["PRODUCT-CODE", "MODULE-CODE", "Describe the test scenario", "Describe the expected result"])
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="0E7490")
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = "A1:D2"
    for column, width in {"A": 22, "B": 22, "C": 55, "D": 55}.items():
        sheet.column_dimensions[column].width = width
    output = io.BytesIO()
    book.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="UAT-template-import.xlsx"'},
    )


def _import_simple_template(content: bytes, template_name: str | None, db: Session, actor: User) -> dict[str, object]:
    if not template_name or not template_name.strip():
        raise ConflictError("UAT_IMPORT_TEMPLATE_NAME", "Enter a template name before importing the workbook.")
    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    sheet = workbook.active
    assert sheet is not None
    values = sheet.iter_rows(values_only=True)
    header = next(values, None)
    columns = {str(value).strip().lower(): index for index, value in enumerate(header or ()) if value is not None}
    products = list(db.scalars(select(Product).where(Product.is_active.in_([True]))))
    modules = list(db.scalars(select(ProductModule).where(ProductModule.is_active.in_([True]))))
    product_by_code = {row.code.casefold(): row for row in products}
    module_by_product_code = {(row.product_id, row.code.casefold()): row for row in modules}
    parsed: list[tuple[Product, ProductModule, str, str]] = []
    errors: list[str] = []
    for number, row in enumerate(values, 2):
        if number > 1001:
            raise ConflictError("UAT_IMPORT_ROW_LIMIT", "Import at most 1,000 rows at a time.")
        product_code, module_code, scenario, expected = (
            _cell(row, columns, key)
            for key in ("product code", "module code", "test scenario", "expected result")
        )
        if not any((product_code, module_code, scenario, expected)):
            continue
        product = product_by_code.get(product_code.casefold())
        module = module_by_product_code.get((product.id, module_code.casefold())) if product else None
        if not product:
            errors.append(f"Row {number}: product code {product_code or '(blank)'} does not exist.")
        elif not module:
            errors.append(f"Row {number}: module code {module_code or '(blank)'} does not exist for {product.code}.")
        if not scenario or not expected:
            errors.append(f"Row {number}: Test Scenario and Expected Result are required.")
        if product and module and scenario and expected:
            parsed.append((product, module, scenario, expected))
    workbook.close()
    if errors:
        raise ConflictError("UAT_IMPORT_VALIDATION", "Import aborted: " + "; ".join(errors[:10]))
    if not parsed:
        raise ConflictError("UAT_IMPORT_EMPTY", "Add at least one test scenario to the workbook.")

    cases: list[UatTestCase] = []
    for product, module, scenario, expected in parsed:
        case_code = f"UAT-{uuid.uuid4().hex[:12].upper()}"
        case = UatTestCase(
            code=case_code, title=scenario[:250], product_id=product.id, module_id=module.id,
            expected_result=expected, priority="MEDIUM", created_by_user_id=actor.id,
        )
        db.add(case)
        db.flush()
        db.add(UatTestCaseStep(test_case_id=case.id, step_order=1, action=scenario,
                               expected_result=expected))
        cases.append(case)
    distinct_products = {case.product_id for case in cases}
    template = UatChecklistTemplate(
        code=f"UAT-TPL-{uuid.uuid4().hex[:10].upper()}", name=template_name.strip(),
        product_id=next(iter(distinct_products)) if len(distinct_products) == 1 else None,
        scope_type="GLOBAL", created_by_user_id=actor.id,
    )
    db.add(template)
    db.flush()
    _new_template_version(db, template, cases, actor)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="UatChecklistTemplate", entity_id=str(template.id),
                    action="uat.checklist.simple_imported"))
    db.commit()
    return {"created": 1, "skipped_duplicates": 0, "template_code": template.code,
            "template_name": template.name, "test_cases_created": len(cases)}


@router.get("/templates/{template_id}/export.xlsx")
def export_checklist(template_id: int, db: Session = Depends(get_db),
                     _actor: User = Depends(require_permission("uat.view"))) -> StreamingResponse:
    template = db.get(UatChecklistTemplate, template_id)
    if not template:
        raise ConflictError("UAT_TEMPLATE_NOT_FOUND", "UAT checklist does not exist.")
    version = db.scalar(select(UatChecklistVersion).where(
        UatChecklistVersion.template_id == template.id,
        UatChecklistVersion.version == template.current_version,
    ))
    items = list(db.scalars(select(UatChecklistVersionItem).where(
        UatChecklistVersionItem.version_id == version.id).order_by(UatChecklistVersionItem.display_order))) if version else []
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.title = "Template"
    sheet.append(["Checklist Code", "Checklist Name", "Product", "Case Code", "Section"])
    cases_sheet = book.create_sheet("Test Cases")
    cases_sheet.append(["Code", "Product", "Module", "Feature", "Title", "Expected Result", "Action", "Step Expected", "Priority"])
    product = db.get(Product, template.product_id) if template.product_id else None
    for item in items:
        case = db.get(UatTestCase, item.test_case_id)
        if not case:
            continue
        case_product = db.get(Product, case.product_id) if case.product_id else None
        case_module = db.get(ProductModule, case.module_id) if case.module_id else None
        sheet.append([template.code, template.name, product.name if product else "", case.code, item.section_name or "General"])
        steps = list(db.scalars(select(UatTestCaseStep).where(
            UatTestCaseStep.test_case_id == case.id).order_by(UatTestCaseStep.step_order)))
        for step in steps:
            cases_sheet.append([case.code, case_product.name if case_product else "", case_module.name if case_module else "", case.feature_name or "", case.title, case.expected_result, step.action, step.expected_result, case.priority])
    sheet.freeze_panes = "A2"
    cases_sheet.freeze_panes = "A2"
    output = io.BytesIO()
    book.save(output)
    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f'attachment; filename="{template.code}.xlsx"'})


@router.post("/test-cases/import", status_code=status.HTTP_201_CREATED)
async def import_test_cases(upload: UploadFile = File(...), db: Session = Depends(get_db),
                            actor: User = Depends(require_permission("uat.library.manage"))) -> dict[str, object]:
    if not (upload.filename or "").lower().endswith(".xlsx"):
        raise ConflictError("UAT_IMPORT_FORMAT", "Upload an .xlsx workbook.")
    content = await upload.read(5_000_001)
    await upload.close()
    if len(content) > 5_000_000:
        raise ConflictError("UAT_IMPORT_TOO_LARGE", "The UAT workbook must be under 5 MB.")
    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        if sheet is None:
            raise ValueError("No worksheet")
        values = sheet.iter_rows(values_only=True)
        header = next(values, None)
        columns = {str(value).strip().lower(): index for index, value in enumerate(header or ()) if value is not None}
        if not HEADERS.issubset(columns):
            raise ValueError("Missing required columns")
        pending: list[tuple[str, str, str, str, str, str]] = []
        errors: list[str] = []
        seen: set[str] = set()
        existing = set(db.scalars(select(UatTestCase.code)))
        skipped = 0
        for number, row in enumerate(values, 2):
            if number > 1001:
                raise ConflictError("UAT_IMPORT_ROW_LIMIT", "Import at most 1,000 rows at a time.")
            code, title, expected, action, step_expected = (_cell(row, columns, name) for name in ("code", "title", "expected result", "action", "step expected"))
            if not any((code, title, expected, action, step_expected)):
                continue
            if not all((code, title, expected, action, step_expected)) or len(code) > 80 or len(title) > 250:
                errors.append(f"Row {number}: required values are missing or too long.")
                continue
            priority = _cell(row, columns, "priority").upper() or "MEDIUM"
            if priority not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
                errors.append(f"Row {number}: invalid priority.")
                continue
            if code in existing or code in seen:
                skipped += 1
                continue
            seen.add(code)
            pending.append((code, title, expected, action, step_expected, priority))
        workbook.close()
    except ConflictError:
        raise
    except Exception as exc:
        raise ConflictError("UAT_IMPORT_FORMAT", "The workbook could not be read. Use the required columns: Code, Title, Expected Result, Action, Step Expected.") from exc
    if errors:
        raise ConflictError("UAT_IMPORT_VALIDATION", "Import aborted: " + "; ".join(errors[:10]))
    for code, title, expected, action, step_expected, priority in pending:
        case = UatTestCase(code=code, title=title, expected_result=expected, priority=priority,
                           created_by_user_id=actor.id)
        db.add(case)
        db.flush()
        db.add(UatTestCaseStep(test_case_id=case.id, step_order=1, action=action, expected_result=step_expected))
    db.add(AuditLog(actor_user_id=actor.id, entity_type="UatTestCase", entity_id="0",
                    action="uat.test_cases.imported"))
    db.commit()
    return {"created": len(pending), "skipped_duplicates": skipped}


@router.post("/templates/import", status_code=status.HTTP_201_CREATED)
async def import_checklists(upload: UploadFile = File(...), db: Session = Depends(get_db),
                            template_name: str | None = Form(default=None, min_length=1, max_length=250),
                            actor: User = Depends(require_permission("uat.library.manage"))) -> dict[str, object]:
    """Create global checklists from ordered workbook rows referencing library case codes."""
    if not (upload.filename or "").lower().endswith(".xlsx"):
        raise ConflictError("UAT_IMPORT_FORMAT", "Upload an .xlsx workbook.")
    content = await upload.read(5_000_001)
    await upload.close()
    if len(content) > 5_000_000:
        raise ConflictError("UAT_IMPORT_TOO_LARGE", "The UAT workbook must be under 5 MB.")
    try:
        probe = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        probe_sheet = probe.active
        probe_header = next(probe_sheet.iter_rows(values_only=True), None) if probe_sheet else None
        probe_columns = {str(value).strip().lower() for value in (probe_header or ()) if value is not None}
        probe.close()
        if SIMPLE_TEMPLATE_HEADERS.issubset(probe_columns):
            return _import_simple_template(content, template_name, db, actor)
    except ConflictError:
        raise
    except Exception:
        pass
    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        if sheet is None:
            raise ValueError("No worksheet")
        values = sheet.iter_rows(values_only=True)
        header = next(values, None)
        columns = {str(value).strip().lower(): index for index, value in enumerate(header or ()) if value is not None}
        if not {"checklist code", "checklist name", "case code"}.issubset(columns):
            raise ValueError("Missing required columns")
        groups: dict[str, tuple[str, list[tuple[str, str]]]] = {}
        group_metadata: dict[str, str] = {}
        embedded: dict[str, tuple[str, str, str, list[tuple[str, str]]]] = {}
        embedded_metadata: dict[str, tuple[str, str, str]] = {}
        errors: list[str] = []
        for number, row in enumerate(values, 2):
            if number > 1001:
                raise ConflictError("UAT_IMPORT_ROW_LIMIT", "Import at most 1,000 rows at a time.")
            code, name, case_code, section = (_cell(row, columns, key) for key in
                                              ("checklist code", "checklist name", "case code", "section"))
            product_name = _cell(row, columns, "product")
            if not any((code, name, case_code, section)):
                continue
            if not all((code, name, case_code)) or len(code) > 80 or len(name) > 250 or len(section) > 150:
                errors.append(f"Row {number}: required values are missing or too long.")
                continue
            if code in groups and groups[code][0] != name:
                errors.append(f"Row {number}: checklist name conflicts with an earlier row.")
                continue
            groups.setdefault(code, (name, []))[1].append((case_code, section))
            previous_product = group_metadata.setdefault(code, product_name)
            if previous_product != product_name:
                errors.append(f"Row {number}: product conflicts with an earlier row.")
        if "Test Cases" in workbook.sheetnames:
            case_values = workbook["Test Cases"].iter_rows(values_only=True)
            case_header = next(case_values, None)
            case_columns = {str(value).strip().lower(): index for index, value in enumerate(case_header or ()) if value is not None}
            if not HEADERS.issubset(case_columns):
                errors.append("Test Cases sheet is missing required columns.")
            else:
                for number, row in enumerate(case_values, 2):
                    code, title, expected, action, step_expected = (_cell(row, case_columns, key) for key in
                                                                     ("code", "title", "expected result", "action", "step expected"))
                    if not any((code, title, expected, action, step_expected)):
                        continue
                    priority = _cell(row, case_columns, "priority").upper() or "MEDIUM"
                    product_name = _cell(row, case_columns, "product")
                    module_name = _cell(row, case_columns, "module")
                    feature_name = _cell(row, case_columns, "feature")
                    if not all((code, title, expected, action, step_expected)) or priority not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
                        errors.append(f"Test Cases row {number}: invalid or missing value.")
                        continue
                    existing_definition = embedded.get(code)
                    if existing_definition and existing_definition[:3] != (title, expected, priority):
                        errors.append(f"Test Cases row {number}: case {code} has conflicting details.")
                        continue
                    embedded.setdefault(code, (title, expected, priority, []))[3].append((action, step_expected))
                    embedded_metadata.setdefault(code, (product_name, module_name, feature_name))
        workbook.close()
    except ConflictError:
        raise
    except Exception as exc:
        raise ConflictError("UAT_IMPORT_FORMAT", "Use columns: Checklist Code, Checklist Name, Case Code, optional Section.") from exc
    if errors:
        raise ConflictError("UAT_IMPORT_VALIDATION", "Import aborted: " + "; ".join(errors[:10]))
    generated_code: str | None = None
    if template_name:
        if len(groups) != 1:
            raise ConflictError("UAT_IMPORT_TEMPLATE_COUNT", "Import one master template per workbook.")
        old_code, (_old_name, template_rows) = next(iter(groups.items()))
        generated_code = f"UAT-TPL-{uuid.uuid4().hex[:10].upper()}"
        groups = {generated_code: (template_name.strip(), template_rows)}
        group_metadata = {generated_code: group_metadata.get(old_code, "")}
    existing_templates = set(db.scalars(select(UatChecklistTemplate.code)))
    products = list(db.scalars(select(Product).where(Product.is_active.in_([True]))))
    modules = list(db.scalars(select(ProductModule).where(ProductModule.is_active.in_([True]))))
    class CatalogRow(Protocol):
        id: int
        name: str
        code: str

    def catalog_match[CatalogT: CatalogRow](value: str, rows: Sequence[CatalogT]) -> CatalogT | None:
        wanted = value.casefold().strip()
        return next((row for row in rows if wanted in {str(getattr(row, "name", "")).casefold(), str(getattr(row, "code", "")).casefold()}), None) if wanted else None
    case_codes = {case_code for _, rows in groups.values() for case_code, _ in rows}
    cases = {case.code: case for case in db.scalars(select(UatTestCase).where(UatTestCase.code.in_(case_codes)))}
    for code in case_codes - set(cases):
        definition = embedded.get(code)
        if not definition:
            continue
        title, expected, priority, steps = definition
        product_name, module_name, feature_name = embedded_metadata.get(code, ("", "", ""))
        product = catalog_match(product_name, products)
        module_options = [row for row in modules if not product or row.product_id == product.id]
        module = catalog_match(module_name, module_options)
        if product_name and not product:
            errors.append(f"Test case {code}: product {product_name} does not exist.")
            continue
        if module_name and not module:
            errors.append(f"Test case {code}: module {module_name} does not exist for the selected product.")
            continue
        case = UatTestCase(code=code, title=title, expected_result=expected, priority=priority,
                           product_id=getattr(product, "id", None), module_id=getattr(module, "id", None),
                           feature_name=feature_name or None,
                           created_by_user_id=actor.id)
        db.add(case)
        db.flush()
        for order, (action, step_expected) in enumerate(steps, 1):
            db.add(UatTestCaseStep(test_case_id=case.id, step_order=order, action=action,
                                   expected_result=step_expected))
        cases[code] = case
    skipped = 0
    pending: list[tuple[TemplateInput, list[UatTestCase]]] = []
    for code, (name, rows) in groups.items():
        if code in existing_templates:
            skipped += 1
            continue
        seen: set[str] = set()
        for case_code, _ in rows:
            if case_code in seen:
                errors.append(f"Checklist {code}: duplicate case code {case_code}.")
            seen.add(case_code)
            if case_code not in cases or not cases[case_code].is_active:
                errors.append(f"Checklist {code}: active case {case_code} does not exist.")
        if not all(case_code in cases and cases[case_code].is_active for case_code, _ in rows):
            continue
        product_name = group_metadata.get(code, "")
        product = catalog_match(product_name, products)
        if product_name and not product:
            errors.append(f"Checklist {code}: product {product_name} does not exist.")
        data = TemplateInput(code=code, name=name, product_id=getattr(product, "id", None),
                             test_case_ids=[cases[case_code].id for case_code, _ in rows],
                             section_names={cases[case_code].id: section for case_code, section in rows if section})
        pending.append((data, _validate_template(db, data)))
    if errors:
        raise ConflictError("UAT_IMPORT_VALIDATION", "Import aborted: " + "; ".join(errors[:10]))
    for data, selected_cases in pending:
        template = UatChecklistTemplate(code=data.code, name=data.name, product_id=data.product_id,
                                          scope_type="GLOBAL", created_by_user_id=actor.id)
        db.add(template)
        db.flush()
        _new_template_version(db, template, selected_cases, actor, data.section_names)
        db.add(AuditLog(actor_user_id=actor.id, entity_type="UatChecklistTemplate", entity_id=str(template.id),
                        action="uat.checklist.imported"))
    db.commit()
    result: dict[str, object] = {"created": len(pending), "skipped_duplicates": skipped}
    if template_name and generated_code:
        result.update(template_code=generated_code, template_name=template_name.strip())
    return result
