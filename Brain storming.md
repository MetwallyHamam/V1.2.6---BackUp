## Ticket Management, Dashboard, and Shift Privilege Requirements

### 1. Ticket Editing After Creation

The system must allow authorized users to edit a ticket after it has been created.

Editable fields should include:

* Ticket subject
* Ticket description
* Priority
* Category and subcategory
* Request type
* Incident classification
* Client
* Assigned engineer
* Support group
* Due date
* Related contract
* Attachments

Ticket editing must be controlled through role-based permissions.

Suggested permissions:

```text
ticket.edit_own
ticket.edit_assigned
ticket.edit_team
ticket.edit_all
ticket.edit_subject
ticket.edit_description
ticket.change_assignment
ticket.change_priority
ticket.change_category
```

Every modification must be recorded in the ticket audit log, including:

* Previous value
* New value
* User who made the change
* Date and time
* Optional change reason

Users without the required permission should see the ticket fields as read-only.

---

### 2. Start Progress Assignment Validation

A user must not be allowed to change a ticket status to **In Progress** unless the ticket is assigned to that logged-in user.

Validation must be applied at both levels:

* Frontend validation
* Backend/API validation

The backend must remain the final authority, even if the frontend button is manipulated.

Example validation logic:

```text
If Ticket.AssignedUserId = LoggedInUserId:
    Allow Start Progress
Else:
    Reject the action
```

Suggested error message:

```text
You cannot start progress on this ticket because it is assigned to another engineer.
```

Users with an administrative override permission may be allowed to bypass this rule.

Suggested override permission:

```text
ticket.start_progress_any
```

---

### 3. Start Progress When Assigned to the Support Group

The ticket may be assigned either to:

* A specific engineer
* A support group or support department without a specific engineer

The **Start Progress** button behavior should be as follows.

#### Ticket assigned to the logged-in engineer

The button is enabled.

When clicked:

* Change the ticket status to In Progress.
* Record the progress start date.
* Record the logged-in user as the working engineer.

#### Ticket assigned to another engineer

The button is disabled.

The system should display a tooltip:

```text
This ticket is assigned to another engineer.
```

#### Ticket assigned to the Support group without a specific engineer

The button is enabled.

When clicked, show a confirmation popup:

```text
This ticket is currently assigned to the Support team.

Starting progress will assign the ticket to you.

Do you want to continue?
```

Buttons:

```text
Assign to Me and Start
Cancel
```

When the user confirms:

1. Assign the ticket to the logged-in user.
2. Keep or update the assigned group as Support.
3. Change the status to In Progress.
4. Record the assignment date.
5. Record the progress start date.
6. Add an entry to the ticket activity history.

Suggested permissions:

```text
ticket.assign_to_self
ticket.start_progress
```

The operation must be executed as one database transaction to avoid assignment conflicts.

If two engineers try to take the same ticket at the same time, only the first successful request should be accepted.

The second user should receive:

```text
This ticket has already been assigned to another engineer.
```

---

### 4. Profile-Based and Customizable Dashboards

The system must support a specific default dashboard for each privilege profile.

Examples of profiles:

* Administrator
* Manager
* Support Manager
* Team Leader
* L1 Support
* L2 Support
* L3 Support
* Call Center
* HR
* Client Portal User
* Contract Manager

Each profile should have a default dashboard containing the widgets relevant to that role.

The system should also allow authorized administrators to customize dashboards by:

* Profile
* Department
* Team
* Individual user

Dashboard configuration priority should be:

```text
User Dashboard
Profile Dashboard
System Default Dashboard
```

This means that a user-specific dashboard overrides the profile dashboard. If no user-specific dashboard exists, the system uses the profile dashboard.

Suggested permissions:

```text
dashboard.view
dashboard.customize_own
dashboard.customize_profile
dashboard.customize_user
dashboard.manage_widgets
```

---

## Manager Dashboard Requirements

The Manager dashboard should include the following widgets.

### Contract Overview

* Total active contracts
* Total inactive contracts
* Contracts pending activation
* Contracts without renewal dates
* Contracts expiring during the current month
* Contracts expiring during the current quarter
* Contracts expiring within 30 days
* Contracts expiring within 60 days
* Contracts expiring within 90 days
* Recently expired contracts
* Contract renewal status
* Contract value, when the user has financial access

Suggested contract statuses:

```text
Draft
Pending Approval
Active
Inactive
Suspended
Expired
Renewal Pending
Renewed
Cancelled
```

The Manager should be able to click any contract widget to open the related filtered contract list.

Example:

```text
Contracts Expiring This Month: 8
```

Clicking the widget should open all eight contracts.

### Engineer Overview

* Total engineers
* Active engineers
* Inactive engineers
* Engineers currently on shift
* Engineers currently available
* Engineers on leave
* Engineers without assigned shifts
* Engineers with overloaded ticket queues
* Engineers grouped by L1, L2, and L3
* Engineers grouped by team or department

### Ticket Status Overview

Display ticket counts for:

* New
* Assigned
* In Progress
* Pending
* Waiting for Client
* Waiting for Internal Team
* Escalated
* Resolved
* Solved
* Closed
* Reopened
* Cancelled

The dashboard should include filters for:

* Today
* This week
* This month
* This quarter
* Custom date range
* Client
* Branch
* Engineer
* Team
* Priority
* Category
* Ticket type
* Contract
* SLA status

### Ticket Statistics

Include:

* Total created tickets
* Total resolved tickets
* Total closed tickets
* Total pending tickets
* Total reopened tickets
* Average first-response time
* Average resolution time
* SLA compliance percentage
* SLA breached tickets
* Tickets approaching SLA breach
* Ticket backlog
* Aging tickets
* Unassigned tickets
* Tickets per engineer
* Tickets per client
* Tickets per category
* Tickets per priority
* Tickets per support level
* Daily, weekly, and monthly ticket trends

Recommended charts:

* Ticket status distribution
* Tickets created versus resolved
* SLA compliance trend
* Tickets by engineer
* Tickets by client
* Tickets by category
* Ticket aging chart
* Contract expiry timeline
* Engineer workload chart

---

### 5. Dashboard Widget Configuration

Each dashboard widget should support configuration such as:

* Widget title
* Widget type
* Data source
* Chart type
* Position
* Width and height
* Refresh interval
* Default filters
* Visibility by role
* Visibility by permission
* Drill-down destination
* Export permission

Suggested widget types:

```text
KPI Card
Table
Bar Chart
Line Chart
Pie Chart
Donut Chart
Calendar
Timeline
Progress Indicator
Alert List
Contract Expiry List
Engineer Workload List
```

Dashboard configurations should be stored in the database rather than hardcoded in the frontend.

Suggested entities:

```text
Dashboard
DashboardWidget
DashboardProfile
DashboardUser
WidgetDefinition
WidgetPermission
```

---

### 6. HR Shift Access and Privileges

The HR role currently cannot see the created shifts. The system must support controlled shift visibility and editing through permissions.

Suggested shift permissions:

```text
shift.view_own
shift.view_team
shift.view_department
shift.view_all
shift.create
shift.edit_own
shift.edit_team
shift.edit_all
shift.delete
shift.publish
shift.assign_employee
shift.approve
shift.export
```

The HR profile should normally have:

```text
shift.view_all
shift.create
shift.edit_all
shift.assign_employee
shift.publish
shift.export
```

The exact permissions must remain configurable by the Administrator.

---

### 7. Shift Visibility Rules

The system should support the following visibility levels:

```text
Own Shifts
Team Shifts
Department Shifts
All Shifts
```

Users should only retrieve shift records they are authorized to see.

The restriction must be enforced in the backend query, not only by hiding the frontend menu.

Example:

```text
HR with shift.view_all:
    Can see all employee shifts.

Team Leader with shift.view_team:
    Can see shifts for employees in their assigned team.

Employee with shift.view_own:
    Can see only their own shifts.
```

---

### 8. Editing Created Shifts

Authorized users must be able to edit created shifts.

Editable fields may include:

* Employee
* Team
* Shift date
* Start time
* End time
* Shift type
* Shift location
* On-call status
* Remote or onsite status
* Notes
* Replacement employee
* Approval status

Shift editing must validate:

* Overlapping shifts
* Duplicate shifts
* Invalid start and end times
* Employee leave
* Employee availability
* Maximum working hours
* Minimum rest period
* Shift capacity
* Required coverage per support level

Every shift modification must be recorded in an audit log.

Audit details should include:

* Shift ID
* Changed field
* Previous value
* New value
* Modified by
* Modification date and time
* Change reason

---

### 9. Published Shift Protection

The system should distinguish between:

```text
Draft Shift
Published Shift
Approved Shift
Completed Shift
Cancelled Shift
```

Editing a published or approved shift may require an additional permission.

Suggested permissions:

```text
shift.edit_draft
shift.edit_published
shift.edit_approved
```

When a published shift is modified, the affected employee should receive a notification.

Notification methods may include:

* In-application notification
* Browser notification
* Email
* SMS, when configured

---

### 10. Recommended Backend Business Rules

The following business rules must be implemented in the backend service layer.

```text
Rule 1:
A ticket cannot start progress when assigned to another engineer.

Rule 2:
A Support-group ticket can be assigned to the logged-in engineer when the engineer confirms Start Progress.

Rule 3:
Assign-to-self and Start Progress must run in one database transaction.

Rule 4:
Only users with ticket-edit permissions can modify ticket fields.

Rule 5:
Every ticket modification must be audited.

Rule 6:
Dashboard data must respect the user's permissions and accessible clients, teams, and departments.

Rule 7:
Shift visibility must be filtered in the backend according to the user's scope.

Rule 8:
Only authorized users can edit, publish, approve, or delete shifts.

Rule 9:
Every shift modification must be audited.

Rule 10:
The backend must reject unauthorized actions even when the frontend button is manually enabled.
```

---

### 11. Suggested Acceptance Criteria

#### Ticket Editing

```text
Given a user with ticket.edit_all permission,
When the user edits the ticket subject or description,
Then the ticket is updated and the old and new values are added to the audit log.
```

```text
Given a user without ticket editing permission,
When the user opens the ticket,
Then the subject and description are read-only.
```
## Notification Enhancements

1. **Mark All as Read**
   Add a **Mark All as Read** button in the Notification Center to mark all notifications belonging to the logged-in user as read and reset the unread counter to zero.

2. **Customize Notification Sound**
   Allow each user to select their preferred notification tone from a predefined list of available sounds. Include a **Play/Test Sound** button before saving.

3. **Customize Notification Volume**
   Allow each user to control the notification volume using a slider from **0% to 100%**, with these optional presets:

   * Low
   * Medium
   * High

The selected sound and volume must be saved in the user’s notification preferences and applied whenever a new notification is received.

#### Start Progress

```text
Given a ticket assigned to Engineer A,
When Engineer B opens the ticket,
Then the Start Progress button is disabled.
```

```text
Given a ticket assigned to the logged-in engineer,
When the engineer clicks Start Progress,
Then the ticket status changes to In Progress.
```

```text
Given a ticket assigned to the Support group without an engineer,
When an authorized engineer clicks Start Progress,
Then a confirmation popup appears.
```

```text
Given the engineer confirms the popup,
Then the ticket is assigned to that engineer and its status changes to In Progress.
```

#### Manager Dashboard

```text
Given a user with the Manager profile,
When the user opens the dashboard,
Then contract, engineer, ticket, SLA, and performance widgets are displayed.
```

```text
Given a contract expires during the current month,
When the Manager opens the contract expiry widget,
Then the contract is included in the result.
```

#### HR Shifts

```text
Given an HR user with shift.view_all,
When the HR user opens the shift calendar,
Then all authorized employee shifts are displayed.
```

```text
Given an HR user with shift.edit_all,
When the HR user modifies a shift,
Then the shift is updated and the change is recorded in the audit log.
```

```text
Given a user without shift.edit permissions,
When the user opens a created shift,
Then the Edit button is hidden or disabled and the backend rejects any edit request.
```
