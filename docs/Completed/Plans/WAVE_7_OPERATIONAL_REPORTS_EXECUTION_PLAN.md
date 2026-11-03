# Wave 7 — Operational Reports Execution Plan

Status: DONE — release checkpoint verified 2026-08-20

## Objective

Deliver reconciled client, department, shift, and visit reporting with transparent formulas and evidence drill-through.

## Prerequisites

- Wave 6 is complete.
- Metric dictionary, date semantics, timezone, organizational scope, and export permissions are approved.
- Source transactions and historical snapshots are sufficiently stable.

## Workstreams

1. Build client service/coverage, SLA, work, visit, entitlement, and outcome reports.
2. Build department capacity/activity, shift coverage, exception, and visit execution reports.
3. Standardize filter bars, saved views where approved, pagination, sorting, exports, and evidence links.
4. Publish formula definitions, exclusions, freshness timestamps, and data-quality warnings.
5. Apply row/field-level authorization consistently to screen, export, and drill-through.
6. Add query indexes/caching only after profiling and define invalidation/freshness behavior.

## Data and API

- Use a canonical reporting/query layer so cards, tables, exports, and detail views agree.
- Preserve exact filter context in links and exports.
- Treat unknown/missing data explicitly; do not silently coerce it to zero.
- Version material formula changes and record deployment dates.

## Verification

- Reconcile every headline metric to independent source queries and curated fixtures.
- Test date boundaries, hierarchy scope, empty data, late corrections, and permission filtering.
- Compare UI, export, and evidence totals for identical filters.
- Run realistic-volume performance and accessibility tests.

## Exit criteria

- Every published metric has an owner, formula, scope, freshness rule, and evidence path.
- UI and exported results reconcile for the same user and filters.
- Unauthorized data cannot leak through totals, filters, exports, or links.
- Reconciliation sign-off, tests, documentation, and runbook pass.

## Next wave

Wave 7A — Dashboard Inventory and Consolidation.

## Required completion checkpoint

When accepted, record the standard `CODEX STOP POINT` and stop before Wave 7A until explicitly continued.

## Completion record

- Added one canonical live query layer for client ticket/visit/entitlement and department shift/visit/exception measures, matching CSV exports, definitions, freshness, UTC date semantics, and evidence destinations.
- Restricted client rows through ticket visibility and non-executive department rows to the manager's department.
- Added the responsive operational reports workspace and reconciliation fixtures.
- Passed all release gates and clean/populated migrations at database head `0103_visit_completion`.
