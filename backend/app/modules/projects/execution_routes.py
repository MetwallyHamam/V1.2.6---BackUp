import json
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.iam.models import AuditLog, User
from app.modules.projects.access import require_project_access, require_task_access
from app.modules.projects.execution_schemas import (
    ApprovalWrite,
    BlockerWrite,
    EvidenceWrite,
    ReviewWrite,
    TaskActionWrite,
    TaskCreate,
    UnplannedTaskCreate,
    WorkLogWrite,
)
from app.modules.projects.lifecycle import transition_project
from app.modules.projects.models import (
    CompanyProject,
    ProjectEvidence,
    ProjectPhase,
    ProjectTask,
    ProjectTaskAssignee,
    ProjectTaskBlocker,
    ProjectTaskDependency,
    ProjectTaskReview,
    ProjectWorkLog,
)

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
    require_project_access(db, actor, project_id)
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
    db.flush()
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
            ProjectTask.status.in_(["READY", "IN_PROGRESS", "BLOCKED", "REVIEW"]),
        )
        .order_by(ProjectTask.planned_end_date, ProjectTask.priority)
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
