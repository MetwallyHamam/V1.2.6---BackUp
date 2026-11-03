# Step-by-Step Implementation Plan

## Delivery Strategy

Build the system as vertical slices. Each phase must produce a working, tested increment. Do not generate the entire system in one Codex request.

Recommended release sequence:

- Release 0: foundations
- Release 1: internal ticketing MVP
- Release 2: client portal and contracts
- Release 3: SLA, escalation, notifications, shifts
- Release 4: knowledge, imports, analytics
- Release 5: advanced workflow, integrations, and hardening

## Phase 0 — Discovery and Governance

### Tasks

1. Name the product and repository.
2. Identify data owners and process owners.
3. Confirm user roles and client visibility boundaries.
4. Define ticket classification catalogs.
5. Define contract and SLA models.
6. List required integrations: email, SMS, monitoring tool, Active Directory/Entra ID, and existing iTop data.
7. Decide hosting environment and availability target.
8. Define data retention and backup policies.
9. Document sensitive healthcare data restrictions.
10. Approve MVP and non-MVP scope.

### Deliverables

- Product charter
- Role/permission matrix
- Classification workbook
- SLA matrix
- Data migration inventory
- Architecture decision records

### Exit Gate

No development begins until ownership, scope, and the MVP are approved.

## Phase 1 — Repository and Engineering Foundation

### Backend

1. Create FastAPI application with app factory.
2. Add configuration profiles: local, test, staging, production.
3. Configure SQLAlchemy and pyodbc for SQL Server.
4. Configure Alembic.
5. Add structured logging with correlation IDs.
6. Add API error envelope and exception handlers.
7. Add health, readiness, and version endpoints.
8. Add pytest, coverage, Ruff, mypy, and pre-commit.
9. Add Docker files for local dependencies where useful.

### Frontend

1. Create React/TypeScript application.
2. Add routing and protected-layout shell.
3. Add UI component library and design tokens.
4. Add API client, request interceptors, query cache, and error handling.
5. Add test framework, linting, and formatting.

### Infrastructure

1. Add CI pipeline.
2. Add secret-management rules.
3. Add environment variable validation.
4. Add SQL Server migration deployment process.
5. Add basic observability.

### Exit Gate

- Backend and frontend start locally.
- CI passes.
- Database migration creates the initial schema.
- Health endpoints verify app/database/Redis connectivity.

## Phase 2 — Identity, RBAC, and Organization Structure

### Features

1. Employee authentication.
2. Optional Entra ID SSO adapter.
3. Client authentication.
4. Users, roles, permissions, teams, departments, and memberships.
5. Password reset and account lockout for local accounts.
6. Session/token revocation.
7. Permission-aware navigation.
8. Audit of login, logout, failed login, role changes, and account state changes.

### Security Rules

- Deny by default.
- Every API endpoint declares required permission.
- Client users are scoped to permitted client/branch IDs.
- Administrators cannot silently impersonate; support impersonation requires reason, banner, expiration, and audit.

### Exit Gate

Automated tests prove that users cannot access unauthorized client, branch, ticket, contract, or attachment records.

## Phase 3 — CRM Master Data

### Entities

- Clients
- Client statuses
- Branches/sites
- Contacts
- Contact roles
- Products and modules
- Client installations
- Environments
- Services/service catalog
- Support teams and skills
- Vendors

### Important Client Statuses

- Prospect
- Implementation
- Active
- On Hold
- Suspended
- Expired Contract
- Terminated

### Rules

- Client status controls portal access and ticket entitlement.
- Branches inherit client defaults but may override contact, timezone, working hours, or escalation contacts.
- Product installations identify version, environment, server names, database instances, integrations, and support ownership.
- Sensitive technical credentials must never be stored in normal text fields.

### Exit Gate

Admins can manage master data; agents can search it; all changes are audited.

## Phase 4 — Internal Ticketing MVP

### Features

1. Ticket creation wizard and quick-create form.
2. Automatic human-readable number, e.g. `INC-2026-000123`.
3. Incident, request, problem, change, access, and monitoring alert types.
4. Category, subcategory, service, product, module, and environment.
5. Impact, urgency, priority matrix.
6. Assignment queue, owner, followers/watchers.
7. Public replies and internal notes.
8. Attachments with allowlist, size limits, malware scanning hook, and secure download.
9. Controlled state transitions.
10. Ticket tasks and checklists.
11. Related/parent/child/duplicate ticket links.
12. Ticket timeline/activity stream.
13. Search and list views.
14. Email notification outbox.
15. Audit log.

### Exit Gate

Agents can process a ticket from New to Closed with full history, permissions, validation, and tests.

## Phase 5 — Client Portal

### Features

1. Branded client login.
2. Client dashboard.
3. Create request/incident with guided forms.
4. View only allowed tickets and branches.
5. Public comments and attachments.
6. Ticket confirmation, reopening, and satisfaction survey.
7. Knowledge-base search before ticket submission.
8. Service announcements and maintenance notices.
9. Contact/client administrator management.
10. Contract entitlement summary without exposing confidential internal financial fields.

### Portal Security

- Object-level authorization on every request.
- Prevent ID enumeration.
- Rate limits and lockout.
- Attachment authorization checked at download time.
- No internal notes, internal SLA comments, or internal user details exposed.

### Exit Gate

Cross-client access tests pass for APIs, WebSockets, exports, search, and attachments.

## Phase 6 — Contracts, Entitlements, and SLA Engine

### Contract Features

- Contract number and status
- Start/end dates
- Renewal notice dates
- Covered products, modules, sites, and environments
- Support hours and timezone
- Response and resolution targets
- Included service/request limits
- Exclusions
- Escalation contacts
- Document attachments
- Renewal reminders

### SLA Engine

1. Resolve applicable contract and entitlement.
2. Select SLA policy from ticket type, priority, service, and client.
3. Calculate first-response and resolution targets.
4. Apply business calendar, weekends, holidays, and timezone.
5. Track elapsed and remaining working time.
6. Pause only in configured statuses.
7. Recalculate safely when authorized fields change.
8. Keep an immutable SLA calculation history.

### Exit Gate

A deterministic test suite verifies deadline calculations across weekends, holidays, pauses, timezone boundaries, and priority changes.

## Phase 7 — Assignment and Escalation

### Assignment

- Manual assignment
- Queue assignment
- Round robin
- Least active workload
- Skill-based assignment
- Client/product ownership
- Shift/on-call-aware routing

### Escalation Levels

- Level 0: assignment reminder
- Level 1: team leader
- Level 2: support manager
- Level 3: specialist/management/client escalation contact
- Critical incident path: immediate incident commander and management alert

### Escalation Triggers

- Unassigned duration
- First-response warning/breach
- Resolution warning/breach
- No update for configured duration
- Reopened count
- Client dissatisfaction
- Critical priority
- Patient safety flag
- Repeated incident threshold

### Exit Gate

Rules are configurable, idempotent, tested, and never send duplicate escalation events for the same threshold.

## Phase 8 — Real-Time Alerts and Notification Center

### Channels

- In-app notification center
- WebSocket live event
- Browser desktop notification
- Browser sound
- Email
- Optional SMS integration

### Browser Sound Rules

Browsers generally require user interaction before audio can play. Add an explicit `Enable alert sound` control. Store user preference, allow sound testing, and provide visual fallback when audio is blocked.

### Notification Requirements

- Read/unread state
- Severity
- Deep link
- Deduplication key
- Retry and failure tracking
- Quiet hours
- Per-user channel preferences
- Event templates
- Acknowledgment for critical alerts

### Exit Gate

Notification delivery remains reliable when a browser is disconnected; queued alerts appear after reconnection.

## Phase 9 — Shift Calendar and Workforce Operations

### Features

- Shift types
- Weekly/monthly calendar
- Recurring shifts
- On-call primary and backup
- Leave and absence
- Shift swap request and approval
- Coverage warnings
- Handover notes
- Timezone display
- Team/employee filters
- Export to calendar format later

### Assignment Integration

Assignment rules must exclude unavailable users and prefer active shift/on-call engineers according to service and skill.

### Exit Gate

No double-booking without an explicit override; every override is audited.

## Phase 10 — Knowledge Base

### Features

- Draft, review, approved, published, retired
- Internal and client visibility
- Product/category/tags
- Rich text with sanitized HTML
- Attachments
- Version history
- Article owner and reviewer
- Review/expiry date
- Helpful/not helpful feedback
- Link article to ticket
- Convert resolution to article draft
- SQL Server full-text search or external search adapter later

### Exit Gate

Only approved and authorized content appears in portal search.

## Phase 11 — Excel Master-Data Import

### Process

1. Download controlled template.
2. Upload file.
3. Validate file format, headers, types, references, duplicates, and business rules.
4. Load to staging tables.
5. Display preview and row-level errors.
6. Require confirmation.
7. Commit in controlled batches.
8. Produce result file and audit record.

Never import directly into production tables from the uploaded workbook.

### Exit Gate

Invalid files make zero production changes. Successful imports are repeatable and use idempotency keys.

## Phase 12 — Dashboards, Filters, and Reporting

### Agent Dashboard

- My open tickets
- Due soon
- Breached
- Waiting for me
- Waiting for client
- Reopened
- High priority
- Assigned today
- Recently updated
- Shift/on-call status

### Manager Dashboard

- Open backlog by team/client/product/priority
- SLA compliance
- First-response and resolution time
- Aging buckets
- Reopen rate
- Escalations
- Ticket inflow vs closure
- Workload distribution
- Top incident categories
- Contract expiry
- CSAT

### Advanced Filters

Support nested AND/OR conditions for:

- Ticket number, type, state, priority
- Client, branch, requester
- Product, module, environment
- Queue, owner, team
- Created, updated, due, resolved date ranges
- SLA state and percentage consumed
- Tags and custom fields
- Has attachment, has unread reply, reopened
- Text search

Saved views support private, team, and global scopes with default columns, sorting, grouping, and optional subscriptions.

### Exit Gate

Common list queries are indexed and meet agreed response-time targets using production-like data.

## Phase 13 — Integrations

- Inbound support email to ticket/comment
- Outbound email
- SMS gateway
- Monitoring tool webhook/API
- Entra ID/LDAP
- Existing iTop migration/import
- Optional Teams notifications
- Optional API for other Millensys applications

All integrations require retries, idempotency, correlation IDs, dead-letter handling, and auditability.

## Phase 14 — Hardening and Production Readiness

1. Threat model.
2. Security verification against OWASP ASVS target level.
3. Dependency and container scanning.
4. SAST and secret scanning.
5. Performance/load tests.
6. Restore drill.
7. Disaster recovery test.
8. Failover and worker-restart tests.
9. Accessibility testing.
10. Operational runbooks.
11. User training and pilot.
12. Staged rollout.

## Suggested Timeline

A realistic production-quality system should be planned by capability, not promised as one giant build. A small focused team can target:

- Foundation and internal MVP: 8–12 weeks
- Portal, contracts, SLA, escalation, and alerts: 8–12 additional weeks
- Shifts, knowledge, imports, advanced analytics, and hardening: 8–12 additional weeks

Actual duration depends on team size, data migration, integrations, approvals, and required compliance.
