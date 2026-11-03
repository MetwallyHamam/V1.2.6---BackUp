# Contract Renewal, Finance, and Chargeable Ticket Development Plan

Status: approved for future implementation; no application behavior has been changed yet.

This document is the durable implementation specification for enhancing the
SupportHub contract lifecycle. It covers repeat renewals, partial product
renewals, effective-dated coverage removal, dynamic SLA governance, optional
contract finances, payment scheduling, chargeable tickets, permissions,
dashboards, reports, client profiles, and the contract workspace UX.

## Product principles

- All financial data is optional. Existing contracts and tickets must continue
  to work without financial values.
- Financial information is protected by backend permissions, not merely hidden
  by the frontend.
- Historical contract, coverage, SLA, renewal, and financial evidence is never
  rewritten or hard-deleted after it has been used.
- Money uses fixed-precision decimal database columns and an explicit currency.
- Contracted, billable, invoiced, collected, outstanding, and overdue amounts
  are separate measures. Only collected payments are reported as income.
- Charts and KPI cards must drill down to the records used in their calculation.
- Every approval, amount change, status transition, waiver, removal, and payment
  is written to the audit trail.

## 1. Renewal lifecycle

Do not update one renewal date repeatedly. Preserve every renewal opportunity
and outcome.

### Proposed `ContractRenewal`

- `id`, `contract_id`, and sequential `renewal_number`
- `status`: `DRAFT`, `UNDER_REVIEW`, `APPROVED`, `COMPLETED`, `REJECTED`, or
  `CANCELLED`
- notice, due, proposed-start, proposed-end, decision, and completion dates
- owner, probability, notes, rejection/cancellation reason
- proposed value and currency when financial management is enabled
- predecessor and successor contract/version references
- created/updated and approval audit fields

### Proposed `ContractRenewalLine`

Each line identifies a product, module, service, or existing coverage record.

- action: `RENEW`, `ADD`, `REMOVE`, or `CHANGE`
- current and proposed coverage dates
- current and proposed price when used
- current and proposed SLA policy/target references
- status, notes, and display order

This supports multiple renewal cycles for one contract and renewal of only some
products or services. Completing a renewal must produce a new contract version
or successor snapshot rather than altering historical evidence in place.

### Renewal KPI definitions

- Contract renewal rate = completed contract renewal opportunities due in the
  selected period / all eligible contract renewal opportunities due in that
  period.
- Product renewal rate uses renewal lines, not contract counts.
- Rejected and cancelled outcomes remain visible and are not counted as renewed.
- Pipeline, expiring value, renewed value, lost value, and days-to-renewal are
  separate KPIs.

The existing date-inference renewal calculation must be retired after historical
renewal records are available. A migration/backfill rule must be documented so
older contracts are not silently presented as confirmed renewals.

## 2. Coverage and service removal

Coverage used by tickets must be ended, not deleted. Extend contract coverage
with lifecycle fields:

- `status`
- `effective_from` and `effective_until`
- `removed_at`, `removed_by`, and `removal_reason`

The removal operation must show the selected effective date, affected clients,
open tickets, and SLA targets. Ending coverage prevents matching for new tickets
after that date but retains historical entitlement and SLA evidence. Hard delete
is permitted only for unused coverage belonging to a draft contract.

When coverage is ended, dependent SLA targets are retired or effective-ended for
future matching. Existing ticket SLA clocks and entitlement snapshots remain
unchanged.

## 3. Dynamic SLA enhancement

Add a controlled SLA lifecycle: `DRAFT`, `PUBLISHED`, and `RETIRED`.

The SLA workspace should provide:

- a priority response/resolution matrix;
- product, module, service, and context targeting;
- effective dates and version history;
- copy-from-previous-version;
- overlapping-target and missing-target validation;
- a test matcher that explains which rule wins for sample ticket inputs;
- an impact preview before publishing or retiring a version.

Ticket creation and reassignment must store the matched policy/target version and
calculated deadlines. Later policy changes must not recalculate historical clocks
unless an explicitly authorized, audited recalculation process is introduced.

## 4. Contract financial process

### Proposed financial profile

Use a contract financial profile or equivalent optional fields:

- currency;
- contract value;
- tax and discount values;
- billing model: `FIXED`, `INSTALLMENT`, `USAGE`, or `HYBRID`;
- purchase order/reference;
- financial notes.

Currency becomes required only when a monetary amount is supplied.

### Proposed payment schedule

`ContractPaymentSchedule` records should include:

- milestone/installment number and description;
- due date, amount, currency, tax, and discount;
- status: `PLANNED`, `INVOICED`, `PARTIALLY_PAID`, `PAID`, `OVERDUE`, or
  `CANCELLED`;
- invoice number/date;
- paid amount/date and remaining balance;
- notes and audit fields.

Use separate payment/receipt transactions when one installment can be collected
through multiple payments. Do not store a single payment status on the contract.

For contracts shared by multiple clients, add optional client allocations by
percentage or amount. Client-income reporting must label money as unallocated
until a valid allocation exists; it must not guess the split.

## 5. Chargeable tickets

An out-of-contract entitlement result may suggest that a ticket is chargeable,
but the system must never create a financial charge automatically.

### Proposed `TicketCharge`

- `ticket_id`
- type: `OUT_OF_SCOPE`, `EXTRA_SERVICE`, or `MANUAL`
- status: `DRAFT`, `APPROVED`, `INVOICED`, `PARTIALLY_PAID`, `PAID`, `WAIVED`,
  or `CANCELLED`
- amount, currency, tax, reason, and notes
- proposed, approved, invoiced, and paid audit references/dates
- invoice and payment references

The ticket may optionally expose a billing disposition such as `INCLUDED`,
`CHARGEABLE_PENDING`, `CHARGEABLE_APPROVED`, `WAIVED`, or `NOT_APPLICABLE`.
A ticket can remain valid without a charge and may contain multiple charges.

Recommended workflow:

1. Entitlement identifies the service as not covered.
2. An authorized manager proposes an optional charge and reason.
3. An authorized approver approves or waives it.
4. Finance invoices and records one or more collections.
5. Dashboard income changes only when collection is recorded.

## 6. Permissions and visibility

Add granular permissions, following the existing effective-permission model:

- `contract.finance.view`
- `contract.finance.manage`
- `payment.view`
- `payment.manage`
- `ticket.finance.view`
- `ticket.finance.manage`
- `dashboard.finance.view`
- `report.finance.export`

Financial endpoints must return only authorized data. List/detail payloads,
search, audit events, notifications, exports, client profile, and dashboard
drilldowns all require permission review. Ordinary engineers and portal users
must not receive financial values unless a separate approved role grants access.

## 7. Contract workspace UX

Move the large contract dialog to a full route such as `/contracts/:id`, while
preserving the current contract and entitlement logic behind the new shell.

Recommended tabs:

1. Overview
2. Customers
3. Scope and Coverage
4. SLA
5. Renewals
6. Financials
7. Documents
8. Audit History

The sticky header should show status, client, dates, renewal state, and authorized
financial summaries. Contract creation should use a guided flow:

`Basics -> Customers -> Coverage -> SLA -> Optional Finance -> Review`

Coverage needs search, filters, bulk actions, and a visible End/Remove action.
Renewal needs a Current versus Proposed comparison and highlighted differences.
Financials needs summary cards, an installment table/timeline, balance validation,
and source-record drilldowns.

## 8. Dashboards, reports, and client profile

Permission-controlled dashboard metrics may include:

- renewals due, pipeline, completed, rejected, and cancelled;
- contract and product renewal rates;
- expiring, renewed, and lost contract value;
- contracted, scheduled, invoiced, collected, outstanding, and overdue value;
- approved, invoiced, and collected paid-ticket value;
- income by client and selected date range.

The client profile receives an optional Financial section only when the user has
permission. Word and Excel exports include that section only when the requesting
user is authorized and financial data exists. UI cards, charts, and exported
totals must use the same server-side calculations. Interactive web charts become
matching static charts in Word, with a supporting detail table.

## 9. Delivery phases

### Phase 1 - Safety foundation

- Database design, migrations, permissions, and audit events.
- Effective-dated coverage removal and UI correction.
- Financial precision, currency, and shared-client allocation rules.
- Regression tests protecting ticket entitlement and SLA history.

### Phase 2 - Renewals and SLA governance

- Renewal and renewal-line workflow.
- Partial product/service renewal.
- SLA draft/publish/retire, matcher preview, and impact validation.
- Renewal dashboard definitions and drilldowns.

### Phase 3 - Contract finance

- Optional financial profile.
- Payment schedules, receipts, balances, overdue calculation, and approvals.
- Financial workspace and contract/client drilldowns.

### Phase 4 - Chargeable tickets

- Charge suggestion, approval, waiver, invoicing, and collection workflow.
- Entitlement integration without automatic charging.
- Ticket-level financial audit and permission tests.

### Phase 5 - UX, analytics, and exports

- Full-page contract workspace and guided creation.
- Management dashboards, reports, client profile, Word, and Excel output.
- Performance, accessibility, security, migration, and release validation.

Each phase should be an independently tested release. Do not combine all phases
into one high-risk migration.

## 10. Minimum acceptance criteria

- Multiple renewal cycles can exist for the same contract.
- A renewal can renew, add, change, or remove individual products/services.
- Renewal KPIs use explicit opportunity outcomes and selected-period rules.
- Authorized users can end contract services; historical tickets stay unchanged.
- SLA conflicts are detected before publication and matched rules are explainable.
- Contracts, schedules, and tickets work when every financial field is blank.
- Unauthorized users cannot receive financial values through APIs or exports.
- Partial payments, overdue balances, waived charges, and cancelled entries are
  calculated correctly.
- Client income for a period equals collected, client-attributed payments only.
- Shared-contract money is allocated explicitly or reported as unallocated.
- Every dashboard value drills down to its source records.
- Client-profile and report financial sections are optional and permission-aware.
- Upgrade, downgrade/recovery, seed, clean-install, and historical-data tests pass.

## 11. Decisions required before implementation

- Whether completion creates a successor contract or a version of the same
  contract identity.
- Supported currencies and whether conversion is deferred to a later phase.
- Tax model and whether invoice generation remains external.
- Approval roles and value thresholds for renewals, payments, and ticket charges.
- Client-portal visibility for quotations, invoices, and payment status.
- Backfill policy for existing renewal dates and payment information.

Record these decisions in this file before Phase 1 schema work begins, and update
`RELEASE_STEPS.md` during every implementation session and release.
