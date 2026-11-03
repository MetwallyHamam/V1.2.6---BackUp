# Wave 4 — Visit Entitlement Ledger and Occurrence Generation Execution Plan

Status: DONE

## Objective

Turn contract visit allowances into a precise, auditable entitlement ledger and generate due occurrences without double counting.

## Prerequisites

- Wave 3C is complete or formally skipped under an approved decision.
- Allowance periods, carry-forward, amendment, cancellation, overage, and consumption policies are approved.
- Coverage is effective-dated and target client/sub-client scope is unambiguous.

## Workstreams

1. Materialize allowance grants by contract, client/sub-client, service, and entitlement period.
2. Represent adjustments, reservations where approved, consumption, release, expiry, and overage as ledger entries.
3. Generate visit occurrences deterministically from contract rules and calendars.
4. Make generation/re-generation idempotent and retain superseded occurrence history.
5. Explain available, scheduled, completed/consumed, expired, adjusted, and remaining quantities.
6. Add exception queues for inconsistent legacy allowances or impossible schedules.

## Data, API, and migration

- Use append-oriented ledger entries with source references and unique idempotency keys.
- Scheduling alone must not consume entitlement unless the approved policy explicitly says so.
- Completion consumes entitlement exactly once; cancellation/reversal produces compensating entries.
- Backfill only from authoritative contract data and reconcile every opening balance.

## Verification

- Property-test ledger conservation and occurrence-generation idempotency.
- Test amendments, partial periods, cancellations, reversals, carry-forward, overage, and concurrency.
- Reconcile per-contract and per-client balances to independent queries.
- Test permissions, audit trails, and migration exception reports.

## Exit criteria

- Every remaining allowance is derivable from immutable ledger evidence.
- Occurrences can be regenerated without duplicates.
- Completion and reversal affect entitlement exactly once.
- Tests, reconciliation, migration rehearsal, and operator runbook pass.

## Next wave

Wave 5 — Weekly Shift Planner and Visit Planner.

## Required completion checkpoint

When accepted, record the standard `CODEX STOP POINT` and stop before Wave 5 until explicitly continued.

## Implementation and verification evidence

- Revision `0101_visit_entitlements` adds exact-client entitlement records, visit types, append-only quantity ledgers, deterministic occurrences, and generation exceptions.
- Opening grants, adjustments, carry-forward, reservation/release, expiry, completion/overage, and reversals are independently evidenced with idempotency keys.
- Quarterly/monthly/semiannual/annual/custom generation is deterministic and regeneration returns existing occurrence identities.
- Scheduling does not consume allowance; completion is concurrency guarded and consumes once; reopening writes a compensating entry.
- Contract workspace controls show entitled, planned, completed, remaining, unplanned, and overdue values for each exact client.
- Ruff and Mypy pass across 130 files; 208 backend tests and 4 frontend tests pass; lint, types, production build, clean SQLite, and clean/populated SQL Server upgrades pass.

============================================================
CODEX STOP POINT
Status: DONE
Completed scope: Wave 4 — Visit Entitlement Ledger and Occurrence Generation
Last completed item: Passed full gates and clean/populated SQL Server revision 0101 rehearsals
Next planned item: Wave 5 — Weekly Shift Planner and Visit Planner
Safe to continue from here: YES
Blocking decision(s): None
Database revision: 0101_visit_entitlements
============================================================
