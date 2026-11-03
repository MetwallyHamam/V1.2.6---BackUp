# Unified entitlement decision model

P4 uses one side-effect-free decision engine for internal, portal, API, and email ticket submission. Every evaluation returns one accountable reason, an effective action, the proposed governed action, the effective feature-policy identity/version, evaluation time, and factual evidence.

## Stable reason precedence

1. `INACTIVE_CLIENT`
2. `MULTIPLE_MATCHING_CONTRACTS`
3. `INACTIVE_CONTRACT`
4. `EXPIRED_CONTRACT`
5. `PRODUCT_NOT_COVERED`
6. `SERVICE_NOT_COVERED`
7. `LIMIT_EXCEEDED`
8. `NO_MATCHING_SLA`

The first true condition is the primary reason. All observed facts remain in evidence, so the primary reason does not hide supporting context.

## Actions and feature modes

Actions are `ALLOW`, `WARN`, `REQUIRE_APPROVAL`, and `BLOCK`. Policies configure an `actions` object keyed by reason code. Invalid values use the documented safe default.

- `OFF`: calculate evidence but preserve the current workflow action.
- `SHADOW`: store the proposed governed action while preserving the current workflow action.
- `ENFORCED`: apply the proposed governed action.

No ticket or approval side effect belongs in the decision engine. P4.2 persists its immutable result and supplies idempotent approval requests.
