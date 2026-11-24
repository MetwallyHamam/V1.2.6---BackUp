"""Authoritative Project and task scope checks."""

from sqlalchemy import Select, or_, select, true
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.iam.models import User
from app.modules.iam.service import effective_permissions
from app.modules.projects.models import (
    CompanyProject,
    CrossDepartmentRequest,
    ProjectAssignmentRequest,
    ProjectDepartment,
    ProjectTask,
    ProjectTaskAssignee,
)


def authorized_project_ids(db: Session, actor: User) -> Select[tuple[int]]:
    """Return only Project IDs visible to the actor; managers retain global scope."""
    statement = select(CompanyProject.id).where(CompanyProject.is_active == true())
    if "project.manage" in effective_permissions(db, actor).permissions:
        return statement
    conditions = [
        CompanyProject.created_by_user_id == actor.id,
        CompanyProject.project_manager_user_id == actor.id,
    ]
    if actor.department_id is not None:
        participating = select(ProjectDepartment.id).where(
            ProjectDepartment.project_id == CompanyProject.id,
            ProjectDepartment.department_id == actor.department_id,
        )
        requested = select(ProjectAssignmentRequest.id).where(
            ProjectAssignmentRequest.project_id == CompanyProject.id,
            ProjectAssignmentRequest.requested_department_id == actor.department_id,
        )
        collaboration_requested = select(CrossDepartmentRequest.id).where(
            CrossDepartmentRequest.project_id == CompanyProject.id,
            CrossDepartmentRequest.requested_department_id == actor.department_id,
        )
        conditions.extend(
            [participating.exists(), requested.exists(), collaboration_requested.exists()]
        )
    return statement.where(or_(*conditions))


def require_project_access(db: Session, actor: User, project_id: int) -> CompanyProject:
    project = db.scalar(
        select(CompanyProject).where(
            CompanyProject.id == project_id,
            CompanyProject.id.in_(authorized_project_ids(db, actor)),
        )
    )
    if project is None:
        raise NotFoundError("Project does not exist.")
    return project


def require_task_access(
    db: Session, actor: User, task_id: int, *, assigned_only: bool = False
) -> ProjectTask:
    task = db.get(ProjectTask, task_id)
    if task is None:
        raise NotFoundError("Project task does not exist.")
    require_project_access(db, actor, task.project_id)
    if assigned_only and "project.manage" not in effective_permissions(db, actor).permissions:
        assigned = task.owner_user_id == actor.id or db.scalar(
            select(ProjectTaskAssignee.id).where(
                ProjectTaskAssignee.task_id == task.id,
                ProjectTaskAssignee.user_id == actor.id,
            )
        )
        if not assigned:
            raise NotFoundError("Project task does not exist.")
    return task
