# Engineer Pre-Ticket and Support Assistant

Last updated: 2026-09-05  
Owner: Product / Engineering  
Status: `IMPLEMENTED — STAGING/UAT AND CONFIGURATION PENDING`

## Outcome

Deliver an **Engineer Pre-Ticket** workflow: Technical Support submits a minimal pre-ticket request; Call Center validates it and converts it into an official Support Hub ticket through the existing ticket-creation service.

After the Pre-Ticket workflow is stable, deliver a lightweight, optional **Support Assistant**: a sticky mini-console connected directly to Support Hub. It helps support engineers handle daily operational work without repeatedly opening the full management interface. It is **not an AI/LLM chatbot**, does not introduce a separate ticket workflow, and remains inside the Support Hub security and business-rule boundary.

## Approved sequencing

| Release | Scope | Status |
|---|---|---|
| A | Pre-Ticket foundation: schema, feature flag, permissions, lifecycle, audit | `IMPLEMENTED in 1.60.0` |
| B | Engineer form, scoped lookup, contact creation, My Pre-Tickets | `IMPLEMENTED; inline Add Contact is source-only pending 1.60.1` |
| C | Call Center queue, claim, information request, termination, ticket conversion | `IMPLEMENTED in 1.60.0` |
| D | Notifications, timing report, UAT and release readiness | `IMPLEMENTED IN SOURCE; staging UAT remains` |
| E | Support Assistant foundation and compact working queue | `PROTOTYPE IN SOURCE — REQUIREMENTS REVISED` |
| F | Complete ticket actions, notifications, sticky-window UX and personal ordering | `IMPLEMENTED IN SOURCE — UAT PENDING` |

Do not release Support Assistant before Releases A–D meet acceptance criteria.

## Current delivery status — 2026-09-05

### Packaged: SupportHub 1.60.0

- Release ZIP: `releases/SupportHub-1.60.0.zip`.
- Database head: `0180_pre_ticket_messages`.
- Includes the feature policy, permissions, migrations, Engineer Pre-Ticket form and list, self-service confirmation, Call Center queue/lifecycle, conversion to the original creator, audit evidence, in-app notifications, and timing summary.
- Verification passed: 368 backend tests, 47 frontend tests, lint, type checks, production build, standalone runtime, and ZIP integrity.

### Packaged: SupportHub 1.60.1

- Inline **Add Contact** action in the Pre-Ticket form; newly created Contact is selected automatically.
- Additional automated Call Center lifecycle test.
- Pre-Ticket staging UAT checklist in `docs/RELEASE_SMOKE_TEST.md`.
- Queue local search, ten-item paging, and CSV export for users with the report permission.
- Guided Fast Create profile editor in Feature Policy control: select the default Ticket Type and map P1–P4 to Impact/Urgency before the feature can be enforced.
- English and Arabic labels for the new queue and Fast Create controls.

These additions are included in `releases/SupportHub-1.60.1.zip`.

### Packaged: SupportHub 1.60.2

- Call Center queue search and paging now execute on the server. The response carries the filtered total count, so paging remains accurate beyond the initial result set.
- Queue CSV export is generated on the server and includes every matching search result, not just the visible page.
- Call Center can filter the queue and export by lifecycle status directly from the UI.
- Pre-Ticket creation, My Pre-Tickets, Call Center queue, actions, and lifecycle dialogs now have English and Arabic labels.
- Personal Call Center queue views can save, apply, and delete a named search and status-filter combination. This adds database migration `0181_pre_ticket_queue_views`.
- Automated coverage verifies a scoped queue search, returned total, and page result.

These changes advance the database head to `0181_pre_ticket_queue_views` and are included in `releases/SupportHub-1.60.2.zip`.

### Not implemented / not approved

- Real Fast Create configuration: the default Ticket Type and P1–P4 to Impact/Urgency mappings are intentionally not selected or enabled.
- Production profile assignments for the new `ticket.pre_ticket.*` permissions.
- Staging UAT, production-copy upgrade rehearsal, and production enablement.

## Architecture decisions

1. Support Hub is the source of truth for tickets, contacts, workflow, SLA, permissions, audit, notifications, and presence.
2. A Pre-Ticket is not a ticket and never starts ticket SLA clocks.
3. Conversion calls existing `create_ticket()` and standard ticket validation. No duplicate ticket model or simplified creation path is allowed.
4. “Caller” means the existing `Contact`; conversion uses the same `requester_contact_id` unless an authorized processor deliberately changes it.
5. Current official ticket priority is derived from Impact and Urgency. Pre-Ticket stores a **proposed priority** (`P1`–`P4`) as evidence; it must not directly override `Ticket.priority`.
6. Feature data, actors, permissions, owner, state, and timestamps are always server-derived or server-validated.
7. Existing ticket-form settings can inform matching optional fields only. Required Pre-Ticket fields cannot be hidden.
8. Customer Portal users have no Pre-Ticket access in this scope.

## Existing components to reuse

| Need | Existing capability | Rule |
|---|---|---|
| Session and presence | Auth context, refresh flow, `/auth/presence`, notification WebSocket | Reuse unchanged |
| Ticket creation | `create_ticket()` and ticket-context validation | Call only during conversion |
| Ticket retries | `creation_idempotency_key` | Derive conversion key deterministically |
| Ticket access | `ensure_ticket_access()` | Apply to resulting-ticket links/actions |
| Caller | `contacts` model and contact APIs | No Pre-Ticket-specific caller table |
| Audit and notifications | Audit log and outbox services | Reuse; do not create parallel systems |
| UI | React, React Query, MUI, English/Arabic locale files | Translation keys required |

## Release A — Pre-Ticket foundation

### Feature flag and permissions

Add governed system Feature Policy `engineer_pre_ticket`, defaulting to `OFF` on upgrade.

- `feature_policy.manage` is required to change it and the change is audited.
- When disabled, mutable APIs reject server-side; history remains readable to authorized users.

Add a governed `pre_ticket_fast_create_profile` configuration. It is disabled by default and contains:

- one active default Ticket Type;
- an approved mapping for every proposed priority (`P1`–`P4`) to official Impact and Urgency;
- the configuration version used for each conversion.

Fast Create is unavailable until the profile is complete and active. Changing the profile is restricted to `configuration.manage`, audited, and affects only later conversions.

Add narrowly scoped permissions:

| Permission | Purpose |
|---|---|
| `ticket.pre_ticket.create` | Submit Pre-Ticket |
| `ticket.pre_ticket.view.own` | Read own Pre-Tickets |
| `ticket.pre_ticket.queue.view` | Read Pre-Ticket queue/detail |
| `ticket.pre_ticket.queue.process` | Claim, request information, reject, cancel, convert |
| `ticket.pre_ticket.report` | Read aggregated Pre-Ticket reporting |
| `ticket.pre_ticket.fast_convert.self` | Confirm and convert the actor's own eligible Pre-Ticket into a self-assigned ticket |

Call Center conversion requires `ticket.create` and assigns only to the Pre-Ticket creator through this controlled workflow; it does not grant general engineer-assignment capability. Fast self-conversion additionally requires `ticket.create` and `ticket.assign.self`. These do not imply client, user, configuration, ticket-admin, or audit-admin permissions.

### Migration and model

Create `engineer_pre_tickets` with project-standard ID, UTC timestamps, and optimistic `version`.

| Field | Rule |
|---|---|
| `pre_ticket_number` | Unique server-generated value, e.g. `PRE-000001` |
| `status` | Controlled lifecycle state |
| `client_id`, `requester_contact_id`, `product_id` | Required and validated active/scope-safe references |
| `proposed_priority` | Required `P1`–`P4` |
| `title` | Required, normalized ticket-subject constraints |
| `initial_description` | Server sets from title; immutable submitted evidence |
| `enriched_description` | Nullable Call Center addition; never replaces initial evidence |
| `submitted_by_user_id`, `submitted_at` | Server-set |
| `claimed_by_user_id`, `claimed_at` | Nullable |
| `converted_by_user_id`, `converted_at`, `resulting_ticket_id` | Nullable; resulting ticket ID unique |
| `conversion_mode` | Nullable until conversion; `CALL_CENTER` or `SELF_SERVICE` |
| terminal reasons | Required for Needs Information, Reject, or Cancel as applicable |
| `idempotency_key`, `request_fingerprint` | Retry-safe, unique within submitter scope |

Use `audit_logs` for lifecycle evidence. Add a separate event table only if reporting cannot be supported from records and audit history.

### Lifecycle

```text
SUBMITTED → CLAIMED → CONVERTED
     │
     └──────────────→ CONVERTED  (Fast Create or Call Center direct conversion)
             ↕
     NEEDS_INFORMATION

SUBMITTED or CLAIMED → REJECTED
SUBMITTED or CLAIMED or NEEDS_INFORMATION → CANCELLED
```

- Only `SUBMITTED` can be claimed.
- Claim uses version checking/atomic update; only one processor can succeed.
- A direct conversion from `SUBMITTED` atomically records the processor claim and conversion in one transaction.
- Needs Information requires a message and permits the submitting engineer to respond/amend.
- Rejected, Cancelled, and Converted are terminal.
- Converted requires exactly one resulting ticket.
- Do not expose a generic status-update endpoint.

### Release A acceptance

- Flag defaults off; disabled mutation is rejected.
- Permission, unique number, retry, lifecycle, stale-version, and audit tests pass.
- Title is trimmed; `initial_description` equals normalized title server-side.
- Fast Create profile validation rejects inactive Ticket Types or incomplete P1–P4 mappings.

## Release B — Engineer Pre-Ticket workflow

### Form

Location: `Tickets → Engineer Pre-Tickets`.

Required fields, and only these fields:

1. Client
2. Caller / Contact
3. Product
4. Proposed priority
5. Title

Description is not entered; the server derives it from Title. Ticket type, service, contract, assignment, Impact, and Urgency belong to final ticket registration.

### Lookup and contact rules

- Client lookup follows current user/client visibility; backend verifies access.
- Contact lookup is restricted to the chosen Client; mismatched crafted requests are rejected.
- Product must be active and allowed by current rules.
- A browser-generated idempotency key is reused for a submit retry.
- Add Contact uses the existing contact model and contact-create permission; unauthorized requests fail server-side.
- The new contact dialog uses selected Client context and includes full name plus supported phone/email fields.
- Existing duplicate checks or a documented client-plus-phone/email rule must run before creation.
- After contact creation, it is automatically selected in the Pre-Ticket form.

### My Pre-Tickets

Display number, client, contact, product, proposed priority, title, submitted time, status, claim owner, and a resulting-ticket link only when normal ticket access permits it.

### Fast Create Ticket

An engineer with `ticket.pre_ticket.fast_convert.self`, `ticket.create`, and `ticket.assign.self` may use **Confirm & Create Ticket** on their own Pre-Ticket when it is `SUBMITTED` and has not been claimed by Call Center.

The confirmation dialog clearly states:

> An official ticket will be created, assigned to you, and its SLA will start now.

This is a fast path, not a validation bypass. The server must:

1. Re-read and lock the Pre-Ticket; validate feature flag, owner, status, version, and all three permissions.
2. Apply a governed Fast Create profile containing the required Ticket Type and approved proposed-priority-to-Impact/Urgency mapping.
3. Call `create_ticket()` with the selected Client, Contact, Product, Title, initial description, mapped Impact/Urgency, `assigned_user_id = actor.id`, and `assigned_team = actor.department` where supported.
4. Use `source_channel = ENGINEER_PRE_TICKET` and a deterministic self-conversion idempotency key.
5. Link the created ticket, set `conversion_mode = SELF_SERVICE`, set status `CONVERTED`, and write audit evidence in one transaction.

The button is unavailable, with an explanatory message, when the Fast Create profile is incomplete, the Pre-Ticket is claimed/terminal, or the actor lacks a required permission. In those cases the normal Call Center process remains available.

### Release B acceptance

- Required fields and scopes are backend-tested.
- Authorized contact creation creates a normal Contact; unauthorized creation is rejected.
- Retry returns original Pre-Ticket only.
- My Pre-Tickets cannot expose another submitter’s records.
- Fast Create Ticket creates one self-assigned official ticket only, starts SLA at ticket creation, and returns that ticket on a repeated confirmation/retry.
- Fast Create is rejected for another user's Pre-Ticket, a claimed Pre-Ticket, an incomplete governed profile, or a stale version.

## Release C — Call Center queue and conversion

### Queue

Location: `Tickets → Call Center Pre-Ticket Queue`.

- Server pagination and oldest-first default.
- Search by Pre-Ticket number, title, client, or contact.
- Filter by status, submitted range, engineer, and client.
- Show age, proposed priority, claim owner, and validation warnings.
- View requires `ticket.pre_ticket.queue.view`; actions require `ticket.pre_ticket.queue.process`.

### Actions

| Action | Rule |
|---|---|
| Claim | Atomic `SUBMITTED → CLAIMED` |
| Needs Information | `CLAIMED → NEEDS_INFORMATION`; mandatory message |
| Engineer response | Only submitter while Needs Information; preserve initial evidence |
| Reject | Valid non-terminal state; mandatory reason |
| Cancel | Valid non-terminal state; mandatory reason and authority |
| Convert & Assign to Creator | `SUBMITTED` or processor-owned `CLAIMED` record; expected version and idempotency required. From `SUBMITTED`, claim and conversion are atomic. |
| Confirm & Create Ticket | Owner-only self-service conversion from unclaimed `SUBMITTED`, with the Fast Create permission/profile |

### Conversion API contract

`POST /pre-tickets/{id}/convert` accepts:

- `expected_version`
- `conversion_idempotency_key`
- standard `TicketCreate` fields required beyond Pre-Ticket data
- optional authorized Contact replacement
- description enrichment
- final official Impact and Urgency, or an approved conversion mapping input

The resulting ticket is not selected from an engineer picker: it is assigned directly to `submitted_by_user_id` (the Pre-Ticket creator) and uses that user's department/team where supported.

Transaction steps:

1. Lock/re-read Pre-Ticket and validate state, claim authority, flag, permission, and version. A Call Center processor may convert an unclaimed `SUBMITTED` record; the action records their claim and conversion atomically. A claimed record can only be converted by its claim owner.
2. Validate final Contact/Client relationship and all official ticket inputs.
3. Confirm that the Pre-Ticket creator is an active, eligible employee. Call `create_ticket()` with `source_channel = ENGINEER_PRE_TICKET`, `assigned_user_id = submitted_by_user_id`, and that user's department/team where supported.
4. Use a deterministic ticket idempotency key based on Pre-Ticket ID plus conversion key.
5. Persist link, actor, timestamp, enrichment, and `CONVERTED` state.
6. Commit once; rollback everything on failure.

If already converted, return the linked ticket. Never create a second ticket.

### Approved priority policy

The governed Fast Create profile maps proposed P1–P4 to official Impact/Urgency. Call Center may review/change the official Impact/Urgency during standard conversion only when the existing ticket permission model allows it; the submitted proposed P-level remains immutable evidence and the final values are audited.

### Release C acceptance

- Concurrent claim/conversion gives one success and clean conflict to others.
- Ticket-validation failure leaves Pre-Ticket unconverted.
- If the Pre-Ticket creator is inactive or cannot receive the assignment, conversion is blocked with a clear reason; Call Center must resolve the ownership issue before conversion.
- Converted ticket runs normal validation, entitlement, audit, notification, and SLA behavior.
- Ticket SLA starts at official ticket creation, never Pre-Ticket submission.
- Contact ID is retained unless an authorized final change is supplied.
- Pre-Ticket reference is visible only to authorized internal users; not the client portal.
- Call Center conversion assigns the resulting ticket to the Pre-Ticket creator and records `CALL_CENTER` conversion mode. Self-service conversion assigns it to the authenticated engineer and records `SELF_SERVICE` conversion mode.
- Ticket schemas, analytics, integrations, and source filters recognize `ENGINEER_PRE_TICKET`; migration/compatibility tests cover the value.

## Release D — notifications, reporting, readiness

### Notifications

- Call Center: new Pre-Ticket submitted.
- Submitting engineer: claim, needs information, rejection, cancellation, and conversion.
- Queue and delivery recipients must pass current visibility checks.

### Metrics

Report separately from ticket SLA:

- Pre-Ticket-to-claim
- Claim-to-ticket-registration
- Pre-Ticket-to-ticket-registration
- Volume and aging by status, client, product, proposed priority, and submitting team where permitted

Never label these as ticket response or resolution SLA.

### Release D acceptance

- Notification access checks and reporting visibility tests pass.
- Audit reconstructs all lifecycle actions.
- Clean migration, upgrade rehearsal, full regression, and controlled UAT conversion walkthrough pass.

## Support Assistant

### Product boundary

The Support Assistant is a lightweight, optional operational mini-console connected directly to Support Hub. It is intended primarily for support engineers and must remain small, fast, action-oriented, and focused on the work that needs attention now.

The Support Assistant:

- Uses the same authentication, session expiration, permissions, department/team/client visibility, database, services, ticket lifecycle, SLA calculations, notifications, and audit history as Support Hub.
- Uses existing ticket APIs and services wherever possible. It must not duplicate or bypass ticket, assignment, visibility, escalation, SLA, or audit business logic.
- Reflects changes made in the full Support Hub and writes normal ticket history/audit records for every Assistant action.
- Is not a second ticketing system, a separate workflow, or an AI/LLM chatbot.
- May remain open independently from the full management interface while still using the existing authenticated Support Hub session; it must not require a second login or maintain a duplicate identity/session model.

Design principle:

> **Support Hub = full management system**  
> **Support Assistant = fast engineer operational console**

### Release E — focused working queue

The existing `/support-workspace` route is the source prototype for the Assistant. It is not final acceptance of the revised Assistant scope.

The main interface displays the engineer's relevant tickets as compact cards. Each card shows:

- Ticket Number
- Client
- Title
- Priority
- Status
- SLA status and remaining time

The working queue prioritizes operational flow rather than dashboard analytics. It gives quick access to:

- New / Unassigned
- Assigned to Me
- In Progress
- Follow-up Required
- Near SLA Breach

Priority and SLA risk must be visually obvious without making the interface noisy. Lists use compact paginated DTOs and the existing ticket-visibility and assignment engines.

The primary lifecycle is immediately accessible from the card:

`Assign to Me` → `Start Progress` → `Resolve`

Available actions adapt to the current ticket status and the authenticated user's existing permissions. The UI must never display an action as available when the backend would reject it under the same known state, while the backend remains the final authorization authority.

### Quick ticket actions

From a ticket card or its keyboard-accessible context menu, an authorized engineer can:

- Assign the ticket to themselves.
- Start Progress.
- Resolve the ticket, including the required resolution fields and provided service selection.
- Add a public comment.
- Add an internal comment.
- Open the customer/contact in WhatsApp when a valid number is available.
- Copy or send the Customer Rating Link.
- Copy or send the Live Ticket Update Link.
- Hand over the ticket to another authorized engineer or team.
- Escalate the ticket.
- Link the ticket to another ticket.
- Open the complete ticket in Support Hub.

Double-clicking a card opens the ticket-details dialog or the complete ticket. An equivalent single-click/keyboard action is required for touch and accessibility.

### Sticky mini-console experience

The Assistant is designed as a compact operational window that can remain available while the engineer works in other applications. It supports:

- Minimize.
- Compact and expanded modes.
- Refresh/reconnect.
- An independently opened Assistant window from the existing authenticated Support Hub session.
- Always-on-top/sticky behaviour where the selected browser/runtime safely supports it. When the platform cannot guarantee always-on-top, the supported fallback is a compact independent window; the application must not claim an unsupported browser capability.

At login, an enabled user can optionally be offered **Open Support Assistant**. Closing or declining the Assistant does not affect normal Support Hub access.

### Live updates and notifications

The Assistant acts as a lightweight operational notification center. Existing notification WebSocket and presence/session mechanisms must be reused. Relevant cards and counters update for:

- New ticket.
- Assignment or reassignment.
- Escalation.
- New public or internal comment, subject to comment visibility permissions.
- SLA warning or changed SLA state.
- Ticket handover.
- Status, priority, follow-up, or resolution changes made in Support Hub.

Bounded polling is recovery only. Reconnection must refresh affected queue data so missed events do not leave stale cards.

### Personal working order

Engineers may organize their immediate working queue through per-user pinning and personal ordering. Drag-and-drop can be provided, but it must have an accessible keyboard/touch alternative. Personal order never changes global ticket order, priority, assignment, SLA, or another user's view.

### Release E acceptance

- The compact queue displays the required card fields and correct visibility-scoped records.
- Assign to Me, Start Progress, Resolve, and Open Complete Ticket use the existing authorized lifecycle services.
- The Assistant shares the existing login/session and reacts correctly to logout and session expiration.
- Changes from either interface become visible in the other without a full Support Hub refresh under normal connected operation.
- English and Arabic layouts, compact/expanded modes, keyboard navigation, touch operation, and supported screen sizes pass controlled UAT.
- Audit and ticket history are indistinguishable from the same actions performed through the full ticket interface.

### Current source status — 2026-09-06

The `/support-workspace` implementation now provides Queue, Mine, Unassigned, In Progress, Follow-up, SLA Risk, and Pre-Tickets in the normal authenticated application. Ticket cards show ticket number, client, title, priority, localized status, and available SLA time. The primary lifecycle reuses the existing self-claim and status-transition endpoints for **Assign to Me** and **Start Progress**, and opens the existing validated resolution dialog for **Resolve**. The keyboard-accessible card menu routes public/internal comments, handover, escalation/help, ticket linking, contact/WhatsApp, and full-ticket work into the existing ticket components; rating and live-update links reuse the existing send-actions dialog. WebSocket notification events refresh the Assistant, bounded polling recovers missed events, and offline/reconnect state is handled. Per-user pinning is persisted through audited, visibility-validated preference API and migration `0186_support_assistant_prefs`. Refresh, compact/expanded display, independent-window opening, double-click, and keyboard ticket opening are implemented. Native always-on-top remains unavailable to a normal browser and uses the documented compact independent-window fallback.

### Related 2026-09-06 operational enhancements

- The Top 3 Support agents widget now uses an independent month-to-date Resolution query and is no longer affected by the dashboard's visible period, date-basis, or business filters. Ranking remains resolved/closed count first, fewer SLA breaches second, then agent name.
- Ticket deletion is now approval-based. A request leaves the ticket active; approval by a different authorized user archives it. Archived tickets are excluded from normal queues, appear under the Tickets **Trash** tab, retain their evidence/audit history, and can be restored by a separately authorized user.
- Migration `0185_ticket_delete_approval` adds the request ledger and separate request, approve, Trash-view, and restore permissions.
- These changes are source-only. Release packaging remains deferred by request.
- Follow-up hardening makes the Approvals tab aggregate entitlement and deletion approvals, returns ticket/requester context in deletion cards, filters Trash rows in SQL through the existing ticket-visibility engine, notifies the requester after the decision, and verifies capability-only Support Assistant entry with frontend tests.
- The Top 3 widget now reads a dedicated lightweight `/dashboards/top-support-agents` endpoint. The endpoint fixes its contract to the current local calendar month through now, uses Resolution as its date basis, applies the authenticated dashboard ticket scope, includes active Support-department employees only, and ranks by resolved count, then fewer resolution-SLA breaches, then agent name.
- Deletion submission is retry-safe: identical retries return the existing pending request, competing requests conflict cleanly, and a SQL Server/SQLite filtered unique index prevents more than one pending request per ticket.

### Source completion verification — 2026-09-06

- Full backend regression passed after the 0185 changes.
- Ruff and strict MyPy passed across the backend source.
- Frontend ESLint, TypeScript compilation, all 49 frontend tests, and the production Vite compilation passed.
- A clean database migrated from base through `0186_support_assistant_prefs (head)`, including the filtered pending-deletion index and per-user Assistant preferences.
- No release ZIP or standalone runtime was built, as requested.
- The remaining blockers are external evidence or business configuration: Fast Create values/approval, production profile review, production-copy SQL Server rehearsal, and controlled staging UAT.

### Release F — completion and advanced UX

Release F completes any Support Assistant capabilities not delivered in the foundation, including the full quick-action set, SLA Risk, Follow-up with an explicit owner and completion condition, live operational notifications, reusable ticket/Pre-Ticket details, sticky-window refinements, and per-user queue preferences.

Release F scope must be finalized from Release E controlled-UAT evidence. Convenience actions must continue to call the same backend commands used by Support Hub and must not create Assistant-only lifecycle behavior.

## Non-functional requirements

- Use Alembic migration(s), clean-install test, and upgrade test.
- Use server UTC timestamps and existing timezone display conventions.
- Add English and Arabic locale keys for every UI string.
- List endpoints are paginated; card DTOs are lightweight.
- Reuse WebSockets; bounded polling is recovery only.
- Every mutation is backend-authorized, concurrency-safe, idempotent where retried, and audited.
- Preserve history when the feature is disabled; no normal hard-delete of Pre-Ticket evidence.

## Implementation checklist

| Item | Status |
|---|---|
| Configure and approve Fast Create profile: Ticket Type and proposed-priority-to-Impact/Urgency mapping | `OPEN — required before enablement` |
| Confirm rejection/cancellation authority | `DECIDED — restricted to ticket.pre_ticket.queue.process` |
| Confirm which fields engineers may amend after Needs Information | `DECIDED — response message only; submitted structured evidence remains immutable` |
| Release A | `IMPLEMENTED — clean install through 0186 passed; production-copy rehearsal pending` |
| Release B | `IMPLEMENTED — localization complete; controlled UAT pending` |
| Release C | `IMPLEMENTED — pending Call Center UAT` |
| Release D | `IMPLEMENTED IN SOURCE — notifications, export, and expanded timing/aging report delivered; UAT pending` |
| Package server-side queue and personal-view additions as 1.60.2 | IMPLEMENTED — `releases/SupportHub-1.60.2.zip` |
| Pre-Ticket form settings: five always-visible fields, configurable mandatory state, mandatory by default | `IMPLEMENTED — 1.61.0` |
| Persist Module and Service and use them during official-ticket coverage validation | `IMPLEMENTED — 1.61.0` |
| Call Center completion of missing optional context during conversion | `PACKAGED — 1.61.1; UAT pending` |
| Staging UAT and production-copy upgrade rehearsal | `NOT STARTED` |
| Support Assistant focused requirements | `IMPLEMENTED IN SOURCE — controlled UAT pending` |
| Support Assistant operational queues and compact cards | `IMPLEMENTED IN SOURCE — controlled UAT pending` |
| Support Assistant primary lifecycle and quick ticket actions | `IMPLEMENTED IN SOURCE — existing services/dialogs reused; controlled UAT pending` |
| Support Assistant mini-console, synchronization and personal pinning | `IMPLEMENTED IN SOURCE — browser fallback used for always-on-top; controlled UAT pending` |

## Definition of done

Engineer Pre-Ticket is complete only after Releases A–D pass regression, migration and upgrade rehearsal, permission review, and controlled UAT conversion. Support Assistant is a subsequent, optional interface over the same Support Hub workflow and is complete only when its revised functional, session, authorization, synchronization, accessibility, and controlled-UAT criteria pass.

## Continuation handoff — 2026-09-06

### Where work stopped

Development and automated verification of the configurable Pre-Ticket form are complete. The self-contained Windows x64 release is packaged as **SupportHub 1.61.0**. Work stopped before deployment to the target SQL Server/IIS environment and before controlled user-acceptance testing.

Release artifact:

- Package: `releases/SupportHub-1.61.0.zip`
- Size: `43,044,874` bytes
- SHA-256: `F5D3298604CBB0DAB6E91793038D26F1B1625F19D87115420CDD1845D74C674C`
- Packaged database head: `0182_pre_ticket_form_context`
- ZIP integrity verified: `1,783` entries

### What was implemented

1. **Pre-Ticket Form Settings** was added to the existing Ticket Form Settings page.
2. The following five Pre-Ticket context fields are always shown and cannot be hidden:
   - Client
   - Contact
   - Product
   - Module
   - Service
3. Each of the five fields can be configured as mandatory or optional. All five are mandatory by default on migration/seed.
4. Pre-Ticket creation now loads the eligible client contract catalog and provides dependent Product → Module → Service selection.
5. The backend validates that Client/Product/Module/Service records are active, Module belongs to Product, Service is linked to Module, and Contact belongs to Client.
6. `product_module_id` and `service_id` are stored on the Pre-Ticket and passed into official ticket creation. This allows module/service-specific contract coverage rules to match instead of incorrectly reporting no coverage.
7. Migration `0182_pre_ticket_form_context`:
   - Adds nullable `product_module_id` and `service_id` foreign keys to `engineer_pre_tickets`.
   - Makes existing Client, Contact, and Product columns nullable so administrators can make those form fields optional.
   - Seeds the five always-visible, mandatory-by-default Pre-Ticket field settings.
8. Engineer Pre-Tickets remains governed by the `engineer_pre_ticket` Feature Policy. A direct Engineer Pre-Tickets entry was added under Site Settings.
9. A **New Pre-Ticket** fast-action button was added to the Tickets page for users with `ticket.pre_ticket.create`.
10. The SQL Server Pre-Ticket-number insertion issue was fixed by inserting a temporary unique number and replacing it with the final `PRE-######` number after the database ID is allocated.
11. English and Arabic labels were added for the new Module, Service, and Pre-Ticket form-settings interface.

### Verification completed

- Clean database migration reached `0182_pre_ticket_form_context`.
- Ruff passed.
- Strict MyPy passed across 154 backend source files.
- All 374 backend tests passed.
- Frontend ESLint passed.
- All 47 frontend tests passed.
- TypeScript compilation passed.
- Production Vite build passed.
- The packaged `SupportHubBackend.exe --help`, release manifest, database revision, and ZIP were verified.

Existing non-blocking warnings remain: the FastAPI/Starlette `httpx` deprecation warning, frontend React test `act(...)` warnings, Node local-storage warnings, and Vite large-chunk notices.

### Exact next step

1. Back up the target application files and SQL Server database.
2. Deploy `releases/SupportHub-1.61.0.zip` over the existing application using the normal controlled deployment process.
3. From the deployed release directory run:

   ```powershell
   ./backend/runtime/SupportHubBackend.exe migrate
   ./backend/runtime/SupportHubBackend.exe seed
   ```

4. Confirm the migration output reaches `0182_pre_ticket_form_context` and restart the application/IIS site.
5. Sign in with a user that has `configuration.manage`. Open **Site Settings → Ticket Form Settings → Pre-Ticket Form Settings** and confirm all five fields are visible and mandatory.
6. Open **Site Settings → Engineer Pre-Tickets**, configure the Fast Create Ticket Type and P1–P4 Impact/Urgency mappings, then set the system policy to **ENFORCED**. If it is already configured and enforced, verify the existing values instead of replacing them.
7. Give the test engineer the required Pre-Ticket permissions, including `ticket.pre_ticket.create` and `ticket.pre_ticket.view.own`. Give the Call Center test user the queue view/process permissions required by the workflow.
8. Run controlled UAT with a client that has a module-specific coverage rule:
   - Create a Pre-Ticket using the covered Product, Module, and Service.
   - Confirm the saved Pre-Ticket retains all five context values.
   - Convert it through both the engineer self-confirm path and the Call Center path where applicable.
   - Confirm exactly one official ticket is created, assigned correctly, and passes the expected contract coverage rule without the “No matching coverage rule” error.
9. Change one Pre-Ticket field to optional and verify creation works without that field. Before production use of optional context, also verify how the missing official-ticket data will be completed during conversion.
10. Record the production-copy upgrade rehearsal and UAT evidence in this document. If both pass, update Releases A–D and the staging/UAT checklist statuses.

### Known follow-up gap

All five fields default to mandatory, so the normal conversion path is complete. If an administrator makes Client, Product, Module, or Service optional and an engineer omits it, official ticket creation can still require that value because of the normal Ticket Form or contract rules. The next functional enhancement should add a Call Center conversion/edit step for completing missing optional Pre-Ticket context before creating the official ticket. Do not treat the Pre-Ticket optional setting as a bypass of official ticket validation or contract coverage.

## Continuation progress — 2026-09-06

The documented optional-context conversion gap is implemented and packaged in SupportHub 1.61.1:

- Call Center conversion opens a completion dialog for Client, Contact, Product, Module, and Service.
- Values already submitted by the engineer are locked; only missing values can be supplied.
- The backend validates active records and Client/Contact, Product/Module, and Module/Service relationships.
- Completed values are persisted on the Pre-Ticket, passed to the official ticket, and included in conversion audit evidence.
- Engineer self-service confirmation cannot use the Call Center completion capability.
- Normal ticket-form, entitlement, and contract-coverage validation still runs during official ticket creation.
- Regression coverage confirms an all-optional Pre-Ticket can be completed and converted into one official ticket with its completed Module and Service retained.

Verification completed for this continuation:

- Ruff passed for the Pre-Ticket backend and tests.
- strict MyPy passed for the Pre-Ticket backend module.
- all 7 focused Pre-Ticket backend tests passed.
- all 374 backend tests passed.
- frontend ESLint passed.
- all 47 frontend tests passed.
- TypeScript compilation and the production Vite build passed.

Release artifact:

- Package: `releases/SupportHub-1.61.1.zip`
- Size: `43,049,196` bytes
- SHA-256: `DC9CDD6EBF717BC205464DB015EBB04AF82C99DB1CDB35691A889EA5DBB9C401`
- Database head: `0182_pre_ticket_form_context`
- ZIP integrity: `1,783` entries; no generated caches, bytecode, or `node_modules`

Next step: deploy 1.61.1 to staging, run the packaged migration and seed commands, then execute the controlled Pre-Ticket UAT described above. Confirm the covered Product list, optional-context completion, both conversion paths, resulting-ticket coverage, and simplified Configuration sidebar.

### Local packaged upgrade rehearsal

An isolated packaged-runtime rehearsal completed successfully:

1. SupportHub 1.61.0 migrated and seeded a clean rehearsal database through `0182_pre_ticket_form_context`.
2. SupportHub 1.61.1 ran migration and seed against that database without changing the schema head.
3. The 1.61.1 migration and seed commands were repeated successfully, confirming idempotent deployment behavior.
4. The final database revision remained `0182_pre_ticket_form_context (head)`.
5. The packaged frontend contains the context-completion UI, and the source navigator no longer contains the three duplicate Site Settings shortcuts.

This is local package evidence only. A production-copy SQL Server rehearsal and controlled browser UAT remain pending and must not be marked complete from this result.

### Release D reporting completion

The Pre-Ticket report now provides the complete non-SLA operational timing set:

- average Pre-Ticket submission-to-claim time;
- average claim-to-ticket-registration time;
- average Pre-Ticket submission-to-ticket-registration time;
- count and average age grouped by lifecycle status;
- count and average age grouped by Client, Product, proposed priority, and submitting team.

Open items use their current age. Converted items stop aging at conversion, while rejected and cancelled items stop aging at their terminal update. The report remains permission-gated by `ticket.pre_ticket.report` and is explicitly labeled as Pre-Ticket timing rather than ticket response or resolution SLA.

Backend regression coverage verifies the timing fields and Client, Product, priority, and status breakdowns. The reporting changes were not included in SupportHub 1.61.1 and are now packaged in SupportHub 1.61.2.

Historical 1.61.2 handoff: controlled Pre-Ticket staging UAT remained pending at that point. Releases E and F were subsequently implemented in source; use the current implementation checklist and Support Assistant UAT section in `docs/RELEASE_SMOKE_TEST.md`.

### SQL Server multiple-unconverted-Pre-Ticket correction

Production error evidence showed that submitting a second unconverted Pre-Ticket failed with SQL Server error 2627 and an auto-named unique constraint reporting a duplicate NULL. The inserted `pre_ticket_number` was already a unique temporary value; the collision came from the nullable `resulting_ticket_id` column's ordinary unique constraint. SQL Server permits only one NULL under that constraint.

Migration `0183_pre_ticket_result_unique` dynamically discovers and removes the auto-named SQL Server unique constraint on `engineer_pre_tickets.resulting_ticket_id`, then creates a filtered unique index applying only when `resulting_ticket_id IS NOT NULL`. This permits multiple unconverted Pre-Tickets while retaining the invariant that one resulting official ticket cannot be linked to more than one Pre-Ticket. The ORM model uses the same filtered-index definition.

Regression coverage now submits two distinct unconverted Pre-Tickets before converting either, and release compatibility coverage verifies the SQL Server filtered-index migration. Database head advances to `0183_pre_ticket_result_unique`.

SupportHub 1.61.2 now packages this correction together with the expanded Release D report. The self-contained runtime migrated and seeded a clean database through `0183_pre_ticket_result_unique`; all 375 backend tests and all 47 frontend tests passed. The archive contains 1,784 entries with no forbidden generated content.

- Package: `releases/SupportHub-1.61.2.zip`
- Size: `43,055,357` bytes
- SHA-256: `0522D7223C81D74479B7F8EAA9F73C2888E0319FFB7249B0AA72D841443E02AA`

SupportHub 1.61.2 supersedes 1.61.1 for deployment. Production SQL Server backup, controlled migration, IIS restart, and submission of at least two distinct unconverted Pre-Tickets remain required deployment/UAT evidence.

### SQL Server migration-driver correction

The first production attempt to apply migration 0183 from SupportHub 1.61.2 failed before the revision was stamped because the installed `pymssql` SQLAlchemy dialect raises `NotImplementedError` for `get_unique_constraints()`. Migration 0183 now queries SQL Server's system catalogs directly, using the configured default schema and a parameterized schema value, to discover the single-column unique constraint on `resulting_ticket_id`. This preserves support for auto-generated constraint names without relying on an unsupported reflection API.

SupportHub 1.61.3 supersedes 1.61.2. The failed 1.61.2 migration can be followed by the normal 1.61.3 `migrate` and `seed` commands; no manual Alembic repair or constraint lookup is expected.

The 1.61.3 self-contained package passed all 375 backend tests, all 47 frontend tests, and a clean packaged migration/seed rehearsal through `0183_pre_ticket_result_unique`. Archive validation found 1,784 entries and no forbidden generated content.

- Package: `releases/SupportHub-1.61.3.zip`
- Size: `43,052,409` bytes
- SHA-256: `034C84E84C7CA0F9AE2F19C8FCE70910A7420431B216E092AA1EA728991D3268`

### Covered-product lookup correction

### Independent Pre-Ticket creation permission

Pre-Ticket submission is now fully independent from official ticket creation authorization. An employee with `ticket.pre_ticket.create` can load the client options, contacts, Pre-Ticket form settings, and covered contract catalog required by the form and can submit the Pre-Ticket without receiving `ticket.create`. Official ticket creation continues to require `ticket.create`, and conversion continues to apply its existing official-ticket authorization rules.

Regression coverage signs in as an employee granted only `ticket.pre_ticket.create` and `ticket.pre_ticket.view.own`, verifies that `ticket.create` is absent, loads every required form lookup, submits a real Pre-Ticket successfully, and confirms that direct official ticket creation is denied with HTTP 403.

This separation is packaged in SupportHub 1.61.4. All 376 backend tests and all 47 frontend tests passed, and the packaged runtime completed a clean migration and seed through the unchanged head `0183_pre_ticket_result_unique`.

- Package: `releases/SupportHub-1.61.4.zip`
- Size: `43,057,340` bytes
- SHA-256: `5A77352D46B8DDDDAA830433C491034FCAD5DB99DDCF2764566382BA30FCF1D8`

### Covered-product lookup correction

The Pre-Ticket Product field previously appeared empty even when the selected active client had a current active contract with covered products. The contract-catalog API intentionally returns only active products but does not include an `is_active` property in each response item. The Pre-Ticket UI incorrectly filtered the response again using that absent property, removing every product. The redundant frontend filter has been removed for both Pre-Ticket creation and the Call Center context-completion dialog. Contract scoping and active-product filtering remain enforced by the backend catalog endpoint.

### Navigation cleanup

### Independent Convert & Assign permission

The Call Center **Convert & Assign to Creator** action now uses the dedicated `ticket.pre_ticket.convert_assign` permission. It no longer requires `ticket.create` and is no longer bundled into `ticket.pre_ticket.queue.process`. Claim, information request, rejection, and cancellation remain governed by the queue-processing permission, while the conversion button is rendered only for the new permission.

Migration `0184_pre_ticket_convert_perm` creates the permission and grants it to the system Call Center profile for upgrade continuity. Administrators can independently add or remove it from custom profiles. Regression coverage converts a real uncovered Pre-Ticket using an employee who has the new permission but lacks both `ticket.create` and `ticket.pre_ticket.queue.process`.

Source implementation and focused verification are complete. Packaging is deferred by request; no SupportHub 1.62.1 artifact has been built.

### Navigation cleanup

### Uncovered Pre-Ticket conversion approval and resolution service

Pre-Ticket creation now requests the expanded contract catalog so active uncovered products remain selectable and are visibly labeled as uncovered. Submission remains a lightweight intake action and creates no entitlement approval. When either Call Center or an authorized engineer converts an uncovered Pre-Ticket, the normal official-ticket entitlement engine creates the ticket as `PENDING_APPROVAL`, removes assignment until approval, creates the existing entitlement approval record, and notifies the submitting engineer accurately.

The Resolve and Close dialogs now require confirmation of the Service actually provided. The current ticket Service is preselected and can be changed. The transition API validates that the selected Service is active and, when a Product Module exists, linked to that module. A change updates the ticket's governed Service and writes `ticket.resolution_service.changed` audit evidence containing the old and new Service IDs. Older API clients that omit the new field remain compatible, while the interactive UI enforces selection.

Regression coverage verifies both the deferred uncovered approval lifecycle and resolution-time Service change/auditing.

SupportHub 1.62.0 packages both enhancements. All 377 backend tests and all 47 frontend tests passed, and the packaged runtime completed a clean migration/seed rehearsal through `0183_pre_ticket_result_unique`.

- Package: `releases/SupportHub-1.62.0.zip`
- Size: `43,060,905` bytes
- SHA-256: `E5FFE35751DC52880514BCF47798F68EB842FEEB5C6FB6890D38521A80D0F760`

### Navigation cleanup

Engineer Pre-Tickets configuration, Email Integration, and Ticket Form Settings remain available inside Site Settings. Their duplicate shortcuts were removed from the Configuration sidebar group, leaving Site Settings as the single configuration entry. The operational Engineer Pre-Tickets entry under Service Operations remains available to authorized workflow users.
