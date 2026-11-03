# Wave 0 Foundation Baseline

Status: `DONE`  
Prepared: 2026-08-20  
Controlling plan: `Support_Hub_Unified_Development_Master_Plan_Refactored_With_Stop_Points.md`

Approved: 2026-08-20 by Project Owner through explicit instruction to complete Wave 0.

This document is the approved implementation-ready Wave 0 baseline. It records the current architecture, policy defaults, KPI ownership, and governing business decisions. Changes after approval require a dated amendment and must preserve the policy version used by historical calculations.

## 1. Architecture inventory

### Current platform

| Concern | Current authoritative implementation | Wave impact |
|---|---|---|
| API composition | FastAPI routers registered in `backend/app/main.py` under `/api/v1` | Extend existing domain routers; do not create a second API stack. |
| Persistence | SQLAlchemy models with Alembic; current single head is `0092_client_profile` | New schema work must start at `0093`, use named constraints, and support SQLite and SQL Server. |
| Clients/catalog | `backend/app/modules/clients` | `clients` remains the exact operational owner. Add hierarchy here in Wave 1. |
| Identity/authorization | `backend/app/modules/iam`; profile permissions and explicit client/branch scopes | Hierarchy never implies access. Scope expansion must be explicit and server-validated. |
| Contracts/SLA | `backend/app/modules/contracts` plus `backend/app/modules/sla` | Preserve selected contract and SLA clock evidence; add deterministic hierarchy-aware resolution in later waves. |
| Tickets | `backend/app/modules/tickets` | `tickets.client_id` remains the affected-client authority. Related branch/contact/contract context must independently validate against it. |
| Portal | `backend/app/modules/client_portal` | Replace implicit single-client assumptions only in Wave 2 after explicit portal-scope data exists. |
| Departments/users | `backend/app/modules/iam` | Existing department master is the base; effective-dated organization hierarchy is a later bounded wave. |
| Shifts | `backend/app/modules/shifts` | Reuse existing shift routes/models and evolve them behind permissions and feature policy. |
| Entitlement approvals | `backend/app/modules/entitlements` | Reuse approval/audit patterns; visit consumption requires a separate immutable ledger. |
| Configuration/flags | `backend/app/modules/configuration` | Use existing feature definitions/policies for staged rollout. |
| Notifications | `backend/app/modules/notifications` and `backend/app/modules/outlook_email` | Reuse outbox/delivery records and post-commit dispatch. |
| Reporting/KPIs | `backend/app/modules/dashboards`, `reports`, and `kpis` | Consolidate formulas into shared services before adding new scorecards. |
| Audit | IAM audit log and existing domain audit patterns | Parent changes, policy versions, adjustments, resolver decisions, and privileged overrides require old/new evidence and reasons. |

### Data ownership rules

1. `clients.id` identifies the exact affected client or sub-client; parentage never rewrites ownership.
2. `tickets.client_id`, visit occurrence client ID, worklog ticket/client derivation, and financial allocation client ID are the reporting facts.
3. Contract ownership, contract eligibility, coverage applicability, and portal visibility are separate relations.
4. Historical SLA, entitlement, renewal, finance, and KPI results use immutable snapshots or effective-dated versions.
5. Aggregated hierarchy reports are derived from centralized scope resolution and retain exact-client drill-down rows.

### Migration and rollout constraints

- Existing clients backfill as roots; existing portal and contract access backfill to exact-client/owner-only behavior.
- Every new capability is disabled by feature policy until schema, authorization, and migration checks pass.
- No Wave 1 schema or application scaffolding is part of Wave 0.
- Clean-install and populated-upgrade rehearsal are required for every schema wave on SQLite and SQL Server.

## 2. KPI dictionary baseline

The business owner column names the accountable role; a person must be assigned during approval.

| KPI | Canonical formula | Source of truth | Direction | Business owner role | Approval |
|---|---|---|---|---|---|
| First-response compliance | completed eligible first-response clocks met / completed eligible first-response clocks × 100 | ticket SLA clocks and snapshotted calendar/policy | Higher | Support Operations Manager | Approved |
| Resolution compliance | completed eligible accountable resolution clocks met / completed eligible accountable resolution clocks × 100 | ticket SLA clocks/intervals and snapshotted policy | Higher | Support Operations Manager | Approved |
| First-response business hours | business-time duration from clock start to persisted first-response completion | ticket SLA clock snapshot | Lower | Support Operations Manager | Approved |
| Accountable resolution hours | business-time duration excluding only policy-approved pauses | SLA clock and interval evidence | Lower | Support Operations Manager | Approved |
| Reopen rate | distinct resolved/closed tickets reopened in period / distinct tickets resolved/closed in period × 100 | ticket status history | Lower | Service Quality Manager | Approved |
| Escalation rate | distinct eligible tickets with an escalation event / distinct eligible tickets × 100 | escalation events and tickets | Lower | Support Operations Manager | Approved |
| Backlog | distinct authorized tickets not in terminal status at period end | tickets plus status history/as-of evidence | Lower | Department Manager | Approved |
| Feedback average | arithmetic mean of active valid overall ratings, displayed only with count and response rate | ticket satisfaction responses | Higher | Service Quality Manager | Approved |
| Feedback response rate | tickets with an active valid response / eligible feedback-requested tickets × 100 | satisfaction and delivery/request evidence | Higher | Service Quality Manager | Approved |
| Worklog hours | sum of approved worklog minutes / 60 | future immutable/audited worklogs | Context | Department Manager | Approved |
| Tickets worked on | distinct tickets with at least one approved qualifying engineer activity in period | future governed activity-event view | Context; not a raw ranking | Department Manager | Approved |
| Contract renewal rate | completed eligible renewal opportunities due in period / all eligible opportunities due in period × 100 | future explicit renewal opportunities | Higher | Commercial Manager | Approved |
| Product renewal rate | renewed eligible renewal lines due in period / all eligible renewal lines due in period × 100 | future renewal lines | Higher | Commercial Manager | Approved |
| Collected income | sum of confirmed non-reversed receipts whose collection date is in period | future receipt ledger | Higher | Finance Manager | Approved |
| Outstanding | invoiced or policy-approved due amount less confirmed non-reversed collections | future schedule/invoice/receipt ledger | Lower | Finance Manager | Approved |
| Visit utilization | consumed entitlement units / active entitlement units × 100 for exact client, type, and service period | future visit entitlement ledger | Context | Contract Service Manager | Approved |

Common rules:

- Dates use the configured business timezone; stored timestamps remain UTC.
- Percentages expose numerator, denominator, exclusions, and evidence links.
- A zero denominator returns unavailable, not zero or 100%.
- Averages expose sample count; feedback additionally exposes response rate.
- Monthly, quarterly, annual, custom, and contract-to-date periods use half-open boundaries `[start, end)`.
- Complexity weights are Simple `1`, Standard `2`, Complex `3`, Critical `5`.
- Individual composite engineer scores remain disabled until a later versioned scorecard policy specifies weights, minimum samples, normalization, visibility, and an HR fairness review. This is an approved control, not an unresolved Wave 0 decision.

### Initial management targets and RAG rules

These are program defaults. A future contract or department target may override them only through versioned policy with an effective date. Comparisons use unrounded values.

| KPI | Green | Amber | Red | Minimum evidence |
|---|---|---|---|---|
| First-response compliance | `>= 95%` | `90%–<95%` | `< 90%` | 10 completed eligible clocks |
| Resolution compliance | `>= 95%` | `90%–<95%` | `< 90%` | 10 completed eligible clocks |
| Reopen rate | `<= 5%` | `>5%–10%` | `> 10%` | 10 resolved/closed tickets |
| Escalation rate | `<= 5%` | `>5%–10%` | `> 10%` | 10 eligible tickets |
| Feedback average | `>= 4.2` | `3.5–<4.2` | `< 3.5` | 5 valid responses and response rate shown |
| Feedback response rate | `>= 30%` | `15%–<30%` | `< 15%` | 10 eligible feedback requests |
| Contract renewal rate | `>= 90%` | `75%–<90%` | `< 75%` | 5 eligible due opportunities |
| Product renewal rate | `>= 90%` | `75%–<90%` | `< 75%` | 10 eligible due lines |

First-response hours, accountable resolution hours, backlog, worklog hours, tickets worked on, collected income, outstanding, and visit utilization are contextual measures and do not receive universal RAG colors. They must be compared with their versioned SLA, budget, capacity, financial, or entitlement target. Insufficient evidence renders `INSUFFICIENT_DATA`, never a color.

## 3. Visit entitlement policy proposal

The approved policy favors auditable completion-based consumption and exact-client isolation.

| Event/rule | Proposed policy | Decision ID |
|---|---|---|
| Scheduled/rescheduled | Does not consume or reserve entitlement; concurrency is controlled when completing. | D-002 |
| Completed | Consumes one unit exactly once through an immutable ledger entry. | D-001 |
| No-show | Does not consume by default; a versioned contract policy may consume it. | D-001 |
| Client-cancelled | Does not consume by default; an approved late-cancellation policy may consume it. | D-001 |
| Support-cancelled | Never consumes; any earlier entry is reversed, not deleted. | D-001 |
| Carry-forward | Disabled by default. If enabled, it is capped, source-period linked, expires explicitly, and is never inferred. | D-003 |
| Overage | Block by default; a privileged, reasoned adjustment can add explicit units. | D-003 |
| Amendments | Create effective-dated entitlement/adjustment rows; never rewrite consumed history. | D-003 |
| Suspension | Prevent new scheduling/completion during the effective suspension unless privileged override policy permits it; history remains. | D-003 |
| Early termination | End future eligibility at the effective date; retain generated/history rows and reconcile unused units explicitly. | D-003 |
| Hierarchy | Materialize entitlement for each exact eligible client; no implicit ancestor/descendant pooling or inheritance. | D-004 |

Invariant: `available = active base + approved adjustments + eligible carry-forward - consumed units`, calculated for one exact client, visit type, and contract service period. Reversals are compensating ledger entries. Generation keys and completion commands must be idempotent.

## 4. Decision register

All decisions below were approved on 2026-08-20 by the Project Owner through the explicit instruction to complete Wave 0. Domain-role owners remain accountable for operating the approved policy and proposing later versioned amendments.

| ID | Decision | Recommended default | Required owner | Status |
|---|---|---|---|---|
| D-001 | Consumption for completed/no-show/client-cancelled/support-cancelled visits | Policy table in section 3 | Contract Service + Commercial | APPROVED |
| D-002 | Reservation versus completion consumption | Completion alone consumes | Contract Service | APPROVED |
| D-003 | Carry-forward, overage, amendment, suspension, termination | Section 3 defaults | Contract Service + Commercial | APPROVED |
| D-004 | Hierarchy visit inheritance | Exact-client materialization; no pooling | Contract Service | APPROVED |
| D-005 | SLA specificity and client-specific targets | Default priority, then service, product, module overrides; reject equal precedence | Support Operations | APPROVED |
| D-006 | KPI/RAG/worklog/feedback/score visibility | Dictionary and target rules above; individual composite scoring deferred under an approved control | Support Operations + HR | APPROVED |
| D-007 | Planner conflicts and override authority | Safety/overlap blocks; workload warns; managers override warnings with reason | Support Operations + HR | APPROVED |
| D-008 | Notification ANY/ALL and eligible creation sources | `ANY`; creation only initially; explicit source allowlist | System Administration | APPROVED |
| D-009 | Organization ownership, reporting, effective dating, visibility | HR owns structure; one effective primary manager; controlled secondary assignments | HR + Top Management | APPROVED |
| D-010 | Tickets Worked On events/attribution/cards | Distinct ticket; approved worklog/assignment/action events; no raw-count ranking | Support Operations + HR | APPROVED |
| D-011 | Inactive/ineligible approval versus override | Approval by default; emergency override privileged, reasoned, audited, no self-approval | Support Operations | APPROVED |
| D-012 | Ticket fees, tax, payment gates, currencies, refunds, accounting | Finance-managed configuration; no currency conversion without an approved rate source | Finance | APPROVED |
| D-013 | Renewal identity and legacy backfill | Successor immutable contract/version; migrated dates labeled inferred | Commercial | APPROVED |
| D-014 | Financial roles, thresholds, allocations, portal visibility | Separate least-privilege roles; explicit allocation; sensitive portal data off by default | Finance + Commercial | APPROVED |

## 5. Wave 0 acceptance status

| Deliverable | Status | Evidence |
|---|---|---|
| Architecture inventory and data ownership | `DONE` | Sections 1 and 5 of this document |
| KPI dictionary and canonical-source rules | `DONE` | Section 2; formulas, owners, targets, RAG, and insufficient-data rules approved |
| Entitlement policy | `DONE` | Section 3; D-001 through D-004 approved |
| Business decision register | `DONE` | Section 4; D-001 through D-014 approved by Project Owner directive |
| Approved rules with no ownership ambiguity | `DONE` | Exact data ownership and accountable operating roles recorded |

No database migration or runtime code change was made in Wave 0.
