import json

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import AuthorizationError
from app.modules.clients.models import Client
from app.modules.configuration.models import SiteSetting
from app.modules.iam.models import User, UserProfile
from app.modules.notifications.models import EventOutbox, TicketNotificationRule
from app.modules.tickets.models import Ticket


def _setting(db: Session, key: str, default: str = "") -> str:
    row = db.get(SiteSetting, key)
    return row.value if row else default

def normalized_addresses(value: str) -> list[str]:
    return list(dict.fromkeys(part.strip().lower() for part in value.replace(";", ",").split(",") if part.strip()))

def _render(template: str, values: dict[str, str]) -> str:
    for key, value in values.items(): template = template.replace("{{" + key + "}}", value)
    return template


def authorized_ticket_addresses(db: Session, ticket: Ticket, addresses: list[str]) -> list[str]:
    """Fail closed for unknown, inactive, ambiguous, or non-visible recipients."""
    from app.modules.tickets.service import ensure_ticket_access

    requested = normalized_addresses(",".join(addresses))
    if not requested:
        return []
    owners: dict[str, list[User]] = {address: [] for address in requested}
    for user in db.scalars(select(User).where(or_(
        func.lower(func.trim(User.email)).in_(requested),
        func.lower(func.trim(User.support_notification_email)).in_(requested),
    ))):
        for address in {user.email, user.support_notification_email}:
            if address and address.strip().lower() in owners:
                owners[address.strip().lower()].append(user)
    allowed = []
    for address in requested:
        users = owners[address]
        if not users or any(not user.is_active for user in users):
            continue
        try:
            for user in users:
                ensure_ticket_access(db, user, ticket)
        except AuthorizationError:
            continue
        allowed.append(address)
    return allowed

def queue_ticket_creation_email(db: Session, ticket: Ticket, actor: User) -> None:
    if ticket.source_channel in {"CLIENT_PORTAL", "MOSAIC"}:
        if _setting(db, "portal_ticket_email_enabled", "false") != "true": return
        recipients = normalized_addresses(_setting(db, "portal_ticket_email_to")); cc = [x for x in normalized_addresses(_setting(db, "portal_ticket_email_cc")) if x not in recipients]
        matches = [{"rule_id": "portal", "version": 1, "reason": "portal creation"}]
    else:
        actor_profiles = set(db.scalars(select(UserProfile.profile_id).where(UserProfile.user_id == actor.id, UserProfile.is_active.in_([True]))))
        recipients, cc, matches = [], [], []
        for rule in db.scalars(select(TicketNotificationRule).where(TicketNotificationRule.is_enabled.in_([True]), TicketNotificationRule.is_deleted.in_([False]))):
            profiles, engineers = set(json.loads(rule.creator_profile_ids_json)), set(json.loads(rule.assigned_engineer_ids_json))
            conditions = ([bool(profiles & actor_profiles)] if profiles else []) + ([ticket.assigned_user_id in engineers] if engineers else [])
            matched = bool(conditions) and (all(conditions) if rule.match_mode == "ALL" else any(conditions))
            if not matched: continue
            rule_to = json.loads(rule.to_json); rule_cc = json.loads(rule.cc_json)
            recipients.extend(rule_to); cc.extend(rule_cc); matches.append({"rule_id": rule.id, "version": rule.version, "reason": "initial creation match"})
            if rule.include_matched_engineer_email and ticket.assigned_user_id in engineers:
                engineer = db.get(User, ticket.assigned_user_id)
                if engineer and engineer.support_notification_email: recipients.append(engineer.support_notification_email)
        recipients = list(dict.fromkeys(normalized_addresses(",".join(recipients)))); cc = [x for x in normalized_addresses(",".join(cc)) if x not in recipients]
    recipients = authorized_ticket_addresses(db, ticket, recipients)
    cc = authorized_ticket_addresses(db, ticket, cc)
    if not recipients: return
    client = db.get(Client, ticket.client_id)
    template_values: dict[str, str] = {"ticket_number": ticket.ticket_number or "Not specified", "ticket_title": ticket.subject or "Not specified", "description": ticket.description or "Not specified", "client_name": client.name if client else "Not specified", "source": ticket.source_channel or "Not specified", "creator_name": actor.full_name, "created_at": ticket.created_at.isoformat()}
    subject_template = _setting(db, "ticket_notification_template_subject", "[Support Hub] New ticket {{ticket_number}}")
    body_template = _setting(db, "ticket_notification_template_body", "A new ticket was created: {{ticket_number}}\nOpen Support Hub to view details you are authorized to access.")
    template_version = int(_setting(db, "ticket_notification_template_version", "1"))
    payload = {"to": recipients, "cc": cc, "subject": _render(subject_template, template_values), "body": _render(body_template, template_values), "deep_link": f"/tickets/{ticket.id}", "template_version": template_version, "matches": matches, "template_snapshot": {"subject": subject_template, "body": body_template}}
    db.add(EventOutbox(event_type="TICKET_CREATION_EMAIL", aggregate_type="Ticket", aggregate_id=str(ticket.id), deduplication_key=f"ticket-created:{ticket.id}:v1", payload_json=json.dumps(payload)))


def queue_ticket_reassignment_email(db: Session, ticket: Ticket, previous_user_id: int | None, actor: User) -> None:
    if ticket.assigned_user_id is None or ticket.assigned_user_id == previous_user_id: return
    recipients: list[str] = []; cc: list[str] = []; matches: list[dict[str, object]] = []
    for rule in db.scalars(select(TicketNotificationRule).where(TicketNotificationRule.is_enabled.in_([True]), TicketNotificationRule.is_deleted.in_([False]), TicketNotificationRule.evaluate_later_reassignment.in_([True]))):
        engineers = set(json.loads(rule.assigned_engineer_ids_json))
        if ticket.assigned_user_id not in engineers or previous_user_id in engineers: continue
        recipients.extend(json.loads(rule.to_json)); cc.extend(json.loads(rule.cc_json)); warning = None
        if rule.include_matched_engineer_email:
            engineer = db.get(User, ticket.assigned_user_id)
            if engineer and engineer.support_notification_email: recipients.append(engineer.support_notification_email)
            else: warning = "Matched engineer has no Support Notification Email."
        matches.append({"rule_id": rule.id, "version": rule.version, "reason": "entered selected engineer scope", "warning": warning})
    recipients = normalized_addresses(",".join(recipients)); cc = [x for x in normalized_addresses(",".join(cc)) if x not in recipients]
    recipients = authorized_ticket_addresses(db, ticket, recipients)
    cc = authorized_ticket_addresses(db, ticket, cc)
    if not recipients: return
    payload = {"to": recipients, "cc": cc, "subject": f"[Support Hub] Ticket assigned {ticket.ticket_number} — {ticket.subject}", "body": f"Ticket {ticket.ticket_number} entered a configured engineer assignment scope.\nAssigned by: {actor.full_name}\n", "deep_link": f"/tickets/{ticket.id}", "template_version": 1, "matches": matches, "previous_user_id": previous_user_id, "assigned_user_id": ticket.assigned_user_id}
    db.add(EventOutbox(event_type="TICKET_CREATION_EMAIL", aggregate_type="Ticket", aggregate_id=str(ticket.id), deduplication_key=f"ticket-assignment-matched:{ticket.id}:version:{ticket.version}:user:{ticket.assigned_user_id}", payload_json=json.dumps(payload)))
