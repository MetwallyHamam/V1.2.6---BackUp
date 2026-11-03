from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TicketFilterRule(BaseModel):
    field: Literal[
        "ticket_number",
        "subject",
        "status_code",
        "priority",
        "client_id",
        "branch_id",
        "assigned_user_id",
        "assigned_team",
        "ticket_type_id",
        "product_id",
        "product_module_id",
        "environment_id",
        "service_id",
        "category_id",
        "subcategory_id",
        "entitlement_status",
        "created_at",
        "updated_at",
        "resolved_at",
    ]
    operator: Literal["eq", "ne", "in", "contains", "gte", "lte", "is_null"]
    value: str | int | list[str | int] | bool | None = None


class TicketFilterGroup(BaseModel):
    logic: Literal["AND", "OR"] = "AND"
    rules: list[TicketFilterRule | TicketFilterGroup] = Field(min_length=1, max_length=20)


class TicketAdvancedSearch(BaseModel):
    filter: TicketFilterGroup
    sort_by: Literal[
        "updated_at", "created_at", "resolved_at", "priority", "ticket_number"
    ] = "updated_at"
    sort_direction: Literal["asc", "desc"] = "desc"
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class TicketCreate(BaseModel):
    ticket_type_id: int
    client_id: int
    contract_id: int | None = None
    branch_id: int | None = None
    requester_contact_id: int | None = None
    assigned_user_id: int | None = None
    assigned_team: str | None = Field(default=None, max_length=150)
    product_id: int | None = None
    product_module_id: int | None = None
    environment_id: int | None = None
    service_id: int | None = None
    category_id: int | None = None
    subcategory_id: int | None = None
    source_channel: str = Field(default="WEB", max_length=30)
    category: str | None = Field(default=None, max_length=150)
    subcategory: str | None = Field(default=None, max_length=150)
    impact: str
    urgency: str
    priority: str | None = Field(default=None, pattern="^P[1-4]$")
    subject: str = Field(min_length=5, max_length=300)
    description: str = Field(min_length=10, max_length=20000)
    affected_users: str | None = Field(default=None, max_length=500)
    first_occurred_at: datetime | None = None
    patient_safety_flag: bool = False
    security_incident_flag: bool = False
    inactive_client_confirmed: bool = False
    entitlement_override_reason: str | None = Field(default=None, max_length=500)
    request_entitlement_approval: bool = False
    entitlement_approval_justification: str | None = Field(default=None, max_length=1000)
    submission_idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)
    creation_idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)
    follower_user_ids: list[int] = Field(default_factory=list)


class PortalChangeRequestCreate(BaseModel):
    request_kind: Literal["NEW_FEATURE", "UPDATE_EXISTING_FEATURE"]
    purpose: str = Field(min_length=3, max_length=20000)
    detailed_description: str = Field(min_length=5, max_length=30000)
    business_impact: str = Field(min_length=3, max_length=20000)
    expected_result: str = Field(min_length=3, max_length=20000)
    required_permissions: str | None = Field(default=None, max_length=10000)
    requested_priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"


class PortalTicketCreate(TicketCreate):
    priority: Literal["P1", "P2", "P3", "P4"]
    creation_method: Literal["PORTAL", "MOSAIC"] = "PORTAL"
    change_request: PortalChangeRequestCreate | None = None


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_number: str
    created_by_user_id: int
    created_by_name: str | None = None
    department_id: int | None = None
    department_name: str | None = None
    parent_department_id: int | None = None
    parent_department_name: str | None = None
    ticket_type_id: int
    client_id: int
    client_name: str | None = None
    branch_id: int | None
    requester_contact_id: int | None
    requester_name: str | None = None
    requester_phone_number: str | None = None
    requester_email: str | None = None
    requester_job_title: str | None = None
    active_flags: list[dict[str, object]] = Field(default_factory=list)
    status_id: int
    contract_id: int | None
    entitlement_status: str | None
    entitlement_override_reason: str | None
    assigned_user_id: int | None
    assigned_user_name: str | None = None
    assigned_team: str | None
    is_shared_assignment: bool = False
    routed_department_id: int | None
    routed_team_id: int | None
    routing_status: str | None
    help_request_result: str | None
    returned_at: datetime | None
    returned_by_user_id: int | None
    escalation_assignee_user_id: int | None
    escalation_level: str | None
    escalation_reason: str | None
    escalated_at: datetime | None
    escalation_parent_ticket_id: int | None
    product_id: int | None
    product_module_id: int | None
    environment_id: int | None
    service_id: int | None
    resolution_service_ids: list[int] = Field(default_factory=list)
    category_id: int | None
    subcategory_id: int | None
    source_channel: str
    category: str | None
    affected_users: str | None
    first_occurred_at: datetime | None
    impact: str
    urgency: str
    priority: str
    subject: str
    description: str
    patient_safety_flag: bool
    security_incident_flag: bool
    support_follow_up_flag: bool
    resolution_summary: str | None
    root_cause_summary: str | None
    root_cause_ids: list[int] = Field(default_factory=list)
    resolution_outcome_id: int | None
    permanent_fix_summary: str | None
    permanent_fix_status: str | None
    root_causes: list[str] = Field(default_factory=list)
    resolved_at: datetime | None
    closed_at: datetime | None
    cancelled_at: datetime | None
    reopened_at: datetime | None
    archived_at: datetime | None
    archived_by_user_id: int | None
    archive_reason: str | None
    progress_started_at: datetime | None
    due_at: datetime | None
    pending_reason: str | None
    pending_owner_user_id: int | None
    pending_follow_up_at: datetime | None
    shift_handover_status: str | None
    shift_handover_reason: str | None
    shift_handover_by_user_id: int | None
    shift_handover_to_user_id: int | None
    shift_handover_at: datetime | None
    shift_handover_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int
    sla_first_response_target_minutes: int | None = None
    sla_first_response_actual_minutes: int | None = None
    sla_resolution_target_minutes: int | None = None
    sla_actual_business_minutes: int | None = None
    sla_saved_minutes: int | None = None
    sla_overrun_minutes: int | None = None
    sla_resolution_state: str | None = None
    sla_match_reason: str | None = None
    sla_target_id: int | None = None
    sla_policy_version: int | None = None
    sla_calendar_id: int | None = None


class SupportAssistantTabFilters(BaseModel):
    search: str = Field(default="", max_length=100)
    priority: Literal["", "P1", "P2", "P3", "P4"] = ""
    status_code: str = Field(default="", max_length=300)


class SupportAssistantWorkspaceState(BaseModel):
    compact: bool = False
    width: int = Field(default=760, ge=360, le=1200)
    page_size: int = Field(default=12, ge=6, le=50)
    hidden_card_fields: list[Literal["client", "priority", "status", "updated", "created", "sla"]] = Field(default_factory=list)
    tab_sorting: dict[str, str] = Field(default_factory=dict)
    tab_filters: dict[str, SupportAssistantTabFilters] = Field(default_factory=dict)
    density: Literal["comfortable", "compact", "dense"] = "comfortable"
    layout: Literal["cards", "list"] = "cards"


class SupportAssistantCustomTab(BaseModel):
    id: str = Field(min_length=1, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = Field(min_length=2, max_length=30)
    source_module: Literal[
        "queue", "mine", "resolved", "backlog", "follow-up", "sla-risk", "missing-resolution"
    ]
    filters: SupportAssistantTabFilters = Field(default_factory=SupportAssistantTabFilters)
    sorting: str = Field(default="updated_at:desc", max_length=40)


class SupportAssistantPreferenceRead(BaseModel):
    pinned_ticket_ids: list[int] = Field(default_factory=list)
    default_tab: str = Field(default="queue", max_length=57, pattern=r"^(queue|mine|resolved|backlog|follow-up|sla-risk|missing-resolution|pre-tickets|custom:[a-zA-Z0-9_-]+)$")
    workspace_state: SupportAssistantWorkspaceState = Field(default_factory=lambda: SupportAssistantWorkspaceState())
    custom_tabs: list[SupportAssistantCustomTab] = Field(default_factory=list)


class SupportAssistantPreferenceUpdate(BaseModel):
    pinned_ticket_ids: list[int] = Field(default_factory=list, max_length=100)
    default_tab: str = Field(default="queue", max_length=57, pattern=r"^(queue|mine|resolved|backlog|follow-up|sla-risk|missing-resolution|pre-tickets|custom:[a-zA-Z0-9_-]+)$")
    workspace_state: SupportAssistantWorkspaceState = Field(default_factory=lambda: SupportAssistantWorkspaceState())
    custom_tabs: list[SupportAssistantCustomTab] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_personal_default(self) -> SupportAssistantPreferenceUpdate:
        if self.default_tab.startswith("custom:"):
            tab_id = self.default_tab.removeprefix("custom:")
            if not any(tab.id == tab_id for tab in self.custom_tabs):
                raise ValueError("The default personal tab must exist in custom_tabs.")
        return self


class PersonalWorkspaceItem(BaseModel):
    id: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9:_-]+$")
    label: str = Field(min_length=1, max_length=120)
    path: str = Field(min_length=1, max_length=1000, pattern=r"^/(?:[^/].*)?$")
    item_type: Literal["page", "ticket", "client", "saved_view", "support_tab", "record"] = "page"
    visited_at: datetime | None = None


class PersonalWorkspaceRead(BaseModel):
    favorites: list[PersonalWorkspaceItem] = Field(default_factory=list)
    recent: list[PersonalWorkspaceItem] = Field(default_factory=list)
    hidden_widgets: list[Literal["support", "shifts", "visits", "operations", "approvals"]] = Field(default_factory=list)


class PersonalWorkspaceUpdate(BaseModel):
    favorites: list[PersonalWorkspaceItem] = Field(default_factory=list, max_length=50)
    hidden_widgets: list[Literal["support", "shifts", "visits", "operations", "approvals"]] = Field(default_factory=list)


class PersonalWorkspaceRecentCreate(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    path: str = Field(min_length=1, max_length=1000, pattern=r"^/(?:[^/].*)?$")
    item_type: Literal["page", "ticket", "client", "saved_view", "support_tab", "record"] = "page"


class SupportFollowUpUpdate(BaseModel):
    marked: bool
    version: int


class TicketEdit(BaseModel):
    client_id: int | None = None
    branch_id: int | None = None
    requester_contact_id: int | None = None
    contract_id: int | None = None
    due_at: datetime | None = None
    subject: str | None = Field(default=None, min_length=5, max_length=300)
    description: str | None = Field(default=None, min_length=10, max_length=10000)
    priority: Literal["P1", "P2", "P3", "P4"] | None = None
    impact: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None
    urgency: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None
    ticket_type_id: int | None = None
    product_id: int | None = None
    product_module_id: int | None = None
    environment_id: int | None = None
    service_id: int | None = None
    category_id: int | None = None
    subcategory_id: int | None = None
    affected_users: str | None = Field(default=None, max_length=500)
    patient_safety_flag: bool | None = None
    security_incident_flag: bool | None = None
    sla_reevaluation_reason: str | None = Field(default=None, min_length=5, max_length=500)
    reason: str = Field(min_length=5, max_length=500)
    version: int


class TicketSlaPreviewRequest(BaseModel):
    client_id: int | None = None
    contract_id: int | None = None
    priority: Literal["P1", "P2", "P3", "P4"] | None = None
    ticket_type_id: int | None = None
    product_id: int | None = None
    product_module_id: int | None = None
    environment_id: int | None = None
    service_id: int | None = None
    version: int


class TicketSlaPreviewRead(BaseModel):
    version: int
    changes_sla: bool
    changed_fields: list[str]
    effective_at: datetime
    old_contract_id: int | None = None
    old_policy_id: int | None = None
    old_target_id: int | None = None
    old_first_response_minutes: int | None = None
    old_resolution_minutes: int | None = None
    new_contract_id: int | None = None
    new_policy_id: int | None = None
    new_target_id: int | None = None
    new_first_response_minutes: int | None = None
    new_resolution_minutes: int | None = None
    match_reason: str | None = None


class TicketCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    is_internal: bool = False
    operation_key: str | None = Field(default=None, min_length=8, max_length=200)


class TicketMentionCreate(BaseModel):
    recipient_user_ids: list[int] = Field(min_length=1, max_length=50)
    message: str = Field(min_length=1, max_length=2000)
    is_internal: bool = False
    add_as_followers: bool = False
    operation_key: str | None = Field(default=None, min_length=8, max_length=200)


class TicketMentionCandidateRead(BaseModel):
    id: int
    full_name: str
    email: str
    user_type: str


class TicketTemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    keywords: str = Field(default="", max_length=1000)
    scope: Literal["GLOBAL", "CLIENT", "PRODUCT", "MODULE"] = "GLOBAL"
    portal_visible: bool = False


class TicketTemplateUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    keywords: str = Field(default="", max_length=1000)
    subject: str = Field(min_length=5, max_length=300)
    description: str = Field(min_length=10, max_length=10000)
    ticket_type_id: int
    client_id: int | None = None
    product_id: int | None = None
    product_module_id: int | None = None
    environment_id: int | None = None
    service_id: int | None = None
    category_id: int | None = None
    subcategory_id: int | None = None
    priority: Literal["P1", "P2", "P3", "P4"]
    impact: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    urgency: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assigned_team: str | None = Field(default=None, max_length=150)
    portal_visible: bool = False
    is_active: bool = True
    expected_version: int = Field(ge=1)


class TicketTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    keywords: str
    source_ticket_id: int | None
    ticket_type_id: int
    client_id: int | None
    product_id: int | None
    product_module_id: int | None
    environment_id: int | None
    service_id: int | None
    category_id: int | None
    subcategory_id: int | None
    subject: str
    description: str
    priority: str
    impact: str
    urgency: str
    assigned_team: str | None
    portal_visible: bool
    is_active: bool
    version: int


class TicketCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author_user_id: int
    is_internal: bool
    body: str
    created_at: datetime


class TicketMentionResult(BaseModel):
    comment: TicketCommentRead
    notified_user_ids: list[int]
    followers_added: list[int]


class TicketResolutionHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ticket_id: int
    resolution_sequence: int
    resolution_summary: str | None
    root_cause_summary: str | None
    resolution_outcome_id: int | None
    permanent_fix_summary: str | None
    permanent_fix_status: str | None
    resolved_at: datetime
    closed_at: datetime | None
    reopen_reason: str
    archived_at: datetime


class TicketTransition(BaseModel):
    to_status_code: str
    service_id: int | None = None
    resolution_service_ids: list[int] = Field(default_factory=list, max_length=50)
    reason: str | None = Field(default=None, max_length=500)
    resolution_summary: str | None = Field(default=None, min_length=5, max_length=10000)
    root_cause_summary: str | None = Field(default=None, min_length=5, max_length=10000)
    root_cause_ids: list[int] = Field(default_factory=list, max_length=20)
    resolution_outcome_id: int | None = None
    permanent_fix_summary: str | None = Field(default=None, min_length=5, max_length=10000)
    permanent_fix_status: Literal["NOT_REQUIRED", "PLANNED", "IMPLEMENTED", "VERIFIED"] | None = (
        None
    )
    version: int
    close_after_resolve: bool = False
    create_knowledge_article: bool = False
    readiness_override_reason: str | None = Field(default=None, min_length=5, max_length=500)
    customer_confirmation_channel: (
        Literal["PHONE", "EMAIL", "PORTAL", "MEETING", "OTHER"] | None
    ) = None
    customer_confirmation_contact: str | None = Field(default=None, min_length=2, max_length=300)
    customer_confirmation_note: str | None = Field(default=None, max_length=10000)
    pending_owner_user_id: int | None = None
    pending_follow_up_at: datetime | None = None
    pending_responsible_party: Literal["CUSTOMER", "MILLENSYS"] | None = None

    @model_validator(mode="after")
    def pending_requires_party_and_comment(self) -> TicketTransition:
        if self.to_status_code.startswith("PENDING_"):
            if not self.reason or len(self.reason.strip()) < 3:
                raise ValueError("A pending comment is required.")
        return self


class TicketAssignment(BaseModel):
    assigned_user_id: int | None = None
    assigned_team: str | None = Field(default=None, max_length=150)
    reason: str | None = Field(default=None, max_length=500)
    version: int


class TicketShiftHandoverCreate(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)
    to_user_id: int | None = None
    follow_up_at: datetime
    reassign: bool = True
    version: int


class TicketShiftHandoverComplete(BaseModel):
    note: str = Field(default="Shift handover accepted", min_length=3, max_length=500)
    version: int


class TicketEscalation(BaseModel):
    escalation_assignee_user_id: int | None = None
    department_id: int | None = None
    team_id: int | None = None
    escalation_level: Literal["SENIOR_ENGINEER", "TEAM_LEADER", "OTHER_DEPARTMENT"] | None = None
    reason: str = Field(min_length=5, max_length=1000)
    version: int

    @model_validator(mode="after")
    def active_escalation_requires_level(self) -> TicketEscalation:
        if (
            self.escalation_assignee_user_id is not None or self.department_id is not None
        ) and self.escalation_level is None:
            raise ValueError("Escalation level is required when assigning an escalation.")
        if self.team_id is not None and self.department_id is None:
            raise ValueError("Department is required when routing to a team.")
        return self


class TicketHelpReturn(BaseModel):
    result: str = Field(min_length=5, max_length=10000)
    version: int


class TicketBulkItem(BaseModel):
    ticket_id: int
    expected_version: int = Field(ge=1)


class TicketBulkAssignment(BaseModel):
    items: list[TicketBulkItem] = Field(min_length=1, max_length=100)
    assigned_user_id: int | None = None
    assigned_team: str | None = Field(default=None, max_length=150)
    reason: str | None = Field(default=None, max_length=500)


class TicketBulkStatus(BaseModel):
    items: list[TicketBulkItem] = Field(min_length=1, max_length=100)
    to_status_code: str = Field(min_length=2, max_length=50)
    reason: str | None = Field(default=None, max_length=500)
    resolution_summary: str | None = Field(default=None, min_length=5, max_length=10000)
    root_cause_summary: str | None = Field(default=None, min_length=5, max_length=10000)
    root_cause_ids: list[int] = Field(default_factory=list, max_length=20)
    pending_owner_user_id: int | None = None
    pending_follow_up_at: datetime | None = None
    pending_responsible_party: Literal["CUSTOMER", "MILLENSYS"] | None = None


class TicketBulkDelete(BaseModel):
    ticket_ids: list[int] = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=5, max_length=500)


class TicketArchiveRestore(BaseModel):
    reason: str = Field(min_length=5, max_length=500)
    version: int


class TicketDeletionDecision(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    comment: str = Field(min_length=3, max_length=1000)


class TicketDeletionRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ticket_id: int
    ticket_number: str | None = None
    ticket_subject: str | None = None
    requested_by_user_id: int
    requested_by_name: str | None = None
    reason: str
    status: str
    decided_by_user_id: int | None
    decision_comment: str | None
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int


class TicketRequesterUpdate(BaseModel):
    requester_contact_id: int | None = None
    reason: str = Field(min_length=3, max_length=500)
    version: int


class TicketFollowersUpdate(BaseModel):
    user_ids: list[int] = Field(default_factory=list)
    reason: str = Field(min_length=3, max_length=500)
    version: int


class TicketFollowerRead(BaseModel):
    user_id: int
    full_name: str
    username: str
    created_at: datetime


class TicketTaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    assigned_user_id: int | None = None
    due_at: datetime | None = None
    is_required: bool = True


class TicketTaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    assigned_user_id: int | None = None
    status: str | None = Field(default=None, pattern="^(OPEN|IN_PROGRESS|COMPLETED|CANCELLED)$")
    due_at: datetime | None = None
    is_required: bool | None = None


class TicketTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ticket_id: int
    title: str
    description: str | None
    assigned_user_id: int | None
    status: str
    due_at: datetime | None
    completed_at: datetime | None
    is_required: bool
    created_at: datetime


class TicketWorklogCreate(BaseModel):
    task_id: int | None = None
    started_at: datetime
    ended_at: datetime
    notes: str = Field(min_length=2, max_length=2000)


class TicketWorklogUpdate(BaseModel):
    task_id: int | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    notes: str | None = Field(default=None, min_length=2, max_length=2000)
    version: int


class TicketWorklogDecision(BaseModel):
    approved: bool
    reason: str | None = Field(default=None, max_length=500)
    version: int


class TicketWorklogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ticket_id: int
    task_id: int | None
    user_id: int
    started_at: datetime
    ended_at: datetime
    duration_minutes: int
    notes: str
    status: str
    approved_by_user_id: int | None
    approved_at: datetime | None
    rejection_reason: str | None
    version: int
    created_at: datetime


class ChecklistItemCreate(BaseModel):
    label: str = Field(min_length=2, max_length=300)
    sort_order: int = 0
    is_required: bool = True


class ChecklistItemUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=2, max_length=300)
    sort_order: int | None = None
    is_completed: bool | None = None
    is_required: bool | None = None


class ChecklistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ticket_id: int
    label: str
    sort_order: int
    is_completed: bool
    is_required: bool
    completed_by_user_id: int | None
    completed_at: datetime | None
    created_at: datetime


class TicketCatalogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    name_ar: str | None = None
    color: str | None = None
    number_prefix: str | None = None
    is_active: bool | None = None
    available_for_deployment_issue: bool | None = None


class TicketTypeCreate(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]+$", min_length=2, max_length=30)
    name: str = Field(min_length=2, max_length=100)
    name_ar: str | None = Field(default=None, min_length=2, max_length=100)
    number_prefix: str = Field(pattern=r"^[A-Za-z0-9_-]+$", min_length=1, max_length=10)
    color: str = Field(default="#607D8B", pattern=r"^#[0-9A-Fa-f]{6}$")
    is_active: bool = True
    available_for_deployment_issue: bool = False


class TicketTypeUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    name_ar: str | None = Field(default=None, min_length=2, max_length=100)
    number_prefix: str = Field(pattern=r"^[A-Za-z0-9_-]+$", min_length=1, max_length=10)
    color: str = Field(default="#607D8B", pattern=r"^#[0-9A-Fa-f]{6}$")
    is_active: bool = True
    available_for_deployment_issue: bool = False


class TicketStatusUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    name_ar: str | None = Field(default=None, min_length=2, max_length=100)
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class RootCauseCreate(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]+$", min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=150)
    name_ar: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    description_ar: str | None = Field(default=None, max_length=1000)
    requires_resolution_outcome: bool = False
    requires_permanent_fix: bool = False
    is_active: bool = True


class RootCauseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    name_ar: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    description_ar: str | None = Field(default=None, max_length=1000)
    requires_resolution_outcome: bool | None = None
    requires_permanent_fix: bool | None = None
    is_active: bool | None = None


class RootCauseRead(RootCauseCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ResolutionOutcomeCreate(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]+$", min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=150)
    name_ar: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    description_ar: str | None = Field(default=None, max_length=1000)
    requires_permanent_fix: bool = False
    is_active: bool = True


class ResolutionOutcomeRead(ResolutionOutcomeCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class TicketAssigneeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    username: str
    department: str | None
    job_title: str | None
    last_assigned_at: datetime | None = None


class TicketAttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    uploaded_by_user_id: int
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    scan_status: str
    created_at: datetime


class TicketRelationCreate(BaseModel):
    related_ticket_id: int
    relation_type: str = Field(pattern="^(RELATED|DUPLICATE|PARENT_CHILD|CAUSED_BY)$")
    reason: str | None = Field(default=None, max_length=500)


class TicketRelationRead(BaseModel):
    id: int
    relation_type: str
    direction: str
    related_ticket_id: int
    related_ticket_number: str
    related_subject: str
    related_priority: str
    created_at: datetime


class TicketTimelineRead(BaseModel):
    id: str
    event_type: str
    title: str
    description: str | None
    actor_name: str | None
    is_internal: bool
    created_at: datetime
