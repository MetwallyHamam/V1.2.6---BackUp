# Wave 3B — Effective-Dated Coverage and Renewal Lifecycle Execution Plan

Status: DONE

## Objective

Represent coverage and renewals as effective-dated history so operational eligibility remains correct through amendments, retirement, and contract succession.

## Prerequisites

- Wave 3A is complete.
- Coverage precedence, renewal stages, partial-renewal behavior, and ownership are approved.
- Existing contract/client/service links have been profiled for duplicates and invalid periods.

## Workstreams

1. Add effective-from/effective-until coverage records; retire records instead of deleting history.
2. Validate non-overlap or explicitly permitted overlap by coverage category.
3. Support multiple renewal opportunities, successor contracts, line-level outcomes, and lost/partial renewals.
4. Preserve SLA/version continuity while ensuring new work selects the correct effective policy.
5. Add renewal workflow, tasks, reminders, aging, evidence, and authorized transitions.
6. Expose timelines and explain-why eligibility details to operational users.

## Data, API, and migration

- Add temporal constraints, stable identifiers, retirement metadata, and audit records.
- Convert legacy links into dated records using conservative defaults and an exception report.
- Make opportunity creation and successor linking idempotent.
- Prevent date edits that would invalidate existing ticket/visit snapshots without an explicit governed correction.

## Verification

- Boundary-test start/end instants, gaps, permitted overlaps, timezone behavior, and amendments.
- Test full, partial, lost, reopened, and duplicate renewal paths.
- Reconcile current eligibility and historical snapshots before and after migration.
- Verify permissions and notification retry behavior.

## Exit criteria

- Coverage can be explained for any relevant date.
- Retirement and amendments retain historical evidence.
- Renewal opportunities and successor links are not duplicated.
- Automated tests, migration reconciliation, permissions, and runbook pass.

## Next wave

Wave 3C — Optional Contract Finance.

## Required completion checkpoint

When accepted, write the standard `CODEX STOP POINT` and stop before Wave 3C until explicitly continued.

## Implementation evidence

- Database revision `0099_coverage_renewals` adds effective-dated coverage revisions, retirement evidence, renewal opportunities, line outcomes, and renewal tasks.
- Eligibility resolution uses the revision effective on the requested date and includes the revision in its explanation.
- Coverage amendments are optimistic-concurrency protected, close the prior period, and retain history; removal retires rather than deletes.
- Contract date edits that would exclude a coverage revision are rejected.
- Renewal creation is idempotent and supports full, partial, and lost outcomes plus validated successor contracts and SLA continuity.
- Manager-facing contract renewal UI and the coverage history/amendment APIs are available.
- Operational procedures are recorded in `docs/COVERAGE_RENEWAL_OPERATIONS.md`.

## Verification evidence

- Ruff and Mypy pass across 126 backend source files.
- 202 backend tests and 4 frontend tests pass.
- Frontend ESLint, TypeScript, and production build pass.
- Clean SQLite migration and clean/populated SQL Server migrations reach `0099_coverage_renewals`.

============================================================
CODEX STOP POINT
Status: DONE
Completed scope: Wave 3B — Effective-Dated Coverage and Renewal Lifecycle
Last completed item: Passed application gates and clean/populated SQL Server revision 0099 rehearsals
Next planned item: Wave 3C — Optional Contract Finance
Safe to continue from here: YES
Blocking decision(s): None
Database revision: 0099_coverage_renewals
============================================================
