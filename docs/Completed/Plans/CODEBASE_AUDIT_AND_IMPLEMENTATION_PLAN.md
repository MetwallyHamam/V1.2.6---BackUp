# SupportHub Audit and Implementation Plan

Last updated: 2026-08-14

## Control status

| Field | Value |
|---|---|
| Current pass | PASS 2 — approved remediation and implementation |
| Overall status | IN_PROGRESS |
| Application code changes authorized | Yes — user approved 2026-08-14 |
| Current stop point | Dashboard gaps completed; geography and shift handover implementation next |
| Resume instruction | Continue from `GEO-01`, then `SHIFT-HO-01`; verify each group before UAT |
| UAT target | LocalUAT / `MillensysSupportHub_UAT` |
| Production target | Not authorized; do not publish |

Status values: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `AWAITING_APPROVAL`, `DONE`, `DEFERRED`.

## Detected stack and tests

- Backend: Python 3.12+, FastAPI, SQLAlchemy 2, Alembic, Pydantic, SQL Server through pyodbc/pymssql; pip/pyproject packaging.
- Frontend: TypeScript, React 19, Material UI, TanStack Query, Axios, Vite; npm/package-lock.
- Deployment: IIS/httpPlatform and a PyInstaller standalone backend.
- Tests exist: a substantial backend pytest suite and four frontend Vitest component tests.
- Coverage gap: there are no focused UI tests for the categorized main dashboard, management dashboard visual selection, map, or drill-through behavior.

## PASS 1 findings

### Security

| ID | Priority | Status | Finding and location | Why it matters | Suggested fix |
|---|---|---|---|---|---|
| SEC-01 | Critical | AWAITING_APPROVAL | Real DB, SMTP, signing, and webhook credentials are present in `backend/.env:4-16` and an archived deployment config at `web.config.outlook-1.13.0:19-43`. | Anyone with filesystem/backup access can authenticate to infrastructure; credentials have also appeared in chat and must be treated as exposed. Repository history could not be checked because this workspace is not a Git worktree. | Rotate every exposed credential first. Remove the archived secret-bearing config, keep only placeholders, tighten ACLs, and use deployment environment/secret storage. Never print secrets in diagnostics. |
| SEC-02 | High | AWAITING_APPROVAL | Access and refresh JWTs are persisted in browser `localStorage` in `frontend/src/api/client.ts:8-38`. | Any successful XSS can extract long-lived tokens; refresh-token persistence increases impact. | Prefer Secure, HttpOnly, SameSite cookies for refresh tokens. As a smaller interim change, keep access tokens in memory and refresh tokens in sessionStorage, with a documented forced-login tradeoff. This changes login persistence and requires approval. |
| SEC-03 | Medium | AWAITING_APPROVAL | Dashboard map dependency added approximately 1.2 MB to the shared vendor chunk; build warns about a 1.6 MB vendor chunk. `frontend/src/pages/ManagementDashboardsPage.tsx:8,20`. | Larger initial JavaScript increases load/parse time for users who never open Top Management. | Lazy-load the map data/component only when the Geography tab is selected. No business behavior change. |
| SEC-04 | Pass | DONE | Top Management routes enforce authentication and `dashboard.executive` at `backend/app/modules/dashboards/management.py:47-65`; CORS is configured from explicit origins with credentials disabled at `backend/app/main.py:88-99`. | Confirms these reviewed controls are not currently open. | Retain and add authorization regression tests for both endpoints. |

No `dangerouslySetInnerHTML`, `eval`, shell execution from request data, or obvious raw-SQL interpolation was found in the reviewed application paths. This is a static review, not a penetration test.

### Dependencies

| ID | Priority | Status | Finding | Suggested action |
|---|---|---|---|---|
| DEP-01 | High | DONE | `npm audit` reported 2 high transitive advisories: `js-yaml <4.3.1` and `nanoid <3.3.18`; compatible fixes were applied and the rescan reports zero vulnerabilities. | Frontend tests and production build passed after the lockfile update. |
| DEP-02 | High | AWAITING_APPROVAL | `pip-audit` reports 9 advisory entries for `cryptography 45.0.7`; fixes require versions outside the current `<46` application constraint (up to 50.0.0). | Treat as a separately approved major/security compatibility task; test JWT, TLS, attachments, email, and standalone packaging. Do not force-update blindly. |
| DEP-03 | Medium | AWAITING_APPROVAL | Development tooling advisories: `pip 25.3` (fix 26.1.2+) and `pytest 8.4.2` (fix 9.0.3). | Update pip in the dev/build environment. List pytest 9 as a major upgrade and validate the suite before changing the project constraint. |
| DEP-04 | Low | AWAITING_APPROVAL | Safe update candidates include hookform resolvers 5.5.7→5.7.1, React types patch updates, react-hook-form 7.83.0→7.85.0, typescript-eslint 8.65.0→8.67.0, Alembic 1.18.5→1.19.1, SQLAlchemy 2.0.51→2.0.52, and Uvicorn 0.52.0→0.52.3. | Apply patch/minor updates as one group after security fixes, update locks, and run all checks. |
| DEP-05 | Deferred | DEFERRED | Major upgrades available: MUI 7→9, Vite 6→8, TypeScript 5→7, Vitest 3→4, Zod 3→4, ESLint 9→10, cryptography 45→50, pytest 8→9. | Separate migration projects; do not include in safe cleanup. |

`pip-audit` was installed only into the local development virtual environment to perform this scan; it was not added to application dependencies.

### Duplicated logic

| ID | Priority | Status | Finding and location | Why it matters | Suggested fix |
|---|---|---|---|---|---|
| DUP-01 | Medium | AWAITING_APPROVAL | Donut, line, and bar visualization logic is duplicated between `frontend/src/pages/DashboardPage.tsx:185-466` and `frontend/src/pages/ManagementDashboardsPage.tsx:15-21`. | Styling and accessibility fixes will drift across dashboards, which has already happened. | Extract only the mature chart primitives into shared components; keep dashboard-specific composition local. |
| DUP-02 | Low | AWAITING_APPROVAL | Repeated query-string drill-through construction exists across both dashboard pages. | Filter names can diverge and silently open incorrect data. | Add one small typed drill-through helper, without changing routes or filter semantics. |

### Obvious refactors

| ID | Priority | Status | Finding and location | Why it matters | Suggested fix |
|---|---|---|---|---|---|
| REF-01 | High | AWAITING_APPROVAL | `analytics()` is a very long multi-purpose function at `backend/app/modules/dashboards/management.py:63-112`. | It mixes authorization, filtering, querying, KPI calculations, and response construction; the earlier `None` aggregation bug came from this concentration. | Split only into small period/filter/aggregation helpers and add regression tests; keep formulas unchanged. |
| REF-02 | Medium | AWAITING_APPROVAL | `DashboardPage` is approximately 1,300 lines from `frontend/src/pages/DashboardPage.tsx:468`. | Category placement is difficult to review and widgets are easily omitted or duplicated. | Extract each approved tab body into a local component in the same feature folder; no state architecture rewrite. |
| REF-03 | Medium | AWAITING_APPROVAL | `ManagementDashboardsPage.tsx` remains compressed and difficult to review around lines 15-24. | High risk of visual and type mistakes during small changes. | Format it and extract the map into one local component file; no behavior change. |

### Reusable pieces

| ID | Priority | Status | Finding | Suggested fix |
|---|---|---|---|---|
| REUSE-01 | Medium | AWAITING_APPROVAL | Dashboard section tabs, visualization panel headers, empty states, and drill-through wrappers now repeat. | Share only chart shells and empty/error states; keep business widgets separate. |

### Quick health checks

| ID | Priority | Status | Finding and location | Why it matters | Suggested fix |
|---|---|---|---|---|---|
| PERF-01 | High | AWAITING_APPROVAL | Top Management loads every ticket, client, branch, product, user, and contract into Python at `backend/app/modules/dashboards/management.py:67-94`, then filters in memory. | Production load grows with total history and can recreate the earlier CPU/loading problem. | Push date/scope filters and simple aggregates into SQL; preserve output with comparison tests. |
| PERF-02 | High | AWAITING_APPROVAL | Contract renewal detection is O(n²) at `backend/app/modules/dashboards/management.py:88`. | Large contract histories will cause disproportionate dashboard latency. | Pre-index contracts by client or calculate renewals with a SQL existence query. |
| PERF-03 | Medium | AWAITING_APPROVAL | Dashboard analytics lacks dedicated regression/performance tests. | Recent bugs were found only in UAT. | Add API tests for empty/null resolution timestamps, all six management sections, filtering, permissions, and a bounded query-count/large-fixture test. |
| ERR-01 | Medium | AWAITING_APPROVAL | Several broad exception handlers exist in attachment/import/configuration paths, including `backend/app/modules/contracts/attachments.py:42`, `tickets/attachments.py:137,196`, and `knowledge_base/routes.py:289`. | Broad catches can hide programming errors and make production diagnosis difficult. | Review individually; narrow exceptions and keep safe cleanup behavior. Do not change user-facing behavior without tests. |

## Dashboard gaps and requested enhancements

| ID | Priority | Status | Task | Acceptance criteria |
|---|---|---|---|---|
| UI-01 | High | DONE | Put “Top repeated issues” back on the main dashboard Overview. | Visible on the first tab for authorized managers; each issue opens correctly filtered tickets; also remains available in SLA analysis if desired, without duplicate API calls. |
| UI-02 | High | DONE | Put “Top 3 agents · YYYY-MM” on the main dashboard Overview. | Visible on the first tab, permission-aware, responsive, and calculated from the selected KPI period. |
| UI-03 | Medium | AWAITING_APPROVAL | Add clear section subtitles/count badges and remember the selected main-dashboard tab for the session. | Navigation remains uncluttered and reload behavior is predictable. |
| UI-04 | High | AWAITING_APPROVAL | Add tests for UI-01/UI-02 and category switching. | Vitest proves Overview contains repeated issues/top agents and other heavy sections are hidden until selected. |
| UI-05 | Medium | AWAITING_APPROVAL | Improve country map loading through lazy data import. | Geography still renders real country boundaries and interactive activity, but the main app bundle is not inflated for unrelated pages. |

## Geography master data enhancement

Current gap: clients and branches store `country` and `zone` as free text in `backend/app/modules/clients/models.py:44-45,110-111`. The create-client UI also accepts free text at `frontend/src/pages/ClientsPage.tsx:211`. This permits spelling variants and prevents reliable country maps, geographic filters, and location analytics.

Recommended concept:

```text
Country master
└── Administrative zone / region master
    └── Client location master
        ├── Client
        └── Optional branch/site
```

Here, a location represents a physical client site such as Alfascan Mohandessin, Alfascan Maadi, or Gulf Medical Riyadh HQ. A branch may reference a location; multiple operational branches should not silently create duplicate geographic records.

| ID | Priority | Status | Task | Acceptance criteria |
|---|---|---|---|---|
| GEO-01 | High | AWAITING_APPROVAL | Add Countries master data. | CRUD/activate/deactivate with unique ISO alpha-2/alpha-3 code, display name, dialing code (optional), default timezone (optional), latitude/longitude centroid, and map identifier. Deletion is blocked while referenced. |
| GEO-02 | High | AWAITING_APPROVAL | Add Zones/regions master data scoped to a country. | Unique code/name per country, active flag, and optional centroid; no hardcoded Egypt/Cairo values. |
| GEO-03 | High | AWAITING_APPROVAL | Add Client Locations master data. | Location has client, country, zone/region, code, name, full address, timezone, latitude, longitude, active flag, and optional linked branch. Coordinates are validated to latitude −90..90 and longitude −180..180. |
| GEO-04 | High | AWAITING_APPROVAL | Link Client to Country and optional primary Location. | Client create/edit uses searchable master-data selectors; selected country must match the selected location. Existing `country`/`zone` text remains readable during migration. |
| GEO-05 | High | AWAITING_APPROVAL | Link Branch/site to a Location. | Branch create/edit selects or creates an authorized client location; location belongs to the same client; branch inherits timezone/geography unless explicitly overridden where allowed. |
| GEO-06 | High | AWAITING_APPROVAL | Backfill existing client/branch geography. | Migration creates normalized countries/zones/locations from distinct trimmed legacy values, reports ambiguous rows, preserves original text during a compatibility release, and is idempotent on SQL Server. |
| GEO-07 | Medium | AWAITING_APPROVAL | Master-data UI and permissions. | Countries, zones, and locations are available under CRM/Master Data with view/create/edit/deactivate permissions. Destructive delete is not offered for referenced rows. |
| GEO-08 | High | AWAITING_APPROVAL | Use master IDs in Top Management filters and map. | Filters submit stable IDs rather than names; country boundaries use ISO codes; exact location pins use stored coordinates; clicking a country/location opens correctly filtered data. |
| GEO-09 | High | AWAITING_APPROVAL | Add validation, migration, authorization, and analytics tests. | Tests cover duplicates, inactive selections, cross-client links, invalid coordinates, legacy backfill, permissions, and map/filter aggregation. |
| GEO-10 | High | AWAITING_APPROVAL | Add searchable geography selectors to Client create/edit. | Country is required and searchable; primary geographic location is searchable and filtered by country; users with permission can create a missing location without leaving the client workflow; inactive values cannot be newly selected but remain visible on existing clients. |
| GEO-11 | High | AWAITING_APPROVAL | Support multiple client-specific sites under the selected geography. | A client has one primary site and optional additional headquarters/branch/office/service-site records; another client's site can never be selected; site address, timezone, and optional coordinates are validated. |
| GEO-12 | High | AWAITING_APPROVAL | Add management geographic analytics and drill-through. | Dashboards calculate clients, tickets, SLA compliance, response/resolution time, critical incidents, delivered projects, contract renewals/expirations, product installations/quality, engineer workload, and field visits by country/zone/location. Every segment or map point opens filtered supporting data. |

Required management drill-down hierarchy:

```text
Country → Zone / Region → Geographic location → Client → Client site / branch → Tickets
```

Dashboard analytics acceptance criteria:

- Country, zone, location, client, and site filters use stable IDs/codes rather than free-text comparisons.
- Common aliases such as `KSA`, `Saudi`, and `Saudi Arabia` resolve to one controlled country record during backfill; ambiguous aliases are reported for review rather than guessed.
- Management widgets can group and compare client count, ticket demand, SLA compliance, response time, resolution time, critical incidents, delivered projects, contract health, products, engineer workload, and field visits geographically.
- A country chart slice or map shape drills into zones/locations; a location point drills into clients/sites; final drill-through opens filtered operational records.
- Exact client-site pins use stored latitude/longitude. Country-level centroids are used only when an exact site coordinate is unavailable and are visibly identified as aggregated results.
- Geographic records deactivated after historical activity remain available to historical reports.

Implementation constraints:

- Do not remove legacy `country`/`zone` columns in the first release. Dual-read normalized IDs first, retain text fallback, and remove legacy fields only in a later explicitly approved migration.
- Use stable foreign keys and ISO codes for analytics, never display-name comparisons.
- Client users may view their own locations but cannot administer global country/zone masters.
- Coordinates are optional for country/zone masters but required for an exact map pin; absence must not block ordinary ticket creation.
- Ticket history should continue using its captured branch/client context; normalization must not rewrite historical ticket ownership.

## PASS 2 proposed execution order

## Shift handover workflow

Current gap: ticket assignment history records who owns a ticket, and workforce shifts define scheduled attendance, but there is no durable handover record joining a ticket to a destination shift. A handover must not be represented by changing ticket status or silently reassigning it because that would conflict with SLA evidence, ownership, approval locks, escalation, and engineer performance reporting.

Recommended lifecycle:

```text
DRAFT → OFFERED → ACCEPTED → COMPLETED
                  ├── REJECTED
                  ├── CANCELLED
                  └── EXPIRED
```

Recommended ownership rule: creating a handover does **not** change the ticket assignee. The outgoing engineer remains accountable until an eligible incoming engineer accepts it. Acceptance can transfer assignment atomically if the site setting enables automatic transfer; otherwise it creates a visible acknowledged handover while a manager/dispatcher completes assignment through the normal assignment workflow.

| ID | Priority | Status | Task | Acceptance criteria |
|---|---|---|---|---|
| SHIFT-HO-01 | High | AWAITING_APPROVAL | Add a durable ticket shift-handover entity and history. | Stores ticket, source engineer/shift, destination shift/date/team and optional intended engineer, reason, structured work summary, pending actions, risk/priority note, offered/accepted/completed/cancelled/expired timestamps, actors, and immutable audit events. Multiple historical handovers are allowed, but only one active handover per ticket. |
| SHIFT-HO-02 | High | AWAITING_APPROVAL | Define eligible source tickets and creators. | Assigned engineer can hand over their own active ticket; managers/dispatchers can hand over visible tickets with a recorded reason; resolved/closed/cancelled/deleted tickets cannot be newly handed over; tickets awaiting entitlement approval cannot be transferred but may be added as `INFORMATION_ONLY` when policy permits. |
| SHIFT-HO-03 | High | AWAITING_APPROVAL | Limit destination scheduling to controlled shifts. | Destination must be an active configured shift occurring later today or tomorrow in the site/shift timezone. It cannot be a past/ended shift. Intended engineer must be an active member scheduled for that destination shift/team unless an authorized override is recorded. |
| SHIFT-HO-04 | High | AWAITING_APPROVAL | Add “Handover tickets” beside All Tickets and Approvals. | Tab shows active incoming handovers relevant to the current user's shift/team, plus outgoing handovers they created. It displays destination shift/date, source engineer, acceptance state, priority, SLA risk, pending actions, and ownership. Counts reflect active actionable records only. |
| SHIFT-HO-05 | High | AWAITING_APPROVAL | Add mark-for-handover actions from ticket detail and Tickets grid. | Single and approved bulk actions require destination shift, reason, work completed, pending actions, and optional intended engineer. Pending-approval tickets, terminal tickets, and conflicting active handovers are disabled with explicit explanations. |
| SHIFT-HO-06 | High | AWAITING_APPROVAL | Implement incoming acceptance/rejection. | Eligible incoming engineer can accept or reject with comment. Acceptance is concurrency-safe and idempotent. Rejection returns it to the source/manager queue and notifies them; it never leaves the ticket unowned. Manager can re-route before shift end. |
| SHIFT-HO-07 | High | AWAITING_APPROVAL | Control assignment behavior through a site setting. | Modes: `ACKNOWLEDGEMENT_ONLY` or `TRANSFER_ON_ACCEPTANCE`. Transfer mode calls the existing assignment service, eligibility validation, assignment history, first-dedicated SLA rules, notification, and audit logic in one transaction; no duplicate assignment implementation. Default is acknowledgement-only until UAT approval. |
| SHIFT-HO-08 | Critical | AWAITING_APPROVAL | Preserve SLA and workflow semantics. | Creating/offering a handover never pauses or resets SLA, never changes status, and never changes first-response evidence. Acceptance does not reset SLA clocks. Existing customer-waiting rules remain authoritative. Handover cannot bypass entitlement approval, escalation level restrictions, resolve permissions, or assignment eligibility. |
| SHIFT-HO-09 | High | AWAITING_APPROVAL | Add expiry and overdue controls. | Unaccepted handover becomes overdue when destination shift starts and expires at a configurable point after shift start/end. Expiry retains current assignment, alerts source/manager/on-call users, and returns the item to an exception queue. No automatic silent assignment. |
| SHIFT-HO-10 | High | AWAITING_APPROVAL | Add notifications and reminders. | In-system notifications are sent on offer, acceptance, rejection, cancellation, overdue, and expiry. Email uses the unified email queue and deduplication/cooldown rules. Role/profile notification preferences control recipients; P1/P2 may use shorter reminder intervals. |
| SHIFT-HO-11 | High | AWAITING_APPROVAL | Add permissions and site settings. | Feature flag; view incoming/team/all; create own/any; accept; reject; cancel own/any; reroute; override eligibility; bulk create; and reporting permissions. Settings cover enablement, today/tomorrow window, transfer mode, acceptance deadline, reminder cadence, expiry, approval-pending information-only behavior, and priority-specific requirements. |
| SHIFT-HO-12 | Medium | AWAITING_APPROVAL | Add management and operational reporting. | Reports show offered/accepted/rejected/expired handovers, acceptance time, overdue count, unresolved carried work, source/destination shifts, teams, engineers, priorities, and SLA outcomes without double-counting tickets or engineer resolutions. Widgets drill into handover records/tickets. |
| SHIFT-HO-13 | High | AWAITING_APPROVAL | Add migration, API, concurrency, permission, SLA, and UI tests. | Clean/upgrade SQL Server migrations pass; tests cover same-day/tomorrow boundaries and timezone/DST, duplicate active handovers, simultaneous acceptance, approval locks, terminal tickets, reassignment mode, SLA continuity, tab counts, filtering, reminders, expiry, and audit history. |

Mandatory conflict rules:

- A handover is a workflow record, not a ticket status.
- Offering a handover does not remove the current assignee or stop their ability to work the ticket.
- Existing assignment endpoints remain the only mechanism that changes ticket ownership.
- `TRANSFER_ON_ACCEPTANCE` must invoke that existing assignment domain service atomically; it cannot write `assigned_user_id` directly.
- A ticket in `PENDING_APPROVAL` remains assignment/status locked. An information-only handover cannot be accepted as an ownership transfer until approval completes.
- Escalation assignment is independent of operational ownership; handover must not clear or rewrite escalation fields.
- SLA clocks continue across shift boundaries. Handover timestamps are evidence only, not SLA start/stop events.
- Resolve/close authorization continues to depend on the actual assignee and existing permissions, not merely handover participation.
- Cancelling or expiring a handover never changes ticket status or assignment.
- Ticket deletion must be blocked or cascade handover records according to the existing audit-retention policy; audit history must not disappear silently.

Default UAT policy proposal:

| Setting | Proposed default |
|---|---|
| Feature enabled | Yes in UAT; disabled by default in production until approved |
| Destination window | Remaining shifts today plus all shifts tomorrow |
| Transfer mode | `ACKNOWLEDGEMENT_ONLY` |
| Source engineer keeps ownership until acceptance | Yes |
| Acceptance deadline | Destination shift start + 30 minutes |
| Expiry | Destination shift end |
| P1/P2 intended engineer required | Yes |
| P3/P4 intended team/shift sufficient | Yes |
| Pending approval | Information-only, no transfer |
| SLA pause/reset | Never |
| Bulk handover | Permission controlled; maximum 100 and atomic validation |

Open business decisions requiring approval before implementation:

1. Should acceptance transfer ownership automatically, or only acknowledge receipt and leave assignment to a manager? Recommended first release: `ACKNOWLEDGEMENT_ONLY`.
2. Can any engineer on the destination shift accept a team handover, or must an intended engineer be named? Recommended: team acceptance for P3/P4, named engineer for P1/P2.
3. Should tomorrow mean the next calendar day or the next configured working shift? Recommended: allow tomorrow's configured shifts, while the UI separately highlights the next shift.
4. What should happen if nobody accepts? Recommended: keep current ownership, mark overdue, notify source plus shift manager/on-call, and expire at destination shift end.

### Shift handover implementation sequence

| Order | Task IDs | Status | Stop/checkpoint |
|---|---|---|---|
| 1 | SHIFT-HO-01, SHIFT-HO-03, SHIFT-HO-08, SHIFT-HO-11 | AWAITING_APPROVAL | Review schema, settings, permissions, and conflict rules before migration. |
| 2 | SHIFT-HO-02, SHIFT-HO-05, SHIFT-HO-06, SHIFT-HO-07 | NOT_STARTED | API/domain tests and SQL Server migration pass before UI deployment. |
| 3 | SHIFT-HO-04 | NOT_STARTED | Tickets tabs switch correctly and counts contain active relevant handovers only. |
| 4 | SHIFT-HO-09, SHIFT-HO-10 | NOT_STARTED | Scheduler/email queue deduplication and CPU checks pass. |
| 5 | SHIFT-HO-12, SHIFT-HO-13 | NOT_STARTED | Analytics, concurrency, SLA continuity, and end-to-end UAT pass. |

Shift handover stop point: `AWAITING_APPROVAL — resolve four open business decisions, then begin SHIFT-HO-01`.

| Order | Task IDs | Status | Required verification checkpoint |
|---|---|---|---|
| 1 | SEC-01 | AWAITING_APPROVAL | User confirms credential rotation; sanitized configs contain no real secrets. |
| 2 | SEC-02, SEC-04 tests | AWAITING_APPROVAL | Auth behavior explicitly approved; backend/frontend auth tests and UAT login pass. |
| 3 | DEP-01, safe parts of DEP-03/04 | AWAITING_APPROVAL | npm audit, pip-audit, tests, lint/type-check, build pass. Major upgrades remain deferred. |
| 4 | UI-01, UI-02, UI-03, UI-04 | AWAITING_APPROVAL | Main Overview reviewed in LocalUAT; drill-through verified. |
| 5 | GEO-01 through GEO-12 | AWAITING_APPROVAL | Clean and upgrade migrations pass on SQL Server; CRUD, searchable client selectors, permissions, exact site pins, management analytics, and hierarchical drill-through pass in UAT. |
| 6 | PERF-01, PERF-02, PERF-03 | AWAITING_APPROVAL | Analytics response equivalence tests and SQL Server UAT timing pass. |
| 7 | Approved DUP/REF/REUSE items | AWAITING_APPROVAL | Before/after behavior comparison, tests, build, and UAT smoke test pass. |
| 8 | Release readiness review | NOT_STARTED | User accepts UAT; only then build a production release. |

## Decision log

| Date | Decision | Result |
|---|---|---|
| 2026-08-14 | User requested two-pass audit. | PASS 1 performed; no audit fixes applied. |
| 2026-08-14 | User requested status and continuation marker. | This document is the authoritative checkpoint. |
| 2026-08-14 | User requested client country/location and country/location master data. | Added normalized geography scope as GEO-01 through GEO-09; no implementation performed in PASS 1. |
| 2026-08-14 | User confirmed geography is required for management dashboards and searchable client assignment. | Expanded scope with GEO-10 through GEO-12 and geographic analytics/drill-through criteria. |
| 2026-08-14 | User requested controlled same-day/tomorrow shift handover for tickets. | Added SHIFT-HO-01 through SHIFT-HO-13, lifecycle, conflict rules, defaults, decisions, and resume checkpoint; no implementation performed in PASS 1. |

## Next action required

User approval is required before PASS 2. Recommended approval scope: `SEC-01`, `DEP-01`, `UI-01`, `UI-02`, `UI-04`, and `PERF-03` first. `SEC-02` changes login persistence and should be an explicit separate decision.
