# Implementation handoff — 2026-09-21

**Status: Completed and release verified.** The original requirements follow this note as the implemented scope.

**Latest enhancement:** The UAT experience now starts with a four-step client/template/assignment/review wizard. Reusable templates can be assigned to multiple clients, exported as portable workbooks with embedded cases and steps, and imported without preloading their library cases. Test execution uses a ticket-style list or drag-and-drop board and opens the selected test in an action drawer. Controlled board moves preserve execution, defect and retest rules. The latest UAT schema migration is `0222_uat_template_clients`.

Implemented so far: UAT test library and versioned checklists; cycle creation and test assignment; internal PASS, FAIL and BLOCKED attempts; defect ticket creation and retesting; cycle board, list and dashboard; internal sign-off; and published, client-scoped portal cycles with assigned client test execution. Internal and client results are stored separately. An assigned client approver can approve, reject or request additional testing; client approval gates internal sign-off when enabled. Internal/client comments and evidence have visibility controls; linked internal defect tickets expose UAT evidence. The portal has Active UAT, My Tests and Completed UAT tabs, guarded linked-ticket access and an optional client failure-to-ticket action with duplicate protection. Managers have a portfolio with an attention panel, activity feed, presentation mode, CSV export and expiring, revocable aggregate-only tracking links. Excel test case import validates all rows and skips duplicate codes. Cycle tests support bulk owner, due-date, priority and ready-state changes, plus selected-test CSV export. Personal saved views and Failed/Overdue filters are present. Test case and checklist duplicate/archive APIs and UI actions are present. Checklist test order can be changed when saving a new version; the case editor can remove individual steps. Existing product, module, description and checklist scope fields are preserved and editable.

The combined per-cycle results report shows internal and client outcomes and exports to Excel. The scheduled worker now queues deduplicated cycle/test due reminders, including assigned client testers. Linked UAT ticket creation and resolution, ready-for-retest, and internal/client retest outcomes generate notifications. Client tests linked to unresolved defects cannot be retested; the portal explains the wait and shows the latest sign-off date.

An internal manager can name an active portal coordinator scoped to the cycle client. Assigned testers see and execute their own tests. The coordinator and approver can review all assigned client tests and the client-visible activity history; the coordinator can request additional testing, while only the approver can approve or reject. Unrelated users at the same client cannot see the published cycle. Client activity excludes internal-only comments and internal test attempts.

Checklist categories are configurable master data. Checklist versions preserve named section placement and ordering; cycles copy the section into their test snapshots. The builder can add/remove sections, move tests between sections or library modules, create/edit library cases in place, duplicate/archive checklists, and save new versions. Removing an unused library case deletes it; cases referenced by historical checklists or cycles are archived. The add-to-cycle picker supports search, selecting visible tests, and a preview of duplicates that will be skipped.

## Remaining work

- [x] **Checklist and library UI:** module/section moves, categories, in-place case creation/editing, duplicate/archive, safe removal, per-step editing and checklist ordering are implemented.
- [x] **Cycle operations:** searchable bulk selection previews duplicate skips; existing bulk owner/due-date/priority/ready changes, selected-test CSV export and personal saved views are implemented.
- [x] **Checklist Excel import:** workbook rows build global checklist templates with ordered test cases and named sections, with atomic validation and duplicate handling.
- [x] **Client acceptance:** assigned tester, named coordinator and named approver now have separate review and decision rights. Client activity and decision history are visible with internal-only data excluded. Guarded linked-ticket access, client failure-to-ticket creation and resolved-ticket retest gating are implemented.
- [x] **Reports:** combined internal/client analysis includes pass, fail, blocked, unexecuted, retest, defect, priority and feature measures, with Excel and PDF export. Portfolio CSV export is implemented.
- [x] **Notifications:** scheduled due-soon/overdue reminders now run in the existing enabled scheduler with one notification per due date and stage; ticket-created/resolved and internal/client retest pass/fail notifications are implemented. Publication, assignment, failure, sign-off and ready-for-retest notifications were already present. Confirm scheduler enablement in the target deployment during release review.
- [x] **Release readiness:** implementation-progress rows are reconciled by migration `0221_uat_completion`. Backend Ruff and strict MyPy passed; the clean full backend suite passed 421 tests. Frontend ESLint, all 80 Vitest tests, TypeScript and the production build passed. Import and PDF endpoint integration tests passed. The release package is prepared through the standard controlled release workflow.

Suggested next step: deploy the controlled release to UAT and run the documented smoke test with representative internal and client users.

---

Implement a new enterprise-grade **Smart UAT Testing Module** inside the existing Support Hub system.

This must be implemented as a fully integrated module, not as a standalone application.

Reuse the existing Support Hub:

* Authentication
* Permissions
* Role/profile framework
* Clients
* Contracts
* Products
* Modules
* Users
* Teams
* Departments
* Tickets
* Attachments
* Notifications
* Audit logs
* Client Portal
* Reporting
* UI design system
* Backend architecture
* API conventions
* Database naming conventions

The module must support:

* Reusable UAT checklist templates
* Reusable test case library
* UAT cycles
* Test execution
* PASS / FAIL / BLOCKED / N/A
* Retesting
* Ticket creation from failed UAT
* Internal testing
* Client Portal testing
* Client sign-off
* Top Management live tracking
* Secure read-only shareable tracking
* Reporting
* Audit trail
* Permissions
* Implementation progress tracking

Do not create duplicate frameworks where Support Hub already has equivalent services.

---

# 1. Main Objective

The Smart UAT Testing Module will manage the complete User Acceptance Testing lifecycle.

The module should support this full process:

Master Test Library
→ Checklist Template
→ UAT Cycle
→ Assign Test Cases
→ Execute Testing
→ PASS / FAIL / BLOCKED
→ Create Ticket from Failure
→ Fix Ticket
→ Ready for Retest
→ Retest
→ Client Acceptance
→ Sign-Off
→ Final Completion

The system should feel like a lightweight combination of:

* Jira Board
* Test Management System
* Support Hub Ticketing
* Client Acceptance Portal
* Executive Live Tracking Dashboard

---

# 2. Main Navigation

Add a new main navigation item:

UAT Testing

Sub-pages:

* Dashboard
* UAT Cycles
* My Tests
* Board
* Test Library
* Checklist Templates
* Failed Tests
* Live Tracking
* Reports
* Master Data
* Implementation Progress

When opening a UAT Cycle, provide tabs:

* Overview
* Board
* List
* Failures
* Defects
* Activity
* Client Testing
* Sign-Off

---

# 3. Implementation Progress Tracking

This feature is mandatory.

Create an internal implementation-progress tracker for this module.

The purpose is to allow us to track what has been implemented by Codex and what is still pending.

Create a page:

UAT Testing
→ Implementation Progress

or place it under Administration / Development if that is more suitable to the current system architecture.

Each implementation task must have:

* Feature Area
* Task / Requirement
* Description
* Backend Status
* Frontend Status
* Database Status
* Testing Status
* Overall Status
* Notes
* Last Updated
* Updated By

Use the following statuses:

* NOT_STARTED
* IN_PROGRESS
* COMPLETED
* BLOCKED
* NEEDS_REVIEW
* DEFERRED

The main grid should contain a visible:

**Status**

column.

Example:

| Feature            | Status       | Backend     | Frontend    | DB          | Testing      |
| ------------------ | ------------ | ----------- | ----------- | ----------- | ------------ |
| UAT Cycle Creation | COMPLETED    | COMPLETED   | COMPLETED   | COMPLETED   | COMPLETED    |
| Test Library       | IN_PROGRESS  | COMPLETED   | IN_PROGRESS | COMPLETED   | NOT_STARTED  |
| Client Portal      | NOT_STARTED  | NOT_STARTED | NOT_STARTED | NOT_STARTED | NOT_STARTED  |
| Ticket Integration | NEEDS_REVIEW | COMPLETED   | COMPLETED   | COMPLETED   | NEEDS_REVIEW |

Support filtering by:

* Status
* Feature Area
* Backend Status
* Frontend Status
* Testing Status

Add summary KPI cards:

* Total Tasks
* Completed
* In Progress
* Not Started
* Blocked
* Needs Review
* Completion %

This implementation progress page is for internal development tracking only and must not appear in the Client Portal.

---

# 4. Initial Implementation Task List

Create initial rows for the following major areas:

1. Database Schema
2. UAT Permissions
3. UAT Navigation
4. UAT Dashboard
5. UAT Cycle Management
6. Test Library
7. Checklist Templates
8. Checklist Builder
9. UAT Test Execution
10. PASS Workflow
11. FAIL Workflow
12. BLOCKED Workflow
13. Ticket Creation From Failure
14. Ticket-to-Retest Integration
15. Board View
16. List View
17. Test Attempt History
18. Comments
19. Attachments
20. Notifications
21. Activity Timeline
22. Sign-Off
23. Client Portal UAT
24. Client Portal Security
25. Client Testing
26. Client Sign-Off
27. Internal vs Client Results
28. Live Tracking
29. Secure Share Link
30. Executive Presentation Mode
31. UAT Portfolio Dashboard
32. Reports
33. Excel Export
34. PDF Export
35. Search
36. Bulk Actions
37. Test Checklist Versioning
38. Ad-hoc Test Cases
39. Test Case Import
40. Automated Tests
41. Performance / Index Review
42. Security Review
43. Final Integration Testing
44. Production Readiness Review

Allow additional implementation tasks to be manually added.

---

# 5. UAT Cycle

Create a UAT Cycle entity.

Recommended fields:

* id
* code
* title
* client_id
* contract_id
* product_id
* release_version
* environment
* start_date
* due_date
* coordinator_user_id
* department_id
* description
* status
* completion_percentage
* pass_percentage
* created_by
* created_at
* updated_by
* updated_at
* completed_at
* signed_off_at
* signed_off_by

Statuses:

* DRAFT
* PLANNING
* ACTIVE
* AWAITING_SIGNOFF
* COMPLETED
* CANCELLED

Example:

Alfa Scan – MiClinic V25.2.0.28062 UAT

---

# 6. UAT Cycle Creation Wizard

Provide a guided workflow.

Step 1:
Select Client

Step 2:
Select Contract

Only show contracts belonging to the selected client.

Step 3:
Select Product

Step 4:
Enter Release Version

Step 5:
Select Environment

Supported values:

* UAT
* TEST
* STAGING
* PRE_PRODUCTION
* PRODUCTION_VALIDATION
* OTHER

Step 6:
Select Checklist Template(s)

Step 7:
Select additional test cases if needed

Step 8:
Assign owners

Step 9:
Set dates

Step 10:
Review and Create

---

# 7. Test Library

Create a reusable Test Case Library.

Hierarchy:

Product
→ Module
→ Feature
→ Test Case

Fields:

* id
* code
* product_id
* module_id
* feature_name
* title
* description
* preconditions
* expected_result
* default_priority
* is_mandatory
* requires_evidence
* estimated_duration_minutes
* is_active
* created_by
* created_at
* updated_by
* updated_at

---

# 8. Structured Test Steps

Do not store all steps only as one text field.

Create:

uat_test_case_steps

Fields:

* id
* test_case_id
* step_order
* action
* expected_result
* notes

Allow:

* Add step
* Edit step
* Delete step
* Reorder step

Example:

Step 1:
Open Patient Registration.

Expected:
Registration page opens.

Step 2:
Enter required patient data.

Expected:
Data is accepted.

Step 3:
Save.

Expected:
Patient is successfully registered.

---

# 9. Test Checklist Templates

Create reusable Checklist Templates.

Fields:

* id
* code
* name
* description
* product_id
* category_id
* scope_type
* client_id
* contract_id
* current_version
* is_active
* created_by
* created_at
* updated_by
* updated_at

Scope Types:

* GLOBAL
* CLIENT
* CONTRACT

Example:

GLOBAL:
MiClinic Standard UAT

CLIENT:
Alfa Scan MiClinic UAT

CONTRACT:
Alfa Scan 2026 Contract UAT

---

# 10. Checklist Builder

Create a user-friendly checklist builder.

Support:

* Add test case
* Add existing test case
* Create new test case
* Edit test case
* Remove test case
* Duplicate test case
* Reorder test case
* Move test case between modules
* Add module section
* Remove module section
* Duplicate checklist
* Archive checklist
* Create new checklist version

Example:

MiClinic Full UAT

Reception

* Register New Patient
* Edit Patient
* Create Visit
* VIP Registration

Nursing

* Record Vitals
* Nursing Assessment

Result Delivery

* Search Result
* Print Report
* Deliver Result

Provide drag-and-drop ordering where practical.

---

# 11. Checklist Categories

Create configurable categories.

Examples:

* Full UAT
* Regression
* Smoke Test
* Upgrade Validation
* Hotfix Validation
* Integration Testing
* New Installation
* Client Acceptance
* Security Testing
* Permission Testing
* Performance Testing

These should be configurable Master Data where practical.

---

# 12. Checklist Versioning

Support checklist versioning.

Example:

MiClinic Standard UAT
Version 1

Later:

MiClinic Standard UAT
Version 2

Historical UAT Cycles must remain linked to the version originally used.

Do not alter historical executions when a checklist changes.

---

# 13. Historical Snapshot Rule

This rule is mandatory.

When a test case is added to a UAT Cycle, snapshot:

* Test Case Code
* Product
* Module
* Feature
* Scenario
* Description
* Preconditions
* Steps
* Expected Result
* Priority
* Mandatory flag

Future changes in Master Data must not modify old UAT executions.

---

# 14. UAT Test Execution

Create a cycle-specific UAT execution entity.

Fields:

* id
* cycle_id
* test_case_id
* checklist_version_id
* product_id
* module_id
* feature_name
* test_scenario
* preconditions
* expected_result
* actual_result
* owner_user_id
* reviewer_user_id
* priority
* severity
* workflow_status
* test_result
* due_date
* tested_at
* retest_count
* failure_reason
* failure_category
* linked_ticket_id
* tester_comments
* created_at
* updated_at

---

# 15. Workflow Status vs Test Result

Keep these separate.

Workflow Status:

* READY
* IN_PROGRESS
* WAITING_FIX
* READY_FOR_RETEST
* COMPLETED
* BLOCKED

Test Result:

* NOT_TESTED
* PASS
* FAIL
* BLOCKED
* NOT_APPLICABLE

Example:

workflow_status = WAITING_FIX

test_result = FAIL

---

# 16. Board View

Create Jira-style Kanban board.

Columns:

* Ready
* In Testing
* Waiting Fix
* Ready for Retest
* Passed
* Blocked

Each card should show:

* UAT Test ID
* Scenario
* Product
* Module
* Owner
* Priority
* Result
* Due Date
* Linked Ticket
* Attachment Count
* Comment Count
* Retest Count

Allow drag-and-drop only when:

* state transition is valid
* user has permission

---

# 17. List View

Create a list/grid view.

Columns:

* UAT ID
* Product
* Module
* Feature
* Scenario
* Owner
* Priority
* Workflow Status
* Test Result
* Severity
* Due Date
* Retest Count
* Linked Ticket
* Tested At

Support:

* Search
* Sorting
* Filtering
* Pagination
* Saved Views
* Column Chooser
* Export
* Bulk Actions

---

# 18. PASS Workflow

When tester selects PASS:

Show confirmation dialog.

Allow:

* Actual Result
* Comment
* Evidence

Support quick PASS if enabled.

Upon PASS:

test_result = PASS
workflow_status = COMPLETED
tested_at = current datetime

Create a test attempt history row.

---

# 19. FAIL Workflow

When user selects FAIL, open a Smart Failure Popup.

Prefill:

* Test ID
* Client
* Contract
* Product
* Module
* Feature
* Test Scenario
* Preconditions
* Steps
* Expected Result
* UAT Cycle
* Version
* Environment
* Owner

Require:

* Actual Result
* Failure Description
* Severity
* Evidence

Optional:

* Failure Category
* Reproduction Notes
* Technical Notes

Failure Categories:

* Software Bug
* Configuration
* Integration
* Environment
* Permission
* Data
* Performance
* Workflow
* User Misunderstanding
* Other

Buttons:

* Save Fail Only
* Save Fail & Create Ticket
* Cancel

---

# 20. Ticket Creation From Failed UAT

If:

Save Fail & Create Ticket

is selected:

Reuse the existing Support Hub ticket creation services.

Do not duplicate ticket creation logic.

Prefill ticket title:

UAT Failed - {Product} - {Module} - {Scenario}

Prefill description with:

* UAT Cycle
* UAT Test ID
* Client
* Contract
* Product
* Module
* Feature
* Release Version
* Environment
* Preconditions
* Steps
* Expected Result
* Actual Result
* Failure Description
* Severity
* Tester

Allow user to review/edit the ticket before saving.

After creation:

* Link ticket to UAT test
* Store linked_ticket_id
* Show ticket number on UAT card
* Set workflow_status = WAITING_FIX
* Keep test_result = FAIL
* Add audit event

Example:

SUP-10425 created from UAT-0145

---

# 21. Duplicate Ticket Prevention

Prevent accidental duplicate ticket creation.

If a ticket is already linked, show:

This UAT case is already linked to SUP-10425.

Do not create another ticket unless the system explicitly supports multiple defect tickets and the user has permission.

---

# 22. Retest Workflow

When the linked Support Hub ticket becomes resolved:

Automatically or through configurable workflow change:

WAITING_FIX
→ READY_FOR_RETEST

Notify the UAT owner.

Example:

SUP-10425 has been resolved.
UAT-0145 is ready for retest.

When retesting:

* increment retest_count
* create new Test Attempt
* preserve old attempt history

---

# 23. Test Attempt History

Create:

uat_test_attempts

Fields:

* id
* uat_execution_id
* attempt_number
* execution_source
* tested_by
* tested_at
* result
* actual_result
* failure_reason
* severity
* failure_category
* comment
* linked_ticket_id
* created_at

Execution Source:

* INTERNAL
* CLIENT_PORTAL

Example:

Attempt 1
FAIL
19-Sep-2026
Ticket SUP-10425

Attempt 2
PASS
21-Sep-2026

Never overwrite previous attempts.

---

# 24. BLOCKED Workflow

When selecting BLOCKED require:

* Blocking Reason
* Comment

Optional:

* Related Ticket
* Dependency
* Environment Issue
* Access Issue
* Test Data Issue

Set:

test_result = BLOCKED
workflow_status = BLOCKED

---

# 25. Add Tests After Cycle Starts

Authorized users must be able to add more tests after a UAT Cycle starts.

Button:

* Add Test

Options:

* Add From Library
* Add From Checklist
* Create Ad-hoc Test

When tests are added:

* update total test count
* update completion %
* update remaining tests
* add activity log

Example:

5 additional tests were added by Ahmed on 20-Sep-2026.

---

# 26. Ad-hoc Test Cases

Allow creating a test only for the current UAT Cycle.

Fields:

* Product
* Module
* Feature
* Scenario
* Preconditions
* Steps
* Expected Result
* Priority

Optional action:

Save to Test Library

This should create a reusable Master Test Case.

---

# 27. Master Data Page

Create:

UAT Testing
→ Master Data

Sections:

* Checklist Templates
* Test Cases
* Checklist Categories
* Failure Categories
* Severity Levels
* Environments
* Tags

All Master Data actions must be permission-controlled.

---

# 28. Test Case Editing and Removal

Authorized users can:

* Add
* Edit
* Duplicate
* Archive
* Remove

If test case has never been used:
Allow delete.

If already used historically:
Do not hard delete.

Archive instead.

Show:

This test case has historical UAT records and cannot be permanently deleted. It will be archived.

Removing a test case from a checklist must not delete the Master Test Case.

---

# 29. Multiple Checklists Per Cycle

Allow multiple checklist templates to be imported.

Example:

MiClinic Standard UAT
+
SAP Integration Checklist
+
Alfa Scan VIP Checklist

Detect duplicates.

Options:

* Skip duplicates
* Keep duplicates
* Review duplicates

Recommended default:

Skip duplicate Test Case IDs.

---

# 30. Bulk Import

Support Excel import for Test Library and checklists.

Allow columns such as:

* Checklist
* Product
* Module
* Feature
* Test Case Code
* Title
* Preconditions
* Step
* Expected Result
* Priority
* Mandatory

Provide preview:

* New
* Existing
* Duplicate
* Invalid

Do not silently overwrite existing test cases.

---

# 31. UAT Dashboard

Create KPI cards:

* Total Tests
* Completed
* Completion %
* Passed
* Failed
* Blocked
* Not Tested
* Overdue
* Pass Rate
* Critical Failures
* Waiting Retest
* Open Defects

Charts:

* Results by Product
* Results by Module
* Results by Owner
* Failures by Severity
* Failures by Category
* Progress Over Time
* Retest Trend
* Tests by Status

---

# 32. Smart Insights

Provide rule-based smart insights.

Examples:

* 8 tests are failing in Reception.
* 3 critical tests remain untested.
* 5 failed tests are waiting for ticket resolution.
* 7 tests are overdue.
* Billing has 4 open failed scenarios.
* 9 tests passed after retesting.

Do not automatically make release approval decisions.

Provide facts and warnings only.

---

# 33. Sign-Off

Create Sign-Off tab.

Fields:

* Requested by
* Requested at
* Approved by
* Approved at
* Status
* Comments
* Acceptance Notes
* Attachments

Statuses:

* NOT_REQUESTED
* PENDING
* APPROVED
* REJECTED

Display summary:

* Total Tests
* Passed
* Failed
* Blocked
* Not Tested
* Mandatory Tests Incomplete
* Open Tickets
* Pass Rate
* Completion %

Require comment for rejection.

---

# 34. Client Portal Integration

The same UAT Cycle must be available in the existing Client Portal when explicitly published.

Do not create separate client UAT tables.

Use the same UAT domain model.

Add Client Portal page:

UAT Testing

Client tabs:

* Active UAT
* My Tests
* Completed UAT

Within a cycle:

* Overview
* Tests
* Failed Tests
* Activity
* Sign-Off

---

# 35. Client Portal UAT Configuration

Add per-cycle settings:

* Visible in Client Portal
* Allow Client Testing
* Allow Client PASS
* Allow Client FAIL
* Allow Client BLOCKED
* Allow Client Comments
* Allow Client Attachments
* Allow Client Sign-Off
* Allow Client View Linked Ticket
* Allow Client Create Ticket From Failure

Also allow:

* Client Access Start
* Client Access End
* Allowed Client Roles

---

# 36. Client Portal Permissions

Add:

UATPortal.View

UATPortal.Cycle.View

UATPortal.Test.View
UATPortal.Test.Execute

UATPortal.Test.MarkPass
UATPortal.Test.MarkFail
UATPortal.Test.MarkBlocked

UATPortal.Comment
UATPortal.UploadEvidence

UATPortal.ViewLinkedTicket
UATPortal.CreateTicketFromFailure

UATPortal.SignOff

---

# 37. Client Security

This is critical.

Every Client Portal API must enforce:

* Authenticated portal user
* Client ownership
* Published UAT cycle
* Permission
* Test-cycle relationship
* Client-specific access

Never trust client_id sent from frontend.

Resolve client identity from authenticated context.

Prevent IDOR vulnerabilities.

A user from Client A must never access Client B UAT data even by changing IDs manually.

---

# 38. Internal vs Client Results

Support separate execution history.

Use:

execution_source

Values:

* INTERNAL
* CLIENT_PORTAL

This allows:

Internal result:
PASS

Client result:
FAIL

without overwriting either result.

Provide combined reporting where appropriate.

---

# 39. Internal and Client Comments

Support visibility levels:

* INTERNAL_ONLY
* CLIENT_VISIBLE

Internal users can choose visibility.

Client comments are automatically CLIENT_VISIBLE.

Do not expose internal comments in Client Portal.

Apply similar logic to attachments when needed.

---

# 40. Client Sign-Off

Allow selected client users to approve or reject UAT.

Roles may include:

* Client UAT Tester
* Client UAT Coordinator
* Client Approver

Client Approver sees:

* Total Tests
* Passed
* Failed
* Blocked
* Not Tested
* Completion %
* Pass %
* Open Defects
* Mandatory Outstanding

Actions:

* Approve UAT
* Reject UAT
* Request Additional Testing

Store:

* Portal user
* Client
* Date/time
* Comment
* Sign-Off Status

---

# 41. Live Tracking

Create:

UAT Testing
→ Live Tracking

This is a read-only management view.

Use real-time updates if existing architecture supports them.

Otherwise use efficient polling.

Display:

* Client
* Contract
* Product
* Version
* Environment
* Coordinator
* Start Date
* Due Date
* Cycle Status

KPI cards:

* Completion %
* Pass Rate
* Total Tests
* Passed
* Failed
* Blocked
* Not Tested
* Overdue
* Waiting Retest
* Open Defects
* Critical Failures
* Sign-Off Status

---

# 42. Executive Attention Required Panel

Add:

Attention Required

Examples:

* 2 critical failed tests
* 5 overdue tests
* 3 blocked scenarios
* 4 open UAT defects
* 7 waiting retest
* 1 mandatory module incomplete
* Sign-off pending

Use factual indicators only.

---

# 43. Module Progress View

Show progress grouped by:

* Product
* Module
* Owner
* Client
* Internal / Client Execution Source

Example:

Reception
94% Complete
2 Failed

Nursing
100% Complete

Result Delivery
75% Complete
1 Blocked

---

# 44. Live Activity Stream

Display important events:

* Test started
* PASS
* FAIL
* Ticket created
* Ticket resolved
* Ready for Retest
* Retested
* Sign-Off Requested
* Sign-Off Approved

Avoid flooding management view with low-value technical audit events.

---

# 45. Secure Shareable Live Tracking Page

Allow authorized users to create a read-only share link.

Use secure random token.

Example route:

/uat/live/{secure-token}

Configuration:

* Expiration
* Password Required
* Show Client Name
* Show Product
* Show Test Scenarios
* Show Failures
* Show Linked Tickets
* Show Activity
* Show Sign-Off Status

Never expose internal comments, sensitive ticket information, contract financials, internal notes, or private attachments.

---

# 46. Share Link Security

Store:

* token hash or secure token reference
* cycle_id
* created_by
* created_at
* expires_at
* revoked_at
* is_active
* visibility configuration

Allow immediate revoke.

Optional password protection.

Store password hash, not plaintext.

Validate token on every request.

Shared page must be read-only.

---

# 47. Executive Presentation Mode

Add Presentation Mode.

Hide:

* Side navigation
* Editing controls
* Operational actions

Show:

* Client
* Product
* Version
* Completion
* Passed
* Failed
* Blocked
* Open Defects
* Critical Failures
* Module Progress
* Sign-Off Status
* Latest Activity

Support full-screen display.

---

# 48. UAT Portfolio Dashboard

For Top Management, add a page showing all active UAT cycles.

Columns/cards:

* Client
* Product
* Release
* Completion
* Pass Rate
* Failed
* Critical Failures
* Open Defects
* Due Date
* Sign-Off
* Current Status

Use factual rule-based labels such as:

* On Schedule
* Due Soon
* Overdue
* Critical Failures Present
* Testing Incomplete
* Awaiting Sign-Off

---

# 49. Notifications

Use the existing notification framework.

Trigger notifications for:

* UAT assigned
* Due soon
* Overdue
* Failed
* Critical failure
* Ticket created
* Ticket resolved
* Ready for retest
* Retest failed
* Retest passed
* Sign-Off requested
* Sign-Off approved
* Sign-Off rejected
* Client UAT published

Avoid duplicate notification noise.

---

# 50. Activity Timeline

Every UAT Test should have a timeline.

Examples:

Created
Assigned
Testing Started
Marked FAIL
Screenshot Added
SUP-10425 Created
Ticket Resolved
Ready for Retest
Retest Started
Marked PASS

Store:

* User
* Date/time
* Action
* Previous Value
* New Value
* Source

---

# 51. Attachments

Reuse existing attachment system.

Support:

* Image
* Screenshot
* PDF
* Video
* Log
* Other supported files

Attachments should remain associated with the relevant Test Attempt.

Allow evidence to be referenced/copied into linked Support Tickets where possible.

---

# 52. Comments

Allow UAT comments.

Fields:

* User
* Date/time
* Text
* Visibility
* Attachments
* Mentions if existing functionality supports it

Do not use comments as a replacement for Actual Result.

---

# 53. Permissions

Integrate into the existing permission framework.

Add permissions similar to:

UAT.View
UAT.Dashboard.View

UAT.Cycle.View
UAT.Cycle.Create
UAT.Cycle.Edit
UAT.Cycle.Delete
UAT.Cycle.Activate
UAT.Cycle.Complete

UAT.Test.View
UAT.Test.Create
UAT.Test.Edit
UAT.Test.Delete
UAT.Test.AssignOwner

UAT.Test.Execute
UAT.Test.MarkPass
UAT.Test.MarkFail
UAT.Test.MarkBlocked
UAT.Test.Retest
UAT.Test.ChangeStatus

UAT.Failure.CreateTicket
UAT.Failure.ViewLinkedTicket

UAT.Attachment.Upload
UAT.Comment.Create

UAT.Library.View
UAT.Library.Manage

UAT.Checklist.View
UAT.Checklist.Create
UAT.Checklist.Edit
UAT.Checklist.Delete
UAT.Checklist.Archive
UAT.Checklist.Version
UAT.Checklist.Duplicate

UAT.SignOff.Request
UAT.SignOff.Approve
UAT.SignOff.Reject

UAT.LiveTracking.View
UAT.LiveTracking.ViewAll
UAT.LiveTracking.Share
UAT.LiveTracking.RevokeShare
UAT.LiveTracking.Export
UAT.LiveTracking.PresentationMode

UAT.Report.View
UAT.Report.Export

UAT.ImplementationProgress.View
UAT.ImplementationProgress.Edit

---

# 54. Visibility Rules

Respect existing Support Hub client and department ownership.

Standard Engineer:

* assigned tests
* permitted department clients

Team Leader:

* own department/team

Department Manager:

* department UAT

Top Management:

* all permitted UAT

Client Portal:

* only its own published cycles

Do not build a separate authorization system.

---

# 55. Search

Global UAT search should support:

* UAT Cycle Code
* Test ID
* Scenario
* Client
* Product
* Module
* Owner
* Ticket Number
* Version

Optionally integrate into existing Support Hub global search.

---

# 56. Saved Views

Support saved views.

Examples:

* My UAT Tests
* Failed Tests
* Waiting Retest
* Critical Tests
* Overdue UAT
* Client Tests
* Internal Tests
* Sign-Off Pending

---

# 57. Bulk Actions

Support:

* Assign Owner
* Set Due Date
* Set Priority
* Add to Cycle
* Move to Ready
* Export

Do not allow unsafe bulk PASS / FAIL unless specifically enabled through permission and confirmation.

---

# 58. Reporting

Provide reports:

* UAT Cycle Summary
* Execution Report
* Failed Test Report
* Open Defects Report
* Retest Report
* Outstanding Tests
* Module Results
* Product Results
* Client UAT Summary
* Internal vs Client Results
* Sign-Off Report

Support Excel export.

Support PDF where existing reporting infrastructure allows it.

---

# 59. Database Tables

Use current project naming conventions.

Suggested tables:

* uat_cycles
* uat_test_cases
* uat_test_case_steps
* uat_checklist_templates
* uat_checklist_versions
* uat_checklist_test_cases
* uat_cycle_tests
* uat_test_attempts
* uat_test_comments
* uat_test_attachments
* uat_test_ticket_links
* uat_signoffs
* uat_share_links
* uat_implementation_progress

Create appropriate:

* PKs
* FKs
* Unique constraints
* Indexes
* created_at
* updated_at
* created_by
* updated_by

---

# 60. Recommended Indexes

Add indexes for:

* cycle_id
* client_id
* contract_id
* product_id
* module_id
* owner_user_id
* workflow_status
* test_result
* due_date
* linked_ticket_id
* execution_source
* signoff_status
* share_token
* implementation_status

Review query plans for large UAT cycles.

---

# 61. API Design

Follow current Support Hub API conventions.

Provide endpoints/services for:

UAT Cycles:

* list
* details
* create
* update
* activate
* complete
* cancel

Test Library:

* list
* create
* update
* archive
* import

Checklist Templates:

* list
* create
* edit
* duplicate
* version
* archive
* manage test cases

Cycle Tests:

* list
* details
* assign
* execute
* pass
* fail
* block
* retest
* change status

Ticket Integration:

* create ticket from failed test
* get linked ticket
* ticket status sync

Client Portal:

* published cycles
* tests
* execute
* fail
* pass
* block
* comments
* sign-off

Live Tracking:

* summary
* module progress
* failures
* activity
* defects

Share Links:

* create
* revoke
* validate

Implementation Progress:

* list
* update status
* add task
* view summary

---

# 62. Transaction Safety

Ticket creation must be safe.

Handle:

* repeated clicks
* API timeout
* duplicate ticket
* concurrent updates
* partial transaction failure

Use idempotency or duplicate checking.

Do not leave inconsistent UAT/ticket relationships.

---

# 63. Validation Rules

Cycle requires:

* Client
* Contract
* Product
* Title
* Coordinator

Test case requires:

* Scenario
* Expected Result

FAIL requires:

* Actual Result
* Failure Description
* Severity

BLOCKED requires:

* Blocking Reason

Ticket creation requires:

* Failed test
* Permission
* No duplicate active link

Sign-Off requires:

* Sign-Off permission
* valid request

---

# 64. UI / UX Requirements

Match existing Support Hub design.

Reuse:

* Cards
* Badges
* Modals
* Drawers
* Grids
* Pagination
* Dropdowns
* Date pickers
* Notifications
* Skeleton loaders
* Empty states

Use clear labels for:

PASS
FAIL
BLOCKED
NOT TESTED

Do not rely only on color.

Use icon + text.

---

# 65. Responsive Design

Support:

* Desktop
* Tablet
* Mobile where practical

Client Portal must be especially mobile-friendly.

Board view can horizontally scroll on smaller screens.

List view should use responsive column behavior.

---

# 66. Automated Tests

Add automated tests for critical paths:

* Cycle creation
* Checklist import
* Test creation
* Permission restrictions
* Client isolation
* Assignment
* PASS
* FAIL
* FAIL validation
* BLOCKED
* Ticket creation
* Duplicate ticket prevention
* Ticket resolved → Ready for Retest
* Retest PASS
* Retest FAIL
* Historical attempt preservation
* Client Portal UAT
* Internal vs Client result separation
* Sign-Off permissions
* Share token security
* Implementation Progress status updates

---

# 67. Security Review

Explicitly test:

* IDOR protection
* Client data isolation
* Permission bypass
* Invalid test-cycle IDs
* Unauthorized ticket access
* Internal comment exposure
* Share token guessing
* Expired links
* Revoked links
* Unsafe attachment access

All security must be enforced server-side.

---

# 68. Performance Requirements

Avoid loading all tests unnecessarily.

Use:

* Server-side pagination
* Indexed filtering
* Lazy loading where appropriate
* Aggregated dashboard endpoints
* Efficient board queries
* Efficient count queries

Do not retrieve full attachment/comment history for every card in the board.

---

# 69. Implementation Progress Update Rules

As each feature is implemented, update the corresponding implementation-progress row.

Example:

Feature:
FAIL Workflow

Backend:
COMPLETED

Frontend:
COMPLETED

Database:
COMPLETED

Testing:
IN_PROGRESS

Overall Status:
IN_PROGRESS

Notes:
Failure popup implemented; integration test still pending.

When all areas are completed and tested:

Overall Status:
COMPLETED

Do not automatically mark a task COMPLETED just because code was generated.

Only mark completed when the implementation exists and relevant tests/checks pass.

---

# 70. Final Implementation Summary

At the end of the implementation work, provide a clear implementation summary.

The summary must include a table:

| Area              | Status      | Notes                                     |
| ----------------- | ----------- | ----------------------------------------- |
| Database          | COMPLETED   | Tables and migrations added               |
| Permissions       | COMPLETED   | UAT permissions registered                |
| Test Library      | COMPLETED   | CRUD and archive implemented              |
| Checklist Builder | COMPLETED   | Add/edit/remove/reorder implemented       |
| UAT Cycle         | COMPLETED   | Wizard and management implemented         |
| Board View        | COMPLETED   | Kanban implemented                        |
| List View         | COMPLETED   | Grid/filter/export implemented            |
| Fail → Ticket     | COMPLETED   | Integrated with Support Hub ticketing     |
| Retesting         | COMPLETED   | Ticket resolution integration implemented |
| Client Portal     | COMPLETED   | External UAT testing implemented          |
| Live Tracking     | COMPLETED   | Management dashboard implemented          |
| Sign-Off          | COMPLETED   | Internal/client sign-off implemented      |
| Reporting         | IN_PROGRESS | PDF export pending                        |
| Automated Tests   | IN_PROGRESS | Security tests pending                    |

Use only truthful statuses based on actual implementation.

Do not claim COMPLETED for work that has not been implemented.

---

# 71. Changed Files Report

At the end provide:

* New database migrations
* New backend files
* Modified backend files
* New frontend files
* Modified frontend files
* Permission/config changes
* Client Portal changes
* Tests added

Also highlight any manual deployment steps.

---

# 72. Deployment Safety

Do not break existing Support Hub functionality.

Before completing:

* Verify database migration safety
* Verify existing ticket creation
* Verify existing Client Portal
* Verify existing permissions
* Verify current dashboards
* Verify no existing API route collision
* Verify no destructive schema changes

Use backward-compatible database migrations.

---

# 73. Expected Example Workflow

Example:

Administrator creates:

MiClinic Standard UAT Checklist

Adds:

Reception
Nursing
Result Delivery
Administration

Later creates:

Alfa Scan MiClinic UAT Checklist

Adds customer-specific cases:

VIP Registration
SAP Integration
Claims Reporting
VIP QR

Creates UAT Cycle:

Alfa Scan – MiClinic V25.2.0.28062

Imports checklist.

Assigns scenarios to engineers.

Engineer tests:

VIP Patient Registration

Expected:
VIP appears correctly.

Actual:
VIP flag missing in result delivery.

Engineer clicks FAIL.

Failure popup opens.

Adds screenshot.

Clicks:

Save Fail & Create Ticket

System creates:

SUP-10425

UAT becomes:

WAITING_FIX

Ticket gets resolved.

System changes UAT test:

READY_FOR_RETEST

Engineer retests.

Result:

PASS

Client Portal user also performs assigned acceptance tests.

Client approves Sign-Off.

Top Management watches progress from Live Tracking.

Final UAT Cycle becomes:

COMPLETED

Implementation Progress page shows all feature implementation statuses separately.

---

# 74. Final Requirement

Implement this module end-to-end.

Do not stop at database models or placeholder UI.

Deliver:

* Database migration
* Backend models
* Services
* APIs
* Permissions
* Frontend pages
* Master Data
* Checklist Builder
* Test Library
* UAT Cycle
* Board
* List
* PASS
* FAIL
* BLOCKED
* Ticket Integration
* Retesting
* Client Portal
* Live Tracking
* Secure Sharing
* Sign-Off
* Reporting
* Audit
* Notifications
* Automated Tests
* Implementation Progress Tracker

The final result must be production-ready and fully integrated with the existing Support Hub architecture.
