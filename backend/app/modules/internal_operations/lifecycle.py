
from app.core.clock import server_now
from app.core.exceptions import ConflictError
from app.modules.internal_operations.models import InternalOperation

TRANSITIONS: dict[str, set[str]] = {
    "PLANNED": {"PENDING_APPROVAL", "SCHEDULED", "CANCELLED"},
    "PENDING_APPROVAL": {"APPROVED", "CHANGE_REQUESTED", "REJECTED", "CANCELLED"},
    "CHANGE_REQUESTED": {"PENDING_APPROVAL", "CANCELLED"},
    "APPROVED": {"SCHEDULED", "IN_PROGRESS", "CANCELLED"},
    "SCHEDULED": {"CONFIRMED", "IN_PROGRESS", "CANCELLED"},
    "CONFIRMED": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"COMPLETED", "CANCELLED"},
}


def transition_operation(
    operation: InternalOperation,
    to_status: str,
    *,
    actor_user_id: int,
    expected_version: int | None = None,
) -> tuple[str, str]:
    if expected_version is not None and operation.version != expected_version:
        raise ConflictError("STALE_INTERNAL_OPERATION", "The operation changed; refresh and retry.")
    current = operation.status
    if to_status == current:
        return current, current
    if to_status not in TRANSITIONS.get(current, set()):
        raise ConflictError(
            "INVALID_INTERNAL_OPERATION_TRANSITION",
            f"Internal operation cannot move from {current} to {to_status}.",
        )
    now = server_now()
    operation.status = to_status
    operation.version += 1
    if to_status == "CONFIRMED":
        operation.confirmed_at = now
        operation.confirmed_by_user_id = actor_user_id
    elif to_status == "COMPLETED":
        operation.completed_at = now
        operation.completed_by_user_id = actor_user_id
    elif to_status == "CANCELLED":
        operation.cancelled_at = now
        operation.cancelled_by_user_id = actor_user_id
    return current, to_status
