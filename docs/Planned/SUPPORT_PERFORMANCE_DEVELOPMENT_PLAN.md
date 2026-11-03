# Support Performance & Improvement Development Plan

Last updated: 2026-08-10  
Plan owner: Support Department / Support Hub product owner  
Current application baseline: Support Hub 1.4.0

## Status legend

| Status | Meaning |
|---|---|
| `DONE` | Implemented and verified |
| `PARTIAL` | Useful data or UI exists, but the business outcome is incomplete |
| `READY` | Defined and ready for implementation |
| `BLOCKED` | Requires a business decision or prerequisite |
| `PLANNED` | Accepted future work, not yet ready to start |

Only mark an item `DONE` after its acceptance criteria and quality gates pass.

## Program objectives

1. Prove what the department delivers to every client using auditable numbers.
2. Identify missing services, weak processes, overload, recurring incidents, and renewal risks.
3. Measure engineers fairly using quality, SLA, effort, complexity, and client outcomes.
4. Show whether performance is improving or deteriorating over time.
5. Produce client renewal packs and department management reports from the same trusted data.

## Measurement principles

- Never label elapsed ticket age as engineer work effort.
- Never rank engineers using ticket count alone.
- Every KPI must have an owner, formula, source, target, period, and drill-down evidence.
- Show `Insufficient data` instead of inventing a score.
- Preserve monthly snapshots so historical reports do not change when master data changes.
- Separate client-caused, vendor-caused, and support-caused waiting or SLA impact.

## Baseline inventory

| Capability | Status | Current position |
|---|---|---|
| Clients, contracts, coverage and SLA targets | `DONE` | Structured records exist |
| Contract-scoped portal catalog | `DONE` | Portal shows eligible contract products/modules/services |
| Portal contract and SLA dashboard | `DONE` | Contract, coverage, requests, SLA and lifecycle metrics |
| Ticket status, priority, escalation and SLA clocks | `DONE` | Suitable for operational reporting |
| Department and engineer operational dashboards | `PARTIAL` | Several KPIs exist; no unified management scorecard |
| Engineer labor/worklog capture | `BLOCKED` | No trustworthy source for hours spent |
| Client satisfaction feedback | `BLOCKED` | No rating workflow or stored responses |
| Root-cause and resolution classification | `PARTIAL` | Free-text summaries exist; structured analytics do not |
| Monthly immutable reporting snapshots | `PLANNED` | Reports currently use live data |
| Renewal health/risk scoring | `PLANNED` | Contract dates exist; scoring model does not |

## Delivery roadmap

### P0 — Governance and KPI definitions

Status: `READY`  
Priority: Critical  
Target duration: 3–5 working days

Deliverables:

- Approve KPI dictionary and management targets.
- Define support hours, business hours, after-hours, response, resolution, reopen and escalation formulas.
- Define ticket complexity weights: Simple `1`, Standard `2`, Complex `3`, Critical `5`.
- Define RAG thresholds per KPI and whether higher or lower is better.
- Assign a business owner to every KPI.
- Define reporting periods: monthly, quarterly, annual and contract-to-date.

Acceptance criteria:

- Every KPI in later phases has an approved formula and data source.
- No two reports calculate the same KPI differently.
- Management signs off on engineer-scoring weights before individual scores are displayed.

### P1 — Engineer worklogs

Status: `READY`  
Priority: Critical  
Depends on: P0  
Target duration: 1–2 weeks

Data to capture:

- Ticket, engineer, activity date and minutes.
- Activity type: investigation, remote support, communication, configuration, testing, documentation, onsite, training or monitoring.
- Normal-hours/after-hours and billable/non-billable flags.
- Notes, creator, timestamps and audit history.

Product work:

- Add/start/stop timer and manual worklog entry in ticket workspace.
- Add correction permission and mandatory correction reason.
- Prevent negative, overlapping or implausibly long entries.
- Show ticket effort total and engineer contribution breakdown.

Acceptance criteria:

- “Hours spent supporting the client” comes only from approved worklogs.
- Worklog changes are audited.
- Client and department totals reconcile with ticket-level drill-downs.

### P2 — Client feedback and service quality

Status: `READY`  
Priority: Critical  
Depends on: P0  
Target duration: 1–2 weeks

Data to capture after resolution/closure:

- Overall rating from 1–5.
- Response quality and resolution quality ratings.
- Optional comment and “problem fully solved” response.
- Ticket, client contact, submission time and channel.
- One active response per ticket/contact, with audited amendments.

Product work:

- Portal feedback form and reminder.
- Feedback dashboard and low-score alert.
- Minimum response count before displaying an average.
- Feedback response rate shown beside the average score.

Acceptance criteria:

- Feedback is isolated by client.
- Low scores create an accountable follow-up action.
- Reports never show an average without its response count/rate.

### P3 — Structured cause, outcome and pending data

Status: `READY`  
Priority: High  
Depends on: P0  
Target duration: 1–2 weeks

Add controlled classifications:

- Pending reason: client, vendor, engineering, access, approval, parts, scheduled work or other.
- Resolution type: permanent fix, workaround, configuration, training, defect, infrastructure, duplicate or no fault found.
- Root-cause category and responsible domain.
- Recurrence indicator and linked known problem.
- Complexity and effort estimate.

Acceptance criteria:

- At least 95% of newly closed tickets contain required structured outcomes.
- Pending age can be split by responsible party.
- Recurring issues can be grouped without parsing free text.

### P4 — Client summary report

Status: `PARTIAL`  
Priority: High  
Depends on: P1–P3 for complete results  
Target duration: 1–2 weeks after prerequisites

Report sections:

- Contract, expiry, request allowance and covered services.
- Requests by type, status, priority, product, module, service and branch.
- Opening/closing backlog and pending aging.
- First-response and resolution SLA performance.
- Worklog hours, after-hours effort and activity mix.
- Escalations, reopens, recurring causes and permanent fixes.
- Feedback score, response rate and comments theme.
- Month-over-month and contract-to-date trends.
- Renewal recommendations and unresolved risks.

Outputs:

- Internal interactive report with drill-down.
- Client-safe portal view.
- Excel and print-ready PDF renewal pack.

Acceptance criteria:

- All headline numbers drill down to the underlying tickets/worklogs.
- Exported totals equal screen totals.
- Report supports month, quarter, year and contract-period filters.

### P5 — Department management scorecard

Status: `PARTIAL`  
Priority: High  
Depends on: P1 and P3  
Target duration: 2 weeks

Required KPIs:

- Incoming, resolved and closed tickets.
- Opening backlog, ending backlog and backlog change.
- SLA compliance and breach causes.
- Average and median response/resolution times.
- Aging buckets: 0–1, 2–3, 4–7, 8–14, 15–30 and 30+ days.
- P1/P2 volumes, escalations and reopens.
- Work hours, capacity, utilization and after-hours load.
- Top clients, products, modules, services and root causes.
- Feedback and renewal-risk distribution.

Acceptance criteria:

- Every KPI displays target, current, previous, variance, trend and RAG status.
- Managers can drill from a red KPI to its responsible records.
- Backlog flow reconciles: opening + incoming − closed/cancelled = ending.

### P6 — Balanced engineer scorecards

Status: `PLANNED`  
Priority: High  
Depends on: P0–P3  
Target duration: 2 weeks

Proposed score weights (requires P0 approval):

| Dimension | Weight |
|---|---:|
| SLA performance | 25% |
| Resolution quality/reopen prevention | 20% |
| Complexity-weighted productivity | 20% |
| Client feedback | 15% |
| Workload and after-hours contribution | 10% |
| Knowledge and permanent prevention | 10% |

Required fairness controls:

- Normalize for working days, shifts, leave, ticket complexity and priority.
- Separate individual contribution from team-owned outcomes.
- Require a minimum evidence volume before scoring.
- Display evidence and allow a documented manager review.

Acceptance criteria:

- Scores reproduce from stored evidence.
- No score is based only on raw ticket count.
- An engineer can see the evidence behind every component.

### P7 — Direction-of-travel and RAG engine

Status: `PLANNED`  
Priority: High  
Depends on: P0, P4–P6  
Target duration: 1–2 weeks

For each KPI store:

- Target, warning threshold, critical threshold and direction.
- Current value, previous comparable value and variance.
- Green/amber/red/grey result.
- Improving/stable/worsening trend.
- Rule-generated explanation and recommended action.

Example conclusion:

> SLA compliance improved from 89.4% to 93.2%, but remains below the 95% target. Reopen rate worsened from 4.8% to 7.1%; resolution-quality review is required.

Acceptance criteria:

- Conclusions come from versioned deterministic rules.
- Every conclusion links to its KPI evidence.
- Grey is used when the sample is insufficient.

### P8 — Renewal intelligence

Status: `PLANNED`  
Priority: Medium–High  
Depends on: P2, P4 and P7  
Target duration: 2 weeks

Renewal health inputs:

- Days to expiry and notice date.
- Allowance and work-hour consumption.
- SLA compliance and unresolved breaches.
- Open critical/pending-aged requests.
- Incident growth and recurring problems.
- Feedback, engagement and service adoption.

Outputs:

- Healthy renewal, opportunity, attention required, high risk or insufficient data.
- Renewal pipeline with owner and next action.
- Automatically prepared renewal meeting pack.
- Quantified value statement and recommended scope changes.

Acceptance criteria:

- Risk score formula is visible and versioned.
- Users can override a recommendation only with a reason.
- Upcoming renewals have an owner and dated next action.

### P9 — Historical snapshots and scheduled reporting

Status: `PLANNED`  
Priority: Medium  
Depends on: P4–P8  
Target duration: 1–2 weeks

Deliverables:

- Immutable month-end KPI snapshots.
- Scheduled client and department reports.
- Controlled email delivery and delivery audit.
- Comparison against the same prior period.
- Rebuild tool for authorized corrections with a reason.

Acceptance criteria:

- A closed period does not silently change.
- Snapshot totals reconcile with the source evidence captured at close.
- Failed deliveries are visible and retryable.

### P10 — Forecasting and continuous improvement

Status: `PLANNED`  
Priority: Medium  
Depends on: at least 6 months of reliable P1–P9 data

Capabilities:

- Ticket-volume and staffing forecast.
- Client/product incident trend alerts.
- Capacity and shift-gap forecast.
- Recurrence and problem-management candidates.
- What-if renewal and staffing scenarios.

Acceptance criteria:

- Forecast accuracy is measured against actual outcomes.
- Predictions show confidence and input period.
- Forecasts assist decisions; they do not replace accountable approval.

## Recommended execution sequence

| Wave | Scope | Exit outcome | Status |
|---|---|---|---|
| Wave 0 | P0 | Approved KPI dictionary and targets | `READY` |
| Wave 1 | P1–P3 | Trustworthy effort, feedback and quality data | `READY` |
| Wave 2 | P4–P5 | Client and department reports | `PLANNED` |
| Wave 3 | P6–P7 | Fair engineer scorecards and direction-of-travel | `PLANNED` |
| Wave 4 | P8–P9 | Renewal management and historical automation | `PLANNED` |
| Wave 5 | P10 | Forecasting based on mature evidence | `PLANNED` |

## Standard quality gates for every phase

- Database migration reviewed and rehearsed on SQL Server when schema changes.
- Authorization and cross-client isolation tests.
- Audit tests for material changes.
- Backend Ruff, Mypy and Pytest.
- Frontend ESLint, Vitest, TypeScript and production build.
- Calculation reconciliation tests using fixed fixtures.
- Empty, insufficient-data, error and loading states.
- Release notes, rollback steps and post-deployment smoke test.

## Immediate decisions required

| Decision | Owner | Status |
|---|---|---|
| Approve KPI formulas and RAG thresholds | Support management | `BLOCKED` |
| Approve engineer score weights and fairness rules | Support + HR | `BLOCKED` |
| Decide whether worklogs are mandatory and minimum granularity | Support management | `BLOCKED` |
| Approve client feedback questions and notification channel | Support + Account Management | `BLOCKED` |
| Define who can view individual engineer scores | Support + HR + Security | `BLOCKED` |

## First development milestone

Start with P0, P1 and P2. The first milestone is complete when the system can prove, for one client and one month:

1. How many requests were received and completed.
2. Which products and services required support.
3. Whether SLA was met.
4. How many verified engineer hours were delivered.
5. What the client rated the completed service.
6. Which weaknesses require an accountable action.

