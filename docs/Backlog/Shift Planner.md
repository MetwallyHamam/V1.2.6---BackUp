# Weekly Shift Planner — One-Dialog Scheduling Plan

Last updated: 2026-09-04  
Status: `READY FOR IMPLEMENTATION — SEPARATE UNIFIED PLANNER ACTION`  
Purpose: Generate an engineer schedule for a selected date range in one simple preview-and-apply process.

> **Implementation baseline (2026-09-05):** The existing Shift module already supplies recipes, row-level time/location/headcount settings, recurrence, eligibility, rotations, conflict-aware preview/apply, coverage slots, batches, Draft creation, and publish/approve status transitions. This backlog does **not** create a second scheduling engine. It extends that engine with staffed recipe rows, a persisted date-range working plan, per-date overrides, and the schedule matrix UI.

> **Approved product boundary:** Add **Weekly Planner** as a separate action in the Unified Planner. Keep **Quick Shift** unchanged: it remains the fast single-shift creator for one Shift Type and a short date range. Weekly Planner supports multiple templates, editable shift blocks, date-by-date staffing, and one batch preview/apply. It reuses the existing scheduling services rather than creating a second scheduling engine.

## 1. Business goal

The shift manager must be able to build shifts for any selected date range from a single dialog, including:

- Weekday 09:00–17:00 office shifts.
- Weekday 09:00–17:00 work-from-home shifts.
- Night shifts from 16:00–00:00.
- Friday and Saturday coverage.
- Weekend shifts from 09:00–17:00, 14:00–22:00, and 16:00–00:00.
- Different engineers on different days, times, and work locations.
- A complete conflict and coverage preview before any shifts are created.

Assumption: The first “09:00 AM to 05:00 AM” example means 09:00 AM to 05:00 PM. If a genuine 20-hour 09:00 AM-to-next-day-05:00 AM shift is required, the overnight model can support it, but the UI must show the next-day end explicitly and warn about excessive duration.

## 2. Core design rule

Keep these concepts separate:

| Concept | Meaning | Example |
|---|---|---|
| Shift Type | Reusable time/work category | Day 09:00–17:00, Evening 14:00–22:00, Night 16:00–00:00 |
| Work Location | Where the engineer works | Office, Work From Home, Hybrid |
| Plan Row | One day/time/location requirement | Monday, Day shift, WFH, 3 engineers |
| Employee Assignment | Who works that row | Ahmed, Sara, Mahmoud |
| Coverage Requirement | How many people are required | Required 3, assigned 2, gap 1 |
| Generated Shift | The dated result saved for one engineer | Sara, Monday 09:00–17:00, WFH |

Do not create separate shift types such as “Day Office” and “Day WFH.” The same 09:00–17:00 Shift Type should be usable with either Office or WFH. This avoids duplicating time templates and makes reporting cleaner.

## 3. Existing capabilities to reuse

The current scheduling module already provides:

- Shift Types with default start/end times.
- Overnight detection when end time is earlier than or equal to start time.
- Work locations: `OFFICE`, `WORK_FROM_HOME`, and `HYBRID`.
- Schedule Recipes with multiple weekday rows.
- Weekly and other recurrence patterns.
- Assignment strategies: manual, fixed, rotation, auto-balance, and keep-existing.
- Eligibility controls per engineer and Shift Type.
- Conflict detection against shifts, visits, and internal operations.
- Coverage slots, headcount, preview, preview hash, and auditable generation batches.

This enhancement should extend the existing recipe/generator architecture rather than create a second scheduling engine.

### Unified Planner navigation

The Unified Planner must expose clear, purpose-based actions:

| Action | Primary use |
|---|---|
| `Quick Shift` | One Shift Type, one simple date range, and a fast create action. No multi-template workflow. |
| `Weekly Planner` | Build a complete week or selected date range from one or more staffed templates, edit before save, preview all work together, then create Draft shifts. |
| `Generate Shifts` | Advanced Schedule Recipe, recurrence, rotation, and Auto Balance workflow. |
| `Copy Week` | Duplicate an existing completed week using the existing copy workflow. |

If a user chooses a multi-row recipe or roster while in Quick Shift, the UI must offer **Open in Weekly Planner** instead of attempting to flatten it into the single-shift form.

## 4. Current functional gap

The generator supports one request-level `fixed_user_ids` list. It does not cleanly express different selected engineers for every plan row and date.

Example of the unsupported requirement:

- Monday 09:00–17:00 Office: Engineers A, B, C.
- Monday 09:00–17:00 WFH: Engineers D, E.
- Tuesday 09:00–17:00 Office: Engineers A, D.
- Tuesday 09:00–17:00 WFH: Engineers B, C, E.
- Friday 14:00–22:00 Office: Engineers F, G.
- Saturday 16:00–00:00 WFH: Engineer H.

The implementation needs row-level or day-cell-level employee assignments.

## 5. Proposed one-dialog workflow

### Step 1 — Date range, scope, and templates

At the top of the dialog select:

- **From date** and **To date**, inclusive. The range may be one day, a full week, or multiple weeks, subject to the existing maximum scheduling range.
- Time zone, default `Africa/Cairo`.
- Department and optional support team.
- One or more saved staffed templates. Each selected template becomes its own editable shift block; the saved template is never modified by editing that block.
- Handling mode for existing shifts:
  - Keep existing and add missing shifts.
  - Replace selected Draft shifts generated for this date range.
  - Cancel and regenerate selected rows only.

Published/approved shifts must never be silently replaced.

### Step 1A — Start from reusable staffed templates

The fastest normal workflow should be:

1. Select the From and To dates.
2. Add one or more saved staffed templates, for example `Weekday Office Team B`, `Weekday WFH Team A`, and `Weekday Night Rotation`.
3. Each template loads its days, times, locations, required headcount, and assigned engineers as an editable block.
4. Modify any block, assignment, or date cell for this date range if needed.
5. Preview conflicts and coverage across **all** selected blocks.
6. Generate the complete selected range as one batch.

Example reusable templates:

| Template | Days | Time | Location | Default engineers |
|---|---|---|---|---|
| Weekday WFH Team A | Sun–Thu | 09:00–17:00 | WFH | Ahmed, Sara, Mona |
| Weekday Office Team B | Sun–Thu | 09:00–17:00 | Office | Mahmoud, Ali, Nour |
| Weekday Night Rotation | Sun–Thu | 16:00–00:00 | Office | Rotation Group Night |
| Friday Coverage | Friday | 09:00–17:00, 14:00–22:00, 16:00–00:00 | Mixed | Saved per-row teams |
| Saturday Coverage | Saturday | 09:00–17:00, 14:00–22:00, 16:00–00:00 | Mixed | Saved per-row teams |

The template is a reusable plan definition—not the generated shifts themselves. Selecting it creates an independent working copy in the selected plan. The same template may be used more than once only after the manager deliberately duplicates the block.

After loading a template, the dialog must offer clearly separated actions:

- `Change this date range only`: modify the working copy without changing the template.
- `Save as new template`: preserve the original and save the modified plan under a new name.
- `Update template for future weeks`: create a new version of the selected template after confirmation and permission validation.
- `Duplicate block` or `Remove block`: adjust only the current plan.

The default action must always be `Change this date range only`. Editing a plan draft must never silently modify the reusable template.

If a template is updated, already generated or published weeks remain unchanged. The new template version applies only to future generations.

### Step 2 — Build weekly rows

Display one row for each coverage pattern:

| Days | Shift Type | Time | Location | Required | Engineers |
|---|---|---|---|---:|---|
| Sun–Thu | Day | 09:00–17:00 | Office | 3 | Select engineers per day |
| Sun–Thu | Day | 09:00–17:00 | WFH | 2 | Select engineers per day |
| Sun–Thu | Night | 16:00–00:00 | Office | 2 | Select engineers per day |
| Friday | Weekend Day | 09:00–17:00 | Office | 2 | Select engineers |
| Friday | Weekend Evening | 14:00–22:00 | Office | 2 | Select engineers |
| Friday | Weekend Night | 16:00–00:00 | Office | 1 | Select engineer |
| Saturday | Weekend Day | 09:00–17:00 | Office | 2 | Select engineers |
| Saturday | Weekend Evening | 14:00–22:00 | WFH | 2 | Select engineers |
| Saturday | Weekend Night | 16:00–00:00 | WFH | 1 | Select engineer |

Managers can add, duplicate, reorder, or remove rows. Selecting multiple days creates linked day cells, but each day can have a different employee list.

For normal use, template blocks are collapsed summary cards. Each card shows Shift Type, time, location, assigned engineers, date applicability, and any warning count. Selecting **Edit** expands that block; this keeps a multi-template plan readable on both desktop and mobile.

### Step 3 — Assign engineers using a date-range matrix

The easiest interaction is a matrix:

| Engineer | Sun | Mon | Tue | Wed | Thu | Fri | Sat |
|---|---|---|---|---|---|---|---|
| Ahmed | Day · Office | Day · Office | WFH | Day · Office | WFH | Off | Off |
| Sara | WFH | Day · Office | WFH | Day · Office | Day · Office | 14–22 | Off |
| Mahmoud | Night | Off | Night | Off | Night | Off | 16–00 |

The matrix displays columns only for the selected dates. For a range longer than seven days, it provides horizontal scrolling on desktop and grouped weekly sections on small screens. The planner must not force an artificial Sunday–Saturday limit.

Each cell can contain one assignment chip showing:

- Shift Type and time.
- Office/WFH/Hybrid icon.
- Draft/conflict/approved state.
- Optional on-call role.

Supported actions:

- Select multiple engineers and paint the same row across selected days.
- Copy Monday assignments to Tuesday–Thursday.
- Alternate Office/WFH days.
- Rotate weekend staff.
- Clear a selected day or row.
- Auto-fill only unassigned positions.
- Lock selected assignments so auto-balance cannot replace them.
- Restore a modified cell or row to the selected template default.
- Compare this plan's draft with the source template and highlight overrides.

### Step 4 — Preview before generation

Preview must show:

- Total shifts to create.
- Shifts retained, replaced, skipped, or conflicted.
- Coverage percentage by day and Shift Type.
- Understaffed and overstaffed rows.
- Engineer scheduled hours for the selected range.
- Office days, WFH days, night shifts, and weekend shifts per engineer.
- Consecutive working days.
- Rest time between shifts.
- Leave, visit, operation, and overlapping-shift conflicts.
- Eligibility violations.
- Any shift that ends on the following calendar day.

The Apply button remains disabled for blocking conflicts. Authorized overrides require a reason and must be audited.

### Step 5 — Apply and publish

Provide two separate actions:

- `Save as Draft`: generate editable draft shifts.
- `Generate and Publish`: generate approved shifts when the user has publish permission.

After completion, show:

- Generation batch number.
- Created, retained, replaced, skipped, and unassigned counts.
- Link to the weekly schedule.
- Link to unresolved coverage gaps.

## 6. Shift-time handling

### Normal shift

For 09:00–17:00:

```text
Start: selected date at 09:00
End:   selected date at 17:00
Duration: 8 hours before break deductions
```

### Midnight-ending shift

For 16:00–00:00:

```text
Start: selected date at 16:00
End:   following date at 00:00
Duration: 8 hours
Crosses midnight: Yes
```

The planner must display this as `16:00 → 00:00 (+1 day)` so users do not mistake midnight for the start of the same day.

### Time zone and daylight-saving rules

- Save timestamps in UTC.
- Generate them from the plan’s named time zone.
- Preserve the time-zone name on coverage slots and generation batches.
- Calculate durations from actual timestamps, not formatted clock labels.

## 7. Implementation contract: data and API extension

### 7.1 Scope of the first implementation release

The first release must deliver the following end-to-end flow:

1. Select From and To dates, scope, and one or more staffed templates.
2. Load every selected template as an independent editable block in a persisted date-range plan draft.
3. Change assigned engineers for an individual row/date cell, optionally lock the assignment, and preview the resulting range.
4. Apply using the existing stale-preview protection, with an explicit policy for existing Draft versus Published/Approved shifts.
5. Create Draft shifts by default; allow publish only through the existing `shift.publish` permission.

Template versioning, advanced labor-policy warnings, full fairness scoring, and KPI calculations are deliberately deferred unless a phase explicitly includes them. The UI must not promise an action whose backend contract has not shipped.

### 7.2 Database changes

Use normalized tables. Do not store employee IDs in comma-separated text or opaque JSON fields.

| Object | Required fields / rules |
|---|---|
| `schedule_recipe_rows` | Add immutable `row_key` (`UUID` or generated stable string), unique per recipe. It must survive row ordering changes. Backfill existing rows before making it non-null. |
| `schedule_recipe_row_members` | `id`, `recipe_row_id`, `employee_id`, `sort_order`, `is_locked`, `created_at`; unique `(recipe_row_id, employee_id)`. These are default staffed members, not generated shifts. |
| `weekly_shift_plans` | `id`, `date_from`, `date_to`, `timezone`, optional `department_id`/`team`, `status` (`DRAFT`, `APPLIED`, `PUBLISHED`, `SUPERSEDED`), `revision`, actor/timestamps. Require `date_to >= date_from`; enforce the generator's maximum range. Unique active plan per exact date range and scope. The existing table name may remain for migration compatibility, but it represents a date-range plan. |
| `weekly_shift_plan_blocks` | `id`, `weekly_plan_id`, source type/ID/version or fingerprint, display order, copied source name, and block-level notes. One record is created for each selected template or blank block. |
| `weekly_shift_plan_rows` | `id`, `weekly_plan_block_id`, copied `row_key`, weekday, Shift Type, local start/end, location, headcount, strategy, sort order. This is a working copy: future template edits must not alter it. |
| `weekly_shift_plan_assignments` | `id`, `weekly_plan_row_id`, `shift_date`, `employee_id`, `assignment_source` (`TEMPLATE`, `MANUAL`, `COPIED`, `ROTATION`, `AUTO_BALANCE`, `RETAINED`), `locked`, `override_reason`; unique `(weekly_plan_row_id, shift_date, employee_id)`. |

Generated Shift records must retain `generation_batch_id`. Add nullable provenance fields only if needed for support/audit queries: `weekly_shift_plan_id`, `weekly_plan_row_id`, and `assignment_source`. Do not retroactively rewrite historical shifts.

### 7.3 Request and response contract

Extend a schedule row with explicit employee assignments. `row_key` is supplied only for an existing saved recipe/plan row; new rows receive a server-generated key.

```json
{
  "row_key": "6c8406fe-6a13-4cbb-a1e2-b391cce5e037",
  "weekday": 0,
  "shift_type_id": 1,
  "start_time": "09:00",
  "end_time": "17:00",
  "work_location": "OFFICE",
  "required_headcount": 3,
  "assignment_strategy": "FIXED",
  "fixed_user_ids": [11, 14, 19]
}
```

For different assignments on different dates, the plan request supports overrides:

```json
{
  "date": "2026-09-07",
  "row_key": "6c8406fe-6a13-4cbb-a1e2-b391cce5e037",
  "fixed_user_ids": [11, 14, 19],
  "locked": true
}
```

The weekly-plan endpoints are the new planner boundary. They may delegate preview/apply calculations to the existing generator service.

```text
POST /weekly-shift-plans                         Create a working plan from selected templates and/or blank blocks
GET  /weekly-shift-plans/{id}                    Read plan, rows, assignments, provenance, and revision
PATCH /weekly-shift-plans/{id}                   Edit rows/assignments using expected revision
POST /weekly-shift-plans/{id}/preview            Calculate a non-persistent preview
POST /weekly-shift-plans/{id}/apply              Apply a matching preview hash and expected revision
POST /weekly-shift-plans/{id}/publish            Publish plan-generated Draft shifts; requires shift.publish
POST /weekly-shift-plans/{id}/save-as-template   Create a new recipe from the working plan
```

`PATCH`, `preview`, and `apply` must reject stale `revision` values. `apply` must require the matching SHA-256 `preview_hash` and execute in one transaction.

Required backend changes:

1. Add stable `row_key` identifiers and staffed row members.
2. Add plan blocks with source-template provenance, plus plan-row/date-specific assignment overrides and locks.
3. Preserve request-level `fixed_user_ids` only for legacy generator compatibility; new planner calls resolve fixed users per plan row/date.
4. Include assignment source, row key, plan row ID, retained/replaced/skipped result, and blocking/warning codes in preview results.
5. Apply an explicit existing-shift policy: retain matching shifts; replace only selected generated Draft shifts belonging to the same plan; never silently replace Published or Approved shifts.
6. Make apply idempotent using plan ID, revision, preview hash, and a generation key. A retry must return the original completed batch/result.
7. Return per-row and per-assignment outcomes in addition to aggregate counts.

If employee assignments must be saved as reusable templates, add a child table such as `schedule_recipe_row_members` containing recipe row, weekday/date rule, employee, sort order, and lock state. Do not store employee ID lists as comma-separated text.

### 7.4 Template versioning (phase 2)

Enhance the existing Schedule Recipe so it can act as a staffed weekly template. Existing staffed Roster Templates are also valid planner sources; the planner copies either source into plan blocks and normalizes them into the same internal plan-row shape.

- Recipe: name, scope, timezone, effective dates, status, and current version.
- Recipe row: weekday, Shift Type, start/end time, location, headcount, and assignment strategy.
- Recipe row member: the default engineer or rotation assigned to that row.
- Recipe version: immutable snapshot of rows and members used for generation.
- Date-range plan draft: target dates plus a reference to the source recipe version.
- Date-range plan override: only the rows or day cells changed for those dates.

Until immutable recipe versions ship, creating a date-range plan must copy rows and members into the plan tables, so template edits cannot change a previously prepared range. When versions are introduced, save the source recipe version on the plan and generated shifts for explainability.

## 8. Validation rules

### Blocking validations

- Engineer is inactive or does not participate in shifts.
- Engineer is not eligible for the Shift Type where eligibility is enforced.
- Overlapping shift, visit, or internal operation.
- Engineer is on approved leave.
- End time cannot produce zero or invalid duration.
- Duplicate assignment for the same engineer and time interval.
- Attempt to overwrite published/approved work without explicit permission.
- Preview is stale because shifts or availability changed before Apply.

### Configurable warnings

- Insufficient rest between consecutive shifts.
- Weekly scheduled hours exceed the configured limit.
- Excessive consecutive working days.
- Too many night or weekend shifts compared with peers.
- WFH allowance or office-presence requirement exceeded.
- Required headcount not met.
- Engineer scheduled after a night shift on the next morning.

Warnings may be overridden only where policy allows, with a reason saved to the generation batch and affected shifts.

## 9. Fairness and auto-assignment

Auto-balance should rank eligible available engineers using configurable weighted factors:

- Lowest scheduled weekly minutes.
- Lowest recent night-shift count.
- Lowest recent weekend-shift count.
- WFH/office rotation balance.
- Required skill or Shift Type eligibility.
- Minimum-rest compliance.
- Existing operations and visits.
- Locked assignments excluded from replacement.

The preview should explain why each engineer was selected or rejected. Managers must be able to manually adjust the proposal before applying it.

## 10. Relationship to engineer KPI and contract coverage

The generated shift establishes the engineer’s scheduled-accountability calendar. It does not replace the contract SLA calendar.

Use separate measures:

- Contract SLA time: calculated from the customer contract calendar.
- Engineer scheduled time: calculated from generated approved shifts.
- Engineer active work: calculated from qualifying activity/worklogs.
- Engineer after-hours work: qualifying activity outside approved shifts.
- Company coverage gap: contract calendar is open but no eligible engineer is scheduled.

Changing or cancelling a past shift must be restricted and audited because it can affect engineer KPI results. Published historical shifts should be versioned rather than silently overwritten.

## 11. Recommended permissions

| Permission | Purpose |
|---|---|
| `shift.view` | View weekly schedules and coverage. |
| `shift.manage` | Build and edit draft date-range plans. |
| `shift.publish` | Publish a date-range plan. |
| `shift.override.conflict` | Override allowed warnings/conflicts with a reason. |
| `shift.edit.published` | Correct published shifts with full audit history. |

Existing permissions may be reused where they already express the same authority. Do not rely only on hiding frontend buttons.

## 12. Implementation phases, dependencies, and status

| ID | Work item | Status |
|---|---|---|
| SP-001 | Confirm organization first weekday, rest/hour policy, weekend definition, WFH rules, and authorized overwrite behavior. Record the decisions in configuration/defaults. | `BLOCKED BY BUSINESS DECISIONS` |
| SP-002 | Migration: stable recipe `row_key`; staffed recipe-row-member table; backfill and uniqueness constraints. Row-level fixed employees are now accepted in ad-hoc generator rows; persistence migration remains. | `IN PROGRESS` |
| SP-003 | Migration and service: persisted date-range plans, copied template blocks/rows, dated assignments/locks, revision handling, and audit records. Support existing staffed Roster Templates first; normalize Recipe sources through the same plan-block contract. Depends on SP-002. | `READY AFTER SP-002` |
| SP-004 | Planner API: create/read/patch/preview/apply; support multiple source template blocks and adapt existing generator so plan assignments are resolved per row/date. Include structured per-row result codes. Depends on SP-003. | `READY AFTER SP-003` |
| SP-005 | Existing-shift policy, idempotent Apply, stale plan revision protection, and selected Draft regeneration. Depends on SP-004. | `READY AFTER SP-004` |
| SP-006 | Separate Weekly Planner dialog in Unified Planner: From/To and scope, multi-template block selection, editable roster-template blocks, combined preview, and Draft creation are implemented as the first vertical slice. Date-cell matrix, locks, persisted plan drafts, and provenance remain dependent on SP-003/SP-004. Quick Shift remains unchanged. | `IN PROGRESS` |
| SP-007 | Quality-of-life interactions: copy, paint, restore template default, rotate, Auto Fill only gaps, and save as template. Depends on SP-006. | `READY AFTER SP-006` |
| SP-008 | Publish plan-generated Draft shifts and show retained/replaced/skipped/unassigned outcomes. Reuse existing status permissions. Depends on SP-005. | `READY AFTER SP-005` |
| SP-009 | Immutable recipe versions and explicit plan-versus-template comparison. Depends on SP-003. | `DEFERRED — PHASE 2` |
| SP-010 | Configurable rest, weekly hours, consecutive-day, night/weekend/WFH fairness rules and override workflow. Depends on SP-004 and SP-001. | `DEFERRED — PHASE 2` |
| SP-011 | Approved-shift KPI/after-hours integration. Depends on SP-008 and KPI policy decisions. | `DEFERRED — PHASE 3` |
| SP-012 | Backend, frontend, migration, overnight, existing-shift, idempotency, stale-revision, permission, and accessibility tests; clean-install/upgrade rehearsal and release build. | `REQUIRED BEFORE RELEASE` |

## 13. Acceptance scenario

In one dialog, a manager selects From/To dates and department, then configures:

- Sunday–Thursday: 3 office and 2 WFH engineers on 09:00–17:00.
- Sunday–Thursday: 2 engineers on 16:00–00:00.
- Friday: 2 engineers on 09:00–17:00, 2 on 14:00–22:00, and 1 on 16:00–00:00.
- Saturday: the same three weekend coverage bands with different selected engineers.

The manager assigns different people in each date cell, copies or rotates assignments where helpful, previews all coverage and conflicts, corrects any gaps, and generates the selected range once.

For the normal recurring case, the manager instead selects a staffed template such as `Weekday WFH Team A`. The complete default schedule and engineers load immediately. The manager changes only absences or exceptional days, previews, and generates. The selected template remains unchanged unless the manager deliberately chooses `Update template for future weeks`.

The system creates one dated shift per engineer assignment, identifies midnight endings as next-day times, prevents duplicates, retains protected existing shifts, stores one auditable generation batch, and immediately shows the completed weekly schedule and remaining gaps.

### Release acceptance tests

The release is accepted only when automated tests prove all of the following:

1. A recipe row retains its `row_key` after rows are reordered; the migration safely backfills existing rows.
2. A staffed recipe loads the correct default engineers for every applicable row/date, without modifying the recipe when the date-range plan is edited.
3. The same Shift Type can be scheduled on the same date for Office and WFH with distinct staffed members.
4. A manual date override affects only its requested row/date; a locked assignment is never replaced by Auto Fill or Auto Balance.
5. A 16:00–00:00 assignment ends at next-day midnight in the configured named timezone and stores UTC timestamps correctly.
6. Inactive, non-participating, ineligible, or conflicting engineers cannot be applied; the preview returns a machine-readable reason.
7. A changed plan revision, availability input, or preview hash rejects Apply without writing partial rows.
8. Retrying the same successful Apply is idempotent and returns the original generation outcome; it does not create duplicate shifts or coverage slots.
9. Selected generated Draft shifts may be regenerated according to policy; Published and Approved shifts are retained unless an authorized, audited correction flow is used.
10. A user without `shift.manage` cannot create/edit/apply a plan, and a user without `shift.publish` cannot publish it, even if frontend controls are bypassed.
11. The date-range matrix is keyboard usable, exposes assignment/conflict/lock state to assistive technology, and remains usable on supported narrow screens.

## 14. Open decisions

| Decision | Recommended default | Status |
|---|---|---|
| Week starts on | Sunday for the Cairo operating context, configurable by organization | `OPEN` |
| Normal weekly hour limit | Use HR policy; warn before blocking | `OPEN` |
| Minimum rest between shifts | 11 hours unless HR policy defines another value | `OPEN` |
| Friday/Saturday definition | Weekend, but allow department-specific working patterns | `OPEN` |
| Can one engineer have two non-overlapping shifts in one day? | Warning plus authorized override | `OPEN` |
| WFH limits | Configurable by employee/team and week | `OPEN` |
| Published-plan corrections | Versioned correction with reason and special permission | `OPEN` |
| Generation behavior | Keep approved shifts; replace only selected draft/generated rows | `OPEN` |
| Template edits after selection | Default to this-week-only overrides; require an explicit action to update future template versions | `OPEN` |

## 15. Current checkpoint

- Existing scheduling foundation: `DONE`
- Date-range planner extension design and implementation contract: `DONE`
- Date-range planner application implementation: `NOT STARTED`
- Date-range planner migrations: `NOT STARTED`
- Date-range planner automated tests: `NOT STARTED`
- Immediate engineering task: `SP-002 — Stable row keys and staffed recipe-row members`
- Required business decision in parallel: `SP-001 — Confirm organization scheduling and HR policy defaults`
