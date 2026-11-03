# Business-Critical Enhancements Implementation Plan

Date: 24 August 2026  
Status: implementation-ready backlog specification  
Target: next version after immutable release `1.31.5`  
Database baseline: `0120_internal_ops_lifecycle`

## 1. Purpose

This plan converts five production/business notices into a coordinated implementation backlog:

1. Remove the effective 201-customer contract-link limit.
2. Make production password-reset email delivery reliable and observable.
3. Redesign Internal Operations around the shared workforce calendar, reusable templates, rosters, and governed field visits.
4. Make Today's Tickets predictable and add permission-controlled fast actions, including today's unassigned queue.
5. Implement the employee Onboarding module described in `docs/Backlog/Onboarding.md`.

The work must preserve tenant/client scope, contract entitlement, ticket visibility, audit history, shift conflicts, and notification security. Search or page limits must never make a valid business record unreachable.

Related detailed references:

- `docs/Backlog/Onboarding.md`
- `docs/Backlog/Contract Configuration and SLA Master Data Implementation Plan.md`
- `docs/Completed/Plans/MASTER_DEVELOPMENT_PLAN V1.md`

This plan establishes current delivery priority and integration boundaries. The related documents remain useful domain references where they do not conflict with the confirmed current code state recorded here.

## 2. Confirmed current-state findings

| Notice | Confirmed current behavior | Business impact |
|---|---|---|
| Contract customers | `ContractsPage.tsx` loads `/clients?limit=200`. The primary customer is separately retained, producing the observed maximum of approximately 201 linked customers. | A contract cannot be reliably linked to all 413 customers through the current selector. |
| Contract selection API | The backend already exposes `client-selection/preview` and `client-selection/apply` with `EXPLICIT` and `ALL_MATCHING` modes. The main contract customer UI does not use them. | A safe server-side solution exists but is not connected to the production workflow. |
| Forgot password | A reset token is created only for an active user whose email domain is allowed. An email outbox item is created only when `SMTP_ENABLED=true`. The public response is intentionally generic. | Misconfiguration, blocked domains, scheduler failure, SMTP failure, or dead-letter delivery all look like success to the requester. |
| Internal Operations | Operation templates and monthly application already exist. The Internal Operations page is card/list-oriented. The Shift Calendar already combines shifts, internal operations, and visits. | Capabilities are fragmented and the primary Operations UX does not expose a calendar/roster workflow comparable to Shift Planning. |
| Field visits | Generic Internal Operation templates explicitly reject `OUTDOOR_VISIT`. Visit Operations owns contract entitlement, occurrence scheduling, allowance consumption, completion, and evidence. | Allowing generic templates to bypass Visit Operations would violate contract governance. |
| Tickets today | The Tickets page initializes `created_from` and `created_to` to today only when there are no URL parameters. Saved views, navigation state, or other tabs can remove that behavior. | “All tickets” is not guaranteed to mean today's tickets on every entry path. |
| Unassigned tickets | The API already supports `unassigned_only`. The page can display an unassigned chip, but there is no prominent, permission-governed ribbon action for today's unassigned work. | Dispatchers and engineers cannot reach the operational queue quickly and consistently. |
| Onboarding | The detailed functional concept exists, and user reporting-line cycle validation already exists. No dedicated onboarding route, permissions, entities, or UI currently exists. | Onboarding remains a document rather than an executable workflow. |

## 3. Delivery priorities

### Wave A — Critical production corrections

- Unlimited/paginated contract customer selection.
- Password-reset delivery configuration, processing, and administrator diagnostics.

These directly affect current customers and account recovery and should be released first as a corrective release.

### Wave B — Ticket operational ribbon

- Stable Today's Tickets behavior.
- Today's Unassigned and other permission-controlled quick actions.
- Optional atomic “Take next ticket” workflow.

### Wave C — Unified Operations Planner

- Calendar-first Internal Operations UX.
- Flexible operation template application.
- Multi-row operation rosters.
- Contract-governed field-visit template preview/application.
- Unified engineer/department workload overview.

### Wave D — Employee Onboarding

- Checklist templates and assignments.
- Training materials and resource links.
- Newcomer/manager progress views.
- Shared organization-chart component.
- Notifications and administration.

Each wave must be independently deployable. Do not hold Wave A for the larger Operations or Onboarding work.

---

# 4. Contract customer linking without record limits

## 4.1 Required behavior

The contract customer workspace must support all 413 current customers and future growth without loading every client into one browser multi-select.

Replace the current single Autocomplete with a two-panel selection workspace:

```text
Available customers                         Linked customers
Search [________________]                   Search [________________]
413 matching                                201 currently linked

[ ] C0001 — Alpha Hospital                  C0201 — Delta Hospital [Remove]
[ ] C0002 — Beta Clinic                     C0202 — Gamma Center   [Remove]
...                                         ...

Previous  Page 1 of 9  Next                 Previous  Page 1 of 5  Next

[Select page] [Select all 413 matching]     [Remove page] [Clear all]
```

Selection modes:

- `EXPLICIT`: selected customer IDs are stored explicitly.
- `ALL_MATCHING`: the server resolves the complete filtered result set, minus explicit exclusions.
- “Select page” affects only the loaded page.
- “Select all N matching” affects the server-side result, not only visible browser options.
- A confirmation preview must show matched, excluded, and final selected counts before applying all matching.

The contract's primary customer must remain linked. Clear/remove actions must not remove it without first changing the contract's primary customer through a separately governed workflow.

## 4.2 API design

Use the existing endpoints rather than sending hundreds of IDs unnecessarily:

- `POST /contracts/{contract_id}/client-selection/preview`
- `POST /contracts/{contract_id}/client-selection/apply`
- `GET /contracts/{contract_id}/clients`

Add/standardize a total-aware page endpoint for selection:

```http
GET /clients/page?search=clinic&active_only=false&limit=50&offset=0
```

Response:

```json
{
  "items": [{"id": 10, "code": "C0010", "name": "Example Clinic"}],
  "total": 413,
  "limit": 50,
  "offset": 0
}
```

All-matching intent:

```json
{
  "mode": "ALL_MATCHING",
  "search": null,
  "explicit_ids": [],
  "excluded_ids": [18, 25]
}
```

The preview response must include:

- `matched_count`
- `selected_count`
- `excluded_count`
- whether the primary customer is forced into the result
- inactive customer count
- customers already covered by a conflicting customer-specific active contract, if applicable

## 4.3 Backend rules

- Resolve `ALL_MATCHING` entirely in SQL.
- Never trust a browser-provided total.
- Revalidate every customer at apply time.
- Enforce the caller's contract and client scope.
- Preserve the primary customer.
- Apply additions/removals in one transaction.
- Retain current contract precedence rules.
- Audit mode, search, matched count, selected count, exclusion count, added IDs count, removed IDs count, and correlation ID.
- Avoid one SQL statement per customer; use set-based reads/inserts/deletes.
- Add indexes only if query-plan inspection shows they are required; the link-table uniqueness constraint remains authoritative.

## 4.4 Frontend rules

- Page size defaults to 50 and is not a functional limit.
- Selected rows persist while searching and paging.
- Display the server-reported total.
- Never render hundreds of selected customers as Autocomplete chips.
- The linked panel must be independently searchable and paginated.
- Show unsaved additions/removals distinctly.
- Require confirmation for “Select all matching” and “Clear all except primary.”
- Refresh the contract count and linked-client query after apply.

## 4.5 Acceptance criteria

- A contract can be linked to all 413 customers in one governed operation.
- Searching and selecting across multiple pages does not lose earlier selections.
- “Select all matching” selects records beyond the first 200.
- The primary customer cannot be accidentally removed.
- Two administrators editing the same contract cannot silently overwrite each other; use version/stale-selection validation.
- Contract details, Visit entitlements, ticket coverage, and financial statements recognize the complete linked set.
- Tests cover 413+ customers, inactive customers, exclusions, primary preservation, concurrent updates, and rollback on validation failure.

---

# 5. Reliable forgot-password email

## 5.1 Likely production failure paths

The public message must remain generic to prevent account enumeration. Administrators, however, need a precise internal reason. Current failure paths include:

- `SMTP_ENABLED=false`: token may be created, but no reset email event is queued.
- User email domain is not in `PASSWORD_RESET_ALLOWED_DOMAINS`: no token/event is created.
- Account is inactive or the entered username/email does not match.
- Scheduler is not running or its cycle is failing.
- SMTP host, port, TLS, username, password, sender, DNS, firewall, or certificate is invalid.
- Outbox item is retrying or dead-lettered.
- Recipient server quarantines/rejects the message after SMTP acceptance.
- `FRONTEND_BASE_URL` is wrong, producing a bad reset link even when delivery succeeds.

## 5.2 Configuration requirements

Production deployment must verify:

```text
SMTP_ENABLED=true
SMTP_HOST=<approved relay>
SMTP_PORT=<relay port>
SMTP_USERNAME=<if required>
SMTP_PASSWORD=<protected secret>
SMTP_FROM_ADDRESS=<approved sender>
SMTP_FROM_NAME=Millensys Support Hub
SMTP_USE_TLS=true/false according to the relay
FRONTEND_BASE_URL=https://millensysonline.net/SupportHub
PASSWORD_RESET_ALLOWED_DOMAINS=<approved domains>
```

The production-readiness check must report configuration state without returning secret values.

## 5.3 Required behavior

Public forgot-password response:

```text
If an active account matches, password reset instructions will be sent.
```

This response remains the same for existing, missing, inactive, or blocked-domain accounts.

Internal behavior for an eligible account:

1. Revoke unused reset tokens.
2. Create one new hashed, expiring reset token.
3. Create `PASSWORD_RESET_REQUESTED` authentication evidence.
4. Queue one `PASSWORD_RESET_EMAIL` outbox event regardless of scheduler timing.
5. Let the singleton background processor claim and deliver it.
6. Record delivery attempt, status, sanitized failure category, timestamps, and retry time.
7. Stop after the configured maximum attempts and expose dead-letter status to administrators.

If SMTP is disabled in production, the request should still remain enumeration-safe, but the server must emit a high-severity structured log/operational health warning. Prefer failing the production-readiness check before users encounter it.

## 5.4 Administrator diagnostics

Extend System Operations → Email with:

- SMTP enabled/configured indicator.
- Last successful SMTP test.
- Scheduler enabled/running/last completed/last error.
- Pending, retrying, dead, skipped, and sent email counts.
- Password-reset deliveries filtered by recipient, requested time, and status.
- “Retry delivery” permission-controlled action.
- “Send test email” action using the configured sender.
- Sanitized error category such as DNS, authentication, TLS, connection refused, timeout, recipient rejected, or unknown.

Never display reset tokens, SMTP passwords, full stack traces, or sensitive connection strings.

## 5.5 Security and rate limiting

- Keep reset tokens hashed at rest.
- Keep the generic public response.
- Rate-limit per normalized login and source IP.
- Suggested initial limits: 5 requests per account per 30 minutes and 20 per IP per 30 minutes, configurable.
- A repeated request invalidates older unused tokens only when a new eligible token is actually created.
- Audit administrative retries and SMTP tests.
- Do not disclose whether the email domain was blocked.

## 5.6 Acceptance criteria

- An eligible production user receives a working link using `/SupportHub/reset-password`.
- The link expires and cannot be reused.
- SMTP disabled, domain blocked, inactive user, missing user, retry, and dead-letter paths are covered by tests.
- Administrators can see why an eligible message was not delivered without seeing secrets or tokens.
- A scheduler restart processes pending reset emails exactly once.
- Public responses remain indistinguishable across account states.

---

# 6. Unified Internal Operations Planner

## 6.1 Design principle

There must be one workforce calendar surface, not separate competing calendars.

The current Shift Calendar already combines:

- shifts;
- internal operations;
- contractual field visits.

Internal Operations should reuse the same calendar component and date navigation, with an Operations-focused default filter. The `/internal-operations` route becomes the Operations Planner while `/shifts` remains the Shift Planner. Both are views over the same scheduled workforce timeline.

## 6.2 Proposed workspace

```text
Operations Workspace

[Calendar] [Operations] [Templates] [Rosters] [Types & Settings] [Reports]

Calendar filters:
Department | Engineer | Operation type | Client | Status | Source
Day | Week | Month | Previous | Today | Next
```

Calendar cards use stable source colors:

- Shift: blue
- Internal operation: purple/type color
- Contract field visit: orange
- Conflict: red outline
- Pending approval: amber
- Completed: muted/green indicator

Clicking a calendar item opens the authoritative detail workflow for its source. A field visit opens Visit Operations, not a generic Internal Operation editor.

## 6.3 Reusable operation templates

Templates already exist and should be expanded rather than replaced.

Template fields:

- Name and generated stable code
- Department scope
- Operation type
- Default title
- Default start/end time and cross-midnight behavior
- Default location/meeting link
- Default purpose/instructions
- Default status
- Required evidence flags
- Default assignee strategy: choose at apply time, fixed engineers, department members, or role placeholder
- Date-selection defaults
- Active/inactive

Applying a template must support the same three date modes as Shift Planning:

- Monthly pattern: month + Weeks 1–4 + weekdays
- Specific dates
- Date range + weekday filtering

Preview must show exact dates, engineer-operation count, overlaps, approval requirements, visit entitlement results, and records that will be skipped.

## 6.4 Operation rosters

Add multi-row reusable rosters similar to Shift roster templates. Each row is independent:

- operation type;
- weekday/date behavior;
- Weeks 1–4 or flexible date mode at apply time;
- start/end;
- location;
- title/instructions;
- one or multiple engineers or an apply-time placeholder;
- optional client/visit placeholder;
- required evidence/approval inherited from the operation type.

Example roster:

| Row | Day | Activity | Time | Engineers |
|---|---|---|---|---|
| 1 | Sunday | WFH | 09:00–17:00 | Engineer A |
| 2 | Tuesday | Team meeting | 10:00–11:00 | Support Department |
| 3 | Thursday | After-shift maintenance | 20:00–22:00 | Engineers B and C |

Suggested new entities:

- `InternalOperationRosterTemplate`
- `InternalOperationRosterRow`
- `InternalOperationRosterRowAssignee`

Use stable codes, unique department/code constraints, display order, active state, audit history, and protected deletion when policy requires retention.

## 6.5 Contractual field-visit governance

Do not remove the current protection that blocks generic `OUTDOOR_VISIT` templates. Replace it with an explicit governed path.

Operation types already expose `visit_behavior` (`NONE`, `OPTIONAL`, `REQUIRED`). Apply these rules:

- `NONE`: create normal internal operations; client is optional only when the type supports it.
- `OPTIONAL`: if a client/visit is selected, run Visit governance; otherwise create an internal activity.
- `REQUIRED`: require client, visit type, and contract entitlement; no generic operation may be created.

Field-visit template application flow:

1. Select client(s), contract/entitlement where ambiguity exists, and visit type.
2. Resolve active contracts for every selected client and target date.
3. Validate visit entitlement period, allowed quantity, consumed/reserved occurrences, visit type, client scope, and contract status.
4. Preview eligible dates and failures by client/date.
5. Create/reserve governed `ClientVisitOccurrence` records through the Visit service.
6. Create/link the Internal Operation and generated visit shift through existing visit scheduling logic.
7. Consume entitlement only through the existing completion/consumption policy; do not double-consume during template application.
8. Preserve the unique link between an operation and a visit occurrence.

If 20 requested visit dates include 3 outside contract coverage and 2 without allowance, preview must show 15 eligible and 5 blocked with exact reasons. The user chooses whether to apply only eligible records or cancel. Applying blocked visits through an override requires a dedicated entitlement-override permission and audited reason; `internal_operation.manage` alone is insufficient.

## 6.6 Unified conflict and workload checks

Preview and create must check:

- overlapping shifts;
- other internal operations;
- field visits;
- approved leave/absence if available;
- cross-midnight spans;
- inactive engineers;
- department membership and manager scope;
- maximum planned hours policy, if configured.

The Operations Planner should show per engineer/department:

- scheduled shift hours;
- internal-operation hours/count;
- visit hours/count;
- after-hours count;
- overlapping/conflicting items;
- unassigned operations/visits;
- available-now indicator using the existing workforce definition.

## 6.7 Permission model

Recommended granular permissions:

- `internal_operation.view`
- `internal_operation.create`
- `internal_operation.edit.own`
- `internal_operation.edit.department`
- `internal_operation.assign`
- `internal_operation.transition`
- `internal_operation.complete`
- `internal_operation.template.view`
- `internal_operation.template.manage`
- `internal_operation.roster.view`
- `internal_operation.roster.manage`
- `internal_operation.apply`
- `internal_operation.conflict_override`
- `internal_operation.approve`
- existing `visit.entitlement.view/manage`
- new or existing dedicated visit entitlement override permission

`internal_operation.manage` can temporarily map to the granular rights during migration, but endpoint authorization should ultimately use the narrow rights.

## 6.8 Acceptance criteria

- Internal Operations opens with a usable day/week/month calendar.
- The same operation appears consistently in Internal Operations and Shift Calendar.
- Templates support monthly, specific-date, and date-range application.
- Rosters can generate mixed activities for multiple engineers.
- Preview reports exact conflicts and does not silently overwrite schedules.
- A contractual field visit cannot be created without valid entitlement or an authorized audited override.
- Visit allowance is never double-consumed.
- Operation/visit/shift links remain navigable and auditable.
- Department and engineer workload totals match the underlying calendar records.

---

# 7. Tickets Today and permission-controlled fast-action ribbon

## 7.1 All Tickets default contract

When the user opens the All Tickets tab without explicitly choosing another date range, it must show tickets created today in the user's configured/business timezone.

Rules:

- `created_from=today`
- `created_to=today`
- The date fields remain visible and editable.
- Changing the date range is remembered for the current navigation session.
- Returning from ticket detail preserves the current filters.
- Reset Filters restores today's range, not an unbounded query.
- Switching from Escalations, Handovers, or Approvals back to All Tickets restores the last All Tickets range; if none exists, use today.
- A saved view with an explicit date policy may override the default only when the user intentionally opens/makes that saved view default.
- Define saved-view date behavior as either fixed dates or a relative preset (`TODAY`, `YESTERDAY`, `LAST_7_DAYS`, `THIS_MONTH`, `CUSTOM`). Avoid silently saving today's literal date as a permanent default.

Backend date boundaries continue using the requester/business timezone and half-open UTC intervals.

## 7.2 Fast-action ribbon

Place a compact ribbon below the Tickets tabs:

```text
[Today's tickets] [Today's unassigned] [My queue] [Due soon] [Breached]
[Take next unassigned] [Create ticket] [Bulk assign]
```

Every action must:

- be visible only with its UI permission;
- still enforce authoritative backend ticket visibility/action permission;
- never broaden client/team/department scope;
- display an active state when its filter is applied;
- clear only conflicting filters, not unrelated user choices;
- reset paging to page 1;
- update the URL so refresh/back navigation is predictable.

## 7.3 Today's unassigned

“Today's unassigned” is a view action:

```text
created_from = today
created_to = today
unassigned_only = true
```

Define unassigned as `assigned_user_id IS NULL`. Team routing may still exist and should be displayed. Optionally add a second filter for “no engineer and no team” if dispatchers need completely unrouted tickets.

Recommended permission: `ticket.quick_action.unassigned_today`. This controls ribbon visibility only; ticket visibility scope remains enforced by existing `ticket.view.*` rights.

## 7.4 Take next unassigned ticket

If “get a ticket” means claim work rather than only display it, add a separate atomic action:

```http
POST /tickets/claim-next
```

Request:

```json
{
  "date_policy": "TODAY",
  "team_id": null,
  "reason": "Claimed from today's unassigned ribbon"
}
```

Selection order should be deterministic and approved by operations, initially:

1. eligible visible tickets only;
2. pending entitlement approval excluded;
3. highest priority (`P1` to `P4`);
4. breached before due-soon before normal;
5. oldest created ticket first;
6. ID as final tie-breaker.

The claim must be atomic on SQL Server so two engineers cannot receive the same ticket. Revalidate assignment eligibility, support team membership, client scope, status, and version within the transaction. Record assignment history, audit evidence, and notifications.

Recommended permission: `ticket.claim.unassigned`. Do not infer it from view permission. `ticket.assign.self` remains an additional required capability unless the new permission explicitly incorporates it by policy.

## 7.5 Suggested quick-action permissions

- `ticket.quick_action.today`
- `ticket.quick_action.unassigned_today`
- `ticket.quick_action.my_queue`
- `ticket.quick_action.due_soon`
- `ticket.quick_action.breached`
- `ticket.claim.unassigned`
- existing `ticket.create`
- existing `ticket.assign.team` for Bulk Assign

Profile assignment should be explicit and documented. Administrators can configure which ribbon actions each profile sees.

## 7.6 Acceptance criteria

- Fresh All Tickets navigation shows today's tickets.
- Users can change dates and return from detail without losing them.
- Today's Unassigned works with more than one page and respects visibility scope.
- Users without an action permission do not see it and receive 403 if calling its endpoint.
- Claim Next cannot double-assign under concurrency.
- Saved relative views remain relative on future days.
- Tabs do not leak or unexpectedly erase their independent filter state.

---

# 8. Employee Onboarding module

## 8.1 Scope and navigation

Implement the approved concept from `docs/Backlog/Onboarding.md` as a lightweight onboarding organizer, not an LMS.

Route:

```text
/onboarding
```

Normal-user tabs:

- My Checklist
- Training Materials
- Department Hierarchy

Authorized management tabs:

- Newcomer Progress
- Checklist Templates
- Manage Materials
- Categories

The sidebar entry is visible when the user has any onboarding view permission.

## 8.2 Data model

### `OnboardingChecklistTemplate`

- `id`
- generated stable `code`
- `name`
- `description`
- optional `department_id`
- optional `profile_id`
- `version`
- `is_active`
- created/updated timestamps and actor IDs

### `OnboardingChecklistTemplateItem`

- `id`
- `template_id`
- `title`
- `description`
- `display_order`
- `is_required`
- optional `training_material_id`
- `due_after_days`
- `is_active`

### `UserOnboarding`

- `id`
- `user_id`
- `template_id` for provenance
- `template_code_snapshot`
- `template_name_snapshot`
- `template_version_snapshot`
- `start_date`
- calculated/optional `target_completion_date`
- `status`: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`
- assigned by/at
- completed by/at
- cancellation reason
- optimistic `version`

### `UserOnboardingItem`

This is a snapshot, not a live template reference for content:

- `id`
- `user_onboarding_id`
- optional source `template_item_id`
- title/description/display order snapshots
- required snapshot
- due date
- optional material reference and material-title snapshot
- status: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `SKIPPED`
- started/completed/skipped timestamps
- completed/skipped actor
- skip reason
- optional newcomer note and manager note
- optimistic `version`

### `TrainingMaterialCategory`

- `id`, generated `code`, `name`, description, display order, active

### `TrainingMaterial`

- `id`, category ID, title, description, required flag, display order, active

### `TrainingMaterialResource`

- `id`
- `training_material_id`
- resource name
- resource type: `PDF`, `SHAREPOINT_DOCUMENT`, `SHAREPOINT_FOLDER`, `YOUTUBE`, `KNOWLEDGE_BASE`, `MICROSOFT_LEARN`, `EXTERNAL_URL`, `OTHER`
- URL
- display order
- active

Use HTTPS URL validation in production. Store links only; do not duplicate hosted content.

## 8.3 Assignment workflow

From User Create/Edit and Onboarding management:

1. Select active newcomer.
2. Select an eligible active checklist template.
3. Select start date.
4. Preview generated items and due dates.
5. Confirm assignment.
6. Create `UserOnboarding` and item snapshots in one transaction.
7. Notify the newcomer.

Default policy should allow one active onboarding plan per user. Reassignment requires completion/cancellation or an explicit authorized replacement action with reason.

Changing a template later must not modify assigned snapshots. A separate “Upgrade onboarding plan to template version” action may be considered later and must never be automatic.

## 8.4 Checklist behavior

- First item interaction changes the plan from Pending to In Progress.
- Newcomers may start/complete their own items.
- Required items cannot be skipped by a normal user.
- Managers may skip an item only with permission and a reason.
- Overall progress is completed items divided by non-skipped applicable items; also display required-item completion separately.
- The plan completes only when every required item is Completed and all optional items are Completed or Skipped.
- Reopening a completed item reopens the overall plan and is audited.
- “Open Material” navigates to the material detail; resource links open in a new tab with safe `noopener,noreferrer` behavior.

## 8.5 Training materials

- Search by title/description.
- Filter by category, required, and active.
- Display one card per topic with all its resources.
- Reorder categories, materials, and resources.
- Prevent hard deletion when historical checklist snapshots reference a material; deactivate instead.
- Knowledge Base resources should link to the internal article route when possible.

## 8.6 Shared organization chart

Do not create onboarding-specific reporting tables.

Use the existing authoritative sources:

- current department membership/history;
- `UserReportingLine` / Reports To;
- department organization hierarchy;
- user profile/avatar/job title.

Build one reusable organization-chart component and one backend hierarchy projection used by:

- Administration → User Hierarchy
- Onboarding → Department Hierarchy

Capabilities:

- user cards with avatar, name, job title, department, and profile summary;
- connector lines;
- zoom, pan, fit screen;
- expand/collapse;
- search and focus user;
- department/profile/active filters;
- read-only onboarding mode;
- optional Open User action in administration mode.

Existing reporting-line cycle validation remains authoritative. Add regression tests for self-reporting, direct cycles, long cycles, inactive managers, and effective-date projections.

## 8.7 Manager progress

Provide a paginated/searchable progress table:

| Newcomer | Template | Start | Due | Required | Overall | Status | Overdue |
|---|---|---|---|---|---|---|---|

Scope rules:

- Direct manager: direct reports.
- Department manager/head: authorized department descendants.
- HR/onboarding administrator: configured organization scope.
- Normal user: own plan only.

Clicking a row opens the employee checklist in manager read/review mode.

## 8.8 Notifications

Use the existing Notification/EventOutbox pipeline:

- onboarding assigned;
- task due tomorrow/configurable lead time;
- task overdue;
- plan completed;
- manager notification for overdue required tasks.

Use stable deduplication keys so recurring scheduler cycles cannot send duplicates. Email delivery follows global notification preferences and the hardened email pipeline; in-app notification remains authoritative.

## 8.9 Permissions

- `onboarding.view.own`
- `onboarding.item.update.own`
- `onboarding.hierarchy.view`
- `onboarding.material.view`
- `onboarding.progress.view.team`
- `onboarding.progress.view.department`
- `onboarding.assign`
- `onboarding.item.override`
- `onboarding.template.manage`
- `onboarding.material.manage`
- `onboarding.category.manage`

User/reporting-line edits continue to require existing user/organization management permissions.

## 8.10 API outline

```text
GET    /onboarding/me
GET    /onboarding/{plan_id}
POST   /onboarding/assign
POST   /onboarding/{plan_id}/cancel
PATCH  /onboarding/{plan_id}/items/{item_id}
GET    /onboarding/progress

GET    /onboarding/templates
POST   /onboarding/templates
PATCH  /onboarding/templates/{id}
DELETE /onboarding/templates/{id}          # deactivate/protected delete

GET    /onboarding/material-categories
POST   /onboarding/material-categories
PATCH  /onboarding/material-categories/{id}

GET    /onboarding/materials
POST   /onboarding/materials
PATCH  /onboarding/materials/{id}
POST   /onboarding/materials/{id}/resources
PATCH  /onboarding/material-resources/{id}
DELETE /onboarding/material-resources/{id}

GET    /organization/people-tree?department_id=&active_only=&as_of=
```

## 8.11 Acceptance criteria

- An administrator can assign a versioned checklist snapshot to a newcomer.
- Later template edits do not alter the assigned plan.
- A newcomer can see progress, open materials, and complete permitted items.
- Required items govern plan completion.
- Managers see only authorized newcomer progress.
- Material topics support multiple external/internal resources.
- The Onboarding and User Hierarchy pages render from the same reporting data/component.
- Reporting cycles remain impossible.
- Due/overdue notifications are deduplicated and audited.
- No external content is copied into SupportHub merely to support onboarding.

---

# 9. Migration and compatibility strategy

## 9.1 Wave A

Contract selector and password-reset observability should prefer existing tables/endpoints. Add schema only if rate-limit persistence or delivery diagnostics cannot be expressed through current authentication events, outbox, and email-delivery records.

## 9.2 Wave B

Relative saved-view date presets may require an additive column such as `date_policy_json`. Preserve existing fixed filter JSON and interpret it as `CUSTOM` for backward compatibility. Claim-next requires no new ticket table if assignment history and audit records remain sufficient.

## 9.3 Wave C

Add operation roster tables and any template governance fields additively. Backfill existing templates as normal internal templates with `visit_behavior=NONE` unless their linked operation type says otherwise. Never reinterpret historical templates as contractual visits automatically.

## 9.4 Wave D

Add onboarding/category/material/template/assignment tables in one or more additive migrations. Seed permissions and initial material categories idempotently. Do not seed employee assignments.

Every migration must pass:

- clean SQL Server installation;
- upgrade from current production revision;
- SQLite test compatibility where supported;
- retry/idempotency expectations;
- rollback rehearsal through verified database restore, not blind downgrade.

---

# 10. Cross-cutting engineering requirements

## 10.1 Authorization

- UI permissions are presentation only; every API enforces permissions.
- Quick actions and templates never expand data visibility.
- Manager/department scope is calculated server-side.
- Contract/visit scope is revalidated at commit time.

## 10.2 Concurrency

- Use optimistic versions for contract selection, onboarding items/plans, templates, and roster edits.
- Use atomic SQL Server selection/locking for claim-next.
- Re-preview stale bulk selections before apply.

## 10.3 Audit

Record actor, action, entity, reason where required, before/after summary, counts, correlation ID, and timestamp. Avoid storing reset tokens, passwords, SMTP secrets, or unnecessary personal data in audit JSON.

## 10.4 Pagination and performance

- Every potentially large catalog is server-searchable and paginated.
- Never solve the contract problem by raising `limit=200` to another arbitrary number.
- Add query-count and 413/1,000-client regression tests.
- Calendar APIs query bounded date ranges and indexed time columns.
- Onboarding progress is paginated and does not load every checklist item for every user in the table endpoint.

## 10.5 Accessibility and UX

- All actions have text labels/tooltips and keyboard access.
- Active ribbon filters are visually and programmatically identifiable.
- Calendar information is also available in list/agenda form.
- Organization charts include a navigable alternative hierarchy list.
- Error messages identify actionable validation failures without leaking sensitive information.

---

# 11. Verification matrix

## Backend

- Contract all-matching selection over 413 and 1,000 clients.
- Explicit/page selection persistence and primary-client protection.
- Password reset eligibility, domain, SMTP disabled, outbox retry/dead/sent, rate limits, token expiry/reuse.
- Ticket today boundaries in Cairo timezone and daylight-saving-capable timezones.
- Quick-action permission/scope isolation.
- Concurrent claim-next test.
- Operation template three-mode date generation.
- Roster mixed rows, overlaps, department scope, cross-midnight behavior.
- Visit entitlement eligible/ineligible/allowance/period/override cases.
- Onboarding snapshot, progress, permissions, overdue scheduler, deduplication, reporting cycles.

## Frontend

- Contract pagination, cross-page selection, all-matching preview, exclusion, and large selected counts.
- Password-reset generic success and error-resilient pending state.
- Email diagnostics permission visibility.
- Operations calendar day/week/month and source navigation.
- Template and roster previews with conflicts.
- Ticket ribbon active states, URL persistence, today reset, and permission hiding.
- Onboarding newcomer, manager, and administrator views.
- Organization-chart keyboard/list alternative.

## Release gates

- Ruff, strict MyPy, full pytest.
- ESLint, full frontend tests, TypeScript, production build.
- Clean and populated SQL Server migration rehearsal.
- Self-contained packaged runtime commands.
- Manifest/version consistency and forbidden-file inspection.
- Production smoke: health, database health, login, forgot-password delivery, contract link count, ticket ribbon, operations calendar, onboarding assignment.

---

# 12. Definition of done

The combined backlog is complete only when:

- All 413 customers can be linked to one contract without browser catalog limits.
- An eligible user receives a working password-reset email and administrators can diagnose non-delivery safely.
- Internal Operations provides a calendar-first workflow, flexible templates, rosters, unified workload visibility, and governed contractual field visits.
- All Tickets reliably defaults to today, and each fast action is explicitly permission-controlled.
- The Onboarding module provides assigned checklist snapshots, training-resource organization, scoped progress, notifications, and the shared visual hierarchy.
- Existing authorization, entitlement, SLA, audit, notification, and conflict protections remain intact.
- Each wave has passed the full release gates and is delivered through a new immutable release artifact.
