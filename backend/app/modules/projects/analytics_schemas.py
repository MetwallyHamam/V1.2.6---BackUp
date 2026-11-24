from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ProjectKpiDefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    domain: str
    description: str
    formula: str
    numerator_definition: str | None
    denominator_definition: str | None
    unit: str
    target_direction: str
    zero_denominator_policy: str
    time_basis: str
    allowed_scopes: list[str]
    eligibility_rules: list[str]
    exclusions: list[str]
    required_permission: str
    drilldown_resource: str
    owner_role: str
    version: int
    is_active: bool
    updated_at: datetime


class AnalyticsScopePolicyRead(BaseModel):
    domains: dict[str, str]
    rules: list[str]


class AnalyticsScopeRead(BaseModel):
    account_id: int | None = None
    organization_id: int | None = None
    client_id: int | None = None
    department_id: int | None = None
    project_id: int | None = None
    team_id: int | None = None
    user_id: int | None = None
    effective_department_ids: list[int]
    global_scope: bool


class KpiProjectionRead(BaseModel):
    code: str
    name: str
    domain: str
    status: str
    value: float | None
    unit: str
    numerator: float | None
    denominator: float | None
    eligible_count: int
    drilldown_count: int
    unavailable_reason: str | None = None


class AnalyticsProjectionRead(BaseModel):
    domain: str
    period_start: date
    period_end: date
    generated_at: datetime
    scope: AnalyticsScopeRead
    metrics: list[KpiProjectionRead]


class KpiDrilldownRow(BaseModel):
    record_type: str
    record_id: int
    project_id: int | None = None
    project_number: str | None = None
    client_id: int | None = None
    department_id: int | None = None
    label: str
    numerator_contribution: float | None = None
    denominator_contribution: float | None = None
    measured_value: float | None = None
    occurred_at: datetime | date | None = None
    status: str | None = None


class KpiDrilldownRead(BaseModel):
    projection: KpiProjectionRead
    scope: AnalyticsScopeRead
    period_start: date
    period_end: date
    rows: list[KpiDrilldownRow]


class AnalyticsOptionRead(BaseModel):
    id: int
    name: str
    department_id: int | None = None


class AnalyticsOptionsRead(BaseModel):
    departments: list[AnalyticsOptionRead]
    teams: list[AnalyticsOptionRead]
    engineers: list[AnalyticsOptionRead]


class SupportReadinessQueueItem(BaseModel):
    handover_id: int
    project_id: int
    project_number: str
    project_name: str
    client_id: int
    department_id: int
    status: str
    readiness_percent: int
    submitted_at: datetime | None
    activated_at: datetime | None
    missing_required_items: int
    missing_evidence_items: int
    open_residual_items: int
    overdue_residual_items: int
    stabilization_status: str | None
    stabilization_end_date: date | None
    risk_level: str
    risk_reasons: list[str]


class SupportReadinessQueueRead(BaseModel):
    scope: AnalyticsScopeRead
    total: int
    review_required: int
    activation_risk: int
    stabilization_active: int
    items: list[SupportReadinessQueueItem]


class ExecutivePortfolioRow(BaseModel):
    account_id: int
    account_name: str
    organization_id: int
    organization_name: str
    project_count: int
    at_risk_count: int
    average_progress_percent: float
    handover_count: int
    average_readiness_percent: float | None


class ExecutivePortfolioRead(BaseModel):
    scope: AnalyticsScopeRead
    total_projects: int
    total_at_risk: int
    rows: list[ExecutivePortfolioRow]
