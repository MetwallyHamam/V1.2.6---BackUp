# Implementation Department Collaboration — Engineering Plan

**Status:** Proposed for approval  
**Prepared:** 2026-11-23  
**System:** Millensys Support Hub  
**Primary owners:** Implementation, Support, Product, Security, QA, Operations

## 1. Objective

Build a governed Implementation workspace in which:

- Implementation manages client projects, phases, issues, planned tasks, unplanned tasks, engineer assignments, work logs, delivery evidence, UAT, and acceptance.
- Support can send a ticket to Implementation and follow its customer-relevant progress without seeing private Implementation information or KPIs.
- Implementation can create or link a Support ticket when project work affects a supported production environment or requires customer-facing Support handling.
- Both departments share an auditable cross-department history while retaining private departmental notes.
- Implementation users see only clients shared with their department and the projects/work authorized for them.
- Support users do not automatically gain access to Implementation engineer performance, internal costing, private discussions, or unrelated tasks.
- Sharing a client never grants access to all of that client's tickets, credentials, finance, or private departmental data.

## 2. Architectural principles

1. **Separate business records:** tickets, projects, issues, and tasks remain distinct.
2. **Explicit relationships:** use typed, auditable links; never infer cross-department access from matching text.
3. **Scope before presentation:** dashboards and navigation never grant access; backend authorization remains authoritative.
4. **Shared events, not copied comments:** cross-department history is recorded once with an explicit visibility level.
5. **Independent lifecycles:** resolving an Implementation issue does not automatically close a Support ticket.
6. **Independent clocks:** Support SLA and Implementation delivery targets are measured separately.
7. **Baseline integrity:** planned work belongs to an approved baseline; unplanned work records its cause, impact, and approval.
8. **Least privilege:** client sharing, ticket routing, project participation, and permissions are separate access dimensions.
9. **Evidence-based KPIs:** every metric drills into the exact authorized records used to calculate it.
10. **Reuse before duplication:** extend current Project Handover, Work Assignment, Deployment, UAT, notification, audit, and dashboard services where their contracts fit.

## 3. Target domain model

```text
Client
└── Client ↔ Department share
    └── Implementation Project
        ├── Project phases / milestones
        ├── Project issues
        │   ├── Linked Support tickets
        │   └── Shared/private events
        ├── Planned tasks
        │   └── Task assignees and work logs
        ├── Unplanned tasks
        │   ├── Cause, approval and impact
        │   └── Task assignees and work logs
        ├── Deployment plans / steps
        ├── UAT cycles / defects
        └── Client acceptance / handover
```

### 3.1 Record responsibilities

| Record | Purpose | Owner |
|---|---|---|
| Support Ticket | Customer request, production incident, SLA and communication | Support |
| Implementation Project | Delivery scope, baseline, phases, schedule, health and acceptance | Implementation |
| Implementation Issue | A delivery problem, risk, scope question, defect or requested change | Implementation |
| Project Task | Executable unit of work assigned to engineers | Implementation |
| Work Log | Engineer effort and activity evidence | Task assignee |
| Shared Event | Cross-department status/history entry | System or authorized actor |
| Deployment/UAT | Execution, verification and acceptance evidence | Authorized project participants |

## 4. Reuse and extension strategy

### 4.1 Reuse

- `ClientDepartmentLink` for authoritative client-to-department sharing.
- `ProjectHandover` as a source/intake and final handover record.
- `WorkAssignment` concepts for multiple assignees, contribution, status events, evidence, dates and effort.
- Deployment plan/step/issue models for controlled deployment execution.
- UAT cycle/test/defect models for validation and retest.
- Ticket timeline, notifications, outbox, audit logs and attachment security.
- Dashboard template/profile/department assignment and the central authenticated scope pattern.

### 4.2 Do not overload

- Do not treat `ProjectHandover` as the entire execution project; it lacks the complete baseline/task/issue model.
- Do not model every project task as a Support ticket.
- Do not use free-text pending points as the task system.
- Do not use generic `WorkAssignmentLink` alone as the authoritative ticket-to-issue relationship.
- Do not copy comments between tickets and projects.

## 5. Proposed persistence model

Names are provisional and must follow the repository's migration and SQL Server naming conventions.

### 5.1 `implementation_projects`

Core fields:

- `id`, `project_number`, `name`, `description`
- `client_id`, `department_id`
- `project_manager_user_id`, `created_by_user_id`
- `source_handover_id`, `contract_id` where applicable
- `status`, `priority`, `health`
- `planned_start_at`, `planned_end_at`
- `actual_started_at`, `actual_finished_at`
- `baseline_version`, `baseline_approved_at`, `baseline_approved_by_user_id`
- `progress_percent`, `client_acceptance_status`, `accepted_at`
- `version`, `created_at`, `updated_at`, `archived_at`

Constraints:

- Unique project number.
- Project client must be active or explicitly approved as historical.
- Project department must be Implementation-capable.
- Planned end must be after planned start.
- Completed project requires completion and acceptance evidence according to policy.

### 5.2 `implementation_project_members`

- `project_id`, `user_id`
- `role`: `PROJECT_MANAGER`, `LEAD`, `ENGINEER`, `REVIEWER`, `OBSERVER`
- `effective_from`, `effective_until`
- `created_by_user_id`, timestamps

Unique active membership per project/user/role as appropriate.

### 5.3 `implementation_project_phases`

- `id`, `project_id`, `code`, `name`, `description`, `display_order`
- `owner_user_id`
- `planned_start_at`, `planned_end_at`
- `actual_started_at`, `actual_finished_at`
- `status`, `progress_percent`, `version`

### 5.4 `implementation_issues`

- `id`, `issue_number`, `project_id`
- `title`, `description`, `issue_type`, `priority`, `status`
- `reported_by_user_id`, `owner_user_id`
- `planned_classification`: `PLANNED`, `UNPLANNED`, or `NOT_APPLICABLE`
- `source_type`, `source_reference`
- `business_impact`, `technical_impact`
- `blocked_reason`, `next_update_at`
- `resolution_summary`, `validation_summary`
- `resolved_at`, `validated_at`
- `version`, timestamps

Issue types should be governed master data or an approved stable enum: defect, risk, dependency, scope question, change request, data issue, integration issue, environment issue, client action, and other.

### 5.5 `implementation_project_tasks`

- `id`, `task_number`, `project_id`, optional `phase_id`, optional `issue_id`
- `title`, `description`, `expected_result`
- `classification`: `PLANNED` or `UNPLANNED`
- `status`, `priority`, `complexity`
- `owner_user_id`, `created_by_user_id`
- `planned_start_at`, `planned_end_at`, `due_at`
- `estimated_minutes`, `actual_minutes`, `progress_percent`
- `requires_review`, `reviewer_user_id`, `reviewed_at`
- `started_at`, `completed_at`, `cancelled_at`
- `client_visible`
- `version`, timestamps

For unplanned tasks also require:

- `unplanned_reason_code`
- `discovered_at`, `discovered_by_user_id`
- `schedule_impact_minutes`, `effort_impact_minutes`
- `approval_status`, `approved_by_user_id`, `approved_at`
- optional `related_planned_task_id`

### 5.6 `implementation_task_assignees`

- `task_id`, `user_id`
- `role`: `OWNER`, `CONTRIBUTOR`, `REVIEWER`
- `contribution_percent`, `assigned_at`, `removed_at`

Rules:

- Exactly one accountable active owner when the task is assigned.
- Execution contribution totals 100%; reviewers may be excluded from execution credit.
- Assignees must be active employees eligible for the project department.

### 5.7 `implementation_task_dependencies`

- `predecessor_task_id`, `successor_task_id`
- `dependency_type`: finish-to-start initially
- `lag_minutes`

Reject self-dependencies and dependency cycles.

### 5.8 `implementation_work_logs`

- `id`, `task_id`, `user_id`
- `work_date`, `started_at`, `ended_at`, `duration_minutes`
- `activity`, `billable_status`
- `approval_status`, `approved_by_user_id`, `approved_at`
- timestamps and version

Actual task effort is the sum of approved work logs. Duration must not be inferred from elapsed task time multiplied by assignee count.

### 5.9 `ticket_implementation_issues`

- `ticket_id`, `implementation_issue_id`
- `relationship_type`: `ORIGINATED_FROM_TICKET`, `RELATED`, `REQUIRES_SUPPORT`, `CAUSED_BY_IMPLEMENTATION`, `DUPLICATE`
- `linked_by_user_id`, `linked_at`
- `unlinked_by_user_id`, `unlinked_at`, `unlink_reason`

Use a filtered uniqueness rule to prevent duplicate active links.

### 5.10 `implementation_events`

- `id`, `project_id`, optional `issue_id`, optional `task_id`
- `event_type`, `actor_user_id`
- `visibility`: `IMPLEMENTATION_PRIVATE`, `CROSS_DEPARTMENT`, `CUSTOMER_VISIBLE`
- `summary`, structured `detail_json`
- `correlation_id`, `created_at`

Events are append-only. Corrections create a new event rather than rewriting history.

### 5.11 Attachments and evidence

Use a governed evidence entity linked to project, issue, task, work log, deployment or UAT. It must retain uploader, hash, size, MIME type, storage identifier, visibility, malware-scan state where available, and download audit.

## 6. Authorization and scope model

### 6.1 Project visibility

A user may view a project only if all applicable conditions succeed:

1. The client is shared with the user's department, or the user has an explicit approved organization-wide permission.
2. The user is a project member, belongs to the owning department with department-project view, or has project portfolio permission.
3. The project is not archived, unless archive permission is present.

### 6.2 Issue/task visibility

- Implementation members see authorized project issues/tasks.
- Support users see only issues linked to tickets they can already view, and only cross-department/customer-visible fields and events.
- Client Portal users see only explicitly customer-visible data through a separate response schema.
- A shared client alone never authorizes Support tickets or Implementation private work.

### 6.3 Proposed permissions

Implementation:

```text
implementation.project.view.own
implementation.project.view.department
implementation.project.manage
implementation.project.baseline.approve
implementation.issue.view
implementation.issue.manage
implementation.task.view
implementation.task.manage
implementation.task.assign
implementation.task.review
implementation.worklog.create
implementation.worklog.approve
implementation.history.view.private
implementation.report.view
implementation.report.export
dashboard.implementation
```

Cross-department Support:

```text
implementation.issue.send
implementation.issue.link
implementation.history.view.shared
implementation.issue.comment.shared
implementation.issue.request_update
```

Sensitive rights remain separate:

```text
implementation.cost.view
implementation.record.export
implementation.client.publish
```

Create dedicated `IMPLEMENTATION_USER` and `IMPLEMENTATION_MANAGER` profiles. Do not clone Support Manager or Administrator.

## 7. Complete workflows

## 7.1 Project intake and baseline

1. An authorized user creates a project from an accepted Project Handover, approved contract/delivery request, or authorized manual intake.
2. The client must be shared with Implementation before project activation.
3. The project manager adds members, phases, dates, deliverables and initial risks.
4. Planned tasks are created with owners, assignees, estimates, dependencies and expected results.
5. The system validates dates, dependency cycles, ownership, assignee eligibility and required fields.
6. The project manager submits the baseline.
7. An authorized approver accepts or returns the baseline with comments.
8. Approval increments `baseline_version` and records an immutable baseline snapshot.
9. Later tasks default to `UNPLANNED` unless added through a formal re-baseline workflow.
10. Notifications inform members that execution can begin.

## 7.2 Planned task execution

1. Task is created in the approved project plan.
2. Assigned engineers are notified.
3. The owner accepts the task.
4. Dependencies must be complete or explicitly waived before start.
5. Starting the task records actual start time.
6. Engineers add work logs, progress, comments and evidence.
7. A blocker moves the task to `BLOCKED` with reason, responsible party and next-review date.
8. Completion requires a completion summary and required evidence.
9. Review-required tasks move to `AWAITING_REVIEW`.
10. Reviewer approves or returns the task for rework.
11. Project/phase progress is recalculated from governed task weights or approved effort rules.

Task lifecycle:

```text
DRAFT → PLANNED → ASSIGNED → ACCEPTED → IN_PROGRESS
                                      ├→ BLOCKED → IN_PROGRESS
                                      ├→ ON_HOLD → IN_PROGRESS
                                      └→ AWAITING_REVIEW → COMPLETED

Any permitted non-terminal state → CANCELLED
COMPLETED → REOPENED/IN_PROGRESS only through audited action
```

## 7.3 Unplanned task workflow

1. Engineer or manager selects **Add Unplanned Task**.
2. They must provide cause, discovery source, project/issue, impact, estimate and requested dates.
3. The system records the active baseline version at discovery.
4. Based on policy thresholds, the task is either immediately authorized or enters `PENDING_APPROVAL`.
5. Approver can approve, reject, request information, or require a project re-baseline.
6. Approved work proceeds through the normal task lifecycle.
7. Rejected work remains in audit/history but cannot receive execution work logs.
8. Schedule and effort impact roll into project variance and unplanned-work KPIs.

Unplanned cause codes:

```text
CLIENT_REQUEST
TECHNICAL_DISCOVERY
SCOPE_GAP
DEFECT
DEPENDENCY
EMERGENCY
REWORK
MANAGEMENT_REQUEST
OTHER
```

## 7.4 Support sends a ticket to Implementation

1. Support opens an authorized ticket and selects **Send to Implementation**.
2. The dialog requires reason, requested action, business impact, priority and customer-safe context.
3. Support may select an accessible project or request Implementation triage.
4. The backend rechecks ticket scope and client sharing.
5. The service creates an Implementation issue or links an existing issue idempotently.
6. A `ticket_implementation_issues` link is created.
7. A cross-department event appears on both records.
8. The Implementation triage queue is notified.
9. Implementation accepts, rejects, marks duplicate, or requests more information.
10. If accepted, Implementation creates or links project tasks.
11. Shared progress events update the ticket's Implementation panel and timeline.
12. When work is ready, Implementation marks the issue `READY_FOR_VALIDATION`.
13. Support validates the customer-facing result.
14. Implementation resolves the issue; Support independently resolves/closes the ticket.

The ticket may use `PENDING_INTERNAL` when approved by the ticket workflow. SLA pause occurs only when the applicable governed SLA policy permits it and always records pause evidence.

## 7.5 Implementation requests Support assistance

1. Implementation opens an issue and selects **Request Support**.
2. It may link an existing authorized ticket or create a new ticket.
3. Creation requires client, ticket type, impact, urgency, product/service context and customer-safe description.
4. Normal ticket entitlement, approval, assignment and SLA rules execute; Implementation cannot bypass them.
5. The issue and ticket receive reciprocal typed links and shared events.
6. Support owns customer communication and Support resolution.
7. Implementation retains project/task ownership.

## 7.6 Information request workflow

1. Either department selects **Request Information** on the linked issue.
2. Request includes question, owner department/user, due time and visibility.
3. The linked record displays an actionable pending request.
4. Response resolves the request and records both messages as shared events.
5. Overdue requests appear in both departments' attention queues.

## 7.7 Issue completion and ticket validation

1. All blocking tasks must be completed, cancelled with approval, or explicitly waived.
2. Implementation records resolution, affected versions, deployment evidence and validation evidence.
3. Issue moves to `READY_FOR_VALIDATION`.
4. Support is notified when a ticket is linked.
5. Support records validation as accepted or failed.
6. Failed validation reopens the issue with reason and evidence.
7. Accepted validation permits Implementation issue resolution.
8. Support decides ticket resolution and customer closure independently.

## 7.8 Client sharing removal

1. Authorized manager requests removal of the client/department share.
2. The system previews active projects, tasks, issues and users affected.
3. Removal is blocked or requires an approved transition when active work exists.
4. On effective removal, project/client browsing disappears immediately for users relying only on that share.
5. Existing ticket-linked shared events remain visible to authorized ticket users as historical evidence.
6. Private project data remains inaccessible.
7. Audit records actor, reason, effective time and impact.

## 8. Status models

### Project

```text
DRAFT
PLANNING
BASELINE_REVIEW
READY
IN_PROGRESS
ON_HOLD
AWAITING_CLIENT
AWAITING_ACCEPTANCE
COMPLETED
CANCELLED
```

### Issue

```text
SUBMITTED
TRIAGE
INFORMATION_REQUIRED
ACCEPTED
IN_PROGRESS
BLOCKED
READY_FOR_VALIDATION
RESOLVED
REJECTED
DUPLICATE
CANCELLED
```

### Task

```text
DRAFT
PENDING_APPROVAL
PLANNED
ASSIGNED
ACCEPTED
IN_PROGRESS
BLOCKED
ON_HOLD
AWAITING_REVIEW
COMPLETED
REJECTED
CANCELLED
```

State transitions must be centralized in services, guarded with optimistic version checks, and recorded as append-only events.

## 9. API design

### Projects

```text
GET    /api/v1/implementation/projects
POST   /api/v1/implementation/projects
GET    /api/v1/implementation/projects/{id}
PATCH  /api/v1/implementation/projects/{id}
POST   /api/v1/implementation/projects/{id}/submit-baseline
POST   /api/v1/implementation/projects/{id}/approve-baseline
GET    /api/v1/implementation/projects/{id}/timeline
```

### Phases and members

```text
POST   /api/v1/implementation/projects/{id}/phases
PATCH  /api/v1/implementation/phases/{id}
POST   /api/v1/implementation/projects/{id}/members
DELETE /api/v1/implementation/projects/{id}/members/{user_id}
```

### Issues

```text
GET    /api/v1/implementation/issues
POST   /api/v1/implementation/issues
GET    /api/v1/implementation/issues/{id}
PATCH  /api/v1/implementation/issues/{id}
POST   /api/v1/implementation/issues/{id}/actions/{action}
POST   /api/v1/implementation/issues/{id}/events
```

### Tasks and work logs

```text
GET    /api/v1/implementation/tasks
POST   /api/v1/implementation/tasks
GET    /api/v1/implementation/tasks/{id}
PATCH  /api/v1/implementation/tasks/{id}
POST   /api/v1/implementation/tasks/{id}/actions/{action}
POST   /api/v1/implementation/tasks/{id}/work-logs
PATCH  /api/v1/implementation/work-logs/{id}
POST   /api/v1/implementation/work-logs/{id}/approve
```

### Ticket integration

```text
GET    /api/v1/tickets/{ticket_id}/implementation
POST   /api/v1/tickets/{ticket_id}/implementation/send
POST   /api/v1/tickets/{ticket_id}/implementation/link
DELETE /api/v1/tickets/{ticket_id}/implementation/links/{issue_id}
POST   /api/v1/implementation/issues/{issue_id}/support-ticket
POST   /api/v1/implementation/issues/{issue_id}/request-information
POST   /api/v1/implementation/issues/{issue_id}/validate
```

All mutation endpoints require idempotency where retries could duplicate issues, tasks, tickets, links, events or notifications.

### Dashboards/reports

```text
GET /api/v1/implementation/dashboard
GET /api/v1/implementation/dashboard/evidence
GET /api/v1/implementation/reports/projects
GET /api/v1/implementation/reports/tasks
GET /api/v1/implementation/reports/engineers
GET /api/v1/implementation/reports/variance
```

## 10. User experience

### 10.1 Navigation

Implementation profiles receive:

- Implementation Now
- Projects
- Tasks
- Issues
- Shared Clients
- Deployments
- UAT
- Implementation Dashboard
- Implementation Reports

Support profiles retain their existing navigation and receive only permitted cross-department actions/history.

### 10.2 Implementation Now

Provide:

- My tasks today
- Tasks to accept
- Overdue and blocked tasks
- Pending unplanned-task approvals
- Information requests
- Projects requiring updates
- Upcoming milestones
- Work logs awaiting submission/approval

### 10.3 Project workspace

Tabs:

1. Overview
2. Plan/Timeline
3. Phases
4. Tasks
5. Issues/Risks
6. Team and capacity
7. Work logs
8. Deployment
9. UAT
10. Documents/Evidence
11. Client updates
12. History

Views:

- List/table
- Kanban by task status
- Timeline/Gantt-style plan
- Calendar
- Engineer workload

### 10.4 Ticket Implementation panel

Show only shared fields:

- Project and issue identifiers
- Issue title, status, priority and classification
- Project manager/owning team
- Progress, blocker and next-update time
- Shared events
- Resolution and validation summary
- Approved evidence
- Actions: request update, add shared comment, validate, open authorized issue

### 10.5 Client profile

Add an **Implementation History** tab showing authorized projects, issues, ticket links, deployments, UAT, acceptance and customer-safe outcomes. Support users get read-only shared history; Implementation users receive actions according to permission and membership.

## 11. Dashboard and KPI contracts

### 11.1 Project KPIs

- Active projects
- On-track, at-risk and delayed projects
- Awaiting client action/acceptance
- Completed in period
- Milestones due/overdue
- Planned versus actual project duration

### 11.2 Task KPIs

- Total planned and unplanned tasks
- Planned completion percentage
- Unplanned task percentage
- Unplanned effort percentage
- Open, overdue, blocked and unassigned tasks
- On-time task completion
- Estimate-to-actual variance
- Rework/reopen rate

### 11.3 Engineer KPIs

- Active assigned effort
- Completed task count
- On-time completion percentage
- Planned versus actual effort
- Overdue owned tasks
- Blocked tasks
- Planned versus unplanned effort
- Review return/rework rate

Engineer KPIs must not combine Support ticket metrics unless a separately approved cross-functional KPI explicitly defines that behavior.

### 11.4 Formulas

```text
Planned completion % = completed planned tasks / eligible planned tasks × 100
Unplanned task % = unplanned tasks / all eligible tasks × 100
Unplanned effort % = approved unplanned work minutes / all approved project work minutes × 100
Effort variance % = (actual approved minutes - estimated minutes) / estimated minutes × 100
On-time completion % = completed tasks finished by approved planned end / completed tasks × 100
```

Define zero-denominator behavior, cancelled-task treatment, reopened-task treatment, time zone, date basis and historical attribution before implementation.

## 12. Notifications

Notify only actionable recipients for:

- Project membership and baseline approval/return
- Task assignment, acceptance, due-soon, overdue, blocked and review
- Unplanned task approval/return/rejection
- Ticket sent to Implementation
- Issue accepted/rejected/information requested
- Shared update and next-update breach
- Ready for validation and failed validation
- Work-log approval/return
- Client share removal impact

Use deduplication keys and transactional outbox delivery. Avoid notifying all department users indiscriminately.

## 13. Delivery phases and gates

### Phase 0 — Decisions and data contract

Approve:

- Project ownership and baseline authority
- Planned/unplanned classification and re-baseline policy
- Status transitions
- Task weighting/progress formula
- Work-log and approval policy
- Support SLA behavior while awaiting Implementation
- Shared/private/customer visibility rules
- Client sharing/removal behavior
- KPI formulas and manager sign-off

**Gate:** signed workflow, permission matrix, state machines, KPI dictionary and wireframes.

### Phase 1 — Security and project foundation

- Add profiles/permissions.
- Add project, member, phase and baseline persistence.
- Implement authoritative project/client/department scope service.
- Add project list/detail and member/phase management.
- Add migrations, compatibility registry and seed data.

**Gate:** unauthorized users cannot enumerate or manipulate projects; sharing add/remove tests pass.

### Phase 2 — Tasks, assignees and work logs

- Add planned/unplanned tasks, dependencies, multiple assignees and approvals.
- Add task state service, optimistic concurrency, evidence and events.
- Add work logs and actual-effort calculation.
- Deliver Implementation Now, task list, Kanban and task detail.

**Gate:** complete task lifecycle, concurrency, dependency, effort and authorization tests pass.

### Phase 3 — Issues and Support ticket collaboration

- Add issues and typed ticket links.
- Add Send to Implementation, Request Support and information-request workflows.
- Add shared visibility events and ticket Implementation panel.
- Add client Implementation History.
- Integrate notifications and ticket timeline.

**Gate:** end-to-end Support→Implementation→validation workflow passes without cross-scope leakage.

### Phase 4 — Deployment, UAT and acceptance integration

- Link project/issues/tasks to current deployment and UAT records.
- Surface readiness, defects, retest and acceptance evidence.
- Enforce completion gates based on approved business rules.

**Gate:** project completion cannot bypass required deployment/UAT/acceptance evidence.

### Phase 5 — Dashboard and reporting

- Build Implementation KPI query services using SQL aggregation.
- Add exact drilldown/evidence routes.
- Add profile+department dashboard templates.
- Add project, task, engineer, variance and client reports.

**Gate:** every KPI matches its authorized drilldown and approved comparison fixture.

### Phase 6 — Hardening and rollout

- Scale/performance tests on SQL Server.
- Accessibility, responsive, Arabic RTL and localization review.
- Export and attachment security tests.
- Migration rehearsal, backup/restore and rollback proof.
- Pilot one Implementation team and selected shared clients.
- Expand after observation and sign-off.

**Gate:** production readiness and pilot acceptance signed by Implementation, Support, Security, QA and Operations.

## 14. Testing strategy

### Unit and service tests

- State transition rules
- Scope resolver
- Baseline versioning
- Planned/unplanned rules
- Dependency cycle rejection
- Contribution validation
- Work-log aggregation
- KPI formulas
- Visibility redaction

### Authorization tests

- Unshared client denial
- Shared client without project membership
- Project member versus department manager
- Support ticket visibility without project visibility
- Linked issue shared fields versus private fields
- Manipulated project/client/user filters
- Export, evidence and attachment denial
- Share removal and effective dating

### Integration tests

- Project creation from handover
- Baseline approval and later unplanned task
- Multi-engineer task execution
- Support sends ticket to Implementation
- Duplicate retry creates one issue/link
- Implementation requests Support ticket
- Information request and overdue state
- Ready-for-validation, failed validation and rework
- Issue resolution without automatic ticket closure
- Deployment/UAT linkage

### Concurrency tests

- Two managers editing the same project/task
- Duplicate accept/start/complete actions
- Task completion while reassigned
- Baseline approval while plan changes
- Link/unlink races
- Work-log double approval

### Migration and SQL Server tests

- Clean migration to head
- Upgrade from populated current head
- Index and filtered-uniqueness behavior
- Rollback feasibility where supported
- Compatibility registry coverage
- Production-scale query plans and response budgets

### UI/UAT scenarios

- Desktop/tablet/mobile
- English and Arabic RTL
- Keyboard and screen-reader workflows
- Empty, loading, partial-error and denied states
- Large project/task lists
- Long names and descriptions
- Light/dark mode

## 15. Data migration

- Do not automatically convert all existing Work Assignments into project tasks.
- Offer an auditable mapping/import for selected Implementation assignments.
- Link existing Project Handovers as project sources where confidently matched.
- Convert structured handover pending points only after preview and owner approval; retain original text as provenance.
- Preserve historical deployment/UAT/ticket identifiers.
- Produce reconciliation totals and exception reports.

## 16. Observability and operations

Track:

- Project/task/issue creation and transition failures
- Authorization denials and suspicious filter manipulation
- Notification/outbox lag
- Overdue information requests
- KPI/drilldown mismatches
- Dashboard/query latency and row counts
- Attachment failures
- Migration and compatibility health

Provide operational tools to:

- Rebuild project progress
- Recalculate approved work-log totals
- Reconcile ticket/issue links
- Replay failed notifications idempotently
- Export a project audit package
- Diagnose scope for a selected user/project without impersonation

## 17. Rollback strategy

- Feature flags independently control Implementation Projects, Tasks, Ticket Collaboration and Dashboard.
- Disabling collaboration hides new mutation actions but preserves existing links/history.
- Never delete created projects, issues, tasks, work logs or audit evidence during rollback.
- Restore frontend/backend from immutable release backups.
- Database downgrade is used only when reviewed and safe; otherwise forward-fix behind disabled flags.
- Retain old Project Handover and Work Assignment workflows until migration acceptance is complete.

## 18. Acceptance criteria

The feature is complete when:

1. Implementation manages projects with phases, planned/unplanned tasks, multiple engineers, work logs and evidence.
2. Client sharing scopes Implementation access without exposing unrelated Support/finance/credential data.
3. Support can send a ticket to Implementation and see the complete shared issue history.
4. Implementation can request Support involvement without bypassing ticket entitlement or SLA rules.
5. Private events and fields remain inaccessible across departments and through direct API requests.
6. Issue resolution never closes a ticket automatically.
7. KPI totals match authorized drilldowns and approved formulas.
8. Sharing removal, user transfer and project membership changes revoke access immediately as designed.
9. Clean and populated SQL Server migrations pass.
10. Backup, restore, monitoring, rollback, accessibility, localization and production pilot evidence are approved.

## 19. Required business decisions before coding

1. Is every project created from a handover, or may Implementation create projects directly?
2. Who approves the baseline and unplanned work, and at what thresholds?
3. Can an approved unplanned task trigger a formal re-baseline?
4. How is project progress weighted: task count, estimated effort, milestones, or approved manual weighting?
5. Are work logs mandatory, and who approves them?
6. Which Implementation updates are shared with Support by default?
7. Can Support see engineer names or only the owning Implementation team/manager?
8. What ticket state is used while waiting for Implementation, and when may SLA pause?
9. Which deployment/UAT/acceptance evidence blocks project or issue completion?
10. What data is client-visible, and who approves publication?
11. How are billable and non-billable unplanned tasks handled?
12. How long are project, work-log, shared-event and attachment records retained?

## 20. Recommended first production slice

Limit the first release to:

- One Implementation department and manager profile
- Selected shared clients
- Projects, phases and planned/unplanned tasks
- Multiple assignees and work logs
- Support **Send to Implementation**
- Shared issue history in the ticket
- No automatic client-portal publication
- No cost/billing functionality
- Dashboard limited to project/task/variance KPIs with exact drilldowns

This slice delivers the core collaboration value while keeping financial, client-publication and advanced scheduling risks outside the initial deployment.
