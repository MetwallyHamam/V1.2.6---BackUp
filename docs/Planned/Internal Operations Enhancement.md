# Internal Operations Enhancement — Implementation Plan

Status: `IN PROGRESS — PHASE 1 IMPLEMENTED; SQL SERVER REHEARSAL PENDING`  
Prepared: 2026-08-23  
Risk: High — workflow, entitlement, approval, calendar, and reporting change

Implementation started: 2026-08-23  
Approved defaults: Section 4 accepted through the instruction to start work. Unsuccessful and no-show outcomes do not consume visit allowance unless a later explicit policy changes this rule.

### Implementation checkpoint — 2026-08-23

Completed in Phase 0/1:

- Moved the work from Backlog to Planned and accepted the documented default decisions.
- Added migration `0120_internal_ops_lifecycle` after `0119_client_profile_permission`.
- Added backward-compatible operation-type governance fields for duration, client requirement, visit behavior, completion evidence, approval policy, and approver profile.
- Linked templates to governed operation types and added duration, default status, recurrence JSON, and required-fields JSON.
- Added operation template/visit links, planning windows, timezone, optimistic version, and lifecycle audit timestamps/actors.
- Added a centralized transition service and a strict versioned transition endpoint.
- Added concurrency-safe rescheduling with overlap rejection and audit evidence.
- Preserved the legacy scheduled-to-completed UI call by executing the governed intermediate transition internally.
- Added lifecycle, invalid-transition, stale-version, and rescheduling regression coverage.

Verification completed:

- Clean disposable SQLite migration through `0120` passed as an automated cross-database compatibility check only; production remains SQL Server.
- Ruff passed.
- MyPy passed over 133 source files.
- Full backend suite passed: 243 tests.
- Frontend ESLint and 4 frontend tests passed.
- TypeScript and production Vite build passed.

Pending Phase 1 gate:

- Run clean and populated migration rehearsals against an isolated SQL Server rehearsal database. Never use the live production database.

### Unified workspace and permission checkpoint — 2026-08-24

- Removed the standalone Shift Planner navigation entry and redirected legacy `/shifts` links into the unified Operations Calendar.
- Preserved authorized shift scheduling inside the merged workspace.
- Separated calendar source loading for shifts, internal operations, and visits so one module no longer requires another module's permission.
- Added granular Internal Operations workspace, calendar, creation, assignment, scheduling, transition, comment, evidence, template, type, and conflict permissions in migration `0122_operations_permissions`.
- Preserved existing profile access through migration-time inheritance from the legacy view/manage permissions.
- Added contract-workspace Financials deep-link state and retained an always-visible Financials tab with explicit permission feedback.
- Clean SQLite migration, backend quality gates and 257 tests, plus all frontend gates passed.
- Isolated SQL Server clean and populated rehearsals remain required before production deployment.

## 1. Outcome

Turn Internal Operations into one unified, template-driven planning and scheduling page. Users should mainly select an operation type or template, client, planning window/date, and engineers. The system should apply defaults, availability checks, contractual visit rules, approvals, and reporting automatically.

All capabilities in this plan must be available from one page using permission-aware tabs. Users must not need to navigate between separate Internal Operations, Visit Operations, template, approval, and reporting pages.

Reuse existing shift and visit scheduling services where their rules match. Keep internal-operation business rules separate from contractual visit-entitlement rules.

## 2. Existing baseline — do not rebuild

The codebase already provides:

- Governed operation types and reusable monthly operation templates.
- Internal-operation CRUD, assignees, comments, documents, filters, and basic statuses.
- Visit entitlements, immutable allowance ledgers, and recurring monthly/quarterly/semiannual/annual planning windows.
- Visit scheduling/rescheduling, shift and leave conflict detection, completion evidence, cancellation, and reopening.
- Completion-only visit consumption and separate `CONSUMPTION`/`OVERAGE` ledger entries.
- A backend feed combining shifts and visit assignments.
- One workspace for Internal Operations, Visit Operations, and Operational Reports.

Extend these locations instead of creating parallel modules:

- `backend/app/modules/internal_operations/`
- `backend/app/modules/visits/`
- `backend/app/modules/shifts/`
- `frontend/src/pages/InternalOperationsPage.tsx`
- `frontend/src/pages/OperationTemplatesPanel.tsx`
- `frontend/src/pages/VisitPlannerPanel.tsx`
- Alembic revisions `0106`, `0107`, and `0108`

## 3. Remaining gaps

1. Internal Operations uses cards and a large create dialog instead of a Day/Week/Month calendar.
2. Templates do not define visit-consumption behavior, required fields, approval policy, or rich recurrence rules.
3. There is no single governed flow linking a visit-consuming operation to a `ClientVisitOccurrence`.
4. Over-allowance visits have no pre-scheduling approval request or configurable approver workflow.
5. Operation statuses are limited to `SCHEDULED`, `IN_PROGRESS`, `COMPLETED`, and `CANCELLED`.
6. Saved views, approval filters, full calendar filters, and a complete combined manager calendar are missing.
7. Reports do not reconcile contractual visits, approved additional visits, and total visits.

## 4. Decisions required before moving to Planned

1. A visit-consuming operation must create or link to `ClientVisitOccurrence`; it must never decrement allowance directly.
2. Allowance is consumed only after governed successful completion with required evidence.
3. An approved visit beyond allowance is classified as `APPROVED_OVERAGE`; it does not increase the contractual grant.
4. Approvers are resolved from configurable profiles by operation type and optionally department, never from a hardcoded user ID.
5. Approval is required when remaining allowance is zero, or when the operation-type policy is `ALWAYS`.
6. Decide whether unsuccessful/no-show outcomes consume allowance; default recommendation is no consumption.
7. The combined calendar may show shifts as read-only availability context; operations and visits remain editable through their governed APIs.

## 5. Target workflows

### Standard operation

1. Select a template/type and populate defaults.
2. Select dates and engineers.
3. Preview shift coverage, leave, operation overlap, and visit overlap.
4. Create as `PLANNED` or `SCHEDULED`.
5. Confirm, start, complete, or cancel through controlled transitions.

### Contractual or additional visit

1. Select client and visit-consuming template.
2. Resolve the active entitlement and show entitled, planned, scheduled, completed, consumed, reserved, remaining, and visit history.
3. If allowance remains, create/link the governed visit occurrence.
4. If exhausted, create an approval request and set `PENDING_APPROVAL`.
5. Approver chooses Approve, Reject, or Request Change with a reason.
6. Approval permits scheduling but does not change the contract allowance.
7. Successful completion creates exactly one `CONSUMPTION` or `APPROVED_OVERAGE` ledger entry using an idempotency key.

## 6. Data model changes

Create a new Alembic revision after the migration head at implementation time. Do not modify revisions `0106`–`0108`.

### Operation types

Add:

```text
default_duration_minutes       INTEGER NULL
requires_client                BOOLEAN NOT NULL DEFAULT false
visit_behavior                 NONE | OPTIONAL | REQUIRED
completion_evidence_required   BOOLEAN NOT NULL DEFAULT false
approval_policy                NEVER | WHEN_ALLOWANCE_EXHAUSTED | ALWAYS
approver_profile_id            BIGINT NULL
```

### Operation templates

Add `operation_type_id`, `default_duration_minutes`, `default_status`, `recurrence_rule_json`, and `required_fields_json`. Backfill the foreign key from the existing operation-type code and retain compatibility during the first release.

### Internal operations

Add:

```text
template_id
visit_occurrence_id (nullable unique FK)
approval_request_id
planned_window_start / planned_window_end
timezone
version (optimistic concurrency)
confirmed_at/by, completed_at/by, cancelled_at/by
```

### Approval records

Create `operation_approval_requests` and append-only `operation_approval_actions`. Store immutable decision context: client, contract, entitlement, allowance/used/reserved/remaining, date, engineers, justification, requester, routed profile, status, and version.

Actions are `SUBMITTED`, `APPROVED`, `REJECTED`, `CHANGE_REQUESTED`, `RESUBMITTED`, or `CANCELLED`. Never overwrite approval history.

### Saved views

Reuse the existing saved-view framework if it supports module-scoped filter JSON. Otherwise add owner, name, shared/private flag, filters, calendar mode, and version.

## 7. Controlled statuses

Use one backend transition service for:

```text
PLANNED -> PENDING_APPROVAL | SCHEDULED | CANCELLED
PENDING_APPROVAL -> APPROVED | CHANGE_REQUESTED | REJECTED | CANCELLED
CHANGE_REQUESTED -> PENDING_APPROVAL | CANCELLED
APPROVED -> SCHEDULED | CANCELLED
SCHEDULED -> CONFIRMED | IN_PROGRESS | CANCELLED
CONFIRMED -> IN_PROGRESS | CANCELLED
IN_PROGRESS -> COMPLETED | CANCELLED
```

`COMPLETED`, `CANCELLED`, and `REJECTED` are terminal. Completed contractual visits may reopen only through the existing ledger-reversal workflow.

## 8. API plan

```text
GET    /internal-operations/calendar
POST   /internal-operations/preview
PATCH  /internal-operations/{id}/schedule
POST   /internal-operations/{id}/transition
GET    /internal-operations/{id}/visit-summary
GET    /internal-operations/approvals
POST   /internal-operations/{id}/approval/submit
POST   /internal-operation-approvals/{id}/decision
CRUD   /internal-operation-saved-views
```

The preview returns validation, entitlement summary, approval requirement, scheduling conflicts, and proposed status without writing data.

Use one event DTO for operations, visits, and read-only shifts: stable ID, source type, title, start/end/timezone, status/color, client, assignees, approval state, edit permissions, and version.

## 9. Unified one-page frontend

Use one route and page container:

```text
/internal-operations
InternalOperationsWorkspacePage
```

The page contains these tabs:

1. **Calendar** — default tab with Day/Week/Month/agenda views for operations and visits, plus optional read-only shifts.
2. **Operations** — searchable table/list for all operations, bulk actions, status management, and evidence access.
3. **Visit Planning** — contractual allowance summary, recurring/quarterly windows, unscheduled visits, scheduling, completion, and history.
4. **Approvals** — pending, approved, rejected, and change-requested additional-visit requests with decision actions.
5. **Templates & Types** — operation-type masters, reusable templates, recurrence defaults, visit behavior, and approval policy.
6. **Reports** — operational totals, contractual versus additional visits, engineer/client analysis, drill-down evidence, and exports.

Tabs are permission-aware. Hide a tab when the user cannot perform any action in it, while backend endpoints continue enforcing authorization. The active tab must be represented by a query parameter such as `/internal-operations?tab=approvals`, allowing bookmarks and links without creating separate pages.

The page header contains shared date, client, engineer, and department context. Each tab may add local filters, but shared context should remain when switching tabs. Persist the last selected tab and safe filters locally for convenience; saved business views remain server-side.

Build reusable tab components:

- `InternalOperationsWorkspacePage`: page header, tab routing, permissions, shared context, and lazy tab loading.
- `OperationsCalendarTab`: Day/Week/Month and responsive agenda modes.
- `OperationsListTab`: searchable table/list, bulk actions, and operation details.
- `VisitPlanningTab`: allowance, recurrence windows, scheduling, completion, and visit history.
- `OperationApprovalsTab`: decision queue and audit history.
- `OperationConfigurationTab`: operation types and templates in one administration tab.
- `OperationalReportsTab`: charts, evidence tables, and exports.
- `OperationsCalendarFilters`: client, engineer, type, status, location, approval status, and date.
- `OperationEditorDrawer`: template-first create/edit with live preview.
- `VisitAllowanceSummary`: allowance, use, reservation, remaining, classification, and history.
- `CombinedScheduleCalendar`: operations/visits plus read-only shifts.

Lazy-load data for the active tab so opening the page does not request every calendar, approval, visit, template, and report dataset at once. Use shared query keys and targeted invalidation so an operation changed in one tab refreshes affected totals and events in other tabs.

Drag/drop calls the schedule endpoint with the current version. A `409` restores the old position, reloads the event, and displays the conflict. Double-click creates on an empty slot or opens an existing event. Use drawers/dialogs over the unified page for create, edit, approval, completion, and evidence details. Keep the current list/cards inside the Operations tab as a fallback through UAT.

## 10. Implementation phases

Execute one phase at a time and stop at each gate.

### Phase 0 — Decisions and regression baseline

Implementation status: `DONE`

- Approve section 4.
- Capture existing permissions and API behavior.
- Add regression tests for templates, CRUD, recurrence, conflicts, completion-only consumption, and ledger reversal.
- Confirm clean/populated SQLite and SQL Server rehearsal commands.

**Gate:** Decisions are recorded and current behavior is protected by tests.

### Phase 1 — Domain model and lifecycle

Implementation status: `IMPLEMENTED — SQL SERVER REHEARSAL PENDING`

- Add backward-compatible schema changes.
- Implement transition validation and optimistic concurrency.
- Link operations to templates, types, approval requests, and optional visit occurrences.
- Add preview, schedule, and transition endpoints.
- Migrate existing operations to compatible status/default values.

**Gate:** Clean and populated migrations pass; invalid transitions and stale updates fail safely.

### Phase 2 — Visit planning and allowance preview

- Make visit-consuming types create/link governed visit occurrences.
- Reuse entitlement summary and recurrence-window services.
- Show allowance/history after client and template selection.
- Preserve completion-only, idempotent ledger consumption.
- Prevent duplicate outdoor-visit records through legacy creation paths.

**Gate:** Operation, occurrence, entitlement summary, and ledger reconcile with no double consumption.

### Phase 3 — Configurable approval workflow

- Add approver-profile configuration and narrow permissions.
- Implement immutable request/action history and routing.
- Add approval queue and notifications.
- Support approve, reject, request change, resubmit, and cancel.
- Classify completed approved additional visits as `APPROVED_OVERAGE` without modifying allowance.

**Gate:** Unauthorized/stale decisions fail; every decision is auditable; contract allowance is unchanged.

### Phase 4 — Calendar and saved views

- Replace the current multi-page operations workspace with `InternalOperationsWorkspacePage` and its permission-aware tabs.
- Redirect legacy `/visit-operations` and `/operational-reports` routes to the matching tab while preserving query filters.
- Add the shared event DTO and calendar tab.
- Implement Day/Week/Month/agenda modes, quick create, editor drawer, drag/drop, and double-click.
- Add requested filters and saved views.
- Move the existing operations list, visit planner, templates/types, and operational reports into their tabs before removing their old page wrappers.
- Lazy-load each tab and preserve shared context during tab changes.
- Retain the current list inside the Operations tab until calendar UAT passes.

**Gate:** All six tabs work from `/internal-operations`; legacy links redirect correctly; calendar/list records match; drag/drop is concurrency-safe; mobile and keyboard flows pass.

### Phase 5 — Combined manager calendar

- Merge operations, visit assignments, and read-only shifts.
- Reuse conflict checks for shift coverage, leave, operation overlap, and visit overlap.
- Add source/status legend and permission-aware details.

**Gate:** Results reconcile to source modules, contain no linked-operation duplicates, and expose no unauthorized details.

### Phase 6 — Reporting and release

- Report contractual completed, approved additional completed, total, pending, rejected, cancelled, and overdue visits.
- Add client/contract/engineer/type/status/approval/date filters and evidence exports.
- Add approval and schedule-change notifications.
- Run migrations, security tests, backend gates, frontend tests/typecheck/build, and release smoke tests.
- Pilot with one client/department before wider enablement.

**Gate:** Reports reconcile to operation and ledger evidence; pilot approval and rollback steps are recorded.

## 11. Permissions

Retain current permissions and add:

```text
internal_operation.calendar.view
internal_operation.schedule
internal_operation.override_conflict
internal_operation.approval.request
internal_operation.approval.decide
internal_operation.saved_view.manage
```

Approval authority must not be implied by general operation-management permission.

## 12. Required tests

- Allowed transitions succeed; unlisted transitions fail.
- Concurrent rescheduling produces one success and one stale-version conflict.
- Available allowance creates a contractual visit.
- Exhausted allowance creates `PENDING_APPROVAL` without consuming/increasing allowance.
- Approval permits scheduling; rejection prevents it.
- Completion creates exactly one ledger entry under retry; reopening creates a reversal.
- Non-visit operations never touch visit ledgers.
- Approval, calendar, and export authorization enforce the same client/department scope.
- Calendar timezone ranges, filters, saved views, conflicts, and combined-view deduplication pass.
- Contract visits plus approved additional visits equal total completed visits.
- Clean/populated SQLite and SQL Server migrations pass.
- Backend lint/type/tests and frontend tests/typecheck/build pass.

## 13. Release controls

- Use separate feature flags for the calendar and approval workflow.
- Deploy schema/backend support before enabling flags.
- Keep the current list available during pilot and rollback.
- Never delete or rewrite historical visit ledger entries.
- Seed new permissions disabled except for approved profiles.
- Compare pre/post pilot entitlement, scheduled/completed visit, and ledger totals.

## 14. Definition of done

- Operations are managed through reusable Day/Week/Month/agenda views.
- Calendar, operations, visit planning, approvals, templates/types, and reports are available on one page through permission-aware tabs.
- Templates control defaults and explicitly declare visit behavior.
- Client selection returns an auditable contractual visit summary.
- Quarterly windows can be planned before exact scheduling.
- Allowance is consumed once, only on governed completion.
- Additional visits require configurable approval and remain separate from contractual allowance.
- Statuses follow the centralized transition matrix.
- Managers can compare shifts, visits, and operations without duplicates.
- Saved views, filters, notifications, reports, and exports are permission-safe.
- Reporting reconciles contractual, approved-additional, and total visits to ledger evidence.
- SQLite/SQL Server rehearsals and all quality gates pass.

## 15. Recommended execution order

Move this document from `Backlog` to `Planned` only after section 4 is approved. Execute Phases 0–6 in order. Data correctness, lifecycle rules, and approval governance must be stable before calendar implementation begins.
