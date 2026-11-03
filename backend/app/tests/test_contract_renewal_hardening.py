import json
from datetime import date, datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_now, server_timezone, server_today
from app.core.config import Settings
from app.modules.configuration.models import SiteSetting
from app.modules.contracts.access import can_receive_renewal
from app.modules.contracts.lifecycle import process_contract_lifecycle
from app.modules.contracts.models import (
    BusinessCalendar,
    Contract,
    ContractCoverage,
    ContractCoverageRevision,
    ContractExpirationNotificationDelivery,
    ContractRenewalTask,
    SlaPolicy,
    TicketSlaClock,
)
from app.modules.contracts.routes import update_calendar_schedule
from app.modules.contracts.schemas import CalendarDayWrite, CalendarScheduleWrite
from app.modules.contracts.service import calculate_due_at, evaluate_entitlement
from app.modules.iam.models import User, UserProfile
from app.modules.notifications.email_service import process_email_outbox
from app.modules.notifications.models import EventOutbox, Notification
from app.modules.tickets.models import Ticket, TicketStatus, TicketType
from app.tests.test_coverage_renewals import _contract_data, _coverage


def renewal_fixture(client: TestClient, admin_headers: dict[str, str], database: Session):  # type: ignore[no-untyped-def]
    contract, service, owner = _contract_data(database)
    contract.end_date = server_today() + timedelta(days=30)
    contract.start_date = server_today() - timedelta(days=30)
    source = ContractCoverage(contract_id=contract.id, service_id=service.id, is_covered=True)
    successor = Contract(
        contract_number="SUCCESSOR",
        client_id=contract.client_id,
        name="Next term",
        start_date=contract.end_date + timedelta(days=1),
        end_date=contract.end_date + timedelta(days=365),
        status="DRAFT",
        is_active=True,
        has_sla=False,
        calendar_id=contract.calendar_id,
    )
    database.add_all([source, successor])
    database.flush()
    target = ContractCoverage(contract_id=successor.id, service_id=service.id, is_covered=True)
    database.add(target)
    database.commit()
    created = client.post(
        f"/api/v1/contracts/{contract.id}/renewal-opportunities",
        headers=admin_headers,
        json={
            "idempotency_key": "renewal-hardening-001",
            "owner_user_id": owner.id,
            "target_close_date": str(server_today()),
            "reason": "Prepare the next term",
            "lines": [{"coverage_id": source.id, "outcome": "PENDING"}],
        },
    )
    assert created.status_code == 201, created.text
    payload = {
        "stage": "CLOSED",
        "outcome": "RENEWED",
        "successor_contract_id": successor.id,
        "reason": "Signed successor contract",
        "version": 1,
        "lines": [
            {"coverage_id": source.id, "outcome": "RENEWED", "successor_coverage_id": target.id}
        ],
    }
    return contract, successor, source, target, owner, created.json()["id"], payload


@pytest.mark.parametrize(
    "case",
    [
        "missing_successor",
        "unknown_successor",
        "overlap",
        "inactive",
        "missing_sla",
        "pending",
        "missing_mapping",
        "foreign_mapping",
        "false_partial",
        "contradictory_lost",
    ],
)
def test_invalid_renewal_closure_is_atomic(
    client: TestClient, admin_headers: dict[str, str], database: Session, case: str
) -> None:
    contract, successor, source, target, owner, opportunity_id, payload = renewal_fixture(
        client, admin_headers, database
    )
    if case == "missing_successor":
        payload["successor_contract_id"] = None
    if case == "unknown_successor":
        payload["successor_contract_id"] = 999999
    if case == "overlap":
        successor.start_date = contract.end_date
    if case == "inactive":
        successor.is_active = False
    if case == "missing_sla":
        successor.has_sla = True
    if case == "pending":
        payload["lines"][0]["outcome"] = "PENDING"
    if case == "missing_mapping":
        payload["lines"][0]["successor_coverage_id"] = None
    if case == "foreign_mapping":
        payload["lines"][0]["successor_coverage_id"] = source.id
    if case == "false_partial":
        payload["outcome"] = "PARTIAL"
    if case == "contradictory_lost":
        payload["outcome"] = "LOST"
    database.commit()
    response = client.put(
        f"/api/v1/contracts/{contract.id}/renewal-opportunities/{opportunity_id}",
        headers=admin_headers,
        json=payload,
    )
    assert response.status_code == 409, response.text
    persisted = client.get(
        f"/api/v1/contracts/{contract.id}/renewal-opportunities", headers=admin_headers
    ).json()[0]
    assert persisted["version"] == 1 and persisted["stage"] == "IDENTIFIED"
    assert persisted["lines"][0]["outcome"] == "PENDING"


@pytest.mark.parametrize("board", [False, True])
def test_renewal_closure_preserves_current_support_completes_tasks_and_notifies(
    client: TestClient, admin_headers: dict[str, str], database: Session, board: bool
) -> None:
    contract, successor, source, target, owner, opportunity_id, payload = renewal_fixture(
        client, admin_headers, database
    )
    if board:
        response = client.post(
            f"/api/v1/contracts/{contract.id}/lifecycle-transition",
            headers=admin_headers,
            json={
                "action": "MARK_RENEWED",
                "version": 1,
                "successor_contract_id": successor.id,
                "reason": payload["reason"],
                "lines": payload["lines"],
            },
        )
    else:
        response = client.put(
            f"/api/v1/contracts/{contract.id}/renewal-opportunities/{opportunity_id}",
            headers=admin_headers,
            json=payload,
        )
    assert response.status_code == 200, response.text
    database.expire_all()
    assert contract.is_active and contract.status == "ACTIVE"
    assert successor.status == "ACTIVE"
    task = database.scalar(
        select(ContractRenewalTask).where(ContractRenewalTask.opportunity_id == opportunity_id)
    )
    assert task.status == "COMPLETED" and task.completed_at is not None
    notification = database.scalar(
        select(Notification).where(Notification.notification_type == "CONTRACT_RENEWAL_UPDATED")
    )
    assert notification is not None and "tab=renewals" in notification.deep_link
    assert (
        evaluate_entitlement(database, client_id=contract.client_id, service_id=source.service_id)[
            1
        ].id
        == contract.id
    )
    assert (
        evaluate_entitlement(
            database,
            client_id=contract.client_id,
            service_id=source.service_id,
            on_date=successor.start_date,
        )[1].id
        == successor.id
    )


def test_board_cannot_bypass_successor_validation(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    contract, successor, source, target, owner, opportunity_id, payload = renewal_fixture(
        client, admin_headers, database
    )
    successor.start_date = contract.end_date
    database.commit()
    response = client.post(
        f"/api/v1/contracts/{contract.id}/lifecycle-transition",
        headers=admin_headers,
        json={
            "action": "MARK_RENEWED",
            "version": 1,
            "successor_contract_id": successor.id,
            "reason": payload["reason"],
            "lines": payload["lines"],
        },
    )
    assert response.status_code == 409


def test_mixed_coverage_history_keeps_unversioned_rows(database: Session) -> None:
    contract, service, owner = _contract_data(database)
    _coverage(database, contract, service, owner)
    from app.modules.clients.models import Product

    product = Product(code="LEGACY-RENEWAL", name="Legacy product")
    database.add(product)
    database.flush()
    legacy = ContractCoverage(contract_id=contract.id, product_id=product.id, is_covered=True)
    database.add(legacy)
    database.commit()
    result = evaluate_entitlement(
        database, client_id=contract.client_id, product_id=product.id, on_date=date(2026, 8, 1)
    )
    assert result[0] == "COVERED"


def test_revision_gap_does_not_turn_into_unrestricted_coverage(database: Session) -> None:
    contract, service, owner = _contract_data(database)
    row = _coverage(database, contract, service, owner)
    for revision in database.scalars(
        select(ContractCoverageRevision).where(ContractCoverageRevision.coverage_id == row.id)
    ):
        revision.effective_until = date(2026, 7, 1)
    database.commit()
    assert (
        evaluate_entitlement(
            database, client_id=contract.client_id, service_id=service.id, on_date=date(2026, 8, 1)
        )[0]
        == "NOT_COVERED"
    )


def test_custom_renewal_notice_catches_up_once(database: Session) -> None:
    contract, _, owner = _contract_data(database)
    today = server_today()
    contract.end_date = today + timedelta(days=80)
    contract.renewal_notice_date = today - timedelta(days=2)
    database.commit()
    process_contract_lifecycle(database, today)
    process_contract_lifecycle(database, today + timedelta(days=1))
    notices = list(
        database.scalars(
            select(Notification).where(Notification.notification_type == "CONTRACT_RENEWAL")
        )
    )
    assert len(notices) == 1
    assert ":notice:" in notices[0].deduplication_key
    owner.is_active = False
    assert not can_receive_renewal(database, owner, contract)


def test_contract_expiration_rule_queues_one_email_with_to_and_cc(database: Session) -> None:
    contract, _, owner = _contract_data(database)
    admin = database.scalar(select(User).where(User.username_normalized == "admin"))
    assert admin
    copied_user = database.scalar(select(User).where(
        User.id != admin.id,
        User.is_active.in_([True]),
        User.user_type == "EMPLOYEE",
        User.email.is_not(None),
    ))
    assert copied_user
    today = server_today()
    contract.end_date = today + timedelta(days=2)
    contract.renewal_notice_date = today + timedelta(days=1)
    database.add_all([
        SiteSetting(key="contract_expiration_notifications_enabled", value="true"),
        SiteSetting(key="contract_expiration_notification_days", value="[60, 30, 14, 7, 0]"),
        SiteSetting(key="contract_expiration_notification_to_user_ids", value=json.dumps([owner.id])),
        SiteSetting(key="contract_expiration_notification_cc_user_ids", value=json.dumps([copied_user.id])),
    ])
    database.commit()

    process_contract_lifecycle(database, today)
    process_contract_lifecycle(database, today)

    events = list(database.scalars(select(EventOutbox).where(EventOutbox.event_type == "CONTRACT_EXPIRATION_EMAIL")))
    assert len(events) == 1
    payload = json.loads(events[0].payload_json)
    assert payload["to"] == [owner.email.lower()]
    assert payload["cc"] == [copied_user.email.lower()]
    assert contract.contract_number in payload["subject"]
    assert contract.name in payload["subject"]
    email_log = database.scalar(select(ContractExpirationNotificationDelivery).where(
        ContractExpirationNotificationDelivery.contract_id == contract.id,
        ContractExpirationNotificationDelivery.channel == "EMAIL",
    ))
    assert email_log
    assert email_log.milestone_key == "d7"
    assert email_log.status == "QUEUED"
    system_logs = list(database.scalars(select(ContractExpirationNotificationDelivery).where(
        ContractExpirationNotificationDelivery.contract_id == contract.id,
        ContractExpirationNotificationDelivery.channel == "SYSTEM",
    )))
    assert len(system_logs) == 2
    assert {row.status for row in system_logs} == {"DELIVERED"}
    sent: list[tuple[list[str], list[str], str]] = []
    result = process_email_outbox(
        database,
        Settings(
            app_env="test",
            secret_key="contract-notification-test-secret-over-thirty-two",
            smtp_enabled=True,
        ),
        group_sender=lambda to, cc, subject, _body: sent.append((to, cc, subject)),
    )
    database.refresh(email_log)
    assert result["sent"] == 1
    assert sent == [
        ([owner.email.lower()], [copied_user.email.lower()], payload["subject"])
    ]
    assert email_log.status == "SENT"
    assert email_log.sent_at is not None


def test_calendar_edit_uses_clock_snapshot_and_anchor(database: Session) -> None:
    contract, _, owner = _contract_data(database)
    calendar = database.get(BusinessCalendar, contract.calendar_id)
    other = BusinessCalendar(
        code="OTHER-SNAPSHOT", name="Other calendar", timezone=calendar.timezone
    )
    database.add(other)
    database.flush()
    policy = SlaPolicy(code="SNAPSHOT-POLICY", name="Snapshot", calendar_id=other.id)
    database.add(policy)
    database.flush()
    tickets = [
        Ticket(
            client_id=contract.client_id,
            ticket_type_id=database.scalar(select(TicketType.id)),
            status_id=database.scalar(select(TicketStatus.id)),
            subject="Calendar snapshot",
            description="Clock calendar regression",
            impact="MEDIUM",
            urgency="MEDIUM",
            priority="P2",
            created_by_user_id=owner.id,
        )
        for _ in range(2)
    ]
    database.add_all(tickets)
    database.flush()
    anchor = datetime.combine(server_today(), time(12), tzinfo=server_timezone())
    running = TicketSlaClock(
        ticket_id=tickets[0].id,
        clock_type="FIRST_RESPONSE",
        policy_id=policy.id,
        calendar_id=calendar.id,
        started_at=anchor - timedelta(days=2),
        start_anchor_at=anchor,
        target_minutes=60,
        warning_percent=75,
        due_at=server_now(),
        state="RUNNING",
        calculation_version="3.0",
    )
    paused = TicketSlaClock(
        ticket_id=tickets[1].id,
        clock_type="FIRST_RESPONSE",
        policy_id=policy.id,
        calendar_id=calendar.id,
        started_at=anchor,
        target_minutes=60,
        warning_percent=75,
        due_at=anchor,
        state="PAUSED",
        calculation_version="3.0",
    )
    database.add_all([running, paused])
    database.commit()
    update_calendar_schedule(
        calendar.id,
        CalendarScheduleWrite(
            timezone=calendar.timezone,
            days=[
                CalendarDayWrite(
                    weekday=i, start_time=time(9), end_time=time(17), is_working_day=True
                )
                for i in range(7)
            ],
        ),
        database,
        owner,
    )
    assert running.due_at == calculate_due_at(database, calendar.id, anchor, 60)
    assert paused.due_at == anchor


def test_reassignment_synchronizes_task_and_rejects_stale_updates(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    contract, successor, source, target, owner, opportunity_id, payload = renewal_fixture(
        client, admin_headers, database
    )
    replacement = User(
        full_name="Renewal replacement",
        username="renewal-replacement",
        username_normalized="renewal-replacement",
        email="replacement@example.com",
        email_normalized="replacement@example.com",
        password_hash="unused",
        user_type="EMPLOYEE",
        is_active=True,
    )
    database.add(replacement)
    database.flush()
    profile_id = database.scalar(
        select(UserProfile.profile_id).where(UserProfile.user_id == owner.id)
    )
    database.add(
        UserProfile(
            user_id=replacement.id,
            profile_id=profile_id,
            assigned_by_user_id=owner.id,
            is_active=True,
        )
    )
    database.commit()
    due = server_today() + timedelta(days=5)
    request = {
        "stage": "NEGOTIATION",
        "reason": "New owner and due date",
        "owner_user_id": replacement.id,
        "target_close_date": str(due),
        "version": 1,
    }
    url = f"/api/v1/contracts/{contract.id}/renewal-opportunities/{opportunity_id}"
    response = client.put(url, headers=admin_headers, json=request)
    assert response.status_code == 200, response.text
    database.expire_all()
    task = database.scalar(
        select(ContractRenewalTask).where(ContractRenewalTask.opportunity_id == opportunity_id)
    )
    assert task.assigned_user_id == replacement.id and task.due_at.date() == due
    recipients = set(
        database.scalars(
            select(Notification.recipient_user_id).where(
                Notification.notification_type == "CONTRACT_RENEWAL_UPDATED"
            )
        )
    )
    assert recipients == {owner.id, replacement.id}
    stale = client.put(url, headers=admin_headers, json={**request, "reason": "Stale overwrite"})
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "STALE_RENEWAL"


def test_owner_list_excludes_employees_without_contract_permission(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    contract, _, owner = _contract_data(database)
    outsider = User(
        full_name="No contract permission",
        username="no-contract",
        username_normalized="no-contract",
        email="no-contract@example.com",
        email_normalized="no-contract@example.com",
        password_hash="unused",
        user_type="EMPLOYEE",
        is_active=True,
    )
    database.add(outsider)
    database.commit()
    result = client.get(f"/api/v1/contracts/{contract.id}/renewal-owners", headers=admin_headers)
    assert result.status_code == 200
    assert owner.id in {row["id"] for row in result.json()}
    assert outsider.id not in {row["id"] for row in result.json()}
    denied = client.post(
        f"/api/v1/contracts/{contract.id}/renewal-opportunities",
        headers=admin_headers,
        json={
            "idempotency_key": "ineligible-owner-001",
            "owner_user_id": outsider.id,
            "target_close_date": str(server_today()),
            "reason": "Owner must have access",
        },
    )
    assert denied.status_code == 409


def test_renewing_future_term_keeps_ticket_creation_covered(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    contract, successor, source, target, owner, opportunity_id, payload = renewal_fixture(
        client, admin_headers, database
    )
    closed = client.put(
        f"/api/v1/contracts/{contract.id}/renewal-opportunities/{opportunity_id}",
        headers=admin_headers,
        json=payload,
    )
    assert closed.status_code == 200, closed.text
    created = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "client_id": contract.client_id,
            "contract_id": contract.id,
            "ticket_type_id": database.scalar(select(TicketType.id)),
            "service_id": source.service_id,
            "subject": "Support after renewal signing",
            "description": "Current term must remain covered",
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "priority": "P2",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["contract_id"] == contract.id
    assert created.json()["entitlement_status"] == "COVERED"


def test_successor_sla_can_be_prepared_during_negotiation(client, admin_headers, database):
    contract, successor, source, target, owner, opportunity_id, payload = renewal_fixture(client, admin_headers, database)
    successor.has_sla = True
    database.commit()
    response = client.put(f"/api/v1/contracts/{contract.id}/renewal-opportunities/{opportunity_id}", headers=admin_headers, json={
        "stage": "NEGOTIATION", "successor_contract_id": successor.id, "version": 1,
        "reason": "Prepare SLA before signing",
    })
    assert response.status_code == 200, response.text
    rejected = client.put(f"/api/v1/contracts/{contract.id}/renewal-opportunities/{opportunity_id}", headers=admin_headers, json={**payload, "version": 2})
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "SUCCESSOR_SLA_NOT_READY"
