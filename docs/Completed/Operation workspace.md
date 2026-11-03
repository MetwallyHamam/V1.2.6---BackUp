# Operations Workspace Enhancement Plan

Status: reviewed and ready for implementation planning.

## Approved enhancement scope

### 1. Rename Operations Calendar

- Rename **Operations Calendar** to **Shifts Calendar** in the Operations Workspace navigation and page heading.
- Keep internal operations and visits available as optional calendar sources when the user has permission; the new name describes the primary planning purpose and must not remove the unified-calendar capability.

Acceptance criteria:

- The new label is used consistently in navigation, breadcrumbs, headings, permissions descriptions, and help text.
- Existing routes and bookmarks continue to work.

### 2. Rename Schedules & Templates

- Rename **Schedules & Templates** to **Operation Jobs**.
- Operation Jobs becomes the management area for internal operations, reusable operation templates, and visit operations.

Acceptance criteria:

- The label is consistent throughout the UI.
- The existing route remains supported or redirects to the new canonical route.

### 3. Move Visit Operations into Operation Jobs

- Add **Internal Operations** and **Visit Operations** as sub-tabs under Operation Jobs.
- Preserve independent permission checks for each sub-tab. A user may see one sub-tab without being allowed to see the other.
- Remove the old standalone Visit Operations top-level tab after the nested route and permissions are verified.

Acceptance criteria:

- Direct links open the correct Operation Jobs sub-tab.
- Hidden sub-tabs cannot be accessed by typing their URL without the required permission.
- Moving the UI does not change contractual entitlement or visit-completion rules.

### 4. Add an effective date range to weekly roster creation

- Add required **Date From** and **Date To** fields when applying a weekly roster.
- Weeks and weekdays must be recalculated inside the selected date range.
- Show the exact dates and proposed shifts before saving.
- Reject an invalid range where Date To is before Date From.

Acceptance criteria:

- Only dates inside the inclusive selected range are generated.
- The preview and committed shifts contain exactly the same dates.
- Overnight shifts and local timezone boundaries are handled correctly.

### 5. Make weekly roster templates reusable and user-independent

- Separate the reusable roster pattern from a roster application.
- Store shift rows, time ranges, weekdays, and week rules in the template, but do not require permanent employee assignments in the template.
- Select employees when applying the template to a Date From / Date To range.
- Allow cloning, editing, deactivating, and reusing templates without changing shifts already generated from an older version.

Acceptance criteria:

- A template can be saved with no users.
- Applying a template requires at least one eligible user.
- Editing a template does not alter historical or already-created shifts.

### 6. Enhance Operational Reports

- Add **shift count per engineer** for a selected Date From / Date To range.
- Default the report range to the first and last day of the current month.
- Add worked/scheduled hours alongside shift count so short and long shifts are not treated as equal workload.
- Paginate the Clients report at 20 clients per page, with next, previous, page number, and total-count information.
- Apply pagination on the backend so the browser does not load every client before displaying 20.

Acceptance criteria:

- Counts reconcile with the shifts visible for the same filters and permissions.
- Changing the range refreshes totals and drill-down data.
- Client pagination preserves filters and sort order.
- CSV export exports the full filtered result, not only the visible page, and clearly states that behavior.

### 7. Show engineer scheduling balance

- Add an engineer balance panel to Shifts Calendar and roster preview.
- Show, for the selected range: shift count, scheduled hours, target hours/shifts, remaining balance, overtime, leave/unavailable time, operation jobs, visits, and detected conflicts.
- Allow sorting by underallocated, balanced, overallocated, unavailable, and conflicted.
- Keep the target source configurable by department, employee, or contract policy instead of hard-coding one balance formula.

Acceptance criteria:

- The balance uses the same canonical schedule data as conflict validation and reporting.
- Every total can be drilled down to its contributing shifts/jobs.
- Users only see engineers and activity details allowed by their data scope.

### 8. Make the hidden-row hint interactive

- Make the **+ N more rows** hint in Shift Templates a keyboard-accessible button.
- Clicking it expands all hidden rows; when expanded, provide a **Show less** action.
- Preserve the expanded state while editing the same template.

Acceptance criteria:

- The displayed number always matches the hidden row count.
- Expansion works by mouse and keyboard and does not discard unsaved row edits.

### 9. Enhance reusable internal-operation templates

- Add **Date From** and **Date To** when applying an internal-operation template.
- Keep weeks and weekdays as recurrence selectors within the inclusive date range and preview exact generated dates.
- Make the client optional for normal internal-operation templates.
- When a template represents a governed field visit, require the applicable client/contract entitlement before generation.
- Support reusable, cloneable, versioned, and deactivatable templates; historical jobs retain the applied template snapshot.


Acceptance criteria:

- Applying a template produces only previewed dates within the selected range.
- Normal operations can be created without a client; governed visits cannot bypass entitlement rules.
- WFH is unavailable for new operation jobs but remains readable in historical records.

## Recommended implementation refinements

The following refinements should be delivered with the approved scope because they prevent permission errors, duplicate activities, and unreliable workload totals.

### Technical objective

Make Operations Workspace the single, permission-correct planning and execution surface for shifts, internal operations, and contractual field visits. The workspace should provide one understandable calendar event per activity, actionable conflict explanations, safe scheduling controls, and drill-down evidence without forcing users to move between unrelated pages.

### Current implementation baseline

The current workspace already provides:

- Permission-aware top-level sections for Operations Calendar, Internal Operations, Visit Operations, and Operational Reports.
- A unified calendar that can load permitted shifts, internal operations, and field visits independently.
- Day, week, and month calendar views with source filters and availability summaries.
- Shift templates, weekly roster templates, duplication, and preview-first bulk deletion.
- Internal-operation types, templates, From/To scheduling, week/day selection, multiple assignees, comments, documents, and lifecycle transitions.
- Governed Outdoor / field visit creation linked to exact-client visit entitlements.
- Operational client/department reports and CSV export.
- Granular internal-operation page and function permissions.

### Confirmed gaps and risks

#### P0 — Correctness and permission alignment

1. **Remove frontend permission fallbacks.** Internal Operations currently enables transition, comment, upload, and download controls when the user merely has `internal_operation.view`. The API requires the granular function permission, so the screen can offer actions that later fail. Every control must use the same permission required by its endpoint.
2. **Use granular read permissions consistently.** Calendar and supporting option endpoints should accept the appropriate workspace/calendar permissions instead of depending on the legacy broad `internal_operation.view` permission.
3. **Prevent duplicate outdoor events.** A linked outdoor internal operation and its generated visit occurrence can both appear in the unified calendar. Render one canonical event with both operation and visit badges, IDs, and links.
4. **Standardize timezone behavior.** Manually created visit assignments currently use UTC while template-generated assignments use `Africa/Cairo`. Store UTC instants consistently, retain the declared business timezone, and convert only at API/UI boundaries.
5. **Add cross-source conflict checks.** Operation-template generation currently checks overlapping internal operations but must also evaluate shifts, visits, approved leave/unavailability, and department restrictions using one conflict service.

Acceptance criteria:

- A user never sees an enabled action that their effective permissions cannot execute.
- A linked field visit appears once on the calendar.
- The same activity displays identical local start/end times whether created manually or from a template.
- Conflict decisions are identical across shift, operation, and visit creation paths.

## Additional future enhancements

### P1 — Unified calendar usability

1. Add employee, department, client, operation type, status, location, and assigned-team filters.
2. Add a text search covering activity title, employee, client, location, and operation/shift code.
3. Save personal and shared Operations views containing date mode, filters, visible sources, and grouping.
4. Make every calendar card clickable and open a common activity drawer. The drawer should show:
   - source and linked records;
   - schedule and timezone;
   - employees, department, client, and location;
   - lifecycle status and permitted actions;
   - conflict evidence, comments, documents, and audit history.
5. Add grouping modes for employee, department, client, and source in day/week views.
6. Add a compact agenda/list view for dense operational periods and mobile devices.
7. Add “Today,” previous/next period, and explicit date-jump controls with the selected range in the URL.
8. Show loading/error state independently per calendar source instead of one combined warning.

Acceptance criteria:

- Filters and selected range survive refresh and can be saved as a view.
- Clicking any source opens consistent details without losing the calendar position.
- Failure to load one source does not hide successfully loaded sources.

### P1 — Preview-first scheduling and conflict resolution

1. Introduce a shared preview endpoint used by shifts, internal operations, templates, rosters, and visits before committing schedules.
2. Return row-level results rather than only `created` and `skipped` totals:
   - proposed date/time;
   - employee;
   - result (`READY`, `WARNING`, or `BLOCKED`);
   - conflicting activity and source;
   - policy/rule code;
   - permitted resolution actions.
3. Display the preview in a selectable table so the scheduler can remove blocked rows, adjust dates, or apply authorized overrides with a mandatory reason.
4. Support partial commit using an idempotency key; repeating the same submission must not create duplicates.
5. Add capacity warnings for excessive consecutive hours, insufficient rest, overlapping assignments, and activities outside an employee’s shift.

Acceptance criteria:

- No bulk generation occurs without a preview matching the submitted version.
- Every skipped or blocked row has a human-readable explanation.
- Override permission and reason are validated and audited by the backend.

### P1 — Internal-operation lifecycle workspace

1. Replace unrestricted status patching with explicit permitted transitions displayed from backend lifecycle metadata.
2. Add schedule, reassign, confirm, reject, cancel, reopen, and complete actions according to the operation type’s policy.
3. Require configured completion evidence before completion when the operation type demands it.
4. Add a structured Minutes of Meeting editor with attendees, decisions, action items, owners, and due dates instead of storing all MOM information as free text.
5. Add operation activity history showing creation, assignment, rescheduling, transitions, comments, documents, approvals, and linked visit consumption.
6. Add “My operations,” “My team,” “My department,” “Unassigned,” “Due today,” “Overdue,” and “Awaiting approval” quick queues.

Acceptance criteria:

- Invalid lifecycle transitions cannot be offered or submitted.
- Completion evidence requirements are enforced server-side.
- Every material change appears in one chronological audit timeline.

### P1 — Template and recurring schedule governance

1. Add template preview before applying a month or date range.
2. Show the exact computed dates produced by From/To, Weeks 1–4, weekdays, and week-start selection.
3. Add an explicit fifth/last-week policy for months containing partial or fifth calendar weeks.
4. Support effective-from/effective-to dates and template versions.
5. Allow templates to be cloned and retired; existing scheduled operations must retain their template/version snapshot.
6. Add recurring-series identity so authorized users can edit or cancel one occurrence, future occurrences, or the entire series.
7. Require client and entitlement selection in the template itself when an outdoor template is client-specific; otherwise require it during application.

Acceptance criteria:

- Preview dates exactly match committed dates.
- Editing a template never changes historical operations.
- Series changes are explicit, version-protected, and audited.

### P2 — Workforce availability and capacity

1. Replace the current text-only availability cards with searchable employee capacity rows.
2. Calculate availability from shifts, operations, visits, approved leave, and active presence.
3. Distinguish `AVAILABLE`, `BUSY`, `WFH`, `FIELD_VISIT`, `OFF_SHIFT`, `ON_LEAVE`, and `CONFLICTED`.
4. Display next availability time and current activity subject to permissions.
5. Add department capacity totals and uncovered shift/visit warnings.
6. Support an employee timeline view for investigating overlaps and handoffs.

Acceptance criteria:

- Availability is derived from the same canonical events used by conflict validation.
- Counts reconcile with the employee-level rows and respect data visibility permissions.

### P2 — Visit integration

1. Treat the internal operation as the planning/execution shell and the visit occurrence as contractual entitlement evidence.
2. Display linked entitlement, contract, visit sequence, allowance state, and consumption state in the common drawer.
3. Synchronize approved rescheduling, reassignment, cancellation, and completion across the operation and visit records atomically.
4. Prevent an operation from completing if required visit evidence is incomplete.
5. Add a repair/diagnostic report for orphan operations, orphan occurrences, duplicate links, and mismatched assignments.

Acceptance criteria:

- A linked operation and visit cannot diverge silently.
- Contract allowance is consumed exactly once through the governed completion path.

### P2 — Notifications and handoffs

1. Notify assignees when an operation is created, reassigned, rescheduled, cancelled, or awaiting action.
2. Add configurable reminders before start, at overdue, and before required evidence deadlines.
3. Support structured shift handoff of unfinished operations with receiving engineer acknowledgement.
4. Avoid duplicate notifications when the same field activity is represented by linked operation and visit records.

### P2 — Reporting and management controls

1. Add operational KPIs for planned versus completed work, cancellation, overdue work, utilization, conflict/override rate, field-visit fulfillment, and evidence completeness.
2. Add drill-down from every metric to the filtered calendar/list evidence.
3. Add export columns for source, operation/shift type, client, department, assignees, timezone, lifecycle timestamps, template/version, conflict decision, and linked visit/entitlement IDs.
4. Add data-quality warnings for missing departments, inactive assignees, orphan links, invalid time ranges, and legacy timezone records.
5. Preserve formula version, generated time, timezone, filters, and source revision in every report/export.

## Permission model

Retain the current granular permissions and add only capabilities that cannot be represented safely by them:

| Capability | Permission |
|---|---|
| Open workspace | `internal_operation.workspace.view` |
| View operation calendar events | `internal_operation.calendar.view` |
| View shifts | Existing shift view permissions |
| View contractual visits | Existing visit view permissions |
| Create operation | `internal_operation.create` |
| Schedule/reschedule | `internal_operation.schedule` |
| Assign/reassign | `internal_operation.assign` |
| Transition lifecycle | `internal_operation.transition` |
| Comment / MOM | `internal_operation.comment` |
| Upload/download documents | Existing granular document permissions |
| Manage templates/types | Existing template/type permissions |
| Override a conflict | `internal_operation.override_conflict` |
| View operation audit history | Proposed `internal_operation.audit.view` |
| Manage recurring series | Proposed `internal_operation.series.manage` |

Backend authorization is authoritative. Frontend visibility must mirror the exact endpoint permission and must not substitute a broad view permission for a function permission.

## Suggested delivery sequence

### Release A — Correctness foundation

- Permission alignment.
- Canonical linked-event deduplication.
- Timezone normalization.
- Shared conflict/availability service.
- Regression tests and populated SQL Server upgrade rehearsal.

### Release B — Planner experience

- Common activity drawer.
- Expanded filters, saved views, agenda/grouped views, and URL state.
- Preview-first bulk scheduling with row-level explanations.
- Template preview and version snapshots.

### Release C — Execution governance

- Explicit lifecycle actions and evidence requirements.
- Structured MOM/action items.
- Atomic operation/visit synchronization.
- Notifications, handoff, audit timeline, and management reports.

## Non-goals and safeguards

- Do not merge shift, operation, and visit database records into one table; use a canonical read model/event adapter while preserving each domain’s rules.
- Do not weaken entitlement, assignment, conflict, or evidence validation for calendar convenience.
- Do not permit drag/drop or bulk actions until preview, version checking, permissions, and audit evidence are enforced server-side.
- Do not delete historical templates, types, series, operations, or visit evidence when retiring master data.
- Do not represent the same linked outdoor activity as two independent calendar events or two notifications.

## Definition of done

- Additive, SQL Server-safe, retryable migration where schema changes are required.
- Clean-install and populated-upgrade rehearsals pass.
- API permission tests cover every section and action.
- Conflict tests cover shift/operation/visit/leave overlaps, timezone boundaries, overnight work, and concurrent submissions.
- Frontend tests cover source failure isolation, saved views, canonical outdoor rendering, preview decisions, and permission-hidden actions.
- Ruff, strict MyPy, full backend tests, ESLint, frontend tests, TypeScript, and production build pass.
- Release notes and the recovery log identify migration head, deployment order, rollback approach, and reconciliation checks.
