from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.core.exceptions import NotFoundError
from app.modules.clients.models import (
    Branch,
    BranchDepartmentAssignment,
    Client,
    ClientDepartmentAssignment,
    ClientDepartmentLink,
    Organization,
    OrganizationDepartmentAssignment,
)
from app.modules.iam.models import Department


@dataclass(frozen=True)
class ResolvedAssignment:
    department_id: int
    department_name: str
    relationship: str
    access_profile: str
    source_type: str
    source_id: int
    inherited: bool
    visibility_only: bool
    effective_from: datetime | None
    effective_until: datetime | None
    reason: str | None


def _active_rows(
    db: Session, model: type[Any], foreign_key: Any, entity_id: int, at: datetime
) -> list[Any]:
    return list(
        db.scalars(
            select(model).where(
                foreign_key == entity_id,
                model.is_active.in_([True]),
                or_(model.effective_from.is_(None), model.effective_from <= at),
                or_(model.effective_until.is_(None), model.effective_until > at),
            )
        )
    )


def _named(
    db: Session, rows: list[Any], source_type: str, source_id: int
) -> list[ResolvedAssignment]:
    department_ids = {row.department_id for row in rows}
    names = {
        item.id: item.name
        for item in db.scalars(select(Department).where(Department.id.in_(department_ids or [-1])))
    }
    return [
        ResolvedAssignment(
            department_id=row.department_id,
            department_name=names.get(row.department_id, f"Department {row.department_id}"),
            relationship=row.relationship,
            access_profile=row.access_profile,
            source_type=source_type,
            source_id=source_id,
            inherited=False,
            visibility_only=False,
            effective_from=row.effective_from,
            effective_until=row.effective_until,
            reason=row.reason,
        )
        for row in rows
    ]


def _inherit(
    items: list[ResolvedAssignment], *, visibility_only: bool = False
) -> list[ResolvedAssignment]:
    return [
        ResolvedAssignment(
            **{
                **item.__dict__,
                "inherited": True,
                "visibility_only": visibility_only or item.visibility_only,
                "relationship": "VIEWER" if visibility_only else item.relationship,
                "access_profile": "CUSTOMER_VIEWER" if visibility_only else item.access_profile,
            }
        )
        for item in items
    ]


def _merge(*groups: list[ResolvedAssignment]) -> list[ResolvedAssignment]:
    merged: dict[int, ResolvedAssignment] = {}
    for group in groups:
        for item in group:
            existing = merged.get(item.department_id)
            if existing is None or (existing.visibility_only and not item.visibility_only):
                merged[item.department_id] = item
    return sorted(merged.values(), key=lambda item: (item.department_name, item.department_id))


def resolve_organization(
    db: Session, organization_id: int, at: datetime | None = None
) -> tuple[str, list[ResolvedAssignment]]:
    organization = db.get(Organization, organization_id)
    if not organization:
        raise NotFoundError("Organization does not exist.")
    effective_at = at or server_now()
    rows = _active_rows(
        db,
        OrganizationDepartmentAssignment,
        OrganizationDepartmentAssignment.organization_id,
        organization.id,
        effective_at,
    )
    return organization.department_policy_mode, _named(
        db, rows, "ORGANIZATION", organization.id
    )


def _legacy_client_assignments(db: Session, client: Client) -> list[ResolvedAssignment]:
    department_ids = set(
        db.scalars(
            select(ClientDepartmentLink.department_id).where(
                ClientDepartmentLink.client_id == client.id
            )
        )
    )
    if client.owner_department_id:
        department_ids.add(client.owner_department_id)
    names = {
        item.id: item.name
        for item in db.scalars(select(Department).where(Department.id.in_(department_ids or [-1])))
    }
    return [
        ResolvedAssignment(
            department_id=department_id,
            department_name=names.get(department_id, f"Department {department_id}"),
            relationship=(
                "PRIMARY_OWNER" if department_id == client.owner_department_id else "SHARED_OPERATOR"
            ),
            access_profile="CUSTOMER_MANAGER",
            source_type="CLIENT_LEGACY",
            source_id=client.id,
            inherited=False,
            visibility_only=False,
            effective_from=None,
            effective_until=None,
            reason="Existing client owner/shared department",
        )
        for department_id in sorted(department_ids)
    ]


def resolve_client(
    db: Session, client_id: int, at: datetime | None = None
) -> tuple[str, list[ResolvedAssignment]]:
    client = db.get(Client, client_id)
    if not client:
        raise NotFoundError("Client does not exist.")
    effective_at = at or server_now()
    inherited: list[ResolvedAssignment] = []
    if client.organization_id:
        _, organization_items = resolve_organization(db, client.organization_id, effective_at)
        inherited = _inherit(organization_items)
    direct = _named(
        db,
        _active_rows(
            db,
            ClientDepartmentAssignment,
            ClientDepartmentAssignment.client_id,
            client.id,
            effective_at,
        ),
        "CLIENT",
        client.id,
    )
    direct = _merge(_legacy_client_assignments(db, client), direct)
    if client.department_policy_mode == "INHERIT":
        resolved = inherited
    elif client.department_policy_mode == "OVERRIDE":
        resolved = _merge(_inherit(inherited, visibility_only=True), direct)
    else:
        resolved = _merge(inherited, direct)
    return client.department_policy_mode, resolved


def resolve_branch(
    db: Session, branch_id: int, at: datetime | None = None
) -> tuple[str, list[ResolvedAssignment]]:
    branch = db.get(Branch, branch_id)
    if not branch:
        raise NotFoundError("Branch does not exist.")
    effective_at = at or server_now()
    _, client_items = resolve_client(db, branch.client_id, effective_at)
    inherited = _inherit(client_items)
    direct = _named(
        db,
        _active_rows(
            db,
            BranchDepartmentAssignment,
            BranchDepartmentAssignment.branch_id,
            branch.id,
            effective_at,
        ),
        "BRANCH",
        branch.id,
    )
    if branch.department_policy_mode == "INHERIT":
        resolved = inherited
    elif branch.department_policy_mode == "OVERRIDE":
        resolved = _merge(_inherit(inherited, visibility_only=True), direct)
    else:
        resolved = _merge(inherited, direct)
    return branch.department_policy_mode, resolved


def resolve_scope(
    db: Session, scope_type: str, scope_id: int, at: datetime | None = None
) -> tuple[str, list[ResolvedAssignment]]:
    if scope_type == "ORGANIZATION":
        return resolve_organization(db, scope_id, at)
    if scope_type == "CLIENT":
        return resolve_client(db, scope_id, at)
    if scope_type == "BRANCH":
        return resolve_branch(db, scope_id, at)
    raise NotFoundError("Unsupported customer scope type.")


def direct_scope_assignments(
    db: Session, scope_type: str, scope_id: int, at: datetime | None = None
) -> list[ResolvedAssignment]:
    effective_at = at or server_now()
    definitions = {
        "ORGANIZATION": (
            OrganizationDepartmentAssignment,
            OrganizationDepartmentAssignment.organization_id,
        ),
        "CLIENT": (ClientDepartmentAssignment, ClientDepartmentAssignment.client_id),
        "BRANCH": (BranchDepartmentAssignment, BranchDepartmentAssignment.branch_id),
    }
    definition = definitions.get(scope_type)
    if definition is None:
        raise NotFoundError("Unsupported customer scope type.")
    model, foreign_key = definition
    rows = _active_rows(db, model, foreign_key, scope_id, effective_at)
    return _named(db, rows, scope_type, scope_id)
