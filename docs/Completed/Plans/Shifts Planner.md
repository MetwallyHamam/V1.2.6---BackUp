Act as a **Senior Software Engineer and System Architect** working on my existing **MILLENSYS Support Hub** application.

Inspect the existing project first, including database schema, Users, Roles/Privileges, Shifts, WFH, Groups, Clients, Contracts, Operations, Calendar, Attachments, Reports and Dashboards.

Reuse the existing architecture and components wherever possible. Do not rebuild working modules or perform unrelated refactoring.

The goal is to introduce a **smart, mobile-friendly scheduling and recurring operations framework** while keeping the existing Shifts and Operations pages as the operational source of truth.

# 1. Department Master Data

Create configurable Department Master Data.

Fields:

* Id
* Name
* Code
* Description
* IsActive
* CreatedAt
* UpdatedAt

Initial metadata should include:

* Support
* Call Center
* Implementation
* Clients
* Sales
* Finance
* HR
* Management

Add Department dropdown to Create/Edit User.

Keep these concepts independent:

**Department = organizational ownership**

**Profile/Role = permissions**

**Group = operational grouping**

Do not hard-code department names anywhere in application logic.

Provide a SQL Server migration/metadata script to safely create/update these records without creating duplicates.

# 2. User Scheduling Eligibility

Extend the User model with:

* DepartmentId
* IncludeInShifts
* IncludeInWFH

When selecting users for shifts:

`IsActive = true`

AND

`IncludeInShifts = true`

AND

`DepartmentId = selected department`

For WFH:

`IsActive = true`

AND

`IncludeInWFH = true`

AND

`DepartmentId = selected department`

Apply these rules in the backend as well as the frontend.

# 3. Shift Type Master Data

Create reusable **Shift Type** Master Data.

Suggested initial metadata:

* Morning
* Evening
* Night
* Weekend Morning
* Weekend Evening
* Weekend Night
* On-Call

Fields:

* Id
* Name
* Code
* Description
* IsActive
* DisplayOrder

Shift Types are reusable across departments.

Example:

`Night`

can be used by both Support and Call Center even when their working hours are different.

Provide an idempotent SQL Server metadata script for initial Shift Types.

# 4. Dynamic Shift Patterns / Windows

Create configurable **Shift Patterns**.

A Shift Pattern defines:

**Department + Shift Type + Days + Time Window**

Fields should include:

* Id
* DepartmentId
* ShiftTypeId
* Name
* StartTime
* EndTime
* ApplicableDays
* DisplayOrder
* IsActive
* Description
* CreatedAt
* UpdatedAt

Do not hard-code working hours.

Example Support patterns:

* Weekday Night — Sun–Thu — 4 PM–12 AM
* Weekend Morning — Fri–Sat — 9 AM–5 PM
* Weekend Evening — Fri–Sat — 2 PM–10 PM
* Weekend Night — Fri–Sat — 4 PM–12 AM

Example Call Center patterns:

* Morning — configurable window
* Evening — configurable window
* Night — configurable window

These are example metadata only.

Administrators must be able to:

* Create
* Edit
* Duplicate
* Activate/deactivate
* Change days
* Change start/end times
* Reorder

Support overnight shifts correctly, for example:

`8 PM → 4 AM`

Historical/generated shifts must preserve their original scheduled start/end times even if the Shift Pattern changes later.

# 5. One Department-Aware Weekly Planner

Do NOT build separate planners for Support and Call Center.

Create/reuse:

**Shifts → Weekly Planner**

The planner should be driven by:

* Selected Week
* Selected Department

Example:

`Department = Support`

loads Support Shift Patterns and Support eligible engineers.

`Department = Call Center`

loads Call Center Shift Patterns and Call Center eligible users.

The same scheduling engine must support future departments.

# 6. Mobile-First Planner

The planner must be fast to use from mobile.

Example:

### Friday

**Weekend Morning**

9 AM–5 PM

`Ahmed ×` `Mohamed ×` `+ Add`

**Weekend Evening**

2 PM–10 PM

`Kareem ×` `+ Add`

**Weekend Night**

4 PM–12 AM

`Mostafa ×` `Ahmed ×` `+ Add`

Normal users should not repeatedly enter:

* shift dates
* shift type
* start time
* end time

These come from the selected week and Shift Pattern.

Use:

* large touch targets
* searchable selection
* engineer chips
* responsive cards
* simple week navigation
* sticky Save/Publish where appropriate

# 7. Multiple Engineers Per Shift

A Shift can contain one or multiple engineers.

Use normalized relational design.

Prefer:

**Shift**

* Id
* DepartmentId
* ShiftTypeId
* ShiftPatternId
* ShiftDate
* ScheduledStartDateTime
* ScheduledEndDateTime
* Status
* Source

**ShiftAssignment**

* Id
* ShiftId
* UserId
* GroupId nullable
* AssignmentSource
* CreatedAt

Never store multiple User IDs inside one database field.

# 8. Individual or Group Assignment

When assigning a shift support:

**Engineers | Groups**

Engineer mode:

* searchable multi-select
* one or multiple users

Group mode:

* select scheduling group

Groups must belong to a Department.

Examples:

* Support Weekend Team
* Support Night Team
* Call Center Morning Team
* Call Center Evening Team

When using a group:

* preserve GroupId
* create individual ShiftAssignment records for eligible members

This is required for accurate engineer-level reporting.

# 9. Existing Shifts Page Integration

Weekly Planner is only a fast scheduling interface.

Generated/published shifts must become normal records and appear in the existing:

* Shifts Page
* Calendar
* Engineer views
* Dashboards
* Reports

Add Department and Shift Type filters.

Useful Source values:

* Manual
* Weekly Planner
* Group

Do not create a disconnected scheduling subsystem.

# 10. Copy Previous Week

Add:

**Copy Last Week**

It should:

* copy previous assignments
* automatically update dates
* use current applicable Shift Patterns
* validate active users
* validate Department
* validate IncludeInShifts
* prevent duplicate assignments
* allow editing before saving

This should significantly reduce repeated weekly entry.

# 11. Basic Scheduling Conflict Detection

Before save/publish detect:

* overlapping shifts
* duplicate assignment to same shift
* WFH overlap when reliable WFH information exists

Show warnings clearly.

Allow override according to the existing privilege model.

Keep conflict logic simple and maintainable.

# 12. Workload Visibility

While selecting engineers, show lightweight information such as:

`Ahmed — 3 shifts this month`

`Mohamed — 5 shifts this month`

`Kareem — 2 shifts this month`

Use this for scheduling guidance.

Do not force automatic assignment based on it.

# 13. WFH Integration

Use the same Department concept for WFH.

WFH selectors must use:

* selected Department
* Active user
* IncludeInWFH = true

Add Department filtering to existing WFH pages.

Do not create a completely separate employee model for WFH.

# 14. Shift Review Report

Create:

**Reports → Shift Review**

Filters:

* Date From
* Date To
* Department
* Engineer
* Group
* Shift Type
* Shift Pattern

KPIs:

* Total Scheduled Shifts
* Total Engineer Assignments
* Shifts per Department
* Shifts per Engineer
* Morning Shifts
* Evening Shifts
* Night Shifts
* Weekend Shifts
* Unassigned Shift Slots
* Cancelled Shifts
* Group vs Individual Assignments

Charts:

* Shift Distribution by Engineer
* Shift Distribution by Department
* Shift Distribution by Type
* Night/Weekend Distribution
* Weekly/Monthly Trend

Use existing Excel export functionality.

Reuse PDF export only if the project already has an appropriate implementation.

# 15. Client-Level Visit Entitlement

Recurring service visits belong to the **Client**, not directly to the Contract.

A single Contract may contain multiple Clients with different visit requirements.

Example:

**Contract A**

* Cairo Client → 4 visits/year
* Giza Client → 4 visits/year
* Alexandria Client → 2 visits/year

The Contract may display a summary, but visit entitlement must remain client-specific.

# 16. Client Visit Plan

Create/reuse:

**ClientVisitPlan**

Fields should include:

* Id
* ClientId
* ContractId nullable/reference
* DepartmentId
* VisitType
* Frequency
* AllowedVisits
* EffectiveFrom
* EffectiveTo
* AutoGenerate
* IsActive
* Description
* CreatedAt
* UpdatedAt

Support frequencies such as:

* Monthly
* Quarterly
* Semi-Annual
* Annual
* Custom

# 17. Recurring Visit Generation

A Visit Plan represents a recurrence rule.

Generate independent **Visit Occurrences** from it.

Example:

Quarterly plan:

* Q1 Visit
* Q2 Visit
* Q3 Visit
* Q4 Visit

Create/reuse:

**ClientVisitOccurrence**

Fields:

* Id
* ClientVisitPlanId
* ClientId
* ContractId nullable
* DepartmentId
* VisitType
* PlannedFromDate
* PlannedToDate
* ScheduledVisitDate nullable
* ActualVisitDate nullable
* ClientLocationId nullable
* Status
* Notes
* ResultSummary
* NextAction
* Source
* CreatedAt
* UpdatedAt

Statuses:

* Planned
* Scheduled
* Completed
* Cancelled
* Overdue

# 18. Fixed Date or Date Window

Visits must support:

### Exact Date

Example:

`15-Mar-2027`

or:

### Date Window

Example:

`01-Mar-2027 → 31-Mar-2027`

This allows quarterly visits to be planned for a period without forcing an exact date during initial generation.

The manager can later schedule the actual visit date within the window.

# 19. Different Engineers Per Visit

Do not assign the recurring Visit Plan permanently to one engineer.

Each Visit Occurrence must have its own assignment.

Example:

* Q1 → Ahmed
* Q2 → Mohamed
* Q3 → Kareem
* Q4 → Mostafa

Create:

**ClientVisitAssignment**

Fields:

* Id
* ClientVisitOccurrenceId
* UserId
* GroupId nullable
* AssignmentSource
* CreatedAt

Support:

* one engineer
* multiple engineers
* group

# 20. Smart Visit Planner

Create a mobile-friendly **Visit Planner**.

Manager should be able to:

* select Department
* review upcoming visits
* select exact visit date
* assign engineer(s)
* assign group
* select client location
* save/schedule

Example:

**Quarterly Visit — Client A**

Window:

`01-Apr → 30-Jun`

Engineer:

`Mohamed`

Visit Date:

`18-May`

`Save`

# 21. Engineer Suggestions for Visits

Add an optional **Suggest Engineer** feature where practical.

The suggestion may consider:

* Department
* existing shifts
* existing visits
* client location / zone
* engineer workload
* number of assigned visits

Suggestions must remain advisory.

Manager can always override them.

Keep the first algorithm simple and explainable.

# 22. Visit Documents

Engineers must be able to attach documents to the actual Visit Occurrence.

Create/reuse:

**ClientVisitAttachment**

Fields:

* Id
* ClientVisitOccurrenceId
* FileName
* StoredFileReference
* DocumentType
* Description
* UploadedByUserId
* UploadedAt

Document types may include:

* Visit Report
* Signed Form
* Screenshot
* PDF
* Image
* Other

Use the current application's secure attachment/storage architecture.

Include:

* authorization
* file-type validation
* file-size validation
* audit logging

# 23. Visit Completion

Visit Details should allow:

* Actual Visit Date
* Notes
* Result / Summary
* Next Action
* Upload Documents
* Mark Completed

Preserve important changes in the audit history.

# 24. Client Visit Summary

On Client Profile show:

**Visits This Year**

`2 / 4 Completed`

**Remaining:** 2

**Next Visit:** date

Show visit history and upcoming visits.

# 25. Contract-Level Summary

The Contract page may show aggregated client visit information.

Example:

| Client     | Allowed | Completed | Remaining |
| ---------- | ------: | --------: | --------: |
| Cairo      |       4 |         2 |         2 |
| Giza       |       4 |         3 |         1 |
| Alexandria |       2 |         1 |         1 |

Do not convert this into one ambiguous contract-level allowance.

# 26. Client Visit Review Report

Create:

**Reports → Client Visit Review**

Filters:

* Date From
* Date To
* Client
* Contract
* Department
* Engineer
* Group
* Visit Type
* Frequency
* Status
* Zone / Location

KPIs:

* Planned Visits
* Scheduled Visits
* Completed Visits
* Overdue Visits
* Remaining Visits
* Completion %
* Visits by Client
* Visits by Engineer
* Visits by Department
* Visits by Zone

Charts:

* Planned vs Completed
* Visits per Client
* Visits per Engineer
* Completion Trend
* Overdue Visits by Client
* Visits by Zone

# 27. Permissions

Reuse the current privilege system.

Add/reuse privileges for:

* Manage Departments
* Manage Shift Types
* Manage Shift Patterns
* Manage Scheduling Groups
* Create/Edit Weekly Schedule
* Publish Weekly Schedule
* View Other Departments
* View Shift Review
* Manage Client Visit Plans
* Schedule Client Visits
* Assign Visit Engineers
* Complete Client Visits
* Upload Visit Documents
* View Client Visit Review

Do not create duplicate privileges if suitable ones already exist.

# 28. Database Script Requirements

Provide SQL Server migration and metadata scripts.

Scripts must be:

* safe to rerun
* idempotent where possible
* transaction-safe
* compatible with the existing schema
* properly indexed
* FK constrained
* backward compatible

Include initial metadata for:

### Departments

* Support
* Call Center
* Implementation
* Clients
* Sales
* Finance
* HR
* Management

### Shift Types

* Morning
* Evening
* Night
* Weekend Morning
* Weekend Evening
* Weekend Night
* On-Call

For Shift Patterns, only insert defaults if doing so is safe for the current data model. Otherwise provide a separate seed section so they can be reviewed before execution.

Do not assume database table names before inspecting the current schema.

# 29. Implementation Order

Implement incrementally:

1. Inspect the existing schema and modules.
2. Reuse existing Department/Group concepts where possible.
3. Add Department Master Data.
4. Update User Department and scheduling eligibility.
5. Add Shift Type Master Data.
6. Add Dynamic Shift Patterns.
7. Update Shift model for normalized multiple assignments if required.
8. Build Department-aware Weekly Planner.
9. Add Group/Individual assignment.
10. Integrate with existing Shifts page.
11. Add Copy Last Week.
12. Add basic conflict detection.
13. Add workload visibility.
14. Add Shift Review Report.
15. Integrate WFH department filtering.
16. Add Client Visit Plan.
17. Add recurring Visit Occurrences.
18. Add visit assignment.
19. Add Visit Planner.
20. Add document upload and completion.
21. Add Client/Contract visit summaries.
22. Add Client Visit Review Report.
23. Add/reuse permissions.
24. Create SQL migration/metadata scripts.
25. Test mobile and desktop behavior.
26. Run regression tests on existing modules.

Do not perform unrelated refactoring.

# 30. Final Architecture

## Shift Scheduling

**Department**

→ **Eligible Users / Groups**

→ **Shift Type**

→ **Dynamic Shift Pattern / Window**

→ **Weekly Planner**

→ **Existing Shift**

→ **Shift Assignments**

→ **Shift Review**

Examples:

`Support → Night → 4 PM–12 AM`

`Call Center → Night → 12 AM–8 AM`

Both use the same scheduling engine.

## Client Visits

**Contract**

→ **Clients**

→ **Client Visit Plan**

→ **Recurring Visit Occurrences**

→ **Engineer / Group Assignment**

→ **Scheduled Visit**

→ **Visit Documents / Completion**

→ **Visit Review**

The final result must reduce repeated manual entry, support Support and Call Center from the same dynamic planner, remain easy to use from mobile, protect historical records, use normalized database design, and integrate with the current Support Hub instead of creating disconnected modules.

After implementation provide:

* Files changed
* Database schema changes
* SQL migration scripts
* Metadata/seed scripts
* APIs added/changed
* Permissions added/reused
* Screens/components changed
* Reports added
* Regression/test results
* Backward compatibility notes
* Assumptions
* Known limitations
* Recommended future improvements
