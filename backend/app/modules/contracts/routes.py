import json
from calendar import monthrange
from datetime import date, datetime, time, timedelta
from string import Formatter
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now, server_timezone, server_today
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import (
    Branch,
    City,
    Client,
    ClientDepartmentLink,
    ClientStatus,
    Contact,
    Country,
    Environment,
    Product,
    ProductModule,
    ServiceCatalogItem,
)
from app.modules.clients.schemas import BranchRead, ClientRead, ContactRead
from app.modules.configuration.models import SiteSetting
from app.modules.configuration.policy_service import resolve_feature_policy
from app.modules.contracts.access import can_access_contract, can_receive_renewal
from app.modules.contracts.attachments import contract_document_path, store_contract_document
from app.modules.contracts.dates import reconcile_contract_dates
from app.modules.contracts.lifecycle import recalculate_client_contract_service_status
from app.modules.contracts.models import (
    BusinessCalendar,
    BusinessCalendarDay,
    Contract,
    ContractClientLink,
    ContractCoverage,
    ContractCoverageClient,
    ContractCoverageRevision,
    ContractDocument,
    ContractExpirationNotificationDelivery,
    ContractRenewalLine,
    ContractRenewalOpportunity,
    ContractRenewalTask,
    ContractTemplate,
    ContractTemplateCoverage,
    ContractTemplateType,
    ContractType,
    SlaPolicy,
    SlaPolicyVersion,
    SlaShadowComparison,
    SlaTarget,
    SlaTargetVersion,
    TicketSlaClock,
)
from app.modules.contracts.renewals import apply_renewal_update, validate_renewal_owner
from app.modules.contracts.schemas import (
    CalendarRead,
    CalendarScheduleRead,
    CalendarScheduleWrite,
    ClientOnboardingRead,
    ClientOnboardingWrite,
    ContractBulkAssignmentCreate,
    ContractClientSelection,
    ContractClientSelectionPreview,
    ContractCoverageAmend,
    ContractCoverageCreate,
    ContractCoverageRead,
    ContractCoverageRetireBatch,
    ContractCoverageRevisionRead,
    ContractCreate,
    ContractDocumentRead,
    ContractFromTemplateWrite,
    ContractLifecycleTransition,
    ContractRead,
    ContractSlaRead,
    ContractSlaWrite,
    ContractTemplateApplyWrite,
    ContractTemplateCoverageWrite,
    ContractTemplatePreview,
    ContractTemplateRead,
    ContractTemplateTypeRead,
    ContractTemplateTypeWrite,
    ContractTemplateWrite,
    ContractTypeClientPage,
    ContractTypeDefaultsPreview,
    ContractTypeRead,
    ContractTypeWrite,
    ContractUpdate,
    ContractUsageRead,
    EntitlementCandidateRead,
    EntitlementCheckRead,
    RenewalLineRead,
    RenewalLineWrite,
    RenewalOpportunityCreate,
    RenewalOpportunityRead,
    RenewalOpportunityUpdate,
    SlaClockRead,
    SlaPolicyRead,
    SlaPolicyVersionRead,
    SlaPolicyWrite,
    SlaPresetWrite,
    SlaShadowComparisonRead,
    SlaTargetBulkWrite,
    SlaTargetRead,
    SlaTargetWrite,
)
from app.modules.contracts.service import (
    calculate_due_at,
    contract_usage,
    evaluate_entitlement,
    resolve_product_scoped_sla_target,
)
from app.modules.entitlements.models import ApprovalGroup
from app.modules.iam.models import AuditLog, Department, User
from app.modules.iam.service import effective_permissions
from app.modules.notifications.models import Notification
from app.modules.tickets.models import Ticket, TicketType
from app.modules.tickets.service import ensure_ticket_access
from app.modules.visits.models import (
    ClientVisitEntitlement,
    ClientVisitOccurrence,
    VisitEntitlementLedgerEntry,
    VisitType,
)

router = APIRouter(tags=["contracts and SLA"])

CONTRACT_NOTIFICATION_DEFAULT_SUBJECT = (
    "Contract {contract_number} — {contract_name} expires in {days_remaining} day(s)"
)
CONTRACT_NOTIFICATION_DEFAULT_BODY = "Contract {contract_number} ({contract_name}) expires on {end_date}. {renewal_status}"
CONTRACT_NOTIFICATION_PLACEHOLDERS = {
    "contract_number", "contract_name", "end_date", "days_remaining", "renewal_status"
}


class ContractExpirationNotificationSettings(BaseModel):
    enabled: bool = False
    reminder_days: list[int] = Field(default_factory=lambda: [60, 30, 14, 7, 0], min_length=1, max_length=20)
    to_user_ids: list[int] = Field(default_factory=list, max_length=100)
    cc_user_ids: list[int] = Field(default_factory=list, max_length=100)
    subject_template: str = Field(default=CONTRACT_NOTIFICATION_DEFAULT_SUBJECT, min_length=3, max_length=300)
    body_template: str = Field(default=CONTRACT_NOTIFICATION_DEFAULT_BODY, min_length=3, max_length=4000)
    version: int = Field(default=1, ge=1)

    @field_validator("reminder_days")
    @classmethod
    def normalize_days(cls, values: list[int]) -> list[int]:
        if any(value < 0 or value > 3650 for value in values):
            raise ValueError("Reminder days must be between 0 and 3650.")
        return sorted(set(values), reverse=True)

    @field_validator("to_user_ids", "cc_user_ids")
    @classmethod
    def normalize_users(cls, values: list[int]) -> list[int]:
        return list(dict.fromkeys(values))

    @model_validator(mode="after")
    def validate_delivery(self) -> "ContractExpirationNotificationSettings":
        if self.enabled and not self.to_user_ids:
            raise ValueError("Select at least one To user before enabling email notifications.")
        if set(self.to_user_ids) & set(self.cc_user_ids):
            raise ValueError("A user cannot be selected in both To and CC.")
        for template in (self.subject_template, self.body_template):
            try:
                fields = {field for _, field, _, _ in Formatter().parse(template) if field}
            except ValueError as exc:
                raise ValueError("Email templates contain unmatched braces.") from exc
            unsupported = fields - CONTRACT_NOTIFICATION_PLACEHOLDERS
            if unsupported:
                raise ValueError(f"Unsupported template placeholder: {sorted(unsupported)[0]}")
        return self


class ContractExpirationNotificationDeliveryRead(BaseModel):
    id: int
    contract_id: int
    contract_number: str
    contract_name: str
    contract_end_date: date
    milestone_key: str
    milestone_days: int | None
    rule_version: int
    channel: str
    recipient: str
    to: list[str]
    cc: list[str]
    status: str
    queued_at: datetime
    sent_at: datetime | None
    failed_at: datetime | None
    last_error: str | None


def contract_notification_settings(db: Session) -> ContractExpirationNotificationSettings:
    keys = {
        "enabled": "contract_expiration_notifications_enabled",
        "reminder_days": "contract_expiration_notification_days",
        "to_user_ids": "contract_expiration_notification_to_user_ids",
        "cc_user_ids": "contract_expiration_notification_cc_user_ids",
        "subject_template": "contract_expiration_notification_subject",
        "body_template": "contract_expiration_notification_body",
        "version": "contract_expiration_notification_version",
    }
    values = {key: db.get(SiteSetting, setting_key) for key, setting_key in keys.items()}
    to_user_ids = json.loads(values["to_user_ids"].value) if values["to_user_ids"] else []
    cc_user_ids = json.loads(values["cc_user_ids"].value) if values["cc_user_ids"] else []
    if not values["to_user_ids"]:
        legacy_to = db.get(SiteSetting, "contract_expiration_notification_to")
        legacy_cc = db.get(SiteSetting, "contract_expiration_notification_cc")
        legacy_to_addresses = {str(value).strip().lower() for value in json.loads(legacy_to.value)} if legacy_to else set()
        legacy_cc_addresses = {str(value).strip().lower() for value in json.loads(legacy_cc.value)} if legacy_cc else set()
        matched_users = list(db.scalars(select(User).where(
            User.is_active.in_([True]), User.user_type == "EMPLOYEE"
        )))
        to_user_ids = [user.id for user in matched_users if user.email and user.email.strip().lower() in legacy_to_addresses]
        cc_user_ids = [user.id for user in matched_users if user.email and user.email.strip().lower() in legacy_cc_addresses and user.id not in to_user_ids]
    requested_enabled = (values["enabled"].value.lower() == "true") if values["enabled"] else False
    return ContractExpirationNotificationSettings(
        enabled=requested_enabled and bool(to_user_ids),
        reminder_days=json.loads(values["reminder_days"].value) if values["reminder_days"] else [60, 30, 14, 7, 0],
        to_user_ids=to_user_ids,
        cc_user_ids=cc_user_ids,
        subject_template=values["subject_template"].value if values["subject_template"] else CONTRACT_NOTIFICATION_DEFAULT_SUBJECT,
        body_template=values["body_template"].value if values["body_template"] else CONTRACT_NOTIFICATION_DEFAULT_BODY,
        version=int(values["version"].value) if values["version"] else 1,
    )


@router.get("/contracts/notification-settings", response_model=ContractExpirationNotificationSettings)
def get_contract_notification_settings(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("contract.notification_rules.manage")),
) -> ContractExpirationNotificationSettings:
    return contract_notification_settings(db)


@router.put("/contracts/notification-settings", response_model=ContractExpirationNotificationSettings)
def update_contract_notification_settings(
    data: ContractExpirationNotificationSettings,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.notification_rules.manage")),
) -> ContractExpirationNotificationSettings:
    current = contract_notification_settings(db)
    if data.version != current.version:
        raise ConflictError("CONTRACT_NOTIFICATION_SETTINGS_CHANGED", "Contract notification settings changed; refresh and retry.")
    selected_ids = set(data.to_user_ids) | set(data.cc_user_ids)
    valid_ids = set(db.scalars(select(User.id).where(
        User.id.in_(selected_ids or {-1}),
        User.is_active.in_([True]),
        User.user_type == "EMPLOYEE",
        User.email.is_not(None),
    )))
    if valid_ids != selected_ids:
        raise ConflictError(
            "INVALID_CONTRACT_NOTIFICATION_RECIPIENT",
            "Select active system users who have an email address.",
        )
    before = current.model_dump(mode="json")
    next_version = current.version + 1
    stored = {
        "contract_expiration_notifications_enabled": str(data.enabled).lower(),
        "contract_expiration_notification_days": json.dumps(data.reminder_days),
        "contract_expiration_notification_to_user_ids": json.dumps(data.to_user_ids),
        "contract_expiration_notification_cc_user_ids": json.dumps(data.cc_user_ids),
        "contract_expiration_notification_subject": data.subject_template,
        "contract_expiration_notification_body": data.body_template,
        "contract_expiration_notification_version": str(next_version),
    }
    for key, value in stored.items():
        row = db.get(SiteSetting, key)
        if row:
            row.value = value
        else:
            db.add(SiteSetting(key=key, value=value))
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ContractNotificationSettings", entity_id="expiration", action="contract.notification_settings.updated", old_values_json=json.dumps(before), new_values_json=json.dumps({**data.model_dump(mode="json"), "version": next_version})))
    db.flush()
    # Apply the newly saved rule immediately. The normal scheduler remains
    # responsible for future milestones. Lifecycle processing commits the rule,
    # audit entry, and delivery evidence atomically on success.
    from app.modules.contracts.lifecycle import process_contract_lifecycle

    process_contract_lifecycle(db)
    return contract_notification_settings(db)


@router.get("/contracts/notification-recipient-options")
def contract_notification_recipient_options(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("contract.notification_rules.manage")),
) -> list[dict[str, object]]:
    users = db.scalars(
        select(User).where(
            User.is_active.in_([True]),
            User.user_type == "EMPLOYEE",
            User.email.is_not(None),
        ).order_by(User.full_name)
    )
    return [
        {"id": user.id, "full_name": user.full_name, "email": user.email}
        for user in users
        if user.email and user.email.strip()
    ]


@router.get(
    "/contracts/notification-deliveries",
    response_model=list[ContractExpirationNotificationDeliveryRead],
)
def contract_notification_deliveries(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("contract.notification_rules.manage")),
) -> list[ContractExpirationNotificationDeliveryRead]:
    rows = db.execute(
        select(ContractExpirationNotificationDelivery, Contract)
        .join(Contract, Contract.id == ContractExpirationNotificationDelivery.contract_id)
        .order_by(ContractExpirationNotificationDelivery.created_at.desc())
        .limit(limit)
    ).all()
    return [
        ContractExpirationNotificationDeliveryRead(
            id=delivery.id,
            contract_id=contract.id,
            contract_number=contract.contract_number,
            contract_name=contract.name,
            contract_end_date=delivery.contract_end_date,
            milestone_key=delivery.milestone_key,
            milestone_days=delivery.milestone_days,
            rule_version=delivery.rule_version,
            channel=delivery.channel,
            recipient=delivery.recipient_key,
            to=json.loads(delivery.to_json or "[]"),
            cc=json.loads(delivery.cc_json or "[]"),
            status=delivery.status,
            queued_at=delivery.queued_at,
            sent_at=delivery.sent_at,
            failed_at=delivery.failed_at,
            last_error=delivery.last_error,
        )
        for delivery, contract in rows
    ]


@router.get("/contracts/options/approval-groups")
def contract_approval_group_options(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("contract.manage")),
) -> list[dict[str, object]]:
    return [{"id": row.id, "name": row.name} for row in db.scalars(
        select(ApprovalGroup).where(ApprovalGroup.is_active.in_([True])).order_by(ApprovalGroup.name)
    )]


def validate_contract_approval_group(db: Session, group_id: int | None) -> None:
    if group_id is None:
        return
    group = db.get(ApprovalGroup, group_id)
    if not group or not group.is_active:
        raise ConflictError("INVALID_APPROVAL_GROUP", "Choose an active approval group, or use the default support managers.")


@router.get("/contracts/{contract_id}/contacts", response_model=list[ContactRead])
def contract_contacts(contract_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("contract.view"))) -> list[Contact]:
    if actor.user_type == "CLIENT_PORTAL":
        raise NotFoundError("Contract does not exist.")
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    statement = select(Contact).where(Contact.is_active.in_([True]))
    if actor.user_type == "CLIENT_PORTAL":
        statement = statement.where(Contact.client_id.in_(effective_permissions(db, actor).client_scope_ids))
    if not contract.applies_to_all_clients:
        statement = statement.where(Contact.client_id.in_(contract.customer_ids))
    return list(db.scalars(statement.order_by(Contact.full_name)))


@router.get("/contracts/{contract_id}/branches", response_model=list[BranchRead])
def contract_branches(contract_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("contract.view"))) -> list[Branch]:
    if actor.user_type == "CLIENT_PORTAL":
        raise NotFoundError("Contract does not exist.")
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    statement = select(Branch).where(Branch.is_active.in_([True]))
    if actor.user_type == "CLIENT_PORTAL":
        statement = statement.where(Branch.client_id.in_(effective_permissions(db, actor).client_scope_ids))
    if not contract.applies_to_all_clients:
        statement = statement.where(Branch.client_id.in_(contract.customer_ids))
    return list(db.scalars(statement.order_by(Branch.name)))


def contract_type_client_ids(type_id: int):  # type: ignore[no-untyped-def]
    direct = select(Contract.client_id.label("client_id")).where(
        Contract.contract_type_id == type_id
    )
    linked = (
        select(ContractClientLink.client_id.label("client_id"))
        .join(Contract, Contract.id == ContractClientLink.contract_id)
        .where(Contract.contract_type_id == type_id)
    )
    return direct.union(linked).subquery()


def contract_type_client_count(db: Session, type_id: int) -> int:
    has_global = db.scalar(
        select(Contract.id)
        .where(
            Contract.contract_type_id == type_id,
            Contract.applies_to_all_clients.in_([True]),
        )
        .limit(1)
    )
    if has_global:
        return int(db.scalar(select(func.count(Client.id))) or 0)
    client_ids = contract_type_client_ids(type_id)
    return int(db.scalar(select(func.count()).select_from(client_ids)) or 0)


def add_calendar_months(value: date, months: int) -> date:
    target = value.month - 1 + months
    year = value.year + target // 12
    month = target % 12 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def template_preview(
    item: ContractTemplate, start: date, duration: int | None = None, name: str | None = None
) -> ContractTemplatePreview:
    months = duration or item.default_duration_months
    return ContractTemplatePreview(
        template_id=item.id,
        template_version=item.version,
        name=name or item.name,
        start_date=start,
        end_date=add_calendar_months(start, months) - timedelta(days=1),
        duration_months=months,
        contract_type_id=item.contract_type_id,
        calendar_id=item.calendar_id,
        sla_policy_id=item.sla_policy_id,
        has_sla=item.has_sla,
        coverage_validation_level=item.coverage_validation_level,
        expiry_grace_days=item.expiry_grace_days,
        approval_group_id=item.approval_group_id,
        support_summary=item.support_summary,
        exclusions=item.exclusions,
        included_request_limit=item.included_request_limit,
        coverages=[
            ContractTemplateCoverageWrite.model_validate(row, from_attributes=True)
            for row in item.coverages
        ],
    )


def replace_template_coverages(
    item: ContractTemplate, rows: list[ContractTemplateCoverageWrite]
) -> None:
    item.coverages = [ContractTemplateCoverage(**row.model_dump()) for row in rows]


def sla_policy_ready(db: Session, policy: SlaPolicy | None) -> bool:
    if not policy or not policy.is_active:
        return False
    published_id = db.scalar(select(SlaPolicyVersion.id).where(
        SlaPolicyVersion.policy_id == policy.id,
        SlaPolicyVersion.version == policy.version,
        SlaPolicyVersion.status == "PUBLISHED",
    ))
    return published_id is not None and db.scalar(select(SlaTargetVersion.id).where(
        SlaTargetVersion.policy_version_id == published_id,
    )) is not None


def validate_template(db: Session, data: ContractTemplateWrite) -> None:
    template_type = db.scalar(
        select(ContractTemplateType).where(
            ContractTemplateType.code == data.template_type,
            ContractTemplateType.is_active.in_([True]),
        )
    )
    if not template_type:
        raise ConflictError(
            "INVALID_CONTRACT_TEMPLATE_TYPE", "Select an active contract template type."
        )
    if not db.get(BusinessCalendar, data.calendar_id):
        raise NotFoundError("Business calendar does not exist.")
    if data.contract_type_id and not db.get(ContractType, data.contract_type_id):
        raise NotFoundError("Contract type does not exist.")
    validate_contract_approval_group(db, data.approval_group_id)
    if data.has_sla and data.sla_policy_id and not sla_policy_ready(db, db.get(SlaPolicy, data.sla_policy_id)):
        raise ConflictError("SLA_POLICY_NOT_READY", "The SLA policy needs active published targets.")
    for row in data.coverages:
        product = db.get(Product, row.product_id) if row.product_id else None
        module = db.get(ProductModule, row.product_module_id) if row.product_module_id else None
        if row.product_id and (not product or not product.is_active):
            raise ConflictError("INVALID_TEMPLATE_PRODUCT", "Template products must be active.")
        if row.product_module_id and (
            not module or not module.is_active or module.product_id != row.product_id
        ):
            raise ConflictError(
                "INVALID_TEMPLATE_MODULE",
                "Each template module must belong to its selected active product.",
            )


@router.get("/contract-template-types", response_model=list[ContractTemplateTypeRead])
def list_contract_template_types(
    active_only: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("contract.template.view")),
) -> list[ContractTemplateType]:
    statement = select(ContractTemplateType)
    if active_only:
        statement = statement.where(ContractTemplateType.is_active.in_([True]))
    return list(db.scalars(statement.order_by(ContractTemplateType.name)))


@router.post("/contract-template-types", response_model=ContractTemplateTypeRead, status_code=201)
def create_contract_template_type(
    data: ContractTemplateTypeWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.template.manage")),
) -> ContractTemplateType:
    item = ContractTemplateType(
        code=f"PENDING-{server_now().timestamp()}", **data.model_dump(), created_by_user_id=actor.id
    )
    db.add(item)
    db.flush()
    item.code = f"CTT-{item.id:06d}"
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ContractTemplateType",
            entity_id=str(item.id),
            action="contract.template_type.created",
            new_values_json=json.dumps(data.model_dump(), default=str),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.patch("/contract-template-types/{type_id}", response_model=ContractTemplateTypeRead)
def update_contract_template_type(
    type_id: int,
    data: ContractTemplateTypeWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.template.manage")),
) -> ContractTemplateType:
    item = db.get(ContractTemplateType, type_id)
    if not item:
        raise NotFoundError("Contract template type does not exist.")
    old = {"name": item.name, "description": item.description, "is_active": item.is_active}
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ContractTemplateType",
            entity_id=str(item.id),
            action="contract.template_type.updated",
            old_values_json=json.dumps(old),
            new_values_json=json.dumps(data.model_dump()),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.delete("/contract-template-types/{type_id}", status_code=204)
def delete_contract_template_type(
    type_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.template.manage")),
) -> None:
    item = db.get(ContractTemplateType, type_id)
    if not item:
        raise NotFoundError("Contract template type does not exist.")
    if db.scalar(select(ContractTemplate.id).where(ContractTemplate.template_type == item.code)):
        raise ConflictError(
            "CONTRACT_TEMPLATE_TYPE_IN_USE",
            "Deactivate this type instead because templates already use it.",
        )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ContractTemplateType",
            entity_id=str(item.id),
            action="contract.template_type.deleted",
            old_values_json=json.dumps({"code": item.code, "name": item.name}),
        )
    )
    db.delete(item)
    db.commit()


@router.get("/contract-templates", response_model=list[ContractTemplateRead])
def list_contract_templates(
    active_only: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("contract.template.view")),
) -> list[ContractTemplate]:
    statement = select(ContractTemplate)
    if active_only:
        statement = statement.where(ContractTemplate.is_active.in_([True]))
    return list(
        db.scalars(statement.order_by(ContractTemplate.is_default.desc(), ContractTemplate.name))
    )


@router.post("/contract-templates", response_model=ContractTemplateRead, status_code=201)
def create_contract_template(
    data: ContractTemplateWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.template.manage")),
) -> ContractTemplate:
    validate_template(db, data)
    values = data.model_dump(exclude={"coverages"})
    if data.is_default:
        db.query(ContractTemplate).update({ContractTemplate.is_default: False})
    requested_code = values.pop("code", None)
    item = ContractTemplate(
        code=requested_code or f"PENDING-{server_now().timestamp()}",
        **values,
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    replace_template_coverages(item, data.coverages)
    db.add(item)
    db.flush()
    if not requested_code:
        item.code = f"CTP-{item.id:06d}"
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "DUPLICATE_CONTRACT_TEMPLATE", "That template code is already in use."
        ) from exc
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ContractTemplate",
            entity_id=str(item.id),
            action="contract.template.created",
            new_values_json=json.dumps(data.model_dump(), default=str),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.patch("/contract-templates/{template_id}", response_model=ContractTemplateRead)
def update_contract_template(
    template_id: int,
    data: ContractTemplateWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.template.manage")),
) -> ContractTemplate:
    item = db.get(ContractTemplate, template_id)
    if not item:
        raise NotFoundError("Contract template does not exist.")
    validate_template(db, data)
    old = {key: getattr(item, key) for key in data.model_dump(exclude={"coverages"})}
    if data.is_default:
        db.query(ContractTemplate).filter(ContractTemplate.id != item.id).update(
            {ContractTemplate.is_default: False}
        )
    for key, value in data.model_dump(exclude={"coverages", "code"}).items():
        setattr(item, key, value)
    replace_template_coverages(item, data.coverages)
    item.version += 1
    item.updated_by_user_id = actor.id
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ContractTemplate",
            entity_id=str(item.id),
            action="contract.template.updated",
            old_values_json=json.dumps(old, default=str),
            new_values_json=json.dumps(data.model_dump(), default=str),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.post(
    "/contract-templates/{template_id}/clone", response_model=ContractTemplateRead, status_code=201
)
def clone_contract_template(
    template_id: int,
    name: str = Query(min_length=2, max_length=150),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.template.manage")),
) -> ContractTemplate:
    source = db.get(ContractTemplate, template_id)
    if not source:
        raise NotFoundError("Contract template does not exist.")
    item = ContractTemplate(
        code=f"PENDING-{server_now().timestamp()}",
        name=name,
        description=source.description,
        template_type=source.template_type,
        contract_type_id=source.contract_type_id,
        calendar_id=source.calendar_id,
        sla_policy_id=source.sla_policy_id,
        default_duration_months=source.default_duration_months,
        has_sla=source.has_sla,
        ticket_catalog_visibility=source.ticket_catalog_visibility,
        require_product_on_ticket=source.require_product_on_ticket,
        require_module_on_ticket=source.require_module_on_ticket,
        require_service_on_ticket=source.require_service_on_ticket,
        coverage_validation_level=source.coverage_validation_level,
        expiry_grace_days=source.expiry_grace_days,
        approval_group_id=source.approval_group_id,
        support_summary=source.support_summary,
        exclusions=source.exclusions,
        included_request_limit=source.included_request_limit,
        default_billing_frequency=source.default_billing_frequency,
        default_payment_terms_days=source.default_payment_terms_days,
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    item.coverages = [
        ContractTemplateCoverage(
            product_id=row.product_id,
            product_module_id=row.product_module_id,
            environment_id=row.environment_id,
            service_id=row.service_id,
            ticket_type_id=row.ticket_type_id,
            is_covered=row.is_covered,
            notes=row.notes,
        )
        for row in source.coverages
    ]
    db.add(item)
    db.flush()
    item.code = f"CTP-{item.id:06d}"
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "DUPLICATE_CONTRACT_TEMPLATE", "That template code is already in use."
        ) from exc
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ContractTemplate",
            entity_id=str(item.id),
            action="contract.template.cloned",
            new_values_json=json.dumps({"source_template_id": source.id}),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.post("/contract-templates/{template_id}/make-default", response_model=ContractTemplateRead)
def make_default_contract_template(
    template_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.template.manage")),
) -> ContractTemplate:
    item = db.get(ContractTemplate, template_id)
    if not item or not item.is_active:
        raise ConflictError("INVALID_DEFAULT_TEMPLATE", "Select an active contract template.")
    db.query(ContractTemplate).update({ContractTemplate.is_default: False})
    item.is_default = True
    item.updated_by_user_id = actor.id
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ContractTemplate",
            entity_id=str(item.id),
            action="contract.template.defaulted",
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.post("/contract-templates/{template_id}/preview", response_model=ContractTemplatePreview)
def preview_contract_template(
    template_id: int,
    start_date: date,
    duration_months: int | None = Query(default=None, ge=1, le=120),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("contract.template.view")),
) -> ContractTemplatePreview:
    item = db.get(ContractTemplate, template_id)
    if not item or not item.is_active:
        raise NotFoundError("Active contract template does not exist.")
    return template_preview(item, start_date, duration_months)


@router.get("/contract-types", response_model=list[ContractTypeRead])
def list_contract_types(
    active_only: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("contract.view")),
) -> list[dict[str, object]]:
    statement = select(ContractType)
    if active_only:
        statement = statement.where(ContractType.is_active.in_([True]))
    items = list(db.scalars(statement.order_by(ContractType.precedence, ContractType.name)))
    return [
        {
            **ContractTypeRead.model_validate(item).model_dump(),
            "linked_client_count": contract_type_client_count(db, item.id),
        }
        for item in items
    ]


@router.get("/contract-types/{type_id}/clients", response_model=ContractTypeClientPage)
def list_contract_type_clients(
    type_id: int,
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("contract.view")),
) -> ContractTypeClientPage:
    item = db.get(ContractType, type_id)
    if not item:
        raise NotFoundError("Contract type does not exist.")
    has_global = db.scalar(
        select(Contract.id)
        .where(
            Contract.contract_type_id == type_id,
            Contract.applies_to_all_clients.in_([True]),
        )
        .limit(1)
    )
    statement = select(Client)
    if not has_global:
        client_ids = contract_type_client_ids(type_id)
        statement = statement.join(client_ids, client_ids.c.client_id == Client.id)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        statement = statement.where(or_(Client.code.ilike(pattern), Client.name.ilike(pattern)))
    total = int(
        db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    )
    rows = list(db.scalars(statement.order_by(Client.name, Client.id).limit(limit).offset(offset)))
    return ContractTypeClientPage(
        items=[
            {"id": row.id, "code": row.code, "name": row.name, "is_active": row.is_active}
            for row in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/contract-types", response_model=ContractTypeRead, status_code=201)
def create_contract_type(
    data: ContractTypeWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> ContractType:
    if db.scalar(select(ContractType.id).where(ContractType.name == data.name)):
        raise ConflictError(
            "DUPLICATE_CONTRACT_TYPE", "A contract type with this code or name already exists."
        )
    values = data.model_dump()
    requested_code = values.pop("code", None)
    item = ContractType(
        code=requested_code or f"PENDING-CTY-{server_now().timestamp()}", **values, is_system=False
    )
    db.add(item)
    db.flush()
    if not requested_code:
        item.code = f"CTY-{item.id:06d}"
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ContractType",
            entity_id=str(item.id),
            action="contract_type.created",
            new_values_json=json.dumps(data.model_dump()),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.put("/contract-types/{type_id}", response_model=ContractTypeRead)
def update_contract_type(
    type_id: int,
    data: ContractTypeWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> ContractType:
    item = db.get(ContractType, type_id)
    if not item:
        raise NotFoundError("Contract type does not exist.")
    if item.is_system and data.code is not None and data.code != item.code:
        raise ConflictError(
            "SYSTEM_CONTRACT_TYPE_CODE", "The code of a system contract type cannot be changed."
        )
    duplicate = (
        db.scalar(
            select(ContractType.id).where(
                or_(ContractType.code == data.code, ContractType.name == data.name),
                ContractType.id != item.id,
            )
        )
        if data.code
        else db.scalar(
            select(ContractType.id).where(
                ContractType.name == data.name, ContractType.id != item.id
            )
        )
    )
    if duplicate:
        raise ConflictError(
            "DUPLICATE_CONTRACT_TYPE", "A contract type with this code or name already exists."
        )
    old = {field: getattr(item, field) for field in data.model_dump()}
    for field, value in data.model_dump(exclude={"code"} if data.code is None else set()).items():
        setattr(item, field, value)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ContractType",
            entity_id=str(item.id),
            action="contract_type.updated",
            old_values_json=json.dumps(old),
            new_values_json=json.dumps(data.model_dump()),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get(
    "/contract-types/{type_id}/defaults-preview",
    response_model=ContractTypeDefaultsPreview,
)
def preview_contract_type_defaults(
    type_id: int,
    client_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.view")),
) -> ContractTypeDefaultsPreview:
    ensure_contract_client_access(db, actor, client_id)
    item = db.get(ContractType, type_id)
    if not item or not item.is_active:
        raise NotFoundError("Contract type does not exist or is inactive.")
    policy = resolve_feature_policy(db, "contract_types", client_id=client_id)
    return ContractTypeDefaultsPreview(
        contract_type_id=item.id,
        code=item.code,
        feature_mode=policy.mode,
        source_scope=policy.source_scope,
        default_has_sla=item.default_has_sla,
        default_duration_days=item.default_duration_days,
        expiry_behavior=item.expiry_behavior,
        approval_behavior=item.approval_behavior,
        type_required=policy.mode == "ENFORCED",
    )


def contract_type_for_write(
    db: Session, type_id: int | None, *, client_id: int
) -> tuple[ContractType, str]:
    policy = resolve_feature_policy(db, "contract_types", client_id=client_id)
    if type_id is None:
        if policy.mode == "ENFORCED":
            raise ConflictError(
                "CONTRACT_TYPE_REQUIRED",
                "Select an active contract type before saving the contract.",
            )
        item = db.scalar(select(ContractType).where(ContractType.code == "LEGACY"))
    else:
        item = db.get(ContractType, type_id)
    if not item or not item.is_active:
        raise ConflictError("INVALID_CONTRACT_TYPE", "The selected contract type is not active.")
    return item, policy.mode


def sla_policy_read(db: Session, policy: SlaPolicy) -> SlaPolicyRead:
    targets = list(
        db.scalars(
            select(SlaTarget)
            .where(SlaTarget.policy_id == policy.id)
            .order_by(SlaTarget.service_id, SlaTarget.priority)
        )
    )
    return SlaPolicyRead(
        id=policy.id,
        code=policy.code,
        name=policy.name,
        calendar_id=policy.calendar_id,
        is_active=policy.is_active,
        include_escalation_time=policy.include_escalation_time,
        targets=targets,
    )


def sla_target_context_key(data: SlaTargetWrite) -> str:
    return f"P{data.product_id or 0}:M{data.product_module_id or 0}:S{data.service_id or 0}:PR{data.priority}"


def validate_sla_target_context(db: Session, data: SlaTargetWrite) -> None:
    if data.product_id is not None and not db.get(Product, data.product_id):
        raise NotFoundError("Product does not exist.")
    if data.product_module_id is not None:
        module = db.get(ProductModule, data.product_module_id)
        if not module or module.product_id != data.product_id:
            raise ConflictError(
                "INVALID_SLA_MODULE", "The SLA module does not belong to the selected product."
            )
    if data.service_id is not None and not db.get(ServiceCatalogItem, data.service_id):
        raise NotFoundError("Service does not exist.")


@router.get("/sla-policies", response_model=list[SlaPolicyRead])
def list_sla_policies(
    db: Session = Depends(get_db), _: User = Depends(require_permission("contract.view"))
) -> list[SlaPolicyRead]:
    return [
        sla_policy_read(db, item)
        for item in db.scalars(
            select(SlaPolicy).where(SlaPolicy.contract_id.is_(None)).order_by(SlaPolicy.name)
        )
    ]


@router.get("/sla-policies/{policy_id}/usage")
def sla_policy_usage(
    policy_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("contract.view")),
) -> dict[str, int]:
    policy = db.get(SlaPolicy, policy_id)
    if not policy or policy.contract_id is not None:
        raise NotFoundError("Central SLA policy does not exist.")
    return {
        "contracts": db.scalar(select(func.count()).select_from(Contract).where(
            Contract.sla_policy_id == policy_id
        )) or 0,
        "templates": db.scalar(select(func.count()).select_from(ContractTemplate).where(
            ContractTemplate.sla_policy_id == policy_id
        )) or 0,
        "ticket_clocks": db.scalar(select(func.count()).select_from(TicketSlaClock).where(
            TicketSlaClock.policy_id == policy_id
        )) or 0,
    }


@router.post("/sla-policies", response_model=SlaPolicyRead, status_code=201)
def create_sla_policy(
    data: SlaPolicyWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> SlaPolicyRead:
    if not db.get(BusinessCalendar, data.calendar_id):
        raise NotFoundError("Business calendar does not exist.")
    if data.code and db.scalar(select(SlaPolicy.id).where(SlaPolicy.code == data.code)):
        raise ConflictError("DUPLICATE_SLA_POLICY", "An SLA policy with this code already exists.")
    values = data.model_dump()
    requested_code = values.pop("code", None)
    policy = SlaPolicy(
        # Keep the temporary value inside the same character contract as a final
        # policy code. SQL Server installations may enforce that constraint even
        # though the value is replaced immediately after the identity flush.
        code=requested_code or f"PENDING-SLA-{uuid4().hex[:20].upper()}",
        **values,
        contract_id=None,
    )
    db.add(policy)
    db.flush()
    if not requested_code:
        policy.code = f"SLA-{policy.id:06d}"
    db.add(
        SlaPolicyVersion(
            policy_id=policy.id,
            version=1,
            name_snapshot=policy.name,
            calendar_id=policy.calendar_id,
            calculation_version=policy.calculation_version,
            include_escalation_time=policy.include_escalation_time,
            status="DRAFT",
            effective_from=server_today(),
            created_by_user_id=actor.id,
            published_at=None,
        )
    )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="SlaPolicy",
            entity_id=str(policy.id),
            action="sla.policy.created",
        )
    )
    db.commit()
    db.refresh(policy)
    return sla_policy_read(db, policy)


@router.post("/sla-policies/presets/l1-l4", response_model=SlaPolicyRead, status_code=201)
def create_l1_l4_sla_preset(
    data: SlaPresetWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> SlaPolicyRead:
    if not db.get(BusinessCalendar, data.calendar_id):
        raise NotFoundError("Business calendar does not exist.")
    code = data.code or "STANDARD_SUPPORT_L1_L4"
    if db.scalar(select(SlaPolicy.id).where(SlaPolicy.code == code)):
        raise ConflictError(
            "DUPLICATE_SLA_POLICY",
            "The standard L1-L4 SLA template already exists. Open the existing template instead.",
        )
    policy = SlaPolicy(
        code=code,
        name=data.name,
        calendar_id=data.calendar_id,
        contract_id=None,
        is_active=data.is_active,
        include_escalation_time=data.include_escalation_time,
    )
    db.add(policy)
    db.flush()
    targets = (
        ("P1", 15, 60, 50),
        ("P2", 30, 180, 67),
        ("P3", 60, 4800, 75),
        ("P4", 240, 14400, 80),
    )
    for priority, response, resolution, warning in targets:
        db.add(
            SlaTarget(
                policy_id=policy.id,
                product_id=None,
                product_module_id=None,
                service_id=None,
                priority=priority,
                context_key=f"*:*:*:{priority}",
                is_fallback=True,
                first_response_minutes=response,
                resolution_minutes=resolution,
                warning_percent=warning,
            )
        )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="SlaPolicy",
            entity_id=str(policy.id),
            action="sla.policy.l1_l4_preset_created",
            new_values_json=json.dumps({"code": code, "targets": [row[0] for row in targets]}),
        )
    )
    db.commit()
    db.refresh(policy)
    publish_sla_policy(policy.id, db, actor)
    return sla_policy_read(db, policy)


@router.put("/sla-policies/{policy_id}", response_model=SlaPolicyRead)
def update_sla_policy(
    policy_id: int,
    data: SlaPolicyWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> SlaPolicyRead:
    policy = db.get(SlaPolicy, policy_id)
    if not policy or policy.contract_id is not None:
        raise NotFoundError("Central SLA policy does not exist.")
    if not db.get(BusinessCalendar, data.calendar_id):
        raise NotFoundError("Business calendar does not exist.")
    if data.code and db.scalar(
        select(SlaPolicy.id).where(SlaPolicy.code == data.code, SlaPolicy.id != policy_id)
    ):
        raise ConflictError("DUPLICATE_SLA_POLICY", "An SLA policy with this code already exists.")
    for field, value in data.model_dump(exclude={"code"} if data.code is None else set()).items():
        setattr(policy, field, value)
    policy.calculation_version = "2.0"
    policy.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="SlaPolicy",
            entity_id=str(policy.id),
            action="sla.policy.updated",
            new_values_json=json.dumps(data.model_dump()),
        )
    )
    db.flush()
    if policy.is_active and db.scalar(select(SlaTarget.id).where(SlaTarget.policy_id == policy_id)):
        publish_sla_policy(policy_id, db, actor)
    else:
        db.commit()
    db.refresh(policy)
    return sla_policy_read(db, policy)


@router.delete("/sla-policies/{policy_id}", status_code=204)
def delete_sla_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> None:
    policy = db.get(SlaPolicy, policy_id)
    if not policy or policy.contract_id is not None:
        raise NotFoundError("Central SLA policy does not exist.")
    if any((
        db.scalar(select(Contract.id).where(Contract.sla_policy_id == policy_id)),
        db.scalar(select(ContractTemplate.id).where(ContractTemplate.sla_policy_id == policy_id)),
        db.scalar(select(TicketSlaClock.id).where(TicketSlaClock.policy_id == policy_id)),
        db.scalar(select(SlaShadowComparison.id).where(SlaShadowComparison.policy_id == policy_id)),
    )):
        raise ConflictError(
            "SLA_POLICY_IN_USE",
            "This SLA is linked to contracts, templates, or ticket history. Deactivate it instead.",
        )
    version_ids = select(SlaPolicyVersion.id).where(SlaPolicyVersion.policy_id == policy_id)
    db.execute(delete(SlaTargetVersion).where(SlaTargetVersion.policy_version_id.in_(version_ids)))
    db.execute(delete(SlaPolicyVersion).where(SlaPolicyVersion.policy_id == policy_id))
    db.execute(delete(SlaTarget).where(SlaTarget.policy_id == policy_id))
    db.delete(policy)
    db.add(AuditLog(
        actor_user_id=actor.id,
        entity_type="SlaPolicy",
        entity_id=str(policy_id),
        action="sla.policy.deleted",
        old_values_json=json.dumps({"code": policy.code, "name": policy.name}),
    ))
    db.commit()


@router.post("/sla-policies/{policy_id}/targets", response_model=SlaTargetRead, status_code=201)
def save_policy_target(
    policy_id: int,
    data: SlaTargetWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> SlaTarget:
    policy = db.get(SlaPolicy, policy_id)
    if not policy or policy.contract_id is not None:
        raise NotFoundError("Central SLA policy does not exist.")
    validate_sla_target_context(db, data)
    target = db.scalar(
        select(SlaTarget).where(
            SlaTarget.policy_id == policy_id, SlaTarget.context_key == sla_target_context_key(data)
        )
    )
    if target:
        for field, value in data.model_dump().items():
            setattr(target, field, value)
        target.version += 1
    else:
        target = SlaTarget(policy_id=policy_id, **data.model_dump())
        db.add(target)
    policy.version += 1
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="SlaTarget",
            entity_id=str(target.id),
            action="sla.policy.target.saved",
        )
    )
    if policy.is_active:
        publish_sla_policy(policy_id, db, actor)
    else:
        db.commit()
    db.refresh(target)
    return target


@router.delete("/sla-policies/{policy_id}/targets/{target_id}", status_code=204)
def delete_policy_target(
    policy_id: int,
    target_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> None:
    policy = db.get(SlaPolicy, policy_id)
    target = db.get(SlaTarget, target_id)
    if not policy or policy.contract_id is not None or not target or target.policy_id != policy_id:
        raise NotFoundError("Central SLA target does not exist.")
    if db.scalar(select(TicketSlaClock.id).where(TicketSlaClock.target_id == target_id)):
        raise ConflictError(
            "SLA_TARGET_IN_USE", "This target has ticket history and cannot be deleted."
        )
    has_remaining = db.scalar(select(SlaTarget.id).where(SlaTarget.policy_id == policy_id, SlaTarget.id != target_id)) is not None
    if not has_remaining and (
        db.scalar(select(Contract.id).where(Contract.sla_policy_id == policy_id))
        or db.scalar(select(ContractTemplate.id).where(ContractTemplate.sla_policy_id == policy_id))
    ):
        raise ConflictError("SLA_TARGETS_REQUIRED", "Linked contracts and templates require at least one SLA target.")
    db.execute(update(SlaTargetVersion).where(SlaTargetVersion.source_target_id == target_id).values(source_target_id=None))
    db.delete(target)
    policy.version += 1
    db.add(AuditLog(
        actor_user_id=actor.id,
        entity_type="SlaTarget",
        entity_id=str(target_id),
        action="sla.policy.target.deleted",
    ))
    db.flush()
    if policy.is_active and has_remaining:
        publish_sla_policy(policy_id, db, actor)
    else:
        policy.is_active = False
        db.commit()


@router.get("/sla-policies/{policy_id}/versions", response_model=list[SlaPolicyVersionRead])
def list_sla_policy_versions(
    policy_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("contract.view")),
) -> list[SlaPolicyVersion]:
    if not db.get(SlaPolicy, policy_id):
        raise NotFoundError("SLA policy does not exist.")
    return list(
        db.scalars(
            select(SlaPolicyVersion)
            .where(SlaPolicyVersion.policy_id == policy_id)
            .order_by(SlaPolicyVersion.version.desc())
        )
    )


@router.post(
    "/sla-policies/{policy_id}/publish", response_model=SlaPolicyVersionRead, status_code=201
)
def publish_sla_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> SlaPolicyVersion:
    policy = db.get(SlaPolicy, policy_id)
    if not policy:
        raise NotFoundError("SLA policy does not exist.")
    existing = db.scalar(
        select(SlaPolicyVersion).where(
            SlaPolicyVersion.policy_id == policy_id, SlaPolicyVersion.version == policy.version
        )
    )
    if existing:
        if db.scalar(select(SlaTargetVersion.id).where(SlaTargetVersion.policy_version_id == existing.id)):
            return existing
        raise ConflictError("SLA_TARGETS_REQUIRED", "At least one target is required before publication.")
    now = server_now()
    previous = db.scalar(
        select(SlaPolicyVersion)
        .where(SlaPolicyVersion.policy_id == policy_id, SlaPolicyVersion.status == "PUBLISHED")
        .order_by(SlaPolicyVersion.version.desc())
    )
    if previous:
        previous.status = "RETIRED"
        previous.effective_until = now
    version = SlaPolicyVersion(
        policy_id=policy.id,
        version=policy.version,
        name_snapshot=policy.name,
        calendar_id=policy.calendar_id,
        calculation_version=policy.calculation_version,
        include_escalation_time=policy.include_escalation_time,
        effective_from=now,
        status="PUBLISHED",
        created_by_user_id=actor.id,
        published_at=now,
    )
    db.add(version)
    db.flush()
    targets = list(db.scalars(select(SlaTarget).where(SlaTarget.policy_id == policy_id)))
    if not targets:
        raise ConflictError(
            "SLA_TARGETS_REQUIRED", "At least one target is required before publication."
        )
    for target in targets:
        db.add(
            SlaTargetVersion(
                policy_version_id=version.id,
                source_target_id=target.id,
                product_id=target.product_id,
                product_module_id=target.product_module_id,
                service_id=target.service_id,
                priority=target.priority,
                context_key=target.context_key,
                is_fallback=target.is_fallback,
                effective_from=target.effective_from,
                effective_until=target.effective_until,
                first_response_minutes=target.first_response_minutes,
                resolution_minutes=target.resolution_minutes,
                warning_percent=target.warning_percent,
            )
        )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="SlaPolicyVersion",
            entity_id=str(version.id),
            action="sla.policy.published",
            new_values_json=json.dumps({"policy_id": policy_id, "version": policy.version}),
        )
    )
    db.commit()
    db.refresh(version)
    return version


def ensure_contract_access(db: Session, user: User, contract: Contract) -> None:
    if not can_access_contract(db, user, contract):
        raise NotFoundError("Contract does not exist.")


def replace_contract_clients(db: Session, contract: Contract, client_ids: list[int]) -> None:
    selected = sorted(set(client_ids))
    if not selected:
        raise ConflictError("CONTRACT_CLIENTS_REQUIRED", "Select at least one contract client.")
    existing = set(db.scalars(select(Client.id).where(Client.id.in_(selected))))
    if existing != set(selected):
        raise NotFoundError("One or more linked clients do not exist.")
    selected_ids = set(selected)
    validate_escalation_contact(db, selected_ids, contract.escalation_contact_id, contract.applies_to_all_clients)
    removed_ids = contract.customer_ids - selected_ids
    if removed_ids and not contract.applies_to_all_clients:
        for coverage in db.scalars(select(ContractCoverage).where(
            ContractCoverage.contract_id == contract.id, ContractCoverage.retired_at.is_(None)
        )):
            if coverage.client_ids and not (set(coverage.client_ids) & selected_ids):
                raise ConflictError("CLIENT_HAS_SCOPED_COVERAGE", f"Coverage #{coverage.id} only applies to clients being removed. Retire or reassign that coverage first.")
            if coverage.branch_id:
                branch = db.get(Branch, coverage.branch_id)
                if branch and branch.client_id not in selected_ids:
                    raise ConflictError("CLIENT_HAS_SCOPED_COVERAGE", f"Coverage #{coverage.id} uses a branch of a client being removed. Retire it first.")
    # Keep the legacy non-null FK valid without assigning ownership or preventing removal.
    contract.client_id = selected[0]
    existing_links = {link.client_id: link for link in contract.client_links}
    for client_id, link in existing_links.items():
        if client_id not in selected_ids:
            contract.client_links.remove(link)
    for client_id in selected:
        if client_id not in existing_links:
            contract.client_links.append(ContractClientLink(client_id=client_id))


def ensure_contract_client_access(db: Session, user: User, client_id: int) -> None:
    if (
        user.user_type == "CLIENT_PORTAL"
        and client_id not in effective_permissions(db, user).client_scope_ids
    ):
        raise NotFoundError("Client does not exist.")


def validate_escalation_contact(db: Session, client_ids: set[int], contact_id: int | None, all_clients: bool = False) -> None:
    if contact_id is None:
        return
    contact = db.get(Contact, contact_id)
    if not contact or (not all_clients and contact.client_id not in client_ids) or not contact.is_active:
        raise ConflictError(
            "INVALID_ESCALATION_CONTACT",
            "The escalation contact must be active and belong to one of the contract's linked clients.",
        )


def validate_coverage_context(
    db: Session, contract: Contract, data: ContractCoverageCreate
) -> None:
    if data.branch_id is not None:
        branch = db.get(Branch, data.branch_id)
        if not branch or (not contract.applies_to_all_clients and branch.client_id not in contract.customer_ids) or not branch.is_active:
            raise ConflictError(
                "INVALID_COVERAGE_BRANCH",
                "The coverage branch must be an active branch for the contract client.",
            )
    product = db.get(Product, data.product_id) if data.product_id is not None else None
    if data.product_id is not None and (not product or not product.is_active):
        raise ConflictError("INVALID_COVERAGE_PRODUCT", "The coverage product is not active.")
    if data.product_module_id is not None:
        module = db.get(ProductModule, data.product_module_id)
        if not module or not module.is_active:
            raise ConflictError("INVALID_COVERAGE_MODULE", "The coverage module is not active.")
        if data.product_id is None or module.product_id != data.product_id:
            raise ConflictError(
                "COVERAGE_MODULE_PRODUCT_MISMATCH",
                "Select the module's parent product in the same coverage rule.",
            )
    references = (
        (data.environment_id, Environment, "environment"),
        (data.service_id, ServiceCatalogItem, "service"),
        (data.ticket_type_id, TicketType, "ticket type"),
    )
    for reference_id, model, label in references:
        item = db.get(model, reference_id) if reference_id is not None else None
        if reference_id is not None and (not item or not getattr(item, "is_active", False)):
            raise ConflictError(
                "INVALID_COVERAGE_REFERENCE", f"The coverage {label} is not active."
            )
    values = data.model_dump(
        exclude={
            "is_covered",
            "notes",
            "applies_to_all_clients",
            "client_ids",
            "effective_from",
            "effective_until",
        }
    )
    duplicate = db.scalar(
        select(ContractCoverage.id).where(
            ContractCoverage.contract_id == contract.id,
            *(
                getattr(ContractCoverage, field).is_(None)
                if value is None
                else getattr(ContractCoverage, field) == value
                for field, value in values.items()
            ),
        )
    )
    if duplicate:
        raise ConflictError(
            "DUPLICATE_COVERAGE_RULE",
            "A coverage rule already exists for this exact context.",
        )


def replace_coverage_clients(
    db: Session,
    contract: Contract,
    coverage: ContractCoverage,
    client_ids: list[int],
    applies_to_all_clients: bool,
) -> None:
    if applies_to_all_clients:
        coverage.client_links.clear()
        return
    selected = set(client_ids)
    eligible = (
        set(db.scalars(select(Client.id)))
        if contract.applies_to_all_clients
        else set(contract.linked_client_ids) | {contract.client_id}
    )
    if not selected:
        raise ConflictError(
            "COVERAGE_CLIENTS_REQUIRED",
            "Select at least one client or apply the assignment to all contract clients.",
        )
    if not selected.issubset(eligible):
        raise ConflictError(
            "INVALID_COVERAGE_CLIENT",
            "Every assignment client must be eligible for this contract.",
        )
    coverage.client_links = [
        ContractCoverageClient(client_id=client_id) for client_id in sorted(selected)
    ]


@router.get("/contracts", response_model=list[ContractRead])
def list_contracts(
    client_id: int | None = None,
    active_on: date | None = Query(default=None),
    status: str | None = Query(default=None),
    expires_within: int | None = Query(default=None, ge=1, le=365),
    renewal_missing: bool = Query(default=False),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.view")),
) -> list[Contract]:
    statement = select(Contract)
    if actor.user_type == "CLIENT_PORTAL":
        statement = statement.where(
            or_(
                Contract.applies_to_all_clients.in_([True]),
                Contract.client_id.in_(effective_permissions(db, actor).client_scope_ids or [-1]),
                Contract.client_links.any(
                    ContractClientLink.client_id.in_(
                        effective_permissions(db, actor).client_scope_ids or [-1]
                    )
                ),
            )
        )
    if client_id:
        statement = statement.where(
            or_(
                Contract.applies_to_all_clients.in_([True]),
                Contract.client_id == client_id,
                Contract.client_links.any(ContractClientLink.client_id == client_id),
            )
        )
    if active_on:
        statement = statement.where(
            Contract.start_date <= active_on, Contract.end_date >= active_on
        )
    if status:
        normalized_status = status.upper()
        if normalized_status == "ACTIVE":
            statement = statement.where(Contract.status == "ACTIVE", Contract.is_active.in_([True]))
        elif normalized_status == "INACTIVE":
            statement = statement.where(
                or_(Contract.status != "ACTIVE", Contract.is_active.in_([False]))
            )
        else:
            statement = statement.where(Contract.status == normalized_status)
    if expires_within:
        today = server_today()
        statement = statement.where(
            Contract.status == "ACTIVE",
            Contract.is_active.in_([True]),
            Contract.end_date >= today,
            Contract.end_date <= today + timedelta(days=expires_within),
        )
    if renewal_missing:
        statement = statement.where(Contract.renewal_notice_date.is_(None))
    return list(db.scalars(statement.order_by(Contract.end_date.desc())))


@router.get("/contracts/renewals/upcoming", response_model=list[ContractRead])
def upcoming_contract_renewals(
    days: int = Query(default=90, ge=1, le=365),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.view")),
) -> list[Contract]:
    today = server_today()
    statement = select(Contract).where(
        Contract.is_active.in_([True]),
        Contract.status == "ACTIVE",
        Contract.end_date >= today,
        Contract.end_date <= today + timedelta(days=days),
    )
    if actor.user_type == "CLIENT_PORTAL":
        scopes = effective_permissions(db, actor).client_scope_ids or [-1]
        statement = statement.where(
            or_(
                Contract.applies_to_all_clients.in_([True]),
                Contract.client_id.in_(scopes),
                Contract.client_links.any(ContractClientLink.client_id.in_(scopes)),
            )
        )
    return list(db.scalars(statement.order_by(Contract.end_date)))


@router.post("/contracts/renewals/notify")
def notify_upcoming_contract_renewals(
    days: int = Query(default=90, ge=1, le=365),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> dict[str, int]:
    contracts = upcoming_contract_renewals(days, db, actor)
    candidate_users = db.scalars(
        select(User).where(User.is_active.in_([True]), User.user_type == "EMPLOYEE")
    ).all()
    recipients = [
        user
        for user in candidate_users
        if "contract.manage" in effective_permissions(db, user).permissions
    ]
    created = 0
    for contract in contracts:
        for recipient in recipients:
            if not can_receive_renewal(db, recipient, contract):
                continue
            key = f"contract-renewal:{contract.id}:{contract.end_date.isoformat()}:user:{recipient.id}"
            if db.scalar(select(Notification.id).where(Notification.deduplication_key == key)):
                continue
            db.add(
                Notification(
                    recipient_user_id=recipient.id,
                    notification_type="CONTRACT_RENEWAL",
                    severity="WARNING",
                    title=f"Contract renewal: {contract.contract_number}",
                    message=f"{contract.name} expires on {contract.end_date.isoformat()}.",
                    deep_link="/contracts",
                    deduplication_key=key,
                )
            )
            created += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Contract",
            entity_id="renewals",
            action="contract.renewals.notified",
            new_values_json=json.dumps(
                {"days": days, "contracts": len(contracts), "notifications": created}
            ),
        )
    )
    db.commit()
    return {"contracts": len(contracts), "notifications_created": created}


@router.post("/contracts", response_model=ContractRead, status_code=status.HTTP_201_CREATED)
def create_contract(
    data: ContractCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> Contract:
    customer_ids = set(data.linked_client_ids)
    if data.client_id is not None:
        customer_ids.add(data.client_id)
    if not customer_ids:
        raise ConflictError("CONTRACT_CLIENTS_REQUIRED", "Select at least one contract client.")
    for customer_id in customer_ids:
        ensure_contract_client_access(db, actor, customer_id)
    if set(db.scalars(select(Client.id).where(Client.id.in_(customer_ids)))) != customer_ids:
        raise NotFoundError("One or more linked clients do not exist.")
    if not db.get(BusinessCalendar, data.calendar_id):
        raise NotFoundError("Business calendar does not exist.")
    validate_contract_approval_group(db, data.approval_group_id)
    validate_escalation_contact(db, customer_ids, data.escalation_contact_id, data.applies_to_all_clients)
    contract_type, feature_mode = contract_type_for_write(
        db, data.contract_type_id, client_id=min(customer_ids)
    )
    values = data.model_dump(exclude={"linked_client_ids"})
    values["client_id"] = min(customer_ids)
    values["contract_type_id"] = contract_type.id
    values["has_sla"] = (
        contract_type.default_has_sla
        if data.has_sla is None and feature_mode == "ENFORCED"
        else True
        if data.has_sla is None
        else data.has_sla
    )
    contract = Contract(**values)
    db.add(contract)
    try:
        db.flush()
        replace_contract_clients(db, contract, sorted(customer_ids))
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "DUPLICATE_CONTRACT", "That contract number is already in use."
        ) from exc
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Contract",
            entity_id=str(contract.id),
            action="contract.created",
            new_values_json=json.dumps(data.model_dump(), default=str),
        )
    )
    recalculate_client_contract_service_status(
        db, {contract.client_id, *contract.linked_client_ids}
    )
    db.commit()
    db.refresh(contract)
    return contract


def create_contract_from_template_record(
    db: Session,
    client: Client,
    item: ContractTemplate,
    data: ContractFromTemplateWrite,
    actor: User,
) -> Contract:
    if item.version != data.expected_template_version or not item.is_active:
        raise ConflictError(
            "STALE_CONTRACT_TEMPLATE",
            "The template changed or became inactive; refresh the preview.",
        )
    previous = db.scalar(
        select(Contract).where(Contract.onboarding_idempotency_key == data.idempotency_key)
    )
    if previous:
        return previous
    start = data.start_date or data.acceptance_date
    preview = template_preview(item, start, data.duration_months, data.name)
    contract = Contract(
        contract_number=data.contract_number or "PENDING",
        client_id=client.id,
        contract_type_id=item.contract_type_id,
        name=data.name or f"{client.name} — {item.name}",
        status="ACTIVE",
        start_date=start,
        end_date=preview.end_date,
        acceptance_date=data.acceptance_date,
        timezone=client.timezone,
        calendar_id=item.calendar_id,
        sla_policy_id=item.sla_policy_id,
        has_sla=item.has_sla,
        ticket_catalog_visibility=item.ticket_catalog_visibility,
        require_product_on_ticket=item.require_product_on_ticket,
        require_module_on_ticket=item.require_module_on_ticket,
        require_service_on_ticket=item.require_service_on_ticket,
        coverage_validation_level=item.coverage_validation_level,
        expiry_grace_days=item.expiry_grace_days,
        approval_group_id=item.approval_group_id,
        support_summary=item.support_summary,
        exclusions=item.exclusions,
        included_request_limit=item.included_request_limit,
        source_template_id=item.id,
        source_template_version=item.version,
        onboarding_idempotency_key=data.idempotency_key,
    )
    for key, value in data.change_overrides.items():
        if key in {
            "support_summary",
            "exclusions",
            "included_request_limit",
            "sla_policy_id",
            "has_sla",
            "ticket_catalog_visibility",
            "require_product_on_ticket",
            "require_module_on_ticket",
            "require_service_on_ticket",
            "coverage_validation_level",
            "expiry_grace_days",
            "approval_group_id",
        }:
            setattr(contract, key, value)
    db.add(contract)
    db.flush()
    if not data.contract_number:
        contract.contract_number = f"CTR-{start.year}-{contract.id:06d}"
    for source in item.coverages:
        row = ContractCoverage(
            contract_id=contract.id,
            product_id=source.product_id,
            product_module_id=source.product_module_id,
            environment_id=source.environment_id,
            service_id=source.service_id,
            ticket_type_id=source.ticket_type_id,
            is_covered=source.is_covered,
            notes=source.notes,
            effective_from=start,
            effective_until=preview.end_date,
        )
        db.add(row)
        db.flush()
        db.add(
            ContractCoverageRevision(
                coverage_id=row.id,
                revision=1,
                effective_from=start,
                effective_until=preview.end_date,
                is_covered=row.is_covered,
                notes=row.notes,
                client_ids_json="[]",
                change_reason=f"Created from template {item.code} v{item.version}",
                created_by_user_id=actor.id,
            )
        )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Contract",
            entity_id=str(contract.id),
            action="contract.created.from_template",
            new_values_json=json.dumps(
                {"template_id": item.id, "template_version": item.version, "client_id": client.id},
                default=str,
            ),
        )
    )
    return contract


@router.post("/clients/onboard", response_model=ClientOnboardingRead, status_code=201)
def onboard_client(
    data: ClientOnboardingWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client.manage")),
) -> ClientOnboardingRead:
    if data.client.owner_department_id is None:
        raise ConflictError(
            "OWNER_DEPARTMENT_REQUIRED", "Select the department that owns this client."
        )
    department = db.get(Department, data.client.owner_department_id)
    if not department or not department.is_active:
        raise ConflictError("INVALID_OWNER_DEPARTMENT", "Select an active owner department.")
    if not db.get(ClientStatus, data.client.status_id):
        raise NotFoundError("Client status does not exist.")
    country = db.get(Country, data.client.country_id) if data.client.country_id else None
    city = db.get(City, data.client.city_id) if data.client.city_id else None
    if data.client.country_id and not country:
        raise NotFoundError("Country does not exist.")
    if city and city.country_id != data.client.country_id:
        raise ConflictError(
            "INVALID_CITY", "The selected city does not belong to the selected country."
        )
    if data.client.code and db.scalar(select(Client.id).where(Client.code == data.client.code)):
        raise ConflictError("DUPLICATE_CLIENT", "The client code is already in use.")
    shared_department_ids = set(data.client.shared_department_ids)
    shared_department_ids.discard(data.client.owner_department_id)
    active_shared = set(
        db.scalars(
            select(Department.id).where(
                Department.id.in_(shared_department_ids or [-1]), Department.is_active.in_([True])
            )
        )
    )
    if active_shared != shared_department_ids:
        raise ConflictError("INVALID_SHARED_DEPARTMENT", "Every shared department must be active.")
    values = data.client.model_dump(exclude={"shared_department_ids"})
    requested_code = values.pop("code", None)
    if country:
        values["country"] = country.name
    if city:
        values["zone"] = city.name
    client = Client(code=requested_code or "PENDING", **values)
    db.add(client)
    db.flush()
    if not requested_code:
        client.code = f"CLI-{client.id:06d}"
    db.add_all(
        ClientDepartmentLink(client_id=client.id, department_id=department_id)
        for department_id in sorted(shared_department_ids)
    )
    contact = None
    if data.contact:
        contact = Contact(
            client_id=client.id,
            code=None,
            is_primary=True,
            is_active=True,
            **data.contact.model_dump(),
        )
        db.add(contact)
        db.flush()
        contact.code = f"CON-{contact.id:06d}"
    contract = None
    if data.contract:
        item = db.get(ContractTemplate, data.contract.template_id)
        if not item:
            raise NotFoundError("Contract template does not exist.")
        contract = create_contract_from_template_record(db, client, item, data.contract, actor)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Client",
            entity_id=str(client.id),
            action="client.onboarded",
            new_values_json=json.dumps(
                {
                    "source": data.source,
                    "owner_department_id": client.owner_department_id,
                    "contact_id": contact.id if contact else None,
                    "contract_id": contract.id if contract else None,
                },
                default=str,
            ),
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "CLIENT_ONBOARDING_CONFLICT",
            "The client, contact, or contract identifier is already in use.",
        ) from exc
    return ClientOnboardingRead(
        client_id=client.id,
        client_code=client.code,
        contact_id=contact.id if contact else None,
        contact_code=contact.code if contact else None,
        contract_id=contract.id if contract else None,
        contract_number=contract.contract_number if contract else None,
    )


@router.post(
    "/clients/{client_id}/contracts/from-template", response_model=ContractRead, status_code=201
)
def create_client_contract_from_template(
    client_id: int,
    data: ContractFromTemplateWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> Contract:
    client = db.get(Client, client_id)
    item = db.get(ContractTemplate, data.template_id)
    if not client:
        raise NotFoundError("Client does not exist.")
    ensure_contract_client_access(db, actor, client.id)
    if not item:
        raise NotFoundError("Contract template does not exist.")
    try:
        contract = create_contract_from_template_record(db, client, item, data, actor)
        db.commit()
        db.refresh(contract)
        return contract
    except IntegrityError as exc:
        db.rollback()
        previous = db.scalar(
            select(Contract).where(Contract.onboarding_idempotency_key == data.idempotency_key)
        )
        if previous:
            return previous
        raise ConflictError(
            "DUPLICATE_CONTRACT", "The generated or selected contract number is already in use."
        ) from exc


@router.post(
    "/contracts/{contract_id}/save-as-template",
    response_model=ContractTemplateRead,
    status_code=201,
)
def save_contract_as_template(
    contract_id: int,
    name: str = Query(min_length=2, max_length=150),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.template.manage")),
) -> ContractTemplate:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    item = ContractTemplate(
        code=f"PENDING-{server_now().timestamp()}",
        name=name,
        template_type="GLOBAL",
        contract_type_id=contract.contract_type_id,
        calendar_id=contract.calendar_id,
        sla_policy_id=contract.sla_policy_id,
        default_duration_months=max(
            1, round((contract.end_date - contract.start_date).days / 30.44)
        ),
        has_sla=contract.has_sla,
        ticket_catalog_visibility=contract.ticket_catalog_visibility,
        require_product_on_ticket=contract.require_product_on_ticket,
        require_module_on_ticket=contract.require_module_on_ticket,
        require_service_on_ticket=contract.require_service_on_ticket,
        coverage_validation_level=contract.coverage_validation_level,
        expiry_grace_days=contract.expiry_grace_days,
        approval_group_id=contract.approval_group_id,
        support_summary=contract.support_summary,
        exclusions=contract.exclusions,
        included_request_limit=contract.included_request_limit,
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    coverages = db.scalars(
        select(ContractCoverage).where(
            ContractCoverage.contract_id == contract.id, ContractCoverage.retired_at.is_(None)
        )
    )
    item.coverages = [
        ContractTemplateCoverage(
            product_id=row.product_id,
            product_module_id=row.product_module_id,
            environment_id=row.environment_id,
            service_id=row.service_id,
            ticket_type_id=row.ticket_type_id,
            is_covered=row.is_covered,
            notes=row.notes,
        )
        for row in coverages
    ]
    db.add(item)
    try:
        db.flush()
        item.code = f"CTP-{item.id:06d}"
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "DUPLICATE_CONTRACT_TEMPLATE", "That template code is already in use."
        ) from exc
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ContractTemplate",
            entity_id=str(item.id),
            action="contract.template.saved_from_contract",
            new_values_json=json.dumps({"contract_id": contract.id}),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.post("/contracts/{contract_id}/template-preview", response_model=ContractTemplatePreview)
def preview_template_for_contract(
    contract_id: int,
    template_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.template.view")),
) -> ContractTemplatePreview:
    contract = db.get(Contract, contract_id)
    item = db.get(ContractTemplate, template_id)
    if not contract or not item:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    return template_preview(item, contract.start_date, None, contract.name)


@router.post("/contracts/{contract_id}/apply-template", response_model=ContractRead)
def apply_template_to_contract(
    contract_id: int,
    data: ContractTemplateApplyWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.template.apply")),
) -> Contract:
    contract = db.get(Contract, contract_id)
    item = db.get(ContractTemplate, data.template_id)
    if not contract or not item:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    if item.version != data.expected_template_version or not item.is_active:
        raise ConflictError("STALE_CONTRACT_TEMPLATE", "Refresh the template before applying it.")
    allowed = {"CORE", "SLA", "COVERAGE", "DURATION", "FUTURE_BILLING"}
    sections = set(data.sections)
    if not sections <= allowed:
        raise ConflictError(
            "INVALID_TEMPLATE_SECTION", "One or more template sections are unsupported."
        )
    if "FUTURE_BILLING" in sections:
        from app.modules.finance.models import ContractCollection, ContractFinanceProfile

        if db.scalar(
            select(ContractCollection.id)
            .where(ContractCollection.contract_id == contract.id)
            .limit(1)
        ):
            raise ConflictError(
                "CONTRACT_HAS_COLLECTIONS",
                "Billing defaults cannot be replaced after payment collection.",
            )
        profile = db.get(ContractFinanceProfile, contract.id)
        if profile:
            if item.default_billing_frequency:
                profile.billing_frequency = item.default_billing_frequency
            if item.default_payment_terms_days is not None:
                profile.payment_terms_days = item.default_payment_terms_days
    old = {
        "source_template_id": contract.source_template_id,
        "source_template_version": contract.source_template_version,
    }
    if "CORE" in sections:
        contract.contract_type_id = item.contract_type_id
        contract.calendar_id = item.calendar_id
        contract.support_summary = item.support_summary
        contract.exclusions = item.exclusions
        contract.included_request_limit = item.included_request_limit
        contract.ticket_catalog_visibility = item.ticket_catalog_visibility
        contract.require_product_on_ticket = item.require_product_on_ticket
        contract.require_module_on_ticket = item.require_module_on_ticket
        contract.require_service_on_ticket = item.require_service_on_ticket
        contract.coverage_validation_level = item.coverage_validation_level
        contract.expiry_grace_days = item.expiry_grace_days
        contract.approval_group_id = item.approval_group_id
    if "SLA" in sections:
        if item.has_sla and item.sla_policy_id and not sla_policy_ready(db, db.get(SlaPolicy, item.sla_policy_id)):
            raise ConflictError("SLA_POLICY_NOT_READY", "The template SLA is inactive or has no current published targets.")
        contract.sla_policy_id = item.sla_policy_id
        contract.has_sla = item.has_sla
    if "DURATION" in sections:
        contract.end_date = add_calendar_months(
            contract.start_date, item.default_duration_months
        ) - timedelta(days=1)
    if "COVERAGE" in sections:
        existing = list(
            db.scalars(
                select(ContractCoverage).where(
                    ContractCoverage.contract_id == contract.id,
                    ContractCoverage.retired_at.is_(None),
                )
            )
        )
        if any(
            db.scalar(
                select(Ticket.id)
                .where(Ticket.contract_id == contract.id, Ticket.product_id == row.product_id)
                .limit(1)
            )
            for row in existing
        ):
            raise ConflictError(
                "CONTRACT_COVERAGE_IN_USE",
                "Retire or amend used coverage explicitly; template application cannot rewrite it.",
            )
        for row in existing:
            db.delete(row)
        for source in item.coverages:
            db.add(
                ContractCoverage(
                    contract_id=contract.id,
                    product_id=source.product_id,
                    product_module_id=source.product_module_id,
                    environment_id=source.environment_id,
                    service_id=source.service_id,
                    ticket_type_id=source.ticket_type_id,
                    is_covered=source.is_covered,
                    notes=source.notes,
                    effective_from=contract.start_date,
                    effective_until=contract.end_date,
                )
            )
    contract.source_template_id = item.id
    contract.source_template_version = item.version
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Contract",
            entity_id=str(contract.id),
            action="contract.template.applied",
            reason=data.reason,
            old_values_json=json.dumps(old),
            new_values_json=json.dumps(
                {
                    "template_id": item.id,
                    "template_version": item.version,
                    "sections": sorted(sections),
                }
            ),
        )
    )
    db.commit()
    db.refresh(contract)
    return contract


@router.get("/contracts/{contract_id}", response_model=ContractRead)
def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.view")),
) -> Contract:
    if actor.user_type == "CLIENT_PORTAL":
        raise NotFoundError("Contract does not exist.")
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    return contract


@router.get("/contracts/{contract_id}/clients/page")
def page_contract_clients(
    contract_id: int,
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.view")),
) -> dict[str, object]:
    if actor.user_type == "CLIENT_PORTAL":
        raise NotFoundError("Contract does not exist.")
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    client_ids = set(contract.linked_client_ids) | {contract.client_id}
    if contract.applies_to_all_clients:
        client_ids.update(
            db.scalars(
                select(ContractCoverageClient.client_id)
                .join(ContractCoverage, ContractCoverage.id == ContractCoverageClient.coverage_id)
                .where(ContractCoverage.contract_id == contract.id)
            )
        )
    statement = select(Client).where(Client.id.in_(client_ids))
    count_statement = select(func.count(Client.id)).where(Client.id.in_(client_ids))
    if search:
        term = f"%{search.strip()}%"
        predicate = or_(Client.code.like(term), Client.name.like(term))
        statement = statement.where(predicate)
        count_statement = count_statement.where(predicate)
    total = db.scalar(count_statement) or 0
    rows = db.scalars(statement.order_by(Client.name).offset(offset).limit(limit))
    return {
        "items": [{"id": row.id, "code": row.code, "name": row.name} for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/contracts/{contract_id}/clients", response_model=list[ClientRead])
def list_contract_clients(
    contract_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.view")),
) -> list[Client]:
    if actor.user_type == "CLIENT_PORTAL":
        raise NotFoundError("Contract does not exist.")
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    client_ids = set(contract.linked_client_ids) | {contract.client_id}
    if contract.applies_to_all_clients:
        client_ids.update(
            db.scalars(
                select(ContractCoverageClient.client_id)
                .join(
                    ContractCoverage,
                    ContractCoverage.id == ContractCoverageClient.coverage_id,
                )
                .where(ContractCoverage.contract_id == contract.id)
            )
        )
    return list(db.scalars(select(Client).where(Client.id.in_(client_ids)).order_by(Client.name)))


def resolve_client_selection(db: Session, data: ContractClientSelection) -> tuple[list[int], int]:
    if data.mode == "EXPLICIT":
        selected = list(dict.fromkeys(data.explicit_ids))
        return selected, len(selected)
    statement = select(Client.id)
    if data.search:
        term = f"%{data.search.strip()}%"
        statement = statement.where(or_(Client.code.like(term), Client.name.like(term)))
    matched = list(db.scalars(statement.order_by(Client.name)))
    excluded = set(data.excluded_ids)
    return [client_id for client_id in matched if client_id not in excluded], len(matched)


@router.post(
    "/contracts/{contract_id}/client-selection/preview",
    response_model=ContractClientSelectionPreview,
)
def preview_contract_client_selection(
    contract_id: int,
    data: ContractClientSelection,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> ContractClientSelectionPreview:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    selected, matched = resolve_client_selection(db, data)
    final_ids = set(selected)
    inactive_count = (
        db.scalar(
            select(func.count(Client.id)).where(
                Client.id.in_(final_ids), Client.is_active.in_([False])
            )
        )
        or 0
    )
    return ContractClientSelectionPreview(
        mode=data.mode,
        matched_count=matched,
        selected_count=len(final_ids),
        excluded_count=len(set(data.excluded_ids)),
        primary_forced=False,
        inactive_count=inactive_count,
    )


@router.post("/contracts/{contract_id}/client-selection/apply", response_model=ContractRead)
def apply_contract_client_selection(
    contract_id: int,
    data: ContractClientSelection,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> Contract:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    selected, matched = resolve_client_selection(db, data)
    affected_clients = contract.customer_ids | set(selected)
    for customer_id in selected:
        ensure_contract_client_access(db, actor, customer_id)
    replace_contract_clients(db, contract, selected)
    recalculate_client_contract_service_status(db, affected_clients)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Contract",
            entity_id=str(contract.id),
            action="contract.clients.selection.applied",
            new_values_json=json.dumps(
                {
                    "mode": data.mode,
                    "search": data.search,
                    "matched_count": matched,
                    "selected_count": len(selected),
                    "excluded_ids": data.excluded_ids,
                }
            ),
        )
    )
    db.commit()
    db.refresh(contract)
    return contract


@router.patch("/contracts/{contract_id}", response_model=ContractRead)
def update_contract(
    contract_id: int,
    data: ContractUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> Contract:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    changes = data.model_dump(exclude_unset=True)
    linked_client_ids = changes.pop("linked_client_ids", None)
    if "contract_type_id" in changes:
        contract_type, _ = contract_type_for_write(
            db, changes["contract_type_id"], client_id=contract.client_id
        )
        changes["contract_type_id"] = contract_type.id
    if changes.get("calendar_id") and not db.get(BusinessCalendar, changes["calendar_id"]):
        raise NotFoundError("Business calendar does not exist.")
    if "approval_group_id" in changes and changes["approval_group_id"] != contract.approval_group_id:
        validate_contract_approval_group(db, changes["approval_group_id"])
    previous_clients = contract.customer_ids
    proposed_clients = set(linked_client_ids) if linked_client_ids is not None else previous_clients
    if linked_client_ids is not None:
        for customer_id in linked_client_ids:
            ensure_contract_client_access(db, actor, customer_id)
    if linked_client_ids is not None or changes.get("escalation_contact_id", contract.escalation_contact_id) != contract.escalation_contact_id or "applies_to_all_clients" in changes:
        validate_escalation_contact(db, proposed_clients,
            changes.get("escalation_contact_id", contract.escalation_contact_id),
            changes.get("applies_to_all_clients", contract.applies_to_all_clients))
    start_date = changes.get("start_date", contract.start_date)
    end_date = changes.get("end_date", contract.end_date)
    reconcile_contract_dates(db, contract, start_date, end_date, actor)
    old_values = {field: getattr(contract, field) for field in changes}
    for field, value in changes.items():
        setattr(contract, field, value)
    if changes.get("has_sla") is False:
        for running_clock in db.scalars(
            select(TicketSlaClock).where(
                TicketSlaClock.contract_id == contract.id,
                TicketSlaClock.state == "RUNNING",
            )
        ):
            # ORM lifecycle events close the matching escalation work item in
            # the same transaction.  A bulk UPDATE would bypass that queue.
            running_clock.state = "DISABLED"
    if linked_client_ids is not None:
        replace_contract_clients(db, contract, linked_client_ids)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Contract",
            entity_id=str(contract.id),
            action="contract.updated",
            old_values_json=json.dumps(old_values, default=str),
            new_values_json=json.dumps(changes, default=str),
        )
    )
    recalculate_client_contract_service_status(
        db, previous_clients | contract.customer_ids
    )
    db.commit()
    db.refresh(contract)
    return contract


@router.delete("/contracts/{contract_id}", status_code=204)
def delete_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.delete")),
    settings: Settings = Depends(get_settings),
) -> None:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    if db.scalar(select(Ticket.id).where(Ticket.contract_id == contract_id).limit(1)):
        raise ConflictError(
            "CONTRACT_IN_USE",
            "This contract is referenced by one or more tickets. Terminate it instead to preserve ticket history.",
        )

    documents = list(
        db.scalars(select(ContractDocument).where(ContractDocument.contract_id == contract_id))
    )
    document_paths = [contract_document_path(document, settings) for document in documents]
    legacy_policy_ids = list(
        db.scalars(select(SlaPolicy.id).where(SlaPolicy.contract_id == contract_id))
    )
    if legacy_policy_ids:
        db.execute(delete(SlaTarget).where(SlaTarget.policy_id.in_(legacy_policy_ids)))
        db.execute(delete(SlaPolicy).where(SlaPolicy.id.in_(legacy_policy_ids)))
    db.execute(delete(ContractDocument).where(ContractDocument.contract_id == contract_id))
    db.execute(delete(ContractCoverage).where(ContractCoverage.contract_id == contract_id))
    db.delete(contract)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Contract",
            entity_id=str(contract_id),
            action="contract.deleted",
            old_values_json=json.dumps(
                {"contract_number": contract.contract_number, "name": contract.name}, default=str
            ),
        )
    )
    db.commit()
    for path in document_paths:
        path.unlink(missing_ok=True)


@router.get("/contracts/{contract_id}/coverage", response_model=list[ContractCoverageRead])
def list_contract_coverage(
    contract_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.view")),
) -> list[ContractCoverage]:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    return list(
        db.scalars(
            select(ContractCoverage)
            .where(ContractCoverage.contract_id == contract_id)
            .order_by(ContractCoverage.id)
        )
    )


@router.get("/contracts/{contract_id}/usage", response_model=ContractUsageRead)
def get_contract_usage(
    contract_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.view")),
) -> dict[str, int | None]:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    return contract_usage(db, contract)


@router.post(
    "/contracts/{contract_id}/coverage", response_model=ContractCoverageRead, status_code=201
)
def add_contract_coverage(
    contract_id: int,
    data: ContractCoverageCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> ContractCoverage:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    validate_coverage_context(db, contract, data)
    values = data.model_dump(exclude={"applies_to_all_clients", "client_ids"})
    values["effective_from"] = data.effective_from or contract.start_date
    values["effective_until"] = data.effective_until or contract.end_date
    if (
        values["effective_from"] < contract.start_date
        or values["effective_until"] > contract.end_date
    ):
        raise ConflictError(
            "COVERAGE_OUTSIDE_CONTRACT", "Coverage dates must remain within the contract period."
        )
    row = ContractCoverage(contract_id=contract_id, **values)
    db.add(row)
    try:
        db.flush()
        replace_coverage_clients(
            db,
            contract,
            row,
            data.client_ids,
            data.applies_to_all_clients,
        )
        db.flush()
        db.add(
            ContractCoverageRevision(
                coverage_id=row.id,
                revision=1,
                effective_from=row.effective_from,
                effective_until=row.effective_until,
                is_covered=row.is_covered,
                notes=row.notes,
                client_ids_json=json.dumps(row.client_ids),
                change_reason="Coverage created",
                created_by_user_id=actor.id,
            )
        )
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "DUPLICATE_COVERAGE_RULE", "That coverage rule already exists."
        ) from exc
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ContractCoverage",
            entity_id=str(row.id),
            action="contract.coverage.created",
            new_values_json=json.dumps(data.model_dump(), default=str),
        )
    )
    db.commit()
    db.refresh(row)
    return row


@router.get(
    "/contracts/{contract_id}/coverage/{coverage_id}/history",
    response_model=list[ContractCoverageRevisionRead],
)
def coverage_history(
    contract_id: int,
    coverage_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.view")),
) -> list[ContractCoverageRevision]:
    contract = db.get(Contract, contract_id)
    row = db.get(ContractCoverage, coverage_id)
    if not contract or not row or row.contract_id != contract_id:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    return list(
        db.scalars(
            select(ContractCoverageRevision)
            .where(ContractCoverageRevision.coverage_id == coverage_id)
            .order_by(ContractCoverageRevision.revision)
        )
    )


@router.post(
    "/contracts/{contract_id}/coverage/{coverage_id}/amend", response_model=ContractCoverageRead
)
def amend_contract_coverage(
    contract_id: int,
    coverage_id: int,
    data: ContractCoverageAmend,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> ContractCoverage:
    contract = db.get(Contract, contract_id)
    row = db.get(ContractCoverage, coverage_id)
    if not contract or not row or row.contract_id != contract_id:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    if row.current_revision != data.expected_revision:
        raise ConflictError("STALE_COVERAGE_REVISION", "Coverage changed; refresh and retry.")
    previous = db.scalar(
        select(ContractCoverageRevision).where(
            ContractCoverageRevision.coverage_id == row.id,
            ContractCoverageRevision.revision == row.current_revision,
        )
    )
    if not previous or data.effective_from <= previous.effective_from:
        raise ConflictError(
            "INVALID_COVERAGE_AMENDMENT_DATE",
            "An amendment must begin after the current revision starts.",
        )
    end = data.effective_until or contract.end_date
    if (
        data.effective_from > end
        or data.effective_from < contract.start_date
        or end > contract.end_date
    ):
        raise ConflictError(
            "COVERAGE_OUTSIDE_CONTRACT", "Coverage dates must remain within the contract period."
        )
    previous.effective_until = data.effective_from - timedelta(days=1)
    replace_coverage_clients(db, contract, row, data.client_ids, data.applies_to_all_clients)
    row.current_revision += 1
    row.effective_from = data.effective_from
    row.effective_until = end
    row.is_covered = data.is_covered
    row.notes = data.notes
    row.retired_at = None
    row.retirement_reason = None
    db.flush()
    db.add(
        ContractCoverageRevision(
            coverage_id=row.id,
            revision=row.current_revision,
            effective_from=data.effective_from,
            effective_until=end,
            is_covered=data.is_covered,
            notes=data.notes,
            client_ids_json=json.dumps(row.client_ids),
            change_reason=data.reason,
            created_by_user_id=actor.id,
        )
    )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ContractCoverage",
            entity_id=str(row.id),
            action="contract.coverage.amended",
            reason=data.reason,
            new_values_json=json.dumps(data.model_dump(), default=str),
        )
    )
    db.commit()
    db.refresh(row)
    return row


@router.post(
    "/contracts/{contract_id}/assignments/bulk",
    response_model=list[ContractCoverageRead],
)
def save_bulk_contract_assignments(
    contract_id: int,
    data: ContractBulkAssignmentCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> list[ContractCoverage]:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    contexts: list[tuple[int | None, int | None, int | None]] = []
    for assignment in data.products:
        product = db.get(Product, assignment.product_id)
        if not product or not product.is_active:
            raise ConflictError("INVALID_COVERAGE_PRODUCT", "The selected product is not active.")
        module_ids = list(dict.fromkeys(assignment.module_ids))
        if not module_ids:
            contexts.append((product.id, None, None))
        for module_id in module_ids:
            module = db.get(ProductModule, module_id)
            if not module or not module.is_active or module.product_id != product.id:
                raise ConflictError(
                    "COVERAGE_MODULE_PRODUCT_MISMATCH",
                    "Every selected module must belong to its assigned product.",
                )
            contexts.append((product.id, module.id, None))
    for selected_service_id in dict.fromkeys(data.service_ids):
        service = db.get(ServiceCatalogItem, selected_service_id)
        if not service or not service.is_active:
            raise ConflictError("INVALID_COVERAGE_SERVICE", "The selected service is not active.")
        contexts.append((None, None, service.id))
    if not contexts:
        raise ConflictError("ASSIGNMENT_REQUIRED", "Select at least one product or service.")
    saved: list[ContractCoverage] = []
    for context_product_id, context_module_id, context_service_id in contexts:
        row = db.scalar(
            select(ContractCoverage).where(
                ContractCoverage.contract_id == contract.id,
                ContractCoverage.product_id == context_product_id,
                ContractCoverage.product_module_id == context_module_id,
                ContractCoverage.service_id == context_service_id,
                ContractCoverage.branch_id.is_(None),
                ContractCoverage.environment_id.is_(None),
                ContractCoverage.ticket_type_id.is_(None),
            )
        )
        if not row:
            row = ContractCoverage(
                contract_id=contract.id,
                product_id=context_product_id,
                product_module_id=context_module_id,
                service_id=context_service_id,
                is_covered=True,
                effective_from=contract.start_date,
                effective_until=contract.end_date,
                current_revision=1,
            )
            db.add(row)
            db.flush()
        row.is_covered = True
        replace_coverage_clients(
            db,
            contract,
            row,
            data.client_ids,
            data.applies_to_all_clients,
        )
        db.flush()
        if not db.scalar(
            select(ContractCoverageRevision.id).where(
                ContractCoverageRevision.coverage_id == row.id
            )
        ):
            db.add(
                ContractCoverageRevision(
                    coverage_id=row.id,
                    revision=1,
                    effective_from=row.effective_from or contract.start_date,
                    effective_until=row.effective_until or contract.end_date,
                    is_covered=True,
                    notes=row.notes,
                    client_ids_json=json.dumps(row.client_ids),
                    change_reason="Bulk coverage assignment",
                    created_by_user_id=actor.id,
                )
            )
        saved.append(row)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Contract",
            entity_id=str(contract.id),
            action="contract.assignments.bulk_saved",
            new_values_json=json.dumps(data.model_dump(), default=str),
        )
    )
    db.commit()
    for row in saved:
        db.refresh(row)
    return saved


def coverage_has_ticket_history(db: Session, contract: Contract, row: ContractCoverage) -> bool:
    client_ids = set(contract.linked_client_ids)
    client_ids.add(contract.client_id)
    query = select(Ticket.id).where(Ticket.client_id.in_(client_ids))
    for ticket_field, value in (
        (Ticket.product_id, row.product_id),
        (Ticket.product_module_id, row.product_module_id),
        (Ticket.branch_id, row.branch_id),
        (Ticket.environment_id, row.environment_id),
        (Ticket.service_id, row.service_id),
        (Ticket.ticket_type_id, row.ticket_type_id),
    ):
        if value is not None:
            query = query.where(ticket_field == value)
    return db.scalar(query.limit(1)) is not None


def delete_or_retire_contract_coverage(
    db: Session,
    contract: Contract,
    row: ContractCoverage,
    actor: User,
    reason: str,
) -> bool:
    old_values = {
        "product_id": row.product_id,
        "product_module_id": row.product_module_id,
        "branch_id": row.branch_id,
        "environment_id": row.environment_id,
        "service_id": row.service_id,
        "ticket_type_id": row.ticket_type_id,
        "is_covered": row.is_covered,
    }
    if not coverage_has_ticket_history(db, contract, row):
        db.add(
            AuditLog(
                actor_user_id=actor.id,
                entity_type="ContractCoverage",
                entity_id=str(row.id),
                action="contract.coverage.deleted",
                reason=reason,
                old_values_json=json.dumps(old_values, default=str),
            )
        )
        db.delete(row)
        return True

    now = server_now()
    today = now.date()
    row.retired_at = now
    row.retired_by_user_id = actor.id
    row.retirement_reason = reason
    effective_from = row.effective_from or contract.start_date
    row.effective_until = max(effective_from, min(row.effective_until or contract.end_date, today))
    revision = db.scalar(
        select(ContractCoverageRevision).where(
            ContractCoverageRevision.coverage_id == row.id,
            ContractCoverageRevision.revision == row.current_revision,
        )
    )
    if revision:
        revision.effective_until = max(
            revision.effective_from,
            min(revision.effective_until or contract.end_date, today),
        )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ContractCoverage",
            entity_id=str(row.id),
            action="contract.coverage.retired",
            reason=reason,
            old_values_json=json.dumps(old_values, default=str),
        )
    )
    return False


@router.delete("/contracts/{contract_id}/coverage/{coverage_id}", status_code=204)
def delete_contract_coverage(
    contract_id: int,
    coverage_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> None:
    row = db.get(ContractCoverage, coverage_id)
    if not row or row.contract_id != contract_id:
        raise NotFoundError()
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    delete_or_retire_contract_coverage(db, contract, row, actor, "Removed from contract coverage")
    db.commit()


@router.post("/contracts/{contract_id}/coverage/retire-batch", status_code=204)
def retire_contract_coverage_batch(
    contract_id: int,
    data: ContractCoverageRetireBatch,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> None:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    coverage_ids = set(data.coverage_ids)
    rows = list(
        db.scalars(
            select(ContractCoverage).where(
                ContractCoverage.id.in_(coverage_ids),
                ContractCoverage.contract_id == contract_id,
                ContractCoverage.retired_at.is_(None),
            )
        )
    )
    if {row.id for row in rows} != coverage_ids:
        raise ConflictError(
            "INVALID_COVERAGE_SELECTION",
            "Every selected coverage rule must be active and belong to this contract.",
        )
    for row in rows:
        delete_or_retire_contract_coverage(db, contract, row, actor, data.reason)
    db.commit()


def renewal_read(db: Session, item: ContractRenewalOpportunity) -> RenewalOpportunityRead:
    lines = list(
        db.scalars(
            select(ContractRenewalLine)
            .where(ContractRenewalLine.opportunity_id == item.id)
            .order_by(ContractRenewalLine.id)
        )
    )
    return RenewalOpportunityRead(
        **{
            column.name: getattr(item, column.name)
            for column in ContractRenewalOpportunity.__table__.columns
        },
        lines=[RenewalLineRead.model_validate(line) for line in lines],
    )


@router.get("/contracts/{contract_id}/renewal-owners")
def list_renewal_owners(
    contract_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> list[dict[str, object]]:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    return [
        {"id": user.id, "full_name": user.full_name}
        for user in db.scalars(select(User).where(
            User.is_active.in_([True]), User.user_type == "EMPLOYEE"
        ).order_by(User.full_name))
        if can_receive_renewal(db, user, contract)
    ]


@router.get(
    "/contracts/{contract_id}/renewal-opportunities", response_model=list[RenewalOpportunityRead]
)
def list_renewal_opportunities(
    contract_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.view")),
) -> list[RenewalOpportunityRead]:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    return [
        renewal_read(db, item)
        for item in db.scalars(
            select(ContractRenewalOpportunity)
            .where(ContractRenewalOpportunity.source_contract_id == contract_id)
            .order_by(ContractRenewalOpportunity.created_at.desc())
        )
    ]


@router.post(
    "/contracts/{contract_id}/renewal-opportunities",
    response_model=RenewalOpportunityRead,
    status_code=201,
)
def create_renewal_opportunity(
    contract_id: int,
    data: RenewalOpportunityCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> RenewalOpportunityRead:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    existing = db.scalar(
        select(ContractRenewalOpportunity).where(
            ContractRenewalOpportunity.source_contract_id == contract_id,
            ContractRenewalOpportunity.idempotency_key == data.idempotency_key,
        )
    )
    if existing:
        return renewal_read(db, existing)
    owner = validate_renewal_owner(db, data.owner_user_id, contract)
    if len({line.coverage_id for line in data.lines}) != len(data.lines):
        raise ConflictError("INVALID_RENEWAL_LINE", "Each coverage line may appear only once.")
    if any(line.outcome != "PENDING" or line.successor_coverage_id for line in data.lines):
        raise ConflictError("INVALID_RENEWAL_LINE", "New opportunities must start with pending coverage lines.")
    active_coverage_ids = set(db.scalars(select(ContractCoverage.id).where(
        ContractCoverage.contract_id == contract_id, ContractCoverage.retired_at.is_(None)
    )))
    if not data.lines:
        data.lines = [RenewalLineWrite(coverage_id=coverage_id, outcome="PENDING") for coverage_id in sorted(active_coverage_ids)]
    coverage_ids = {line.coverage_id for line in data.lines}
    if coverage_ids != active_coverage_ids:
        raise ConflictError("INVALID_RENEWAL_LINE", "Include every non-retired coverage line in the renewal.")
    valid_ids = (
        set(
            db.scalars(
                select(ContractCoverage.id).where(
                    ContractCoverage.contract_id == contract_id,
                    ContractCoverage.id.in_(coverage_ids),
                )
            )
        )
        if coverage_ids
        else set()
    )
    if valid_ids != coverage_ids:
        raise ConflictError(
            "INVALID_RENEWAL_LINE", "Every renewal line must belong to the source contract."
        )
    item = ContractRenewalOpportunity(
        source_contract_id=contract_id,
        idempotency_key=data.idempotency_key,
        stage="IDENTIFIED",
        owner_user_id=owner.id,
        target_close_date=data.target_close_date,
        reason=data.reason,
        version=1,
        created_by_user_id=actor.id,
    )
    db.add(item)
    db.flush()
    for line in data.lines:
        db.add(ContractRenewalLine(opportunity_id=item.id, **line.model_dump()))
    due_at = datetime.combine(data.target_close_date, time(17, 0), tzinfo=server_timezone())
    db.add(
        ContractRenewalTask(
            opportunity_id=item.id,
            title="Prepare renewal proposal and coverage-line outcomes",
            assigned_user_id=owner.id,
            due_at=due_at,
            created_by_user_id=actor.id,
        )
    )
    db.add(
        Notification(
            recipient_user_id=owner.id,
            notification_type="CONTRACT_RENEWAL_ASSIGNED",
            severity="INFO",
            title=f"Renewal assigned: {contract.contract_number}",
            message=data.reason,
            deep_link=f"/contracts?section=contracts&contract_id={contract.id}&tab=renewals",
            deduplication_key=f"renewal-assigned:{item.id}:{owner.id}",
        )
    )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ContractRenewalOpportunity",
            entity_id=str(item.id),
            action="contract.renewal.created",
            reason=data.reason,
        )
    )
    db.commit()
    db.refresh(item)
    return renewal_read(db, item)


@router.put(
    "/contracts/{contract_id}/renewal-opportunities/{opportunity_id}",
    response_model=RenewalOpportunityRead,
)
def update_renewal_opportunity(
    contract_id: int,
    opportunity_id: int,
    data: RenewalOpportunityUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> RenewalOpportunityRead:
    contract = db.get(Contract, contract_id)
    item = db.get(ContractRenewalOpportunity, opportunity_id)
    if not contract or not item or item.source_contract_id != contract_id:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    apply_renewal_update(db, contract, item, data, actor)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ContractRenewalOpportunity",
            entity_id=str(item.id),
            action="contract.renewal.updated",
            reason=data.reason,
            new_values_json=json.dumps(data.model_dump(), default=str),
        )
    )
    db.commit()
    db.refresh(item)
    return renewal_read(db, item)


def _lifecycle_stage(
    contract: Contract,
    renewal: ContractRenewalOpportunity | None,
    today: date,
) -> str:
    if renewal and renewal.stage == "CLOSED":
        return "RENEWED" if renewal.outcome in {"RENEWED", "PARTIAL"} else "NOT_RENEWED"
    if renewal and renewal.stage != "CLOSED":
        return "RENEWING"
    if contract.status in {"TERMINATED", "SUSPENDED"} or not contract.is_active:
        return "NOT_RENEWED"
    if contract.end_date < today:
        return "EXPIRED"
    if contract.end_date <= today + timedelta(days=60):
        return "EXPIRING"
    return "ACTIVE"


@router.get("/contracts/lifecycle/board")
def contract_lifecycle_board(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.view")),
) -> dict[str, object]:
    """Return a compact, computed contract board without duplicating lifecycle state."""
    today = server_today()
    statement = select(Contract)
    if actor.user_type == "CLIENT_PORTAL":
        scopes = effective_permissions(db, actor).client_scope_ids or [-1]
        statement = statement.where(
            or_(
                Contract.applies_to_all_clients.in_([True]),
                Contract.client_id.in_(scopes),
                Contract.client_links.any(ContractClientLink.client_id.in_(scopes)),
            )
        )
    contracts = list(db.scalars(statement.order_by(Contract.end_date, Contract.id)))
    contract_ids = {item.id for item in contracts}
    client_ids = {customer_id for item in contracts for customer_id in item.customer_ids}
    renewals: dict[int, ContractRenewalOpportunity] = {}
    if contract_ids:
        for row in db.scalars(
            select(ContractRenewalOpportunity)
            .where(ContractRenewalOpportunity.source_contract_id.in_(contract_ids))
            .order_by(
                ContractRenewalOpportunity.source_contract_id,
                ContractRenewalOpportunity.created_at.desc(),
            )
        ):
            renewals.setdefault(row.source_contract_id, row)
    clients = {
        item.id: item for item in db.scalars(select(Client).where(Client.id.in_(client_ids or {-1})))
    }
    types = {
        item.id: item
        for item in db.scalars(
            select(ContractType).where(
                ContractType.id.in_({item.contract_type_id for item in contracts if item.contract_type_id} or {-1})
            )
        )
    }
    coverages: dict[int, list[ContractCoverage]] = {}
    for coverage_row in db.scalars(
        select(ContractCoverage).where(
            ContractCoverage.contract_id.in_(contract_ids or {-1}),
            ContractCoverage.retired_at.is_(None),
            ContractCoverage.is_covered.in_([True]),
        )
    ):
        coverages.setdefault(coverage_row.contract_id, []).append(coverage_row)
    product_ids = {row.product_id for rows in coverages.values() for row in rows if row.product_id}
    products = {
        item.id: item.name
        for item in db.scalars(select(Product).where(Product.id.in_(product_ids or {-1})))
    }
    visit_rows = list(
        db.scalars(
            select(ClientVisitEntitlement).where(
                ClientVisitEntitlement.contract_id.in_(contract_ids or {-1})
            )
        )
    )
    visit_types = {
        item.id: item.name
        for item in db.scalars(
            select(VisitType).where(
                VisitType.id.in_({row.visit_type_id for row in visit_rows} or {-1})
            )
        )
    }
    visit_by_contract: dict[int, list[dict[str, object]]] = {}
    for entitlement in visit_rows:
        balance = int(
            db.scalar(
                select(func.coalesce(func.sum(VisitEntitlementLedgerEntry.quantity), 0)).where(
                    VisitEntitlementLedgerEntry.entitlement_id == entitlement.id
                )
            )
            or 0
        )
        overdue = int(
            db.scalar(
                select(func.count(ClientVisitOccurrence.id)).where(
                    ClientVisitOccurrence.entitlement_id == entitlement.id,
                    ClientVisitOccurrence.window_end < today,
                    ClientVisitOccurrence.status.notin_(["COMPLETED", "CANCELLED", "SUPERSEDED"]),
                )
            )
            or 0
        )
        visit_by_contract.setdefault(entitlement.contract_id, []).append(
            {
                "type": visit_types.get(entitlement.visit_type_id, f"Visit #{entitlement.visit_type_id}"),
                "allowed": entitlement.allowed_visits,
                "remaining": max(0, balance),
                "overdue": overdue,
                "status": entitlement.status,
            }
        )
    cards: list[dict[str, object]] = []
    for contract in contracts:
        renewal = renewals.get(contract.id)
        customer_names = [clients[customer_id].name for customer_id in sorted(contract.customer_ids) if customer_id in clients]
        contract_type = types.get(contract.contract_type_id) if contract.contract_type_id is not None else None
        days_remaining = (contract.end_date - today).days
        product_names = sorted(
            {products[row.product_id] for row in coverages.get(contract.id, []) if row.product_id in products}
        )
        cards.append(
            {
                "id": contract.id,
                "contract_number": contract.contract_number,
                "name": contract.name,
                "client_id": contract.client_id,
                "client_name": "All clients" if contract.applies_to_all_clients else ", ".join(customer_names),
                "linked_client_ids": sorted(contract.customer_ids),
                "contract_type": contract_type.name if contract_type is not None else None,
                "stage": _lifecycle_stage(contract, renewal, today),
                "status": contract.status,
                "start_date": contract.start_date,
                "end_date": contract.end_date,
                "days_remaining": days_remaining,
                "has_sla": contract.has_sla,
                "sla_ready": not contract.has_sla or contract.sla_policy_id is not None,
                "products": product_names[:4],
                "product_count": len(product_names),
                "renewal_id": renewal.id if renewal else None,
                "renewal_owner_user_id": renewal.owner_user_id if renewal else None,
                "renewal_target_date": renewal.target_close_date if renewal else None,
                "successor_contract_id": renewal.successor_contract_id if renewal else None,
                "visits": visit_by_contract.get(contract.id, []),
            }
        )
    counts = {stage: 0 for stage in ("ACTIVE", "EXPIRING", "RENEWING", "RENEWED", "EXPIRED", "NOT_RENEWED")}
    for card in cards:
        counts[str(card["stage"])] += 1
    return {"as_of": today, "counts": counts, "cards": cards}


@router.post("/contracts/{contract_id}/lifecycle-transition")
def transition_contract_lifecycle(
    contract_id: int,
    data: ContractLifecycleTransition,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> dict[str, object]:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    latest = db.scalar(
        select(ContractRenewalOpportunity)
        .where(ContractRenewalOpportunity.source_contract_id == contract.id)
        .order_by(ContractRenewalOpportunity.created_at.desc())
        .limit(1)
    )
    if data.action == "START_RENEWAL":
        if latest and latest.stage != "CLOSED":
            return {"contract_id": contract.id, "stage": "RENEWING", "renewal_id": latest.id}
        if not data.owner_user_id or not data.target_close_date:
            raise ConflictError("RENEWAL_DETAILS_REQUIRED", "Renewal owner and target date are required.")
        owner = validate_renewal_owner(db, data.owner_user_id, contract)
        latest = ContractRenewalOpportunity(
            source_contract_id=contract.id,
            idempotency_key=f"lifecycle:{contract.id}:{uuid4()}",
            stage="IDENTIFIED",
            owner_user_id=owner.id,
            target_close_date=data.target_close_date,
            reason=data.reason,
            version=1,
            created_by_user_id=actor.id,
        )
        db.add(latest)
        db.flush()
        for coverage_id in db.scalars(
            select(ContractCoverage.id).where(
                ContractCoverage.contract_id == contract.id,
                ContractCoverage.retired_at.is_(None),
            )
        ):
            db.add(ContractRenewalLine(opportunity_id=latest.id, coverage_id=coverage_id, outcome="PENDING"))
        db.add(ContractRenewalTask(opportunity_id=latest.id, title="Complete contract renewal", assigned_user_id=owner.id, due_at=datetime.combine(data.target_close_date, time(17), tzinfo=server_timezone()), created_by_user_id=actor.id))
        db.add(Notification(recipient_user_id=owner.id, notification_type="CONTRACT_RENEWAL_ASSIGNED", severity="WARNING", title=f"Renewal assigned: {contract.contract_number}", message=data.reason, deep_link=f"/contracts?section=contracts&contract_id={contract.id}&tab=renewals", deduplication_key=f"lifecycle-renewal:{latest.id}:user:{owner.id}"))
    elif data.action in {"MARK_RENEWED", "MARK_NOT_RENEWED"}:
        if not latest:
            raise ConflictError("RENEWAL_REQUIRED", "Start the renewal before marking it renewed.")
        if data.version is None:
            raise ConflictError("STALE_RENEWAL", "Open the renewal workspace to review its version and coverage lines.")
        apply_renewal_update(db, contract, latest, RenewalOpportunityUpdate(
            stage="CLOSED", outcome="RENEWED" if data.action == "MARK_RENEWED" else "LOST",
            successor_contract_id=data.successor_contract_id, reason=data.reason,
            version=data.version, lines=data.lines,
        ), actor)
    elif data.action == "REACTIVATE":
        if contract.end_date < server_today():
            raise ConflictError("CONTRACT_EXPIRED", "Extend the contract before reactivating it.")
        contract.status, contract.is_active = "ACTIVE", True
    elif data.action == "EXTEND":
        if not data.new_end_date or data.new_end_date <= contract.end_date:
            raise ConflictError("INVALID_EXTENSION", "The new end date must be after the current end date.")
        reconcile_contract_dates(db, contract, contract.start_date, data.new_end_date, actor)
        contract.end_date, contract.status, contract.is_active = data.new_end_date, "ACTIVE", True
    db.add(AuditLog(actor_user_id=actor.id, entity_type="Contract", entity_id=str(contract.id), action=f"contract.lifecycle.{data.action.lower()}", reason=data.reason, new_values_json=json.dumps(data.model_dump(), default=str)))
    affected_clients = {contract.client_id, *contract.linked_client_ids}
    if data.action == "MARK_RENEWED" and data.successor_contract_id:
        successor = db.get(Contract, data.successor_contract_id)
        if successor:
            affected_clients.update({successor.client_id, *successor.linked_client_ids})
    recalculate_client_contract_service_status(db, affected_clients)
    db.commit()
    return {"contract_id": contract.id, "stage": _lifecycle_stage(contract, latest, server_today()), "renewal_id": latest.id if latest else None}


@router.get("/contracts/{contract_id}/documents", response_model=list[ContractDocumentRead])
def list_contract_documents(
    contract_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.view")),
) -> list[ContractDocument]:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    return list(
        db.scalars(
            select(ContractDocument)
            .where(ContractDocument.contract_id == contract_id)
            .order_by(ContractDocument.created_at.desc())
        )
    )


@router.post(
    "/contracts/{contract_id}/documents", response_model=ContractDocumentRead, status_code=201
)
async def upload_contract_document(
    contract_id: int,
    upload: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
    settings: Settings = Depends(get_settings),
) -> ContractDocument:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    original, stored, content_type, size = await store_contract_document(
        upload, contract_id, settings
    )
    document = ContractDocument(
        contract_id=contract_id,
        original_filename=original,
        stored_filename=stored,
        content_type=content_type,
        size_bytes=size,
        uploaded_by_user_id=actor.id,
    )
    db.add(document)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ContractDocument",
            entity_id=str(document.id),
            action="contract.document.uploaded",
            new_values_json=json.dumps({"filename": original, "size_bytes": size}),
        )
    )
    db.commit()
    db.refresh(document)
    return document


@router.get("/contracts/{contract_id}/documents/{document_id}/download")
def download_contract_document(
    contract_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.view")),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    document = db.get(ContractDocument, document_id)
    if not document or document.contract_id != contract_id:
        raise NotFoundError()
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    return FileResponse(
        contract_document_path(document, settings),
        media_type=document.content_type,
        filename=document.original_filename,
    )


@router.delete("/contracts/{contract_id}/documents/{document_id}", status_code=204)
def delete_contract_document(
    contract_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
    settings: Settings = Depends(get_settings),
) -> None:
    document = db.get(ContractDocument, document_id)
    if not document or document.contract_id != contract_id:
        raise NotFoundError()
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    path = contract_document_path(document, settings)
    db.delete(document)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="ContractDocument",
            entity_id=str(document.id),
            action="contract.document.deleted",
            reason=document.original_filename,
        )
    )
    db.commit()
    path.unlink(missing_ok=True)


@router.get("/entitlements/check", response_model=EntitlementCheckRead)
def check_entitlement(
    client_id: int,
    branch_id: int | None = None,
    product_id: int | None = None,
    product_module_id: int | None = None,
    environment_id: int | None = None,
    service_id: int | None = None,
    ticket_type_id: int | None = None,
    contract_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.create")),
) -> EntitlementCheckRead:
    if (
        actor.user_type == "CLIENT_PORTAL"
        and client_id not in effective_permissions(db, actor).client_scope_ids
    ):
        raise NotFoundError("Client does not exist.")
    result, contract, reason = evaluate_entitlement(
        db,
        client_id=client_id,
        branch_id=branch_id,
        product_id=product_id,
        product_module_id=product_module_id,
        environment_id=environment_id,
        service_id=service_id,
        ticket_type_id=ticket_type_id,
        preferred_contract_id=contract_id,
    )
    return EntitlementCheckRead(
        status=result,
        contract_id=contract.id if contract else None,
        contract_number=contract.contract_number if contract else None,
        reason=reason,
    )


@router.get("/entitlements/candidates", response_model=list[EntitlementCandidateRead])
def entitlement_candidates(
    client_id: int,
    branch_id: int | None = None,
    product_id: int | None = None,
    product_module_id: int | None = None,
    environment_id: int | None = None,
    service_id: int | None = None,
    ticket_type_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("ticket.create")),
) -> list[EntitlementCandidateRead]:
    if (
        actor.user_type == "CLIENT_PORTAL"
        and client_id not in effective_permissions(db, actor).client_scope_ids
    ):
        raise NotFoundError("Client does not exist.")
    today = server_today()
    possible = list(
        db.scalars(
            select(Contract)
            .where(
                or_(
                    Contract.applies_to_all_clients.in_([True]),
                    Contract.client_id == client_id,
                    Contract.client_links.any(ContractClientLink.client_id == client_id),
                ),
                Contract.is_active.in_([True]),
                Contract.status == "ACTIVE",
                Contract.start_date <= today,
                Contract.end_date >= today,
            )
            .order_by(Contract.is_shared_default, Contract.start_date.desc())
        )
    )
    results: list[EntitlementCandidateRead] = []
    for candidate in possible:
        result, selected, reason = evaluate_entitlement(
            db,
            client_id=client_id,
            branch_id=branch_id,
            product_id=product_id,
            product_module_id=product_module_id,
            environment_id=environment_id,
            service_id=service_id,
            ticket_type_id=ticket_type_id,
            preferred_contract_id=candidate.id,
        )
        if selected is None or selected.id != candidate.id:
            continue
        results.append(
            EntitlementCandidateRead(
                contract_id=candidate.id,
                contract_number=candidate.contract_number,
                contract_name=candidate.name,
                contract_type=candidate.contract_type.name if candidate.contract_type else None,
                precedence=candidate.contract_type.precedence if candidate.contract_type else 900,
                start_date=candidate.start_date,
                end_date=candidate.end_date,
                status=result,
                reason=reason,
            )
        )
    return sorted(results, key=lambda item: (item.precedence, item.end_date, item.contract_id))


@router.get("/business-calendars", response_model=list[CalendarRead])
def list_calendars(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("contract.view")),
) -> list[BusinessCalendar]:
    return list(db.scalars(select(BusinessCalendar).where(BusinessCalendar.is_active.in_([True]))))


@router.get("/business-calendars/{calendar_id}/schedule", response_model=CalendarScheduleRead)
def get_calendar_schedule(
    calendar_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("contract.view")),
) -> CalendarScheduleRead:
    calendar = db.get(BusinessCalendar, calendar_id)
    if not calendar:
        raise NotFoundError("Business calendar does not exist.")
    days = list(
        db.scalars(
            select(BusinessCalendarDay)
            .where(BusinessCalendarDay.calendar_id == calendar_id)
            .order_by(BusinessCalendarDay.weekday)
        )
    )
    return CalendarScheduleRead(
        id=calendar.id,
        code=calendar.code,
        name=calendar.name,
        timezone=calendar.timezone,
        days=days,
    )


@router.put("/business-calendars/{calendar_id}/schedule", response_model=CalendarScheduleRead)
def update_calendar_schedule(
    calendar_id: int,
    data: CalendarScheduleWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> CalendarScheduleRead:
    calendar = db.get(BusinessCalendar, calendar_id)
    if not calendar:
        raise NotFoundError("Business calendar does not exist.")
    calendar.timezone = data.timezone
    db.execute(delete(BusinessCalendarDay).where(BusinessCalendarDay.calendar_id == calendar_id))
    db.flush()
    db.add_all(
        [BusinessCalendarDay(calendar_id=calendar_id, **item.model_dump()) for item in data.days]
    )
    db.flush()
    policy_ids = select(SlaPolicy.id).where(SlaPolicy.calendar_id == calendar_id)
    for clock in db.scalars(
        select(TicketSlaClock).where(
            or_(TicketSlaClock.calendar_id == calendar_id,
                (TicketSlaClock.calendar_id.is_(None)) & TicketSlaClock.policy_id.in_(policy_ids)),
            TicketSlaClock.state.in_(["RUNNING", "PAUSED"]),
        )
    ):
        if clock.state == "PAUSED" and clock.start_anchor_at is None:
            continue
        clock.due_at = calculate_due_at(
            db, calendar_id, clock.start_anchor_at or clock.started_at, clock.target_minutes
        )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="BusinessCalendar",
            entity_id=str(calendar.id),
            action="business_calendar.schedule_updated",
            new_values_json=json.dumps(data.model_dump(), default=str),
        )
    )
    db.commit()
    return get_calendar_schedule(calendar_id, db, actor)


@router.get("/contracts/{contract_id}/sla/coverage-preview")
def preview_contract_sla_coverage(
    contract_id: int,
    policy_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.view")),
) -> list[dict[str, int | str | None]]:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    policy = db.get(SlaPolicy, policy_id or contract.sla_policy_id) if (policy_id or contract.sla_policy_id) else None
    if not policy:
        return []
    if policy.contract_id not in {None, contract_id}:
        raise NotFoundError("SLA policy does not belong to this contract.")
    today = server_today()
    rows = db.scalars(select(ContractCoverage).where(
        ContractCoverage.contract_id == contract_id,
        ContractCoverage.is_covered.in_([True]),
        ContractCoverage.retired_at.is_(None),
        or_(ContractCoverage.effective_from.is_(None), ContractCoverage.effective_from <= today),
        or_(ContractCoverage.effective_until.is_(None), ContractCoverage.effective_until >= today),
    ))
    result: list[dict[str, int | str | None]] = []
    for coverage in rows:
        for priority in ("P1", "P2", "P3", "P4"):
            target, reason = resolve_product_scoped_sla_target(
                db, policy_id=policy.id, priority=priority,
                product_id=coverage.product_id,
                product_module_id=coverage.product_module_id,
                service_id=coverage.service_id,
            )
            result.append({
                "coverage_id": coverage.id,
                "product_id": coverage.product_id,
                "service_id": coverage.service_id,
                "priority": priority,
                "target_id": target.id if target else None,
                "match_reason": reason if policy.is_active else "SLA_POLICY_INACTIVE",
            })
    return result


@router.get("/contracts/{contract_id}/sla", response_model=ContractSlaRead | None)
def get_contract_sla(
    contract_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.view")),
) -> ContractSlaRead | None:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    policy = db.get(SlaPolicy, contract.sla_policy_id) if contract.sla_policy_id else None
    if not policy:
        return None
    targets = list(
        db.scalars(
            select(SlaTarget)
            .where(SlaTarget.policy_id == policy.id)
            .order_by(SlaTarget.service_id, SlaTarget.priority)
        )
    )
    return ContractSlaRead(
        id=policy.id,
        code=policy.code,
        name=policy.name,
        contract_id=policy.contract_id,
        calendar_id=policy.calendar_id,
        is_active=policy.is_active,
        include_escalation_time=policy.include_escalation_time,
        targets=targets,
    )


@router.put("/contracts/{contract_id}/sla", response_model=ContractSlaRead)
def save_contract_sla(
    contract_id: int,
    data: ContractSlaWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> ContractSlaRead:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    if data.policy_id:
        policy = db.get(SlaPolicy, data.policy_id)
        if not policy or policy.contract_id is not None:
            raise NotFoundError("Central SLA policy does not exist.")
        if not sla_policy_ready(db, policy):
            raise ConflictError("SLA_POLICY_NOT_READY", "Publish active SLA targets before linking this template.")
        contract.sla_policy_id = policy.id
        db.add(
            AuditLog(
                actor_user_id=actor.id,
                entity_type="Contract",
                entity_id=str(contract.id),
                action="contract.sla.linked",
                new_values_json=json.dumps({"sla_policy_id": policy.id}),
            )
        )
        db.commit()
        saved = get_contract_sla(contract_id, db, actor)
        assert saved is not None
        return saved
    if not data.calendar_id or not db.get(BusinessCalendar, data.calendar_id):
        raise NotFoundError("Business calendar does not exist.")
    policy = db.scalar(select(SlaPolicy).where(SlaPolicy.contract_id == contract_id))
    if not policy:
        policy = SlaPolicy(
            code=data.code or f"CONTRACT_{contract_id}_{uuid4().hex[:12]}",
            name=data.name or f"{contract.name} SLA",
            contract_id=contract_id,
            calendar_id=data.calendar_id,
            is_active=data.is_active,
        )
        db.add(policy)
        db.flush()
    else:
        policy.name, policy.calendar_id, policy.is_active = (
            data.name or policy.name,
            data.calendar_id,
            data.is_active,
        )
    contract.sla_policy_id = policy.id
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="SlaPolicy",
            entity_id=str(policy.id),
            action="contract.sla.saved",
        )
    )
    db.commit()
    saved = get_contract_sla(contract_id, db, actor)
    assert saved is not None
    return saved


@router.delete("/contracts/{contract_id}/sla", status_code=204)
def unlink_contract_sla(
    contract_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> None:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    previous_policy_id = contract.sla_policy_id
    contract.sla_policy_id = None
    db.add(AuditLog(
        actor_user_id=actor.id,
        entity_type="Contract",
        entity_id=str(contract.id),
        action="contract.sla.unlinked",
        old_values_json=json.dumps({"sla_policy_id": previous_policy_id}),
    ))
    db.commit()


@router.post("/contracts/{contract_id}/sla/targets", response_model=SlaTargetRead, status_code=201)
def add_sla_target(
    contract_id: int,
    data: SlaTargetWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> SlaTarget:
    contract = db.get(Contract, contract_id)
    policy = db.get(SlaPolicy, contract.sla_policy_id) if contract and contract.sla_policy_id else None
    if not contract or not policy:
        raise NotFoundError("Create the contract SLA first.")
    ensure_contract_access(db, actor, contract)
    if policy.contract_id != contract_id:
        source_policy = policy
        policy = SlaPolicy(
            code=f"CONTRACT_{contract_id}_{uuid4().hex[:12]}",
            name=f"{contract.name} SLA",
            contract_id=contract_id,
            calendar_id=source_policy.calendar_id,
            is_active=True,
            include_escalation_time=source_policy.include_escalation_time,
        )
        db.add(policy)
        db.flush()
        source_targets = list(
            db.scalars(select(SlaTarget).where(SlaTarget.policy_id == source_policy.id))
        )
        db.add_all(
            SlaTarget(
                policy_id=policy.id,
                product_id=row.product_id,
                product_module_id=row.product_module_id,
                service_id=row.service_id,
                priority=row.priority,
                first_response_minutes=row.first_response_minutes,
                resolution_minutes=row.resolution_minutes,
                warning_percent=row.warning_percent,
                is_fallback=row.is_fallback,
                effective_from=row.effective_from,
                effective_until=row.effective_until,
            )
            for row in source_targets
        )
        db.flush()
        contract.sla_policy_id = policy.id
        db.add(
            AuditLog(
                actor_user_id=actor.id,
                entity_type="SlaPolicy",
                entity_id=str(policy.id),
                action="contract.sla.central_policy_cloned",
                old_values_json=json.dumps({"source_policy_id": source_policy.id}),
                new_values_json=json.dumps({"contract_id": contract_id}),
            )
        )
    validate_sla_target_context(db, data)
    existing = db.scalar(
        select(SlaTarget).where(
            SlaTarget.policy_id == policy.id, SlaTarget.context_key == sla_target_context_key(data)
        )
    )
    if existing:
        for field, value in data.model_dump().items():
            setattr(existing, field, value)
        existing.version += 1
        target = existing
    else:
        target = SlaTarget(policy_id=policy.id, **data.model_dump())
        db.add(target)
    policy.version += 1
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="SlaTarget",
            entity_id=str(target.id),
            action="contract.sla.target.saved",
        )
    )
    publish_sla_policy(policy.id, db, actor)
    db.refresh(target)
    return target


@router.post(
    "/contracts/{contract_id}/sla/targets/bulk",
    response_model=list[SlaTargetRead],
    status_code=201,
)
def add_sla_targets_bulk(
    contract_id: int,
    data: SlaTargetBulkWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> list[SlaTarget]:
    contract = db.get(Contract, contract_id)
    policy = db.get(SlaPolicy, contract.sla_policy_id) if contract and contract.sla_policy_id else None
    if not contract or not policy:
        raise NotFoundError("Create the contract SLA first.")
    ensure_contract_access(db, actor, contract)
    if policy.contract_id != contract_id:
        source_policy = policy
        policy = SlaPolicy(
            code=f"CONTRACT_{contract_id}_{uuid4().hex[:12]}",
            name=f"{contract.name} SLA",
            contract_id=contract_id,
            calendar_id=source_policy.calendar_id,
            is_active=True,
            include_escalation_time=source_policy.include_escalation_time,
        )
        db.add(policy)
        db.flush()
        for row in db.scalars(select(SlaTarget).where(SlaTarget.policy_id == source_policy.id)):
            db.add(SlaTarget(
                policy_id=policy.id,
                product_id=row.product_id,
                product_module_id=row.product_module_id,
                service_id=row.service_id,
                priority=row.priority,
                first_response_minutes=row.first_response_minutes,
                resolution_minutes=row.resolution_minutes,
                warning_percent=row.warning_percent,
                is_fallback=row.is_fallback,
                effective_from=row.effective_from,
                effective_until=row.effective_until,
            ))
        db.flush()
        contract.sla_policy_id = policy.id

    coverage_rows = list(db.scalars(select(ContractCoverage).where(
        ContractCoverage.contract_id == contract_id,
        ContractCoverage.id.in_(list(dict.fromkeys(data.coverage_ids))),
        ContractCoverage.is_covered.in_([True]),
    )))
    if len({row.id for row in coverage_rows}) != len(set(data.coverage_ids)):
        raise ConflictError(
            "INVALID_SLA_COVERAGE",
            "Every selected SLA scope must be active coverage assigned to this contract.",
        )
    saved: list[SlaTarget] = []
    seen: set[str] = set()
    for coverage in coverage_rows:
        for priority in data.priorities:
            target_data = SlaTargetWrite(
                product_id=coverage.product_id,
                product_module_id=coverage.product_module_id,
                service_id=coverage.service_id,
                priority=priority,
                first_response_minutes=data.first_response_minutes,
                resolution_minutes=data.resolution_minutes,
                warning_percent=data.warning_percent,
                effective_from=data.effective_from,
                effective_until=data.effective_until,
            )
            key = sla_target_context_key(target_data)
            if key in seen:
                continue
            seen.add(key)
            target = db.scalar(select(SlaTarget).where(
                SlaTarget.policy_id == policy.id,
                SlaTarget.context_key == key,
            ))
            if target:
                for field, value in target_data.model_dump().items():
                    setattr(target, field, value)
                target.version += 1
            else:
                target = SlaTarget(policy_id=policy.id, **target_data.model_dump())
                db.add(target)
            db.flush()
            saved.append(target)
    policy.version += 1
    db.add(AuditLog(
        actor_user_id=actor.id,
        entity_type="SlaPolicy",
        entity_id=str(policy.id),
        action="contract.sla.targets.bulk_saved",
        new_values_json=json.dumps({
            "coverage_ids": data.coverage_ids,
            "priorities": data.priorities,
            "target_count": len(saved),
        }),
    ))
    publish_sla_policy(policy.id, db, actor)
    for target in saved:
        db.refresh(target)
    return saved


@router.delete("/contracts/{contract_id}/sla/targets/{target_id}", status_code=204)
def delete_sla_target(
    contract_id: int,
    target_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.manage")),
) -> None:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise NotFoundError()
    target = db.get(SlaTarget, target_id)
    policy = db.get(SlaPolicy, target.policy_id) if target else None
    if not target or not policy or policy.id != contract.sla_policy_id or policy.contract_id not in {None, contract_id}:
        raise NotFoundError()
    ensure_contract_access(db, actor, contract)
    if not db.scalar(select(SlaTarget.id).where(SlaTarget.policy_id == policy.id, SlaTarget.id != target.id)):
        raise ConflictError("SLA_TARGETS_REQUIRED", "A contract SLA must retain at least one target.")
    if policy.contract_id is None:
        local_policy = SlaPolicy(
            code=f"CONTRACT_{contract_id}_{uuid4().hex[:12]}",
            name=f"{contract.name} SLA",
            contract_id=contract_id,
            calendar_id=policy.calendar_id,
            is_active=True,
            include_escalation_time=policy.include_escalation_time,
        )
        db.add(local_policy)
        db.flush()
        remaining_targets = db.scalars(
            select(SlaTarget).where(
                SlaTarget.policy_id == policy.id,
                SlaTarget.id != target.id,
            )
        )
        db.add_all(
            SlaTarget(
                policy_id=local_policy.id,
                product_id=row.product_id,
                product_module_id=row.product_module_id,
                service_id=row.service_id,
                priority=row.priority,
                first_response_minutes=row.first_response_minutes,
                resolution_minutes=row.resolution_minutes,
                warning_percent=row.warning_percent,
                is_fallback=row.is_fallback,
                effective_from=row.effective_from,
                effective_until=row.effective_until,
            )
            for row in remaining_targets
        )
        contract.sla_policy_id = local_policy.id
        db.add(
            AuditLog(
                actor_user_id=actor.id,
                entity_type="SlaTarget",
                entity_id=str(target.id),
                action="contract.sla.target.removed_from_central_policy",
                old_values_json=json.dumps({"source_policy_id": policy.id}),
                new_values_json=json.dumps(
                    {"contract_id": contract_id, "local_policy_id": local_policy.id}
                ),
            )
        )
    else:
        if db.scalar(select(TicketSlaClock.id).where(TicketSlaClock.target_id == target.id)):
            raise ConflictError("SLA_TARGET_IN_USE", "This target has ticket history and cannot be deleted.")
        db.execute(update(SlaTargetVersion).where(SlaTargetVersion.source_target_id == target.id).values(source_target_id=None))
        db.delete(target)
        policy.version += 1
    db.flush()
    publish_sla_policy(contract.sla_policy_id, db, actor)


@router.get("/tickets/{ticket_id}/sla", response_model=list[SlaClockRead])
def ticket_sla(
    ticket_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.view")),
) -> list[TicketSlaClock]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError("Ticket does not exist.")
    ticket_type = db.get(TicketType, ticket.ticket_type_id)
    if ticket_type and ticket_type.code == "CHANGE_REQUEST":
        return []
    if actor.user_type == "CLIENT_PORTAL":
        ensure_ticket_access(db, actor, ticket)
    return list(
        db.scalars(
            select(TicketSlaClock)
            .where(TicketSlaClock.ticket_id == ticket_id)
            .order_by(TicketSlaClock.clock_type)
        )
    )


@router.get(
    "/tickets/{ticket_id}/sla/shadow-comparison",
    response_model=SlaShadowComparisonRead | None,
)
def ticket_sla_shadow_comparison(
    ticket_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contract.view")),
) -> SlaShadowComparison | None:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError("Ticket does not exist.")
    if actor.user_type == "CLIENT_PORTAL":
        ensure_ticket_access(db, actor, ticket)
    return db.scalar(select(SlaShadowComparison).where(SlaShadowComparison.ticket_id == ticket_id))


@router.get("/sla/shadow-comparisons", response_model=list[SlaShadowComparisonRead])
def list_sla_shadow_comparisons(
    outcome: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("contract.view")),
) -> list[SlaShadowComparison]:
    statement = select(SlaShadowComparison)
    if outcome:
        statement = statement.where(SlaShadowComparison.outcome == outcome.upper())
    return list(
        db.scalars(statement.order_by(SlaShadowComparison.evaluated_at.desc()).limit(limit))
    )
