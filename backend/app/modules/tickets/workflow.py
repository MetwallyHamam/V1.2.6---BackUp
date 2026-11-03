from __future__ import annotations

from typing import Any

from app.core.clock import server_now, server_timezone
from app.core.exceptions import AuthorizationError, ConflictError

TRANSITIONS: dict[str, frozenset[str]] = {
    "NEW": frozenset({"TRIAGED", "ASSIGNED", "IN_PROGRESS", "PENDING_INTERNAL", "CANCELLED"}),
    "TRIAGED": frozenset({"ASSIGNED", "IN_PROGRESS", "PENDING_INTERNAL", "CANCELLED"}),
    "ASSIGNED": frozenset(
        {"IN_PROGRESS", "PENDING_CLIENT", "PENDING_INTERNAL", "PENDING_VENDOR", "RESOLVED", "CANCELLED"}
    ),
    "IN_PROGRESS": frozenset(
        {"PENDING_CLIENT", "PENDING_INTERNAL", "PENDING_VENDOR", "RESOLVED", "CLOSED", "CANCELLED"}
    ),
    "PENDING_CLIENT": frozenset({"IN_PROGRESS", "RESOLVED", "CLOSED", "CANCELLED"}),
    "PENDING_INTERNAL": frozenset({"IN_PROGRESS", "RESOLVED", "CLOSED", "CANCELLED"}),
    "PENDING_VENDOR": frozenset({"IN_PROGRESS", "RESOLVED", "CLOSED", "CANCELLED"}),
    "RESOLVED": frozenset({"CLIENT_CONFIRMATION", "REOPENED", "CLOSED"}),
    "CLIENT_CONFIRMATION": frozenset({"CLOSED", "REOPENED"}),
    "CLOSED": frozenset({"REOPENED"}),
    "CANCELLED": frozenset({"REOPENED"}),
    "REOPENED": frozenset(
        {"ASSIGNED", "IN_PROGRESS", "PENDING_INTERNAL", "RESOLVED", "CLOSED", "CANCELLED"}
    ),
}

REASON_REQUIRED = frozenset({"PENDING_CLIENT", "PENDING_INTERNAL", "PENDING_VENDOR", "CANCELLED", "REOPENED"})

TARGET_PERMISSIONS = {
    "RESOLVED": "ticket.resolve",
    "CLOSED": "ticket.close",
    "REOPENED": "ticket.reopen",
    "CANCELLED": "ticket.cancel",
}


def authorize_transition_actor(
    *, target_code: str, assigned_user_id: int | None, actor_user_id: int, permissions: set[str]
) -> None:
    """Apply actor-specific workflow rules consistently across all transition entry points."""
    if (
        target_code == "RESOLVED"
        and assigned_user_id != actor_user_id
        and "ticket.resolve.any" not in permissions
    ):
        raise ConflictError(
            "TICKET_NOT_ASSIGNED_TO_ACTOR",
            "Only the assigned engineer can resolve this ticket. Assign it to yourself first.",
        )


def allowed_transition_codes(current_code: str, permissions: set[str]) -> frozenset[str]:
    return frozenset(
        target
        for target in TRANSITIONS.get(current_code, frozenset())
        if (
            "ticket.start.progress" in permissions
            if target == "IN_PROGRESS"
            else "ticket.change.status" in permissions
        )
        if TARGET_PERMISSIONS.get(target) in {None, *permissions}
    )


def validate_transition(
    current_code: str,
    target_code: str,
    data: Any,
    permissions: set[str],
    *,
    resolution_details_required_on_close: bool = False,
    require_root_cause: bool = True,
) -> None:
    transition_permission = (
        "ticket.start.progress" if target_code == "IN_PROGRESS" else "ticket.change.status"
    )
    if transition_permission not in permissions:
        raise AuthorizationError()
    if target_code not in TRANSITIONS.get(current_code, frozenset()):
        raise ConflictError(
            "TICKET_TRANSITION_NOT_ALLOWED",
            f"The ticket cannot move from {current_code} to {target_code}.",
        )
    required_permission = TARGET_PERMISSIONS.get(target_code)
    if required_permission and required_permission not in permissions:
        raise AuthorizationError()
    if target_code == "RESOLVED" and getattr(data, "close_after_resolve", False) and "ticket.close" not in permissions:
        raise AuthorizationError("You do not have permission to close tickets after resolution.")
    if target_code in REASON_REQUIRED and not data.reason:
        raise ConflictError("TRANSITION_REASON_REQUIRED", f"A reason is required when moving to {target_code}.")
    if target_code.startswith("PENDING_"):
        follow_up = getattr(data, "pending_follow_up_at", None)
        if not follow_up:
            raise ConflictError("PENDING_FOLLOW_UP_REQUIRED", "A pending follow-up deadline is required.")
        comparable = follow_up if follow_up.tzinfo else follow_up.replace(tzinfo=server_timezone())
        if comparable <= server_now():
            raise ConflictError("PENDING_FOLLOW_UP_INVALID", "The pending follow-up deadline must be in the future.")
    resolution_target = (
        target_code == "CLOSED"
        or (target_code == "RESOLVED" and getattr(data, "close_after_resolve", False))
        if resolution_details_required_on_close
        else target_code == "RESOLVED"
    )
    if resolution_target and not data.resolution_summary:
        raise ConflictError("RESOLUTION_REQUIRED", "A resolution summary is required.")
    if resolution_target and require_root_cause and not (
        getattr(data, "root_cause_ids", None) or getattr(data, "root_cause_summary", None)
    ):
        raise ConflictError("ROOT_CAUSE_REQUIRED", "Select at least one root cause.")
    if target_code == "CLIENT_CONFIRMATION" and not (
        getattr(data, "customer_confirmation_channel", None)
        and getattr(data, "customer_confirmation_contact", None)
    ):
        raise ConflictError(
            "CUSTOMER_CONFIRMATION_EVIDENCE_REQUIRED",
            "Record the customer confirmation channel and contact.",
        )
