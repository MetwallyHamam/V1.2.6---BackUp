from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.clients.schemas import ClientCreate


class ContractCreate(BaseModel):
    contract_number: str = Field(min_length=2, max_length=80)
    # Legacy callers may still supply a single client; new callers use linked_client_ids.
    client_id: int | None = None
    contract_type_id: int | None = None
    name: str = Field(min_length=2, max_length=200)
    status: str = Field(default="ACTIVE", pattern="^(DRAFT|ACTIVE|SUSPENDED|EXPIRED|TERMINATED)$")
    start_date: date
    end_date: date
    acceptance_date: date | None = None
    renewal_notice_date: date | None = None
    timezone: str = "Africa/Cairo"
    calendar_id: int
    support_summary: str | None = Field(default=None, max_length=4000)
    exclusions: str | None = Field(default=None, max_length=10000)
    included_request_limit: int | None = Field(default=None, ge=1)
    escalation_contact_id: int | None = None
    linked_client_ids: list[int] = Field(default_factory=list)
    is_shared_default: bool = False
    applies_to_all_clients: bool = False
    is_active: bool = True
    has_sla: bool | None = None
    ticket_catalog_visibility: str = Field(default="CONTRACT_ONLY", pattern="^(CONTRACT_ONLY|ALL_WITH_COVERAGE_STATUS)$")
    require_product_on_ticket: bool = True
    require_module_on_ticket: bool = False
    require_service_on_ticket: bool = False
    coverage_validation_level: str = Field(
        default="PRODUCT", pattern="^(CONTRACT|PRODUCT|PRODUCT_MODULE|FULL)$"
    )
    expiry_grace_days: int = Field(default=0, ge=0, le=3650)
    approval_group_id: int | None = None

    @model_validator(mode="after")
    def dates_are_valid(self) -> "ContractCreate":
        if self.end_date <= self.start_date:
            raise ValueError("Contract end date must be after start date.")
        return self


class ContractRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    contract_number: str
    client_id: int
    contract_type_id: int | None
    name: str
    status: str
    start_date: date
    end_date: date
    acceptance_date: date | None
    source_template_id: int | None
    source_template_version: int | None
    renewal_notice_date: date | None
    timezone: str
    calendar_id: int
    sla_policy_id: int | None
    has_sla: bool
    ticket_catalog_visibility: str
    require_product_on_ticket: bool
    require_module_on_ticket: bool
    require_service_on_ticket: bool
    coverage_validation_level: str
    expiry_grace_days: int
    approval_group_id: int | None
    support_summary: str | None
    exclusions: str | None
    included_request_limit: int | None
    escalation_contact_id: int | None
    linked_client_ids: list[int]
    is_shared_default: bool
    applies_to_all_clients: bool
    is_active: bool


class ContractUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    contract_type_id: int | None = None
    status: str | None = Field(default=None, pattern="^(DRAFT|ACTIVE|SUSPENDED|EXPIRED|TERMINATED)$")
    start_date: date | None = None
    end_date: date | None = None
    acceptance_date: date | None = None
    renewal_notice_date: date | None = None
    timezone: str | None = Field(default=None, max_length=100)
    calendar_id: int | None = None
    sla_policy_id: int | None = None
    has_sla: bool | None = None
    ticket_catalog_visibility: str | None = Field(default=None, pattern="^(CONTRACT_ONLY|ALL_WITH_COVERAGE_STATUS)$")
    require_product_on_ticket: bool | None = None
    require_module_on_ticket: bool | None = None
    require_service_on_ticket: bool | None = None
    coverage_validation_level: str | None = Field(
        default=None, pattern="^(CONTRACT|PRODUCT|PRODUCT_MODULE|FULL)$"
    )
    expiry_grace_days: int | None = Field(default=None, ge=0, le=3650)
    approval_group_id: int | None = None
    support_summary: str | None = Field(default=None, max_length=4000)
    exclusions: str | None = Field(default=None, max_length=10000)
    included_request_limit: int | None = Field(default=None, ge=1)
    escalation_contact_id: int | None = None
    linked_client_ids: list[int] | None = None
    is_shared_default: bool | None = None
    applies_to_all_clients: bool | None = None
    is_active: bool | None = None


class ContractLifecycleTransition(BaseModel):
    action: str = Field(
        pattern="^(START_RENEWAL|MARK_RENEWED|MARK_NOT_RENEWED|REACTIVATE|EXTEND)$"
    )
    owner_user_id: int | None = None
    target_close_date: date | None = None
    successor_contract_id: int | None = None
    new_end_date: date | None = None
    reason: str = Field(min_length=5, max_length=1000)
    version: int | None = Field(default=None, ge=1)
    lines: list["RenewalLineWrite"] = Field(default_factory=list)


class ContractTemplateCoverageWrite(BaseModel):
    product_id: int | None = None
    product_module_id: int | None = None
    environment_id: int | None = None
    service_id: int | None = None
    ticket_type_id: int | None = None
    is_covered: bool = True
    notes: str | None = Field(default=None, max_length=1000)


class ContractTemplateWrite(BaseModel):
    code: str | None = Field(default=None, pattern="^[A-Z0-9_-]+$", min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    template_type: str = Field(default="GLOBAL", max_length=50)
    contract_type_id: int | None = None
    calendar_id: int
    sla_policy_id: int | None = None
    default_duration_months: int = Field(default=12, ge=1, le=120)
    has_sla: bool = True
    ticket_catalog_visibility: str = Field(default="CONTRACT_ONLY", pattern="^(CONTRACT_ONLY|ALL_WITH_COVERAGE_STATUS)$")
    require_product_on_ticket: bool = True
    require_module_on_ticket: bool = False
    require_service_on_ticket: bool = False
    coverage_validation_level: str = Field(
        default="PRODUCT", pattern="^(CONTRACT|PRODUCT|PRODUCT_MODULE|FULL)$"
    )
    expiry_grace_days: int = Field(default=0, ge=0, le=3650)
    approval_group_id: int | None = None
    support_summary: str | None = Field(default=None, max_length=4000)
    exclusions: str | None = Field(default=None, max_length=10000)
    included_request_limit: int | None = Field(default=None, ge=1)
    default_billing_frequency: str | None = Field(default=None, max_length=20)
    default_payment_terms_days: int | None = Field(default=None, ge=0, le=3650)
    is_default: bool = False
    is_active: bool = True
    coverages: list[ContractTemplateCoverageWrite] = Field(default_factory=list)


class ContractTemplateRead(ContractTemplateWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    version: int


class ContractTemplateTypeWrite(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool = True


class ContractTemplateTypeRead(ContractTemplateTypeWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str


class ContractFromTemplateWrite(BaseModel):
    template_id: int
    expected_template_version: int
    acceptance_date: date
    start_date: date | None = None
    duration_months: int | None = Field(default=None, ge=1, le=120)
    name: str | None = Field(default=None, min_length=2, max_length=200)
    contract_number: str | None = Field(default=None, min_length=2, max_length=80)
    change_overrides: dict[str, object] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=8, max_length=200)


class ContractTemplateApplyWrite(BaseModel):
    template_id: int
    expected_template_version: int
    sections: list[str] = Field(min_length=1)
    reason: str = Field(min_length=5, max_length=1000)


class ContractTemplatePreview(BaseModel):
    template_id: int
    template_version: int
    name: str
    start_date: date
    end_date: date
    duration_months: int
    contract_type_id: int | None
    calendar_id: int
    sla_policy_id: int | None
    has_sla: bool
    coverage_validation_level: str
    expiry_grace_days: int
    approval_group_id: int | None
    support_summary: str | None
    exclusions: str | None
    included_request_limit: int | None
    coverages: list[ContractTemplateCoverageWrite]


class OptionalOnboardingContact(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone_number: str | None = Field(default=None, max_length=50)
    job_title: str | None = Field(default=None, max_length=150)
    contact_role: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def communication_method_required(self) -> "OptionalOnboardingContact":
        if not self.email and not self.phone_number:
            raise ValueError("An optional contact requires an email or phone number.")
        return self


class ClientOnboardingWrite(BaseModel):
    client: ClientCreate
    contact: OptionalOnboardingContact | None = None
    contract: ContractFromTemplateWrite | None = None
    source: str = Field(default="CLIENT_SETUP", pattern="^(CLIENT_SETUP|DELIVERY_PROJECT)$")


class ClientOnboardingRead(BaseModel):
    client_id: int
    client_code: str
    contact_id: int | None
    contact_code: str | None
    contract_id: int | None
    contract_number: str | None


class ContractClientSelection(BaseModel):
    mode: str = Field(pattern="^(EXPLICIT|ALL_MATCHING)$")
    search: str | None = Field(default=None, max_length=100)
    explicit_ids: list[int] = Field(default_factory=list)
    excluded_ids: list[int] = Field(default_factory=list)


class ContractClientSelectionPreview(BaseModel):
    mode: str
    matched_count: int
    selected_count: int
    excluded_count: int
    primary_forced: bool
    inactive_count: int


class ContractTypeWrite(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=50, pattern="^[A-Z0-9_-]+$")
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    precedence: int = Field(default=100, ge=1, le=9999)
    default_has_sla: bool = True
    default_duration_days: int | None = Field(default=None, ge=1, le=36500)
    expiry_behavior: str = Field(default="EXPIRE", pattern="^(EXPIRE|RENEW|CONTINUE_WITH_APPROVAL)$")
    approval_behavior: str = Field(default="INHERIT", pattern="^(INHERIT|ALLOW|WARN|REQUIRE_APPROVAL|BLOCK)$")
    is_active: bool = True


class ContractTypeRead(ContractTypeWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_system: bool
    created_at: datetime
    updated_at: datetime
    linked_client_count: int = 0


class ContractTypeClientItem(BaseModel):
    id: int
    code: str
    name: str
    is_active: bool


class ContractTypeClientPage(BaseModel):
    items: list[ContractTypeClientItem]
    total: int
    limit: int
    offset: int


class ContractTypeDefaultsPreview(BaseModel):
    contract_type_id: int
    code: str
    feature_mode: str
    source_scope: str
    default_has_sla: bool
    default_duration_days: int | None
    expiry_behavior: str
    approval_behavior: str
    type_required: bool


class ContractCoverageCreate(BaseModel):
    product_id: int | None = None
    product_module_id: int | None = None
    branch_id: int | None = None
    environment_id: int | None = None
    service_id: int | None = None
    ticket_type_id: int | None = None
    is_covered: bool = True
    notes: str | None = Field(default=None, max_length=1000)
    applies_to_all_clients: bool = True
    client_ids: list[int] = Field(default_factory=list)
    effective_from: date | None = None
    effective_until: date | None = None

    @model_validator(mode="after")
    def effective_dates_are_valid(self) -> "ContractCoverageCreate":
        if self.effective_from and self.effective_until and self.effective_until < self.effective_from:
            raise ValueError("Coverage effective-until cannot precede effective-from.")
        return self


class ContractCoverageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    contract_id: int
    product_id: int | None
    product_module_id: int | None
    branch_id: int | None
    environment_id: int | None
    service_id: int | None
    ticket_type_id: int | None
    is_covered: bool
    notes: str | None
    applies_to_all_clients: bool
    client_ids: list[int]
    effective_from: date | None
    effective_until: date | None
    retired_at: datetime | None
    retirement_reason: str | None
    current_revision: int


class ContractCoverageAmend(BaseModel):
    effective_from: date
    effective_until: date | None = None
    is_covered: bool
    notes: str | None = Field(default=None, max_length=1000)
    applies_to_all_clients: bool = True
    client_ids: list[int] = Field(default_factory=list)
    reason: str = Field(min_length=5, max_length=1000)
    expected_revision: int = Field(ge=1)


class ContractCoverageRevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    coverage_id: int
    revision: int
    effective_from: date
    effective_until: date | None
    is_covered: bool
    notes: str | None
    client_ids_json: str
    change_reason: str
    created_by_user_id: int | None
    created_at: datetime


class RenewalLineWrite(BaseModel):
    coverage_id: int
    outcome: str = Field(pattern="^(PENDING|RENEWED|LOST|CHANGED|EXCLUDED)$")
    successor_coverage_id: int | None = None
    reason: str | None = Field(default=None, max_length=1000)


class RenewalOpportunityCreate(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=200)
    owner_user_id: int
    target_close_date: date
    reason: str = Field(min_length=5, max_length=1000)
    lines: list[RenewalLineWrite] = Field(default_factory=list)


class RenewalOpportunityUpdate(BaseModel):
    stage: str = Field(pattern="^(IDENTIFIED|QUALIFYING|PROPOSAL|NEGOTIATION|CLOSED)$")
    outcome: str | None = Field(default=None, pattern="^(RENEWED|PARTIAL|LOST|CANCELLED)$")
    successor_contract_id: int | None = None
    reason: str = Field(min_length=5, max_length=1000)
    version: int = Field(ge=1)
    lines: list[RenewalLineWrite] = Field(default_factory=list)
    owner_user_id: int | None = None
    target_close_date: date | None = None


class RenewalLineRead(RenewalLineWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int


class RenewalOpportunityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_contract_id: int
    successor_contract_id: int | None
    idempotency_key: str
    stage: str
    outcome: str | None
    owner_user_id: int
    target_close_date: date
    closed_at: datetime | None
    reason: str
    version: int
    created_at: datetime
    updated_at: datetime
    lines: list[RenewalLineRead]


class ContractProductAssignment(BaseModel):
    product_id: int
    module_ids: list[int] = Field(default_factory=list)


class ContractBulkAssignmentCreate(BaseModel):
    products: list[ContractProductAssignment] = Field(default_factory=list)
    service_ids: list[int] = Field(default_factory=list)
    applies_to_all_clients: bool = True
    client_ids: list[int] = Field(default_factory=list)


class EntitlementCheckRead(BaseModel):
    status: str
    contract_id: int | None
    contract_number: str | None
    reason: str


class EntitlementCandidateRead(BaseModel):
    contract_id: int
    contract_number: str
    contract_name: str
    contract_type: str | None
    precedence: int
    start_date: date
    end_date: date
    status: str
    reason: str


class ContractUsageRead(BaseModel):
    included_request_limit: int | None
    used_requests: int
    remaining_requests: int | None
    overridden_requests: int
    total_primary_requests: int


class ContractDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    contract_id: int
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_by_user_id: int
    created_at: datetime


class CalendarRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    timezone: str


class SlaClockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    contract_id: int | None
    policy_id: int
    target_id: int | None
    calendar_id: int | None
    policy_version: int
    calculation_version: str
    match_reason: str | None
    start_mode_snapshot: str | None
    start_anchor_at: datetime | None
    clock_type: str
    target_minutes: int
    warning_percent: int
    started_at: datetime
    due_at: datetime
    state: str
    breached_at: datetime | None
    completed_at: datetime | None


class SlaShadowComparisonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ticket_id: int
    contract_id: int | None
    policy_id: int | None
    legacy_target_id: int | None
    governed_target_id: int | None
    legacy_response_minutes: int | None
    legacy_resolution_minutes: int | None
    governed_response_minutes: int | None
    governed_resolution_minutes: int | None
    governed_match_reason: str
    outcome: str
    evaluated_at: datetime


class SlaTargetWrite(BaseModel):
    product_id: int | None = None
    product_module_id: int | None = None
    service_id: int | None = None
    priority: str = Field(pattern="^P[1-4]$")
    first_response_minutes: int = Field(ge=1, le=525600)
    resolution_minutes: int = Field(ge=1, le=525600)
    warning_percent: int = Field(default=75, ge=1, le=99)
    is_fallback: bool = False
    effective_from: datetime | None = None
    effective_until: datetime | None = None

    @model_validator(mode="after")
    def resolution_cannot_precede_response(self) -> "SlaTargetWrite":
        if self.resolution_minutes < self.first_response_minutes:
            raise ValueError("Resolution duration must be greater than or equal to response duration.")
        if self.product_module_id is not None and self.product_id is None:
            raise ValueError("A module-scoped SLA target requires a product.")
        if self.effective_from and self.effective_until and self.effective_until <= self.effective_from:
            raise ValueError("SLA target effective-until must be after effective-from.")
        if self.product_id is None and self.service_id is None:
            self.is_fallback = True
        return self


class SlaTargetBulkWrite(BaseModel):
    coverage_ids: list[int] = Field(min_length=1, max_length=500)
    priorities: list[str] = Field(min_length=1, max_length=4)
    first_response_minutes: int = Field(ge=1, le=525600)
    resolution_minutes: int = Field(ge=1, le=525600)
    warning_percent: int = Field(default=75, ge=1, le=99)
    effective_from: datetime | None = None
    effective_until: datetime | None = None

    @model_validator(mode="after")
    def valid_commitments(self) -> "SlaTargetBulkWrite":
        self.priorities = list(dict.fromkeys(self.priorities))
        if any(value not in {"P1", "P2", "P3", "P4"} for value in self.priorities):
            raise ValueError("Priorities must be P1, P2, P3, or P4.")
        if self.resolution_minutes < self.first_response_minutes:
            raise ValueError("Resolution duration must be greater than or equal to response duration.")
        if self.effective_from and self.effective_until and self.effective_until <= self.effective_from:
            raise ValueError("SLA target effective-until must be after effective-from.")
        return self


class SlaTargetRead(SlaTargetWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    policy_id: int
    context_key: str
    version: int


class ContractSlaRead(BaseModel):
    id: int
    code: str
    name: str
    contract_id: int | None
    calendar_id: int
    is_active: bool
    include_escalation_time: bool
    targets: list[SlaTargetRead]


class ContractSlaWrite(BaseModel):
    policy_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=200)
    code: str | None = Field(default=None, min_length=2, max_length=80, pattern="^[A-Z0-9_-]+$")
    calendar_id: int | None = None
    is_active: bool = True


class ContractCoverageRetireBatch(BaseModel):
    coverage_ids: list[int] = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=5, max_length=1000)


class SlaPolicyRead(BaseModel):
    id: int
    code: str
    name: str
    calendar_id: int
    is_active: bool
    include_escalation_time: bool
    targets: list[SlaTargetRead]


class SlaPolicyWrite(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=80, pattern="^[A-Z0-9_-]+$")
    name: str = Field(min_length=2, max_length=200)
    calendar_id: int
    is_active: bool = True
    include_escalation_time: bool = True


class SlaPresetWrite(BaseModel):
    name: str = Field(default="Standard Support SLA — L1 to L4", min_length=2, max_length=200)
    code: str | None = Field(default=None, min_length=2, max_length=80, pattern="^[A-Z0-9_-]+$")
    calendar_id: int
    is_active: bool = True
    include_escalation_time: bool = True


class SlaPolicyVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    policy_id: int
    version: int
    name_snapshot: str
    calendar_id: int
    calculation_version: str
    include_escalation_time: bool
    effective_from: datetime
    effective_until: datetime | None
    status: str
    published_at: datetime | None


class CalendarDayWrite(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    is_working_day: bool = True


class CalendarDayRead(CalendarDayWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int


class CalendarScheduleRead(BaseModel):
    id: int
    code: str
    name: str
    timezone: str
    days: list[CalendarDayRead]


class CalendarScheduleWrite(BaseModel):
    timezone: str = Field(min_length=2, max_length=100)
    days: list[CalendarDayWrite]

    @model_validator(mode="after")
    def unique_weekdays(self) -> "CalendarScheduleWrite":
        if len({item.weekday for item in self.days}) != len(self.days):
            raise ValueError("Each weekday can appear only once.")
        return self
