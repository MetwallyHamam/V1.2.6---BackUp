from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.core.clock import server_now
from app.core.exceptions import AuthorizationError, ConflictError
from app.modules.tickets.service import pending_responsible_party
from app.modules.tickets.workflow import (
    TRANSITIONS,
    allowed_transition_codes,
    authorize_transition_actor,
    validate_transition,
)

ALL_TRANSITION_PERMISSIONS = {
    "ticket.change.status",
    "ticket.start.progress",
    "ticket.resolve",
    "ticket.close",
    "ticket.reopen",
    "ticket.cancel",
}


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        ("PENDING_CLIENT", "CUSTOMER"),
        ("PENDING_INTERNAL", "MILLENSYS"),
        ("PENDING_VENDOR", "MILLENSYS"),
    ],
)
def test_pending_responsible_party_defaults(status_code: str, expected: str) -> None:
    assert pending_responsible_party(status_code, None) == expected


def transition_data(target: str, **overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "to_status_code": target,
        "reason": "Required workflow reason",
        "resolution_summary": "Resolution completed successfully",
        "root_cause_summary": "Root cause was identified",
        "close_after_resolve": False,
        "pending_follow_up_at": server_now() + timedelta(days=1),
        "customer_confirmation_channel": "PHONE",
        "customer_confirmation_contact": "Verified requester",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_every_declared_transition_passes_central_validation() -> None:
    for current, targets in TRANSITIONS.items():
        for target in targets:
            validate_transition(
                current,
                target,
                transition_data(target),
                ALL_TRANSITION_PERMISSIONS,
            )


def test_allowed_transitions_apply_base_and_destination_permissions() -> None:
    assert allowed_transition_codes("ASSIGNED", set()) == frozenset()
    ordinary = allowed_transition_codes("ASSIGNED", {"ticket.change.status", "ticket.cancel"})
    assert "IN_PROGRESS" not in ordinary
    assert "CANCELLED" in ordinary
    assert "RESOLVED" not in ordinary
    starter = allowed_transition_codes("ASSIGNED", {"ticket.start.progress"})
    assert starter == frozenset({"IN_PROGRESS"})
    resolver = allowed_transition_codes(
        "ASSIGNED",
        {"ticket.change.status", "ticket.resolve", "ticket.cancel"},
    )
    assert "RESOLVED" in resolver


def test_start_progress_uses_its_dedicated_permission() -> None:
    with pytest.raises(AuthorizationError):
        validate_transition(
            "ASSIGNED",
            "IN_PROGRESS",
            transition_data("IN_PROGRESS"),
            {"ticket.change.status"},
        )
    validate_transition(
        "ASSIGNED",
        "IN_PROGRESS",
        transition_data("IN_PROGRESS"),
        {"ticket.start.progress"},
    )


def test_resolve_any_authorization_is_explicit_and_reusable() -> None:
    permissions = {"ticket.change.status", "ticket.resolve"}
    with pytest.raises(ConflictError) as error:
        authorize_transition_actor(
            target_code="RESOLVED",
            assigned_user_id=7,
            actor_user_id=9,
            permissions=permissions,
        )
    assert error.value.code == "TICKET_NOT_ASSIGNED_TO_ACTOR"
    authorize_transition_actor(
        target_code="RESOLVED",
        assigned_user_id=7,
        actor_user_id=9,
        permissions=permissions | {"ticket.resolve.any"},
    )


@pytest.mark.parametrize("current", ["NEW", "TRIAGED"])
def test_unowned_ticket_cannot_resolve_directly(current: str) -> None:
    with pytest.raises(ConflictError) as error:
        validate_transition(
            current,
            "RESOLVED",
            transition_data("RESOLVED"),
            ALL_TRANSITION_PERMISSIONS,
        )
    assert error.value.code == "TICKET_TRANSITION_NOT_ALLOWED"


@pytest.mark.parametrize(
    ("target", "permission"),
    [
        ("RESOLVED", "ticket.resolve"),
        ("CLOSED", "ticket.close"),
        ("REOPENED", "ticket.reopen"),
        ("CANCELLED", "ticket.cancel"),
    ],
)
def test_privileged_destinations_require_permission(target: str, permission: str) -> None:
    source = {
        "RESOLVED": "ASSIGNED",
        "CLOSED": "RESOLVED",
        "REOPENED": "CLOSED",
        "CANCELLED": "IN_PROGRESS",
    }[target]
    permissions = ALL_TRANSITION_PERMISSIONS - {permission}
    with pytest.raises(AuthorizationError):
        validate_transition(source, target, transition_data(target), permissions)


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("ASSIGNED", "PENDING_CLIENT"),
        ("IN_PROGRESS", "PENDING_INTERNAL"),
        ("IN_PROGRESS", "PENDING_VENDOR"),
        ("IN_PROGRESS", "CANCELLED"),
        ("CLOSED", "REOPENED"),
    ],
)
def test_pending_cancel_and_reopen_require_reason(source: str, target: str) -> None:
    with pytest.raises(ConflictError) as error:
        validate_transition(
            source,
            target,
            transition_data(target, reason=None),
            ALL_TRANSITION_PERMISSIONS,
        )
    assert error.value.code == "TRANSITION_REASON_REQUIRED"
