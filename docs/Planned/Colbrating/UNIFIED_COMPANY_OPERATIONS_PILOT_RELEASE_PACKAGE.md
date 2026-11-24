# Unified Company Operations — Pilot Release Package

**Package status:** PREPARED — approval and rehearsal pending  
**Prepared:** 2026-11-24  
**Database target:** `0292_unified_ops_hardening`  
**Related plan:** `UNIFIED_COMPANY_OPERATIONS_IMPLEMENTATION_PLAN.md`  
**Authority boundary:** This package does not select pilot participants, change customer data, grant permissions, migrate a database, deploy software, or activate a workflow.

## 1. Release objective and containment

The pilot validates one approved Account/Organization/customer group through Project intake, Implementation execution, cross-department collaboration, Support handover and governed analytics while preserving the existing ticket, SLA and legacy `ProjectHandover` workflows.

The pilot is contained by all of the following:

1. Only explicitly approved pilot Account, Organization, Clients and Branches are mapped.
2. Only named users receive the minimum permissions in section 3.
3. Effective-dated department policies restrict customer visibility and operational responsibility.
4. One pilot Project is created after hierarchy and access reconciliation passes.
5. Existing customer records are not merged, deleted or automatically reclassified.
6. Production activation requires a signed deployment decision in section 9 after the restored-copy rehearsal.

## 2. Feature-flag and activation plan

### 2.1 Current implementation truth

The Unified Company Operations routes are protected by backend permissions and customer/department scope. The repository's governed feature-policy framework currently has no Unified Operations feature definition, and the implemented routes do not evaluate a Unified Operations runtime flag. Hiding navigation is not a kill switch.

Therefore, the current safe controls are permission non-grant, no pilot hierarchy mapping, and no Project creation. These are sufficient for packaging and restored-copy rehearsal, but production pilot activation must not rely on an undocumented feature flag.

### 2.2 Required pilot control

Before production activation, Step 8.11 must resolve one of these two release choices and record evidence:

| Choice | Control | Acceptance |
|---|---|---|
| A — preferred | Add a governed `unified_company_operations` policy with `OFF`, `SHADOW`, and `ENFORCED` modes, default `OFF`, supporting `SYSTEM` and `ACCOUNT` scope. Enforce it in backend dependencies for mutating Unified Operations routes; use it for frontend discoverability only after backend enforcement. | `OFF` denies new mutations, `SHADOW` permits read/reconciliation evidence only, `ENFORCED` permits authorized pilot work, and a tested switch back to `OFF` stops new mutations without deleting evidence. |
| B — exception | Use permission withdrawal plus removal/expiry of pilot department assignments as the operational kill switch. | Release owner accepts the slower rollback and demonstrates that all pilot write permissions can be withdrawn, active timers stopped, and new mutations denied without affecting normal Support operations. |

Choice A requires a separately reviewed source change and migration/seed decision; this package does not implement it. Until A or B is signed, production activation is `NO-GO`.

### 2.3 Activation sequence

1. Keep the feature `OFF`, or withhold all pilot write permissions under Choice B.
2. Deploy the verified build and migrate to `0292` while the application is stopped.
3. Run compatibility, health, reconciliation and read-only authorization checks.
4. Apply only the approved Account/Organization/Client/Branch mappings.
5. Apply effective-dated department policies and named-user permissions.
6. Create one pilot Project and confirm its hierarchy keys.
7. Enable `ENFORCED` for the pilot Account, or complete the signed Choice B activation.
8. Observe the pilot for the approved period; do not expand scope implicitly.

## 3. Minimum permission matrix

`Administrator` is for deployment and emergency recovery, not daily pilot work. Every assignment must be named, time-bounded where practical, approved by the business owner and security owner, and verified with both allowed and denied tests.

| Pilot role | Required permissions | Explicit exclusions unless separately approved |
|---|---|---|
| Customer-structure administrator | `client.view`, `client.manage`, `customer_structure.policy.view`, `customer_structure.policy.manage` | Project execution, private Implementation history, Support activation |
| Project manager | `project.portfolio.view`, `project.create`, `project.manage`, `project.assignment.request`, `analytics.dictionary.view`, `analytics.project.view` | Assignment response, Implementation approval/review, Support acceptance/activation |
| Implementation manager | `project.portfolio.view`, `project.assignment.respond`, `implementation.task.view`, `implementation.task.manage`, `implementation.task.assign`, `implementation.task.review`, `implementation.unplanned.create`, `implementation.unplanned.approve`, `implementation.private_history.view`, `cross_department.request.create`, `cross_department.request.respond`, `cross_department.request.manage`, `cross_department.event.publish`, `cross_department.ticket_link.manage`, `cross_department.history.view`, `handover.view`, `handover.prepare`, `handover.submit`, `analytics.dictionary.view`, `analytics.implementation.view` | Customer-policy management, Support acceptance/activation, Executive analytics |
| Implementation engineer | `project.portfolio.view`, `implementation.task.view`, `implementation.task.worklog`, `implementation.unplanned.create`, `cross_department.request.create`, `cross_department.history.view` | Task administration, unplanned approval, private history unless justified, handover decision |
| Support manager | `project.portfolio.view`, `cross_department.request.create`, `cross_department.request.respond`, `cross_department.event.publish`, `cross_department.ticket_link.manage`, `cross_department.history.view`, `handover.view`, `handover.review`, `handover.accept`, `handover.activate_support`, `analytics.dictionary.view`, `analytics.support_readiness.view` | Implementation private history, Implementation task mutation, customer-policy management |
| Support engineer | `cross_department.history.view` plus existing ticket permissions | Private Implementation history, handover decisions, Project/Implementation mutation |
| Executive observer | `analytics.dictionary.view`, `analytics.project.view`, `analytics.support_readiness.view`, `analytics.executive.view`, with `project.portfolio.view` only if direct Project navigation is approved | All mutations and private Implementation history |
| Release operator | Existing deployment, database backup/restore and permission-seeding authority; temporary `Administrator` only when required by the runbook | Daily pilot work and approval of their own release |

Permission checks do not replace effective customer access. A user must also have the approved customer/department scope, and `OVERRIDE` must retain inherited customer visibility while replacing operational responsibility.

## 4. Named-pilot approval template

Copy this table into the release evidence record; do not commit personal credentials or secrets.

| Item | Approved value | Owner | Approval/evidence | Expiry or review date |
|---|---|---|---|---|
| Pilot Account | `TBD` | Business owner | `TBD` | `TBD` |
| Pilot Organization | `TBD` | Business owner | `TBD` | `TBD` |
| Pilot Clients | `TBD` | Customer-data owner | `TBD` | `TBD` |
| Pilot Branches | `TBD` | Customer-data owner | `TBD` | `TBD` |
| Project Management department and manager | `TBD` | PM director | `TBD` | `TBD` |
| Implementation department, team, manager and engineers | `TBD` | Implementation director | `TBD` | `TBD` |
| Support department, manager and engineers | `TBD` | Support director | `TBD` | `TBD` |
| Executive observers | `TBD` | Executive sponsor | `TBD` | `TBD` |
| Release operator and DBA | `TBD` | IT operations | `TBD` | End of pilot |
| Security reviewer | `TBD` | Security owner | `TBD` | End of pilot |
| Pilot Project name/number | `TBD — create only after mapping approval` | Project manager | `TBD` | Pilot close |
| Observation period | `TBD` | Executive sponsor | `TBD` | Pilot close |
| Support/escalation channel | `TBD` | Release owner | `TBD` | Pilot close |

Mandatory attachments are the approved mapping workbook, dry-run reconciliation JSON/CSV/Markdown, permission export before and after activation, database backup identity and restore proof, build/version checksum, acceptance evidence and decision record.

## 5. Pilot acceptance checklist

### 5.1 Pre-deployment

- [ ] Release artifact/version and SHA-256 are recorded and match the rehearsed build.
- [ ] Database backup completes and restore verification is recorded.
- [ ] Current schema revision, application health and storage health are recorded.
- [ ] Reconciliation reports have identical before/after counts and zero automatic changes.
- [ ] Every proposed customer mapping is reviewed; unresolved critical hierarchy exceptions are zero for pilot scope.
- [ ] Named participants, permission bundles and department assignments are approved.
- [ ] Feature control Choice A or B is signed and rehearsed.
- [ ] Monitoring owners, thresholds and escalation contacts are staffed for the observation window.

### 5.2 Functional and security acceptance

- [ ] Account → Organization → Client → Branch navigation matches the approved mapping.
- [ ] A non-pilot customer cannot be discovered through pilot routes, options, analytics or drilldowns.
- [ ] Project manager can create and govern only the pilot Project.
- [ ] Implementation accepts capacity, completes planned work, records one approved unplanned item, work log, blocker, evidence and review.
- [ ] A second simultaneous active timer for one engineer is rejected by the database invariant.
- [ ] Cross-department request/response and shared event history work; private Implementation notes are absent from Support views.
- [ ] Ticket link is limited to the same Client and exposes only the Support-safe history.
- [ ] Readiness evidence gate, Support review, acceptance, stabilization and explicit activation work in order.
- [ ] Legacy ticket/SLA behavior and legacy `ProjectHandover` remain unchanged.
- [ ] Project, Implementation, Support-readiness and Executive totals reconcile with authorized drilldowns.
- [ ] English/Arabic, keyboard operation, responsive layout and access-denied routes pass.
- [ ] Audit events identify actor, action, entity and relevant reason/decision.

### 5.3 Pilot exit

- [ ] No unresolved severity-1 or severity-2 defect exists.
- [ ] No unauthorized disclosure, cross-customer result or private-history leak occurred.
- [ ] No unexplained KPI/drilldown variance exists.
- [ ] Open residual work has an owner and due date; stabilization ownership is active.
- [ ] Business, security, Support, Implementation and release owners sign the exit decision.
- [ ] Expansion, pause, rollback or production adoption is explicitly selected; silence does not authorize expansion.

## 6. Backup, deployment and rollback runbook

### 6.1 Backup and evidence

1. Announce the maintenance window and stop new application writes.
2. Record application version, database server/database, current Alembic revision, row-count baseline and current permission export.
3. Take a native SQL Server full backup to the approved protected location; record backup name, UTC/Cairo timestamps, size and checksum where supported.
4. Restore that backup to a separate validation database and run integrity plus application compatibility checks. A backup without restore evidence is not accepted.
5. Back up deployment configuration and user-uploaded storage using the existing protected operational process. Do not place secrets or customer files in the repository.

### 6.2 Deployment

1. Stop IIS/application services and confirm no process is writing to the database.
2. Deploy the exact rehearsed artifact; preserve environment-specific protected configuration.
3. Run the packaged migration command to `0292_unified_ops_hardening` and then the packaged seed command.
4. Start the service and verify health, schema compatibility, authentication and ordinary ticket operation before pilot activation.
5. Run read-only reconciliation and authorization smoke tests.
6. Apply only signed pilot mappings, assignments and permission changes, then activate the chosen feature control.
7. Record the release start/end, operator, artifact checksum, migration output and smoke evidence.

### 6.3 Rollback triggers

Rollback or immediately disable new Unified Operations mutations on any of these events:

- unauthorized customer, department, private-history or analytics evidence exposure;
- migration/compatibility failure, database corruption signal or unreconciled count change;
- inability to stop/expire pilot access;
- repeated Project timer invariant or critical workflow failure;
- severity-1 defect, sustained service unavailability, or unacceptable regression to tickets/SLAs;
- KPI aggregate/drilldown variance that cannot be explained within the agreed response time.

### 6.4 Rollback procedure

1. Freeze pilot mutations using the rehearsed Choice A `OFF` control or Choice B permission withdrawal; stop active timers and announce the freeze.
2. Preserve logs, audit identifiers, error correlation IDs, current revision and a post-incident database backup before destructive recovery.
3. If the schema and application are healthy, roll back the application artifact while leaving additive schema/data evidence intact only if the prior version is compatibility-tested with `0292`.
4. If database restoration is required, stop all writers, restore the verified pre-deployment backup, restore matching uploaded storage/configuration, deploy the matching prior artifact, and verify revision/health.
5. Never run a production Alembic downgrade merely because the application is rolled back. The `0292 → 0291` downgrade is for isolated rehearsal unless the DBA and release owner explicitly approve it with backup evidence.
6. Reconcile pilot records, permissions, ticket/SLA behavior and audit continuity; record data loss window, if any.
7. Reopen access only after security, business and release owners sign a new decision.

## 7. Monitoring and alert plan

All alerts require a named primary owner, backup owner, response deadline and evidence link before activation.

| Signal | Initial threshold | Severity | Owner/action |
|---|---|---|---|
| API health or database compatibility failure | Any failed production check; 2 consecutive health failures | Critical | Release operator disables pilot writes and follows rollback triage. |
| Unified Operations 5xx rate | 3 in 5 minutes or >2% of requests | High | Application owner inspects correlation IDs; freeze mutations if state is uncertain. |
| Authorization denial surge | 10 denials for one user/route in 10 minutes | High | Security owner checks incorrect grants, probing and expired scope. |
| Cross-scope/privacy signal | Any confirmed non-pilot customer or private-history disclosure | Critical | Disable pilot immediately, preserve evidence and start security incident process. |
| Migration/schema mismatch | Any revision other than approved head or compatibility error | Critical | Block activation; no manual schema edits. |
| Active timer conflict | Any database unique-index violation after user feedback handling, or repeated failure for one user | Medium/High | Implementation owner stops duplicate work and application owner diagnoses race/UI state. |
| Handover activation risk | Any `HIGH` risk at proposed activation | High | Support owner blocks activation until evidence/residual/stabilization reason is resolved. |
| Overdue cross-department request | Any critical request overdue; or 3 total overdue | Medium | Owning department manager assigns action and due time. |
| KPI reconciliation variance | Any row mismatch or non-zero unexplained aggregate difference | High | Analytics owner blocks reporting sign-off and captures filters/drilldown evidence. |
| Backup/restore failure | Any failed backup, integrity check or restore validation | Critical | DBA blocks deployment. |
| Ticket/SLA regression | Any confirmed pilot-caused failure or material latency regression | Critical/High | Support owner freezes pilot; release owner evaluates rollback. |

During the first business day, review Critical/High signals continuously and record checkpoints at activation, +1 hour, +4 hours and end of day. Thereafter review daily for the approved observation period. Threshold tuning must be recorded; it must not silently weaken privacy, backup or schema alerts.

## 8. Evidence register

| Evidence ID | Required content | Status |
|---|---|---|
| `UCO-PILOT-01` | Approved named-pilot template and scope | Pending business approval |
| `UCO-PILOT-02` | Artifact version/checksum and verification results | Pending build selection |
| `UCO-PILOT-03` | Pre-deployment backup and independent restore proof | Pending rehearsal |
| `UCO-PILOT-04` | Reconciliation JSON/CSV/Markdown and mapping approval | Pending approved mapping |
| `UCO-PILOT-05` | Permission/access before-after export and denied tests | Pending rehearsal |
| `UCO-PILOT-06` | Feature control/kill-switch evidence | Pending Step 8.11 |
| `UCO-PILOT-07` | Functional, security, analytics and accessibility acceptance | Pending rehearsal |
| `UCO-PILOT-08` | Monitoring alert delivery and owner acknowledgement | Pending rehearsal |
| `UCO-PILOT-09` | Rollback drill and recovery reconciliation | Pending rehearsal |
| `UCO-PILOT-10` | Signed deployment decision record | Pending decision |

## 9. Deployment decision record

**Decision:** `NO-GO — package prepared; approvals and restored-copy rehearsal outstanding`  
**Decision date/time (Africa/Cairo):** `TBD`  
**Release/build/checksum:** `TBD`  
**Target environment:** `TBD`  
**Pilot scope:** `TBD`  
**Feature control choice:** `TBD — A or approved B exception`  
**Evidence reviewed:** `TBD — UCO-PILOT-01 through UCO-PILOT-09`  
**Known accepted risks:** `TBD`  
**Rollback authority:** `TBD`  
**Observation window:** `TBD`  

| Decision authority | Name | Decision/signature | Date/time |
|---|---|---|---|
| Executive/business sponsor | `TBD` | `TBD` | `TBD` |
| Customer-data owner | `TBD` | `TBD` | `TBD` |
| Project Management owner | `TBD` | `TBD` | `TBD` |
| Implementation owner | `TBD` | `TBD` | `TBD` |
| Support owner | `TBD` | `TBD` | `TBD` |
| Security owner | `TBD` | `TBD` | `TBD` |
| DBA/operations owner | `TBD` | `TBD` | `TBD` |
| Release owner | `TBD` | `TBD` | `TBD` |

Allowed final decisions are `GO`, `CONDITIONAL GO` with explicit time-bounded conditions, `NO-GO`, or `ROLLBACK`. Only a signed `GO`/`CONDITIONAL GO` authorizes the named scope; it does not authorize broader rollout.
