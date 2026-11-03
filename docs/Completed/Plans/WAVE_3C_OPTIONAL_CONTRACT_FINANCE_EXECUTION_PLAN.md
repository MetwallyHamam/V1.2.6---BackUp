# Wave 3C — Optional Contract Finance Execution Plan

Status: DONE

## Objective

Add optional contract finance capabilities without making finance data mandatory for operational contract use.

## Prerequisites

- Wave 3B is complete.
- Currency, tax, rounding, invoice, receipt, allocation, correction, and access policies are approved.
- Authoritative sources and integration boundaries are documented.

## Workstreams

1. Add optional finance profiles, currencies, tax treatment, billing schedules, and payment terms.
2. Add invoices/credit adjustments, receipts/payments, and explicit allocations.
3. Keep draft, issued, overdue, disputed, cancelled, paid, and collected meanings separate.
4. Provide authorized ledgers, aging, reconciliation, evidence, and exports.
5. Add correction/reversal workflows that preserve history rather than editing posted records.

## Data, API, and migration

- Use fixed-precision amounts, currency on every monetary record, and deterministic rounding.
- Permit all finance fields to remain blank without affecting ordinary contract workflows.
- Treat imported legacy balances as unverified until reconciled.
- Require idempotency keys for financial posting/import endpoints and immutable audit events for state changes.

## Verification

- Test tax/rounding, partial payments, overpayments, reversals, allocation changes, and multi-currency rejection rules.
- Test operational contracts with no finance profile.
- Reconcile invoices, allocations, outstanding balances, and confirmed collections.
- Perform role, export, audit, migration, and recovery tests.

## Exit criteria

- Operational users can manage contracts with finance entirely blank.
- Posted finance history is reversible but not silently rewritten.
- Collected income is based only on confirmed allocated receipts.
- Automated tests, reconciliation, permission review, and runbook pass.

## Next wave

Wave 4 — Visit Entitlement Ledger and Occurrence Generation.

## Required completion checkpoint

When accepted, write the standard `CODEX STOP POINT` and stop before Wave 4 until explicitly continued.

## Implementation and verification evidence

- Revision `0100_contract_finance` adds optional finance profiles, billing schedules, invoices/credits, receipts/reversals, and explicit allocations using fixed precision.
- Posting endpoints are idempotent, currency constrained, audited, and preserve corrections as new evidence.
- Only confirmed, reconciled receipts are eligible for allocation and collected totals; imported balances remain unverified.
- Permission-gated contract finance APIs and a Financials workspace tab expose summary and ledger data without affecting contracts that have no profile.
- Ruff and Mypy pass across 126 files; 205 backend tests and 4 frontend tests pass; frontend lint, types, and production build pass.
- Clean SQLite and clean/populated SQL Server migrations reach `0100_contract_finance`.

============================================================
CODEX STOP POINT
Status: DONE
Completed scope: Wave 3C — Optional Contract Finance
Last completed item: Passed full gates and clean/populated SQL Server revision 0100 rehearsals
Next planned item: Wave 4 — Visit Entitlement Ledger and Occurrence Generation
Safe to continue from here: YES
Blocking decision(s): None
Database revision: 0100_contract_finance
============================================================
