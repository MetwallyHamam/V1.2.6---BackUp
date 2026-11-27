from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.iam.models import User
from app.modules.projects.models import ProjectTemplate, ProjectTemplateVersion
from app.modules.projects.template_plan import TemplatePlan

router = APIRouter(prefix="/project-templates", tags=["project templates"])
Database = Annotated[Session, Depends(get_db)]
TemplateOwner = Annotated[User, Depends(require_permission("project.create"))]


class TemplateVersionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan: TemplatePlan
    publish: bool = False


class TemplateWrite(TemplateVersionWrite):
    name: str = Field(min_length=1, max_length=200, pattern=r"\S")

class TemplateRevisionWrite(TemplateVersionWrite):
    name: str | None = Field(default=None, min_length=1, max_length=200, pattern=r"\S")


class TemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class TemplateVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_id: int
    version_number: int
    plan: TemplatePlan
    published_at: datetime | None


def _owned_template(db: Session, actor: User, template_id: int) -> ProjectTemplate:
    template = db.scalar(
        select(ProjectTemplate).where(
            ProjectTemplate.id == template_id,
            ProjectTemplate.owner_user_id == actor.id,
            ProjectTemplate.archived_at.is_(None),
        )
    )
    if template is None:
        raise NotFoundError("Project template does not exist.")
    return template


def _save_version(
    db: Session, template_id: int, number: int, data: TemplateVersionWrite
) -> ProjectTemplateVersion:
    version = ProjectTemplateVersion(
        template_id=template_id,
        version_number=number,
        plan=data.plan.model_dump(mode="json"),
        published_at=server_now() if data.publish else None,
    )
    db.add(version)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "TEMPLATE_VERSION_CONFLICT", "The template changed. Refresh and try again."
        ) from exc
    db.refresh(version)
    return version


@router.get("", response_model=list[TemplateRead])
def list_templates(db: Database, actor: TemplateOwner) -> list[ProjectTemplate]:
    return list(db.scalars(
        select(ProjectTemplate).where(
            ProjectTemplate.owner_user_id == actor.id, ProjectTemplate.archived_at.is_(None)
        ).order_by(ProjectTemplate.name, ProjectTemplate.id)
    ))


@router.post("", response_model=TemplateVersionRead, status_code=201)
def create_template(
    data: TemplateWrite, db: Database, actor: TemplateOwner
) -> ProjectTemplateVersion:
    template = ProjectTemplate(name=data.name.strip(), owner_user_id=actor.id)
    db.add(template)
    db.flush()
    return _save_version(db, template.id, 1, data)


@router.get("/{template_id}/versions", response_model=list[TemplateVersionRead])
def list_versions(
    template_id: int, db: Database, actor: TemplateOwner
) -> list[ProjectTemplateVersion]:
    _owned_template(db, actor, template_id)
    return list(db.scalars(
        select(ProjectTemplateVersion).where(
            ProjectTemplateVersion.template_id == template_id
        ).order_by(ProjectTemplateVersion.version_number.desc())
    ))


@router.post("/{template_id}/versions", response_model=TemplateVersionRead, status_code=201)
def create_version(
    template_id: int, data: TemplateRevisionWrite, db: Database, actor: TemplateOwner
) -> ProjectTemplateVersion:
    template = _owned_template(db, actor, template_id)
    if data.name is not None:
        template.name = data.name.strip()
    latest = db.scalar(
        select(func.max(ProjectTemplateVersion.version_number)).where(
            ProjectTemplateVersion.template_id == template_id
        )
    )
    return _save_version(db, template_id, (latest or 0) + 1, data)
