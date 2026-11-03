# Problem, Major Incident, and Change Management

## Document purpose

This document defines how Problem Management, Major-Incident Management, and Change Request Management can be added to the existing Millensys Support Hub without replacing or weakening the current ticket workflow.

Status: implementation in progress. Phase 1 backend foundation is implemented through migration `0253_change_deployment_closure`.

## Implementation checkpoint — 2026-10-07

Implementation has resumed from this checkpoint. Continue from the ordered **Next implementation steps** below; do not recreate the completed database foundation or Change Request workspace.

### Work resumed after checkpoint

- The internal Problem portfolio is now available at `/problems`, with search, status and priority filters, ownership, linked-ticket count, open-task count, overdue-task warnings, and target-resolution visibility.
- The dedicated Problem workspace is now available at `/problems/{id}`. It supports investigation editing, lifecycle actions, comments, tasks, protected evidence upload/download, relationship views, and lifecycle history.
- Problem relationship actions are now available in the workspace for visible tickets, root-cause catalog entries, Change Requests, published Knowledge articles, and Knowledge draft generation from the workaround or permanent fix.
- Ticket Detail now includes a permission-scoped Problem card. Authorized users can open linked Problems, link an existing Problem, or create a new Problem using the Ticket as its source incident.
- Major Incident continues to reuse the existing `INCIDENT` request type; no separate Major-Incident request type or global Ticket status was added.
- The Major-Incident portfolio is now available at `/major-incidents`, including severity/status filters, commander, primary Incident ticket, affected-ticket and Problem counts, and overdue update indication.
- The commander workspace is now available at `/major-incidents/{id}` with lifecycle commands, situation editing, internal/client/restoration updates, affected-ticket linking, affected scope, Problem linkage/commitment, restoration gates, resolution, monitoring, PIR, and closure controls.
- Incident Ticket Detail now includes a Major-Incident card for permission-controlled declaration or opening the existing commander workspace.
- Major-Incident read APIs now expose complete detail, portfolio aggregation, updates, affected tickets, normalized scope, and linked Problems.
- Support Now now displays a permission-scoped active SEV1/SEV2 banner with direct commander-workspace links. It refreshes in the browser and does not add a scheduler or continuously scanning backend worker.
- The Problem follow-up commitment uses a named employee selector. Major-Incident scope editing uses catalog selectors for clients, products, services, and environments; module selection remains a catalog-ID field pending a product-aware module selector.
- Major-Incident product scope now drives a searchable multi-module selector; invalid modules outside the selected products are excluded when the scope is saved.
- Event-driven in-app notifications are created inside the same transaction for Problem assignment/status changes and Major-Incident declaration/status/update publication. Notifications target the relevant owners and primary-ticket participants, use direct workspace links and deduplication keys, and require no scheduled scanner.
- Problem and Major-Incident portfolios now use server-calculated management summaries across the full permission scope, including active, known-error/SEV1, overdue-task/update, unassigned, and PIR indicators.
- Permission-scoped Excel exports are available from both portfolios and include operational lifecycle, ownership, impact, resolution, and timing fields.
- Client Portal Ticket Detail now shows client-approved Major-Incident communications and published Problem workaround/permanent-fix Knowledge associated with that ticket.
- Portal disclosure is enforced server-side: only `CLIENT` incident updates and `PUBLISHED`, client-visible `CLIENT_PORTAL`/`BOTH` Knowledge within the ticket client scope are returned. Internal updates, current-status diagnostics, Problem narratives, drafts, evidence, and internal Knowledge are excluded.
- English and Arabic localization keys now cover the Problem and Major-Incident portfolios, Support navigation, the Support Now Major-Incident alert, and client-safe Portal advisory sections. Responsive wrapping and direction-isolated technical identifiers are applied to these additions.
- Focused frontend verification covers both localized service-management portfolios, localization parity, representative Arabic/RTL pages, and active SEV1 visibility in Support Now (19 tests passed). Existing RTL test `act(...)` warnings remain non-blocking cleanup work.
- The Problem and Major-Incident workspaces now localize their primary investigation/command sections, details, actions, lifecycle dialogs, evidence, relationships, and locale-aware dates in English and Arabic.
- Focused workspace tests verify Arabic Problem and Major-Incident rendering and LTR isolation of their technical identifiers. The combined workspace, portfolio, and localization slice passes 7 targeted tests and TypeScript compilation.
- Secondary workspace controls are now localized: Problem relationship types and guidance; Major-Incident update audiences, Problem commitment fields, affected-scope catalogs, link dialogs, and scope guidance.
- The localized Problem edit dialog is covered through its accessible dialog name and a save-action test that verifies the versioned update payload. Current focused results: 3 workspace tests and 5 localization/portfolio tests passed; TypeScript compilation passed.
- Workspace dialogs now autofocus their first meaningful input for keyboard operation while retaining Material UI focus trapping and focus restoration.
- Major-Incident client-safe publication is covered by a permission-scoped action test that verifies client content is sent in `client_message` and not `internal_message`.
- Client Portal advisory rendering is covered for translated Major-Incident communications, approved Problem Knowledge, the exact ticket advisory endpoint, and LTR isolation of `MI`/`PRB` identifiers.
- Major-Incident affected-ticket linking is covered through the localized selector and verifies the selected ticket ID, `AFFECTED` relationship, and optimistic version payload.
- Workspace accessibility coverage verifies initial dialog autofocus and focus restoration to the launching control after cancellation. Save paths retain payload verification independently of asynchronous query refresh focus.
- Full frontend regression passes: ESLint, 43 test files / 117 tests, TypeScript compilation, and the Vite production build. Existing bundle-size/static-import warnings and React test `act(...)` warnings remain non-blocking.
- Backend Ruff and Mypy pass across 201 source files. The full backend run produced 519 passes, one SQL Server boolean-compatibility failure, and ten Windows temp-directory cleanup setup errors. The boolean query was corrected to use SQLAlchemy `true()`; all affected files then passed 54/54 using an isolated temp root.
- A clean SQLite installation migrated successfully from an empty database through `0252_problem_attachments`, and `alembic current` confirmed `0252_problem_attachments (head)`.
- The database upgrade policy now identifies `0252_problem_attachments` as the authoritative current schema head instead of the obsolete pre-1.66 revision examples.
- An opt-in staging attachment rehearsal is available at `backend/scripts/attachment_rehearsal.py`. It uploads uniquely named evidence to a disposable Problem, verifies the authorized download SHA-256, requires an out-of-scope account to receive `403` or `404` for list and download, and can write credential-free JSON evidence. It has passed Ruff, strict MyPy, and CLI validation; it has not been run because no isolated application/storage target was provided.
- The local SQL Server production-like rehearsal passed on 2026-10-07 using a verified `COPY_ONLY` backup restored as `MillensysSupportHub_Rehearsal_20261007` on drive `D:`. The isolated copy upgraded from `0248_portal_client_profile` through `0252_problem_attachments`, permission seeding passed, and the application compatibility checker returned `READY`. Verification found 21 service-management tables, 58 enabled/trusted foreign keys, 47 indexes, and the required Problem attachment index. Credential-free evidence is stored under `rehearsal-evidence/upgrade-rehearsal-20261007-164041.json` and `rehearsal-evidence/schema-verification-20261007.json`.
- Problem read APIs now return the complete investigation record. Read endpoints were added for linked tickets, root causes, Changes, Knowledge articles, and status history.
- A permission-scoped `/problem-portfolio` API performs aggregate counts without per-row API calls.
- Verification after this continuation: Ruff passed; Mypy passed across 201 source files; focused service-management API tests passed (9 tests); frontend TypeScript and Vite production builds passed.

### Architectural decisions to preserve

- A Change Request is its own workflow attached one-to-one to a `CHANGE_REQUEST` Ticket.
- UAT is a completely separate workflow. Do not add a Change-to-UAT link or make UAT a Change completion requirement.
- Specialized lifecycle states remain outside the global Ticket Status catalog.
- Ticket/Change synchronization uses validation gates, not automatic status equivalence.
- Change notifications are event-driven and do not depend on the escalation scheduler.
- Ticket comments, attachments, tasks, checklists, worklogs, resolution, and closure remain shared Ticket capabilities.

### Completed at this checkpoint

- Database migrations through `0253_change_deployment_closure`; the expected production revision is `0253_change_deployment_closure`.
- Change Requests are SLA-exempt and now use a controlled deployment lifecycle: Planned → Pending Deployment → Implementing → Validation, with repeat promotion from validation back to Pending Deployment for test/staging/production progression. Completion requires a deployment-requirements summary, resolved permissions/access, training/communication and documentation readiness, a successful implementation outcome, actual implementation date, and validation evidence. The parent ticket can then be resolved with a Change completion summary without incident-only root cause or service-provided requirements.
- Problem, Major Incident, and Change Request models, permissions, lifecycle validation, audit records, optimistic versioning, and scoped APIs.
- Problem ticket/root-cause/Change/Knowledge links, comments, tasks, secure evidence attachments, and Knowledge drafts.
- Major-Incident affected-ticket and normalized scope management, updates, Problem follow-up, restoration, and post-incident-review gates.
- Structured Change Request details, assessment, planning, implementation, rollback, validation, cancellation, failure, completion, and documented reopening.
- Parent Ticket/Change lifecycle consistency gates for implementation, validation, resolution, cancellation, closure, and reopening.
- Dedicated internal Change Request workspace at `/tickets/{id}/change-request` with editing, transitions, plans, validation, approvals, and lifecycle history.
- Immutable approval cycles with permission-filtered candidates, one pending cycle, approver-only decisions, latest-cycle lifecycle validation, notifications, and history.
- Change Request portfolio at `/change-requests` with search, status filtering, summary metrics, overdue count, navigation, and permission-scoped Excel export.
- Client Portal structured Change Request form. Ticket and Change details are created atomically, while attachments continue through the secured Ticket attachment workflow.
- Legacy Change Request tickets can initialize structured details from the dedicated workspace.
- Event-driven approval, decision, and lifecycle notifications with direct workspace links and deduplication.
- Ticket Detail shows a compact Change summary and an **Open workspace** action.

### Last verification results

- Backend Ruff: passed.
- Backend Mypy: passed across 201 source files.
- Focused Change portfolio/export tests: 8 passed.
- Combined Client Portal and service-management tests: 18 passed.
- Expanded lifecycle/workflow suite: 33 passed.
- Frontend TypeScript build: passed.
- Frontend Vite production build: passed.
- Focused localization, RTL, Support Now, and service-management portfolio suite: 19 passed.
- Known non-blocking build warnings: existing large bundle chunks and modules imported both statically and dynamically.

### Next implementation steps

1. Run a focused production-like attachment authorization/storage rehearsal against the restored isolated database and an isolated storage root; automated attachment tests pass and the rehearsal command is ready.
2. Perform controlled role-based UAT for Major Incident, Problem, and Change Request workflows.
3. After those checks pass, update release notes/version and build release `1.66.121`.

Environment checkpoint on 2026-10-07: the disposable SQL Server upgrade rehearsal has passed. Release candidate `1.66.121` is reserved as the next unused version, but packaging remains gated by the attachment rehearsal and controlled UAT above.

### Recommended first task when resuming

Run the isolated attachment/storage rehearsal and controlled role-based UAT against the restored rehearsal database, then prepare release notes and packaging. Do not point these checks at the production database or production attachment storage.

## Implementation progress

Completed in the Phase 1 foundation:

- Dedicated Problem, Major Incident, and Change Request database records without changing global Ticket statuses.
- Ticket linkage, status-history, root-cause linkage, Major-Incident updates, and Problem-to-Change linkage tables.
- Version-checked lifecycle validation for all three domains, including documented reasons for exceptional transitions.
- Structured Change Request details and immutable approval-cycle decisions.
- Permission catalog and initial Support/Administrator profile assignments.
- Audited REST endpoints for core creation, transitions, updates, and approvals.
- Cross-client visibility filtering based on the existing visible-ticket query.
- Versioned and audited Problem/Major-Incident ticket link and unlink operations.
- Problem assignment, root-cause, and permanent-fix Change linkage endpoints.
- Normalized Major-Incident client, product, module, service, and environment scopes.
- Lifecycle-specific permission checks and initial Problem, Major-Incident, and Change closure-readiness rules.
- Major-Incident Problem linkage, create-from-incident flow, and owned/due-dated Problem commitments.
- Service-restoration and post-incident-review gates requiring Problem follow-up.
- Problem comments, versioned investigation tasks, and approved Knowledge article links.
- Protected Problem evidence uploads with the ticket attachment security controls.
- Internal Knowledge draft creation from Problem workarounds and permanent fixes.
- Change/Ticket lifecycle consistency gates for implementation, validation, resolution, cancellation, closure, and documented reopening.
- Compact Change Request summary card on Ticket Detail with a dedicated, permission-protected Change Request workspace for request definition, impact, plans, validation, schedule, and controls.
- Permission-aware Change Request detail editing and lifecycle transition actions in the dedicated workspace, including server-side readiness and Ticket-status gates.
- Governed Change approval candidates, single-pending-cycle enforcement, approver-only immutable decisions, latest-cycle lifecycle gates, and approval history in the workspace.
- Auditable Change lifecycle timeline and direct structured-detail initialization for legacy Change Request tickets.
- Searchable, permission-scoped Change Request portfolio and Support navigation entry.
- Client Portal Change Request form with atomic Ticket/structured-detail creation and product/module context inheritance.
- Event-driven Change approval and lifecycle notifications with direct workspace links and deduplication; no scheduler dependency.
- Permission-scoped Change portfolio metrics, overdue visibility, and Excel export.
- Production database compatibility revision and clean-install migration validation.
- Permission-scoped Problem portfolio with owner, linked-ticket, task, overdue, and target-resolution indicators.
- Dedicated Problem workspace with investigation editing, lifecycle transitions, comments, tasks, secure evidence, relationship visibility, and lifecycle history.
- Governed Problem relationship controls for tickets, root causes, Changes, Knowledge links, and Knowledge drafts.
- Ticket Detail Problem summary with existing-Problem linking and create-from-ticket actions.
- Major-Incident portfolio, commander workspace, read APIs, and Incident Ticket declaration/open card.
- Active SEV1/SEV2 Support Now banner and named/catalog-based Major-Incident owner and scope controls.
- Product-aware module scope selection and event-driven Problem/Major-Incident notifications.
- Permission-scoped management summaries and Excel exports for Problems and Major Incidents.
- Server-filtered Client Portal presentation for approved Major-Incident updates and Problem Knowledge guidance.

Remaining Phase 1 work:

- Knowledge review/publishing remains governed by the existing Knowledge workflow.
- Production-like attachment authorization and storage rehearsal using an isolated attachment root.
- Controlled role-based UAT of the connected Major Incident, Problem, and Change Request workflows.
- Controlled release packaging and deployment smoke testing after those two environment gates pass.

## Core architecture decision

The existing Ticket remains the common operational record and continues to provide ticket numbering, client/requester context, assignment, comments, attachments, tasks, checklists, worklogs, SLA, escalation, notifications, audit history, and resolution/closure.

Specialized workflows are added around the Ticket:

```text
                          Existing Ticket
                               |
            +------------------+------------------+
            |                  |                  |
            v                  v                  v
     MajorIncident       ProblemTicketLink    ChangeRequestDetail
       one-to-one            many-to-many          one-to-one
            |                  |                  |
     Affected Tickets       Problem Record     Approvals / Plans
     Status Updates         Known Error        Validation / Implementation
            |                  |                  |
            +---------- Problem -> Change --------+
```

Do not add Problem, Major-Incident, CAB, or implementation states to the global Ticket Status catalog. Each specialized record has its own lifecycle, with explicit synchronization rules to the normal Ticket lifecycle.

## Existing capabilities to reuse

- Ticket types, numbers, lifecycle, assignment, teams, followers, comments, attachments, tasks, checklists, and worklogs.
- Clients, contacts, contracts, covered products, modules, services, environments, and SLA evidence.
- Root Cause and Resolution Outcome catalogs.
- Knowledge Base articles and ticket/article links.
- UAT remains a separate, independent workflow and is not required or linked by Change Requests.
- Notification rules and outbound email infrastructure.
- Permission-based authorization and client/branch scope.
- Audit logs and optimistic version checking.
- Saved views, operational reports, dashboards, and exports.
- Client Portal authentication, ticket creation, ticket tracking, and attachment handling.

## Domain boundaries

### Major Incident

A Major Incident extends one existing Incident ticket. It coordinates restoration of a critical or widespread service interruption and links all affected tickets.

### Problem

A Problem is an independent investigation record that can link many Incident tickets and Major Incidents. It owns the shared root cause, workaround, known-error information, and permanent-fix investigation.

### Change Request

A Change Request extends the existing `CHANGE_REQUEST` ticket type through a one-to-one detail record. It owns assessment, approval, planning, implementation, rollback, and validation information.

## End-to-end relationship

```text
Incident Tickets
       |
       v
Major Incident -- service restored
       |
       v
Problem -- root cause and permanent fix identified
       |
       v
Change Request -- assessment, approval, implementation, and validation
       |
       v
Knowledge Article + Problem Closure
```

# Problem Management

## Data model

### `problems`

- `id`
- `problem_number`, unique, generated with `PRB` prefix
- `title`
- `description`
- `status`
- `priority`
- `owner_user_id`
- `owner_team_id`
- `product_id`
- `product_module_id`
- `environment_id`
- `business_impact`
- `symptoms`
- `workaround`
- `known_error_summary`
- `root_cause_summary`
- `permanent_fix_summary`
- `target_resolution_date`
- `resolved_at`
- `closed_at`
- `created_by_user_id`
- `created_at`
- `updated_at`
- `version`

### `problem_ticket_links`

- `problem_id`
- `ticket_id`
- `link_type`: `AFFECTED_INCIDENT`, `EVIDENCE`, or `RELATED`
- `linked_by_user_id`
- `linked_at`
- Unique constraint on `problem_id`, `ticket_id`, and `link_type`.

### `problem_root_causes`

- `problem_id`
- `root_cause_id`
- Unique constraint on the pair.

### `problem_change_links`

- `problem_id`
- `change_ticket_id`
- `link_type`: `PERMANENT_FIX` or `RELATED`
- `linked_by_user_id`
- `linked_at`

### Supporting records

Add Problem comments, attachments, tasks, and status history using the established Ticket patterns. Avoid polymorphic foreign keys without database constraints; use explicit Problem tables where integrity would otherwise be weakened.

## Lifecycle

```text
NEW
  -> INVESTIGATING
  -> ROOT_CAUSE_IDENTIFIED
  -> KNOWN_ERROR
  -> FIX_PROPOSED
  -> FIX_IMPLEMENTED
  -> MONITORING
  -> CLOSED
```

Alternative states: `CANCELLED`. Reopening a closed Problem requires permission and a documented reason.

## Ticket integration

Add the following actions to Ticket Detail:

- Create Problem from ticket.
- Link to existing Problem.
- View linked Problem.
- Apply the approved Problem workaround to the ticket resolution draft.
- View other incidents linked to the Problem when authorized.
- Unlink an incorrect relationship with an audited reason.

Closing a Problem must not automatically close its linked tickets. Each ticket can belong to a different client and retains its own resolution, client confirmation, and closure requirements.

## Knowledge integration

- Publish an approved workaround as a Known Error article.
- Publish the permanent fix as a resolution article.
- Link existing Knowledge articles.
- Record Knowledge usage when an engineer applies the workaround to a ticket.

# Major-Incident Management

## Data model

### `major_incidents`

- `id`
- `major_incident_number`, unique, generated with `MI` prefix
- `primary_ticket_id`, unique
- `severity`
- `status`
- `incident_commander_user_id`
- `technical_owner_user_id`
- `communication_owner_user_id`
- `declared_at`
- `detected_at`
- `service_restored_at`
- `monitoring_started_at`
- `closed_at`
- `business_impact`
- `affected_users`
- `current_status_summary`
- `next_update_at`
- `resolution_summary`
- `post_incident_review`
- `created_by_user_id`
- `created_at`
- `updated_at`
- `version`

### `major_incident_ticket_links`

- `major_incident_id`
- `ticket_id`
- `link_type`: `PRIMARY`, `AFFECTED`, or `DUPLICATE`
- `linked_by_user_id`
- `linked_at`
- Unique constraint on `major_incident_id` and `ticket_id`.

Do not reuse `Ticket.escalation_parent_ticket_id`. That relationship already has escalation-specific assignment and closure synchronization behavior.

### `major_incident_updates`

- `major_incident_id`
- `update_type`: `INTERNAL`, `CLIENT`, or `RESTORATION`
- `internal_message`
- `client_message`
- `published_by_user_id`
- `published_at`

### Scope tables

Use association tables for affected clients, products, modules, services, and environments so the incident can represent a multi-client or multi-product outage.

## Lifecycle

```text
DECLARED
  -> RESPONSE_ACTIVE
  -> SERVICE_RESTORED
  -> MONITORING
  -> POST_INCIDENT_REVIEW
  -> CLOSED
```

Cancellation requires a reason and is allowed only when the declaration was incorrect.

## Declaration flow

1. An authorized user promotes an Incident ticket.
2. The server locks and revalidates the ticket.
3. A Major Incident record is created.
4. The source ticket becomes the primary linked ticket.
5. Commander, technical owner, communication owner, severity, and update interval are recorded.
6. The configured response team is notified.
7. Support Now displays the active incident prominently.
8. The operation is written to the audit log.

## Support Now integration

Add a Major Incidents area showing:

- Severity and lifecycle state.
- Incident commander and owners.
- Elapsed incident duration.
- Affected clients, products, and services.
- Number of linked tickets.
- Latest internal and client-safe updates.
- Next communication deadline.
- `Publish update` and `Restore service` actions.

Display a prominent banner while any Major Incident visible to the user is active.

## Client communication

- Internal investigation notes remain internal.
- Client updates use a separate client-safe message.
- One update can be distributed to authorized contacts for affected clients.
- Client-safe updates can appear in the Client Portal and linked-ticket live tracking.
- Every publication records recipient scope, delivery result, actor, and timestamp.

## Problem integration

When service is restored, require either:

- A linked Problem record, or
- A `Problem to be created` action with owner and due date.

The post-incident review cannot be completed until the Problem or an approved documented root cause exists.

# Change Request Management

## Current-system fit

The `CHANGE_REQUEST` ticket type and `CHG` prefix already exist, and the Client Portal can submit this ticket type. Add structured detail rather than introducing another competing intake record.

### `change_request_details`

- `id`
- `ticket_id`, unique
- `request_kind`: `NEW_FEATURE` or `UPDATE_EXISTING_FEATURE`
- `purpose`
- `detailed_description`
- `business_impact`
- `expected_result`
- `affected_product_id`
- `affected_module_id`
- `required_permissions`
- `requested_priority`
- `change_status`
- `assessment_owner_user_id`
- `technical_impact`
- `security_impact`
- `data_impact`
- `downtime_required`
- `risk_level`
- `estimated_effort`
- `target_release`
- `planned_start_at`
- `planned_end_at`
- `implementation_plan`
- `rollback_plan`
- `test_plan`
- `validation_result`
- `created_at`
- `updated_at`
- `version`

### `change_request_approvals`

- `change_request_id`
- `approval_stage`
- `approver_user_id`
- `decision`: `PENDING`, `APPROVED`, or `REJECTED`
- `comment`
- `requested_at`
- `decided_at`
- `version`

Approval history is immutable. A new approval cycle creates new rows rather than overwriting previous decisions.

## Lifecycle

```text
SUBMITTED
  -> UNDER_ASSESSMENT
  -> AWAITING_APPROVAL
  -> APPROVED
  -> PLANNED
  -> IMPLEMENTING
  -> VALIDATION
  -> COMPLETED
```

Alternative states: `REJECTED`, `CANCELLED`, `FAILED`, and `ROLLED_BACK`.

## Ticket/change synchronization

| Ticket status | Typical Change status |
|---|---|
| `NEW` | `SUBMITTED` |
| `ASSIGNED` | `UNDER_ASSESSMENT` |
| `PENDING_INTERNAL` | `AWAITING_APPROVAL` |
| `IN_PROGRESS` | `IMPLEMENTING` |
| `RESOLVED` | `VALIDATION` |
| `CLOSED` | `COMPLETED` |

These are validation rules, not automatic equivalence. A Change can be approved but not yet implemented, and the Ticket status should continue to represent the operational owner state.

## Creation transaction

For internal and Client Portal creation:

1. Validate that the selected ticket type is `CHANGE_REQUEST`.
2. Validate the normal Ticket payload and structured Change fields.
3. Create the Ticket and `ChangeRequestDetail` in one database transaction.
4. Store attachments using the normal Ticket attachment mechanism.
5. Record one audit event containing the Ticket ID and Change detail ID.
6. Return the standard Ticket response with Change detail summary.

The existing ticket API remains compatible for integrations that create ordinary tickets. Change Request creation can use a dedicated endpoint or an optional nested `change_request` payload that is accepted only for the `CHANGE_REQUEST` type.

## Initial implementation scope

The first version requires:

- Structured request form.
- Assessment.
- One approval stage.
- Implementation plan.
- Rollback plan.
- Test plan.
- Validation result.
- Audit history.

CAB meetings, multiple conditional approvals, release trains, source-code integration, and full SDLC governance are later phases.

## Existing-feature reuse

| Existing capability | Change Request use |
|---|---|
| Ticket assignment | Assessment and implementation ownership |
| Comments | Internal and client discussion |
| Attachments | Requirements, screenshots, plans, and evidence |
| Ticket tasks | Assessment and implementation tasks |
| Ticket checklist | Deployment-readiness checklist |
| UAT | Separate workflow; no Change Request link or completion dependency |
| Worklogs | Analysis and implementation effort |
| Knowledge Base | Updated procedures and release documentation |
| Notifications | Approval, schedule, and outcome notifications |
| Ticket relations | Related incidents and service requests |
| Audit logs | Decisions, transitions, and material field changes |

# Permissions

## Problem permissions

- `problem.view`
- `problem.create`
- `problem.edit`
- `problem.assign`
- `problem.link_ticket`
- `problem.identify_root_cause`
- `problem.publish_known_error`
- `problem.close`
- `problem.reopen`

## Major-Incident permissions

- `major_incident.view`
- `major_incident.declare`
- `major_incident.command`
- `major_incident.link_ticket`
- `major_incident.publish_update`
- `major_incident.restore_service`
- `major_incident.close`

## Change Request permissions

- `change_request.view`
- `change_request.create`
- `change_request.assess`
- `change_request.approve`
- `change_request.plan`
- `change_request.implement`
- `change_request.validate`
- `change_request.complete`
- `change_request.rollback`

Portal permissions remain separate from internal permissions. Existing client and branch scoping applies to every ticket and client-visible update.

# API outline

## Problems

- `POST /problems`
- `GET /problems`
- `GET /problems/{id}`
- `PATCH /problems/{id}`
- `POST /problems/{id}/transition`
- `POST /problems/{id}/tickets`
- `DELETE /problems/{id}/tickets/{ticket_id}` with reason
- `POST /problems/{id}/changes`
- `POST /problems/{id}/knowledge`

## Major Incidents

- `POST /tickets/{ticket_id}/major-incident`
- `GET /major-incidents`
- `GET /major-incidents/{id}`
- `POST /major-incidents/{id}/transition`
- `POST /major-incidents/{id}/tickets`
- `DELETE /major-incidents/{id}/tickets/{ticket_id}` with reason
- `POST /major-incidents/{id}/updates`
- `POST /major-incidents/{id}/problem`

## Change Requests

- `GET /tickets/{ticket_id}/change-request`
- `PUT /tickets/{ticket_id}/change-request`
- `POST /tickets/{ticket_id}/change-request/transition`
- `POST /tickets/{ticket_id}/change-request/approvals`
- `POST /tickets/{ticket_id}/change-request/approval-decision`

Every modifying endpoint requires permission, visibility validation, optimistic version input, server-side lifecycle validation, and an audit event.

# UI integration

## Navigation

```text
Support
|- Support App
|- Support Now
|- Tickets
|- Major Incidents
|- Problems
`- Change Requests
```

## Ticket Detail

Render conditional cards for:

- Active or historical Major Incident.
- Linked Problems and approved workaround.
- Change Request Details.
- Related Changes.
- Known Error and linked Knowledge articles.
- Related affected tickets, subject to authorization.

## Client Portal

Clients can:

- Create and track their Change Requests.
- Add requested information and evidence.
- View client-safe Major-Incident updates affecting their client scope.
- View approved workaround or Knowledge content.
- Participate in authorized UAT and validation.

Clients cannot view internal Problem investigation, internal Major-Incident notes, other clients, internal approval discussion, or security-sensitive implementation details.

# SLA and timing rules

- Incident Ticket SLA remains authoritative during a Major Incident.
- Linking a ticket to a Major Incident does not silently pause its SLA.
- Any new SLA pause behavior must be explicit, configured, and written to `TicketSlaInterval` history.
- Problems use investigation target dates and age metrics rather than normal ticket SLA unless a separate Problem SLA is later configured.
- Change Requests use approval, planning, implementation, and validation target dates. They should not distort Incident SLA metrics.
- Major-Incident reporting records detection, declaration, acknowledgment, restoration, monitoring, and closure durations.

# Notifications

Add notification events for:

- Major Incident declared, ownership changed, update due, service restored, and closed.
- Ticket linked to or removed from a Major Incident.
- Problem assigned, root cause identified, workaround published, fix implemented, monitoring overdue, and closed.
- Change submitted, assessment assigned, approval requested, approved, rejected, scheduled, implementation started, validation requested, completed, failed, or rolled back.

All scheduled notifications must use the durable background-job architecture when that foundation is implemented.

# Audit requirements

Audit at minimum:

- Creation and every lifecycle transition.
- Assignment and ownership changes.
- Ticket linking and unlinking.
- Root-cause and workaround changes.
- Major-Incident declarations and published updates.
- Change assessments, approval requests, decisions, implementation plans, rollback plans, and validation results.
- Client-visible publication and recipient scope.
- Reopen, cancellation, rejection, failure, and rollback reasons.

Audit metadata should include actor, timestamp, entity, entity ID, action, reason, old/new values where appropriate, correlation ID, and source channel.

# Reporting and dashboards

## Problem metrics

- Open Problems by status, priority, product, module, owner, and age.
- Recurring incidents by Problem.
- Mean time to identify root cause.
- Mean time from root cause to permanent fix.
- Known Errors without approved workarounds.
- Problems without linked Changes after a permanent fix is proposed.

## Major-Incident metrics

- Count by severity and affected service.
- Detection-to-declaration time.
- Declaration-to-restoration time.
- Communication timeliness.
- Number of affected clients and linked tickets.
- Post-incident reviews overdue.

## Change metrics

- Changes by state, type, product, risk, and owner.
- Approval lead time.
- Planned versus actual implementation duration.
- Success, failure, and rollback rates.
- Validation and client-acceptance duration.
- Problems resolved by Change.

# Migration and compatibility

- Add new tables through Alembic without modifying existing ticket data destructively.
- Seed permissions idempotently and include scope metadata.
- Preserve the existing `CHANGE_REQUEST` ticket type and `CHG` prefix.
- Backfill `ChangeRequestDetail` only when reliable structured data exists; otherwise leave legacy Change tickets accessible with a clear `Details not yet structured` state.
- Do not automatically promote existing P1 tickets to Major Incidents.
- Do not reinterpret existing `TicketRelation` or `escalation_parent_ticket_id` rows.
- Existing APIs remain backward compatible.

# Testing requirements

## Backend

- Lifecycle transition matrix for all three modules.
- Permission and visibility tests.
- Cross-client isolation tests.
- Optimistic concurrency and stale-version tests.
- Link uniqueness and unlink audit tests.
- Major-Incident declaration idempotency.
- Client-safe versus internal update isolation.
- Problem closure requirements.
- Change approval immutability.
- Change rollback and failed-implementation paths.
- Ticket/Change transaction rollback when detail validation fails.
- SQL Server migration and constraint validation.

## Frontend

- Conditional Ticket Detail cards.
- Major-Incident declaration and linking flows.
- Support Now active-incident banner.
- Problem workspace and ticket linking.
- Change Request dynamic form.
- Approval, implementation, rollback, and validation actions.
- Portal visibility and information isolation.
- Arabic and RTL behavior.
- Mobile layouts and keyboard accessibility.

## End-to-end scenario

1. Create multiple related Incident tickets.
2. Promote one to Major Incident.
3. Link the remaining tickets.
4. Publish internal and client-safe updates.
5. Restore service.
6. Create and link a Problem.
7. Record workaround and root cause.
8. Create a Change Request from the Problem.
9. Assess and approve the Change.
10. Implement and validate the Change Request using its own validation record.
11. Publish a Knowledge article.
12. Monitor and close the Problem.
13. Resolve or close each client ticket independently.

# Delivery plan

## Phase 1 — Foundations

- Database models and migrations.
- Permissions and profile grants.
- Lifecycle services.
- Audit events.
- API schemas and optimistic version validation.
- Shared comments, attachments, task, and timeline patterns.

## Phase 2 — Major Incidents

- Promote Incident.
- Dedicated ticket links.
- Commander workspace.
- Internal and client-safe updates.
- Notifications and Support Now banner.
- Restoration and post-incident-review flow.

## Phase 3 — Problems

- Problem workspace.
- Incident and Major-Incident linking.
- Root cause, workaround, Known Error, and permanent-fix management.
- Knowledge integration.
- Problem dashboards and reports.

## Phase 4 — Simple Change Requests

- Structured Client Portal and internal forms.
- Assessment and single approval.
- Planning, implementation, rollback, and validation.
- Optional Problem links; UAT remains a separate workflow.
- Change dashboards and exports.

## Phase 5 — Advanced governance

- CAB meetings and conditional approval matrices.
- Maintenance-window collision detection.
- Release management and deployment coordination.
- Full SDLC integration.
- Automated post-implementation review.

# Completion criteria

This initiative is complete when:

- Major Incidents coordinate restoration without abusing escalation parent/child behavior.
- Problems can link multiple authorized incidents and govern root cause, workaround, Known Error, and permanent fix.
- Change Request tickets have structured, versioned, auditable assessment and implementation details.
- The three lifecycles connect without forcing specialized states into normal Ticket statuses.
- Internal and client-visible information remain strictly separated.
- Permissions, audit, concurrency, notifications, reports, Arabic/RTL, and mobile behavior are verified.
- Clean installation, upgrade rehearsal, SQL Server migration, backend regression, frontend regression, and controlled UAT all pass.

# Resume marker

Continue from **Next implementation steps** near the top of this document. Automated regression, SQLite clean-install, and the disposable SQL Server upgrade rehearsal are complete. The next step is the isolated attachment/storage rehearsal and controlled role-based UAT before release packaging.
