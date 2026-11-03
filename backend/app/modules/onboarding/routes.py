import ipaddress
import json
from datetime import date, timedelta
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, require_any_permission, require_permission
from app.core.clock import server_now, server_today
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.iam.models import AuditLog, User
from app.modules.iam.organization import department_descendant_ids
from app.modules.iam.service import effective_permissions

from .models import (
    OnboardingCompletionType,
    OnboardingMaterial,
    OnboardingMaterialCategory,
    OnboardingMaterialResource,
    OnboardingTaskType,
    OnboardingTemplate,
    OnboardingTemplateBundle,
    OnboardingTemplateBundleItem,
    OnboardingTemplateItem,
    UserOnboarding,
    UserOnboardingItem,
)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class TaskDurationIn(BaseModel):
    template_item_id: int
    duration_days: int = Field(ge=1, le=730)
    mentor_mode: str = Field(default="INHERIT", pattern="^(INHERIT|SPECIFIC|NONE)$")
    mentor_user_id: int | None = None


class AssignIn(BaseModel):
    user_id: int
    template_id: int | None = None
    bundle_id: int | None = None
    start_date: date
    mentor_user_id: int | None = None
    task_durations: list[TaskDurationIn] = Field(default_factory=list, max_length=200)


class UnassignIn(BaseModel):
    version: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=1000)


class ReplaceAssignmentIn(AssignIn):
    version: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=1000)


class ItemUpdate(BaseModel):
    status: str = Field(pattern="^(PENDING|IN_PROGRESS|COMPLETED|SKIPPED)$")
    version: int


class TemplateIn(BaseModel):
    code: str | None = Field(default=None, max_length=80)
    name: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    category_id: int | None = None
    default_duration_days: int | None = Field(default=None, ge=1, le=730)
    display_order: int = Field(default=0, ge=0, le=10000)
    items: list[dict[str, object]] = Field(default_factory=list, max_length=200)


class BundleIn(BaseModel):
    code: str = Field(min_length=3, max_length=80)
    name: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    default_duration_days: int | None = Field(default=None, ge=1, le=730)
    items: list[dict[str, object]] = Field(default_factory=list, max_length=100)


class ReviewIn(BaseModel):
    decision: str = Field(pattern="^(APPROVED|REJECTED)$")
    comment: str | None = Field(default=None, max_length=2000)


class CategoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    display_order: int = Field(default=0, ge=0, le=10000)
    is_active: bool = True


class MaterialIn(BaseModel):
    category_id: int | None = None
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    is_required: bool = False
    display_order: int = Field(default=0, ge=0, le=10000)
    is_active: bool = True
    show_in_client_portal: bool = False


class ResourceIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    resource_type: str = Field(
        pattern="^(PDF|SHAREPOINT|VIDEO|KNOWLEDGE|WEBSITE|MICROSOFT_LEARN|OTHER)$"
    )
    url: str = Field(min_length=8, max_length=2000, pattern=r"^https?://")
    display_order: int = Field(default=0, ge=0, le=10000)
    is_active: bool = True


def portal_safe_url(value: str) -> bool:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return False
    hostname = parsed.hostname.casefold().rstrip(".")
    if hostname == "localhost" or hostname.endswith((".local", ".internal", ".lan")):
        return False
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return "." in hostname
    return address.is_global


def validate_portal_resources(db: Session, material_id: int) -> None:
    resources = list(db.scalars(select(OnboardingMaterialResource).where(OnboardingMaterialResource.material_id == material_id, OnboardingMaterialResource.is_active.in_([True]))))
    if not resources:
        raise ConflictError("PORTAL_RESOURCE_REQUIRED", "Publish at least one active portal-safe resource first.")
    if any(not portal_safe_url(resource.url) for resource in resources):
        raise ConflictError("UNSAFE_PORTAL_RESOURCE", "Portal publication requires HTTPS resources with a public hostname.")


def template_payload(db: Session, template: OnboardingTemplate) -> dict[str, object]:
    items = list(
        db.scalars(
            select(OnboardingTemplateItem)
            .where(OnboardingTemplateItem.template_id == template.id)
            .order_by(OnboardingTemplateItem.display_order)
        )
    )
    return {
        "id": template.id,
        "code": template.code,
        "name": template.name,
        "description": template.description,
        "category_id": template.category_id,
        "default_duration_days": template.default_duration_days,
        "display_order": template.display_order,
        "version": template.version,
        "is_active": template.is_active,
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "display_order": item.display_order,
                "required": item.is_required,
                "material_id": item.material_id,
                "start_after_days": item.start_after_days,
                "due_after_days": item.due_after_days,
                "task_type_code": item.task_type_code,
                "completion_type_code": item.completion_type_code,
                "requires_approval": item.requires_approval,
                "is_active": item.is_active,
            }
            for item in items
        ],
    }


def replace_template_items(
    db: Session, template: OnboardingTemplate, items: list[dict[str, object]]
) -> None:
    db.query(OnboardingTemplateItem).filter(
        OnboardingTemplateItem.template_id == template.id
    ).delete()
    for index, item in enumerate(items):
        material_id = int(str(item["material_id"])) if item.get("material_id") else None
        if material_id is not None and not db.get(OnboardingMaterial, material_id):
            raise NotFoundError("A linked training material does not exist.")
        db.add(
            OnboardingTemplateItem(
                template_id=template.id,
                title=str(item["title"]).strip(),
                description=str(item.get("description") or "").strip() or None,
                display_order=int(str(item.get("display_order", index))),
                is_required=bool(item.get("required", True)),
                due_after_days=int(str(item["due_after_days"]))
                if item.get("due_after_days") is not None
                else None,
                material_id=material_id,
                start_after_days=int(str(item.get("start_after_days", 0))),
                is_active=bool(item.get("is_active", True)),
                task_type_code=str(item.get("task_type_code", "OTHER")),
                completion_type_code=str(item.get("completion_type_code", "SELF_COMPLETE")),
                requires_approval=bool(item.get("requires_approval", False)),
            )
        )


def plan_payload(db: Session, plan: UserOnboarding) -> dict[str, object]:
    items = list(
        db.scalars(
            select(UserOnboardingItem)
            .where(UserOnboardingItem.user_onboarding_id == plan.id)
            .order_by(UserOnboardingItem.display_order)
        )
    )
    done = sum(row.status in {"COMPLETED", "SKIPPED"} for row in items)
    user_ids = {plan.mentor_user_id, *(row.mentor_user_id for row in items)} - {None}
    people = {
        user.id: user
        for user in db.scalars(select(User).where(User.id.in_(user_ids or {-1})))
    }
    return {
        "id": plan.id,
        "user_id": plan.user_id,
        "template_name": plan.template_name,
        "start_date": plan.start_date,
        "status": plan.status,
        "version": plan.version,
        "mentor_user_id": plan.mentor_user_id,
        "mentor_name": people[plan.mentor_user_id].full_name
        if plan.mentor_user_id in people
        else None,
        "completed": done,
        "total": len(items),
        "items": [
            {
                "id": row.id,
                "title": row.title,
                "description": row.description,
                "status": row.status,
                "required": row.is_required,
                "due_date": row.due_date,
                "material_id": row.material_id,
                "available_date": row.available_date,
                "task_type_code": row.task_type_code,
                "completion_type_code": row.completion_type_code,
                "requires_approval": row.requires_approval,
                "approval_status": row.approval_status,
                "review_comment": row.review_comment,
                "mentor_mode": row.mentor_mode,
                "mentor_user_id": row.mentor_user_id
                if row.mentor_mode == "SPECIFIC"
                else (plan.mentor_user_id if row.mentor_mode == "INHERIT" else None),
                "mentor_name": people[row.mentor_user_id].full_name
                if row.mentor_mode == "SPECIFIC" and row.mentor_user_id in people
                else (
                    people[plan.mentor_user_id].full_name
                    if row.mentor_mode == "INHERIT" and plan.mentor_user_id in people
                    else None
                ),
                "version": row.version,
            }
            for row in items
        ],
    }


def reconcile_plan(db: Session, plan: UserOnboarding) -> None:
    required = list(
        db.scalars(
            select(UserOnboardingItem).where(
                UserOnboardingItem.user_onboarding_id == plan.id,
                UserOnboardingItem.is_required,
            )
        )
    )
    plan.status = (
        "COMPLETED"
        if required and all(row.status == "COMPLETED" for row in required)
        else "IN_PROGRESS"
    )
    plan.version += 1


@router.get("/me")
def my_plan(
    db: Session = Depends(get_db), actor: User = Depends(current_user)
) -> dict[str, object] | None:
    plan = db.scalar(
        select(UserOnboarding)
        .where(UserOnboarding.user_id == actor.id, UserOnboarding.status == "IN_PROGRESS")
        .order_by(UserOnboarding.created_at.desc())
        .limit(1)
    )
    return plan_payload(db, plan) if plan else None


@router.patch("/{plan_id}/items/{item_id}")
def update_item(
    plan_id: int,
    item_id: int,
    data: ItemUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> dict[str, object]:
    plan = db.get(UserOnboarding, plan_id)
    row = db.get(UserOnboardingItem, item_id)
    if not plan or not row or row.user_onboarding_id != plan.id:
        raise NotFoundError()
    if plan.user_id != actor.id:
        raise ConflictError("ONBOARDING_SCOPE", "Only the assigned employee can update this item.")
    if row.version != data.version:
        raise ConflictError("STALE_ONBOARDING_ITEM", "Refresh the checklist and try again.")
    if row.available_date and row.available_date > server_today():
        raise ConflictError("ONBOARDING_ITEM_NOT_AVAILABLE", "This item is not available yet.")
    if data.status == "SKIPPED" and row.is_required:
        raise ConflictError(
            "ONBOARDING_REQUIRED_ITEM", "Required onboarding items cannot be skipped."
        )
    needs_review = row.requires_approval or row.completion_type_code in {
        "MENTOR_CONFIRMATION",
        "MANAGER_APPROVAL",
    }
    if data.status == "COMPLETED" and needs_review:
        row.status = "IN_PROGRESS"
        row.approval_status = "PENDING"
        row.submitted_at = server_now()
        row.completed_at = None
    else:
        row.status = data.status
        row.approval_status = None
        row.completed_at = server_now() if data.status == "COMPLETED" else None
    row.version += 1
    reconcile_plan(db, plan)
    db.commit()
    return plan_payload(db, plan)


@router.get("/materials")
def materials(
    db: Session = Depends(get_db), _: User = Depends(current_user)
) -> list[dict[str, object]]:
    rows = list(
        db.scalars(
            select(OnboardingMaterial)
            .where(OnboardingMaterial.is_active)
            .order_by(OnboardingMaterial.display_order)
        )
    )
    return [
        {
            "id": m.id,
            "title": m.title,
            "description": m.description,
            "category_id": m.category_id,
            "required": m.is_required,
            "display_order": m.display_order,
            "is_active": m.is_active,
            "show_in_client_portal": m.show_in_client_portal,
            "resources": [
                {
                    "id": r.id,
                    "name": r.name,
                    "type": r.resource_type,
                    "url": r.url,
                    "display_order": r.display_order,
                    "is_active": r.is_active,
                }
                for r in db.scalars(
                    select(OnboardingMaterialResource)
                    .where(
                        OnboardingMaterialResource.material_id == m.id,
                        OnboardingMaterialResource.is_active,
                    )
                    .order_by(OnboardingMaterialResource.display_order)
                )
            ],
        }
        for m in rows
    ]


@router.get("/material-categories")
def material_categories(
    db: Session = Depends(get_db), _: User = Depends(current_user)
) -> list[dict[str, object]]:
    return [
        {
            "id": row.id,
            "name": row.name,
            "display_order": row.display_order,
            "is_active": row.is_active,
        }
        for row in db.scalars(
            select(OnboardingMaterialCategory).order_by(
                OnboardingMaterialCategory.display_order, OnboardingMaterialCategory.name
            )
        )
    ]


@router.post("/material-categories", status_code=201)
def create_category(
    data: CategoryIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding.category.manage")),
) -> dict[str, object]:
    if db.scalar(
        select(OnboardingMaterialCategory.id).where(
            OnboardingMaterialCategory.name == data.name.strip()
        )
    ):
        raise ConflictError(
            "ONBOARDING_CATEGORY_EXISTS", "A material category with this name already exists."
        )
    row = OnboardingMaterialCategory(**data.model_dump())
    row.name = row.name.strip()
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, **data.model_dump()}


@router.patch("/material-categories/{category_id}")
def update_category(
    category_id: int,
    data: CategoryIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding.category.manage")),
) -> dict[str, object]:
    row = db.get(OnboardingMaterialCategory, category_id)
    if not row:
        raise NotFoundError()
    for key, value in data.model_dump().items():
        setattr(row, key, value.strip() if key == "name" else value)
    db.commit()
    return {"id": row.id, **data.model_dump()}


@router.delete("/material-categories/{category_id}", status_code=204)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding.category.manage")),
) -> None:
    row = db.get(OnboardingMaterialCategory, category_id)
    if not row:
        raise NotFoundError()
    # Categories are retained as inactive masters so existing material and audit
    # references remain valid. They disappear from new-material selection.
    row.is_active = False
    db.commit()


@router.post("/materials", status_code=201)
def create_material(
    data: MaterialIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding.material.manage")),
) -> dict[str, object]:
    if data.category_id is not None and not db.get(OnboardingMaterialCategory, data.category_id):
        raise NotFoundError("Material category does not exist.")
    if data.show_in_client_portal:
        raise ConflictError("PORTAL_RESOURCE_REQUIRED", "Create the material and portal-safe resources before publishing it.")
    row = OnboardingMaterial(**data.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, **data.model_dump()}


@router.patch("/materials/{material_id}")
def update_material(
    material_id: int,
    data: MaterialIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("onboarding.material.manage")),
) -> dict[str, object]:
    row = db.get(OnboardingMaterial, material_id)
    if not row:
        raise NotFoundError()
    if data.category_id is not None and not db.get(OnboardingMaterialCategory, data.category_id):
        raise NotFoundError("Material category does not exist.")
    old_portal_visibility = row.show_in_client_portal
    if data.show_in_client_portal:
        validate_portal_resources(db, row.id)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    if old_portal_visibility != data.show_in_client_portal:
        db.add(AuditLog(actor_user_id=actor.id, entity_type="OnboardingMaterial", entity_id=str(row.id), action="PORTAL_PUBLICATION_CHANGED", reason="Published to client portal" if data.show_in_client_portal else "Removed from client portal", old_values_json=f'{{"show_in_client_portal":{str(old_portal_visibility).lower()}}}', new_values_json=f'{{"show_in_client_portal":{str(data.show_in_client_portal).lower()}}}'))
    db.commit()
    return {"id": row.id, **data.model_dump()}


@router.delete("/materials/{material_id}", status_code=204)
def delete_material(
    material_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding.material.manage")),
) -> None:
    row = db.get(OnboardingMaterial, material_id)
    if not row:
        raise NotFoundError()
    # Preserve material IDs already copied into template/employee snapshots.
    row.is_active = False
    db.commit()


@router.post("/materials/{material_id}/resources", status_code=201)
def create_resource(
    material_id: int,
    data: ResourceIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding.material.manage")),
) -> dict[str, object]:
    material = db.get(OnboardingMaterial, material_id)
    if not material:
        raise NotFoundError()
    if material.show_in_client_portal and data.is_active and not portal_safe_url(data.url):
        raise ConflictError("UNSAFE_PORTAL_RESOURCE", "Published materials require HTTPS resources with a public hostname.")
    row = OnboardingMaterialResource(
        material_id=material_id,
        name=data.name.strip(),
        resource_type=data.resource_type,
        url=data.url,
        display_order=data.display_order,
        is_active=data.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "material_id": material_id, **data.model_dump()}


@router.patch("/material-resources/{resource_id}")
def update_resource(
    resource_id: int,
    data: ResourceIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding.material.manage")),
) -> dict[str, object]:
    row = db.get(OnboardingMaterialResource, resource_id)
    if not row:
        raise NotFoundError()
    material = db.get(OnboardingMaterial, row.material_id)
    if material and material.show_in_client_portal and data.is_active and not portal_safe_url(data.url):
        raise ConflictError("UNSAFE_PORTAL_RESOURCE", "Published materials require HTTPS resources with a public hostname.")
    row.name = data.name.strip()
    row.resource_type = data.resource_type
    row.url = data.url
    row.display_order = data.display_order
    row.is_active = data.is_active
    db.commit()
    return {"id": row.id, "material_id": row.material_id, **data.model_dump()}


@router.delete("/material-resources/{resource_id}", status_code=204)
def delete_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding.material.manage")),
) -> None:
    row = db.get(OnboardingMaterialResource, resource_id)
    if not row:
        raise NotFoundError()
    db.delete(row)
    db.commit()


@router.get("/hierarchy")
def hierarchy(
    db: Session = Depends(get_db), _: User = Depends(current_user)
) -> list[dict[str, object]]:
    return [
        {
            "id": u.id,
            "name": u.full_name,
            "job_title": u.job_title,
            "department": u.department,
            "manager_id": u.reports_to_user_id,
            "picture": u.profile_picture_url,
        }
        for u in db.scalars(
            select(User)
            .where(User.is_active, User.user_type == "EMPLOYEE")
            .order_by(User.full_name)
        )
    ]


@router.get("/templates")
def templates(
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("onboarding.template.manage", "onboarding.assign")),
) -> list[dict[str, object]]:
    return [
        template_payload(db, template)
        for template in db.scalars(select(OnboardingTemplate).order_by(OnboardingTemplate.name))
    ]


@router.post("/templates", status_code=201)
def create_template(
    data: TemplateIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding.template.manage")),
) -> dict[str, object]:
    row = OnboardingTemplate(**data.model_dump(exclude={"items"}))
    db.add(row)
    db.flush()
    replace_template_items(db, row, data.items)
    db.commit()
    return template_payload(db, row)


@router.patch("/templates/{template_id}")
def update_template(
    template_id: int,
    data: TemplateIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding.template.manage")),
) -> dict[str, object]:
    row = db.get(OnboardingTemplate, template_id)
    if not row:
        raise NotFoundError()
    for key, value in data.model_dump(exclude={"items"}).items():
        setattr(row, key, value.strip() if key in {"name", "code"} and value else value)
    row.version += 1
    replace_template_items(db, row, data.items)
    db.commit()
    return template_payload(db, row)


@router.delete("/templates/{template_id}", status_code=204)
def deactivate_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding.template.manage")),
) -> None:
    row = db.get(OnboardingTemplate, template_id)
    if not row:
        raise NotFoundError()
    row.is_active = False
    row.version += 1
    db.commit()


def bundle_payload(db: Session, bundle: OnboardingTemplateBundle) -> dict[str, object]:
    items = list(
        db.scalars(
            select(OnboardingTemplateBundleItem)
            .where(OnboardingTemplateBundleItem.bundle_id == bundle.id)
            .order_by(OnboardingTemplateBundleItem.sequence_no)
        )
    )
    return {
        "id": bundle.id,
        "code": bundle.code,
        "name": bundle.name,
        "description": bundle.description,
        "default_duration_days": bundle.default_duration_days,
        "version": bundle.version,
        "is_active": bundle.is_active,
        "items": [
            {
                "template_id": item.template_id,
                "sequence_no": item.sequence_no,
                "start_after_days": item.start_after_days,
                "required": item.is_required,
            }
            for item in items
        ],
    }


@router.get("/catalogs")
def onboarding_catalogs(
    db: Session = Depends(get_db), _: User = Depends(current_user)
) -> dict[str, object]:
    return {
        "task_types": [
            {"code": row.code, "name": row.name}
            for row in db.scalars(
                select(OnboardingTaskType)
                .where(OnboardingTaskType.is_active)
                .order_by(OnboardingTaskType.name)
            )
        ],
        "completion_types": [
            {"code": row.code, "name": row.name}
            for row in db.scalars(
                select(OnboardingCompletionType)
                .where(OnboardingCompletionType.is_active)
                .order_by(OnboardingCompletionType.name)
            )
        ],
    }


@router.get("/bundles")
def bundles(
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("onboarding.template.manage", "onboarding.assign")),
) -> list[dict[str, object]]:
    return [
        bundle_payload(db, row)
        for row in db.scalars(
            select(OnboardingTemplateBundle).order_by(OnboardingTemplateBundle.name)
        )
    ]


def replace_bundle_items(
    db: Session, bundle: OnboardingTemplateBundle, items: list[dict[str, object]]
) -> None:
    db.query(OnboardingTemplateBundleItem).filter(
        OnboardingTemplateBundleItem.bundle_id == bundle.id
    ).delete()
    for index, item in enumerate(items):
        template_id = int(str(item["template_id"]))
        if not db.get(OnboardingTemplate, template_id):
            raise NotFoundError("A bundled checklist template does not exist.")
        db.add(
            OnboardingTemplateBundleItem(
                bundle_id=bundle.id,
                template_id=template_id,
                sequence_no=int(str(item.get("sequence_no", (index + 1) * 10))),
                start_after_days=int(str(item.get("start_after_days", 0))),
                is_required=bool(item.get("required", True)),
            )
        )


@router.post("/bundles", status_code=201)
def create_bundle(
    data: BundleIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding.template.manage")),
) -> dict[str, object]:
    row = OnboardingTemplateBundle(**data.model_dump(exclude={"items"}))
    db.add(row)
    db.flush()
    replace_bundle_items(db, row, data.items)
    db.commit()
    return bundle_payload(db, row)


@router.patch("/bundles/{bundle_id}")
def update_bundle(
    bundle_id: int,
    data: BundleIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding.template.manage")),
) -> dict[str, object]:
    row = db.get(OnboardingTemplateBundle, bundle_id)
    if not row:
        raise NotFoundError()
    for key, value in data.model_dump(exclude={"items"}).items():
        setattr(row, key, value)
    row.version += 1
    replace_bundle_items(db, row, data.items)
    db.commit()
    return bundle_payload(db, row)


@router.delete("/bundles/{bundle_id}", status_code=204)
def delete_bundle(
    bundle_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding.template.manage")),
) -> None:
    row = db.get(OnboardingTemplateBundle, bundle_id)
    if not row:
        raise NotFoundError()
    row.is_active = False
    row.version += 1
    db.commit()


@router.get("/employees")
def onboarding_employees(
    db: Session = Depends(get_db), _: User = Depends(require_permission("onboarding.assign"))
) -> list[dict[str, object]]:
    active_users = list(
        db.scalars(
            select(User)
            .where(User.is_active, User.user_type == "EMPLOYEE")
            .order_by(User.full_name)
        )
    )
    active_plans = {
        plan.user_id: plan
        for plan in db.scalars(select(UserOnboarding).where(UserOnboarding.status == "IN_PROGRESS"))
    }
    return [
        {
            "id": user.id,
            "name": user.full_name,
            "department": user.department,
            "has_active_plan": user.id in active_plans,
            "active_plan_id": active_plans[user.id].id if user.id in active_plans else None,
            "active_plan_name": active_plans[user.id].template_name if user.id in active_plans else None,
            "active_plan_version": active_plans[user.id].version if user.id in active_plans else None,
        }
        for user in active_users
    ]


@router.get("/mentor-candidates")
def mentor_candidates(
    db: Session = Depends(get_db),
    _: User = Depends(
        require_any_permission(
            "onboarding.assign",
            "onboarding.item.override",
            "onboarding.progress.view.team",
            "onboarding.progress.view.department",
        )
    ),
) -> list[dict[str, object]]:
    return [
        {
            "id": user.id,
            "name": user.full_name,
            "department": user.department,
            "job_title": user.job_title,
        }
        for user in db.scalars(select(User).where(User.is_active).order_by(User.full_name))
    ]


@router.get("/progress")
def onboarding_progress(
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> list[dict[str, object]]:
    permissions = set(effective_permissions(db, actor).permissions)
    plans = list(
        db.scalars(select(UserOnboarding).order_by(UserOnboarding.created_at.desc()).limit(200))
    )
    users = {
        user.id: user
        for user in db.scalars(
            select(User).where(User.id.in_({plan.user_id for plan in plans} or {-1}))
        )
    }
    global_scope = bool(permissions.intersection({"onboarding.assign", "onboarding.item.override"}))
    department_ids: set[int] = set()
    if "onboarding.progress.view.department" in permissions and actor.department_id:
        department_ids.update(
            department_descendant_ids(db, actor.department_id, server_today(), include_self=True)
        )
    direct_reports = {user.id for user in users.values() if user.reports_to_user_id == actor.id}
    result: list[dict[str, object]] = []
    for plan in plans:
        employee = users.get(plan.user_id)
        items = list(
            db.scalars(
                select(UserOnboardingItem).where(UserOnboardingItem.user_onboarding_id == plan.id)
            )
        )
        mentors_plan = plan.mentor_user_id == actor.id or any(
            item.mentor_mode == "SPECIFIC" and item.mentor_user_id == actor.id for item in items
        )
        in_scope = global_scope or mentors_plan or plan.user_id == actor.id
        in_scope = in_scope or (
            "onboarding.progress.view.team" in permissions and plan.user_id in direct_reports
        )
        in_scope = in_scope or bool(employee and employee.department_id in department_ids)
        if not in_scope:
            continue
        payload = plan_payload(db, plan)
        overdue = sum(
            item.status not in {"COMPLETED", "SKIPPED"}
            and item.due_date is not None
            and item.due_date < server_today()
            for item in items
        )
        pending_approval = sum(item.approval_status == "PENDING" for item in items)
        manager = db.get(User, employee.reports_to_user_id) if employee and employee.reports_to_user_id else None
        result.append(
            {
                **payload,
                "user_name": employee.full_name if employee else "Unknown user",
                "department": employee.department if employee else None,
                "job_title": employee.job_title if employee else None,
                "manager_name": manager.full_name if manager else None,
                "overdue_count": overdue,
                "pending_approval_count": pending_approval,
                "expected_completion_date": max(
                    (item.due_date for item in items if item.due_date), default=None
                ),
            }
        )
    return result


@router.get("/approvals")
def pending_approvals(
    db: Session = Depends(get_db), actor: User = Depends(current_user)
) -> list[dict[str, object]]:
    can_override = "onboarding.item.override" in effective_permissions(db, actor).permissions
    rows = list(
        db.scalars(
            select(UserOnboardingItem).where(UserOnboardingItem.approval_status == "PENDING")
        )
    )
    result: list[dict[str, object]] = []
    for row in rows:
        plan = db.get(UserOnboarding, row.user_onboarding_id)
        employee = db.get(User, plan.user_id) if plan else None
        effective_mentor_id = (
            row.mentor_user_id if row.mentor_mode == "SPECIFIC"
            else (plan.mentor_user_id if row.mentor_mode == "INHERIT" else None)
        ) if plan else None
        if plan and employee and (
            can_override or employee.reports_to_user_id == actor.id or effective_mentor_id == actor.id
        ):
            result.append(
                {
                    "plan_id": plan.id,
                    "item_id": row.id,
                    "employee_name": employee.full_name,
                    "title": row.title,
                    "completion_type_code": row.completion_type_code,
                    "submitted_at": row.submitted_at,
                    "version": row.version,
                }
            )
    return result


@router.post("/{plan_id}/items/{item_id}/review")
def review_item(
    plan_id: int,
    item_id: int,
    data: ReviewIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> dict[str, object]:
    plan = db.get(UserOnboarding, plan_id)
    row = db.get(UserOnboardingItem, item_id)
    employee = db.get(User, plan.user_id) if plan else None
    can_override = "onboarding.item.override" in effective_permissions(db, actor).permissions
    if not plan or not row or row.user_onboarding_id != plan.id or not employee:
        raise NotFoundError()
    effective_mentor_id = (
        row.mentor_user_id if row.mentor_mode == "SPECIFIC"
        else (plan.mentor_user_id if row.mentor_mode == "INHERIT" else None)
    )
    if not can_override and employee.reports_to_user_id != actor.id and effective_mentor_id != actor.id:
        raise ConflictError(
            "ONBOARDING_REVIEW_SCOPE", "Only the employee's manager or assigned mentor may review this item."
        )
    if row.approval_status != "PENDING":
        raise ConflictError("ONBOARDING_REVIEW_STATE", "This item is not awaiting review.")
    row.approval_status = data.decision
    row.reviewed_by_user_id = actor.id
    row.reviewed_at = server_now()
    row.review_comment = data.comment
    row.status = "COMPLETED" if data.decision == "APPROVED" else "IN_PROGRESS"
    row.completed_at = server_now() if data.decision == "APPROVED" else None
    row.version += 1
    reconcile_plan(db, plan)
    db.commit()
    return plan_payload(db, plan)


@router.post("/{plan_id}/unassign")
def unassign(
    plan_id: int,
    data: UnassignIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("onboarding.assign")),
) -> dict[str, object]:
    plan = db.get(UserOnboarding, plan_id)
    if not plan:
        raise NotFoundError("Onboarding assignment does not exist.")
    if plan.status != "IN_PROGRESS":
        raise ConflictError("ONBOARDING_NOT_ACTIVE", "Only an active onboarding plan can be unassigned.")
    if plan.version != data.version:
        raise ConflictError("ONBOARDING_VERSION_CONFLICT", "The onboarding plan changed. Refresh and try again.")
    previous = {"status": plan.status, "version": plan.version}
    plan.status = "UNASSIGNED"
    plan.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="UserOnboarding",
            entity_id=str(plan.id),
            action="onboarding.unassigned",
            old_values_json=json.dumps(previous),
            new_values_json=json.dumps(
                {"status": plan.status, "version": plan.version, "reason": data.reason}
            ),
        )
    )
    db.commit()
    return plan_payload(db, plan)


@router.post("/assign", status_code=201)
def assign(
    data: AssignIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("onboarding.assign")),
) -> dict[str, object]:
    if db.scalar(
        select(UserOnboarding.id).where(
            UserOnboarding.user_id == data.user_id, UserOnboarding.status == "IN_PROGRESS"
        )
    ):
        raise ConflictError("ACTIVE_ONBOARDING_EXISTS", "This user already has active onboarding.")
    user = db.get(User, data.user_id)
    mentor = db.get(User, data.mentor_user_id) if data.mentor_user_id else None
    if data.mentor_user_id and (not mentor or not mentor.is_active):
        raise ConflictError("ONBOARDING_MENTOR_INVALID", "Select an active mentor.")
    if data.mentor_user_id == data.user_id:
        raise ConflictError("ONBOARDING_MENTOR_SELF", "The employee cannot mentor their own onboarding.")
    if bool(data.template_id) == bool(data.bundle_id):
        raise ConflictError(
            "ONBOARDING_ASSIGNMENT_SOURCE", "Select one template or one program bundle."
        )
    template = db.get(OnboardingTemplate, data.template_id) if data.template_id else None
    bundle = db.get(OnboardingTemplateBundle, data.bundle_id) if data.bundle_id else None
    if (
        not user
        or (template and not template.is_active)
        or (bundle and not bundle.is_active)
        or (not template and not bundle)
    ):
        raise NotFoundError()
    bundle_items = (
        list(
            db.scalars(
                select(OnboardingTemplateBundleItem)
                .where(OnboardingTemplateBundleItem.bundle_id == bundle.id)
                .order_by(OnboardingTemplateBundleItem.sequence_no)
            )
        )
        if bundle
        else []
    )
    templates = (
        [template]
        if template
        else [db.get(OnboardingTemplate, item.template_id) for item in bundle_items]
    )
    active_templates = [item for item in templates if item and item.is_active]
    if not active_templates:
        raise ConflictError(
            "EMPTY_ONBOARDING_PROGRAM", "The selected onboarding program has no active templates."
        )
    start = data.start_date
    duration_by_item = {
        override.template_item_id: override.duration_days for override in data.task_durations
    }
    mentor_by_item = {override.template_item_id: override for override in data.task_durations}
    valid_item_ids = set(
        db.scalars(
            select(OnboardingTemplateItem.id).where(
                OnboardingTemplateItem.template_id.in_([item.id for item in active_templates]),
                OnboardingTemplateItem.is_active,
            )
        )
    )
    if not set(duration_by_item).issubset(valid_item_ids):
        raise ConflictError(
            "ONBOARDING_TASK_DURATION_SOURCE",
            "A task duration does not belong to the selected onboarding program.",
        )
    for override in data.task_durations:
        if override.mentor_mode == "SPECIFIC":
            task_mentor = db.get(User, override.mentor_user_id) if override.mentor_user_id else None
            if not task_mentor or not task_mentor.is_active or task_mentor.id == data.user_id:
                raise ConflictError(
                    "ONBOARDING_TASK_MENTOR_INVALID", "Select an active mentor for each task override."
                )
    plan = UserOnboarding(
        user_id=user.id,
        template_id=active_templates[0].id,
        bundle_id=bundle.id if bundle else None,
        template_name=bundle.name if bundle else active_templates[0].name,
        template_version=bundle.version if bundle else active_templates[0].version,
        start_date=start,
        assigned_by_user_id=actor.id,
        mentor_user_id=data.mentor_user_id,
    )
    db.add(plan)
    db.flush()
    sequence = 0
    for template_row in active_templates:
        bundle_offset = next(
            (item.start_after_days for item in bundle_items if item.template_id == template_row.id),
            0,
        )
        for source in db.scalars(
            select(OnboardingTemplateItem)
            .where(
                OnboardingTemplateItem.template_id == template_row.id,
                OnboardingTemplateItem.is_active,
            )
            .order_by(OnboardingTemplateItem.display_order)
        ):
            sequence += 1
            available_date = start + timedelta(days=bundle_offset + source.start_after_days)
            duration_days = duration_by_item.get(source.id)
            mentor_override = mentor_by_item.get(source.id)
            db.add(
                UserOnboardingItem(
                    user_onboarding_id=plan.id,
                    template_item_id=source.id,
                    title=source.title,
                    description=source.description,
                    display_order=sequence,
                    is_required=source.is_required,
                    material_id=source.material_id,
                    available_date=available_date,
                    due_date=available_date + timedelta(days=duration_days)
                    if duration_days is not None
                    else (
                        start + timedelta(days=bundle_offset + source.due_after_days)
                        if source.due_after_days is not None
                        else None
                    ),
                    task_type_code=source.task_type_code,
                    completion_type_code=source.completion_type_code,
                    requires_approval=source.requires_approval,
                    mentor_mode=mentor_override.mentor_mode if mentor_override else "INHERIT",
                    mentor_user_id=(
                        mentor_override.mentor_user_id
                        if mentor_override and mentor_override.mentor_mode == "SPECIFIC"
                        else None
                    ),
                    status="COMPLETED"
                    if source.completion_type_code == "AUTO_COMPLETE"
                    else "PENDING",
                    completed_at=server_now()
                    if source.completion_type_code == "AUTO_COMPLETE"
                    else None,
                )
            )
    db.commit()
    return plan_payload(db, plan)


@router.post("/{plan_id}/replace", status_code=201)
def replace_assignment(
    plan_id: int,
    data: ReplaceAssignmentIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("onboarding.assign")),
) -> dict[str, object]:
    current = db.get(UserOnboarding, plan_id)
    if not current or current.user_id != data.user_id:
        raise NotFoundError("Onboarding assignment does not exist.")
    if current.status != "IN_PROGRESS":
        raise ConflictError("ONBOARDING_NOT_ACTIVE", "Only an active onboarding plan can be changed.")
    if current.version != data.version:
        raise ConflictError(
            "ONBOARDING_VERSION_CONFLICT", "The onboarding plan changed. Refresh and try again."
        )
    previous = {
        "plan_id": current.id,
        "template_id": current.template_id,
        "bundle_id": current.bundle_id,
        "template_name": current.template_name,
        "version": current.version,
    }
    current.status = "REPLACED"
    current.version += 1
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="UserOnboarding",
            entity_id=str(current.id),
            action="onboarding.assignment_replaced",
            old_values_json=json.dumps(previous),
            new_values_json=json.dumps(
                {
                    "template_id": data.template_id,
                    "bundle_id": data.bundle_id,
                    "start_date": str(data.start_date),
                    "reason": data.reason,
                }
            ),
        )
    )
    return assign(
        AssignIn(
            user_id=data.user_id,
            template_id=data.template_id,
            bundle_id=data.bundle_id,
            start_date=data.start_date,
            mentor_user_id=data.mentor_user_id,
            task_durations=data.task_durations,
        ),
        db,
        actor,
    )
