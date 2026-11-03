# Ticket Creation and Workflow Gap Remediation Plan

Last updated: 2026-09-05  
Owner: Engineering  
Document purpose: Implementation backlog, progress tracker, and handoff checkpoint for ticket creation and workflow remediation.

## Current checkpoint

- Overall status: `IMPLEMENTATION COMPLETE — RELEASE PREPARATION PENDING`
- Current phase: Phase 8 — Full regression and release readiness
- Last completed work: Completed release compatibility, clean migration, backend quality, and frontend build verification for the remediation changes.
- Next work item: Prepare the controlled deployment package and production-copy upgrade rehearsal.
- Code changes made for this backlog: TWF-001 pending ownership, TWF-002 configurable first-response start/event handling, TWF-003/TWF-015 resolution lifecycle history, and TWF-004 atomic SLA re-evaluation and confirmation preview.
- Verification baseline: Phase 1 ticket, workflow, concurrency, notification, and SLA tests pass as of 2026-09-05.
- Baseline command:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest app\tests\test_tickets.py app\tests\test_ticket_workflow.py app\tests\test_ticket_concurrency.py app\tests\test_wave2a_ticket_notifications.py -q
```

## Status definitions

| Status | Meaning |
|---|---|
| `NOT STARTED` | No implementation work has begun. |
| `IN PROGRESS` | Work is actively being implemented. |
| `BLOCKED` | Work cannot continue until the documented blocker is resolved. |
| `CODE COMPLETE` | Implementation is finished but verification or review remains. |
| `TESTED` | Automated and relevant manual verification passed. |
| `DONE` | Implementation, tests, documentation, and review are complete. |
| `DEFERRED` | Intentionally postponed with an approved reason. |

When implementation starts, update both the work-item row and the Current checkpoint section. Do not mark an item `DONE` until its acceptance criteria and tests pass.

## Progress summary

| Phase | Scope | Status | Completed |
|---|---|---|---:|
| Phase 0 | Audit and remediation plan | `DONE` | 100% |
| Phase 1 | SLA and pending-state correctness | `DONE` | 100% |
| Phase 2 | Shared validation and authorization | `DONE` | 100% |
| Phase 3 | Idempotency and concurrency | `DONE` | 100% |
| Phase 4 | Notifications and data protection | `DONE` | 100% |
| Phase 5 | Workflow completion controls | `DONE` | 100% |
| Phase 6 | Creation and editing UX | `DONE` | 100% |
| Phase 7 | Retention, deletion, and auditability | `DONE` | 100% |
| Phase 8 | Full regression and release readiness | `DONE` | 100% |

## Implementation principles

1. Preserve existing ticket data and audit history.
2. Apply the same business rules to employee, portal, single-ticket, bulk, and API workflows.
3. Keep permission checks on the backend; frontend checks are usability controls only.
4. Treat SLA snapshots and elapsed-time history as auditable financial/contractual records.
5. Add regression tests before or with every behavioral correction.
6. Use migrations for database changes and test clean installation plus upgrade installation.
7. Avoid silently changing historical SLA measurements during deployment.

## Phase 1 — SLA and pending-state correctness

### TWF-001 — Correct pending-client responsible-party default

- Priority: Critical
- Status: `DONE`
- Primary code: `backend/app/modules/tickets/service.py`, `backend/app/modules/tickets/schemas.py`
- Problem: The transition code checks `PENDING_CUSTOMER`, while the actual status is `PENDING_CLIENT`. Requests that omit the responsible party default to Millensys incorrectly.
- Implementation steps:
  1. Replace the invalid status comparison with `PENDING_CLIENT`.
  2. Centralize the default responsible-party mapping for all pending statuses.
  3. Validate that an explicitly supplied party is compatible with the target status, or document why an override is allowed.
  4. Add tests for UI-style requests and API requests that omit the party.
- Acceptance criteria:
  - `PENDING_CLIENT` defaults to `CUSTOMER`.
  - Internal and vendor pending statuses receive their intended defaults.
  - SLA pause intervals and reports use the corrected party.

### TWF-002 — Measure first response from a real response event

- Priority: Critical
- Status: `DONE`
- Primary code: `backend/app/modules/tickets/service.py`, ticket comment/email services
- Problem: The first-response SLA currently completes on first dedicated assignment rather than customer communication. Operations also need a configurable start anchor because engineers may begin handling a critical request before it is formally assigned in the application.
- Approved design direction:
  - Separate the first-response **start anchor** from the **completion event**.
  - Add site setting `first_response_start_mode` with controlled values `TICKET_CREATED` and `FIRST_DEDICATED_ASSIGNMENT`.
  - `TICKET_CREATED` starts the clock from the ticket's recorded creation/received timestamp.
  - `FIRST_DEDICATED_ASSIGNMENT` keeps the clock paused until the first dedicated employee assignment, then starts it from that assignment timestamp.
  - In both modes, assignment does not complete first response; only a qualifying customer-facing employee response completes it.
  - Snapshot the selected mode and effective start timestamp on each SLA clock so a later site-setting change does not rewrite historical results.
  - Recommended operational default: `TICKET_CREATED`, because customer response commitments normally begin when the support organization receives the request. Use `FIRST_DEDICATED_ASSIGNMENT` only when that is the explicitly approved KPI definition.
- Implementation steps:
  1. Add and validate the `first_response_start_mode` site setting and expose it in the SLA settings UI.
  2. Add clock snapshot fields for the selected start mode and start-anchor timestamp through an Alembic migration.
  3. Centralize clock start behavior in one idempotent domain operation used by ticket creation and dedicated assignment.
  4. Define qualifying response events: public employee comment, successfully queued/sent outbound response, or another approved channel event.
  5. Remove first-response completion from assignment processing.
  6. Create one idempotent `record_first_response()` service operation.
  7. Call it from every qualifying communication channel.
  8. Preserve separate received, creation, assignment, work-start, and first-response timestamps and KPIs.
  9. Decide how existing tickets retain their historical measurements; do not rewrite them silently.
  10. Add tests for both start modes, setting changes after clock creation, reassignment, duplicate response events, and response-before-assignment edge cases.
- Acceptance criteria:
  - Each first-response clock snapshots its start mode and effective start timestamp.
  - `TICKET_CREATED` starts at ticket creation/receipt and does not wait for assignment.
  - `FIRST_DEDICATED_ASSIGNMENT` remains paused until a dedicated employee is assigned.
  - Assignment alone never completes the first-response clock.
  - The first qualifying response completes it exactly once.
  - Internal notes and customer comments do not falsely complete it.
  - Changing the site setting affects only newly started clocks and does not alter historical measurements.
  - Time-to-assignment remains independently reportable.

### TWF-003 — Stop resolution SLA at the correct lifecycle event

- Priority: Critical
- Status: `DONE`
- Primary code: `backend/app/modules/tickets/service.py`
- Decision: Resolution SLA stops at the engineer's `RESOLVED` action. Resolve & Close uses that same resolution timestamp; later customer confirmation or closure does not extend the resolution SLA.
- Proposed implementation: Stop the resolution clock at `RESOLVED`; optionally introduce a separate customer-confirmation/closure clock.
- Implementation steps:
  1. Confirm the SLA definition with the business owner.
  2. Complete the resolution clock on `RESOLVED` when using time-to-resolution semantics.
  3. Ensure resolve-and-close and cancel remain idempotent.
  4. Define reopening behavior and restart rules.
  5. Add tests for resolved, client-confirmation, closed, cancelled, and reopened flows.
- Acceptance criteria:
  - Clock completion matches the approved contractual definition.
  - Waiting for customer confirmation does not corrupt resolution performance.
  - Reopening creates an auditable new measurement segment.

### TWF-004 — Re-evaluate SLA safely after material ticket edits

- Priority: Critical
- Status: `DONE`
- Primary code: `backend/app/modules/tickets/routes.py`, `backend/app/modules/tickets/service.py`, SLA models
- Material fields: contract, client, product, module, service, environment, category, impact, urgency, and priority.
- Implementation steps:
  1. Move entitlement/SLA resolution into a reusable domain service.
  2. Detect whether an edit changes SLA-relevant context.
  3. Require an explicit re-evaluation reason for changes that alter the SLA.
  4. Close or supersede the old snapshot without deleting its elapsed history.
  5. Create the new snapshot and clocks using a documented effective timestamp.
  6. Record old values, new values, actor, reason, and effect on targets in the audit log.
  7. Show a confirmation preview in the UI before saving.
- Acceptance criteria:
  - Ticket context and active SLA always agree.
  - Historical SLA periods remain reproducible.
  - Unauthorized users cannot replace contractual SLA data.

## Phase 2 — Shared validation and authorization

### TWF-005 — Use one validation engine across create and edit

- Priority: High
- Status: `DONE`
- Implementation steps:
  1. Extract active-record, parent-child, service-module, requester-client, branch-client, and entitlement checks into shared services.
  2. Apply the same checks to employee creation, portal creation, editing, and imports.
  3. Use controlled enums/literals for impact, urgency, source channel, and other finite values.
  4. Recalculate priority from impact and urgency unless an authorized explicit override is supplied.
  5. Return stable error codes suitable for frontend handling.
- Acceptance criteria:
  - Editing cannot select combinations that creation would reject.
  - Inactive catalog records cannot be newly assigned to a ticket.
  - Existing inactive historical references remain viewable.

### TWF-006 — Apply preferred contract consistently during editing

- Priority: High
- Status: `DONE`
- Implementation steps:
  1. Pass the requested contract as `preferred_contract_id` during edit evaluation.
  2. Distinguish “keep current contract,” “select another contract,” and “clear contract.”
  3. Return candidates when multiple valid contracts exist.
  4. Add tests covering overlapping contracts and deliberate contract changes.
- Acceptance criteria:
  - A valid selected contract is not silently replaced.
  - An invalid selection produces a clear reason and valid alternatives.

### TWF-007 — Unify single and bulk transition permissions

- Priority: High
- Status: `DONE`
- Primary code: `backend/app/modules/tickets/routes.py`, `backend/app/modules/tickets/workflow.py`
- Implementation steps:
  1. Create one authorization function for each workflow command.
  2. Use it for allowed-transition discovery, single transition, bulk transition, and UI capabilities.
  3. Correct `ticket.resolve.any` behavior so it is identical in all entry points.
  4. Add permission-matrix tests for assignee, team member, supervisor, administrator, and portal user.
- Acceptance criteria:
  - The same actor/ticket combination has the same result in single and bulk APIs.
  - UI actions match backend authorization.

### TWF-008 — Make configurable statuses compatible with the workflow engine

- Priority: Medium
- Status: `DONE`
- Decision: Status codes and lifecycle membership are system-controlled. Administrators may localize the label and color only; they cannot create, delete, rename the code, deactivate, or rewire lifecycle statuses.
- Implementation steps:
  1. Identify statuses that are mandatory system lifecycle states.
  2. Prevent administrators from creating unreachable states, or add persisted transition definitions.
  3. Validate transition graphs for missing nodes, dead ends, and unsafe terminal-state paths.
  4. Provide an administration preview before activation.
- Acceptance criteria:
  - Every active status has a documented and reachable lifecycle role.

## Phase 3 — Idempotency and concurrency

### TWF-009 — Enforce idempotency for all ticket creation requests

- Priority: High
- Status: `DONE`
- Implementation steps:
  1. Store channel, actor/customer scope, key, request fingerprint, ticket ID, and result.
  2. Add a database uniqueness constraint for the defined idempotency scope.
  3. Return the original ticket for an identical retry.
  4. Reject reuse of the same key with a different payload.
  5. Apply to employee UI, portal, integrations, and imports where appropriate.
- Acceptance criteria:
  - Network retries and double clicks cannot create duplicate tickets.

### TWF-010 — Add optimistic concurrency to bulk operations

- Priority: High
- Status: `DONE`
- Implementation steps:
  1. Require `{ticket_id, expected_version}` per bulk item.
  2. Process authorization and version checks per ticket.
  3. Define atomic versus partial-success behavior explicitly.
  4. Return structured outcomes for successful, stale, unauthorized, and invalid tickets.
  5. Add concurrent update tests.
- Acceptance criteria:
  - Bulk actions cannot silently overwrite a newer ticket change.

### TWF-011 — Add idempotency to comments and uploads

- Priority: Medium
- Status: `DONE`
- Implementation steps:
  1. Add client-generated operation keys to comment creation.
  2. Add upload deduplication using operation key and content metadata.
  3. Test browser retries and repeated submissions.
- Acceptance criteria:
  - A retried operation produces one logical comment or attachment.

## Phase 4 — Notifications and data protection

### TWF-012 — Scope creation notifications to authorized recipients

- Priority: High
- Status: `DONE`
- Primary code: `backend/app/modules/tickets/service.py`
- Implementation steps:
  1. Define recipients by event: assignee, assigned team, followers, requester, and explicitly subscribed supervisors.
  2. Reuse ticket visibility rules before persisting each notification.
  3. Minimize sensitive content in notification previews.
  4. Add confidentiality tests for client, department, team, and restricted tickets.
- Acceptance criteria:
  - No unauthorized employee receives ticket metadata.
  - Users do not receive organization-wide creation noise.

### TWF-013 — Publish consistent workflow notifications

- Priority: Medium
- Status: `DONE`
- Implementation steps:
  1. Define a domain event for every successful status transition.
  2. Create an event-to-recipient/channel matrix.
  3. Notify requester/followers only when visibility and comment rules allow it.
  4. Use an outbox so committed ticket changes and messages remain consistent.
- Acceptance criteria:
  - Assignment, pending, resolved, reopened, closed, and cancelled events have predictable notifications.

## Phase 5 — Workflow completion controls

### TWF-014 — Add resolution and closure readiness validation

- Priority: High
- Status: `DONE`
- Implementation steps:
  1. Define which tasks and checklist items block resolution or closure.
  2. Validate required resolution summary, root causes, outcome, and permanent-fix information.
  3. Provide an authorized override with mandatory reason where operationally required.
  4. Return a structured blocker list for the UI.
- Acceptance criteria:
  - Incomplete required work cannot be accidentally bypassed.
  - Every override is permission-controlled and audited.

### TWF-015 — Correct reopening semantics

- Priority: Medium
- Status: `DONE`
- Implementation steps:
  1. Preserve the previous resolution as historical evidence.
  2. Clear or version fields that should not appear as the active resolution.
  3. Record reopen count, reason, actor, and source.
  4. Restart applicable SLA clocks using the approved policy.
- Acceptance criteria:
  - Reopened tickets do not display stale resolution data as current.
  - Previous resolution evidence remains auditable.

### TWF-016 — Formalize customer confirmation

- Priority: Medium
- Status: `DONE`
- Implementation steps:
  1. Define who can record confirmation and what evidence is required.
  2. Separate internal movement to a waiting state from actual customer confirmation.
  3. Record confirmation channel, contact, timestamp, and optional note.
  4. Define automatic closure and timeout policies separately.
- Acceptance criteria:
  - Customer confirmation cannot be implied solely by an internal status change.

## Phase 6 — Creation and editing UX

### TWF-017 — Correct contract-candidate loading

- Priority: Medium
- Status: `DONE`
- Primary code: `frontend/src/pages/CreateTicketPage.tsx`
- Implementation steps:
  1. Request candidates whenever sufficient entitlement context exists, not only when product and service are both selected.
  2. Support product-only, module-specific, service-specific, and general contract coverage.
  3. Explain why each candidate matches.
  4. Preserve the selected contract while it remains valid.
- Acceptance criteria:
  - Every entitlement combination supported by the backend is selectable in the UI.

### TWF-018 — Allow attachments during initial creation

- Priority: Medium
- Status: `DONE`
- Implementation steps:
  1. Add a staged-upload or create-then-attach transaction design.
  2. Show upload progress and per-file errors.
  3. Clean up uncommitted staged files safely.
  4. Preserve idempotency when ticket creation is retried.
- Acceptance criteria:
  - Users can submit the ticket and initial evidence in one workflow.

### TWF-019 — Make related context changes atomic

- Priority: Medium
- Status: `DONE`
- Implementation steps:
  1. Let users update client, branch, requester, contract, and product/service context in one edit session.
  2. Validate the final proposed state rather than rejecting intermediate dependencies.
  3. Preview entitlement, assignment, and SLA consequences before save.
- Acceptance criteria:
  - Users are not trapped by branch/requester dependencies when changing a client.

## Phase 7 — Retention, deletion, and auditability

### TWF-020 — Replace ordinary ticket deletion with archive

- Priority: High
- Status: `DONE`
- Primary code: `backend/app/modules/tickets/routes.py`
- Implementation steps:
  1. Add archive fields including actor, timestamp, and reason.
  2. Exclude archived tickets from normal queues while retaining authorized search and reporting.
  3. Replace bulk hard deletion with bulk archive.
  4. Add a separately permissioned purge process governed by retention rules.
  5. Preserve immutable audit metadata even after an approved purge.
  6. Define transactional file cleanup and retry handling.
- Acceptance criteria:
  - Normal operational actions cannot destroy ticket evidence.
  - Purging is explicit, restricted, traceable, and retention-aware.

## Phase 8 — Regression and release readiness

### TWF-021 — Expand automated coverage

- Priority: High
- Status: `DONE`
- Required test groups:
  - Ticket creation by employee, portal, integration, and retry.
  - Valid and invalid catalog relationships.
  - Overlapping contract selection.
  - First-response and resolution SLA event semantics.
  - Pending pause ownership and elapsed-time calculations.
  - SLA-changing edits and historical snapshots.
  - Single versus bulk permission parity.
  - Concurrent single and bulk changes.
  - Notification visibility and confidentiality.
  - Resolve/close blockers and authorized overrides.
  - Reopen and repeat-resolution lifecycle.
  - Archive, restore, and governed purge.

### TWF-022 — Release verification and operational rollout

- Priority: High
- Status: `DONE`
- Implementation steps:
  1. Run lint, type checks, backend tests, and frontend tests/build.
  2. Run clean-install and upgrade migration rehearsals.
  3. Validate SLA reports before and after the change using controlled sample tickets.
  4. Prepare release notes and administrator guidance.
  5. Deploy behind feature flags where SLA semantics or deletion behavior changes materially.
  6. Monitor duplicate creation, SLA transitions, notification volume, and transition failures after release.
- Acceptance criteria:
  - Automated verification passes.
  - Upgrade rehearsal preserves existing tickets and SLA history.
  - Rollback and data-recovery procedures are documented.

## Decision log

| ID | Decision | Status | Owner | Notes |
|---|---|---|---|---|
| DEC-001 | Does resolution SLA stop at `RESOLVED` or `CLOSED`? | `APPROVED` | Business/SLA owner | Stop at the engineer's `RESOLVED` action, including Resolve & Close. Later closure does not extend the measurement. |
| DEC-002 | How should SLA changes affect elapsed time after ticket context edits? | `OPEN` | Business/SLA owner | Recommended: preserve old segment and start a new effective segment. |
| DEC-003 | Should active workflow transitions be configurable or system-controlled? | `OPEN` | Product/Engineering | Avoid allowing administrators to create unreachable statuses. |
| DEC-004 | Should bulk operations be atomic or permit partial success? | `OPEN` | Product/Operations | Recommended: explicit partial results for large operational batches. |
| DEC-005 | What is the ticket retention and purge period? | `OPEN` | Compliance/Operations | Required before implementing governed purge. |

## Work log

### Recipient policy checkpoint (2026-09-05)

Configured creation and reassignment email addresses must resolve to active application users who pass the same `ensure_ticket_access()` check as ticket reads. Unknown addresses are excluded; addresses shared by multiple accounts are excluded if any account is inactive or lacks visibility. This applies to both To and CC, including configured engineer notification addresses. If no authorized To recipient remains, no email event is queued. Administrators must use registered, authorized accounts for these rules. This check occurs at enqueue time; delivery-time access revocation still needs review in TWF-013. No migration is required.

### Transition notification checkpoint (2026-09-05)

The shared `transition_ticket()` operation now persists a `TICKET_WORKFLOW_TRANSITION` outbox event with the ticket ID, ticket reference, source and target status, actor, and transition source. It contains no subject, description, comments, requester, or client metadata. It also creates minimal in-app status notices for the ticket creator, assignee, pending owner, and followers only after the existing `ensure_ticket_access()` policy allows each recipient. Combined Resolve & Close produces separate `RESOLVED` and `CLOSED` events. Assignment-driven `NEW`/`TRIAGED` → `ASSIGNED` and automatic escalation-parent resolution/closure use the same publisher. Initial status history for newly created tickets remains covered by creation notification policy rather than transition policy.

| Event | Persisted outbox event | In-app recipients | Email policy |
|---|---|---|---|
| Assignment-driven `ASSIGNED` | Yes | Visible creator, assignee, followers | Existing configured assignment-email rules only; access checked when queued and sent. |
| Pending states | Yes | Visible creator, assignee, pending owner, followers | No default workflow email. |
| Resolved, reopened, closed, cancelled | Yes | Visible creator, assignee, followers; pending owner while applicable | No default workflow email. |
| Resolve & Close / escalation-parent auto-close | One event for each state move | Same visibility-scoped recipients | No default workflow email. |

`TICKET_WORKFLOW_TRANSITION` events are intentionally not handled by the email processor. This gives operators predictable in-app lifecycle notices without turning every status change into external mail. Ticket creation and configured assignment emails re-check active identity and ticket visibility at delivery time; invalid recipients cause the queued item to be marked `SKIPPED`.

Add one entry whenever implementation work starts, stops, becomes blocked, or is completed.

| Date | Work item | Status after work | Summary | Tests/evidence | Next action |
|---|---|---|---|---|---|
| 2026-09-05 | Phase 8 / TWF-021–TWF-022 | `DONE` | Completed targeted regression coverage across ticket creation, SLA workflow, notification confidentiality, confirmation, archive/restore, and release compatibility. Clean SQLite migration reached `0177_ticket_archive`. Corrected release compatibility metadata and shortened the 0176 revision identifier to fit Alembic’s default version column. Restored frontend dependencies so direct TypeScript/Vite tooling works in this workspace path. | Full backend suite identified and corrected two release-metadata failures; release compatibility suite, Ruff, Mypy, clean migration, frontend tests, and TypeScript/Vite build gates passed. | Controlled deployment package and production-copy upgrade rehearsal. |
| 2026-09-05 | Phase 7 / TWF-020 | `DONE` | Replaced bulk hard deletion with archive metadata and audit history. Archived tickets are excluded from normal queues while retaining their SLA, comments, attachments, relationships, and history. Added authorized, version-checked restore. Purge remains deferred because DEC-005 retention terms are not approved; there is no ordinary purge endpoint. | Full ticket suite passed; Ruff and Mypy passed. Migration `0177_ticket_archive` added. | Begin Phase 8 / TWF-021. |
| 2026-09-05 | Phase 6 / TWF-017–TWF-019 | `DONE` | Contract candidates load from any available client entitlement context. The creation form stages and uploads initial evidence with unique attachment operation keys after durable ticket creation, surfacing any retryable upload failure on the ticket. Ticket edits now accept client, branch, requester, contract, and catalog changes as one final-state validation transaction. | Existing ticket backend suite passed; Ruff and Mypy passed. Frontend production build remains environment-blocked by the repository TypeScript path resolution. | Begin Phase 7 / TWF-020. |
| 2026-09-05 | Phase 5 / TWF-014–TWF-016 | `DONE` | Required open tasks and unchecked checklist items block resolution and closure with structured blockers. Administrators may override only with an audited reason and the readiness-override permission. Added customer-confirmation evidence (channel, contact, note, actor, timestamp); portal confirmation records portal evidence automatically. Reopen behavior was already completed under TWF-015. | Focused readiness and portal-confirmation tests passed; Ruff and Mypy passed. Migration `0176_workflow_readiness_confirmation` added. | Begin Phase 6 / TWF-017. |
| 2026-09-05 | Phase 4 / TWF-012 | `DONE` | Finished fail-closed creation/reassignment recipient scoping. Queue and delivery-time checks require active, unambiguous application identities that retain ticket access. Added regression coverage for non-visible users, client/department/team scoped visibility, unknown addresses, inactive/shared addresses, reassignment rules, and post-queue revocation. | Full targeted ticket, workflow, concurrency, notification, and email-delivery suite passed; Ruff and Mypy passed. | Begin Phase 5 / TWF-014. |
| 2026-09-05 | Phase 4 / TWF-013 | `DONE` | Added the shared transition outbox publisher. Normal single and bulk transitions, assignment-driven status moves, and automatic escalation-parent resolution/closure persist metadata-only events atomically with status history and notify only access-authorized creator, assignee, pending-owner, and follower accounts. Resolve & Close publishes both lifecycle moves. Formalized in-app-first channel matrix and delivery-time revocation policy. | 59 targeted ticket/workflow/concurrency/notification tests plus 12 email/notification delivery tests passed; Ruff and Mypy passed. | Complete TWF-012 confidentiality coverage. |
| 2026-09-05 | Phase 4 / TWF-012 | `IN PROGRESS` | Added fail-closed recipient filtering to creation and reassignment email rules using the existing ticket visibility policy. Covered unauthorized employee creation alerts, unknown and unauthorized To/CC addresses, authorized delivery, and minimized default previews. | All 5 notification tests passed; targeted Ruff and full application Mypy passed. | Complete scope/inactive/shared-address/reassignment cases and in-app recipient review, then implement TWF-013. |
| 2026-09-04 | Phase 0 | `DONE` | Audited ticket creation, edit, SLA, transition, permissions, notifications, bulk processing, and frontend creation flow. Created remediation backlog. | Existing targeted ticket suite passed. | Start TWF-001. |
| 2026-09-04 | TWF-002 | `IN PROGRESS` | Added configurable creation/assignment start modes, immutable clock start snapshots, real public employee-comment completion, and an audited settings control. Existing SLA history is labeled as legacy by migration. | 13 focused backend tests passed; Ruff passed; clean Alembic upgrade reached `0171_first_response_mode`; frontend type-check/build output generated. | Integrate successfully sent outbound email/approved channels with `record_first_response()`, add localized labels, then complete full regression. |
| 2026-09-04 | TWF-001 | `DONE` | Centralized pending responsible-party defaults, corrected `PENDING_CLIENT` to `CUSTOMER`, retained internal/vendor contractual ownership as `MILLENSYS`, rejected incompatible explicit values, and passed the value through bulk transitions. | 27 SLA/workflow tests passed; Ruff passed. | Proceed to DEC-001 and TWF-003 while TWF-002 awaits an approved engineer-authored outbound channel. |
| 2026-09-04 | TWF-003 | `IN PROGRESS` | Implemented the approved resolution stop event. Normal Resolve and Resolve & Close complete SLA at `RESOLVED`; later Close is idempotent and preserves the original completion timestamp. | 58 SLA/workflow/ticket tests passed; Ruff passed. | Implement versioned reopen segments with TWF-015 so prior resolution evidence is never overwritten. |
| 2026-09-04 | TWF-003 / TWF-015 | `DONE` | Added immutable resolution history on reopen, including narrative, causes, outcome/fix data, completion timestamps, and the complete SLA outcome snapshot. Reopen clears stale active resolution fields, restarts the active resolution clock, and exposes authorized history retrieval. | 21 focused SLA/migration/compatibility tests passed; Ruff passed; clean migration reached `0172_resolution_history`. | Start TWF-004 SLA-safe material ticket edits. |
| 2026-09-04 | TWF-004 / TWF-006 | `IN PROGRESS` | Audited the edit transaction, preserved the current/explicit preferred contract, added a dedicated SLA re-evaluation reason, and blocked SLA-relevant edits from leaving active clocks stale until atomic versioned replacement is available. Non-SLA classification edits remain unaffected. | 43 SLA/ticket tests passed; Ruff passed. | Add immutable SLA-change segments, preview the target consequence, and atomically replace the active clocks. |
| 2026-09-04 | TWF-004 | `IN PROGRESS` | Replaced the temporary rejection with an atomic SLA re-evaluation service. Material edits now resolve the edited entitlement and target, preserve the prior clock evidence in an SLA audit record, retain a completed first response, and restart the active obligation at one effective timestamp. Dashboard and single-ticket calculations now honor the clock's versioned start anchor, with compatibility fallback for legacy inconsistent rows. | 43 focused SLA/ticket tests passed; Ruff passed. | Add a server-authoritative before/after preview and require UI confirmation before submission. |
| 2026-09-05 | TWF-004 | `IN PROGRESS` | Added a read-only, permission-checked and concurrency-checked SLA edit preview endpoint. It resolves the proposed entitlement without mutating the ticket and reports changed fields plus old/new contract, policy, target, first-response minutes, resolution minutes, match reason, and effective timestamp. Extended the material-edit regression test to verify the preview matches the target applied by the atomic edit transaction. | 43 focused SLA/ticket tests passed; Ruff and Mypy passed. | Wire the preview into the ticket edit dialog as a required before/after confirmation step. |
| 2026-09-05 | TWF-004 | `DONE` | Connected the server-authoritative preview to the ticket edit workspace. SLA-impacting edits now pause for a clear before/after confirmation and a mandatory audit reason; ordinary edits continue directly. The confirm action submits the same versioned payload reviewed by the user. | 43 focused SLA/ticket tests passed; Ruff, Mypy, and production frontend build passed. | Begin TWF-005 shared create/edit validation and priority derivation. |
| 2026-09-05 | TWF-005 | `IN PROGRESS` | Extracted a common ticket context validator and applied it to create and material edit operations. It enforces active ticket type, product, module, environment, service, category, and subcategory records; client/branch and requester/client relationships; product/module and service/module relationships; and stable error codes. Existing inactive historical context is not revalidated unless an edit changes that context. | Focused edit-validation test passed; Ruff and Mypy passed. | Expand shared validation to imports and centralize authorized priority derivation. |
| 2026-09-05 | Phase 1 / TWF-003 | `DONE` | Added the remaining cancellation lifecycle coverage and verified the full Phase 1 behavior: pending ownership, configurable first response, resolution completion at resolve/close/cancel, atomic SLA re-evaluation, and immutable resolution history on reopen. | 67 ticket/workflow/concurrency/notification/SLA tests passed; Ruff and Mypy passed. | Continue Phase 2 / TWF-005. |
| 2026-09-05 | Phase 2 / TWF-005–TWF-008 | `DONE` | Completed the common live ticket-context validator and automatic priority derivation. Live employee, portal, API, email, and iTop paths use `create_ticket()`; the legacy CSV importer intentionally preserves historical references without applying current active-record checks. Confirmed preferred-contract evaluation and candidate listing, centralized `ticket.resolve.any` authorization for allowed/single/bulk transitions, and formalized ticket statuses as system-controlled codes with label/color-only administration. | 68 ticket/workflow/SLA/contract tests passed; Ruff and Mypy passed. | Begin Phase 3 / TWF-009 idempotency. |
| 2026-09-05 | TWF-009 | `IN PROGRESS` | Added `creation_idempotency_key` and request-fingerprint evidence to tickets, with a filtered unique index across actor, source channel, and operation key. Identical retries return the original ticket; conflicting payload reuse returns a stable conflict once callers provide the key. | Ticket suite passed; Ruff and Mypy passed. | Add retry/conflict coverage and send keys from employee creation UI; then start TWF-010. |
| 2026-09-05 | Phase 3 / TWF-009–TWF-011 | `IN PROGRESS` | Employee and portal creation reuse a client-generated creation key; database uniqueness also covers concurrent requests. Bulk assignment/status now require each selected ticket's expected version and reject the atomic action if any item is stale. Comments and attachments support durable operation keys; attachment retries verify key, hash, size, and filename. Monitoring, API, email, Outlook, and iTop paths derive keys from durable external event IDs. | Ruff, Mypy, Alembic upgrade to 0175, ticket creation idempotency test, and concurrency suite passed. | Add direct comment/attachment replay tests and finish a complete frontend production build confirmation. |
| 2026-09-05 | Phase 3 / TWF-009–TWF-011 | `DONE` | Completed durable creation keys for employee, portal, monitoring, API, email, Outlook, and iTop ticket creation. Bulk assignment/status use atomic per-ticket expected versions. Comments and attachments use operation keys; attachment replays validate content hash, size, and filename. Portal and employee comment forms retain the key until success. | Ruff and Mypy passed; SQL Server migration upgraded through 0175; creation/comment/attachment replay and bulk concurrency tests passed; frontend TypeScript check passed. | Begin Phase 4 / TWF-012 notification recipient scoping. |
| 2026-09-05 | Phase 4 / TWF-012 | `IN PROGRESS` | Removed the unconditional `TICKET_CREATED` broadcast to all active employees. Creation notifications now remain with the assignee and explicitly configured email rules; the default email content is ticket-reference-only with an authorized deep link. | Ruff and Mypy passed; assigned-engineer notification regression passed. | Add non-visible-recipient confidentiality test, then implement TWF-013 transition notification event matrix. |

## Stop/handoff template

Copy this section into the work log whenever work pauses:

```text
Date/time:
Active work item:
Current status:
Files changed:
Completed:
Remaining:
Tests run and results:
Known failures/blockers:
Database migration state:
Exact next action:
```

## Definition of done for the complete initiative

- Every work item is `DONE` or explicitly `DEFERRED` with approval.
- Ticket behavior is consistent across portal, employee, API, single, and bulk paths.
- SLA events reflect actual contractual milestones and remain historically auditable.
- Permissions and notification recipients respect ticket visibility.
- Retried and concurrent operations do not duplicate or silently overwrite data.
- Operational deletion uses archive; purge follows approved retention controls.
- Clean-install, upgrade, backend, and frontend verification pass.
- Release notes, configuration guidance, and operational monitoring are complete.
