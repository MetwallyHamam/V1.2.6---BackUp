import pytest

from app.core.exceptions import ConflictError
from app.modules.service_management.lifecycle import (
    CHANGE_TRANSITIONS,
    MAJOR_INCIDENT_TRANSITIONS,
    PROBLEM_TRANSITIONS,
    validate_transition,
)


@pytest.mark.parametrize(
    ("matrix", "current", "target"),
    [
        (PROBLEM_TRANSITIONS, "NEW", "INVESTIGATING"),
        (MAJOR_INCIDENT_TRANSITIONS, "DECLARED", "RESPONSE_ACTIVE"),
        (CHANGE_TRANSITIONS, "IMPLEMENTING", "VALIDATION"),
    ],
)
def test_valid_lifecycle_transitions(matrix: dict[str, set[str]], current: str, target: str) -> None:
    validate_transition(matrix, current, target)


def test_invalid_lifecycle_transition_is_rejected() -> None:
    with pytest.raises(ConflictError, match="Cannot transition"):
        validate_transition(CHANGE_TRANSITIONS, "SUBMITTED", "COMPLETED")


@pytest.mark.parametrize("target", ["CANCELLED", "REJECTED", "FAILED", "ROLLED_BACK"])
def test_exception_transitions_require_reason(target: str) -> None:
    source = {"CANCELLED": "SUBMITTED", "REJECTED": "AWAITING_APPROVAL", "FAILED": "IMPLEMENTING", "ROLLED_BACK": "IMPLEMENTING"}[target]
    with pytest.raises(ConflictError, match="reason"):
        validate_transition(CHANGE_TRANSITIONS, source, target)
    validate_transition(CHANGE_TRANSITIONS, source, target, "Documented operational reason")
