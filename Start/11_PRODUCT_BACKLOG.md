# Product Backlog

Priority labels:

- Must: MVP requirement
- Should: next release
- Could: later enhancement

## Epic 1 — Identity and Access

- Must: Employee login
- Must: Client login
- Must: Role and permission administration
- Must: Team membership
- Must: Client/branch data isolation
- Must: Audit privileged changes
- Should: Entra ID SSO
- Should: MFA enforcement policies

## Epic 2 — CRM

- Must: Clients and statuses
- Must: Branches/sites
- Must: Contacts and branch access
- Must: Products/modules/environments
- Must: Client installation profile
- Should: Vendors and escalation contacts
- Could: Sales opportunity pipeline

## Epic 3 — Tickets

- Must: Incident and service request
- Must: Problem, change, access, monitoring alert classifications
- Must: Comments/internal notes
- Must: Attachments
- Must: Assignment and status workflow
- Must: Priority and categorization
- Must: Timeline and audit
- Must: Related tickets
- Should: Approvals and checklists
- Could: Major incident workspace

## Epic 4 — Client Portal

- Must: Create/view/comment tickets
- Must: Client isolation
- Must: Resolution confirmation/reopen
- Must: Portal knowledge search
- Should: Announcements
- Should: Satisfaction survey
- Could: Client SSO

## Epic 5 — Contracts and SLA

- Must: Contract master data
- Must: Coverage and entitlement
- Must: Business calendars and holidays
- Must: Response/resolution clocks
- Must: Warning/breach tracking
- Should: Renewal reminders
- Could: Usage quotas and billable request tracking

## Epic 6 — Automation

- Must: Email notifications
- Must: Notification center
- Must: WebSocket updates
- Must: Browser alert sound preference
- Must: SLA escalation
- Should: Skill/shift-aware assignment
- Should: SMS
- Could: Teams integration

## Epic 7 — Workforce

- Must: Shift calendar
- Must: On-call primary/backup
- Must: Leave/availability
- Must: Handover
- Should: Shift swap approvals
- Could: Calendar synchronization

## Epic 8 — Knowledge

- Must: Article workflow and visibility
- Must: Search
- Must: Link to tickets
- Should: Convert resolution to draft
- Should: Review expiry
- Could: Suggested articles using semantic search

## Epic 9 — Imports and Reporting

- Must: Validated Excel imports
- Must: Agent dashboard
- Must: Manager dashboard
- Must: Advanced filter builder
- Must: Saved views
- Must: Controlled exports
- Should: Scheduled reports
- Could: Custom dashboard builder

## Sample Acceptance Criteria — Create Incident

Given an authorized employee or client user,
when they submit all required incident fields,
then the system creates one incident with a unique number,
resolves the client/branch entitlement,
derives priority from impact and urgency,
calculates applicable SLA deadlines,
adds an immutable creation activity,
queues notifications exactly once,
and returns the created public identifier.

Invalid or unauthorized client/branch combinations must return a safe error and create no ticket.
