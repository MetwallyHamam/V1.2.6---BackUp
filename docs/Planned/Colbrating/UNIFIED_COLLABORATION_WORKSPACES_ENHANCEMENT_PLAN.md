# Unified Collaboration Workspaces — Enhancement Execution Plan

**Status:** IN CONTROLLED IMPLEMENTATION  
**Prepared:** 2026-11-24 (Africa/Cairo)  
**Baseline:** Local `MillensysSupportHub`, revision `0294_project_status_capacity`  
**Scope:** Project Management, Implementation intake/execution, collaboration, Support handover, navigation and role workspaces  
**Production activation:** NOT AUTHORIZED by this plan

## 1. Purpose

Convert the delivered Unified Company Operations foundation into coherent, secure operational workspaces for Project Management and Implementation users.

The current implementation provides hierarchy, Project portfolio, creation wizard, assignment requests, task execution, analytics, collaboration and Support handover primitives. The missing layer is a governed role-oriented operating model: least-privilege profiles, lifecycle enforcement, intake queues, personal/team workspaces, consistent navigation, actionable dashboards and safe cross-scope authorization.

This plan extends the existing `company_projects` and related tables. It must not introduce a second authoritative `implementation_projects` domain. The older `IMPLEMENTATION_DEPARTMENT_COLLABORATION_PLAN.md` remains useful background for business intent, event visibility and ticket collaboration, but any persistence proposal in it must be reconciled into the delivered `company_project_*` and `project_*` model.

## 2. Confirmed current-state gaps

### 2.1 Security and scope

- Project list visibility is scoped, while Project detail, plan and portfolio-summary behavior is not consistently based on the same authorized Project set.
- Assignment-request response does not prove that the actor is authorized for the requested department/team.
- Several task, blocker, evidence, review, worklog and timer mutations authorize by broad permission without rechecking Project membership or task assignment.
- Support-handover operations use broad permissions without consistently verifying Project/department participation.
- Frontend action visibility does not consistently match backend permission and lifecycle requirements.

### 2.2 Lifecycle

- Legacy and new Project statuses coexist without one state machine.
- Generic Project patching can write uncontrolled status values.
- Execution operations are not uniformly blocked before Implementation acceptance.
- Task progress recalculation and Project lifecycle progression are not governed by one service.
- Handover initialization lacks a backend eligibility rule.

### 2.3 Identity and roles

- `PROJECT_HANDOVER` is overloaded with Project Management, Implementation, analytics, collaboration, UAT and handover capabilities.
- Dedicated Project Manager, Implementation Manager, Team Leader, Engineer and Support Handover Reviewer profiles do not exist.
- Local Project data proves intake-owner selection can cross the requested department when no Team is selected.

### 2.4 Operational user experience

- No Implementation intake inbox exists.
- No Project Manager operational workspace exists.
- `/project-tasks/my-work` exists but has no dedicated Implementation Engineer page.
- Analytics pages measure results but do not operate the daily workflow.
- Sidebar navigation presents separate technical pages rather than a role-oriented Projects & Implementation area.
- No team capacity/resource-assignment workspace exists.

### 2.5 Project creation and plan maintenance

- Draft requires a complete plan and cannot be resumed or edited in the wizard.
- Published plan revision/republish is not governed.
- Products/modules come from the global catalog rather than verified Client installation/contract scope.
- Project Manager and intake-owner selectors are insufficiently department-scoped.
- Branch primary selection is implicit.
- Documents are references rather than governed binary uploads.

## 3. Target operating model

### 3.1 Role workspaces

| Role | Default workspace | Primary responsibilities |
|---|---|---|
| Project Manager | Project Management Workspace | Drafts, publishing, returned intake, schedule/scope, plan revision, stakeholder coordination and handover oversight |
| Implementation Manager | Implementation Intake & Delivery Workspace | Accept/return/propose requests, capacity, team assignment, approvals, risks, reviews and handover readiness |
| Implementation Team Leader | Team Delivery Workspace | Team queue, engineer allocation, blockers, reviews, load and schedule conflicts |
| Implementation Engineer | My Implementation Work | Assigned tasks, timer/worklogs, dependencies, evidence, blockers and review responses |
| Support Handover Reviewer | Support Readiness Workspace | Readiness review, decision, residual ownership, stabilization and Support activation |
| Executive | Existing dashboard panel | Authorized aggregate evidence and drilldown only |

### 3.2 Navigation

Add a permission-aware top-level group: **Projects & Implementation**.

Recommended entries:

1. My Implementation Work
2. Intake Requests
3. Project Management Workspace
4. Team Delivery Board
5. Project Portfolio
6. Project Analytics
7. Implementation Analytics
8. Support Readiness
9. Project Administration

Navigation must never grant access. Every route and API retains authoritative backend scope checks. Items and actions are hidden when irrelevant, but direct requests must still return `403` or privacy-preserving `404` as defined by policy.

## 4. Canonical lifecycle

Implement one transition service and forbid direct status mutation outside it.

```text
DRAFT
  -> AWAITING_IMPLEMENTATION_ACCEPTANCE
      -> INTAKE_PROPOSED
      -> INTAKE_RETURNED
      -> INTAKE_REJECTED
      -> READY_FOR_EXECUTION
          -> IN_EXECUTION
              -> DELIVERY_REVIEW
                  -> HANDOVER_PREPARATION
                      -> SUPPORT_REVIEW
                          -> STABILIZATION
                              -> COMPLETED

Any active delivery state -> ON_HOLD -> prior governed state
Authorized terminal action -> CANCELLED
```

Every transition requires:

- permitted source and target;
- actor permission and scope;
- reason where required;
- prerequisite validation;
- concurrency/version protection;
- audit event and notification;
- idempotency behavior;
- transition history record.

Legacy states (`INTAKE`, `PLANNING`, `ACTIVE`, `HANDOVER_PENDING`, `READINESS_REVIEW`) must receive a documented forward mapping. No automatic populated-data conversion may run until a read-only report is reviewed.

## 5. Delivery waves

### Wave 0 — Decisions, inventory and safety harness

**Goal:** Freeze contracts before modifying behavior.

Deliverables:

- Approve canonical lifecycle and transition ownership.
- Approve privacy behavior: when to return `403` versus scope-hiding `404`.
- Approve role/profile names and permission matrix.
- Inventory every Project/Implementation/handover endpoint and frontend action.
- Create a reusable `ProjectScopeService` contract.
- Capture populated SQL Server counts and current status/profile distributions.
- Add a dedicated Unified Collaboration runtime feature flag or approve the documented permission-withdrawal fallback.

Exit gate:

- Signed state-transition table, permission matrix, scope matrix and data-conversion decision.
- No behavior change and no populated-data mutation.

### Wave 1 — Authorization hardening

**Goal:** Close cross-Project and cross-department authorization gaps before adding new workspaces.

Backend:

- Centralize `authorized_project_query(actor, capability)` and `require_project_access(...)`.
- Apply the same scope to list, summary, detail, plan, analytics drilldown and export.
- Require requested-department manager/team-leader authority for assignment response.
- Require Project participation plus task ownership/assignment/manager scope for task mutations.
- Scope blocker, evidence, worklog, timer, review, collaboration and handover mutations.
- Prevent arbitrary evidence IDs and cross-Project references.
- Add optimistic concurrency where decisions or task state can race.

Frontend:

- Add a centralized capability contract for action visibility.
- Remove buttons that the current actor cannot execute.
- Render privacy-safe empty/forbidden states without global error noise.

Required tests:

- Same-department, other-department, unrelated-user, Project Manager, team leader, engineer, Support reviewer and administrator matrices.
- Direct-object-reference tests for every Project child resource.
- Summary/list/drilldown reconciliation tests.

Exit gate:

- No known IDOR path.
- Visible totals equal the caller's authorized records.

### Wave 2 — Lifecycle and intake workflow

**Goal:** Make Publish-to-Implementation operational.

Persistence candidates:

- `project_status_transitions` append-only history.
- assignment-request version, decision reason, proposed dates/team and decision timestamps where missing.
- Project row version for concurrency.

Backend:

- Introduce `ProjectLifecycleService`.
- Replace arbitrary Project status patching with explicit transition commands.
- Add paginated assignment-request inbox endpoints: pending for my department, decided, created by me and request detail/history.
- Enforce department/team membership on acceptance and proposal.
- On acceptance, establish Project department/team/membership records atomically.
- Permit execution only in executable states.
- Notify Project Manager, intake manager, Team leader and assigned intake owner.

Frontend:

- Build **Implementation Intake Requests** with Accept, Propose, Return and Reject actions.
- Show capability, requested dates, requested Team, scope, Products/Modules, phases, workload warning and decision history.
- Add Project Manager queue for pending, proposed, returned and rejected requests.

Exit gate:

- Published Project can be processed end-to-end without API tools or administrator privileges.
- Duplicate acceptance cannot create duplicate Project departments/teams.

### Wave 3 — Least-privilege profiles and membership

**Goal:** Stop using `PROJECT_HANDOVER` as a universal Project/Implementation role.

Profiles:

- `PROJECT_MANAGER`
- `IMPLEMENTATION_MANAGER`
- `IMPLEMENTATION_TEAM_LEADER`
- `IMPLEMENTATION_ENGINEER`
- `SUPPORT_HANDOVER_REVIEWER`

Deliverables:

- Seed idempotent profiles and granular permissions.
- Separate view, plan, assign, execute, review, approve-unplanned, publish, handover-prepare and handover-review powers.
- Create or formalize effective-dated Project membership roles.
- Build read-only migration preview from current `PROJECT_HANDOVER` assignments.
- Require explicit approval before changing existing user profiles.

#### Proposed permission preview

These are proposed pilot bundles. Each bundle assumes the actor also satisfies the relevant record scope. Existing access profiles may contribute additional permissions, so review effective access before approving any mapping.

| Profile | Existing permissions suited to the pilot | Scope and outstanding work |
|---|---|---|
| Project Manager | `project.portfolio.view`, `project.create`, `project.assignment.request`, `handover.view` | Wizard creation and publication are available. Editing phases and milestones, holding, and resuming require a scoped management permission. Today those actions require `project.manage`, which grants company-wide Project visibility. |
| Implementation Manager | `project.portfolio.view`, `project.assignment.respond`, `implementation.task.view`, `implementation.task.review`, `implementation.unplanned.approve`, `handover.view` | Intake belongs to the requested department. Review and approval need independent checks that the work belongs to the manager’s delivery department. |
| Implementation Team Leader | `project.portfolio.view`, `implementation.task.view`, `implementation.task.review` | Review and reassignment need team membership checks. The existing `implementation.task.assign` code alone does not secure the execution routes. |
| Implementation Engineer | `implementation.task.view`, `implementation.task.worklog`, `implementation.unplanned.create` | My Work and assigned worklogs are available. Task status, blockers, and evidence currently share `implementation.task.manage` with broader actions. Split those actions and enforce assignment before granting them. Verify project-wide task lists against the intended engineer scope. |
| Support Handover Reviewer | `handover.view`, `handover.review` | Review requires the intended receiving Support scope. Reserve `handover.activate_support` for the designated activation owner. Ticket implementation history additionally requires Ticket visibility and authorized Project scope. |

For the assignment preview, list current `PROJECT_HANDOVER` holders with their active department and team memberships, current effective permissions, proposed profile or profiles, and permissions gained or lost. Flag missing or conflicting evidence for manual mapping. A department name alone cannot distinguish a manager, team leader, engineer, or reviewer. Include a check for grants retained through other profiles, especially `project.manage`.

Exit gate:

- Each pilot user completes only their assigned workflow.
- Permission withdrawal takes effect immediately with the same token.

### Wave 4 — Role-specific workspaces and sidebar

**Goal:** Give each role a coherent daily operating surface.

#### Project Management Workspace

Portfolio UX slice: default the Overview queue to My projects, use a searchable and paginated portfolio with current lifecycle statuses, and put Schedule and Execution actions on each row. Keep customer, ownership and planning details available from the project name. The next workflow slice is a Project details hub with Overview, Plan, Schedule, Activity and Handover views, followed by resumable drafts and a manager-facing intake decisions queue. Validate the main paths with keyboard navigation and signed-in desktop and mobile checks.

1. Ship a dedicated Project Management shell with a default Overview page, project portfolio, and customer navigation. The first release selects the shell for users with scoped Project Manager access. Verify with `Projectuser` on local IIS.
2. Add Project Templates with draft, published and archived states and versioned plans. Allow managers to start from scratch or copy a plan from a project they can access. Store products, modules, phases, tasks, duration estimates and dependencies. Keep customer records, attachments and employee assignments outside template versions.
3. Add Start from template and Start blank to the project wizard. Validate customer product and module availability, detect missing dependencies, and calculate dates from the selected start date. Let the manager edit the copied plan before saving or publishing. Record the source version on the project.
4. Add Project Overview and Gantt & Schedule tabs. Show milestones, overdue and blocked tasks, intake and handover status, planned versus actual dates, and schedule variance. Use the same authorized plan data for both views and provide a keyboard-accessible schedule table.
5. Test template version isolation, date calculation and dependency validation, workspace navigation under the IIS base path, and the complete draft-to-publication flow. Add manager-facing intake, collaboration and handover queues as their scoped read APIs become available.

Implementation progress: the customer-neutral template plan models product and module scope, phases, tasks, relative dates and finish-to-start dependencies. Relative dates use elapsed minutes. Validation covers scope, phase boundaries, missing predecessors, dependency cycles and predecessor finish times. Migration `0296_project_templates` and the owner-scoped API now save drafts and published versions as separate snapshots. The API regression test verifies that revisions preserve earlier plans and another user cannot access them. The migration passed an isolated SQLite upgrade, downgrade and re-upgrade. Local SQL Server migration and deployment, catalog validation, archive actions and the wizard picker remain pending.

The wizard can publish a reusable template from Review and copy a published version into a new project at a chosen start time. It checks the wizard catalog, preserves finish-to-start dependencies on project save, and asks the manager to choose task assignees. Review shows current customer contract coverage as guidance for new installations. Wizard audit events record the source template version after checking that it is published and owned by the creator. The dedicated workspace has a Project Templates page for browsing version history and publishing a draft as a new version. Project details link to Gantt & Schedule for planned phases, tasks and milestones and project-level start and completion variance. Governed lifecycle transitions record actual dates for new activity. Local IIS runs revision `0296_project_templates`.

- My drafts and resume action
- Pending/proposed/returned intake
- Projects requiring attention
- Milestone and schedule variance
- Scope/change queue
- Document/evidence completeness
- Collaboration response queue
- Handover readiness

#### Implementation Manager Workspace

- Pending intake
- Accepted but unassigned Projects
- Team capacity and forecast
- Overdue/blocked/review tasks
- Unplanned-work approvals
- Projects approaching handover
- Department notifications and recent events

#### Team Delivery Workspace

- Team Projects and task lanes
- Engineer load and conflicts
- Assignment/reassignment
- Blockers and review queue
- Planned versus approved-unplanned effort

#### My Implementation Work

- Today, upcoming, overdue and blocked tasks
- Active timer
- Dependencies and Project context
- Worklog and evidence capture
- Submit for review and returned-review actions
- Personal notifications and recent history

Frontend requirements:

- Add the Projects & Implementation sidebar group.
- Set role-aware default pages without overriding a user's explicit preference.
- Preserve `/SupportHub` router basename for every link.
- Provide responsive and keyboard-accessible layouts with English and Arabic labels.

Exit gate:

- A Project Manager, Implementation Manager and Engineer can complete their primary daily workflows from their own landing page.

### Wave 5 — Project workspace and plan governance

**Goal:** Replace the basic task board with a Project command center.

Project workspace tabs:

1. Overview
2. Plan (phases, milestones and timeline)
3. Tasks
4. Team and capacity
5. Products and Modules
6. Documents and evidence
7. Risks, blockers and changes
8. Collaboration and linked tickets
9. UAT/deployment
10. Handover and stabilization
11. Audit history

Deliverables:

- Partial Draft save and resume.
- Controlled Draft edit and published-plan revision.
- Versioned baseline with approval and change summary.
- Explicit primary Branch.
- Client Product/Module eligibility from installations/contracts with governed exception.
- Department-scoped Project Manager/intake/engineer selection.
- Schedule/dependency validation and conflict warnings.
- Actual secured document upload, malware state, hash, visibility and download audit.

Exit gate:

- No Project-plan maintenance requires direct database access or an unrelated legacy page.
- Published scope changes are versioned and auditable.

### Wave 6 — Handover, Support activation and stabilization

**Goal:** Enforce the delivery-to-Support boundary.

- Backend eligibility for handover initialization.
- Template/version ownership and required evidence rules.
- Support review queue with Accept, Conditional Accept, Return and Reject.
- Residual-item ownership and due-date enforcement.
- Stabilization reviews, exit criteria and governed completion.
- Support activation must not occur before acceptance and stabilization-plan prerequisites.
- Client `support_started_at` changes must remain audited and policy-approved.

Exit gate:

- Early handover and early Support activation are rejected by the backend.
- Project completion requires resolved/accepted readiness obligations.

### Wave 7 — Analytics, notifications and operational hardening

**Goal:** Make dashboards actionable and trustworthy after workflow correctness.

- Reconcile workspace counts, portfolio totals and analytic drilldowns through shared authorized queries.
- Add intake aging, acceptance cycle, capacity, schedule variance, blocker aging, review cycle and handover-readiness metrics.
- Link every metric to exact authorized evidence.
- Add durable notifications with deduplication and deep links.
- Add monitoring for authorization denials, transition conflicts, active timers, stuck intake, overdue blockers and failed evidence storage.
- Complete accessibility, Arabic layout, performance, backup/restore and rollback rehearsals.

Exit gate:

- KPI numerator/denominator reconcile with workspace queues.
- Alert ownership and response procedures are signed.

## 6. Data and migration strategy

- Continue from `0294_project_status_capacity`; assign new revision numbers only during implementation.
- One concern per migration where practical.
- Support SQL Server and clean SQLite rehearsals for every revision.
- Back up and `RESTORE VERIFYONLY` before local populated migration.
- Run clean upgrade, single-step downgrade and re-upgrade rehearsals.
- Use read-only preview reports for status/profile conversion.
- Never auto-assign new profiles or rewrite populated Project states without an approved mapping file.
- Preserve the existing legacy `ProjectHandover` boundary unless a separate conversion plan is approved.

## 7. API design standards

- Paginate all inbox/workspace collections.
- Use stable filter contracts and server-side scope.
- Return typed error codes for invalid transition, scope, conflict and prerequisite failures.
- Require idempotency keys for publish, accept, transition and activation commands where retries can duplicate work.
- Use row versions or equivalent optimistic concurrency for decisions and task transitions.
- Avoid generic mutation endpoints for lifecycle state.
- Include permitted actions in resource responses where useful, but never treat them as backend authorization.

## 8. Testing strategy

Minimum gates for every wave:

- Ruff and strict MyPy for changed backend modules.
- Backend unit/service and authorization matrix tests.
- SQL Server integration for dialect-sensitive behavior.
- TypeScript, focused ESLint and Vitest coverage.
- Production frontend build.
- Clean migration rehearsal and populated-copy rehearsal when schema changes.
- Manual keyboard, responsive, Arabic/English and IIS-basename navigation checks.
- Audit, notification, concurrency and rollback evidence proportional to the change.

Critical end-to-end scenarios:

1. Project Manager saves partial Draft, resumes, publishes and receives a returned proposal.
2. Implementation Manager sees only their department inbox, proposes a Team/date, then accepts once.
3. Team leader assigns eligible engineers without cross-department leakage.
4. Engineer sees only assigned work, logs time, adds evidence, blocks and submits review.
5. Reviewer returns and approves tasks; Project progress and lifecycle reconcile.
6. Unplanned work cannot start before authorized approval.
7. Support cannot initialize/review/activate outside the governed handover stage.
8. Unrelated users cannot enumerate Projects, tasks, evidence, totals or drilldowns by ID.
9. Removing a permission or membership revokes access immediately.
10. Backup restore, rollback and re-upgrade preserve counts and audit history.

## 9. Release controls

Each wave requires its own GO/NO-GO record. A local test deployment does not authorize production activation.

Required before pilot:

- approved Account/Organization/Client hierarchy;
- named Project Management, Implementation and Support pilot users;
- approved role/profile mapping;
- one pilot Project and acceptance criteria;
- feature-control decision;
- monitoring and recovery owners;
- rollback artifacts and database backup;
- security and privacy sign-off.

## 10. Recommended first implementation slice

Start with Waves 0 and 1, followed by the smallest usable portion of Wave 2:

1. central Project scope service;
2. detail/summary/task/handover authorization hardening;
3. assignment responder department validation;
4. lifecycle transition service foundation;
5. read-only Implementation intake inbox;
6. governed Accept/Propose/Return/Reject actions;
7. focused tests and local deployment.

Do not begin dashboard expansion before this slice passes. A polished workspace built on inconsistent authorization and lifecycle rules would increase risk and rework.

## 11. Tracking table

| Wave | Status | Migration | Local deployment | Evidence |
|---|---|---|---|---|
| 0 — Decisions/safety harness | IN PROGRESS | None in current slice | Pending | Canonical lifecycle and scope rules recorded; formal sign-off remains |
| 1 — Authorization hardening | IN PROGRESS | None | Deployed 2026-11-24 | Central Project scope plus portfolio/detail/plan/task/assignment/handover/collaboration child-resource checks; Project scope cannot bypass authoritative Ticket visibility for history, links or referenced events; focused same/requested/unrelated department matrix passing |
| 2 — Lifecycle/intake | IN PROGRESS | `0295_project_lifecycle` | Deployed 2026-11-24 | Intake, canonical transition/history/versioning, execution/handover flow, notifications, hold/resume, residual closure and stabilization completion delivered; broader notification policy and legacy mapping remain |
| 3 — Profiles/membership | IN PROGRESS | None in current slice | No | Five least-privilege profiles are seeded but unassigned; engineer execute/blocker/evidence powers are assignment-scoped; the read-only legacy-holder preview reports candidate permission deltas. Approved per-user mappings, live seed/deployment and same-token withdrawal verification remain. |
| 4 — Role workspaces/navigation | NOT STARTED | None expected | No | Role UAT and accessibility |
| 5 — Project workspace/plan | NOT STARTED | TBD | No | Draft/version/evidence E2E |
| 6 — Handover/stabilization | NOT STARTED | TBD | No | Lifecycle prerequisite E2E |
| 7 — Analytics/hardening | NOT STARTED | TBD | No | KPI/recovery/release evidence |

## 12. Current stop point

**Current delivered slice:** Central Project access is now reused by portfolio, summary, detail, plan, assignment response, task execution and Support handover operations. Assignment decisions verify the requested department and Team. A permission-gated `/implementation-intake` workspace exposes department-scoped requests with Accept, Propose, Return and Reject actions. Focused authorization tests prove that unrelated departments cannot list or decide the request.

**Lifecycle slice delivered:** Migration `0295_project_lifecycle` adds Project and assignment-request versions plus append-only `project_status_transitions`. Generic Project patching no longer accepts status. Explicit transitions validate source/target, version and required reasons. Implementation intake decisions now advance the canonical Project lifecycle, increment versions, record history, and avoid duplicate department/team membership.

**Execution and handover slice delivered:** Task actions, worklogs and timers reject Projects that have not been accepted. First work advances `READY_FOR_EXECUTION -> IN_EXECUTION`; final approved eligible task advances `IN_EXECUTION -> DELIVERY_REVIEW`. Handover initialization, submission and Support activation now advance `HANDOVER_PREPARATION -> SUPPORT_REVIEW -> STABILIZATION` through the same audited lifecycle. Returned/rejected handovers return to preparation with a recorded reason.

**Closure slice delivered:** Lifecycle transitions now notify the Project Manager and intake owner with versioned deduplication. Project managers can place active Projects on hold with a required reason and resume to the last governed state. Residual handover work can be explicitly closed. Stabilization completion requires the planned end date, an active plan, zero open residual items, current Project version and exit-criteria notes before advancing to `COMPLETED`.

**Collaboration authorization slice delivered:** Project collaboration reads, request creation, request response, event publishing and ticket linking now require the centralized Project scope. Non-administrative request creators cannot spoof another requesting department. Responders and owners must belong to the requested department. Ticket implementation history returns only links/events from Projects authorized to the caller. Cross-department requests grant the requested department limited Project visibility while unrelated departments receive privacy-preserving `404` responses.

**Ticket authorization reconciliation delivered:** Implementation-history reads, ticket linking and ticket-referenced collaboration events now reuse the authoritative Ticket visibility query in addition to Project scope. A caller with legitimate Project collaboration access but no right to the Ticket receives privacy-preserving `404`; ticket-referenced events also enforce the Project/Client boundary. Sixteen focused Project tests pass. Backend-only deployment rollback: `D:\SupportHub\Release\backend\runtime.pre-ticket-authorization-20261124-231112`.

**Assignment inventory:** From `backend`, run `.\.venv\Scripts\python.exe -m scripts.preview_project_handover_profiles` against the configured database. The read-only JSON lists current holders, memberships, active profiles and effective permissions. On local `MillensysSupportHub`, all three active holders had company-wide Project access through their effective `project.manage` permission. The report flags each holder for manual mapping.

**Wave 3 profile slice delivered:** The five proposed r