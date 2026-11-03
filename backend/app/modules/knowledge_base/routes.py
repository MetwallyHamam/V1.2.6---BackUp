import hashlib
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, require_permission
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, AuthorizationError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import Client, Product, ProductModule, ServiceCatalogItem
from app.modules.iam.models import AuditLog, User
from app.modules.knowledge_base.models import (
    Article,
    ArticleClientLink,
    ArticleModuleLink,
    ArticleProductLink,
    ArticleResource,
    ArticleServiceLink,
    ArticleVersion,
    DownloadCategory,
    KnowledgeCategory,
    KnowledgeUsage,
    TicketArticleLink,
)
from app.modules.tickets.models import ResolutionOutcome, RootCause, Ticket
from app.modules.tickets.service import ensure_ticket_access

router = APIRouter(prefix="/knowledge", tags=["knowledge base"])


class ArticleCreate(BaseModel):
    title: str = Field(min_length=5, max_length=300)
    summary: str = Field(min_length=5, max_length=1000)
    body: str = Field(min_length=10, max_length=50000)
    content_type: Literal["ARTICLE", "DOWNLOAD"] = "ARTICLE"
    download_category_id: int | None = None
    category: str | None = Field(default=None, max_length=150)
    tags: str | None = Field(default=None, max_length=500)
    visibility: Literal["INTERNAL", "CLIENT_PORTAL", "BOTH"] = "INTERNAL"
    category_id: int | None = None
    product_ids: list[int] = Field(default_factory=list, max_length=100)
    product_module_ids: list[int] = Field(default_factory=list, max_length=100)
    service_ids: list[int] = Field(default_factory=list, max_length=100)
    client_ids: list[int] = Field(default_factory=list, max_length=500)
    resolution_summary_template: str | None = Field(default=None, max_length=10000)
    root_cause_ids: list[int] = Field(default_factory=list, max_length=50)
    resolution_service_ids: list[int] = Field(default_factory=list, max_length=50)
    resolution_outcome_id: int | None = None
    permanent_fix_summary_template: str | None = Field(default=None, max_length=10000)
    permanent_fix_status: Literal["PLANNED", "IMPLEMENTED", "NOT_REQUIRED"] | None = None


class ArticleUpdate(ArticleCreate):
    pass


class ArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    summary: str
    body: str
    content_type: str
    download_category_id: int | None
    category: str | None
    category_id: int | None
    tags: str | None
    status: str
    client_visible: bool
    visibility: str
    version: int
    product_ids: list[int]
    product_module_ids: list[int]
    service_ids: list[int]
    client_ids: list[int]
    resolution_summary_template: str | None
    root_cause_ids: list[int]
    resolution_service_ids: list[int]
    resolution_outcome_id: int | None
    permanent_fix_summary_template: str | None
    permanent_fix_status: str | None


class KnowledgeCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str


class DownloadCategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)


class DownloadCategoryUpdate(DownloadCategoryCreate):
    is_active: bool = True


class DownloadCategoryRead(DownloadCategoryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool


class ArticleRecommendation(ArticleRead):
    match_score: int
    match_reasons: list[str]


class ResolutionApplication(BaseModel):
    article_id: int
    article_version: int
    resolution_summary: str
    root_cause_ids: list[int]
    resolution_service_ids: list[int]
    resolution_outcome_id: int | None
    permanent_fix_summary: str | None
    permanent_fix_status: str | None
    match_score: int
    match_reasons: list[str]


class ArticleVersionRead(BaseModel):
    id: int
    version: int
    title: str
    summary: str
    body: str
    status: str
    changed_by_user_id: int
    changed_by_name: str
    created_at: datetime


class ArticleLinkCreate(BaseModel):
    article_id: int
    reason: str | None = Field(default=None, max_length=500)


class ArticleLinkRead(BaseModel):
    id: int
    article_id: int
    title: str
    summary: str
    category: str | None
    status: str
    created_at: datetime


class ResourceUrlCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    external_url: str = Field(min_length=8, max_length=2000)


class ResourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    article_id: int
    resource_type: str
    name: str
    description: str | None
    external_url: str | None
    original_filename: str | None
    content_type: str | None
    size_bytes: int | None
    sha256: str | None
    created_at: datetime


TOOL_EXTENSIONS = {".zip", ".exe", ".msi", ".msix", ".pdf", ".txt", ".docx", ".xlsx"}


def accessible_article(db: Session, article_id: int, user: User) -> Article:
    article = db.get(Article, article_id)
    if not article:
        raise NotFoundError()
    if user.user_type == "CLIENT_PORTAL" and not (
        article.status == "PUBLISHED" and article.visibility in {"CLIENT_PORTAL", "BOTH"}
    ):
        raise AuthorizationError()
    return article


def resource_path(resource: ArticleResource, settings: Settings) -> Path:
    root = Path(settings.attachment_storage_path).expanduser().resolve()
    path = (root / "knowledge" / str(resource.article_id) / str(resource.stored_filename)).resolve()
    if root not in path.parents or not path.is_file():
        raise AppError("RESOURCE_FILE_MISSING", "The resource file is unavailable.", 404)
    return path


def escaped_term(value: str) -> str:
    return "%" + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def replace_scope_links(db: Session, article: Article, data: ArticleCreate) -> None:
    article.category_id = data.category_id
    if data.category_id:
        category = db.get(KnowledgeCategory, data.category_id)
        if not category or not category.is_active:
            raise ConflictError(
                "KNOWLEDGE_CATEGORY_INVALID", "Select an active knowledge category."
            )
        article.category = category.name
    else:
        article.category = data.category
    references = (
        ("products", Product, data.product_ids),
        ("product modules", ProductModule, data.product_module_ids),
        ("services", ServiceCatalogItem, data.service_ids),
        ("clients", Client, data.client_ids),
        ("root causes", RootCause, data.root_cause_ids),
        ("resolution services", ServiceCatalogItem, data.resolution_service_ids),
    )
    for label, model, values in references:
        requested = set(values)
        if not requested:
            continue
        existing = set(db.scalars(select(model.id).where(model.id.in_(requested))))
        if existing != requested:
            raise ConflictError(
                "KNOWLEDGE_SCOPE_INVALID",
                f"One or more selected {label} no longer exist.",
            )
    if data.resolution_outcome_id is not None:
        outcome = db.get(ResolutionOutcome, data.resolution_outcome_id)
        if not outcome or not outcome.is_active:
            raise ConflictError(
                "KNOWLEDGE_SCOPE_INVALID", "Select an active resolution outcome."
            )
    article.root_cause_ids_json = json.dumps(list(dict.fromkeys(data.root_cause_ids)))
    article.resolution_service_ids_json = json.dumps(
        list(dict.fromkeys(data.resolution_service_ids))
    )
    article.product_links = [
        ArticleProductLink(product_id=value) for value in dict.fromkeys(data.product_ids)
    ]
    article.module_links = [
        ArticleModuleLink(product_module_id=value)
        for value in dict.fromkeys(data.product_module_ids)
    ]
    article.service_links = [
        ArticleServiceLink(service_id=value) for value in dict.fromkeys(data.service_ids)
    ]
    article.client_links = [
        ArticleClientLink(client_id=value) for value in dict.fromkeys(data.client_ids)
    ]


def recommendation_score(article: Article, ticket: Ticket) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    if ticket.client_id in article.client_ids:
        score += 35
        reasons.append("same client")
    elif article.client_ids:
        return 0, []
    if ticket.product_id and ticket.product_id in article.product_ids:
        score += 30
        reasons.append("same product")
    if ticket.product_module_id and ticket.product_module_id in article.product_module_ids:
        score += 25
        reasons.append("same product module")
    if ticket.service_id and ticket.service_id in article.service_ids:
        score += 20
        reasons.append("same service")
    ticket_tokens = set(re.findall(r"[a-z0-9]+", f"{ticket.subject} {ticket.description}".casefold()))
    article_tokens = set(
        re.findall(r"[a-z0-9]+", f"{article.title} {article.summary} {article.tags or ''}".casefold())
    )
    keyword_matches = sorted(
        token for token in ticket_tokens & article_tokens if len(token) >= 3
    )
    if keyword_matches:
        score += min(30, len(keyword_matches) * 6)
        reasons.append("keywords: " + ", ".join(keyword_matches[:5]))
    return min(score, 100), reasons


@router.get("/categories", response_model=list[KnowledgeCategoryRead])
def knowledge_categories(
    db: Session = Depends(get_db), _: User = Depends(require_permission("knowledge.view"))
) -> list[KnowledgeCategory]:
    return list(
        db.scalars(
            select(KnowledgeCategory)
            .where(KnowledgeCategory.is_active.in_([True]))
            .order_by(KnowledgeCategory.name)
        )
    )


@router.get("/download-categories", response_model=list[DownloadCategoryRead])
def download_categories(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
) -> list[DownloadCategory]:
    statement = select(DownloadCategory)
    if not include_inactive:
        statement = statement.where(DownloadCategory.is_active.in_([True]))
    return list(db.scalars(statement.order_by(DownloadCategory.name)))


@router.post("/download-categories", response_model=DownloadCategoryRead, status_code=201)
def create_download_category(
    data: DownloadCategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("knowledge.approve")),
) -> DownloadCategory:
    name = data.name.strip()
    if db.scalar(select(DownloadCategory.id).where(DownloadCategory.name == name)):
        raise ConflictError("DOWNLOAD_CATEGORY_EXISTS", "This download category already exists.")
    item = DownloadCategory(name=name, is_active=True)
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.patch("/download-categories/{category_id}", response_model=DownloadCategoryRead)
def update_download_category(
    category_id: int,
    data: DownloadCategoryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("knowledge.approve")),
) -> DownloadCategory:
    item = db.get(DownloadCategory, category_id)
    if not item:
        raise NotFoundError()
    name = data.name.strip()
    duplicate = db.scalar(select(DownloadCategory.id).where(
        DownloadCategory.name == name, DownloadCategory.id != category_id
    ))
    if duplicate:
        raise ConflictError("DOWNLOAD_CATEGORY_EXISTS", "This download category already exists.")
    item.name = name; item.is_active = data.is_active
    db.commit(); db.refresh(item)
    return item


@router.delete("/download-categories/{category_id}", status_code=204)
def delete_download_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("knowledge.approve")),
) -> Response:
    item = db.get(DownloadCategory, category_id)
    if not item:
        raise NotFoundError()
    if db.scalar(select(Article.id).where(Article.download_category_id == category_id).limit(1)):
        raise ConflictError(
            "DOWNLOAD_CATEGORY_IN_USE",
            "This category is used by downloads. Deactivate it instead of deleting it.",
        )
    db.delete(item); db.commit()
    return Response(status_code=204)


def validate_download_category(db: Session, data: ArticleCreate) -> None:
    if data.content_type == "ARTICLE":
        data.download_category_id = None
        return
    category = db.get(DownloadCategory, data.download_category_id) if data.download_category_id else None
    if not category or not category.is_active:
        raise ConflictError("DOWNLOAD_CATEGORY_INVALID", "Select an active download category.")


@router.get("", response_model=list[ArticleRead])
def articles(
    search: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=150),
    category_id: int | None = Query(default=None, ge=1),
    product_id: int | None = Query(default=None, ge=1),
    product_module_id: int | None = Query(default=None, ge=1),
    client_id: int | None = Query(default=None, ge=1),
    content_type: Literal["ARTICLE", "DOWNLOAD"] = "ARTICLE",
    download_category_id: int | None = Query(default=None, ge=1),
    published_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[Article]:
    statement = select(Article).where(Article.content_type == content_type)
    if download_category_id:
        statement = statement.where(Article.download_category_id == download_category_id)
    if user.user_type == "CLIENT_PORTAL":
        statement = statement.where(
            Article.status == "PUBLISHED", Article.visibility.in_(["CLIENT_PORTAL", "BOTH"])
        )
    elif published_only:
        statement = statement.where(Article.status == "PUBLISHED")
    if category:
        statement = statement.where(Article.category == category)
    if category_id is not None:
        statement = statement.where(Article.category_id == category_id)
    if product_id is not None:
        statement = statement.where(
            Article.product_links.any(ArticleProductLink.product_id == product_id)
        )
    if product_module_id is not None:
        statement = statement.where(
            Article.module_links.any(
                ArticleModuleLink.product_module_id == product_module_id
            )
        )
    if client_id is not None:
        statement = statement.where(
            Article.client_links.any(ArticleClientLink.client_id == client_id)
        )
    for token in (search or "").split():
        term = escaped_term(token)
        statement = statement.where(
            or_(
                Article.title.ilike(term, escape="\\"),
                Article.summary.ilike(term, escape="\\"),
                Article.body.ilike(term, escape="\\"),
                Article.category.ilike(term, escape="\\"),
                Article.tags.ilike(term, escape="\\"),
            )
        )
    return list(db.scalars(statement.order_by(Article.updated_at.desc()).limit(limit)))


@router.post("", response_model=ArticleRead, status_code=status.HTTP_201_CREATED)
def create_article(
    data: ArticleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge.create")),
) -> Article:
    validate_download_category(db, data)
    values = data.model_dump(exclude={"product_ids", "product_module_ids", "service_ids", "client_ids", "root_cause_ids", "resolution_service_ids"})
    item = Article(
        **values,
        root_cause_ids_json="[]",
        resolution_service_ids_json="[]",
        client_visible=values["visibility"] in {"CLIENT_PORTAL", "BOTH"},
        owner_user_id=user.id,
    )
    db.add(item)
    db.flush()
    replace_scope_links(db, item, data)
    db.add(
        ArticleVersion(
            article_id=item.id,
            version=1,
            title=item.title,
            summary=item.summary,
            body=item.body,
            status=item.status,
            changed_by_user_id=user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/articles/{article_id}", response_model=ArticleRead)
def get_article(
    article_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> Article:
    item = db.get(Article, article_id)
    if not item:
        raise NotFoundError()
    if user.user_type == "CLIENT_PORTAL" and not (
        item.status == "PUBLISHED" and item.visibility in {"CLIENT_PORTAL", "BOTH"}
    ):
        raise AuthorizationError()
    return item


@router.get("/articles/{article_id}/resources", response_model=list[ResourceRead])
def article_resources(
    article_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[ArticleResource]:
    accessible_article(db, article_id, user)
    return list(db.scalars(select(ArticleResource).where(
        ArticleResource.article_id == article_id
    ).order_by(ArticleResource.created_at.desc())))


@router.post("/articles/{article_id}/resources/url", response_model=ResourceRead, status_code=201)
def add_resource_url(
    article_id: int,
    data: ResourceUrlCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge.create")),
) -> ArticleResource:
    article = accessible_article(db, article_id, user)
    parsed = urlparse(data.external_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise AppError("RESOURCE_URL_INVALID", "Use a valid HTTP or HTTPS download URL.")
    resource = ArticleResource(article_id=article.id, resource_type="URL", name=data.name.strip(), description=data.description, external_url=data.external_url.strip(), created_by_user_id=user.id)
    db.add(resource)
    db.flush()
    db.add(AuditLog(actor_user_id=user.id, entity_type="KnowledgeResource", entity_id=str(resource.id), action="knowledge.resource.url_added", new_values_json=json.dumps({"article_id": article.id, "name": resource.name, "url": resource.external_url})))
    db.commit(); db.refresh(resource)
    return resource


@router.post("/articles/{article_id}/resources/file", response_model=ResourceRead, status_code=201)
async def upload_resource_file(
    article_id: int,
    upload: UploadFile = File(...),
    name: str = Form(..., min_length=2, max_length=255),
    description: str | None = Form(default=None, max_length=1000),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission("knowledge.create")),
) -> ArticleResource:
    article = accessible_article(db, article_id, user)
    original = Path(upload.filename or "tool").name.strip()
    if not original or len(original) > 255 or re.search(r"[\x00-\x1f\x7f]", original):
        raise AppError("RESOURCE_NAME_INVALID", "The uploaded filename is invalid.")
    extension = Path(original).suffix.casefold()
    if extension not in TOOL_EXTENSIONS:
        raise AppError("RESOURCE_TYPE_NOT_ALLOWED", "Upload ZIP, EXE, MSI, MSIX, PDF, TXT, DOCX, or XLSX files.", 415)
    root = Path(settings.attachment_storage_path).expanduser().resolve()
    directory = (root / "knowledge" / str(article.id)).resolve()
    if root not in directory.parents:
        raise AppError("RESOURCE_STORAGE_INVALID", "Resource storage is invalid.", 500)
    directory.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex}{extension}"
    temporary, final = directory / f".{stored}.uploading", directory / stored
    digest = hashlib.sha256(); size = 0; header = bytearray()
    try:
        with temporary.open("xb") as destination:
            while chunk := await upload.read(64 * 1024):
                size += len(chunk)
                if size > settings.attachment_max_bytes:
                    raise AppError("RESOURCE_TOO_LARGE", f"Files may not exceed {settings.attachment_max_bytes} bytes.", 413)
                digest.update(chunk); destination.write(chunk)
                if len(header) < 16: header.extend(chunk[:16 - len(header)])
        if not size: raise AppError("EMPTY_RESOURCE", "The uploaded file is empty.")
        if extension == ".exe" and not bytes(header).startswith(b"MZ"):
            raise AppError("RESOURCE_CONTENT_INVALID", "The executable signature is invalid.", 415)
        if extension in {".zip", ".docx", ".xlsx", ".msix"} and not bytes(header).startswith(b"PK"):
            raise AppError("RESOURCE_CONTENT_INVALID", "The archive signature is invalid.", 415)
        os.replace(temporary, final)
        resource = ArticleResource(article_id=article.id, resource_type="FILE", name=name.strip(), description=description, original_filename=original, stored_filename=stored, content_type=upload.content_type or "application/octet-stream", size_bytes=size, sha256=digest.hexdigest(), created_by_user_id=user.id)
        db.add(resource); db.flush()
        db.add(AuditLog(actor_user_id=user.id, entity_type="KnowledgeResource", entity_id=str(resource.id), action="knowledge.resource.file_uploaded", new_values_json=json.dumps({"article_id": article.id, "filename": original, "size_bytes": size, "sha256": resource.sha256})))
        db.commit(); db.refresh(resource)
        return resource
    except Exception:
        temporary.unlink(missing_ok=True); final.unlink(missing_ok=True); raise
    finally:
        await upload.close()


@router.get("/articles/{article_id}/resources/{resource_id}/download")
def download_resource(
    article_id: int,
    resource_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(current_user),
) -> FileResponse:
    accessible_article(db, article_id, user)
    resource = db.scalar(select(ArticleResource).where(ArticleResource.id == resource_id, ArticleResource.article_id == article_id, ArticleResource.resource_type == "FILE"))
    if not resource: raise NotFoundError("Resource does not exist.")
    return FileResponse(resource_path(resource, settings), media_type="application/octet-stream", filename=resource.original_filename)


@router.delete("/articles/{article_id}/resources/{resource_id}", status_code=204)
def delete_resource(
    article_id: int,
    resource_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission("knowledge.create")),
) -> Response:
    accessible_article(db, article_id, user)
    resource = db.scalar(select(ArticleResource).where(ArticleResource.id == resource_id, ArticleResource.article_id == article_id))
    if not resource: raise NotFoundError("Resource does not exist.")
    path = resource_path(resource, settings) if resource.resource_type == "FILE" else None
    db.add(AuditLog(actor_user_id=user.id, entity_type="KnowledgeResource", entity_id=str(resource.id), action="knowledge.resource.deleted", old_values_json=json.dumps({"article_id": article_id, "name": resource.name})))
    db.delete(resource); db.commit()
    if path: path.unlink(missing_ok=True)
    return Response(status_code=204)


@router.get(
    "/articles/{article_id}/versions", response_model=list[ArticleVersionRead]
)
def article_versions(
    article_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge.view")),
) -> list[dict[str, object]]:
    if user.user_type == "CLIENT_PORTAL":
        raise AuthorizationError()
    if not db.get(Article, article_id):
        raise NotFoundError()
    rows = db.execute(
        select(ArticleVersion, User)
        .join(User, User.id == ArticleVersion.changed_by_user_id)
        .where(ArticleVersion.article_id == article_id)
        .order_by(ArticleVersion.version.desc())
    )
    return [
        {
            "id": version.id,
            "version": version.version,
            "title": version.title,
            "summary": version.summary,
            "body": version.body,
            "status": version.status,
            "changed_by_user_id": editor.id,
            "changed_by_name": editor.full_name,
            "created_at": version.created_at,
        }
        for version, editor in rows
    ]


@router.patch("/articles/{article_id}", response_model=ArticleRead)
def update_article(
    article_id: int,
    data: ArticleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge.create")),
) -> Article:
    item = db.get(Article, article_id)
    if not item:
        raise NotFoundError()
    validate_download_category(db, data)
    previous_version = item.version
    for key, value in data.model_dump(exclude={"product_ids", "product_module_ids", "service_ids", "client_ids", "root_cause_ids", "resolution_service_ids"}).items():
        setattr(item, key, value)
    replace_scope_links(db, item, data)
    item.client_visible = item.visibility in {"CLIENT_PORTAL", "BOTH"}
    item.version += 1
    db.add(
        ArticleVersion(
            article_id=item.id,
            version=item.version,
            title=item.title,
            summary=item.summary,
            body=item.body,
            status=item.status,
            changed_by_user_id=user.id,
        )
    )
    db.add(
        AuditLog(
            actor_user_id=user.id,
            entity_type="KnowledgeArticle",
            entity_id=str(item.id),
            action="knowledge.article.updated",
            old_values_json=json.dumps({"version": previous_version}),
            new_values_json=json.dumps({"version": item.version}),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.post("/articles/{article_id}/publish", response_model=ArticleRead)
def publish(
    article_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge.approve")),
) -> Article:
    item = db.get(Article, article_id)
    if not item:
        raise NotFoundError()
    if item.status not in {"DRAFT", "REVIEW", "APPROVED"}:
        raise ConflictError(
            "ARTICLE_STATE_INVALID", "Article cannot be published from its current state."
        )
    item.status = "PUBLISHED"
    item.version += 1
    db.add(
        ArticleVersion(
            article_id=item.id,
            version=item.version,
            title=item.title,
            summary=item.summary,
            body=item.body,
            status=item.status,
            changed_by_user_id=user.id,
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.post("/articles/{article_id}/unpublish", response_model=ArticleRead)
def unpublish(
    article_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge.approve")),
) -> Article:
    item = db.get(Article, article_id)
    if not item:
        raise NotFoundError()
    if item.status != "PUBLISHED":
        raise ConflictError(
            "ARTICLE_STATE_INVALID", "Only a published article can be unpublished."
        )
    item.status = "DRAFT"
    item.version += 1
    db.add(
        ArticleVersion(
            article_id=item.id,
            version=item.version,
            title=item.title,
            summary=item.summary,
            body=item.body,
            status=item.status,
            changed_by_user_id=user.id,
        )
    )
    db.add(
        AuditLog(
            actor_user_id=user.id,
            entity_type="KnowledgeArticle",
            entity_id=str(item.id),
            action="knowledge.article.unpublished",
            old_values_json=json.dumps({"status": "PUBLISHED"}),
            new_values_json=json.dumps({"status": "DRAFT", "version": item.version}),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(
    article_id: int,
    unlink_tickets: bool = Query(default=False),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_permission("knowledge.approve")),
) -> Response:
    item = db.get(Article, article_id)
    if not item:
        raise NotFoundError()
    linked_ticket_ids = list(db.scalars(
        select(TicketArticleLink.ticket_id).where(
            TicketArticleLink.article_id == article_id
        )
    ))
    if linked_ticket_ids and not unlink_tickets:
        raise ConflictError(
            "ARTICLE_IN_USE",
            f"This article is linked to {len(linked_ticket_ids)} ticket(s). Confirm unlinking before deletion.",
        )
    resources = list(db.scalars(select(ArticleResource).where(ArticleResource.article_id == article_id)))
    root = Path(settings.attachment_storage_path).expanduser().resolve()
    files = [(root / "knowledge" / str(article_id) / str(resource.stored_filename)).resolve() for resource in resources if resource.resource_type == "FILE"]
    db.add(
        AuditLog(
            actor_user_id=user.id,
            entity_type="KnowledgeArticle",
            entity_id=str(item.id),
            action="knowledge.article.deleted",
            old_values_json=json.dumps(
                {"title": item.title, "status": item.status, "version": item.version, "unlinked_ticket_ids": linked_ticket_ids}
            ),
        )
    )
    if linked_ticket_ids:
        db.execute(delete(TicketArticleLink).where(TicketArticleLink.article_id == article_id))
    db.execute(delete(ArticleResource).where(ArticleResource.article_id == article_id))
    db.delete(item)
    db.commit()
    for path in files:
        if root in path.parents: path.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tickets/{ticket_id}/links", response_model=list[ArticleLinkRead])
def ticket_article_links(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge.view")),
) -> list[dict[str, object]]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    rows = db.execute(
        select(TicketArticleLink, Article)
        .join(Article, Article.id == TicketArticleLink.article_id)
        .where(TicketArticleLink.ticket_id == ticket_id)
        .order_by(TicketArticleLink.created_at)
    )
    return [
        {
            "id": link.id,
            "article_id": article.id,
            "title": article.title,
            "summary": article.summary,
            "category": article.category,
            "status": article.status,
            "created_at": link.created_at,
        }
        for link, article in rows
    ]


@router.get(
    "/tickets/{ticket_id}/recommendations", response_model=list[ArticleRecommendation]
)
def ticket_knowledge_recommendations(
    ticket_id: int,
    limit: int = Query(default=10, ge=1, le=25),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge.view")),
) -> list[dict[str, object]]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    candidates = list(
        db.scalars(
            select(Article)
            .where(Article.status == "PUBLISHED", Article.content_type == "ARTICLE")
            .order_by(Article.updated_at.desc())
            .limit(500)
        )
    )
    ranked: list[tuple[int, Article, list[str]]] = []
    for article in candidates:
        score, reasons = recommendation_score(article, ticket)
        if score > 0:
            ranked.append((score, article, reasons))
    ranked.sort(key=lambda row: (row[0], row[1].updated_at), reverse=True)
    return [
        {
            **ArticleRead.model_validate(article).model_dump(),
            "match_score": score,
            "match_reasons": reasons,
        }
        for score, article, reasons in ranked[:limit]
    ]


@router.post(
    "/tickets/{ticket_id}/articles/{article_id}/apply-resolution",
    response_model=ResolutionApplication,
)
def apply_article_resolution(
    ticket_id: int,
    article_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge.view")),
) -> dict[str, object]:
    if user.user_type == "CLIENT_PORTAL":
        raise AuthorizationError()
    ticket = db.get(Ticket, ticket_id)
    article = db.get(Article, article_id)
    if not ticket or not article:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    if article.status != "PUBLISHED":
        raise ConflictError("ARTICLE_NOT_PUBLISHED", "Only published knowledge can be applied.")
    score, reasons = recommendation_score(article, ticket)
    if article.client_ids and ticket.client_id not in article.client_ids:
        raise ConflictError(
            "ARTICLE_CLIENT_MISMATCH", "This knowledge article is not approved for this client."
        )
    if not db.scalar(
        select(TicketArticleLink.id).where(
            TicketArticleLink.ticket_id == ticket.id,
            TicketArticleLink.article_id == article.id,
        )
    ):
        db.add(
            TicketArticleLink(
                ticket_id=ticket.id,
                article_id=article.id,
                linked_by_user_id=user.id,
                reason="Applied as a resolution template",
            )
        )
    db.add(
        KnowledgeUsage(
            article_id=article.id,
            article_version=article.version,
            ticket_id=ticket.id,
            client_id=ticket.client_id,
            usage_type="APPLIED_TO_RESOLUTION",
            match_score=score,
            match_reasons_json=json.dumps(reasons),
            used_by_user_id=user.id,
        )
    )
    db.add(
        AuditLog(
            actor_user_id=user.id,
            entity_type="KnowledgeArticle",
            entity_id=str(article.id),
            action="knowledge.resolution_template.applied",
            new_values_json=json.dumps(
                {"ticket_id": ticket.id, "article_version": article.version, "match_score": score}
            ),
        )
    )
    db.commit()
    return {
        "article_id": article.id,
        "article_version": article.version,
        "resolution_summary": article.resolution_summary_template or article.summary,
        "root_cause_ids": article.root_cause_ids,
        "resolution_service_ids": article.resolution_service_ids,
        "resolution_outcome_id": article.resolution_outcome_id,
        "permanent_fix_summary": article.permanent_fix_summary_template,
        "permanent_fix_status": article.permanent_fix_status,
        "match_score": score,
        "match_reasons": reasons,
    }


@router.post(
    "/tickets/{ticket_id}/links",
    response_model=ArticleLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def link_article(
    ticket_id: int,
    data: ArticleLinkCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge.view")),
) -> dict[str, object]:
    if user.user_type == "CLIENT_PORTAL":
        raise AuthorizationError()
    ticket = db.get(Ticket, ticket_id)
    article = db.get(Article, data.article_id)
    if not ticket or not article:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    if article.status != "PUBLISHED":
        raise ConflictError(
            "ARTICLE_NOT_PUBLISHED",
            "Only published knowledge articles can be linked to tickets.",
        )
    if db.scalar(
        select(TicketArticleLink.id).where(
            TicketArticleLink.ticket_id == ticket_id,
            TicketArticleLink.article_id == article.id,
        )
    ):
        raise ConflictError("ARTICLE_ALREADY_LINKED", "This article is already linked.")
    link = TicketArticleLink(
        ticket_id=ticket_id,
        article_id=article.id,
        linked_by_user_id=user.id,
        reason=data.reason,
    )
    db.add(link)
    db.add(
        AuditLog(
            actor_user_id=user.id,
            entity_type="TicketArticleLink",
            entity_id=str(ticket_id),
            action="ticket.knowledge.linked",
            reason=data.reason,
            new_values_json=json.dumps({"article_id": article.id}),
        )
    )
    db.commit()
    db.refresh(link)
    return {
        "id": link.id,
        "article_id": article.id,
        "title": article.title,
        "summary": article.summary,
        "category": article.category,
        "status": article.status,
        "created_at": link.created_at,
    }


@router.delete("/tickets/{ticket_id}/links/{link_id}", status_code=204)
def unlink_article(
    ticket_id: int,
    link_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("knowledge.view")),
) -> Response:
    if user.user_type == "CLIENT_PORTAL":
        raise AuthorizationError()
    ticket = db.get(Ticket, ticket_id)
    link = db.scalar(
        select(TicketArticleLink).where(
            TicketArticleLink.id == link_id,
            TicketArticleLink.ticket_id == ticket_id,
        )
    )
    if not ticket or not link:
        raise NotFoundError()
    ensure_ticket_access(db, user, ticket)
    db.add(
        AuditLog(
            actor_user_id=user.id,
            entity_type="TicketArticleLink",
            entity_id=str(ticket_id),
            action="ticket.knowledge.unlinked",
            old_values_json=json.dumps({"article_id": link.article_id}),
        )
    )
    db.delete(link)
    db.commit()
    return Response(status_code=204)
