# Approval Enhancements

Status: **PLANNED — NOT IMPLEMENTED**

Last reviewed: 2026-09-26

## Purpose

This document records the planned approval improvements identified during the approval-workflow review. It is a future implementation specification and is not part of the current application behavior.

## Approved scope

The planned work covers:

1. A unified approval inbox in the Tickets page.
2. Complete approval-group administration.
3. Dedicated worklog approval permissions and self-approval controls.
4. Complete, correctly labelled approval totals on dashboards.
5. Clear ticket-creation entitlement rules, with product coverage as the primary coverage dimension and service coverage controlled by configuration.

## Ticket-creation entitlement rule

### Product is the primary coverage dimension

Product coverage is the main entitlement check during ticket creation. When the selected product is not covered by the applicable contract, the configured entitlement policy determines whether the ticket is allowed, warned, blocked, or created in a pending-approval state.

### Service coverage is configurable

Service coverage must not always trigger approval. Administrators must be able to configure whether service selection participates in entitlement validation.

The effective configuration should support at least:

- `PRODUCT`: validate product coverage only. Service remains classification data and an uncovered service does not independently require approval.
- `PRODUCT_SERVICE`: validate the selected product and service combination. An uncovered service can require approval according to policy.
- `NONE`: do not use product or service coverage as an approval gate, when explicitly allowed by policy.

The ticket-creation form, portal form, pre-ticket conversion, entitlement evidence, approval reason and audit history must all use the same effective validation level.

The approval reason shown to users must identify the actual controlling rule. For example, a contract configured for product-only validation must not show `SERVICE_NOT_COVERED` or request approval only because its service is uncovered.

### Other entitlement conditions

Existing configurable policy behavior remains applicable to inactive clients, inactive or expired contracts, allowance limits, ambiguous contract matches and other contract exceptions. The treatment of `NO_CONTRACT` should be reviewed explicitly before implementation because it is currently allowed while several narrower coverage failures require approval.

## Worklog approval permissions

Introduce dedicated permissions instead of using `ticket.resolve.any` as the worklog approval authority:

- `ticket.worklog.approval.view`: view submitted worklogs awaiting approval.
- `ticket.worklog.approve`: approve or reject another employee's submitted worklog.
- `ticket.worklog.approve.self`: high-risk exception permitting self-approval.

Rules:

- Normal worklog approvers cannot approve or reject their own worklogs.
- Self-approval requires `ticket.worklog.approve.self`, a mandatory reason and an audit record identifying the decision as an override.
- The self-approval permission is not assigned to normal profiles by default.
- Decisions continue to require the current worklog version.
- The requester, approver, decision, reason and override status are available to approval reporting.

## Unified approval inbox

Keep the inbox as the **Approvals** tab in the Tickets page. The backend should expose a normalized, permission-filtered approval query while existing domain decision endpoints remain authoritative during the first implementation phase.

Initial sources:

- Ticket entitlement approvals
- Ticket deletion approvals
- Submitted worklogs
- Access requests
- Onboarding approvals
- UAT internal sign-offs
- Shift approvals
- Field-visit approvals

Finance and KPI workflows may be added after their decision semantics are aligned with the common approval lifecycle.

The inbox should provide:

- All pending, actionable by me, my groups, my requests and overdue views.
- Type, group, requester, client, status, age and deadline filters.
- Search by ticket/reference number, subject, client or requester.
- Desktop table and mobile card layouts.
- A responsive detail and decision dialog rather than browser prompts or immediate generic decisions.
- Meaningful approve/reject comments and request-more-information where supported.
- Direct links to related records and a complete approval timeline.
- Backend-calculated action eligibility so the UI never guesses whether the current user can decide.

## Approval-group administration

Add an Approval Groups workspace under System Operations.

Introduce dedicated permissions:

- `approval_group.view`
- `approval_group.manage`

Administration capabilities:

- List and search active and inactive groups.
- Create and edit group name, code, status and membership.
- Show active-member, pending-approval, contract and contract-template usage counts.
- Open the unified inbox filtered to the selected group.
- Prevent an active group from having no active eligible members.
- Prevent unsafe deactivation when pending requests would have no eligible approver.
- Validate employee activity and eligibility when changing membership.
- Audit group creation, editing, activation, deactivation and member changes.
- Use optimistic concurrency for updates.

## Dashboard approval totals

Replace the current entitlement-only `pending_approvals` interpretation with an aggregated approval summary produced from the same query rules as the unified inbox.

The summary should contain:

- Total visible pending approvals.
- Total actionable by the current user.
- Total overdue.
- Counts by approval type.

The dashboard's main action number should represent approvals the logged-in user can decide. The total visible count should be secondary. Clicking a count should open the Tickets Approvals tab with URL filters that survive refresh and use the configured application base URL.

Until aggregation is implemented, any entitlement-only metric should be labelled **Pending entitlement approvals**, not **Pending approvals**.

## Implementation order

1. Add worklog permissions and separation-of-duty rules.
2. Complete approval-group backend operations and validation.
3. Add the normalized approval aggregation API.
4. Build the Approval Groups administration UI.
5. Replace the Tickets Approvals tab with the unified responsive inbox.
6. Make dashboard totals consume the same aggregation logic.
7. Add regression, authorization, concurrency, notification and mobile-layout tests.

## Minimum acceptance criteria

- Product-only contracts never request approval solely because a service is uncovered.
- Service coverage approval behavior follows the effective contract or template configuration.
- A normal worklog approver cannot decide their own worklog.
- A self-approval override is permission-controlled, reasoned and auditable.
- The unified inbox never exposes an approval outside the viewer's client, department or permission scope.
- Inbox and dashboard counts match for the same user and filters.
- Empty or inactive approval groups cannot leave pending requests without an eligible approver.
- Approval filters and deep links work below the configured base URL and after browser refresh.
- Inbox cards and decision dialogs remain usable on mobile widths.

