from datetime import UTC, datetime

from app.modules.configuration.policy_service import EffectiveFeaturePolicy
from app.modules.entitlements.decision_service import (
    EntitlementAction,
    EntitlementReason,
    evaluate_entitlement_decision,
)


def policy(mode: str, configuration: dict[str, object] | None = None) -> EffectiveFeaturePolicy:
    return EffectiveFeaturePolicy(
        feature_key="entitlement_approvals",
        mode=mode,
        configuration=configuration or {},
        source_scope="CONTRACT",
        source_scope_key="CONTRACT:42",
        policy_id=7,
        policy_version=3,
        evaluated_at=datetime(2026, 8, 12, tzinfo=UTC),
    )


def test_enforced_policy_uses_stable_reason_precedence_and_configured_action() -> None:
    result = evaluate_entitlement_decision(
        policy("ENFORCED", {"actions": {"INACTIVE_CLIENT": "BLOCK"}}),
        conditions={
            EntitlementReason.NO_MATCHING_SLA: True,
            EntitlementReason.INACTIVE_CLIENT: True,
        },
        evidence={"client_id": 9, "contract_id": 42},
    )
    assert result.reason_code == "INACTIVE_CLIENT"
    assert result.effective_action == "BLOCK"
    assert result.proposed_action == "BLOCK"
    assert result.policy_version == 3
    assert result.evidence == {"client_id": 9, "contract_id": 42}


def test_shadow_records_proposed_action_but_preserves_legacy_behavior() -> None:
    result = evaluate_entitlement_decision(
        policy("SHADOW"),
        conditions={EntitlementReason.EXPIRED_CONTRACT: True},
        evidence={"contract_end_date": "2026-07-31"},
        legacy_action=EntitlementAction.WARN,
    )
    assert result.reason_code == "EXPIRED_CONTRACT"
    assert result.proposed_action == "REQUIRE_APPROVAL"
    assert result.effective_action == "WARN"


def test_no_exception_is_allowed_in_every_mode() -> None:
    result = evaluate_entitlement_decision(
        policy("ENFORCED"), conditions={}, evidence={"contract_id": 42}
    )
    assert result.reason_code is None
    assert result.effective_action == "ALLOW"
    assert result.proposed_action == "ALLOW"


def test_invalid_configured_action_falls_back_to_safe_default() -> None:
    result = evaluate_entitlement_decision(
        policy("ENFORCED", {"actions": {"LIMIT_EXCEEDED": "SKIP"}}),
        conditions={EntitlementReason.LIMIT_EXCEEDED: True},
        evidence={},
    )
    assert result.effective_action == "REQUIRE_APPROVAL"
