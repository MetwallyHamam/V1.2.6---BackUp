"""Keep linked UAT tests aligned with resolved defect tickets."""

from datetime import date, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.iam.models import AuditLog, User
from app.modules.notifications.models import Notification
from app.modules.tickets.models import Ticket
from app.modules.uat.models import UatCycle, UatCycleTest


def notify_defect_created(db: Session, cycle: UatCycle, test: UatCycleTest, ticket: Ticket) -> None:
    recipients = {cycle.coordinator_user_id}
    if test.owner_user_id:
        recipients.add(test.owner_user_id)
    for recipient_id in recipients:
        db.add(Notification(recipient_user_id=recipient_id, notification_type="UAT_TICKET_CREATED",
                            severity="WARNING", title=f"UAT defect ticket created: {ticket.ticket_number}",
                            message=f"Ticket {ticket.ticket_number} is linked to UAT test #{test.id} in {cycle.code}.",
                            deep_link="/uat", deduplication_key=f"uat-ticket-created:{test.id}:{ticket.id}:user:{recipient_id}"))


def queue_due_reminders(db: Session, today: date) -> int:
    """Queue one reminder per due date and stage for active cycles and unfinished tests."""
    created = 0

    def add(recipient_id: int, kind: str, key: str, title: str, message: str) -> None:
        nonlocal created
        if db.scalar(select(Notification.id).where(Notification.deduplication_key == key)):
            return
        db.add(Notification(recipient_user_id=recipient_id, notification_type=kind,
                            severity="WARNING" if kind == "UAT_OVERDUE" else "INFO",
                            title=title, message=message, deep_link="/uat", deduplication_key=key))
        created += 1

    horizon = today + timedelta(days=3)
    cycles = list(db.scalars(select(UatCycle).where(UatCycle.status == "ACTIVE", UatCycle.due_date.is_not(None), UatCycle.due_date <= horizon)))
    for cycle in cycles:
        assert cycle.due_date is not None
        overdue = cycle.due_date < today
        stage = "overdue" if overdue else "due"
        add(cycle.coordinator_user_id, "UAT_OVERDUE" if overdue else "UAT_DUE_SOON",
            f"uat-cycle-{stage}:{cycle.id}:{cycle.due_date}:user:{cycle.coordinator_user_id}",
            f"UAT cycle {'overdue' if overdue else 'due soon'}: {cycle.code}",
            f"{cycle.title} was due on {cycle.due_date}." if overdue else f"{cycle.title} is due on {cycle.due_date}.")
    tests = list(db.execute(select(UatCycleTest, UatCycle).join(UatCycle, UatCycle.id == UatCycleTest.cycle_id).where(
        UatCycle.status == "ACTIVE", UatCycleTest.due_date.is_not(None), UatCycleTest.due_date <= horizon)))
    for test, cycle in tests:
        assert test.due_date is not None
        overdue = test.due_date < today
        stage = "overdue" if overdue else "due"
        for recipient_id, audience in (
            (test.owner_user_id if test.test_result != "PASS" else None, "internal"),
            (test.client_tester_user_id if cycle.portal_visible and cycle.allow_client_testing and test.client_test_result != "PASS" else None, "client"),
        ):
            if not recipient_id:
                continue
            add(recipient_id, "UAT_OVERDUE" if overdue else "UAT_DUE_SOON",
                f"uat-test-{stage}:{test.id}:{test.due_date}:{audience}:user:{recipient_id}",
                f"UAT test {'overdue' if overdue else 'due soon'}: #{test.id}",
                f"Test #{test.id} was due on {test.due_date}." if overdue else f"Test #{test.id} is due on {test.due_date}.")
    db.commit()
    return created


def mark_retests_ready(db: Session, ticket: Ticket, actor: User) -> None:
    for test in db.scalars(select(UatCycleTest).where(
        UatCycleTest.linked_ticket_id == ticket.id,
        or_(
            (UatCycleTest.test_result == "FAIL") & (UatCycleTest.workflow_status == "WAITING_FIX"),
            (UatCycleTest.client_test_result == "FAIL") & (UatCycleTest.client_workflow_status == "WAITING_FIX"),
        ),
    )):
        internal_ready = test.test_result == "FAIL" and test.workflow_status == "WAITING_FIX"
        client_ready = test.client_test_result == "FAIL" and test.client_workflow_status == "WAITING_FIX"
        if internal_ready:
            test.workflow_status = "READY_FOR_RETEST"
        if client_ready:
            test.client_workflow_status = "READY_FOR_RETEST"
        db.add(AuditLog(actor_user_id=actor.id, entity_type="UatCycleTest", entity_id=str(test.id), action="uat.test.ready_for_retest"))
        cycle = db.get(UatCycle, test.cycle_id)
        if cycle:
            db.add(Notification(recipient_user_id=cycle.coordinator_user_id,
                                notification_type="UAT_TICKET_RESOLVED", severity="INFO",
                                title=f"UAT defect resolved: {ticket.ticket_number}",
                                message=f"The linked ticket for UAT test #{test.id} is resolved.",
                                deep_link="/uat", deduplication_key=f"uat-ticket-resolved:{test.id}:{ticket.id}:attempt:{test.attempt_count}:{test.client_attempt_count}"))
        if internal_ready and test.owner_user_id:
            db.add(Notification(
                recipient_user_id=test.owner_user_id,
                notification_type="UAT_READY_FOR_RETEST",
                severity="INFO",
                title=f"UAT test ready for retest: {ticket.ticket_number}",
                message=f"{ticket.ticket_number} is resolved. Retest UAT test #{test.id}.",
                deep_link="/uat",
                deduplication_key=f"uat-retest:{test.id}:attempt:{test.attempt_count}",
            ))
        if client_ready and test.client_tester_user_id:
            db.add(Notification(recipient_user_id=test.client_tester_user_id,
                                notification_type="UAT_READY_FOR_RETEST", severity="INFO",
                                title=f"Client UAT test ready for retest: {ticket.ticket_number}",
                                message=f"{ticket.ticket_number} is resolved. Retest your assigned UAT test #{test.id}.",
                                deep_link="/portal/uat",
                                deduplication_key=f"uat-client-retest:{test.id}:attempt:{test.client_attempt_count}"))
