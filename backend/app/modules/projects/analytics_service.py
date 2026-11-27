from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import func, or_, select, true
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.clock import server_now
from app.core.exceptions import AuthorizationError, NotFoundError
from app.modules.clients.models import Account, Organization, SupportTeam, SupportTeamMember
from app.modules.customer_structure.policies import resolve_client
from app.modules.iam.models import Department, DepartmentMembership, User
from app.modules.iam.service import effective_permissions
from app.modules.projects.analytics_schemas import (
    AnalyticsOptionRead,
    AnalyticsOptionsRead,
    AnalyticsProjectionRead,
    AnalyticsScopeRead,
    ExecutivePortfolioRead,
    ExecutivePortfolioRow,
    KpiDrilldownRead,
    KpiDrilldownRow,
    KpiProjectionRead,
    SupportReadinessQueueItem,
    SupportReadinessQueueRead,
)
from app.modules.projects.models import (
    CompanyProject,
    CrossDepartmentRequest,
    ProjectDepartment,
    ProjectHandoverItem,
    ProjectHandoverResidualItem,
    ProjectHandoverSection,
    ProjectKpiDefinition,
    ProjectStabilizationPlan,
    ProjectSupportHandover,
    ProjectTask,
    ProjectTaskAssignee,
    ProjectTaskBlocker,
    ProjectTaskReview,
    ProjectTeam,
    ProjectWorkLog,
)

DOMAIN_PERMISSIONS = {
    "PROJECT": "analytics.project.view",
    "IMPLEMENTATION": "analytics.implementation.view",
    "SUPPORT_READINESS": "analytics.support_readiness.view",
    "EXECUTIVE": "analytics.executive.view",
}


@dataclass(frozen=True)
class ProjectionFilters:
    period_start: date
    period_end: date
    account_id: int | None = None
    organization_id: int | None = None
    client_id: int | None = None
    department_id: int | None = None
    project_id: int | None = None
    team_id: int | None = None
    user_id: int | None = None


@dataclass
class CalculatedMetric:
    projection: KpiProjectionRead
    rows: list[KpiDrilldownRow]


def _date_bounds(filters: ProjectionFilters) -> tuple[datetime, datetime]:
    return (
        datetime.combine(filters.period_start, time.min, tzinfo=UTC),
        datetime.combine(filters.period_end, time.max, tzinfo=UTC),
    )


def _department_ids(db: Session, actor: User, on_date: date) -> set[int]:
    ids = {actor.department_id} if actor.department_id else set()
    ids.update(
        db.scalars(
            select(DepartmentMembership.department_id).where(
                DepartmentMembership.user_id == actor.id,
                DepartmentMembership.effective_from <= on_date,
                or_(
                    DepartmentMembership.effective_until.is_(None),
                    DepartmentMembership.effective_until >= on_date,
                ),
            )
        )
    )
    return ids


def _authorized_projects(
    db: Session, actor: User, domain: str, filters: ProjectionFilters
) -> tuple[list[CompanyProject], AnalyticsScopeRead]:
    permissions = effective_permissions(db, actor).permissions
    required = DOMAIN_PERMISSIONS[domain]
    if required not in permissions:
        raise AuthorizationError(details={"required_permission": required})
    global_scope = "analytics.executive.view" in permissions
    department_ids = _department_ids(db, actor, filters.period_end)
    if filters.department_id is not None:
        if not global_scope and filters.department_id not in department_ids:
            raise AuthorizationError(details={"requested_department_id": filters.department_id})
        requested_departments = {filters.department_id}
    else:
        requested_departments = department_ids

    if filters.team_id is not None:
        team = db.get(SupportTeam, filters.team_id)
        if team is None:
            raise NotFoundError("Analytics team does not exist.")
        if not global_scope and team.department_id not in requested_departments:
            raise AuthorizationError(details={"requested_team_id": filters.team_id})
    if filters.user_id is not None:
        target = db.get(User, filters.user_id)
        if target is None or not target.is_active:
            raise NotFoundError("Analytics engineer does not exist.")
        target_departments = _department_ids(db, target, filters.period_end)
        if not global_scope and requested_departments.isdisjoint(target_departments):
            raise AuthorizationError(details={"requested_user_id": filters.user_id})

    statement = select(CompanyProject).where(CompanyProject.is_active == true())
    if filters.account_id is not None:
        statement = statement.where(CompanyProject.account_id == filters.account_id)
    if filters.organization_id is not None:
        statement = statement.where(CompanyProject.organization_id == filters.organization_id)
    if filters.client_id is not None:
        statement = statement.where(CompanyProject.client_id == filters.client_id)
    if filters.project_id is not None:
        statement = statement.where(CompanyProject.id == filters.project_id)
    if domain == "PROJECT" and not global_scope and "workspace.project_management.access" in permissions:
        statement = statement.where(CompanyProject.project_manager_user_id == actor.id)
    projects = list(db.scalars(statement.order_by(CompanyProject.id)))

    if filters.team_id is not None:
        team_project_ids = set(
            db.scalars(
                select(ProjectTeam.project_id).where(ProjectTeam.team_id == filters.team_id)
            )
        )
        projects = [row for row in projects if row.id in team_project_ids]

    if not global_scope:
        project_department_pairs = set(
            db.execute(
                select(ProjectDepartment.project_id, ProjectDepartment.department_id).where(
                    ProjectDepartment.project_id.in_([row.id for row in projects] or [-1]),
                    ProjectDepartment.department_id.in_(requested_departments or {-1}),
                )
            )
        )
        allowed_project_ids = {project_id for project_id, _ in project_department_pairs}
        if domain == "SUPPORT_READINESS":
            for project in projects:
                _, assignments = resolve_client(db, project.client_id)
                if any(item.department_id in requested_departments for item in assignments):
                    allowed_project_ids.add(project.id)
        projects = [row for row in projects if row.id in allowed_project_ids]
    elif filters.department_id is not None:
        project_ids = set(
            db.scalars(
                select(ProjectDepartment.project_id).where(
                    ProjectDepartment.department_id == filters.department_id
                )
            )
        )
        projects = [row for row in projects if row.id in project_ids]

    return projects, AnalyticsScopeRead(
        account_id=filters.account_id,
        organization_id=filters.organization_id,
        client_id=filters.client_id,
        department_id=filters.department_id,
        project_id=filters.project_id,
        team_id=filters.team_id,
        user_id=filters.user_id,
        effective_department_ids=sorted(department_ids),
        global_scope=global_scope,
    )


def analytics_options(db: Session, actor: User, domain: str) -> AnalyticsOptionsRead:
    normalized = domain.upper()
    if normalized not in DOMAIN_PERMISSIONS:
        raise NotFoundError("Analytics domain does not exist.")
    permissions = effective_permissions(db, actor).permissions
    if DOMAIN_PERMISSIONS[normalized] not in permissions:
        raise AuthorizationError(details={"required_permission": DOMAIN_PERMISSIONS[normalized]})
    global_scope = "analytics.executive.view" in permissions
    department_ids = _department_ids(db, actor, server_now().date())
    departments_query = select(Department).where(Department.is_active == true())
    teams_query = select(SupportTeam).where(SupportTeam.is_active == true())
    users_query = select(User).where(User.is_active == true(), User.user_type == "EMPLOYEE")
    if normalized == "IMPLEMENTATION" and _implementation_self_scope(permissions):
        users_query = users_query.where(User.id == actor.id)
        teams_query = teams_query.where(SupportTeam.id == -1)
    if not global_scope:
        departments_query = departments_query.where(Department.id.in_(department_ids or {-1}))
        teams_query = teams_query.where(SupportTeam.department_id.in_(department_ids or {-1}))
        users_query = users_query.where(User.department_id.in_(department_ids or {-1}))
    departments = list(db.scalars(departments_query.order_by(Department.name)))
    teams = list(db.scalars(teams_query.order_by(SupportTeam.name)))
    users = list(db.scalars(users_query.order_by(User.full_name)))
    return AnalyticsOptionsRead(
        departments=[AnalyticsOptionRead(id=row.id, name=row.name, department_id=row.id) for row in departments],
        teams=[AnalyticsOptionRead(id=row.id, name=row.name, department_id=row.department_id) for row in teams],
        engineers=[AnalyticsOptionRead(id=row.id, name=row.full_name, department_id=row.department_id) for row in users],
    )


def support_readiness_queue(
    db: Session, actor: User, filters: ProjectionFilters
) -> SupportReadinessQueueRead:
    projects, scope = _authorized_projects(db, actor, "SUPPORT_READINESS", filters)
    project_map = {row.id: row for row in projects}
    handovers = list(
        db.scalars(
            select(ProjectSupportHandover)
            .where(ProjectSupportHandover.project_id.in_(list(project_map) or [-1]))
            .order_by(ProjectSupportHandover.updated_at.desc())
        )
    )
    items: list[SupportReadinessQueueItem] = []
    for handover in handovers:
        project = project_map[handover.project_id]
        required_items = list(
            db.scalars(
                select(ProjectHandoverItem)
                .join(
                    ProjectHandoverSection,
                    ProjectHandoverSection.id == ProjectHandoverItem.section_id,
                )
                .where(
                    ProjectHandoverSection.handover_id == handover.id,
                    ProjectHandoverItem.is_required == true(),
                )
            )
        )
        residual = list(
            db.scalars(
                select(ProjectHandoverResidualItem).where(
                    ProjectHandoverResidualItem.handover_id == handover.id,
                    ProjectHandoverResidualItem.status != "CLOSED",
                )
            )
        )
        plan = db.scalar(
            select(ProjectStabilizationPlan).where(
                ProjectStabilizationPlan.handover_id == handover.id
            )
        )
        missing_required = sum(row.status != "READY" for row in required_items)
        missing_evidence = sum(
            row.requires_evidence and row.evidence_id is None for row in required_items
        )
        overdue_residual = sum(row.target_date < filters.period_end for row in residual)
        reasons: list[str] = []
        if handover.status == "SUBMITTED":
            reasons.append("Support review required")
        if missing_required:
            reasons.append(f"{missing_required} required item(s) not ready")
        if missing_evidence:
            reasons.append(f"{missing_evidence} evidence item(s) missing")
        if handover.status in {"ACCEPTED", "CONDITIONALLY_ACCEPTED"} and plan is None:
            reasons.append("Stabilization plan missing")
        if overdue_residual:
            reasons.append(f"{overdue_residual} residual item(s) overdue")
        if plan and plan.end_date < filters.period_end and plan.status == "ACTIVE":
            reasons.append("Stabilization end date passed")
        if handover.status in {"REJECTED", "CHANGES_REQUESTED"}:
            reasons.append("Implementation action required")
        high_risk = bool(
            missing_evidence
            or overdue_residual
            or "Stabilization plan missing" in reasons
            or handover.status in {"REJECTED", "CHANGES_REQUESTED"}
        )
        risk_level = "HIGH" if high_risk else "MEDIUM" if reasons else "LOW"
        items.append(
            SupportReadinessQueueItem(
                handover_id=handover.id,
                project_id=project.id,
                project_number=project.project_number,
                project_name=project.name,
                client_id=project.client_id,
                department_id=project.owning_department_id,
                status=handover.status,
                readiness_percent=handover.readiness_percent,
                submitted_at=handover.submitted_at,
                activated_at=handover.activated_at,
                missing_required_items=missing_required,
                missing_evidence_items=missing_evidence,
                open_residual_items=len(residual),
                overdue_residual_items=overdue_residual,
                stabilization_status=plan.status if plan else None,
                stabilization_end_date=plan.end_date if plan else None,
                risk_level=risk_level,
                risk_reasons=reasons,
            )
        )
    return SupportReadinessQueueRead(
        scope=scope,
        total=len(items),
        review_required=sum(row.status == "SUBMITTED" for row in items),
        activation_risk=sum(row.risk_level == "HIGH" for row in items),
        stabilization_active=sum(row.stabilization_status == "ACTIVE" for row in items),
        items=sorted(
            items,
            key=lambda row: (
                {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[row.risk_level],
                row.project_number,
            ),
        ),
    )


def executive_portfolio(
    db: Session, actor: User, filters: ProjectionFilters
) -> ExecutivePortfolioRead:
    projects, scope = _authorized_projects(db, actor, "EXECUTIVE", filters)
    account_ids = {row.account_id for row in projects}
    organization_ids = {row.organization_id for row in projects}
    account_names = {
        row.id: row.name
        for row in db.scalars(select(Account).where(Account.id.in_(account_ids or {-1})))
    }
    organization_names = {
        row.id: row.name
        for row in db.scalars(
            select(Organization).where(Organization.id.in_(organization_ids or {-1}))
        )
    }
    groups: dict[tuple[int, int], list[CompanyProject]] = {}
    for project in projects:
        groups.setdefault((project.account_id, project.organization_id), []).append(project)
    rows: list[ExecutivePortfolioRow] = []
    for (account_id, organization_id), grouped in groups.items():
        handovers = list(
            db.scalars(
                select(ProjectSupportHandover).where(
                    ProjectSupportHandover.project_id.in_([row.id for row in grouped])
                )
            )
        )
        readiness = [float(row.readiness_percent) for row in handovers]
        rows.append(
            ExecutivePortfolioRow(
                account_id=account_id,
                account_name=account_names.get(account_id, f"Account {account_id}"),
                organization_id=organization_id,
                organization_name=organization_names.get(
                    organization_id, f"Organization {organization_id}"
                ),
                project_count=len(grouped),
                at_risk_count=sum(
                    row.health in {"AT_RISK", "CRITICAL"} for row in grouped
                ),
                average_progress_percent=round(
                    sum(row.progress_percent for row in grouped) / len(grouped), 2
                ),
                handover_count=len(handovers),
                average_readiness_percent=(
                    round(sum(readiness) / len(readiness), 2) if readiness else None
                ),
            )
        )
    return ExecutivePortfolioRead(
        scope=scope,
        total_projects=len(projects),
        total_at_risk=sum(row.health in {"AT_RISK", "CRITICAL"} for row in projects),
        rows=sorted(rows, key=lambda row: (row.account_name, row.organization_name)),
    )


def _task_scope_ids(db: Session, project_ids: list[int], filters: ProjectionFilters) -> list[int]:
    statement = select(ProjectTask.id).where(ProjectTask.project_id.in_(project_ids or [-1]))
    scoped_user_ids: set[int] | None = None
    if filters.team_id is not None:
        scoped_user_ids = set(
            db.scalars(
                select(SupportTeamMember.user_id).where(
                    SupportTeamMember.team_id == filters.team_id
                )
            )
        )
    if filters.user_id is not None:
        scoped_user_ids = (
            {filters.user_id}
            if scoped_user_ids is None
            else scoped_user_ids.intersection({filters.user_id})
        )
    if scoped_user_ids is not None:
        assigned_task_ids = select(ProjectTaskAssignee.task_id).where(
            ProjectTaskAssignee.user_id.in_(scoped_user_ids or {-1})
        )
        statement = statement.where(
            or_(
                ProjectTask.owner_user_id.in_(scoped_user_ids or {-1}),
                ProjectTask.id.in_(assigned_task_ids),
            )
        )
    return list(db.scalars(statement))


def _row(project: CompanyProject, record_type: str, record_id: int, label: str, **values: Any) -> KpiDrilldownRow:
    return KpiDrilldownRow(
        record_type=record_type,
        record_id=record_id,
        project_id=project.id,
        project_number=project.project_number,
        client_id=project.client_id,
        department_id=project.owning_department_id,
        label=label,
        **values,
    )


def _projection(
    definition: ProjectKpiDefinition,
    rows: list[KpiDrilldownRow],
    *,
    numerator: float | None,
    denominator: float | None,
    value: float | None,
    eligible_count: int | None = None,
) -> CalculatedMetric:
    return CalculatedMetric(
        projection=KpiProjectionRead(
            code=definition.code,
            name=definition.name,
            domain=definition.domain,
            status="READY",
            value=round(value, 2) if value is not None else None,
            unit=definition.unit,
            numerator=round(numerator, 2) if numerator is not None else None,
            denominator=round(denominator, 2) if denominator is not None else None,
            eligible_count=len(rows) if eligible_count is None else eligible_count,
            drilldown_count=len(rows),
        ),
        rows=rows,
    )


def _unavailable(definition: ProjectKpiDefinition, reason: str) -> CalculatedMetric:
    return CalculatedMetric(
        projection=KpiProjectionRead(
            code=definition.code,
            name=definition.name,
            domain=definition.domain,
            status="UNAVAILABLE",
            value=None,
            unit=definition.unit,
            numerator=None,
            denominator=None,
            eligible_count=0,
            drilldown_count=0,
            unavailable_reason=reason,
        ),
        rows=[],
    )


def _calculate(
    db: Session,
    definition: ProjectKpiDefinition,
    projects: list[CompanyProject],
    filters: ProjectionFilters,
) -> CalculatedMetric:
    project_map = {row.id: row for row in projects}
    project_ids = list(project_map) or [-1]
    task_ids = _task_scope_ids(db, list(project_map), filters) or [-1]
    start_at, end_at = _date_bounds(filters)
    code = definition.code

    if code in {"MILESTONE_ON_TIME_RATE", "TASK_ON_TIME_RATE"}:
        return _unavailable(
            definition,
            "Authoritative completion timestamp is not stored; updated_at is not accepted as KPI evidence.",
        )
    if code == "PROJECT_ON_TIME_RATE":
        eligible = [row for row in projects if row.planned_end_date is not None]
        rows = []
        on_time = 0
        for project in eligible:
            planned_end = project.planned_end_date
            if planned_end is None:
                continue
            on_time_flag = (
                project.actual_end_date <= planned_end
                if project.actual_end_date
                else planned_end >= filters.period_end
            )
            on_time += int(on_time_flag)
            rows.append(_row(project, "PROJECT", project.id, project.name, numerator_contribution=float(on_time_flag), denominator_contribution=1, measured_value=float(on_time_flag * 100), occurred_at=project.actual_end_date or filters.period_end, status="ON_TIME" if on_time_flag else "OVERDUE"))
        denominator = float(len(eligible))
        value = on_time / denominator * 100 if denominator else None
        return _projection(definition, rows, numerator=float(on_time), denominator=denominator, value=value)
    if code == "AT_RISK_PROJECT_COUNT":
        selected = [row for row in projects if row.health in {"AT_RISK", "CRITICAL"}]
        rows = [_row(row, "PROJECT", row.id, row.name, numerator_contribution=1, measured_value=1, occurred_at=filters.period_end, status=row.health) for row in selected]
        return _projection(definition, rows, numerator=float(len(rows)), denominator=None, value=float(len(rows)))
    if code == "UNPLANNED_EFFORT_PERCENT":
        worklog_scope: list[ColumnElement[bool]] = [ProjectTask.id.in_(task_ids)]
        if filters.user_id is not None:
            worklog_scope.append(ProjectWorkLog.user_id == filters.user_id)
        records = list(db.execute(select(ProjectWorkLog, ProjectTask).join(ProjectTask, ProjectTask.id == ProjectWorkLog.task_id).where(*worklog_scope, ProjectWorkLog.started_at >= start_at, ProjectWorkLog.started_at <= end_at, ProjectWorkLog.duration_minutes.is_not(None))))
        rows = []
        numerator = denominator = 0.0
        for worklog, task in records:
            minutes = float(worklog.duration_minutes or 0)
            contribution = minutes if task.classification == "UNPLANNED" and task.approval_status == "APPROVED" else 0.0
            numerator += contribution
            denominator += minutes
            rows.append(_row(project_map[task.project_id], "WORK_LOG", worklog.id, task.title, numerator_contribution=contribution, denominator_contribution=minutes, measured_value=minutes, occurred_at=worklog.started_at, status=task.classification))
        return _projection(definition, rows, numerator=numerator, denominator=denominator, value=numerator / denominator * 100 if denominator else None)
    if code == "ESTIMATE_ACCURACY_PERCENT":
        tasks = list(db.scalars(select(ProjectTask).where(ProjectTask.id.in_(task_ids), ProjectTask.status.in_(["DONE", "COMPLETED"]), ProjectTask.updated_at >= start_at, ProjectTask.updated_at <= end_at, ProjectTask.estimate_minutes > 0)))
        rows = []
        scores = []
        for task in tasks:
            worklog_query = select(func.coalesce(func.sum(ProjectWorkLog.duration_minutes), 0)).where(ProjectWorkLog.task_id == task.id)
            if filters.user_id is not None:
                worklog_query = worklog_query.where(ProjectWorkLog.user_id == filters.user_id)
            actual = float(db.scalar(worklog_query) or 0)
            if actual <= 0:
                continue
            score = min(float(task.estimate_minutes), actual) / max(float(task.estimate_minutes), actual) * 100
            scores.append(score)
            rows.append(_row(project_map[task.project_id], "TASK", task.id, task.title, numerator_contribution=score, denominator_contribution=1, measured_value=score, occurred_at=task.updated_at, status=task.status))
        return _projection(definition, rows, numerator=sum(scores), denominator=float(len(scores)), value=sum(scores) / len(scores) if scores else None)
    if code == "BLOCKED_TASK_AGING_HOURS":
        records = list(db.execute(select(ProjectTaskBlocker, ProjectTask).join(ProjectTask, ProjectTask.id == ProjectTaskBlocker.task_id).where(ProjectTask.id.in_(task_ids), ProjectTaskBlocker.status == "OPEN", ProjectTaskBlocker.created_at <= end_at)))
        rows = []
        ages = []
        for blocker, task in records:
            created = blocker.created_at.replace(tzinfo=UTC) if blocker.created_at.tzinfo is None else blocker.created_at
            age = max(0.0, (end_at - created).total_seconds() / 3600)
            ages.append(age)
            rows.append(_row(project_map[task.project_id], "BLOCKER", blocker.id, blocker.description, numerator_contribution=age, denominator_contribution=1, measured_value=age, occurred_at=blocker.created_at, status=blocker.status))
        return _projection(definition, rows, numerator=sum(ages), denominator=float(len(ages)), value=sum(ages) / len(ages) if ages else None)
    if code == "FIRST_PASS_REVIEW_RATE":
        reviews = list(db.execute(select(ProjectTaskReview, ProjectTask).join(ProjectTask, ProjectTask.id == ProjectTaskReview.task_id).where(ProjectTask.id.in_(task_ids), ProjectTaskReview.created_at >= start_at, ProjectTaskReview.created_at <= end_at).order_by(ProjectTaskReview.task_id, ProjectTaskReview.created_at, ProjectTaskReview.id)))
        first: dict[int, tuple[ProjectTaskReview, ProjectTask]] = {}
        for review, task in reviews:
            first.setdefault(task.id, (review, task))
        rows = []
        accepted_count = 0
        for review, task in first.values():
            accepted = review.decision in {"ACCEPTED", "APPROVED", "PASS"}
            accepted_count += int(accepted)
            rows.append(_row(project_map[task.project_id], "TASK_REVIEW", review.id, task.title, numerator_contribution=float(accepted), denominator_contribution=1, measured_value=float(accepted * 100), occurred_at=review.created_at, status=review.decision))
        denominator = float(len(rows))
        return _projection(definition, rows, numerator=float(accepted_count), denominator=denominator, value=accepted_count / denominator * 100 if denominator else None)
    if code == "HANDOVER_READINESS_PERCENT":
        records = list(db.execute(select(ProjectHandoverItem, ProjectHandoverSection, ProjectSupportHandover).join(ProjectHandoverSection, ProjectHandoverSection.id == ProjectHandoverItem.section_id).join(ProjectSupportHandover, ProjectSupportHandover.id == ProjectHandoverSection.handover_id).where(ProjectSupportHandover.project_id.in_(project_ids), ProjectHandoverItem.is_required == true())))
        rows = []
        ready_count = 0
        for item, _, handover in records:
            ready_flag = item.status == "READY"
            ready_count += int(ready_flag)
            rows.append(_row(project_map[handover.project_id], "HANDOVER_ITEM", item.id, item.title, numerator_contribution=float(ready_flag), denominator_contribution=1, measured_value=float(ready_flag * 100), occurred_at=item.updated_at, status=item.status))
        denominator = float(len(rows))
        return _projection(definition, rows, numerator=float(ready_count), denominator=denominator, value=ready_count / denominator * 100 if denominator else None)
    if code == "HANDOVER_CYCLE_HOURS":
        handovers = list(db.scalars(select(ProjectSupportHandover).where(ProjectSupportHandover.project_id.in_(project_ids), ProjectSupportHandover.submitted_at.is_not(None), ProjectSupportHandover.activated_at >= start_at, ProjectSupportHandover.activated_at <= end_at)))
        rows = []
        hours = []
        for handover in handovers:
            submitted = handover.submitted_at.replace(tzinfo=UTC) if handover.submitted_at and handover.submitted_at.tzinfo is None else handover.submitted_at
            activated = handover.activated_at.replace(tzinfo=UTC) if handover.activated_at and handover.activated_at.tzinfo is None else handover.activated_at
            if submitted is None or activated is None:
                continue
            duration = max(0.0, (activated - submitted).total_seconds() / 3600)
            hours.append(duration)
            rows.append(_row(project_map[handover.project_id], "HANDOVER", handover.id, "Support handover", numerator_contribution=duration, denominator_contribution=1, measured_value=duration, occurred_at=handover.activated_at, status=handover.status))
        return _projection(definition, rows, numerator=sum(hours), denominator=float(len(hours)), value=sum(hours) / len(hours) if hours else None)
    if code == "OPEN_RESIDUAL_ITEM_COUNT":
        records = list(db.execute(select(ProjectHandoverResidualItem, ProjectSupportHandover).join(ProjectSupportHandover, ProjectSupportHandover.id == ProjectHandoverResidualItem.handover_id).where(ProjectSupportHandover.project_id.in_(project_ids), ProjectHandoverResidualItem.status != "CLOSED")))
        rows = [_row(project_map[handover.project_id], "RESIDUAL_ITEM", item.id, item.description, numerator_contribution=1, measured_value=1, occurred_at=item.target_date, status=item.status) for item, handover in records]
        return _projection(definition, rows, numerator=float(len(rows)), denominator=None, value=float(len(rows)))
    if code == "CROSS_DEPARTMENT_RESPONSE_HOURS":
        requests = list(db.scalars(select(CrossDepartmentRequest).where(CrossDepartmentRequest.project_id.in_(project_ids), CrossDepartmentRequest.responded_at >= start_at, CrossDepartmentRequest.responded_at <= end_at)))
        rows = []
        hours = []
        for request in requests:
            created = request.created_at.replace(tzinfo=UTC) if request.created_at.tzinfo is None else request.created_at
            responded = request.responded_at.replace(tzinfo=UTC) if request.responded_at and request.responded_at.tzinfo is None else request.responded_at
            if responded is None:
                continue
            duration = max(0.0, (responded - created).total_seconds() / 3600)
            hours.append(duration)
            rows.append(_row(project_map[request.project_id], "CROSS_DEPARTMENT_REQUEST", request.id, request.title, numerator_contribution=duration, denominator_contribution=1, measured_value=duration, occurred_at=request.responded_at, status=request.status))
        return _projection(definition, rows, numerator=sum(hours), denominator=float(len(hours)), value=sum(hours) / len(hours) if hours else None)
    return _unavailable(definition, "No approved projection implementation exists for this KPI code.")


def _implementation_self_scope(permissions: list[str]) -> bool:
    return "workspace.implementation.access" in permissions and not any(
        code in permissions for code in ("project.assignment.respond", "analytics.executive.view")
    )


def _dashboard_filters(
    db: Session, actor: User, domain: str, filters: ProjectionFilters,
) -> ProjectionFilters:
    if domain == "IMPLEMENTATION" and _implementation_self_scope(effective_permissions(db, actor).permissions):
        if filters.user_id not in (None, actor.id) or filters.team_id is not None:
            raise AuthorizationError("This Implementation dashboard is scoped to your own work.")
        return replace(filters, user_id=actor.id)
    return filters


def projection(
    db: Session, actor: User, domain: str, filters: ProjectionFilters
) -> AnalyticsProjectionRead:
    normalized = domain.upper()
    if normalized not in DOMAIN_PERMISSIONS:
        raise NotFoundError("Analytics domain does not exist.")
    filters = _dashboard_filters(db, actor, normalized, filters)
    projects, scope = _authorized_projects(db, actor, normalized, filters)
    definitions = list(db.scalars(select(ProjectKpiDefinition).where(ProjectKpiDefinition.domain == normalized, ProjectKpiDefinition.is_active == true()).order_by(ProjectKpiDefinition.code)))
    return AnalyticsProjectionRead(
        domain=normalized,
        period_start=filters.period_start,
        period_end=filters.period_end,
        generated_at=server_now(),
        scope=scope,
        metrics=[_calculate(db, item, projects, filters).projection for item in definitions],
    )


def drilldown(
    db: Session, actor: User, code: str, filters: ProjectionFilters
) -> KpiDrilldownRead:
    definition = db.scalar(select(ProjectKpiDefinition).where(ProjectKpiDefinition.code == code.upper(), ProjectKpiDefinition.is_active == true()))
    if definition is None:
        raise NotFoundError("KPI definition does not exist.")
    filters = _dashboard_filters(db, actor, definition.domain, filters)
    projects, scope = _authorized_projects(db, actor, definition.domain, filters)
    result = _calculate(db, definition, projects, filters)
    return KpiDrilldownRead(projection=result.projection, scope=scope, period_start=filters.period_start, period_end=filters.period_end, rows=result.rows)
