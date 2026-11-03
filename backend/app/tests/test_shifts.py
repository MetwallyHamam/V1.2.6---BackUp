from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.modules.iam.models import Department, Permission, ProfilePermission, User, UserProfile
from app.modules.iam.service import effective_permissions
from app.modules.shifts.generator import recurrence_dates
from app.modules.shifts.models import Shift, ShiftType
from app.modules.shifts.schemas import ScheduleRecurrence


def test_real_date_recurrence_handles_month_lengths_leap_year_and_cross_year() -> None:
    leap=recurrence_dates(ScheduleRecurrence(frequency="DAILY",date_from=date(2028,2,1),date_to=date(2028,2,29)))
    normal=recurrence_dates(ScheduleRecurrence(frequency="DAILY",date_from=date(2027,2,1),date_to=date(2027,2,28)))
    april=recurrence_dates(ScheduleRecurrence(frequency="DAILY",date_from=date(2030,4,1),date_to=date(2030,4,30)))
    may=recurrence_dates(ScheduleRecurrence(frequency="DAILY",date_from=date(2030,5,1),date_to=date(2030,5,31)))
    monthly=recurrence_dates(ScheduleRecurrence(frequency="MONTHLY",date_from=date(2028,1,31),date_to=date(2028,3,31)))
    cross_year=recurrence_dates(ScheduleRecurrence(frequency="WEEKLY",date_from=date(2031,12,29),date_to=date(2032,1,12)))
    assert len(leap)==29 and leap[-1]==date(2028,2,29)
    assert len(normal)==28 and len(april)==30 and len(may)==31
    assert monthly==[date(2028,1,31),date(2028,2,29),date(2028,3,31)]
    assert cross_year==[date(2031,12,29),date(2032,1,5),date(2032,1,12)]


def test_shift_employee_picker_does_not_require_user_management(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    admin = database.scalar(select(User).where(User.username == "admin"))
    user_manage_id = database.scalar(select(Permission.id).where(Permission.code == "user.manage"))
    assert admin is not None and user_manage_id is not None
    profile_ids = select(UserProfile.profile_id).where(UserProfile.user_id == admin.id)
    database.execute(
        delete(ProfilePermission).where(
            ProfilePermission.profile_id.in_(profile_ids),
            ProfilePermission.permission_id == user_manage_id,
        )
    )
    database.commit()
    permissions = set(effective_permissions(database, admin).permissions)
    assert "user.manage" not in permissions
    assert "shift.assign_employee" in permissions

    response = client.get("/api/v1/shift-employees", headers=admin_headers)
    assert response.status_code == 200, response.text
    assert any(item["id"] == admin.id for item in response.json())


def test_shift_overlap_requires_override(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    user_id = database.scalar(select(User.id).where(User.username == "admin"))
    shift_type_id = database.scalar(select(ShiftType.id).where(ShiftType.code == "DAY"))
    start = server_now() + timedelta(days=1)
    payload = {"shift_type_id": shift_type_id, "user_id": user_id, "starts_at": start.isoformat(), "ends_at": (start + timedelta(hours=8)).isoformat()}
    first = client.post("/api/v1/shifts", headers=admin_headers, json=payload)
    assert first.status_code == 201, first.text
    second = client.post("/api/v1/shifts", headers=admin_headers, json=payload)
    assert second.status_code == 409
    payload["overlap_override_reason"] = "Approved backup coverage"
    override = client.post("/api/v1/shifts", headers=admin_headers, json=payload)
    assert override.status_code == 201, override.text


def test_quick_shift_uses_type_defaults_multi_select_and_preserves_historical_time(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    employees = list(database.scalars(select(User).where(User.is_active.in_([True]), User.user_type == "EMPLOYEE").order_by(User.id).limit(2)))
    shift_type = database.scalar(select(ShiftType).where(ShiftType.code == "DAY"))
    assert len(employees) == 2 and shift_type is not None
    for employee in employees:
        employee.participates_in_shifts = True
    database.commit()
    updated = client.patch(f"/api/v1/shift-types/{shift_type.id}", headers=admin_headers, json={
        "name": shift_type.name, "description": shift_type.description, "color": shift_type.color,
        "is_on_call": shift_type.is_on_call, "display_order": shift_type.display_order,
        "is_active": True, "enforce_employee_eligibility": False,
        "default_start_time": "09:00:00", "default_end_time": "17:00:00", "default_required_headcount": 2,
    })
    assert updated.status_code == 200, updated.text
    context = client.get("/api/v1/shifts/quick-context", headers=admin_headers, params={"date":"2035-08-24","shift_type_id":shift_type.id,"timezone":"UTC"})
    assert context.status_code == 200, context.text
    assert context.json()["required_headcount"] == 2
    assert {row["employee_id"] for row in context.json()["candidates"]} >= {employee.id for employee in employees}
    created = client.post("/api/v1/shifts/quick", headers=admin_headers, json={
        "date":"2035-08-24", "shift_type_id":shift_type.id, "assignment_mode":"MANUAL",
        "user_ids":[employee.id for employee in employees], "timezone":"UTC", "notes":"V2 quick manual shift",
    })
    assert created.status_code == 201, created.text
    assert created.json()["created"] == 2 and created.json()["required_headcount"] == 2
    assert created.json()["starts_at"].startswith("2035-08-24T12:00:00+03:00")
    assert created.json()["ends_at"].startswith("2035-08-24T20:00:00+03:00")

    changed = client.patch(f"/api/v1/shift-types/{shift_type.id}", headers=admin_headers, json={
        "name": shift_type.name, "description": shift_type.description, "color": shift_type.color,
        "is_on_call": shift_type.is_on_call, "display_order": shift_type.display_order,
        "is_active": True, "enforce_employee_eligibility": False,
        "default_start_time": "10:00:00", "default_end_time": "18:00:00", "default_required_headcount": 2,
    })
    assert changed.status_code == 200, changed.text
    database.expire_all()
    stored = list(database.scalars(select(Shift).where(Shift.id.in_([row["id"] for row in created.json()["shifts"]]))))
    assert all(row.starts_at == datetime(2035, 8, 24, 12) and row.ends_at == datetime(2035, 8, 24, 20) for row in stored)


def test_quick_shift_creates_inclusive_date_range_transactionally(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    actor = database.scalar(select(User).where(User.username == "admin"))
    shift_type = database.scalar(select(ShiftType).where(ShiftType.code == "DAY"))
    assert actor is not None and shift_type is not None
    actor.participates_in_shifts = True
    shift_type.enforce_employee_eligibility = False
    shift_type.default_start_time = datetime.strptime("09:00", "%H:%M").time()
    shift_type.default_end_time = datetime.strptime("17:00", "%H:%M").time()
    database.commit()
    context = client.get("/api/v1/shifts/quick-context", headers=admin_headers, params={
        "date":"2037-09-01", "date_to":"2037-09-03", "shift_type_id":shift_type.id, "timezone":"UTC",
    })
    assert context.status_code == 200, context.text
    assert context.json()["date_to"] == "2037-09-03"
    created = client.post("/api/v1/shifts/quick", headers=admin_headers, json={
        "date_from":"2037-09-01", "date_to":"2037-09-03", "shift_type_id":shift_type.id,
        "assignment_mode":"MANUAL", "user_ids":[actor.id], "timezone":"UTC",
    })
    assert created.status_code == 201, created.text
    assert created.json()["created"] == 3
    assert len(created.json()["coverage_slot_ids"]) == 3
    assert [row["starts_at"][:10] for row in created.json()["shifts"]] == ["2037-09-01", "2037-09-02", "2037-09-03"]


def test_manual_shift_rejects_non_participant_even_without_type_eligibility_enforcement(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    actor = database.scalar(select(User).where(User.username == "admin"))
    shift_type = database.scalar(select(ShiftType).where(ShiftType.code == "DAY"))
    assert actor is not None and shift_type is not None
    actor.participates_in_shifts = False
    shift_type.enforce_employee_eligibility = False
    database.commit()
    response = client.post("/api/v1/shifts", headers=admin_headers, json={
        "shift_type_id":shift_type.id, "user_id":actor.id,
        "starts_at":"2036-01-04T09:00:00+00:00", "ends_at":"2036-01-04T17:00:00+00:00",
    })
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SHIFT_EMPLOYEE_NOT_PARTICIPANT"


def test_quick_shift_context_handles_friday_overlap_and_cross_midnight(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    actor = database.scalar(select(User).where(User.username == "admin"))
    assert actor is not None
    actor.participates_in_shifts = True
    types = [
        ShiftType(code="V2_FRI_MORNING", name="Friday Morning", color="#145da0", default_start_time=datetime.strptime("09:00", "%H:%M").time(), default_end_time=datetime.strptime("17:00", "%H:%M").time(), default_required_headcount=2),
        ShiftType(code="V2_FRI_EVENING", name="Friday Evening", color="#7b1fa2", default_start_time=datetime.strptime("14:00", "%H:%M").time(), default_end_time=datetime.strptime("22:00", "%H:%M").time(), default_required_headcount=2),
        ShiftType(code="V2_FRI_NIGHT", name="Friday Night", color="#263238", default_start_time=datetime.strptime("16:00", "%H:%M").time(), default_end_time=datetime.strptime("00:00", "%H:%M").time(), default_required_headcount=2),
    ]
    database.add_all(types); database.commit()
    morning = client.post("/api/v1/shifts/quick", headers=admin_headers, json={"date":"2036-08-29","shift_type_id":types[0].id,"assignment_mode":"MANUAL","user_ids":[actor.id],"timezone":"UTC"})
    assert morning.status_code == 201, morning.text
    evening = client.get("/api/v1/shifts/quick-context", headers=admin_headers, params={"date":"2036-08-29","shift_type_id":types[1].id,"timezone":"UTC"})
    actor_evening = next(row for row in evening.json()["candidates"] if row["employee_id"] == actor.id)
    assert actor_evening["available"] is False and actor_evening["shift_conflict"] is True
    night = client.get("/api/v1/shifts/quick-context", headers=admin_headers, params={"date":"2036-08-29","shift_type_id":types[2].id,"timezone":"UTC"})
    assert night.status_code == 200
    assert night.json()["starts_at"].startswith("2036-08-29T19:00:00+03:00")
    assert night.json()["ends_at"].startswith("2036-08-30T03:00:00+03:00")


def test_scheduling_workload_includes_participants_and_real_shift_minutes(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    actor = database.scalar(select(User).where(User.username == "admin"))
    shift_type_id = database.scalar(select(ShiftType.id).where(ShiftType.code == "DAY"))
    assert actor is not None and shift_type_id is not None
    actor.participates_in_shifts = True
    database.commit()
    starts_at = datetime(2031, 2, 3, 8, tzinfo=UTC)
    created = client.post(
        "/api/v1/shifts",
        headers=admin_headers,
        json={
            "shift_type_id": shift_type_id,
            "user_id": actor.id,
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(hours=7, minutes=30)).isoformat(),
        },
    )
    assert created.status_code == 201, created.text
    response = client.get(
        "/api/v1/scheduling/workload",
        headers=admin_headers,
        params={
            "starts_at": (starts_at - timedelta(days=1)).isoformat(),
            "ends_at": (starts_at + timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    row = next(item for item in response.json() if item["employee_id"] == actor.id)
    assert row["shift_count"] == 1
    assert row["shift_minutes"] == 450
    assert row["total_minutes"] == 450


def test_copy_week_previews_multiple_targets_and_rejects_reusing_a_stale_preview(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    actor = database.scalar(select(User).where(User.username == "admin"))
    shift_type_id = database.scalar(select(ShiftType.id).where(ShiftType.code == "DAY"))
    assert actor is not None and shift_type_id is not None
    actor.participates_in_shifts = True
    database.commit()
    source_start = datetime(2034, 5, 1, tzinfo=UTC)
    created = client.post(
        "/api/v1/shifts",
        headers=admin_headers,
        json={"shift_type_id":shift_type_id,"user_id":actor.id,"starts_at":(source_start+timedelta(hours=8)).isoformat(),"ends_at":(source_start+timedelta(hours=16)).isoformat()},
    )
    assert created.status_code == 201, created.text
    request = {
        "source_week_start": source_start.isoformat(),
        "target_week_starts": [(source_start+timedelta(days=7)).isoformat(),(source_start+timedelta(days=14)).isoformat()],
        "assignment_mode": "KEEP_ENGINEERS",
        "skip_conflicts": True,
    }
    preview = client.post("/api/v1/shifts/duplicate-week/preview",headers=admin_headers,json=request)
    assert preview.status_code == 200, preview.text
    assert preview.json()["source_count"] == 1
    assert preview.json()["target_week_count"] == 2
    assert preview.json()["ready"] == 2
    applied = client.post("/api/v1/shifts/duplicate-week",headers=admin_headers,json={**request,"preview_hash":preview.json()["preview_hash"]})
    assert applied.status_code == 200, applied.text
    assert applied.json() == {"created":2,"skipped":0}
    stale = client.post("/api/v1/shifts/duplicate-week",headers=admin_headers,json={**request,"preview_hash":preview.json()["preview_hash"]})
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "SCHEDULE_PREVIEW_CHANGED"


def test_enforced_shift_eligibility_requires_participation_and_explicit_eligibility(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    actor = database.scalar(select(User).where(User.username == "admin"))
    assert actor is not None
    shift_type = client.post(
        "/api/v1/shift-types",
        headers=admin_headers,
        json={"name": "Eligibility enforced night", "enforce_employee_eligibility": True},
    )
    assert shift_type.status_code == 201, shift_type.text
    shift_type_id = shift_type.json()["id"]
    start = datetime(2028, 1, 3, 20, tzinfo=UTC)
    payload = {"shift_type_id": shift_type_id, "user_id": actor.id, "starts_at": start.isoformat(), "ends_at": (start + timedelta(hours=8)).isoformat()}

    missing = client.post("/api/v1/shifts", headers=admin_headers, json=payload)
    assert missing.status_code == 409
    assert missing.json()["error"]["code"] == "SHIFT_EMPLOYEE_NOT_ELIGIBLE"

    saved = client.put(
        "/api/v1/shift-eligibilities",
        headers=admin_headers,
        json={"rows": [{"employee_id": actor.id, "shift_type_id": shift_type_id, "is_eligible": True}]},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()[0]["is_eligible"] is True
    created = client.post("/api/v1/shifts", headers=admin_headers, json=payload)
    assert created.status_code == 201, created.text

    actor.participates_in_shifts = False
    database.commit()
    later = {**payload, "starts_at": (start + timedelta(days=1)).isoformat(), "ends_at": (start + timedelta(days=1, hours=8)).isoformat()}
    rejected = client.post("/api/v1/shifts", headers=admin_headers, json=later)
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "SHIFT_EMPLOYEE_NOT_PARTICIPANT"
    picker = client.get("/api/v1/shift-employees", headers=admin_headers)
    assert picker.status_code == 200
    assert actor.id not in {row["id"] for row in picker.json()}


def test_exact_time_availability_reports_eligibility_and_conflict_reason(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    actor = database.scalar(select(User).where(User.username == "admin"))
    assert actor is not None
    actor.participates_in_shifts = True
    database.commit()
    shift_type = client.post("/api/v1/shift-types",headers=admin_headers,json={"name":"Availability night","enforce_employee_eligibility":True})
    assert shift_type.status_code == 201, shift_type.text
    shift_type_id = shift_type.json()["id"]
    eligible = client.put("/api/v1/shift-eligibilities",headers=admin_headers,json={"rows":[{"employee_id":actor.id,"shift_type_id":shift_type_id,"is_eligible":True}]})
    assert eligible.status_code == 200, eligible.text
    starts_at=datetime(2035,6,8,20,tzinfo=UTC);ends_at=starts_at+timedelta(hours=8)
    existing = client.post("/api/v1/shifts",headers=admin_headers,json={"shift_type_id":shift_type_id,"user_id":actor.id,"starts_at":starts_at.isoformat(),"ends_at":ends_at.isoformat()})
    assert existing.status_code == 201, existing.text
    availability = client.get("/api/v1/scheduling/availability",headers=admin_headers,params={"shift_type_id":shift_type_id,"starts_at":starts_at.isoformat(),"ends_at":ends_at.isoformat()})
    assert availability.status_code == 200, availability.text
    actor_row=next(row for row in availability.json() if row["employee_id"]==actor.id)
    assert actor_row["eligible"] is True
    assert actor_row["available"] is False
    assert actor_row["shift_conflict"] is True
    assert actor_row["reason"] == "Overlapping shift"


def test_coverage_slots_track_required_headcount_independently_per_overlapping_slot(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    actor = database.scalar(select(User).where(User.username == "admin"))
    shift_type_id = database.scalar(select(ShiftType.id).where(ShiftType.code == "DAY"))
    assert actor is not None and shift_type_id is not None
    periods = [
        (datetime(2028, 1, 7, 9, tzinfo=UTC), datetime(2028, 1, 7, 17, tzinfo=UTC)),
        (datetime(2028, 1, 7, 14, tzinfo=UTC), datetime(2028, 1, 7, 22, tzinfo=UTC)),
        (datetime(2028, 1, 7, 16, tzinfo=UTC), datetime(2028, 1, 8, 0, tzinfo=UTC)),
    ]
    for starts_at, ends_at in periods:
        created = client.post("/api/v1/shift-coverage-slots", headers=admin_headers, json={
            "shift_type_id": shift_type_id, "starts_at": starts_at.isoformat(), "ends_at": ends_at.isoformat(),
            "timezone": "Africa/Cairo", "required_headcount": 2,
        })
        assert created.status_code == 201, created.text
        assert created.json()["coverage_status"] == "UNASSIGNED"
    assigned = client.post("/api/v1/shifts", headers=admin_headers, json={
        "shift_type_id": shift_type_id, "user_id": actor.id,
        "starts_at": periods[0][0].isoformat(), "ends_at": periods[0][1].isoformat(),
    })
    assert assigned.status_code == 201, assigned.text
    second_employee = database.scalar(select(User).where(User.id != actor.id, User.is_active.in_([True]), User.user_type == "EMPLOYEE"))
    assert second_employee is not None
    second_assignment = client.post("/api/v1/shifts", headers=admin_headers, json={
        "shift_type_id": shift_type_id, "user_id": second_employee.id,
        "starts_at": periods[0][0].isoformat(), "ends_at": periods[0][1].isoformat(),
    })
    assert second_assignment.status_code == 201, second_assignment.text
    overstaffed = client.post("/api/v1/shift-coverage-slots", headers=admin_headers, json={
        "shift_type_id": shift_type_id, "starts_at": periods[0][0].isoformat(), "ends_at": periods[0][1].isoformat(),
        "timezone": "Africa/Cairo", "required_headcount": 1,
    })
    assert overstaffed.status_code == 201, overstaffed.text
    assert overstaffed.json()["coverage_status"] == "OVERSTAFFED"
    listed = client.get("/api/v1/shift-coverage-slots", headers=admin_headers, params={
        "ends_after": "2028-01-07T00:00:00+00:00", "starts_before": "2028-01-08T01:00:00+00:00",
    })
    assert listed.status_code == 200, listed.text
    assert [row["coverage_status"] for row in listed.json()] == ["FULL", "OVERSTAFFED", "UNASSIGNED", "UNASSIGNED"]
    assert [row["assigned_headcount"] for row in listed.json()] == [2, 2, 0, 0]
    summary = client.get("/api/v1/shift-coverage-summary", headers=admin_headers, params={
        "ends_after": "2028-01-07T00:00:00+00:00", "starts_before": "2028-01-08T01:00:00+00:00",
    })
    assert summary.status_code == 200, summary.text
    assert summary.json()[0]["required_positions"] == 7
    assert summary.json()[0]["assigned_positions"] == 4
    assert summary.json()[0]["full_slots"] == 1
    assert summary.json()[0]["overstaffed_slots"] == 1


def test_coverage_slots_can_be_created_empty_and_bulk_deleted_by_selected_ids(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    shift_type_id = database.scalar(select(ShiftType.id).where(ShiftType.code == "DAY"))
    assert shift_type_id is not None
    slot_ids: list[int] = []
    for day in (10, 11):
        response = client.post("/api/v1/shift-coverage-slots", headers=admin_headers, json={
            "shift_type_id": shift_type_id,
            "starts_at": f"2036-02-{day:02d}T09:00:00+00:00",
            "ends_at": f"2036-02-{day:02d}T17:00:00+00:00",
            "timezone": "Africa/Cairo",
            "required_headcount": 2,
        })
        assert response.status_code == 201, response.text
        assert response.json()["assigned_headcount"] == 0
        assert response.json()["coverage_status"] == "UNASSIGNED"
        slot_ids.append(response.json()["id"])
    deleted = client.post("/api/v1/shift-coverage-slots/bulk-delete", headers=admin_headers, json={
        "slot_ids": slot_ids,
        "reason": "Remove test coverage days",
    })
    assert deleted.status_code == 200, deleted.text
    assert deleted.json() == {"deleted": 2}
    remaining = client.get("/api/v1/shift-coverage-slots", headers=admin_headers, params={
        "ends_after": "2036-02-10T00:00:00+00:00",
        "starts_before": "2036-02-12T00:00:00+00:00",
    })
    assert remaining.status_code == 200, remaining.text
    assert remaining.json() == []


def test_rotations_and_multi_slot_recipes_are_reusable_and_effective_dated(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    actor = database.scalar(select(User).where(User.username == "admin"))
    shift_type_id = database.scalar(select(ShiftType.id).where(ShiftType.code == "DAY"))
    assert actor is not None and shift_type_id is not None
    rotation = client.post("/api/v1/assignment-rotations", headers=admin_headers, json={
        "name": "Night Support Rotation", "members": [{"employee_id": actor.id, "is_active": True}],
    })
    assert rotation.status_code == 201, rotation.text
    assert rotation.json()["code"].startswith("ROTATION-NIGHT-SUPPORT-ROTATION")
    recipe = client.post("/api/v1/schedule-recipes", headers=admin_headers, json={
        "name": "Weekend Coverage", "timezone": "Africa/Cairo", "assignment_strategy": "ROTATION",
        "rotation_id": rotation.json()["id"], "effective_from": "2028-01-01", "effective_to": "2028-12-31",
        "rows": [
            {"weekday": 4, "shift_type_id": shift_type_id, "start_time": "09:00:00", "end_time": "17:00:00", "required_headcount": 2, "work_location": "OFFICE"},
            {"weekday": 4, "shift_type_id": shift_type_id, "start_time": "16:00:00", "end_time": "00:00:00", "required_headcount": 2, "work_location": "OFFICE"},
        ],
    })
    assert recipe.status_code == 201, recipe.text
    body = recipe.json()
    assert body["code"].startswith("RECIPE-WEEKEND-COVERAGE")
    assert len(body["rows"]) == 2
    assert body["rows"][1]["crosses_midnight"] is True
    assert body["rows"][0]["required_headcount"] == 2
    listed = client.get("/api/v1/schedule-recipes", headers=admin_headers)
    assert listed.status_code == 200 and listed.json()[0]["effective_to"] == "2028-12-31"
    in_use = client.delete(f"/api/v1/assignment-rotations/{rotation.json()['id']}", headers=admin_headers)
    assert in_use.status_code == 409


def test_rotation_advances_between_dates_instead_of_restarting_at_first_member(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    employees = list(database.scalars(select(User).where(User.is_active.in_([True]), User.user_type == "EMPLOYEE").order_by(User.id).limit(2)))
    shift_type_id = database.scalar(select(ShiftType.id).where(ShiftType.code == "DAY"))
    assert len(employees) == 2 and shift_type_id is not None
    rotation = client.post("/api/v1/assignment-rotations", headers=admin_headers, json={
        "name": "Alternating Day Rotation",
        "members": [{"employee_id": employee.id, "is_active": True} for employee in employees],
    })
    assert rotation.status_code == 201, rotation.text
    request = {
        "rows": [{"weekday": 0, "shift_type_id": shift_type_id, "start_time": "09:00:00", "end_time": "17:00:00", "required_headcount": 1, "work_location": "OFFICE"}],
        "recurrence": {"frequency": "WEEKLY", "date_from": "2032-01-05", "date_to": "2032-01-26", "weekdays": [0]},
        "timezone": "UTC", "assignment_strategy": "ROTATION", "rotation_id": rotation.json()["id"],
    }

    preview = client.post("/api/v1/shifts/generator/preview", headers=admin_headers, json=request)

    assert preview.status_code == 200, preview.text
    assignments = [slot["assigned_user_ids"] for slot in preview.json()["slots"]]
    assert assignments == [[employees[0].id], [employees[1].id], [employees[0].id], [employees[1].id]]


def test_smart_generator_supports_week_five_preview_and_sequential_overlap_assignment(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    employees = list(database.scalars(select(User).where(User.is_active.in_([True]), User.user_type == "EMPLOYEE").limit(2)))
    shift_type_id = database.scalar(select(ShiftType.id).where(ShiftType.code == "DAY"))
    assert len(employees) == 2 and shift_type_id is not None
    request = {
        "rows": [
            {"weekday": 4, "shift_type_id": shift_type_id, "start_time": "09:00:00", "end_time": "17:00:00", "required_headcount": 1, "work_location": "OFFICE"},
            {"weekday": 4, "shift_type_id": shift_type_id, "start_time": "14:00:00", "end_time": "22:00:00", "required_headcount": 1, "work_location": "OFFICE"},
        ],
        "recurrence": {"frequency": "WEEKLY", "date_from": "2028-09-01", "date_to": "2028-09-30", "weekdays": [4]},
        "timezone": "UTC", "assignment_strategy": "AUTO_BALANCE",
    }
    preview = client.post("/api/v1/shifts/generator/preview", headers=admin_headers, json=request)
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["slot_count"] == 10  # Five Fridays, two independent slots each.
    assert body["required_positions"] == 10
    first_day = [slot for slot in body["slots"] if slot["date"] == "2028-09-01"]
    assert len(first_day) == 2
    assert set(first_day[0]["assigned_user_ids"]).isdisjoint(first_day[1]["assigned_user_ids"])
    applied = client.post("/api/v1/shifts/generator/apply", headers=admin_headers, json={"request": request, "preview_hash": body["preview_hash"]})
    assert applied.status_code == 200, applied.text
    assert applied.json()["created_shifts"] == 10
    assert applied.json()["created_coverage_slots"] == 10


def test_smart_generator_supports_fixed_engineers_per_row(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    employees = list(database.scalars(select(User).where(User.is_active.in_([True]), User.user_type == "EMPLOYEE").order_by(User.id).limit(2)))
    shift_type_id = database.scalar(select(ShiftType.id).where(ShiftType.code == "DAY"))
    assert len(employees) == 2 and shift_type_id is not None
    request = {
        "rows": [
            {"weekday": 0, "shift_type_id": shift_type_id, "start_time": "09:00:00", "end_time": "17:00:00", "required_headcount": 1, "assignment_strategy": "FIXED", "fixed_user_ids": [employees[0].id], "work_location": "OFFICE"},
            {"weekday": 0, "shift_type_id": shift_type_id, "start_time": "14:00:00", "end_time": "22:00:00", "required_headcount": 1, "assignment_strategy": "FIXED", "fixed_user_ids": [employees[1].id], "work_location": "WORK_FROM_HOME"},
        ],
        "recurrence": {"frequency": "CUSTOM", "date_from": "2032-01-05", "date_to": "2032-01-05", "weekdays": [0]},
        "timezone": "UTC", "assignment_strategy": "FIXED",
    }
    preview = client.post("/api/v1/shifts/generator/preview", headers=admin_headers, json=request)
    assert preview.status_code == 200, preview.text
    assert [slot["assigned_user_ids"] for slot in preview.json()["slots"]] == [[employees[0].id], [employees[1].id]]


def test_smart_generator_rejects_a_materially_stale_preview(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    actor = database.scalar(select(User).where(User.username == "admin"))
    shift_type_id = database.scalar(select(ShiftType.id).where(ShiftType.code == "DAY"))
    assert actor is not None and shift_type_id is not None
    request = {
        "rows": [{"weekday": 0, "shift_type_id": shift_type_id, "start_time": "09:00:00", "end_time": "17:00:00", "required_headcount": 1, "work_location": "OFFICE"}],
        "recurrence": {"frequency": "ONCE", "date_from": "2029-01-01", "date_to": "2029-01-01"},
        "timezone": "UTC", "assignment_strategy": "AUTO_BALANCE",
    }
    preview = client.post("/api/v1/shifts/generator/preview", headers=admin_headers, json=request)
    assert preview.status_code == 200, preview.text
    competing = client.post("/api/v1/shifts", headers=admin_headers, json={"shift_type_id": shift_type_id, "user_id": actor.id, "starts_at": "2029-01-01T08:00:00+00:00", "ends_at": "2029-01-01T18:00:00+00:00"})
    assert competing.status_code == 201, competing.text
    stale = client.post("/api/v1/shifts/generator/apply", headers=admin_headers, json={"request": request, "preview_hash": preview.json()["preview_hash"]})
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "SCHEDULE_PREVIEW_CHANGED"


def test_shift_week_duplication_preserves_work_location(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    user_id = database.scalar(select(User.id).where(User.username == "admin"))
    shift_type_id = database.scalar(select(ShiftType.id).where(ShiftType.code == "DAY"))
    source = datetime(2026, 8, 10, 8, tzinfo=UTC)
    created = client.post("/api/v1/shifts", headers=admin_headers, json={"shift_type_id": shift_type_id, "user_id": user_id, "starts_at": source.isoformat(), "ends_at": (source + timedelta(hours=8)).isoformat(), "work_location": "WORK_FROM_HOME"})
    assert created.status_code == 201, created.text
    duplicate = client.post("/api/v1/shifts/duplicate-week", headers=admin_headers, json={"source_week_start": datetime(2026, 8, 10, tzinfo=UTC).isoformat(), "target_week_start": datetime(2026, 8, 17, tzinfo=UTC).isoformat(), "skip_conflicts": True})
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json() == {"created": 1, "skipped": 0}
    rows = client.get("/api/v1/shift-calendar", headers=admin_headers, params={"ends_after": datetime(2026, 8, 17, tzinfo=UTC).isoformat(), "starts_before": datetime(2026, 8, 24, tzinfo=UTC).isoformat()})
    assert rows.status_code == 200
    assert rows.json()[0]["work_location"] == "WORK_FROM_HOME"


def test_shift_type_and_department_pattern_masters(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    department_id = database.scalar(select(Department.id))
    if department_id is None:
        department = client.post("/api/v1/departments", headers=admin_headers, json={"code":"W2_SHIFT_DEPT","name":"Wave 2 Shift Department","is_active":True})
        assert department.status_code == 201, department.text
        department_id = department.json()["id"]
    shift_type = client.post("/api/v1/shift-types", headers=admin_headers, json={"code":"W2_NIGHT","name":"Wave 2 Night","description":"Reusable night shift","color":"#123456","display_order":20,"is_active":True})
    assert shift_type.status_code == 201, shift_type.text
    pattern = client.post("/api/v1/shift-patterns", headers=admin_headers, json={"department_id":department_id,"shift_type_id":shift_type.json()["id"],"code":"W2_NIGHT_PATTERN","name":"Night pattern","start_time":"20:00:00","end_time":"08:00:00","crosses_midnight":True,"is_active":True})
    assert pattern.status_code == 201, pattern.text
    rows = client.get("/api/v1/shift-patterns", headers=admin_headers, params={"department_id":department_id})
    assert rows.status_code == 200 and any(item["id"] == pattern.json()["id"] for item in rows.json())
    invalid = client.post("/api/v1/shift-patterns", headers=admin_headers, json={"department_id":department_id,"shift_type_id":shift_type.json()["id"],"code":"BAD_PERIOD","name":"Bad period","start_time":"08:00:00","end_time":"17:00:00","crosses_midnight":True,"is_active":True})
    assert invalid.status_code == 409


def test_shift_master_codes_are_generated_when_omitted(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    department_id = database.scalar(select(Department.id))
    if department_id is None:
        department = client.post("/api/v1/departments", headers=admin_headers, json={"code":"AUTO_CODE_DEPT", "name":"Automatic Code Department", "is_active":True})
        assert department.status_code == 201, department.text
        department_id = department.json()["id"]
    shift_type = client.post("/api/v1/shift-types", headers=admin_headers, json={"name":"Weekend Evening", "color":"#123456"})
    assert shift_type.status_code == 201, shift_type.text
    assert shift_type.json()["code"] == "WEEKEND-EVENING-001"
    pattern = client.post("/api/v1/shift-patterns", headers=admin_headers, json={"department_id":department_id, "shift_type_id":shift_type.json()["id"], "name":"Weekend Evening", "start_time":"14:00:00", "end_time":"22:00:00", "crosses_midnight":False})
    assert pattern.status_code == 201, pattern.text
    assert pattern.json()["code"] == "WEEKEND-EVENING-001"
    assert pattern.json()["default_week_numbers"] == [1, 2, 3, 4]
    assert pattern.json()["default_weekdays"] == [6, 0, 1, 2, 3, 4]
    edited = client.patch(f"/api/v1/shift-patterns/{pattern.json()['id']}", headers=admin_headers, json={"department_id":department_id, "shift_type_id":shift_type.json()["id"], "name":"Weekend Evening Updated", "start_time":"14:00:00", "end_time":"22:00:00", "default_week_numbers":[1,3], "default_weekdays":[4,5], "week_start_day":4})
    assert edited.status_code == 200, edited.text
    assert edited.json()["default_week_numbers"] == [1, 3]
    assert edited.json()["default_weekdays"] == [4, 5]
    deleted = client.delete(f"/api/v1/shift-patterns/{pattern.json()['id']}", headers=admin_headers)
    assert deleted.status_code == 204


def test_bulk_delete_previews_and_deletes_engineer_range(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    user_id = database.scalar(select(User.id).where(User.username == "admin"))
    shift_type_id = database.scalar(select(ShiftType.id).where(ShiftType.code == "DAY"))
    for day in (3, 4, 5):
        start = datetime(2026, 9, day, 8, tzinfo=UTC)
        response = client.post("/api/v1/shifts", headers=admin_headers, json={"shift_type_id":shift_type_id, "user_id":user_id, "starts_at":start.isoformat(), "ends_at":(start+timedelta(hours=8)).isoformat()})
        assert response.status_code == 201, response.text
    selection = {"user_id":user_id, "starts_at":"2026-09-01T00:00:00+00:00", "ends_at":"2026-10-01T00:00:00+00:00", "shift_type_id":shift_type_id}
    preview = client.post("/api/v1/shifts/bulk-delete/preview", headers=admin_headers, json=selection)
    assert preview.status_code == 200 and preview.json()["deletable"] == 3
    deleted = client.post("/api/v1/shifts/bulk-delete", headers=admin_headers, json={**selection, "expected_count":3, "reason":"Remove the engineer monthly roster."})
    assert deleted.status_code == 200 and deleted.json() == {"deleted":3, "protected":0}
    assert client.post("/api/v1/shifts/bulk-delete/preview", headers=admin_headers, json=selection).json()["matched"] == 0


def test_template_weeks_start_at_first_configured_weekday_in_month(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    department = Department(code="SUNDAY_WEEK", name="Sunday Week Department", is_active=True)
    actor = database.scalar(select(User).where(User.username == "admin"))
    actor.department = department.name
    database.add(department); database.commit()
    shift_type_id = database.scalar(select(ShiftType.id).where(ShiftType.code == "DAY"))
    pattern = client.post("/api/v1/shift-patterns", headers=admin_headers, json={"department_id":department.id, "shift_type_id":shift_type_id, "name":"Sunday anchored weeks", "start_time":"16:00:00", "end_time":"23:00:00"})
    assert pattern.status_code == 201, pattern.text
    applied = client.post(f"/api/v1/shift-patterns/{pattern.json()['id']}/apply-month", headers=admin_headers, json={"month":"2026-09-01", "week_numbers":[1,2,3,4], "weekdays":[6], "week_start_day":6, "user_ids":[actor.id], "timezone":"Africa/Cairo", "work_location":"OFFICE"})
    assert applied.status_code == 200, applied.text
    assert applied.json()["dates"] == ["2026-09-06", "2026-09-13", "2026-09-20", "2026-09-27"]


def test_template_supports_specific_dates_and_filtered_date_ranges(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    department = Department(code="FLEX_DATES", name="Flexible Dates Department", is_active=True)
    actor = database.scalar(select(User).where(User.username == "admin"))
    assert actor is not None
    actor.department = department.name
    database.add(department)
    database.commit()
    shift_type_id = database.scalar(select(ShiftType.id).where(ShiftType.code == "DAY"))
    pattern = client.post(
        "/api/v1/shift-patterns",
        headers=admin_headers,
        json={
            "department_id": department.id,
            "shift_type_id": shift_type_id,
            "name": "Flexible date selection",
            "start_time": "08:00:00",
            "end_time": "16:00:00",
        },
    )
    assert pattern.status_code == 201, pattern.text
    endpoint = f"/api/v1/shift-patterns/{pattern.json()['id']}/apply"
    common = {
        "user_ids": [actor.id],
        "timezone": "Africa/Cairo",
        "work_location": "OFFICE",
    }

    specific = client.post(
        endpoint,
        headers=admin_headers,
        json={
            **common,
            "selection_mode": "SPECIFIC_DATES",
            "specific_dates": ["2026-09-05", "2026-09-02", "2026-09-05"],
        },
    )
    assert specific.status_code == 200, specific.text
    assert specific.json()["dates"] == ["2026-09-02", "2026-09-05"]
    assert specific.json()["created"] == 2

    date_range = client.post(
        endpoint,
        headers=admin_headers,
        json={
            **common,
            "selection_mode": "DATE_RANGE",
            "date_from": "2026-09-07",
            "date_to": "2026-09-13",
            "weekdays": [0, 2],
        },
    )
    assert date_range.status_code == 200, date_range.text
    assert date_range.json()["dates"] == ["2026-09-07", "2026-09-09"]
    assert date_range.json()["created"] == 2


def test_template_rejects_invalid_or_empty_date_ranges(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    department = Department(code="EMPTY_DATES", name="Empty Dates Department", is_active=True)
    actor = database.scalar(select(User).where(User.username == "admin"))
    assert actor is not None
    actor.department = department.name
    database.add(department)
    database.commit()
    shift_type_id = database.scalar(select(ShiftType.id).where(ShiftType.code == "DAY"))
    pattern = client.post(
        "/api/v1/shift-patterns",
        headers=admin_headers,
        json={
            "department_id": department.id,
            "shift_type_id": shift_type_id,
            "name": "Empty selection validation",
            "start_time": "08:00:00",
            "end_time": "16:00:00",
        },
    )
    endpoint = f"/api/v1/shift-patterns/{pattern.json()['id']}/apply"
    invalid = client.post(
        endpoint,
        headers=admin_headers,
        json={
            "selection_mode": "DATE_RANGE",
            "date_from": "2026-09-10",
            "date_to": "2026-09-01",
            "weekdays": [0],
            "user_ids": [actor.id],
        },
    )
    assert invalid.status_code == 422


def test_unused_shift_type_can_be_edited_and_deleted(client:TestClient,admin_headers:dict[str,str])->None:
    created=client.post("/api/v1/shift-types",headers=admin_headers,json={"name":"Temporary coverage","color":"#445566"})
    assert created.status_code==201,created.text
    edited=client.patch(f"/api/v1/shift-types/{created.json()['id']}",headers=admin_headers,json={"name":"Temporary coverage updated","color":"#445566"})
    assert edited.status_code==200 and edited.json()["code"]==created.json()["code"]
    assert client.delete(f"/api/v1/shift-types/{created.json()['id']}",headers=admin_headers).status_code==204


def test_weekly_roster_template_supports_day_specific_engineers_and_editing(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    department = Department(code="ROSTER_DEPT", name="Roster Department", is_active=True)
    users = list(database.scalars(select(User).where(User.is_active.in_([True])).limit(2)))
    assert len(users) == 2
    for user in users: user.department = department.name
    database.add(department); database.commit()
    shift_type_id = database.scalar(select(ShiftType.id).where(ShiftType.code == "DAY"))
    payload = {"department_id":department.id,"name":"Weekly WFH roster","week_start_day":6,"rows":[
        {"shift_type_id":shift_type_id,"weekday":6,"week_numbers":[1,2,3,4],"start_time":"09:00:00","end_time":"17:00:00","work_location":"WORK_FROM_HOME","user_ids":[users[0].id]},
        {"shift_type_id":shift_type_id,"weekday":1,"week_numbers":[1,2,3,4],"start_time":"09:00:00","end_time":"17:00:00","work_location":"WORK_FROM_HOME","user_ids":[users[1].id]},
    ]}
    created = client.post("/api/v1/shift-roster-templates", headers=admin_headers, json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["code"].startswith("ROSTER-WEEKLY-WFH-ROSTER")
    payload["name"] = "Weekly WFH roster updated"
    payload["rows"][0]["user_ids"] = [users[0].id, users[1].id]
    edited = client.patch(f"/api/v1/shift-roster-templates/{created.json()['id']}", headers=admin_headers, json=payload)
    assert edited.status_code == 200, edited.text
    assert edited.json()["code"] == created.json()["code"] and len(edited.json()["rows"][0]["user_ids"]) == 2
    applied = client.post(f"/api/v1/shift-roster-templates/{created.json()['id']}/apply-month", headers=admin_headers, json={"month":"2026-09-01","timezone":"Africa/Cairo","skip_conflicts":True})
    assert applied.status_code == 200, applied.text
    assert applied.json()["created"] == 12


def test_reusable_roster_accepts_empty_users_and_applies_an_inclusive_date_range(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    department = Department(code="REUSABLE_ROSTER", name="Reusable Roster", is_active=True)
    user = database.scalar(select(User).where(User.is_active.in_([True])))
    assert user is not None
    user.department = department.name
    database.add(department); database.commit()
    shift_type_id = database.scalar(select(ShiftType.id).where(ShiftType.code == "DAY"))
    created = client.post("/api/v1/shift-roster-templates", headers=admin_headers, json={
        "department_id": department.id,
        "name": "Reusable coverage",
        "week_start_day": 6,
        "rows": [{
            "shift_type_id": shift_type_id,
            "weekday": 0,
            "week_numbers": [1, 2, 3, 4],
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "work_location": "OFFICE",
            "user_ids": [],
        }],
    })
    assert created.status_code == 201, created.text
    applied = client.post(f"/api/v1/shift-roster-templates/{created.json()['id']}/apply-month", headers=admin_headers, json={
        "date_from": "2027-09-01",
        "date_to": "2027-09-14",
        "user_ids": [user.id],
        "timezone": "Africa/Cairo",
        "skip_conflicts": True,
    })
    assert applied.status_code == 200, applied.text
    assert applied.json()["created"] == 2
    assert applied.json()["dates"] == ["2027-09-06", "2027-09-13"]
