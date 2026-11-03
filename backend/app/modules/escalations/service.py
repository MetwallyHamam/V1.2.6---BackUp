import json
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_now, server_timezone
from app.modules.clients.models import SupportTeam, SupportTeamMember
from app.modules.configuration.models import SiteSetting
from app.modules.contracts.models import (
    BusinessCalendar,
    BusinessCalendarDay,
    Holiday,
    SlaPolicy,
    TicketSlaClock,
)
from app.modules.contracts.service import working_minutes_between
from app.modules.escalations.models import EscalationEvent, EscalationRule, EscalationWorkItem
from app.modules.iam.models import Profile, User, UserProfile
from app.modules.notifications.models import EventOutbox, Notification
from app.modules.tickets.models import Ticket, TicketStatus, TicketType
from app.modules.tickets.service import SLA_EXEMPT_TICKET_TYPE_CODES


def _json_setting(db: Session, key: str, default: list[object]) -> list[object]:
    row = db.get(SiteSetting, key)
    if not row:
        return default
    try:
        value = json.loads(row.value)
        return value if isinstance(value, list) else default
    except (TypeError, ValueError):
        return default


def _sla_warning_configuration(db: Session) -> tuple[bool, dict[str, list[int]], set[int], set[str]]:
    enabled_row = db.get(SiteSetting, "sla_warning_enabled")
    enabled = enabled_row is None or enabled_row.value == "true"
    thresholds = {
        "FIRST_RESPONSE": [int(str(value)) for value in _json_setting(db, "sla_response_warning_minutes", [60])],
        "RESOLUTION": [int(str(value)) for value in _json_setting(db, "sla_resolution_warning_minutes", [240])],
    }
    team_ids = {int(str(value)) for value in _json_setting(db, "sla_warning_support_team_ids", [])}
    direct_emails = {str(value).strip().lower() for value in _json_setting(db, "sla_warning_recipient_emails", []) if str(value).strip()}
    return enabled, thresholds, team_ids, direct_emails


def _next_clock_evaluation(
    clock: TicketSlaClock,
    rules: list[EscalationRule],
    warning_minutes: list[int],
    now: datetime,
) -> datetime | None:
    """Return the next meaningful SLA threshold instead of polling the clock."""
    if clock.state != "RUNNING" or clock.completed_at is not None:
        return None
    started_at = clock.started_at.replace(tzinfo=server_timezone())
    due_at = clock.due_at.replace(tzinfo=server_timezone())
    candidates = [due_at]
    duration = max(due_at - started_at, timedelta(seconds=1))
    candidates.extend(
        started_at + duration * (rule.threshold_percent / 100)
        for rule in rules
        if rule.clock_type == clock.clock_type
    )
    candidates.extend(due_at - timedelta(minutes=minutes) for minutes in warning_minutes)
    future = [candidate for candidate in candidates if candidate > now]
    return min(future) if future else None


def evaluate_escalations(
    db: Session,
    now: datetime | None = None,
    metrics: dict[str, int] | None = None,
    limit: int | None = None,
) -> int:
    now = now or server_now()
    created = 0
    work_query = (
        select(EscalationWorkItem)
        .where(
            EscalationWorkItem.status == "PENDING",
            EscalationWorkItem.next_evaluation_at <= now,
        )
        .order_by(EscalationWorkItem.next_evaluation_at, EscalationWorkItem.id)
    )
    if limit is not None:
        work_query = work_query.limit(limit)
    work_items = list(db.scalars(work_query))
    work_by_clock = {item.ticket_sla_clock_id: item for item in work_items}
    for item in work_items:
        item.status = "PROCESSING"
        item.last_started_at = now
        item.attempt_count += 1
    clocks = list(
        db.scalars(
            select(TicketSlaClock)
            .join(Ticket, Ticket.id == TicketSlaClock.ticket_id)
            .join(TicketType, TicketType.id == Ticket.ticket_type_id)
            .where(
                TicketSlaClock.id.in_(set(work_by_clock) or {-1}),
                TicketSlaClock.state == "RUNNING",
                TicketSlaClock.completed_at.is_(None),
                TicketType.code.not_in(SLA_EXEMPT_TICKET_TYPE_CODES),
            )
            .order_by(TicketSlaClock.due_at, TicketSlaClock.id)
        )
    )
    rules = list(db.scalars(select(EscalationRule).where(EscalationRule.is_active.in_([True]))))
    clock_ids = {clock.id for clock in clocks}
    ticket_ids = {clock.ticket_id for clock in clocks}
    policy_ids = {clock.policy_id for clock in clocks}
    tickets = {
        ticket.id: ticket
        for ticket in db.scalars(select(Ticket).where(Ticket.id.in_(ticket_ids or {-1})))
    }
    policies = {
        policy.id: policy
        for policy in db.scalars(select(SlaPolicy).where(SlaPolicy.id.in_(policy_ids or {-1})))
    }
    calendar_ids = {policy.calendar_id for policy in policies.values()}
    calendars = {
        calendar.id: calendar
        for calendar in db.scalars(
            select(BusinessCalendar).where(BusinessCalendar.id.in_(calendar_ids or {-1}))
        )
    }
    calendar_days: dict[int, dict[int, tuple[time, time]]] = {}
    for calendar_day in db.scalars(
        select(BusinessCalendarDay).where(
            BusinessCalendarDay.calendar_id.in_(calendar_ids or {-1}),
            BusinessCalendarDay.is_working_day.in_([True]),
        )
    ):
        calendar_days.setdefault(calendar_day.calendar_id, {})[calendar_day.weekday] = (
            calendar_day.start_time,
            calendar_day.end_time,
        )
    calendar_holidays: dict[int, set[date]] = {}
    for holiday in db.scalars(
        select(Holiday).where(Holiday.calendar_id.in_(calendar_ids or {-1}))
    ):
        calendar_holidays.setdefault(holiday.calendar_id, set()).add(holiday.holiday_date)
    existing_escalations = {
        (clock_id, rule_id)
        for clock_id, rule_id in db.execute(
            select(EscalationEvent.ticket_sla_clock_id, EscalationEvent.rule_id).where(
                EscalationEvent.ticket_sla_clock_id.in_(clock_ids or {-1})
            )
        )
    }
    manager_ids = list(
        db.scalars(
            select(User.id)
            .join(UserProfile, UserProfile.user_id == User.id)
            .join(Profile, Profile.id == UserProfile.profile_id)
            .where(Profile.code == "SUPPORT_MANAGER", User.is_active.in_([True]))
        )
    )
    warning_enabled, warning_thresholds, warning_team_ids, direct_warning_emails = _sla_warning_configuration(db)
    team_users = list(db.scalars(select(User).join(SupportTeamMember, SupportTeamMember.user_id == User.id).join(SupportTeam, SupportTeam.id == SupportTeamMember.team_id).where(SupportTeam.id.in_(warning_team_ids or {-1}), SupportTeam.is_active.in_([True]), User.is_active.in_([True]))))
    team_user_ids = {user.id for user in team_users}
    team_emails = {str(user.support_notification_email).strip().lower() for user in team_users if user.support_notification_email}
    pending_status_ids = select(TicketStatus.id).where(
        TicketStatus.code.in_(["PENDING_CLIENT", "PENDING_INTERNAL", "PENDING_VENDOR"])
    )
    pending_query = (
        select(Ticket)
        .where(
                Ticket.status_id.in_(pending_status_ids),
                Ticket.pending_owner_user_id.is_not(None),
                Ticket.pending_follow_up_at.is_not(None),
                Ticket.pending_follow_up_at <= now,
            )
        .order_by(Ticket.pending_follow_up_at, Ticket.id)
    )
    if limit is not None:
        pending_query = pending_query.limit(limit)
    due_pending = list(db.scalars(pending_query))
    all_recipient_ids = set(manager_ids) | team_user_ids
    all_recipient_ids.update(
        ticket.assigned_user_id for ticket in tickets.values() if ticket.assigned_user_id
    )
    recipient_users = {
        user.id: user
        for user in db.scalars(
            select(User).where(
                User.id.in_(all_recipient_ids or {-1}), User.is_active.in_([True])
            )
        )
    }
    if metrics is not None:
        metrics.update(
            {
                "running_clocks": len(clocks),
                "due_work_items": len(work_items),
                "active_rules": len(rules),
                "due_pending_tickets": len(due_pending),
                "calendars": len(calendars),
            }
        )
    for pending_ticket in due_pending:
        recipient = pending_ticket.pending_owner_user_id
        if not recipient or not pending_ticket.pending_follow_up_at:
            continue
        reminder_key = f"pending-due:{pending_ticket.id}:{pending_ticket.pending_follow_up_at.isoformat()}:user:{recipient}"
        if db.scalar(select(Notification.id).where(Notification.deduplication_key == reminder_key)):
            continue
        db.add(
            Notification(
                recipient_user_id=recipient,
                notification_type="PENDING_FOLLOW_UP_DUE",
                severity="WARNING",
                title=f"Pending follow-up due: {pending_ticket.ticket_number}",
                message=pending_ticket.pending_reason or "The ticket follow-up deadline is due.",
                deep_link=f"/tickets/{pending_ticket.id}",
                deduplication_key=reminder_key,
            )
        )
        created += 1
    for clock in clocks:
        work_item = work_by_clock[clock.id]
        ticket = tickets.get(clock.ticket_id)
        if not ticket:
            work_item.status = "COMPLETED"
            work_item.last_completed_at = now
            continue
        policy = policies.get(clock.policy_id)
        elapsed_minutes = (
            working_minutes_between(
                clock.started_at.replace(tzinfo=server_timezone()),
                now,
                calendars[policy.calendar_id].timezone,
                calendar_days.get(policy.calendar_id, {}),
                calendar_holidays.get(policy.calendar_id, set()),
            )
            if policy and policy.calendar_id in calendars
            else max(
                0,
                int(
                    (now - clock.started_at.replace(tzinfo=server_timezone())).total_seconds()
                    // 60
                ),
            )
        )
        consumed = int(elapsed_minutes * 100 / max(clock.target_minutes, 1))
        if now >= clock.due_at.replace(tzinfo=server_timezone()):
            consumed = max(consumed, 100)
            clock.state = "BREACHED"
            clock.breached_at = now
        remaining_minutes = max(0, clock.target_minutes - elapsed_minutes)
        if warning_enabled:
            warning_recipients = set(manager_ids) | team_user_ids
            if ticket.assigned_user_id:
                warning_recipients.add(ticket.assigned_user_id)
            recipient_emails = set(direct_warning_emails) | team_emails
            recipient_emails.update(str(recipient_users[user_id].support_notification_email or recipient_users[user_id].email).strip().lower() for user_id in warning_recipients if user_id in recipient_users and (recipient_users[user_id].support_notification_email or recipient_users[user_id].email))
            due_version = int(clock.due_at.replace(tzinfo=server_timezone()).timestamp())
            for threshold_minutes in warning_thresholds.get(clock.clock_type, []):
                if remaining_minutes > threshold_minutes:
                    continue
                warning_prefix = f"sla-warning:{clock.id}:v{clock.policy_version}:due{due_version}:m{threshold_minutes}"
                title = f"SLA due within {threshold_minutes} minutes: {ticket.ticket_number}"
                message = f"{clock.clock_type.replace('_', ' ').title()} SLA has approximately {remaining_minutes} working minutes remaining ({consumed}% consumed)."
                warning_created = False
                for recipient in warning_recipients:
                    warning_key = f"{warning_prefix}:user:{recipient}"
                    if db.scalar(select(Notification.id).where(Notification.deduplication_key == warning_key)):
                        continue
                    db.add(Notification(recipient_user_id=recipient, notification_type="SLA_WARNING", severity="WARNING" if consumed < 100 else "CRITICAL", title=title, message=message, deep_link=f"/tickets/{ticket.id}", deduplication_key=warning_key))
                    warning_created = True
                    created += 1
                outbox_key = f"email:{warning_prefix}"
                if recipient_emails and not db.scalar(select(EventOutbox.id).where(EventOutbox.deduplication_key == outbox_key)):
                    db.add(EventOutbox(event_type="SLA_WARNING", aggregate_type="Ticket", aggregate_id=str(ticket.id), deduplication_key=outbox_key, payload_json=json.dumps({"ticket_id": ticket.id, "clock_id": clock.id, "threshold_minutes": threshold_minutes, "remaining_minutes": remaining_minutes, "consumed_percent": consumed, "recipient_emails": sorted(recipient_emails), "subject": title, "body": message, "deep_link": f"/tickets/{ticket.id}"})))
                    warning_created = True
                if warning_created and not warning_recipients:
                    created += 1
        for rule in rules:
            if rule.clock_type != clock.clock_type or consumed < rule.threshold_percent:
                continue
            if rule.priority and rule.priority != ticket.priority:
                continue
            if (clock.id, rule.id) in existing_escalations:
                continue
            event = EscalationEvent(ticket_id=ticket.id, ticket_sla_clock_id=clock.id, rule_id=rule.id, threshold_percent=rule.threshold_percent)
            db.add(event)
            existing_escalations.add((clock.id, rule.id))
            recipients: set[int] = set()
            if rule.notify_assignee and ticket.assigned_user_id:
                recipients.add(ticket.assigned_user_id)
            if rule.notify_managers:
                recipients.update(manager_ids)
            for recipient in recipients:
                key = f"sla:{clock.id}:rule:{rule.id}:user:{recipient}"
                db.add(Notification(recipient_user_id=recipient, notification_type="SLA_ESCALATION", severity=rule.severity, title=f"SLA {rule.threshold_percent}%: {ticket.ticket_number}", message=f"{clock.clock_type.replace('_', ' ').title()} SLA requires attention.", deep_link=f"/tickets/{ticket.id}", deduplication_key=key))
            db.add(EventOutbox(event_type="SLA_ESCALATED", aggregate_type="Ticket", aggregate_id=str(ticket.id), deduplication_key=f"email:sla-escalated:{clock.id}:{rule.id}", payload_json=json.dumps({"ticket_id": ticket.id, "clock_id": clock.id, "rule_id": rule.id, "threshold": rule.threshold_percent})))
            created += 1
        next_evaluation = _next_clock_evaluation(
            clock,
            rules,
            warning_thresholds.get(clock.clock_type, []) if warning_enabled else [],
            now,
        )
        work_item.last_completed_at = now
        work_item.processed_count += 1
        work_item.last_error = None
        if next_evaluation is None:
            work_item.status = "COMPLETED"
        else:
            work_item.status = "PENDING"
            work_item.next_evaluation_at = next_evaluation
    processed_clock_ids = {clock.id for clock in clocks}
    for clock_id, work_item in work_by_clock.items():
        if clock_id not in processed_clock_ids:
            work_item.status = "COMPLETED"
            work_item.last_completed_at = now
    db.commit()
    return created
