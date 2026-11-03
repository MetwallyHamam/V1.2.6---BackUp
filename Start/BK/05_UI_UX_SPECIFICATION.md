# UI/UX Specification

## 1. Design Direction

Create a professional, information-dense interface inspired by Zoho Desk and iTop, but do not copy their branding or exact layouts.

Principles:

- Fast keyboard-friendly operation for support agents
- Clear status, priority, SLA, and client context
- Consistent side navigation
- Responsive layout for desktop and tablet
- Accessible contrast and focus states
- Minimal full-page reloads
- Progressive disclosure for complex technical fields

## 2. Main Application Shell

### Left Navigation

- Home/Dashboard
- Tickets
- Clients
- Contracts
- Knowledge Base
- Calendar/Shifts
- Reports
- Imports
- Administration

### Top Bar

- Global search
- Quick create
- Current shift/on-call indicator
- Notification bell
- Help/knowledge shortcut
- User profile

## 3. Ticket Workspace

Three-column option:

1. Queue/list pane
2. Ticket detail and conversation
3. Context pane

Context pane tabs:

- Client
- Contract/SLA
- Installation
- Related tickets
- Tasks
- Timeline
- Knowledge suggestions

Ticket header displays:

- Number
- Status
- Priority
- SLA countdown
- Client/branch
- Product/module
- Assignee/team
- Last activity

## 4. List and Grid Behavior

- Server-side pagination/filter/sort
- Column chooser
- Resize and reorder columns
- Pin columns
- Grouping
- Bulk selection
- Bulk actions with permission checks
- Export visible result set
- Saved views
- Share view with team
- Default view per role

## 5. Advanced Filter Builder

Allow nested groups:

```text
(Client = Alfa Scan AND Priority in [P1,P2])
AND
(Status not in [Closed,Cancelled] OR SLA State = Breached)
```

Each field defines allowed operators and value controls. Backend receives a validated filter AST—not raw SQL.

## 6. Saved Views

Properties:

- Name
- Owner
- Scope: Private, Team, Global
- Filter definition
- Columns
- Sort
- Grouping
- Refresh interval
- Dashboard pin
- Optional scheduled email export

## 7. Dashboard Design

Use a configurable 12-column widget grid.

Widget types:

- KPI card
- Trend chart
- Donut/bar chart
- Aging table
- SLA breach table
- Ticket queue
- Contract expiry list
- Shift coverage
- Announcement

All charts must link to the underlying filtered ticket list.

## 8. Client Portal UI

Keep the portal simpler than the agent UI:

- My requests
- Create request
- Service status/announcements
- Knowledge base
- Contract/service coverage
- Contacts
- Profile/security

Ticket creation uses dynamic forms by request type. Ask only relevant questions.

## 9. Notifications and Sound

- Notification bell with unread count
- Toast for high-priority events
- Persistent critical-alert panel until acknowledged
- Preference page for sound, desktop notifications, email, quiet hours, and severity
- `Test sound` button
- Visual indicator if browser blocks sound/notifications

Do not play continuous or repeated sound without controls. Apply cooldown/deduplication.

## 10. Accessibility

Target WCAG 2.2 AA practices:

- Keyboard navigation
- Visible focus
- Semantic labels
- Screen-reader announcements for new alerts
- Do not rely only on color
- Reduced-motion support
- Accessible data table patterns
- Meaningful validation errors

## 11. Required Screens

1. Login/SSO
2. Agent dashboard
3. Ticket list
4. Ticket detail
5. Ticket create/edit
6. Client list/detail
7. Contract list/detail
8. Knowledge list/editor/article
9. Shift calendar
10. Notification center/preferences
11. Reports/dashboard builder
12. Excel import wizard
13. Administration catalogs
14. User/role/permission management
15. Client portal dashboard and ticket pages
