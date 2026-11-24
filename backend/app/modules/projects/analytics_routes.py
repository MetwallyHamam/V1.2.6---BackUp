from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, true
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, require_permission
from app.db.session import get_db
from app.modules.iam.models import User
from app.modules.projects.analytics_schemas import (
    AnalyticsOptionsRead,
    AnalyticsProjectionRead,
    AnalyticsScopePolicyRead,
    ExecutivePortfolioRead,
    KpiDrilldownRead,
    ProjectKpiDefinitionRead,
    SupportReadinessQueueRead,
)
from app.modules.projects.analytics_service import (
    ProjectionFilters,
    analytics_options,
    drilldown,
    executive_portfolio,
    projection,
    support_readiness_queue,
)
from app.modules.projects.models import ProjectKpiDefinition

router = APIRouter(prefix="/project-analytics", tags=["project-analytics"])


def _filters(
    period_start: date,
    period_end: date,
    account_id: int | None,
    organization_id: int | None,
    client_id: int | None,
    department_id: int | None,
    project_id: int | None,
    team_id: int | None,
    user_id: int | None,
) -> ProjectionFilters:
    if period_end < period_start:
        raise HTTPException(status_code=422, detail="period_end cannot precede period_start")
    if (period_end - period_start).days > 731:
        raise HTTPException(status_code=422, detail="Analytics period cannot exceed 731 days")
    return ProjectionFilters(
        period_start=period_start,
        period_end=period_end,
        account_id=account_id,
        organization_id=organization_id,
        client_id=client_id,
        department_id=department_id,
        project_id=project_id,
        team_id=team_id,
        user_id=user_id,
    )


@router.get("/options/{domain}", response_model=AnalyticsOptionsRead)
def get_analytics_options(
    domain: str,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> AnalyticsOptionsRead:
    return analytics_options(db, actor, domain)


@router.get("/support-readiness/queue", response_model=SupportReadinessQueueRead)
def get_support_readiness_queue(
    period_start: date,
    period_end: date,
    account_id: int | None = None,
    organization_id: int | None = None,
    client_id: int | None = None,
    department_id: int | None = None,
    project_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> SupportReadinessQueueRead:
    return support_readiness_queue(
        db,
        actor,
        _filters(
            period_start,
            period_end,
            account_id,
            organization_id,
            client_id,
            department_id,
            project_id,
            None,
            None,
        ),
    )


@router.get("/executive/portfolio", response_model=ExecutivePortfolioRead)
def get_executive_portfolio(
    period_start: date,
    period_end: date,
    account_id: int | None = None,
    organization_id: int | None = None,
    client_id: int | None = None,
    department_id: int | None = None,
    project_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> ExecutivePortfolioRead:
    return executive_portfolio(
        db,
        actor,
        _filters(
            period_start,
            period_end,
            account_id,
            organization_id,
            client_id,
            department_id,
            project_id,
            None,
            None,
        ),
    )


@router.get("/projections/{domain}", response_model=AnalyticsProjectionRead)
def get_projection(
    domain: str,
    period_start: date,
    period_end: date,
    account_id: int | None = None,
    organization_id: int | None = None,
    client_id: int | None = None,
    department_id: int | None = None,
    project_id: int | None = None,
    team_id: int | None = None,
    user_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> AnalyticsProjectionRead:
    return projection(
        db,
        actor,
        domain,
        _filters(
            period_start,
            period_end,
            account_id,
            organization_id,
            client_id,
            department_id,
            project_id,
            team_id,
            user_id,
        ),
    )


@router.get("/projections/kpi/{code}/drilldown", response_model=KpiDrilldownRead)
def get_projection_drilldown(
    code: str,
    period_start: date,
    period_end: date,
    account_id: int | None = None,
    organization_id: int | None = None,
    client_id: int | None = None,
    department_id: int | None = None,
    project_id: int | None = None,
    team_id: int | None = None,
    user_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> KpiDrilldownRead:
    return drilldown(
        db,
        actor,
        code,
        _filters(
            period_start,
            period_end,
            account_id,
            organization_id,
            client_id,
            department_id,
            project_id,
            team_id,
            user_id,
        ),
    )


@router.get("/kpi-dictionary", response_model=list[ProjectKpiDefinitionRead])
def list_kpi_dictionary(
    domain: str | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("analytics.dictionary.view")),
) -> list[ProjectKpiDefinition]:
    query = select(ProjectKpiDefinition)
    if domain:
        query = query.where(ProjectKpiDefinition.domain == domain.upper())
    if not include_inactive:
        query = query.where(ProjectKpiDefinition.is_active == true())
    return list(db.scalars(query.order_by(ProjectKpiDefinition.domain, ProjectKpiDefinition.code)))


@router.get("/kpi-dictionary/{code}", response_model=ProjectKpiDefinitionRead)
def get_kpi_definition(
    code: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("analytics.dictionary.view")),
) -> ProjectKpiDefinition:
    definition = db.scalar(
        select(ProjectKpiDefinition).where(ProjectKpiDefinition.code == code.upper())
    )
    if definition is None:
        raise HTTPException(status_code=404, detail="KPI definition not found")
    return definition


@router.get("/scope-policy", response_model=AnalyticsScopePolicyRead)
def get_scope_policy(
    _: User = Depends(require_permission("analytics.dictionary.view")),
) -> AnalyticsScopePolicyRead:
    return AnalyticsScopePolicyRead(
        domains={
            "PROJECT": "analytics.project.view",
            "IMPLEMENTATION": "analytics.implementation.view",
            "SUPPORT_READINESS": "analytics.support_readiness.view",
            "EXECUTIVE": "analytics.executive.view",
        },
        rules=[
            "Dictionary access does not grant access to calculated KPI values.",
            "Every metric query must enforce its required permission and customer/department scope.",
            "Drilldowns must apply the same or a narrower scope than the aggregate.",
            "Cross-department visibility never exposes department-private notes or employee KPIs.",
        ],
    )
