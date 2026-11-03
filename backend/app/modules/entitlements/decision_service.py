from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from app.modules.configuration.policy_service import EffectiveFeaturePolicy


class EntitlementReason(StrEnum):
    INACTIVE_CLIENT = "INACTIVE_CLIENT"
    INACTIVE_CONTRACT = "INACTIVE_CONTRACT"
    EXPIRED_CONTRACT = "EXPIRED_CONTRACT"
    PRODUCT_NOT_COVERED = "PRODUCT_NOT_COVERED"
    SERVICE_NOT_COVERED = "SERVICE_NOT_COVERED"
    NO_MATCHING_SLA = "NO_MATCHING_SLA"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
    MULTIPLE_MATCHING_CONTRACTS = "MULTIPLE_MATCHING_CONTRACTS"


class EntitlementAction(StrEnum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    BLOCK = "BLOCK"


# The first active condition is the accountable reason. This stable order prevents
# callers from obtaining different outcomes by changing evaluation order.
REASON_PRECEDENCE = (
    EntitlementReason.INACTIVE_CLIENT,
    EntitlementReason.MULTIPLE_MATCHING_CONTRACTS,
    EntitlementReason.INACTIVE_CONTRACT,
    EntitlementReason.EXPIRED_CONTRACT,
    EntitlementReason.PRODUCT_NOT_COVERED,
    EntitlementReason.SERVICE_NOT_COVERED,
    EntitlementReason.LIMIT_EXCEEDED,
    EntitlementReason.NO_MATCHING_SLA,
)

DEFAULT_ACTIONS: dict[EntitlementReason, EntitlementAction] = {
    EntitlementReason.INACTIVE_CLIENT: EntitlementAction.WARN,
    EntitlementReason.INACTIVE_CONTRACT: EntitlementAction.REQUIRE_APPROVAL,
    EntitlementReason.EXPIRED_CONTRACT: EntitlementAction.REQUIRE_APPROVAL,
    EntitlementReason.PRODUCT_NOT_COVERED: EntitlementAction.REQUIRE_APPROVAL,
    EntitlementReason.SERVICE_NOT_COVERED: EntitlementAction.REQUIRE_APPROVAL,
    EntitlementReason.NO_MATCHING_SLA: EntitlementAction.WARN,
    EntitlementReason.LIMIT_EXCEEDED: EntitlementAction.REQUIRE_APPROVAL,
    EntitlementReason.MULTIPLE_MATCHING_CONTRACTS: EntitlementAction.BLOCK,
}


@dataclass(frozen=True)
class EntitlementDecision:
    feature_mode: str
    reason_code: str | None
    effective_action: str
    proposed_action: str
    policy_id: int | None
    policy_version: int
    policy_scope: str
    evaluated_at: datetime
    evidence: dict[str, Any]


def _configured_actions(configuration: dict[str, Any]) -> dict[EntitlementReason, EntitlementAction]:
    raw_actions = configuration.get("actions", {})
    if not isinstance(raw_actions, dict):
        return DEFAULT_ACTIONS
    resolved = dict(DEFAULT_ACTIONS)
    for reason in EntitlementReason:
        value = raw_actions.get(reason.value)
        if isinstance(value, str):
            try:
                resolved[reason] = EntitlementAction(value.upper())
            except ValueError:
                continue
    return resolved


def evaluate_entitlement_decision(
    policy: EffectiveFeaturePolicy,
    *,
    conditions: dict[EntitlementReason, bool],
    evidence: dict[str, Any],
    legacy_action: EntitlementAction = EntitlementAction.ALLOW,
) -> EntitlementDecision:
    """Return one deterministic, traceable decision without performing side effects."""
    reason = next((item for item in REASON_PRECEDENCE if conditions.get(item, False)), None)
    proposed = (
        _configured_actions(policy.configuration)[reason]
        if reason is not None
        else EntitlementAction.ALLOW
    )
    effective = proposed if policy.mode == "ENFORCED" else legacy_action
    return EntitlementDecision(
        feature_mode=policy.mode,
        reason_code=reason.value if reason else None,
        effective_action=effective.value,
        proposed_action=proposed.value,
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        policy_scope=policy.source_scope_key,
        evaluated_at=policy.evaluated_at,
        evidence=dict(evidence),
    )
