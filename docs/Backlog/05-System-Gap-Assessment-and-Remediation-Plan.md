# Point 5 — System Gap Assessment and Remediation Program

Status: `IP` — planning baseline prepared; discovery and implementation have not yet been completed.

Baseline release: `1.55.1`  
Baseline database revision: `0162_handover_edit_permission`

## 1. Objective

Create a repeatable, evidence-based process to identify, prioritize, correct, and prevent gaps across the complete SupportHub system. A gap is not limited to a missing feature. It includes any weakness in security, authorization, business workflow, data integrity, performance, availability, deployment, recovery, observability, accessibility, localization, documentation, or automated verification.

The program is complete only when:

1. Every supported module and cross-module workflow has an owner and an audit result.
2. Every finding has evidence, impact, priority, remediation, acceptance criteria, and release status.
3. All Critical and High findings are closed or formally risk-accepted by an authorized owner.
4. Production upgrade and rollback have been rehearsed against a restored production-like database.
5. The gap checks become recurring release gates so the same weaknesses do not return.

## 2. Scope

### Business domains

- Identity, users, profiles, permissions, scopes, access requests, and audit.
- Clients, branches, callers, contacts, products, modules, services, installations, and credentials.
- Contracts, templates, coverage, entitlement, SLA, renewals, finance, collections, and adjustments.
- Internal tickets, Client Portal tickets, complaints, escalation, notifications, satisfaction, and public links.
- Project Handovers, pending points, delivery scope, documents, and dashboard evidence.
- Shifts, visits, operations, schedules, onboarding, knowledge, KPI reviews, reports, and dashboards.
- Imports, exports, email/Outlook, monitoring integrations, API clients, storage, and system operations.

### Technical and operational layers

- React client, FastAPI API, SQLAlchemy/Alembic schema, SQL Server behavior, standalone runtime, IIS configuration, scheduled processing, shared storage, email delivery, backup, restore, deployment, monitoring, and support documentation.

### Environments

- Source development environment.
- Clean SQLite regression database.
- Clean SQL Server database with MARS disabled.
- Populated historical-upgrade SQL Server database.
- Isolated UAT using production-like configuration and data volume.
- Production configuration review without changing production during discovery.

## 3. Non-negotiable rules

- Discovery is read-only. A finding does not authorize a production change.
- Never print, copy, or commit real credentials. Suspected exposure is recorded generically and escalated for rotation.
- Authorization is verified at the API and data-scope levels; hiding a button is not a security control.
- Historical audit findings must be revalidated against `1.55.1` before being marked Open.
- A feature is not Done because it renders. Its permissions, lifecycle, concurrency, audit, reporting, mobile behavior, localization, migration, and recovery must also pass.
- Database changes use Alembic, preserve upgrade compatibility, and are rehearsed on SQL Server.
- Production rollback uses the previous immutable release plus a verified database restore when required; it does not rely on blind migration downgrade.
- Fixes are delivered in small risk-based releases. Critical unrelated changes are not bundled into one large release.

## 4. Priority model

Each finding receives an impact score and a likelihood score from 1 to 5.

| Impact | Definition |
|---:|---|
| 5 | Credential exposure, authorization bypass, irreversible data loss/corruption, system-wide outage, or material legal/compliance impact |
| 4 | Incorrect financial/SLA/contract decision, cross-client disclosure, major workflow outage, or failed recovery |
| 3 | Important workflow blocked, incorrect reporting/notification, serious performance degradation, or significant UX/accessibility failure |
| 2 | Limited workflow friction, localized incorrect behavior, or maintainability risk with a practical workaround |
| 1 | Cosmetic, wording, documentation, or low-impact internal issue |

| Likelihood | Definition |
|---:|---|
| 5 | Occurring now or reliably reproducible in normal use |
| 4 | Likely under normal production volume or common configuration |
| 3 | Plausible under an expected edge case or failure condition |
| 2 | Uncommon and requires several conditions |
| 1 | Theoretical or requires privileged/exceptional conditions |

Priority is calculated from `impact × likelihood`, then raised when regulatory, cross-client, credential, or irreversible-data risk exists:

| Score | Priority | Required response |
|---:|---|---|
| 20–25 | P0 Critical | Contain immediately; stop affected deployment/workflow; correction release before feature work |
| 12–19 | P1 High | Put in the next correction wave with an owner and target release |
| 6–11 | P2 Medium | Schedule after P0/P1 or combine safely with the owning module wave |
| 1–5 | P3 Low | Normal backlog; address when touching the affected area |

The register also records confidence as `Confirmed`, `Probable`, or `Needs validation`. Priority does not replace evidence.

## 5. Required gap register

Maintain one table with these fields:

| Field | Meaning |
|---|---|
| ID | Stable code such as `SEC-001`, `AUTH-001`, or `DATA-001` |
| Domain/page | Where the behavior exists |
| Finding | One observable problem, not a proposed solution |
| Evidence | File/test/query/screenshot/log reference with secrets removed |
| Environment | Development, clean DB, upgrade DB, UAT, or production observation |
| Impact / likelihood | Numeric scores and explanation |
| Priority / confidence | P0–P3 and Confirmed/Probable/Needs validation |
| Owner | Business and technical owner |
| Remediation | Approved correction approach |
| Acceptance | Objective pass/fail conditions |
| Regression coverage | Test or operational control preventing recurrence |
| Status | New, Triaged, Approved, In progress, Ready for UAT, Done, Risk accepted, or Rejected |
| Release/evidence | Migration, release number, test result, and UAT approval |

No item may be marked Done without acceptance evidence and a release or documented non-code control.

## 6. Audit workstreams and checklists

### A. Security and privacy

- Search tracked and deployment files for secrets without displaying secret values; validate rotation and ACL evidence.
- Review cookie/token storage, refresh rotation, logout, revocation, lockout, reset tokens, public tokens, CSRF/XSS/CORS/CSP/HSTS, trusted hosts, and TLS enforcement.
- Test horizontal and vertical authorization, client/branch scope leakage, inactive/expired grants, deny overrides, direct API calls, exports, attachments, and public endpoints.
- Review upload signatures, limits, storage traversal, malware-scanner integration, retention, download authorization, and sensitive logs.
- Run dependency, secret, SAST, and dynamic security scans; triage each result rather than blindly upgrading.
- Review PII retention, audit access, backup encryption, notification content, and data export exposure.

Exit gate: no open P0 security item; all P1 items fixed or formally accepted; authorization abuse suite and security configuration checklist pass.

### B. Identity, permissions, and profile behavior

- Build a permission-to-endpoint-to-page matrix and identify orphaned, missing, over-broad, or unseeded permissions.
- Compare migration grants, seed grants, live profile assignments, UI capability labels, and API enforcement.
- Test each system profile's visible menu, default landing page, permitted API calls, client scope, and denied direct URLs.
- Verify permission changes, access requests, overrides, expiry, concurrent edits, and audit events.

Exit gate: every sensitive endpoint maps to a permission/scope test; each supported profile passes a golden access scenario.

### C. Business workflow and lifecycle integrity

- Model allowed states and transitions for tickets, approvals, escalations, complaints, contracts, finance, visits, onboarding, and Project Handovers.
- Test invalid transitions, repeated submissions, simultaneous updates, stale versions, retries, partial failures, and terminal-state locks.
- Trace cross-module workflows end to end: client → contract/template → coverage → project → ticket → entitlement/SLA → notification/report.
- Verify email-disabled behavior, idempotency, queue retry/dead-letter behavior, audit evidence, and manual overrides.
- Reconcile the remaining B-41 Engineer Intake requirement with the current product roadmap.

Exit gate: lifecycle matrices are documented and concurrency/idempotency tests cover all high-impact transitions.

### D. Data model, migrations, and integrity

- Compare ORM models, Alembic history, SQL Server schema, compatibility head, seed data, and release manifest.
- Detect nullable/duplicate/orphaned records, missing foreign keys, weak uniqueness, inconsistent statuses, invalid dates, and cross-client references.
- Rehearse clean install, every supported historical upgrade path, interrupted/retried migration, seed replay, and large populated upgrade with MARS disabled.
- Validate Unicode, time zones, decimal precision, finance totals, SLA snapshots, historical attribution, and deletion/retention behavior.
- Introduce explicit data-quality queries and a pre-release report with zero unexplained critical violations.

Exit gate: clean and populated SQL Server migrations pass; data-quality report is accepted; compatibility and manifest agree with Alembic head.

### E. Performance, scalability, and availability

- Establish production-like baselines for login, ticket list/detail/create, portal, dashboards, reports, exports, schedules, and contract/project pages.
- Capture query counts, slow SQL, pagination behavior, payload sizes, memory/CPU, frontend bundle sizes, and concurrent-user results.
- Identify in-memory aggregation, N+1 queries, unbounded lists/exports, missing indexes, repeated polling, and oversized chunks.
- Validate single-instance WebSocket behavior and plan Redis/fan-out before multiple API instances.
- Validate scheduled jobs cannot run twice across processes and email/SLA work survives restarts.

Initial service targets to approve during discovery: p95 read API ≤ 1.5 s, p95 normal write ≤ 2 s, dashboard ≤ 3 s, first portal load ≤ 3 s on the agreed network, and zero failed requests in the agreed concurrency test. Targets must be adjusted using measured business volume.

Exit gate: approved service-level targets pass at projected 12-month data volume with documented capacity and scaling limits.

### F. Reliability, observability, and supportability

- Define structured logs, correlation IDs, redaction, retention, rotation, and operator access.
- Monitor API health, database compatibility, scheduled cycles, email queue depth/age/failures, SLA event lag, storage capacity, backup age, and certificate expiry.
- Define alert severity, owner, response time, runbook, suppression, and escalation for every alert.
- Inject controlled failures for database loss, SMTP failure, storage failure, process restart, timeout, and duplicate worker execution.
- Ensure System Operations status is accurate without exposing secrets.

Exit gate: dashboards/alerts and runbooks exist; failure drills create actionable alerts and recover without silent data loss.

### G. Backup, recovery, deployment, and rollback

- Record RPO/RTO with business approval and map backup frequency/retention to those objectives.
- Verify encrypted off-host backup, `RESTORE VERIFYONLY`, scheduled restore drills, application validation after restore, and attachment recovery.
- Rehearse upgrade and rollback from a restored production-like database using the packaged standalone runtime.
- Validate immutable release directories, protected configuration transfer, IIS switch, shared storage preservation, health checks, smoke tests, and evidence capture.
- Add release rejection rules for stale revision docs, missing notes, test failures, unresolved P0/P1 items, or absent rollback evidence.

Exit gate: timed upgrade and rollback rehearsals meet approved RPO/RTO and produce retained evidence.

### H. UX, accessibility, responsive behavior, and localization

- Inventory every page/dialog at supported desktop, tablet, and mobile widths in English LTR and Arabic RTL.
- Detect raw translation keys, duplicate locale objects, clipped labels, narrow selectors, horizontal overflow, unusable tables, focus loss, and poor empty/loading/error states.
- Test keyboard-only navigation, focus order/trapping/restoration, labels, error associations, contrast, zoom/reflow, screen-reader names, and reduced motion.
- Standardize searchable selectors, destructive confirmations, technical-code presentation, permission-denied guidance, and server-error feedback.
- Add automated missing/duplicate translation-key validation and representative responsive/RTL component tests.

Exit gate: agreed WCAG 2.2 AA checklist passes for critical workflows; no raw localization key or blocker at supported widths.

### I. Reporting, dashboards, notifications, and audit accuracy

- Reconcile dashboard totals with source queries and drill-through records using controlled datasets.
- Verify date/time-zone boundaries, distinct-ticket counting, historical attribution, permission scope, exports, empty data, and filters.
- Verify every notification setting actually controls enqueue and delivery; test retries, duplicates, templates, recipients, links, localization, and disabled states.
- Verify audit coverage for security-sensitive and high-value business mutations, including before/after context and actor/correlation evidence.

Exit gate: approved reconciliation cases produce identical UI, API, export, and drill-through results.

### J. Code quality, architecture, dependencies, tests, and documentation

- Revalidate the August 14 audit findings; close obsolete items and migrate only current findings to the new register.
- Find oversized modules, duplicated validation, broad exceptions, circular domain dependencies, dead placeholders, and inconsistent shared controls.
- Map unit, API, component, migration, SQL Server, security, performance, and end-to-end coverage to critical workflows.
- Review dependency support windows and advisories; upgrade in isolated compatibility waves.
- Update stale canonical documentation, especially database heads, release processes, remaining backlog, module behavior, and operational runbooks.

Exit gate: CI enforces lint, strict typing, backend/frontend tests, single Alembic head, clean and historical SQL Server migration, dependency/security checks, production build, and documentation revision consistency.

## 7. Initial findings requiring validation

These are starting hypotheses or observed documentation inconsistencies, not a completed audit:

| Candidate ID | Initial priority | Confidence | Observation | First validation action |
|---|---|---|---|---|
| DOC-001 | P1 | Confirmed | `DATABASE_UPGRADE_POLICY.md` describes revision `0057` and an example `0067`, while release `1.55.1` is at `0162`. | Update canonical revision guidance and add an automated consistency check. |
| DOC-002 | P1 | Confirmed | `Backlog/Remaining.md` still says release `1.49.3` and database head `0144`, while later releases and notes exist. | Reconcile canonical backlog ownership and archive obsolete resume markers. |
| SEC-001 | P0 pending evidence | Needs validation | The prior audit recorded credential exposure. Current rotation, sanitization, ACL, and history status is unknown. | Perform a secret-safe configuration/history review and request rotation evidence; never display values. |
| AUTH-001 | P1 | Needs validation | The documented production cookie/CSRF strategy remains deferred; current access-token behavior must be rechecked. | Threat-model and test the current session implementation under the actual IIS topology. |
| SCALE-001 | P1 | Confirmed design limitation | README states WebSocket fan-out is single-instance and Redis is required before multi-instance scaling. | Confirm production instance count and define a scale trigger/implementation plan. |
| SEC-002 | P1 | Confirmed documentation gap | Threat model still lists dependency/SAST/secret/dynamic testing and authorization abuse cases as residual work. | Inspect CI evidence and add missing security gates with triage rules. |
| DR-001 | P1 | Needs validation | Backup/restore procedures exist, but current scheduled restore-drill evidence and approved RPO/RTO are not visible in the repository. | Obtain operating evidence and run a timed isolated drill if absent. |
| OBS-001 | P1 | Needs validation | Health and error logging exist, but complete queue/job/storage/certificate alert ownership and response evidence is not established. | Produce the monitoring inventory and run controlled failure tests. |
| PERF-001 | P1 | Needs validation | Prior audit identified dashboard in-memory aggregation and O(n²) renewal detection; current code must be reprofiled. | Run SQL/query-count and volume tests against current management dashboards. |
| UX-001 | P1 | Confirmed pattern | Recent raw translation keys and narrow dropdowns show that locale completeness and responsive layout are not enforced globally. | Add automated locale-key/duplicate checks and a page-width/RTL audit matrix. |
| QA-001 | P1 | Needs validation | CI has strong unit/component/migration gates but no visible browser end-to-end suite for critical cross-module journeys. | Inventory current tests and add risk-based E2E scenarios for login, ticket, entitlement, project, portal, and recovery workflows. |
| PROD-001 | P1 | Confirmed backlog item | B-41 Engineer Intake to Call Center remains the documented unimplemented product workflow. | Validate business priority and specification before adding it to a remediation wave. |

## 8. Implementation waves

### Wave 0 — Baseline and evidence collection

1. Freeze the baseline at release `1.55.1` / revision `0162`.
2. Create the gap register and module/endpoint/page/job/integration inventory.
3. Create permission, lifecycle, data-flow, notification, reporting, and test matrices.
4. Revalidate historical audits and close stale claims.
5. Capture current test, dependency, security, query, performance, bundle, backup, and monitoring baselines.
6. Hold a triage review and approve owners, priorities, service targets, RPO/RTO, supported browsers/devices, and UAT dataset.

Deliverable: signed discovery report and approved P0/P1 queue. No feature release is built from discovery alone.

### Wave 1 — Immediate production safety

Order of work:

1. Contain any credential, authorization, cross-client, corruption, or unrecoverable-backup P0 issue.
2. Correct configuration/documentation drift that can cause a wrong deployment or migration.
3. Add regression tests before or with each correction.
4. Rehearse the correction on a restored production-like database.
5. Deliver small patch releases with explicit rollback instructions.

Exit: zero open P0; every remaining P1 has an owner, approved treatment, and target wave.

### Wave 2 — Business and data correctness

Implement authorization matrix corrections, lifecycle/concurrency controls, contract-template-project-ticket consistency, finance/SLA/report reconciliation, data-quality constraints, migration repairs, and notification-setting correctness.

Exit: critical end-to-end business scenarios and reconciliation datasets pass in SQL Server UAT.

### Wave 3 — Reliability, scale, and operations

Implement slow-query/index corrections, bounded exports and pagination, worker/job idempotency, multi-instance readiness where required, monitoring/alerts, queue visibility, backup automation, restore evidence, capacity tests, and recovery runbooks.

Exit: performance targets, failure drills, upgrade, and rollback rehearsal pass.

### Wave 4 — UX, accessibility, localization, and product gaps

Correct global responsive/RTL/localization/accessibility patterns, standardize controls and feedback, and implement approved missing workflows such as B-41 only after its business rules are signed off.

Exit: critical user journeys pass the responsive, RTL, keyboard, screen-reader, and UAT matrices.

### Wave 5 — Maintainability and prevention

Refactor only verified risk hotspots behind behavior tests, remove obsolete documentation/code, update supported dependencies in isolated groups, and make the new audit checks mandatory in CI and release packaging.

Exit: all P0/P1 findings are Done or formally risk-accepted; recurring quarterly and pre-release audit cadence is assigned.

## 9. Verification matrix for every remediation release

- Backend Ruff and strict MyPy.
- Full backend pytest suite plus new focused regression tests.
- Frontend ESLint, Vitest, TypeScript, and production build.
- Clean SQLite migration and clean SQL Server migration.
- Historical populated SQL Server upgrade with MARS disabled.
- Seed replay and database compatibility/manifest checks.
- Permission and scope abuse tests for changed endpoints.
- Concurrency/idempotency tests for changed workflows.
- English/Arabic, desktop/mobile, loading/empty/error/access-denied checks for changed UI.
- Performance comparison for changed queries/pages.
- Packaged standalone runtime help and clean packaged migration.
- Isolated UAT smoke test, upgrade rehearsal, and rollback rehearsal when database or deployment behavior changes.
- Gap register, release notes, operational docs, and audit evidence updated before packaging.

## 10. Governance and reporting

### Roles

- Product owner: approves business behavior, priority, and risk acceptance.
- Security owner: approves security findings, credential rotation, and residual risk.
- Technical owner: owns architecture, remediation, tests, migration, and code review.
- DBA/operations owner: owns backup, restore, SQL Server performance, deployment, monitoring, and rollback evidence.
- UAT owner: signs off realistic workflows and reconciliation results.

One person may hold more than one role, but the approval must be recorded. Developers cannot silently mark a material risk as accepted.

### Weekly status

Report new findings, closed findings, P0/P1 aging, blocked decisions, test/rehearsal results, upcoming releases, and changed residual risk. Do not use percentage complete without listing the underlying register counts.

### Risk acceptance

Risk acceptance must name the finding, impact, reason, compensating control, owner, expiry/review date, and trigger for remediation. `Deferred` without this evidence is not acceptance.

## 11. Recommended first execution slice

Start with Wave 0, then immediately triage `SEC-001`, `DOC-001`, `DOC-002`, `DR-001`, `AUTH-001`, and `UX-001`. This slice is recommended because it verifies production safety, prevents incorrect upgrades, establishes recovery confidence, and adds preventive checks for the visible localization/responsive pattern before expanding into lower-risk feature work.

## 12. Point 5 completion definition

Point 5 remains `IP` while the audit or remediation queue is active. It becomes `DN` only when:

- the full inventory and gap register are complete;
- all P0/P1 items are Done or formally accepted;
- P2/P3 items have approved backlog ownership;
- UAT, performance, security, migration, upgrade, restore, and rollback evidence pass;
- canonical documents match the delivered release and database revision; and
- CI/release gates continuously enforce the agreed preventive controls.

