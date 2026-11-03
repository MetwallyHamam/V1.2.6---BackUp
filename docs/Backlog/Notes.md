# Product Backlog Notes

Last reviewed: 2026-08-28

## Status legend

- `Not Started`: Work has not started.
- `In Progress`: Work is currently being implemented.
- `Blocked`: Work cannot continue until a dependency or decision is resolved.
- `Ready for Testing`: Implementation is complete and awaiting verification.
- `Completed`: Work has been implemented and verified.

## Progress summary

| Status | Count |
|---|---:|
| Not Started | 4 |
| In Progress | 0 |
| Blocked | 0 |
| Ready for Testing | 41 |
| Completed | 0 |

The counts above cover the 45 numbered backlog items through B-46 (B-33 is unused). The B-32 correction and the complete confirmed B-39 icon/request/direct-profile-grant workflow are implemented and verified in the working tree.

## Current stopping point

**B-01** through **B-20** are packaged in **release 1.44.0**. **B-21–B-23** and **B-25–B-28** are packaged in corrected verified **release 1.45.1**. Corrected verified **release 1.47.1** supersedes 1.47.0 and packages B-24, B-29–B-32, B-34–B-37, B-39, B-40, B-42, B-43, the Project Handover workspace-isolation correction, and user permission-source visibility at `0144_handover_cleanup`. **Release 1.48.0** packages B-45. **B-38**, **B-41**, **B-44**, and **B-46** remain **Not Started**. B-33 is intentionally unused.

## Remaining work — prioritized view

Post-release correction status: **B-32 routine-renewal notification** and **B-39 repeated-popup suppression** are packaged in 1.47.1.

Numbered Not Started items are **B-38**, **B-41**, **B-44**, and **B-46**.

This is the active implementation queue. Detailed specifications remain below for traceability; completed and release history should not be used to choose the next point.

| Order | Priority | Item | Rationale |
|---:|---|---|---|
| 1 | P1 | **B-44 / B-38 — Restore guided Mosaic ticket creation** | Fixes the released portal action and fulfills the intended Product → Module → Service workflow through one implementation. |
| 2 | P1 | **B-46 — Mobile live tracking, escalation state, and inline satisfaction** | Corrects a public mobile workflow and safely closes the feedback loop without duplicate ratings. |
| 3 | P1 | **B-41 — Engineer Intake to Call Center Queue** | Replaces untracked WhatsApp ticket requests with a governed, measurable intake-to-ticket workflow. |

B-39's confirmed shared-profile grant model is implemented and verified in the working tree; it is no longer an active queue item.

Canonical filtered queue: [`Remaining.md`](Remaining.md).

## Backlog

### B-01 — Contract Setup form requires two clicks to close

- **Area:** Contracts and SLA
- **Feature/Page:** Contract Setup
- **Status:** Ready for Testing
- **Issue:** Clicking **Close Workspace** once does not close the Contract Setup form; it currently requires two clicks.
- **Expected result:** The form closes after one click.

### B-02 — “Today's Unassigned” quick action returns no tickets

- **Area:** Tickets
- **Feature/Page:** Quick Actions — Today's Unassigned
- **Status:** Ready for Testing
- **Issue:** The quick action returns no results when a ticket is assigned to a support engineer. Tickets assigned only to the support engineer should be treated as unassigned for this filter because the support engineer is excluded from the assigned-engineer calculation.
- **Expected result:** A ticket assigned only to support appears in **Today's Unassigned**.

### B-03 — Public live ticket-update URL

- **Area:** Tickets
- **Feature/Page:** Ticket creation and ticket details
- **Status:** Ready for Testing
- **Request:** Add a tokenized public URL, similar to the satisfaction URL, that lets a client track a ticket and view its public comments.
- **Requested controls:**
  - Use the current ticket-creation action to open a prepared message in the caller's WhatsApp chat.
  - Add a button to copy the live-update message/template.
  - Add a setting to enable or disable sending the live ticket-update URL.
- **Expected result:** Authorized clients can follow public ticket updates without signing in, using a secure tokenized link.
- **Permission:** **Copy live update** and **Send live update** require the dedicated `ticket.live_update.send` permission. This permission is independent of `ticket.comment.public` and is enforced by both the UI and API.

### B-04 — Client Portal date filter is one day behind

- **Area:** Client Portal
- **Feature/Page:** Ticket date filter
- **Status:** Ready for Testing
- **Issue:** Dates are not filtered correctly. For example, to find a ticket created on 2026-08-26, the filter must be set to 2026-08-25.
- **Expected result:** Filtering by 2026-08-26 returns tickets created on 2026-08-26.
- **Likely investigation area:** Time-zone conversion and inclusive date boundaries.

### B-05 — Move adjustment reasons to Master Data

- **Area:** Financial / Master Data
- **Feature/Page:** Adjustment Reason
- **Status:** Ready for Testing
- **Request:** Manage adjustment reasons from the Master Data page.
- **Expected capabilities:** Create, edit, activate, and deactivate an adjustment reason.

### B-06 — Improve Clients page on mobile

- **Area:** Clients
- **Feature/Page:** Clients page
- **Status:** Ready for Testing
- **Issue:** The page does not fit or display correctly on mobile screens.
- **Expected result:** The page is responsive and usable at supported mobile widths without unintended horizontal overflow.

### B-07 — Multiple material types per training material

- **Area:** Employee Onboarding
- **Feature/Page:** Training Materials
- **Status:** Ready for Testing
- **Request:** Allow one training material to have multiple material types.
- **Expected result:** Users can select, save, and display more than one material type for each training material.

### B-08 — Edit a user's assigned onboarding content

- **Area:** Employee Onboarding
- **Feature/Page:** User assignments
- **Status:** Ready for Testing
- **Request:** Allow an assigned program, material, or template to be edited after assignment, including changing the program assigned to an engineer.
- **Expected result:** Authorized users can update existing onboarding assignments without recreating them.

### B-09 — Schedule checklist tasks when assigning a program

- **Area:** Employee Onboarding
- **Feature/Page:** My Checklist / Program assignment
- **Status:** Ready for Testing
- **Request:** Allow a duration to be configured for each task when assigning a program.
- **Examples:** 1 day, 2 days, or 1 week.
- **Expected result:** Checklist task dates are scheduled from the configured durations.

### B-10 — Show Training Materials on the Knowledge page

- **Area:** Knowledge
- **Feature/Page:** Training Materials tab
- **Status:** Ready for Testing
- **Request:** Display the same Training Materials content/tab used in Employee Onboarding on the Knowledge page.
- **Expected result:** Users with appropriate permissions can access training materials from Knowledge.

### B-11 — Move Knowledge administration to Master Data

- **Area:** Knowledge / Master Data
- **Feature/Page:** Administration
- **Status:** Ready for Testing
- **Request:** Move Knowledge administration functions into the Master Data page.
- **Expected result:** Knowledge-related reference data is administered centrally from Master Data.

### B-12 — Group Master Data by category

- **Area:** Master Data
- **Feature/Page:** Page navigation and layout
- **Status:** Ready for Testing
- **Issue:** The page uses a long, difficult-to-navigate list of tabs.
- **Request:** Organize Master Data into categories, such as Ticket data, User data, CRM data, and other relevant groups.
- **Expected result:** Users can find Master Data sections through clear category grouping.

### B-13 — Add Mosaic as a Client Portal ticket-creation option

- **Area:** Client Portal
- **Feature/Page:** Create Ticket
- **Status:** Ready for Testing
- **Request:** Add Mosaic as a method or option when creating a ticket.
- **Expected result:** Clients can select and use Mosaic during ticket creation.
- **Implemented interpretation:** Mosaic is a selectable ticket-creation channel. It uses the standard portal form and records `MOSAIC` as the ticket source.

### B-14 — Show total working hours on the Client Portal home page

- **Area:** Client Portal
- **Feature/Page:** Portal home dashboard
- **Status:** Ready for Testing
- **Request:** Add a **Total Working Hours** card to the portal home page, reusing the value already available in the client profile.
- **Expected result:** The portal dashboard displays the client's total working hours consistently with the client profile.

### B-15 — Link CRM services to modules

- **Area:** CRM Master Data
- **Feature/Page:** Services and Modules
- **Status:** Ready for Testing
- **Request:** Allow each service to be linked to one or more specific modules.
- **Expected result:** Users can configure and retrieve the valid modules for a selected service.

### B-16 — Make “Needs Attention” collapsible

- **Area:** Operations & Scheduling
- **Feature/Page:** Needs Attention
- **Status:** Ready for Testing
- **Request:** Make the section collapsible and expandable when clicked.
- **Expected result:** Users can hide or reveal the section content while retaining a clear summary/header.

### B-17 — Move Advanced Templates to Unified Planner

- **Area:** Operations & Scheduling
- **Feature/Page:** Advanced Templates
- **Status:** Ready for Testing
- **Request:** Move the **Advanced Templates** tab to **Unified Planner**.
- **Expected result:** Advanced Templates is available from Unified Planner and removed from its old location without losing functionality or permissions.

### B-18 — Preserve ticket destination through email login

- **Area:** Email Notifications / Authentication
- **Feature/Page:** Ticket URL in ticket-created email
- **Status:** Ready for Testing
- **Issue:** Opening the ticket URL while signed out requires login, but a successful login redirects to the dashboard instead of the requested ticket. A user who is already signed in should not be asked to log in again.
- **Expected result:**
  - Signed-in users go directly to the ticket.
  - Signed-out users authenticate and are then redirected to the original ticket URL.


### B-19 — Show the client name after ticket creation

- **Area:** Tickets
- **Feature/Page:** Ticket details / post-creation view
- **Status:** Ready for Testing
- **Priority:** Quick win
- **Request:** Show the associated client name in the ticket details displayed after a ticket is created.
- **Smart logic:** Resolve the name from the ticket's saved client relationship rather than from temporary form data, so the displayed client always matches the persisted ticket.
- **Expected result:**
  - A ticket linked to a client displays that client's name prominently in the ticket details.
  - The client name links to the client profile when the current user has permission to view it.
  - If the persisted client record cannot be resolved, the page displays **Client name unavailable** and does not fail to render.
- **Acceptance checks:** Verify the result after creation, after a page refresh, and when directly opening the ticket URL.

### B-20 — Manually send the service-rating URL by WhatsApp or email

- **Area:** Tickets / Customer Satisfaction
- **Feature/Page:** Ticket details actions
- **Status:** Ready for Testing
- **Priority:** Quick win
- **Request:** Add an action that lets an authorized user manually send the ticket's service-rating URL to the caller through WhatsApp or email.
- **Smart logic:** Clicking **Send Rating Link** opens a small channel-selection dialog. Show WhatsApp and email only when the corresponding recipient contact and system setting are available. Reuse the existing satisfaction token and message-template flow; do not generate a different rating record or expose an unprotected ticket identifier.
- **Expected result:**
  - The action is available only when satisfaction/rating links are enabled and the ticket is eligible for rating.
  - The user can select **WhatsApp** or **Email** after clicking the action.
  - WhatsApp uses the caller's normalized WhatsApp-capable phone number and opens a prepared message containing the rating URL.
  - Email uses the caller's email address, a configured subject, and a prepared body containing the same rating URL.
  - The user can preview and copy the prepared message when a contact method is missing or the selected application cannot be opened.
  - Administrators can configure separate WhatsApp and email templates using validated placeholders such as client name, ticket number, rating URL, and company name.
  - Repeated manual sends reuse a still-valid rating link and do not create duplicate ratings.
  - Each send/open action records the selected channel in the audit trail without marking the survey as completed.
- **Settings:** Master enable/disable switch plus independent WhatsApp and email channel switches, subject/template fields, token expiry, and allowed placeholders. Disabled channels must not appear in the selector.
- **Dependency:** Existing satisfaction URL, token-expiry rules, configuration setting, and message-template behavior.
- **Acceptance checks:** Test both channels, eligible and ineligible tickets, missing phone/email, disabled master setting, individually disabled channels, invalid template placeholders, repeated sends, expired links, and an already-submitted rating.

### B-21 — Add a complaint-management workflow

- **Area:** Complaints / Tickets / Notifications
- **Feature/Page:** New **Complaints** navigation entry, creation form, list, and details view
- **Status:** Ready for Testing
- **Priority:** Feature epic
- **Goal:** Allow call-center agents to register, assign, communicate, and track a complaint, optionally linking it to an existing ticket.
- **Roles and permissions:**
  - Call-center users with complaint-create permission can register complaints.
  - Users can view complaints assigned directly to them or to an eligible profile/team; broader access requires a complaint-management permission.
  - Status changes, reassignment, notifications, and linked-ticket reopening require explicit permissions and are audited.
- **Creation fields:** Client, complaint reason, description, assignment target, optional linked ticket, and contact details inherited from the selected client/caller when available.
- **Smart logic:**
  - Use a dedicated complaint record and unique complaint number; do not model a complaint as a normal ticket.
  - Restrict the linked-ticket selector to tickets belonging to the selected client. Clear or revalidate the ticket when the client changes.
  - Allow assignment to either one engineer or one profile/team. If a profile/team is selected, keep it as the owner until an engineer claims or is assigned the complaint.
  - Store every status transition, reassignment, notification attempt, and ticket-reopen action in an immutable activity timeline.
  - After complaint creation, an authorized user can choose WhatsApp or email to send the client a configured complaint-created template and secure live-tracking link.
  - Email and WhatsApp use separate configurable templates because their formatting and subject requirements differ.
  - Support validated placeholders such as client name, complaint number, complaint status, complaint tracking URL, company name, and support contact. A default message may begin with **Dear valued customer** and confirm that the complaint was created with its complaint number.
  - The public tracking URL uses a revocable, expiring, non-guessable token and exposes only client-visible complaint information and public updates; internal notes, assignment history, and staff-only data remain hidden.
  - Client closure is a confirmation action available only when the complaint is in an allowed status. It records satisfaction feedback and an audit event, and cannot silently close or reopen a linked ticket.
  - Reopening a linked ticket is a separate confirmed action; changing complaint status must never reopen it automatically.
- **Initial status lifecycle:** `Open` → `In Review` → `Resolved` → `Closed`, with `Reopened` returning to active handling. Invalid transitions must be rejected by the backend.
- **Expected capabilities:**
  - Create, view, filter, assign/reassign, and track complaints by client, reason, owner, status, and date.
  - Send an assignment email to the assigned engineer when an email address exists.
  - Manually open a prepared WhatsApp message for the assigned engineer when a mobile number exists.
  - Send the client a complaint-created notification by WhatsApp or email using the enabled channel and configured template.
  - Let the client securely track the complaint's public status and public updates without signing in.
  - When enabled and status-eligible, let the client submit a satisfaction rating and confirm complaint closure from the tracking page.
  - Update complaint status from the complaint details view with an optional/required note according to the transition.
  - Open the linked ticket and, with confirmation and permission, reopen it when it is currently closed.
  - Display clear delivery outcomes for email/WhatsApp without treating a failed notification as a failed complaint creation.
- **Settings and controls:**
  - Master switch for client complaint notifications and public tracking.
  - Independent WhatsApp, email, client satisfaction, and client closure switches.
  - Separate client WhatsApp template, client email subject/body, tracking-token expiry, satisfaction scale, and closure-eligible statuses.
  - Settings are enforced by the backend as well as the UI. When disabled, public tokens/actions must be rejected rather than merely hidden.
  - Engineer assignment notifications remain independently configurable from client notifications.
  - Tickets with linked active complaints display a prominent, accessible complaint indicator in ticket lists and details. Use an icon, label, and color with a non-animated fallback; do not rely on flashing alone. The indicator links to the complaint only when the user has complaint-view permission.
- **Implementation phases:**
  1. Data model, complaint reasons, permissions, numbering, status rules, settings, and audit history.
  2. Complaints navigation, creation form, list/filter view, and complaint details.
  3. Engineer/profile assignment plus configurable client and engineer email/WhatsApp actions.
  4. Secure public tracking, client satisfaction/closure, validated ticket linking, and explicit linked-ticket reopening.
  5. Automated tests, authorization tests, migration verification, and manual end-to-end testing.
- **Decisions to confirm before implementation:** Whether complaint reasons are managed in Master Data; which profiles/teams are valid assignees; whether notifications send automatically or only through manual actions; which transitions require a note; which statuses allow client closure; whether complaint closure requires the linked ticket to be closed; and whether the linked-ticket complaint indicator should escalate based on complaint age, severity, or SLA state.
- **Acceptance checks:** Cover direct and team assignment, unauthorized access, client/ticket mismatch, every valid and invalid status transition, all setting combinations, missing client contact details, template validation, expired/revoked public tokens, internal-data exclusion, duplicate closure attempts, failed notifications, closed-ticket reopening, and complete audit-history visibility.

### B-22 — Pause live-tracking refresh while a ticket is closed

- **Area:** Public Ticket Tracking / Performance
- **Feature/Page:** Public live ticket-update page
- **Status:** Ready for Testing
- **Priority:** Performance quick win
- **Issue:** The public tracking page continues polling after the ticket reaches `Closed`, even though a closed ticket normally has no new activity.
- **Required behavior:**
  - Continue automatic refresh while the ticket is in an active status.
  - Stop the recurring 30-second refresh when the API reports `Closed`.
  - Perform a lightweight, lower-frequency status check while closed so the page can detect a later reopen without requiring the client to reload it manually.
  - Resume normal refresh automatically when the ticket is reopened or otherwise returns to an active status.
  - Refresh immediately when the browser tab becomes visible again or the network reconnects, subject to the same status rules.
- **Engineering constraint:** The public API remains the authority for ticket status. Do not infer closure from display text, elapsed time, or the client clock. Polling changes must not expose internal ticket data or weaken token validation and expiry.
- **Recommended polling policy:** Keep the existing 30-second interval for active tickets and use a configurable low-frequency interval for closed tickets, initially 5 minutes. Completely stopping all requests would prevent the already-open page from detecting a reopen.
- **Expected result:** Closed tickets generate substantially fewer public polling requests, and an already-open tracking page returns to live refresh after the ticket is reopened.
- **Dependency:** Existing B-03 public live-tracking endpoint and token lifecycle.
- **Acceptance checks:** Active polling, transition to closed, sustained closed state, closed-to-reopened transition, tab hide/show, network disconnect/reconnect, expired/revoked token, and no duplicated polling timers.

### B-23 — Customer Success results and risk-analysis workspace

- **Area:** Customer Management / Customer Success / Analytics
- **Feature/Page:** New Customer Success navigation page
- **Status:** Ready for Testing
- **Priority:** Feature epic
- **Goal:** Provide an authorized customer-management workspace for satisfaction and complaint outcomes, and use governed aggregate evidence from both sources in client-risk analysis.
- **Navigation:** Add **Customer Success** under **Customer Management**, protected by dedicated view/export permissions rather than general ticket access.
- **Expected capabilities:**
  - Summary cards for satisfaction response rate, average service rating, complaint volume, open complaints, overdue complaints, resolution time, reopen rate, and complaint satisfaction when available.
  - Separate **Satisfaction Results** and **Complaint Results** views with filters for client, date range, status, owner/team, complaint reason, service/product, and rating band where applicable.
  - Client-level drill-down showing trends and the underlying permitted records that contribute to an aggregate result.
  - Clear empty, insufficient-sample, loading, and failed-data states; missing evidence must remain unavailable and must not be treated as zero.
  - Export only for users with an explicit export permission, with the same authorization and filtering rules as the on-screen results.
- **Risk-analysis integration:**
  - Extend the existing customer-health/risky-client model instead of introducing a second conflicting risk score.
  - Incorporate eligible satisfaction and complaint evidence through documented, versioned weights and thresholds.
  - Exclude unsubmitted surveys, ineligible feedback, duplicate records, and complaints outside the selected analysis period.
  - Show the evidence and reason codes behind each client classification so a user can understand why a client is marked at risk.
  - Apply a minimum sample rule before ratings influence risk; low response volume must be labelled insufficient evidence.
- **Privacy and security:** Complaint notes, internal comments, personal contact data, and individual engineer ratings must not leak through aggregates, drill-downs, or exports. Backend authorization is required for every analytics and export endpoint.
- **Dependencies:** B-21 complaint management, existing ticket satisfaction records, and the existing management customer-health portfolio.
- **Implementation phases:**
  1. Confirm metrics, risk weights, minimum samples, date semantics, permissions, and data-retention rules.
  2. Add governed aggregate/query services and regression-tested risk inputs.
  3. Add Customer Success navigation, summary, filters, drill-downs, and exports.
  4. Validate performance, authorization, reconciliation with source records, and historical calculations.
- **Decisions to confirm before implementation:** Who can view or export individual results; whether complaint severity and aging affect risk; the minimum satisfaction sample; the analysis time window; whether risk scoring is real-time or snapshot-based; and the missing remainder of the original note after `also the co...`.
- **Acceptance checks:** Permission boundaries, empty and insufficient samples, date/time-zone boundaries, filter combinations, aggregate-to-source reconciliation, complaint lifecycle changes, survey eligibility, risk-score explainability, export parity, pagination, and query performance at production-scale volumes.

### B-24 — Unified Send Actions menu for tickets

- **Area:** Tickets / Quick Actions / Customer Communication
- **Feature/Page:** Ticket list and ticket details
- **Status:** Ready for Testing; packaged in release 1.46.1
- **Priority:** Workflow enhancement
- **Goal:** Add a single **Send Actions** dropdown that exposes the valid communication actions for a ticket from both the Tickets page and Ticket Details.
- **Initial actions:**
  - **Send rating link** — reuses B-20 eligibility, channels, templates, token, and audit behavior.
  - **Send live-tracking link** — reuses B-03 settings, token, recipient, template, and audit behavior.
  - **Send complaint-tracking link** — available only when B-21 exists and the ticket has an eligible linked complaint.
- **Smart behavior:**
  - On the Tickets page, each row action must operate on that exact ticket and must not depend on stale selection state.
  - On Ticket Details, use the same shared action definitions and dialogs so eligibility behavior cannot drift between pages.
  - Hide actions the user is not permitted to discover; show a disabled action with a concise reason only when the user has permission but the selected ticket is temporarily ineligible.
  - Channel selection must show only enabled channels with usable recipient data. Missing contact details must not trigger an invalid API request.
  - Server endpoints must independently enforce permission, feature setting, ticket/complaint relationship, status eligibility, token validity, and recipient rules.
  - Sending or opening a prepared message must use the existing idempotent link flows and create an audit event without changing ticket, complaint, or survey status.
- **Permissions:** Retain the existing `ticket.satisfaction.send` and `ticket.live_update.send` permissions. Add a dedicated complaint-tracking send permission under B-21. Add no broad umbrella permission that silently grants all three actions; profiles may receive any combination explicitly.
- **UX constraint:** Use one reusable send-action menu and channel dialog component with keyboard navigation, mobile support, loading protection, success/error feedback, and protection against double submission.
- **Dependencies:** B-03 and B-20 for existing actions; B-21 for complaint tracking. The first two actions may be delivered before B-21, while the complaint action remains feature-gated.
- **Expected result:** Authorized users can initiate every eligible client-facing link from either the ticket list or details page through a consistent, permission-aware workflow.
- **Acceptance checks:** Both entry points, every permission combination, feature switches, ticket status eligibility, linked/unlinked or multiple complaints, missing phone/email, disabled channels, repeated clicks, API rejection, audit records, keyboard/mobile behavior, and no duplicate survey or tracking records.

### B-25 — Match the Engineer Queues button styling

- **Area:** Tickets / UI consistency
- **Feature/Page:** Tickets page header actions
- **Status:** Ready for Testing
- **Priority:** Quick win
- **Issue:** **Engineer Queues** is rendered without the outlined frame used by adjacent actions.
- **Expected result:** Render it with the same button variant, size, spacing, focus state, responsive behavior, and dark/light-theme contrast as peer header actions without changing its permission or destination.
- **Acceptance checks:** Desktop/mobile widths, keyboard focus, both themes, permission hidden state, and navigation.

### B-26 — Configurable SLA pre-threshold notifications

- **Area:** SLA / Notifications / Site Settings
- **Feature/Page:** Site settings and SLA notification scheduler
- **Status:** Ready for Testing
- **Priority:** Operational control
- **Goal:** Let administrators enable or disable SLA warning delivery and configure how many minutes before each applicable SLA deadline a warning is generated.
- **Required behavior:**
  - Add a master SLA-warning switch plus positive whole-minute thresholds in Site Settings.
  - Define thresholds independently for response and resolution deadlines; support multiple unique thresholds in descending order.
  - Calculate warnings against the ticket's effective, versioned SLA and business calendar, not raw wall-clock duration.
  - Do not notify for paused, completed, cancelled, or otherwise inapplicable SLA clocks.
  - Deduplicate by ticket, SLA clock, deadline version, threshold, and recipient so scheduler retries cannot resend the same warning.
  - Recalculate pending warnings when priority, SLA, calendar, pause state, or deadline changes; never send a warning for a superseded deadline.
  - Configure escalation recipients using both direct email addresses and selectable recipient groups.
  - Treat an email distribution-list address as a direct address; validate and normalize it like any other email without attempting to expand external membership.
  - Initially use existing active Support Teams as system recipient groups. At delivery time, resolve their active members and use each member's **Support Notification Email**, falling back to the account email only if the approved notification policy allows it.
  - Show a recipient preview and warn about selected groups with no deliverable members before saving. A configuration with no effective recipient cannot be enabled.
  - Resolve group membership when the warning is queued so membership changes apply to future warnings without rewriting historical delivery evidence.
  - Combine direct and group-derived recipients case-insensitively, remove duplicates, and send one warning per effective recipient while preserving per-recipient delivery outcomes.
  - A missing or invalid recipient must not stop delivery to other valid recipients; record the partial outcome and expose it in operational delivery status.
  - Enforce settings and recipient authorization in the backend scheduler, not only in the UI, and audit configuration and recipient changes without exposing full addresses to unauthorized viewers.
- **Permissions:** Viewing uses configuration-view access; changes require `configuration.manage` or a dedicated SLA-notification management permission.
- **Decisions to confirm:** Default thresholds; whether Departments or Permission Profiles should also be selectable groups in addition to Support Teams; whether account email fallback is allowed when Support Notification Email is missing; whether breached alerts are controlled separately; and whether email/in-app channels have independent switches.
- **Acceptance checks:** Enabled/disabled states, response/resolution clocks, multiple thresholds, business hours, paused/resumed tickets, deadline recalculation, direct emails, distribution-list addresses, team membership changes, empty groups, duplicate addresses across sources, invalid/missing recipients, partial delivery, concurrent scheduler runs, time zones, authorization, audit redaction, and exact deduplication.

### B-27 — Full lifecycle management for internal ticket-notification rules

- **Area:** Ticket Notifications / Administration
- **Feature/Page:** Internal creation rules
- **Status:** Ready for Testing
- **Priority:** Administration enhancement
- **Goal:** Add edit, delete, enable, and disable controls for existing internal ticket-creation notification rules.
- **Required behavior:**
  - Reuse optimistic version checks for edits and state changes; reject stale updates with a reloadable conflict message.
  - Edit every supported match, recipient, and reassignment option through a pre-populated dialog.
  - Enable/disable without losing configuration.
  - Use confirmed soft deletion/archiving by default so audit history and past delivery evidence remain valid; hard deletion is allowed only when the rule has no dependencies and policy explicitly permits it.
  - Record before/after values and the acting user for every mutation.
  - Validate email addresses, active referenced profiles/users, match-mode rules, and at least one effective recipient before enabling.
- **Permissions:** Separate view and manage enforcement in both UI and API.
- **Acceptance checks:** Create/edit/disable/re-enable/archive, stale version, referenced inactive users, invalid recipients, unauthorized requests, audit evidence, and rules already associated with notification history.

### B-28 — Permission-aware ticket row context menu

- **Area:** Tickets / Fast Actions
- **Feature/Page:** Ticket list rows
- **Status:** Ready for Testing
- **Priority:** Workflow enhancement
- **Goal:** Open an application context menu on right-click/long-press with eligible actions such as change status, view history, reassign, and escalate, instead of showing the browser inspection menu over actionable rows.
- **Required behavior:**
  - Select the exact row under the pointer and use its current ID/version; never reuse stale row selection.
  - Reuse the existing dialogs, transition rules, assignment rules, escalation APIs, and audit behavior rather than duplicating business logic.
  - Filter actions using existing granular permissions and server-provided eligibility. Add only narrowly scoped permissions where no equivalent permission exists.
  - Provide an equivalent visible keyboard/touch action button; right-click cannot be the only route.
  - Preserve normal browser context behavior for links, selectable text, inputs, and users without any available fast action.
  - Refresh the affected row after success and handle version conflicts without optimistic data loss.
- **Accessibility:** Keyboard invocation, focus management, Escape dismissal, screen-reader labels, viewport-edge positioning, and long-press behavior are required.
- **Acceptance checks:** Each action and permission combination, closed/ineligible tickets, concurrency conflict, pagination, virtual/filtered lists, right-click on links/text, keyboard, mobile long-press, and audit records.

### B-29 — Inactive Clients KPI card across operational pages

- **Area:** Clients / Tickets / Dashboards
- **Feature/Page:** Clients page, Tickets page, Support Dashboard, and Top Management Dashboard
- **Status:** Ready for Testing; packaged in release 1.46.1
- **Priority:** Reporting enhancement
- **Goal:** Display a consistent **Inactive Clients** card near the top of each specified page.
- **Metric definition:** Count distinct client records whose current master-data status is inactive, subject to the viewer's client scope. Do not infer inactivity from a lack of tickets or contracts.
- **Required behavior:** Use one shared backend metric/query contract, display the same as-of semantics everywhere, and make the card navigate to a prefiltered Clients page when permitted. Users lacking client-list permission see only an authorized aggregate or no card, according to policy.
- **Performance:** Avoid loading all clients in the browser; compute the count server-side and index/filter appropriately.
- **Decisions to confirm:** Whether archived clients are included, whether dashboard date filters affect this point-in-time metric, and whether portal-scoped users may see it.
- **Acceptance checks:** Active/inactive/status changes, client scope, zero state, navigation filter, dashboard date changes, permission combinations, and consistency across all four locations.

### B-30 — Simplify Clients-page profile navigation

- **Area:** Clients / UX
- **Feature/Page:** Clients list
- **Status:** Ready for Testing; packaged in release 1.46.1
- **Priority:** Quick win
- **Goal:** Make the client name open Client Information and move **Open interactive profile** into the row's Actions column.
- **Required behavior:**
  - Client name is a semantic link to the saved client record and supports normal open-in-new-tab behavior.
  - Keep Edit as a distinct permission-controlled action; editing must not be the route to client information.
  - Place **Open interactive profile** in the Actions column/menu, visible only with its existing permission.
  - Preserve filters, search, sorting, and pagination when returning to the list.
- **Acceptance checks:** View/manage permission combinations, keyboard navigation, new-tab behavior, mobile action layout, deleted/inaccessible client, and list-state restoration.

### B-31 — Mobile dropdown must close after selection

- **Area:** Mobile UI / Shared form controls
- **Feature/Page:** Application-wide select/dropdown components
- **Status:** Ready for Testing; packaged in release 1.46.1
- **Priority:** Mobile usability defect
- **Issue:** After selecting a value, a full-screen mobile dropdown remains open. The device Back action navigates away and loses the user's context instead of dismissing the menu.
- **Required behavior:**
  - Close single-select menus immediately after a valid choice and retain the selected value.
  - For multi-select, provide explicit **Done** and **Cancel** actions; Done commits and closes, while Cancel restores the value from before opening.
  - Hardware/browser Back dismisses the open menu first without changing route or clearing the form.
  - Restore focus to the triggering field and prevent background scroll while the menu is open.
  - Fix the shared component/theme configuration where possible and audit page-specific native/select overrides.
- **Acceptance checks:** Android/iOS browsers, single/multi-select, Back/Escape/outside tap, required fields, long lists/search, orientation change, keyboard visibility, value persistence, and no history-entry pollution.

### B-32 — Diagnose and prevent unexpected user logout

- **Area:** Authentication / Session Reliability
- **Feature/Page:** Auth context and API token refresh
- **Status:** Ready for Testing; packaged in release 1.46.1
- **Priority:** Reliability and security defect
- **Issue:** An authenticated user can be logged out without an intentional sign-out and without a visible explanation.
- **Investigation requirements:** Capture structured client-safe reason codes for refresh expiry, refresh rejection, account/session revocation, storage loss, network failure, clock skew, and concurrent refresh races. Never log tokens or credentials.
- **Required behavior:**
  - A transient network/server failure must not erase a still-valid session; retry with bounded backoff and show a reconnecting state.
  - Only authoritative authentication failures clear credentials.
  - Coordinate concurrent 401 responses behind one refresh operation and prevent an older failed request from invalidating a newly refreshed session.
  - Persist the intended route and show a clear reason when reauthentication is genuinely required.
  - Define and document absolute and idle-session expiry; warn the user before policy-driven expiry when applicable.
  - Keep explicit logout and security revocation behavior immediate and reliable.
- **Acceptance checks:** Access-token expiry, refresh success/failure, offline/online, backend restart, multiple tabs, simultaneous requests, password-reset revocation, disabled user, clock skew, browser storage lifecycle, route restoration, and user-visible reason message.

#### B-32 follow-up — Keep routine token renewal silent

- **Status:** Ready for Testing; packaged in release 1.47.1
- **Observed behavior:** The frontend shows **Connection restored. Your session is active.** after every successful refresh-token exchange, including ordinary renewal of the configured 15-minute access token when no connection interruption occurred.
- **Cause:** The session-restored event is dispatched unconditionally after every successful token rotation instead of only after a preceding transient network/server failure.
- **Required behavior:**
  - Keep successful routine access-token renewal completely silent.
  - Track whether the current refresh cycle experienced at least one transient network, timeout, or server-availability failure.
  - Dispatch **Connection restored** only when that failed cycle later succeeds.
  - Do not classify an ordinary 401 caused by access-token expiry as a connection interruption when the refresh exchange succeeds normally.
  - Deduplicate reconnecting/restored notifications across simultaneous requests and browser tabs where practical.
  - Preserve the existing 15-minute access-token lifetime and silent refresh behavior; this correction must not weaken token security or extend token validity.
  - Keep authoritative refresh rejection, account disablement, token reuse, expiry, and session revocation behavior unchanged.
- **Acceptance checks:** Normal 15-minute renewal, renewal immediately after page focus, concurrent API 401 responses, multiple tabs, first-attempt success, transient failure followed by retry success, all retries failing, offline/online recovery, backend restart, authoritative refresh rejection, and notification deduplication.

### B-34 — Compact collapsible Contract Types workspace

- **Area:** Contracts and SLA
- **Feature/Page:** Contract Types tab
- **Status:** Ready for Testing; packaged in release 1.46.1
- **Priority:** UX enhancement
- **Goal:** Present each contract type as a collapsed summary that expands when its header is clicked, while keeping linked-client information compact.
- **Required behavior:** Show key status/default/SLA/count information in the header; lazy-load or reveal details on expansion; show linked-client count and a paginated/searchable dialog or compact preview instead of rendering every client inline. Preserve edit, activation, permissions, deep links, and keyboard-accessible accordion behavior.
- **Acceptance checks:** Zero/one/many linked clients, large datasets, expand/collapse, keyboard/mobile, permissions, edit refresh, and no layout shift from loading all customers.

### B-35 — Move Contract Templates into Contract Workspace

- **Area:** Contracts and SLA
- **Feature/Page:** Contract Workspace navigation
- **Status:** Ready for Testing; packaged in release 1.46.1
- **Priority:** Information-architecture change
- **Goal:** Make Contract Templates a permission-controlled section within Contract Workspace and remove the duplicate standalone navigation entry.
- **Required behavior:** Preserve the existing route as a redirect/deep-link compatibility path, reuse the current template component and permissions, retain unsaved-change protection, and update breadcrumbs/navigation tests and documentation.
- **Acceptance checks:** Direct old URL, workspace navigation, view/manage permission combinations, browser back/forward, create/edit templates, responsive layout, and no duplicate menu entry.

### B-36 — One structured application log file per day

- **Area:** Operations / Observability
- **Feature/Page:** Backend logging
- **Status:** Ready for Testing
- **Priority:** Operational reliability
- **Confirmed scope:** Preserve IIS/HttpPlatformHandler `uvicorn_*` process-output logs and add one separate structured application error/exception file for each local calendar day.
- **Goal:** Centralize `ERROR` and `CRITICAL` records in `support-hub-errors-YYYY-MM-DD.log` without making application health depend on file logging.
- **Required behavior:**
  - Use the configured deployment timezone and deterministic `support-hub-errors-YYYY-MM-DD.log` naming policy without renaming a shared active file at midnight.
  - Keep structured JSON lines, timestamps, severity, logger, correlation/request ID, and safe exception context.
  - Redact credentials, tokens, secrets, authorization headers, and sensitive request bodies.
  - Configure retention, compression/archive policy, maximum disk usage, encoding, and failure fallback to the process/event stream.
  - Prevent duplicate handlers and duplicated lines during startup/reload.
  - Serialize each short append and maintenance pass with a Windows inter-process file lock so all four IIS workers safely share the daily file.
  - Compress inactive daily files, remove expired files, and enforce a configurable total disk cap while never deleting the active file.
- **Deployment configuration:** `ERROR_LOG_ENABLED`, `ERROR_LOG_PATH`, `ERROR_LOG_TIMEZONE`, `ERROR_LOG_RETENTION_DAYS`, `ERROR_LOG_MAX_TOTAL_MB`, `ERROR_LOG_COMPRESS_ARCHIVES`, and `DEPLOYMENT_INSTANCE_ID`. The IIS application-pool identity requires Modify access to `ERROR_LOG_PATH`; packaged defaults use `.\logs\errors`, 30 days, 512 MB, Cairo time, and instance `support-hub-primary`.
- **Acceptance checks:** Verified midnight rollover, restart-safe naming, four concurrent Windows worker processes, complete JSON lines, retention cleanup, compression, Unicode, exception serialization, credential/token redaction, correlation and deployment identity, duplicate-handler prevention, and continued stream fallback when the path is unwritable. Disk-full behavior uses the same guarded failure path.

### B-37 — Control Training Material visibility in Client Portal

- **Area:** Training Materials / Client Portal
- **Feature/Page:** Training material administration and portal knowledge/training view
- **Status:** Ready for Testing; packaged in release 1.46.1
- **Priority:** Content-governance enhancement
- **Goal:** Add an enable/disable option that determines whether each active training material is visible to authorized client-portal users.
- **Required behavior:**
  - Add a dedicated `show_in_client_portal` flag defaulting to false for existing material to avoid accidental publication.
  - Internal active/visibility behavior remains independent from portal publication.
  - Portal APIs enforce client-portal visibility server-side and return only active, portal-published materials and active resources.
  - Validate every linked resource for portal-safe access; internal file paths or protected internal URLs must not be exposed.
  - Audit publication changes and show a clear portal-visible indicator in administration.
  - Define portal permission/scope and add an empty state when no material is published.
- **Acceptance checks:** Default migration, enable/disable, inactive material/resource, unauthorized API access, internal-versus-portal listings, unsafe resource link, caching invalidation, audit trail, and mobile portal display.

### B-38 — Guided Mosaic ticket creation by Product → Module → Service

- **Area:** Client Portal / Ticket Creation
- **Feature/Page:** Create with Mosaic
- **Status:** Not Started
- **Priority:** Portal workflow correction
- **Goal:** Replace the current standard form entry with a progressive card-based Mosaic flow: select a product, then one of its modules, then a service linked to that module, and continue to ticket details.
- **Required behavior:**
  - Display only active products entitled/visible to the portal user's client and contract scope.
  - Selecting a product opens its active modules as cards; selecting a module opens only active services linked through the B-15 service-module relationship.
  - Provide clear Back/Change controls that retain valid prior choices and clear downstream choices when an upstream selection changes.
  - Do not allow query parameters or crafted requests to submit a product/module/service combination outside the user's scope or configured relationship; backend validation is authoritative.
  - After the three selections, show the remaining required ticket fields and a review step. Persist `MOSAIC` as the source channel.
  - Define empty states for products without modules, modules without services, missing entitlement, and catalogs changed during submission.
  - Support keyboard, screen reader, touch, loading skeletons, retry, and responsive card layouts.
- **Dependencies:** B-15 service-to-module links, portal contract/product visibility, ticket-form required-field configuration, and existing Mosaic source handling.
- **Decisions to confirm:** Whether contracts restrict services in addition to products/modules, whether ticket type is inferred or selected after service, and whether users may save/resume a draft.
- **Acceptance checks:** Valid hierarchy, every empty state, inactive/unlinked items, client scope, crafted invalid payload, upstream reselection, browser Back, refresh/deep-link policy, duplicate submit protection, created-ticket relationships/source, and mobile accessibility.

### B-39 — Calm missing-permission recovery and delegated access grants (follow-up)

- **Area:** Identity and Access Management / Application-wide UX
- **Feature/Page:** Protected pages and actions
- **Status:** Ready for Testing; confirmed icon/request/direct-profile-grant workflow implemented in the working tree and not yet packaged
- **Priority:** Authorization usability and security
- **Released baseline:** Release 1.46.1 suppresses the generic red permission-denied notification when the backend identifies the missing permission, opens a calm **Access required** dialog, creates a governed request for the exact capability, and keeps high-risk permissions restricted to Profiles & Privileges.
- **Confirmed goal:** Show only a consistent clickable access indicator when a known capability is missing. Clicking it offers a normal permission request or an immediate credential-authorized grant to the requester's shared primary profile.
- **Required behavior:**
  - Derive the missing capability from authoritative backend authorization metadata; never trust a permission supplied only by the browser.
  - Never open the dialog automatically. Repeated 403 responses update/retain the compact access icon without producing a popup.
  - Clicking the indicator opens a calm dialog explaining the capability and two explicit paths: **Send permission request** and **Grant permission**.
  - A normal request creates/reuses a pending Access Request with source action `REQUESTED` for review on the Access Requests page.
  - Immediate grant requires an authorized approver username/email and password. The approver must be active, unlocked, hold `permission.grant.in_context`, and already hold the capability being granted; self-grant is prohibited.
  - Show the requester's active primary profile name and affected active-user count before granting. The confirmed behavior permanently adds the capability to that shared profile, affecting all users currently assigned to it.
  - Apply profile assignment and request resolution atomically. A direct grant creates or resolves an Access Request with decision/source evidence `DIRECT_GRANTED`, approver identity, reason, profile impact, audit record, authentication event, and target notification.
  - Access Requests displays whether the source was a normal request or a grant from the missing-access dialog, plus the latest decision actor/action.
  - Refresh effective permissions after approval without requiring logout, while preserving server-side enforcement.
  - Rate-limit failed step-up attempts and never log, persist, echo, or reuse the approver password.
  - High-risk permissions remain manageable only in Profiles & Privileges unless a separately approved policy explicitly whitelists them.
- **Confirmed security decision:** Mutate the requester's shared active primary profile after displaying its impact. Credential reveal/storage is forbidden; failed approver authentication is rate-limited through the existing account lockout counters. High-risk capabilities remain restricted to Profiles & Privileges.
- **Acceptance checks:** Icon-only denial, repeated/parallel 403 responses, polling/remount/navigation, intentional click, normal request deduplication/source, direct-grant source, active primary profile resolution, affected-user preview, invalid/locked/inactive approver, missing grant authority, approver lacking the capability, self-grant, existing pending request, atomic profile assignment, immediate permission refresh, high-risk block, audit/authentication evidence, notification, Access Requests source display, accessibility, and safe generic fallback.

### B-40 — Compact Contract Workspace and separate operational contract access

- **Area:** Contracts and SLA / Authorization
- **Feature/Page:** Contract Workspace (`/contracts`)
- **Status:** Ready for Testing
- **Priority:** Role separation and workspace usability
- **Issue:** Contract sections render the complete linked-customer collection inline. Also, project-delivery users currently need `contract.view`, which admits them to Contract Workspace and risks exposing master-data functions outside their role.
- **Goal:** Keep contract summaries compact and separate operational contract use from contract master-data administration.
- **Required behavior — compact customers:**
  - Replace the full inline customer list with a linked-customer count and compact preview.
  - Load the complete collection on demand in a searchable, server-paginated dialog or drawer.
  - Preserve customer scope, links, empty states, responsive layout, keyboard access, and refresh after edits.
- **Required behavior — permissions:**
  - Keep `project_handover.view` as the permission to open Project Handovers and view only handovers within the user's authorized assignment/scope.
  - Keep `project_handover.manage` as the permission to start and complete the delivery workflow, change its governed status, and save handover-specific products, documents, comments, recipients, warranty, acceptance, and pending-point information.
  - Add dedicated Project Delivery supporting permissions instead of requiring access to unrelated modules:
    - `project_handover.client.lookup`: search and select the minimum client identity data required by a handover; does not open `/clients` or return the general Client page payload.
    - `project_handover.client.create`: create a client only through **Create client for delivery project** using the restricted onboarding contract; does not grant `client.view`, `client.manage`, Client navigation, general editing, deletion, import, or export.
    - `project_handover.contact.create`: add callers/contacts for the selected or newly created client inside the delivery workflow; does not grant the general `contact.manage` page capability or editing/deleting unrelated contacts.
    - `project_handover.client_access.create`: add client access records during delivery onboarding; does not grant the general Client page or permission to reveal existing stored passwords.
    - `project_handover.engineer.lookup`: search and select eligible active support engineers as recipients or project managers, returning only ID, display name, and fields required for assignment; does not grant Operations Workspace, employee administration, schedules, workload, or unrelated HR data.
    - `project_handover.contract_template.apply`: list active applicable contract templates using a safe summary and create the handover's client contract from the selected immutable template version; does not grant Contract Workspace, template administration, arbitrary contract editing, or `contract.view`.
  - Treat reading or revealing existing client access credentials as a separate high-risk capability (proposed `project_handover.client_access.reveal`). Do not include it automatically in the Project Delivery profile; require explicit approval, password step-up, audit evidence, and client scope if the workflow genuinely needs it.
  - The Project Delivery profile may receive the handover permissions above as its dedicated baseline but must not receive `client.view`, `client.manage`, `contact.manage`, `contract.view`, `contract.manage`, `contract.template.view`, `contract.template.manage`, `internal_operation.view`, `internal_operation.manage`, or `internal_operation.workspace.view` merely to complete a project handover.
  - Keep `contract.view` strictly read-only. It must not authorize create, edit, status changes, customer linking, request-limit/configuration changes, or deletion.
  - Protect every mutation with its specific manage permission in both frontend and backend.
  - Make Project Delivery APIs use the dedicated permissions plus client/handover scope and return only the minimum required fields. Do not call the general Clients, Contracts, Users, or Internal Operations list APIs as a shortcut.
  - Seed and document the permission without automatically broadening non-administrator profiles.
- **Dedicated workflow boundary:**
  - A correctly configured Project Delivery user can open Project Handovers, create or select a client, add callers, add new client-access data, select eligible engineers, select and apply an active contract template, upload delivery documents, and complete the handover lifecycle entirely inside `/project-handovers`.
  - Successful creation of a client, contact, access record, or contract must return only the identifiers and safe summaries required to continue the handover. It must not create a route or deep link into the corresponding master page for this profile.
  - All created client/contact/access/contract records remain normal governed domain records and become visible/manageable in their master workspaces only to users who independently hold those workspace permissions.
  - Validate client scope, active status, engineer eligibility, template version, duplicate submission/idempotency, and cross-entity relationships on the backend in one transactional onboarding path where possible. If optional follow-up records fail, expose precise recoverable results without silently granting broader permissions.
  - Audit the full delivery onboarding transaction and each sensitive sub-action using the acting user, handover/client identifiers, selected template/version, assigned engineer IDs, and safe changed-field metadata; never audit plaintext access passwords.
- **Proposed Project Delivery profile baseline:** `project_handover.view`, `project_handover.manage`, `project_handover.client.lookup`, `project_handover.client.create`, `project_handover.contact.create`, `project_handover.client_access.create`, `project_handover.engineer.lookup`, and `project_handover.contract_template.apply`. Credential reveal is excluded by default.
- **Decisions to confirm:** Whether Project Delivery may only create client access records or also reveal existing credentials; whether contact editing is required after creation; whether existing Project Delivery users should be migrated automatically from broad permissions to the proposed baseline; required client/template/engineer summary fields; compact customer preview size; and dialog versus drawer.
- **Acceptance checks:** Proposed Project Delivery baseline without any Clients/Contracts/Operations permission; view-only and manage combinations; each supporting permission independently absent; direct master-page URLs; crafted calls to general APIs and mutations; client create/select; caller creation; access-data creation and secret non-disclosure; engineer assignment eligibility; template application/version conflict; complete lifecycle; duplicate submission; transaction/partial-failure behavior; client/handover scope; zero/one/many and large customer datasets; search/pagination; accessibility; permission migration; audit redaction; and no regression for independently authorized master-data administrators.
- **Implementation note (2026-08-27):** Contract rows now show a compact linked-customer count and two-name preview opening a searchable, server-paginated dialog. Migration `0143_project_delivery` adds the six scoped permissions and removes broad Client/Operations viewing from the Project Handover profile. Delivery client lookup/onboarding, contacts, access creation, engineers, products, and safe template application now stay under `/project-handovers`; credential reveal remains excluded.

### B-41 — Engineer Intake to Call Center Queue and ticket conversion

- **Area:** Tickets / Call Center / Technical Support
- **Feature/Page:** Engineer Intake form and **Call Center Queue** tab
- **Status:** Not Started
- **Priority:** Workflow governance and response-time evidence
- **Problem:** Technical Support engineers currently ask the Call Center to register tickets through an unstructured WhatsApp message such as **Kindly add new ticket**, organization, branch, title, and caller. The request time, ownership, conversion time, missing-data exchanges, and resulting ticket relationship are not governed or reliably measurable.
- **Recommended solution:** Persist an **Engineer Intake** record that is not yet an official ticket. Engineers submit a structured request; authorized Call Center users work a dedicated queue and atomically convert an eligible intake into one normal ticket. Preserve the immutable intake and its timestamps as the source evidence linked to that ticket.
- **Feature setting:**
  - Add a system setting such as `engineer_ticket_intake_enabled`, defaulting to disabled for upgrades.
  - When disabled, hide the Engineer Intake entry and Call Center Queue tab and reject intake API operations server-side with a clear feature-disabled response. Existing intake history remains readable to authorized administrators/auditors and must never be deleted by disabling the feature.
  - Enabling/disabling requires the existing governed configuration-management permission and audit evidence.
- **Proposed permissions:**
  - `ticket.intake.create`: open the intake form and submit a request as a Technical Support engineer.
  - `ticket.intake.view.own`: view requests submitted by the current engineer and their progress/resulting ticket summary.
  - `ticket.intake.queue.view`: see the dedicated Call Center Queue tab and scoped pending/history rows.
  - `ticket.intake.queue.process`: claim, return for information, reject with reason, and convert an intake to a ticket.
  - `ticket.intake.report`: view/export intake timing metrics beyond rows the user may otherwise access.
  - These permissions do not imply general client, contact, user, configuration, audit, or ticket-management permissions. Ticket conversion also requires the normal `ticket.create` permission; the backend enforces both permissions.
- **Engineer Intake form:**
  - Required searchable **Organization/client**, **Branch/site**, **Caller**, and **Title/subject** fields corresponding to the current WhatsApp template.
  - Require a problem description and capture optional product, module, service, ticket type, priority suggestion, contact channel, attachments, and engineer notes when available.
  - Lists must come from dedicated minimum-data scoped endpoints. Selecting a client restricts branches and callers to that client; inactive or inaccessible records cannot be submitted through a crafted request.
  - If the caller is missing, allow a governed **proposed caller** name and contact details only when policy permits. It remains intake data until the Call Center deliberately creates/links the caller with the appropriate permission; do not silently create CRM master data.
  - Record `submitted_at` on the server, submitting engineer, source channel `ENGINEER_INTAKE`, client timezone, and an idempotency key. Browser time is display-only evidence.
  - After submission, show an intake number and status; prevent the engineer from silently editing material fields after the Call Center claims it. Amendments must be versioned and audited.
- **Call Center Queue tab:**
  - Add a dedicated tab under Tickets or a Call Center workspace, visible only with `ticket.intake.queue.view` and only while the feature is enabled.
  - Default queue shows `SUBMITTED` and `NEEDS_INFORMATION` items with age, intake number, organization, branch, caller, title, submitting engineer, submitted time, claim owner, and warning indicators for missing/invalid data.
  - Support server pagination, search, status/date/engineer/client filters, oldest-first default ordering, accessible refresh, and an explicit empty state.
  - A processor can atomically claim one intake. Store `claimed_at` and `claimed_by`; use optimistic concurrency so two Call Center users cannot convert the same intake.
  - Supported lifecycle: `SUBMITTED` → `CLAIMED` → `CONVERTED`; `CLAIMED` ↔ `NEEDS_INFORMATION`; and governed `REJECTED`/`CANCELLED` terminal outcomes with mandatory reasons. Define who may cancel before implementation.
- **Convert to ticket:**
  - **Convert to ticket** opens the standard ticket-creation workflow prefilled from the intake. The Call Center user reviews and completes all fields required by current ticket policy; intake suggestions are not trusted as authorization or final classification.
  - Create the official ticket and transition the intake to `CONVERTED` in one database transaction, recording `converted_at`, converter, ticket ID/number, and the immutable values used. Repeated clicks or retries return the existing ticket rather than creating duplicates.
  - Ticket creation continues to enforce client scope, contract/entitlement, required-field settings, caller relationship, active catalog relationships, assignment eligibility, and normal audit/notification rules.
  - Set a dedicated ticket source such as `ENGINEER_INTAKE`; preserve the intake link in Ticket Details for authorized users without exposing internal intake notes to the client portal.
- **Timing and reporting semantics:**
  - `submitted_at`: when the server accepted the engineer's structured intake; this is the reliable replacement for the WhatsApp request timestamp.
  - `claimed_at`: when a Call Center processor accepted responsibility.
  - `converted_at` / ticket `created_at`: when the official ticket was committed.
  - Report **intake-to-claim**, **claim-to-registration**, and **intake-to-ticket** durations separately, with median, percentile, and breach counts by period/team/engineer as authorized.
  - Do not label `intake-to-ticket` as **engineer response time** by default: the engineer is the requester in this workflow, so the duration mainly measures Call Center registration delay. If management requires an Engineer Response KPI, define its start and stop events separately (for example, official ticket creation to first accountable engineer action) and exclude paused/non-working time according to an approved SLA policy.
  - Official ticket SLA clocks continue to start according to the existing ticket policy, normally at ticket creation. Any decision to start SLA at intake submission is a separate high-impact policy and migration decision.
- **Notifications:** Notify the Call Center queue on submission without exposing client secrets; notify the submitting engineer on claim, needs-information, rejection/cancellation, and conversion with the resulting ticket number when authorized. Deduplicate delivery and retain in-app evidence even if optional channels fail.
- **Security and privacy:** Enforce server-side scope for every intake and lookup; never include client access credentials in the intake; malware/size/type-check attachments through the existing governed storage path; redact notifications and logs; and audit create, claim, amendment, return, reject, cancel, and conversion actions.
- **Decisions to confirm:** Queue location (recommended: a new tab inside Tickets); whether engineers may submit for every scoped client or only assigned clients; proposed-caller policy; cancellation authority; queue SLA targets; notification recipients/channels; whether attachments copy to the ticket or remain linked; and whether intake submission affects contractual SLA (recommended: no).
- **Acceptance checks:** Feature enabled/disabled, every permission combination, scoped client/branch/caller lookup, missing caller proposal, inactive/mismatched entities, required fields, attachments, idempotent submission, simultaneous claim/conversion, needs-information loop, rejection/cancellation reasons, standard ticket validation, atomic conversion rollback, resulting ticket/source/link, notifications and failures, all timing fields and timezone display, reports/exports, pagination/filtering, audit evidence, client-portal exclusion, accessibility, mobile layout, and preservation of history when disabled.

### B-42 — Mobile compatibility and responsive UX audit

- **Area:** Shared application shell / Tickets / Complaints / Knowledge / IAM / Administration
- **Feature/Page:** Tickets, Saved Views, Complaints, Knowledge Base, Profile Privileges, Master Data, and Data Imports
- **Status:** Ready for Testing
- **Priority:** P1 mobile usability and responsive-layout defect
- **Problem:** Several high-use pages do not fit a mobile viewport and provide poor touch UX. Content, filters, actions, tables, dialogs, and navigation can overflow or become difficult to operate on phones. The reported pages are Tickets, Saved Views, Complaints, Knowledge Base, Profile Privileges, Master Data, and Data Imports.
- **Implementation approach:** Audit the reported pages at common phone and tablet widths, then correct shared primitives before applying page-specific exceptions. Reuse one responsive page header, filter/action toolbar, data-list/table container, tab/section selector, dialog form grid, and pagination pattern so future pages inherit the same behavior.
- **Shared responsive behavior:**
  - Support at least 320, 360, 390, 412, 768, and 1024 CSS-pixel viewports at normal browser zoom without page-level horizontal scrolling.
  - Stack page titles, search, filters, and primary actions in a predictable order on narrow screens. Keep the main action visible and place secondary actions in an accessible overflow menu when space is limited.
  - Prefer a compact card/list presentation for dense operational data when a table cannot preserve essential meaning. If a table remains necessary, contain horizontal scrolling inside the table region, keep row actions reachable, and do not force the entire page wider than the viewport.
  - Replace overflowing tab strips with a responsive selector, wrapped tabs, or a controlled horizontally scrollable tab region with a visible current section.
  - Make dialogs and drawers fit the viewport, keep headers/footers and submit/cancel actions reachable, allow the body to scroll, and ensure the on-screen keyboard does not hide the focused field or action.
  - Use touch targets of at least 44×44 CSS pixels for primary interactive controls, retain visible keyboard focus, avoid hover-only actions, and preserve labels or accessible names for icon-only controls.
  - Preserve the selected section, search, filters, sort, and pagination when opening a row and returning. Responsive changes must not weaken existing permission checks or expose hidden data/actions.
- **Page-specific requirements:**
  - **Tickets:** Make quick actions, Saved Views access, filters, ticket rows/cards, bulk selection, pagination, and row/context actions usable by touch. Preserve the permission-aware action registry and detailed ticket navigation.
  - **Saved Views:** Fit view selection, create/edit controls, rule/filter builders, long field values, and save/cancel actions without clipped inputs or off-screen buttons.
  - **Complaints:** Make list filters, status/ownership information, row actions, creation/details forms, activity history, and public-link actions usable without losing lifecycle context.
  - **Knowledge Base:** Provide readable article cards/content, responsive category/search controls, resource links, administration actions, and create/edit dialogs. Long URLs and rich content must wrap without expanding the page.
  - **Profile Privileges:** Replace the wide permission matrix with a mobile-friendly grouped permission list or cards. Keep permission code, name, state, search/category filters, inherited/direct source, and save feedback understandable without accidental toggles.
  - **Master Data:** Preserve category/section navigation, search, tables/forms, create/edit/status actions, and validation feedback in a compact layout; avoid restoring the old overflowing tab strip.
  - **Data Imports:** Fit template selection, file chooser/drop zone, validation summary, progress, error rows, and result/download actions. Large validation results may scroll within their own region or use mobile cards, but row-level errors must remain identifiable.
- **State and performance:** Responsive mode changes must not issue duplicate API calls, lose unsaved form data, reset active filters, or rerender large datasets unnecessarily. Continue to use server pagination for large lists.
- **Testing strategy:** Add automated component/regression coverage for shared responsive primitives and the critical action path on each reported page. Supplement it with browser viewport checks at 320×568, 390×844, 768×1024, and desktop width in both LTR and the application's supported language/direction modes.
- **Acceptance checks:** No document-level horizontal overflow; no clipped text, fields, menus, dialogs, alerts, or action buttons; keyboard and touch operation; 200% zoom/reflow; long names/codes/URLs; empty/loading/error/permission-denied states; large result sets; open/close dialogs with the mobile keyboard; portrait/landscape changes; filter and navigation state preservation; role-based visibility; screen-reader names and focus order; and no regression at desktop widths.
- **Out of scope:** A native mobile application, a visual rebrand, or changes to business rules and permission semantics. Any newly discovered functional defect should be logged separately rather than hidden inside this responsive-layout item.
- **Implementation sequence:** (1) reproduce and capture baseline widths; (2) fix shared shell/components; (3) Tickets and Saved Views; (4) Complaints and Knowledge Base; (5) Profile Privileges, Master Data, and Data Imports; (6) accessibility, viewport, and desktop-regression verification. Stop after B-42 and request confirmation before starting another backlog point.

### B-43 — Unify Client Portal training materials inside Knowledge Base

- **Area:** Knowledge Base / Employee Onboarding / Client Portal
- **Feature/Page:** Knowledge Base → Training Materials tab
- **Status:** Ready for Testing
- **Priority:** Information-architecture correction
- **Problem:** The Client Portal exposes a standalone Training Materials page even though employee training materials already appear as a tab in Knowledge Base. Both experiences use the same onboarding-material catalog, creating duplicate navigation and the impression that two independent material stores exist.
- **Implemented behavior:** Removed the standalone portal page and navigation item. Client Portal users now use the existing Knowledge Base page and its Training Materials tab. The legacy `/portal/training` URL redirects to `/knowledge?section=training` so existing bookmarks remain valid.
- **Publication rule:** The existing **Show in Client Portal** material flag remains authoritative. Portal users load only active materials with this flag enabled through the governed `/portal/training-materials` endpoint; employees continue to load the internal active material catalog. The client portal never calls the employee onboarding endpoint.
- **Permissions:** `knowledge.view` continues to govern the Knowledge Base. The Training Materials tab is visible to portal users only with `portal.training.view`; internal users retain their existing Knowledge/Onboarding access. Hiding the navigation or tab is not an authorization boundary—the backend portal endpoint continues to enforce portal user type and permission.
- **Security and compatibility:** Existing portal-safe URL validation, active-resource filtering, permission enforcement, and publication audit evidence remain unchanged. No material records are copied, migrated, or deleted. Removing the standalone component does not remove the backend feed or publication flag.
- **Acceptance checks:** Employee Knowledge articles and Training Materials tabs; portal-visible and portal-hidden materials; inactive materials/resources; portal user with and without `portal.training.view`; direct Knowledge URL; legacy `/portal/training` redirect; browser refresh on `?section=training`; internal versus portal API selection; no duplicate portal navigation; mobile tabs; safe external links; and no regression to onboarding material administration.
- **Implementation note (2026-08-28):** Knowledge Base now resolves the requested tab through the URL, selects the portal-safe or employee feed by user type, and suppresses the portal Training Materials tab without its dedicated permission. The standalone `PortalTrainingPage` component and navigation entry were removed.

## Notes reported against release 1.47.1

### B-44 — Restore the Create with Mosaic guided card flow

- **Area:** Client Portal / Ticket Creation
- **Feature/Page:** Portal Home → **Create with Mosaic**
- **Status:** Not Started
- **Priority:** P1 released-workflow defect
- **Problem:** In release 1.47.1, clicking **Create with Mosaic** navigates to the normal portal ticket form. The URL records `method=mosaic` and the created ticket source may become `MOSAIC`, but the promised card-guided behavior is not rendered. The visible workflow therefore does not match the action label.
- **Relationship to B-38:** B-44 is the concrete released defect; B-38 contains the intended Product → Module → Service guided design. Implement them through one shared Mosaic mode rather than building a second ticket-creation form. Completing B-44 should also satisfy B-38 only when every B-38 acceptance rule passes; retain both identifiers in test and release evidence.
- **Required behavior:**
  - Preserve the explicit Mosaic mode from Portal Home through refresh, browser navigation, validation errors, entitlement approval, and final submission.
  - In Mosaic mode, display accessible selectable cards for the eligible product catalog first, then modules belonging to the selected product, then services linked to the selected product/module. Do not initially render the normal full details form.
  - Show the current selection as a visible step/breadcrumb with Back and Change controls. Changing an earlier choice clears incompatible downstream choices without losing unrelated draft details.
  - Only after Product → Module (or an explicitly supported product-level/general option) → Service is valid should the normal remaining ticket details appear, prefilled with those governed identifiers.
  - The normal **Create Support Request** path remains unchanged and must not be silently switched into Mosaic mode.
- **Backend authority:** Continue using the portal catalog/entitlement response and standard ticket-creation transaction. A crafted request must not submit a service unrelated to the selected product/module or outside client/contract visibility. `creation_method=MOSAIC` identifies the UI path; it never bypasses required fields, entitlement approval, attachment rules, or scope checks.
- **UX requirements:** Responsive one-column cards on phones and denser grids on larger screens; clear selected, unavailable, covered, approval-required, loading, empty, and error states; keyboard selection and visible focus; long multilingual labels wrap; browser refresh retains the mode and safe URL-backed selections where practical.
- **Acceptance checks:** Mosaic versus normal entry; direct/refresh URL; zero/one/many products/modules/services; product-level service; inactive/unlinked/out-of-scope catalog records; covered and approval-required contracts; Back/change/reset; validation failure retention; double submission; ticket source and saved relationships; mobile/keyboard/screen reader; and no regression to ordinary portal creation.

### B-45 — Searchable form dropdowns across the system

- **Area:** Shared UI / All form and filter workspaces
- **Feature/Page:** Data-selection dropdowns
- **Status:** Ready for Testing; packaged in release 1.48.0
- **Priority:** P2 system-wide usability improvement
- **Problem:** Many form and filter dropdowns require scrolling through long lists. Selection becomes slow and error-prone as clients, contacts, users, products, services, permissions, templates, and other master datasets grow.
- **Scope definition:** Every dropdown that selects a business/data record or a configurable catalog value must support typing to search. This includes single-select and multi-select controls in create/edit forms, filters, dialogs, imports, workspaces, and administration. Application navigation menus, context/action menus, tiny fixed confirmation choices, and native date/time pickers are not data dropdowns and remain out of scope unless separately unusable.
- **Shared component:** Create one accessible `SearchableSelect`/autocomplete family supporting single and multiple values, controlled/uncontrolled forms, IDs distinct from labels, clear/reset, disabled/read-only/required states, helper and validation text, loading/error/empty states, long labels, keyboard operation, and mobile dismissal consistent with `MobileMultiAutocomplete`.
- **Search behavior:** Case-insensitive partial matching across the user-visible primary label and approved secondary identifiers such as code, username, email, ticket number, or client name. Normalize whitespace and diacritics where supported; never search or display secrets. Preserve the selected option even when it is inactive or absent from the current result page during editing, while clearly marking its state.
- **Large datasets:** Do not download unbounded tables merely to make them searchable. Lists that can grow materially must use debounced server search, minimum-data endpoints, pagination/continuation, request cancellation or stale-response protection, and client/permission scope enforced by the backend. Small bounded enums may search locally using the same visual component.
- **Migration strategy:** Inventory every MUI `Select`, native `<select>`, autocomplete, and custom menu; classify it as data select, bounded enum, action/navigation, or exception. Migrate shared/high-use workflows first (Tickets, Clients, Contracts, Operations, Project Handover, Users/Profiles), then remaining administration/import/report filters. Track intentional exceptions so completion is measurable.
- **Security and state:** Search must not broaden existing list endpoints, permissions, client/department scope, or record fields. Preserve existing IDs and payload contracts, unsaved form values, filter URL state, validation, and dependent-field clearing rules.
- **Acceptance checks:** Complete inventory; single/multi select; mouse, touch, and keyboard; 320 px viewport; 200% zoom; long/duplicate/non-Latin labels; codes and secondary-field search; no results/loading/error; inactive current value; dependent fields; server pagination and stale responses; permission/scope isolation; form reset/edit defaults; performance with large datasets; and no action/navigation menu regressions.
- **Implementation note:** Audited 197 form-selector locations across 62 frontend files. All MUI form `Select` controls now inherit one accessible searchable menu with case-insensitive visible-label filtering, keyboard-safe input, sticky mobile-friendly search, and an explicit no-results state. Existing dedicated `Autocomplete`/`MobileMultiAutocomplete` controls and their scoped data-loading behavior remain unchanged; action and navigation menus are not affected. Search filters only the options already authorized and loaded by each control, so it does not broaden endpoint scope or payload contracts.

### B-46 — Mobile live tracking, escalation state, and inline satisfaction

- **Area:** Public Ticket Live Update / Satisfaction
- **Feature/Page:** Secure public ticket-update URL
- **Status:** Not Started
- **Priority:** P1 public mobile workflow and feedback integrity
- **Problem:** The public live-update page does not fit phones well, its horizontal status flow is difficult to read, escalation is not represented, and a closed unrated ticket requires the client to leave the tracking experience to provide satisfaction feedback.
- **Responsive status flow:** Render the ticket lifecycle horizontally when adequate width exists and vertically on narrow/zoomed layouts. The vertical flow must keep chronological order, current/completed/upcoming semantics, timestamps, descriptions, and accessible labels without document-level horizontal scrolling.
- **Escalation representation:** Include only client-safe escalation facts in the public API and flow. Show a distinct **Escalated** event/status when escalation is active or occurred, with an approved client-facing timestamp and description. Never expose internal assignee names, department discussions, reasons marked internal, child-ticket identifiers, audit metadata, or routing/security details.
- **Inline satisfaction eligibility:** For a `CLOSED` ticket, the public tracking response may expose an `AVAILABLE`, `SUBMITTED`, `UNAVAILABLE`, or `EXPIRED` satisfaction state derived server-side. Show the rating form only when a valid unexpired satisfaction token is securely associated with the live-update request, the ticket is eligible, and no satisfaction response already exists.
- **Rating submission:** Reuse the existing public satisfaction validation and persistence service rather than creating a second rating model. Accept the configured service/engineer ratings and optional comments, validate ranges and length, prevent CSRF/replay/double submission as appropriate for the token design, audit safely, and return a thank-you/submitted state without exposing the rating token.
- **Duplicate prevention:** If the client already submitted through the dedicated rating URL, every subsequent live-update refresh must report `SUBMITTED` and never show the form. Concurrent submissions from the rating page and live-update page must result in one satisfaction record and an idempotent/already-submitted response, not duplicate evidence.
- **Token boundary:** A live-update token alone must not automatically become a satisfaction credential. Define a secure server-side association or issue/reuse the existing satisfaction token only under the configured delivery/eligibility policy. Do not place raw reusable tokens in API JSON, logs, analytics, or browser storage.
- **Polling behavior:** Preserve B-22 closed-ticket polling. After rating submission, refresh only the satisfaction state without restarting frequent closed-ticket polling. Reopened tickets hide the closed-ticket rating form while preserving an already submitted acknowledgement.
- **Acceptance checks:** 320/360/390 px and desktop status flows; 200% zoom; long translations; all lifecycle statuses; active/historical/no escalation; redaction; open/resolved/closed/reopened tickets; rating available/submitted/expired/disabled; valid/invalid/revoked live and satisfaction tokens; dedicated-link submission before/after/concurrent with inline submission; network retry/double click; validation and accessibility; polling cadence; privacy headers; and no regression to the standalone rating URL.

B-47- i need to make a big enhancment in the system , i need to make the system multi language , Arabic , English . the source of the system language is the english languange , but i need a option langage drop menu beside the user profile 
but i need it dynamic, as the system will contain a json file to detect the labes translate , such as a Languages folder contain Ar.json ENG.json the file contain all of labels by english and its Ar name , so when the user select AR language the system will look to the ar.json and change the labels and the needed UI data with the matched labels 


## Work log

| Date | Item | Status change | Notes |
|---|---|---|---|
| 2026-08-28 | Release 1.48.0 | Built and verified | Created the self-contained Windows x64 B-45 feature release at database head `0144_handover_cleanup`. Ruff, strict MyPy, 306 backend tests, ESLint, 31 frontend tests, TypeScript, production build, packaged-runtime clean migration, runtime help, manifest/version/head, required-content, ZIP-integrity, and forbidden-file checks passed. Artifact: `releases/SupportHub-1.48.0.zip`; SHA-256 `942B57727EB75EC3C31D411538FDEFC6281C0F9E239E5A14AC2C571FC1565775`. |
| 2026-08-28 | B-45 | Not Started → Ready for Testing | Audited 197 selector locations across 62 frontend files and applied one shared searchable paper to all MUI form Select controls through the application theme. Existing autocomplete/server-backed selectors retain their loading and permission boundaries; action/navigation menus remain unchanged. ESLint, TypeScript, two focused regression tests, all 31 frontend tests, and the production build passed. Packaged in release 1.48.0. |
| 2026-08-28 | B-44–B-46 | Untracked → Not Started | Prepared the reported 1.47.1 issues as implementation-ready items: B-44 links the broken Mosaic action to B-38's guided catalog workflow, B-45 defines a scoped reusable searchable-select migration rather than unbounded client-side lists, and B-46 defines responsive public status flow, redacted escalation evidence, and token-safe idempotent inline satisfaction. No application code was changed. |
| 2026-08-28 | Release 1.47.1 | Built and verified | Created the corrected self-contained Windows x64 release superseding 1.47.0. It packages the `0144_handover_cleanup` correction, permission-source visibility, B-42, and B-43. Ruff, strict MyPy, 306 backend tests, ESLint, 29 frontend tests, TypeScript, production build, packaged-runtime clean migration, runtime help, manifest/version/head, ZIP content/integrity, and forbidden-file checks passed. Artifact: `releases/SupportHub-1.47.1.zip`; SHA-256 `9B3542FFC59754A8B831EED1B0BB600327F4EE2BAB18542D73A383444195F080`. |
| 2026-08-28 | B-43 | Untracked → Ready for Testing | Unified portal training materials into Knowledge Base, retained the governed publication flag/feed and permission boundary, redirected the legacy URL, removed duplicate portal navigation and the standalone component, and added regression coverage for tab permission and endpoint selection. No database or material migration was required. Work stopped after B-43 pending confirmation. |
| 2026-08-28 | B-42 | Not Started → Ready for Testing | Added application-wide narrow-viewport containment, long-content wrapping, touch-friendly controls, mobile dialog actions, scrollable tabs and tables, responsive page padding, and targeted layouts for Tickets, Saved Views, Knowledge Base, Profile Privileges, Master Data, and Data Imports; Complaints inherits the shared table, dialog, touch, wrapping, and paper protections. ESLint, TypeScript, all 27 frontend tests, and the production build passed. No backend or permission behavior changed. Work stopped after B-42 pending confirmation. |
| 2026-08-28 | B-42 | Untracked → Not Started | Converted the reported mobile-fit problems on Tickets, Saved Views, Complaints, Knowledge Base, Profile Privileges, Master Data, and Data Imports into a shared responsive-layout specification with page-specific requirements, accessibility targets, viewport coverage, state preservation, and acceptance checks. No application code was changed. |
| 2026-08-27 | B-39 confirmed workflow | Clarification → Ready for Testing | Replaced automatic dialogs with a compact clickable access icon. The dialog now supports normal `REQUESTED` history and credential-authorized permanent shared-profile grants recorded as `DIRECT_GRANTED`, with impact preview, lockout, authority/capability checks, self/high-risk blocks, audit/authentication evidence, notification, and Access Requests source details. Ruff, strict MyPy, four focused backend tests, all 305 backend tests, ESLint, focused icon coverage, all 25 frontend tests, TypeScript, and production build passed. No migration; not yet packaged. |
| 2026-08-27 | B-39 follow-up | Not Started → Ready for Testing | Each missing capability now auto-opens at most once per browser page lifetime, including across repeated 403s and component remounts. A persistent compact access icon keeps intentional reopening available. ESLint, two focused tests, all 26 frontend tests, TypeScript, and production build passed. Delegated grant semantics remain a separate decision. Not yet packaged. |
| 2026-08-27 | B-32 follow-up | Not Started → Ready for Testing | Routine successful access-token renewal is now silent. The restored event is emitted only when the same refresh cycle first experienced a transient network/server failure and later succeeded. ESLint, two focused regression tests, all 24 frontend tests, TypeScript, and the production build passed. Not yet packaged. |
| 2026-08-27 | B-41 | Untracked → Not Started | Prepared an Engineer Intake form, feature switch, dedicated permissions, Call Center Queue, governed lifecycle, atomic ticket conversion, immutable timing evidence, notification/security boundaries, and reporting definitions. Recommended measuring intake-to-registration separately from actual Engineer Response KPI. No application code was changed. |
| 2026-08-27 | Backlog audit | Status reconciliation | Corrected stale Not Started labels on B-24, B-29–B-32, B-34, B-35, and B-37 to match release 1.46.1. Separated the two actionable post-release UX corrections from B-38/B-40 and from B-39's decision-required grant model. No application code was changed. |
| 2026-08-27 | B-36 | Not Started → Ready for Testing | Kept IIS/Uvicorn output logs unchanged and added daily Cairo-time JSON error/exception files with Windows inter-process locking, correlation and deployment identity, redaction, compression, 30-day retention, a 512 MB cap, and stream fallback. Ruff, strict MyPy, four focused logging tests including four worker processes, and all 304 backend tests passed. Not yet packaged. |
| 2026-08-27 | B-40 | Clarified → Prepared | Defined a dedicated Project Delivery permission baseline and scoped APIs for opening/completing handovers, client lookup/creation, caller creation, client-access creation, engineer lookup, and contract-template application without granting Clients, Contracts, or Operations workspace access. Existing credential reveal remains a separate high-risk decision. No application code was changed. |
| 2026-08-27 | B-40 | Prepared → Ready for Testing | Added compact linked-customer previews with a searchable server-paginated dialog, six dedicated Project Delivery permissions, restricted onboarding/lookup APIs, and migration `0143_project_delivery` removing legacy broad Client/Operations access from the Project Handover profile. Ruff, strict MyPy, 304 backend tests plus corrected compatibility tests, clean migration, frontend ESLint/TypeScript, 25 tests, and production build passed. Work stopped after B-40 pending confirmation. |
| 2026-08-27 | Release 1.47.0 | Built and verified | Packaged B-36, the B-32/B-39 corrections, and B-40 as a self-contained Windows x64 release at `0143_project_delivery`. All 305 backend tests, 25 frontend tests, release gates, standalone migration/runtime, artifact integrity, and forbidden-file checks passed. |
| 2026-08-28 | B-40 correction | Ready for Testing → Ready for Testing | Found legacy broad rights in `user_permission_overrides` and renamed Project Handover profiles. Migration `0144_handover_cleanup` restores the complete dedicated baseline, removes broad profile assignments and broad ALLOW overrides for Project Handover users, and exact route guards prevent Contract/Operations access without independent workspace permissions. All 305 backend and 27 frontend tests plus quality and migration gates passed. Release 1.47.0 is superseded pending a corrected package. |
| 2026-08-27 | B-39 follow-up | Clarified → Prepared | Limited automatic missing-permission dialogs to once per capability per browser page load. Repeated API denials, polling, route changes, and component remounts remain suppressed; manual icon opening remains available, and a manual browser reload permits one new automatic notice. No application code was changed. |
| 2026-08-27 | B-32 follow-up | Reported → Prepared | Documented that routine 15-minute access-token renewal must remain silent and that the restored notification is valid only after a transient connection/server failure followed by recovery. Token lifetime and authoritative session-ending behavior remain unchanged. No application code was changed. |
| 2026-08-27 | B-39/B-40 | Raw notes → Prepared | Preserved the released B-39 governed-access baseline, documented the security decision between user-specific grants and shared-profile mutation, and normalized B-40 into compact linked-customer UX plus a backend-enforced operational/master-data permission split. No application code was changed. |
| 2026-08-26 | All items | Untracked → Not Started | Notes normalized into a trackable backlog; no implementation status was inferred. |
| 2026-08-26 | B-01 | Not Started → Ready for Testing | Added a close guard that prevents the contract deep-link synchronization from reopening the workspace while its URL parameters are being cleared. Frontend lint, TypeScript build, 12 tests, and production build passed. |
| 2026-08-26 | B-02 | Not Started → Ready for Testing | Updated the unassigned-ticket filter to include tickets owned by the configured/shared Support queue while continuing to exclude tickets assigned to a dedicated engineer. Added a regression test; targeted tests, Ruff, and mypy passed. |
| 2026-08-26 | B-03 | Not Started → Ready for Testing | Added hashed, expiring public ticket-update tokens; a read-only auto-refreshing public page that exposes only non-internal comments; copy and WhatsApp actions on the ticket; a system enable/disable setting; migration 0131; and regression coverage. Backend checks and tests plus frontend lint, TypeScript, 12 tests, and production build passed. |
| 2026-08-26 | B-04 | Not Started → Ready for Testing | Client Portal list and Excel-export date boundaries now convert the browser's local calendar day to UTC using its timezone offset. Added a Cairo-offset regression case; four portal tests, Ruff, mypy, frontend lint, and TypeScript passed. |
| 2026-08-26 | B-05 | Not Started → Ready for Testing | Moved adjustment-reason creation from Payments into CRM Master Data and added editing plus active/inactive management. Added the audited PATCH API and regression coverage; seven finance tests, Ruff, mypy, frontend lint, and TypeScript passed. |
| 2026-08-26 | B-06 | Not Started → Ready for Testing | Made Client-page filters and actions stack on small screens, contained the data table in a horizontal scrolling region, tightened mobile padding and pagination, and made access-entry controls responsive. Frontend lint, TypeScript, and 12 tests passed. |
| 2026-08-26 | B-07 | Not Started → Ready for Testing | Upgraded the training-material create/edit dialog to manage multiple typed content resources in one save. Existing resources can be edited or removed, and new PDF, SharePoint, video, knowledge, website, Microsoft Learn, or other resources can be added together. Frontend lint, TypeScript, and 12 tests passed. |
| 2026-08-26 | B-08 | Not Started → Ready for Testing | Added an audited assignment-replacement workflow. Administrators can change an engineer's active onboarding program with a required reason; the old plan and checklist snapshot remain preserved as replaced while a fresh plan is assigned. Backend Ruff, mypy, and four administration tests plus frontend lint, TypeScript, and 12 tests passed. |
| 2026-08-26 | B-09 | Not Started → Ready for Testing | The assignment dialog now lists every task in the selected template or role program and accepts a duration in days for each task. Assignment snapshots calculate each due date from that task's availability date and reject durations for tasks outside the selected source. Backend Ruff, mypy, and five administration tests plus frontend lint, TypeScript, and 12 tests passed. |
| 2026-08-26 | B-10 | Not Started → Ready for Testing | Added a Training Materials tab to the Knowledge page backed by the existing onboarding material catalog. It displays active materials, categories, required flags, and every typed resource link, so changes made in Onboarding remain synchronized automatically. Frontend lint, TypeScript, and 12 tests passed. |
| 2026-08-26 | B-11 | Not Started → Ready for Testing | Added Knowledge Administration to Master Data. Article creation, editing, publishing, resource management, and deletion controls are exposed only when Knowledge is opened through the Master Data administration entry. |
| 2026-08-26 | B-12 | Not Started → Ready for Testing | Replaced the long Master Data tab strip with category and section selectors covering Ticket, User, CRM, Contracts & Finance, and Other data. |
| 2026-08-26 | B-13 | Not Started → Ready for Testing | Added Create with Mosaic to the Client Portal and persist Mosaic-created requests with the dedicated MOSAIC source channel. Portal regression coverage passed. |
| 2026-08-26 | B-14 | Not Started → Ready for Testing | Added Total Working Hours to the portal dashboard using the same accountable ticket hours plus completed-operation engineer-hours calculation used by Client Profile. |
| 2026-08-26 | B-15 | Not Started → Ready for Testing | Added many-to-many CRM service-to-product-module links, Master Data multi-selection, API validation, migration 0132, and regression coverage. |
| 2026-08-26 | B-16 | Not Started → Ready for Testing | Converted Needs Attention into an expandable section with a visible issue-count summary. |
| 2026-08-26 | B-17 | Not Started → Ready for Testing | Moved Advanced Templates from Scheduling Setup into the Unified Planner source tabs while preserving shift and operation template permissions. |
| 2026-08-26 | B-18 | Not Started → Ready for Testing | Login now restores the complete protected destination path, query, and hash after authentication; authenticated users continue directly to the requested route. Added redirect-state regression coverage. |
| 2026-08-26 | B-19–B-21 | Untracked → Not Started | Normalized the newly added notes into testable backlog items. B-21 was defined as a phased complaint-management epic with permissions, lifecycle validation, audit history, notification behavior, safe client/ticket linking, and explicit ticket reopening. |
| 2026-08-26 | B-20–B-21 | Not Started → Not Started | Refined manual rating delivery to support a setting-controlled WhatsApp/email selector and configurable templates. Added setting-controlled complaint-created notifications, secure public tracking, client satisfaction, and status-aware client closure without exposing internal data or automatically changing a linked ticket. |
| 2026-08-26 | B-03 | Ready for Testing → Ready for Testing | Added the dedicated `ticket.live_update.send` permission for Copy/Send live-update buttons and API issuance. Existing profiles with public-comment permission inherit it during upgrade, after which it can be managed independently. The ticket page now reads only authenticated public settings instead of requiring configuration management. |
| 2026-08-26 | Release 1.43.1 | Built and verified | Packaged the dedicated live-update permission correction as a self-contained Windows x64 release at database revision `0133_live_update_permission`. All release gates and artifact checks passed. |
| 2026-08-26 | B-19 | Not Started → Ready for Testing | The single-ticket API now resolves `client_name` from the persisted ticket relationship. Ticket Details displays it prominently after creation, refresh, and direct URL access, with a client link only for users holding `client.view`. Ruff, MyPy, three focused backend tests, frontend ESLint, and TypeScript passed. |
| 2026-08-26 | B-20 | Not Started → Ready for Testing | Added the independent `ticket.satisfaction.send` permission and a closed-ticket **Send rating link** dialog for enabled WhatsApp/email channels. The backend securely reuses valid encrypted survey tokens, rotates expired or legacy links without duplicate surveys, queues templated email, prepares normalized WhatsApp delivery, and audits each action. Administrators control the master switch, channels, expiry, subject, and validated templates. Migration `0134_satisfaction_delivery`, permission catalog export, Ruff, MyPy, six focused tests, frontend ESLint/TypeScript, and the production build passed. |
| 2026-08-26 | B-03 | Ready for Testing → Ready for Testing | Modernized public live tracking with a responsive dashboard, client and ticket details, elapsed/solved time, current status, and a pointed status-history flow. The secure public API now supplies those fields while continuing to expose only public comments. Ruff, MyPy, two focused tests, frontend ESLint/TypeScript, and production build passed. |
| 2026-08-26 | Release 1.44.0 | Built and verified | Packaged B-20 manual satisfaction delivery and the modernized B-03 public live-tracking page as a self-contained Windows x64 release at database revision `0134_satisfaction_delivery`. All 290 backend tests, 12 frontend tests, release gates, runtime checks, and artifact integrity checks passed. Implementation remains stopped after B-20; B-21 complaint management is the remaining point for later. |
| 2026-08-26 | B-22–B-24 | Untracked → Not Started | Converted the new raw notes into implementation-ready backlog specifications. B-22 defines status-aware public polling; B-23 extends the governed customer-health model with complaint and satisfaction evidence; B-24 defines a shared permission-aware Send Actions menu for ticket list and details. The truncated ending of B-23 remains a decision to confirm. |
| 2026-08-26 | B-25–B-32, B-34–B-38 | Untracked → Not Started | Prepared 13 new notes with implementation boundaries, permissions, backend enforcement, accessibility, operational safety, dependencies, decisions, and acceptance checks. Assigned the duplicate B-26 unexpected-logout note to B-32 and left B-33 unused to preserve the user's remaining identifiers. |
| 2026-08-26 | B-25 | Not Started → Ready for Testing | Added the missing outlined frame to the permission-controlled Engineer Queues fast action while preserving its navigation and responsive layout. Frontend ESLint, TypeScript, all 12 tests, and the production build passed. Work stopped after B-25 pending confirmation before B-26. |
| 2026-08-26 | B-26 | Not Started → Not Started | Extended the prepared SLA-warning scope with direct email recipients and Support Team recipient groups, runtime membership resolution, recipient preview, validation, deduplication, partial-delivery evidence, authorization, audit redaction, and additional acceptance checks. Implementation remains stopped pending confirmation. |
| 2026-08-26 | B-26 | Not Started → Ready for Testing | Added setting-controlled response/resolution warning thresholds in minutes, direct and distribution-list email recipients, active Support Team recipient expansion through Support Notification Email, backend validation, deadline-version deduplication, durable email payloads, and System Operations controls. Existing percentage escalation rules remain independent. Ruff, MyPy, 292 backend tests, frontend ESLint/TypeScript, all 12 frontend tests, and the production build passed. Work stopped after B-26 pending confirmation before B-27. |
| 2026-08-26 | B-27 | Not Started → Ready for Testing | Added pre-populated editing, enable/disable, and confirmed soft-delete controls for internal ticket-notification rules. The backend validates active profiles/engineers and unique active names, enforces optimistic versions, archives instead of destroying history, audits every mutation, and excludes archived rules from creation and reassignment evaluation. Migration `0135_notification_rule_archive`, clean-install migration verification, Ruff, MyPy, 292 backend tests, frontend ESLint/TypeScript, all 12 frontend tests, and the production build passed. Work stopped after B-27 pending confirmation before B-28. |
| 2026-08-26 | B-28 | Not Started → Ready for Testing | Added a permission-filtered right-click menu to ticket rows plus a visible keyboard/touch-accessible three-dot action. History, status, reassignment, and escalation actions deep-link into the existing Ticket Details workflows, preserving server eligibility, concurrency, validation, and audit behavior. Native context menus remain available on links, inputs, and buttons. Frontend ESLint, TypeScript, all 12 tests, and the production build passed. Work stopped after B-28 pending confirmation before B-29. |
| 2026-08-26 | B-21 | Not Started → Ready for Testing | Added the dedicated complaint domain, unique numbering, reasons, scoped permissions, direct/team ownership, validated client/ticket/contact links, optimistic lifecycle transitions, immutable activity history, audited reassignment and explicit ticket reopening, setting-enforced email/WhatsApp tracking delivery, expiring public links, public updates, satisfaction, and client-confirmed closure. Added Complaints list/create/details navigation and a public tracking page. Migration `0136_complaint_management` passed a clean install; Ruff, MyPy, all 292 backend tests, frontend ESLint/TypeScript, all 12 frontend tests, and the production build passed. Work stopped after B-21 pending confirmation before the next point. |
| 2026-08-26 | B-22 | Not Started → Ready for Testing | Public ticket tracking now polls active tickets every 30 seconds and uses a server-configured 5-minute status check after the API reports `CLOSED`. It immediately refetches on tab focus and network reconnection, resumes the active cadence after a reopen, and pauses interval work in background tabs. Migration `0137_closed_ticket_polling`, clean-install verification, polling-policy tests, and all quality gates passed. Work stopped after B-22 pending confirmation before B-23. |
| 2026-08-26 | B-23 | Not Started → Ready for Testing | Added a dedicated Customer Success workspace with governed satisfaction and complaint summaries, date/client/reason/product/rating filters, privacy-safe source rows, explicit empty states, and filter-parity CSV exports protected by separate view/export permissions. Extended the existing client-health model with period-bounded complaint evidence, a three-response minimum for satisfaction influence, explainable reason codes, and version `CUSTOMER_SUCCESS_V1`. Migration `0138_customer_success`, clean installation, all backend tests, frontend checks/tests, and production build passed. Work stopped after B-23 pending confirmation before B-24.