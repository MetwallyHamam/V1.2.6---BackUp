from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import func, select, true
from sqlalchemy.dialects import mssql
from sqlalchemy.orm import Session

from app.modules.clients.models import Client, ClientStatus
from app.modules.contracts.models import BusinessCalendar, Contract, ContractClientLink
from app.modules.iam.models import User
from app.modules.shifts.models import Shift, ShiftType
from app.modules.visits.models import (
    ClientVisitEntitlement,
    VisitEntitlementLedgerEntry,
    VisitType,
)


def test_visit_type_active_filter_is_sql_server_safe() -> None:
    statement = select(VisitType.id).where(VisitType.is_active == true())
    sql = str(statement.compile(dialect=mssql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "= 1" in sql
    assert "IS 1" not in sql


def _data(database: Session) -> tuple[Contract, Client, Client]:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    primary = Client(
        code="VISIT-PRIMARY", name="Visit Primary", status_id=status_id, is_active=True
    )
    child = Client(
        code="VISIT-CHILD",
        name="Visit Child",
        status_id=status_id,
        parent_client_id=None,
        is_active=True,
    )
    outsider = Client(
        code="VISIT-OUTSIDE", name="Visit Outside", status_id=status_id, is_active=True
    )
    database.add_all([primary, child, outsider])
    database.flush()
    contract = Contract(
        contract_number="VISIT-2026",
        client_id=primary.id,
        name="Visit Contract",
        status="ACTIVE",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        calendar_id=database.scalar(select(BusinessCalendar.id)),
        is_active=True,
    )
    database.add(contract)
    database.flush()
    database.add(ContractClientLink(contract_id=contract.id, client_id=child.id))
    database.commit()
    return contract, child, outsider


def _entitlement(
    client: TestClient, headers: dict[str, str], database: Session
) -> dict[str, object]:
    contract, child, _ = _data(database)
    visit_type_id = database.scalar(select(VisitType.id).where(VisitType.code == "PREVENTIVE"))
    response = client.post(
        "/api/v1/visits/entitlements",
        headers=headers,
        json={
            "contract_id": contract.id,
            "client_id": child.id,
            "visit_type_id": visit_type_id,
            "service_period_start": "2026-01-01",
            "service_period_end": "2026-12-31",
            "allowed_visits": 4,
            "recurrence": "QUARTERLY",
            "scheduling_mode": "DATE_WINDOW",
            "default_duration_minutes": 120,
            "carry_forward_limit": 0,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_exact_client_scope_rejects_unlinked_client(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    contract, _, outsider = _data(database)
    visit_type_id = database.scalar(select(VisitType.id).where(VisitType.code == "PREVENTIVE"))
    response = client.post(
        "/api/v1/visits/entitlements",
        headers=admin_headers,
        json={
            "contract_id": contract.id,
            "client_id": outsider.id,
            "visit_type_id": visit_type_id,
            "service_period_start": "2026-01-01",
            "service_period_end": "2026-12-31",
            "allowed_visits": 1,
            "recurrence": "ANNUAL",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "VISIT_CLIENT_NOT_CONTRACTED"


def test_bulk_entitlement_creation_is_multi_client_and_atomic(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    contract, child, outsider = _data(database)
    visit_type_id = database.scalar(select(VisitType.id).where(VisitType.code == "PREVENTIVE"))
    common = {
        "contract_id": contract.id,
        "visit_type_id": visit_type_id,
        "service_period_start": "2026-01-01",
        "service_period_end": "2026-12-31",
        "allowed_visits": 4,
        "recurrence": "QUARTERLY",
    }
    created = client.post(
        "/api/v1/visits/entitlements/bulk",
        headers=admin_headers,
        json={**common, "client_ids": [contract.client_id, child.id, child.id]},
    )
    assert created.status_code == 201, created.text
    assert {row["client_id"] for row in created.json()} == {
        contract.client_id,
        child.id,
    }

    before = database.scalar(select(func.count()).select_from(ClientVisitEntitlement))
    second_visit_type_id = database.scalar(
        select(VisitType.id).where(VisitType.code == "OUTDOOR_VISIT")
    )
    rejected = client.post(
        "/api/v1/visits/entitlements/bulk",
        headers=admin_headers,
        json={
            **common,
            "visit_type_id": second_visit_type_id,
            "client_ids": [child.id, outsider.id],
        },
    )
    assert rejected.status_code == 409
    assert database.scalar(select(func.count()).select_from(ClientVisitEntitlement)) == before


def test_outdoor_visit_type_is_linked_to_internal_operations_and_is_defaultable(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    types = client.get("/api/v1/visits/types", headers=admin_headers)
    assert types.status_code == 200
    outdoor = next(item for item in types.json() if item["code"] == "OUTDOOR_VISIT")
    assert outdoor["name"] == "Outdoor / field visit"
    assert outdoor["operation_type_code"] == "OUTDOOR_VISIT"
    contract, child, _ = _data(database)
    created = client.post(
        "/api/v1/visits/entitlements",
        headers=admin_headers,
        json={
            "contract_id": contract.id,
            "client_id": child.id,
            "service_period_start": "2026-01-01",
            "service_period_end": "2026-12-31",
            "allowed_visits": 1,
            "recurrence": "ANNUAL",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["visit_type_id"] == outdoor["id"]


def test_operation_generator_previews_exact_client_entitlement_before_commit(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    entitlement = _entitlement(client, admin_headers, database)
    actor = database.scalar(select(User).where(User.username == "admin"))
    assert actor is not None
    payload = {
        "title": "Entitlement governed preventive visit",
        "operation_type": "OUTDOOR_VISIT",
        "client_id": entitlement["client_id"],
        "start_time": "09:00:00",
        "end_time": "11:00:00",
        "recurrence": {"frequency": "ONCE", "date_from": "2026-09-15", "date_to": "2026-09-15"},
        "timezone": "Africa/Cairo",
        "assignment_strategy": "FIXED",
        "fixed_user_ids": [actor.id],
    }
    preview = client.post(
        "/api/v1/internal-operations/generator/preview", headers=admin_headers, json=payload
    )
    assert preview.status_code == 200, preview.text
    slot = preview.json()["slots"][0]
    assert slot["entitlement_status"] == "COVERED"
    assert slot["entitlement_id"] == entitlement["id"]
    assert slot["entitlement_sequence"] == 1
    applied = client.post(
        "/api/v1/internal-operations/generator/apply",
        headers=admin_headers,
        json={"request": payload, "preview_hash": preview.json()["preview_hash"]},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["created_visit_occurrences"] == 1

    outside = {
        **payload,
        "recurrence": {"frequency": "ONCE", "date_from": "2027-01-15", "date_to": "2027-01-15"},
    }
    uncovered = client.post(
        "/api/v1/internal-operations/generator/preview", headers=admin_headers, json=outside
    )
    assert uncovered.status_code == 200, uncovered.text
    assert uncovered.json()["slots"][0]["entitlement_status"] == "NO_ACTIVE_ENTITLEMENT"
    rejected = client.post(
        "/api/v1/internal-operations/generator/apply",
        headers=admin_headers,
        json={"request": outside, "preview_hash": uncovered.json()["preview_hash"]},
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "VISIT_ENTITLEMENT_PREVIEW_FAILED"


def test_generation_is_idempotent_and_quarterly(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    item = _entitlement(client, admin_headers, database)
    first = client.post(f"/api/v1/visits/entitlements/{item['id']}/generate", headers=admin_headers)
    second = client.post(
        f"/api/v1/visits/entitlements/{item['id']}/generate", headers=admin_headers
    )
    assert first.status_code == 200 and [row["id"] for row in first.json()] == [
        row["id"] for row in second.json()
    ]
    assert [row["window_end"] for row in first.json()] == [
        "2026-03-31",
        "2026-06-30",
        "2026-09-30",
        "2026-12-31",
    ]
    assert (
        client.get(
            f"/api/v1/visits/entitlements/{item['id']}/summary", headers=admin_headers
        ).json()["remaining"]
        == 4
    )


def test_planner_returns_unassigned_occurrences_with_client_and_remaining_allowance(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    item = _entitlement(client, admin_headers, database)
    generated = client.post(
        f"/api/v1/visits/entitlements/{item['id']}/generate", headers=admin_headers
    )
    assert generated.status_code == 200

    planner = client.get(
        "/api/v1/visits/planner?ends_after=2026-01-01T00:00:00%2B00:00&starts_before=2026-12-31T23:59:59%2B00:00&unassigned_only=true",
        headers=admin_headers,
    )

    assert planner.status_code == 200, planner.text
    assert len(planner.json()) == 4
    assert all(row["assignments"] == [] for row in planner.json())
    assert all(row["client_name"] == "Visit Child" for row in planner.json())
    assert all(row["entitlement_remaining"] == 4 for row in planner.json())


def test_completion_consumes_once_and_reopen_compensates(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    item = _entitlement(client, admin_headers, database)
    occurrence = client.post(
        f"/api/v1/visits/entitlements/{item['id']}/generate", headers=admin_headers
    ).json()[0]
    document = client.post(
        f"/api/v1/visits/occurrences/{occurrence['id']}/documents",
        headers=admin_headers,
        files={
            "upload": ("visit-report.pdf", b"%PDF-1.4\nvisit evidence\n%%EOF", "application/pdf")
        },
    )
    assert document.status_code == 201, document.text
    completed = client.post(
        f"/api/v1/visits/occurrences/{occurrence['id']}/complete",
        headers=admin_headers,
        json={
            "actual_visit_date": "2026-03-20",
            "actual_started_at": "2026-03-20T09:00:00+00:00",
            "actual_ended_at": "2026-03-20T11:00:00+00:00",
            "outcome_code": "SUCCESSFUL",
            "result": "Preventive checks completed.",
            "next_action": "Review in next quarter.",
            "customer_acknowledged": True,
            "customer_acknowledged_by": "Client Engineer",
            "customer_acknowledged_at": "2026-03-20T11:00:00+00:00",
            "expected_version": 1,
        },
    )
    assert completed.status_code == 200, completed.text
    repeated = client.post(
        f"/api/v1/visits/occurrences/{occurrence['id']}/complete",
        headers=admin_headers,
        json={
            "actual_visit_date": "2026-03-20",
            "actual_started_at": "2026-03-20T09:00:00+00:00",
            "actual_ended_at": "2026-03-20T11:00:00+00:00",
            "outcome_code": "SUCCESSFUL",
            "result": "Preventive checks completed.",
            "expected_version": 2,
        },
    )
    assert repeated.status_code == 200
    database.expire_all()
    count = database.scalar(
        select(func.count())
        .select_from(VisitEntitlementLedgerEntry)
        .where(
            VisitEntitlementLedgerEntry.idempotency_key == f"visit-completion:{occurrence['id']}"
        )
    )
    assert count == 1
    summary = client.get(
        f"/api/v1/visits/entitlements/{item['id']}/summary", headers=admin_headers
    ).json()
    assert summary["consumed"] == 1 and summary["remaining"] == 3
    reopened = client.post(
        f"/api/v1/visits/occurrences/{occurrence['id']}/reopen",
        headers=admin_headers,
        json={"reason": "Completion evidence requires correction.", "expected_version": 2},
    )
    assert reopened.status_code == 200
    assert (
        client.get(
            f"/api/v1/visits/entitlements/{item['id']}/summary", headers=admin_headers
        ).json()["remaining"]
        == 4
    )


def test_visit_planner_checks_shift_and_visit_overlap(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    item = _entitlement(client, admin_headers, database)
    occurrences = client.post(
        f"/api/v1/visits/entitlements/{item['id']}/generate", headers=admin_headers
    ).json()
    actor = database.scalar(select(User).where(User.username == "admin"))
    shift_type = database.scalar(select(ShiftType).where(ShiftType.code != "LEAVE"))
    database.add(
        Shift(
            shift_type_id=shift_type.id,
            user_id=actor.id,
            starts_at=datetime(2026, 2, 10, 7, tzinfo=UTC),
            ends_at=datetime(2026, 2, 10, 17, tzinfo=UTC),
            status="APPROVED",
            work_location="OFFICE",
            created_by_user_id=actor.id,
        )
    )
    database.commit()
    payload = {
        "starts_at": "2026-02-10T09:00:00+00:00",
        "ends_at": "2026-02-10T11:00:00+00:00",
        "timezone": "UTC",
        "user_ids": [actor.id],
        "expected_version": 1,
        "shift_action": "KEEP_AND_CREATE",
        "shift_decision_reason": "Keep normal coverage and add client visit.",
    }
    scheduled = client.post(
        f"/api/v1/visits/occurrences/{occurrences[0]['id']}/schedule",
        headers=admin_headers,
        json=payload,
    )
    assert scheduled.status_code == 200, scheduled.text
    conflict = client.post(
        f"/api/v1/visits/occurrences/{occurrences[1]['id']}/schedule",
        headers=admin_headers,
        json=payload,
    )
    assert conflict.status_code == 409 and "VISIT_OVERLAP" in conflict.json()["error"]["message"]
    payload["override_reason"] = "Manager approved paired engineer coverage."
    overridden = client.post(
        f"/api/v1/visits/occurrences/{occurrences[1]['id']}/schedule",
        headers=admin_headers,
        json=payload,
    )
    assert overridden.status_code == 200, overridden.text
    assert "VISIT_OVERLAP" in overridden.json()["assignments"][0]["conflict_codes"]


def test_visit_schedule_without_shift_creates_approved_visit_shift(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    item = _entitlement(client, admin_headers, database)
    occurrence = client.post(
        f"/api/v1/visits/entitlements/{item['id']}/generate", headers=admin_headers
    ).json()[0]
    actor = database.scalar(select(User).where(User.username == "admin"))

    response = client.post(
        f"/api/v1/visits/occurrences/{occurrence['id']}/schedule",
        headers=admin_headers,
        json={
            "starts_at": "2026-02-10T09:00:00+00:00",
            "ends_at": "2026-02-10T11:00:00+00:00",
            "timezone": "UTC",
            "user_ids": [actor.id],
            "expected_version": 1,
        },
    )

    assert response.status_code == 200, response.text
    database.expire_all()
    shift = database.scalar(
        select(Shift)
        .join(ShiftType)
        .where(Shift.user_id == actor.id, ShiftType.code == "OUTDOOR_VISIT")
    )
    assert shift is not None
    assert shift.status == "APPROVED"
    assert shift.starts_at == datetime(2026, 2, 10, 11)


def test_existing_same_day_shift_requires_popup_decision(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    item = _entitlement(client, admin_headers, database)
    occurrence = client.post(
        f"/api/v1/visits/entitlements/{item['id']}/generate", headers=admin_headers
    ).json()[0]
    actor = database.scalar(select(User).where(User.username == "admin"))
    shift_type = database.scalar(select(ShiftType).where(ShiftType.code == "DAY"))
    shift = Shift(
        shift_type_id=shift_type.id,
        user_id=actor.id,
        starts_at=datetime(2026, 2, 10, 7, tzinfo=UTC),
        ends_at=datetime(2026, 2, 10, 17, tzinfo=UTC),
        status="APPROVED",
        work_location="OFFICE",
        created_by_user_id=actor.id,
    )
    database.add(shift)
    database.commit()

    response = client.post(
        f"/api/v1/visits/occurrences/{occurrence['id']}/schedule",
        headers=admin_headers,
        json={
            "starts_at": "2026-02-10T09:00:00+00:00",
            "ends_at": "2026-02-10T11:00:00+00:00",
            "timezone": "UTC",
            "user_ids": [actor.id],
            "expected_version": 1,
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "VISIT_SHIFT_DECISION_REQUIRED"
    assert response.json()["error"]["details"]["existing_shifts"][0]["id"] == shift.id


def test_visit_schedule_can_transfer_same_day_shift_and_create_visit_coverage(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    item = _entitlement(client, admin_headers, database)
    occurrence = client.post(
        f"/api/v1/visits/entitlements/{item['id']}/generate", headers=admin_headers
    ).json()[0]
    actor = database.scalar(select(User).where(User.username == "admin"))
    replacement = database.scalar(
        select(User).where(
            User.id != actor.id, User.is_active == true(), User.user_type == "EMPLOYEE"
        )
    )
    shift_type = database.scalar(select(ShiftType).where(ShiftType.code == "DAY"))
    shift = Shift(
        shift_type_id=shift_type.id,
        user_id=actor.id,
        starts_at=datetime(2026, 2, 10, 7, tzinfo=UTC),
        ends_at=datetime(2026, 2, 10, 17, tzinfo=UTC),
        status="APPROVED",
        work_location="OFFICE",
        created_by_user_id=actor.id,
    )
    database.add(shift)
    database.commit()

    response = client.post(
        f"/api/v1/visits/occurrences/{occurrence['id']}/schedule",
        headers=admin_headers,
        json={
            "starts_at": "2026-02-10T09:00:00+00:00",
            "ends_at": "2026-02-10T11:00:00+00:00",
            "timezone": "UTC",
            "user_ids": [actor.id],
            "expected_version": 1,
            "shift_action": "TRANSFER_AND_CREATE",
            "existing_shift_id": shift.id,
            "replacement_user_id": replacement.id,
            "shift_decision_reason": "Transfer normal coverage while engineer attends client visit.",
        },
    )

    assert response.status_code == 200, response.text
    database.expire_all()
    assert database.get(Shift, shift.id).user_id == replacement.id
    visit_shift = database.scalar(
        select(Shift)
        .join(ShiftType)
        .where(Shift.user_id == actor.id, ShiftType.code == "OUTDOOR_VISIT")
    )
    assert visit_shift is not None and visit_shift.status == "APPROVED"


def test_bulk_normal_visits_use_exact_client_entitlement_and_feed_summary_cards(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    entitlement = _entitlement(client, admin_headers, database)
    actor = database.scalar(select(User).where(User.username == "admin"))
    response = client.post(
        "/api/v1/visits/bulk",
        headers=admin_headers,
        json={
            "override_reason": "Approved visit outside a published shift.",
            "rows": [
                {
                    "client_id": entitlement["client_id"],
                    "contract_id": entitlement["contract_id"],
                    "entitlement_id": entitlement["id"],
                    "starts_at": "2026-08-25T09:00:00+00:00",
                    "ends_at": "2026-08-25T11:00:00+00:00",
                    "timezone": "Africa/Cairo",
                    "user_ids": [actor.id],
                    "source_type": "AD_HOC",
                    "notes": "Bulk field visit.",
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["created"] == 1
    cards = client.get(
        "/api/v1/visits/summary-cards?date_from=2026-01-01&date_to=2026-12-31&source_type=AD_HOC",
        headers=admin_headers,
    )
    assert cards.status_code == 200
    assert cards.json()["visits"] == 1 and cards.json()["scheduled"] == 1
    assert cards.json()["entitled"] == 4 and cards.json()["remaining"] == 4
    selected = client.get(
        f"/api/v1/visits/summary-cards?date_from=2026-01-01&date_to=2026-12-31&source_type=AD_HOC&client_ids={entitlement['client_id']}",
        headers=admin_headers,
    )
    outsider_id = database.scalar(select(Client.id).where(Client.code == "VISIT-OUTSIDE"))
    excluded = client.get(
        f"/api/v1/visits/summary-cards?date_from=2026-01-01&date_to=2026-12-31&source_type=AD_HOC&client_ids={outsider_id}",
        headers=admin_headers,
    )
    assert selected.json()["visits"] == 1
    assert excluded.json()["visits"] == 0
