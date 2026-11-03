import json
import re
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import delete, desc, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.api.dependencies import require_any_permission, require_permission
from app.core.clock import server_now
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.db.base import Base
from app.db.session import get_db
from app.modules.clients.credentials import decrypt_password, encrypt_password
from app.modules.clients.hierarchy import (
    get_ancestors,
    get_client_path,
    get_descendants,
    validate_parent_change,
)
from app.modules.clients.models import (
    Branch,
    City,
    Client,
    ClientAccessCredential,
    ClientDepartmentLink,
    ClientInstallation,
    ClientLocation,
    ClientStatus,
    Contact,
    ContactClientLink,
    Country,
    DeploymentIssueType,
    Environment,
    InstallationComponent,
    Product,
    ProductModule,
    ServiceCatalogItem,
    SupportSkill,
    SupportTeam,
    SupportTeamMember,
    SupportTeamSkill,
    TicketCategory,
    TicketSubcategory,
    Vendor,
)
from app.modules.clients.schemas import (
    BranchCreate,
    BranchRead,
    BranchUpdate,
    CatalogCreate,
    CatalogUpdate,
    CityCreate,
    CityRead,
    CityUpdate,
    ClientAccessCreate,
    ClientAccessRead,
    ClientAccessRevealResponse,
    ClientAccessUpdate,
    ClientCreate,
    ClientHierarchyNode,
    ClientHierarchyRead,
    ClientLocationCreate,
    ClientLocationRead,
    ClientPageRead,
    ClientRead,
    ClientStatusCreate,
    ClientStatusRead,
    ClientStatusUpdate,
    ClientTicketOptionRead,
    ClientUpdate,
    ContactCreate,
    ContactLinkCreate,
    ContactRead,
    ContactUpdate,
    CountryCreate,
    CountryRead,
    CountryUpdate,
    DeploymentIssueTypeCreate,
    DeploymentIssueTypeRead,
    DeploymentIssueTypeUpdate,
    EnvironmentCreate,
    EnvironmentRead,
    EnvironmentUpdate,
    InstallationCreate,
    InstallationRead,
    InstallationUpdate,
    ProductCreate,
    ProductModuleCreate,
    ProductModuleRead,
    ProductModuleUpdate,
    ProductRead,
    ProductUpdate,
    ServiceCreate,
    ServiceRead,
    ServiceUpdate,
    SupportCatalogCreate,
    SupportCatalogRead,
    SupportCatalogUpdate,
    TicketSubcategoryAdminCreate,
    TicketSubcategoryCreate,
    TicketSubcategoryRead,
    TicketSubcategoryUpdate,
    VendorCreate,
    VendorRead,
    VendorUpdate,
)
from app.modules.iam.models import AuditLog, Department, User
from app.modules.iam.service import effective_permissions

router = APIRouter(prefix="/clients", tags=["clients"])
catalog_router = APIRouter(tags=["CRM catalogs"])


def _generated_code(
    db: Session,
    model: type[Country] | type[City],
    name: str,
    length: int = 3,
    country_id: int | None = None,
) -> str:
    words = re.findall(r"[A-Za-z0-9]+", name.upper())
    base = "".join(word[0] for word in words) if len(words) > 1 else (words[0] if words else "ITEM")
    base = (base[:length] or "ITEM").ljust(length, "X")
    for sequence in range(10000):
        code = base if sequence == 0 else f"{base}{sequence}"
        statement = (
            select(model.id).where(model.code == code)
            if model is City
            else select(Country.id).where(Country.iso_alpha3 == code)
        )
        if model is City and country_id is not None:
            statement = statement.where(City.country_id == country_id)
        if not db.scalar(statement):
            return code
    raise ConflictError(
        "CODE_GENERATION_FAILED", "A unique master-data code could not be generated."
    )


def _generated_alpha2(db: Session, name: str) -> str:
    letters = "".join(character for character in name.upper() if character.isalpha()) or "XX"
    seed = (letters[:2]).ljust(2, "X")
    if not db.scalar(select(Country.id).where(Country.iso_alpha2 == seed)):
        return seed
    for first in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        for second in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            code = first + second
            if not db.scalar(select(Country.id).where(Country.iso_alpha2 == code)):
                return code
    raise ConflictError("CODE_GENERATION_FAILED", "A unique country code could not be generated.")


@catalog_router.get("/countries", response_model=list[CountryRead])
def list_countries(
    active_only: bool = True,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> list[Country]:
    statement = select(Country)
    if active_only:
        statement = statement.where(Country.is_active.in_([True]))
    return list(db.scalars(statement.order_by(Country.name)))


@catalog_router.post("/countries", response_model=CountryRead, status_code=201)
def create_country(
    data: CountryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.manage")),
) -> Country:
    values = data.model_dump(exclude={"city_name", "city_name_ar"})
    values["iso_alpha2"] = (
        data.iso_alpha2.upper() if data.iso_alpha2 else _generated_alpha2(db, data.name)
    )
    values["iso_alpha3"] = (
        data.iso_alpha3.upper() if data.iso_alpha3 else _generated_code(db, Country, data.name)
    )
    country = Country(**values)
    db.add(country)
    db.flush()
    if data.city_name:
        db.add(
            City(
                country_id=country.id,
                code=_generated_code(db, City, data.city_name, country_id=country.id),
                name=data.city_name,
                name_ar=data.city_name_ar,
                is_active=True,
            )
        )
    commit_or_conflict(db, "DUPLICATE_COUNTRY", "Country and city names must be unique.")
    db.refresh(country)
    return country


@catalog_router.patch("/countries/{country_id}", response_model=CountryRead)
def update_country(
    country_id: int,
    data: CountryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.manage")),
) -> Country:
    country = db.get(Country, country_id)
    if not country:
        raise NotFoundError("Country does not exist.")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(country, key, value)
    commit_or_conflict(db, "DUPLICATE_COUNTRY", "Country names must be unique.")
    db.refresh(country)
    return country


@catalog_router.get("/cities", response_model=list[CityRead])
def list_cities(
    country_id: int | None = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> list[City]:
    statement = select(City)
    if country_id:
        statement = statement.where(City.country_id == country_id)
    if active_only:
        statement = statement.where(City.is_active.in_([True]))
    return list(db.scalars(statement.order_by(City.name)))


@catalog_router.post("/cities", response_model=CityRead, status_code=201)
def create_city(
    data: CityCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.manage")),
) -> City:
    if not db.get(Country, data.country_id):
        raise NotFoundError("Country does not exist.")
    city = City(
        country_id=data.country_id,
        code=_generated_code(db, City, data.name, country_id=data.country_id),
        name=data.name,
        is_active=data.is_active,
    )
    db.add(city)
    commit_or_conflict(db, "DUPLICATE_CITY", "The city already exists for this country.")
    db.refresh(city)
    return city


@catalog_router.patch("/cities/{city_id}", response_model=CityRead)
def update_city(
    city_id: int,
    data: CityUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.manage")),
) -> City:
    city = db.get(City, city_id)
    if not city:
        raise NotFoundError("City does not exist.")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(city, key, value)
    commit_or_conflict(db, "DUPLICATE_CITY", "The city already exists for this country.")
    db.refresh(city)
    return city


@catalog_router.get("/client-locations", response_model=list[ClientLocationRead])
def list_all_client_locations(
    active_only: bool = True,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> list[ClientLocation]:
    statement = select(ClientLocation)
    if active_only:
        statement = statement.where(ClientLocation.is_active.in_([True]))
    return list(db.scalars(statement.order_by(ClientLocation.client_id, ClientLocation.name)))


@router.get("/{client_id}/locations", response_model=list[ClientLocationRead])
def list_client_locations(
    client_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> list[ClientLocation]:
    statement = select(ClientLocation).where(ClientLocation.client_id == client_id)
    if active_only:
        statement = statement.where(ClientLocation.is_active.in_([True]))
    return list(db.scalars(statement.order_by(ClientLocation.name)))


@router.post("/{client_id}/locations", response_model=ClientLocationRead, status_code=201)
def create_client_location(
    client_id: int,
    data: ClientLocationCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.manage")),
) -> ClientLocation:
    client = db.get(Client, client_id)
    country = db.get(Country, data.country_id)
    if not client or not country:
        raise NotFoundError("Client or country does not exist.")
    values = data.model_dump()
    requested_code = values.pop("code", None)
    location = ClientLocation(
        client_id=client_id,
        code=requested_code or f"PENDING-LOC-{server_now().timestamp()}",
        **values,
    )
    db.add(location)
    try:
        db.flush()
        if not requested_code:
            location.code = f"LOC-{location.id:06d}"
        if client.primary_location_id is None:
            client.primary_location_id = location.id
            client.country_id = country.id
            client.country = country.name
            client.zone = location.zone
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "DUPLICATE_LOCATION", "The location code is already used for this client."
        ) from exc
    db.refresh(location)
    return location


def audit(
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


def commit_or_conflict(db: Session, code: str, message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(code, message) from exc


def add_with_generated_code(
    db: Session, item: Any, requested_code: str | None, prefix: str
) -> None:
    item.code = requested_code or f"PENDING-{prefix}-{server_now().timestamp()}"
    db.add(item)
    db.flush()
    if not requested_code:
        item.code = f"{prefix}-{item.id:06d}"


@router.get("", response_model=list[ClientRead])
def list_clients(
    search: str | None = Query(default=None, max_length=100),
    active_only: bool = True,
    account_status: Literal["ACTIVE", "INACTIVE", "ALL"] | None = None,
    status_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> list[Client]:
    statement = select(Client)
    if account_status == "ACTIVE" or (account_status is None and active_only):
        statement = statement.where(Client.is_active.in_([True]))
    elif account_status == "INACTIVE":
        statement = statement.where(Client.is_active.in_([False]))
    if status_id is not None:
        statement = statement.where(Client.status_id == status_id)
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(or_(Client.code.like(term), Client.name.like(term)))
    statement = statement.order_by(Client.name).offset(offset).limit(limit)
    return list(db.scalars(statement))


@router.get("/search-page", response_model=ClientPageRead)
def search_clients_page(
    search: str | None = Query(default=None, max_length=100),
    active_only: bool = True,
    account_status: Literal["ACTIVE", "INACTIVE", "ALL"] | None = None,
    status_id: int | None = None,
    country_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> ClientPageRead:
    filters: list[ColumnElement[bool]] = []
    if account_status == "ACTIVE" or (account_status is None and active_only):
        filters.append(Client.is_active.in_([True]))
    elif account_status == "INACTIVE":
        filters.append(Client.is_active.in_([False]))
    if status_id is not None:
        filters.append(Client.status_id == status_id)
    if country_id is not None:
        clients_with_location = select(ClientLocation.client_id).where(
            ClientLocation.country_id == country_id
        )
        filters.append(or_(Client.country_id == country_id, Client.id.in_(clients_with_location)))
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(Client.code.like(term), Client.name.like(term)))
    total = db.scalar(select(func.count(Client.id)).where(*filters)) or 0
    items = list(
        db.scalars(select(Client).where(*filters).order_by(Client.name).offset(offset).limit(limit))
    )
    return ClientPageRead(items=items, total=total, limit=limit, offset=offset)


@router.get("/metrics/inactive")
def inactive_clients_metric(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client.view")),
) -> dict[str, int | str]:
    """Point-in-time inactive client count shared by every operational page."""
    permissions = effective_permissions(db, actor)
    filters: list[ColumnElement[bool]] = [Client.is_active.in_([False])]
    if permissions.client_scope_ids:
        filters.append(Client.id.in_(permissions.client_scope_ids))
    count = db.scalar(select(func.count(Client.id.distinct())).where(*filters)) or 0
    return {
        "inactive_clients": count,
        "as_of": server_now().isoformat(),
        "definition": "CURRENT_MASTER_STATUS",
    }


@router.get("/ticket-options", response_model=list[ClientTicketOptionRead])
def ticket_client_options(
    search: str | None = Query(default=None, max_length=100),
    limit: int | None = Query(default=None, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(
        require_any_permission(
            "client.view",
            "ticket.pre_ticket.create",
            "ticket.pre_ticket.convert_assign",
        )
    ),
) -> list[ClientTicketOptionRead]:
    # Imported locally to keep the CRM and ticket modules loosely coupled.
    from app.modules.tickets.models import Ticket

    counts = (
        select(Ticket.client_id.label("client_id"), func.count(Ticket.id).label("ticket_count"))
        .group_by(Ticket.client_id)
        .subquery()
    )
    ticket_count = func.coalesce(counts.c.ticket_count, 0)
    statement = (
        select(Client, ticket_count.label("ticket_count"))
        .outerjoin(counts, counts.c.client_id == Client.id)
        .order_by(desc(ticket_count), Client.name)
        .offset(offset)
    )
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(or_(Client.code.like(term), Client.name.like(term)))
    if limit is not None:
        statement = statement.limit(limit)
    rows = db.execute(statement).all()
    return [
        ClientTicketOptionRead(
            id=client.id,
            code=client.code,
            name=client.name,
            is_active=client.is_active,
            ticket_creation_allowed=client.ticket_creation_allowed,
            ticket_count=ticket_count,
        )
        for client, ticket_count in rows
    ]


@router.post("", response_model=ClientRead, status_code=201)
def create_client(
    data: ClientCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client.manage")),
) -> Client:
    validate_parent_change(db, None, data.parent_client_id)
    if not db.get(ClientStatus, data.status_id):
        raise NotFoundError("Client status does not exist.")
    if data.owner_department_id is not None:
        department = db.get(Department, data.owner_department_id)
        if not department or not department.is_active:
            raise ConflictError("INVALID_OWNER_DEPARTMENT", "Select an active owner department.")
    shared_department_ids = set(data.shared_department_ids)
    if data.owner_department_id:
        shared_department_ids.discard(data.owner_department_id)
    active_shared = set(
        db.scalars(
            select(Department.id).where(
                Department.id.in_(shared_department_ids or [-1]), Department.is_active.in_([True])
            )
        )
    )
    if active_shared != shared_department_ids:
        raise ConflictError("INVALID_SHARED_DEPARTMENT", "Every shared department must be active.")
    country = db.get(Country, data.country_id) if data.country_id else None
    city = db.get(City, data.city_id) if data.city_id else None
    if data.country_id and not country:
        raise NotFoundError("Country does not exist.")
    if city and city.country_id != data.country_id:
        raise ConflictError(
            "INVALID_CITY", "The selected city does not belong to the selected country."
        )
    if data.code and db.scalar(select(Client.id).where(Client.code == data.code)):
        raise ConflictError("DUPLICATE_CLIENT", "The client code is already in use.")
    values = data.model_dump(exclude={"shared_department_ids"})
    if country:
        values["country"] = country.name
    if city:
        values["zone"] = city.name
    requested_code = values.pop("code", None)
    client = Client(code=requested_code or "PENDING", **values)
    db.add(client)
    db.flush()
    db.add_all(
        ClientDepartmentLink(client_id=client.id, department_id=department_id)
        for department_id in sorted(shared_department_ids)
    )
    if not requested_code:
        client.code = f"CLI-{client.id:06d}"
    audit(db, actor.id, "Client", client.id, "client.created", data.model_dump())
    commit_or_conflict(db, "DUPLICATE_CLIENT", "The client code is already in use.")
    db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientRead)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> Client:
    client = db.get(Client, client_id)
    if not client:
        raise NotFoundError()
    return client


def _hierarchy_node(db: Session, item: Client) -> ClientHierarchyNode:
    path = get_client_path(db, item.id)
    direct_children = get_descendants(db, item.id, depth=1)
    descendants = get_descendants(db, item.id)
    return ClientHierarchyNode(
        id=item.id,
        code=item.code,
        name=item.name,
        is_active=item.is_active,
        parent_client_id=item.parent_client_id,
        depth=len(path) - 1,
        hierarchy_path=" > ".join(node.name for node in path),
        direct_child_count=len(direct_children),
        descendant_count=len(descendants),
    )


@router.get("/{client_id}/ancestors", response_model=list[ClientHierarchyNode])
def client_ancestors(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> list[ClientHierarchyNode]:
    return [_hierarchy_node(db, item) for item in get_ancestors(db, client_id)]


@router.get("/{client_id}/descendants", response_model=list[ClientHierarchyNode])
def client_descendants(
    client_id: int,
    depth: int | None = Query(default=None, ge=0, le=1000),
    include_self: bool = False,
    active_only: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> list[ClientHierarchyNode]:
    return [
        _hierarchy_node(db, item)
        for item in get_descendants(
            db, client_id, depth=depth, include_self=include_self, active_only=active_only
        )
    ]


@router.get("/{client_id}/hierarchy", response_model=ClientHierarchyRead)
def client_hierarchy(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> ClientHierarchyRead:
    client = db.get(Client, client_id)
    if client is None:
        raise NotFoundError("Client does not exist.")
    return ClientHierarchyRead(
        client=_hierarchy_node(db, client),
        ancestors=[_hierarchy_node(db, item) for item in get_ancestors(db, client_id)],
        descendants=[_hierarchy_node(db, item) for item in get_descendants(db, client_id)],
    )


@router.patch("/{client_id}", response_model=ClientRead)
def update_client(
    client_id: int,
    data: ClientUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client.manage")),
) -> Client:
    client = db.get(Client, client_id)
    if not client:
        raise NotFoundError()
    changes = data.model_dump(exclude_unset=True)
    shared_department_ids = changes.pop("shared_department_ids", None)
    old_path = " > ".join(item.name for item in get_client_path(db, client.id))
    if "parent_client_id" in changes:
        validate_parent_change(db, client.id, changes["parent_client_id"])
    if "status_id" in changes and not db.get(ClientStatus, changes["status_id"]):
        raise NotFoundError("Client status does not exist.")
    if "owner_department_id" in changes:
        department = (
            db.get(Department, changes["owner_department_id"])
            if changes["owner_department_id"]
            else None
        )
        if changes["owner_department_id"] and (not department or not department.is_active):
            raise ConflictError("INVALID_OWNER_DEPARTMENT", "Select an active owner department.")
    if shared_department_ids is not None:
        requested_shared = set(shared_department_ids)
        requested_shared.discard(changes.get("owner_department_id", client.owner_department_id))
        active_shared = set(
            db.scalars(
                select(Department.id).where(
                    Department.id.in_(requested_shared or [-1]), Department.is_active.in_([True])
                )
            )
        )
        if active_shared != requested_shared:
            raise ConflictError(
                "INVALID_SHARED_DEPARTMENT", "Every shared department must be active."
            )
        client.department_links = [
            ClientDepartmentLink(department_id=department_id)
            for department_id in sorted(requested_shared)
        ]
    if "country_id" in changes:
        country = db.get(Country, changes["country_id"]) if changes["country_id"] else None
        if changes["country_id"] and not country:
            raise NotFoundError("Country does not exist.")
        changes["country"] = country.name if country else None
    if "city_id" in changes:
        city = db.get(City, changes["city_id"]) if changes["city_id"] else None
        selected_country_id = changes.get("country_id", client.country_id)
        if changes["city_id"] and not city:
            raise NotFoundError("City does not exist.")
        if city and city.country_id != selected_country_id:
            raise ConflictError(
                "INVALID_CITY", "The selected city does not belong to the selected country."
            )
        changes["zone"] = city.name if city else None
    if "primary_location_id" in changes:
        location = (
            db.get(ClientLocation, changes["primary_location_id"])
            if changes["primary_location_id"]
            else None
        )
        if location and location.client_id != client.id:
            raise ConflictError(
                "INVALID_CLIENT_LOCATION", "The selected location does not belong to this client."
            )
        if location:
            country = db.get(Country, location.country_id)
            changes.update(
                country_id=location.country_id,
                country=country.name if country else None,
                zone=location.zone,
            )
    for key, value in changes.items():
        setattr(client, key, value)
    db.flush()
    audit_values: dict[str, object] = dict(changes)
    if "parent_client_id" in changes:
        audit_values["old_hierarchy_path"] = old_path
        audit_values["new_hierarchy_path"] = " > ".join(
            item.name for item in get_client_path(db, client.id)
        )
    audit(db, actor.id, "Client", client.id, "client.updated", audit_values)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=204)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client.delete")),
    settings: Settings = Depends(get_settings),
) -> None:
    client = db.get(Client, client_id)
    if not client:
        raise NotFoundError()
    if db.scalar(select(Client.id).where(Client.parent_client_id == client_id).limit(1)):
        raise ConflictError(
            "CLIENT_HAS_CHILDREN", "Move or remove child clients before deleting this parent."
        )
    tables = Base.metadata.tables
    tickets = tables["tickets"]
    contracts = tables["contracts"]
    ticket_ids = select(tickets.c.id).where(tickets.c.client_id == client_id)
    contract_ids = select(contracts.c.id).where(contracts.c.client_id == client_id)
    operation_ids = select(tables["internal_operations"].c.id).where(
        tables["internal_operations"].c.client_id == client_id
    )
    handover_ids = select(tables["project_handovers"].c.id).where(
        tables["project_handovers"].c.client_id == client_id
    )
    installation_ids = select(tables["client_installations"].c.id).where(
        tables["client_installations"].c.client_id == client_id
    )
    legacy_policy_ids = select(tables["sla_policies"].c.id).where(
        tables["sla_policies"].c.contract_id.in_(contract_ids)
    )
    coverage_ids = select(tables["contract_coverages"].c.id).where(
        tables["contract_coverages"].c.contract_id.in_(contract_ids)
    )

    root = Path(settings.attachment_storage_path).expanduser().resolve()
    files: list[Path] = []
    files.extend(
        root / str(row.ticket_id) / row.stored_filename
        for row in db.execute(
            select(
                tables["ticket_attachments"].c.ticket_id,
                tables["ticket_attachments"].c.stored_filename,
            ).where(tables["ticket_attachments"].c.ticket_id.in_(ticket_ids))
        )
    )
    files.extend(
        root / "contracts" / str(row.contract_id) / row.stored_filename
        for row in db.execute(
            select(
                tables["contract_documents"].c.contract_id,
                tables["contract_documents"].c.stored_filename,
            ).where(tables["contract_documents"].c.contract_id.in_(contract_ids))
        )
    )
    files.extend(
        root / "internal-operations" / str(row.operation_id) / row.stored_filename
        for row in db.execute(
            select(
                tables["internal_operation_documents"].c.operation_id,
                tables["internal_operation_documents"].c.stored_filename,
            ).where(tables["internal_operation_documents"].c.operation_id.in_(operation_ids))
        )
    )
    files.extend(
        root / "internal-operations" / str(row.handover_id) / row.stored_filename
        for row in db.execute(
            select(
                tables["project_handover_documents"].c.handover_id,
                tables["project_handover_documents"].c.stored_filename,
            ).where(tables["project_handover_documents"].c.handover_id.in_(handover_ids))
        )
    )

    db.execute(
        update(tickets)
        .where(
            tickets.c.escalation_parent_ticket_id.in_(ticket_ids), tickets.c.client_id != client_id
        )
        .values(escalation_parent_ticket_id=None)
    )
    db.execute(
        delete(tables["ticket_relations"]).where(
            or_(
                tables["ticket_relations"].c.source_ticket_id.in_(ticket_ids),
                tables["ticket_relations"].c.target_ticket_id.in_(ticket_ids),
            )
        )
    )
    for name in (
        "escalation_events",
        "integration_deliveries",
        "legacy_ticket_maps",
        "ticket_article_links",
        "ticket_assignment_history",
        "ticket_attachments",
        "ticket_checklist_items",
        "ticket_comments",
        "ticket_followers",
        "ticket_sla_clocks",
        "ticket_status_history",
        "ticket_tasks",
    ):
        db.execute(delete(tables[name]).where(tables[name].c.ticket_id.in_(ticket_ids)))
    db.execute(delete(tickets).where(tickets.c.client_id == client_id))

    db.execute(
        delete(tables["sla_targets"]).where(
            tables["sla_targets"].c.policy_id.in_(legacy_policy_ids)
        )
    )
    db.execute(
        delete(tables["sla_policies"]).where(tables["sla_policies"].c.id.in_(legacy_policy_ids))
    )
    db.execute(
        delete(tables["contract_coverage_clients"]).where(
            tables["contract_coverage_clients"].c.coverage_id.in_(coverage_ids)
        )
    )
    for name in ("contract_documents", "contract_coverages", "contract_client_links"):
        db.execute(delete(tables[name]).where(tables[name].c.contract_id.in_(contract_ids)))
    db.execute(delete(contracts).where(contracts.c.client_id == client_id))
    db.execute(
        delete(tables["contract_client_links"]).where(
            tables["contract_client_links"].c.client_id == client_id
        )
    )
    db.execute(
        delete(tables["contract_coverage_clients"]).where(
            tables["contract_coverage_clients"].c.client_id == client_id
        )
    )

    for name in (
        "internal_operation_assignees",
        "internal_operation_comments",
        "internal_operation_documents",
    ):
        db.execute(delete(tables[name]).where(tables[name].c.operation_id.in_(operation_ids)))
    db.execute(
        delete(tables["internal_operations"]).where(
            tables["internal_operations"].c.client_id == client_id
        )
    )
    for name in (
        "project_handover_comments",
        "project_handover_documents",
        "project_handover_products",
        "project_handover_recipients",
    ):
        db.execute(delete(tables[name]).where(tables[name].c.handover_id.in_(handover_ids)))
    db.execute(
        delete(tables["project_handovers"]).where(
            tables["project_handovers"].c.client_id == client_id
        )
    )
    db.execute(
        delete(tables["installation_components"]).where(
            tables["installation_components"].c.installation_id.in_(installation_ids)
        )
    )
    db.execute(
        delete(tables["client_installations"]).where(
            tables["client_installations"].c.client_id == client_id
        )
    )
    for name in (
        "client_access_credentials",
        "integration_api_clients",
        "contacts",
        "branches",
        "client_department_links",
    ):
        db.execute(delete(tables[name]).where(tables[name].c.client_id == client_id))
    db.execute(delete(tables["clients"]).where(tables["clients"].c.id == client_id))
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="Client",
            entity_id=str(client_id),
            action="client.deleted",
            old_values_json=json.dumps({"code": client.code, "name": client.name}),
        )
    )
    db.commit()
    for path in files:
        path.unlink(missing_ok=True)


@router.get("/{client_id}/access", response_model=list[ClientAccessRead])
def list_client_access(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client_access.view")),
) -> list[ClientAccessCredential]:
    if not db.get(Client, client_id):
        raise NotFoundError()
    return list(
        db.scalars(
            select(ClientAccessCredential)
            .where(ClientAccessCredential.client_id == client_id)
            .order_by(ClientAccessCredential.is_active.desc(), ClientAccessCredential.label)
        )
    )


@router.post("/{client_id}/access", response_model=ClientAccessRead, status_code=201)
def create_client_access(
    client_id: int,
    data: ClientAccessCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client_access.manage")),
) -> ClientAccessCredential:
    if not db.get(Client, client_id):
        raise NotFoundError()
    values = data.model_dump(exclude={"password"})
    item = ClientAccessCredential(
        client_id=client_id,
        **values,
        password_ciphertext=encrypt_password(data.password) if data.password else None,
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    db.add(item)
    db.flush()
    audit(
        db,
        actor.id,
        "ClientAccessCredential",
        item.id,
        "client_access.created",
        {**values, "has_password": bool(data.password)},
    )
    db.commit()
    db.refresh(item)
    return item


def _client_access(db: Session, client_id: int, access_id: int) -> ClientAccessCredential:
    item = db.scalar(
        select(ClientAccessCredential).where(
            ClientAccessCredential.id == access_id,
            ClientAccessCredential.client_id == client_id,
        )
    )
    if not item:
        raise NotFoundError("Client access record does not exist.")
    return item


@router.patch("/{client_id}/access/{access_id}", response_model=ClientAccessRead)
def update_client_access(
    client_id: int,
    access_id: int,
    data: ClientAccessUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client_access.manage")),
) -> ClientAccessCredential:
    item = _client_access(db, client_id, access_id)
    changes = data.model_dump(exclude_unset=True)
    password = changes.pop("password", None)
    if password is not None:
        item.password_ciphertext = encrypt_password(password) if password else None
    for key, value in changes.items():
        setattr(item, key, value)
    item.updated_by_user_id = actor.id
    audit(
        db,
        actor.id,
        "ClientAccessCredential",
        item.id,
        "client_access.updated",
        {**changes, **({"password_changed": True} if password is not None else {})},
    )
    db.commit()
    db.refresh(item)
    return item


@router.post("/{client_id}/access/{access_id}/reveal", response_model=ClientAccessRevealResponse)
def reveal_client_access_password(
    client_id: int,
    access_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client_access.reveal")),
) -> ClientAccessRevealResponse:
    item = _client_access(db, client_id, access_id)
    if not item.password_ciphertext:
        raise NotFoundError("This access record has no saved password.")
    audit(
        db,
        actor.id,
        "ClientAccessCredential",
        item.id,
        "client_access.password_revealed",
        {"trigger": "user_click"},
    )
    password = decrypt_password(item.password_ciphertext)
    db.commit()
    return ClientAccessRevealResponse(password=password)


@router.get("/{client_id}/branches", response_model=list[BranchRead])
def list_branches(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> list[Branch]:
    return list(
        db.scalars(select(Branch).where(Branch.client_id == client_id).order_by(Branch.name))
    )


@router.post("/{client_id}/branches", response_model=BranchRead, status_code=201)
def create_branch(
    client_id: int,
    data: BranchCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client.manage")),
) -> Branch:
    if not db.get(Client, client_id):
        raise NotFoundError()
    if data.escalation_contact_id:
        contact = db.get(Contact, data.escalation_contact_id)
        if not contact or contact.client_id != client_id:
            raise ConflictError(
                "INVALID_ESCALATION_CONTACT", "The escalation contact must belong to this client."
            )
    values = data.model_dump()
    requested_code = values.pop("code", None)
    branch = Branch(
        client_id=client_id,
        code=requested_code or f"PENDING-BRA-{server_now().timestamp()}",
        **values,
    )
    db.add(branch)
    try:
        db.flush()
        if not requested_code:
            branch.code = f"BRA-{branch.id:06d}"
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "DUPLICATE_BRANCH", "The branch code already exists for this client."
        ) from exc
    audit(db, actor.id, "Branch", branch.id, "branch.created", data.model_dump())
    db.commit()
    db.refresh(branch)
    return branch


@router.patch("/{client_id}/branches/{branch_id}", response_model=BranchRead)
def update_branch(
    client_id: int,
    branch_id: int,
    data: BranchUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client.manage")),
) -> Branch:
    branch = db.scalar(select(Branch).where(Branch.id == branch_id, Branch.client_id == client_id))
    if not branch:
        raise NotFoundError("Branch does not exist for this client.")
    changes = data.model_dump(exclude_unset=True)
    if changes.get("escalation_contact_id"):
        contact = db.get(Contact, changes["escalation_contact_id"])
        if not contact or contact.client_id != client_id:
            raise ConflictError(
                "INVALID_ESCALATION_CONTACT", "The escalation contact must belong to this client."
            )
    for field, value in changes.items():
        setattr(branch, field, value)
    audit(db, actor.id, "Branch", branch.id, "branch.updated", changes)
    db.commit()
    db.refresh(branch)
    return branch


@catalog_router.get("/contacts", response_model=list[ContactRead])
def list_contacts(
    client_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(
        require_any_permission(
            "client.view",
            "ticket.pre_ticket.create",
            "ticket.pre_ticket.convert_assign",
        )
    ),
) -> list[Contact]:
    from app.modules.tickets.models import Ticket

    recent_use = (
        select(func.max(Ticket.created_at))
        .where(Ticket.requester_contact_id == Contact.id)
        .correlate(Contact)
        .scalar_subquery()
    )
    statement = select(Contact)
    if client_id is not None:
        linked = select(ContactClientLink.contact_id).where(
            ContactClientLink.client_id == client_id
        )
        statement = statement.where(or_(Contact.client_id == client_id, Contact.id.in_(linked)))
    return list(db.scalars(statement.order_by(recent_use.desc(), Contact.full_name)))


@catalog_router.get("/contacts/search-existing", response_model=list[ContactRead])
def search_existing_contacts(
    query: str = Query(min_length=2, max_length=100),
    client_id: int = Query(gt=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("contact.link_existing")),
) -> list[Contact]:
    if not db.get(Client, client_id):
        raise NotFoundError("Client does not exist.")
    term = f"%{query.strip()}%"
    already_linked = select(ContactClientLink.contact_id).where(
        ContactClientLink.client_id == client_id
    )
    statement = (
        select(Contact)
        .where(
            Contact.is_active == True,  # noqa: E712
            Contact.client_id != client_id,
            Contact.id.not_in(already_linked),
            or_(
                Contact.full_name.ilike(term),
                Contact.phone_number.ilike(term),
                Contact.email.ilike(term),
                Contact.code.ilike(term),
            ),
        )
        .order_by(Contact.full_name)
        .limit(20)
    )
    return list(db.scalars(statement))


@catalog_router.post("/clients/{client_id}/contacts/link", response_model=ContactRead)
def link_existing_contact(
    client_id: int,
    data: ContactLinkCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contact.link_existing")),
) -> Contact:
    if not db.get(Client, client_id):
        raise NotFoundError("Client does not exist.")
    contact = db.get(Contact, data.contact_id)
    if not contact or not contact.is_active:
        raise NotFoundError("Active contact does not exist.")
    if contact.client_id != client_id:
        existing = db.scalar(
            select(ContactClientLink).where(
                ContactClientLink.contact_id == contact.id, ContactClientLink.client_id == client_id
            )
        )
        if not existing:
            db.add(
                ContactClientLink(
                    contact_id=contact.id, client_id=client_id, linked_by_user_id=actor.id
                )
            )
            db.flush()
            audit(
                db,
                actor.id,
                "Contact",
                contact.id,
                "contact.client_linked",
                {"client_id": client_id},
            )
            db.commit()
    return contact


@catalog_router.post("/contacts", response_model=ContactRead, status_code=201)
def create_contact(
    data: ContactCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contact.manage")),
) -> Contact:
    if not db.get(Client, data.client_id):
        raise NotFoundError("Client does not exist.")
    if data.branch_id:
        branch = db.get(Branch, data.branch_id)
        if not branch or branch.client_id != data.client_id:
            raise ConflictError("INVALID_BRANCH", "The branch does not belong to the client.")
    values = data.model_dump()
    requested_code = values.pop("code", None)
    contact = Contact(code=requested_code, **values)
    db.add(contact)
    try:
        db.flush()
        if not requested_code:
            contact.code = f"CON-{contact.id:06d}"
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("DUPLICATE_CONTACT", "That contact email already exists.") from exc
    audit(db, actor.id, "Contact", contact.id, "contact.created", data.model_dump())
    db.commit()
    db.refresh(contact)
    return contact


@catalog_router.patch("/contacts/{contact_id}", response_model=ContactRead)
def update_contact(
    contact_id: int,
    data: ContactUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("contact.manage")),
) -> Contact:
    contact = db.get(Contact, contact_id)
    if not contact:
        raise NotFoundError("Contact does not exist.")
    changes = data.model_dump(exclude_unset=True)
    target_client_value = changes.get("client_id", contact.client_id)
    if target_client_value is None:
        raise ConflictError("CLIENT_REQUIRED", "A contact must belong to a client.")
    target_client_id = int(target_client_value)
    if not db.get(Client, target_client_id):
        raise NotFoundError("Client does not exist.")
    branch_id = changes.get("branch_id", contact.branch_id)
    if branch_id is not None:
        branch = db.get(Branch, branch_id)
        if not branch or branch.client_id != target_client_id:
            raise ConflictError("INVALID_BRANCH", "The branch does not belong to the client.")
    for field, value in changes.items():
        setattr(contact, field, value)
    audit(db, actor.id, "Contact", contact.id, "contact.updated", changes)
    commit_or_conflict(db, "DUPLICATE_CONTACT", "That contact email already exists.")
    db.refresh(contact)
    return contact


@catalog_router.get("/products", response_model=list[ProductRead])
def list_products(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> list[Product]:
    return list(db.scalars(select(Product).order_by(Product.name)))


@catalog_router.post("/products", response_model=ProductRead, status_code=201)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("installation.manage")),
) -> Product:
    values = data.model_dump()
    requested_code = values.pop("code", None)
    product = Product(code="PENDING", **values)
    try:
        add_with_generated_code(db, product, requested_code, "PRD")
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("DUPLICATE_PRODUCT", "That product code is already in use.") from exc
    audit(db, actor.id, "Product", product.id, "product.created", data.model_dump())
    db.commit()
    db.refresh(product)
    return product


@catalog_router.patch("/products/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("installation.manage")),
) -> Product:
    product = db.get(Product, product_id)
    if not product:
        raise NotFoundError("Product does not exist.")
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(product, field, value)
    audit(db, actor.id, "Product", product.id, "product.updated", changes)
    db.commit()
    db.refresh(product)
    return product


@catalog_router.post(
    "/products/{product_id}/modules", response_model=ProductModuleRead, status_code=201
)
def create_product_module(
    product_id: int,
    data: ProductModuleCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("installation.manage")),
) -> ProductModule:
    if not db.get(Product, product_id):
        raise NotFoundError()
    values = data.model_dump()
    requested_code = values.pop("code", None)
    module = ProductModule(product_id=product_id, code="PENDING", **values)
    try:
        add_with_generated_code(db, module, requested_code, "MOD")
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("DUPLICATE_MODULE", "That module code already exists.") from exc
    audit(
        db,
        actor.id,
        "ProductModule",
        module.id,
        "product_module.created",
        {"product_id": product_id, **data.model_dump()},
    )
    db.commit()
    db.refresh(module)
    return module


@catalog_router.patch(
    "/products/{product_id}/modules/{module_id}", response_model=ProductModuleRead
)
def update_product_module(
    product_id: int,
    module_id: int,
    data: ProductModuleUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("installation.manage")),
) -> ProductModule:
    module = db.scalar(
        select(ProductModule).where(
            ProductModule.id == module_id, ProductModule.product_id == product_id
        )
    )
    if not module:
        raise NotFoundError("Product module does not exist.")
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(module, field, value)
    audit(db, actor.id, "ProductModule", module.id, "product_module.updated", changes)
    db.commit()
    db.refresh(module)
    return module


@catalog_router.get("/installations", response_model=list[InstallationRead])
def list_installations(
    client_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("installation.read")),
) -> list[ClientInstallation]:
    statement = select(ClientInstallation)
    if client_id is not None:
        statement = statement.where(ClientInstallation.client_id == client_id)
    return list(db.scalars(statement.order_by(ClientInstallation.installation_name)))


@catalog_router.post("/installations", response_model=InstallationRead, status_code=201)
def create_installation(
    data: InstallationCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("installation.manage")),
) -> ClientInstallation:
    for model, value, label in (
        (Client, data.client_id, "Client"),
        (Product, data.product_id, "Product"),
        (Environment, data.environment_id, "Environment"),
    ):
        if not db.get(model, value):
            raise NotFoundError(f"{label} does not exist.")
    if data.branch_id is not None:
        branch = db.get(Branch, data.branch_id)
        if not branch or branch.client_id != data.client_id:
            raise ConflictError("INVALID_BRANCH", "The branch does not belong to the client.")
    component_values: list[dict[str, Any]]
    if data.components is not None:
        component_values = [item.model_dump() for item in data.components]
    else:
        component_values = [
            {"product_id": data.product_id, "product_module_id": data.product_module_id}
        ]
    if not component_values:
        raise ConflictError("COMPONENT_REQUIRED", "Add at least one product to the installation.")
    for component in component_values:
        product = db.get(Product, component["product_id"])
        if not product:
            raise NotFoundError("Product does not exist.")
        module_id = component.get("product_module_id")
        if module_id is not None:
            module = db.get(ProductModule, module_id)
            if not module or module.product_id != component["product_id"]:
                raise ConflictError("INVALID_MODULE", "The module does not belong to the product.")
    values = data.model_dump(exclude={"components"})
    values["product_id"] = component_values[0]["product_id"]
    values["product_module_id"] = component_values[0].get("product_module_id")
    installation = ClientInstallation(**values)
    installation.components = [InstallationComponent(**item) for item in component_values]
    db.add(installation)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("DUPLICATE_INSTALLATION", "That installation already exists.") from exc
    audit(
        db,
        actor.id,
        "ClientInstallation",
        installation.id,
        "installation.created",
        data.model_dump(),
    )
    db.commit()
    db.refresh(installation)
    return installation


@catalog_router.patch("/installations/{installation_id}", response_model=InstallationRead)
def update_installation(
    installation_id: int,
    data: InstallationUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("installation.manage")),
) -> ClientInstallation:
    installation = db.get(ClientInstallation, installation_id)
    if not installation:
        raise NotFoundError("Installation does not exist.")
    changes = data.model_dump(exclude_unset=True)
    requested_components = changes.pop("components", None)
    if requested_components is not None:
        if not requested_components:
            raise ConflictError(
                "COMPONENT_REQUIRED", "Add at least one product to the installation."
            )
        for component in requested_components:
            product = db.get(Product, component["product_id"])
            if not product:
                raise NotFoundError("Product does not exist.")
            module_id = component.get("product_module_id")
            if module_id is not None:
                module = db.get(ProductModule, module_id)
                if not module or module.product_id != component["product_id"]:
                    raise ConflictError(
                        "INVALID_MODULE", "The module does not belong to the product."
                    )
        changes["product_id"] = requested_components[0]["product_id"]
        changes["product_module_id"] = requested_components[0].get("product_module_id")
    client_id = changes.get("client_id", installation.client_id)
    product_id = changes.get("product_id", installation.product_id)
    environment_id = changes.get("environment_id", installation.environment_id)
    if client_id is None or product_id is None or environment_id is None:
        raise ConflictError(
            "INSTALLATION_REFERENCE_REQUIRED", "Client, product, and environment are required."
        )
    for model, value, label in (
        (Client, client_id, "Client"),
        (Product, product_id, "Product"),
        (Environment, environment_id, "Environment"),
    ):
        if not db.get(model, value):
            raise NotFoundError(f"{label} does not exist.")
    branch_id = changes.get("branch_id", installation.branch_id)
    if branch_id is not None:
        branch = db.get(Branch, branch_id)
        if not branch or branch.client_id != client_id:
            raise ConflictError("INVALID_BRANCH", "The branch does not belong to the client.")
    module_id = changes.get("product_module_id", installation.product_module_id)
    if module_id is not None:
        module = db.get(ProductModule, module_id)
        if not module or module.product_id != product_id:
            raise ConflictError("INVALID_MODULE", "The module does not belong to the product.")
    for field, value in changes.items():
        setattr(installation, field, value)
    if requested_components is not None:
        installation.components = [
            InstallationComponent(**component) for component in requested_components
        ]
        changes["components"] = requested_components
    audit(db, actor.id, "ClientInstallation", installation.id, "installation.updated", changes)
    commit_or_conflict(db, "DUPLICATE_INSTALLATION", "That installation already exists.")
    db.refresh(installation)
    return installation


@catalog_router.get("/client-statuses", response_model=list[ClientStatusRead])
def list_statuses(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> list[ClientStatus]:
    return list(db.scalars(select(ClientStatus).order_by(ClientStatus.name)))


@catalog_router.post("/client-statuses", response_model=ClientStatusRead, status_code=201)
def create_status(
    data: ClientStatusCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client.manage")),
) -> ClientStatus:
    values = data.model_dump()
    requested_code = values.pop("code", None)
    item = ClientStatus(code="PENDING", **values)
    try:
        add_with_generated_code(db, item, requested_code, "CST")
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "DUPLICATE_CLIENT_STATUS", "That client status code already exists."
        ) from exc
    audit(db, actor.id, "ClientStatus", item.id, "client_status.created", data.model_dump())
    db.commit()
    db.refresh(item)
    return item


@catalog_router.patch("/client-statuses/{status_id}", response_model=ClientStatusRead)
def update_status(
    status_id: int,
    data: ClientStatusUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client.manage")),
) -> ClientStatus:
    item = db.get(ClientStatus, status_id)
    if not item:
        raise NotFoundError("Client status does not exist.")
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(item, field, value)
    audit(db, actor.id, "ClientStatus", item.id, "client_status.updated", changes)
    db.commit()
    db.refresh(item)
    return item


@catalog_router.get("/environments", response_model=list[EnvironmentRead])
def list_environments(
    db: Session = Depends(get_db),
    _: User = Depends(
        require_any_permission(
            "installation.read",
            "client.view",
            "contract.view",
            "ticket.create",
            "ticket.view.own",
            "ticket.view.team",
            "ticket.view.department",
            "ticket.view.all",
        )
    ),
) -> list[Environment]:
    return list(db.scalars(select(Environment).order_by(Environment.name)))


@catalog_router.post("/environments", response_model=EnvironmentRead, status_code=201)
def create_environment(
    data: EnvironmentCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("installation.manage")),
) -> Environment:
    values = data.model_dump()
    requested_code = values.pop("code", None)
    item = Environment(code="PENDING", **values)
    try:
        add_with_generated_code(db, item, requested_code, "ENV")
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "DUPLICATE_ENVIRONMENT", "That environment code already exists."
        ) from exc
    audit(db, actor.id, "Environment", item.id, "environment.created", data.model_dump())
    db.commit()
    db.refresh(item)
    return item


@catalog_router.patch("/environments/{environment_id}", response_model=EnvironmentRead)
def update_environment(
    environment_id: int,
    data: EnvironmentUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("installation.manage")),
) -> Environment:
    item = db.get(Environment, environment_id)
    if not item:
        raise NotFoundError("Environment does not exist.")
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(item, field, value)
    audit(db, actor.id, "Environment", item.id, "environment.updated", changes)
    db.commit()
    db.refresh(item)
    return item


@catalog_router.post("/services", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
def create_service(
    data: ServiceCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client.manage")),
) -> ServiceCatalogItem:
    values = data.model_dump()
    requested_code = values.pop("code", None)
    module_ids = values.pop("module_ids")
    modules = (
        list(db.scalars(select(ProductModule).where(ProductModule.id.in_(module_ids))))
        if module_ids
        else []
    )
    if len(modules) != len(set(module_ids)):
        raise NotFoundError("A selected product module does not exist.")
    make_resolution_default = values.get("is_default_resolution_service", False)
    if make_resolution_default and not values.get("is_active", True):
        raise ConflictError(
            "INACTIVE_DEFAULT_RESOLUTION_SERVICE",
            "The default resolution service must be active.",
        )
    if make_resolution_default:
        db.execute(
            update(ServiceCatalogItem)
            .where(ServiceCatalogItem.is_default_resolution_service.in_([True]))
            .values(is_default_resolution_service=False)
        )
    item = ServiceCatalogItem(code="PENDING", **values)
    item.modules = modules
    try:
        add_with_generated_code(db, item, requested_code, "SVC")
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("DUPLICATE_SERVICE", "That service code is already in use.") from exc
    audit(db, actor.id, "ServiceCatalogItem", item.id, "service.created", data.model_dump())
    db.commit()
    db.refresh(item)
    return item


@catalog_router.get("/products/{product_id}/modules", response_model=list[ProductModuleRead])
def list_product_modules(
    product_id: int,
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> list[ProductModule]:
    if not db.get(Product, product_id):
        raise NotFoundError("Product does not exist.")
    statement = select(ProductModule).where(ProductModule.product_id == product_id)
    if not include_inactive:
        statement = statement.where(ProductModule.is_active.in_([True]))
    return list(db.scalars(statement.order_by(ProductModule.name)))


@catalog_router.get("/services", response_model=list[ServiceRead])
def list_services(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> list[ServiceCatalogItem]:
    return list(db.scalars(select(ServiceCatalogItem).order_by(ServiceCatalogItem.name)))


@catalog_router.patch("/services/{service_id}", response_model=ServiceRead)
def update_service(
    service_id: int,
    data: ServiceUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client.manage")),
) -> ServiceCatalogItem:
    item = db.get(ServiceCatalogItem, service_id)
    if not item:
        raise NotFoundError("Service does not exist.")
    changes = data.model_dump(exclude_unset=True)
    if changes.get("is_default_resolution_service") and not changes.get(
        "is_active", item.is_active
    ):
        raise ConflictError(
            "INACTIVE_DEFAULT_RESOLUTION_SERVICE",
            "The default resolution service must be active.",
        )
    if item.is_default_resolution_service and changes.get("is_active") is False:
        raise ConflictError(
            "INACTIVE_DEFAULT_RESOLUTION_SERVICE",
            "Choose another default resolution service before deactivating this service.",
        )
    if changes.get("is_default_resolution_service"):
        db.execute(
            update(ServiceCatalogItem)
            .where(
                ServiceCatalogItem.id != item.id,
                ServiceCatalogItem.is_default_resolution_service.in_([True]),
            )
            .values(is_default_resolution_service=False)
        )
    module_ids = changes.pop("module_ids", None)
    if module_ids is not None:
        modules = (
            list(db.scalars(select(ProductModule).where(ProductModule.id.in_(module_ids))))
            if module_ids
            else []
        )
        if len(modules) != len(set(module_ids)):
            raise NotFoundError("A selected product module does not exist.")
        item.modules = modules
    for field, value in changes.items():
        setattr(item, field, value)
    audit(db, actor.id, "ServiceCatalogItem", item.id, "service.updated", changes)
    db.commit()
    db.refresh(item)
    return item


@catalog_router.post("/vendors", response_model=VendorRead, status_code=201)
def create_vendor(
    data: VendorCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client.manage")),
) -> Vendor:
    values = data.model_dump()
    requested_code = values.pop("code", None)
    vendor = Vendor(code="PENDING", **values)
    try:
        add_with_generated_code(db, vendor, requested_code, "VND")
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("DUPLICATE_VENDOR", "That vendor code is already in use.") from exc
    audit(db, actor.id, "Vendor", vendor.id, "vendor.created", data.model_dump())
    db.commit()
    db.refresh(vendor)
    return vendor


@catalog_router.get("/vendors", response_model=list[VendorRead])
def list_vendors(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> list[Vendor]:
    return list(db.scalars(select(Vendor).order_by(Vendor.name)))


@catalog_router.get("/skills", response_model=list[SupportCatalogRead])
def list_skills(
    db: Session = Depends(get_db), _: User = Depends(require_permission("client.view"))
) -> list[SupportSkill]:
    return list(db.scalars(select(SupportSkill).order_by(SupportSkill.name)))


@catalog_router.get("/ticket-categories", response_model=list[ServiceRead])
def list_ticket_categories(
    db: Session = Depends(get_db), _: User = Depends(require_permission("client.view"))
) -> list[TicketCategory]:
    return list(db.scalars(select(TicketCategory).order_by(TicketCategory.name)))


@catalog_router.get("/deployment-issue-types", response_model=list[DeploymentIssueTypeRead])
def list_deployment_issue_types(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> list[DeploymentIssueType]:
    statement = select(DeploymentIssueType)
    if not include_inactive:
        statement = statement.where(DeploymentIssueType.is_active.in_([True]))
    return list(db.scalars(statement.order_by(DeploymentIssueType.name)))


@catalog_router.post("/deployment-issue-types", response_model=DeploymentIssueTypeRead, status_code=201)
def create_deployment_issue_type(
    data: DeploymentIssueTypeCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> DeploymentIssueType:
    values = data.model_dump()
    requested_code = values.pop("code", None)
    if values["is_default"]:
        db.execute(update(DeploymentIssueType).values(is_default=False))
    item = DeploymentIssueType(code="PENDING", **values)
    add_with_generated_code(db, item, requested_code, "DIT")
    commit_or_conflict(db, "DUPLICATE_DEPLOYMENT_ISSUE_TYPE", "That deployment issue type already exists.")
    db.refresh(item)
    audit(db, actor.id, "DeploymentIssueType", item.id, "deployment_issue_type.created", data.model_dump())
    db.commit()
    return item


@catalog_router.patch("/deployment-issue-types/{issue_type_id}", response_model=DeploymentIssueTypeRead)
def update_deployment_issue_type(
    issue_type_id: int,
    data: DeploymentIssueTypeUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> DeploymentIssueType:
    item = db.get(DeploymentIssueType, issue_type_id)
    if not item:
        raise NotFoundError("Deployment issue type does not exist.")
    changes = data.model_dump(exclude_unset=True)
    if changes.get("is_default"):
        db.execute(update(DeploymentIssueType).where(DeploymentIssueType.id != item.id).values(is_default=False))
    for field, value in changes.items():
        setattr(item, field, value)
    audit(db, actor.id, "DeploymentIssueType", item.id, "deployment_issue_type.updated", changes)
    db.commit()
    db.refresh(item)
    return item


@catalog_router.post("/ticket-categories", response_model=ServiceRead, status_code=201)
def create_ticket_category(
    data: CatalogCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> TicketCategory:
    values = data.model_dump()
    requested_code = values.pop("code", None)
    item = TicketCategory(code="PENDING", **values)
    add_with_generated_code(db, item, requested_code, "CAT")
    commit_or_conflict(db, "DUPLICATE_CATEGORY", "That ticket category already exists.")
    db.refresh(item)
    audit(db, actor.id, "TicketCategory", item.id, "ticket_category.created", data.model_dump())
    db.commit()
    return item


@catalog_router.patch("/ticket-categories/{category_id}", response_model=ServiceRead)
def update_ticket_category(
    category_id: int,
    data: CatalogUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> TicketCategory:
    item = db.get(TicketCategory, category_id)
    if not item:
        raise NotFoundError("Ticket category does not exist.")
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(item, field, value)
    audit(db, actor.id, "TicketCategory", item.id, "ticket_category.updated", changes)
    db.commit()
    db.refresh(item)
    return item


@catalog_router.get(
    "/ticket-categories/{category_id}/subcategories",
    response_model=list[TicketSubcategoryRead],
)
def list_ticket_subcategories(
    category_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> list[TicketSubcategory]:
    return list(
        db.scalars(
            select(TicketSubcategory)
            .where(TicketSubcategory.category_id == category_id)
            .order_by(TicketSubcategory.name)
        )
    )


@catalog_router.get("/ticket-subcategories", response_model=list[TicketSubcategoryRead])
def list_all_ticket_subcategories(
    category_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("client.view")),
) -> list[TicketSubcategory]:
    statement = select(TicketSubcategory)
    if category_id:
        statement = statement.where(TicketSubcategory.category_id == category_id)
    return list(
        db.scalars(statement.order_by(TicketSubcategory.category_id, TicketSubcategory.name))
    )


@catalog_router.post("/ticket-subcategories", response_model=TicketSubcategoryRead, status_code=201)
def create_ticket_subcategory_admin(
    data: TicketSubcategoryAdminCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> TicketSubcategory:
    if not db.get(TicketCategory, data.category_id):
        raise NotFoundError("Ticket category does not exist.")
    values = data.model_dump()
    requested_code = values.pop("code", None)
    item = TicketSubcategory(code="PENDING", **values)
    add_with_generated_code(db, item, requested_code, "SUB")
    commit_or_conflict(
        db, "DUPLICATE_SUBCATEGORY", "That subcategory code already exists in this category."
    )
    db.refresh(item)
    audit(
        db, actor.id, "TicketSubcategory", item.id, "ticket_subcategory.created", data.model_dump()
    )
    db.commit()
    return item


@catalog_router.patch(
    "/ticket-subcategories/{subcategory_id}", response_model=TicketSubcategoryRead
)
def update_ticket_subcategory_admin(
    subcategory_id: int,
    data: TicketSubcategoryUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> TicketSubcategory:
    item = db.get(TicketSubcategory, subcategory_id)
    if not item:
        raise NotFoundError("Ticket subcategory does not exist.")
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(item, field, value)
    audit(db, actor.id, "TicketSubcategory", item.id, "ticket_subcategory.updated", changes)
    db.commit()
    db.refresh(item)
    return item


@catalog_router.post(
    "/ticket-categories/{category_id}/subcategories",
    response_model=TicketSubcategoryRead,
    status_code=201,
)
def create_ticket_subcategory(
    category_id: int,
    data: TicketSubcategoryCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> TicketSubcategory:
    if not db.get(TicketCategory, category_id):
        raise NotFoundError("Ticket category does not exist.")
    values = data.model_dump()
    requested_code = values.pop("code", None)
    item = TicketSubcategory(category_id=category_id, code="PENDING", **values)
    add_with_generated_code(db, item, requested_code, "SUB")
    commit_or_conflict(db, "DUPLICATE_SUBCATEGORY", "That subcategory code already exists.")
    db.refresh(item)
    audit(
        db, actor.id, "TicketSubcategory", item.id, "ticket_subcategory.created", data.model_dump()
    )
    db.commit()
    return item


@catalog_router.patch(
    "/ticket-categories/{category_id}/subcategories/{subcategory_id}",
    response_model=TicketSubcategoryRead,
)
def update_ticket_subcategory(
    category_id: int,
    subcategory_id: int,
    data: TicketSubcategoryUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> TicketSubcategory:
    item = db.get(TicketSubcategory, subcategory_id)
    if not item or item.category_id != category_id:
        raise NotFoundError("Ticket subcategory does not exist.")
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(item, field, value)
    audit(db, actor.id, "TicketSubcategory", item.id, "ticket_subcategory.updated", changes)
    db.commit()
    db.refresh(item)
    return item


@catalog_router.post("/skills", response_model=SupportCatalogRead, status_code=201)
def create_skill(
    data: SupportCatalogCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> SupportSkill:
    values = data.model_dump(
        exclude={"department_id", "skill_ids", "member_user_ids", "leader_user_id"}
    )
    requested_code = values.pop("code", None)
    item = SupportSkill(code="PENDING", **values)
    try:
        add_with_generated_code(db, item, requested_code, "SKL")
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("DUPLICATE_SKILL", "That skill code or name already exists.") from exc
    audit(db, actor.id, "SupportSkill", item.id, "support_skill.created", values)
    db.commit()
    db.refresh(item)
    return item


@catalog_router.patch("/skills/{skill_id}", response_model=SupportCatalogRead)
def update_skill(
    skill_id: int,
    data: SupportCatalogUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> SupportSkill:
    item = db.get(SupportSkill, skill_id)
    if not item:
        raise NotFoundError("Support skill does not exist.")
    changes = data.model_dump(
        exclude_unset=True,
        exclude={"department_id", "skill_ids", "member_user_ids", "leader_user_id"},
    )
    for field, value in changes.items():
        setattr(item, field, value)
    audit(db, actor.id, "SupportSkill", item.id, "support_skill.updated", changes)
    commit_or_conflict(db, "DUPLICATE_SKILL", "That skill name already exists.")
    db.refresh(item)
    return item


@catalog_router.get("/support-teams", response_model=list[SupportCatalogRead])
def list_support_teams(
    db: Session = Depends(get_db), _: User = Depends(require_permission("client.view"))
) -> list[SupportTeam]:
    return list(db.scalars(select(SupportTeam).order_by(SupportTeam.name)))


@catalog_router.post("/support-teams", response_model=SupportCatalogRead, status_code=201)
def create_support_team(
    data: SupportCatalogCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> SupportTeam:
    skill_ids = set(data.skill_ids)
    member_user_ids = set(data.member_user_ids)
    if data.department_id is not None:
        department = db.get(Department, data.department_id)
        if not department or not department.is_active:
            raise ConflictError("INVALID_TEAM_DEPARTMENT", "Team department must be active.")
    if skill_ids and len(
        set(db.scalars(select(SupportSkill.id).where(SupportSkill.id.in_(skill_ids))))
    ) != len(skill_ids):
        raise NotFoundError("One or more skills do not exist.")
    if data.leader_user_id is not None:
        leader = db.get(User, data.leader_user_id)
        if not leader or not leader.is_active or leader.user_type != "EMPLOYEE":
            raise ConflictError("INVALID_TEAM_LEADER", "Team Leader must be an active employee.")
    if member_user_ids:
        valid_members = set(
            db.scalars(
                select(User.id).where(
                    User.id.in_(member_user_ids),
                    User.is_active.in_([True]),
                    User.user_type == "EMPLOYEE",
                )
            )
        )
        if valid_members != member_user_ids:
            raise ConflictError(
                "INVALID_TEAM_MEMBERS", "All team members must be active employees."
            )
    values = data.model_dump(exclude={"skill_ids", "member_user_ids"})
    requested_code = values.pop("code", None)
    item = SupportTeam(**values)
    item.skill_links = [SupportTeamSkill(skill_id=x) for x in skill_ids]
    item.member_links = [SupportTeamMember(user_id=x) for x in member_user_ids]
    try:
        add_with_generated_code(db, item, requested_code, "TEM")
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("DUPLICATE_TEAM", "That team code or name already exists.") from exc
    audit(db, actor.id, "SupportTeam", item.id, "support_team.created", data.model_dump())
    db.commit()
    db.refresh(item)
    return item


@catalog_router.patch("/support-teams/{team_id}", response_model=SupportCatalogRead)
def update_support_team(
    team_id: int,
    data: SupportCatalogUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("configuration.manage")),
) -> SupportTeam:
    item = db.get(SupportTeam, team_id)
    if not item:
        raise NotFoundError("Support team does not exist.")
    changes = data.model_dump(exclude_unset=True)
    skill_ids = changes.pop("skill_ids", None)
    member_user_ids = changes.pop("member_user_ids", None)
    if changes.get("department_id") is not None:
        department = db.get(Department, changes["department_id"])
        if not department or not department.is_active:
            raise ConflictError("INVALID_TEAM_DEPARTMENT", "Team department must be active.")
    if "leader_user_id" in changes and changes["leader_user_id"] is not None:
        leader = db.get(User, changes["leader_user_id"])
        if not leader or not leader.is_active or leader.user_type != "EMPLOYEE":
            raise ConflictError("INVALID_TEAM_LEADER", "Team Leader must be an active employee.")
    if skill_ids is not None:
        if skill_ids and len(
            set(db.scalars(select(SupportSkill.id).where(SupportSkill.id.in_(skill_ids))))
        ) != len(set(skill_ids)):
            raise NotFoundError("One or more skills do not exist.")
        item.skill_links = [SupportTeamSkill(skill_id=x) for x in set(skill_ids)]
    if member_user_ids is not None:
        requested_members = set(member_user_ids)
        valid_members = set(
            db.scalars(
                select(User.id).where(
                    User.id.in_(requested_members),
                    User.is_active.in_([True]),
                    User.user_type == "EMPLOYEE",
                )
            )
        )
        if valid_members != requested_members:
            raise ConflictError(
                "INVALID_TEAM_MEMBERS", "All team members must be active employees."
            )
        item.member_links = [SupportTeamMember(user_id=x) for x in requested_members]
    for field, value in changes.items():
        setattr(item, field, value)
    audit_values = {
        **changes,
        **({"skill_ids": skill_ids} if skill_ids is not None else {}),
        **({"member_user_ids": member_user_ids} if member_user_ids is not None else {}),
    }
    audit(db, actor.id, "SupportTeam", item.id, "support_team.updated", audit_values)
    commit_or_conflict(db, "DUPLICATE_TEAM", "That team name already exists.")
    db.refresh(item)
    return item


@catalog_router.patch("/vendors/{vendor_id}", response_model=VendorRead)
def update_vendor(
    vendor_id: int,
    data: VendorUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("client.manage")),
) -> Vendor:
    vendor = db.get(Vendor, vendor_id)
    if not vendor:
        raise NotFoundError("Vendor does not exist.")
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(vendor, field, value)
    audit(db, actor.id, "Vendor", vendor.id, "vendor.updated", changes)
    db.commit()
    db.refresh(vendor)
    return vendor
