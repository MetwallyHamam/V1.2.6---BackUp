# Dashboard Profiles and Department Analytics Enhancement

## Status

**PAUSED — safe continuation point recorded on 2026-08-31. Foundation and administration work are implemented; domain dashboards, remaining scope contracts, drilldowns, and production UAT remain.**

Reviewed against the current source and attached SQL Server database on 2026-08-31. Existing performance work remains tracked in `Dashboard Scalability and Progress.md` and is a prerequisite for expensive historical widgets.

## Requested outcome

Provide governed dashboards for Top Management, Project Delivery, Human Resources, Finance, Implementation, and future departments, including:

* profile-default dashboards and administrator-controlled widget layouts;
* department-aware data scope and optional profile/department variants;
* optional personal layout customization that cannot expand access;
* cards and charts whose drilldowns exactly match their metrics;
* scalable aggregation for long ranges and future million-ticket history.

## Current-system audit

| Point | Status | Evidence |
|---|---|---|
| Profile permissions | **Completed foundation** | Profiles, permissions, and primary/additional user-profile assignments exist. |
| Departments/hierarchy | **Completed foundation** | Departments, memberships, hierarchy, reporting lines, and heads exist. |
| Client sharing | **Completed foundation** | Client/department sharing should remain authoritative for Implementation scope. |
| Dashboard/widget records | **Completed foundation** | Widget layout, width, order, refresh interval, configuration, and active state exist. |
| Dashboard fallback | **Completed** | Deterministic user, profile+department, primary-profile, department, system, and legacy fallback resolution exists. |
| Widget permission filtering | **Completed for registered widgets** | Registered financial widgets are filtered per request; future widgets must declare their required permissions in the governed registry. |
| Personal customization | **Completed foundation** | Authorized users can save a user dashboard override. |
| Dashboard scalability | **In progress elsewhere** | Core SQL pushdown exists; client-health/evidence materialization remains. |

Attached database inventory:

* The original database audit found 12 active profiles; migration `0152_financial_profile` now adds `FINANCIAL_MANAGEMENT`.
* Relevant departments include Implementation, Development, Human Resources, Support, Top Management, Call Center, and Project Manager.
* The original database contained four user-customized dashboards. Migration `0151_dashboard_assignments` preserves legacy records and enables governed profile, department, profile+department, user, and system assignments.

## Approved design direction

Use a hybrid model—not department-only or profile-only dashboards.

| Concern | Authoritative control |
|---|---|
| Page/widget access | Effective profile permissions |
| Default layout | Profile dashboard template |
| Visible business data | Department, sharing, user scope, and permission services |
| Department layout variation | Profile + department assignment |
| Personal arrangement | User override |
| Metric calculation | Governed backend widget-query registry |

Dashboard configuration controls presentation only. It must never grant permission or expand data access.

### Effective dashboard precedence

1. Active user customization.
2. Active profile + department assignment.
3. Active primary-profile assignment.
4. Active department default.
5. System default.

Additional profiles may contribute permissions, but the primary profile determines the default dashboard unless a separate audited policy is approved.

## Target architecture

Add reusable templates and separate assignments:

```text
dashboard_templates
  id, code, name, description, version, is_active, timestamps

dashboard_assignments
  id, dashboard_id
  profile_id nullable
  department_id nullable
  user_id nullable
  priority, effective_from, effective_until, is_active

dashboard_widgets
  dashboard_id, widget_code, title
  position, width, refresh_seconds, config_json, is_active
```

Reject ambiguous active assignments. Use optimistic concurrency, effective dates, audit evidence, and affected-user preview.

Every governed widget must declare a stable code, localization keys, required permissions, allowed scopes, supported filters, aggregation service, drilldown contract, evidence limit, and performance classification. Never accept arbitrary SQL, routes, or permission codes from browser configuration.

## Implementation plan and status

### Point 1 — Metric and scope contracts

**Status: In progress — business-owner approval required**

* [ ] Confirm project lifecycle codes and exact Delivered, Pending Delivery, and Overdue definitions.
* [ ] Define pending products and pending points using structured data, not free text.
* [ ] Approve HR engineer-performance formula, evidence, minimum sample, and privacy rules.
* [ ] Approve Finance terminology/formulas: invoiced, collected, outstanding, overdue, discount, and adjustment.
* [ ] Define department/descendant visibility for Implementation, HR, and management roles.
* [ ] Document formula version, date basis, filters, permission, evidence, and drilldown for every widget.

Implementation note: engineering will not invent lifecycle, HR privacy, or financial accounting policy. Proposed metric contracts must be reviewed with the Project Delivery, HR, and Finance owners before their widget query services are enabled.

#### Metric contract review draft

| Domain | Metric | Proposed governed definition | Current readiness |
|---|---|---|---|
| Project | Delivered Projects | `project_handovers.current_status IN ('DELIVERED','ACCEPTED')`; date basis must be an explicit delivery timestamp, not `updated_at`. | **Blocked:** no delivery timestamp exists. |
| Project | Awaiting Delivery | Status in `DRAFT`, `READY`, or `ON_HOLD`, shown separately by status rather than merged without explanation. | **Ready after owner approval.** |
| Project | Awaiting Acceptance | Status `DELIVERED` with at least one unaccepted required recipient. | **Ready after owner approval.** |
| Project | Overdue/At Risk | Planned delivery date before the reporting as-of date and status not `DELIVERED`/`ACCEPTED`; at-risk threshold must be configurable and separate. | **Blocked:** no planned delivery date exists. |
| Project | Pending Products | Count `project_handover_products.delivery_status IN ('PENDING','HOLD')`; evidence is the matching product rows. | **Ready after owner approval.** |
| Project | Pending Points | Count active structured project-point rows with owner, due date, state, and completion evidence. | **Blocked:** current `pending_points` is free text. |
| Finance | Invoiced | Sum issued invoice `total_amount` by `issued_date`, separated by currency; exclude cancelled documents and treat credit notes separately. | **Existing governed service available.** |
| Finance | Collected | Sum confirmed actual cash (`actual_payment` and verified allocated receipts) by collection/receipt date; discounts are not cash collection. | **Existing governed service available.** |
| Finance | Outstanding | `max(0, invoice amount + additional adjustments - actual cash - discounts - credits)` as of the report date, by currency. | **Existing governed service available.** |
| Finance | Overdue | Outstanding amount for invoices whose due date is before the report as-of date; cap at total outstanding and exclude cancelled documents. | **Existing governed service available.** |
| Finance | Discount/Adjustment | Report discount and additional amounts separately with their governed adjustment reason; never merge either into collected cash. | **Existing governed service available.** |
| HR | Engineer performance | Use finalized KPI-review results for the selected period; show aggregates only when the approved minimum sample is met. | **Blocked:** formula weights, minimum sample, and privacy audience require HR approval. |

All monetary widgets must group by currency and must not sum unlike currencies. All project/financial cards must preserve the exact as-of date, date basis, target scope, and evidence filters in their drilldowns.

Acceptance: every requested widget has one approved calculation and drilldown population before coding.

### Point 2 — Reusable templates and assignments

**Status: Completed**

* [x] Add template version metadata and effective-dated assignments.
* [x] Support user, profile, department, and profile+department targets in persistence/resolution.
* [x] Migrate existing user/profile/department/system dashboards without changing layouts.
* [x] Keep `profiles.dashboard_widgets_json` as a temporary fallback, then retire it later.
* [x] Add ambiguity, stale-version, active-period, and audit controls.

Acceptance: existing users retain their layouts and new users automatically receive the correct assignment.

### Point 3 — Effective dashboard resolver

**Status: Completed**

* [x] Implement the five-level precedence policy.
* [x] Resolve primary profile and current effective department at request time.
* [x] Filter resolved widgets through current effective permissions.
* [x] Return assignment source, template version, and resolution explanation.
* [x] Reevaluate permissions per request; no user scope is cached.
* [x] Test every precedence branch, inactive/future dates, multiple-profile primary selection, missing-template fallback, ambiguity, and per-request permission filtering.

Acceptance: resolution is deterministic, explainable, and cannot retain a widget after its permission is removed.

### Point 4 — Central authorization and data scope

**Status: In progress; reusable ticket scope, scoped metadata, filter rejection, and HR bypass removal implemented**

* [x] Create a reusable dashboard ticket scope derived from the authenticated user.
* [ ] Apply department, descendants, clients, sharing, team, engineer, geography, and user scope in SQL.
* [x] Use the central `visible_ticket_query` for dashboard ticket aggregation and metadata; drilldown consolidation remains.
* [x] Reject requested client, product, engineer, team, country, zone, and location filters outside the effective ticket scope.
* [x] Add a negative HR cross-profile fixture proving metadata, aggregation, and manipulated client filters cannot bypass central ticket scope.
* [x] Add a routed-department/sharing fixture proving own-department routed work is visible while shared-client, engineer, team, and geography manipulation cannot expand access.
* [ ] Add descendant-scope fixtures after the department visibility contract is approved.

Acceptance: metric and drilldown totals match, and parameter manipulation cannot reveal additional data.

### Point 5 — Dashboard Administration workspace

**Status: Completed foundation — administration workspace and governed previews available**

* [x] Add a permission-protected administration page.
* [x] Create, clone, edit, version, activate, and deactivate templates.
* [x] Assign templates to profiles, departments, combinations, system default, and exceptional users.
* [x] Add searchable catalog selection, reorder/resize controls, safe refresh intervals, and reject arbitrary configuration until a widget declares a typed schema.
* [x] Preview a user's effective profile/department resolution without impersonation.
* [x] Add direct profile/department scenario preview and set-based affected-user counts.
* [x] Show effective permissions, resolution source, conflicts, effective dates, and affected-user counts.
* [x] Reset a user override to its assigned template.
* [x] Localize the initial workspace in English/Arabic with responsive layouts.

Acceptance: administrators can safely configure and preview the exact authorized dashboard users will receive.

### Point 6 — Top Management project widgets

**Status: Pending — blocked by Point 1 project metric approval and missing structured dates/points**

* [ ] Delivered Projects.
* [ ] Projects Awaiting Delivery.
* [ ] Overdue/At-Risk Projects.
* [ ] Pending Project Points.
* [ ] Projects by Client and delivery trend.
* [ ] Open Delivered Projects using exact status/date filters.
* [ ] Link evidence to project details and client profile.

Acceptance: every card/chart segment matches its governed project-list drilldown count.

### Point 7 — Project Delivery dashboard

**Status: Initial governed dashboard implemented on 2026-09-01; planned-delivery and structured-point enhancements remain blocked by Point 1 data contracts.**

Implemented dashboard widgets: total projects, delivered, in progress, awaiting acceptance, pending products, projects by status, and projects by client. The dashboard uses the same manage-or-participant visibility rule as the Project Handovers workspace. Pending points explicitly reports unavailable rather than deriving a metric from free text.

* [ ] Extend the existing profile rather than creating a duplicate.
* [ ] Add total, delivered, in-progress, awaiting-acceptance, and overdue cards.
* [ ] Add pending products and pending points per project, including owner/due evidence.
* [ ] Add delivery progress, projects by client, and recently delivered widgets.
* [ ] Add structured project-product/project-point persistence if Point 1 confirms it is needed.
* [ ] Add exact project/client filters and permission tests.

Acceptance: Project Delivery staff manage their workload without unrelated CRM, finance, or support access.

### Point 8 — Human Resources dashboard

**Status: Initial governed dashboard implemented on 2026-09-01; approved performance scoring and descendant-scope policy remain blocked by Point 1.**

Implemented dashboard widgets: total/active/inactive employees, active departments, department-head vacancies, reporting-line exceptions, pending/finalized KPI reviews, onboarding in progress, and unscheduled shift participants. Widgets require the existing organization-wide KPI permission and do not publish an invented performance score.

* [ ] Department headcount and active/inactive analysis.
* [ ] Department hierarchy, head vacancies, and reporting-line exceptions.
* [ ] Approved engineer-performance and KPI completion/approval widgets.
* [ ] Shift calendar, current/upcoming coverage, unscheduled employees, and participation.
* [ ] Authorized onboarding-progress indicators.
* [ ] Organization-wide or descendant scope based on explicit HR permissions.
* [ ] Sensitive evidence protection and unsafe-small-sample suppression.

Acceptance: HR metrics obey privacy/scope rules and link to matching governed pages.

### Point 9 — Financial profile and dashboard

**Status: Completed technically; finance terminology remains subject to business-owner sign-off**

* [x] Create `FINANCIAL_MANAGEMENT` through migration/seed.
* [x] Grant minimum financial read permissions; do not clone Administrator/Support Manager wholesale.
* [x] Add governed invoiced, collected, outstanding, overdue, collection-rate, aging, client-contribution, invoice-status, and year-over-year trend analytics, separated by currency.
* [x] Add dedicated contract-value, contract-expiry, discount, and adjustment widgets.
* [x] Support client, contract, owner-department, date, and currency analysis.
* [x] Reuse the existing `/manager-finance/dashboard` service and approved accounting terminology.
* [x] Hide/reject financial widgets when permissions are absent.
* [x] Add direct-API denial and catalog-filtering tests for an unauthorized control user.

Acceptance: Finance receives only approved analytics and drilldowns without operational administration access.

### Point 10 — Implementation department dashboard

**Status: Pending; client sharing is the completed foundation**

* [ ] Resolve clients shared with Implementation from authoritative sharing tables.
* [ ] Add shared clients, open tickets, tickets by client/status, projects, pending actions, delivery dates, and overdue actions.
* [ ] Include related tickets only when existing visibility rules allow them.
* [ ] Reuse identical client/ticket/project scope in drilldowns.
* [ ] Add an Implementation profile+department variant.
* [ ] Test sharing add/remove, transfers, hierarchy, and unshared-client attempts.

Acceptance: Implementation sees shared clients and authorized work; unrelated data stays inaccessible through APIs, cards, exports, and drilldowns.

### Point 11 — User personalization

**Status: Completed**

* [x] User dashboard records and layout saving exist.
* [x] Restrict personalization to catalog widgets and presentation properties.
* [x] Prevent personal configuration from changing permissions or scope.
* [x] Show whether the dashboard source is user, profile+department, profile, department, or system.
* [x] Add Reset to Assigned Dashboard.
* [x] Define template-update behavior when a personal override exists: retain the pinned personal layout and notify the user when its assigned base template has a newer version.

Acceptance: users personalize presentation safely and can restore the assigned template.

### Point 12 — Scalable widget query services

**Status: In progress in `Dashboard Scalability and Progress.md`**

* [x] Substantial Executive/Top Management SQL pushdown exists.
* [x] SLA batching/snapshots, evidence caps, and large-range benchmarks exist.
* [ ] Complete client-health/evidence SQL or pre-aggregation paths.
* [ ] Implement each new widget as a narrow aggregate query, never an ORM full-history scan.
* [x] Set automated query-count, time, returned-row, response-size, and peak-memory regression budgets for the current summary and assignment-impact endpoints; production-scale SQL Server acceptance remains Point 14.
* [ ] Add daily facts only where indexed grouped SQL misses the target.
* [ ] Use asynchronous jobs for export-grade analysis that cannot remain interactive.

Acceptance: production-scale ranges meet the interactive target and million-row behavior is measured.

### Point 13 — Drilldown consistency and evidence

**Status: Completed for existing ticket widgets; future domain widgets must adopt the same contract**

* [x] Define typed ticket drilldown parameters for the existing dashboard ticket widgets.
* [x] Preserve date basis/range and all active ticket scope filters for existing cards and status/priority charts.
* [x] Compare every existing ticket widget population with destination API totals in automated fixtures, including routed-team/date, total-open, assigned-to-me, unassigned, critical, created/closed today, routing states, shift-handover, status/priority segments, breached, and due-soon.
* [ ] Limit inline evidence and provide full governed routes/exports.
* [ ] Add client-profile links to appropriate project evidence.
* [x] Provide explicit empty, unavailable, and denied states for the existing ticket dashboard; domain-specific insufficient-data states remain with future governed widgets.

Acceptance: no card redirects to a different population and evidence never bypasses route authorization.

### Point 14 — Validation, UAT, and release

**Status: In progress — automated foundation gates pass; production/UAT gates remain**

* [x] Test assignment CRUD, all precedence levels, effective dates, ambiguity, optimistic concurrency, and auditing.
* [ ] Test positive and negative access for every specialist profile.
* [ ] Test profile+department scope and all drilldown invariants.
* [ ] Test English/Arabic, RTL, responsive, loading, retry, empty, and failure states.
* [ ] Prove existing formulas remain unchanged on comparison fixtures.
* [x] Run real SQL Server 30K and generated/restored million-row validation: rollback-only 30K full endpoints pass, and 1,000,000 tickets plus 2,000,000 dense scalar SLA facts aggregate in 0.434 seconds with 0.028 MB Python peak.
* [x] Rehearse clean SQLite migration through `0152_financial_profile`; populated SQL Server, backup, and rollback rehearsal remain.
* [ ] Perform UAT with Top Management, Project Delivery, HR, Finance, Implementation, and an unauthorized control user.
* [x] Pass the current full backend suite, Ruff checks for changed backend files, TypeScript compilation, and frontend production build.
* [ ] Build and smoke-test a new immutable release after remaining scope/UAT gates pass.

Acceptance: automation, migration rehearsals, performance budgets, scope/drilldown comparisons, and role UAT all pass before packaging.

## Pause and continuation handoff — 2026-08-31

### Delivered and verified

| Area | Current status |
|---|---|
| Template and assignment persistence | **Completed** — migrations `0151_dashboard_assignments` and `0152_financial_profile` reach migration head on a clean database. |
| Effective resolver | **Completed** — user, profile+department, profile, department, and system precedence is deterministic and tested. |
| Administration workspace | **Mostly completed** — create, clone, edit, activate/deactivate, assign, search, reorder, resize, refresh control, effective-user preview, permission explanation, and EN/AR UI are available. |
| Personal dashboards | **Mostly completed** — safe presentation customization and Reset to Assigned Dashboard are available. |
| Central ticket scope | **Partially completed** — aggregation and metadata use `visible_ticket_query`; out-of-scope filters are rejected and the unsafe HR all-ticket bypass is removed. |
| Financial dashboard | **Completed technically** — least-privilege profile, default assignment, governed analytics, contract/value/expiry/discount/adjustment widgets, direct contract filtering, and negative authorization tests are implemented. |
| Automated verification | **Passed** — full backend suite, focused dashboard tests, Ruff, TypeScript, Vite production build, compatibility tests, and clean migration rehearsal. |

### Remaining work

| Priority | Point | Remaining work | Dependency/blocker |
|---:|---|---|---|
| 1 | Point 1 | Approve project lifecycle/date formulas, HR KPI privacy/formula, finance adjustment terminology, and department/descendant visibility. | Business-owner decisions. |
| 2 | Point 4 | Consolidate drilldown scope and add descendant fixtures. Geography, team, and engineer negative fixtures are complete. | Department visibility contract from Point 1 for descendants. |
| 3 | Point 5 | Completed: direct profile/department scenario preview and set-based affected-user counts. | Validate production-scale count latency during Point 14. |
| 4 | Points 6–7 | Implement Top Management project and Project Delivery widgets, structured delivery dates, pending points, filters, and matching evidence routes. | Project metric approval and missing structured fields. |
| 5 | Point 8 | Implement HR organization, KPI, shift, onboarding, privacy, and minimum-sample widgets. | HR formula, audience, and privacy approval. |
| 6 | Point 9 | Technical implementation completed; obtain business-owner terminology sign-off. | Finance owner approval. |
| 7 | Point 10 | Implement the Implementation shared-client dashboard and profile+department assignment with sharing-removal tests. | Department/sharing scope contract. |
| 8 | Point 11 | Completed: personal overrides remain pinned and display an assigned-template update notification. | None. |
| 9 | Points 12–13 | Finish scale budgets, client-health/evidence aggregation, typed drilldowns, exact metric/destination comparison tests, and explicit empty/denied states. | Domain widgets and approved contracts. |
| 10 | Point 14 | Run populated SQL Server migration/rollback, 30K and million-row tests, EN/AR/RTL UAT, specialist-profile authorization UAT, then build an immutable release. | All preceding acceptance gates. |

### Exact next implementation step

Resume with **Point 12**: capture SQL Server logical reads through a driver/session that exposes `STATISTICS IO`, then finish the unusually wide covering-index review; do not replace it from estimated plans alone. Estimated plans already select the ticket creation/status and SLA outcome indexes for the governed aggregates. Both historical endpoints pass the rollback-only 30K/29,657-clock dense fixture, and the expanded generated benchmark aggregates 1,000,000 tickets plus 2,000,000 dense SLA facts in 0.434 seconds with 0.028 MB Python peak. Descendant fixtures remain blocked by the unapproved visibility policy.

### Files to open first when resuming

* `backend/app/modules/dashboards/routes.py`
* `backend/app/modules/dashboards/schemas.py`
* `backend/app/modules/dashboards/models.py`
* `backend/app/modules/tickets/service.py`
* `backend/app/tests/test_dashboards.py`
* `frontend/src/pages/DashboardAdminPage.tsx`
* `backend/alembic/versions/0151_dashboard_assignments.py`
* `backend/alembic/versions/0155_financial_dashboard_widgets.py`

No release artifact was built during this dashboard-enhancement continuation. The source currently passes automated build gates, but Point 14 production-scale, rollback, and UAT gates remain open.

## Recommended delivery order

1. Point 1 — metric/scope approval.
2. Points 2–4 — templates, assignments, resolution, and authorization.
3. Point 5 — administration and preview.
4. Points 6–7 — Project Delivery and Top Management project analytics.
5. Point 8 — HR analytics.
6. Point 9 — Financial profile/dashboard.
7. Point 10 — Implementation shared-client dashboard.
8. Points 11–13 — personalization, scale, and drilldown consistency.
9. Point 14 — UAT and release.

Do not build all widget families before Points 2–4. One resolver and one authorization/scope contract must be established first to prevent inconsistent dashboard systems per department.

## Completion summary

| Category | Status |
|---|---|
| Permissions, profiles, departments, sharing, and user-dashboard foundation | **Completed foundation** |
| Existing dashboard scalability work | **In progress separately** |
| Metric/scope approval | **In progress — owner approval required** |
| Template/assignment architecture | **Completed** |
| Profile+department resolver and scope | **Resolver completed; central data scope in progress** |
| Dashboard Administration | **In progress — editor and effective-user preview delivered** |
| Top Management project widgets | **Pending** |
| Project Delivery dashboard | **Pending** |
| HR dashboard | **Pending** |
| Financial profile/dashboard | **Completed technically; terminology sign-off pending** |
| Implementation dashboard | **Pending** |
| Drilldown, performance, UAT, and release acceptance | **Pending** |

## Latest verification evidence — 2026-08-31

* Full backend `pytest -q`: **passed (100%)**.
* Dashboard-focused backend tests: **15 passed** after resource-budget enforcement, drilldown invariants, and Cairo-local date-boundary alignment.
* Release revision and database compatibility tests: **8 passed**.
* Changed backend Ruff checks: **passed**.
* Populated SQL Server migration: **passed at `0155_financial_widgets (head)`** after correcting the dashboard self-reference to a non-cascading foreign key.
* TypeScript project compilation: **passed**.
* Vite production build: **passed** (existing large-chunk advisory only).
