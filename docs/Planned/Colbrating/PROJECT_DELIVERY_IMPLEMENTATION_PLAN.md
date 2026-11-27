# SupportHub project delivery implementation plan

**Updated:** 2026-11-25, Africa/Cairo  
**Current stop point:** PD-03 workspace grants are implemented in source and previewed against the local profile inventory. PD-05 now captures an agreed schedule baseline on intake acceptance. PD-07 has a receiving-department handover inbox in source. Resume with grant rollout and signed-in checks once pilot roles are designated. PD-02 still requires a delivery sign-off decision.

## Target structure

Use one SupportHub application, one customer hierarchy, and one shared Project record. The shared shell keeps profile, themes, language, and notifications. Each workspace has its own navigation and work queue.

| Workspace | Route | Responsibility |
|---|---|---|
| Project Management | Existing `/project-workspace` and `/project-my-work` | Create department-owned clients, draft and publish plans, agree delivery terms, track commitments, and raise changes. |
| Implementation | New `/implementation-workspace` in source. Existing `/implementation-intake` remains available. | Review requests, accept delivery terms, assign and execute work, and submit delivery evidence. |
| Support | Existing `/support-workspace`. Add a handover queue within it. | Review readiness, accept or return operational handover, activate Support, and track stabilization obligations. |
| Shared project | Existing `/projects/:id` | Keep one source of truth for Plan, Deliver, and Hand Over. Deep links open the appropriate project view. |

Default workspace and available switches follow effective permissions. A single-workspace user sees their own workspace. Multi-role users can switch between authorized workspaces. The backend independently enforces action permissions and record scope. Preserve deployed routes, including `/project-management`, and the IIS `/SupportHub/` base path.

## Dedicated profiles, pages, and workflow permissions

Give each workspace a dedicated access permission. Use it for landing-page selection, menu visibility, workspace switching, and direct-route guards. A shared project permission such as `implementation.task.view` can allow an authorized project view without granting access to the Implementation Workspace. Keep profile, password, theme, language, and authorized notifications available through the shared shell.

| Profile | Workspace grant | Dedicated pages and queues | Workflow grants to verify |
|---|---|---|---|
| `PROJECT_MANAGER` | Proposed `workspace.project_management.access` | Project Workspace, My Project Work, Portfolio, Templates, and the scoped Add Client flow | Create department-owned clients, create and publish plans, manage assigned projects, submit or revise intake, propose plan changes, and prepare or submit handover where authorized. |
| `IMPLEMENTATION_MANAGER` | Proposed `workspace.implementation.access` | Implementation Workspace, Intake, Team Delivery, and Delivery Attention | Decide intake for the receiving department, coordinate assignment, review work, approve unplanned work within the delivery scope, and submit the delivery package under PD-06. |
| `IMPLEMENTATION_TEAM_LEADER` | Proposed `workspace.implementation.access` | Implementation Workspace, Team Delivery, blockers, and review queues | Assign or review work within the authorized team. Grant intake decisions or unplanned-work approval separately if the approved workflow assigns those responsibilities. |
| `IMPLEMENTATION_ENGINEER` | Proposed `workspace.implementation.access` | Implementation Workspace and My Assigned Tasks | Execute assigned work, record blockers, evidence, and time, and submit work for review. |
| Existing Support engineer profiles | Preserve existing Support access during rollout | Support Workspace and existing ticket tools | Preserve existing ticket rights. Add handover actions only through an explicitly granted Support permission. |
| `SUPPORT_HANDOVER_REVIEWER` | Authorized Support handover access | Support Handover Inbox and assigned readiness packages | Review, return, or reject within receiving scope. Acceptance requires `handover.accept`; activation requires separate `handover.activate_support`. Audit the reviewer bundle against the approved division of responsibility. |
| Designated delivery acceptor | To be decided in PD-02 | Delivery acceptance queue or authorized project acceptance view | Accept or return the submitted project version with evidence. Delivery acceptance does not grant Support acceptance or activation. |

The matrix describes intended responsibilities. During implementation, inventory the actual seeded permission codes and backend guards. Record what each role gains, retains, or loses before approving profile changes. Until PD-02 is approved, leave delivery acceptance and exception-waiver grants undecided.

For shared `/projects/:id` pages, show only authorized sections and actions. Use department, team, project, or task assignment checks as applicable. On direct links, render the authorized shared view or the appropriate denied state. For multiple workspace grants, show only the explicitly granted choices and retain the selected default when it remains authorized. Route and menu checks do not replace API authorization.

### PD-03 implementation and verification checklist

- [ ] Inventory current profile assignments and build the profile-to-page and profile-to-action matrices against the implemented API routes.
- [ ] Seed the dedicated workspace permissions and map them to existing profiles. Review effective grant deltas and validate single-role and multi-role test accounts before rolling out assignment changes.
- [ ] Wire landing pages, navigation, workspace switching, and deep-link guards to the same workspace grant checks. Keep legacy links and the IIS base path working.
- [ ] Match action visibility and API authorization for client creation, plan publication, intake decisions, task assignment and execution, delivery acceptance, and Support handover. Confirm record scope separately from action permissions.
- [ ] Verify each role can complete its own workflow and is denied out-of-role actions and out-of-scope records. Check that withdrawing a workspace grant removes the landing choice and direct-route access and that existing Support ticket flows still work.
- [ ] Record the tested profile, page, action, role scope, outcome, and build or rollback stamp. Update the PD-03 stop point before handing off.

## Status rules

Use **Open**, **In progress**, **Blocked**, **Deployed — acceptance open**, or **Done**. For every step, record owner, evidence, and where to resume. Mark a step Done only after its completion check passes. For an IIS sign-off, record the build or rollback stamp and the roles tested.

| ID | Status | Owner | Step and completion check | Stop point or resume instruction |
|---|---|---|---|---|
| PD-00 | Done — deployment baseline | Engineering | Existing planning, implementation intake, and handover capabilities were deployed and smoke-tested on local IIS. | Baseline recorded in the [Project Management tracker](PROJECT_MANAGEMENT_IMPLEMENTATION_TRACKER.md). Intake deployment rollback stamp `20261125-205208`, database revision `0296_project_templates`. Begin PD-01. |
| PD-01 | Blocked — test accounts | QA and department leads | Walk one synthetic project through the current deployment as separate Project Manager, Implementation, and Support users. Record successful actions, denied actions, and where each user gets stuck. Covers PM-01. | No designated Implementation or reviewer accounts have been confirmed. Resume by identifying existing test accounts or approving temporary local accounts. Record project ID and role-by-role evidence. |
| PD-02 | Open — workflow decision | Project Management, Implementation, Support | Agree who can sign delivery acceptance, whether client signature is required, which evidence is mandatory, who may waive an exception, and what blocks closure. Approve the role/action matrix and state transitions. | Stop at approved rules and acceptance scenarios. Resume PD-03 and PD-06 using that decision. If an in-app approval is sufficient, define the identity, scope, version, timestamp, and decision evidence it must capture. |
| PD-03 | In progress | Engineering | Implement the dedicated profile, page, and workflow permission matrices. Consolidate routing, default landing, workspace switching, and compatibility redirects. Verify direct URLs, notifications, and the IIS base path. | Seed definitions and route/navigation checks are in source. Resume with a local grant preview, seed/deploy, and signed-in matrix. Multi-role users can reach both granted workspaces from navigation. A persistent default workspace switch and full workflow permission audit remain open. |
| PD-04 | In progress | Project Management and Engineering | Deliver resumable drafts and a publish checklist for customer, scope, schedule, owners, and evidence. Build My Project Work queues for returned intake, schedule decisions, and delivery risk. Reuse existing client creation and intake resubmission. | Server-side drafts and the publish readiness checklist are implemented. The review screen links back to incomplete sections and blocks full submission until required checks pass. Resume with the expanded action queues and signed-in acceptance. Migration `0297_project_wizard_drafts` is required before IIS rollout. |
| PD-05 | In progress | Implementation and Engineering | Build the Implementation Workspace with Intake, My Tasks, Team Delivery, Blockers, and Ready for Review. On intake acceptance, record the agreed scope, dates, team, and immutable approved baseline. Link to the relevant shared project views. | Team Delivery shows accepted projects, team, agreed dates, and progress. Intake decision-makers see their department's delivery portfolio. Team assignees see their authorized teams. The agreement snapshot includes project branches, products, modules, and planned item dates. Resume with assignment planning actions and the PD-06 delivery submission workflow. |
| PD-06 | In progress | Delivery acceptor and Engineering | Add delivery acceptance as a distinct workflow. Implementation submits completion evidence. The designated acceptor can accept or return the package with a reason. Bind the decision to the reviewed project version and evidence. | Delivery submission is implemented in source. It requires completed tasks and shared evidence, records the reviewed project version, and rejects duplicate submissions. Resume with the acceptance and return actions after PD-02 defines the sign-off authority. |
| PD-07 | In progress | Support and Engineering | Add a Support Handover Inbox. Reuse the existing review, conditional acceptance, activation, and stabilization capabilities. Surface evidence, owner, due dates, and outstanding obligations. Enforce agreed acceptance and closure gates on the backend. | Project Managers can route a handover to its receiving department before submission. That department sees it in the inbox and can review it with the appropriate grants. Routing is locked once Support review begins. Resume with the acceptance and closure gates from PD-02. |
| PD-08 | Open | QA and Operations | Deploy and verify the full workflow on local IIS. Repeat the pilot using separate roles and cover schedule revisions, baseline preservation, risk/change links, permissions, mobile navigation, and Support ticket regression. Covers PM-05. | Stop at documented local acceptance, including rollback stamp, verified routes, and remaining exceptions. Treat production rollout as a separate release decision. |

## Acceptance scenarios

- **Negotiated delivery:** Create a test client, save and resume a draft, publish, receive an Implementation proposal or return, revise and resubmit, and accept the final delivery plan. Retain the original decisions and lock the agreed baseline.
- **Delivery and acceptance:** Execute assigned work, submit evidence, return an incomplete package, and accept the corrected version. Capture the approver, decision, project version, evidence, and timestamp.
- **Operational handover:** Support reviews the accepted delivery, conditionally accepts with named owners and due dates, activates only after prerequisites pass, and completes stabilization before project closure.
- **Permissions and regressions:** Test cross-project denial, stale or duplicate actions, role-only workspace access, existing Support ticket workflows, retained deep links, and audit history.

## Checkpoint entry

**PD-05 task owner assignment:** Delivery coordinators and accepted team leaders can change the accountable owner of unstarted tasks from Work Packages. The API validates the receiving department, accepted team, eligible employee, and expected previous owner. The portfolio workflow test covers ineligible, successful, and stale reassignment. The feature is in source and awaits local IIS verification.

**PD-07 reviewer notifications:** Handover submission notifies active, authorized reviewers in the selected receiving department. Submission and decision notifications now link directly to the project's Support Handover view. The routing test verifies the notification and deep link. The change is in source and awaits local IIS verification.

**PD-07 receiving scope:** For routed handovers, Support review, activation, and stabilization closure require both the action permission and receiving-department scope. Company-wide project administrators retain their existing override. Regression coverage verifies that a collaborating department can view the project while activation and closure are denied. The change awaits local IIS verification.

**PD-03 workspace selection:** Multi-role users can switch authorized workspaces from the account menu. The choice is saved per account on the current browser and is ignored when its grant is withdrawn. Existing deep links take priority over the login preference.

**PD-04 action queues:** My Project Work now includes Returned Intake, Schedule Decisions, and Delivery Risk filters. Pending revision counts are limited to the signed-in manager's projects and visible revision types. The queues link to the relevant project view.

**PD-03 dashboard access:** Both workspace landing pages link to their dashboard when the user's analytics permission is present. Chart rows and KPI cards use the same evidence drilldown. The local `impuser` account holds the dedicated **Impelemntation** profile. Signed-in HTTP checks on the current release returned 200 for Implementation analytics and 403 for Project analytics. The updated UI and analytics rules remain in source.

**Project Dashboard schedule exceptions:** Managers can open late or overdue projects from their own schedule drilldown. Executive viewers retain the at-risk portfolio list. Both lists link to the corresponding project schedule.

**Local IIS rollout — 2026-11-25:** The current delivery workspaces, dashboards, server drafts, and handover routing are deployed. SQL Server backup `D:\SupportHub\DB\MillensysSupportHub_pre_0297_20261125-221853.bak` passed checksum verification before migration `0297_project_wizard_drafts`. Frontend and backend rollback copies are under `D:\SupportHub\Release` with stamp `20261125-221853`. IIS served the new build and reported a compatible database. The targeted grant seed preserved existing user assignments.

**Signed-in evidence:** On the new build, `impuser` received HTTP 200 for Implementation analytics, intake, my tasks, and Team Delivery. Project analytics and the Support Handover Inbox returned HTTP 403. This covers the Implementation access checks. PD-01 and PD-08 still need the full walkthrough with Project Management, Implementation, and Support role accounts. PD-02 still needs the delivery sign-off authority and evidence decision.

Copy this block below after each work session. Keep the current stop point at the top aligned with the latest verified checkpoint.

```text
Step ID and status:
Owner:
Completed:
Evidence and deployment or rollback stamp:
Pending or blocked:
Exact next action:
```
