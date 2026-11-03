# Wave 7B — Dashboard Evidence Links and Department Structure Execution Plan

Status: DONE — release checkpoint verified 2026-08-20

## Objective

Make dashboard values provable through exact evidence links and add a Department Structure view based on the canonical hierarchy.

## Prerequisites

- Wave 7A is complete.
- Canonical dashboard metrics, destination reports, URL filter contracts, and hierarchy APIs are stable.

## Workstreams

1. Map every actionable card/chart segment to an exact authorized evidence destination.
2. Preserve date range, department, client, engineer, status, metric version, and other relevant filter context.
3. Add resilient back-navigation and understandable handling for stale or unauthorized targets.
4. Add a Department Structure tab reusing Wave 2D hierarchy data, rules, and permissions.
5. Show effective-dated membership/leadership context without creating a second hierarchy model.
6. Instrument broken mappings and evidence-link usage without collecting unnecessary personal data.

## Data and API

- Define and test a versioned filter/deep-link contract.
- Resolve evidence server-side under the destination user's authorization.
- Represent unavailable or excluded evidence explicitly rather than changing headline totals.

## Verification

- Contract-test each metric-to-destination mapping and filter round trip.
- Reconcile source values with destination result sets.
- Test unauthorized, deleted, reclassified, historical, and empty evidence states.
- Test hierarchy dates, cycles, multi-membership presentation, accessibility, and mobile layout.

## Exit criteria

- Every retained actionable dashboard value has a tested evidence path or documented non-actionable rationale.
- Links preserve metric context and never bypass authorization.
- Department Structure uses the canonical hierarchy and matches effective-dated results.

## Next wave

Wave 7C — Department Achievements.

## Required completion checkpoint

When accepted, record the standard `CODEX STOP POINT` and stop before Wave 7C until explicitly continued.

## Completion record

- Added stable filter-preserving evidence contracts for operational metrics and server-side authorization for report, export, and achievement evidence.
- Added an as-of department structure view using existing effective-dated memberships, with deduplicated headcount and explicit vacant-head warnings.
- Reused the canonical organization model; no parallel hierarchy persistence was introduced.
