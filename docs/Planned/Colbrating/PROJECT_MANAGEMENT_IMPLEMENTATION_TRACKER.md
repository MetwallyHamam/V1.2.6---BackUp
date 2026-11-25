# Project Management implementation tracker

Updated 2026-11-25. This tracker covers the remaining Project Management work and the handoffs to Implementation and Support.

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

## Working order

PM-02 implementation includes version-checked draft edits and invalidation of both task views after saving. Automated coverage checks a successful schedule change, a stale save, and a dependency overlap. [Project execution tests](../../../backend/app/tests/test_project_execution.py)

PM-03 automated coverage approves task schedule and predecessor proposals with a separate reviewer. PM-04 automated coverage checks project isolation, reviewer permission, same-project revision linkage, and duplicate decisions. [Portfolio tests](../../../backend/app/tests/test_project_portfolio.py)

PM-02 through PM-04 are deployed on local IIS. Work Packages, Schedule Revisions and Risks and Changes returned HTTP 200. The register API returned HTTP 401 without a session. Database health reported compatible at `0296_project_templates`. Rollback stamp `20261125-024239`.

Run the signed-in PM-01 and PM-05 walkthroughs with designated local test accounts for each role. Use a test project and record the result of each workflow and denial check.

### Signed-in acceptance evidence

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
