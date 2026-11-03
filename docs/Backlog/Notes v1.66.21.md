# Support Hub Backlog — Ticket Enhancements and Checklist Modules

Status: **REVIEWED AND PREPARED FOR IMPLEMENTATION**  
Prepared: **2026-09-13**

This document preserves the requested behavior and converts it into an implementation-ready specification. The new features should share versioned checklist, evidence, notification, audit, and export foundations, but remain separate modules because internal recurring work and client-visible UAT have different workflows and access rules.

## 1. Tickets Page Enhancements

### 1.1 Update a saved view without losing current filters

**Gap:** Opening **Edit View** restores the saved filters, discarding filters just added on the Tickets page.

**Required behavior:**

- **Update from Current Filters** saves exactly the filters currently applied to the page.
- **Edit Name & Settings** changes only name, sharing, and default options.
- Show filters added, changed, and removed before overwrite.
- Provide **Save as New View** beside Update.
- Preserve current page state on cancel or failure.
- Use optimistic version checking for concurrent edits.

Recommended saved-view menu: Apply View; Update from Current Filters; Edit Name & Settings; Save as New View; Set as Default; Delete View.

### 1.2 Save layout per view

A saved view may optionally store separate Grid and Cards layouts:

- Grid columns, order, width, visibility, sorting, and direction.
- Card lanes, lane order, grouping, sorting, direction, and collapsed state.
- Selected layout style and density.

**Save Layout** should offer:

1. **This view and current layout** — recommended default.
2. **This view for both Grid and Cards**.
3. **My global layout** — fallback when a view has no override.

Applying a view restores its filters and optional layout together.

### 1.3 Replace technical filter names

Never expose keys such as `strictly_unassigned_only`. Display **Strictly Unassigned** with localized help: “Tickets with no assigned engineer and no assigned team.” Audit all filters for raw API/database labels.

### 1.4 Keep layout controls visible for empty results

The workspace header must render even when zero tickets match. Always show ticket/selection counts, Sort, Direction, Group By, Grid/Cards switch, Save Layout, Set Default, grid columns, and configured card lanes. The empty state belongs inside the grid body or lanes.

### 1.5 Assigned In Progress tickets missing from lane

The In Progress lane must use authoritative status code `IN_PROGRESS`, not assignment state, translated labels, or `progress_started_at` alone. Review hidden saved filters—especially Strictly Unassigned—and add regression cases for engineer assignment, team assignment, and both.

### 1.6 Product-driven ticket exception approval

A ticket requires approval only when:

1. The client is inactive or ticket-restricted.
2. The selected product is outside effective contract coverage.

A module or service must not independently request approval when its parent product is covered. It may show a warning.

Add **Site Settings → Contracts → Ticket Validation & Approval**:

- Approval for inactive/restricted clients.
- Approval for uncovered products.
- Uncovered module treatment: Allow / Warn / Require Approval.
- Uncovered service treatment: Allow / Warn / Require Approval.
- Recipient profiles and named users.
- Reminder/timeout values.
- Awaiting approval behavior: create Pending Approval or block creation.

Recommended defaults are product-driven approval with module/service set to **Warn**. The server remains authoritative and stores an immutable decision snapshot.

---

## 2. New Module A — Recurring Service Checklists

### 2.1 Purpose

Manage repeatable internal service work for dedicated clients. Example: **Alfa Scan Weekly Checklist** containing Database Backup, Storage Checkup, Cleanup, and Application Backup. Every generated occurrence has a due date. The parent cannot complete until all required items and evidence are complete or formally waived with permission and a reason.

Do not reuse onboarding or ticket checklist records as live service checklists; their lifecycle and ownership differ.

### 2.2 Navigation and UI

Add **Service Checklists** under Operations with:

- **My Work:** due today, upcoming, overdue, completed.
- **Team Board:** Upcoming, Due Today, In Progress, Overdue, Completed lanes.
- **Calendar:** day/week/month occurrences.
- **Templates:** reusable definitions and version history.
- **Schedules:** recurrence, clients, ownership, reminders, escalation.
- **Reports:** completion, timeliness, waivers, evidence, clients, engineers.

Summary cards: Due Today, Overdue, Due This Week, Completed On Time, Completion Rate, Escalated.

### 2.3 Template designer

Use a two-panel editor: template/product details on the left; draggable sections/items on the right. Each item supports title, instructions, required/optional, expected duration, assignee override, warning threshold, waiver control, and evidence type: none, comment, file, value, confirmation, or link.

Publishing creates an immutable version. Existing occurrences retain their snapshot; future occurrences use the latest published version.

### 2.4 Schedule wizard

1. Select template.
2. Select one or multiple clients.
3. Assignment: dedicated engineer, named engineer, team rotation, or manual.
4. Recurrence: daily, weekly, monthly, custom interval, or specific dates.
5. Due time, timezone, date range, weekend/holiday behavior.
6. Reminders and escalation.
7. Preview exact occurrences before saving.

Dedicated-engineer assignment is resolved from authoritative responsibility at generation time and stored on each occurrence.

### 2.5 Occurrence workspace and lifecycle

Display client, template/version, owner, due date, progress ring, checklist sections, inline evidence, comments, files, worklog, and audit timeline. Actions: Start, Complete Item, Waive, Reassign, Complete Checklist.

Statuses: Scheduled, Due, In Progress, Completed, Completed Late, Overdue, Cancelled. Completion is transactional: the server revalidates every required item/evidence before completing the parent.

### 2.6 Notifications and escalation

Schedules configure reminders before due time, warning at due time, escalation after an overdue interval, repeat interval/limit, and recipients: named users, team leader, team, department manager, or selected profiles.

Use the durable notification/outbox system with stable deduplication keys. Store profiles by ID and revalidate recipient activity/access at delivery time.

### 2.7 Permissions

- `service_checklist.view_own`, `.view_team`, `.view_all`
- `service_checklist.perform`, `.reassign`, `.waive_item`
- `service_checklist.template.view`, `.template.manage`
- `service_checklist.schedule.manage`
- `service_checklist.report.view`, `.export`

### 2.8 Reporting

Report on on-time/late completion, duration, overdue aging, missing evidence, waived/failed items, escalations, and performance by engineer, client, product, and template. Every metric drills down to exact occurrences; export active filters to Excel/PDF.

---

## 3. New Module B — UAT & Test Management

### 3.1 Purpose and structure

Create reusable product-linked UAT templates, assign versioned runs to clients, let authorized internal/portal participants execute tests, calculate transparent results, identify attention areas, create defect tickets, and export professional reports.

```text
UAT Template
└── Functional Area / Section
    └── Test Case
        ├── Preconditions and numbered steps
        ├── Expected result
        ├── Product(s) / module(s)
        ├── Weight and criticality
        └── Evidence requirement

UAT Run (immutable template snapshot for one client)
└── Test Result
    ├── Pass / Fail / Blocked / N/A / Not Tested
    ├── Actual result and evidence
    ├── Tester and timestamp
    └── Linked defect ticket(s)
```

One template may cover multiple products; each test case may link to one or more products/modules.

### 3.2 Navigation and dashboards

Add **UAT & Testing** with Dashboard, UAT Runs, Templates, Defects, and Reports tabs. Dashboard cards: Active Runs, Awaiting Client, Critical Failures, Blocked Tests, Pass Rate, Overdue Runs.

UAT Runs supports Grid/Cards with client, product, owner, deadline, progress, score, and status. Client Portal shows UAT only with portal permission and exact assigned client/run access.

### 3.3 Template library and import

Support create, clone, edit draft, publish version, deactivate, audit/change history, section/test ordering, product/module linking, Excel export, and governed Excel import with template download, preview, validation errors, and idempotency.

Test cases include code, title, area, products/modules, preconditions, numbered steps, expected result, Critical/High/Medium/Low classification, score weight, evidence requirement/types, and Internal Only flag. Published versions are immutable; editing creates a new draft version.

### 3.4 Create UAT Run wizard

1. Client.
2. Product(s).
3. Compatible template/version.
4. Internal owner and client participants.
5. Planned start and due dates.
6. Pass threshold and critical-test rule.
7. Preview visible cases/assignments.
8. Create and notify participants.

The run stores a complete snapshot so later template edits never alter active or historical testing.

### 3.5 Test execution UI

- Left: sections with progress/attention indicators.
- Center: current case, steps, expected result, result, actual result, evidence.
- Right: score/progress, failures, blockers, defects, participants, due date.
- Portal/mobile: one test-case card with large result buttons.

**Fail** requires actual result/bug description; **Blocked** requires reason; required **N/A** requires reason. Autosave drafts and show last editor/time. Optimistic concurrency prevents silent overwrites.

### 3.6 Scoring and acceptance

```text
Score = passed applicable weight / completed applicable weight × 100
```

- Approved N/A is excluded.
- Submission is blocked while required cases are Not Tested.
- Passed: threshold met and no Critical failures.
- Passed with Conditions: threshold met but approved non-critical defects remain.
- Failed: threshold missed or a Critical case failed.
- Incomplete: required testing unfinished.

Show formula, included/excluded weight, threshold, and critical failures in the UI.

### 3.7 Defect-ticket integration

Failed/blocked cases provide **Create Defect Ticket**, prefilling client, product/module, UAT references, steps, expected/actual result, evidence links, and configurable priority from criticality. Maintain bidirectional links and show ticket status, assignee, and resolution. Use idempotency to prevent duplicate tickets.

### 3.8 Professional report

Generate versioned PDF and Excel reports with branding; client/products/template; dates/participants; acceptance decision; score/threshold/progress; status and functional-area summaries; critical/high failures; blockers; linked defect status; evidence appendix; sign-offs; and report revision/audit data.

Build the bug summary from structured failed/blocked results. Optional AI-assisted narrative can be added later, but must be editable, labelled assisted, and unable to alter authoritative results or scores.

### 3.9 Lifecycle

Draft, Planned, In Progress, Awaiting Client, Submitted for Review, Changes Requested, Accepted, Accepted with Conditions, Rejected, Cancelled. Only authorized reviewers accept/reject. Reopening an accepted run creates an audited retest cycle or new revision; historical sign-off is immutable.

### 3.10 Permissions and portal isolation

Internal:

- `uat.view`, `.view_all`, `.create`, `.execute`, `.review`, `.accept`, `.reopen`
- `uat.template.view`, `.template.manage`, `.import`
- `uat.defect.create`, `.report.export`

Portal:

- `portal.uat.view`, `.execute`, `.submit`, `.accept`, `.report.download`

Portal users are restricted by exact client scope. Internal cases, notes, evidence, audit metadata, and defect details are removed server-side—not merely hidden in the UI.

### 3.11 Audit/history

Audit templates/imports/versions, item changes/reordering, run assignment/rescheduling, every result/evidence change, defect linking, submission/review/sign-off/reopen, and report generation. Referenced templates, runs, results, evidence, sign-offs, and reports use deactivation/soft deletion; never destructive deletion.

---

## 4. Shared Technical Foundation

Share infrastructure, not business records:

- Versioned templates and ordered sections/items.
- Immutable occurrence/run snapshots.
- Evidence/attachments, comments, timelines, audit.
- Optimistic concurrency.
- Notification/email outbox and recurrence preview.
- Import validation/error reports.
- Permission and exact-client-scope enforcement.
- Pagination, search, saved filters, and exports.

Keep occurrence/result tables and APIs separate so internal work cannot leak to the portal and UAT scoring cannot affect service-checklist completion.

## 5. Recommended Delivery Sequence

### Phase 1 — Recurring Service Checklists

Shared schema, permissions, versioned templates, occurrences, evidence, My Work/Team Board, schedule preview/generation, reminders, overdue escalation, reports, and exports.

### Phase 2 — Internal UAT

Templates, product/test structure, Excel import preview, immutable runs, execution, scoring, review, defect tickets, and PDF/Excel reporting.

### Phase 3 — Client Portal UAT

Exact-client portal access, mobile execution, evidence, submission, sign-off, notifications, secure report download, and server-side internal-content exclusion.

### Phase 4 — Analytics and controlled intelligence

Cross-run trends, recurring failure areas, product/module attention analysis, defect reconciliation, then optional evidence-grounded assisted summaries.

## 6. Acceptance Criteria

- Recurring occurrences and notifications are generated once despite retries/multiple workers.
- Required checklist items/evidence are server-validated before completion.
- Published template changes never alter existing occurrences/runs.
- UAT scoring is deterministic, transparent, and reproducible.
- Portal users see only assigned runs within exact client scope; internal content never leaks through APIs, exports, search, or notifications.
- Failed tests create traceable, idempotent defect tickets.
- Acceptance, retests, reports, and sign-offs preserve immutable history.
- Lists use server-side pagination and stable searchable identifiers.
- English, Arabic, RTL, dark mode, keyboard, and mobile behavior are covered.
- Every KPI drills down to authoritative records.

## 7. Recommendation

Implement **Recurring Service Checklists** first because it reuses existing scheduling and notification services and establishes the shared checklist foundation. Build **UAT & Test Management** second while preserving its separate portal lifecycle, scoring, defects, reporting, and sign-off controls.

## 8. Final Application Navigation

```text
Support Hub
├── Tickets
│   ├── All Tickets
│   ├── Saved Views
│   └── Pending Approvals
├── Operations
│   └── Service Checklists
│       ├── My Work
│       ├── Team Board
│       ├── Calendar
│       ├── Templates
│       ├── Schedules
│       └── Reports
├── UAT & Testing
│   ├── Dashboard
│   ├── UAT Runs
│   ├── Templates
│   ├── Defects
│   └── Reports
└── Client Portal
    └── UAT Testing
        ├── Assigned to Me
        ├── Completed Tests
        └── Reports
```

Navigation items are permission-driven. Hiding a navigation item is not authorization; every API and export must independently enforce permission and scope.

## 9. Final Data Design

### 9.1 Saved-view and layout changes

- `SavedView`: retain filter definition, owner, visibility, default flag, version, timestamps.
- `SavedViewLayout`: saved-view ID, layout type (`GRID`/`CARDS`), layout JSON, scope (`VIEW`/`GLOBAL`), version.
- Validate layout JSON against a server-owned allowlist of columns, lanes, groupings, and sort keys.
- Do not store translated labels; store stable codes.

### 9.2 Shared checklist definitions

Use reusable structural tables while keeping operational/UAT transactions separate:

- `ChecklistTemplate`: code, name, purpose, state, current version, active flag.
- `ChecklistTemplateVersion`: immutable version metadata, effective dates, publisher.
- `ChecklistSection`: version, title, order.
- `ChecklistTemplateItem`: section, stable item code, instructions, order, requirement/evidence configuration.
- `ChecklistItemProduct`: many-to-many product/module applicability.

Templates move through `DRAFT → PUBLISHED → RETIRED`. A published version is never edited in place.

### 9.3 Recurring service records

- `ServiceChecklistSchedule`: template/version selection policy, recurrence, timezone, clients, assignment policy, reminder/escalation policy, version.
- `ServiceChecklistScheduleClient`: exact selected clients.
- `ServiceChecklistOccurrence`: schedule, snapshot version, client, contract/product/location, owner/team, scheduled/due timestamps, status, progress, completion data.
- `ServiceChecklistOccurrenceItem`: immutable item snapshot plus result, evidence state, completion/waiver actor and time.
- `ServiceChecklistEvidence`: item, evidence type, protected attachment/reference, author, visibility.
- `ServiceChecklistEscalation`: level, reason, recipients, timestamps, acknowledgement.
- `ServiceDeliveryRecord`: client-facing service outcome created atomically from a completed occurrence.

### 9.4 Scheduled Service Ticket relationship

Each occurrence creates exactly one ticket with type **Scheduled Service**. Store `service_checklist_occurrence_id` as a unique relationship. The occurrence is the checklist authority; the ticket provides assignment, communication, visibility, worklogs, and customer-care integration.

- Occurrence creation and ticket creation occur in one transaction.
- One checklist item does not create one ticket.
- Failed items may create separate Incident/Problem/Change follow-up tickets.
- Use idempotency key `schedule_id + planned_occurrence_timestamp + client_id`.
- Cancelling a future occurrence cancels its Scheduled Service ticket with an audited reason.
- Completing the checklist resolves the parent ticket and creates the service-delivery record atomically.

### 9.5 UAT records

- `UatRun`: number, client, snapshot version, owner, dates, threshold, state, score, decision, version.
- `UatRunProduct`: selected products/modules.
- `UatParticipant`: user/contact, role, portal visibility, invitation state.
- `UatRunSection` and `UatRunCase`: immutable template snapshot.
- `UatCaseResult`: result, actual outcome, reason, tester, timestamps, version.
- `UatEvidence`: protected files/links/comments with internal/client visibility.
- `UatDefectLink`: case result and linked ticket with relationship type.
- `UatReview`: reviewer decision, comments, timestamp.
- `UatSignOff`: internal/client signer, decision, statement/version, timestamp.
- `UatReportRevision`: generated artifact, source snapshot hash, generation audit.
- `UatRetestCycle`: original failed result, retest result, cycle number.

All identifiers visible to users should use generated stable numbers such as `SCL-2026-000123` and `UAT-2026-000045`.

## 10. Final API Boundaries

### 10.1 Tickets and saved views

- `GET/PATCH/DELETE /saved-views/{id}`
- `POST /saved-views/{id}/update-from-current`
- `GET/PUT /saved-views/{id}/layouts/{layout_type}`
- `GET/PUT /users/me/ticket-layouts/{layout_type}`
- `POST /tickets/exceptions/preview` returns authoritative reasons before creation.
- Ticket creation accepts the preview version/token and re-evaluates inside the transaction.

### 10.2 Service checklists

- Template CRUD, clone, validate, publish, retire, and history endpoints.
- Schedule CRUD plus occurrence preview, activate, pause, and history endpoints.
- Paginated occurrence list/detail.
- Explicit lifecycle actions: start, complete item, waive item, reassign, complete, cancel.
- Evidence upload/download through the existing protected attachment service.
- Reports expose filtered rows and separate export jobs.

### 10.3 UAT

- Template CRUD, clone, import preview/apply, publish, retire, export, history.
- Run create preview/apply, list/detail, participant management.
- Explicit run lifecycle actions instead of unrestricted status patching.
- Case-result update requires row version and validates evidence/reason requirements.
- Defect preview/create/link endpoints use idempotency keys.
- Submit, request changes, accept, conditional accept, reject, retest, and report-generation endpoints.
- Portal endpoints return dedicated portal response schemas; do not reuse internal schemas and hide fields in JavaScript.

All list endpoints require server pagination, bounded page size, allowlisted sorting, and indexed filtering.

## 11. Final UI Interaction Details

### 11.1 Tickets toolbar

Keep the complete toolbar mounted above both empty and populated results. Display an inline active-filter ribbon and a **View has unsaved changes** indicator when current filters/layout differ from the applied saved view.

**Update from Current Filters** opens a compact comparison dialog:

```text
Update “Critical Client Tickets”

Added       Product = PACS
Changed     Status: Open → In Progress
Removed     Assigned Engineer = Ahmed

[Cancel] [Save as New] [Update View]
```

### 11.2 Service checklist card

```text
SCL-2026-000123                 OVERDUE 2h
Alfa Scan · Weekly Infrastructure Check
Assigned: Engineer Name        Due: 14 Sep 10:00

██████████████░░░░  3 / 4 required items
Attention: Storage check failed

[Open Checklist] [Create Follow-up]
```

Use red only for overdue/failure, amber for due/blocked, green for successfully completed, and neutral/primary colors for scheduled work. Dark-mode contrast must meet WCAG AA.

### 11.3 Service checklist completion dialog

Show incomplete required items, missing evidence, waived items, warnings, linked follow-ups, service provided, and client-visible summary. Disable completion with a precise reason until requirements pass. Confirmation resolves the Scheduled Service ticket and records service delivery.

### 11.3.1 Cards board, lanes, and drag actions

Service Checklists must support both Grid and Cards layouts. The Cards layout uses these authoritative lanes:

- **Scheduled** — future occurrences not yet due.
- **Due Today** — due during the current server-local day.
- **In Progress** — work has started.
- **Blocked** — waiting for an internal dependency or client action.
- **Overdue** — incomplete after the due timestamp.
- **Completed** — completed on time or late, with a visible outcome badge.
- **Cancelled** — optional hidden-by-default historical lane.

Each card shows occurrence number, client, template, product/location, assignee, scheduled/due time, required-item progress, warnings, evidence gaps, and escalation state. Card and Grid layouts share the same server filters and saved-view rules.

Dragging is a workflow action, not a cosmetic reorder:

| Drag destination | Server action |
|---|---|
| Scheduled/Due Today → In Progress | Starts the occurrence and linked Scheduled Service ticket. |
| In Progress → Blocked | Opens a dialog requiring Internal or Client reason and expected follow-up time. |
| Blocked → In Progress | Resumes work and records who resumed it. |
| Any active lane → Cancelled | Requires cancellation permission and reason. |
| In Progress/Overdue → Completed | Runs completion preview and opens the completion dialog. |

The client updates the card optimistically only after the transition is accepted. A version conflict, permission failure, or validation error restores the card to its original lane and reloads authoritative data.

#### Complete-on-drop behavior

Dropping into **Completed** must not silently falsify checklist evidence. The dialog provides **Complete all eligible remaining tasks**:

- It may bulk-complete ordinary confirmation/checkbox items.
- It cannot automatically complete items requiring files, measured values, comments, links, approval, or other evidence.
- Failed or blocked items require a follow-up ticket, approved waiver, or permitted risk disposition.
- The dialog lists every item that will be completed and every item still preventing completion.
- Confirmation revalidates all items, evidence, version, and permission inside one database transaction.
- Successful confirmation completes the occurrence, resolves its Scheduled Service ticket, and creates the Service Delivery Record atomically.

#### Next scheduled occurrence

After successful completion, the system ensures that the next recurrence exists exactly once:

- If already generated, display it as **Next scheduled** without creating a duplicate.
- If the generation horizon has not created it yet, calculate and create exactly the next occurrence using the schedule timezone and recurrence rule.
- The next occurrence remains **Scheduled** until its planned start/due window; it does not automatically become In Progress.
- Assignment is resolved using the schedule policy, and the next occurrence receives its own checklist snapshot and Scheduled Service ticket.
- Paused, expired, or inactive schedules do not generate a next occurrence.
- The completion response returns the next occurrence number/date so the UI can offer **Open Next Scheduled Checklist**.

An additional permission-controlled **Start Next Now** action may move the next occurrence to In Progress early. It requires a reason and preserves its original scheduled/due timestamps for accurate service-compliance reporting.

### 11.3.2 Client-responsible checklist items

Some checklist items are the responsibility of the client's IT team rather than the assigned support engineer. Responsibility is configured per template item and may also be changed on an occurrence with permission.

Responsibility values:

- **Millensys Responsible** — normal scheduled engineer work and required for internal completion.
- **Client Responsible** — action belongs to the client's IT team and is excluded from engineer workload/scheduling requirements after a documented handoff.
- **Shared Responsibility** — both parties have required actions; each side is tracked independently.

Marking an occurrence item **Client Responsible** is a disposition, not a false completion. Open a required dialog containing:

- Client contact/person responsible.
- Handoff date and time.
- Required action and expected completion date, if known.
- Engineer note.
- At least one mandatory evidence attachment: email (`.eml`/`.msg` or governed email reference), screenshot/image, PDF, or document.
- Client-visible/internal visibility selection, constrained by permission.

The server rejects the action without valid evidence. Store the evidence, actor, timestamp, original responsibility, new responsibility, client contact, reason, and version in immutable audit history.

Item states for this workflow:

- `PENDING_CLIENT_HANDOFF`
- `CLIENT_RESPONSIBLE`
- `CLIENT_CONFIRMED`
- `CLIENT_DECLINED`
- `RETURNED_TO_ENGINEER`

Once a valid handoff is recorded, a Client Responsible item:

- Does not block completion of the engineer's scheduled checklist.
- Is excluded from required internal-task completion and engineer lateness calculations.
- Is not counted as Passed or Completed.
- Is reported separately as **Transferred to Client Responsibility**.
- Remains visible in the checklist summary, Service Delivery Record, Client Profile, and authorized reports.
- May generate a client follow-up due date and notification without creating another recurring engineer schedule.

If the complete checklist template is defined as **Client Managed / Unscheduled**, it does not generate recurring occurrences or Scheduled Service Tickets. It is created manually or assigned to the client as an independent checklist/run. Its items may have target dates and reminders, but they remain outside internal scheduling, engineer workload, overdue-service, and service-commitment calculations.

If only selected items are Client Responsible, the parent checklist remains scheduled; only those items are removed from internal scheduling/completion requirements after evidence-backed handoff.

The completion dialog must separate completed Millensys tasks, incomplete blocking Millensys tasks, Client Responsible tasks with evidence, Client Responsible tasks missing evidence, and Shared tasks with the outstanding party.

### 11.4 UAT run card

```text
UAT-2026-000045                       IN PROGRESS
Client: GDR                 Product: PACS / Viewer
Progress 72%     Score 91%     Required threshold 90%
2 Failed · 1 Blocked · 3 Not Tested
Due 20 Sep 2026

[Continue Testing] [View Defects]
```

### 11.5 UAT attention panel

Group attention by Critical Failures, Blocked, Missing Required Evidence, Not Tested, and Open Defects. Each count opens the exact cases. Do not present a score without its denominator and excluded N/A weight.

### 11.6 Portal experience

Use plain client-facing language and omit internal assignment/escalation/audit details. Show test instructions, expected result, client-visible evidence, result controls, comments, submission, sign-off, and downloadable approved reports. Clearly identify whether a draft is saved, submitted, or returned for changes.

## 12. Scheduled Jobs and Reliability

Use a database-backed distributed lock so multiple API workers cannot generate the same work twice.

Required jobs:

- Generate checklist occurrences within a configurable future horizon.
- Mark due/overdue occurrences.
- Send reminder and escalation events.
- Reconcile occurrence and Scheduled Service ticket state.
- Mark UAT runs approaching/overdue deadlines.
- Queue UAT invitations, reminders, review notices, and report jobs.

Every event uses a durable outbox and semantic deduplication key. A worker crash after commit and before delivery must be safely retryable. Store job run time, result counts, duration, and error correlation ID for operational monitoring.

## 13. Customer Care and Service Measurement

Scheduled checklist work affects the client through a **Service Delivery Record**, not by inflating incident counts.

### 13.1 Client Profile additions

Add a **Service Delivery** tab showing:

- Upcoming and overdue scheduled services.
- Delivered services and completion reports.
- On-time/late status.
- Products, locations, and responsible engineers.
- Warnings, waivers, follow-up tickets, and client acknowledgement.

### 13.2 Measures

- `Planned Services`: occurrences due in the reporting period.
- `Delivered Services`: occurrences completed with a delivery record.
- `On-time Rate`: delivered by due time / delivered services.
- `Missed Rate`: overdue and incomplete / planned services.
- `Checklist Compliance`: completed required items / applicable required items.
- `Evidence Compliance`: satisfied evidence requirements / applicable evidence requirements.
- `Follow-up Rate`: occurrences creating corrective tickets / delivered services.
- `Repeat Attention`: repeated failed/warning item codes for the same client/product.

Show scheduled-service commitment separately from incident/request SLA. A transparent client-health model may consume both, but must expose their individual contributions and evidence.

## 14. Detailed Business Rules

### 14.1 Checklist rules

- Schedule edits affect only ungenerated future occurrences unless an authorized user explicitly regenerates with preview and reason.
- Removing an assignee never deletes work; it moves the occurrence to an unassigned exception queue.
- Required failed items can complete only when a follow-up/risk disposition policy permits it.
- Waiver requires permission, reason, and optionally reviewer approval.
- Client-visible summaries exclude internal notes and recipient details.
- Attachments follow existing size, type, authorization, and retention controls.
- Changing an item to Client Responsible requires evidence and never records the item as successfully completed.
- Evidence-backed Client Responsible items are excluded from engineer completion and schedule compliance, but remain a separately reported customer-care responsibility.
- Entire Client Managed / Unscheduled checklists do not generate recurring occurrences or Scheduled Service Tickets.

### 14.2 UAT rules

- Only invited participants with client scope can execute a run.
- Result changes after submission require Changes Requested or Reopen action.
- Critical failed cases prevent Pass regardless of numeric score.
- N/A requires a reason and optional reviewer approval.
- A case cannot pass when mandatory evidence is missing.
- Conditional acceptance records conditions, owner, due date, and linked defects.
- Client sign-off statement text/version is snapshotted at signing time.
- Generated reports use the same immutable result revision that was reviewed/signed.

### 14.3 Deletion rules

- Draft unused templates may be deleted with permission and audit.
- Published or referenced templates are retired, never hard-deleted.
- Schedules with history are deactivated.
- Occurrences, UAT runs/results, delivery records, evidence, sign-offs, and reports cannot be hard-deleted through normal APIs.

## 15. Notification Matrix

| Event | Primary recipient | Optional recipient | Channels |
|---|---|---|---|
| Checklist assigned | Engineer | Team leader | In-app, email |
| Checklist due soon | Engineer | — | In-app, email |
| Checklist overdue | Engineer | Team leader/profile | In-app, email |
| Checklist completed | Owner/reviewer | Client contact if visible | In-app, email |
| Failed item | Owner | Product/team lead | In-app, email |
| UAT invitation | Participant | Owner | In-app, email |
| UAT approaching due | Incomplete participants | Owner | In-app, email |
| UAT submitted | Reviewer | Owner | In-app, email |
| Changes requested | Participants | Owner | In-app, email |
| UAT accepted/rejected | Owner and participants | Client contacts | In-app, email |
| Defect status changed | UAT owner | Tester/client if visible | In-app, email |

Site settings control channel enablement and defaults. Access is rechecked at generation and link opening; notification possession never grants record access.

## 16. Indexing and Capacity Requirements

Create indexes around schedule/client/status/due date, occurrence owner/status/due date, UAT client/status/due date, case result/run/status, participant/user/run, and defect ticket links. Use narrow list projections; load item/evidence detail only when a record opens.

- Never return all occurrences, cases, clients, products, or users in one response.
- Perform scoring and dashboard aggregation in SQL or bounded queries.
- Generate large PDF/Excel exports asynchronously with progress and expiry.
- Keep attachments outside SQL Server; store protected metadata and object/file keys.
- Define evidence retention and backup capacity before enabling portal uploads.

## 17. Migration and Rollout Plan

1. Add additive nullable/versioned schema and permission catalog entries.
2. Seed Scheduled Service ticket type, statuses/mappings, and default settings idempotently.
3. Deploy APIs behind feature policies disabled by default.
4. Enable internal checklist templates for administrators only.
5. Pilot one template, one client, and a small engineer group.
6. Validate generation, reminders, completion, tickets, client metrics, and exports.
7. Enable internal UAT pilot and validate scoring/defect/report reconciliation.
8. Enable Client Portal UAT only after security and visibility tests pass.
9. Monitor job failures, overdue counts, notification retries, storage, and query performance.

Existing ticket/onboarding checklists remain unchanged. No automatic conversion should occur without an explicit migration specification and approved mapping.

## 18. Verification Matrix

### Backend

- Permissions and exact client/department/profile scope.
- Template immutability, cloning, publishing, retiring, and optimistic conflicts.
- Recurrence across timezone/DST, month ends, leap years, holidays, retries, and concurrent workers.
- Atomic occurrence/ticket creation and checklist/ticket completion.
- Required evidence, waiver, failure disposition, and follow-up idempotency.
- UAT scoring, N/A, critical failure, conditional acceptance, retest, and sign-off immutability.
- Portal response-field isolation and unauthorized identifier tests.
- Notification/outbox deduplication and retry.
- Clean and populated SQL Server migration rehearsal.

### Frontend

- Saved-view filter/layout restoration and update comparison.
- Empty Grid/Cards headers and In Progress lane regression.
- Desktop/mobile, English/Arabic, RTL, light/dark, keyboard, and screen-reader behavior.
- Template designer ordering and unsaved-change protection.
- Schedule/run preview versus created records.
- Offline/transient failure recovery without lost UAT drafts.
- Portal internal-content exclusion.

### Reporting reconciliation

- Dashboard counts equal filtered lists and exports.
- Service Delivery records equal completed eligible occurrences.
- UAT report score equals case-result evidence.
- Defect summaries equal linked ticket records and current statuses.
- Historical reports remain unchanged after later template/result revisions.

## 19. Definition of Done

An implementation phase is complete only when:

- Approved functional behavior and permissions are implemented server-side and in the UI.
- Audit, notification, localization, accessibility, dark mode, pagination, and exports are included—not deferred as cleanup.
- Database migrations are additive, retry-safe, and rehearsed against clean and populated SQL Server databases.
- Automated unit, API, concurrency, permission, portal-isolation, and frontend regression tests pass.
- Every dashboard/report measure reconciles to evidence.
- Deployment, rollback, seed, storage, backup, and smoke-test instructions are updated.
- A controlled pilot confirms real assignment, recurrence, evidence, notification, customer-care, scoring, and reporting behavior.

## 20. Final Product Decision

Use this final model:

1. Implement the six Tickets Page corrections first as a contained quality release.
2. Build the shared versioned checklist foundation and **Recurring Service Checklists**.
3. Represent every generated service occurrence as one **Scheduled Service Ticket** and produce a client **Service Delivery Record** at completion.
4. Keep scheduled-service compliance separate from ordinary support SLA and incident volume.
5. Build **UAT & Test Management** on the shared template/evidence foundation with separate transactional records and APIs.
6. Introduce Client Portal UAT only after internal workflow, scoring, reports, and server-side isolation are proven.
7. Add assisted summaries only after structured results are authoritative and stable.

No application code or database migration is included in this document. It is the final functional, UI, data, API, security, rollout, and verification blueprint for approval before implementation.
