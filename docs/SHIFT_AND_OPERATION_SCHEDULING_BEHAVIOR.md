# Shift and Operation Scheduling Behavior and Logic

This document describes the scheduling behavior implemented by the smart scheduling, coverage, and operations refactor. Sections 1–7 retain the original scheduling baseline; sections 8 onward describe the current smart workflow and supersede any older implementation-boundary note where the two differ.

## Current Quick Shift behavior (V2)

- Normal creation follows **Date From → Date To → Shift Type → Engineers → Create**. The inclusive Quick Shift range supports 1–31 days. The Shift Type supplies canonical start time, end time, and required headcount for every day; an end at or before the start crosses midnight.
- Manual assignment immediately lists active Shift participants who are available on every date in the range. Suggested assignment preselects range-available candidates for confirmation. Auto Balance ignores client-supplied employee IDs and chooses the lowest-load available candidates independently for each day.
- Candidate availability is loaded in one batched request and combines Shift Type eligibility, Shift participation, overlapping Shifts, Operations, and Visits, plus workload hints. Unavailable engineers remain visible for explanation but cannot be selected normally.
- The server independently revalidates participation, eligibility, permissions, and conflicts during creation. Disabling Shift Type eligibility enforcement never disables the active Shift-participant requirement.
- One Quick Shift request may create Draft Shifts for multiple engineers across the inclusive range transactionally and creates or reuses one dated coverage slot per day using the Shift Type headcount default. Any invalid date or assignment rolls back the whole request.
- Advanced overrides for time, location, team, on-call role, and overlap reason are collapsed by default. Override periods are revalidated by the server when saved.
- Existing Shifts retain their persisted actual timestamps when Shift Type defaults are later edited.
- Workload lists active Shift participants only. Its default table emphasizes Shift count/hours and total scheduled hours; Operation and Visit detail is expandable.
- Generator, Copy Week, Bulk Delete, and Paint Mode remain available under advanced planner tools. Agenda is the small-screen default and Quick Shift becomes full-screen on small screens.
- Calendar coverage details are actionable: unassigned or understaffed slots show **Assign Engineers**, which opens Quick Shift with the slot date, Shift Type, and team prefilled. Fully staffed slots and users without Shift creation permission do not receive the action.
- Database revision `0130_shift_type_defaults` adds the Shift Type defaults without rewriting historical Shift rows.

## 1. Shared scheduling principles

- Schedule intervals use half-open overlap logic: two records overlap when `existing.start < new.end` and `existing.end > new.start`. A record ending exactly when another starts is not an overlap.
- Persisted timestamps are UTC. Template application builds the time in the selected local timezone and then converts it to UTC.
- A schedule end must be later than its start. A template whose end time is less than or equal to its start time is treated as crossing midnight.
- Cancelled shifts do not block another shift. Completed and cancelled internal operations do not block template-generated operations; rejected operations also do not block explicit rescheduling.
- Generation and mutation actions are audited. Generated records retain their template reference or a note identifying their source.
- Bulk/template generation is transactional: an unhandled conflict rolls back the request. “Skip conflicts” behavior is described separately below.

## 2. Shift scheduling

### 2.1 Shift visibility and employee selection

Shift records are filtered on the server, not only in the user interface.

- `shift.view.all`: all shifts.
- `shift.view.department`: shifts belonging to users in the actor's department.
- `shift.view.team`: shifts belonging to users who share one of the actor's support teams.
- `shift.view.own` or the legacy `shift.view`: the actor's shifts only.
- The allowed scopes are additive.

The shift employee selector returns active employee accounts. Users with `shift.assign_employee` or `shift.manage` can select any active employee; otherwise an authorized user can select only themselves.

### 2.2 Creating and editing shifts

A shift contains an employee, shift type, start and end, status, optional team/on-call role/location/notes, and creator.

- Creation requires `shift.create` or `shift.manage`.
- Assigning somebody other than oneself additionally requires `shift.assign_employee` or `shift.manage`.
- Editing is allowed by `shift.edit.all`, `shift.edit.team`, or `shift.edit.own`, according to the target employee.
- Editing a `PUBLISHED` or `APPROVED` shift additionally requires `shift.edit.published`.
- An overlap with any non-cancelled shift for the same employee is rejected with `SHIFT_OVERLAP`, unless a non-empty overlap override reason is supplied. The reason is recorded in the audit log.
- Editing a published/approved shift for another employee sends that employee a notification.

### 2.3 Shift statuses

New manually created shifts use the submitted status; generated and duplicated shifts are always `DRAFT`.

- Setting `APPROVED` requires `shift.approve` (or `shift.manage`).
- Setting any other status through the status endpoint requires `shift.publish` (or `shift.manage`).
- Status changes are audited and notify the affected employee when another user performs the change.
- The endpoint currently authorizes status values but does not enforce a fixed shift-status transition graph.

### 2.4 Shift pattern templates

A shift pattern belongs to a department and one shift type. It stores start/end time, cross-midnight behavior, default weeks 1–4, default weekdays, week-start day, optional effective dates, and active state.

Three application modes are supported:

1. `MONTHLY_PATTERN`: derives dates from the chosen month, Weeks 1–4, weekdays, and week-start day. Dates outside the selected calendar month are discarded.
2. `SPECIFIC_DATES`: uses the exact distinct dates supplied by the caller.
3. `DATE_RANGE`: walks the inclusive From/To range and keeps dates whose weekday is selected. The range may not exceed 366 days.

For every selected date and employee, the system:

1. Validates that the pattern is active and every employee is active.
2. Enforces that all selected employees belong to the pattern's department.
3. Resolves the requested IANA timezone and constructs local start/end timestamps.
4. Adds one day to the end when the pattern crosses midnight.
5. Converts the timestamps to UTC.
6. Checks the employee's non-cancelled shifts for overlap.
7. Creates a `DRAFT` shift, or increments `skipped` when `skip_conflicts=true`.

If `skip_conflicts=false`, the first overlap rejects and rolls back the whole application. An empty calculated date selection is rejected with `SHIFT_DATE_SELECTION_EMPTY`.

Note: effective From/To dates are persisted template metadata. The current apply endpoint does not clamp generated dates to those fields, so callers/UI must keep selections inside that range.

### 2.5 Weekly roster templates

A roster template belongs to a department and contains ordered rows. Each row independently defines:

- Shift type.
- Weekday and Weeks 1–4.
- Start/end time and derived cross-midnight behavior.
- Work location and notes.
- One or more saved employee assignments.

Roster application accepts either a month or an inclusive date range. A request-level employee list overrides every row's saved assignees; otherwise each row uses its own assignments. All employees and shift types must be active, and employees must belong to the roster department.

The week number is recalculated for each calendar month using the template's week-start day. Days before the first configured week start have week number `0` and are not generated. Matching rows create `DRAFT` shifts. Conflicts are skipped or reject the transaction according to `skip_conflicts`.

As with shift patterns, roster effective From/To values are stored but are not currently enforced by the apply endpoint.

### 2.6 Duplicate week and bulk deletion

- Duplicate week copies visible, non-cancelled shifts from the seven-day source interval to the target week by applying the date/time offset. Copies are `DRAFT`; overlaps are skipped or reject the request.
- Bulk deletion first supports a preview by employee, intersecting date/time range, optional shift type, and optional status.
- `COMPLETED` shifts are protected from bulk deletion.
- Execution must provide the preview's expected deletable count. If the selection changed, `SHIFT_BULK_SELECTION_CHANGED` forces a new preview.
- Bulk and single deletion require `shift.delete` and create audit evidence. Single deletion currently has no completed-status protection.

### 2.7 Shift master-data protection

Shift types and patterns require `shift.manage`. Generated codes are stable identifiers. A shift type cannot be deleted while referenced by a shift, shift pattern, or roster row. Deleting a template does not delete shifts that were previously generated from it.

## 3. Internal operation scheduling

### 3.1 Access and permissions

The operation workspace uses granular permissions, including `internal_operation.view`, `create`, `schedule`, `assign`, `transition`, `comment`, `document.upload`, `document.download`, `template.manage`, and `type.manage`.

- Operations managers can access all operations and change scheduling/assignment fields.
- HR-scoped users are limited to operations assigned to employees in their department.
- Other users see operations they created or to which they are assigned.
- Non-managers may only start or complete an accessible assigned operation; managers control other lifecycle transitions and schedule/assignment edits.

### 3.2 Creating an operation

An operation requires a governed active type, title, valid start/end, at least one active employee assignee, status (`PLANNED` or `SCHEDULED`), and timezone. Client, template, planned window, location, and description are optional unless required by the operation type.

- Duplicate assignee IDs are removed.
- A selected template must be active and match the operation type.
- A type marked as requiring a client rejects creation without one.
- Creation is audited.
- General manual creation does not currently reject overlap with another internal operation; overlap enforcement occurs during template application and explicit rescheduling.

### 3.3 Explicit rescheduling

Rescheduling requires `internal_operation.schedule`, a reason, and the current operation version.

- A stale version is rejected with `STALE_INTERNAL_OPERATION`.
- `COMPLETED`, `CANCELLED`, and `REJECTED` operations cannot be rescheduled.
- Every current assignee is checked against other non-terminal internal operations.
- An overlap is rejected with `INTERNAL_OPERATION_SCHEDULE_CONFLICT`.
- A successful change updates start, end, timezone, increments the version, and records old/new values and reason in the audit log.

There is a permission named `internal_operation.override_conflict`, but the current reschedule endpoint does not use it to bypass this overlap check.

### 3.4 Operation lifecycle

Allowed transitions are:

| From | Allowed destinations |
| --- | --- |
| `PLANNED` | `PENDING_APPROVAL`, `SCHEDULED`, `CANCELLED` |
| `PENDING_APPROVAL` | `APPROVED`, `CHANGE_REQUESTED`, `REJECTED`, `CANCELLED` |
| `CHANGE_REQUESTED` | `PENDING_APPROVAL`, `CANCELLED` |
| `APPROVED` | `SCHEDULED`, `CANCELLED` |
| `SCHEDULED` | `CONFIRMED`, `IN_PROGRESS`, `CANCELLED` |
| `CONFIRMED` | `IN_PROGRESS`, `CANCELLED` |
| `IN_PROGRESS` | `COMPLETED`, `CANCELLED` |

Every real transition increments the optimistic-lock version. Confirmation, completion, and cancellation record their actor and UTC timestamp. A request to move to the current status is a no-op. The general update endpoint automatically passes through `IN_PROGRESS` when changing directly from `SCHEDULED` to `COMPLETED`.

### 3.5 Operation templates

An operation template stores a governed type, optional department, local start/end time, Weeks 1–4, weekdays, week-start day, optional effective dates, location, description, default status, and active state. Template application uses `Africa/Cairo` for local-to-UTC conversion.

Date selection modes are:

- `MONTHLY_PATTERN`: uses selected/default weeks and weekdays; dates outside the chosen month are discarded.
- `SPECIFIC_DATES`: uses the exact dates supplied.
- `DATE_RANGE`: walks the inclusive range and keeps dates matching both the selected weekday and that calendar month's selected week number. The maximum range is 366 days.

For each date, employees already assigned to an overlapping non-completed/non-cancelled operation are removed from that date's assignee list and counted as skipped. If at least one employee remains, one operation is created for that date with all remaining assignees. Therefore `created` counts operations, while `skipped` counts employee/date assignments.

Unlike shift generation, operation-template overlap handling always skips conflicting employees; there is no reject-on-first-conflict option.

Template effective From/To fields are persisted but are not currently applied as generation boundaries.

### 3.6 Outdoor / field visit behavior

`OUTDOOR_VISIT` is governed by the visit-entitlement subsystem and cannot bypass client allowance controls.

- A client is required.
- An active entitlement for that exact client must cover the operation date; the earliest-ending matching entitlement is used.
- Creation also creates one linked scheduled visit occurrence with a unique entitlement sequence number.
- One visit assignment is created for every operation assignee using the same time interval.
- The operation stores the linked visit occurrence ID, and the occurrence stores the internal operation ID and source type.
- Template application performs the same entitlement/linking logic for each generated date.

If any selected generated date lacks a covering entitlement, the template request fails transactionally rather than partially committing earlier dates.

## 4. Calendar and availability behavior

The unified Shifts Calendar can display shifts, internal operations, and field visits as separate sources, subject to each source's page/function permissions. Source filtering in the UI does not weaken backend visibility rules.

Operational availability means an employee has active shift coverage at the relevant time and is not occupied by an overlapping visit or internal operation. An active account alone is not treated as available. Planner workload metrics separately total scheduled shift minutes, assigned visit minutes, visit count, and visit assignments carrying conflict codes.

## 5. Important implementation boundaries

- Shift overlap checks compare shifts with shifts. Internal-operation checks compare internal operations with internal operations. Cross-source conflicts are primarily handled by visit-planner/availability workflows, not by every create endpoint.
- Template effective dates are descriptive/persisted in the current implementation and require endpoint enforcement if they must become hard boundaries.
- Internal operation template times are fixed to `Africa/Cairo`; shift templates and rosters accept a caller-supplied timezone.
- Deleting a template preserves generated schedules. Deleting a master type is blocked while schedules/templates reference it.
- All permissions and scoping must be enforced in backend queries and mutations; hiding a UI control is not an authorization mechanism.

## 6. Key error codes

| Code | Meaning |
| --- | --- |
| `SHIFT_OVERLAP` | A non-cancelled shift overlaps the proposed shift. |
| `INVALID_SHIFT_PERIOD` | Shift end is not later than shift start. |
| `SHIFT_DATE_SELECTION_EMPTY` | The chosen pattern criteria produce no dates. |
| `SHIFT_TEMPLATE_DEPARTMENT_MISMATCH` | At least one employee is outside the template department. |
| `SHIFT_ROSTER_ASSIGNEES_REQUIRED` | A roster row has no saved or request-level assignee. |
| `SHIFT_BULK_SELECTION_CHANGED` | Bulk-delete data changed after preview. |
| `STALE_INTERNAL_OPERATION` | The submitted operation version is no longer current. |
| `INTERNAL_OPERATION_SCHEDULE_CONFLICT` | An assignee has an overlapping active operation. |
| `INVALID_INTERNAL_OPERATION_TRANSITION` | The requested lifecycle edge is not allowed. |
| `INTERNAL_OPERATION_CLIENT_REQUIRED` | The selected operation type requires a client. |
| `VISIT_ENTITLEMENT_REQUIRED` | No active exact-client entitlement covers the operation date. |

## 7. Primary implementation references

- `backend/app/modules/shifts/routes.py` and `schemas.py`
- `backend/app/modules/internal_operations/routes.py`, `schemas.py`, and `lifecycle.py`
- `backend/app/modules/visits/routes.py`
- `frontend/src/pages/ShiftsPage.tsx`
- `frontend/src/pages/ShiftRosterTemplatesPanel.tsx`
- `frontend/src/pages/OperationTemplatesPanel.tsx`
- `frontend/src/pages/InternalOperationsPage.tsx`

## 8. Implemented UX architecture

The former collection of scheduling panels is presented as one permission-aware workspace:

```text
Overview -> health, risks, gaps, unassigned visits, and upcoming work
Planner  -> unified calendar, internal operations, and field visits
Workload -> cross-source employee load and availability
Setup    -> Shift Types, Eligibility, Rotations, Recipes, and Advanced templates
```

Desktop uses the calendar and setup editors. Small screens use stacked layouts and a floating quick-action menu for Quick Shift, Generate Shifts, Quick Operation, Generate Operations, and Schedule Client Visit. All hidden tabs and actions remain protected by backend permissions.

The Overview health score combines coverage, workload balance, conflict-free work, and operation timeliness. “Needs attention” contains coverage gaps, overloaded employees, draft/pending operations, and unassigned visits. Upcoming visits show the exact client, due date, assignee state, and current entitlement-ledger balance.

## 9. Participation and eligibility

Employees have two independent flags:

- `participates_in_shifts`
- `participates_in_operations`

Disabling either flag removes the employee from future candidate selection for that scheduling domain. It does not edit or delete historical records. Inactive/non-employee accounts are also excluded.

Each Shift Type can enable `enforce_employee_eligibility`. When disabled, every active shift participant is eligible. When enabled, an explicit active `employee_shift_eligibilities` row is required. The rule is enforced in manual creation, templates, rosters, week copy, generator preview/apply, availability, and rotations—not only in the UI. Eligibility and participation changes invalidate an earlier preview hash.

## 10. Coverage and headcount

A `shift_coverage_slot` is a dated requirement independent from an employee Shift. It records Shift Type, optional department/team scope, start/end, timezone, required headcount, source, and notes. Overlapping slots remain independent requirements.

Assigned headcount is calculated from distinct eligible employees whose non-cancelled Shift of the same type covers the whole slot. Status is derived as follows:

| Assigned | Required | Status |
| ---: | ---: | --- |
| 0 | any positive value | `UNASSIGNED` |
| less than required | required | `UNDERSTAFFED` |
| equal to required | required | `FULL` |
| greater than required | required | `OVERSTAFFED` |

Coverage percentage is capped at 100%, while overstaffing is retained as its own status. Daily summaries aggregate required/assigned positions and counts for all four states. The Coverage Gap Queue can preview and apply Auto Balance for a real slot.

## 11. Real-date recurrence and generation

The smart generator accepts ad-hoc rows or a saved Schedule Recipe. Supported recurrence modes are `ONCE`, `DAILY`, `WEEKLY`, `MONTHLY`, and `SPECIFIC_DATES`. It operates on real calendar dates, including leap years, 28/29-day February, 30/31-day months, partial weeks, fifth calendar occurrences, month/year boundaries, and cross-midnight slots. Recipe effective dates are enforced by the smart generator.

Generation is always two phase:

1. `preview` resolves dates, availability, workload, assignments, conflicts, headcount, and coverage without writing schedules.
2. `apply` recalculates the preview and requires the same SHA-256 preview hash. A changed participant, eligibility row, conflict, workload input, or request is rejected with `SCHEDULE_PREVIEW_CHANGED`.

Apply creates Draft shifts, their coverage slots, audit evidence, and a durable `schedule_generation_batch`. The batch stores the request range/mode, preview hash, required and created positions, conflicts, skipped/unassigned counts, actor, and timestamp. Created shifts link back to the batch.

## 12. Assignment strategies

- `MANUAL`: leaves positions open unless an existing covering assignment is retained.
- `FIXED`: considers only the selected employee IDs, in submitted order.
- `KEEP_EXISTING`: retains valid covering shifts, then fills remaining positions by workload.
- `AUTO_BALANCE`: orders available candidates by combined Shift, Operation, and Visit minutes, then assignment count and stable employee ID. Workload and proposed conflicts are recalculated after every generated assignment.
- `ROTATION`: walks the saved member order cyclically across generated slots. Inactive members, inactive users, non-participants, ineligible employees, and conflicting employees are skipped for that occurrence without being removed from the saved rotation. The cursor advances after the selected valid member.

Availability uses half-open interval overlap checks across non-cancelled shifts, non-terminal operations, and assigned visits. Sequential generation also checks proposed assignments, so one employee cannot be assigned to overlapping slots within the same preview.

## 13. Recipes, paint mode, and copy week

Schedule Recipes store multiple ordered coverage rows, timezone, scope, effective dates, default assignment strategy, and optional Rotation. Every row can define weekday, Shift Type, start/end, headcount, work location, notes, and strategy overrides.

Paint Mode stages selected dates locally, then uses the same preview/apply service; painting alone never persists a Shift. Copy Week supports next week, a selected week, or up to 12 target weeks with Keep Engineers, Rotate Engineers, or Auto Balance. Copy also uses a stale-safe preview hash and creates Draft shifts.

## 14. Internal operation generator

Operations use an equivalent preview/apply workflow with recurrence, candidate availability, fixed or Auto Balance assignment, and durable generation batches. Employees must participate in Operation Planning. Generated operations link to their batch.

`OUTDOOR_VISIT` preview performs an exact-client entitlement check for every occurrence before commit. Apply rejects the batch if a date is not covered, and covered operations create linked governed Visit occurrences and assignments. The Visit planner batches clients, assignments, users, and entitlement balances; `entitlement_remaining` is returned from the authoritative ledger without per-occurrence queries.

## 15. Added and modified API surface

| Method and route | Behavior |
| --- | --- |
| `GET /scheduling/availability` | Exact-time eligibility, cross-source conflicts, reason, and workload per employee. |
| `GET /scheduling/workload` | Shift/Operation/Visit counts and minutes plus conflict totals. |
| `GET/PUT /shift-eligibilities` | Read or replace Shift Type eligibility matrix values. |
| `GET/POST/PATCH/DELETE /shift-coverage-slots` | Manage dated headcount requirements. |
| `GET /shift-coverage-summary` | Aggregate daily coverage and status counts. |
| `GET/POST/PUT/DELETE /assignment-rotations` | Manage reusable ordered rotations. |
| `GET/POST/PUT/DELETE /schedule-recipes` | Manage effective-dated multi-row recipes. |
| `POST /shifts/generator/preview` | Calculate a non-persistent shift plan. |
| `POST /shifts/generator/apply` | Stale-safe creation of shifts, slots, and batch evidence. |
| `POST /shifts/duplicate-week/preview` | Preview multi-target copy and assignment changes. |
| `POST /shifts/duplicate-week` | Apply a matching Copy Week preview. |
| `POST /internal-operations/generator/preview` | Preview recurring operation generation and entitlement checks. |
| `POST /internal-operations/generator/apply` | Apply the matching operation preview transactionally. |
| `GET /visits/planner` | Includes batched assignments/client names and `entitlement_remaining`. |

Existing user create/update/read APIs now carry both participation flags; existing Shift Type APIs carry eligibility enforcement.

## 16. Database migrations

The migration chain is additive and ends at `0129_operation_generation`:

1. `0126_smart_schedule_foundation`: participation flags, Shift Type enforcement flag, and employee eligibility table.
2. `0127_shift_coverage_slots`: independent dated coverage/headcount requirements.
3. `0128_schedule_recipes_rotations`: rotations, members, recipes, recipe rows, generation batches, and Shift batch link.
4. `0129_operation_generation`: Internal Operation batch link and index.

Legacy shifts, templates, rosters, and operations remain intact. New participation fields default to enabled, and Shift Type enforcement defaults to disabled, preserving previous assignment behavior until administrators opt in.

## 17. Validation and test coverage

Automated coverage includes participation and eligibility enforcement, exact-time availability, headcount states, overlapping slots, sequential conflict avoidance, workload-aware selection, true cyclic rotations, stale previews, operation/visit entitlement boundaries, recurrence calendar edges, workspace navigation/permissions, and production compilation.

Validation completed on 2026-08-25:

- Backend Ruff: passed.
- Backend MyPy: passed for 141 source files.
- Full backend Pytest suite: 277 tests passed.
- Backend focused Shift tests: 22 passed.
- Backend focused Visit tests: 12 passed.
- Frontend ESLint and TypeScript: passed.
- Frontend Vitest: 7 files and 11 tests passed.
- Frontend production build: passed. Vite reports a non-blocking large vendor-chunk warning.
- Clean SQLite migration from base to `0129_operation_generation`: passed.

## 18. Known limitations

- The frontend uses a responsive full-screen/stacked planner rather than a separate native mobile bottom-sheet implementation.
- Paint Mode is date-chip based; it does not provide pointer-drag painting directly on calendar cells.
- Auto Balance is deterministic workload balancing, not an optimization solver for labor law, preferences, or forecast demand.
- Existing legacy pattern/roster apply endpoints retain their original behavior; Schedule Recipes and the smart generator are the effective-dated workflow.
- The production build’s shared vendor bundle remains above Vite’s advisory 500 kB threshold.
- Status transition behavior for legacy manual Shifts remains unchanged.

## 19. Manual acceptance cases

1. Disable Shift participation for an employee; confirm they disappear from generator candidates while historical Shifts remain.
2. Enable eligibility enforcement on a Shift Type; mark one employee ineligible and verify manual create, Auto Balance, Rotation, and Copy Week exclude them.
3. Create headcount-2 coverage and add zero, one, two, then three covering employees; verify `UNASSIGNED`, `UNDERSTAFFED`, `FULL`, and `OVERSTAFFED`.
4. Generate two overlapping Friday rows and confirm one employee is never selected for both.
5. Generate across February and a month boundary, including a cross-midnight Night Shift; confirm actual dates and UTC timestamps.
6. Preview a month with Auto Balance, change an employee conflict, then Apply; confirm stale-preview rejection.
7. Preview a Rotation containing an unavailable member; confirm the next valid member is chosen and the saved list is unchanged.
8. Copy one source week to several targets with each assignment mode; review conflicts before creating Drafts.
9. Paint several dates, modify the selection after Preview, and confirm Apply remains disabled until re-preview.
10. Generate an Outdoor Visit inside and outside an exact-client entitlement period; confirm covered creation and uncovered rejection.
11. Open Overview on desktop and mobile; verify health, gap actions, unassigned visits, visit allowance, and quick actions honor permissions.

## 20. Changed-file inventory

Core backend files:

- `backend/app/modules/iam/models.py`, `schemas.py`, `service.py`, `routes.py`
- `backend/app/modules/shifts/models.py`, `schemas.py`, `routes.py`, `generator.py`, `availability.py`, `workload.py`, `copy_week.py`
- `backend/app/modules/internal_operations/models.py`, `schemas.py`, `routes.py`, `generator.py`
- `backend/app/modules/visits/schemas.py`, `routes.py`
- `backend/app/db/compatibility.py`
- `backend/alembic/versions/0126_smart_scheduling_foundation.py`
- `backend/alembic/versions/0127_shift_coverage_slots.py`
- `backend/alembic/versions/0128_scheduling_recipes_rotations.py`
- `backend/alembic/versions/0129_operation_generation_batch.py`

Core frontend files:

- `frontend/src/pages/OperationsWorkspacePage.tsx`, `SchedulingOverviewPage.tsx`, `SchedulingWorkloadPage.tsx`, `SchedulingSetupPage.tsx`
- `frontend/src/pages/ShiftsPage.tsx`, `SmartScheduleBuilder.tsx`, `ShiftPaintMode.tsx`, `CoverageGapQueue.tsx`
- `frontend/src/pages/ShiftTypesPanel.tsx`, `AssignmentRotationsPanel.tsx`, `ScheduleRecipesPanel.tsx`
- `frontend/src/pages/InternalOperationsPage.tsx`, `SmartOperationBuilder.tsx`, `VisitOperationsPage.tsx`
- `frontend/src/pages/CreateUserPage.tsx`, `EditUserPage.tsx`
- `frontend/src/test/SchedulingWorkspace.test.tsx`, `ShiftDateSelection.test.ts`

Backend validation files include `backend/app/tests/test_shifts.py`, `test_operation_templates.py`, `test_visit_entitlements.py`, and `test_release_database_revision.py`.

## 21. Before and after

```text
BEFORE
Calendar + many configuration panels + Weeks 1–4 + manual assignment

AFTER
Overview -> see risks and gaps
Planner  -> Quick Create / Generate / Preview / Apply
Workload -> compare cross-source employee load
Setup    -> Shift Types / Eligibility / Rotations / Recipes / Advanced
```
