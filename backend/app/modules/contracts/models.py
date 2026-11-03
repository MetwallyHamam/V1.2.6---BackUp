from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class BusinessCalendar(Base):
    __tablename__ = "business_calendars"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    timezone: Mapped[str] = mapped_column(String(100), default="Africa/Cairo")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class BusinessCalendarDay(Base):
    __tablename__ = "business_calendar_days"
    __table_args__ = (UniqueConstraint("calendar_id", "weekday"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    calendar_id: Mapped[int] = mapped_column(IdType, ForeignKey("business_calendars.id", ondelete="CASCADE"))
    weekday: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column()
    end_time: Mapped[time] = mapped_column()
    is_working_day: Mapped[bool] = mapped_column(Boolean, default=True)


class Holiday(Base):
    __tablename__ = "holidays"
    __table_args__ = (UniqueConstraint("calendar_id", "holiday_date"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    calendar_id: Mapped[int] = mapped_column(IdType, ForeignKey("business_calendars.id", ondelete="CASCADE"))
    holiday_date: Mapped[date] = mapped_column(Date)
    name: Mapped[str] = mapped_column(String(150))


class ContractType(Base):
    __tablename__ = "contract_types"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    description: Mapped[str | None] = mapped_column(String(1000))
    precedence: Mapped[int] = mapped_column(Integer, default=100)
    default_has_sla: Mapped[bool] = mapped_column(Boolean, default=True)
    default_duration_days: Mapped[int | None] = mapped_column(Integer)
    expiry_behavior: Mapped[str] = mapped_column(String(30), default="EXPIRE")
    approval_behavior: Mapped[str] = mapped_column(String(30), default="INHERIT")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Contract(Base):
    __tablename__ = "contracts"
    __table_args__ = (
        Index("ix_contracts_client_status_end", "client_id", "status", "end_date"),
        Index(
            "uq_contract_onboarding_idempotency",
            "onboarding_idempotency_key",
            unique=True,
            mssql_where=text("onboarding_idempotency_key IS NOT NULL"),
            sqlite_where=text("onboarding_idempotency_key IS NOT NULL"),
        ),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    contract_number: Mapped[str] = mapped_column(String(80), unique=True)
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id"))
    contract_type_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contract_types.id"))
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    acceptance_date: Mapped[date | None] = mapped_column(Date)
    source_template_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("contract_templates.id")
    )
    source_template_version: Mapped[int | None] = mapped_column(Integer)
    onboarding_idempotency_key: Mapped[str | None] = mapped_column(String(200))
    renewal_notice_date: Mapped[date | None] = mapped_column(Date)
    timezone: Mapped[str] = mapped_column(String(100), default="Africa/Cairo")
    calendar_id: Mapped[int] = mapped_column(IdType, ForeignKey("business_calendars.id"))
    sla_policy_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("sla_policies.id", name="fk_contracts_sla_policy", use_alter=True))
    has_sla: Mapped[bool] = mapped_column(Boolean, default=True)
    ticket_catalog_visibility: Mapped[str] = mapped_column(String(30), default="CONTRACT_ONLY")
    require_product_on_ticket: Mapped[bool] = mapped_column(Boolean, default=True)
    require_module_on_ticket: Mapped[bool] = mapped_column(Boolean, default=False)
    require_service_on_ticket: Mapped[bool] = mapped_column(Boolean, default=False)
    coverage_validation_level: Mapped[str] = mapped_column(String(30), default="PRODUCT")
    expiry_grace_days: Mapped[int] = mapped_column(Integer, default=0)
    approval_group_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("approval_groups.id", use_alter=True)
    )
    support_summary: Mapped[str | None] = mapped_column(Text)
    exclusions: Mapped[str | None] = mapped_column(Text)
    included_request_limit: Mapped[int | None] = mapped_column(Integer)
    escalation_contact_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contacts.id"))
    is_shared_default: Mapped[bool] = mapped_column(Boolean, default=False)
    applies_to_all_clients: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    client_links: Mapped[list["ContractClientLink"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    contract_type: Mapped[ContractType | None] = relationship()

    @property
    def linked_client_ids(self) -> list[int]:
        return [link.client_id for link in self.client_links]

    @property
    def customer_ids(self) -> set[int]:
        """All clients are peers; client_id is a compatibility reference for old records."""
        return {self.client_id, *self.linked_client_ids}


class ContractExpirationNotificationDelivery(Base):
    __tablename__ = "contract_expiration_notification_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "contract_id",
            "contract_end_date",
            "milestone_key",
            "channel",
            "recipient_key",
            name="uq_contract_expiration_delivery_milestone",
        ),
        Index("ix_contract_expiration_delivery_status", "status", "queued_at"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False
    )
    contract_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    milestone_key: Mapped[str] = mapped_column(String(100), nullable=False)
    milestone_days: Mapped[int | None] = mapped_column(Integer)
    rule_version: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient_key: Mapped[str] = mapped_column(String(320), nullable=False)
    to_json: Mapped[str] = mapped_column(Text, default="[]")
    cc_json: Mapped[str] = mapped_column(Text, default="[]")
    notification_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("notifications.id", ondelete="SET NULL")
    )
    outbox_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("event_outbox.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(20), default="QUEUED")
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ContractTemplate(Base):
    __tablename__ = "contract_templates"
    __table_args__ = (UniqueConstraint("code", name="uq_contract_template_code"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(String(1000))
    template_type: Mapped[str] = mapped_column(String(50), default="GLOBAL")
    contract_type_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contract_types.id"))
    calendar_id: Mapped[int] = mapped_column(IdType, ForeignKey("business_calendars.id"))
    sla_policy_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("sla_policies.id", use_alter=True))
    default_duration_months: Mapped[int] = mapped_column(Integer, default=12)
    has_sla: Mapped[bool] = mapped_column(Boolean, default=True)
    ticket_catalog_visibility: Mapped[str] = mapped_column(String(30), default="CONTRACT_ONLY")
    require_product_on_ticket: Mapped[bool] = mapped_column(Boolean, default=True)
    require_module_on_ticket: Mapped[bool] = mapped_column(Boolean, default=False)
    require_service_on_ticket: Mapped[bool] = mapped_column(Boolean, default=False)
    coverage_validation_level: Mapped[str] = mapped_column(String(30), default="PRODUCT")
    expiry_grace_days: Mapped[int] = mapped_column(Integer, default=0)
    approval_group_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("approval_groups.id", use_alter=True)
    )
    support_summary: Mapped[str | None] = mapped_column(Text)
    exclusions: Mapped[str | None] = mapped_column(Text)
    included_request_limit: Mapped[int | None] = mapped_column(Integer)
    default_billing_frequency: Mapped[str | None] = mapped_column(String(20))
    default_payment_terms_days: Mapped[int | None] = mapped_column(Integer)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    updated_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    coverages: Mapped[list["ContractTemplateCoverage"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class ContractTemplateType(Base):
    __tablename__ = "contract_template_types"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    description: Mapped[str | None] = mapped_column(String(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ContractTemplateCoverage(Base):
    __tablename__ = "contract_template_coverages"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(IdType, ForeignKey("contract_templates.id", ondelete="CASCADE"))
    product_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("products.id"))
    product_module_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("product_modules.id"))
    environment_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("environments.id"))
    service_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("service_catalog_items.id"))
    ticket_type_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("ticket_types.id"))
    is_covered: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(String(1000))


class ContractClientLink(Base):
    __tablename__ = "contract_client_links"
    __table_args__ = (UniqueConstraint("contract_id", "client_id", name="uq_contract_client_link"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(IdType, ForeignKey("contracts.id", ondelete="CASCADE"))
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id", ondelete="CASCADE"))


class ContractCoverage(Base):
    __tablename__ = "contract_coverages"
    __table_args__ = (
        UniqueConstraint(
            "contract_id",
            "product_id",
            "product_module_id",
            "branch_id",
            "environment_id",
            "service_id",
            "ticket_type_id",
            name="uq_contract_coverage_context",
        ),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(IdType, ForeignKey("contracts.id", ondelete="CASCADE"))
    product_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("products.id"))
    product_module_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("product_modules.id"))
    branch_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("branches.id"))
    environment_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("environments.id"))
    service_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("service_catalog_items.id"))
    ticket_type_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("ticket_types.id"))
    is_covered: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(String(1000))
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_until: Mapped[date | None] = mapped_column(Date)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retired_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    retirement_reason: Mapped[str | None] = mapped_column(String(1000))
    current_revision: Mapped[int] = mapped_column(Integer, default=1)
    client_links: Mapped[list["ContractCoverageClient"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def client_ids(self) -> list[int]:
        return [link.client_id for link in self.client_links]

    @property
    def applies_to_all_clients(self) -> bool:
        return not self.client_links


class ContractCoverageClient(Base):
    __tablename__ = "contract_coverage_clients"
    __table_args__ = (
        UniqueConstraint("coverage_id", "client_id", name="uq_contract_coverage_client"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    coverage_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("contract_coverages.id", ondelete="CASCADE")
    )
    client_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("clients.id", ondelete="CASCADE")
    )


class ContractCoverageRevision(Base):
    __tablename__ = "contract_coverage_revisions"
    __table_args__ = (
        UniqueConstraint("coverage_id", "revision", name="uq_contract_coverage_revision"),
        Index("ix_contract_coverage_revision_dates", "coverage_id", "effective_from", "effective_until"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    coverage_id: Mapped[int] = mapped_column(IdType, ForeignKey("contract_coverages.id", ondelete="CASCADE"))
    revision: Mapped[int] = mapped_column(Integer)
    effective_from: Mapped[date] = mapped_column(Date)
    effective_until: Mapped[date | None] = mapped_column(Date)
    is_covered: Mapped[bool] = mapped_column(Boolean)
    notes: Mapped[str | None] = mapped_column(String(1000))
    client_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    change_reason: Mapped[str] = mapped_column(String(1000))
    created_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ContractRenewalOpportunity(Base):
    __tablename__ = "contract_renewal_opportunities"
    __table_args__ = (
        UniqueConstraint("source_contract_id", "idempotency_key", name="uq_contract_renewal_idempotency"),
        Index("ix_contract_renewal_stage_target", "stage", "target_close_date"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    source_contract_id: Mapped[int] = mapped_column(IdType, ForeignKey("contracts.id"))
    successor_contract_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contracts.id"))
    idempotency_key: Mapped[str] = mapped_column(String(200))
    stage: Mapped[str] = mapped_column(String(30), default="IDENTIFIED")
    outcome: Mapped[str | None] = mapped_column(String(30))
    owner_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    target_close_date: Mapped[date] = mapped_column(Date)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(String(1000))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ContractRenewalLine(Base):
    __tablename__ = "contract_renewal_lines"
    __table_args__ = (UniqueConstraint("opportunity_id", "coverage_id", name="uq_contract_renewal_line"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[int] = mapped_column(IdType, ForeignKey("contract_renewal_opportunities.id", ondelete="CASCADE"))
    coverage_id: Mapped[int] = mapped_column(IdType, ForeignKey("contract_coverages.id"))
    outcome: Mapped[str] = mapped_column(String(30), default="PENDING")
    successor_coverage_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contract_coverages.id"))
    reason: Mapped[str | None] = mapped_column(String(1000))


class ContractRenewalTask(Base):
    __tablename__ = "contract_renewal_tasks"
    __table_args__ = (Index("ix_contract_renewal_task_due", "status", "due_at"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[int] = mapped_column(IdType, ForeignKey("contract_renewal_opportunities.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(300))
    assigned_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ContractDocument(Base):
    __tablename__ = "contract_documents"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("contracts.id", ondelete="CASCADE")
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(100), unique=True)
    content_type: Mapped[str] = mapped_column(String(150))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    uploaded_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SlaPolicy(Base):
    __tablename__ = "sla_policies"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    contract_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contracts.id"))
    calendar_id: Mapped[int] = mapped_column(IdType, ForeignKey("business_calendars.id"))
    calculation_version: Mapped[str] = mapped_column(String(30), default="2.0")
    version: Mapped[int] = mapped_column(Integer, default=1)
    include_escalation_time: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SlaTarget(Base):
    __tablename__ = "sla_targets"
    __table_args__ = (UniqueConstraint("policy_id", "context_key", name="uq_sla_target_context"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    policy_id: Mapped[int] = mapped_column(IdType, ForeignKey("sla_policies.id", ondelete="CASCADE"))
    product_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("products.id"))
    product_module_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("product_modules.id"))
    service_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("service_catalog_items.id"))
    priority: Mapped[str] = mapped_column(String(5))
    context_key: Mapped[str] = mapped_column(String(120))
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)
    first_response_minutes: Mapped[int] = mapped_column(Integer)
    resolution_minutes: Mapped[int] = mapped_column(Integer)
    warning_percent: Mapped[int] = mapped_column(Integer, default=75)


class SlaPolicyVersion(Base):
    __tablename__ = "sla_policy_versions"
    __table_args__ = (UniqueConstraint("policy_id", "version", name="uq_sla_policy_version"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    policy_id: Mapped[int] = mapped_column(IdType, ForeignKey("sla_policies.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer)
    name_snapshot: Mapped[str] = mapped_column(String(200))
    calendar_id: Mapped[int] = mapped_column(IdType, ForeignKey("business_calendars.id"))
    calculation_version: Mapped[str] = mapped_column(String(30))
    include_escalation_time: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="PUBLISHED")
    created_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SlaTargetVersion(Base):
    __tablename__ = "sla_target_versions"
    __table_args__ = (UniqueConstraint("policy_version_id", "context_key", name="uq_sla_target_version_context"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    policy_version_id: Mapped[int] = mapped_column(IdType, ForeignKey("sla_policy_versions.id", ondelete="CASCADE"))
    source_target_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("sla_targets.id"))
    product_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("products.id"))
    product_module_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("product_modules.id"))
    service_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("service_catalog_items.id"))
    priority: Mapped[str] = mapped_column(String(5))
    context_key: Mapped[str] = mapped_column(String(120))
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_response_minutes: Mapped[int] = mapped_column(Integer)
    resolution_minutes: Mapped[int] = mapped_column(Integer)
    warning_percent: Mapped[int] = mapped_column(Integer, default=75)


def sla_target_context_key(target: SlaTarget) -> str:
    return (
        f"P{target.product_id or 0}:M{target.product_module_id or 0}:"
        f"S{target.service_id or 0}:PR{target.priority}"
    )


@event.listens_for(SlaTarget, "before_insert")
@event.listens_for(SlaTarget, "before_update")
def set_sla_target_context_key(_mapper: object, _connection: object, target: SlaTarget) -> None:
    target.context_key = sla_target_context_key(target)


class TicketSlaClock(Base):
    __tablename__ = "ticket_sla_clocks"
    __table_args__ = (UniqueConstraint("ticket_id", "clock_type"), Index("ix_sla_due_state", "state", "due_at"))
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    contract_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contracts.id"))
    policy_id: Mapped[int] = mapped_column(IdType, ForeignKey("sla_policies.id"))
    target_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("sla_targets.id"))
    calendar_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("business_calendars.id"))
    policy_version: Mapped[int] = mapped_column(Integer, default=1)
    policy_version_id: Mapped[int | None] = mapped_column(IdType)
    policy_code_snapshot: Mapped[str | None] = mapped_column(String(80))
    policy_name_snapshot: Mapped[str | None] = mapped_column(String(200))
    target_context_snapshot: Mapped[str | None] = mapped_column(String(120))
    match_reason: Mapped[str | None] = mapped_column(String(80))
    start_mode_snapshot: Mapped[str | None] = mapped_column(String(40))
    start_anchor_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    clock_type: Mapped[str] = mapped_column(String(30))
    target_minutes: Mapped[int] = mapped_column(Integer)
    warning_percent: Mapped[int] = mapped_column(Integer, default=75)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(30), default="RUNNING")
    breached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_response_minutes: Mapped[int | None] = mapped_column(Integer)
    accountable_minutes: Mapped[int | None] = mapped_column(Integer)
    customer_pending_minutes: Mapped[int | None] = mapped_column(Integer)
    millensys_pending_minutes: Mapped[int | None] = mapped_column(Integer)
    escalation_minutes: Mapped[int | None] = mapped_column(Integer)
    saved_minutes: Mapped[int | None] = mapped_column(Integer)
    overrun_minutes: Mapped[int | None] = mapped_column(Integer)
    outcome_calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    calculation_version: Mapped[str] = mapped_column(String(30))


class SlaShadowComparison(Base):
    __tablename__ = "sla_shadow_comparisons"
    __table_args__ = (UniqueConstraint("ticket_id", name="uq_sla_shadow_ticket"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    contract_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contracts.id"))
    policy_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("sla_policies.id"))
    legacy_target_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("sla_targets.id"))
    governed_target_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("sla_targets.id"))
    legacy_response_minutes: Mapped[int | None] = mapped_column(Integer)
    legacy_resolution_minutes: Mapped[int | None] = mapped_column(Integer)
    governed_response_minutes: Mapped[int | None] = mapped_column(Integer)
    governed_resolution_minutes: Mapped[int | None] = mapped_column(Integer)
    governed_match_reason: Mapped[str] = mapped_column(String(80))
    outcome: Mapped[str] = mapped_column(String(30))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TicketSlaInterval(Base):
    """Auditable lifecycle interval used by accountable SLA calculations."""
    __tablename__ = "ticket_sla_intervals"
    __table_args__ = (Index("ix_ticket_sla_intervals_ticket_started", "ticket_id", "started_at"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    interval_type: Mapped[str] = mapped_column(String(30))
    responsible_party: Mapped[str | None] = mapped_column(String(20))
    comment: Mapped[str | None] = mapped_column(String(1000))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
