# Project Management implementation tracker

Updated 2026-11-25. This tracker covers the remaining Project Management work and the handoffs to Implementation and Support.

The [Project Delivery Implementation Plan](PROJECT_DELIVERY_IMPLEMENTATION_PLAN.md) tracks the next phase across Project Management, Implementation, and Support. Keep the existing PM items here for their detailed deployment and acceptance evidence.

## Delivered and deployed locally

- [x] Dedicated Project Management profile and project workspace.
- [x] Work Packages list and shareable task and milestone details.
- [x] Draft milestone date and task predecessor edits with version checks and audit history.
- [x] Schedule baselines, predecessor visibility in the Gantt table, and baseline variance in the revision queue.
- [x] Published milestone proposals, approval by a separate reviewer, rejection, and decision history.
- [x] Project intake decision history, links to the filtered Implementation inbox, and Support handover access.
- [x] Local IIS deployment and smoke checks. The new frontend build was served, the protected routes returned HTTP 401 without a session, and database revision `0296_project_templates` reported compatible. Rollback stamp `20261125-022620`.

## Remaining work

| ID | Status | Work item | Completion check |
|---|---|---|---|
| PM-01 | Open | Run the signed-in IIS walkthrough against the current deployment. | A Project Manager publishes a test project, Implementation accepts and executes it, and a Support reviewer decides the handover. Verify that the designated activation role can activate Support and that cross-project and out-of-role actions are denied. Record role, result, and evidence for each step. |
| PM-02 | Implemented, IIS verification open | Add draft task schedule editing to Work Packages. | A scoped Project Manager can change planned start and finish. Validate project and phase windows, predecessor timing, and stale versions. Verify that Work Packages and Schedule show the same dates after saving. |
| PM-03 | Implemented, IIS verification open | Extend published-plan revisions to task dates and dependencies. | Proposals require a reason and show the old and proposed plan. A separate reviewer can approve or reject. Approval applies the change atomically, preserves the baseline, and rejects stale proposals, cycles, and invalid dates. The revision queue shows both milestone and task revisions. |
| PM-04 | Implemented, IIS verification open | Add a project risk and change register. | Project-scoped viewers can read entries. The project manager can record risks and changes and is the initial owner. A company-wide Project Management reviewer records decisions, with a separate reviewer required for a change. Approved changes can link to a revision in the same project. |
| PM-05 | Open | Verify the completed workflow on IIS. | Deploy the tested build with rollback copies. Repeat PM-01 and add signed-in checks for task revisions, baseline preservation, and risk/change visibility across Project Management, Implementation, and Support. Depends on PM-02 through PM-04. |
| PM-06 | Deployed, signed-in verification open | Resubmit proposed or returned Implementation intake. | The project manager revises the delivery window and adds a reason. The original decision remains visible. Implementation receives a new pending request and can accept it to open execution. |

## Working order

PM-02 implementation includes version-checked draft edits and invalidation of both task views after saving. Automated coverage checks a successful schedule change, a stale save, and a dependency overlap. [Project execution tests](../../../backend/app/tests/test_project_execution.py)

PM-03 automated coverage approves task schedule and predecessor proposals with a separate reviewer. PM-04 automated coverage checks project isolation, reviewer permission, same-project revision linkage, and duplicate decisions. [Portfolio tests](../../../backend/app/tests/test_project_portfolio.py)

PM-02 through PM-04 are deployed on local IIS. Work Packages, Schedule Revisions and Risks and Changes returned HTTP 200. The register API returned HTTP 401 without a session. Database health reported compatible at `0296_project_templates`. Rollback stamp `20261125-024239`.

Run the signed-in PM-01 and PM-05 walkthroughs with designated local test accounts for each role. Use a test project and record the result of each workflow and denial check.

### Signed-in acceptance evidence

PM-06 was deployed to local IIS with rollback stamp `20261125-205208`. My Project Work, Project Intake, and the Implementation inbox served the updated build. Backend and database health passed at `0296_project_templates`. The local role inventory found no active assignments to the dedicated Implementation Manager, Implementation Engineer, or Support Handover Reviewer profiles. Designated test accounts or approved temporary role assignments are needed for signed-in acceptance.

The handover permission update is deployed on local IIS with rollback stamp `20261125-124307`. Automated tests verified that review-only users cannot accept or conditionally accept a handover. Both IIS health endpoints and the project workspace smoke routes returned HTTP 200.

| Role | Check | IIS evidence |
|---|---|---|
| Project Manager | Publish a test project and submit an Implementation request. The intake decision appears in the project workspace. | Pending |
| Implementation | Accept the request, execute the assigned work, and confirm that the project reaches delivery review. | Pending |
| Support reviewer | Submit a review. A review-only account receives HTTP 403 for both acceptance decisions. | Pending |
| Support acceptor | Accept the reviewed handover. Activation requires its own permission. | Pending |
| Support activation owner | Activate only when acceptance and stabilization requirements are satisfied. | Pending |
| Project Manager and separate plan reviewer | Approve a proposed task change, verify the saved baseline is unchanged, and link an approved register entry to its revision. | Pending |

When moving an item to **In progress**, record the owner. Mark it **Done** when its completion check passes and add a link to the test, deployment record, or acceptance evidence.

Related roadmap: [Unified Collaboration Workspaces Enhancement Plan](UNIFIED_COLLABORATION_WORKSPACES_ENHANCEMENT_PLAN.md).

## Project Management UX and feature roadmap

Updated 2026-11-26. This roadmap extends the delivery workflow already in SupportHub. Each item has an implementation status and a completion checkpoint. Use the earlier tracker entries and the delivery plan for existing release evidence.

### Starting point

- **Live on local IIS** — Project Portfolio, planning backlog, Calendar/Gantt, Product Timeline, Implementation Queued projects, and the intake acceptance fix.
- **Implemented in the workspace** — Project editing, template authoring and versioning, reuse with project-specific changes, and Save as template in the wizard. These changes still need a local IIS deployment and signed-in walkthrough.
- **Open** — The roadmap items below. Each builds on the existing project, role, scheduling, intake, and handover records.

### Implementation sequence

| ID | Status | Work item | Depends on | Stop point |
|---|---|---|---|---|
| PMX-00 | Deployed, walkthrough open | Confirm the starting workflow. Deploy the pending edit and template changes, inventory the current routes and permissions, and run a signed-in walkthrough using local test accounts and a test project. | Existing work | Record a working route and role matrix, identify any release blockers, and capture the baseline from project creation through Support handover. |
| PMX-01 | Partially deployed | Unify the project workspace. Use one full-width header and four sections: Overview, Plan, Delivery, and Handover. Keep existing deep links working. Surface project number, customer, accountable owner, milestone, and primary action. Consolidate filter layouts, status styles, and quick-review panels. | PMX-00 | Each role can find its landing queue, open the same project, and reach its next authorized action. Verify deep links, mobile navigation, keyboard focus, and light/dark themes. |
| PMX-02 | Partially deployed | Build the Project Action Center. Bring drafts, returned intake, approvals, blocked tasks, overdue milestones, and handover actions into a filterable queue. Include owner, due date, reason, and direct action. Add saved filters and dashboard drill-downs using the same scope rules. | PMX-01 | Every test item opens the correct record and leaves or updates the queue after an action. Users see only authorized items and counts. |
| PMX-03 | Partially deployed | Add stage readiness to the project overview. Show required items, missing information, next owner, and links to resolve gaps. Cover publish, intake review, delivery acceptance, and handover. Use the same rules for UI guidance and server validation. | PMX-01 | Complete projects can advance through each stage. Incomplete projects show the exact missing requirement, and direct API calls enforce the same rules. |
| PMX-04 | Partially deployed | Extend milestone and change control. Surface approved dates, current forecasts, and variance in Plan and the portfolio. Connect change requests to affected milestones and tasks, show dependency impact, and preserve the existing approval history. | PMX-01 | A test revision shows baseline versus forecast, routes to the authorized reviewer, and updates Schedule and Work Packages together when approved. Rejected and stale proposals preserve the approved plan. |
| PMX-05 | Implemented, verification open | Build Implementation capacity planning. Show accepted projects awaiting a team, planned workload by team and week, availability, and conflicts. Link directly to team assignment and intake review. | PMX-02, PMX-04 | Assigning work updates the relevant queue and workload. Overbooking is visible before a delivery date is confirmed. Capacity changes and cross-department visibility are tested with scoped roles. |
| PMX-06 | Open | Enhance the template library. Add department sharing, ownership and publish permissions, version previews, and selection of phases to copy. Keep the project wizard's Save as template action and default tasks. | PMX-00, PMX-01 | A manager can preview and reuse approved phases, modify the copied tasks, and publish an authorized new version. Historical versions and unrelated projects retain their original plans. |
| PMX-07 | Open | Add customer acceptance and sign-off. Define acceptance criteria during planning, connect UAT results and evidence, and record the sign-off decision, signer, date, and open exceptions. | PMX-03 | A designated reviewer can verify criteria, evidence, and the sign-off history. Conditional acceptance carries exceptions forward with owners and due dates. |
| PMX-08 | Open | Consolidate Support handover and stabilization. Show sign-off, training, open issues, evidence, support owner, stabilization dates, and activation status in one checklist. | PMX-03, PMX-07 | Implementation submits a complete handover; Support can accept, return, or conditionally accept it under existing permissions. Activation is audited and unresolved items stay visible through stabilization. |
| PMX-09 | Open | Add cross-project and cross-department dependencies. Link a task or milestone to work in another authorized project, show blocking status in My Work and Gantt, and record the dependency owner. | PMX-04 | A linked blocker appears in both authorized workflows. Cycle validation works, and restricted project details remain protected. |
| PMX-10 | Open | Add portfolio prioritization. Turn the planning backlog into a reviewable ranked queue with urgency, customer commitments, effort, dependencies, and ranking rationale. Connect ranking to Implementation readiness and capacity. | PMX-05, PMX-09 | Managers can rank and filter projects, see the reason for each ranking, and distinguish approved priorities from tentative delivery dates. |
| PMX-11 | Open | Add weekly status reporting and dashboard drill-downs. Generate a snapshot of milestones, upcoming commitments, blockers, decisions, and handover readiness. Let managers add commentary and export a shareable report. | PMX-02, PMX-04, PMX-08 | A report for a fixed period reconciles with its source records. Repeat exports preserve the recorded snapshot and respect project visibility. |
| PMX-12 | Open | Verify and release the full workflow on local IIS. Exercise Project Manager, Implementation Manager/Engineer, and Support Reviewer/Activator journeys with separate test accounts. | PMX-01 through PMX-11 | Record build and database checks, signed-in walkthrough results, permission denials, and regression results. Store rollback copies on D: and document the rollback location. |

### Delivery checkpoints

1. **Workspace foundation** — Complete PMX-00 through PMX-03. Walk a project manager through creating a client, reusing a template, editing the plan, publishing, and finding the next action.
2. **Planning and commitments** — Complete PMX-04 through PMX-06. Walk Implementation through reviewing intake, confirming capacity, assigning an engineer, and handling a schedule change.
3. **Acceptance and Support** — Complete PMX-07 and PMX-08. Verify acceptance evidence, sign-off, Support activation, and ownership of remaining issues.
4. **Portfolio controls and release** — Complete PMX-09 through PMX-12. Verify dependency visibility, ranked backlog decisions, and weekly reporting before final sign-off.

For each item, record the status, changed routes and permissions, tests run, evidence, and deployment or rollback location where applicable. Move an item to **Complete** once its stop point is verified. Record **Implemented** or **Deployed** separately when signed-in acceptance is still open.

**First work item** — PMX-00. Once the current release and role boundaries are verified, start PMX-01 and PMX-02 together so the new navigation and action queue support the same day-to-day workflow.

### 2026-11-26 implementation evidence

- **PMX-00** — Project editing and template changes passed project portfolio and template regression tests. Local IAM confirmed that Projectuser can edit assigned projects and cannot respond to Implementation intake. impuser can respond to Implementation intake and lacks assigned-project edit permission. Support has active reviewers and activators. The first IIS rollout restored the prior release after its backend startup check timed out. The retry increases the cold-start timeout for backend health to 55 seconds.
- **PMX-01** — The project workspace now uses Overview, Plan, Delivery, and Handover sections, with the existing view URLs and permission checks. The header shows customer and manager when available and links to stage-relevant work. Responsive, theme, and signed-in role walkthroughs remain open.
- **PMX-02** — My Project Work includes an Action Center for drafts, intake responses, schedule decisions, blocked tasks, overdue milestones, and handover review. Items show the project, owner, due date when available, and a deep link. The API regression test verified an assigned manager receives an overdue milestone. Saved filters, dashboard drill-downs, and signed-in action completion remain open.

| Role | Entry point | Permission and scope to verify |
|---|---|---|
| Project Manager | /project-my-work and /projects/{id} | Project workspace access, portfolio visibility, and project.manage.assigned for edits to the project they manage. |
| Implementation Manager | /implementation-intake?view=queue | project.assignment.respond and the requested department for intake review and acceptance. |
| Implementation Engineer | /implementation-workspace and /projects/{id}/execution | Implementation workspace access and the corresponding task permissions. Verify assignment and project scope. |
| Support Reviewer / Activator | /support-handover-inbox | handover.review for the inbox; handover.accept and handover.activate_support for their respective decisions, subject to handover scope. |

The IIS retry passed on 2026-11-26 with rollback stamp 20261126-153734. Project editing, wizard template actions, the four-section project workspace, and the initial Project Action Center are in the deployed build. The rollout passed frontend asset and route checks plus backend and database health at revision 0297_project_wizard_drafts. The backend regression suite passed 10 tests. A direct authenticated request using workspace settings returned HTTP 401 against IIS, so signed-in acceptance remains open. No delivery records or account assignments were changed by the deployment checks.

### Follow-up verification

- **PMX-00** — Signed in on local IIS using the designated Implementation test account. The intake inbox returned HTTP 200. Project Templates returned HTTP 403. The full Project Management, Implementation, and Support mutation walkthrough remains open.
- **PMX-02** — The Action Center remembers its selected filter per account and accepts a filter in the URL. Project Management analytics links directly to the Schedule queue. Verify those controls and action completion during the signed-in browser walkthrough.
- **PMX-03** — Delivery review shows open task count, shared evidence availability, and eligibility to submit. The read view and submission use the same task and evidence rules. Handover submission checks every required item, so a rounded percentage cannot allow an incomplete checklist. The complete stage-by-stage readiness overview remains open.
- **Regression evidence** — All 15 tests across execution, support handover, and project portfolio passed, including the delivery readiness API check.
The follow-up release passed IIS and database checks, and the designated Implementation account received HTTP 200 from the deployed delivery readiness endpoint for project 3. Rollback stamp 20261126-154314. PMX-04 through PMX-12 remain open.
- **PMX-04** — Schedule now shows baseline and forecast finish variance, a Milestones only view, direct dependents, and work package links. TypeScript, the production build, and three focused frontend tests passed. The schedule route and IIS health checks passed with rollback stamp 20261126-154838 on D:. Portfolio variance, broader change-impact visibility, and signed-in revision acceptance remain open.
- **PMX-05** — Implementation Workspace now includes an eight-week, department-scoped capacity forecast based on active team membership and unfinished task estimates. It highlights overloaded team-weeks, lists accepted projects without a team, and links back to the intake assignment queue. Scoped API regression, frontend build, and signed-in IIS verification remain open.
