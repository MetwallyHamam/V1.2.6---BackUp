# Wave 5 — Weekly Shift and Visit Planner Execution Plan

Status: DONE

## Objective

Provide department-aware weekly planning for engineer shifts and visits, with reliable conflict detection and usable desktop/mobile workflows.

## Prerequisites

- Wave 4 is complete.
- Department hierarchy, shift patterns, holidays/calendars, visit occurrences, and assignment rules are stable.
- Conflict severity and override authority are approved.

## Workstreams

1. Build weekly department/team/engineer shift planning from reusable patterns.
2. Build visit planning from due occurrences and entitlement context.
3. Detect overlaps, absence/calendar conflicts, coverage gaps, capacity pressure, and duplicate assignments.
4. Support bulk assignment, copy-forward, controlled overrides, filters, and evidence drill-through.
5. Provide accessible keyboard/form alternatives to drag-and-drop and responsive mobile views.
6. Add workload summaries, unscheduled queues, notifications, and audit history.

## Data and API

- Store planned times with explicit timezone semantics and stable assignment identifiers.
- Enforce critical conflicts server-side; never rely only on the browser.
- Use optimistic concurrency and return actionable conflict details.
- Keep planning changes separate from actual completion and time worked.

## Verification

- Test daylight-saving/timezone boundaries, overlaps, concurrent edits, overrides, copy-forward, and reassignment.
- Test planner permissions by department and role.
- Run accessibility, keyboard, responsive-layout, and realistic-volume performance checks.
- Reconcile planner workload totals to assignments and occurrences.

## Exit criteria

- Planners can explain every warning and override.
- Critical conflicts cannot be bypassed without authorized evidence.
- Desktop, keyboard, and mobile workflows are usable.
- Automated, accessibility, performance, and permission tests pass.

## Next wave

Wave 6 — Bulk Coverage, Imports, and Visit Completion/Documents.

## Required completion checkpoint

When accepted, record the standard `CODEX STOP POINT` and stop before Wave 6 until explicitly continued.

## Implementation and verification evidence

- Revision `0102_visit_planner` adds stable, optimistic-concurrency-controlled occurrence assignments with explicit timezone, conflict codes, and override evidence.
- Server-side planning checks occurrence windows, other visits, published/approved shift coverage, leave shifts, and department eligibility.
- Multi-engineer assignment, reassignment history, deduplicated notifications, workload totals, unassigned queues, and period/department filters are available.
- The existing weekly shift calendar/copy-forward workflow and the responsive visit planner share one page; all scheduling actions have keyboard-accessible forms.
- Ruff and Mypy pass across 130 files; 209 backend tests and 4 frontend tests pass; lint, types, production build, clean SQLite, and clean/populated SQL Server upgrades pass.

============================================================
CODEX STOP POINT
Status: DONE
Completed scope: Wave 5 — Weekly Shift and Visit Planner
Last completed item: Passed full gates and clean/populated SQL Server revision 0102 rehearsals
Next planned item: Wave 6 — Bulk Coverage, Imports, and Visit Completion/Documents
Safe to continue from here: YES
Blocking decision(s): None
Database revision: 0102_visit_planner
============================================================
