import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_any_permission, require_permission
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import (
    Account,
    Branch,
    BranchDepartmentAssignment,
    Client,
    ClientDepartmentAssignment,
    Organization,
    OrganizationDepartmentAssignment,
)
from app.modules.customer_structure.policies import direct_scope_assignments, resolve_scope
from app.modules.customer_structure.schemas import (
    AccountCreate,
    AccountRead,
    AccountUpdate,
    DepartmentPolicyImpactRead,
    DepartmentPolicyRead,
    DepartmentPolicyWrite,
    EffectiveDepartmentAccessRead,
    OrganizationClientBulkAssign,
    OrganizationClientBulkAssignResult,
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)
from app.modules.iam.models import AuditLog, Department, User

router = APIRouter(tags=["customer structure"])

POLICY_MODELS = {
    "ORGANIZATION": (Organization, OrganizationDepartmentAssignment, "organization_id"),
    "CLIENT": (Client, ClientDepartmentAssignment, "client_id"),
    "BRANCH": (Branch, BranchDepartmentAssignment, "branch_id"),
}


def _validate_department(db: Session, department_id: int | None) -> None:
    if department_id is None:
        return
    department = db.get(Department, department_id)
    if not department or not department.is_active:
        raise ConflictError("INVALID_OWNER_DEPARTMENT", "Select an active owner department.")


def _audit(
    db: Session,
    actor_id: int,
    entity_type: str,
    entity_id: int,
    action: str,
    values: dict[str, object],
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor_id,
            entity_type=entity_type,
            entity_id=str(entity_id),
            action=action,
            new_values_json=json.dumps(values, default=str),
        )
    )


def _commit(db: Session, code: str, message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(code, message) from exc


def _policy_target(
    db: Session, scope_type: str, scope_id: int
) -> tuple[str, Any, type[Any], str]:
    normalized = scope_type.upper()
    definition = POLICY_MODELS.get(normalized)
    if definition is None:
        raise NotFoundError("Unsupported customer scope type.")
    entity_model, assignment_model, foreign_key_name = definition
    entity = db.get(entity_model, scope_id)
    if not entity:
        raise NotFoundError(f"{normalized.title()} does not exist.")
    return normalized, entity, assignment_model, foreign_key_name


def _validate_policy(db: Session, data: DepartmentPolicyWrite) -> None:
    department_ids = [item.department_id for item in data.assignments]
    if len(department_ids) != len(set(department_ids)):
        raise ConflictError(
            "DUPLICATE_DEPARTMENT_ASSIGNMENT",
            "A department can appear only once in the submitted policy.",
        )
    active_ids = set(
        db.scalars(
            select(Department.id).where(
                Department.id.in_(department_ids or [-1]), Department.is_active.in_([True])
            )
        )
    )
    if active_ids != set(department_ids):
        raise ConflictError(
            "INVALID_POLICY_DEPARTMENT", "Every policy department must be active."
        )
    if sum(item.relationship == "PRIMARY_OWNER" for item in data.assignments) > 1:
        raise ConflictError(
            "MULTIPLE_PRIMARY_DEPARTMENTS", "A policy can have only one primary department."
        )
    for item in data.assignments:
        if (
            item.effective_from
            and item.effective_until
            and item.effective_until <= item.effective_from
        ):
            raise ConflictError(
                "INVALID_POLICY_PERIOD", "Assignment end must be after its start."
            )


def _flush(db: Session, code: str, message: str) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(code, message) from exc


@router.get("/accounts", response_model=list[AccountRead])
def list_accounts(
    search: str | None = Query(default=None, max_length=100),
    active_only: bool = True,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> list[AccountRead]:
    counts = (
        select(Organization.account_id, func.count(Organization.id).label("count"))
        .group_by(Organization.account_id)
        .subquery()
    )
    statement = select(Account, func.coalesce(counts.c.count, 0)).outerjoin(
        counts, counts.c.account_id == Account.id
    )
    if active_only:
        statement = statement.where(Account.is_active.in_([True]))
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(or_(Account.code.like(term), Account.name.like(term)))
    rows = db.execute(statement.order_by(Account.name, Account.id)).all()
    return [
        AccountRead.model_validate(item).model_copy(update={"organization_count": count})
        for item, count in rows
    ]


@router.post("/accounts", response_model=AccountRead, status_code=201)
def create_account(
    data: AccountCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client.manage")),
) -> AccountRead:
    _validate_department(db, data.owner_department_id)
    item = Account(**data.model_dump())
    db.add(item)
    _flush(db, "DUPLICATE_ACCOUNT", "The account code is already in use.")
    _audit(db, actor.id, "Account", item.id, "account.created", data.model_dump())
    _commit(db, "DUPLICATE_ACCOUNT", "The account code is already in use.")
    db.refresh(item)
    return AccountRead.model_validate(item)


@router.patch("/accounts/{account_id}", response_model=AccountRead)
def update_account(
    account_id: int,
    data: AccountUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client.manage")),
) -> AccountRead:
    item = db.get(Account, account_id)
    if not item:
        raise NotFoundError("Account does not exist.")
    changes = data.model_dump(exclude_unset=True)
    if "owner_department_id" in changes:
        _validate_department(db, changes["owner_department_id"])
    for key, value in changes.items():
        setattr(item, key, value)
    _audit(db, actor.id, "Account", item.id, "account.updated", changes)
    _commit(db, "DUPLICATE_ACCOUNT", "The account code is already in use.")
    db.refresh(item)
    count = (
        db.scalar(select(func.count(Organization.id)).where(Organization.account_id == item.id))
        or 0
    )
    return AccountRead.model_validate(item).model_copy(update={"organization_count": count})


@router.get("/organizations", response_model=list[OrganizationRead])
def list_organizations(
    account_id: int | None = None,
    search: str | None = Query(default=None, max_length=100),
    active_only: bool = True,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> list[OrganizationRead]:
    counts = (
        select(Client.organization_id, func.count(Client.id).label("count"))
        .where(Client.organization_id.is_not(None))
        .group_by(Client.organization_id)
        .subquery()
    )
    statement = select(Organization, func.coalesce(counts.c.count, 0)).outerjoin(
        counts, counts.c.organization_id == Organization.id
    )
    if account_id is not None:
        statement = statement.where(Organization.account_id == account_id)
    if active_only:
        statement = statement.where(Organization.is_active.in_([True]))
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(Organization.code.like(term), Organization.name.like(term))
        )
    rows = db.execute(statement.order_by(Organization.name, Organization.id)).all()
    return [
        OrganizationRead.model_validate(item).model_copy(update={"client_count": count})
        for item, count in rows
    ]


@router.post("/organizations", response_model=OrganizationRead, status_code=201)
def create_organization(
    data: OrganizationCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client.manage")),
) -> OrganizationRead:
    if not db.get(Account, data.account_id):
        raise NotFoundError("Account does not exist.")
    _validate_department(db, data.owner_department_id)
    item = Organization(**data.model_dump())
    db.add(item)
    _flush(
        db,
        "DUPLICATE_ORGANIZATION",
        "The organization code is already used in this account.",
    )
    _audit(db, actor.id, "Organization", item.id, "organization.created", data.model_dump())
    _commit(
        db,
        "DUPLICATE_ORGANIZATION",
        "The organization code is already used in this account.",
    )
    db.refresh(item)
    return OrganizationRead.model_validate(item)


@router.patch("/organizations/{organization_id}", response_model=OrganizationRead)
def update_organization(
    organization_id: int,
    data: OrganizationUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client.manage")),
) -> OrganizationRead:
    item = db.get(Organization, organization_id)
    if not item:
        raise NotFoundError("Organization does not exist.")
    changes = data.model_dump(exclude_unset=True)
    if "account_id" in changes and not db.get(Account, changes["account_id"]):
        raise NotFoundError("Account does not exist.")
    if "owner_department_id" in changes:
        _validate_department(db, changes["owner_department_id"])
    for key, value in changes.items():
        setattr(item, key, value)
    _audit(db, actor.id, "Organization", item.id, "organization.updated", changes)
    _commit(
        db,
        "DUPLICATE_ORGANIZATION",
        "The organization code is already used in this account.",
    )
    db.refresh(item)
    count = db.scalar(select(func.count(Client.id)).where(Client.organization_id == item.id)) or 0
    return OrganizationRead.model_validate(item).model_copy(update={"client_count": count})


@router.post(
    "/organizations/{organization_id}/clients/bulk-assign",
    response_model=OrganizationClientBulkAssignResult,
)
def bulk_assign_clients_to_organization(
    organization_id: int,
    data: OrganizationClientBulkAssign,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client.manage")),
) -> OrganizationClientBulkAssignResult:
    organization = db.get(Organization, organization_id)
    if not organization:
        raise NotFoundError("Organization does not exist.")
    requested_ids = list(dict.fromkeys(data.client_ids))
    clients = list(db.scalars(select(Client).where(Client.id.in_(requested_ids))))
    clients_by_id = {item.id: item for item in clients}
    missing_ids = [client_id for client_id in requested_ids if client_id not in clients_by_id]
    if missing_ids:
        raise NotFoundError(f"Clients do not exist: {', '.join(map(str, missing_ids))}.")
    updated_count = 0
    for client_id in requested_ids:
        item = clients_by_id[client_id]
        previous_organization_id = item.organization_id
        if previous_organization_id == organization.id:
            continue
        item.organization_id = organization.id
        updated_count += 1
        _audit(
            db,
            actor.id,
            "Client",
            item.id,
            "client.organization_bulk_assigned",
            {
                "previous_organization_id": previous_organization_id,
                "organization_id": organization.id,
                "reason": data.reason,
            },
        )
    _commit(
        db,
        "CLIENT_ORGANIZATION_BULK_ASSIGN_FAILED",
        "The selected clients could not be assigned to the organization.",
    )
    return OrganizationClientBulkAssignResult(
        organization_id=organization.id,
        updated_count=updated_count,
        unchanged_count=len(requested_ids) - updated_count,
        client_ids=requested_ids,
    )


@router.get(
    "/customer-structure/{scope_type}/{scope_id}/department-policy",
    response_model=DepartmentPolicyRead,
)
def get_department_policy(
    scope_type: str,
    scope_id: int,
    effective_at: datetime | None = None,
    db: Session = Depends(get_db),
    viewer: User = Depends(
        require_any_permission("customer_structure.policy.view", "client.view")
    ),
) -> DepartmentPolicyRead:
    del viewer
    normalized, _entity, _assignment_model, _foreign_key_name = _policy_target(
        db, scope_type, scope_id
    )
    at = effective_at or datetime.now().astimezone()
    mode, assignments = resolve_scope(db, normalized, scope_id, at)
    direct_assignments = direct_scope_assignments(db, normalized, scope_id, at)
    return DepartmentPolicyRead(
        scope_type=normalized,
        scope_id=scope_id,
        mode=mode,
        effective_at=at,
        assignments=[EffectiveDepartmentAccessRead(**item.__dict__) for item in assignments],
        direct_assignments=[
            EffectiveDepartmentAccessRead(**item.__dict__) for item in direct_assignments
        ],
    )


@router.put(
    "/customer-structure/{scope_type}/{scope_id}/department-policy",
    response_model=DepartmentPolicyRead,
)
def replace_department_policy(
    scope_type: str,
    scope_id: int,
    data: DepartmentPolicyWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_any_permission("customer_structure.policy.manage", "client.manage")
    ),
) -> DepartmentPolicyRead:
    normalized, entity, assignment_model, foreign_key_name = _policy_target(
        db, scope_type, scope_id
    )
    _validate_policy(db, data)
    current_rows = list(
        db.scalars(
            select(assignment_model).where(
                getattr(assignment_model, foreign_key_name) == scope_id,
                assignment_model.is_active.in_([True]),
            )
        )
    )
    for row in current_rows:
        row.is_active = False
    entity.department_policy_mode = data.mode
    for assignment in data.assignments:
        db.add(
            assignment_model(
                **{foreign_key_name: scope_id},
                **assignment.model_dump(),
                created_by_user_id=actor.id,
                is_active=True,
            )
        )
    _audit(
        db,
        actor.id,
        normalized.title(),
        scope_id,
        "customer_structure.department_policy_replaced",
        {
            "mode": data.mode,
            "assignment_count": len(data.assignments),
            "change_reason": data.change_reason,
        },
    )
    _commit(db, "INVALID_DEPARTMENT_POLICY", "The department policy could not be saved.")
    return get_department_policy(normalized, scope_id, None, db, actor)


@router.post(
    "/customer-structure/{scope_type}/{scope_id}/department-policy/impact-preview",
    response_model=DepartmentPolicyImpactRead,
)
def preview_department_policy_impact(
    scope_type: str,
    scope_id: int,
    data: DepartmentPolicyWrite,
    db: Session = Depends(get_db),
    viewer: User = Depends(
        require_any_permission("customer_structure.policy.manage", "client.manage")
    ),
) -> DepartmentPolicyImpactRead:
    del viewer
    normalized, entity, _assignment_model, _foreign_key_name = _policy_target(
        db, scope_type, scope_id
    )
    _validate_policy(db, data)
    _mode, current = resolve_scope(db, normalized, scope_id)
    current_ids = {item.department_id for item in current}
    direct_ids = {item.department_id for item in data.assignments}
    proposed_ids = direct_ids if data.mode == "INHERIT" else current_ids | direct_ids
    affected_client_count = 1 if normalized == "CLIENT" else 0
    affected_branch_count = 1 if normalized == "BRANCH" else 0
    if normalized == "ORGANIZATION":
        client_ids = select(Client.id).where(Client.organization_id == entity.id)
        affected_client_count = db.scalar(select(func.count()).select_from(client_ids.subquery())) or 0
        affected_branch_count = (
            db.scalar(select(func.count(Branch.id)).where(Branch.client_id.in_(client_ids))) or 0
        )
    elif normalized == "CLIENT":
        affected_branch_count = (
            db.scalar(select(func.count(Branch.id)).where(Branch.client_id == entity.id)) or 0
        )
    return DepartmentPolicyImpactRead(
        scope_type=normalized,
        scope_id=scope_id,
        affected_client_count=affected_client_count,
        affected_branch_count=affected_branch_count,
        current_department_ids=sorted(current_ids),
        proposed_department_ids=sorted(proposed_ids),
        added_department_ids=sorted(proposed_ids - current_ids),
        retained_visibility_department_ids=(
            sorted(current_ids - direct_ids) if data.mode == "OVERRIDE" else []
        ),
    )
