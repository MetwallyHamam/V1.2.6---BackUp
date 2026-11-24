import io
import json
from collections import Counter
from datetime import date, datetime, time, timedelta
from typing import Any, cast

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, require_permission
from app.core.clock import server_now, server_timezone, server_today
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.client_portal.schemas import (
    PortalAnnouncement,
    PortalContractRead,
    PortalResolutionAction,
    PortalTicketRead,
)
from app.modules.clients.models import (
    Branch,
    Client,
    Contact,
    Product,
    ProductModule,
    ServiceCatalogItem,
    ServiceModuleLink,
)
from app.modules.clients.routes import create_contact
from app.modules.clients.schemas import ContactCreate, ContactRead
from app.modules.contracts.models import (
    BusinessCalendar,
    BusinessCalendarDay,
    Contract,
    ContractClientLink,
    ContractCoverage,
    ContractCoverageClient,
    SlaPolicy,
    SlaTarget,
    TicketSlaClock,
)
from app.modules.iam.models import AuditLog, User
from app.modules.iam.service import effective_permissions
from app.modules.internal_operations.models import InternalOperation, InternalOperationAssignee
from app.modules.knowledge_base.models import Article, ArticleClientLink
from app.modules.onboarding.models import OnboardingMaterial, OnboardingMaterialResource
from app.modules.onboarding.routes import portal_safe_url
from app.modules.service_management.models import (
    ChangeRequestDetail,
    MajorIncident,
    MajorIncidentTicketLink,
    MajorIncidentUpdate,
    Problem,
    ProblemKnowledgeLink,
    ProblemTicketLink,
)
from app.modules.sla.service import (
    attach_ticket_sla_evidence,
    first_dedicated_assignments,
    resolution_sla_results,
)
from app.modules.tickets.models import (
    Ticket,
    TicketComment,
    TicketStatus,
    TicketType,
)
from app.modules.tickets.satisfaction import (
    SatisfactionSubmit,
    ensure_satisfaction_survey,
    satisfaction_result,
    submit_satisfaction,
)
from app.modules.tickets.schemas import (
    PortalTicketCreate,
    TicketCommentCreate,
    TicketCommentRead,
    TicketTransition,
)
from app.modules.tickets.service import (
    create_ticket,
    ensure_ticket_access,
    transition_ticket,
    visible_ticket_query,
)
from app.modules.uat.models import DeploymentPlan, UatCycle

router = APIRouter(prefix="/portal", tags=["client portal"])


@router.get("/contracts/{contract_id}", response_model=PortalContractRead)
def portal_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> Contract:
    require_portal_user(user)
    client_ids = sorted(effective_permissions(db, user).client_scope_ids)
    contract = next((item for item in portal_contracts(db, client_ids) if item.id == contract_id), None)
    if contract is None:
        raise NotFoundError("Contract does not exist.")
    return contract


@router.get("/training-materials")
def portal_training_materials(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("portal.training.view")),
) -> list[dict[str, object]]:
    require_portal_user(user)
    materials = list(
        db.scalars(
            select(OnboardingMaterial)
            .where(
                OnboardingMaterial.is_active.in_([True]),
                OnboardingMaterial.show_in_client_portal.in_([True]),
            )
            .order_by(OnboardingMaterial.display_order, OnboardingMaterial.title)
        )
    )
    result: list[dict[str, object]] = []
    for material in materials:
        resources = [
            resource
            for resource in db.scalars(
                select(OnboardingMaterialResource)
                .where(
                    OnboardingMaterialResource.material_id == material.id,
                    OnboardingMaterialResource.is_active.in_([True]),
                )
                .order_by(OnboardingMaterialResource.display_order)
            )
            if portal_safe_url(resource.url)
        ]
        result.append(
            {
                "id": material.id,
                "title": material.title,
                "description": material.description,
                "required": material.is_required,
                "resources": [
                    {
                        "id": resource.id,
                        "name": resource.name,
                        "type": resource.resource_type,
                        "url": resource.url,
                    }
                    for resource in resources
                ],
            }
        )
    return result


def require_portal_user(user: User) -> None:
    if user.user_type != "CLIENT_PORTAL":
        raise AuthorizationError("This endpoint is available only to client portal users.")


def require_portal_client(db: Session, user: User, client_id: int) -> None:
    require_portal_user(user)
    if client_id not in effective_permissions(db, user).client_scope_ids:
        raise NotFoundError("Client does not exist.")


@router.get("/client-profile")
def get_portal_client_profile(
    client_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("portal.client_profile.view")),
) -> dict[str, object]:
    """Return a customer-safe profile for a client in the caller's portal scope."""
    require_portal_user(user)
    authorized_ids = effective_permissions(db, user).client_scope_ids
    if client_id is None:
        if not authorized_ids:
            raise NotFoundError("Client does not exist.")
        client_id = authorized_ids[0]
    require_portal_client(db, user, client_id)
    client = db.get(Client, client_id)
    if client is None:
        raise NotFoundError("Client does not exist.")
    clients = list(
        db.scalars(select(Client).where(Client.id.in_(authorized_ids)).order_by(Client.name))
    )
    branches = list(
        db.scalars(
            select(Branch)
            .where(Branch.client_id == client_id, Branch.is_active.in_([True]))
            .order_by(Branch.name)
        )
    )
    contacts = list(
        db.scalars(
            select(Contact)
            .where(Contact.client_id == client_id, Contact.is_active.in_([True]))
            .order_by(Contact.is_primary.desc(), Contact.full_name)
        )
    )
    visible_tickets = list(
        db.scalars(
            visible_ticket_query(db, user)
            .where(Ticket.client_id == client_id)
            .order_by(Ticket.created_at.desc())
        )
    )
    ticket_types = {item.id: item.code for item in db.scalars(select(TicketType))}
    incidents = [
        item for item in visible_tickets if ticket_types.get(item.ticket_type_id) == "INCIDENT"
    ]
    changes = [
        item
        for item in visible_tickets
        if ticket_types.get(item.ticket_type_id) == "CHANGE_REQUEST"
    ]
    uat_cycles = list(
        db.scalars(
            select(UatCycle)
            .where(UatCycle.client_id == client_id, UatCycle.portal_visible.in_([True]))
            .order_by(UatCycle.created_at.desc())
        )
    )
    deployments = list(
        db.scalars(
            select(DeploymentPlan)
            .where(
                DeploymentPlan.client_id == client_id,
                DeploymentPlan.client_visible.in_([True]),
            )
            .order_by(DeploymentPlan.created_at.desc())
        )
    )
    visible_ticket_ids = {item.id for item in visible_tickets}
    problem_ids = (
        set(
            db.scalars(
                select(ProblemTicketLink.problem_id).where(
                    ProblemTicketLink.ticket_id.in_(visible_ticket_ids)
                )
            )
        )
        if visible_ticket_ids
        else set()
    )
    problems = (
        list(db.scalars(select(Problem).where(Problem.id.in_(problem_ids)))) if problem_ids else []
    )
    ticket_statuses = {item.id: item.name for item in db.scalars(select(TicketStatus))}
    visible_ticket_by_id = {item.id: item for item in visible_tickets}
    problem_records: list[dict[str, object]] = []
    for problem in problems[:10]:
        linked_ticket_id = db.scalar(
            select(ProblemTicketLink.ticket_id)
            .where(
                ProblemTicketLink.problem_id == problem.id,
                ProblemTicketLink.ticket_id.in_(visible_ticket_ids),
            )
            .order_by(ProblemTicketLink.linked_at.desc())
        )
        linked_ticket = visible_ticket_by_id.get(linked_ticket_id) if linked_ticket_id else None
        if linked_ticket:
            problem_records.append(
                {
                    "id": problem.id,
                    "number": linked_ticket.ticket_number,
                    "title": linked_ticket.subject,
                    "status": problem.status,
                    "route": f"/portal/tickets/{linked_ticket.id}",
                }
            )
    lifecycle = {
        "uat": {
            "count": len(uat_cycles),
            "active": sum(item.status != "COMPLETED" for item in uat_cycles),
            "records": [
                {
                    "id": item.id,
                    "number": item.code,
                    "title": item.title,
                    "status": item.status,
                    "route": "/portal/uat",
                }
                for item in uat_cycles[:10]
            ],
        },
        "deployments": {
            "count": len(deployments),
            "active": sum(item.status != "COMPLETED" for item in deployments),
            "records": [
                {
                    "id": item.id,
                    "number": item.code,
                    "title": item.name,
                    "status": item.status,
                    "route": "/portal/uat",
                }
                for item in deployments[:10]
            ],
        },
        "incidents": {
            "count": len(incidents),
            "active": sum(item.closed_at is None for item in incidents),
            "records": [
                {
                    "id": item.id,
                    "number": item.ticket_number,
                    "title": item.subject,
                    "status": ticket_statuses.get(item.status_id, "Unknown"),
                    "route": f"/portal/tickets/{item.id}",
                }
                for item in incidents[:10]
            ],
        },
        "changes": {
            "count": len(changes),
            "active": sum(item.closed_at is None for item in changes),
            "records": [
                {
                    "id": item.id,
                    "number": item.ticket_number,
                    "title": item.subject,
                    "status": ticket_statuses.get(item.status_id, "Unknown"),
                    "route": f"/portal/tickets/{item.id}",
                }
                for item in changes[:10]
            ],
        },
        "problems": {
            "count": len(problems),
            "active": sum(item.status not in {"RESOLVED", "CLOSED"} for item in problems),
            "records": problem_records,
        },
    }
    return {
        "clients": [{"id": item.id, "code": item.code, "name": item.name} for item in clients],
        "client": {
            "id": client.id,
            "code": client.code,
            "name": client.name,
            "status": client.status.name,
            "timezone": client.timezone,
            "country": client.country,
            "zone": client.zone,
            "phone_number": client.phone_number,
            "email": client.email,
            "address": client.address,
            "support_started_at": client.support_started_at,
            "contract_service_status": client.contract_service_status,
        },
        "branches": [
            {
                "id": item.id,
                "code": item.code,
                "name": item.name,
                "country": item.country,
                "zone": item.zone,
                "phone_number": item.phone_number,
                "email": item.email,
                "address": item.address,
                "support_hours": item.support_hours,
                "timezone": item.timezone,
            }
            for item in branches
        ],
        "contacts": [
            {
                "id": item.id,
                "full_name": item.full_name,
                "email": item.email,
                "phone_number": item.phone_number,
                "job_title": item.job_title,
                "contact_role": item.contact_role,
                "is_primary": item.is_primary,
                "is_escalation_contact": item.is_escalation_contact,
            }
            for item in contacts
        ],
        "lifecycle": lifecycle,
    }


@router.get("/callers", response_model=list[ContactRead])
def list_portal_callers(
    client_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("portal.caller.manage")),
) -> list[Contact]:
    require_portal_client(db, user, client_id)
    return list(
        db.scalars(
            select(Contact)
            .where(Contact.client_id == client_id, Contact.is_active.in_([True]))
            .order_by(Contact.full_name)
        )
    )


@router.post("/callers", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
def create_portal_caller(
    data: ContactCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("portal.caller.manage")),
) -> Contact:
    require_portal_client(db, user, data.client_id)
    # Use the governed CRM creation path after enforcing the portal client scope.
    return create_contact(data=data, db=db, actor=user)


def portal_contracts(db: Session, client_ids: list[int]) -> list[Contract]:
    if not client_ids:
        return []
    today = server_today()
    return list(
        db.scalars(
            select(Contract)
            .where(
                or_(
                    Contract.applies_to_all_clients.in_([True]),
                    Contract.client_id.in_(client_ids),
                    Contract.client_links.any(ContractClientLink.client_id.in_(client_ids)),
                ),
                Contract.is_active.in_([True]),
                Contract.status == "ACTIVE",
                Contract.start_date <= today,
                Contract.end_date >= today,
            )
            .order_by(Contract.end_date)
        )
    )


def portal_coverage_rows(
    db: Session, contracts: list[Contract], client_ids: list[int]
) -> list[ContractCoverage]:
    if not contracts:
        return []
    return list(
        db.scalars(
            select(ContractCoverage).where(
                ContractCoverage.contract_id.in_([item.id for item in contracts]),
                or_(
                    ~ContractCoverage.client_links.any(),
                    ContractCoverage.client_links.any(
                        ContractCoverageClient.client_id.in_(client_ids)
                    ),
                ),
            )
        )
    )


@router.get("/catalog")
def get_portal_catalog(
    client_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    require_portal_user(user)
    authorized_client_ids = effective_permissions(db, user).client_scope_ids
    if client_id is None and len(authorized_client_ids) == 1:
        client_id = authorized_client_ids[0]
    if client_id is not None and client_id not in authorized_client_ids:
        raise NotFoundError("Client does not exist.")
    client_ids = [client_id] if client_id is not None else authorized_client_ids
    client_rows = (
        list(
            db.scalars(
                select(Client).where(Client.id.in_(authorized_client_ids)).order_by(Client.name)
            )
        )
        if authorized_client_ids
        else []
    )
    contracts = portal_contracts(db, client_ids)
    candidate_products = list(
        db.scalars(select(Product).where(Product.is_active.in_([True])).order_by(Product.name))
    )
    candidate_modules = list(
        db.scalars(
            select(ProductModule)
            .where(ProductModule.is_active.in_([True]))
            .order_by(ProductModule.name)
        )
    )
    candidate_services = list(
        db.scalars(
            select(ServiceCatalogItem)
            .where(ServiceCatalogItem.is_active.in_([True]))
            .order_by(ServiceCatalogItem.name)
        )
    )
    rows = portal_coverage_rows(db, contracts, client_ids)
    if not contracts:
        return {
            "client_ids": authorized_client_ids,
            "clients": [
                {"id": item.id, "code": item.code, "name": item.name} for item in client_rows
            ],
            "selected_client_id": client_id,
            "visibility_mode": "CONTRACT_ONLY",
            "products": [],
            "modules": [],
            "services": [],
        }
    contracts_with_rows = {row.contract_id for row in rows}
    blanket = any(contract.id not in contracts_with_rows for contract in contracts) or any(
        row.is_covered
        and all(
            getattr(row, field) is None
            for field in (
                "product_id",
                "product_module_id",
                "branch_id",
                "environment_id",
                "service_id",
                "ticket_type_id",
            )
        )
        for row in rows
    )
    product_ids = {row.product_id for row in rows if row.is_covered and row.product_id}
    module_ids = {row.product_module_id for row in rows if row.is_covered and row.product_module_id}
    service_ids = {row.service_id for row in rows if row.is_covered and row.service_id}
    excluded_product_ids = {row.product_id for row in rows if not row.is_covered and row.product_id}
    excluded_module_ids = {
        row.product_module_id for row in rows if not row.is_covered and row.product_module_id
    }
    excluded_service_ids = {row.service_id for row in rows if not row.is_covered and row.service_id}
    for row in rows:
        if row.is_covered and row.product_id and row.product_module_id is None:
            module_ids.update(
                item.id for item in candidate_modules if item.product_id == row.product_id
            )
    show_all = any(
        item.ticket_catalog_visibility == "ALL_WITH_COVERAGE_STATUS" for item in contracts
    )

    def product_covered(item: Product) -> bool:
        return (blanket or item.id in product_ids) and item.id not in excluded_product_ids

    def module_covered(item: ProductModule) -> bool:
        return (blanket or item.id in module_ids) and item.id not in excluded_module_ids

    def service_covered(item: ServiceCatalogItem) -> bool:
        return (blanket or item.id in service_ids) and item.id not in excluded_service_ids

    products = [item for item in candidate_products if show_all or product_covered(item)]
    modules = [item for item in candidate_modules if show_all or module_covered(item)]
    services = [item for item in candidate_services if show_all or service_covered(item)]
    return {
        "client_ids": authorized_client_ids,
        "clients": [{"id": item.id, "code": item.code, "name": item.name} for item in client_rows],
        "selected_client_id": client_id,
        "visibility_mode": "ALL_WITH_COVERAGE_STATUS" if show_all else "CONTRACT_ONLY",
        "products": [
            {"id": item.id, "name": item.name, "covered": product_covered(item)}
            for item in products
        ],
        "modules": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "name": item.name,
                "covered": module_covered(item),
            }
            for item in modules
        ],
        "services": [
            {
                "id": item.id,
                "name": item.name,
                "covered": service_covered(item),
                "module_ids": item.module_ids,
            }
            for item in services
        ],
    }


@router.get("/contract-insights")
def portal_contract_insights(
    date_from: date | None = None,
    date_to: date | None = None,
    client_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    access = effective_permissions(db, user)
    if user.user_type == "CLIENT_PORTAL":
        client_ids = access.client_scope_ids
    elif client_id is not None and (
        {"contract.view", "client.profile.view"} & set(access.permissions)
    ):
        if not db.get(Client, client_id):
            raise NotFoundError("Client does not exist.")
        client_ids = [client_id]
    else:
        raise AuthorizationError()
    contracts = portal_contracts(db, client_ids)
    rows = portal_coverage_rows(db, contracts, client_ids)
    contract_ids = [item.id for item in contracts]
    today = server_today()
    date_from = date_from or today.replace(day=1)
    date_to = date_to or today
    period_start = datetime.combine(date_from, time.min, server_timezone())
    period_end = datetime.combine(date_to + timedelta(days=1), time.min, server_timezone())
    tickets = (
        list(
            db.scalars(
                select(Ticket).where(
                    Ticket.client_id.in_(client_ids),
                    Ticket.created_at >= period_start,
                    Ticket.created_at < period_end,
                )
            )
        )
        if client_ids
        else []
    )
    # Older and imported tickets can have no contract_id. They still form part
    # of the scoped client's support history and renewal evidence.
    contract_tickets = tickets
    statuses = {item.id: item for item in db.scalars(select(TicketStatus))}
    types = {item.id: item for item in db.scalars(select(TicketType))}
    clocks = (
        list(
            db.scalars(
                select(TicketSlaClock).where(
                    TicketSlaClock.ticket_id.in_([item.id for item in contract_tickets])
                )
            )
        )
        if contract_tickets
        else []
    )
    clocks_by_ticket: dict[int, list[TicketSlaClock]] = {}
    for clock in clocks:
        clocks_by_ticket.setdefault(clock.ticket_id, []).append(clock)
    closed = [
        item
        for item in contract_tickets
        if statuses.get(item.status_id) and statuses[item.status_id].is_closed_state
    ]
    bulk_sla_results = resolution_sla_results(db, contract_tickets)
    sla_results = {
        item.id: bulk_sla_results[item.id]
        for item in contract_tickets
        if statuses.get(item.status_id)
        and statuses[item.status_id].code in {"RESOLVED", "CLOSED"}
        and (item.resolved_at or item.closed_at)
        and item.id in bulk_sla_results
    }
    evaluated = set(sla_results)
    breached = {ticket_id for ticket_id, result in sla_results.items() if not result.met}
    pending = [
        item
        for item in contract_tickets
        if statuses.get(item.status_id) and statuses[item.status_id].code.startswith("PENDING_")
    ]
    first_assignments = first_dedicated_assignments(db, [item.id for item in closed])
    lifecycle_hours = [
        (completed - started).total_seconds() / 3600
        for item in closed
        if (completed := item.closed_at or item.resolved_at) is not None
        and (started := first_assignments.get(item.id)) is not None
        and completed >= started
    ]
    operations = list(
        db.scalars(
            select(InternalOperation).where(
                InternalOperation.client_id.in_(client_ids or [-1]),
                InternalOperation.starts_at >= period_start,
                InternalOperation.starts_at < period_end,
                InternalOperation.status == "COMPLETED",
            )
        )
    )
    operation_ids = {item.id for item in operations}
    assignee_counts = Counter(
        db.scalars(
            select(InternalOperationAssignee.operation_id).where(
                InternalOperationAssignee.operation_id.in_(operation_ids or {-1})
            )
        )
    )
    operation_working_hours = round(
        sum(
            max(0.0, (item.ends_at - item.starts_at).total_seconds() / 3600)
            * max(1, assignee_counts[item.id])
            for item in operations
        ),
        1,
    )
    product_names = {item.id: item.name for item in db.scalars(select(Product))}
    module_names = {item.id: item.name for item in db.scalars(select(ProductModule))}
    service_names = {item.id: item.name for item in db.scalars(select(ServiceCatalogItem))}
    clients = (
        {item.id: item.name for item in db.scalars(select(Client).where(Client.id.in_(client_ids)))}
        if client_ids
        else {}
    )
    policy_ids = {item.sla_policy_id for item in contracts if item.sla_policy_id}
    policy_ids.update(
        db.scalars(select(SlaPolicy.id).where(SlaPolicy.contract_id.in_(contract_ids)))
        if contract_ids
        else []
    )
    targets = (
        list(db.scalars(select(SlaTarget).where(SlaTarget.policy_id.in_(policy_ids))))
        if policy_ids
        else []
    )
    calendar_ids = (
        {
            item.calendar_id
            for item in db.scalars(select(SlaPolicy).where(SlaPolicy.id.in_(policy_ids)))
        }
        if policy_ids
        else set()
    )
    calendar_rows = (
        {
            item.id: item
            for item in db.scalars(
                select(BusinessCalendar).where(BusinessCalendar.id.in_(calendar_ids))
            )
        }
        if calendar_ids
        else {}
    )
    calendar_days: dict[int, list[BusinessCalendarDay]] = {}
    if calendar_ids:
        for item in db.scalars(
            select(BusinessCalendarDay)
            .where(BusinessCalendarDay.calendar_id.in_(calendar_ids))
            .order_by(BusinessCalendarDay.weekday)
        ):
            calendar_days.setdefault(item.calendar_id, []).append(item)
    return {
        "clients": [{"id": key, "name": value} for key, value in clients.items()],
        "contracts": [
            {
                "id": item.id,
                "number": item.contract_number,
                "name": item.name,
                "start_date": item.start_date,
                "end_date": item.end_date,
                "days_to_expiry": (item.end_date - server_today()).days,
                "included_request_limit": item.included_request_limit,
                "support_summary": item.support_summary,
            }
            for item in contracts
        ],
        "coverage": {
            "products": sorted(
                {
                    product_names[row.product_id]
                    for row in rows
                    if row.is_covered and row.product_id in product_names
                }
            ),
            "modules": sorted(
                {
                    module_names[row.product_module_id]
                    for row in rows
                    if row.is_covered and row.product_module_id in module_names
                }
            ),
            "services": sorted(
                {
                    service_names[row.service_id]
                    for row in rows
                    if row.is_covered and row.service_id in service_names
                }
            ),
        },
        "sla_targets": [
            {
                "service": service_names.get(item.service_id, "All services")
                if item.service_id is not None
                else "All services",
                "priority": item.priority,
                "first_response_minutes": item.first_response_minutes,
                "resolution_minutes": item.resolution_minutes,
            }
            for item in targets
        ],
        "support_calendars": [
            {
                "id": calendar.id,
                "name": calendar.name,
                "timezone": calendar.timezone,
                "days": [
                    {
                        "weekday": day.weekday,
                        "start_time": day.start_time.strftime("%H:%M"),
                        "end_time": day.end_time.strftime("%H:%M"),
                        "is_working_day": day.is_working_day,
                    }
                    for day in calendar_days.get(calendar.id, [])
                ],
            }
            for calendar in calendar_rows.values()
        ],
        "metrics": {
            "total_requests": len(contract_tickets),
            "incident_count": sum(
                types.get(item.ticket_type_id) is not None
                and types[item.ticket_type_id].code == "INCIDENT"
                for item in contract_tickets
            ),
            "closed_count": len(closed),
            "pending_count": len(pending),
            "sla_evaluated": len(evaluated),
            "sla_met": len(evaluated - breached),
            "sla_breached": len(breached),
            "sla_compliance_percent": round(100 * len(evaluated - breached) / len(evaluated), 1)
            if evaluated
            else None,
            "total_resolution_lifecycle_hours": round(sum(lifecycle_hours), 1),
            "average_resolution_hours": round(sum(lifecycle_hours) / len(lifecycle_hours), 1)
            if lifecycle_hours
            else None,
            "feedback_count": 0,
            "average_feedback_rating": None,
            "saved_business_minutes": sum(result.saved_minutes for result in sla_results.values()),
            "saved_business_hours": round(
                sum(result.saved_minutes for result in sla_results.values()) / 60, 1
            ),
            "sla_target_business_hours": round(
                sum(result.target_minutes for result in sla_results.values()) / 60, 1
            ),
            "spent_business_hours": round(
                sum(result.accountable_minutes for result in sla_results.values()) / 60, 1
            ),
            "total_working_hours": round(
                sum(result.accountable_minutes for result in sla_results.values()) / 60
                + operation_working_hours,
                1,
            ),
            "sla_evidence_excluded": sum(1 for item in closed if item.id not in sla_results),
            "customer_pending_minutes_excluded": sum(
                result.customer_pending_minutes for result in sla_results.values()
            ),
            "millensys_pending_minutes_included": sum(
                result.millensys_pending_minutes for result in sla_results.values()
            ),
            "escalation_minutes": sum(result.escalation_minutes for result in sla_results.values()),
        },
        "period": {"date_from": date_from, "date_to": date_to},
        "ticket_sla_details": [
            {
                "ticket_id": item.id,
                "ticket_number": item.ticket_number,
                "subject": item.subject,
                "target_minutes": sla_results[item.id].target_minutes,
                "accountable_minutes": sla_results[item.id].accountable_minutes,
                "saved_minutes": sla_results[item.id].saved_minutes,
                "overrun_minutes": sla_results[item.id].overrun_minutes,
                "customer_pending_minutes": sla_results[item.id].customer_pending_minutes,
                "millensys_pending_minutes": sla_results[item.id].millensys_pending_minutes,
                "escalation_minutes": sla_results[item.id].escalation_minutes,
                "met": sla_results[item.id].met,
                "started_at": sla_results[item.id].started_at,
                "completed_at": sla_results[item.id].completed_at,
            }
            for item in contract_tickets
            if item.id in sla_results
        ],
        "calculation_methods": [
            {
                "name": "First-response SLA",
                "formula": "Ticket creation → first dedicated-engineer assignment",
                "details": "Automatic assignment to the shared Support account is ignored. Reassignment does not restart this clock.",
            },
            {
                "name": "Resolution SLA",
                "formula": "First dedicated-engineer assignment → ticket closure",
                "details": "Only contract-calendar business minutes count. Customer-pending time is excluded; Millensys-pending time remains included. Escalation follows the SLA policy.",
            },
            {
                "name": "Net business hours saved",
                "formula": "Resolution SLA target − accountable business time",
                "details": "Met tickets add positive time and breached tickets add negative time. The displayed total is the signed sum for eligible closed tickets.",
            },
            {
                "name": "Evidence eligibility",
                "formula": "Closed ticket + applicable SLA + recorded dedicated assignment",
                "details": "Incomplete historical records are excluded instead of estimating missing timestamps.",
            },
        ],
        "measurement_notes": [
            "First response ends, and accountable resolution begins, at the first dedicated-engineer assignment.",
            "Client satisfaction is not yet captured; feedback metrics remain unavailable until a rating workflow is added.",
        ],
    }


@router.get("/contract-report.xlsx")
def export_portal_contract_report(
    date_from: date | None = None,
    date_to: date | None = None,
    client_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> StreamingResponse:
    data: Any = portal_contract_insights(
        date_from=date_from, date_to=date_to, client_id=client_id, db=db, user=user
    )
    book = Workbook()
    summary = book.active
    assert summary is not None
    summary.title = "Executive Summary"
    summary.append(["Client Support & SLA Performance Report"])
    summary.append(["Period", f"{data['period']['date_from']} to {data['period']['date_to']}"])
    summary.append([])
    summary.append(["Metric", "Value"])
    labels = {
        "total_requests": "Total requests",
        "incident_count": "Incidents",
        "closed_count": "Closed",
        "pending_count": "Pending",
        "sla_met": "SLA met",
        "sla_breached": "SLA breached",
        "sla_compliance_percent": "SLA compliance %",
        "saved_business_hours": "Business hours saved",
        "customer_pending_minutes_excluded": "Customer pending minutes excluded",
        "millensys_pending_minutes_included": "Millensys pending minutes included",
        "escalation_minutes": "Escalation minutes",
    }
    metrics = data["metrics"]
    for key, label in labels.items():
        summary.append([label, metrics.get(key)])
    contracts_sheet = book.create_sheet("Contracts & Coverage")
    contracts_sheet.append(
        ["Contract", "Name", "Start", "End", "Days to expiry", "Support summary"]
    )
    for item in data["contracts"]:
        contracts_sheet.append(
            [
                item["number"],
                item["name"],
                item["start_date"],
                item["end_date"],
                item["days_to_expiry"],
                item["support_summary"],
            ]
        )
    details = book.create_sheet("SLA Ticket Detail")
    detail_headers = [
        "Ticket",
        "Subject",
        "Target min",
        "Accountable min",
        "Saved min",
        "Overrun min",
        "Customer pending",
        "Millensys pending",
        "Escalation",
        "Result",
    ]
    details.append(detail_headers)
    for item in data["ticket_sla_details"]:
        details.append(
            [
                item["ticket_number"],
                item["subject"],
                item["target_minutes"],
                item["accountable_minutes"],
                item["saved_minutes"],
                item["overrun_minutes"],
                item["customer_pending_minutes"],
                item["millensys_pending_minutes"],
                item["escalation_minutes"],
                "MET" if item["met"] else "BREACHED",
            ]
        )
    for sheet in book.worksheets:
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="145DA0")
        sheet.freeze_panes = "A2"
        for column in sheet.columns:
            letter = column[0].column_letter
            sheet.column_dimensions[letter].width = min(
                55, max(14, max(len(str(cell.value or "")) for cell in column) + 2)
            )
    stream = io.BytesIO()
    book.save(stream)
    stream.seek(0)
    filename = (
        f"client_support_report_{data['period']['date_from']}_{data['period']['date_to']}.xlsx"
    )
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/tickets", response_model=list[PortalTicketRead])
def list_portal_tickets(
    response: Response,
    search: str | None = Query(default=None, max_length=100),
    ticket_number: str | None = Query(default=None, max_length=100),
    status_id: int | None = None,
    product_id: int | None = None,
    product_module_id: int | None = None,
    service_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    timezone_offset_minutes: int = Query(default=0, ge=-840, le=840),
    view: str | None = Query(
        default=None, pattern="^(all|incident|closed|pending|sla-met|sla-breached)$"
    ),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[Ticket]:
    require_portal_user(user)
    statement = visible_ticket_query(db, user)
    if view == "incident":
        statement = statement.where(
            Ticket.ticket_type_id.in_(select(TicketType.id).where(TicketType.code == "INCIDENT"))
        )
    elif view == "closed":
        statement = statement.where(
            Ticket.status_id.in_(
                select(TicketStatus.id).where(TicketStatus.is_closed_state.in_([True]))
            )
        )
    elif view == "pending":
        statement = statement.where(
            Ticket.status_id.in_(select(TicketStatus.id).where(TicketStatus.code.like("PENDING_%")))
        )
    elif view in {"sla-met", "sla-breached"}:
        candidates = list(db.scalars(statement))
        bulk_results = resolution_sla_results(db, candidates)
        matching_ids = [
            candidate.id
            for candidate in candidates
            if (result := bulk_results.get(candidate.id))
            and result.met == (view == "sla-met")
        ]
        statement = statement.where(Ticket.id.in_(matching_ids or [-1]))
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where((Ticket.ticket_number.like(term)) | (Ticket.subject.like(term)))
    if ticket_number and (normalized_ticket_number := ticket_number.strip().lower()):
        statement = statement.where(
            func.lower(Ticket.ticket_number).like(f"%{normalized_ticket_number}%")
        )
    if status_id is not None:
        statement = statement.where(Ticket.status_id == status_id)
    if product_id is not None:
        statement = statement.where(Ticket.product_id == product_id)
    if product_module_id is not None:
        statement = statement.where(Ticket.product_module_id == product_module_id)
    if service_id is not None:
        statement = statement.where(Ticket.service_id == service_id)
    if date_from is not None:
        statement = statement.where(
            Ticket.created_at >= datetime.combine(date_from, time.min, server_timezone())
        )
    if date_to is not None:
        statement = statement.where(
            Ticket.created_at
            < datetime.combine(date_to + timedelta(days=1), time.min, server_timezone())
        )
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    response.headers["X-Total-Count"] = str(total)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
    tickets = list(
        db.scalars(
            statement.order_by(Ticket.updated_at.desc()).offset(offset).limit(limit)
        )
    )
    return attach_ticket_sla_evidence(db, tickets)


@router.get("/tickets/export.xlsx")
def export_portal_tickets(
    search: str | None = Query(default=None, max_length=100),
    status_id: int | None = None,
    ticket_number: str | None = Query(default=None, max_length=100),
    product_id: int | None = None,
    product_module_id: int | None = None,
    service_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    timezone_offset_minutes: int = Query(default=0, ge=-840, le=840),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> StreamingResponse:
    require_portal_user(user)
    statement = visible_ticket_query(db, user)
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where((Ticket.ticket_number.like(term)) | (Ticket.subject.like(term)))
    if ticket_number and (normalized_ticket_number := ticket_number.strip().lower()):
        statement = statement.where(
            func.lower(Ticket.ticket_number).like(f"%{normalized_ticket_number}%")
        )
    for column, value in (
        (Ticket.status_id, status_id),
        (Ticket.product_id, product_id),
        (Ticket.product_module_id, product_module_id),
        (Ticket.service_id, service_id),
    ):
        if value is not None:
            statement = statement.where(column == value)
    if date_from is not None:
        statement = statement.where(
            Ticket.created_at >= datetime.combine(date_from, time.min, server_timezone())
        )
    if date_to is not None:
        statement = statement.where(
            Ticket.created_at
            < datetime.combine(date_to + timedelta(days=1), time.min, server_timezone())
        )
    tickets = list(db.scalars(statement.order_by(Ticket.created_at.desc()).limit(10_000)))
    statuses = {x.id: x.name for x in db.scalars(select(TicketStatus)).all()}
    products = {x.id: x.name for x in db.scalars(select(Product)).all()}
    modules = {x.id: x.name for x in db.scalars(select(ProductModule)).all()}
    services = {x.id: x.name for x in db.scalars(select(ServiceCatalogItem)).all()}
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.title = "My Requests"
    sheet.append(["Client Portal - My Requests"])
    sheet.merge_cells("A1:J1")
    sheet["A1"].font = Font(size=16, bold=True, color="FFFFFF")
    sheet["A1"].fill = PatternFill("solid", fgColor="1565C0")
    sheet["A1"].alignment = Alignment(horizontal="center")
    sheet.append(["Exported", server_now().strftime("%Y-%m-%d %H:%M %z"), "Records", len(tickets)])
    headers = [
        "Ticket Number",
        "Subject",
        "Status",
        "Priority",
        "Product",
        "Module",
        "Service",
        "Created",
        "Updated",
        "Resolution",
    ]
    sheet.append(headers)
    for cell in sheet[3]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1976D2")
    for ticket in tickets:
        sheet.append(
            [
                ticket.ticket_number,
                ticket.subject,
                statuses.get(ticket.status_id, ""),
                ticket.priority,
                products.get(ticket.product_id, "") if ticket.product_id else "",
                modules.get(ticket.product_module_id, "") if ticket.product_module_id else "",
                services.get(ticket.service_id, "") if ticket.service_id else "",
                ticket.created_at.replace(tzinfo=None),
                ticket.updated_at.replace(tzinfo=None),
                ticket.resolution_summary or "",
            ]
        )
    sheet.freeze_panes = "A4"
    sheet.auto_filter.ref = f"A3:J{max(3, sheet.max_row)}"
    for excel_column, width in {
        "A": 18,
        "B": 45,
        "C": 20,
        "D": 10,
        "E": 24,
        "F": 24,
        "G": 24,
        "H": 20,
        "I": 20,
        "J": 45,
    }.items():
        sheet.column_dimensions[excel_column].width = width
    stream = io.BytesIO()
    book.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="my_requests_{server_today().isoformat()}.xlsx"'
        },
    )


@router.post("/tickets", response_model=PortalTicketRead, status_code=status.HTTP_201_CREATED)
def create_portal_ticket(
    data: PortalTicketCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("ticket.create")),
) -> Ticket:
    require_portal_user(user)
    if (
        data.requester_contact_id
        and "portal.caller.manage" not in effective_permissions(db, user).permissions
    ):
        raise AuthorizationError("You do not have permission to select a caller.")
    if data.creation_method != "MOSAIC" and data.service_id:
        linked_module_ids = set(
            db.scalars(
                select(ServiceModuleLink.product_module_id).where(
                    ServiceModuleLink.service_id == data.service_id
                )
            )
        )
        if linked_module_ids and data.product_module_id is None:
            raise ConflictError(
                "SERVICE_MODULE_REQUIRED",
                "The selected service requires a module. Select a compatible module before submitting.",
                {"allowed_module_ids": sorted(linked_module_ids)},
            )
    if data.creation_method == "MOSAIC":
        if not data.product_id or not data.product_module_id or not data.service_id:
            raise ConflictError(
                "MOSAIC_SELECTION_INCOMPLETE",
                "Select a product, module, and linked service before continuing.",
            )
        catalog = get_portal_catalog(client_id=data.client_id, db=db, user=user)

        def catalog_ids(key: str) -> set[int]:
            rows = cast(list[dict[str, object]], catalog[key])
            return {cast(int, row["id"]) for row in rows}

        if (
            data.product_id not in catalog_ids("products")
            or data.product_module_id not in catalog_ids("modules")
            or data.service_id not in catalog_ids("services")
        ):
            raise ConflictError(
                "MOSAIC_SELECTION_OUT_OF_SCOPE",
                "The selected Mosaic catalog path is no longer available for this client.",
            )
        linked = db.scalar(
            select(ServiceModuleLink.id).where(
                ServiceModuleLink.service_id == data.service_id,
                ServiceModuleLink.product_module_id == data.product_module_id,
            )
        )
        if linked is None:
            raise ConflictError(
                "MOSAIC_SERVICE_MODULE_MISMATCH",
                "The selected service is not linked to the selected module.",
            )
    ticket_type = db.get(TicketType, data.ticket_type_id)
    is_change = bool(ticket_type and ticket_type.code == "CHANGE_REQUEST")
    if is_change and data.change_request is None:
        raise ConflictError(
            "CHANGE_DETAILS_REQUIRED", "Complete the Change Request details before submitting."
        )
    if not is_change and data.change_request is not None:
        raise ConflictError(
            "CHANGE_REQUEST_TICKET_REQUIRED",
            "Change details are accepted only for the Change Request ticket type.",
        )
    source_channel = "MOSAIC" if data.creation_method == "MOSAIC" else "CLIENT_PORTAL"
    ticket = create_ticket(
        db, data.model_copy(update={"source_channel": source_channel}), user, commit=False
    )
    if (
        is_change
        and data.change_request
        and not db.scalar(
            select(ChangeRequestDetail.id).where(ChangeRequestDetail.ticket_id == ticket.id)
        )
    ):
        detail = ChangeRequestDetail(
            ticket_id=ticket.id,
            affected_product_id=ticket.product_id,
            affected_module_id=ticket.product_module_id,
            **data.change_request.model_dump(),
        )
        db.add(detail)
        db.flush()
        db.add(
            AuditLog(
                actor_user_id=user.id,
                entity_type="ChangeRequestDetail",
                entity_id=str(detail.id),
                action="change_request.created_from_portal",
                new_values_json=json.dumps(data.change_request.model_dump(), default=str),
            )
        )
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/tickets/{ticket_id}", response_model=PortalTicketRead)
def get_portal_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> Ticket:
    require_portal_user(user)
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    return attach_ticket_sla_evidence(db, [ticket])[0]


@router.get("/tickets/{ticket_id}/service-advisories")
def get_portal_ticket_service_advisories(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    """Return only explicitly client-safe Major-Incident and published Knowledge content."""
    require_portal_user(user)
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    major_rows = db.execute(
        select(MajorIncident, MajorIncidentUpdate)
        .join(
            MajorIncidentTicketLink, MajorIncidentTicketLink.major_incident_id == MajorIncident.id
        )
        .join(MajorIncidentUpdate, MajorIncidentUpdate.major_incident_id == MajorIncident.id)
        .where(
            MajorIncidentTicketLink.ticket_id == ticket_id,
            MajorIncidentUpdate.update_type == "CLIENT",
            MajorIncidentUpdate.client_message.is_not(None),
        )
        .order_by(MajorIncidentUpdate.published_at.desc())
    ).all()
    major_incidents: dict[int, dict[str, object]] = {}
    for incident, update in major_rows:
        item = major_incidents.setdefault(
            incident.id,
            {
                "id": incident.id,
                "major_incident_number": incident.major_incident_number,
                "severity": incident.severity,
                "status": incident.status,
                "updates": [],
            },
        )
        cast(list[dict[str, object]], item["updates"]).append(
            {"id": update.id, "message": update.client_message, "published_at": update.published_at}
        )
    knowledge_rows = db.execute(
        select(Problem, ProblemKnowledgeLink, Article)
        .join(ProblemTicketLink, ProblemTicketLink.problem_id == Problem.id)
        .join(ProblemKnowledgeLink, ProblemKnowledgeLink.problem_id == Problem.id)
        .join(Article, Article.id == ProblemKnowledgeLink.article_id)
        .where(
            ProblemTicketLink.ticket_id == ticket_id,
            ProblemKnowledgeLink.link_type.in_(["WORKAROUND", "PERMANENT_FIX"]),
            Article.status == "PUBLISHED",
            Article.client_visible.in_([True]),
            Article.visibility.in_(["CLIENT_PORTAL", "BOTH"]),
            or_(
                ~Article.client_links.any(),
                Article.client_links.any(ArticleClientLink.client_id == ticket.client_id),
            ),
        )
        .order_by(Article.updated_at.desc())
    ).all()
    return {
        "major_incidents": list(major_incidents.values()),
        "knowledge": [
            {
                "problem_number": problem.problem_number,
                "article_id": article.id,
                "link_type": link.link_type,
                "title": article.title,
                "summary": article.summary,
                "body": article.body,
                "updated_at": article.updated_at,
            }
            for problem, link, article in knowledge_rows
        ],
    }


@router.get("/tickets/{ticket_id}/comments", response_model=list[TicketCommentRead])
def list_portal_comments(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[TicketComment]:
    require_portal_user(user)
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    return list(
        db.scalars(
            select(TicketComment)
            .where(
                TicketComment.ticket_id == ticket_id,
                TicketComment.is_internal.in_([False]),
            )
            .order_by(TicketComment.created_at)
        )
    )


@router.post(
    "/tickets/{ticket_id}/comments",
    response_model=TicketCommentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_portal_comment(
    ticket_id: int,
    data: TicketCommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("ticket.comment.public")),
) -> TicketComment:
    require_portal_user(user)
    if data.is_internal:
        raise AuthorizationError()
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    if data.operation_key:
        previous = db.scalar(
            select(TicketComment).where(
                TicketComment.ticket_id == ticket_id,
                TicketComment.author_user_id == user.id,
                TicketComment.operation_key == data.operation_key,
            )
        )
        if previous:
            if previous.body == data.body and not previous.is_internal:
                return previous
            raise ConflictError(
                "COMMENT_IDEMPOTENCY_CONFLICT",
                "This comment key was already used with different content.",
            )
    comment = TicketComment(
        ticket_id=ticket_id,
        author_user_id=user.id,
        body=data.body,
        is_internal=False,
        operation_key=data.operation_key,
    )
    ticket.version += 1
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.post("/tickets/{ticket_id}/confirm", response_model=PortalTicketRead)
def confirm_resolution(
    ticket_id: int,
    data: PortalResolutionAction,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> Ticket:
    require_portal_user(user)
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    current = db.get(TicketStatus, ticket.status_id)
    if not current or current.code not in {"RESOLVED", "CLIENT_CONFIRMATION"}:
        raise ConflictError("CONFIRMATION_NOT_ALLOWED", "This ticket is not awaiting confirmation.")
    if current.code == "RESOLVED":
        ticket = transition_ticket(
            db,
            ticket,
            TicketTransition(
                to_status_code="CLIENT_CONFIRMATION",
                reason=data.reason or "Client accepted resolution",
                customer_confirmation_channel="PORTAL",
                customer_confirmation_contact=user.email,
                version=data.version,
            ),
            user,
            commit=False,
            additional_permissions={"ticket.change.status"},
            source="CLIENT_PORTAL",
        )
        data.version = ticket.version
    return transition_ticket(
        db,
        ticket,
        TicketTransition(
            to_status_code="CLOSED",
            reason=data.reason or "Client confirmed resolution",
            version=data.version,
        ),
        user,
        additional_permissions={"ticket.change.status", "ticket.close"},
        source="CLIENT_PORTAL",
    )


@router.post("/tickets/{ticket_id}/reopen", response_model=PortalTicketRead)
def reopen_ticket(
    ticket_id: int,
    data: PortalResolutionAction,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("ticket.reopen")),
) -> Ticket:
    require_portal_user(user)
    if not data.reason:
        raise ConflictError("REOPEN_REASON_REQUIRED", "A reopen reason is required.")
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    return transition_ticket(
        db,
        ticket,
        TicketTransition(
            to_status_code="REOPENED",
            reason=data.reason,
            version=data.version,
        ),
        user,
        additional_permissions={"ticket.change.status"},
        source="CLIENT_PORTAL",
    )


def _portal_satisfaction_ticket(
    db: Session, user: User, ticket_id: int, *, require_closed: bool = True
) -> Ticket:
    require_portal_user(user)
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    status_row = db.get(TicketStatus, ticket.status_id)
    if require_closed and (not status_row or status_row.code != "CLOSED"):
        raise ConflictError(
            "SATISFACTION_NOT_ELIGIBLE", "The ticket can be rated after it is closed."
        )
    return ticket


@router.get("/tickets/{ticket_id}/satisfaction")
def portal_ticket_satisfaction(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    ticket = _portal_satisfaction_ticket(db, user, ticket_id, require_closed=False)
    status_row = db.get(TicketStatus, ticket.status_id)
    if not status_row or status_row.code != "CLOSED":
        return {"state": "UNAVAILABLE"}
    survey = ensure_satisfaction_survey(db, ticket, user.email)
    db.commit()
    db.refresh(survey)
    return {
        "state": "SUBMITTED" if survey.submitted_at else "AVAILABLE",
        **(satisfaction_result(survey) if survey.submitted_at else {}),
    }


@router.post("/tickets/{ticket_id}/satisfaction")
def submit_portal_ticket_satisfaction(
    ticket_id: int,
    data: SatisfactionSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict[str, object]:
    ticket = _portal_satisfaction_ticket(db, user, ticket_id)
    survey = ensure_satisfaction_survey(db, ticket, user.email)
    result = submit_satisfaction(db, survey, data, source="CLIENT_PORTAL", actor_user_id=user.id)
    db.refresh(survey)
    return {**result, "state": "SUBMITTED", **satisfaction_result(survey)}


@router.get("/announcements", response_model=list[PortalAnnouncement])
def announcements(user: User = Depends(current_user)) -> list[PortalAnnouncement]:
    require_portal_user(user)
    return []
