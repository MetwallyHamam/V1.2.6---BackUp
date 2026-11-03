import json
from datetime import date

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from app.core.clock import server_today
from app.modules.clients.models import Client
from app.modules.configuration.models import SiteSetting
from app.modules.contracts.access import can_receive_renewal
from app.modules.contracts.models import (
    Contract,
    ContractClientLink,
    ContractExpirationNotificationDelivery,
    ContractRenewalOpportunity,
)
from app.modules.iam.models import User
from app.modules.iam.service import effective_permissions
from app.modules.notifications.models import EventOutbox, Notification
from app.modules.visits.models import ClientVisitEntitlement

REMINDER_DAYS = (60, 30, 14, 7, 0)


def _json_setting(db: Session, key: str, default: list[object]) -> list[object]:
    row = db.get(SiteSetting, key)
    if not row:
        return default
    try:
        value = json.loads(row.value)
        return value if isinstance(value, list) else default
    except (TypeError, ValueError):
        return default


def recalculate_client_contract_service_status(
    db: Session, client_ids: set[int], today: date | None = None
) -> None:
    today = today or server_today()
    for client in db.scalars(select(Client).where(Client.id.in_(client_ids or {-1}))):
        if not client.is_active:
            client.contract_service_status = "ADMIN_INACTIVE"
            continue
        contracts = list(
            db.scalars(
                select(Contract).where(
                    Contract.is_shared_default.in_([False]),
                    or_(
                        Contract.client_id == client.id,
                        Contract.client_links.any(ContractClientLink.client_id == client.id),
                    ),
                )
            )
        )
        if any(row.status == "ACTIVE" and row.is_active and row.start_date <= today <= row.end_date for row in contracts):
            client.contract_service_status = "COVERED"
        elif any(row.end_date < today and (today - row.end_date).days <= row.expiry_grace_days for row in contracts):
            client.contract_service_status = "GRACE_PERIOD"
        elif any(row.start_date > today and row.status in {"DRAFT", "ACTIVE"} for row in contracts):
            client.contract_service_status = "FUTURE_CONTRACT"
        else:
            client.contract_service_status = "NO_ACTIVE_CONTRACT"


def process_contract_lifecycle(
    db: Session, today: date | None = None, metrics: dict[str, int] | None = None
) -> int:
    """Expire contracts/visit allowances and queue deduplicated renewal reminders."""
    # Saving notification settings and the background scheduler can evaluate the
    # lifecycle concurrently on different IIS workers. Serialize that small
    # critical section on SQL Server so they cannot both enqueue the same event.
    if db.get_bind().dialect.name == "mssql":
        lock_result = db.scalar(text("""
            SET NOCOUNT ON;
            DECLARE @result int;
            EXEC @result = sys.sp_getapplock
                @Resource = 'SupportHub.ContractLifecycleNotifications',
                @LockMode = 'Exclusive',
                @LockOwner = 'Transaction',
                @LockTimeout = 15000;
            -- SET options survive transaction commit and pool check-in. Restore
            -- row counts before any ORM flush uses this physical connection.
            SET NOCOUNT OFF;
            SELECT @result;
        """))
        if lock_result is None or int(lock_result) < 0:
            raise RuntimeError("Could not acquire the contract lifecycle notification lock.")
    today = today or server_today()
    contracts = list(db.scalars(select(Contract)))
    linked_client_ids = set(db.scalars(select(ContractClientLink.client_id)))
    to_user_ids = [int(value) for value in _json_setting(db, "contract_expiration_notification_to_user_ids", []) if isinstance(value, int)]
    cc_user_ids = [int(value) for value in _json_setting(db, "contract_expiration_notification_cc_user_ids", []) if isinstance(value, int)]
    if not to_user_ids:
        legacy_to = {str(value).strip().lower() for value in _json_setting(db, "contract_expiration_notification_to", [])}
        legacy_cc = {str(value).strip().lower() for value in _json_setting(db, "contract_expiration_notification_cc", [])}
        legacy_users = list(db.scalars(select(User).where(
            User.is_active.in_([True]), User.user_type == "EMPLOYEE"
        )))
        to_user_ids = [user.id for user in legacy_users if user.email and user.email.strip().lower() in legacy_to]
        cc_user_ids = [user.id for user in legacy_users if user.email and user.email.strip().lower() in legacy_cc and user.id not in to_user_ids]
    selected_user_ids = list(dict.fromkeys([*to_user_ids, *cc_user_ids]))
    selected_users = {
        user.id: user
        for user in db.scalars(
            select(User).where(
                User.id.in_(selected_user_ids or [-1]),
                User.is_active.in_([True]),
                User.user_type == "EMPLOYEE",
            )
        )
    }
    recipients = [selected_users[user_id] for user_id in selected_user_ids if user_id in selected_users]
    use_default_contract_managers = not selected_user_ids
    if use_default_contract_managers:
        recipients = [
            user
            for user in db.scalars(
                select(User).where(User.is_active.in_([True]), User.user_type == "EMPLOYEE")
            )
            if "contract.manage" in effective_permissions(db, user).permissions
        ]
    configured_days = tuple(
        sorted(
            {
                int(value)
                for value in _json_setting(
                    db, "contract_expiration_notification_days", list(REMINDER_DAYS)
                )
                if isinstance(value, int) and 0 <= value <= 3650
            },
            reverse=True,
        )
    ) or REMINDER_DAYS
    enabled_row = db.get(SiteSetting, "contract_expiration_notifications_enabled")
    email_enabled = bool(enabled_row and enabled_row.value.lower() == "true")
    to_addresses = [selected_users[user_id].email.strip().lower() for user_id in to_user_ids if user_id in selected_users and selected_users[user_id].email]
    cc_addresses = [selected_users[user_id].email.strip().lower() for user_id in cc_user_ids if user_id in selected_users and selected_users[user_id].email]
    subject_row = db.get(SiteSetting, "contract_expiration_notification_subject")
    body_row = db.get(SiteSetting, "contract_expiration_notification_body")
    version_row = db.get(SiteSetting, "contract_expiration_notification_version")
    rule_version = int(version_row.value) if version_row else 1
    subject_template = (
        subject_row.value
        if subject_row
        else "Contract {contract_number} — {contract_name} expires in {days_remaining} day(s)"
    )
    body_template = body_row.value if body_row else "Contract {contract_number} ({contract_name}) expires on {end_date}. {renewal_status}"
    expired = reminders = emails = 0
    for contract in contracts:
        if contract.status == "ACTIVE" and contract.end_date < today:
            contract.status = "EXPIRED"
            contract.is_active = False
            expired += 1
            for entitlement in db.scalars(
                select(ClientVisitEntitlement).where(
                    ClientVisitEntitlement.contract_id == contract.id,
                    ClientVisitEntitlement.status == "ACTIVE",
                )
            ):
                entitlement.status = "EXPIRED"
        if contract.status != "ACTIVE" or not contract.is_active:
            continue
        days_remaining = (contract.end_date - today).days
        custom_notice_due = contract.renewal_notice_date is not None and contract.renewal_notice_date <= today
        crossed_milestones = [value for value in configured_days if days_remaining <= value]
        milestone_days: int | None = min(crossed_milestones) if crossed_milestones else None
        # A contract-specific renewal date is an additional fallback signal; it
        # must not suppress the globally configured expiration milestones.
        if milestone_days is None and not custom_notice_due:
            continue
        open_renewal = db.scalar(
            select(ContractRenewalOpportunity.id).where(
                ContractRenewalOpportunity.source_contract_id == contract.id,
                ContractRenewalOpportunity.stage != "CLOSED",
            )
        )
        eligible_recipient_count = 0
        for recipient in recipients:
            if use_default_contract_managers and not can_receive_renewal(db, recipient, contract):
                continue
            eligible_recipient_count += 1
            # A configured date also catches up after scheduler downtime, once per term.
            milestone = f"d{milestone_days}" if milestone_days is not None else f"notice:{contract.renewal_notice_date}"
            key = f"contract-lifecycle:{contract.id}:{contract.end_date}:{milestone}:u{recipient.id}"
            applied = db.scalar(select(ContractExpirationNotificationDelivery).where(
                ContractExpirationNotificationDelivery.contract_id == contract.id,
                ContractExpirationNotificationDelivery.contract_end_date == contract.end_date,
                ContractExpirationNotificationDelivery.milestone_key == milestone,
                ContractExpirationNotificationDelivery.channel == "SYSTEM",
                ContractExpirationNotificationDelivery.recipient_key == str(recipient.id),
            ))
            if applied:
                continue
            notification = db.scalar(select(Notification).where(Notification.deduplication_key == key))
            if not notification:
                notification = Notification(
                    recipient_user_id=recipient.id,
                    notification_type="CONTRACT_RENEWAL",
                    severity="CRITICAL" if days_remaining <= 7 else "WARNING",
                    title=f"Contract expires in {days_remaining} day(s): {contract.contract_number}",
                    message=(
                        "Renewal is in progress."
                        if open_renewal
                        else "Renewal has not been started."
                    ),
                    deep_link=f"/contracts?section=contracts&contract_id={contract.id}&tab=renewals",
                    deduplication_key=key,
                )
                db.add(notification)
                db.flush()
            db.add(ContractExpirationNotificationDelivery(
                contract_id=contract.id,
                contract_end_date=contract.end_date,
                milestone_key=milestone,
                milestone_days=milestone_days,
                rule_version=rule_version,
                channel="SYSTEM",
                recipient_key=str(recipient.id),
                notification_id=notification.id,
                status="DELIVERED",
                sent_at=notification.created_at,
            ))
            reminders += 1
        if eligible_recipient_count == 0:
            milestone = f"d{milestone_days}" if milestone_days is not None else f"notice:{contract.renewal_notice_date}"
            missing_recipient_log = db.scalar(select(ContractExpirationNotificationDelivery.id).where(
                ContractExpirationNotificationDelivery.contract_id == contract.id,
                ContractExpirationNotificationDelivery.contract_end_date == contract.end_date,
                ContractExpirationNotificationDelivery.milestone_key == milestone,
                ContractExpirationNotificationDelivery.channel == "SYSTEM",
                ContractExpirationNotificationDelivery.recipient_key == "none",
            ))
            if not missing_recipient_log:
                db.add(ContractExpirationNotificationDelivery(
                    contract_id=contract.id,
                    contract_end_date=contract.end_date,
                    milestone_key=milestone,
                    milestone_days=milestone_days,
                    rule_version=rule_version,
                    channel="SYSTEM",
                    recipient_key="none",
                    status="SKIPPED",
                    last_error="No active system users are selected for this notification rule.",
                ))
        if email_enabled and to_addresses:
            milestone = f"d{milestone_days}" if milestone_days is not None else f"notice:{contract.renewal_notice_date}"
            applied = db.scalar(select(ContractExpirationNotificationDelivery).where(
                ContractExpirationNotificationDelivery.contract_id == contract.id,
                ContractExpirationNotificationDelivery.contract_end_date == contract.end_date,
                ContractExpirationNotificationDelivery.milestone_key == milestone,
                ContractExpirationNotificationDelivery.channel == "EMAIL",
                ContractExpirationNotificationDelivery.recipient_key == "rule",
            ))
            if applied:
                continue
            outbox_key = f"contract-expiration-email:{contract.id}:{contract.end_date}:{milestone}"
            existing_outbox = db.scalar(select(EventOutbox).where(EventOutbox.deduplication_key == outbox_key))
            if not existing_outbox:
                template_values = {
                    "contract_number": contract.contract_number,
                    "contract_name": contract.name,
                    "end_date": contract.end_date.isoformat(),
                    "days_remaining": days_remaining,
                    "renewal_status": "Renewal is in progress." if open_renewal else "Renewal has not been started.",
                }
                existing_outbox = EventOutbox(
                    event_type="CONTRACT_EXPIRATION_EMAIL",
                    aggregate_type="Contract",
                    aggregate_id=str(contract.id),
                    deduplication_key=outbox_key,
                    payload_json=json.dumps({
                        "to": list(dict.fromkeys(to_addresses)),
                        "cc": list(dict.fromkeys(cc_addresses)),
                        "subject": subject_template.format(**template_values),
                        "body": body_template.format(**template_values),
                        "deep_link": f"/contracts?section=contracts&contract_id={contract.id}&tab=renewals",
                    }),
                )
                db.add(existing_outbox)
                db.flush()
                emails += 1
            db.add(ContractExpirationNotificationDelivery(
                contract_id=contract.id,
                contract_end_date=contract.end_date,
                milestone_key=milestone,
                milestone_days=milestone_days,
                rule_version=rule_version,
                channel="EMAIL",
                recipient_key="rule",
                to_json=json.dumps(list(dict.fromkeys(to_addresses))),
                cc_json=json.dumps(list(dict.fromkeys(cc_addresses))),
                outbox_id=existing_outbox.id,
                status="SENT" if existing_outbox.status == "SENT" else ("FAILED" if existing_outbox.status == "DEAD" else "QUEUED"),
            ))
    recalculate_client_contract_service_status(
        db, {row.client_id for row in contracts} | linked_client_ids, today
    )
    db.commit()
    if metrics is not None:
        metrics.update({"contracts_scanned": len(contracts), "expired": expired, "reminders": reminders, "emails": emails})
    return expired + reminders + emails
