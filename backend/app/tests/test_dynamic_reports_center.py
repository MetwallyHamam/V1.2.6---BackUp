from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import ConflictError
from app.modules.reports.dynamic_routes import FilterDefinition, validate_report_scope


def test_admin_can_register_a_structured_stored_procedure_report(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    created = client.post(
        "/api/v1/reports-center/definitions",
        headers=admin_headers,
        json={
            "code": "TEST_ACTIVITY_REPORT",
            "name": "Test activity report",
            "category": "Testing",
            "stored_procedure": "dbo.usp_SupportHub_Report_TestActivity",
            "filters": [
                {
                    "name": "date_from",
                    "label": "Date from",
                    "type": "date",
                    "required": False,
                    "options": [],
                },
                {
                    "name": "result",
                    "label": "Result",
                    "type": "select",
                    "required": False,
                    "options": [{"value": "PASSED", "label": "Passed"}],
                },
            ],
            "default_page_size": 50,
            "default_sort_column": "created_at",
            "default_sort_direction": "DESC",
            "is_active": True,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["stored_procedure"] == "dbo.usp_SupportHub_Report_TestActivity"
    assert created.json()["filters"][1]["options"][0]["value"] == "PASSED"

    catalog = client.get("/api/v1/reports-center", headers=admin_headers)
    assert catalog.status_code == 200, catalog.text
    assert any(row["code"] == "TEST_ACTIVITY_REPORT" for row in catalog.json())


def test_report_definition_rejects_sql_text_and_reserved_parameters(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    invalid_procedure = client.post(
        "/api/v1/reports-center/definitions",
        headers=admin_headers,
        json={
            "code": "UNSAFE_REPORT",
            "name": "Unsafe report",
            "stored_procedure": "dbo.report; DROP TABLE users",
            "filters": [],
        },
    )
    assert invalid_procedure.status_code == 409
    assert invalid_procedure.json()["error"]["code"] == "INVALID_REPORT_PROCEDURE"

    reserved = client.post(
        "/api/v1/reports-center/definitions",
        headers=admin_headers,
        json={
            "code": "RESERVED_REPORT",
            "name": "Reserved report",
            "stored_procedure": "dbo.usp_SupportHub_Report_Reserved",
            "filters": [
                {"name": "page", "label": "Page", "type": "number", "options": []}
            ],
        },
    )
    assert reserved.status_code == 409
    assert reserved.json()["error"]["code"] == "RESERVED_REPORT_FILTER"


def test_report_center_exposes_whitelisted_lookup_options(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    users = client.get(
        "/api/v1/reports-center/filter-options/users",
        headers=admin_headers,
        params={"q": "admin"},
    )
    assert users.status_code == 200, users.text
    assert any(option["value"] and option["label"] for option in users.json())

    unknown = client.get(
        "/api/v1/reports-center/filter-options/database_tables",
        headers=admin_headers,
    )
    assert unknown.status_code == 404


def test_report_definition_accepts_only_approved_lookup_sources(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    payload = {
        "code": "LOOKUP_REPORT",
        "name": "Lookup report",
        "stored_procedure": "dbo.usp_SupportHub_Report_Lookup",
        "filters": [{
            "name": "client_id", "label": "Client", "type": "lookup",
            "lookup_source": "clients", "options": [],
        }],
    }
    valid = client.post("/api/v1/reports-center/definitions", headers=admin_headers, json=payload)
    assert valid.status_code == 201, valid.text
    assert valid.json()["filters"][0]["lookup_source"] == "clients"

    payload["code"] = "UNSAFE_LOOKUP_REPORT"
    payload["filters"][0]["lookup_source"] = "arbitrary_table"
    invalid = client.post("/api/v1/reports-center/definitions", headers=admin_headers, json=payload)
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "INVALID_REPORT_LOOKUP"


def test_report_scope_requires_bounded_dates() -> None:
    definitions = [
        FilterDefinition(name="date_from", label="Date from", type="date"),
        FilterDefinition(name="date_to", label="Date to", type="date"),
    ]
    with pytest.raises(ConflictError):
        validate_report_scope(definitions, {"date_from": None, "date_to": None})
    with pytest.raises(ConflictError):
        validate_report_scope(
            definitions,
            {"date_from": date(2025, 1, 1), "date_to": date(2026, 9, 27)},
        )


def test_report_without_dates_requires_a_narrowing_filter() -> None:
    definitions = [FilterDefinition(name="client_id", label="Client", type="number")]
    with pytest.raises(ConflictError):
        validate_report_scope(definitions, {"client_id": None})
    validate_report_scope(definitions, {"client_id": 42})


def test_report_allows_optional_paired_date_filters_with_another_filter() -> None:
    definitions = [
        FilterDefinition(name="expiry_from", label="Expiry from", type="date", default=""),
        FilterDefinition(name="expiry_to", label="Expiry to", type="date", default=""),
        FilterDefinition(name="status", label="Status", type="select", default="ACTIVE"),
    ]
    validate_report_scope(
        definitions,
        {"expiry_from": None, "expiry_to": None, "status": "ACTIVE"},
    )
    with pytest.raises(ConflictError):
        validate_report_scope(
            definitions,
            {"expiry_from": date(2026, 1, 1), "expiry_to": None, "status": "ACTIVE"},
        )
