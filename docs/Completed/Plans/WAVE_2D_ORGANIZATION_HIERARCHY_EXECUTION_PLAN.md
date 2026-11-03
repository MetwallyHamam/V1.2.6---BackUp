# Wave 2D — User and Department Hierarchy Foundation

Status: `DONE`

## Objective

Create a cycle-safe, effective-dated organizational hierarchy shared by User Setup, permissions, dashboards, and reporting.

## Workstreams

1. Add department parent relationships, effective dates, head/manager assignments, and active lifecycle rules.
2. Effective-date user reporting lines and department membership without destroying history.
3. Centralize ancestor/descendant, as-of-date, orphan, vacancy, and cycle validation services.
4. Add governed APIs for trees, paths, direct reports, descendants, vacancies, and historical views.
5. Enhance User/Department UI with parent/manager selectors, breadcrumbs, tree/list alternatives, filters, and history.
6. Reuse the hierarchy service in authorization and dashboards; prohibit dashboard-only hierarchy copies.
7. Audit old/new paths, dates, manager/head changes, and corrective actions.

## Tests and exit criteria

- Cycle, self-parent, missing parent, effective-date overlap, reparent, deactivate, orphan, and authorization tests.
- Large-tree pagination/lazy loading, historical as-of results, accessibility, and semantic deep links.
- All gates and populated rehearsals pass with current users/departments backfilled safely.
- Exit: one authoritative current/historical organization model exists.

Next wave after completion: Wave 3.

## Required completion checkpoint

When accepted, update this file and the master plan, record the standard `CODEX STOP POINT` (status, completed scope, last item, next item, continuation safety, and blockers), and stop before Wave 3 until explicitly continued.

## Implementation record — 2026-08-20

- Added revision `0096_org_hierarchy` with current department parent/head mirrors and append-only effective-dated department hierarchy, primary membership, and reporting-line history.
- Backfilled every existing department and every current user department/manager relationship on populated upgrades.
- Added centralized, bounded hierarchy services for as-of paths, descendants, cycles, missing parents, period overlap, membership transitions, and reporting-line transitions.
- Added governed tree, vacancy, department-history, user-history, membership, and reporting-line APIs with management permissions and audit evidence.
- Existing user creation/editing now writes the same temporal history, preventing legacy UI paths from bypassing the canonical organization model.
- User queries can resolve a department with descendants and an optional historical organization date through the centralized service.
- Added department parent/head/effective-date management, an as-of Department Structure view, vacancy presentation, semantic head links, and organization history on User Setup.
- Clean and populated SQLite migrations reached `0096`; populated fixtures preserved and produced one hierarchy, membership, and reporting record.
- Clean and populated SQL Server rehearsals reached `0096`, seeded, passed runtime compatibility, and preserved/backfilled the same fixture evidence. Both explicitly named disposable databases were removed.
- Verification: Ruff passed; Mypy passed across 122 files; 192 backend tests passed; frontend ESLint, 4 Vitest tests, TypeScript, and production build passed. The existing non-blocking vendor chunk advisory remains.

============================================================
CODEX STOP POINT
Status: DONE
Completed scope: Wave 2D — effective-dated user and department hierarchy foundation
Last completed item: Passed full gates plus clean/populated SQLite and SQL Server revision 0096 rehearsals; removed disposable databases
Next planned item: Wave 3 — service governance (versioned SLA, worklogs, feedback, outcomes)
Safe to continue from here: YES
Blocking decision(s): None
Database revision: 0096_org_hierarchy
============================================================
