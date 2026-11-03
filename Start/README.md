# Millensys Support Hub

## Ticketing, CRM, Client Portal, Contracts, Knowledge Base, and Workforce Management

Millensys Support Hub is a secure web application for the Millensys Support Department. It combines the most useful concepts from iTop, Zoho Desk, and modern CRM platforms, while adapting workflows to healthcare IT support, RIS, PACS, HIS, LIS, ERP, integrations, SQL Server, Windows Server, IIS, DICOM, HL7, and client contracts.

This repository plan is designed to be implemented incrementally with Codex in VS Code.

## 1. Product Vision

Build one platform where Millensys can:

- Receive incidents, service requests, problems, changes, and access requests.
- Allow clients to create, follow, comment on, and approve tickets through a client portal.
- Manage clients, branches, contacts, systems, installed products, environments, and contracts.
- Calculate SLA deadlines from contract rules, priority, working calendars, holidays, and pauses.
- Escalate tickets automatically and manually.
- Alert agents in real time with browser notifications and optional sounds.
- Schedule employee shifts, on-call rotations, leave, and handovers.
- Store and publish internal and client-facing knowledge articles.
- Import master data from controlled Excel templates.
- Provide professional role-based dashboards, filters, saved views, reports, and exports.
- Maintain a complete audit trail for sensitive changes.

## 2. Recommended Architecture

Start as a **modular monolith**. Do not begin with microservices.

### Backend

- Python 3.13+
- FastAPI
- SQLAlchemy 2.x
- Alembic migrations
- Pydantic settings and schemas
- pyodbc with Microsoft ODBC Driver for SQL Server
- Redis for cache, distributed locks, notification fan-out, and job coordination
- Celery or Dramatiq for durable background jobs
- WebSockets for live ticket and alert updates

### Frontend

- React + TypeScript
- Vite
- Material UI or Ant Design
- TanStack Query
- TanStack Table
- React Hook Form + Zod
- FullCalendar for shifts and operational calendars
- Recharts or Apache ECharts for dashboards

### Database

- Microsoft SQL Server 2022 or later
- Separate application login with minimum permissions
- UTC timestamps in the database
- Temporal/history tables for critical business entities where appropriate
- Full-text search for knowledge articles and optionally ticket descriptions

### Deployment

Initial supported deployment:

- Windows Server or Linux application hosts
- IIS reverse proxy or Nginx
- Uvicorn workers managed by a service/process manager
- SQL Server on a separate database server
- Redis on a protected internal host
- HTTPS only

### Authentication

Preferred:

- Internal employees: Microsoft Entra ID/OpenID Connect SSO
- Client users: secure local accounts initially, with optional client SSO later
- Multi-factor authentication for administrators and privileged roles

## 3. Core Modules

1. Identity, users, roles, permissions, teams, and departments
2. Clients, branches, contacts, products, installations, and environments
3. Contracts, entitlements, SLAs, working calendars, holidays, and renewals
4. Tickets, comments, attachments, tasks, watchers, links, and approvals
5. Classification catalogs: request, incident, problem, change, and access request
6. Assignment, queues, skills, ownership, and dispatching
7. Escalation policies and automated workflow rules
8. Real-time notification center, browser notification, sound, email, and optional SMS
9. Client portal
10. Knowledge base
11. Shift calendar, on-call rotation, leave, handover, and availability
12. Excel master-data import and validation
13. Dashboards, saved views, advanced filters, reports, exports, and subscriptions
14. Administration, audit, configuration, feature flags, and integrations
15. Optional asset/CMDB expansion

## 4. Ticket Types

- Incident: service interruption, error, degraded performance, failed integration, stopped service, or unavailable function.
- Service Request: information, configuration, installation, account, report, or operational request.
- Problem: recurring or high-impact root-cause investigation.
- Change Request: controlled modification requiring risk, plan, approval, implementation, validation, and rollback.
- Access Request: account, permission, role, VPN, or portal access.
- Monitoring Alert: automatically created from Millensys monitoring tools or integrations.

## 5. Ticket Lifecycle

Default statuses:

`New -> Triaged -> Assigned -> In Progress -> Pending Client -> Pending Internal -> Pending Vendor -> Resolved -> Client Confirmation -> Closed`

Additional terminal/control statuses:

`Cancelled`, `Rejected`, `Duplicate`, `Reopened`

Important rules:

- Status transitions must be controlled by a workflow state machine.
- Every transition records actor, timestamp, old state, new state, reason, and source.
- SLA timers pause only for configured pause states.
- Resolution requires resolution code, resolution summary, and affected configuration item when applicable.
- Closure can occur after client confirmation or after a configurable auto-close period.
- Reopening preserves the original ticket number and records the reopen reason.

## 6. Priority Model

Use Impact x Urgency to derive Priority.

| Impact | Urgency | Priority |
|---|---|---|
| Critical | Critical | P1 Critical |
| High | High/Critical | P2 High |
| Medium | Medium/High | P3 Medium |
| Low | Low/Medium | P4 Low |

P1 examples:

- Complete RIS/PACS/HIS outage
- All branches unable to operate
- Patient safety or critical clinical workflow risk
- Data corruption or ransomware indication
- Production integration outage with no workaround

Priority overrides require a reason and audit entry.

## 7. Required Ticket Fields

Common required fields:

- Ticket type
- Client and branch
- Requester/contact
- Channel
- Product/system
- Environment: Production, UAT, DR, Training, Test
- Category, subcategory, and service
- Subject and structured description
- Impact and urgency
- Derived priority
- Affected users/branches
- First occurrence time
- Reproducibility
- Screenshots, logs, error messages, or evidence
- Assigned queue and owner
- Contract and SLA entitlement

Healthcare IT extensions:

- RIS/PACS/HIS/LIS/ERP module
- Modality
- DICOM AE title
- HL7 message type
- Interface/channel name
- Server/application/database name
- Study/accession/order/patient identifiers with masking rules
- Business workflow stage
- Workaround available
- Patient safety flag

Do not store unnecessary patient data. Sensitive identifiers must be masked in UI and logs according to role.

## 8. Main User Roles and Default Profiles

- System Administrator
- Support Manager
- Team Leader
- L1 Agent
- L2 Engineer
- L3/Specialist
- Integration Engineer
- Database Administrator
- Change Approver
- Knowledge Manager
- Contract Manager
- Client Administrator
- Client Requester
- Auditor/Read Only

Use permission policies, not hard-coded role checks. Roles/profiles are bundles of permissions; permissions remain the authorization source of truth. During user creation, an administrator selects a default profile such as Call Center, L1, L2, L3, Support Manager, System Administrator, or Client Portal. Additional profiles and exceptional overrides require controlled authorization and auditing. See `12_USER_PROFILES_AND_PRIVILEGES.md`.

## 9. Project Files

- `01_IMPLEMENTATION_PLAN.md`: phased delivery plan and acceptance gates
- `02_ARCHITECTURE.md`: architecture, modules, runtime design, and deployment
- `03_DATABASE_DESIGN.md`: SQL Server entities, keys, indexes, history, and tenancy
- `04_WORKFLOWS_AND_SLA.md`: ticket lifecycle, SLA, assignment, and escalation
- `05_UI_UX_SPECIFICATION.md`: Zoho-inspired UI, dashboards, filters, views, and portal
- `06_SECURITY_BEST_PRACTICES.md`: authentication, authorization, audit, data protection, and secure SDLC
- `07_TESTING_AND_DEVOPS.md`: test strategy, CI/CD, observability, backups, and release process
- `08_CODEX_EXECUTION_PROMPTS.md`: step-by-step prompts to implement each phase with Codex
- `09_INITIAL_SQL_SCHEMA.sql`: starter SQL Server schema for core entities
- `10_EXCEL_IMPORT_SPEC.md`: import templates, validation, staging, and error handling
- `11_PRODUCT_BACKLOG.md`: epics, user stories, priorities, and MVP scope
- `12_USER_PROFILES_AND_PRIVILEGES.md`: default L1/L2/L3/Call Center/Manager/Administrator/Client Portal profiles and permission matrix
- `.env.example`: configuration example with no secrets

## 10. MVP Definition

The MVP is complete when:

- Employees can sign in and have correct permissions.
- Administrators can manage clients, branches, contacts, teams, users, services, and classifications.
- Agents and client users can create and update tickets.
- Tickets support comments, internal notes, attachments, assignment, status transitions, priority, and SLA deadlines.
- Client users can see only their authorized client/branch data.
- Agents have queue views, advanced filters, saved views, and a dashboard.
- Real-time in-app alerts work; browser sound requires prior user interaction and explicit preference.
- Email notifications are queued and retried.
- All critical actions are audited.
- SQL Server migrations, tests, backup procedures, and deployment documentation exist.

## 11. Non-Goals for the First Release

Do not include these in the first MVP unless absolutely required:

- Microservices
- Native mobile applications
- AI auto-resolution
- Full asset discovery
- Complex omnichannel social media ingestion
- Billing/accounting
- Automatic production changes
- Direct storage of unmasked clinical documents

## 12. Definition of Done

A feature is done only when it has:

- Approved acceptance criteria
- Permission checks
- Server-side validation
- Database migration
- Unit and integration tests
- Audit requirements
- Error handling and user feedback
- Logging and metrics
- API documentation
- UI empty/loading/error states
- Security review
- Deployment notes
- User documentation

## 13. First Commands

The exact commands should be generated after the repository structure is created, but the intended layout is:

```text
support-hub/
  backend/
  frontend/
  infrastructure/
  docs/
  scripts/
  tests/
```

Begin with the prompts in `08_CODEX_EXECUTION_PROMPTS.md`. Execute one phase at a time. Require Codex to run tests and summarize changed files after every step.
