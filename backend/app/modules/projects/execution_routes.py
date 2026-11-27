import json
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select, true, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_any_permission, require_permission
from app.core.clock import server_now
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import SupportTeam, SupportTeamMember
from app.modules.iam.models import AuditLog, User
from app.modules.iam.service import effective_permissions
from app.modules.projects.access import (
    authorized_project_ids,
    require_project_access,
    require_task_access,
)
from app.modules.projects.execution_schemas import (
    ApprovalWrite,
    BlockerWrite,
    DeliverySubmissionWrite,
    EvidenceWrite,
    ReviewWrite,
    TaskActionWrite,
    TaskCreate,
    TaskOwnerWrite,
    UnplannedTaskCreate,
    WorkLogWrite,
)
from app.modules.projects.lifecycle import transition_project
from app.modules.projects.models import (
    CompanyProject,
    ProjectAssignmentRequest,
    ProjectDepartment,
    ProjectEvidence,
    ProjectPhase,
    ProjectTask,
    ProjectTaskAssignee,
    ProjectTaskBlocker,
    ProjectTaskDependency,
    ProjectTaskReview,
    ProjectTeam,
    ProjectWorkLog,
)
from app.modules.projects.numbering import format_task_number, lock_number_allocation

router = APIRouter(tags=["project execution"])

TRANSITIONS = {
    "BACKLOG": {"READY", "CANCELLED"},
    "READY": {"IN_PROGRESS", "BLOCKED", "CANCELLED"},
    "IN_PROGRESS": {"BLOCKED", "REVIEW", "CANCELLED"},
    "BLOCKED": {"READY", "IN_PROGRESS", "CANCELLED"},
    "REVIEW": {"IN_PROGRESS", "DONE"},
    "DONE": {"IN_PROGRESS"},
    "CANCELLED": {"BACKLOG"},
}
EXECUTION_PROJECT_STATES = {
    "READY_FOR_EXECUTION",
    "IN_EXECUTION",
    "DELIVERY_REVIEW",
    # Temporary forward-compatible legacy states; new Projects use the canonical states above.
    "PLANNING",
    "ACTIVE",
}


def _values(row: Any) -> dict[str, Any]:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def _task(
    db: Session, task_id: int, actor: User, *, assigned_only: bool = False
) -> ProjectTask:
    return require_task_access(db, actor, task_id, assigned_only=assigned_only)


def _assert_project_access(db: Session, actor: User, project_id: int) -> None:
    require_project_access(db, actor, project_id)


def _execution_project(db: Session, actor: User, project_id: int) -> CompanyProject:
    project = require_project_access(db, actor, project_id)
    if project.status not in EXECUTION_PROJECT_STATES:
        raise ConflictError(
            "PROJECT_NOT_EXECUTABLE",
            "Implementation must accept this project before execution work can change.",
        )
    return project


def _audit(
    db: Session, actor: User, task: ProjectTask, action: str, values: dict[str, object]
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="project_task",
            entity_id=str(task.id),
            action=action,
            new_values_json=json.dumps(values, default=str),
        )
    )


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "PROJECT_EXECUTION_CONFLICT",
            "The task number, assignment, or dependency conflicts with existing project data.",
        ) from exc


def _recalculate_project(db: Session, project_id: int) -> None:
    project = db.get(CompanyProject, project_id)
    rows = list(
        db.scalars(
            select(ProjectTask).where(
                ProjectTask.project_id == project_id,
                ProjectTask.status != "CANCELLED",
                or_(
                    ProjectTask.classification == "PLANNED",
                    ProjectTask.approval_status == "APPROVED",
                ),
            )
        )
    )
    total = sum(row.weight for row in rows)
    if project:
        project.progress_percent = (
            round(sum(row.weight * row.progress_percent for row in rows) / total) if total else 0
        )


def _create_task(
    db: Session, project_id: int, data: TaskCreate, actor: User, classification: str
) -> ProjectTask:
    project = require_project_access(db, actor, project_id)
    if not db.get(User, data.owner_user_id):
        raise NotFoundError("Task owner does not exist.")
    if data.phase_id:
        phase = db.get(ProjectPhase, data.phase_id)
        if not phase or phase.project_id != project_id:
            raise ConflictError("INVALID_TASK_PHASE", "Task phase must belong to this project.")
    values = data.model_dump(
        exclude={
            "assignees",
            "dependency_ids",
            "unplanned_cause",
            "unplanned_source",
            "impact_summary",
            "schedule_impact_minutes",
        }
    )
    if classification == "UNPLANNED" and not data.task_number.strip():
        lock_number_allocation(db, f"SupportHub.TaskNumber.{project_id}")
        prefix = project.project_number.upper()
        last_serial = 0
        for number in db.scalars(select(ProjectTask.task_number).where(ProjectTask.project_id == project_id)):
            suffix = number.rpartition("-")[2]
            if suffix.isascii() and suffix.isdecimal():
                serial = int(suffix)
                if number.upper() == format_task_number(prefix, serial):
                    last_serial = max(last_serial, serial)
        values["task_number"] = format_task_number(prefix, last_serial + 1)
    row = ProjectTask(
        project_id=project_id,
        classification=classification,
        approval_status="PENDING" if classification == "UNPLANNED" else "NOT_REQUIRED",
        created_by_user_id=actor.id,
        **values,
    )
    if classification == "UNPLANNED":
        if not isinstance(data, UnplannedTaskCreate):
            raise ConflictError("INVALID_UNPLANNED_WORK", "Unplanned work details are required.")
        row.unplanned_cause = data.unplanned_cause
        row.unplanned_source = data.unplanned_source
        row.impact_summary = data.impact_summary
        row.schedule_impact_minutes = data.schedule_impact_minutes
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("TASK_NUMBER_CONFLICT", "The task number is already in use. Try saving again.") from exc
    assignments = data.assignees or []
    for item in assignments:
        if not db.get(User, item.user_id):
            raise NotFoundError("An assigned engineer does not exist.")
        db.add(
            ProjectTaskAssignee(
                task_id=row.id,
                user_id=item.user_id,
                allocation_percent=item.allocation_percent,
                planned_minutes=item.planned_minutes,
                is_accountable=item.is_accountable or item.user_id == data.owner_user_id,
            )
        )
    if not any(item.user_id == data.owner_user_id for item in assignments):
        db.add(
            ProjectTaskAssignee(
                task_id=row.id,
                user_id=data.owner_user_id,
                allocation_percent=100,
                planned_minutes=data.estimate_minutes,
                is_accountable=True,
            )
        )
    for dependency_id in set(data.dependency_ids):
        dependency = _task(db, dependency_id, actor)
        if dependency.project_id != project_id or dependency.id == row.id:
            raise ConflictError(
                "INVALID_TASK_DEPENDENCY",
                "Dependencies must be different tasks in the same project.",
            )
        db.add(ProjectTaskDependency(task_id=row.id, depends_on_task_id=dependency_id))
    _audit(
        db,
        actor,
        row,
        "project.task.created",
        {"classification": classification, "task_number": row.task_number},
    )
    _commit(db)
    db.refresh(row)
    return row


@router.get("/projects/{project_id}/tasks")
def list_tasks(
    project_id: int,
    classification: str | None = None,
    task_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("implementation.task.view")),
) -> list[dict[str, Any]]:
    _assert_project_access(db, actor, project_id)
    statement = select(ProjectTask).where(ProjectTask.project_id == project_id)
    if classification:
        statement = statement.where(ProjectTask.classification == classification.upper())
    if task_status:
        statement = statement.where(ProjectTask.status == task_status.upper())
    rows = list(db.scalars(statement.order_by(ProjectTask.planned_end_date, ProjectTask.id)))
    result = []
    for row in rows:
        item = _values(row)
        item["assignees"] = [
            _values(x)
            for x in db.scalars(
                select(ProjectTaskAssignee).where(ProjectTaskAssignee.task_id == row.id)
            )
        ]
        item["actual_minutes"] = (
            db.scalar(
                select(func.coalesce(func.sum(ProjectWorkLog.duration_minutes), 0)).where(
                    ProjectWorkLog.task_id == row.id
                )
            )
            or 0
        )
        result.append(item)
    return result


@router.get("/projects/{project_id}/task-dependencies")
def list_task_dependencies(
    project_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("implementation.task.view")),
) -> list[dict[str, Any]]:
    require_project_access(db, actor, project_id)
    task_ids = select(ProjectTask.id).where(ProjectTask.project_id == project_id)
    rows = db.scalars(
        select(ProjectTaskDependency)
        .where(
            ProjectTaskDependency.task_id.in_(task_ids),
            ProjectTaskDependency.depends_on_task_id.in_(task_ids),
        )
        .order_by(ProjectTaskDependency.id)
    )
    return [_values(row) for row in rows]


@router.get("/project-tasks/my-work")
def my_work(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("implementation.task.view")),
) -> list[dict[str, Any]]:
    statement = (
        select(ProjectTask)
        .join(ProjectTaskAssignee, ProjectTaskAssignee.task_id == ProjectTask.id)
        .where(
            ProjectTaskAssignee.user_id == actor.id,
            ProjectTask.project_id.in_(authorized_project_ids(db, actor)),
            ProjectTask.status.in_(["READY", "IN_PROGRESS", "BLOCKED", "REVIEW"]),
        )
        .order_by(ProjectTask.planned_end_date, ProjectTask.priority)
    )
    return [_values(row) for row in db.scalars(statement)]


@router.get("/project-tasks/team-delivery")
def team_delivery(
    db: Session = Depends(get_db),
    actor: User = Depends(require_any_permission("project.assignment.respond", "implementation.task.assign")),
) -> list[dict[str, Any]]:
    if actor.department_id is None:
        return []
    latest_accepted = (
        select(func.max(ProjectAssignmentRequest.id))
        .where(ProjectAssignmentRequest.status == "ACCEPTED",
               ProjectAssignmentRequest.requested_department_id == actor.department_id)
        .group_by(ProjectAssignmentRequest.project_id)
    )
    statement = (
        select(CompanyProject, ProjectAssignmentRequest, SupportTeam)
        .join(ProjectAssignmentRequest, ProjectAssignmentRequest.project_id == CompanyProject.id)
        .outerjoin(SupportTeam, SupportTeam.id == ProjectAssignmentRequest.requested_team_id)
        .where(
            CompanyProject.id.in_(authorized_project_ids(db, actor)),
            CompanyProject.status.notin_(["COMPLETED", "CANCELLED"]),
            ProjectAssignmentRequest.id.in_(latest_accepted),
        )
        .order_by(ProjectAssignmentRequest.requested_end_date, CompanyProject.id)
        .limit(50)
    )
    if "project.assignment.respond" not in effective_permissions(db, actor).permissions:
        assigned_teams = select(SupportTeam.id).where(
            SupportTeam.department_id == actor.department_id,
            SupportTeam.is_active == true(),
            or_(SupportTeam.leader_user_id == actor.id, SupportTeam.id.in_(
                select(SupportTeamMember.team_id).where(SupportTeamMember.user_id == actor.id)
            )),
        )
        statement = statement.where(CompanyProject.id.in_(select(ProjectTeam.project_id).where(
            ProjectTeam.role == "IMPLEMENTATION", ProjectTeam.team_id.in_(assigned_teams),
        )))
    return [{
        "project_id": project.id, "project_number": project.project_number, "name": project.name,
        "status": project.status, "progress_percent": project.progress_percent,
        "team_name": team.name if team else None,
        "start_date": request.requested_start_date or project.planned_start_date,
        "end_date": request.requested_end_date or project.planned_end_date,
    } for project, request, team in db.execute(statement)]


@router.get("/project-tasks/capacity-plan")
def capacity_plan(
    weeks: int = Query(default=8, ge=1, le=26),
    db: Session = Depends(get_db),
    actor: User = Depends(require_any_permission("project.assignment.respond", "implementation.task.assign")),
) -> dict[str, Any]:
    """Return a department-scoped weekly workload forecast for accepted delivery work."""
    if actor.department_id is None:
        return {"week_starts": [], "teams": [], "unassigned_projects": []}
    today = server_now().date()
    first_week = today - timedelta(days=today.weekday())
    week_starts = [first_week + timedelta(days=7 * index) for index in range(weeks)]
    teams = list(db.scalars(select(SupportTeam).where(
        SupportTeam.department_id == actor.department_id, SupportTeam.is_active == true(),
    ).order_by(SupportTeam.name, SupportTeam.id)))
    permitted_team_ids = {team.id for team in teams}
    if "project.assignment.respond" not in effective_permissions(db, actor).permissions:
        permitted_team_ids = {
            team.id for team in teams if team.leader_user_id == actor.id or db.scalar(select(
                SupportTeamMember.id
            ).where(SupportTeamMember.team_id == team.id, SupportTeamMember.user_id == actor.id))
        }
        teams = [team for team in teams if team.id in permitted_team_ids]
    member_counts = {
        team_id: count
        for team_id, count in db.execute(
            select(SupportTeamMember.team_id, func.count(SupportTeamMember.user_id))
            .where(SupportTeamMember.team_id.in_(permitted_team_ids))
            .group_by(SupportTeamMember.team_id)
        )
    } if permitted_team_ids else {}
    latest_accepted = (
        select(func.max(ProjectAssignmentRequest.id))
        .where(ProjectAssignmentRequest.status == "ACCEPTED",
               ProjectAssignmentRequest.requested_department_id == actor.department_id)
        .group_by(ProjectAssignmentRequest.project_id)
    )
    accepted = list(db.execute(
        select(CompanyProject, ProjectAssignmentRequest)
        .join(ProjectAssignmentRequest, ProjectAssignmentRequest.project_id == CompanyProject.id)
        .where(CompanyProject.id.in_(authorized_project_ids(db, actor)),
               CompanyProject.status.notin_(["COMPLETED", "CANCELLED"]),
               ProjectAssignmentRequest.id.in_(latest_accepted))
    ))
    project_team = {project.id: request.requested_team_id for project, request in accepted}
    unassigned = [{
        "project_id": project.id, "project_number": project.project_number, "name": project.name,
        "start_date": request.requested_start_date or project.planned_start_date,
        "end_date": request.requested_end_date or project.planned_end_date,
    } for project, request in accepted if request.requested_team_id is None]
    project_ids = [project.id for project, _ in accepted if project_team[project.id] in permitted_team_ids]
    loads: dict[tuple[int, date], int] = {}
    if project_ids:
        for task in db.scalars(select(ProjectTask).where(
            ProjectTask.project_id.in_(project_ids),
            ProjectTask.status.notin_(["DONE", "CANCELLED"]),
        )):
            team_id = project_team.get(task.project_id)
            start = task.planned_start_date or first_week
            finish = task.planned_end_date or start
            active_weeks = [week for week in week_starts if week <= finish and week + timedelta(days=6) >= start]
            if team_id and active_weeks:
                minutes = max(task.estimate_minutes, 0)
                per_week = (minutes + len(active_weeks) - 1) // len(active_weeks)
                for week in active_weeks:
                    loads[(team_id, week)] = loads.get((team_id, week), 0) + per_week
    return {
        "week_starts": week_starts,
        "teams": [{
            "team_id": team.id, "team_name": team.name,
            "member_count": member_counts.get(team.id, 0),
            "weeks": [{
                "week_start": week, "planned_minutes": loads.get((team.id, week), 0),
                "capacity_minutes": member_counts.get(team.id, 0) * 40 * 60,
                "overbooked": loads.get((team.id, week), 0) > member_counts.get(team.id, 0) * 40 * 60,
            } for week in week_starts],
        } for team in teams],
        "unassigned_projects": unassigned,
    }


def _delivery_owner_options(db: Session, actor: User, project_id: int) -> list[User]:
    require_project_access(db, actor, project_id)
    accepted = db.scalar(
        select(ProjectAssignmentRequest).where(
            ProjectAssignmentRequest.project_id == project_id,
            ProjectAssignmentRequest.status == "ACCEPTED",
            ProjectAssignmentRequest.requested_department_id == actor.department_id,
        ).order_by(ProjectAssignmentRequest.id.desc()).limit(1)
    )
    if accepted is None:
        raise NotFoundError("Project is outside your delivery scope.")
    team = db.get(SupportTeam, accepted.requested_team_id) if accepted.requested_team_id else None
    if team is not None and (not team.is_active or team.department_id != actor.department_id):
        raise ConflictError("DELIVERY_TEAM_UNAVAILABLE", "The accepted delivery team is unavailable.")
    coordinator = "project.assignment.respond" in effective_permissions(db, actor).permissions
    if not coordinator and (team is None or team.leader_user_id != actor.id):
        raise NotFoundError("Project is outside your delivery team.")
    options = select(User).where(
        User.is_active == true(), User.user_type == "EMPLOYEE", User.department_id == actor.department_id,
    )
    if team is not None:
        options = options.where(or_(User.id == team.leader_user_id, User.id.in_(
            select(SupportTeamMember.user_id).where(SupportTeamMember.team_id == team.id)
        )))
    return list(db.scalars(options.order_by(User.full_name, User.id)))


@router.get("/projects/{project_id}/delivery-owner-options")
def delivery_owner_options(
    project_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("implementation.task.assign")),
) -> list[dict[str, Any]]:
    return [{"id": user.id, "name": user.full_name} for user in _delivery_owner_options(db, actor, project_id)]


@router.put("/project-tasks/{task_id}/owner")
def change_task_owner(
    task_id: int,
    data: TaskOwnerWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("implementation.task.assign")),
) -> dict[str, Any]:
    task = _task(db, task_id, actor)
    project = require_project_access(db, actor, task.project_id)
    if project.status not in {"READY_FOR_EXECUTION", "IN_EXECUTION"}:
        raise ConflictError("TASK_ASSIGNMENT_CLOSED", "Task planning is unavailable at this stage.")
    options = _delivery_owner_options(db, actor, project.id)
    if data.owner_user_id not in {user.id for user in options}:
        raise NotFoundError("Engineer is outside the accepted delivery team.")
    result = db.connection().execute(update(ProjectTask).where(
        ProjectTask.id == task.id,
        ProjectTask.owner_user_id == data.expected_owner_user_id,
        ProjectTask.status.in_(["BACKLOG", "READY"]),
    ).values(owner_user_id=data.owner_user_id))
    if result.rowcount != 1:
        raise ConflictError("TASK_ASSIGNMENT_CONFLICT", "Refresh the task. Only unstarted work can be reassigned.")
    assignments = list(db.scalars(select(ProjectTaskAssignee).where(ProjectTaskAssignee.task_id == task.id)))
    previous = next((entry for entry in assignments if entry.user_id == data.expected_owner_user_id), None)
    current = next((entry for entry in assignments if entry.user_id == data.owner_user_id), None)
    for entry in assignments:
        entry.is_accountable = False
    if current is None:
        if previous is not None:
            previous.user_id = data.owner_user_id
            current = previous
        else:
            current = ProjectTaskAssignee(task_id=task.id, user_id=data.owner_user_id, planned_minutes=task.estimate_minutes)
            db.add(current)
    current.is_accountable = True
    _audit(db, actor, task, "project.task.owner_changed", {
        "previous_owner_user_id": data.expected_owner_user_id, "owner_user_id": data.owner_user_id,
    })
    _commit(db)
    db.refresh(task)
    return _values(task)


DELIVERY_SUBMITTED = "project.delivery.submitted"


def _latest_delivery_submission(db: Session, project_id: int) -> AuditLog | None:
    return db.scalar(select(AuditLog).where(
        AuditLog.entity_type == "company_project",
        AuditLog.entity_id == str(project_id),
        AuditLog.action == DELIVERY_SUBMITTED,
    ).order_by(AuditLog.id.desc()).limit(1))


@router.get("/projects/{project_id}/delivery-submission")
def get_delivery_submission(
    project_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.portfolio.view")),
) -> dict[str, Any] | None:
    project = require_project_access(db, actor, project_id)
    row = _latest_delivery_submission(db, project_id)
    if row is None:
        return None
    snapshot = json.loads(row.new_values_json or "{}")
    return {
        "submitted_at": row.created_at, "project_version": snapshot["project_version"],
        "summary": snapshot["summary"], "task_count": len(snapshot["task_ids"]),
        "evidence_count": len(snapshot["evidence_ids"]),
        "is_current": project.row_version == snapshot["project_version"],
    }


def _delivery_inputs(db: Session, project_id: int) -> tuple[list[tuple[int, str]], list[int]]:
    tasks = [(task_id, task_status) for task_id, task_status in db.execute(
        select(ProjectTask.id, ProjectTask.status).where(
            ProjectTask.project_id == project_id, ProjectTask.status != "CANCELLED",
        )
    ).all()]
    evidence = list(db.scalars(select(ProjectEvidence.id).where(
        ProjectEvidence.project_id == project_id, ProjectEvidence.visibility == "DEPARTMENT_SHARED",
    )))
    return tasks, evidence


def _in_delivery_department(db: Session, project_id: int, actor: User) -> bool:
    return bool(db.scalar(select(ProjectDepartment.id).where(
        ProjectDepartment.project_id == project_id, ProjectDepartment.department_id == actor.department_id,
        ProjectDepartment.role == "PRIMARY_IMPLEMENTATION",
    ).limit(1)))


@router.get("/projects/{project_id}/delivery-readiness")
def delivery_readiness(
    project_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("project.portfolio.view")),
) -> dict[str, Any]:
    project = require_project_access(db, actor, project_id)
    permissions = set(effective_permissions(db, actor).permissions)
    tasks, evidence = _delivery_inputs(db, project_id)
    return {
        "in_review": project.status == "DELIVERY_REVIEW",
        "has_tasks": bool(tasks),
        "open_tasks": sum(task_status != "DONE" for _, task_status in tasks),
        "has_shared_evidence": bool(evidence),
        "can_submit": "implementation.task.review" in permissions
        and _in_delivery_department(db, project_id, actor),
    }


@router.post("/projects/{project_id}/delivery-submission", status_code=201)
def submit_delivery(
    project_id: int,
    data: DeliverySubmissionWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("implementation.task.review")),
) -> dict[str, int]:
    require_project_access(db, actor, project_id)
    if not _in_delivery_department(db, project_id, actor):
        raise NotFoundError("Project is outside your delivery scope.")
    locked = db.connection().execute(update(CompanyProject).where(
        CompanyProject.id == project_id,
        CompanyProject.status == "DELIVERY_REVIEW",
        CompanyProject.row_version == data.expected_version,
    ).values(row_version=data.expected_version))
    if locked.rowcount != 1:
        raise ConflictError("DELIVERY_NOT_READY", "Refresh the project. Delivery must be ready for review.")
    previous = _latest_delivery_submission(db, project_id)
    if previous and json.loads(previous.new_values_json or "{}").get("project_version") == data.expected_version:
        raise ConflictError("DELIVERY_ALREADY_SUBMITTED", "This project version already has a delivery submission.")
    tasks, evidence_ids = _delivery_inputs(db, project_id)
    if not tasks or any(task_status != "DONE" for _, task_status in tasks):
        raise ConflictError("DELIVERY_TASKS_OPEN", "Complete all delivery tasks before submitting.")
    if not evidence_ids or len(data.summary.strip()) < 3:
        raise ConflictError("DELIVERY_EVIDENCE_REQUIRED", "Add shared project evidence and a delivery summary.")
    record = AuditLog(
        entity_type="company_project", entity_id=str(project_id), actor_user_id=actor.id,
        action=DELIVERY_SUBMITTED,
        new_values_json=json.dumps({
            "project_version": data.expected_version, "summary": data.summary.strip(),
            "task_ids": sorted(task_id for task_id, _ in tasks), "evidence_ids": sorted(evidence_ids),
        }),
    )
    db.add(record)
    _commit(db)
    db.refresh(record)
    return {"submission_id": record.id}


@router.get("/project-tasks/delivery-attention")
def delivery_attention(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("implementation.task.review")),
) -> list[dict[str, Any]]:
    if actor.department_id is None:
        return []
    delivery_projects = select(ProjectDepartment.project_id).where(
        ProjectDepartment.department_id == actor.department_id,
        ProjectDepartment.role == "PRIMARY_IMPLEMENTATION",
    )
    statement = (
        select(ProjectTask)
        .where(
            ProjectTask.project_id.in_(authorized_project_ids(db, actor)),
            ProjectTask.project_id.in_(delivery_projects),
            ProjectTask.status.in_(["BLOCKED", "REVIEW"]),
        )
        .order_by(ProjectTask.planned_end_date, ProjectTask.id)
        .limit(30)
    )
    return [_values(row) for row in db.scalars(statement)]


@router.post("/projects/{project_id}/tasks", status_code=status.HTTP_201_CREATED)
def create_planned_task(
    project_id: int,
    data: TaskCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("implementation.task.manage")),
) -> dict[str, Any]:
    return _values(_create_task(db, project_id, data, actor, "PLANNED"))


@router.post("/projects/{project_id}/unplanned-work", status_code=status.HTTP_201_CREATED)
def create_unplanned_task(
    project_id: int,
    data: UnplannedTaskCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("implementation.unplanned.create")),
) -> dict[str, Any]:
    return _values(_create_task(db, project_id, data, actor, "UNPLANNED"))


@router.post("/project-tasks/{task_id}/approve-unplanned")
def approve_unplanned(
    task_id: int,
    data: ApprovalWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("implementation.unplanned.approve")),
) -> dict[str, Any]:
    row = _task(db, task_id, actor)
    decision = data.decision.upper()
    if row.classification != "UNPLANNED" or row.approval_status != "PENDING":
        raise ConflictError("UNPLANNED_NOT_PENDING", "Only pending unplanned work can be decided.")
    if decision not in {"APPROVED", "REJECTED"}:
        raise ConflictError("INVALID_UNPLANNED_DECISION", "Select APPROVED or REJECTED.")
    row.approval_status = decision
    row.approved_by_user_id = actor.id
    row.approved_at = server_now()
    row.approval_notes = data.notes
    if decision == "REJECTED":
        row.status = "CANCELLED"
    _audit(
        db,
        actor,
        row,
        "project.task.unplanned_decided",
        {"decision": decision, "notes": data.notes},
    )
    _recalculate_project(db, row.project_id)
    _commit(db)
    db.refresh(row)
    return _values(row)


@router.post("/project-tasks/{task_id}/actions/{action}")
def task_action(
    task_id: int,
    action: str,
    data: TaskActionWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("implementation.task.execute")),
) -> dict[str, Any]:
    row = _task(db, task_id, actor, assigned_only=True)
    project = _execution_project(db, actor, row.project_id)
    target = action.upper().replace("-", "_")
    aliases = {
        "START": "IN_PROGRESS",
        "SUBMIT_REVIEW": "REVIEW",
        "COMPLETE": "DONE",
        "UNBLOCK": "READY",
        "REOPEN": "IN_PROGRESS",
        "CANCEL": "CANCELLED",
    }
    target = aliases.get(target, target)
    if (
        row.classification == "UNPLANNED"
        and row.approval_status != "APPROVED"
        and target not in {"CANCELLED", "BACKLOG"}
    ):
        raise ConflictError(
            "UNPLANNED_APPROVAL_REQUIRED", "Unplanned work must be approved before execution."
        )
    if target not in TRANSITIONS.get(row.status, set()):
        raise ConflictError(
            "INVALID_TASK_TRANSITION", f"Task cannot move from {row.status} to {target}."
        )
    if target == "DONE" and not data.summary:
        raise ConflictError("COMPLETION_SUMMARY_REQUIRED", "Completion requires a summary.")
    previous = row.status
    row.status = target
    if data.progress_percent is not None:
        row.progress_percent = data.progress_percent
    if target == "IN_PROGRESS" and row.progress_percent == 0:
        row.progress_percent = 1
    if target == "IN_PROGRESS" and project.status == "READY_FOR_EXECUTION":
        transition_project(
            db,
            project,
            actor,
            "IN_EXECUTION",
            source="TASK_EXECUTION",
        )
    if target == "DONE":
        row.progress_percent = 100
        row.completion_summary = data.summary
    _audit(
        db,
        actor,
        row,
        "project.task.transitioned",
        {"from": previous, "to": target, "summary": data.summary},
    )
    _recalculate_project(db, row.project_id)
    _commit(db)
    db.refresh(row)
    return _values(row)


@router.post("/project-tasks/{task_id}/work-logs", status_code=201)
def add_work_log(
    task_id: int,
    data: WorkLogWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("implementation.task.worklog")),
) -> dict[str, Any]:
    row = _task(db, task_id, actor, assigned_only=True)
    project = _execution_project(db, actor, row.project_id)
    if project.status == "READY_FOR_EXECUTION":
        transition_project(
            db, project, actor, "IN_EXECUTION", source="TASK_WORKLOG"
        )
    if row.status == "READY":
        row.status = "IN_PROGRESS"
        row.progress_percent = max(row.progress_percent, 1)
    duration = max(1, round((data.ended_at - data.started_at).total_seconds() / 60))
    log = ProjectWorkLog(
        task_id=row.id,
        user_id=actor.id,
        duration_minutes=duration,
        is_timer=False,
        **data.model_dump(),
    )
    db.add(log)
    _audit(db, actor, row, "project.task.work_logged", {"duration_minutes": duration})
    _commit(db)
    db.refresh(log)
    return _values(log)


@router.post("/project-tasks/{task_id}/timer/start", status_code=201)
def start_timer(
    task_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("implementation.task.worklog")),
) -> dict[str, Any]:
    row = _task(db, task_id, actor, assigned_only=True)
    project = _execution_project(db, actor, row.project_id)
    active = db.scalar(
        select(ProjectWorkLog.id).where(
            ProjectWorkLog.user_id == actor.id,
            ProjectWorkLog.is_timer == true(),
            ProjectWorkLog.ended_at.is_(None),
        )
    )
    if active:
        raise ConflictError(
            "ACTIVE_TIMER_EXISTS", "Stop the active project timer before starting another one."
        )
    if project.status == "READY_FOR_EXECUTION":
        transition_project(
            db, project, actor, "IN_EXECUTION", source="TASK_TIMER"
        )
    if row.status == "READY":
        row.status = "IN_PROGRESS"
        row.progress_percent = max(row.progress_percent, 1)
    log = ProjectWorkLog(task_id=row.id, user_id=actor.id, started_at=server_now(), is_timer=True)
    db.add(log)
    _audit(db, actor, row, "project.task.timer_started", {})
    _commit(db)
    db.refresh(log)
    return _values(log)


@router.post("/project-tasks/{task_id}/timer/stop")
def stop_timer(
    task_id: int,
    notes: str | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("implementation.task.worklog")),
) -> dict[str, Any]:
    row = _task(db, task_id, actor, assigned_only=True)
    log = db.scalar(
        select(ProjectWorkLog).where(
            ProjectWorkLog.task_id == task_id,
            ProjectWorkLog.user_id == actor.id,
            ProjectWorkLog.is_timer == true(),
            ProjectWorkLog.ended_at.is_(None),
        )
    )
    if not log:
        raise ConflictError("ACTIVE_TIMER_NOT_FOUND", "No active timer exists for this task.")
    ended_at = server_now()
    started_at = log.started_at
    if started_at.tzinfo is None and ended_at.tzinfo is not None:
        started_at = started_at.replace(tzinfo=ended_at.tzinfo)
    elif started_at.tzinfo is not None and ended_at.tzinfo is None:
        ended_at = ended_at.replace(tzinfo=started_at.tzinfo)
    log.ended_at = ended_at
    log.duration_minutes = max(1, round((ended_at - started_at).total_seconds() / 60))
    log.notes = notes
    _audit(db, actor, row, "project.task.timer_stopped", {"duration_minutes": log.duration_minutes})
    _commit(db)
    db.refresh(log)
    return _values(log)


@router.post("/project-tasks/{task_id}/blockers", status_code=201)
def add_blocker(
    task_id: int,
    data: BlockerWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("implementation.task.blocker.manage")),
) -> dict[str, Any]:
    row = _task(db, task_id, actor, assigned_only=True)
    _execution_project(db, actor, row.project_id)
    blocker = ProjectTaskBlocker(task_id=row.id, **data.model_dump())
    db.add(blocker)
    previous = row.status
    row.status = "BLOCKED"
    _audit(db, actor, row, "project.task.blocked", {"from": previous, **data.model_dump()})
    _commit(db)
    db.refresh(blocker)
    return _values(blocker)


@router.post("/project-task-blockers/{blocker_id}/resolve")
def resolve_blocker(
    blocker_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("implementation.task.blocker.manage")),
) -> dict[str, Any]:
    blocker = db.get(ProjectTaskBlocker, blocker_id)
    if not blocker:
        raise NotFoundError("Task blocker does not exist.")
    row = _task(db, blocker.task_id, actor, assigned_only=True)
    blocker.status = "RESOLVED"
    blocker.resolved_at = server_now()
    remaining = (
        db.scalar(
            select(func.count())
            .select_from(ProjectTaskBlocker)
            .where(
                ProjectTaskBlocker.task_id == row.id,
                ProjectTaskBlocker.status == "OPEN",
                ProjectTaskBlocker.id != blocker.id,
            )
        )
        or 0
    )
    if not remaining and row.status == "BLOCKED":
        row.status = "READY"
    _audit(db, actor, row, "project.task.blocker_resolved", {"blocker_id": blocker.id})
    _commit(db)
    return _values(blocker)


@router.post("/project-tasks/{task_id}/evidence", status_code=201)
def add_evidence(
    task_id: int,
    data: EvidenceWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("implementation.task.evidence.create")),
) -> dict[str, Any]:
    row = _task(db, task_id, actor, assigned_only=True)
    _execution_project(db, actor, row.project_id)
    evidence = ProjectEvidence(
        project_id=row.project_id, task_id=row.id, created_by_user_id=actor.id, **data.model_dump()
    )
    db.add(evidence)
    _audit(
        db,
        actor,
        row,
        "project.task.evidence_added",
        {"title": data.title, "visibility": data.visibility},
    )
    _commit(db)
    db.refresh(evidence)
    return _values(evidence)


@router.post("/project-tasks/{task_id}/reviews", status_code=201)
def review_task(
    task_id: int,
    data: ReviewWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("implementation.task.review")),
) -> dict[str, Any]:
    row = _task(db, task_id, actor)
    project = _execution_project(db, actor, row.project_id)
    decision = data.decision.upper()
    if row.status != "REVIEW" or decision not in {"APPROVED", "RETURNED"}:
        raise ConflictError("INVALID_TASK_REVIEW", "A task in REVIEW can be APPROVED or RETURNED.")
    review = ProjectTaskReview(
        task_id=row.id, reviewer_user_id=actor.id, decision=decision, notes=data.notes
    )
    db.add(review)
    row.status = "DONE" if decision == "APPROVED" else "IN_PROGRESS"
    if decision == "APPROVED":
        row.progress_percent = 100
        row.completion_summary = row.completion_summary or data.notes or "Approved in review."
        remaining = (
            db.scalar(
                select(func.count())
                .select_from(ProjectTask)
                .where(
                    ProjectTask.project_id == row.project_id,
                    ProjectTask.id != row.id,
                    ProjectTask.status.not_in(["DONE", "CANCELLED"]),
                    or_(
                        ProjectTask.classification == "PLANNED",
                        ProjectTask.approval_status == "APPROVED",
                    ),
                )
            )
            or 0
        )
        if not remaining and project.status == "IN_EXECUTION":
            transition_project(
                db,
                project,
                actor,
                "DELIVERY_REVIEW",
                source="TASK_EXECUTION",
            )
    _audit(db, actor, row, "project.task.reviewed", {"decision": decision, "notes": data.notes})
    _recalculate_project(db, row.project_id)
    _commit(db)
    db.refresh(review)
    return _values(review)
