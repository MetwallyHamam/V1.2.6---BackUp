# Wave 3A — Ticket Exception Approvals and Manager Finance Execution Plan

Status: DONE

## Objective

Introduce explicit approval for operational exceptions and an auditable manager-facing view of ticket commercial decisions.

## Prerequisites

- Wave 3 is complete.
- Exception categories, approver roles, expiry behavior, and chargeability policy are approved.
- Finance terminology distinguishes contracted, billable, invoiced, collected, waived, and disputed amounts.

## Workstreams

1. Build exception requests for inactive clients, invalid coverage, and other approved categories.
2. Require reason, evidence, requester, authorized approver, decision, timestamps, and optional expiry.
3. Make approval consumption idempotent and scoped to the exact requested operation.
4. Add chargeable-ticket decisions, estimates/quotes, approval state, and adjustment reasons.
5. Add a manager finance ledger and drill-through while preventing unsupported revenue claims.
6. Add notifications, aging views, escalation, audit history, and least-privilege authorization.

## Data, API, and migration

- Use append-oriented decision/audit records; do not overwrite prior decisions.
- Store money in fixed precision with currency and explicit status dates.
- Backfill legacy commercial data as unverified unless authoritative evidence exists.
- Enforce optimistic concurrency and server-side permission checks on all decisions.

## Verification

- Test request, approve, reject, expire, revoke, retry, and concurrent-decision paths.
- Test separation of duties and attempts to reuse an approval outside its scope.
- Reconcile ledger states and amounts; verify that only confirmed collections appear as collected.
- Test notification retries and duplicate delivery protection.

## Exit criteria

- Every exception is attributable, bounded, reviewable, and non-reusable.
- Commercial states and amounts are unambiguous and reconcile to source records.
- Unauthorized users cannot approve or view restricted finance data.
- Migration, automated tests, audit review, and operational runbook pass.

## Next wave

Wave 3B — Effective-Dated Coverage and Renewal Lifecycle.

## Required completion checkpoint

When accepted, write the standard `CODEX STOP POINT` with status, scope, last item, next item, continuation safety, and blockers. Stop before Wave 3B pending explicit continuation.

## Completed implementation

- Extended exception approvals with exact operation scopes, optimistic versions, one-time consumption, revocation, overdue expiry, approval-group enforcement, separation of duties, requester notifications, deduplicated reminders, and append-only history/audit evidence.
- Added fixed-precision append-only ticket commercial decisions and finance ledger entries for billable, invoice, collection, waiver, dispute, and adjustment evidence.
- Added idempotency and reversal validation; only confirmed ledger entries affect totals and confirmed collections require an external payment reference.
- Added a permission-protected Manager Finance UI with ticket drill-through, sequenced decisions, ledger entry capture, per-currency reconciliation, and explicit outstanding balances.
- Added finance permissions to the Support Manager profile and documented the operating rules in `docs/MANAGER_FINANCE_OPERATIONS.md`.
- Added regression coverage for scope mismatch/reuse, stale decisions, confirmed versus pending collections, required payment references, and idempotent overdue expiry.

## Verification record

- Ruff and MyPy passed across 126 source files; the complete backend suite passed.
- Frontend ESLint, four Vitest tests, TypeScript, and production build passed; the existing vendor chunk advisory remains non-blocking.
- Clean SQLite and clean/populated SQL Server migrations passed through `0098_exception_finance`.

============================================================
CODEX STOP POINT
Status: DONE
Completed scope: Wave 3A — scoped exception approvals and manager ticket finance
Last completed item: Passed complete gates and clean/populated cross-database revision 0098 rehearsals
Next planned item: Wave 3B — Effective-Dated Coverage and Renewal Lifecycle
Safe to continue from here: YES
Blocking decision(s): None
Database revision: 0098_exception_finance
============================================================
