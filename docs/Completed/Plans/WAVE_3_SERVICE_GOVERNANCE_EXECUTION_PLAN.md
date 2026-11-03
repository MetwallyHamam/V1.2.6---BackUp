# Wave 3 — Service Governance Execution Plan

Status: DONE

## Objective

Make SLA measurement, worklogs, feedback, and resolution outcomes consistent, auditable, and historically reproducible.

## Prerequisites

- Waves 2B–2D are complete and accepted.
- SLA precedence, pause rules, and reporting definitions are confirmed from the master plan.
- Existing ticket timing and worklog data has been profiled before migrations are written.

## Workstreams

1. Add versioned SLA policies/templates with effective dates and deterministic specificity rules.
2. Snapshot the selected SLA/version and calculated targets onto each ticket; never rewrite history when a policy changes.
3. Add trustworthy worklogs linked to tickets/tasks, with ownership, duration, notes, approval state, and overlap validation.
4. Add structured customer feedback isolated from internal scoring, with eligibility and minimum-sample rules.
5. Add controlled root-cause, outcome, and permanent-fix fields and reference data.
6. Provide authorized administration, operational views, audit events, and evidence links.

## Data, API, and migration

- Add immutable policy versions and ticket-level SLA snapshots.
- Add worklog approval/audit fields and safe constraints without destroying legacy rows.
- Backfill normalized outcomes only where mapping is unambiguous; report unresolved values.
- Expose read/write endpoints with authorization, concurrency protection, validation, and pagination.
- Recalculate only explicitly selected open tickets; record who initiated every recalculation.

## Verification

- Unit-test SLA selection, calendars, pauses, deadlines, worklog totals, and feedback eligibility.
- Integration-test create/edit/version/approve flows and unauthorized access.
- Migration-test representative legacy, empty, duplicate, and ambiguous datasets.
- Reconcile dashboard/report totals against independent database queries.

## Exit criteria

- Historical tickets retain their original SLA evidence.
- Worklog totals are explainable and cannot be silently duplicated or overlapped.
- Feedback and internal assessment remain distinct.
- Root cause/outcome reporting uses controlled, auditable values.
- Automated tests, migration rehearsal, permission review, and operator documentation pass.

## Next wave

Wave 3A — Ticket Exception Approvals and Manager Finance.

## Required completion checkpoint

When implementation is accepted, update this file and the master plan, then record: status, completed scope, last completed item, next planned item, continuation safety, and blocking decisions under a `CODEX STOP POINT` heading. Do not start Wave 3A without explicit continuation.

## Completed implementation

- Added revision `0097_service_governance` with immutable SLA policy/target versions and durable policy/context snapshots on newly created ticket SLA clocks.
- Added explicit SLA publication/history APIs; policy changes no longer rewrite published evidence.
- Added ticket/task-linked worklogs with owner-only draft editing, calculated duration, optimistic version checks, overlap rejection, submission, manager approval/rejection, and audit events.
- Added customer-only feedback source and eligibility evidence plus a manager metric endpoint enforcing the approved 10-request minimum sample; individual engineer composite scoring remains disabled.
- Added controlled resolution outcomes and permanent-fix status/evidence to the ticket workflow and operator UI.
- Added focused regression coverage for SLA immutability, worklog overlap/approval, feedback isolation/minimum samples, and database compatibility.

## Verification record

- Ruff passed; MyPy passed across 122 source files; the full backend suite passed.
- Frontend ESLint, four Vitest tests, TypeScript, and production build passed. The existing vendor-chunk advisory remains non-blocking.
- Clean SQLite and SQL Server migrations passed through `0097_service_governance`.
- A populated SQL Server database was seeded at `0096_org_hierarchy` and upgraded successfully to `0097_service_governance`.

============================================================
CODEX STOP POINT
Status: DONE
Completed scope: Wave 3 — immutable SLA governance, trustworthy worklogs, isolated feedback evidence, and structured resolution outcomes
Last completed item: Passed full static/test/build gates and clean/populated SQLite and SQL Server revision 0097 rehearsals
Next planned item: Wave 3A — Ticket Exception Approvals and Manager Finance
Safe to continue from here: YES
Blocking decision(s): None
Database revision: 0097_service_governance
============================================================
