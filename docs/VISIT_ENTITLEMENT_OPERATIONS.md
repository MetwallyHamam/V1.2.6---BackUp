# Visit Entitlement Operations

Create each entitlement for the exact client or sub-client receiving service, within its linked contract period. Never treat a parent and descendants as one allowance pool. Overlapping active records for the same contract, exact client, visit type, service, and period are rejected.

The opening grant and all later changes are immutable ledger entries. Use adjustments with signed quantities and a reason; use explicit carry-forward within the approved cap, reservations/releases only when policy authorizes them, expiry for unused allowance, and exact compensating reversals for mistakes. Never edit or delete posted ledger evidence.

Generate occurrences from the active entitlement. Repeating generation is safe and returns the same generated identities. Scheduling alone does not consume allowance. Completion requires outcome evidence and consumes exactly one unit; an authorized reopen restores that unit with a compensating entry. Overage must be explicit.

Daily controls:

- Review unplanned and overdue counts by exact client and entitlement period.
- Investigate open generation exceptions before scheduling.
- Reconcile remaining quantity to the sum of ledger entries.
- Confirm completed occurrence count equals completion/overage entries net of reversals.
- Retain cancelled, superseded, completed, and reopened history.

Before release, validate clean and populated migration to `0101_visit_entitlements`, permissions, full application gates, and independent ledger reconciliation. Recover by restoring the pre-upgrade backup; never truncate visit evidence.
