
Status: Consolidated planning baseline  
Prepared: 2026-08-19  
Source plans: Client Hierarchy; Contract Configuration and SLA Master Data; Shifts Planner; Support Performance & Improvement; and Contract Renewal, Finance, and Chargeable Ticket Development  
Risk: Multi-phase, cross-system program

Refactoring note: This edition reorganizes headings, labels, navigation, and document structure only. Existing business rules, formulas, workflows, permissions, precedence, lifecycle states, acceptance criteria, migration requirements, and rollout logic remain unchanged.


## Codex Execution Control — Mandatory Stop Points

This master plan must be executed incrementally. Codex must **not** continue automatically through the full roadmap.

### Execution rule

For every implementation session:

1. Work only on the explicitly requested wave, sub-wave, section, or bounded task.
2. Do not start the next roadmap item unless the user explicitly asks to continue.
3. Complete implementation, migrations, tests, and documentation for the current bounded scope.
4. Update the relevant implementation status using the existing statuses: `DONE`, `PARTIAL`, `READY`, `BLOCKED`, or `PLANNED`.
5. Record:
   - What was completed.
   - Files/modules changed.
   - Database migrations added.
   - Tests executed and their result.
   - Remaining items or blockers.
   - Any business decision still required.
6. Update `RELEASE_STEPS.md` where the current task affects release or deployment.
7. Add the following checkpoint at the exact stopping location:

```text
============================================================
CODEX STOP POINT
Status: <DONE | PARTIAL | BLOCKED>
Completed scope: <wave / section / task>
Last completed item: <short description>
Next planned item: <next wave / section / task>
Safe to continue from here: YES/NO
Blocking decision(s): <None or list>
============================================================
```

8. **STOP immediately after writing the checkpoint.**
9. Do not implement, scaffold, migrate, refactor, or prepare code for the next item.
10. Wait for a new explicit instruction such as `continue`, `continue from stop point`, or a specific next task.

### Resume rule

When instructed to continue:

1. Read the latest `CODEX STOP POINT`.
2. Verify the repository/database state matches that checkpoint.
3. Review incomplete or blocked items from the previous session.
4. Continue from `Next planned item` unless the new user instruction specifies a different scope.
5. Never repeat completed migrations or destructive operations.
6. At the end of the new bounded scope, create a new `CODEX STOP POINT` and stop again.

### Partial or blocked work

If the current scope cannot be completed:

- Mark it `PARTIAL` or `BLOCKED`.
- Preserve all safe completed work.
- State exactly what remains.
- State what is required to unblock it.
- Do not bypass unresolved business decisions.
- Do not continue to another wave merely because the current wave is blocked.
- Write the `CODEX STOP POINT` and stop.

### Definition of session completion

A Codex implementation session is complete only when:

- The requested bounded scope has been implemented as far as safely possible.
- Required tests for that scope have been executed.
- Migration state is known and documented.
- Relevant plan/status documentation is updated.
- A `CODEX STOP POINT` has been written.
- Codex has stopped before starting the next scope.

This execution-control section changes **only how the plan is executed**. It does not change any business rule, workflow, formula, permission, data model, precedence rule, acceptance criterion, roadmap scope, or implementation logic defined elsewhere in this master plan.

## Document Navigation

### Part I — Program Foundations
1. Purpose  
2. Program-wide Design Rules  
3. Governance, Status, and Terminology  
4. Logical Target Architecture  

### Part II — Core Business Domains
5. Client and Sub-client Hierarchy  
6. Contracts, Coverage, SLA, Renewals, and Finance  
7. Workforce Structure, Shifts, and Workload Planning  
8. Client/Sub-client Visit Entitlement and Scheduling  
9. Site Settings, Ticket Notifications, Navigation, and Search  

### Part III — Performance and Management Intelligence
10. Performance, Reporting, Dashboards, and Forecasting  

### Part IV — Delivery, Quality, and Governance
11. Delivery Roadmap  
12. Business Decisions and Policy Gates  
13. API, Migration, and Data Delivery Checklist  
14. Verification and Test Strategy  
15. Release and Rollout Controls  
16. Definition of Done  
17. Traceability to Source Plans  

---

# Part I — Program Foundations

## 1. Purpose

This is the single controlling development plan for the features and enhancements described in the five source planning files in this folder. The original files remain as historical source material, but implementation status, decisions, sequencing, and acceptance should be maintained here.

The program delivers six connected capabilities:

1. Client and sub-client hierarchy with exact operational ownership and controlled visibility.
2. Efficient contract, coverage, entitlement, and versioned SLA administration.
3. Department-aware shift planning and workload visibility.
4. Contract-based visit entitlement, scheduling, completion, and reporting for every client or sub-client.
5. Auditable support performance, client value, engineer fairness, renewal intelligence, and forecasting.
6. Repeatable contract renewals, effective-dated coverage, optional contract finance, payment schedules, and governed chargeable tickets.

## 2. Program-wide design rules

- Every ticket, visit, installation, operation, attachment, and evidence row belongs to the exact affected client, including a sub-client; hierarchy never rewrites ownership to the root.
- Hierarchy does not automatically grant portal access or contract coverage. Both require explicit scope.
- Contract and SLA decisions must be deterministic, explainable, versioned, and historically reproducible.
- Visit allowances belong to an exact client/sub-client within a contract period, not to an ambiguous shared contract pool, unless a future pooled entitlement is explicitly designed.
- A search limit must never make valid clients, users, or catalog values unreachable.
- Master-data changes must not rewrite historical ticket, SLA, shift, visit, or KPI evidence.
- Monetary values use fixed-precision decimals and explicit currencies. Contracted, billable, invoiced, collected, outstanding, and overdue are separate measures; only confirmed collections are income.
- Authorization, tenant/client isolation, audit history, and server-side validation are mandatory.
- Aggregates must reconcile to source records and show exact owning clients in drill-downs.
- Existing standalone clients and current workflows retain backward-compatible defaults.
- Reuse existing departments, groups, privileges, storage, audit, calendar, and attachment architecture where suitable.
- Support SQLite development and SQL Server production migrations; migration scripts must be safe, indexed, constrained, and rehearsed.

## 3. Governance, Status, and Terminology

Statuses: `DONE`, `PARTIAL`, `READY`, `BLOCKED`, and `PLANNED`. An item becomes `DONE` only after its acceptance criteria and quality gates pass.

- Client: an independently owned operational account.
- Sub-client: a client with a parent; it remains a full client account.
- Affected client: exact client/sub-client receiving a ticket, visit, or operation.
- Contract owner: client that owns the commercial contract.
- Eligible client: exact client allowed to use a contract through ownership, explicit link, hierarchy scope, or global applicability.
- Visit entitlement: allowed visit quantity for one eligible client, visit type, and contract service period.
- Visit occurrence: one schedulable instance generated from an entitlement/plan.
- Reporting scope: `SELF`, `DIRECT_CHILDREN`, or `FULL_HIERARCHY`.

## 4. Logical Target Architecture

```text
Client hierarchy
  -> exact affected client
  -> explicit portal scope
  -> explicit contract eligibility
  -> tickets / installations / operations / visits

Contract
  -> eligible clients
  -> coverage and exclusions
  -> versioned SLA policy and targets
  -> per-client visit entitlements

Department
  -> eligible users and groups
  -> shift types and patterns
  -> weekly shift planner
  -> visit planner and workload checks

Operational evidence
  -> worklogs / feedback / outcomes / SLA / visits
  -> client and department reports
  -> engineer scorecards / RAG trends
  -> renewal intelligence / snapshots / forecasts
```

# Part II — Core Business Domains

## 5. Client and Sub-client Hierarchy

### 5.1 Data and services

Add nullable `clients.parent_client_id`, an index, and a restrictive self-reference. Existing clients migrate as roots. Initially use centralized application traversal rather than a stored path; consider a closure table only after measured performance requires it.

Provide one hierarchy service:

```text
get_ancestors(client_id)
get_descendants(client_id, depth=None, include_self=False)
get_scope_ids(client_id, scope_mode, include_self=True)
get_client_path(client_id)
is_descendant(ancestor_id, candidate_id)
validate_parent_change(client_id, parent_client_id)
```

Reject self-parenting, indirect cycles, missing parents, and deletion of a parent with children. Use deterministic ordering, defensive depth protection, old/new path auditing, and deliberate handling of inactive nodes. Deactivating a parent does not deactivate descendants.

### 5.2 Client experience

- Optional parent selector in client create/edit.
- Breadcrumb, parent link, expandable tree, and direct/total descendant counts.
- Search results display full paths such as `UHIA > Luxor > Karnak`.
- Scope selector appears only where meaningful and defaults to `SELF`.
- Profile aggregates show each source record's owning client.

### 5.3 Tickets and portal

Internal ticket creation selects the exact affected client and reloads only that client's branches, contacts, installations, policies, eligible contracts, and catalog. Changing a ticket client requires permission and reason, clears incompatible context, reruns entitlement/SLA selection, and audits old/new decisions.

Portal assignments gain explicit scope: `CLIENT_ONLY`, `CLIENT_AND_DIRECT_CHILDREN`, or `CLIENT_AND_ALL_DESCENDANTS`; existing assignments default to `CLIENT_ONLY`. A multi-client user must choose the affected client. Remove any implicit `client_ids[0]` behavior. The backend validates client, branch, requester, contract, and coverage scope independently of the UI.

### 5.4 Contract hierarchy eligibility

Contracts gain `hierarchy_scope`: `OWNER_ONLY`, `DIRECT_CHILDREN`, or `ALL_DESCENDANTS`, defaulting to `OWNER_ONLY`. Explicit client links and global applicability remain supported.

Candidate order is exact child-owned contract, explicit link, nearest eligible ancestor, more distant ancestor, then shared/global default, while preserving coverage specificity and exclusions. Equal-precedence ambiguity requires explicit selection. Historical tickets retain the selected contract and SLA evidence after reparenting or contract edits.

### 5.5 Cross-system scope

Use centralized scope resolution in dashboards, reports, contracts, tickets, operations, satisfaction, installations, imports, APIs, Outlook/email ticket creation, feature policies, notifications, saved views, and exports. Automated sources must resolve the exact affected client and never default to the hierarchy root.

## 6. Contracts, Coverage, SLA, Renewals, and Finance

### 6.1 Guided contract workflow

Provide a staged editor for details, eligible clients, coverage, SLA, validation, and activation. Include unsaved-change protection, a review summary, readiness checks, and explicit publish/activate actions.

All large selectors use server-side search and pagination. Selected values disappear from available results. Support select visible, select all matching, remove visible, and clear all. “All matching” must store a query/exclusion intent or perform a server-side bulk operation; it must not depend on one loaded page. Preview counts and affected dependencies before mutation.

### 6.2 Bulk coverage

Allow bulk construction and editing across products, modules, services, environments, branches, ticket types, and exact eligible clients. Normalize duplicates, validate module/product ownership, preview generated rules, preserve exclusions and specificity, and audit the before/after set.

Coverage eligibility and row applicability are separate checks. Empty coverage-client scope retains its documented meaning of all clients eligible for that contract. Contract-covered products and products installed at a client remain distinct facts in the UI.

Coverage that has been used by a ticket is effective-ended, never deleted. Coverage records gain lifecycle status, `effective_from`, `effective_until`, `removed_at`, `removed_by`, and mandatory `removal_reason`. The End/Remove preview shows effective date, affected clients, open tickets, and dependent SLA targets. Ended coverage stops matching new tickets after its effective end while historical entitlement and SLA snapshots remain unchanged. Hard deletion is allowed only for unused coverage on a draft contract. Dependent future SLA targets must be retired/effective-ended consistently.

### 6.3 SLA master data

Create reusable SLA template masters with immutable published versions and editable drafts. Templates include identity, description, status, business calendar, response/resolution behavior, and target matrix. Only published versions may be attached to active contracts. Publishing closes the version; later edits create a new draft/version. Historical tickets retain resolved target snapshots and resolver evidence.

Target resolution must support default priority targets independent of service, followed by optional service-, product-, and module-specific overrides according to one documented precedence table. Status transitions do not silently select a different priority target. Resolver output records template/version, matched target, specificity, calendar, timestamps, and explanation. Ambiguity is rejected rather than silently resolved.

Published SLA versions may later become `RETIRED` without altering historical clocks. The SLA workspace includes copy-from-version, priority response/resolution matrix, effective dates, overlap/missing-target validation, a sample-ticket matcher explaining the winning rule, and impact preview before publish or retire. Ticket creation and reassignment snapshot the matched policy/target version and deadlines. Historical recalculation is prohibited unless a separately privileged, reasoned, audited process is approved.

### 6.4 Import, export, API, and permissions

- Versioned Excel/CSV template with stable IDs/codes where possible.
- Download template, validate-only import, row-level errors, preview, commit, and result export.
- Reject unknown priorities, malformed durations, duplicates, invalid relations, ambiguity, and unauthorized scope.
- APIs for paginated searches, selection previews/commits, bulk coverage previews/commits, SLA template/version lifecycle, target validation, and imports.
- Reuse/add granular privileges for client links, coverage, SLA templates, publishing, imports, and contract activation.
- Audit selection query, exclusions, counts, target changes, version publication, import file/result, actor, and reason.

### 6.5 Contract renewal lifecycle

Do not repeatedly overwrite one renewal date. Store every renewal opportunity and outcome in `ContractRenewal` with contract, sequential renewal number, status (`DRAFT`, `UNDER_REVIEW`, `APPROVED`, `COMPLETED`, `REJECTED`, or `CANCELLED`), notice/due/proposed-period/decision/completion dates, owner, probability, notes, mandatory rejection/cancellation reason, optional proposed value/currency, predecessor/successor reference, and complete approval audit.

`ContractRenewalLine` records support partial renewal at product, module, service, or existing-coverage level. Each line stores `RENEW`, `ADD`, `REMOVE`, or `CHANGE`, current/proposed coverage dates, optional current/proposed price, current/proposed SLA policy/target version, status, notes, and ordering. Completing a renewal produces a new immutable contract version or successor snapshot; it never rewrites the prior contract/coverage/SLA evidence.

Renewal workspace requirements:

- Multiple cycles per contract with one clearly identified active opportunity per applicable period unless parallel proposals are explicitly approved.
- Current-versus-proposed comparison with highlighted coverage, SLA, price, period, and client-allocation differences.
- Approval routing and monetary thresholds independent from ticket exception approval.
- Completion transaction validates dates, line actions, coverage, SLA, finances, and successor/version creation atomically.
- Explicit renewal KPIs: contract renewal rate, product/line renewal rate, pipeline, due, completed, rejected, cancelled, expiring value, renewed value, lost value, and days to renewal.
- Contract renewal rate is completed eligible opportunities due in the selected period divided by all eligible opportunities due then. Product renewal rate uses renewal lines, not contract counts. Rejected/cancelled remain visible and are not renewed.
- Retire date-inference KPIs only after explicit records exist. Backfilled legacy dates are labeled inferred/migrated and never silently represented as confirmed outcomes.

### 6.6 Optional contract finance and payment schedules

Financial data remains optional. Contracts, entitlement, SLA, tickets, and renewals must work when every monetary field is blank. An optional contract financial profile stores currency, fixed-precision contract value, tax, discount, billing model (`FIXED`, `INSTALLMENT`, `USAGE`, or `HYBRID`), purchase-order/reference, and protected notes. Currency becomes mandatory when an amount exists.

Use `ContractPaymentSchedule` for milestone/installment description and number, due date, fixed-precision amount/currency/tax/discount, status (`PLANNED`, `INVOICED`, `PARTIALLY_PAID`, `PAID`, `OVERDUE`, or `CANCELLED`), invoice reference/date, calculated paid/balance values, notes, and audit. Collections use separate immutable receipt/payment transactions so one installment supports partial/multiple payments and reversals.

For contracts covering multiple clients, support optional explicit financial allocations by client and effective period using percentage or amount, with validation that the allocation reconciles. Client-income reporting labels unmatched value `Unallocated`; it never guesses a split from ticket volume, hierarchy, or coverage.

Financial definitions:

- Contracted: approved contract value.
- Scheduled: valid payment-schedule amount.
- Billable: approved charge/schedule amount eligible to invoice.
- Invoiced: amount represented by an invoice reference/status.
- Collected/income: confirmed, non-reversed receipt amount in the selected collection period.
- Outstanding: invoiced or otherwise due amount less confirmed collections according to approved policy.
- Overdue: positive outstanding balance past its due date and not cancelled/waived.

Contract workspace becomes a full route such as `/contracts/:id` with tabs for Overview, Customers, Scope and Coverage, SLA, Renewals, Financials, Documents, and Audit History. Creation uses `Basics -> Customers -> Coverage -> SLA -> Optional Finance -> Review`. Sticky summary/header content and each tab are permission-aware. Financials provides summary cards, installment timeline/table, reconciliation validation, and source-record drill-down.

### 6.7 Inactive-client/catalog approval and permission-controlled override

Ticket creation must normally allow only active clients and currently eligible active contract/catalog data. When business operations require a ticket for an inactive client, product, module, service, contract, or SLA policy/target, do not silently accept it as normal and do not lose the submitted request. Create a governed exception workflow.

Exception sources:

- Exact affected client/sub-client is inactive.
- Selected contract is inactive, suspended, expired, or otherwise ineligible.
- Product, module, or service is inactive or outside the selected contract coverage.
- Selected SLA policy/target or required business calendar is inactive/unavailable.
- Any other entitlement failure explicitly classified as approval-eligible by policy; hard security/isolation failures are never approval-eligible.

Standard approval path:

```text
Ticket submitted
  -> normal eligibility validation
  -> exception detected
  -> ticket/reference created as PENDING_APPROVAL
  -> approval request routed to configured approver(s)
  -> APPROVED -> activate ticket and snapshot approved exception context
  -> REJECTED -> retain request/audit, notify requester, do not activate work
  -> RETURNED -> requester/creator corrects and resubmits
  -> CANCELLED/EXPIRED -> close approval without deleting evidence
```

- The requester/creator sees the exact reason requiring approval before submission and sees current approval status afterward.
- Store an immutable approval request with ticket/reference ID, exception codes, inactive entity IDs/names/statuses, submitted values, requester, approvers, comments, timestamps, and decision history.
- Route by configurable approval policy, initially to the appropriate Support manager(s); avoid self-approval unless an explicit emergency privilege/policy permits it.
- Multiple inactive/coverage issues on one ticket should form one consolidated approval request listing every exception, not unrelated parallel approvals.
- Approval validates the ticket again. Newly introduced exceptions require renewed approval; corrected/active data may remove the need.
- While pending, the ticket cannot enter normal assignment/work/SLA queues unless policy explicitly allows triage. Clearly exclude it from ordinary operational counts or label it separately.
- SLA clocks do not start while approval is pending by default. On approval, resolve a current valid SLA where possible; if approval permits an inactive SLA, snapshot its approved version/targets and record the clock-start policy. Never reference mutable inactive master data without a snapshot.
- Client portal users may submit an inactive-client exception only if their existing portal assignment still explicitly authorizes that exact client. Inactivity never expands portal visibility.

Permission-controlled direct override:

- Add granular privilege(s), for example `tickets.exception.request`, `tickets.exception.approve`, and `tickets.exception.override`; reuse equivalent existing privileges where available.
- The `Override and create/activate` button is rendered only when an exception exists and the current user has the override privilege. It must be absent—not merely disabled—for unauthorized users, while backend enforcement remains mandatory.
- Override requires a reason and confirmation showing every bypassed rule. High-risk exception types may still be configured as approval-only and unavailable for direct override.
- Store actor, permission, reason, exception list, original/resolved values, timestamps, and resulting SLA/contract snapshot. Surface an `Exception approved/overridden` badge and history on the ticket to authorized viewers.
- Approval and override do not reactivate master data and do not make the inactive item selectable for unrelated tickets.
- Editing an approved/overridden ticket's client, contract, product, module, service, or SLA reruns validation and may require a new approval; previous approval cannot authorize a materially different context.

### 6.8 Chargeable tickets, fees, approvals, and payments

Some services may require a financial flow. Add optional financial configuration without giving ordinary engineers authority to price or record payments.

Service configuration:

```text
Financial flow required                 boolean
Default fee                             optional reference/suggestion
Currency                                required when financial flow is enabled
Tax/discount policy                     optional, manager-controlled
Payment required before work            configurable policy
Payment required before closure         configurable policy
```

Out-of-contract entitlement may suggest that finance review is appropriate, but it never creates a charge automatically. A ticket remains valid without a charge and may contain multiple independent charges.

Use `TicketCharge` as the authoritative financial record rather than one mutable fee field on the ticket:

```text
Id, TicketId
Type: OUT_OF_SCOPE, EXTRA_SERVICE, or MANUAL
Status: DRAFT, APPROVED, INVOICED, PARTIALLY_PAID,
        PAID, WAIVED, or CANCELLED
Currency, BaseAmount, Discount, Tax, TotalAmount
Reason, PricingNotes
Proposed/approved/invoiced audit references and dates
InvoiceReference nullable, version/audit fields
```

- Ticket-level `PricingStatus`, `PaymentStatus`, totals, collected, and balance values are derived summaries across its charges, not an independently editable source of truth. Optional billing disposition may be `INCLUDED`, `CHARGEABLE_PENDING`, `CHARGEABLE_APPROVED`, `WAIVED`, or `NOT_APPLICABLE`.
- Only users with explicit manager financial privileges may set/change the ticket fee, discount, tax, total, currency, payment policy, or pricing notes. Being assigned to the ticket, having override permission, or being a normal Support engineer grants no financial authority.
- Suggested/default service prices are never silently final. A permitted manager confirms the fee and the ticket stores a pricing snapshot so later service-price changes do not rewrite history.
- If a selected service requires finance or entitlement is out of scope, set the ticket billing disposition to `CHARGEABLE_PENDING` and route a suggestion to an authorized manager; do not create an approved amount automatically. Show engineers the operational status needed for work decisions while restricting sensitive amounts according to permission.
- Price changes after confirmation require a reason and create a new immutable revision. Define whether client acceptance or a new approval is required when the amount changes.
- Do not overload ticket status with financial state. Track operational, exception-approval, pricing, and payment states separately and display a clear combined summary.

Payment ledger:

```text
TicketPayment
  Id, TicketId, TicketChargeId, Amount, Currency
  PaymentMethod, ReferenceNumber
  PaymentDate, Status
  Notes, RecordedByManagerId
  ReversalOfPaymentId nullable
  CreatedAt, audit fields
```

- Only users with `ticket_finance.manage_payments` (or an approved equivalent manager privilege) may record, confirm, reverse, refund, or correct payments.
- Support partial and multiple payments per charge; calculate collected totals from confirmed non-reversed ledger entries and charge/ticket balances from approved amounts less collections. Do not allow destructive editing/deletion of confirmed payments; use reversal/correction records with reasons.
- Validate currency consistency, positive amounts, overpayment/refund policy, unique external references where applicable, and transactional concurrency.
- Payment management is not a full accounting system. If invoices/receipts/accounting integration are required, store external references and integrate through a separately approved interface rather than inventing unsupported accounting behavior.
- Client-visible fee/payment details require an explicit portal permission/policy. Email notifications must not include financial amounts unless the template and recipient policy explicitly allow them.
- Provide authorized filters/reports for pending pricing, awaiting payment, partially paid, paid, overdue, waived, refunded, total fees, collected amount, and balance, with exact ticket/payment drill-down and exports.
- Income dashboards change only when confirmed collection transactions are recorded. Approved or invoiced ticket charges are not income.

Approval/override and financial actions use separate permissions, even when the same manager currently holds them. All server APIs enforce these permissions independently of UI visibility.

Use granular permissions aligned to the effective-permission model, including `contract.finance.view/manage`, `payment.view/manage`, `ticket.finance.view/manage`, `dashboard.finance.view`, and `report.finance.export`, or equivalent existing privileges. Review financial leakage across list/detail APIs, search, audit, notifications, exports, client profiles, dashboard queries, and drill-downs. Ordinary engineers and portal users receive no financial values unless explicitly granted.

## 7. Workforce Structure, Shifts, and Workload Planning

### 7.1 Master data

- Department master: code, name, status, display order, scheduling/reporting flags, audit fields.
- Initial departments: Support, Call Center, Implementation, Clients, Sales, Finance, HR, and Management.
- User department and explicit scheduling eligibility; reuse groups for team assignment where suitable.
- Shift type master: Morning, Evening, Night, Weekend Morning/Evening/Night, and On-Call.
- Dynamic shift patterns/windows contain department, type, start/end time, cross-midnight behavior, weekdays, color, status, and effective dates.

### 7.2 Weekly planner

Build one department-aware, mobile-first weekly planner supporting individual, multiple-engineer, and group assignment. Normalize multiple assignments rather than storing delimited users. Integrate with the existing shifts page and preserve existing records.

Features include department/week filters, reusable patterns, copy previous week with preview, edit before save, publish state, today/upcoming views, overnight display, basic overlap/leave/WFH/duplicate conflicts, warnings versus hard blocks, and authorized overrides with reasons.

Show per-engineer scheduled hours, shift count, visit count, after-hours load, conflicts, and unassigned slots. WFH selection is department-aware. Suggestions remain advisory, explainable, and manager-overridable.

### 7.3 Shift review

Report by period, department, engineer, group, shift type, pattern, and status. Include coverage gaps, assigned hours, after-hours/weekend distribution, conflicts, workload balance, and evidence exports.

### 7.4 User and department organizational hierarchy

Add a professional organizational structure for staff independently of security roles and scheduling groups. A user's position in the organization must not implicitly grant application permissions.

Recommended model:

```text
Department
  Id, Code, Name, ParentDepartmentId nullable
  DepartmentHeadUserId nullable
  Status, DisplayOrder, audit fields

User organizational assignment
  UserId
  DepartmentId
  ManagerUserId nullable
  JobTitle/PositionId nullable
  IsPrimaryAssignment
  EffectiveFrom, EffectiveTo nullable
  DisplayOrder, audit fields
```

- Support root departments, child departments/teams, and unlimited reporting levels with cycle prevention and defensive traversal limits.
- Each active user has one primary department assignment; optional secondary assignments must be explicitly labeled and must not create duplicate headcount.
- A manager normally belongs to the same department or an ancestor department. Cross-department reporting requires an explicit approved exception.
- Department Head and direct Manager are separate concepts: a department may have one accountable head while teams retain their immediate managers.
- Reorganizations are effective-dated and audited so historical reports can reproduce the structure applicable during a selected period.
- Inactive users/departments remain visible in historical views but are excluded from current headcount by default.
- Prevent self-management, indirect manager cycles, department-parent cycles, invalid effective periods, and silent orphaning when a manager or department is deactivated.

User Setup additions:

- Primary department, optional secondary departments, job title/position, direct manager, effective dates, and organizational display order.
- Searchable selectors display department path and manager title; manager options exclude the user and descendants.
- Profile/role, privilege, scheduling group, department, and reporting manager remain visibly distinct fields.

Provide a reusable responsive organization-tree component:

- Department hierarchy view and people reporting-line view.
- Expand/collapse all, expand a branch, breadcrumb/path, zoom/fit, and compact/full-card modes.
- Search by employee name, username, email, title, or department.
- Department multi-select filter with `selected department only` or `include sub-departments` scope.
- Filters for active status, manager, job title/position, and users without a manager/department.
- Cards show photo/avatar, display name, title, department, manager/head indicator, direct-report count, and permitted contact/operational summary.
- Selecting a person or department opens the exact authorized profile/detail route using semantic links that support normal click, right-click, and middle-click.
- Large structures load progressively/lazily, preserve expanded nodes and filters in the URL, and provide an accessible list/tree alternative to a visual chart.
- Authorization controls which people and attributes are visible. The structure must not leak private profile information through counts, search, APIs, or hidden nodes.

Add a dedicated `Department Structure` tab to the top-management dashboard. It uses the same shared organization-tree component and hierarchy service, provides department/sub-department filters, current/historical effective-date selection where authorized, headcount/direct-report summaries, vacant-head and unassigned-user indicators, and drill-down links to the exact department or permitted user profile. Do not implement a separate dashboard-only copy of hierarchy logic.

## 8. Client/Sub-client Visit Entitlement and Scheduling

### 8.1 Business rule

Engineers schedule visits from each client's contractual agreement. Therefore, the authoritative allowance is recorded for the exact client or sub-client, contract, contract service period, and visit type.

Example:

| Contract | Exact client | Visit type | Period | Allowed |
|---|---|---|---|---:|
| C-2027 | Cairo | Preventive | 2027 | 4 |
| C-2027 | Giza | Preventive | 2027 | 4 |
| C-2027 | Alexandria | Preventive | 2027 | 2 |

The contract page may total these rows for display, but it must never convert them into a shared pool. A parent entitlement does not cover a sub-client unless the entitlement explicitly names that sub-client or a separately approved inheritance/allocation rule creates an exact child entitlement.

### 8.2 Entitlement model

Use an authoritative entity such as `ClientVisitEntitlement` (the existing proposed `ClientVisitPlan` may implement this if the fields and constraints are equivalent):

```text
Id
ContractId
ClientId                       exact client/sub-client
VisitTypeId
ServicePeriodStart
ServicePeriodEnd
AllowedVisits
Recurrence                     monthly/quarterly/semiannual/annual/custom
SchedulingMode                 EXACT_DATE or DATE_WINDOW
DefaultDurationMinutes
DepartmentId
PreferredLocationId nullable
CarryForwardLimit              default 0
Status                         DRAFT/ACTIVE/SUSPENDED/EXPIRED
ContractVersionId or amendment reference
Created/updated/audit fields
```

Constraints:

- `AllowedVisits >= 0`, valid period, valid exact client-contract eligibility, and no overlapping duplicate active entitlement for the same contract/client/type/period unless explicitly versioned.
- The contract service period, not calendar year alone, controls the allowance.
- Contract amendment, renewal, suspension, or termination creates a new version/effective period; it does not rewrite completed history.
- Carry-forward is disabled by default and, if enabled, is capped, traceable to its source period, and never inferred.
- Manual allowance adjustments require privilege, reason, and an immutable adjustment ledger (`+/- quantity`) rather than destructive editing after usage exists.

### 8.3 Occurrence generation

Generate independent `ClientVisitOccurrence` records from an active entitlement:

```text
Id, EntitlementId, ContractId, ClientId
SequenceNumber, VisitTypeId
WindowStart, WindowEnd, DueDate
ScheduledVisitDate nullable, ActualVisitDate nullable
Status, LocationId nullable, DurationMinutes
GenerationKey, SourceVersion
Notes, Result, NextAction
Created/updated/audit fields
```

- Generation is idempotent through a unique generation key.
- Quarterly allowance may generate Q1–Q4 windows; custom rules distribute the allowed count deterministically.
- Regeneration never duplicates, deletes, or silently changes scheduled/completed occurrences.
- A manager may schedule an exact date inside its window; outside-window overrides require permission and reason.
- Each occurrence has its own one/many engineer or group assignments via normalized `ClientVisitAssignment` records.

### 8.4 Counting ledger and state rules

The dashboard must show, per exact client and service period:

```text
Entitled = active base allowance + approved adjustments + eligible carry-forward
Planned = generated occurrences not cancelled
Scheduled = occurrences with a scheduled date in a schedulable state
Completed = occurrences marked COMPLETED with required completion evidence
Remaining entitlement = max(Entitled - Completed - ChargeableReserved, 0)
Unplanned = max(Entitled - Planned, 0)
Overdue = incomplete occurrences whose window/due date has passed
```

`ChargeableReserved` defaults to zero so a scheduled visit does not permanently consume allowance. If the business elects to reserve capacity at confirmation, show reserved and available separately. Only completion consumes allowance by default.

State machine:

```text
PLANNED -> SCHEDULED -> IN_PROGRESS -> COMPLETED
PLANNED/SCHEDULED -> CANCELLED
SCHEDULED -> RESCHEDULED (audit event; same occurrence remains)
COMPLETED -> REOPENED only with privilege and reason
```

- Rescheduling does not create or consume another entitlement unit.
- Cancelled occurrences do not consume allowance; a chargeable late cancellation requires an explicit policy/event and remains visible.
- No-show and unsuccessful visits are explicit outcomes; whether they consume an allowance is a versioned contract policy, not an ad hoc user choice.
- Completion must be concurrency-safe/transactional so two requests cannot consume the same remaining unit.
- Never count rows by current client name, parent totals, or attachment count. Count exact occurrence IDs under the entitlement ledger.

### 8.5 Planner and engineer workflow

The mobile-friendly Visit Planner filters by department, client path, contract, visit type, window, status, zone/location, engineer, and group. Managers review upcoming/unplanned/overdue visits, choose date/location/duration, assign engineers/groups, see remaining entitlement, and save.

Conflict checks cover shifts, other visits, leave/WFH where relevant, department eligibility, working windows, and optionally travel/zone. Engineer suggestions may consider those facts and workload but remain explainable and advisory.

Engineers see assigned visits and can start, record actual date/duration, notes, outcome/summary, next action, and complete. Attachments belong to the occurrence and use secure existing storage with authorization, type/size validation, malware controls where available, and audit history. Document types include visit report, signed form, screenshot, PDF, image, and other.

### 8.6 Client, contract, hierarchy, and reports

- Client profile: entitlement/complete/remaining, next visit, overdue count, history, and upcoming visits by period/type.
- Sub-client profile shows only its exact visits by default. Parent hierarchy view may aggregate descendants once and must show per-client breakdown.
- Contract view: table per exact client and visit type with entitled, planned, scheduled, completed, remaining, overdue, and next visit.
- Ticket/operation linking is optional but, when used, retains exact client consistency.
- Visit Review filters: dates, client/hierarchy scope, contract, department, engineer/group, type, frequency, status, and zone.
- KPIs/charts: entitled versus completed, planned/scheduled/completed/overdue, remaining/unplanned, completion percentage, trends, and breakdowns by client, engineer, department, and zone.
- Exports disclose period, hierarchy scope, included clients, counting policy, and generation time.

### 8.7 Visit alerts and permissions

Alerts: entitlement not configured, unplanned allowance, scheduling window approaching, overdue visit, contract nearing expiry with remaining visits, incomplete evidence, and allowance exhausted. Notifications must be deduplicated, role-scoped, and auditable.

Privileges: manage visit entitlements, approve adjustments, generate occurrences, schedule/reschedule, assign engineers, override windows/conflicts, start/complete/reopen, upload documents, view exact/hierarchy reports, and export. Reuse existing privileges where equivalent.

## 9. Site Settings, Ticket Notifications, Navigation, and Search

### 9.1 Site Settings

Redesign Site Settings as a categorized tabbed page instead of one long mixed form. Related settings must be kept together, and adding a new setting requires assigning it to the appropriate category rather than appending it arbitrarily.

Proposed tabs (show only categories supported by the installed/current modules):

| Tab | Settings grouped within it |
|---|---|
| General | Site identity, organization, locale, timezone, date/time formats, canonical application URL, and general behavior |
| Branding | Logo, favicon, colors, report/email branding, and portal appearance |
| Email & SMTP | SMTP/server connection, sender identity, reply-to, delivery defaults, test connection, queue/retry defaults, and diagnostics |
| Ticket Notifications | Portal ticket notification settings, internal profile/engineer notification rules, recipients, templates, and test email |
| Tickets & SLA | Ticket defaults, numbering, statuses/priorities where site-configurable, business calendars, SLA defaults, and escalation behavior |
| Client Portal | Portal availability, registration/access behavior, ticket options, catalog behavior, and client-facing defaults |
| Attachments & Storage | File limits/types, storage configuration/status, retention, and attachment security |
| Security & Access | Authentication/session/password settings and other site-wide security controls, subject to higher privileges |
| Integrations | Outlook/email-to-ticket and other configured external integrations |
| Advanced | Rare operational settings, feature switches, maintenance, and diagnostics, with warnings where changes are high-risk |

Do not duplicate a setting across tabs. If an existing setting fits a different label in the actual application, preserve its business meaning and place it in the closest category after inventorying the current page. Tabs should use stable URL state such as `/settings?tab=ticket-notifications`, allowing refresh, bookmarking, right-click, and open-in-new-tab behavior.

Site Settings UX requirements:

- Responsive tab bar: standard tabs on desktop and horizontally scrollable tabs or an accessible category selector on mobile.
- Show only tabs and fields the current user is authorized to view; enforce the same permissions on the backend.
- Each tab has a short description, logically grouped sections, consistent field labels/help text, and its own validation summary.
- Prefer save/cancel per tab so unrelated settings are not submitted or overwritten. Disable Save until that tab is changed and valid.
- Protect unsaved changes when switching tabs, navigating away, refreshing, or opening another settings category. Offer `Stay`, `Discard`, or `Save and continue` where permitted.
- Preserve server validation errors and focus/scroll to the first invalid field. Show success without losing the selected tab.
- Support loading, empty/not-configured, read-only, saving, success, conflict/stale-version, and failure states.
- Use optimistic concurrency/version checks so two administrators cannot silently overwrite one another's settings.
- Record actor, timestamp, category, changed keys, old/new safe values, and reason where required. Secrets must be masked and never returned to the browser after saving.
- Provide category-level warning/invalid badges where useful, but never expose secret values or sensitive diagnostics to unauthorized users.

Add the editable ticket notification configuration described below inside the `Ticket Notifications` tab. Access requires the appropriate site-settings/notification administration privilege, and every change is audited.

Portal-created ticket settings:

```text
Enable email when a client portal user creates a ticket    boolean, default false
To addresses                                                required when enabled
CC addresses                                                optional
```

- Seed the suggested `To` value as `Support@millensys.com`, but keep it editable and do not hard-code it in ticket logic.
- Support one or more validated email addresses in `To` and `CC`, stored as normalized recipient entries rather than an ambiguous free-text string where practical.
- Hide or disable `To` and `CC` while the feature is off; show them immediately when enabled.
- Enabling requires at least one valid `To` recipient. Remove duplicates across `To` and `CC`, trim whitespace, and reject malformed addresses.
- Provide a `Send test email` action that uses the unsaved form values, reports delivery/queue outcome, and does not create a ticket.

Internal ticket notification rules:

Replace the fixed “support engineer created a ticket” condition with one or more configurable rules. This supports cases such as a Call Center profile creating a ticket that is automatically assigned to a dedicated Support engineer.

```text
Rule name                                                   required
Enabled                                                     boolean, default false
Creator profiles                                            multi-select, optional
Assigned engineers                                          multi-select, optional
Match mode                                                   ANY or ALL
To addresses                                                 required when enabled
CC addresses                                                 optional
Include matched engineer notification email                  optional
Evaluate initial/automatic assignment                        default true
Evaluate later reassignment                                  default false
```

- `Creator profiles` is a searchable multi-select of active profiles/role groups from the existing authorization model. A rule matches this condition when the ticket creator belongs to any selected profile.
- `Assigned engineers` is a searchable multi-select of active eligible users. A rule matches when any selected engineer is assigned directly to the ticket at the evaluated event.
- `ANY` sends when either a selected creator profile or selected assigned engineer matches. `ALL` requires every configured condition group to match. Empty condition groups are ignored, but an enabled rule must contain at least one creator profile or assigned engineer.
- Each rule has its own normalized `To` and optional `CC` recipients, allowing different profiles or dedicated engineers to notify different support addresses.
- `Include matched engineer notification email` additionally resolves the matched assigned engineer's `Support Notification Email` from User Setup. If it is missing or invalid, retain the rule's configured recipients and record a warning rather than failing ticket creation.
- Evaluate the rule after initial routing and automatic assignment have completed, but only after the ticket transaction commits. Therefore, `Call Center creates -> routing assigns dedicated Support engineer` can match both the creator-profile and assigned-engineer conditions.
- Initial creation is one logical event even when auto-assignment is performed by another service step. It must not generate separate creation and assignment emails.
- Later reassignment is excluded by default. If explicitly enabled for a rule, use a distinct `TICKET_ASSIGNMENT_MATCHED` event and notify only when the ticket enters the selected-engineer scope, not on unrelated edits or repeated saves.
- Profile membership and assignment are evaluated server-side using stable IDs. Renaming a profile/user does not break the rule, and inactive/deleted selections remain visible as historical configuration warnings until removed.

Add an editable `Support Notification Email` field to User Setup for optional dynamic engineer recipients. Do not infer engineer eligibility or profile membership from display names.

Keep portal notification settings and internal notification rules independent. Administrators may enable either, both, or neither. API/import/email-generated tickets use internal rules only when their source is explicitly included in the applicable rule; the initial implementation may restrict internal rules to authenticated staff-created tickets.

### 9.2 Triggering and Delivery

- Queue the message only after the ticket transaction commits successfully. A rolled-back or validation-failed ticket produces no email.
- Use the existing asynchronous email queue, SMTP configuration, retry policy, delivery status, and administration diagnostics; never delay or fail ticket creation because SMTP is unavailable.
- Create one idempotent notification event per `ticket_id + event_type + rule_id + rule_version` so request retries cannot send duplicates.
- If several enabled rules match the same event, evaluate every rule but coalesce identical recipient/message combinations and deduplicate addresses across `To`, `CC`, and dynamic engineer recipients. Preserve all matched rule IDs and reasons in the delivery audit.
- Snapshot resolved `To`, `CC`, template/version, ticket source, and trigger reason in the delivery record. Later settings changes do not alter historical delivery evidence.
- Do not place recipients in BCC unless a future explicit setting is added. Do not send to the client implicitly from these internal-notification settings.
- Log queued, sent, retrying, failed, and suppressed outcomes without exposing SMTP credentials or sensitive message content in ordinary logs.

### 9.3 Email Content

Provide editable/versioned subject and body templates with safe system defaults. Both HTML and plain-text forms should be generated. At minimum include:

- Ticket number and clickable ticket URL.
- Ticket title and description, safely escaped/sanitized.
- Exact client/sub-client name and hierarchy path where applicable.
- Branch/site, requester name, requester email, and requester phone when present and authorized for the recipient.
- Source (`Client Portal`, `Internal User`, or another explicitly configured source), creator name/profile, creation date/time with timezone, ticket type, priority, status, product/module/service, contract, and assigned engineer/group when available.
- A clear fallback such as `Not specified` for optional values; never fail rendering because a field is empty.

The ticket URL is built from a configured canonical public application base URL, never from an untrusted request `Host` header. It must route the recipient to the exact ticket after login and preserve the intended destination through authentication. Authorization remains enforced when the link is opened; possession of the URL grants no additional access. Do not include attachments in the notification unless separately approved.

Suggested default subject:

```text
[Support Hub] New ticket {{ticket_number}} — {{ticket_title}}
```

### 9.4 Browser-native Open in New Tab

All safe navigable items throughout the internal application and client portal must expose a real URL and support normal browser behavior:

- Right-click shows the browser context menu including `Open link in new tab`.
- Middle-mouse/scroll-wheel click opens the destination in a new tab.
- `Ctrl+Click` on Windows/Linux and `Cmd+Click` on macOS open a new tab; `Shift+Click` may open a new window according to browser behavior.
- Normal primary click keeps the existing single-page navigation experience.

Apply this to navigation menus, breadcrumbs, dashboard cards with destinations, ticket numbers/titles/rows, clients, contracts, users, reports, visits, shifts, notifications, search results, and other entity/page links. Render navigable elements as semantic anchors with valid `href` values (or router link components that output anchors). Do not use click-only `div`, table-row, or button handlers for navigation, do not suppress the context menu, and do not call `preventDefault` for modified or middle clicks.

Where an entire row is clickable, include a primary semantic link inside the row and make auxiliary interactive controls independent; avoid invalid nested links and accidental row navigation when selecting text, opening a menu, checking a box, or clicking an action button. Destructive commands, form submissions, modal-only actions, disabled items, and controls with no stable route are not “open in new tab” targets.

Routes opened directly in a new tab must survive refresh, load required data from the URL, show loading/not-found/unauthorized states, and return through login to the original deep link. Preserve only non-sensitive useful URL state such as entity ID, report filters, hierarchy scope, pagination, and tab selection. Establish a shared link component and audit existing click-only navigation so behavior remains consistent and accessible (keyboard focus, Enter activation, meaningful accessible name).

### 9.5 Ticket-number Search on the Tickets Page

Add a clearly labeled `Ticket number` search field to the internal Tickets page. If the client portal has a ticket list, provide the same behavior within the portal user's authorized ticket scope.

- Search by the displayed ticket number, including its configured prefix and numeric portion (for example, `TKT-001234` or `1234`).
- Trim whitespace and compare case-insensitively where the ticket-number format contains letters.
- An exact ticket number should be the strongest match. Partial/prefix matching may return multiple tickets, but must use documented minimum-length and result-limit rules to prevent expensive broad scans.
- Apply the search server-side across the full authorized dataset, not only the currently loaded page.
- Combine ticket-number search with existing filters using `AND`; clearing the field restores the prior filtered list.
- Debounce typed searches or submit on Enter/search-button activation. Reset pagination to page 1 when the value changes.
- Store the search value in the URL query string so refresh, bookmarking, sharing, browser Back/Forward, and open-in-new-tab preserve it.
- Show a clear empty state for no match and a clear/reset action. Invalid ticket-number syntax should display useful guidance without breaking the list.
- Search results retain normal sorting and display ticket number as a semantic deep link to the ticket.
- Enforce normal ticket/client/portal authorization in the query. A valid number outside the user's scope must appear as no accessible result and must not disclose whether the ticket exists.
- Add an indexed normalized ticket-number lookup where the existing schema/query plan requires it; avoid unindexed string transformations over the full tickets table.

### 9.6 Notification, Navigation, and Ticket-search Acceptance Tests

- Current Site Settings are inventoried and each setting appears in exactly one appropriate tab without changing its stored meaning or default.
- Authorized tab visibility, per-tab save/cancel, validation focus, unsaved-change decisions, concurrent-edit detection, mobile category navigation, refresh, bookmark, and direct-tab URLs work correctly.
- Saving one tab does not submit, reset, or overwrite values in another tab; secret fields remain masked and audit records exclude recoverable secret values.
- Portal ticket with the feature disabled sends nothing; when enabled it queues exactly one message to normalized `To` and `CC` recipients.
- Settings cannot be enabled without a valid `To`; test email does not create a ticket.
- Internal rules validate enabled state, at least one condition, searchable multi-profile/multi-engineer selections, match mode, and rule-specific recipients.
- Test profile-only, engineer-only, `ANY`, and `ALL` matching, including Call Center creation followed by automatic assignment to a selected dedicated Support engineer.
- Initial auto-assignment produces one logical creation notification; later reassignment sends nothing by default and sends one distinct event only when explicitly enabled and entering the configured assignment scope.
- Dynamic matched-engineer email resolution, missing-address warnings, overlapping rules, and recipient/message deduplication behave deterministically.
- Transaction rollback, repeated HTTP request, queue retry, and worker restart do not create duplicate logical notifications.
- Email includes correct escaped ticket details and a canonical deep link; an unauthorized recipient cannot access the ticket through that link.
- Settings/template changes are audited and historical delivery records preserve resolved recipients/version.
- Right-click, middle-click, modifier-click, normal click, direct URL load, refresh, and login return work for representative links in every module and both portals.
- Clicking row actions, checkboxes, menus, or destructive controls does not trigger unwanted navigation.
- Keyboard and screen-reader checks confirm that links are semantic and discoverable.
- Exact full number, numeric-only number, prefix/partial value, mixed case, surrounding whitespace, invalid input, no match, and clearing produce the expected results.
- Ticket-number search combines correctly with client/status/date/engineer filters, searches beyond the loaded page, resets pagination, and persists through URL refresh and browser navigation.
- Unauthorized and cross-client ticket numbers reveal no ticket data; query performance uses the intended index on representative production-scale fixtures.

# Part III — Performance and Management Intelligence

## 10. Performance, Reporting, Dashboards, and Forecasting

### 10.1 P0 — KPI Governance (`READY`)

Approve formulas, sources, targets, reporting periods, RAG thresholds/direction, complexity weights (`1/2/3/5` proposed), ownership, engineer-score weights, and minimum evidence. The same KPI must not have different formulas across reports.

### 10.2 P1 — Engineer Worklogs (`READY`)

Capture ticket, engineer, date, minutes, activity type, normal/after-hours, billable flag, notes, creator, and audit. Add timer/manual entry, correction permission/reason, and overlap/implausible-duration validation. Work effort comes only from approved worklogs, never elapsed ticket age.

### 10.3 P2 — Client Feedback (`READY`)

Capture overall, response, and resolution ratings; optional comment; fully-solved answer; ticket/contact/channel/time; one active response with audited amendments. Add portal form/reminders, low-score follow-up, response rate, and minimum sample handling.

### 10.4 P3 — Cause, Outcome, and Pending Data (`READY`)

Controlled pending responsibility, resolution type, root cause/domain, recurrence/known problem, complexity, and estimate. Target at least 95% structured outcomes on new closures.

### 10.5 P4–P5 — Client and Department Reports

Client summary/renewal pack covers contract, coverage, requests, backlog, SLA, worklogs, escalations, reopens, causes, permanent fixes, feedback, trends, risks, and exact visit entitlement/delivery. Department scorecard covers flow reconciliation, SLA/breaches, response/resolution distributions, aging, priority, effort/capacity, shifts, visits, after-hours load, leading clients/products/causes, feedback, and renewal risk. Every number drills down and exports reconcile.

### 10.6 P6–P7 — Engineer Scorecards and RAG Trends

Balanced scoring considers SLA, quality/reopens, complexity-weighted productivity, feedback, workload/after-hours, and knowledge/prevention. Normalize for working days, shifts, leave, priority, complexity, and team outcomes. Require minimum evidence and manager review. Store target/current/previous/variance/RAG/trend and deterministic explanations.

### 10.7 P8–P10 — Renewal, Snapshots, and Forecasting

Renewal health includes expiry/notice dates, request and visit allowance usage, work hours, SLA, aged/critical tickets, recurrence, feedback, engagement, and service adoption. Produce versioned transparent risk, owner, next action, scope recommendations, and meeting pack. Add immutable month-end snapshots, scheduled delivery/audit/retry, authorized rebuild with reason, then forecasting only after at least six months of reliable data, with confidence and measured accuracy.

Renewal and finance analytics use the explicit lifecycle and ledger records from Sections 6.5, 6.6, and 6.8. Permission-controlled metrics include renewals due/pipeline/completed/rejected/cancelled; contract and product renewal rates; expiring/renewed/lost value; contracted/scheduled/invoiced/collected/outstanding/overdue amounts; approved/invoiced/collected ticket-charge value; and collected income by client and collection date range. Every metric uses server-side fixed-precision calculations and exact source drill-downs.

The client profile shows a Financial section only when the viewer has permission and data exists. Word/Excel exports apply the same permission and optional-section rules; interactive charts become matching static charts plus supporting detail tables. Shared-contract client reporting includes allocated and unallocated values explicitly.

### 10.8 Dashboard Card and Chart Consolidation

Audit all dashboards and dashboard tabs before adding further metrics. Build a dashboard-component inventory containing component ID, title, KPI/formula, filters and scope, visualization type, data source/API, audience, current tabs, permissions, and drill-down destination. Use the inventory to identify true duplicates rather than relying only on similar titles.

Consolidation rules:

- Every KPI card or chart has one canonical dashboard/tab based on its primary audience and decision purpose.
- Remove duplicate components when they use the same formula, scope, period, data source, and visualization without providing a distinct decision context.
- Do not remove components that look similar but represent different scopes or formulas. Rename them clearly and display scope/period so the difference is obvious.
- When another dashboard needs awareness of the same KPI, show a compact linked summary only when it materially supports that dashboard's workflow. The summary must use the shared KPI definition and link to the canonical detailed view.
- Do not maintain copied frontend calculation/query implementations. Reuse shared KPI services, selectors, chart components, formatting, filter definitions, and drill-down contracts.
- Prefer one card with a deliberate scope/filter selector over several nearly identical cards, provided permissions and comprehension remain clear.
- Preserve dashboard-specific authorization and client isolation. Removing a duplicate must not expose a canonical component to users who previously lacked access.
- Preserve useful saved filters and deep links where possible. Retired component/tab URLs should redirect to the canonical dashboard with equivalent non-sensitive filters.
- Avoid empty gaps after removal; rebalance the responsive grid and card ordering for desktop, tablet, and mobile.
- Record each keep, merge, move, rename, or remove decision in the inventory, including the replacement destination and business owner approval.

#### 10.8.1 Dashboard Navigation and Evidence Rules

- Every actionable KPI card, chart series, segment, legend value, and summary count must define its real evidence target: the specific ticket/report/entity list capable of displaying the records used to calculate that value.
- A click must open that target with the complete calculation context already applied, not a general module landing page. Preserve applicable period/date basis, client/hierarchy scope, department, engineer/group, contract, status, priority, SLA state, visit state, product/module/service, source, timezone, and any chart-series/category selection.
- Use stable, documented URL query parameters for filter state. Normal click uses in-app navigation; semantic links must also support right-click, middle-click, modifier-click, refresh, bookmarking, and sharing without losing filters.
- Chart points/segments that cannot be rendered directly as anchors must provide an accessible action/link with the same destination and must honor modified-click behavior where technically supported. Never make a decorative chart element appear clickable without a valid evidence destination.
- The target page parses and visibly displays every transferred filter as active filter chips/fields. Unsupported, expired, or unauthorized filter values produce an explicit message and safe fallback; they must not be silently discarded.
- The target list is filtered server-side across the full authorized dataset. Client and user authorization is reapplied and URL manipulation cannot expand scope.
- Dashboard and target use the same KPI definition, inclusion/exclusion rules, timezone, and as-of boundary. The target should show the evidence-row count and, where aggregation is not one-row-per-record, explain why the KPI value and row count differ.
- Returning with browser Back restores the dashboard tab, filters, period, scroll position where practical, and selected chart context.
- Cards that are informational calculations without row-level evidence must link to the precise explanatory report/methodology view or be clearly non-clickable; never redirect them to an unrelated general page.

#### 10.8.2 Suggested Canonical Dashboard Ownership

| Metric family | Canonical dashboard |
|---|---|
| Incoming tickets, status, priority, backlog, aging | Operational/Department dashboard |
| SLA response/resolution and breach causes | SLA/Performance dashboard |
| Individual workload, worklogs, shifts, and engineer contribution | Engineer/Workforce dashboard |
| Contract usage, covered services, visits, satisfaction, and renewal risk | Client/Contract dashboard |
| Visit schedule, completion, overdue, and remaining entitlement | Visit Review dashboard |

Use existing dashboard names where they differ; the table defines ownership intent, not mandatory labels.

#### 10.8.3 Department Ticket-work and Achievement Cards

Add a prominent `Tickets Worked On` KPI to the Department/Operational dashboard and an attractive `Department Achievements` section visible to ordinary engineers within their authorized department scope.

Define `Tickets Worked On` as the distinct count of tickets with at least one qualifying department activity during the selected reporting period—not simply tickets created during the period or all tickets currently stored. Qualifying activity should be approved during KPI governance and should initially include auditable events such as assignment/acceptance by the department, status or resolution work, approved worklog, technical note, escalation action, or closure by an eligible department member. Exclude automated/system-only changes, duplicate audit writes, and passive viewing.

Display supporting context beside the headline value:

- Selected department and period.
- Unique tickets worked on.
- New tickets received during the same period.
- Resolved/closed tickets during the period.
- Tickets still active at period end.
- Previous comparable period, absolute/percentage change, and trend direction when comparable data exists.
- `Insufficient data` rather than a misleading trend when the comparison is unavailable.

Count each ticket once per department per reporting period even if several engineers or activities touched it. Cross-department tickets may count once for each department that performed qualifying work, but the all-departments total must use distinct ticket IDs and clearly disclose that it is not the sum of department rows. The card must link to the exact evidence list with department, period, qualifying-activity definition/version, and authorization filters applied.

#### 10.8.4 Recommended Department Achievement Cards

| Card | Meaning |
|---|---|
| Tickets Worked On | Unique tickets receiving qualifying department work during the period |
| Resolved for Clients | Unique tickets resolved/closed by the department during the period |
| SLA Success | Response/resolution compliance with numerator, denominator, and excluded count |
| Client Appreciation | Satisfaction average plus response count/rate; hidden or marked insufficient below the approved sample |
| Verified Support Effort | Approved worklog hours, available only after trustworthy worklogs are implemented |
| Critical Cases Handled | Unique high-priority tickets worked/resolved, shown with outcome rather than volume alone |
| Permanent Improvements | Permanent fixes, known-problem resolutions, knowledge articles, or recurrence-prevention actions with evidence |
| Contract Visits Delivered | Completed contractual visits versus due/entitled visits for the period |
| Backlog Improvement | Opening versus ending backlog, shown as an achievement only when the reconciled backlog decreased |

#### 10.8.5 Achievement Presentation Requirements

- Use a polished responsive card layout with clear icons, restrained status colors, readable large values, short positive labels, subtle trend indicators, and optional lightweight motion that respects reduced-motion preferences.
- Celebrate verified department outcomes, not vanity metrics. Do not label increased incoming volume, raw work hours, or ticket count alone as success.
- Use team language such as `Our department resolved 184 client requests` and show the period/scope prominently.
- Cards are not an employee leaderboard and must not rank normal engineers by raw ticket count. Individual performance remains governed by the balanced scorecard and minimum-evidence rules.
- Every card uses the shared KPI dictionary, exposes a tooltip/methodology link, supports semantic click/right-click/middle-click, and opens its exact filtered evidence target.
- Allow authorized dashboard configuration to choose which approved cards are visible and their order, while preventing users from changing formulas.
- Show honest zero, loading, unavailable, insufficient-data, and error states; never replace missing data with a celebratory value.
- Ensure color contrast, keyboard access, screen-reader names, responsive behavior, and reduced-motion compliance.

#### 10.8.6 Dashboard and Achievement Acceptance Criteria

- The approved inventory accounts for every existing dashboard card and chart.
- No unexplained duplicate KPI/chart remains across dashboard tabs.
- Canonical and compact-summary values reconcile under identical filters.
- Similar but non-duplicate metrics display their formula/scope difference clearly.
- Drill-down totals, permissions, exports, responsive layout, saved filters, and deep links continue working after consolidation.
- Dashboard API calls and rendering work are equal to or lower than the baseline for equivalent views.
- Every clickable card/chart has a documented target and filter mapping; clicking or opening it in a new tab produces evidence that reconciles to the originating value under identical scope.
- Automated tests fail when a dashboard link drops a required filter, targets a general page, or the destination count/calculation does not reconcile.
- `Tickets Worked On` deduplicates multiple activities/engineers correctly, handles cross-department work according to the disclosed rule, and reconciles to its filtered activity evidence.
- Ordinary engineers can view authorized Department Achievements with accurate period/scope, accessible presentation, and no prohibited individual ranking or cross-department/client disclosure.

# Part IV — Delivery, Quality, and Governance

## 11. Delivery Roadmap

| Wave | Scope | Main exit outcome |
|---|---|---|
| 0 | Decisions, KPI dictionary, entitlement policies, architecture inventory | Approved rules and no unresolved data ownership ambiguity |
| 1 | Hierarchy foundation, departments, resolver correction | Safe shared foundations and backward-compatible migrations |
| 2 | Portal/ticket hierarchy, paginated selectors, shift masters | Exact-client security and scalable administration |
| 2A | Ticket email notifications and semantic navigation | Reliable creation alerts and browser-native deep links |
| 2B | Categorized Site Settings tabs | Related settings are discoverable, permission-safe, and independently editable |
| 2C | Ticket-number list search | Users can locate an authorized ticket directly from the Tickets page |
| 2D | User/department hierarchy foundation | Cycle-safe, effective-dated departments and staff reporting lines |
| 3 | SLA templates/versioning, worklogs, feedback, structured outcomes | Trustworthy operational evidence |
| 3A | Ticket exception approvals and manager finance | Governed inactive-data overrides, pricing, and payment ledger |
| 3B | Effective-dated coverage and renewal lifecycle | Safe coverage retirement, repeat renewals, and partial line renewal |
| 3C | Optional contract finance | Financial profiles, schedules, allocations, receipts, and reconciliation |
| 4 | Visit entitlement ledger and occurrence generation | Contract allowances represented per exact client/sub-client |
| 5 | Weekly shift planner and Visit Planner | Department-aware scheduling with conflict/workload visibility |
| 6 | Bulk coverage/imports and visit completion/documents | Efficient administration and complete field workflow |
| 7 | Client/department/shift/visit reports | Reconciled operational and contractual reporting |
| 7A | Dashboard inventory and consolidation | Each KPI/chart has one canonical home with no unexplained duplicates |
| 7B | Dashboard evidence links and Department Structure tab | Exact filtered drill-downs and management organization visibility |
| 7C | Department Achievements cards | Engineers see verified team outcomes including distinct tickets worked on |
| 8 | Engineer scorecards, RAG trends, renewal intelligence | Fair performance and actionable client risk |
| 9 | Snapshots, scheduled reporting, forecasting | Stable historical and predictive management layer |

Each wave should be implemented as bounded migrations and feature-flagged increments. Do not combine the entire program into one unreviewed release.

Implementation status: Wave 0 is `DONE` as of 2026-08-20. The approved architecture inventory, KPI dictionary and targets, entitlement policy, and decision register D-001 through D-014 are recorded in `WAVE_0_FOUNDATION_BASELINE.md`. Wave 1 has not started.

Wave 1 implementation status: `DONE` as of 2026-08-20. Hierarchy, department-foundation verification, resolver correction, UI, tests, and clean/populated migration rehearsals on SQLite and SQL Server are complete. The SQL Server rehearsal identified and verified correction of the self-reference's restrictive-delete syntax; see `WAVE_1_IMPLEMENTATION_STATUS.md`.

Wave 2 implementation status: `DONE` as of 2026-08-20. Explicit portal hierarchy scopes, affected-client selection, scalable contract selection, shift masters, full gates, and populated SQLite/SQL Server rehearsals are complete; see `WAVE_2_IMPLEMENTATION_STATUS.md`.

Wave 2A implementation status: `DONE` as of 2026-08-20. Portal/internal rule-driven creation notifications, reassignment entry semantics, versioned templates, administration, semantic navigation, full gates, and populated SQLite/SQL Server rehearsals are complete; see `WAVE_2A_IMPLEMENTATION_STATUS.md`.

**Mandatory execution checkpoint:** After completing the explicitly requested wave/sub-wave, Codex must update status, write the `CODEX STOP POINT` defined at the beginning of this document, and stop. It must not begin the next wave without a new explicit instruction.

## 12. Business Decisions and Policy Gates

1. Visit consumption policy for completed, no-show, client-cancelled, and support-cancelled visits.
2. Whether scheduling reserves entitlement or completion alone consumes it (recommended: completion alone).
3. Carry-forward, overage, amendment, suspension, and early-termination rules.
4. Whether any hierarchy visit inheritance is needed (recommended: store materialized exact-client entitlements).
5. SLA target precedence and whether client-specific SLA targets are needed for the same product.
6. KPI/RAG definitions, worklog requirements, feedback questions/channel, engineer-score weights, and score visibility.
7. Conflict types that warn versus block and who may override them.
8. Confirm whether internal notification rules default to `ANY` or `ALL`, whether later reassignment may trigger notifications, and which staff-created/API/import sources administrators may include.
9. Approve department ownership, department heads, manager-reporting rules, secondary assignments, historical effective dating, and which organization details top management and other roles may view.
10. Approve the qualifying activity events for `Tickets Worked On`, its cross-department attribution rule, achievement-card targets, comparison periods, and which cards ordinary engineers may view.
11. Approve which inactive/ineligible ticket conditions permit approval versus direct override, approver routing, self-approval/emergency policy, pending-approval SLA clock behavior, and pending-ticket operational visibility.
12. Approve fee/tax/discount authority, payment-before-work/closure policies, client visibility, overpayment/refund rules, supported currencies/conversion policy, invoice ownership, and whether external accounting integration is required.
13. Decide whether renewal completion creates a successor contract or a new version under the same identity, plus legacy renewal-date backfill labeling and parallel-proposal policy.
14. Approve renewal/payment/ticket-charge roles and value thresholds, shared-contract allocation rules, and portal visibility for quotations, invoices, charges, and payment status.

These decisions should be stored as versioned policy/master data when they affect historical calculations.

## 13. API, Migration, and Data Delivery Checklist

- Next Alembic revisions after current head; named constraints compatible with SQL Server and SQLite.
- Backfill hierarchy/portal/contract scopes to exact-client defaults.
- Add hierarchy endpoints and compact path/count metadata without recursively embedding unlimited trees.
- Add paginated search and bulk preview/commit endpoints.
- Add SLA template/version/target and import endpoints.
- Add department, shift type/pattern, planner, assignment, copy, publish, and review endpoints.
- Add cycle-safe/effective-dated department and user-reporting hierarchy endpoints, filtered organization-tree queries, orphan validation, and authorized management summaries.
- Add visit entitlement, adjustment, generation, occurrence, assignment, lifecycle, attachment, summary, and report endpoints.
- Add worklog, feedback, classification, KPI snapshot, renewal, and reporting endpoints in their waves.
- Add versioned site settings for both notification triggers/recipients/templates, User Setup support-notification email, test-email endpoint, and idempotent delivery-event metadata.
- Add transactional ticket-exception validation, approval lifecycle, permission-controlled override, immutable exception/SLA snapshots, notification routing, and pending-approval list endpoints.
- Add manager-only pricing revisions, service financial configuration, payment/reversal ledger, calculated balances, finance filters/reports, and independent finance permission enforcement.
- Add contract renewal/opportunity and renewal-line lifecycle, current/proposed comparison, approval, atomic successor/version completion, explicit KPI, and legacy-backfill metadata endpoints.
- Add effective-dated coverage end/impact-preview operations; prevent hard deletion after usage and retire dependent future SLA targets consistently.
- Add optional contract financial profile, payment schedules, invoice references, receipt/reversal transactions, shared-client allocations, unallocated-value reporting, and fixed-precision reconciliation endpoints.
- Move contract administration to a permission-aware full-page tabbed workspace while preserving existing contract/entitlement services and compatible routes during migration.
- Add category-scoped Site Settings read/update contracts with concurrency versions; keep compatibility adapters for existing settings consumers during migration.
- Extend the ticket-list API with a validated ticket-number query parameter and add/confirm an efficient normalized ticket-number index.
- Index all client, contract, period, status, scheduled/due date, department, engineer, and generation-key query paths.
- Make generation, bulk selection, imports, completion, and adjustments transactional and idempotent where applicable.
- Rehearse clean install and populated upgrade on SQLite and SQL Server; provide rollback/feature-disable steps.

## 14. Verification and Test Strategy

### Security and hierarchy

- Reject cycles, invalid parent changes, unauthorized descendants/siblings, tampered client/branch/contact/contract IDs, and portal scope expansion.
- Preserve standalone behavior and exact ownership after reparenting.
- Reconcile `SELF`, direct-child, and full-hierarchy totals without double counting.
- Reject department and manager cycles, invalid cross-department reporting/effective dates, duplicate primary assignments, and unauthorized organization-tree data; verify reorganizations preserve historical views.

### Contract and SLA

- Paginate/search beyond 50/200 items; verify all-matching plus exclusions.
- Test candidate precedence, coverage inclusions/exclusions, ambiguity rejection, default and scoped SLA targets, version publishing, imports, and historical snapshots.
- Test inactive client/contract/product/module/service/SLA submissions, consolidated approval routing, approve/reject/return/expire, revalidation, SLA start/snapshot policy, portal scope, self-approval prevention, direct-override visibility and backend denial, mandatory reasons, and reapproval after material edits.
- Test manager-only pricing, default-versus-confirmed fee snapshots, tax/discount arithmetic, pricing revisions, payment-before-work/closure gates, partial/multiple payments, reversals/refunds, duplicate references, currency/overpayment validation, concurrency, sensitive-value visibility, and financial report reconciliation.
- Test repeated renewal cycles, sequential numbers, partial `RENEW/ADD/REMOVE/CHANGE` lines, rejection/cancellation retention, current/proposed differences, approval thresholds, atomic completion, predecessor/successor history, explicit renewal KPIs, and legacy inferred/backfilled labels.
- Test effective-dated coverage ending, impact preview, draft-unused hard-delete restriction, open-ticket behavior, dependent SLA retirement, and unchanged historical entitlement/SLA clocks.
- Test blank optional finances, decimal precision, contract billing models/schedules, invoice versus collection measures, overdue dates, multiple receipts/reversals, shared-client percentage/amount allocations, unallocated income, and permission isolation across APIs/search/audit/notifications/profile/export/drill-down.

### Shifts and visits

- Test cross-midnight shifts, multi-assignment, group expansion policy, copy week, overlaps, department eligibility, WFH/leave, publish, mobile layouts, and workload totals.
- Test entitlement per sibling sub-client, non-calendar contract periods, amendments, carry-forward, idempotent generation, concurrency, reschedule/no duplicate consumption, cancellation/no-show policy, window overrides, contract expiry, occurrence assignments, attachments, and completion evidence.
- Verify `entitled = completed + remaining` under the approved reservation/adjustment policy and reconcile contract aggregate to client rows.

### Performance reporting

- Fixed-fixture formula tests, worklog reconciliation, feedback isolation/minimum sample, flow equation, fairness normalization, snapshot immutability, scheduled-delivery retry, and forecast back-testing.
- Test the dashboard inventory against rendered components, canonical/summary reconciliation, duplicate removal, permissions, filter/deep-link migration, responsive grid layout, drill-downs, and before/after API/render performance.
- Test every card/chart target against its filter-mapping contract, exact evidence reconciliation, semantic new-tab behavior, URL tampering, visible destination filters, browser Back restoration, and explicit handling of unsupported filters.
- Test Department Structure filtering with/without descendants, people search, expand/collapse, lazy loading, headcount deduplication, current/historical dates, vacancies/orphans, responsive layouts, accessibility, and profile/department deep links.
- Test `Tickets Worked On` event qualification, distinct-ticket deduplication, period boundaries/timezones, cross-department attribution, all-department reconciliation, previous-period comparison, achievement permissions, insufficient-data behavior, exact evidence links, accessibility, and reduced-motion presentation.

### Notifications and navigation

- Test trigger/source classification, recipient validation/resolution, CC deduplication, post-commit queueing, idempotency, retries, rendering/sanitization, canonical URLs, permission enforcement, audit history, and disabled behavior.
- Test semantic links, pointer/modifier behavior, deep-link refresh/login return, URL filter state, accessibility, and non-navigation controls across desktop and supported mobile/touch behavior.
- Test settings-category authorization, exact-once placement, per-tab mutation isolation, unsaved changes, stale concurrent updates, secret masking, responsive tabs, keyboard navigation, and direct-tab deep links.
- Test ticket-number exact/partial matching, filter composition, URL state, pagination, authorization non-disclosure, and production-scale query performance.

### Standard quality gates

- Backend Ruff, Mypy, and Pytest.
- Frontend ESLint, Vitest, TypeScript, and production build.
- Authorization, audit, migration, calculation, empty/loading/error, desktop/mobile, export, rollback, and post-deployment smoke tests.

## 15. Release and Rollout Controls

- Feature flags for hierarchy, SLA master data, planners, visits, and scorecards.
- Deploy schema before enabling configuration; retain backward-compatible defaults.
- Pilot with a controlled hierarchy/contract and compare old/new totals.
- Preview contract eligibility, SLA resolution, and visit entitlements before activation.
- Do not delete historical planning, entitlement, occurrence, or snapshot data during rollback; disable features and restore prior read paths.
- Monitor authorization denials, resolver ambiguity, duplicate generation attempts, overdue visits, migration errors, and report reconciliation.
- Roll out ticket notification switches disabled by default; verify SMTP/test delivery and canonical application URL before enabling production recipients.
- Introduce semantic-link conversions module by module with navigation regression checks.
- Release renewal/finance work in independent safety, renewal/SLA, contract-finance, chargeable-ticket, and analytics/UX increments; update `RELEASE_STEPS.md` during every implementation/release session.
- Verify clean install, populated upgrade, recovery/downgrade strategy, seeds, optional-all-blank financial compatibility, and historical-data preservation before enabling finance features.

## 16. Definition of Done

- One maintained roadmap governs the consolidated feature groups and source requirements.
- Unlimited client hierarchy is cycle-safe and exact-client authorization is enforced.
- Contract configuration scales to large client/catalog sets and coverage is auditable.
- SLA templates and targets are deterministic, versioned, importable, and historically safe.
- Tickets involving inactive clients or inactive/ineligible contract/catalog/SLA data follow an auditable approval cycle or an explicitly permitted, reasoned override; unauthorized users never see or execute the override.
- Financial services use manager-controlled, versioned ticket fees and a permission-protected, reconcilable payment ledger that remains separate from operational ticket state.
- Contracts support multiple explicit renewal opportunities, partial coverage-line outcomes, effective-dated coverage retirement, and immutable successor/version evidence.
- Optional contract and ticket finance distinguishes contracted, billable, invoiced, collected, outstanding, overdue, allocated, and unallocated values; only confirmed collections are income.
- Support and Call Center use one department-aware shift planner on desktop and mobile.
- Every contract visit allowance is traceable to an exact client/sub-client and service period.
- Engineers can be scheduled per occurrence, complete visits, and attach evidence without double counting.
- Portal and support-engineer ticket creation notifications are independently configurable, reliable, deduplicated, auditable, and contain secure ticket deep links.
- Every navigable page/entity uses browser-compatible semantic links wherever a stable destination exists.
- Site Settings are organized into responsive, permission-aware categories, and each tab can be validated and saved without affecting unrelated configuration.
- Authorized users can find tickets efficiently by ticket number from ticket lists without weakening client isolation.
- Client, contract, hierarchy, shift, visit, department, and engineer reports reconcile to source evidence.
- Dashboard tabs contain no unexplained duplicate cards/charts; each shared KPI has one documented canonical owner and any secondary summary links to it.
- Every actionable dashboard value opens its real evidence target with complete working filters and reconciles to the originating calculation.
- Users and departments have a professional, cycle-safe, permission-aware organizational structure, including department filtering and a shared top-management dashboard tab.
- Department dashboards show a reconciled distinct `Tickets Worked On` metric and accessible, evidence-backed team achievement cards to authorized engineers without encouraging unfair raw-count rankings.
- Performance measures use trustworthy worklogs, feedback, outcomes, fair normalization, and immutable snapshots.
- Clean install, upgrade, security, regression, calculation, and production build gates pass for every released wave.

## 17. Traceability to Source Plans

| Original plan | Consolidated sections |
|---|---|
| Client Hierarchy Implementation Plan | 2, 4, 5, 11–16 |
| Contract Configuration and SLA Master Data Implementation Plan | 2, 4, 6, 11–16 |
| Shifts Planner | 2, 4, 7, 8, 11–16 |
| Support Performance & Improvement Development Plan | 2, 4, 10–16 |
| Additional ticket notification and browser-navigation requirements | 2, 9, 11–16 |
| Contract Renewal, Finance, and Chargeable Ticket Development Plan | 2, 6, 10–16 |

When a source file and this plan conflict, this master plan controls after business approval. Detailed implementation discoveries should be added to the applicable master section rather than creating another independent plan file.

============================================================
CODEX STOP POINT
Status: DONE
Completed scope: Wave 7C — Department Achievements
Last completed item: Passed full gates and clean/populated SQL Server rehearsals through Wave 7C
Next planned item: Wave 8 — Engineer Scorecards, RAG Trends, and Renewal Intelligence
Safe to continue from here: YES
Blocking decision(s): None
Database revision: 0103_visit_completion
============================================================
