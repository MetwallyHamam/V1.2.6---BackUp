import json
import re
import secrets
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased, load_only

from app.api.dependencies import current_user, require_permission
from app.core.clock import server_now, server_timezone
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import (
    Branch,
    Client,
    ClientLocation,
    Country,
    Product,
    ProductModule,
    SupportTeam,
    SupportTeamMember,
)
from app.modules.contracts.models import Contract, TicketSlaClock
from app.modules.dashboards.models import (
    AgentActivity,
    Dashboard,
    DashboardAssignment,
    DashboardProfileAccess,
    DashboardTab,
    DashboardTabWidget,
    DashboardUserPreference,
    DashboardWidget,
    SavedView,
    TicketGridPreference,
    WidgetDefinition,
)
from app.modules.dashboards.schemas import (
    AccessibleDashboardRead,
    AgentActivityCreate,
    AgentActivityRead,
    AgentKpi,
    AvailableEmployee,
    DashboardAdminPreviewRead,
    DashboardAssignmentCreate,
    DashboardAssignmentImpactRead,
    DashboardAssignmentRead,
    DashboardAssignmentUpdate,
    DashboardConfigRead,
    DashboardConfigUpdate,
    DashboardProfileAccessUpdate,
    DashboardScenarioPreviewRead,
    DashboardSummary,
    DashboardTabRead,
    DashboardTabWidgetRead,
    DashboardTemplateCreate,
    DashboardTemplateRead,
    DashboardTemplateUpdate,
    DashboardWidgetCatalogItem,
    DashboardWidgetConfig,
    OnlineEngineer,
    ProductKpi,
    SavedViewCreate,
    SavedViewRead,
    SavedViewUpdate,
    TicketGridPreferenceData,
    TopSupportAgent,
    TopSupportAgentsRead,
)
from app.modules.dashboards.service import (
    AuthenticatedDashboardScope,
    DashboardTicketFilters,
)
from app.modules.escalations.models import EscalationEvent
from app.modules.finance.models import ContractInvoice
from app.modules.iam.models import (
    AuditLog,
    Department,
    DepartmentMembership,
    Permission,
    Profile,
    ProfilePermission,
    User,
    UserClientScope,
    UserProfile,
    UserReportingLine,
)
from app.modules.iam.service import effective_permissions
from app.modules.internal_operations.models import InternalOperation, InternalOperationAssignee
from app.modules.knowledge_base.models import Article
from app.modules.kpis.models import KpiReview
from app.modules.onboarding.models import UserOnboarding
from app.modules.project_handovers.models import (
    HandoverPendingPoint,
    HandoverProduct,
    HandoverRecipient,
    ProjectHandover,
)
from app.modules.shifts.models import Shift, ShiftType
from app.modules.sla.service import first_dedicated_assignments, resolution_sla_results
from app.modules.tickets.models import (
    Ticket,
    TicketAssignmentHistory,
    TicketFollower,
    TicketStatus,
    TicketStatusHistory,
    TicketTask,
)
from app.modules.tickets.service import visible_ticket_query

router = APIRouter(tags=["dashboards and saved views"])
# Stay below SQL Server's 2,100-parameter ceiling while minimizing round trips.
SQL_ID_BATCH_SIZE = 1900


def _id_batches(values: list[int]) -> list[list[int]]:
    return [
        values[offset : offset + SQL_ID_BATCH_SIZE]
        for offset in range(0, len(values), SQL_ID_BATCH_SIZE)
    ]


DEFAULT_WIDGETS = [
    ("total_open", "Open tickets"),
    ("my_open", "Assigned to me"),
    ("unassigned", "Unassigned"),
    ("critical", "P1 critical"),
    ("breached", "SLA breached"),
    ("due_soon", "Due in four hours"),
    ("shift_handovers", "Shift handovers"),
    ("client_hours", "Client working and saved hours"),
    ("service_incidents", "Incidents"),
    ("service_change_requests", "Change Requests"),
    ("service_problems", "Problems"),
]

WIDGET_CATALOG = [
    ("total_open", "Open tickets", "Current open workload", "KPI_CARD", "total_open", 2),
    ("my_open", "Assigned to me", "Your open workload", "KPI_CARD", "my_open", 2),
    ("unassigned", "Unassigned", "Open tickets awaiting assignment", "KPI_CARD", "unassigned", 2),
    ("critical", "P1 critical", "Open critical-priority tickets", "KPI_CARD", "critical", 2),
    ("breached", "SLA breached", "Tickets that breached SLA", "KPI_CARD", "breached", 2),
    ("due_soon", "Due in four hours", "SLA deadlines approaching", "KPI_CARD", "due_soon", 2),
    (
        "shift_handovers",
        "Shift handovers",
        "Tickets pending between support shifts",
        "KPI_CARD",
        "shift_handovers",
        2,
    ),
    (
        "department_new",
        "New department requests",
        "New routed work visible to you",
        "KPI_CARD",
        "department_new",
        2,
    ),
    (
        "department_in_progress",
        "Department work in progress",
        "Active routed work visible to you",
        "KPI_CARD",
        "department_in_progress",
        2,
    ),
    (
        "department_returned",
        "Returned to Support",
        "Completed department responses visible to you",
        "KPI_CARD",
        "department_returned",
        2,
    ),
    (
        "total_tickets",
        "Total tickets",
        "All tickets visible in the selected scope",
        "KPI_CARD",
        "total_tickets",
        2,
    ),
    ("created_today", "Created today", "Tickets created today", "KPI_CARD", "created_today", 2),
    ("closed_today", "Closed today", "Tickets closed today", "KPI_CARD", "closed_today", 2),
    (
        "status_donut",
        "Tickets by status",
        "Clickable status distribution and total",
        "DONUT",
        "status_distribution",
        6,
    ),
    (
        "priority_status",
        "Priority by status",
        "Priority mix across ticket statuses",
        "STACKED_BAR",
        "priority_status",
        6,
    ),
    (
        "volume_trend",
        "Volume trend",
        "Created versus completed over time",
        "LINE",
        "volume_trend",
        6,
    ),
    (
        "service_health",
        "Service health",
        "SLA compliance, resolution time, reopen rate, and escalations",
        "KPI_CARD",
        "service_health",
        12,
    ),
    (
        "top_support_agents",
        "Top 3 Support agents",
        "Highest-ranked Support agents for the selected period",
        "KPI_CARD",
        "top_support_agents",
        6,
    ),
    (
        "support_consumption",
        "Customers with the Highest Support Consumption",
        "Customers ranked by tickets created in the selected period",
        "STACKED_BAR",
        "support_consumption",
        6,
    ),
    (
        "customer_workhours",
        "Support work hours per customer",
        "Approved ticket worklogs, or completed resolution SLA time when a ticket has no approved worklog, by customer",
        "STACKED_BAR",
        "customer_workhours",
        6,
    ),
    (
        "client_hours",
        "Client working and saved hours",
        "Working hours, resolution SLA target hours, and saved hours per client",
        "STACKED_BAR",
        "client_hours",
        12,
    ),
    (
        "service_incidents",
        "Incidents",
        "Incident records visible in the selected scope",
        "KPI_CARD",
        "service_incidents",
        4,
    ),
    (
        "service_change_requests",
        "Change Requests",
        "Change requests visible in the selected scope",
        "KPI_CARD",
        "service_change_requests",
        4,
    ),
    (
        "service_problems",
        "Problems",
        "Problem investigations visible in the selected scope",
        "KPI_CARD",
        "service_problems",
        4,
    ),
    (
        "financial_contracts",
        "Income and collection trend",
        "Invoiced revenue and collected cash with prior-year comparison",
        "LINE",
        "financial_contracts",
        6,
    ),
    (
        "financial_invoices",
        "Cash contribution by client",
        "Confirmed client cash contribution without implying accounting profit",
        "STACKED_BAR",
        "financial_invoices",
        6,
    ),
    (
        "financial_contract_value",
        "Contract value",
        "Recorded contract value by contract and currency",
        "STACKED_BAR",
        "financial_contract_value",
        6,
    ),
    (
        "financial_contract_expiry",
        "Contract expiry",
        "Upcoming contract expiries with direct contract evidence",
        "STACKED_BAR",
        "financial_contract_expiry",
        6,
    ),
    (
        "financial_discounts",
        "Discounts",
        "Recorded collection discounts by contract and currency",
        "STACKED_BAR",
        "financial_discounts",
        6,
    ),
    (
        "financial_adjustments",
        "Additional adjustments",
        "Recorded additional collection adjustments by contract and currency",
        "STACKED_BAR",
        "financial_adjustments",
        6,
    ),
    (
        "hr_total_employees",
        "Total employees",
        "Employees in the authorized HR scope",
        "KPI_CARD",
        "hr_total_employees",
        2,
    ),
    (
        "hr_active_employees",
        "Active employees",
        "Active employees in the authorized HR scope",
        "KPI_CARD",
        "hr_active_employees",
        2,
    ),
    (
        "hr_inactive_employees",
        "Inactive employees",
        "Inactive employees in the authorized HR scope",
        "KPI_CARD",
        "hr_inactive_employees",
        2,
    ),
    (
        "hr_departments",
        "Departments",
        "Active organization departments",
        "KPI_CARD",
        "hr_departments",
        2,
    ),
    (
        "hr_head_vacancies",
        "Head vacancies",
        "Active departments without an assigned head",
        "KPI_CARD",
        "hr_head_vacancies",
        2,
    ),
    (
        "hr_reporting_exceptions",
        "Reporting-line exceptions",
        "Active employees without a current reporting line",
        "KPI_CARD",
        "hr_reporting_exceptions",
        2,
    ),
    (
        "hr_kpi_pending",
        "KPI reviews pending",
        "KPI reviews not yet finalized in the selected period",
        "KPI_CARD",
        "hr_kpi_pending",
        2,
    ),
    (
        "hr_kpi_finalized",
        "KPI reviews finalized",
        "Finalized KPI reviews in the selected period",
        "KPI_CARD",
        "hr_kpi_finalized",
        2,
    ),
    (
        "hr_onboarding_in_progress",
        "Onboarding in progress",
        "Active employee onboarding programs",
        "KPI_CARD",
        "hr_onboarding_in_progress",
        2,
    ),
    (
        "hr_unscheduled_employees",
        "Unscheduled employees",
        "Active shift participants without a current or upcoming shift",
        "KPI_CARD",
        "hr_unscheduled_employees",
        2,
    ),
    (
        "project_total",
        "Total projects",
        "Project handovers visible to the current user",
        "KPI_CARD",
        "project_total",
        2,
    ),
    (
        "project_delivered",
        "Delivered projects",
        "Visible projects marked delivered or accepted",
        "KPI_CARD",
        "project_delivered",
        2,
    ),
    (
        "project_in_progress",
        "Projects in progress",
        "Visible projects not yet delivered",
        "KPI_CARD",
        "project_in_progress",
        2,
    ),
    (
        "project_awaiting_acceptance",
        "Awaiting acceptance",
        "Delivered projects with an unaccepted recipient",
        "KPI_CARD",
        "project_awaiting_acceptance",
        2,
    ),
    (
        "project_pending_products",
        "Pending products",
        "Pending or held product delivery rows",
        "KPI_CARD",
        "project_pending_products",
        2,
    ),
    (
        "project_pending_points",
        "Open pending points",
        "Unresolved structured pending points in visible projects",
        "KPI_CARD",
        "project_pending_points",
        2,
    ),
    (
        "projects_by_status",
        "Projects by status",
        "Visible project handovers grouped by lifecycle status",
        "DONUT",
        "projects_by_status",
        6,
    ),
    (
        "projects_by_client",
        "Projects by client",
        "Visible project handovers grouped by client",
        "STACKED_BAR",
        "projects_by_client",
        6,
    ),
]
CATALOG_BY_CODE = {item[0]: item for item in WIDGET_CATALOG}
WIDGET_REQUIRED_PERMISSIONS: dict[str, frozenset[str]] = {
    "service_change_requests": frozenset({"change_request.view"}),
    "service_problems": frozenset({"problem.view"}),
    "financial_contracts": frozenset({"finance.dashboard.view"}),
    "financial_invoices": frozenset({"finance.dashboard.view"}),
    "financial_contract_value": frozenset({"finance.dashboard.view"}),
    "financial_contract_expiry": frozenset({"finance.dashboard.view"}),
    "financial_discounts": frozenset({"finance.dashboard.view"}),
    "financial_adjustments": frozenset({"finance.dashboard.view"}),
    **{
        code: frozenset({"kpi.view.all"})
        for code in (
            "hr_total_employees",
            "hr_active_employees",
            "hr_inactive_employees",
            "hr_departments",
            "hr_head_vacancies",
            "hr_reporting_exceptions",
            "hr_kpi_pending",
            "hr_kpi_finalized",
            "hr_onboarding_in_progress",
            "hr_unscheduled_employees",
        )
    },
    **{
        code: frozenset({"project_handover.view"})
        for code in (
            "project_total",
            "project_delivered",
            "project_in_progress",
            "project_awaiting_acceptance",
            "project_pending_products",
            "project_pending_points",
            "projects_by_status",
            "projects_by_client",
        )
    },
}


@router.get("/dashboards/filter-metadata")
def dashboard_filter_metadata(
    db: Session = Depends(get_db), user: User = Depends(current_user)
) -> dict[str, object]:
    permissions = set(effective_permissions(db, user).permissions)
    if not ({"dashboard.agent", "dashboard.manager"} & permissions):
        raise AuthorizationError()
    visible = (
        AuthenticatedDashboardScope(db, user).ticket_query().subquery("visible_dashboard_tickets")
    )
    # Resolve the expensive permission-filtered ticket scope once. Previously it
    # was embedded independently in every dimension query, making SQL Server
    # repeat the same authorization joins up to eight times per dashboard load.
    metadata_branch_location = aliased(ClientLocation)
    metadata_client_location = aliased(ClientLocation)
    dimension_rows = db.execute(
        select(
            visible.c.client_id,
            visible.c.product_id,
            visible.c.assigned_user_id,
            visible.c.routed_team_id,
            visible.c.assigned_team,
            func.coalesce(metadata_branch_location.id, metadata_client_location.id).label(
                "location_id"
            ),
            func.coalesce(
                metadata_branch_location.country_id,
                metadata_client_location.country_id,
                Client.country_id,
            ).label("country_id"),
            func.coalesce(
                metadata_branch_location.zone, metadata_client_location.zone, Client.zone
            ).label("zone"),
        )
        .select_from(visible)
        .join(Client, Client.id == visible.c.client_id)
        .outerjoin(Branch, Branch.id == visible.c.branch_id)
        .outerjoin(metadata_branch_location, metadata_branch_location.id == Branch.location_id)
        .outerjoin(
            metadata_client_location, metadata_client_location.id == Client.primary_location_id
        )
        .distinct()
    ).all()
    client_ids = {row.client_id for row in dimension_rows if row.client_id is not None}
    product_ids = {row.product_id for row in dimension_rows if row.product_id is not None}
    engineer_ids = {
        row.assigned_user_id for row in dimension_rows if row.assigned_user_id is not None
    }
    routed_team_ids = {
        row.routed_team_id for row in dimension_rows if row.routed_team_id is not None
    }
    assigned_team_names = {
        row.assigned_team for row in dimension_rows if row.assigned_team is not None
    }
    location_ids = {row.location_id for row in dimension_rows if row.location_id is not None}
    country_ids = {row.country_id for row in dimension_rows if row.country_id is not None}
    zones = {row.zone for row in dimension_rows if row.zone is not None}
    clients = list(
        db.scalars(
            select(Client)
            .where(Client.id.in_(client_ids or {-1}), Client.is_active.in_([True]))
            .order_by(Client.name)
        )
    )
    locations = list(
        db.scalars(
            select(ClientLocation)
            .where(
                ClientLocation.id.in_(location_ids or {-1}),
                ClientLocation.is_active.in_([True]),
            )
            .order_by(ClientLocation.name)
        )
    )
    return {
        "countries": [
            {"id": item.id, "name": item.name}
            for item in db.scalars(
                select(Country)
                .where(Country.id.in_(country_ids or [-1]), Country.is_active.in_([True]))
                .order_by(Country.name)
            )
        ],
        "zones": sorted(zones),
        "clients": [{"id": item.id, "name": item.name} for item in clients],
        "locations": [
            {"id": item.id, "client_id": item.client_id, "name": item.name} for item in locations
        ],
        "products": [
            {"id": item.id, "name": item.name}
            for item in db.scalars(
                select(Product)
                .where(Product.id.in_(product_ids or {-1}), Product.is_active.in_([True]))
                .order_by(Product.name)
            )
        ],
        "teams": [
            {"id": item.id, "name": item.name}
            for item in db.scalars(
                select(SupportTeam)
                .where(
                    or_(
                        SupportTeam.id.in_(routed_team_ids or {-1}),
                        SupportTeam.name.in_(assigned_team_names or {""}),
                    ),
                    SupportTeam.is_active.in_([True]),
                )
                .order_by(SupportTeam.name)
            )
        ],
        "engineers": [
            {"id": item.id, "name": item.full_name}
            for item in db.scalars(
                select(User)
                .where(
                    User.id.in_(engineer_ids or {-1}),
                    User.is_active.in_([True]),
                    User.user_type == "EMPLOYEE",
                )
                .order_by(User.full_name)
            )
        ],
    }


def dashboard_read(
    dashboard: Dashboard,
    widgets: list[DashboardWidget],
    source: str,
    assignment: DashboardAssignment | None = None,
    explanation: str | None = None,
) -> DashboardConfigRead:
    return DashboardConfigRead(
        source=source,
        name=dashboard.name,
        template_code=dashboard.code,
        template_version=dashboard.version,
        assignment_id=assignment.id if assignment else None,
        resolution_explanation=explanation,
        widgets=[
            DashboardWidgetConfig(
                widget_code=item.widget_code,
                title=item.title,
                widget_type=item.widget_type,
                query_code=item.query_code,
                position=item.position,
                width=item.width,
                refresh_seconds=item.refresh_seconds,
                config=json.loads(item.config_json or "{}"),
            )
            for item in widgets
        ],
    )


def _primary_profile(db: Session, user_id: int) -> Profile | None:
    return db.scalar(
        select(Profile)
        .join(UserProfile, UserProfile.profile_id == Profile.id)
        .where(
            UserProfile.user_id == user_id,
            UserProfile.is_primary.in_([True]),
            UserProfile.is_active.in_([True]),
            Profile.is_active.in_([True]),
        )
    )


def _effective_department_id(db: Session, user: User, at: datetime) -> int | None:
    membership = db.scalar(
        select(DepartmentMembership)
        .where(
            DepartmentMembership.user_id == user.id,
            DepartmentMembership.is_primary.in_([True]),
            DepartmentMembership.effective_from <= at.date(),
            or_(
                DepartmentMembership.effective_until.is_(None),
                DepartmentMembership.effective_until >= at.date(),
            ),
        )
        .order_by(DepartmentMembership.effective_from.desc(), DepartmentMembership.id.desc())
    )
    return membership.department_id if membership else user.department_id


def _resolved_assignment(
    db: Session,
    user: User,
    primary_profile: Profile | None,
    at: datetime,
    *,
    include_user: bool = True,
    dashboard_type: Literal["EXECUTIVE", "TOP_MANAGEMENT"] = "EXECUTIVE",
) -> tuple[DashboardAssignment, Dashboard, str, str] | None:
    department_id = _effective_department_id(db, user, at)
    rows = db.execute(
        select(DashboardAssignment, Dashboard)
        .join(Dashboard, Dashboard.id == DashboardAssignment.dashboard_id)
        .where(
            DashboardAssignment.is_active.in_([True]),
            DashboardAssignment.is_personal.in_([False]),
            Dashboard.is_active.in_([True]),
            DashboardAssignment.dashboard_type == dashboard_type,
            Dashboard.destination == dashboard_type,
            or_(
                DashboardAssignment.effective_from.is_(None),
                DashboardAssignment.effective_from <= at,
            ),
            or_(
                DashboardAssignment.effective_until.is_(None),
                DashboardAssignment.effective_until > at,
            ),
        )
    ).all()
    ranked: list[tuple[int, int, DashboardAssignment, Dashboard, str, str]] = []
    for assignment, dashboard in rows:
        if (
            include_user
            and assignment.user_id == user.id
            and assignment.profile_id is None
            and assignment.department_id is None
        ):
            rank, source, reason = 5, "USER", "Active user-specific assignment"
        elif (
            primary_profile
            and department_id
            and assignment.user_id is None
            and assignment.profile_id == primary_profile.id
            and assignment.department_id == department_id
        ):
            rank, source, reason = (
                4,
                "PROFILE_DEPARTMENT",
                "Primary profile and department assignment",
            )
        elif (
            primary_profile
            and assignment.user_id is None
            and assignment.department_id is None
            and assignment.profile_id == primary_profile.id
        ):
            rank, source, reason = 3, "PROFILE", "Primary profile assignment"
        elif (
            department_id
            and assignment.user_id is None
            and assignment.profile_id is None
            and assignment.department_id == department_id
        ):
            rank, source, reason = 2, "DEPARTMENT", "Department default assignment"
        elif (
            assignment.user_id is None
            and assignment.profile_id is None
            and assignment.department_id is None
        ):
            rank, source, reason = 1, "SYSTEM", "System default assignment"
        else:
            continue
        ranked.append((rank, assignment.priority, assignment, dashboard, source, reason))
    if not ranked:
        return None
    ranked.sort(key=lambda item: (item[0], item[1], item[2].id), reverse=True)
    winner = ranked[0]
    if len(ranked) > 1 and ranked[1][:2] == winner[:2]:
        raise ConflictError(
            "AMBIGUOUS_DASHBOARD_ASSIGNMENT",
            f"Multiple active {winner[4]} dashboard assignments have the same priority.",
        )
    return winner[2], winner[3], winner[4], winner[5]


def _resolved_scenario_assignment(
    db: Session,
    profile_id: int | None,
    department_id: int | None,
    at: datetime,
    dashboard_type: Literal["EXECUTIVE", "TOP_MANAGEMENT"] = "EXECUTIVE",
) -> tuple[DashboardAssignment, Dashboard, str, str] | None:
    rows = db.execute(
        select(DashboardAssignment, Dashboard)
        .join(Dashboard, Dashboard.id == DashboardAssignment.dashboard_id)
        .where(
            DashboardAssignment.is_active.in_([True]),
            DashboardAssignment.is_personal.in_([False]),
            Dashboard.is_active.in_([True]),
            DashboardAssignment.dashboard_type == dashboard_type,
            Dashboard.destination == dashboard_type,
            or_(
                DashboardAssignment.effective_from.is_(None),
                DashboardAssignment.effective_from <= at,
            ),
            or_(
                DashboardAssignment.effective_until.is_(None),
                DashboardAssignment.effective_until > at,
            ),
            DashboardAssignment.user_id.is_(None),
        )
    ).all()
    ranked = []
    for assignment, dashboard in rows:
        if (
            profile_id
            and department_id
            and assignment.profile_id == profile_id
            and assignment.department_id == department_id
        ):
            rank, source, reason = (
                4,
                "PROFILE_DEPARTMENT",
                "Profile and department scenario assignment",
            )
        elif (
            profile_id and assignment.profile_id == profile_id and assignment.department_id is None
        ):
            rank, source, reason = 3, "PROFILE", "Profile scenario assignment"
        elif (
            department_id
            and assignment.profile_id is None
            and assignment.department_id == department_id
        ):
            rank, source, reason = 2, "DEPARTMENT", "Department scenario assignment"
        elif assignment.profile_id is None and assignment.department_id is None:
            rank, source, reason = 1, "SYSTEM", "System default assignment"
        else:
            continue
        ranked.append((rank, assignment.priority, assignment, dashboard, source, reason))
    if not ranked:
        return None
    ranked.sort(key=lambda item: (item[0], item[1], item[2].id), reverse=True)
    return ranked[0][2], ranked[0][3], ranked[0][4], ranked[0][5]


def _authorized_widgets(
    widgets: list[DashboardWidget], permissions: set[str]
) -> list[DashboardWidget]:
    return [
        item
        for item in widgets
        if WIDGET_REQUIRED_PERMISSIONS.get(item.widget_code, frozenset()) <= permissions
    ]


def _validate_widget_config(items: list[DashboardWidgetConfig]) -> None:
    if len({item.widget_code for item in items}) != len(items):
        raise ConflictError(
            "DUPLICATE_DASHBOARD_WIDGET",
            "A template cannot contain the same widget more than once.",
        )
    if len({item.position for item in items}) != len(items):
        raise ConflictError(
            "DUPLICATE_DASHBOARD_POSITION", "Every widget must have a distinct position."
        )
    for item in items:
        catalog_item = CATALOG_BY_CODE.get(item.widget_code)
        if (
            not catalog_item
            or item.query_code != catalog_item[4]
            or item.widget_type != catalog_item[3]
        ):
            raise ConflictError(
                "INVALID_DASHBOARD_WIDGET", f"Unsupported dashboard widget: {item.widget_code}"
            )
        if item.config:
            raise ConflictError(
                "INVALID_DASHBOARD_WIDGET_CONFIG",
                f"Widget {item.widget_code} does not define configurable query options.",
            )


def _replace_widgets(db: Session, dashboard_id: int, items: list[DashboardWidgetConfig]) -> None:
    _validate_widget_config(items)
    db.query(DashboardWidget).filter(DashboardWidget.dashboard_id == dashboard_id).delete()
    db.add_all(
        DashboardWidget(
            dashboard_id=dashboard_id,
            widget_code=item.widget_code,
            title=item.title,
            widget_type=item.widget_type,
            query_code=item.query_code,
            position=item.position,
            width=item.width,
            refresh_seconds=item.refresh_seconds,
            config_json=json.dumps(item.config),
        )
        for item in items
    )


def _template_read(db: Session, item: Dashboard) -> DashboardTemplateRead:
    widgets = list(
        db.scalars(
            select(DashboardWidget)
            .where(DashboardWidget.dashboard_id == item.id, DashboardWidget.is_active.in_([True]))
            .order_by(DashboardWidget.position)
        )
    )
    return DashboardTemplateRead(
        id=item.id,
        code=item.code,
        name=item.name,
        description=item.description,
        destination=item.destination,
        version=item.version,
        is_active=item.is_active,
        widgets=[
            DashboardWidgetConfig(
                widget_code=row.widget_code,
                title=row.title,
                widget_type=row.widget_type,
                query_code=row.query_code,
                position=row.position,
                width=row.width,
                refresh_seconds=row.refresh_seconds,
                config=json.loads(row.config_json or "{}"),
            )
            for row in widgets
        ],
    )


def _periods_overlap(
    left_from: datetime | None,
    left_until: datetime | None,
    right_from: datetime | None,
    right_until: datetime | None,
) -> bool:
    return (left_until is None or right_from is None or right_from < left_until) and (
        right_until is None or left_from is None or left_from < right_until
    )


def _ensure_unambiguous_assignment(
    db: Session, candidate: DashboardAssignment, exclude_id: int | None = None
) -> None:
    if candidate.is_active is False:
        return
    rows = db.scalars(
        select(DashboardAssignment).where(
            DashboardAssignment.is_active.in_([True]),
            DashboardAssignment.user_id.is_(candidate.user_id)
            if candidate.user_id is None
            else DashboardAssignment.user_id == candidate.user_id,
            DashboardAssignment.profile_id.is_(candidate.profile_id)
            if candidate.profile_id is None
            else DashboardAssignment.profile_id == candidate.profile_id,
            DashboardAssignment.department_id.is_(candidate.department_id)
            if candidate.department_id is None
            else DashboardAssignment.department_id == candidate.department_id,
            DashboardAssignment.priority == candidate.priority,
            DashboardAssignment.dashboard_type == candidate.dashboard_type,
        )
    )
    for row in rows:
        if row.id != exclude_id and _periods_overlap(
            row.effective_from,
            row.effective_until,
            candidate.effective_from,
            candidate.effective_until,
        ):
            raise ConflictError(
                "AMBIGUOUS_DASHBOARD_ASSIGNMENT",
                "An active assignment with the same target, priority, and overlapping period already exists.",
            )


@router.get("/dashboards/admin/templates", response_model=list[DashboardTemplateRead])
def list_dashboard_templates(
    destination: Literal["EXECUTIVE", "TOP_MANAGEMENT"] | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("dashboard.manage_widgets")),
) -> list[DashboardTemplateRead]:
    statement = select(Dashboard)
    if destination:
        statement = statement.where(Dashboard.destination == destination)
    return [_template_read(db, item) for item in db.scalars(statement.order_by(Dashboard.name))]


@router.post(
    "/dashboards/admin/templates",
    response_model=DashboardTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
def create_dashboard_template(
    data: DashboardTemplateCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("dashboard.manage_widgets")),
) -> DashboardTemplateRead:
    _validate_widget_config(data.widgets)
    if db.scalar(select(Dashboard.id).where(Dashboard.code == data.code)):
        raise ConflictError(
            "DUPLICATE_DASHBOARD_CODE", "A dashboard template with this code already exists."
        )
    item = Dashboard(
        name=data.name,
        code=data.code,
        description=data.description,
        destination=data.destination,
        assignment_type="TEMPLATE",
        assignment_id=secrets.randbelow(9_000_000_000_000_000_000) + 1,
    )
    db.add(item)
    db.flush()
    _replace_widgets(db, item.id, data.widgets)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Dashboard",
            entity_id=str(item.id),
            action="dashboard.template.created",
            new_values_json=json.dumps(data.model_dump(mode="json")),
        )
    )
    db.commit()
    db.refresh(item)
    return _template_read(db, item)


@router.patch("/dashboards/admin/templates/{dashboard_id}", response_model=DashboardTemplateRead)
def update_dashboard_template(
    dashboard_id: int,
    data: DashboardTemplateUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("dashboard.manage_widgets")),
) -> DashboardTemplateRead:
    item = db.get(Dashboard, dashboard_id)
    if not item:
        raise NotFoundError("Dashboard template does not exist.")
    if item.version != data.expected_version:
        raise ConflictError(
            "STALE_DASHBOARD_TEMPLATE", "The dashboard template changed; refresh and retry."
        )
    before = _template_read(db, item).model_dump(mode="json")
    changes = data.model_dump(exclude_unset=True, exclude={"expected_version", "widgets"})
    for field, value in changes.items():
        setattr(item, field, value)
    if data.widgets is not None:
        _replace_widgets(db, item.id, data.widgets)
    item.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Dashboard",
            entity_id=str(item.id),
            action="dashboard.template.updated",
            old_values_json=json.dumps(before),
            new_values_json=json.dumps(data.model_dump(mode="json")),
        )
    )
    db.commit()
    db.refresh(item)
    return _template_read(db, item)


@router.post(
    "/dashboards/admin/templates/{dashboard_id}/clone",
    response_model=DashboardTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
def clone_dashboard_template(
    dashboard_id: int,
    code: str = Query(pattern=r"^[A-Z0-9_]{2,80}$"),
    name: str = Query(min_length=2, max_length=150),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("dashboard.manage_widgets")),
) -> DashboardTemplateRead:
    source = db.get(Dashboard, dashboard_id)
    if not source:
        raise NotFoundError("Dashboard template does not exist.")
    if db.scalar(select(Dashboard.id).where(Dashboard.code == code)):
        raise ConflictError(
            "DUPLICATE_DASHBOARD_CODE", "A dashboard template with this code already exists."
        )
    clone = Dashboard(
        name=name,
        code=code,
        description=source.description,
        destination=source.destination,
        assignment_type="TEMPLATE",
        assignment_id=secrets.randbelow(9_000_000_000_000_000_000) + 1,
    )
    db.add(clone)
    db.flush()
    source_widgets = list(
        db.scalars(
            select(DashboardWidget)
            .where(DashboardWidget.dashboard_id == source.id)
            .order_by(DashboardWidget.position)
        )
    )
    db.add_all(
        DashboardWidget(
            dashboard_id=clone.id,
            widget_code=row.widget_code,
            title=row.title,
            widget_type=row.widget_type,
            query_code=row.query_code,
            position=row.position,
            width=row.width,
            refresh_seconds=row.refresh_seconds,
            config_json=row.config_json,
            is_active=row.is_active,
        )
        for row in source_widgets
    )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Dashboard",
            entity_id=str(clone.id),
            action="dashboard.template.cloned",
            new_values_json=json.dumps({"source_id": source.id, "code": code, "name": name}),
        )
    )
    db.commit()
    db.refresh(clone)
    return _template_read(db, clone)


@router.get("/dashboards/admin/assignments", response_model=list[DashboardAssignmentRead])
def list_dashboard_assignments(
    db: Session = Depends(get_db), _: User = Depends(require_permission("dashboard.manage_widgets"))
) -> list[DashboardAssignment]:
    return list(db.scalars(select(DashboardAssignment).order_by(DashboardAssignment.id)))


@router.get(
    "/dashboards/admin/assignment-impact", response_model=list[DashboardAssignmentImpactRead]
)
def dashboard_assignment_impact(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("dashboard.manage_widgets")),
) -> list[DashboardAssignmentImpactRead]:
    """Count effective users per winning assignment in one set-based query."""
    now = server_now()
    primary_profile_id = (
        select(UserProfile.profile_id)
        .where(
            UserProfile.user_id == User.id,
            UserProfile.is_primary.in_([True]),
            UserProfile.is_active.in_([True]),
        )
        .order_by(UserProfile.id.desc())
        .limit(1)
        .correlate(User)
        .scalar_subquery()
    )
    effective_department_id = (
        select(DepartmentMembership.department_id)
        .where(
            DepartmentMembership.user_id == User.id,
            DepartmentMembership.is_primary.in_([True]),
            DepartmentMembership.effective_from <= now.date(),
            or_(
                DepartmentMembership.effective_until.is_(None),
                DepartmentMembership.effective_until >= now.date(),
            ),
        )
        .order_by(DepartmentMembership.effective_from.desc(), DepartmentMembership.id.desc())
        .limit(1)
        .correlate(User)
        .scalar_subquery()
    )
    department_id = func.coalesce(effective_department_id, User.department_id)
    match_rank = case(
        (
            and_(
                DashboardAssignment.user_id == User.id,
                DashboardAssignment.profile_id.is_(None),
                DashboardAssignment.department_id.is_(None),
            ),
            5,
        ),
        (
            and_(
                DashboardAssignment.user_id.is_(None),
                DashboardAssignment.profile_id == primary_profile_id,
                DashboardAssignment.department_id == department_id,
            ),
            4,
        ),
        (
            and_(
                DashboardAssignment.user_id.is_(None),
                DashboardAssignment.profile_id == primary_profile_id,
                DashboardAssignment.department_id.is_(None),
            ),
            3,
        ),
        (
            and_(
                DashboardAssignment.user_id.is_(None),
                DashboardAssignment.profile_id.is_(None),
                DashboardAssignment.department_id == department_id,
            ),
            2,
        ),
        (
            and_(
                DashboardAssignment.user_id.is_(None),
                DashboardAssignment.profile_id.is_(None),
                DashboardAssignment.department_id.is_(None),
            ),
            1,
        ),
        else_=0,
    )
    candidates = (
        select(
            User.id.label("user_id"),
            DashboardAssignment.id.label("assignment_id"),
            func.row_number()
            .over(
                partition_by=(User.id, DashboardAssignment.dashboard_type),
                order_by=(
                    match_rank.desc(),
                    DashboardAssignment.priority.desc(),
                    DashboardAssignment.id.desc(),
                ),
            )
            .label("winner"),
        )
        .select_from(User)
        .join(DashboardAssignment, match_rank > 0)
        .join(Dashboard, Dashboard.id == DashboardAssignment.dashboard_id)
        .where(
            User.is_active.in_([True]),
            DashboardAssignment.is_active.in_([True]),
            DashboardAssignment.is_personal.in_([False]),
            Dashboard.is_active.in_([True]),
            or_(
                DashboardAssignment.effective_from.is_(None),
                DashboardAssignment.effective_from <= now,
            ),
            or_(
                DashboardAssignment.effective_until.is_(None),
                DashboardAssignment.effective_until > now,
            ),
        )
        .subquery("dashboard_assignment_candidates")
    )
    counts: dict[int, int] = {
        int(assignment_id): int(affected_user_count)
        for assignment_id, affected_user_count in db.execute(
            select(candidates.c.assignment_id, func.count())
            .where(candidates.c.winner == 1)
            .group_by(candidates.c.assignment_id)
        )
    }
    assignment_ids = list(db.scalars(select(DashboardAssignment.id)))
    return [
        DashboardAssignmentImpactRead(assignment_id=item, affected_user_count=counts.get(item, 0))
        for item in assignment_ids
    ]


@router.post(
    "/dashboards/admin/assignments",
    response_model=DashboardAssignmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_dashboard_assignment(
    data: DashboardAssignmentCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("dashboard.manage_widgets")),
) -> DashboardAssignment:
    dashboard = db.get(Dashboard, data.dashboard_id)
    if not dashboard:
        raise NotFoundError("Dashboard template does not exist.")
    if dashboard.destination != data.dashboard_type:
        raise ConflictError(
            "DASHBOARD_DESTINATION_MISMATCH",
            "The template belongs to a different dashboard destination. Clone it for the selected destination first.",
        )
    if data.profile_id and not db.get(Profile, data.profile_id):
        raise NotFoundError("Profile does not exist.")
    if data.user_id and not db.get(User, data.user_id):
        raise NotFoundError("User does not exist.")
    from app.modules.iam.models import Department

    if data.department_id and not db.get(Department, data.department_id):
        raise NotFoundError("Department does not exist.")
    item = DashboardAssignment(**data.model_dump())
    _ensure_unambiguous_assignment(db, item)
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="DashboardAssignment",
            entity_id=str(item.id),
            action="dashboard.assignment.created",
            new_values_json=json.dumps(data.model_dump(mode="json")),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.patch(
    "/dashboards/admin/assignments/{assignment_id}", response_model=DashboardAssignmentRead
)
def update_dashboard_assignment(
    assignment_id: int,
    data: DashboardAssignmentUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("dashboard.manage_widgets")),
) -> DashboardAssignment:
    item = db.get(DashboardAssignment, assignment_id)
    if not item:
        raise NotFoundError("Dashboard assignment does not exist.")
    if item.version != data.expected_version:
        raise ConflictError(
            "STALE_DASHBOARD_ASSIGNMENT", "The dashboard assignment changed; refresh and retry."
        )
    before = {
        column: getattr(item, column)
        for column in ("priority", "effective_from", "effective_until", "is_active", "version")
    }
    for field, value in data.model_dump(exclude_unset=True, exclude={"expected_version"}).items():
        setattr(item, field, value)
    if item.effective_from and item.effective_until and item.effective_until <= item.effective_from:
        raise ConflictError(
            "INVALID_DASHBOARD_PERIOD", "The assignment end must be after its start."
        )
    _ensure_unambiguous_assignment(db, item, item.id)
    item.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="DashboardAssignment",
            entity_id=str(item.id),
            action="dashboard.assignment.updated",
            old_values_json=json.dumps(before, default=str),
            new_values_json=json.dumps(data.model_dump(mode="json")),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/dashboards/widget-catalog", response_model=list[DashboardWidgetCatalogItem])
def widget_catalog(
    db: Session = Depends(get_db), user: User = Depends(current_user)
) -> list[DashboardWidgetCatalogItem]:
    permissions = set(effective_permissions(db, user).permissions)
    can_manage = "dashboard.manage_widgets" in permissions
    return [
        DashboardWidgetCatalogItem(
            widget_code=code,
            title=title,
            description=description,
            widget_type=widget_type,
            query_code=query_code,
            default_width=width,
            required_permissions=sorted(WIDGET_REQUIRED_PERMISSIONS.get(code, frozenset())),
        )
        for code, title, description, widget_type, query_code, width in WIDGET_CATALOG
        if can_manage or WIDGET_REQUIRED_PERMISSIONS.get(code, frozenset()) <= permissions
    ]


def _accessible_dashboard_read(
    db: Session, dashboard: Dashboard, is_default: bool
) -> AccessibleDashboardRead:
    tabs: list[DashboardTabRead] = []
    for tab in db.scalars(
        select(DashboardTab)
        .where(DashboardTab.dashboard_id == dashboard.id, DashboardTab.is_active.in_([True]))
        .order_by(DashboardTab.display_order, DashboardTab.id)
    ):
        placements = db.execute(
            select(DashboardTabWidget, WidgetDefinition)
            .join(WidgetDefinition, WidgetDefinition.id == DashboardTabWidget.widget_id)
            .where(DashboardTabWidget.dashboard_tab_id == tab.id)
            .order_by(DashboardTabWidget.display_order, DashboardTabWidget.id)
        ).all()
        tabs.append(
            DashboardTabRead(
                id=tab.id,
                code=tab.code,
                name=tab.name,
                description=tab.description,
                display_order=tab.display_order,
                widgets=[
                    DashboardTabWidgetRead(
                        assignment_id=placement.id,
                        widget_id=definition.id,
                        code=definition.code,
                        name=definition.name,
                        description=definition.description,
                        category=definition.category,
                        component_key=definition.component_key,
                        source_type=definition.source_type,
                        display_order=placement.display_order,
                        width=placement.width,
                        height=placement.height,
                        is_visible=placement.is_visible,
                        configuration=json.loads(placement.configuration_json or "{}"),
                    )
                    for placement, definition in placements
                    if definition.is_active
                ],
            )
        )
    return AccessibleDashboardRead(
        id=dashboard.id,
        code=dashboard.code,
        name=dashboard.name,
        description=dashboard.description,
        scope="EXECUTIVE" if dashboard.destination == "TOP_MANAGEMENT" else "OPERATIONAL",
        is_default=is_default,
        tabs=tabs,
    )


@router.get("/dashboards/available", response_model=list[AccessibleDashboardRead])
def available_dashboards(
    db: Session = Depends(get_db), user: User = Depends(current_user)
) -> list[AccessibleDashboardRead]:
    """Return only dashboards explicitly granted to the user's primary profile."""
    profile = _primary_profile(db, user.id)
    if not profile:
        return []
    rows = db.execute(
        select(DashboardProfileAccess, Dashboard)
        .join(Dashboard, Dashboard.id == DashboardProfileAccess.dashboard_id)
        .where(
            DashboardProfileAccess.profile_id == profile.id,
            DashboardProfileAccess.is_active.in_([True]),
            DashboardProfileAccess.can_view.in_([True]),
            Dashboard.is_active.in_([True]),
        )
        .order_by(DashboardProfileAccess.is_default.desc(), Dashboard.name)
    ).all()
    return [
        _accessible_dashboard_read(db, dashboard, access.is_default) for access, dashboard in rows
    ]


@router.get("/dashboards/default", response_model=AccessibleDashboardRead)
def default_dashboard(
    db: Session = Depends(get_db), user: User = Depends(current_user)
) -> AccessibleDashboardRead:
    dashboards = available_dashboards(db, user)
    default = next((item for item in dashboards if item.is_default), None)
    if not default:
        raise ConflictError(
            "DASHBOARD_DEFAULT_REQUIRED",
            "Your profile does not have exactly one active default dashboard. Contact an administrator.",
        )
    return default


@router.put(
    "/dashboards/admin/profile-access/{profile_id}", response_model=list[AccessibleDashboardRead]
)
def replace_profile_dashboard_access(
    profile_id: int,
    data: list[DashboardProfileAccessUpdate],
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("dashboard.manage_widgets")),
) -> list[AccessibleDashboardRead]:
    if not db.get(Profile, profile_id):
        raise NotFoundError("Profile does not exist.")
    active_defaults = [
        item for item in data if item.is_active and item.can_view and item.is_default
    ]
    if len(active_defaults) != 1:
        raise ConflictError(
            "DASHBOARD_DEFAULT_REQUIRED",
            "Every profile must have exactly one active default dashboard.",
        )
    if len({item.dashboard_id for item in data}) != len(data):
        raise ConflictError(
            "DUPLICATE_DASHBOARD_ACCESS", "A dashboard can only be assigned once to a profile."
        )
    dashboards = {
        item.id: item
        for item in db.scalars(
            select(Dashboard).where(
                Dashboard.id.in_([row.dashboard_id for row in data]),
                Dashboard.is_active.in_([True]),
            )
        )
    }
    if len(dashboards) != len(data):
        raise ConflictError("INVALID_DASHBOARD_ACCESS", "All assigned dashboards must be active.")
    db.query(DashboardProfileAccess).filter(
        DashboardProfileAccess.profile_id == profile_id
    ).delete()
    db.add_all(
        DashboardProfileAccess(
            profile_id=profile_id,
            dashboard_id=item.dashboard_id,
            can_view=item.can_view,
            is_default=item.is_default,
            is_active=item.is_active,
        )
        for item in data
    )
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Profile",
            entity_id=str(profile_id),
            action="dashboard.profile_access.replaced",
            new_values_json=json.dumps([item.model_dump() for item in data]),
        )
    )
    db.commit()
    rows = db.execute(
        select(DashboardProfileAccess, Dashboard)
        .join(Dashboard, Dashboard.id == DashboardProfileAccess.dashboard_id)
        .where(
            DashboardProfileAccess.profile_id == profile_id,
            DashboardProfileAccess.is_active.in_([True]),
            DashboardProfileAccess.can_view.in_([True]),
        )
        .order_by(DashboardProfileAccess.is_default.desc(), Dashboard.name)
    ).all()
    return [
        _accessible_dashboard_read(db, dashboard, access.is_default) for access, dashboard in rows
    ]


@router.get("/dashboards/config", response_model=DashboardConfigRead)
def effective_dashboard_config(
    dashboard_type: Literal["EXECUTIVE", "TOP_MANAGEMENT"] = Query(default="EXECUTIVE"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> DashboardConfigRead:
    permissions = set(effective_permissions(db, user).permissions)
    primary_profile = _primary_profile(db, user.id)
    # User choices are a visibility overlay. They must never replace the
    # administrator-governed assignment itself.
    resolved = _resolved_assignment(
        db,
        user,
        primary_profile,
        server_now(),
        dashboard_type=dashboard_type,
    )
    if resolved:
        assignment, dashboard, source, explanation = resolved
        widgets = list(
            db.scalars(
                select(DashboardWidget)
                .where(
                    DashboardWidget.dashboard_id == dashboard.id,
                    DashboardWidget.is_active.in_([True]),
                )
                .order_by(DashboardWidget.position)
            )
        )
        authorized = _authorized_widgets(widgets, permissions)
        preference = db.scalar(
            select(DashboardUserPreference).where(
                DashboardUserPreference.user_id == user.id,
                DashboardUserPreference.dashboard_type == dashboard_type,
            )
        )
        hidden = (
            set(json.loads(preference.hidden_widget_codes_json or "[]"))
            if preference and preference.assigned_dashboard_id == dashboard.id
            else set()
        )
        config = dashboard_read(
            dashboard,
            [item for item in authorized if item.widget_code not in hidden],
            source,
            assignment,
            explanation,
        )
        available = dashboard_read(dashboard, authorized, source, assignment, explanation).widgets
        return config.model_copy(
            update={
                "available_widgets": available,
                "hidden_widget_codes": sorted(hidden & {item.widget_code for item in authorized}),
            }
        )
    # Temporary compatibility fallback for pre-assignment profile configuration.
    codes = [code for code, _ in DEFAULT_WIDGETS]
    codes = [
        code for code in codes if WIDGET_REQUIRED_PERMISSIONS.get(code, frozenset()) <= permissions
    ]
    codes = list(dict.fromkeys(codes))
    labels = dict(DEFAULT_WIDGETS)
    available = [
        DashboardWidgetConfig(
            widget_code=code,
            title=labels.get(code, CATALOG_BY_CODE.get(code, (code, code))[1]),
            widget_type=CATALOG_BY_CODE.get(code, (None, None, None, "KPI_CARD"))[3],
            query_code=CATALOG_BY_CODE.get(code, (None, None, None, None, code))[4],
            position=index,
            width=CATALOG_BY_CODE.get(code, (None, None, None, None, None, 2))[5],
            refresh_seconds=60,
        )
        for index, code in enumerate(codes)
    ]
    preference = db.scalar(
        select(DashboardUserPreference).where(
            DashboardUserPreference.user_id == user.id,
            DashboardUserPreference.dashboard_type == dashboard_type,
        )
    )
    hidden = (
        set(json.loads(preference.hidden_widget_codes_json or "[]"))
        if preference and preference.assigned_dashboard_id is None
        else set()
    )
    return DashboardConfigRead(
        source="SYSTEM",
        name="System default",
        widgets=[item for item in available if item.widget_code not in hidden],
        available_widgets=available,
        hidden_widget_codes=sorted(hidden & {item.widget_code for item in available}),
    )


@router.get("/dashboards/admin/preview", response_model=DashboardAdminPreviewRead)
def preview_effective_dashboard(
    user_id: int = Query(gt=0),
    dashboard_type: Literal["EXECUTIVE", "TOP_MANAGEMENT"] = Query(default="EXECUTIVE"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("dashboard.manage_widgets")),
) -> DashboardAdminPreviewRead:
    """Resolve a user's dashboard without impersonating or mutating that user."""
    target = db.scalar(select(User).where(User.id == user_id, User.is_active.in_([True])))
    if not target:
        raise NotFoundError("Active user does not exist.")
    resolved = effective_dashboard_config(dashboard_type=dashboard_type, db=db, user=target)
    permissions = sorted(set(effective_permissions(db, target).permissions))
    return DashboardAdminPreviewRead(
        **resolved.model_dump(),
        user_id=target.id,
        user_name=target.full_name,
        permission_codes=permissions,
    )


@router.get("/dashboards/admin/scenario-preview", response_model=DashboardScenarioPreviewRead)
def preview_dashboard_scenario(
    profile_id: int | None = Query(default=None, gt=0),
    department_id: int | None = Query(default=None, gt=0),
    dashboard_type: Literal["EXECUTIVE", "TOP_MANAGEMENT"] = Query(default="EXECUTIVE"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("dashboard.manage_widgets")),
) -> DashboardScenarioPreviewRead:
    if profile_id is None and department_id is None:
        raise ConflictError("DASHBOARD_SCENARIO_REQUIRED", "Choose a profile or department.")
    profile = db.get(Profile, profile_id) if profile_id else None
    if profile_id and not profile:
        raise NotFoundError("Profile does not exist.")
    from app.modules.iam.models import Department

    if department_id and not db.get(Department, department_id):
        raise NotFoundError("Department does not exist.")
    permissions = (
        set(
            db.scalars(
                select(Permission.code)
                .join(ProfilePermission)
                .where(ProfilePermission.profile_id == profile_id, Permission.is_active.in_([True]))
            )
        )
        if profile_id
        else set()
    )
    resolved = _resolved_scenario_assignment(
        db, profile_id, department_id, server_now(), dashboard_type
    )
    if resolved:
        assignment, dashboard, source, explanation = resolved
        widgets = list(
            db.scalars(
                select(DashboardWidget)
                .where(
                    DashboardWidget.dashboard_id == dashboard.id,
                    DashboardWidget.is_active.in_([True]),
                )
                .order_by(DashboardWidget.position)
            )
        )
        config = dashboard_read(
            dashboard, _authorized_widgets(widgets, permissions), source, assignment, explanation
        )
    else:
        codes = [code for code, _ in DEFAULT_WIDGETS]
        codes = [
            code
            for code in codes
            if WIDGET_REQUIRED_PERMISSIONS.get(code, frozenset()) <= permissions
        ]
        config = DashboardConfigRead(
            source="SYSTEM",
            name="System default",
            widgets=[
                DashboardWidgetConfig(
                    widget_code=code,
                    title=CATALOG_BY_CODE.get(code, (code, code))[1],
                    widget_type=CATALOG_BY_CODE.get(code, (None, None, None, "KPI_CARD"))[3],
                    query_code=CATALOG_BY_CODE.get(code, (None, None, None, None, code))[4],
                    position=index,
                    width=CATALOG_BY_CODE.get(code, (None, None, None, None, None, 2))[5],
                    refresh_seconds=60,
                )
                for index, code in enumerate(codes)
            ],
        )
    return DashboardScenarioPreviewRead(
        **config.model_dump(),
        profile_id=profile_id,
        department_id=department_id,
        permission_codes=sorted(permissions),
    )


@router.put("/dashboards/config", response_model=DashboardConfigRead)
def save_my_dashboard_config(
    data: DashboardConfigUpdate,
    dashboard_type: Literal["EXECUTIVE", "TOP_MANAGEMENT"] = Query(default="EXECUTIVE"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> DashboardConfigRead:
    permissions = set(effective_permissions(db, user).permissions)
    if (
        "dashboard.customize.own" not in permissions
        and "dashboard.manage_widgets" not in permissions
    ):
        raise AuthorizationError("You do not have permission to customize your dashboard.")
    primary_profile = _primary_profile(db, user.id)
    assigned = _resolved_assignment(
        db, user, primary_profile, server_now(), dashboard_type=dashboard_type
    )
    dashboard = assigned[1] if assigned else None
    governed_widgets = (
        list(
            db.scalars(
                select(DashboardWidget)
                .where(
                    DashboardWidget.dashboard_id == dashboard.id,
                    DashboardWidget.is_active.in_([True]),
                )
                .order_by(DashboardWidget.position)
            )
        )
        if dashboard
        else []
    )
    governed_codes = {
        item.widget_code for item in _authorized_widgets(governed_widgets, permissions)
    }
    if not dashboard:
        governed_codes = {code for code, _ in DEFAULT_WIDGETS}
        governed_codes = {
            code
            for code in governed_codes
            if WIDGET_REQUIRED_PERMISSIONS.get(code, frozenset()) <= permissions
        }
    submitted_codes = {item.widget_code for item in data.widgets}
    if not submitted_codes <= governed_codes:
        raise ConflictError(
            "UNASSIGNED_DASHBOARD_WIDGET",
            "Users may only show or hide widgets from their assigned dashboard.",
        )
    for item in data.widgets:
        catalog_item = CATALOG_BY_CODE.get(item.widget_code)
        if (
            not catalog_item
            or item.query_code != catalog_item[4]
            or item.widget_type != catalog_item[3]
        ):
            raise ConflictError(
                "INVALID_DASHBOARD_WIDGET", f"Unsupported dashboard widget: {item.widget_code}"
            )
        if not WIDGET_REQUIRED_PERMISSIONS.get(item.widget_code, frozenset()) <= permissions:
            raise AuthorizationError("You do not have permission to use this dashboard widget.")
        if item.config:
            raise ConflictError(
                "INVALID_DASHBOARD_WIDGET_CONFIG",
                f"Widget {item.widget_code} does not define configurable query options.",
            )
    preference = db.scalar(
        select(DashboardUserPreference).where(
            DashboardUserPreference.user_id == user.id,
            DashboardUserPreference.dashboard_type == dashboard_type,
        )
    )
    if not preference:
        preference = DashboardUserPreference(user_id=user.id, dashboard_type=dashboard_type)
        db.add(preference)
    preference.hidden_widget_codes_json = json.dumps(sorted(governed_codes - submitted_codes))
    preference.assigned_dashboard_id = dashboard.id if dashboard else None
    preference.assigned_dashboard_version = dashboard.version if dashboard else None
    db.commit()
    return effective_dashboard_config(dashboard_type=dashboard_type, db=db, user=user)


@router.delete("/dashboards/config", response_model=DashboardConfigRead)
def reset_my_dashboard_config(
    dashboard_type: Literal["EXECUTIVE", "TOP_MANAGEMENT"] = Query(default="EXECUTIVE"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> DashboardConfigRead:
    permissions = set(effective_permissions(db, user).permissions)
    if (
        "dashboard.customize.own" not in permissions
        and "dashboard.manage_widgets" not in permissions
    ):
        raise AuthorizationError("You do not have permission to reset your dashboard.")
    preference = db.scalar(
        select(DashboardUserPreference).where(
            DashboardUserPreference.user_id == user.id,
            DashboardUserPreference.dashboard_type == dashboard_type,
        )
    )
    if preference:
        db.add(
            AuditLog(
                actor_user_id=user.id,
                entity_type="DashboardUserPreference",
                entity_id=str(preference.id),
                action="dashboard.visibility.reset",
                old_values_json=preference.hidden_widget_codes_json,
            )
        )
        db.delete(preference)
        db.commit()
    return effective_dashboard_config(dashboard_type=dashboard_type, db=db, user=user)


@router.get("/dashboards/online-engineers", response_model=list[OnlineEngineer])
def list_online_engineers(
    db: Session = Depends(get_db), user: User = Depends(current_user)
) -> list[OnlineEngineer]:
    permissions = set(effective_permissions(db, user).permissions)
    if "dashboard.online_engineers.view" not in permissions:
        raise AuthorizationError()
    is_hr = bool(
        db.scalar(
            select(UserProfile.id)
            .join(Profile, Profile.id == UserProfile.profile_id)
            .where(
                UserProfile.user_id == user.id,
                UserProfile.is_active.in_([True]),
                Profile.code == "HR",
            )
        )
    )
    in_progress_id = db.scalar(select(TicketStatus.id).where(TicketStatus.code == "IN_PROGRESS"))
    ticket_statement = (select(Ticket) if is_hr else visible_ticket_query(db, user)).where(
        Ticket.status_id == in_progress_id, Ticket.assigned_user_id.is_not(None)
    )
    # Aggregate in SQL rather than materializing every in-progress Ticket ORM
    # object and repeatedly counting it in Python for each online engineer.
    ticket_counts: dict[int, int] = {}
    ticket_numbers: dict[int, str] = {}
    ticket_priorities: dict[int, dict[str, int]] = {}
    for engineer_id, priority, count, ticket_number in db.execute(
        ticket_statement.with_only_columns(
            Ticket.assigned_user_id,
            Ticket.priority,
            func.count(Ticket.id),
            func.min(Ticket.ticket_number),
            maintain_column_froms=True,
        ).group_by(Ticket.assigned_user_id, Ticket.priority)
    ):
        if engineer_id is None:
            continue
        ticket_counts[engineer_id] = ticket_counts.get(engineer_id, 0) + int(count)
        current_ticket = ticket_numbers.get(engineer_id)
        if ticket_number is not None and (current_ticket is None or ticket_number < current_ticket):
            ticket_numbers[engineer_id] = ticket_number
        if priority in {"P1", "P2", "P3", "P4"}:
            ticket_priorities.setdefault(engineer_id, {})[priority] = int(count)
    online_statement = select(User).where(
        User.is_active.in_([True]),
        User.user_type == "EMPLOYEE",
        User.last_seen_at >= server_now() - timedelta(minutes=2),
    )
    if is_hr:
        online_statement = online_statement.where(User.department == user.department)
    return [
        OnlineEngineer(
            user_id=employee.id,
            engineer=employee.full_name,
            department=employee.department,
            status="WORKING_ON_TICKET" if employee.id in ticket_counts else "AVAILABLE",
            ticket_number=ticket_numbers.get(employee.id),
            active_ticket_count=ticket_counts.get(employee.id, 0),
            tickets_by_priority=ticket_priorities.get(employee.id, {}),
        )
        for employee in db.scalars(online_statement.order_by(User.full_name))
    ]


@router.get("/dashboards/top-support-agents", response_model=TopSupportAgentsRead)
def top_support_agents(
    timezone_offset_minutes: int = Query(default=180, ge=-840, le=840),
    limit: int = Query(default=3, ge=1, le=10),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> TopSupportAgentsRead:
    permissions = set(effective_permissions(db, user).permissions)
    if not ({"dashboard.agent", "dashboard.manager"} & permissions):
        raise AuthorizationError()
    now = server_now()
    local_now = now
    period_start = datetime(local_now.year, local_now.month, 1, tzinfo=server_timezone())
    period_end = now
    scoped_tickets = (
        AuthenticatedDashboardScope(db, user)
        .ticket_query()
        .where(
            Ticket.resolved_at >= period_start,
            Ticket.resolved_at <= period_end,
            Ticket.assigned_user_id.is_not(None),
        )
        .subquery()
    )
    breached_tickets = (
        select(TicketSlaClock.ticket_id.label("ticket_id"))
        .where(
            TicketSlaClock.clock_type == "RESOLUTION",
            or_(TicketSlaClock.breached_at.is_not(None), TicketSlaClock.state == "BREACHED"),
        )
        .distinct()
        .subquery()
    )
    breached_count = func.sum(case((breached_tickets.c.ticket_id.is_not(None), 1), else_=0))
    rows = db.execute(
        select(
            User.id,
            User.full_name,
            User.department,
            func.count(scoped_tickets.c.id),
            breached_count,
        )
        .join(scoped_tickets, scoped_tickets.c.assigned_user_id == User.id)
        .outerjoin(breached_tickets, breached_tickets.c.ticket_id == scoped_tickets.c.id)
        .where(
            User.is_active.in_([True]),
            User.user_type == "EMPLOYEE",
            func.lower(func.trim(User.department)) == "support",
        )
        .group_by(User.id, User.full_name, User.department)
        .order_by(
            func.count(scoped_tickets.c.id).desc(),
            breached_count.asc(),
            User.full_name.asc(),
        )
        .limit(limit)
    )
    agents = [
        TopSupportAgent(
            user_id=user_id,
            agent=full_name,
            department=department,
            assigned=int(resolved_count),
            resolved=int(resolved_count),
            breached=int(breached_count or 0),
        )
        for user_id, full_name, department, resolved_count, breached_count in rows
    ]
    return TopSupportAgentsRead(
        date_from=period_start,
        date_to=period_end,
        agents=agents,
    )


@router.get("/dashboards/summary", response_model=DashboardSummary)
def summary(
    dashboard_scope: Literal["GENERAL", "MY"] | None = None,
    kpi_month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    kpi_quarter: str | None = Query(default=None, pattern=r"^\d{4}-Q[1-4]$"),
    date_from: date | None = None,
    date_to: date | None = None,
    date_basis: Literal["CREATION", "RESOLUTION", "ASSIGNMENT"] = "CREATION",
    country_id: int | None = None,
    zone: str | None = None,
    client_id: int | None = None,
    location_id: int | None = None,
    product_id: int | None = None,
    team_id: int | None = None,
    engineer_id: int | None = None,
    timezone_offset_minutes: int = 180,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> DashboardSummary:
    permissions = set(effective_permissions(db, user).permissions)
    if not ({"dashboard.agent", "dashboard.manager"} & permissions):
        raise AuthorizationError()
    is_hr = bool(
        db.scalar(
            select(UserProfile.id)
            .join(Profile, Profile.id == UserProfile.profile_id)
            .where(
                UserProfile.user_id == user.id,
                UserProfile.is_active.in_([True]),
                Profile.code == "HR",
            )
        )
    )
    now = server_now()
    local_now = now
    if sum(bool(value) for value in (kpi_month, kpi_quarter, date_from or date_to)) > 1:
        raise ConflictError("INVALID_KPI_PERIOD", "Choose a month, quarter, or custom date range.")
    if (date_from is None) != (date_to is None):
        raise ConflictError("INVALID_KPI_PERIOD", "Both From and To dates are required.")
    if date_from and date_to and date_from > date_to:
        raise ConflictError("INVALID_KPI_PERIOD", "From date cannot be after To date.")
    selected_period = kpi_quarter or kpi_month or local_now.strftime("%Y-%m")
    if date_from and date_to:
        selected_period = f"{date_from.isoformat()} to {date_to.isoformat()} ({date_basis.title()})"
        month_start = datetime.combine(date_from, datetime.min.time(), tzinfo=server_timezone())
        month_end = datetime.combine(date_to, datetime.max.time(), tzinfo=server_timezone())
    elif kpi_quarter:
        year = int(kpi_quarter[:4])
        quarter = int(kpi_quarter[-1])
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        month_start = datetime(year, start_month, 1, tzinfo=server_timezone())
        month_end = datetime(
            year, end_month, monthrange(year, end_month)[1], 23, 59, 59, 999999, tzinfo=server_timezone()
        )
    else:
        year, month = (int(value) for value in selected_period.split("-"))
        month_start = datetime(year, month, 1, tzinfo=server_timezone())
        month_end = datetime(
            year, month, monthrange(year, month)[1], 23, 59, 59, 999999, tzinfo=server_timezone()
        )
    # A dashboard profile may change presentation, never ticket visibility. HR
    # workforce widgets are calculated separately below, while all ticket
    # aggregates remain constrained by the central ticket scope service.
    dashboard_ticket_scope = AuthenticatedDashboardScope(db, user)
    dashboard_ticket_scope.ensure_filters_allowed(
        DashboardTicketFilters(
            country_id=country_id,
            zone=zone,
            client_id=client_id,
            location_id=location_id,
            product_id=product_id,
            engineer_id=engineer_id,
            team_id=team_id,
        )
    )
    scope_statement = dashboard_ticket_scope.ticket_query()
    ticket_statement = scope_statement
    if date_basis == "RESOLUTION":
        ticket_statement = ticket_statement.where(
            Ticket.resolved_at >= month_start, Ticket.resolved_at <= month_end
        )
    elif date_basis == "ASSIGNMENT":
        assigned_in_period = select(TicketAssignmentHistory.ticket_id).where(
            TicketAssignmentHistory.created_at >= month_start,
            TicketAssignmentHistory.created_at <= month_end,
        )
        ticket_statement = ticket_statement.where(Ticket.id.in_(assigned_in_period))
    else:
        ticket_statement = ticket_statement.where(
            Ticket.created_at >= month_start, Ticket.created_at <= month_end
        )
    department_user_ids: set[int] | None = None
    if is_hr:
        department_user_ids = set(
            db.scalars(
                select(User.id).where(
                    User.is_active.in_([True]),
                    User.user_type == "EMPLOYEE",
                    User.department == user.department,
                )
            )
        )
        ticket_statement = ticket_statement.where(
            Ticket.assigned_user_id.in_(department_user_ids or [-1])
        )
    effective_dashboard_scope = dashboard_scope or user.default_dashboard_scope
    if effective_dashboard_scope == "MY":
        ticket_statement = ticket_statement.where(Ticket.assigned_user_id == user.id)
    team_user_ids = (
        set(
            db.scalars(
                select(SupportTeamMember.user_id).where(SupportTeamMember.team_id == team_id)
            )
        )
        if team_id
        else None
    )
    if client_id:
        ticket_statement = ticket_statement.where(Ticket.client_id == client_id)
    if product_id:
        ticket_statement = ticket_statement.where(Ticket.product_id == product_id)
    if engineer_id:
        ticket_statement = ticket_statement.where(Ticket.assigned_user_id == engineer_id)
    if team_user_ids is not None:
        ticket_statement = ticket_statement.where(
            or_(
                Ticket.routed_team_id == team_id,
                Ticket.assigned_user_id.in_(team_user_ids or [-1]),
            )
        )
    if country_id or zone or location_id:
        branch_location = aliased(ClientLocation)
        client_location = aliased(ClientLocation)
        ticket_statement = (
            ticket_statement.join(Client, Client.id == Ticket.client_id)
            .outerjoin(Branch, Branch.id == Ticket.branch_id)
            .outerjoin(branch_location, branch_location.id == Branch.location_id)
            .outerjoin(client_location, client_location.id == Client.primary_location_id)
        )
        effective_location_id = func.coalesce(branch_location.id, client_location.id)
        effective_country_id = func.coalesce(
            branch_location.country_id, client_location.country_id, Client.country_id
        )
        effective_zone = func.coalesce(branch_location.zone, client_location.zone, Client.zone)
        if location_id:
            ticket_statement = ticket_statement.where(effective_location_id == location_id)
        if country_id:
            ticket_statement = ticket_statement.where(effective_country_id == country_id)
        if zone:
            ticket_statement = ticket_statement.where(effective_zone == zone)
    filtered_tickets = ticket_statement.subquery("dashboard_tickets")
    tickets = list(
        db.scalars(
            ticket_statement.options(
                load_only(
                    Ticket.id,
                    Ticket.ticket_number,
                    Ticket.status_id,
                    Ticket.assigned_user_id,
                    Ticket.priority,
                    Ticket.category,
                    Ticket.subject,
                    Ticket.client_id,
                    Ticket.product_id,
                    Ticket.product_module_id,
                    Ticket.entitlement_status,
                    Ticket.routing_status,
                    Ticket.shift_handover_status,
                    Ticket.created_at,
                    Ticket.resolved_at,
                    Ticket.closed_at,
                )
            )
        )
    )
    status_map = {item.id: item.code for item in db.scalars(select(TicketStatus))}
    open_codes = {
        "NEW",
        "TRIAGED",
        "ASSIGNED",
        "IN_PROGRESS",
        "PENDING_CLIENT",
        "PENDING_INTERNAL",
        "PENDING_VENDOR",
        "REOPENED",
    }
    pending_approvals, shift_handovers = db.execute(
        select(
            func.sum(
                case((filtered_tickets.c.entitlement_status == "PENDING_APPROVAL", 1), else_=0)
            ),
            func.sum(case((filtered_tickets.c.shift_handover_status == "PENDING", 1), else_=0)),
        )
    ).one()
    pending_approvals = int(pending_approvals or 0)
    shift_handovers = int(shift_handovers or 0)
    ticket_ids = [item.id for item in tickets]
    clock_rows = list(
        db.execute(
            select(
                TicketSlaClock.ticket_id,
                TicketSlaClock.state,
                TicketSlaClock.due_at,
            ).join(filtered_tickets, filtered_tickets.c.id == TicketSlaClock.ticket_id)
        )
    )
    clock_ticket_ids = {int(row.ticket_id) for row in clock_rows}
    accountable_results = resolution_sla_results(db, tickets, as_of=now)
    breached_ids = {
        ticket_id for ticket_id, result in accountable_results.items() if not result.met
    }
    due_soon_ids = {
        int(clock.ticket_id)
        for clock in clock_rows
        if clock.state == "RUNNING"
        and now < clock.due_at.replace(tzinfo=server_timezone()) <= now + timedelta(hours=4)
    }
    open_tickets = [item for item in tickets if status_map.get(item.status_id) in open_codes]
    open_status_ids = [status_id for status_id, code in status_map.items() if code in open_codes]
    priority_rows = db.execute(
        select(filtered_tickets.c.priority, func.count(filtered_tickets.c.id))
        .where(filtered_tickets.c.status_id.in_(open_status_ids or [-1]))
        .group_by(filtered_tickets.c.priority)
    )
    priority_counts = {str(priority): int(count) for priority, count in priority_rows}
    by_priority = {
        priority: priority_counts.get(priority, 0) for priority in ("P1", "P2", "P3", "P4")
    }
    status_priority_rows = list(
        db.execute(
            select(
                TicketStatus.code, filtered_tickets.c.priority, func.count(filtered_tickets.c.id)
            )
            .join(filtered_tickets, filtered_tickets.c.status_id == TicketStatus.id)
            .group_by(TicketStatus.code, filtered_tickets.c.priority)
        )
    )
    by_status: dict[str, int] = {}
    priority_by_status: dict[str, dict[str, int]] = {}
    for code, priority, count in status_priority_rows:
        code = str(code)
        by_status[code] = by_status.get(code, 0) + int(count)
        priority_by_status.setdefault(code, {value: 0 for value in ("P1", "P2", "P3", "P4")})[
            str(priority)
        ] = int(count)
    today = local_now.date()
    product_names = {item.id: item.name for item in db.scalars(select(Product))}
    module_names = {item.id: item.name for item in db.scalars(select(ProductModule))}

    def breakdown(values: list[str]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10])

    def grouped_breakdown(
        key_column: Any, model: Any, label_column: Any, empty_label: str
    ) -> dict[str, int]:
        rows = db.execute(
            select(func.coalesce(label_column, empty_label), func.count(filtered_tickets.c.id))
            .select_from(filtered_tickets)
            .outerjoin(model, key_column == model.id)
            .where(filtered_tickets.c.status_id.in_(open_status_ids or [-1]))
            .group_by(label_column)
            .order_by(func.count(filtered_tickets.c.id).desc(), label_column)
            .limit(10)
        )
        return {str(label): int(count) for label, count in rows}

    backlog_by_client = grouped_breakdown(
        filtered_tickets.c.client_id, Client, Client.name, "No client"
    )
    backlog_by_product = grouped_breakdown(
        filtered_tickets.c.product_id, Product, Product.name, "No product"
    )
    backlog_by_module = grouped_breakdown(
        filtered_tickets.c.product_module_id, ProductModule, ProductModule.name, "No module"
    )
    workload_by_engineer = grouped_breakdown(
        filtered_tickets.c.assigned_user_id, User, User.full_name, "Unassigned"
    )
    backlog_by_team = {
        str(label): int(count)
        for label, count in db.execute(
            select(
                func.coalesce(filtered_tickets.c.assigned_team, "No team"),
                func.count(filtered_tickets.c.id),
            )
            .where(filtered_tickets.c.status_id.in_(open_status_ids or [-1]))
            .group_by(filtered_tickets.c.assigned_team)
            .order_by(func.count(filtered_tickets.c.id).desc(), filtered_tickets.c.assigned_team)
            .limit(10)
        )
    }
    today_start = datetime.combine(today, datetime.min.time(), tzinfo=server_timezone())
    aging_row = db.execute(
        select(
            func.sum(
                case((filtered_tickets.c.created_at >= today_start - timedelta(days=1), 1), else_=0)
            ),
            func.sum(
                case(
                    (
                        and_(
                            filtered_tickets.c.created_at >= today_start - timedelta(days=3),
                            filtered_tickets.c.created_at < today_start - timedelta(days=1),
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
            func.sum(
                case(
                    (
                        and_(
                            filtered_tickets.c.created_at >= today_start - timedelta(days=7),
                            filtered_tickets.c.created_at < today_start - timedelta(days=3),
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
            func.sum(
                case(
                    (
                        and_(
                            filtered_tickets.c.created_at >= today_start - timedelta(days=14),
                            filtered_tickets.c.created_at < today_start - timedelta(days=7),
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
            func.sum(
                case((filtered_tickets.c.created_at < today_start - timedelta(days=14), 1), else_=0)
            ),
        ).where(filtered_tickets.c.status_id.in_(open_status_ids or [-1]))
    ).one()
    aging_buckets = dict(
        zip(
            ("0–1 days", "2–3 days", "4–7 days", "8–14 days", "15+ days"),
            (int(value or 0) for value in aging_row),
            strict=True,
        )
    )
    trend_days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    trend_expressions: list[Any] = []
    for day in trend_days:
        day_start = datetime.combine(day, datetime.min.time(), tzinfo=server_timezone())
        day_end = day_start + timedelta(days=1)
        trend_expressions.extend(
            (
                func.sum(
                    case(
                        (
                            and_(
                                filtered_tickets.c.created_at >= day_start,
                                filtered_tickets.c.created_at < day_end,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                func.sum(
                    case(
                        (
                            or_(
                                and_(
                                    filtered_tickets.c.closed_at >= day_start,
                                    filtered_tickets.c.closed_at < day_end,
                                ),
                                and_(
                                    filtered_tickets.c.resolved_at >= day_start,
                                    filtered_tickets.c.resolved_at < day_end,
                                ),
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
            )
        )
    trend_values = db.execute(select(*trend_expressions)).one()
    inflow_last_7_days = {
        day.isoformat(): int(trend_values[index * 2] or 0) for index, day in enumerate(trend_days)
    }
    closures_last_7_days = {
        day.isoformat(): int(trend_values[index * 2 + 1] or 0)
        for index, day in enumerate(trend_days)
    }
    sla_ticket_ids = set(accountable_results)
    sla_compliance_percent = (
        round(100 * len(sla_ticket_ids - breached_ids) / len(sla_ticket_ids), 1)
        if sla_ticket_ids
        else None
    )
    histories = [
        history
        for ticket_id_batch in _id_batches(ticket_ids)
        for history in db.scalars(
            select(TicketStatusHistory).where(TicketStatusHistory.ticket_id.in_(ticket_id_batch))
        )
    ]
    reopened_status_ids = {
        status_id for status_id, code in status_map.items() if code == "REOPENED"
    }
    reopened_ticket_ids = {
        item.ticket_id for item in histories if item.to_status_id in reopened_status_ids
    }
    first_assignments = first_dedicated_assignments(db, ticket_ids)
    resolution_hours_by_ticket = {
        item.id: (_aware_end - _aware_start).total_seconds() / 3600
        for item in tickets
        if (completed := item.closed_at or item.resolved_at) is not None
        and (assigned := first_assignments.get(item.id)) is not None
        and (_aware_end := completed.replace(tzinfo=server_timezone()) if completed.tzinfo is None else completed)
        >= (_aware_start := assigned.replace(tzinfo=server_timezone()) if assigned.tzinfo is None else assigned)
    }
    resolution_hours = list(resolution_hours_by_ticket.values())
    average_resolution_hours = (
        round(sum(resolution_hours) / len(resolution_hours), 1) if resolution_hours else None
    )
    reopen_rate_percent = (
        round(100 * len(reopened_ticket_ids) / len(tickets), 1) if tickets else 0.0
    )
    open_ticket_ids = [item.id for item in open_tickets]
    active_escalations = sum(
        len(
            list(
                db.scalars(
                    select(EscalationEvent.id).where(EscalationEvent.ticket_id.in_(ticket_id_batch))
                )
            )
        )
        for ticket_id_batch in _id_batches(open_ticket_ids)
    )
    in_progress_status_ids = {key for key, code in status_map.items() if code == "IN_PROGRESS"}
    busy_ticket_user_ids = {
        item.assigned_user_id
        for item in tickets
        if item.status_id in in_progress_status_ids and item.assigned_user_id is not None
    }
    working_tickets: dict[int, list[Ticket]] = {}
    for item in tickets:
        if item.status_id in in_progress_status_ids and item.assigned_user_id is not None:
            working_tickets.setdefault(item.assigned_user_id, []).append(item)
    online_cutoff = now - timedelta(minutes=2)
    online_statement = select(User).where(
        User.is_active.in_([True]), User.user_type == "EMPLOYEE", User.last_seen_at >= online_cutoff
    )
    if department_user_ids is not None:
        online_statement = online_statement.where(User.id.in_(department_user_ids or [-1]))
    online_engineers = (
        [
            OnlineEngineer(
                user_id=employee.id,
                engineer=employee.full_name,
                department=employee.department,
                status="WORKING_ON_TICKET" if employee.id in working_tickets else "AVAILABLE",
                ticket_number=working_tickets[employee.id][0].ticket_number
                if employee.id in working_tickets
                else None,
                active_ticket_count=len(working_tickets.get(employee.id, [])),
                tickets_by_priority={
                    priority: sum(
                        ticket.priority == priority
                        for ticket in working_tickets.get(employee.id, [])
                    )
                    for priority in ("P1", "P2", "P3", "P4")
                    if any(
                        ticket.priority == priority
                        for ticket in working_tickets.get(employee.id, [])
                    )
                },
            )
            for employee in db.scalars(online_statement.order_by(User.full_name))
        ]
        if "dashboard.online_engineers.view" in permissions
        else []
    )
    busy_operation_user_ids = set(
        db.scalars(
            select(InternalOperationAssignee.user_id)
            .join(InternalOperation, InternalOperation.id == InternalOperationAssignee.operation_id)
            .where(InternalOperation.status == "IN_PROGRESS")
        )
    )
    shift_types = {item.id: item for item in db.scalars(select(ShiftType))}
    current_shifts = list(
        db.scalars(select(Shift).where(Shift.starts_at <= now, Shift.ends_at > now))
    )
    available_employees = []
    available_employee_statement = select(User).where(
        User.is_active.in_([True]), User.user_type == "EMPLOYEE"
    )
    if department_user_ids is not None:
        available_employee_statement = available_employee_statement.where(
            User.id.in_(department_user_ids or [-1])
        )
    employee_names = {item.id: item.full_name for item in db.scalars(available_employee_statement)}
    for shift in current_shifts:
        if shift.user_id in busy_ticket_user_ids or shift.user_id in busy_operation_user_ids:
            continue
        shift_type = shift_types.get(shift.shift_type_id)
        if shift.user_id not in employee_names or not shift_type or shift_type.code == "LEAVE":
            continue
        available_employees.append(
            AvailableEmployee(
                user_id=shift.user_id,
                employee=employee_names[shift.user_id],
                shift_name=shift_type.name,
                shift_color=shift_type.color,
                starts_at=shift.starts_at,
                ends_at=shift.ends_at,
                team=shift.team,
            )
        )
    available_employees.sort(key=lambda item: (item.employee, item.starts_at))
    top_categories = breakdown([item.category or "Uncategorized" for item in open_tickets])
    repeated_issue_groups: dict[str, tuple[str, int]] = {}
    for item in tickets:
        normalized = re.sub(r"[^a-z0-9 ]+", " ", item.subject.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if not normalized:
            continue
        label, count = repeated_issue_groups.get(normalized, (item.subject.strip(), 0))
        repeated_issue_groups[normalized] = (label, count + 1)
    top_repeated_issues = dict(
        sorted(
            ((label, count) for label, count in repeated_issue_groups.values() if count > 1),
            key=lambda value: (-value[1], value[0].lower()),
        )[:10]
    )
    contracts = list(db.scalars(select(Contract)))
    contracts_by_status = breakdown([item.status for item in contracts])
    quarter_end_month = ((today.month - 1) // 3 + 1) * 3
    quarter_end = date(today.year, quarter_end_month, monthrange(today.year, quarter_end_month)[1])
    month_end_date = date(today.year, today.month, monthrange(today.year, today.month)[1])
    active_contracts = [item for item in contracts if item.is_active and item.status == "ACTIVE"]
    contracts_expiring = {
        "THIS_MONTH": sum(today <= item.end_date <= month_end_date for item in active_contracts),
        "THIS_QUARTER": sum(today <= item.end_date <= quarter_end for item in active_contracts),
        "30_DAYS": sum(
            today <= item.end_date <= today + timedelta(days=30) for item in active_contracts
        ),
        "60_DAYS": sum(
            today <= item.end_date <= today + timedelta(days=60) for item in active_contracts
        ),
        "90_DAYS": sum(
            today <= item.end_date <= today + timedelta(days=90) for item in active_contracts
        ),
    }

    def ticket_is_breached(ticket_id: int) -> bool:
        return ticket_id in breached_ids

    def average_hours(items: list[Ticket]) -> float | None:
        durations = [
            resolution_hours_by_ticket[item.id]
            for item in items
            if item.id in resolution_hours_by_ticket
        ]
        return round(sum(durations) / len(durations), 1) if durations else None

    agent_kpis: list[AgentKpi] = []
    assigned_groups: dict[int | None, list[Ticket]] = {}
    for item in tickets:
        assigned_groups.setdefault(item.assigned_user_id, []).append(item)
    employee_statement = select(User).where(
        User.is_active.in_([True]), User.user_type == "EMPLOYEE"
    )
    if department_user_ids is not None:
        employee_statement = employee_statement.where(User.id.in_(department_user_ids or [-1]))
    active_employees = list(db.scalars(employee_statement))
    all_employee_statement = select(User).where(User.user_type == "EMPLOYEE")
    if department_user_ids is not None:
        all_employee_statement = all_employee_statement.where(
            User.id.in_(department_user_ids or [-1])
        )
    all_employees = list(db.scalars(all_employee_statement))
    employee_ids = {item.id for item in all_employees}
    shifted_user_ids = {shift.user_id for shift in current_shifts if shift.user_id in employee_ids}
    leave_user_ids = {
        shift.user_id
        for shift in current_shifts
        if shift.user_id in employee_ids
        and shift_types.get(shift.shift_type_id)
        and shift_types[shift.shift_type_id].code == "LEAVE"
    }
    future_shift_user_ids = set(
        db.scalars(
            select(Shift.user_id).where(
                Shift.starts_at >= now,
                Shift.starts_at <= now + timedelta(days=7),
                Shift.status != "CANCELLED",
            )
        )
    )
    open_by_user: dict[int, int] = {}
    for item in open_tickets:
        if item.assigned_user_id:
            open_by_user[item.assigned_user_id] = open_by_user.get(item.assigned_user_id, 0) + 1
    engineer_counts = {
        "TOTAL": len(all_employees),
        "ACTIVE": sum(item.is_active for item in all_employees),
        "INACTIVE": sum(not item.is_active for item in all_employees),
        "ON_SHIFT": len(shifted_user_ids - leave_user_ids),
        "AVAILABLE": len(available_employees),
        "ON_LEAVE": len(leave_user_ids),
        "WITHOUT_SHIFT": sum(
            item.is_active
            and item.id not in future_shift_user_ids
            and item.id not in shifted_user_ids
            for item in all_employees
        ),
        "OVERLOADED": sum(count >= 10 for count in open_by_user.values()),
    }
    engineers_by_level = breakdown(
        [
            (
                "L1"
                if "fresh" in (item.job_title or "").lower()
                or "junior" in (item.job_title or "").lower()
                else "L3"
                if "senior" in (item.job_title or "").lower()
                else "LEADERSHIP"
                if (item.job_title or "") in {"Team Leader", "Manager"}
                else "L2"
            )
            for item in all_employees
            if item.is_active
        ]
    )
    engineers_by_department = breakdown(
        [item.department or "No department" for item in all_employees if item.is_active]
    )
    escalation_assignments_by_user: dict[int, int] = {}
    for audit in db.scalars(
        select(AuditLog).where(
            AuditLog.action == "ticket.escalated",
            AuditLog.created_at >= month_start,
            AuditLog.created_at <= month_end,
        )
    ):
        try:
            assignee_id = json.loads(audit.new_values_json or "{}").get(
                "escalation_assignee_user_id"
            )
            if isinstance(assignee_id, int):
                escalation_assignments_by_user[assignee_id] = (
                    escalation_assignments_by_user.get(assignee_id, 0) + 1
                )
        except (json.JSONDecodeError, TypeError):
            continue
    activities_by_user: dict[int, list[AgentActivity]] = {}
    for activity in db.scalars(
        select(AgentActivity).where(
            AgentActivity.occurred_at >= month_start, AgentActivity.occurred_at <= month_end
        )
    ):
        activities_by_user.setdefault(activity.user_id, []).append(activity)
    after_shift_by_user: dict[int, list[InternalOperation]] = {}
    after_shift_rows = db.execute(
        select(InternalOperationAssignee.user_id, InternalOperation)
        .join(InternalOperation, InternalOperation.id == InternalOperationAssignee.operation_id)
        .where(
            InternalOperation.operation_type == "AFTER_SHIFT",
            InternalOperation.status == "COMPLETED",
            InternalOperation.ends_at >= month_start,
            InternalOperation.ends_at <= month_end,
        )
    )
    for activity_user_id, operation in after_shift_rows:
        after_shift_by_user.setdefault(activity_user_id, []).append(operation)
    tasks_by_user: dict[int, int] = {
        user_id: count
        for user_id, count in db.execute(
            select(TicketTask.created_by_user_id, func.count(TicketTask.id))
            .where(TicketTask.created_at >= month_start, TicketTask.created_at <= month_end)
            .group_by(TicketTask.created_by_user_id)
        )
    }
    articles_by_user: dict[int, int] = {
        user_id: count
        for user_id, count in db.execute(
            select(Article.owner_user_id, func.count(Article.id))
            .where(Article.created_at >= month_start, Article.created_at <= month_end)
            .group_by(Article.owner_user_id)
        )
    }
    followers_by_user: dict[int, int] = {
        user_id: count
        for user_id, count in db.execute(
            select(TicketFollower.user_id, func.count(TicketFollower.ticket_id))
            .where(TicketFollower.created_at >= month_start, TicketFollower.created_at <= month_end)
            .group_by(TicketFollower.user_id)
        )
    }
    dedicated_clients_by_user: dict[int, set[int]] = {}
    for scope_user_id, scope_client_id in db.execute(
        select(UserClientScope.user_id, UserClientScope.client_id).where(
            UserClientScope.user_id.in_(employee_ids or [-1])
        )
    ):
        dedicated_clients_by_user.setdefault(scope_user_id, set()).add(scope_client_id)
    agent_status_rows = list(
        db.execute(
            select(
                filtered_tickets.c.assigned_user_id,
                TicketStatus.code,
                func.count(filtered_tickets.c.id),
            )
            .join(TicketStatus, TicketStatus.id == filtered_tickets.c.status_id)
            .where(filtered_tickets.c.assigned_user_id.is_not(None))
            .group_by(filtered_tickets.c.assigned_user_id, TicketStatus.code)
        )
    )
    agent_status_counts: dict[int, dict[str, int]] = {}
    for assigned_user_id, status_code, count in agent_status_rows:
        agent_status_counts.setdefault(int(assigned_user_id), {})[str(status_code)] = int(count)
    for employee in active_employees:
        user_id = employee.id
        items = assigned_groups.get(user_id, [])
        if date_basis == "RESOLUTION":
            monthly_items = [
                item
                for item in items
                if item.resolved_at
                and month_start <= item.resolved_at.replace(tzinfo=server_timezone()) <= month_end
            ]
        elif date_basis == "ASSIGNMENT":
            assigned_codes = {key for key, code in status_map.items() if code == "ASSIGNED"}
            assigned_ticket_ids = {
                history.ticket_id
                for history in histories
                if history.to_status_id in assigned_codes
                and month_start <= history.created_at.replace(tzinfo=server_timezone()) <= month_end
            }
            monthly_items = [item for item in items if item.id in assigned_ticket_ids]
        else:
            monthly_items = [
                item
                for item in items
                if month_start <= item.created_at.replace(tzinfo=server_timezone()) <= month_end
            ]
        agent_sla_ticket_ids = {item.id for item in items if item.id in clock_ticket_ids}
        agent_breaches = sum(ticket_is_breached(item.id) for item in items)
        tickets_by_status = agent_status_counts.get(user_id, {})
        employee_histories = [
            item for item in histories if any(ticket.id == item.ticket_id for ticket in items)
        ]
        reopened_tickets = len(
            {
                item.ticket_id
                for item in employee_histories
                if item.to_status_id in reopened_status_ids
                and month_start <= item.created_at.replace(tzinfo=server_timezone()) <= month_end
            }
        )
        response_durations: list[float] = []
        history_by_ticket: dict[int, list[TicketStatusHistory]] = {}
        for history in employee_histories:
            history_by_ticket.setdefault(history.ticket_id, []).append(history)
        assigned_status_ids = {key for key, code in status_map.items() if code == "ASSIGNED"}
        in_progress_status_ids = {key for key, code in status_map.items() if code == "IN_PROGRESS"}
        for ticket_histories in history_by_ticket.values():
            ordered = sorted(ticket_histories, key=lambda item: item.created_at)
            assigned_at = next(
                (item.created_at for item in ordered if item.to_status_id in assigned_status_ids),
                None,
            )
            in_progress_at = next(
                (
                    item.created_at
                    for item in ordered
                    if item.to_status_id in in_progress_status_ids
                    and (assigned_at is None or item.created_at >= assigned_at)
                ),
                None,
            )
            if assigned_at and in_progress_at:
                response_durations.append((in_progress_at - assigned_at).total_seconds() / 3600)
        escalation_assignments = escalation_assignments_by_user.get(user_id, 0)
        activities = activities_by_user.get(user_id, [])
        after_shift_operations = after_shift_by_user.get(user_id, [])
        after_shift_hours = round(
            sum(
                (item.ends_at - item.starts_at).total_seconds() / 3600
                for item in after_shift_operations
            ),
            1,
        )
        tasks_created = int(tasks_by_user.get(user_id, 0))
        knowledge_articles = int(articles_by_user.get(user_id, 0))
        follower_assignments = int(followers_by_user.get(user_id, 0))
        dedicated_client_ids = dedicated_clients_by_user.get(user_id, set())
        agent_kpis.append(
            AgentKpi(
                user_id=user_id,
                agent=employee.full_name,
                department=employee.department,
                assigned=sum(tickets_by_status.values()),
                open=sum(count for code, count in tickets_by_status.items() if code in open_codes),
                resolved=sum(
                    count
                    for code, count in tickets_by_status.items()
                    if code in {"RESOLVED", "CLOSED"}
                ),
                breached=agent_breaches,
                sla_compliance_percent=(
                    round(
                        100 * len(agent_sla_ticket_ids - breached_ids) / len(agent_sla_ticket_ids),
                        1,
                    )
                    if agent_sla_ticket_ids
                    else None
                ),
                average_resolution_hours=average_hours(monthly_items),
                tickets_by_status=tickets_by_status,
                escalation_assignments=escalation_assignments,
                average_response_hours=round(sum(response_durations) / len(response_durations), 1)
                if response_durations
                else None,
                reopened_tickets=reopened_tickets,
                external_activities=len(activities)
                + knowledge_articles
                + len(after_shift_operations),
                after_shift_work=len(after_shift_operations),
                after_shift_hours=after_shift_hours,
                training_attended=sum(
                    item.activity_type == "TRAINING" and item.participation_role == "ATTENDEE"
                    for item in activities
                ),
                training_delivered=sum(
                    item.activity_type == "TRAINING"
                    and item.participation_role in {"FACILITATOR", "PRESENTER"}
                    for item in activities
                ),
                meetings=sum(item.activity_type == "MEETING" for item in activities),
                tasks_created=tasks_created,
                knowledge_articles=knowledge_articles,
                follower_assignments=follower_assignments,
                dedicated_clients=len(dedicated_client_ids),
                dedicated_client_tickets=sum(
                    item.client_id in dedicated_client_ids for item in monthly_items
                ),
            )
        )
    agent_kpis.sort(key=lambda item: (-item.resolved, item.breached, item.agent))

    product_groups: dict[tuple[str, str], list[Ticket]] = {}
    for item in tickets:
        product = (
            product_names.get(item.product_id, "No product") if item.product_id else "No product"
        )
        module = (
            module_names.get(item.product_module_id, "No module")
            if item.product_module_id
            else "No module"
        )
        product_groups.setdefault((product, module), []).append(item)
    product_aggregate_rows = list(
        db.execute(
            select(
                func.coalesce(Product.name, "No product"),
                func.coalesce(ProductModule.name, "No module"),
                func.count(filtered_tickets.c.id),
                func.sum(
                    case((filtered_tickets.c.status_id.in_(open_status_ids or [-1]), 1), else_=0)
                ),
                func.sum(
                    case(
                        (
                            filtered_tickets.c.status_id.in_(
                                [
                                    status_id
                                    for status_id, code in status_map.items()
                                    if code in {"RESOLVED", "CLOSED"}
                                ]
                                or [-1]
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
            )
            .select_from(filtered_tickets)
            .outerjoin(Product, Product.id == filtered_tickets.c.product_id)
            .outerjoin(ProductModule, ProductModule.id == filtered_tickets.c.product_module_id)
            .group_by(Product.name, ProductModule.name)
        )
    )
    product_kpis = [
        ProductKpi(
            product=product,
            module=module,
            total=int(total),
            open=int(open_count or 0),
            resolved=int(resolved_count or 0),
            breached=sum(ticket_is_breached(item.id) for item in items),
            average_resolution_hours=average_hours(items),
        )
        for product, module, total, open_count, resolved_count in product_aggregate_rows
        if (items := product_groups.get((str(product), str(module)), [])) is not None
    ]
    product_kpis.sort(key=lambda item: (-item.total, item.product, item.module))
    can_view_financial_dashboard = "finance.dashboard.view" in permissions
    can_view_hr_dashboard = "kpi.view.all" in permissions
    hr_employees = (
        list(db.scalars(select(User).where(User.user_type == "EMPLOYEE")))
        if can_view_hr_dashboard
        else []
    )
    hr_employee_ids = {item.id for item in hr_employees}
    active_hr_employee_ids = {item.id for item in hr_employees if item.is_active}
    active_departments = (
        list(db.scalars(select(Department).where(Department.is_active.in_([True]))))
        if can_view_hr_dashboard
        else []
    )
    reporting_user_ids = (
        set(
            db.scalars(
                select(UserReportingLine.user_id).where(
                    UserReportingLine.user_id.in_(active_hr_employee_ids or [-1]),
                    UserReportingLine.effective_from <= today,
                    or_(
                        UserReportingLine.effective_until.is_(None),
                        UserReportingLine.effective_until >= today,
                    ),
                )
            )
        )
        if can_view_hr_dashboard
        else set()
    )
    hr_kpi_rows = (
        list(
            db.scalars(
                select(KpiReview).where(
                    KpiReview.user_id.in_(hr_employee_ids or [-1]),
                    KpiReview.period_start <= month_end,
                    KpiReview.period_end >= month_start,
                )
            )
        )
        if can_view_hr_dashboard
        else []
    )

    can_view_projects = "project_handover.view" in permissions
    project_statement = select(ProjectHandover)
    if can_view_projects and "project_handover.manage" not in permissions:
        assigned_projects = select(HandoverRecipient.handover_id).where(
            HandoverRecipient.user_id == user.id
        )
        project_statement = project_statement.where(
            or_(
                ProjectHandover.delivered_by_user_id == user.id,
                ProjectHandover.id.in_(assigned_projects),
            )
        )
    projects = list(db.scalars(project_statement)) if can_view_projects else []
    project_ids = {item.id for item in projects}
    project_status_counts = breakdown([item.current_status for item in projects])
    project_client_counts: dict[str, int] = {}
    if project_ids:
        project_client_counts = {
            str(name): int(count)
            for name, count in db.execute(
                select(Client.name, func.count(ProjectHandover.id))
                .join(ProjectHandover, ProjectHandover.client_id == Client.id)
                .where(ProjectHandover.id.in_(project_ids))
                .group_by(Client.name)
            )
        }
    awaiting_acceptance_ids = (
        set(
            db.scalars(
                select(HandoverRecipient.handover_id).where(
                    HandoverRecipient.handover_id.in_(project_ids or [-1]),
                    HandoverRecipient.accepted.in_([False]),
                )
            )
        )
        if project_ids
        else set()
    )
    pending_product_count = (
        int(
            db.scalar(
                select(func.count(HandoverProduct.id)).where(
                    HandoverProduct.handover_id.in_(project_ids or [-1]),
                    HandoverProduct.delivery_status.in_(["PENDING", "HOLD"]),
                )
            )
            or 0
        )
        if project_ids
        else 0
    )
    pending_point_count = (
        int(
            db.scalar(
                select(func.count(HandoverPendingPoint.id)).where(
                    HandoverPendingPoint.handover_id.in_(project_ids or [-1]),
                    HandoverPendingPoint.status == "OPEN",
                )
            )
            or 0
        )
        if project_ids
        else 0
    )
    return DashboardSummary(
        total_tickets=len(tickets),
        created_today=sum(
            item.created_at.replace(tzinfo=server_timezone()).date() == today
            for item in tickets
        ),
        closed_today=sum(
            status_map.get(item.status_id) == "CLOSED"
            and item.resolved_at is not None
            and item.resolved_at.replace(tzinfo=server_timezone()).date() == today
            for item in tickets
        ),
        total_open=len(open_tickets),
        my_open=sum(item.assigned_user_id == user.id for item in open_tickets),
        unassigned=sum(item.assigned_user_id is None for item in open_tickets),
        critical=by_priority["P1"],
        breached=len(breached_ids),
        due_soon=len(due_soon_ids),
        pending_approvals=pending_approvals,
        shift_handovers=shift_handovers,
        department_new=sum(item.routing_status == "NEW" for item in tickets),
        department_in_progress=sum(item.routing_status == "IN_PROGRESS" for item in tickets),
        department_returned=sum(item.routing_status == "RETURNED" for item in tickets),
        resolved=by_status.get("RESOLVED", 0),
        closed=by_status.get("CLOSED", 0),
        by_priority=by_priority,
        by_status=by_status,
        priority_by_status=priority_by_status,
        backlog_by_client=backlog_by_client,
        backlog_by_product=backlog_by_product,
        backlog_by_module=backlog_by_module,
        workload_by_engineer=workload_by_engineer,
        backlog_by_team=backlog_by_team,
        sla_compliance_percent=sla_compliance_percent,
        aging_buckets=aging_buckets,
        inflow_last_7_days=inflow_last_7_days,
        closures_last_7_days=closures_last_7_days,
        average_resolution_hours=average_resolution_hours,
        reopen_rate_percent=reopen_rate_percent,
        active_escalations=active_escalations,
        top_categories=top_categories,
        top_repeated_issues=top_repeated_issues,
        expiring_contracts=contracts_expiring["30_DAYS"],
        agent_kpis=agent_kpis,
        product_kpis=product_kpis,
        kpi_month=selected_period,
        available_employees=available_employees,
        online_engineers=online_engineers,
        contracts_by_status=contracts_by_status,
        contracts_expiring=contracts_expiring,
        contracts_without_renewal_date=sum(
            item.renewal_notice_date is None for item in active_contracts
        ),
        recently_expired_contracts=sum(
            today - timedelta(days=30) <= item.end_date < today for item in contracts
        ),
        engineer_counts=engineer_counts,
        engineers_by_level=engineers_by_level,
        engineers_by_department=engineers_by_department,
        financial_contracts=len(contracts) if can_view_financial_dashboard else 0,
        financial_invoices=(
            db.scalar(
                select(func.count(ContractInvoice.id)).where(ContractInvoice.status != "CANCELLED")
            )
            or 0
        )
        if can_view_financial_dashboard
        else 0,
        hr_total_employees=len(hr_employees),
        hr_active_employees=len(active_hr_employee_ids),
        hr_inactive_employees=len(hr_employees) - len(active_hr_employee_ids),
        hr_departments=len(active_departments),
        hr_head_vacancies=sum(item.head_user_id is None for item in active_departments),
        hr_reporting_exceptions=len(active_hr_employee_ids - reporting_user_ids),
        hr_kpi_pending=sum(item.status != "FINALIZED" for item in hr_kpi_rows),
        hr_kpi_finalized=sum(item.status == "FINALIZED" for item in hr_kpi_rows),
        hr_onboarding_in_progress=int(
            db.scalar(
                select(func.count(UserOnboarding.id)).where(
                    UserOnboarding.user_id.in_(active_hr_employee_ids or [-1]),
                    UserOnboarding.status == "IN_PROGRESS",
                )
            )
            or 0
        )
        if can_view_hr_dashboard
        else 0,
        hr_unscheduled_employees=sum(
            item.is_active
            and item.participates_in_shifts
            and item.id not in future_shift_user_ids
            and item.id not in shifted_user_ids
            for item in hr_employees
        ),
        project_total=len(projects),
        project_delivered=sum(
            item.current_status in {"DELIVERED", "ACCEPTED"} for item in projects
        ),
        project_in_progress=sum(
            item.current_status not in {"DELIVERED", "ACCEPTED"} for item in projects
        ),
        project_awaiting_acceptance=sum(
            item.current_status == "DELIVERED" and item.id in awaiting_acceptance_ids
            for item in projects
        ),
        project_pending_products=pending_product_count,
        project_pending_points=pending_point_count,
        projects_by_status=project_status_counts,
        projects_by_client=project_client_counts,
    )


@router.get("/agent-activities", response_model=list[AgentActivityRead])
def list_agent_activities(
    user_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[AgentActivity]:
    permissions = set(effective_permissions(db, user).permissions)
    target_user_id = user_id if "dashboard.manager" in permissions and user_id else user.id
    return list(
        db.scalars(
            select(AgentActivity)
            .where(AgentActivity.user_id == target_user_id)
            .order_by(AgentActivity.occurred_at.desc())
            .limit(100)
        )
    )


@router.post(
    "/agent-activities", response_model=AgentActivityRead, status_code=status.HTTP_201_CREATED
)
def create_agent_activity(
    data: AgentActivityCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> AgentActivity:
    permissions = set(effective_permissions(db, user).permissions)
    if not ({"dashboard.agent", "dashboard.manager"} & permissions):
        raise AuthorizationError()
    if data.user_id != user.id and "dashboard.manager" not in permissions:
        raise AuthorizationError("Only managers can log activity for another employee.")
    employee = db.get(User, data.user_id)
    if not employee or not employee.is_active or employee.user_type != "EMPLOYEE":
        raise NotFoundError("Employee does not exist or is inactive.")
    item = AgentActivity(**data.model_dump(), logged_by_user_id=user.id)
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=user.id,
            entity_type="AgentActivity",
            entity_id=str(item.id),
            action="agent.activity.created",
            new_values_json=json.dumps(
                {
                    "user_id": item.user_id,
                    "activity_type": item.activity_type,
                    "participation_role": item.participation_role,
                }
            ),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/ticket-grid-preference", response_model=TicketGridPreferenceData)
def ticket_grid_preference(
    db: Session = Depends(get_db), user: User = Depends(current_user)
) -> TicketGridPreferenceData:
    item = db.get(TicketGridPreference, user.id)
    if not item:
        return TicketGridPreferenceData()
    return TicketGridPreferenceData(
        columns=json.loads(item.columns_json or "[]"),
        column_widths=json.loads(item.column_widths_json or "{}"),
        density=item.density,
        page_size=item.page_size,
        sort_by=item.sort_by,
        sort_direction=item.sort_direction,
        group_by=item.group_by,
        default_view_mode=item.default_view_mode,
        selected_group_values=json.loads(item.selected_group_values_json or "[]"),
        board_settings=json.loads(item.board_settings_json or "{}"),
    )


@router.put("/ticket-grid-preference", response_model=TicketGridPreferenceData)
def update_ticket_grid_preference(
    data: TicketGridPreferenceData,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> TicketGridPreferenceData:
    item = db.get(TicketGridPreference, user.id)
    if not item:
        item = TicketGridPreference(user_id=user.id)
        db.add(item)
    item.columns_json = json.dumps(data.columns)
    item.column_widths_json = json.dumps(data.column_widths)
    item.density = data.density
    item.page_size = data.page_size
    item.sort_by = data.sort_by
    item.sort_direction = data.sort_direction
    item.group_by = data.group_by
    item.default_view_mode = data.default_view_mode
    item.selected_group_values_json = json.dumps(data.selected_group_values)
    item.board_settings_json = json.dumps(data.board_settings)
    db.commit()
    return data


@router.get("/saved-views", response_model=list[SavedViewRead])
def saved_views(
    db: Session = Depends(get_db), user: User = Depends(current_user)
) -> list[SavedView]:
    team_ids = set(
        db.scalars(
            select(SupportTeam.id)
            .outerjoin(SupportTeamMember, SupportTeamMember.team_id == SupportTeam.id)
            .where(
                SupportTeam.is_active.in_([True]),
                or_(
                    SupportTeamMember.user_id == user.id,
                    SupportTeam.leader_user_id == user.id,
                ),
            )
        )
    )
    return list(
        db.scalars(
            select(SavedView)
            .where(
                SavedView.is_active.in_([True]),
                or_(
                    SavedView.owner_user_id == user.id,
                    SavedView.scope == "GLOBAL",
                    SavedView.team_id.in_(team_ids or [-1]),
                    SavedView.department_id == user.department_id,
                ),
            )
            .order_by(SavedView.name)
        )
    )


@router.post("/saved-views/department-defaults", response_model=list[SavedViewRead])
def create_department_default_views(
    db: Session = Depends(get_db), user: User = Depends(current_user)
) -> list[SavedView]:
    presets = (
        ("My Tickets", {"assigned_user_id": str(user.id), "open_only": "true"}),
        (
            "My Team Requests",
            {"my_teams_only": "true", "department_requests_only": "true", "open_only": "true"},
        ),
        (
            "My Department Requests",
            {
                "my_department_requests": "true",
                "department_requests_only": "true",
                "open_only": "true",
            },
        ),
        (
            "New Department Requests",
            {
                "my_department_requests": "true",
                "department_requests_only": "true",
                "routing_status": "NEW",
            },
        ),
        (
            "Department Work In Progress",
            {
                "my_department_requests": "true",
                "department_requests_only": "true",
                "routing_status": "IN_PROGRESS",
            },
        ),
        ("Escalations Sent", {"escalations_sent_only": "true"}),
        ("Resolved / Returned", {"department_requests_only": "true", "routing_status": "RETURNED"}),
    )
    existing = {
        item.name: item
        for item in db.scalars(select(SavedView).where(SavedView.owner_user_id == user.id))
    }
    result: list[SavedView] = []
    for name, filters in presets:
        item = existing.get(name)
        if not item:
            item = SavedView(
                owner_user_id=user.id,
                name=name,
                scope="PRIVATE",
                filter_json=json.dumps(filters),
                columns_json=json.dumps([]),
                sort_json=json.dumps([{"field": "updated_at", "direction": "desc"}]),
            )
            db.add(item)
        else:
            item.filter_json = json.dumps(filters)
            item.is_active = True
        result.append(item)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=user.id,
            entity_type="SavedView",
            entity_id="department-defaults",
            action="saved_view.department_defaults.created",
        )
    )
    db.commit()
    for item in result:
        db.refresh(item)
    return result


@router.post("/saved-views", response_model=SavedViewRead, status_code=status.HTTP_201_CREATED)
def create_view(
    data: SavedViewCreate, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> SavedView:
    permissions = set(effective_permissions(db, user).permissions)
    if data.scope == "GLOBAL" and "configuration.manage" not in permissions:
        raise AuthorizationError()
    if data.scope == "TEAM":
        team = db.get(SupportTeam, data.team_id)
        is_member = db.scalar(
            select(SupportTeamMember.user_id).where(
                SupportTeamMember.team_id == data.team_id,
                SupportTeamMember.user_id == user.id,
            )
        )
        if (
            not team
            or not team.is_active
            or not (
                team.leader_user_id == user.id or is_member or "configuration.manage" in permissions
            )
        ):
            raise AuthorizationError("You may only share a view with one of your teams.")
    if data.scope == "DEPARTMENT" and (
        user.department_id != data.department_id
        or not ({"ticket.view.department", "configuration.manage"} & permissions)
    ):
        raise AuthorizationError("You may only share a view with your department.")
    if data.is_default:
        db.query(SavedView).filter(SavedView.owner_user_id == user.id).update(
            {SavedView.is_default: False}
        )
    item = db.scalar(
        select(SavedView).where(
            SavedView.owner_user_id == user.id,
            SavedView.name == data.name,
        )
    )
    if item and item.is_active:
        raise ConflictError("DUPLICATE_VIEW", "A saved view with that name already exists.")
    if item:
        # Soft-deleted rows still participate in the owner/name unique
        # constraint. Reuse the inactive row so its name becomes available
        # again without discarding the audit trail.
        item.team_id = data.team_id
        item.department_id = data.department_id
        item.scope = data.scope
        item.filter_json = json.dumps(data.filters)
        item.columns_json = json.dumps(data.columns)
        item.sort_json = json.dumps(data.sort)
        item.has_layout = data.has_layout
        item.is_default = data.is_default
        item.is_active = True
    else:
        item = SavedView(
            owner_user_id=user.id,
            team_id=data.team_id,
            department_id=data.department_id,
            name=data.name,
            scope=data.scope,
            filter_json=json.dumps(data.filters),
            columns_json=json.dumps(data.columns),
            sort_json=json.dumps(data.sort),
            has_layout=data.has_layout,
            is_default=data.is_default,
        )
        db.add(item)
    try:
        db.flush()
        if data.is_default:
            user.default_saved_view_id = item.id
        db.add(
            AuditLog(
                actor_user_id=user.id,
                entity_type="SavedView",
                entity_id=str(item.id),
                action="saved_view.created",
                new_values_json=json.dumps(
                    {
                        "name": item.name,
                        "scope": item.scope,
                        "team_id": item.team_id,
                        "department_id": item.department_id,
                    }
                ),
            )
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "DUPLICATE_VIEW", "A saved view with that name already exists."
        ) from exc
    db.refresh(item)
    return item


@router.put("/saved-views/{view_id}", response_model=SavedViewRead)
def update_view(
    view_id: int,
    data: SavedViewUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> SavedView:
    item = db.scalar(
        select(SavedView).where(
            SavedView.id == view_id,
            SavedView.owner_user_id == user.id,
            SavedView.is_active.in_([True]),
        )
    )
    if not item:
        raise NotFoundError("Saved view does not exist or cannot be edited.")
    permissions = set(effective_permissions(db, user).permissions)
    if data.scope == "GLOBAL" and "configuration.manage" not in permissions:
        raise AuthorizationError()
    if data.scope == "DEPARTMENT" and (
        data.department_id != user.department_id
        or not ({"ticket.view.department", "configuration.manage"} & permissions)
    ):
        raise AuthorizationError("You may only share a view with your department.")
    if data.scope == "TEAM":
        team = db.get(SupportTeam, data.team_id)
        is_member = db.scalar(
            select(SupportTeamMember.user_id).where(
                SupportTeamMember.team_id == data.team_id,
                SupportTeamMember.user_id == user.id,
            )
        )
        if not team or not team.is_active or not (
            team.leader_user_id == user.id or is_member or "configuration.manage" in permissions
        ):
            raise AuthorizationError("You may only share a view with one of your teams.")
    was_default = user.default_saved_view_id == item.id
    if data.is_default:
        db.query(SavedView).filter(SavedView.owner_user_id == user.id).update(
            {SavedView.is_default: False}
        )
    item.name = data.name
    item.scope = data.scope
    item.team_id = data.team_id
    item.department_id = data.department_id
    item.filter_json = json.dumps(data.filters)
    item.columns_json = json.dumps(data.columns)
    item.sort_json = json.dumps(data.sort)
    item.has_layout = data.has_layout
    item.is_default = data.is_default
    if data.is_default:
        user.default_saved_view_id = item.id
    elif was_default:
        user.default_saved_view_id = None
    db.add(
        AuditLog(
            actor_user_id=user.id,
            entity_type="SavedView",
            entity_id=str(item.id),
            action="saved_view.updated",
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "DUPLICATE_VIEW", "A saved view with that name already exists."
        ) from exc
    db.refresh(item)
    return item


@router.patch("/saved-views/{view_id}/default", response_model=SavedViewRead)
def set_default_view(
    view_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> SavedView:
    item = db.scalar(
        select(SavedView).where(
            SavedView.id == view_id,
            SavedView.owner_user_id == user.id,
            SavedView.is_active.in_([True]),
        )
    )
    if not item:
        raise NotFoundError("Saved view does not exist.")
    db.query(SavedView).filter(SavedView.owner_user_id == user.id).update(
        {SavedView.is_default: False}
    )
    item.is_default = True
    user.default_saved_view_id = item.id
    db.add(
        AuditLog(
            actor_user_id=user.id,
            entity_type="SavedView",
            entity_id=str(item.id),
            action="saved_view.defaulted",
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.delete("/saved-views/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_view(
    view_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> Response:
    item = db.get(SavedView, view_id)
    if not item or not item.is_active:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    permissions = set(effective_permissions(db, user).permissions)
    if item.owner_user_id != user.id and not (
        item.scope == "GLOBAL" and "configuration.manage" in permissions
    ):
        raise AuthorizationError()
    if item.owner_user_id == user.id and user.default_saved_view_id == item.id:
        user.default_saved_view_id = None
    item.is_active = False
    db.add(
        AuditLog(
            actor_user_id=user.id,
            entity_type="SavedView",
            entity_id=str(item.id),
            action="saved_view.deleted",
        )
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
