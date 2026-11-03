from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentKpi(BaseModel):
    user_id: int | None
    agent: str
    department: str | None
    assigned: int
    open: int
    resolved: int
    breached: int
    sla_compliance_percent: float | None
    average_resolution_hours: float | None
    tickets_by_status: dict[str, int]
    escalation_assignments: int
    average_response_hours: float | None
    reopened_tickets: int
    external_activities: int
    after_shift_work: int
    after_shift_hours: float
    training_attended: int
    training_delivered: int
    meetings: int
    tasks_created: int
    knowledge_articles: int
    follower_assignments: int
    dedicated_clients: int
    dedicated_client_tickets: int


class TopSupportAgent(BaseModel):
    user_id: int
    agent: str
    department: str | None
    assigned: int
    resolved: int
    breached: int


class TopSupportAgentsRead(BaseModel):
    date_from: datetime
    date_to: datetime
    date_basis: Literal["RESOLUTION"] = "RESOLUTION"
    agents: list[TopSupportAgent]


class ProductKpi(BaseModel):
    product: str
    module: str
    total: int
    open: int
    resolved: int
    breached: int
    average_resolution_hours: float | None


class AvailableEmployee(BaseModel):
    user_id: int
    employee: str
    shift_name: str
    shift_color: str
    starts_at: datetime
    ends_at: datetime
    team: str | None


class OnlineEngineer(BaseModel):
    user_id: int
    engineer: str
    department: str | None
    status: str
    ticket_number: str | None
    active_ticket_count: int = 0
    tickets_by_priority: dict[str, int] = Field(default_factory=dict)


class DashboardSummary(BaseModel):
    total_tickets: int
    created_today: int
    closed_today: int
    total_open: int
    my_open: int
    unassigned: int
    critical: int
    breached: int
    due_soon: int
    pending_approvals: int
    shift_handovers: int
    department_new: int
    department_in_progress: int
    department_returned: int
    resolved: int
    closed: int
    by_priority: dict[str, int]
    by_status: dict[str, int]
    priority_by_status: dict[str, dict[str, int]]
    backlog_by_client: dict[str, int]
    backlog_by_product: dict[str, int]
    backlog_by_module: dict[str, int]
    workload_by_engineer: dict[str, int]
    backlog_by_team: dict[str, int]
    sla_compliance_percent: float | None
    aging_buckets: dict[str, int]
    inflow_last_7_days: dict[str, int]
    closures_last_7_days: dict[str, int]
    average_resolution_hours: float | None
    reopen_rate_percent: float
    active_escalations: int
    top_categories: dict[str, int]
    top_repeated_issues: dict[str, int]
    expiring_contracts: int
    agent_kpis: list[AgentKpi]
    product_kpis: list[ProductKpi]
    kpi_month: str
    available_employees: list[AvailableEmployee]
    online_engineers: list[OnlineEngineer]
    contracts_by_status: dict[str, int]
    contracts_expiring: dict[str, int]
    contracts_without_renewal_date: int
    recently_expired_contracts: int
    engineer_counts: dict[str, int]
    engineers_by_level: dict[str, int]
    engineers_by_department: dict[str, int]
    financial_contracts: int
    financial_invoices: int
    hr_total_employees: int
    hr_active_employees: int
    hr_inactive_employees: int
    hr_departments: int
    hr_head_vacancies: int
    hr_reporting_exceptions: int
    hr_kpi_pending: int
    hr_kpi_finalized: int
    hr_onboarding_in_progress: int
    hr_unscheduled_employees: int
    project_total: int
    project_delivered: int
    project_in_progress: int
    project_awaiting_acceptance: int
    project_pending_products: int
    project_pending_points: int
    projects_by_status: dict[str, int]
    projects_by_client: dict[str, int]


class AgentActivityCreate(BaseModel):
    user_id: int
    activity_type: Literal["TRAINING", "MEETING"]
    participation_role: Literal["ATTENDEE", "FACILITATOR", "PRESENTER", "PARTICIPANT"]
    title: str = Field(min_length=3, max_length=300)
    duration_minutes: int = Field(ge=1, le=1440)
    occurred_at: datetime
    notes: str | None = Field(default=None, max_length=1000)


class AgentActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    activity_type: str
    participation_role: str
    title: str
    duration_minutes: int
    occurred_at: datetime
    notes: str | None


class SavedViewCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    scope: Literal["PRIVATE", "TEAM", "DEPARTMENT", "GLOBAL"] = "PRIVATE"
    team_id: int | None = None
    department_id: int | None = None
    filters: dict[str, object]
    columns: list[str] = []
    sort: list[dict[str, str]] = []
    has_layout: bool = False
    is_default: bool = False

    @model_validator(mode="after")
    def team_scope_requires_team(self) -> "SavedViewCreate":
        if self.scope == "TEAM" and self.team_id is None:
            raise ValueError("Team-scoped views require a support team.")
        if self.scope != "TEAM" and self.team_id is not None:
            raise ValueError("A support team may only be set for team-scoped views.")
        if self.scope == "DEPARTMENT" and self.department_id is None:
            raise ValueError("Department-scoped views require a department.")
        if self.scope != "DEPARTMENT" and self.department_id is not None:
            raise ValueError("A department may only be set for department-scoped views.")
        return self


class SavedViewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_user_id: int
    name: str
    scope: str
    team_id: int | None
    department_id: int | None
    filter_json: str
    columns_json: str | None
    sort_json: str | None
    has_layout: bool
    is_default: bool


class SavedViewUpdate(SavedViewCreate):
    pass


class TicketGridPreferenceData(BaseModel):
    columns: list[str] = Field(default_factory=list)
    column_widths: dict[str, int] = Field(default_factory=dict)
    density: Literal["COMPACT", "STANDARD"] = "COMPACT"
    page_size: Literal[25, 50, 100] = 25
    sort_by: Literal["updated_at", "created_at", "priority", "ticket_number"] = "updated_at"
    sort_direction: Literal["asc", "desc"] = "desc"
    group_by: str = Field(default="", max_length=40)
    default_view_mode: Literal["GRID", "CARDS"] = "GRID"
    selected_group_values: list[str] = Field(default_factory=list, max_length=100)
    board_settings: dict[str, object] = Field(default_factory=dict)


class DashboardWidgetConfig(BaseModel):
    widget_code: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9_]+$")
    title: str = Field(min_length=2, max_length=150)
    widget_type: Literal["KPI_CARD", "DONUT", "STACKED_BAR", "LINE"] = "KPI_CARD"
    query_code: str = Field(min_length=2, max_length=80)
    position: int = Field(ge=0, le=100)
    width: int = Field(default=2, ge=1, le=12)
    refresh_seconds: int = Field(default=60, ge=15, le=3600)
    config: dict[str, object] = Field(default_factory=dict)


class DashboardWidgetCatalogItem(BaseModel):
    widget_code: str
    title: str
    description: str
    widget_type: Literal["KPI_CARD", "DONUT", "STACKED_BAR", "LINE"]
    query_code: str
    default_width: int
    required_permissions: list[str] = Field(default_factory=list)


class DashboardConfigUpdate(BaseModel):
    name: str = Field(default="My Dashboard", min_length=2, max_length=150)
    widgets: list[DashboardWidgetConfig]


class DashboardConfigRead(BaseModel):
    source: str
    name: str
    template_code: str | None = None
    template_version: int = 1
    assignment_id: int | None = None
    resolution_explanation: str | None = None
    base_template_code: str | None = None
    base_template_version: int | None = None
    assigned_template_version: int | None = None
    template_update_available: bool = False
    widgets: list[DashboardWidgetConfig]
    available_widgets: list[DashboardWidgetConfig] = Field(default_factory=list)
    hidden_widget_codes: list[str] = Field(default_factory=list)


class DashboardAdminPreviewRead(DashboardConfigRead):
    user_id: int
    user_name: str
    permission_codes: list[str]


class DashboardScenarioPreviewRead(DashboardConfigRead):
    profile_id: int | None
    department_id: int | None
    permission_codes: list[str]


class DashboardAssignmentImpactRead(BaseModel):
    assignment_id: int
    affected_user_count: int


class DashboardTemplateCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80, pattern=r"^[A-Z0-9_]+$")
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    destination: Literal["EXECUTIVE", "TOP_MANAGEMENT"] = "EXECUTIVE"
    widgets: list[DashboardWidgetConfig] = Field(default_factory=list)


class DashboardTemplateUpdate(BaseModel):
    expected_version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None
    widgets: list[DashboardWidgetConfig] | None = None


class DashboardTemplateRead(BaseModel):
    id: int
    code: str | None
    name: str
    description: str | None
    destination: Literal["EXECUTIVE", "TOP_MANAGEMENT"]
    version: int
    is_active: bool
    widgets: list[DashboardWidgetConfig]


class DashboardAssignmentCreate(BaseModel):
    dashboard_id: int
    dashboard_type: Literal["EXECUTIVE", "TOP_MANAGEMENT"] = "EXECUTIVE"
    profile_id: int | None = None
    department_id: int | None = None
    user_id: int | None = None
    priority: int = Field(default=0, ge=-1000, le=1000)
    effective_from: datetime | None = None
    effective_until: datetime | None = None

    @model_validator(mode="after")
    def validate_target(self) -> "DashboardAssignmentCreate":
        if self.user_id is not None and (
            self.profile_id is not None or self.department_id is not None
        ):
            raise ValueError(
                "User assignments cannot be combined with profile or department targets."
            )
        if (
            self.effective_from
            and self.effective_until
            and self.effective_until <= self.effective_from
        ):
            raise ValueError("The assignment end must be after its start.")
        return self


class DashboardAssignmentUpdate(BaseModel):
    expected_version: int = Field(ge=1)
    priority: int | None = Field(default=None, ge=-1000, le=1000)
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_period(self) -> "DashboardAssignmentUpdate":
        if (
            self.effective_from
            and self.effective_until
            and self.effective_until <= self.effective_from
        ):
            raise ValueError("The assignment end must be after its start.")
        return self


class DashboardAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    dashboard_id: int
    dashboard_type: str
    is_personal: bool
    profile_id: int | None
    department_id: int | None
    user_id: int | None
    priority: int
    effective_from: datetime | None
    effective_until: datetime | None
    is_active: bool
    version: int


class DashboardProfileAccessUpdate(BaseModel):
    dashboard_id: int = Field(gt=0)
    can_view: bool = True
    is_default: bool = False
    is_active: bool = True


class DashboardTabWidgetRead(BaseModel):
    assignment_id: int
    widget_id: int
    code: str
    name: str
    description: str | None
    category: str
    component_key: str
    source_type: str
    display_order: int
    width: int
    height: int
    is_visible: bool
    configuration: dict[str, object] = Field(default_factory=dict)


class DashboardTabRead(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    display_order: int
    widgets: list[DashboardTabWidgetRead] = Field(default_factory=list)


class AccessibleDashboardRead(BaseModel):
    id: int
    code: str | None
    name: str
    description: str | None
    scope: str
    is_default: bool
    tabs: list[DashboardTabRead] = Field(default_factory=list)
