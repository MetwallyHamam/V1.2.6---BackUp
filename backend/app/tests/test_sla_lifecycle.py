from datetime import UTC, date, datetime, time, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.modules.clients.models import ClientStatus
from app.modules.configuration.models import FeaturePolicy, SiteSetting
from app.modules.contracts.models import (
    BusinessCalendar,
    SlaPolicy,
    SlaShadowComparison,
    TicketSlaClock,
    TicketSlaInterval,
)
from app.modules.contracts.service import (
    add_working_minutes,
    calculate_working_minutes,
    working_minutes_between,
)
from app.modules.iam.models import AuditLog, User
from app.modules.sla.service import resolution_sla_result, resolution_sla_results
from app.modules.tickets.models import (
    Ticket,
    TicketAssignmentHistory,
    TicketResolutionHistory,
    TicketType,
)


def create_sla_ticket(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> dict[str, object]:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    customer = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "SLA-LIFE", "name": "SLA Lifecycle", "status_id": status_id},
    ).json()
    service = client.post(
        "/api/v1/services",
        headers=admin_headers,
        json={"code": "SLA-SERVICE", "name": "SLA Service"},
    ).json()
    calendar_id = database.scalar(select(BusinessCalendar.id))
    contract = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "SUP-SLA-LIFECYCLE",
            "client_id": customer["id"],
            "name": "Lifecycle SLA Contract",
            "start_date": str(date.today() - timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=30)),
            "calendar_id": calendar_id,
        },
    ).json()
    coverage = client.post(
        f"/api/v1/contracts/{contract['id']}/coverage",
        headers=admin_headers,
        json={"service_id": service["id"], "is_covered": True},
    )
    assert coverage.status_code == 201, coverage.text
    policy = client.put(
        f"/api/v1/contracts/{contract['id']}/sla",
        headers=admin_headers,
        json={"name": "Service SLA", "calendar_id": calendar_id, "is_active": True},
    )
    assert policy.status_code == 200, policy.text
    target = client.post(
        f"/api/v1/contracts/{contract['id']}/sla/targets",
        headers=admin_headers,
        json={
            "service_id": service["id"],
            "priority": "P3",
            "first_response_minutes": 30,
            "resolution_minutes": 120,
            "warning_percent": 60,
        },
    )
    assert target.status_code == 201, target.text
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": customer["id"],
            "service_id": service["id"],
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "Service-specific SLA lifecycle",
            "description": "Verify response, resolution, warning, completion, and reopen behavior.",
        },
    )
    assert ticket.status_code == 201, ticket.text
    return ticket.json()


def test_shadow_mode_persists_comparison_evidence(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    actor_id = database.scalar(select(User.id).where(User.username == "admin"))
    database.add(
        FeaturePolicy(
            feature_key="product_scoped_sla",
            scope_type="SYSTEM",
            scope_key="SYSTEM",
            mode="SHADOW",
            configuration_json="{}",
            effective_from=server_now() - timedelta(minutes=1),
            version=1,
            created_by_user_id=actor_id,
            updated_by_user_id=actor_id,
        )
    )
    database.commit()
    ticket = create_sla_ticket(client, admin_headers, database)
    comparison = database.scalar(
        select(SlaShadowComparison).where(SlaShadowComparison.ticket_id == ticket["id"])
    )
    assert comparison is not None
    assert comparison.outcome == "SAME"
    assert comparison.legacy_target_id == comparison.governed_target_id
    response = client.get(
        f"/api/v1/tickets/{ticket['id']}/sla/shadow-comparison",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["governed_match_reason"] == "CONTRACT_SERVICE_DEFAULT"


def test_service_priority_sla_completes_and_restarts_with_ticket_workflow(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    ticket = create_sla_ticket(client, admin_headers, database)
    clocks = list(
        database.scalars(select(TicketSlaClock).where(TicketSlaClock.ticket_id == ticket["id"]))
    )
    assert {clock.clock_type: clock.target_minutes for clock in clocks} == {
        "FIRST_RESPONSE": 30,
        "RESOLUTION": 120,
    }
    assert {clock.warning_percent for clock in clocks} == {60}
    visible_clocks = client.get(f"/api/v1/tickets/{ticket['id']}/sla", headers=admin_headers)
    assert visible_clocks.status_code == 200, visible_clocks.text
    assert {item["warning_percent"] for item in visible_clocks.json()} == {60}
    assert all(item["completed_at"] is None for item in visible_clocks.json())
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    assert admin_id is not None
    assigned = client.post(
        f"/api/v1/tickets/{ticket['id']}/assignment",
        headers=admin_headers,
        json={
            "assigned_user_id": admin_id,
            "assigned_team": "Support",
            "version": ticket["version"],
        },
    )
    assert assigned.status_code == 200, assigned.text
    response = client.post(
        f"/api/v1/tickets/{ticket['id']}/comments",
        headers=admin_headers,
        json={"body": "Support is investigating.", "is_internal": False},
    )
    assert response.status_code == 201, response.text
    started = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        headers=admin_headers,
        json={"to_status_code": "IN_PROGRESS", "version": assigned.json()["version"] + 1},
    )
    assert started.status_code == 200, started.text
    database.expire_all()
    response_clock = database.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket["id"],
            TicketSlaClock.clock_type == "FIRST_RESPONSE",
        )
    )
    resolution_clock = database.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket["id"],
            TicketSlaClock.clock_type == "RESOLUTION",
        )
    )
    assert response_clock is not None and response_clock.state == "COMPLETED"
    assert response_clock.completed_at is not None
    assert response_clock.actual_response_minutes is not None
    assert resolution_clock is not None and resolution_clock.state == "RUNNING"
    original_resolution_due = resolution_clock.due_at
    resolved = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "RESOLVED",
            "version": started.json()["version"],
            "close_after_resolve": True,
            "resolution_summary": "The service issue was corrected and verified.",
            "root_cause_summary": "A service configuration mismatch caused the incident.",
        },
    )
    assert resolved.status_code == 200, resolved.text
    database.expire_all()
    resolution_clock = database.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket["id"],
            TicketSlaClock.clock_type == "RESOLUTION",
        )
    )
    assert resolution_clock is not None and resolution_clock.state == "COMPLETED"
    assert resolution_clock.completed_at is not None
    assert resolution_clock.accountable_minutes is not None
    assert resolution_clock.customer_pending_minutes is not None
    assert resolution_clock.millensys_pending_minutes is not None
    assert resolution_clock.escalation_minutes is not None
    assert resolution_clock.saved_minutes is not None
    assert resolution_clock.overrun_minutes is not None
    assert resolution_clock.outcome_calculated_at is not None
    completed_ticket = database.get(Ticket, ticket["id"])
    assert completed_ticket is not None
    snapshotted_result = resolution_sla_results(database, [completed_ticket])[ticket["id"]]
    assert snapshotted_result.accountable_minutes == resolution_clock.accountable_minutes
    assert snapshotted_result.saved_minutes == resolution_clock.saved_minutes
    reopened = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "REOPENED",
            "version": resolved.json()["version"],
            "reason": "The customer reproduced the service issue after closure.",
        },
    )
    assert reopened.status_code == 200, reopened.text
    database.expire_all()
    resolution_clock = database.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket["id"],
            TicketSlaClock.clock_type == "RESOLUTION",
        )
    )
    assert resolution_clock is not None and resolution_clock.state == "RUNNING"
    assert resolution_clock.completed_at is None
    assert resolution_clock.breached_at is None
    assert resolution_clock.due_at >= original_resolution_due
    assert resolution_clock.accountable_minutes is None
    assert resolution_clock.customer_pending_minutes is None
    assert resolution_clock.millensys_pending_minutes is None
    assert resolution_clock.escalation_minutes is None
    assert resolution_clock.saved_minutes is None
    assert resolution_clock.overrun_minutes is None
    assert resolution_clock.outcome_calculated_at is None
    reopened_ticket = database.get(Ticket, ticket["id"])
    assert reopened_ticket is not None
    assert reopened_ticket.resolution_summary is None
    assert reopened_ticket.root_cause_summary is None
    history = database.scalar(
        select(TicketResolutionHistory).where(TicketResolutionHistory.ticket_id == ticket["id"])
    )
    assert history is not None
    assert history.resolution_sequence == 1
    assert history.resolution_summary == "The service issue was corrected and verified."
    assert history.sla_snapshot_json is not None
    visible_history = client.get(
        f"/api/v1/tickets/{ticket['id']}/resolution-history", headers=admin_headers
    )
    assert visible_history.status_code == 200, visible_history.text
    assert visible_history.json()[0]["resolution_sequence"] == 1


def test_resolution_clock_stops_at_resolved_and_close_does_not_extend_it(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    ticket = create_sla_ticket(client, admin_headers, database)
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    assigned = client.post(
        f"/api/v1/tickets/{ticket['id']}/assignment",
        headers=admin_headers,
        json={
            "assigned_user_id": admin_id,
            "assigned_team": "Support",
            "version": ticket["version"],
        },
    )
    assert assigned.status_code == 200, assigned.text
    started = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        headers=admin_headers,
        json={"to_status_code": "IN_PROGRESS", "version": assigned.json()["version"]},
    )
    assert started.status_code == 200, started.text
    resolved = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "RESOLVED",
            "version": started.json()["version"],
            "resolution_summary": "The incident was resolved by the assigned engineer.",
            "root_cause_summary": "The service configuration required correction.",
        },
    )
    assert resolved.status_code == 200, resolved.text
    database.expire_all()
    clock = database.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket["id"],
            TicketSlaClock.clock_type == "RESOLUTION",
        )
    )
    assert clock is not None
    assert clock.state in {"COMPLETED", "BREACHED"}
    assert clock.completed_at is not None
    resolved_completion = clock.completed_at
    closed = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        headers=admin_headers,
        json={"to_status_code": "CLOSED", "version": resolved.json()["version"]},
    )
    assert closed.status_code == 200, closed.text
    database.expire_all()
    assert clock.completed_at == resolved_completion


def test_resolution_clock_stops_when_an_active_ticket_is_cancelled(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    ticket = create_sla_ticket(client, admin_headers, database)
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    assert admin_id is not None
    assigned = client.post(
        f"/api/v1/tickets/{ticket['id']}/assignment",
        headers=admin_headers,
        json={
            "assigned_user_id": admin_id,
            "assigned_team": "Support",
            "version": ticket["version"],
        },
    )
    assert assigned.status_code == 200, assigned.text
    started = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        headers=admin_headers,
        json={"to_status_code": "IN_PROGRESS", "version": assigned.json()["version"]},
    )
    assert started.status_code == 200, started.text
    cancelled = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "CANCELLED",
            "reason": "The customer withdrew the request before resolution.",
            "version": started.json()["version"],
        },
    )
    assert cancelled.status_code == 200, cancelled.text
    clock = database.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket["id"],
            TicketSlaClock.clock_type == "RESOLUTION",
        )
    )
    assert clock is not None
    assert clock.state in {"COMPLETED", "BREACHED"}
    assert clock.completed_at is not None


def test_public_employee_comment_completes_created_at_first_response_clock(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    ticket = create_sla_ticket(client, admin_headers, database)
    comment = client.post(
        f"/api/v1/tickets/{ticket['id']}/comments",
        headers=admin_headers,
        json={"body": "Support has started investigating this request.", "is_internal": False},
    )
    assert comment.status_code == 201, comment.text
    database.expire_all()
    response_clock = database.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket["id"],
            TicketSlaClock.clock_type == "FIRST_RESPONSE",
        )
    )
    resolution_clock = database.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket["id"],
            TicketSlaClock.clock_type == "RESOLUTION",
        )
    )
    assert response_clock is not None and response_clock.state == "COMPLETED"
    assert response_clock.completed_at is not None
    assert response_clock.actual_response_minutes is not None
    assert response_clock.start_mode_snapshot == "TICKET_CREATED"
    assert response_clock.start_anchor_at is not None
    assert resolution_clock is not None and resolution_clock.state == "PAUSED"


def test_assignment_start_mode_pauses_until_assignment_and_response(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    database.add(SiteSetting(key="first_response_start_mode", value="FIRST_DEDICATED_ASSIGNMENT"))
    database.commit()
    ticket = create_sla_ticket(client, admin_headers, database)
    response_clock = database.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket["id"],
            TicketSlaClock.clock_type == "FIRST_RESPONSE",
        )
    )
    assert response_clock is not None
    assert response_clock.state == "PAUSED"
    assert response_clock.start_anchor_at is None
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    assigned = client.post(
        f"/api/v1/tickets/{ticket['id']}/assignment",
        headers=admin_headers,
        json={
            "assigned_user_id": admin_id,
            "assigned_team": "Support",
            "version": ticket["version"],
        },
    )
    assert assigned.status_code == 200, assigned.text
    database.expire_all()
    response_clock = database.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket["id"],
            TicketSlaClock.clock_type == "FIRST_RESPONSE",
        )
    )
    assert response_clock is not None
    assert response_clock.state == "RUNNING"
    assert response_clock.start_anchor_at is not None
    comment = client.post(
        f"/api/v1/tickets/{ticket['id']}/comments",
        headers=admin_headers,
        json={"body": "We are actively investigating.", "is_internal": False},
    )
    assert comment.status_code == 201, comment.text
    database.expire_all()
    assert response_clock.state == "COMPLETED"
    assert response_clock.completed_at is not None


def test_pending_client_defaults_to_customer_and_rejects_mismatch(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    ticket = create_sla_ticket(client, admin_headers, database)
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    assigned = client.post(
        f"/api/v1/tickets/{ticket['id']}/assignment",
        headers=admin_headers,
        json={
            "assigned_user_id": admin_id,
            "assigned_team": "Support",
            "version": ticket["version"],
        },
    )
    assert assigned.status_code == 200, assigned.text
    mismatch = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "PENDING_CLIENT",
            "reason": "Waiting for customer evidence.",
            "pending_follow_up_at": (server_now() + timedelta(days=1)).isoformat(),
            "pending_responsible_party": "MILLENSYS",
            "version": assigned.json()["version"],
        },
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "PENDING_RESPONSIBLE_PARTY_MISMATCH"
    pending = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "PENDING_CLIENT",
            "reason": "Waiting for customer evidence.",
            "pending_follow_up_at": (server_now() + timedelta(days=1)).isoformat(),
            "version": assigned.json()["version"],
        },
    )
    assert pending.status_code == 200, pending.text
    interval = database.scalar(
        select(TicketSlaInterval).where(
            TicketSlaInterval.ticket_id == ticket["id"],
            TicketSlaInterval.interval_type == "PENDING",
        )
    )
    assert interval is not None
    assert interval.responsible_party == "CUSTOMER"


def test_material_edit_cannot_leave_sla_clock_stale(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    ticket = create_sla_ticket(client, admin_headers, database)
    target = client.post(
        f"/api/v1/contracts/{ticket['contract_id']}/sla/targets",
        headers=admin_headers,
        json={
            "service_id": ticket["service_id"],
            "priority": "P2",
            "first_response_minutes": 15,
            "resolution_minutes": 60,
            "warning_percent": 60,
        },
    )
    assert target.status_code == 201, target.text
    old_resolution = database.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket["id"],
            TicketSlaClock.clock_type == "RESOLUTION",
        )
    )
    assert old_resolution is not None
    old_target_id = old_resolution.target_id
    old_started_at = old_resolution.started_at
    preview = client.post(
        f"/api/v1/tickets/{ticket['id']}/sla-preview",
        headers=admin_headers,
        json={"priority": "P2", "version": ticket["version"]},
    )
    assert preview.status_code == 200, preview.text
    preview_data = preview.json()
    assert preview_data["version"] == ticket["version"]
    assert preview_data["changes_sla"] is True
    assert preview_data["changed_fields"] == ["priority"]
    assert preview_data["old_target_id"] == old_target_id
    assert preview_data["new_target_id"] == target.json()["id"]
    assert preview_data["old_resolution_minutes"] == 120
    assert preview_data["new_resolution_minutes"] == 60
    missing_reason = client.patch(
        f"/api/v1/tickets/{ticket['id']}",
        headers=admin_headers,
        json={"priority": "P2", "reason": "Priority corrected", "version": ticket["version"]},
    )
    assert missing_reason.status_code == 409
    assert missing_reason.json()["error"]["code"] == "SLA_REEVALUATION_REASON_REQUIRED"
    reevaluated = client.patch(
        f"/api/v1/tickets/{ticket['id']}",
        headers=admin_headers,
        json={
            "priority": "P2",
            "reason": "Priority corrected",
            "sla_reevaluation_reason": "Customer confirmed the production impact.",
            "version": ticket["version"],
        },
    )
    assert reevaluated.status_code == 200, reevaluated.text
    database.expire_all()
    assert database.get(Ticket, ticket["id"]).priority == "P2"
    resolution = database.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == ticket["id"],
            TicketSlaClock.clock_type == "RESOLUTION",
        )
    )
    assert resolution is not None
    assert resolution.target_id == target.json()["id"]
    assert resolution.target_id != old_target_id
    assert resolution.target_minutes == 60
    assert resolution.started_at >= old_started_at
    audit = database.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "TicketSla",
            AuditLog.entity_id == str(ticket["id"]),
            AuditLog.action == "ticket.sla.reevaluated",
        )
    )
    assert audit is not None
    assert audit.reason == "Customer confirmed the production impact."
    assert str(old_target_id) in (audit.old_values_json or "")


def test_sla_rejects_resolution_duration_shorter_than_response(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    ticket = create_sla_ticket(client, admin_headers, database)
    assert ticket["id"]
    invalid = client.post(
        "/api/v1/contracts/1/sla/targets",
        headers=admin_headers,
        json={
            "priority": "P2",
            "first_response_minutes": 120,
            "resolution_minutes": 30,
            "warning_percent": 75,
        },
    )
    assert invalid.status_code == 422


def test_completed_sla_clocks_do_not_become_false_breaches(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    ticket = create_sla_ticket(client, admin_headers, database)
    completed_at = server_now() - timedelta(days=2)
    clocks = list(
        database.scalars(select(TicketSlaClock).where(TicketSlaClock.ticket_id == ticket["id"]))
    )
    for clock in clocks:
        clock.state = "COMPLETED"
        clock.completed_at = completed_at
        clock.due_at = server_now() - timedelta(days=1)
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    assert admin_id is not None
    row = database.get(Ticket, ticket["id"])
    assert row is not None
    row.closed_at = completed_at
    database.add(
        TicketAssignmentHistory(
            ticket_id=ticket["id"],
            assigned_user_id=admin_id,
            assigned_team="Support",
            assigned_by_user_id=admin_id,
            created_at=completed_at - timedelta(minutes=10),
        )
    )
    row.closed_at = None
    database.commit()

    evidence = resolution_sla_result(database, row, as_of=server_now())
    assert evidence is not None
    assert evidence.completed_at == completed_at

    dashboard = client.get("/api/v1/dashboards/summary", headers=admin_headers)
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["breached"] == 0
    assert dashboard.json()["sla_compliance_percent"] == 100.0
    listing = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"breached_only": "true"},
    )
    assert listing.status_code == 200, listing.text
    assert all(item["id"] != ticket["id"] for item in listing.json())


def test_working_minutes_exclude_nights_and_weekends(database: Session) -> None:
    calendar = database.scalar(select(BusinessCalendar))
    assert calendar is not None
    # Sunday and Monday are working days in the seeded Cairo calendar.
    start = datetime.combine(date(2026, 8, 9), time(16), tzinfo=UTC)
    end = datetime.combine(date(2026, 8, 10), time(7), tzinfo=UTC)
    assert calculate_working_minutes(database, calendar.id, start, end) == 120


def test_working_minutes_supports_historical_tickets_beyond_one_year() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2025, 1, 6, tzinfo=UTC)
    schedule = {weekday: (time(9), time(17)) for weekday in range(7)}

    assert working_minutes_between(start, end, "UTC", schedule, set()) > 0


def test_midnight_end_time_delays_after_hours_sla_start() -> None:
    schedules = {6: (time(8), time(0)), 0: (time(8), time(0))}
    before_hours = datetime(2026, 8, 9, 2, tzinfo=UTC)
    assert add_working_minutes(before_hours, 60, "UTC", schedules, set()) == datetime(
        2026, 8, 9, 9, tzinfo=UTC
    )
    near_midnight = datetime(2026, 8, 9, 23, 30, tzinfo=UTC)
    assert add_working_minutes(near_midnight, 60, "UTC", schedules, set()) == datetime(
        2026, 8, 10, 8, 30, tzinfo=UTC
    )


def test_calendar_schedule_can_use_midnight_as_end_of_day(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    calendar = database.scalar(select(BusinessCalendar))
    assert calendar is not None
    response = client.put(
        f"/api/v1/business-calendars/{calendar.id}/schedule",
        headers=admin_headers,
        json={
            "timezone": "Africa/Cairo",
            "days": [
                {
                    "weekday": weekday,
                    "start_time": "08:00",
                    "end_time": "00:00",
                    "is_working_day": weekday < 5,
                }
                for weekday in range(7)
            ],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["days"][0]["end_time"] == "00:00:00"


def test_accountable_sla_excludes_customer_pending_and_optionally_escalation(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    created = create_sla_ticket(client, admin_headers, database)
    ticket = database.get(Ticket, created["id"])
    clock = database.scalar(
        select(TicketSlaClock).where(
            TicketSlaClock.ticket_id == created["id"], TicketSlaClock.clock_type == "RESOLUTION"
        )
    )
    assert ticket is not None and clock is not None
    policy = database.get(SlaPolicy, clock.policy_id)
    actor_id = database.scalar(select(User.id).where(User.username == "admin"))
    assert policy is not None and actor_id is not None
    start = datetime(2026, 8, 9, 5, tzinfo=UTC)
    end = datetime(2026, 8, 9, 12, tzinfo=UTC)
    ticket.closed_at = end
    clock.completed_at = end
    clock.target_minutes = 600
    database.add_all(
        [
            TicketAssignmentHistory(
                ticket_id=ticket.id,
                assigned_user_id=actor_id,
                assigned_team="Support",
                assigned_by_user_id=actor_id,
                created_at=start,
            ),
            TicketSlaInterval(
                ticket_id=ticket.id,
                interval_type="PENDING",
                responsible_party="CUSTOMER",
                comment="Waiting for client evidence",
                started_at=start + timedelta(hours=1),
                ended_at=start + timedelta(hours=2),
                created_by_user_id=actor_id,
            ),
            TicketSlaInterval(
                ticket_id=ticket.id,
                interval_type="PENDING",
                responsible_party="MILLENSYS",
                comment="Internal investigation",
                started_at=start + timedelta(hours=2),
                ended_at=start + timedelta(hours=3),
                created_by_user_id=actor_id,
            ),
            TicketSlaInterval(
                ticket_id=ticket.id,
                interval_type="ESCALATION",
                comment="Specialist review",
                started_at=start + timedelta(hours=4),
                ended_at=start + timedelta(hours=5),
                created_by_user_id=actor_id,
            ),
        ]
    )
    database.commit()
    gross = calculate_working_minutes(database, policy.calendar_id, start, end)
    policy.include_escalation_time = True
    included = resolution_sla_result(database, ticket)
    assert included is not None
    assert included.accountable_minutes == gross - included.customer_pending_minutes
    assert included.millensys_pending_minutes > 0
    policy.include_escalation_time = False
    excluded = resolution_sla_result(database, ticket)
    assert excluded is not None
    assert (
        excluded.accountable_minutes == included.accountable_minutes - excluded.escalation_minutes
    )
    assert resolution_sla_results(database, [ticket])[ticket.id] == excluded
    clock.target_minutes = 1
    overrun = resolution_sla_result(database, ticket)
    assert overrun is not None
    assert overrun.saved_minutes < 0
    assert overrun.target_minutes == 1
    assert overrun.overrun_minutes == overrun.accountable_minutes - overrun.target_minutes
