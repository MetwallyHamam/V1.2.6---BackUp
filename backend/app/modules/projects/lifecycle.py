"""Canonical project lifecycle transitions and immutable history."""

from sqlalchemy.orm import Session

from app.core.clock import server_today
from app.core.exceptions import ConflictError
from app.modules.iam.models import User
from app.modules.notifications.models import Notification
from app.modules.projects.models import CompanyProject, ProjectStatusTransition

TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"AWAITING_IMPLEMENTATION_ACCEPTANCE", "CANCELLED"},
    "INTAKE": {"AWAITING_IMPLEMENTATION_ACCEPTANCE", "READY_FOR_EXECUTION", "CANCELLED"},
    "AWAITING_IMPLEMENTATION_ACCEPTANCE": {
        "INTAKE_PROPOSED",
        "INTAKE_RETURNED",
        "INTAKE_REJECTED",
        "READY_FOR_EXECUTION",
        "CANCELLED",
    },
    "INTAKE_PROPOSED": {
        "AWAITING_IMPLEMENTATION_ACCEPTANCE",
        "READY_FOR_EXECUTION",
        "INTAKE_RETURNED",
        "INTAKE_REJECTED",
        "CANCELLED",
    },
    "INTAKE_RETURNED": {"AWAITING_IMPLEMENTATION_ACCEPTANCE", "CANCELLED"},
    "INTAKE_REJECTED": {"AWAITING_IMPLEMENTATION_ACCEPTANCE", "CANCELLED"},
    "READY_FOR_EXECUTION": {"IN_EXECUTION", "ON_HOLD", "CANCELLED"},
    "PLANNING": {"READY_FOR_EXECUTION", "IN_EXECUTION", "ON_HOLD", "CANCELLED"},
    "IN_EXECUTION": {"DELIVERY_REVIEW", "ON_HOLD", "CANCELLED"},
    "ACTIVE": {"DELIVERY_REVIEW", "HANDOVER_PREPARATION", "ON_HOLD", "CANCELLED"},
    "DELIVERY_REVIEW": {"IN_EXECUTION", "HANDOVER_PREPARATION", "ON_HOLD", "CANCELLED"},
    "HANDOVER_PREPARATION": {"SUPPORT_REVIEW", "ON_HOLD", "CANCELLED"},
    "HANDOVER_PENDING": {"SUPPORT_REVIEW", "ON_HOLD", "CANCELLED"},
    "SUPPORT_REVIEW": {"HANDOVER_PREPARATION", "STABILIZATION", "ON_HOLD", "CANCELLED"},
    "READINESS_REVIEW": {"HANDOVER_PREPARATION", "STABILIZATION", "ON_HOLD", "CANCELLED"},
    "STABILIZATION": {"COMPLETED", "ON_HOLD", "CANCELLED"},
    "ON_HOLD": {
        "READY_FOR_EXECUTION",
        "IN_EXECUTION",
        "DELIVERY_REVIEW",
        "HANDOVER_PREPARATION",
        "SUPPORT_REVIEW",
        "STABILIZATION",
        "CANCELLED",
    },
}


def transition_project(
    db: Session,
    project: CompanyProject,
    actor: User,
    target: str,
    *,
    reason: str | None = None,
    source: str,
) -> ProjectStatusTransition:
    target = target.upper()
    previous = project.status
    if target == previous:
        raise ConflictError("PROJECT_STATUS_UNCHANGED", "Project is already in that status.")
    if target not in TRANSITIONS.get(previous, set()):
        raise ConflictError(
            "INVALID_PROJECT_TRANSITION",
            f"Project cannot move from {previous} to {target}.",
        )
    if target in {"INTAKE_RETURNED", "INTAKE_REJECTED", "ON_HOLD", "CANCELLED"} and not reason:
        raise ConflictError(
            "PROJECT_TRANSITION_REASON_REQUIRED",
            "A reason is required for this project transition.",
        )
    project.status = target
    if target == "IN_EXECUTION" and previous != "ON_HOLD" and project.actual_start_date is None:
        project.actual_start_date = server_today()
    if target == "COMPLETED" and project.actual_end_date is None:
        project.actual_end_date = server_today()
    project.row_version += 1
    history = ProjectStatusTransition(
        project_id=project.id,
        from_status=previous,
        to_status=target,
        reason=reason,
        source=source,
        actor_user_id=actor.id,
    )
    db.add(history)
    recipients = {
        recipient_id
        for recipient_id in (project.project_manager_user_id, project.intake_owner_user_id)
        if recipient_id and recipient_id != actor.id
    }
    severity = (
        "WARNING"
        if target in {"INTAKE_RETURNED", "INTAKE_REJECTED", "ON_HOLD", "CANCELLED"}
        else "INFO"
    )
    for recipient_id in recipients:
        db.add(
            Notification(
                recipient_user_id=recipient_id,
                notification_type="PROJECT_LIFECYCLE",
                severity=severity,
                title=f"{project.project_number} moved to {target.replace('_', ' ').title()}",
                message=reason or f"Project lifecycle advanced from {previous} to {target}.",
                deep_link=f"/projects/{project.id}/execution",
                deduplication_key=(
                    f"project-lifecycle:{project.id}:{project.row_version}:{recipient_id}"
                ),
            )
        )
    return history
