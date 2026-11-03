import json

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_any_permission, require_permission
from app.core.clock import server_now, server_today
from app.core.config import Settings, get_settings
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import Client, Product, ProductModule, ServiceCatalogItem
from app.modules.clients.schemas import ClientAccessCreate, ContactCreate
from app.modules.contracts.models import ContractTemplate
from app.modules.iam.models import AuditLog, User
from app.modules.iam.service import effective_permissions
from app.modules.project_handovers.models import (
    HandoverComment,
    HandoverDocument,
    HandoverPendingPoint,
    HandoverProduct,
    HandoverRecipient,
    HandoverSourceTemplate,
    ProjectHandover,
    ProjectManager,
)
from app.modules.project_handovers.schemas import (
    CommentCreate,
    HandoverCreate,
    HandoverRead,
    HandoverUpdate,
    ProjectManagerRead,
    ProjectManagerWrite,
)

router = APIRouter(prefix="/project-handovers", tags=["project-handovers"])


def _has(db: Session, user: User, permission: str) -> bool:
    return permission in effective_permissions(db, user).permissions


@router.get("/options/clients")
def delivery_clients(
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("project_handover.client.lookup")),
) -> list[dict[str, object]]:
    statement = select(Client).where(Client.is_active.in_([True]))
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(or_(Client.code.like(term), Client.name.like(term)))
    return [{"id": row.id, "code": row.code, "name": row.name} for row in db.scalars(statement.order_by(Client.name).limit(limit))]


@router.get("/options/engineers")
def delivery_engineers(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("project_handover.engineer.lookup")),
) -> list[dict[str, object]]:
    return [{"id": row.id, "full_name": row.full_name} for row in db.scalars(select(User).where(User.is_active.in_([True])).order_by(User.full_name))]


@router.get("/options/products")
def delivery_products(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("project_handover.manage")),
) -> list[dict[str, object]]:
    return [{"id": row.id, "name": row.name, "name_ar": row.name_ar} for row in db.scalars(select(Product).order_by(Product.name))]


@router.get("/options/scope-catalog")
def delivery_scope_catalog(
    db: Session = Depends(get_db),
    _: User = Depends(
        require_any_permission("project_handover.manage", "project_handover.edit_pending")
    ),
) -> dict[str, object]:
    return {
        "modules": [{"id": row.id, "product_id": row.product_id, "name": row.name, "name_ar": row.name_ar} for row in db.scalars(select(ProductModule).where(ProductModule.is_active.in_([True])).order_by(ProductModule.name))],
        "services": [{"id": row.id, "name": row.name, "name_ar": row.name_ar} for row in db.scalars(select(ServiceCatalogItem).where(ServiceCatalogItem.is_active.in_([True])).order_by(ServiceCatalogItem.name))],
        "templates": [{"id": row.id, "name": row.name, "version": row.version} for row in db.scalars(select(ContractTemplate).where(ContractTemplate.is_active.in_([True])).order_by(ContractTemplate.name))],
    }


@router.get("/options/templates/{template_id}/scope")
def delivery_template_scope(template_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("project_handover.contract_template.apply"))) -> dict[str, object]:
    template = db.get(ContractTemplate, template_id)
    if not template or not template.is_active:
        raise NotFoundError("Active contract template does not exist.")
    rows = [{"product_id": row.product_id, "product_module_id": row.product_module_id, "service_id": row.service_id} for row in template.coverages if row.is_covered and row.product_id]
    return {"template_id": template.id, "template_version": template.version, "rows": rows}


@router.get("/onboarding/options")
def delivery_onboarding_options(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project_handover.client.create")),
) -> dict[str, object]:
    from app.modules.clients.models import ClientStatus
    from app.modules.contracts.models import ContractTemplate
    from app.modules.iam.models import Department

    statuses = [{"id": row.id, "name": row.name, "name_ar": row.name_ar} for row in db.scalars(select(ClientStatus).order_by(ClientStatus.name))]
    departments = [{"id": row.id, "name": row.name, "name_ar": row.name_ar, "is_active": row.is_active} for row in db.scalars(select(Department).where(Department.is_active.in_([True])).order_by(Department.name))]
    templates: list[dict[str, object]] = []
    if _has(db, actor, "project_handover.contract_template.apply"):
        templates = [{"id": row.id, "name": row.name, "version": row.version, "default_duration_months": row.default_duration_months, "is_default": row.is_default, "is_active": row.is_active} for row in db.scalars(select(ContractTemplate).where(ContractTemplate.is_active.in_([True])).order_by(ContractTemplate.name))]
    return {"statuses": statuses, "departments": departments, "templates": templates}


@router.post("/onboard-client", status_code=201)
def delivery_onboard_client(
    data: dict[str, object],
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project_handover.client.create")),
) -> object:
    from app.modules.contracts.routes import onboard_client
    from app.modules.contracts.schemas import ClientOnboardingWrite

    parsed = ClientOnboardingWrite.model_validate(data)
    if parsed.contract and not _has(db, actor, "project_handover.contract_template.apply"):
        raise AuthorizationError(details={"required_permission": "project_handover.contract_template.apply"})
    if parsed.contact and not _has(db, actor, "project_handover.contact.create"):
        raise AuthorizationError(details={"required_permission": "project_handover.contact.create"})
    result = onboard_client(parsed, db, actor)
    client = db.get(Client, result.client_id)
    if not client:
        raise NotFoundError("The newly created client could not be loaded.")
    return {**result.model_dump(), "client": {"id": client.id, "code": client.code, "name": client.name}}


@router.post("/clients/{client_id}/contacts", status_code=201)
def delivery_create_contact(client_id: int, data: ContactCreate, db: Session = Depends(get_db), actor: User = Depends(require_permission("project_handover.contact.create"))) -> dict[str, object]:
    from app.modules.clients.routes import create_contact

    if data.client_id != client_id:
        raise ConflictError("CLIENT_MISMATCH", "The contact client does not match the delivery client.")
    row = create_contact(data, db, actor)
    return {"id": row.id, "code": row.code, "client_id": row.client_id, "full_name": row.full_name}


@router.post("/clients/{client_id}/access", status_code=201)
def delivery_create_access(client_id: int, data: ClientAccessCreate, db: Session = Depends(get_db), actor: User = Depends(require_permission("project_handover.client_access.create"))) -> dict[str, object]:
    from app.modules.clients.routes import create_client_access

    row = create_client_access(client_id, data, db, actor)
    return {"id": row.id, "client_id": row.client_id, "access_type": row.access_type, "label": row.label, "has_password": row.has_password}


def manageable(db: Session, user: User) -> bool:
    return "project_handover.manage" in effective_permissions(db, user).permissions


def validated_scope(db: Session, data: HandoverCreate) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    products: list[dict[str, object]] = []
    assigned: set[tuple[int, int | None, int | None]] = set()
    for line in data.products:
        if not db.get(Product, line.product_id): raise NotFoundError("Project product does not exist.")
        module = db.get(ProductModule, line.product_module_id) if line.product_module_id else None
        if module and module.product_id != line.product_id: raise ConflictError("INVALID_PROJECT_MODULE", "The module does not belong to the selected product.")
        if line.service_id and not db.get(ServiceCatalogItem, line.service_id): raise NotFoundError("Project service does not exist.")
        values = line.model_dump()
        values["delivery_date"] = line.delivery_date or server_today() if line.delivery_status == "DELIVERED" else None
        products.append(values); assigned.add((line.product_id, line.product_module_id, line.service_id))
    points: list[dict[str, object]] = []
    for point in data.structured_pending_points:
        if (point.product_id, point.product_module_id, point.service_id) not in assigned:
            raise ConflictError("PENDING_POINT_OUTSIDE_SCOPE", "Every pending point must reference an assigned project product, module, and service row.")
        points.append(point.model_dump())
    return products, points


def validated_templates(db: Session, data: HandoverCreate) -> list[dict[str, int]]:
    requested = [item.model_dump() for item in data.source_templates]
    if not requested and data.source_template_id:
        requested = [{
            "template_id": data.source_template_id,
            "template_version": data.source_template_version,
        }]
    if len({item["template_id"] for item in requested}) != len(requested):
        raise ConflictError("DUPLICATE_CONTRACT_TEMPLATE", "Select each contract template only once.")
    for item in requested:
        template = db.get(ContractTemplate, item["template_id"])
        if not template or not template.is_active or template.version != item["template_version"]:
            raise ConflictError("STALE_CONTRACT_TEMPLATE", "Refresh the selected template scope.")
    return requested


def can_access(db: Session, user: User, row: ProjectHandover) -> bool:
    return manageable(db, user) or row.delivered_by_user_id == user.id or db.scalar(select(HandoverRecipient.id).where(HandoverRecipient.handover_id == row.id, HandoverRecipient.user_id == user.id)) is not None


def serialize(db: Session, row: ProjectHandover) -> HandoverRead:
    client = db.get(Client, row.client_id); deliverer = db.get(User, row.delivered_by_user_id)
    recipients = list(db.scalars(select(HandoverRecipient).where(HandoverRecipient.handover_id == row.id)))
    products = list(db.scalars(select(HandoverProduct).where(HandoverProduct.handover_id == row.id)))
    points = list(db.scalars(select(HandoverPendingPoint).where(HandoverPendingPoint.handover_id == row.id)))
    source_templates = list(db.scalars(select(HandoverSourceTemplate).where(HandoverSourceTemplate.handover_id == row.id).order_by(HandoverSourceTemplate.id)))
    documents=list(db.scalars(select(HandoverDocument).where(HandoverDocument.handover_id==row.id)))
    comments = list(db.scalars(select(HandoverComment).where(HandoverComment.handover_id == row.id).order_by(HandoverComment.created_at)))
    users = {u.id: u.full_name for u in db.scalars(select(User))}; product_names = {p.id: p.name for p in db.scalars(select(Product))}; module_names = {m.id: m.name for m in db.scalars(select(ProductModule))}; service_names = {s.id: s.name for s in db.scalars(select(ServiceCatalogItem))}
    manager = db.get(ProjectManager, row.project_manager_id) if row.project_manager_id else None
    return HandoverRead(
        id=row.id, project_number=row.project_number, project_name=row.project_name, client_id=row.client_id, source_template_id=row.source_template_id, source_template_version=row.source_template_version,
        source_templates=[{"template_id": x.template_id, "template_version": x.template_version} for x in source_templates] or ([{"template_id": row.source_template_id, "template_version": row.source_template_version}] if row.source_template_id and row.source_template_version else []),
        client_name=client.name if client else "Unknown client", delivered_by_user_id=row.delivered_by_user_id,
        delivered_by_name=deliverer.full_name if deliverer else "Unknown", project_manager_user_id=row.project_manager_user_id, project_manager_id=row.project_manager_id,
        project_manager_name=manager.full_name if manager else (users.get(row.project_manager_user_id, row.project_manager_name) if row.project_manager_user_id else row.project_manager_name),
        project_manager_email=manager.email if manager else row.project_manager_email, project_manager_phone=manager.phone_number if manager else row.project_manager_phone,
        warranty_months=row.warranty_months, warranty_start_date=row.warranty_start_date, acceptance_date=row.acceptance_date,
        pending_points=row.pending_points, current_status=row.current_status, notes=row.notes, created_at=row.created_at,
        recipients=[{"user_id": x.user_id, "name": users.get(x.user_id, "Unknown"), "accepted": x.accepted} for x in recipients],
        products=[{"id": x.id, "product_id": x.product_id, "product": product_names.get(x.product_id, "Unknown"), "product_module_id": x.product_module_id, "module": module_names.get(x.product_module_id) if x.product_module_id else None, "service_id": x.service_id, "service": service_names.get(x.service_id) if x.service_id else None, "delivery_status": x.delivery_status, "delivered_version": x.delivered_version, "delivery_percent": float(x.delivery_percent) if x.delivery_percent is not None else None, "delivery_date": x.delivery_date, "notes": x.notes} for x in products],
        structured_pending_points=[{"id": x.id, "product_id": x.product_id, "product": product_names.get(x.product_id, "Unknown"), "product_module_id": x.product_module_id, "module": module_names.get(x.product_module_id) if x.product_module_id else None, "service_id": x.service_id, "service": service_names.get(x.service_id) if x.service_id else None, "description": x.description, "status": x.status} for x in points],
        comments=[{"id": x.id, "author_user_id": x.author_user_id, "author": users.get(x.author_user_id, "Unknown"), "body": x.body, "created_at": x.created_at} for x in comments],
        documents=[{"id":x.id,"original_filename":x.original_filename,"size_bytes":x.size_bytes,"uploaded_by":users.get(x.uploaded_by_user_id,"Unknown")} for x in documents],
    )


@router.get("", response_model=list[HandoverRead])
def list_handovers(db: Session = Depends(get_db), user: User = Depends(require_permission("project_handover.view"))) -> list[HandoverRead]:
    query = select(ProjectHandover).order_by(ProjectHandover.created_at.desc())
    if not manageable(db, user):
        assigned = select(HandoverRecipient.handover_id).where(HandoverRecipient.user_id == user.id)
        query = query.where(or_(ProjectHandover.delivered_by_user_id == user.id, ProjectHandover.id.in_(assigned)))
    return [serialize(db, row) for row in db.scalars(query).all()]


@router.get("/project-managers/options", response_model=list[ProjectManagerRead])
def list_project_managers(db: Session = Depends(get_db), _: User = Depends(require_permission("project_handover.view"))) -> list[ProjectManager]:
    return list(db.scalars(select(ProjectManager).where(ProjectManager.is_active.in_([True])).order_by(ProjectManager.full_name)))


@router.post("/project-managers", response_model=ProjectManagerRead, status_code=201)
def create_project_manager(data: ProjectManagerWrite, db: Session = Depends(get_db), _: User = Depends(require_permission("project_handover.manage"))) -> ProjectManager:
    manager = ProjectManager(**data.model_dump(), is_active=True)
    db.add(manager); db.commit(); db.refresh(manager)
    return manager


@router.post("", response_model=HandoverRead, status_code=201)
def create_handover(data: HandoverCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("project_handover.manage"))) -> HandoverRead:
    if data.project_number and db.scalar(select(ProjectHandover.id).where(ProjectHandover.project_number == data.project_number)):
        raise ConflictError("DUPLICATE_PROJECT_NUMBER", "That project number already exists.")
    client = db.get(Client, data.client_id)
    if not client or not client.is_active: raise NotFoundError("Client not found or inactive.")
    engineer_ids = set(data.recipient_user_ids)
    if set(db.scalars(select(User.id).where(User.id.in_(engineer_ids), User.is_active.in_([True])))) != engineer_ids: raise NotFoundError("One or more support engineers are unavailable.")
    manager_id = data.project_manager_id
    if manager_id and not db.get(ProjectManager, manager_id):
        raise NotFoundError("Project manager does not exist.")
    if not manager_id and data.project_manager_name:
        manager = ProjectManager(full_name=data.project_manager_name, email=data.project_manager_email, phone_number=data.project_manager_phone, is_active=True)
        db.add(manager); db.flush(); manager_id = manager.id
    product_values, point_values = validated_scope(db, data)
    template_values = validated_templates(db, data)
    values = data.model_dump(exclude={"recipient_user_ids", "products", "structured_pending_points", "source_templates", "project_manager_id"})
    requested_number = values.pop("project_number", None)
    values["project_number"] = requested_number or f"PENDING-{server_now().timestamp()}"
    row = ProjectHandover(**values, project_manager_id=manager_id, delivered_by_user_id=user.id)
    db.add(row); db.flush()
    if not requested_number:
        row.project_number = f"PRJ-{server_now().year}-{row.id:06d}"
    db.add_all(HandoverRecipient(handover_id=row.id, user_id=x) for x in engineer_ids)
    db.add_all(HandoverSourceTemplate(handover_id=row.id, **values) for values in template_values)
    db.add_all(HandoverProduct(handover_id=row.id, **values) for values in product_values)
    db.add_all(HandoverPendingPoint(handover_id=row.id, **values) for values in point_values)
    db.add(AuditLog(actor_user_id=user.id, entity_type="ProjectHandover", entity_id=str(row.id), action="project_handover.created", new_values_json=json.dumps(data.model_dump(), default=str)))
    db.commit(); db.refresh(row); return serialize(db, row)


@router.patch("/{handover_id}", response_model=HandoverRead)
def update_pending_handover(
    handover_id: int,
    data: HandoverUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("project_handover.edit_pending")),
) -> HandoverRead:
    row = db.get(ProjectHandover, handover_id)
    if not row:
        raise NotFoundError()
    if row.current_status not in {"DRAFT", "READY", "ON_HOLD"}:
        raise ConflictError("HANDOVER_FINALIZED", "Delivered or accepted projects cannot be modified.")
    client = db.get(Client, data.client_id)
    if not client or not client.is_active:
        raise NotFoundError("Client not found or inactive.")
    engineer_ids = set(data.recipient_user_ids)
    active_engineers = set(db.scalars(select(User.id).where(User.id.in_(engineer_ids), User.is_active.in_([True]))))
    if active_engineers != engineer_ids:
        raise NotFoundError("One or more support engineers are unavailable.")
    manager_id = data.project_manager_id
    if manager_id and not db.get(ProjectManager, manager_id):
        raise NotFoundError("Project manager does not exist.")
    if not manager_id and data.project_manager_name:
        manager = ProjectManager(full_name=data.project_manager_name, email=data.project_manager_email, phone_number=data.project_manager_phone, is_active=True)
        db.add(manager); db.flush(); manager_id = manager.id
    old_values = {"project_name": row.project_name, "client_id": row.client_id, "current_status": row.current_status, "pending_points": row.pending_points}
    product_values, point_values = validated_scope(db, data)
    template_values = validated_templates(db, data)
    values = data.model_dump(exclude={"project_number", "recipient_user_ids", "products", "structured_pending_points", "source_templates", "project_manager_id"})
    for field, value in values.items():
        setattr(row, field, value)
    row.project_manager_id = manager_id
    db.execute(delete(HandoverRecipient).where(HandoverRecipient.handover_id == row.id))
    db.execute(delete(HandoverProduct).where(HandoverProduct.handover_id == row.id))
    db.execute(delete(HandoverPendingPoint).where(HandoverPendingPoint.handover_id == row.id))
    db.execute(delete(HandoverSourceTemplate).where(HandoverSourceTemplate.handover_id == row.id))
    db.add_all(HandoverRecipient(handover_id=row.id, user_id=engineer_id) for engineer_id in engineer_ids)
    db.add_all(HandoverSourceTemplate(handover_id=row.id, **values) for values in template_values)
    db.add_all(HandoverProduct(handover_id=row.id, **values) for values in product_values)
    db.add_all(HandoverPendingPoint(handover_id=row.id, **values) for values in point_values)
    db.add(AuditLog(actor_user_id=user.id, entity_type="ProjectHandover", entity_id=str(row.id), action="project_handover.updated", old_values_json=json.dumps(old_values, default=str), new_values_json=json.dumps(data.model_dump(), default=str)))
    db.commit(); db.refresh(row)
    return serialize(db, row)


@router.get("/{handover_id}", response_model=HandoverRead)
def get_handover(handover_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission("project_handover.view"))) -> HandoverRead:
    row=db.get(ProjectHandover,handover_id)
    if not row: raise NotFoundError()
    if not can_access(db,user,row): raise AuthorizationError()
    return serialize(db,row)


@router.post("/{handover_id}/comments", response_model=HandoverRead)
def comment(handover_id: int, data: CommentCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("project_handover.manage"))) -> HandoverRead:
    row=db.get(ProjectHandover,handover_id)
    if not row: raise NotFoundError()
    if not can_access(db,user,row): raise AuthorizationError()
    db.add(HandoverComment(handover_id=row.id,author_user_id=user.id,body=data.body)); db.commit(); return serialize(db,row)

@router.post("/{handover_id}/documents",response_model=HandoverRead)
async def upload_doc(handover_id:int,upload:UploadFile=File(...),db:Session=Depends(get_db),user:User=Depends(require_permission("project_handover.manage")),settings:Settings=Depends(get_settings))->HandoverRead:
    from app.modules.internal_operations.attachments import store_document
    row=db.get(ProjectHandover,handover_id)
    if not row or not can_access(db,user,row): raise NotFoundError()
    original,stored,content_type,size=await store_document(upload,handover_id,settings);db.add(HandoverDocument(handover_id=handover_id,original_filename=original,stored_filename=stored,content_type=content_type,size_bytes=size,uploaded_by_user_id=user.id));db.commit();return serialize(db,row)

@router.get("/{handover_id}/documents/{document_id}/download")
def download_doc(handover_id:int,document_id:int,db:Session=Depends(get_db),user:User=Depends(require_permission("project_handover.view")),settings:Settings=Depends(get_settings))->FileResponse:
    from pathlib import Path
    row=db.get(ProjectHandover,handover_id);doc=db.get(HandoverDocument,document_id)
    if not row or not doc or doc.handover_id!=handover_id or not can_access(db,user,row): raise NotFoundError()
    path=Path(settings.attachment_storage_path).resolve()/"internal-operations"/str(handover_id)/doc.stored_filename
    return FileResponse(path,media_type=doc.content_type,filename=doc.original_filename)
