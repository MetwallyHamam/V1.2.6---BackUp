# Multi-Organization Project Delivery and Product Development Plan

## 1. Purpose

This plan evolves Support Hub from an Egypt-headquarters support system into a company-group platform supporting multiple related organizations, including Egypt and Gulf operations.

The target platform will coordinate:

- Sales intake
- Project planning and management
- Implementation teams and tasks
- Business requirements and approvals
- Development requests
- Development execution and QA/UAT
- Product releases
- Project acceptance
- Handover to Support
- Client delivery history
- Department and group-level dashboards

The existing Support workflow remains specialized and is not reused as the workflow for Projects, Implementation, Business, or Development.

## 2. Core Design Principles

1. Every business record has one accountable organization.
2. Related organizations collaborate through explicit access and work relationships.
3. Internal departments and client departments are separate domains.
4. A Support ticket remains customer-facing and keeps its Support SLA.
5. Other departments receive linked work items rather than repeatedly taking ownership of the Support ticket.
6. Projects, implementation tasks, Development Requests, and releases have independent workflows.
7. All cross-department work remains traceable to its source and downstream delivery.
8. Access control is enforced in backend queries, not only in the user interface.
9. Historical ownership, workflow transitions, approvals, and documents are auditable.
10. The Egypt organization is migrated first without changing existing user behavior.

## 3. Target Organization Structure

```text
Millensys Group
├── Egypt Organization
│   ├── Egypt Sales
│   ├── Egypt Projects
│   ├── Egypt Implementation
│   ├── Egypt Development
│   ├── Egypt Business
│   └── Egypt Support
│
└── Gulf Organization
    ├── Gulf Sales
    ├── Gulf Projects
    ├── Gulf Implementation
    ├── Gulf Development or Shared Development
    ├── Gulf Business
    └── Gulf Support
```

The organizational levels are:

1. Organization group
2. Organization or legal entity
3. Department
4. Team
5. User

Client organizations and client departments are maintained separately.

## 4. End-to-End Business Flow

```text
Sales Deal
    ↓
Projects Department
    ↓
Project Planning and Staffing
    ↓
Implementation Teams
    ↓
Products, Modules, Tasks and Implementation Issues
    ↓
Business and Development Requests when required
    ↓
Development, QA, UAT and Release
    ↓
Implementation Validation
    ↓
Project Acceptance and Required Documents
    ↓
Support Review and Handover
    ↓
Ongoing Support
```

## 5. Multi-Organization Foundation

### 5.1 Organization entities

Create the following entities:

```text
organization_groups
- id
- code
- name
- is_active

organizations
- id
- group_id
- code
- legal_name
- display_name
- country_id
- timezone
- currency
- default_language
- registration_number
- is_active

organization_relationships
- id
- source_organization_id
- target_organization_id
- relationship_type
- effective_from
- effective_until
- is_active
```

Supported relationship types:

- `PARENT`
- `SUBSIDIARY`
- `SERVICE_PROVIDER`
- `SHARED_SERVICE`
- `DELIVERY_PARTNER`
- `ESCALATION_PARTNER`

### 5.2 Organization-scoped departments

Add `organization_id` to internal departments. Department codes become unique within an organization instead of globally.

```text
Unique constraint: organization_id + department_code
```

Both Egypt and Gulf may therefore have a `SUPPORT` department.

### 5.3 User memberships

Create effective-dated memberships:

```text
user_organization_memberships
- user_id
- organization_id
- membership_role
- is_primary
- effective_from
- effective_until

user_department_memberships
- user_id
- department_id
- is_primary
- effective_from
- effective_until
```

A user can have a primary organization and authorized memberships in related organizations.

### 5.4 Organization context

Users with multiple memberships receive an organization selector:

```text
Organization: Egypt | Gulf | Group View
```

The selected organization affects tickets, clients, contracts, projects, implementation work, Development Requests, releases, reports, and dashboards. The backend validates every requested organization context.

### 5.5 Access scopes

Extend permission scopes to support:

- `OWN`
- `TEAM`
- `DEPARTMENT`
- `ORGANIZATION`
- `RELATED_ORGANIZATIONS`
- `GROUP`
- `ALL`

### 5.6 Organization-aware numbering

Recommended number formats:

```text
EGY-TKT-000125
GUL-TKT-000041
EGY-PRJ-000022
GUL-PRJ-000009
EGY-DEV-000318
GUL-DEV-000044
EGY-REL-000052
```

Numbering rules must be configurable per organization and record type.

## 6. Clients and Client Departments

The existing internal department ownership of clients must not represent the client's own departments.

Create:

```text
client_organization_links
- client_id
- organization_id
- relationship_type
- is_primary
- effective_from
- effective_until

client_departments
- id
- client_id
- parent_department_id
- code
- name
- manager_contact_id
- location_id
- is_active

contact_department_memberships
- contact_id
- client_department_id
- role
- is_primary

client_portal_department_access
- portal_user_id
- client_department_id
- can_view_department_requests
- can_approve
```

Client-to-organization relationship types include:

- `ACCOUNT_OWNER`
- `SALES_OWNER`
- `SUPPORT_PROVIDER`
- `IMPLEMENTATION_PROVIDER`
- `CONTRACTING_ENTITY`
- `SHARED_ACCESS`

Example:

```text
Client ABC
├── Contracting organization: Gulf
├── Support provider: Gulf Support
├── Implementation provider: Egypt Implementation
└── Development provider: Egypt Development
```

## 7. Team and Product Ownership

Implementation and Development teams belong to departments and inherit the department organization.

Create:

```text
team_product_links
- team_id
- product_id
- is_primary

team_module_links
- team_id
- product_module_id
- is_primary
```

Example structure:

| Team | Products | Example modules |
|---|---|---|
| ERP Team | ERP | Finance, HR, Inventory |
| HIS Team | HIS | ADT, Billing, Pharmacy |
| PACS Team | PACS, VNA, Workstations | Archive, Viewer, Routing |
| RIS Team | RIS | Scheduling, Reporting, Worklist |
| Integration Team | Integration services | HL7, DICOM, API |

Teams may own several products, and a product may have several contributing teams.

## 8. Project Management

### 8.1 Project entities

Create:

```text
projects
project_manager_assignments
project_products
project_modules
project_teams
project_stakeholders
project_comments
project_documents
project_activity_history
```

Each project contains:

- Project number
- Sales or deal reference
- Client and contract
- Sales organization
- Accountable project organization
- Delivery organization
- Implementation organization
- Support destination organization
- Primary project manager
- Additional project managers/coordinators
- Products and modules
- Planned and actual dates
- Priority, risk, scope, and exclusions
- Overall status and completion percentage

### 8.2 Project workflow

```text
NEW
→ PLANNING
→ READY_FOR_IMPLEMENTATION
→ IMPLEMENTING
→ ACCEPTANCE_PENDING
→ ACCEPTED
→ HANDOVER_PENDING
→ HANDED_OVER
→ CLOSED
```

Additional statuses:

- `ON_HOLD`
- `CANCELLED`

### 8.3 Project permissions

- View own projects
- View department projects
- View organization projects
- Create projects
- Manage project information
- Assign project managers
- Assign implementation teams
- Manage the project baseline
- Manage acceptance
- Submit Support handover
- View group portfolio

## 9. Project Planning, Gantt and Tasks

### 9.1 Planning entities

Create:

```text
project_phases
project_milestones
project_tasks
project_task_assignees
project_task_dependencies
project_task_checklists
project_task_documents
project_task_history
project_baselines
```

### 9.2 Suggested project structure

```text
Project
├── Planning
├── Infrastructure Preparation
├── Product Installation
│   ├── HIS
│   ├── RIS
│   ├── PACS
│   └── ERP
├── Configuration
├── Integration
├── Training
├── UAT
├── Go-Live
├── Acceptance
└── Support Handover
```

### 9.3 Task fields

- Project and phase
- Product and module
- Responsible organization, department, and team
- Assigned users
- Planned and actual dates
- Estimated and actual effort
- Priority and status
- Dependencies
- Completion percentage
- Acceptance criteria
- Required evidence
- Blocked reason
- Client visibility
- Planned or unplanned origin

### 9.4 Task workflow

```text
BACKLOG
→ READY
→ IN_PROGRESS
→ BLOCKED
→ REVIEW
→ COMPLETED
```

Additional statuses:

- `CANCELLED`
- `NOT_APPLICABLE`

Implementation users may create unplanned tasks. Any unplanned task records its reason, effort impact, schedule impact, and whether project-manager approval is required.

### 9.5 Planning views

- List
- Kanban lanes
- Calendar
- Gantt chart
- Portfolio Gantt
- My Tasks
- Team Tasks
- Overdue Tasks
- Blocked Tasks

The Gantt chart displays phases, milestones, dependencies, planned versus actual dates, critical path, progress, and baseline revisions.

## 10. Implementation Workspace

Create:

```text
implementation_issues
implementation_issue_comments
implementation_issue_documents
implementation_issue_links
implementation_checklists
```

Implementation issue types:

- Product defect
- Infrastructure problem
- Integration problem
- Missing client prerequisite
- Scope clarification
- Data migration problem
- Training problem
- Client dependency

Each issue records its project, task, product, module, responsible team, severity, owner, root cause, resolution, blocking impact, and client visibility.

Implementation workspace sections:

- Implementation Now
- My Projects
- My Tasks
- Team Tasks
- Running Tasks
- Overdue Tasks
- Blocked Tasks
- Unplanned Tasks
- Open Issues
- Upcoming Milestones

Confirmed product defects can create linked Development Requests.

## 11. Development Requests

Development receives requests from Projects, Implementation, Support, Business, incidents, problems, UAT, and project tasks.

Development Requests are separate from Support tickets to preserve correct workflows and SLA measurements.

### 11.1 Entities

Create:

```text
development_requests
development_request_stakeholders
development_request_requirements
development_request_acceptance_criteria
development_request_links
development_request_comments
development_request_documents
development_request_history
```

### 11.2 Request fields

- Request number
- Request type
- Requesting organization and department
- Accountable Development organization
- Development team and owner
- Client, project, task, or Support ticket source
- Product and module
- Business owner and business analysts
- Priority and business value
- Requirements and acceptance criteria
- Target release
- Due date
- Client visibility
- Confidentiality level

### 11.3 Request types

- `BUG`
- `NEW_FEATURE`
- `ENHANCEMENT`
- `NEW_MODULE`
- `INTEGRATION`
- `TECHNICAL_DEBT`
- `SECURITY_FIX`
- `DATA_FIX`
- `RESEARCH`

### 11.4 Development Request workflow

```text
DRAFT
→ SUBMITTED
→ BUSINESS_ANALYSIS
→ REQUIREMENTS_READY
→ DEVELOPMENT_TRIAGE
→ APPROVAL_PENDING
→ APPROVED
→ BACKLOG
→ PLANNED
→ IN_DEVELOPMENT
→ CODE_REVIEW
→ QA_TESTING
→ UAT
→ RELEASE_READY
→ RELEASED
→ DELIVERED
→ ACCEPTED
→ CLOSED
```

Alternative statuses:

- `MORE_INFORMATION_REQUIRED`
- `ON_HOLD`
- `DUPLICATE`
- `REJECTED`
- `CANCELLED`

Not every request must use every status. Workflow templates determine the required stages by request type.

## 12. Business Requirements and Approvals

Business participation is mandatory for new modules, new features, major enhancements, and significant process changes.

Assign formal roles:

- Business owner
- Business analyst
- Product owner
- Subject-matter expert
- Business approver
- UAT approver

Required Business Requirements fields:

- Business problem
- Business objective
- Current process
- Proposed process
- User roles
- Functional requirements
- Business rules
- In-scope items
- Out-of-scope items
- Expected business value
- Acceptance criteria
- Regulatory requirements
- Mockups and documents
- Affected products/modules
- Client-specific or general-product classification

A request requiring Business analysis cannot enter Development planning until the requirements are marked ready and approved.

## 13. Development Execution

Create:

```text
development_work_items
development_work_item_assignees
development_dependencies
development_sprints
development_sprint_items
development_test_results
development_code_references
```

A Development Request may be divided into:

- Analysis
- Backend
- Frontend
- Database
- Integration
- Automated testing
- QA
- Documentation
- Deployment

Optional code references include repository, branch, commit, pull request, build number, and CI/CD result. These may be entered manually before repository integration is introduced.

Development views:

- Intake inbox
- Triage queue
- Requirements waiting for Business
- Approved backlog
- Sprint board
- Development in progress
- Code review queue
- QA queue
- UAT queue
- Release-ready queue
- Team and member workload

## 14. Cross-Organization Collaboration

When one organization assists another, the source record remains owned by the requesting organization while a linked collaboration request is assigned to the delivering organization.

Example:

```text
Gulf Support Ticket
    ↓
Owned by Gulf Organization / Gulf Support
    ↓
Development Request
    ↓
Delivered by Egypt Organization / Egypt Development
    ↓
Release returned to Gulf Support
```

This preserves customer ownership, SLA, effort reporting, and accountability.

An ownership transfer is a separate action requiring receiving-organization acceptance.

## 15. Release Management

### 15.1 Release entities

Create:

```text
releases
release_items
release_artifacts
release_approvals
release_documents
release_department_deliveries
release_deployments
release_history
```

### 15.2 Release types

- `MAJOR`
- `MINOR`
- `PATCH`
- `HOTFIX`
- `EMERGENCY`
- `CLIENT_SPECIFIC`

### 15.3 Release requirements

- Product and version
- Owning organization
- Included Development Requests
- Features, enhancements, and fixes
- Release notes
- Database scripts
- Configuration changes
- Installation instructions
- Upgrade prerequisites
- Test results
- Security review
- Known issues
- Rollback procedure
- Supported environments
- Planned and actual release dates

### 15.4 Department delivery

A release may be delivered independently to Projects, Implementation, Support, Business, QA, or UAT in one or several organizations.

Delivery statuses:

- `NOT_REQUIRED`
- `PENDING`
- `DELIVERED`
- `ACKNOWLEDGED`
- `VALIDATION_REQUIRED`
- `ACCEPTED`
- `REJECTED`

Each recipient records delivery date, acknowledgement, validation, acceptance, rejection reason, and follow-up actions.

### 15.5 Source automation

On release delivery:

- Implementation receives the version and deployment guide.
- Project tasks and issues become ready for validation.
- Support receives fixed-version details and release notes.
- Support tickets become ready for customer validation when appropriate.
- Projects receives delivery impact and acceptance updates.
- Business receives functional acceptance tasks.

## 16. Project Acceptance

Create:

```text
project_acceptance_checklists
project_acceptance_requirements
project_acceptance_approvals
```

A project cannot become accepted until all mandatory requirements are satisfied.

Requirements may include:

- Mandatory tasks completed
- Critical issues resolved
- UAT approved
- Training completed
- Go-live completed
- Installation documentation
- Configuration documentation
- Network/infrastructure documentation
- Client acceptance document
- Licensing information
- Support contacts
- Known limitations
- Pending points with owners and dates
- Secure credential transfer
- Project-manager approval
- Client representative approval

Acceptance templates are configurable by project type, contract, product, and organization.

## 17. Handover to Support

The current Project Handovers module becomes the final controlled gateway from an accepted project to Support.

The handover references the source project and contains:

- Client and locations
- Products, modules, and delivered versions
- Project and implementation teams
- Go-live and acceptance dates
- Contract and warranty
- Acceptance evidence
- Configuration and technical documents
- Client contacts and departments
- Known issues and pending points
- Implementation issue history
- Release history
- Access information
- Support entitlement

Support can:

- Accept handover
- Request clarification
- Reject handover with a reason

The project becomes `HANDED_OVER` only after Support acceptance.

After handover:

- Support sees the accepted package and read-only implementation history.
- Support cannot modify the historical project plan.
- Projects and Implementation retain their work history.
- Pending points can create linked Support tickets.
- The client profile receives the complete delivery timeline.

## 18. Client Profile Timeline

The client profile displays:

```text
Deal Received
→ Project Created
→ Planning Completed
→ Implementation Started
→ UAT
→ Go-Live
→ Acceptance
→ Support Handover
→ Ongoing Support
```

It also shows active/historical projects, installed products/modules, project managers, implementation teams, client departments, acceptance documents, handover packages, implementation issues, releases, and Support tickets.

## 19. Dashboards

### 19.1 Projects dashboard

- Active projects
- Projects by lifecycle status
- Projects by client and organization
- Portfolio Gantt
- Project-manager workload
- Planned versus actual completion
- At-risk and delayed projects
- Overdue milestones
- Projects awaiting acceptance
- Projects awaiting Support handover
- Implementation workload by team
- Product implementation distribution

### 19.2 Implementation dashboard

- Implementation Now
- Active teams and projects
- Running tasks
- Tasks starting today
- Overdue tasks
- Blocked tasks
- Unplanned tasks
- Tasks waiting for review
- Team/member workload
- Capacity versus allocation
- Open and critical issues
- Upcoming milestones and go-lives
- Completion by product and team

### 19.3 Development dashboard

- Requests by source organization/department
- Requests awaiting triage
- Requests awaiting Business requirements
- Approved backlog
- Sprint progress
- Developer/team workload
- Code-review and QA queues
- UAT failures
- Release-ready items
- Overdue and blocked requests
- Bugs by product/module
- Planned versus unplanned work
- Releases and hotfix frequency

### 19.4 Business dashboard

- Requirements awaiting action
- Requests awaiting approval
- Features awaiting UAT
- Acceptance tasks
- Requests by product/module
- Released features awaiting acceptance

### 19.5 Support dashboard

- Handovers awaiting review
- Recently accepted projects
- Implementation history linked to tickets
- Fixes awaiting customer validation
- Releases affecting Support
- Known issues and pending points

### 19.6 Management dashboard

- Group-wide portfolio
- Egypt versus Gulf performance
- Cross-organization assistance
- Project and delivery health
- Department capacity and bottlenecks
- Release-delivery performance
- Project-to-Support handover performance
- SLA and workload by organization

All dashboard widgets must support evidence-based drill-through.

## 20. Permissions

Recommended permission families:

### Organization

- `organization.view`
- `organization.manage`
- `organization.switch`
- `organization.view.related`
- `organization.view.group`

### Projects

- `project.view.own`
- `project.view.department`
- `project.view.organization`
- `project.create`
- `project.manage`
- `project.plan.manage`
- `project.team.assign`
- `project.acceptance.manage`
- `project.handover.submit`

### Implementation

- `implementation.project.view`
- `implementation.task.view`
- `implementation.task.update`
- `implementation.task.create_unplanned`
- `implementation.issue.manage`
- `implementation.dashboard.department`

### Development

- `development_request.create`
- `development_request.view.source`
- `development_request.view.department`
- `development_request.triage`
- `development_request.approve`
- `development_request.assign`
- `development_request.transition`

### Business

- `business_requirement.manage`
- `business_requirement.approve`
- `business_acceptance.approve`

### Releases

- `release.create`
- `release.approve`
- `release.publish`
- `release.deliver`
- `release.accept`

### Handover

- `project_handover.prepare`
- `project_handover.review`
- `project_handover.accept`
- `project_handover.reject`

## 21. Notifications and Automation

Generate meaningful notifications for:

- Organization or project assignment
- Team/task assignment
- Due-date warning
- Overdue or blocked work
- Requirement clarification
- Business approval
- Development transition
- QA/UAT result
- Release publication
- Department delivery
- Acceptance rejection
- Support handover review

Support in-app and email delivery. Escalation rules are configurable per organization and workflow. Avoid notifications for insignificant field edits.

## 22. Audit and Traceability

The platform must provide end-to-end traceability:

```text
Sales Deal
→ Project
→ Project Task
→ Implementation Issue
→ Development Request
→ Development Work Items
→ QA/UAT
→ Release
→ Department Delivery
→ Client Deployment
→ Acceptance
→ Support Handover
```

Support-originated work follows:

```text
Support Ticket
→ Problem or Root Cause
→ Development Request
→ Fix
→ Release
→ Support Validation
→ Customer Confirmation
→ Ticket Closure
```

Record status changes, assignments, approvals, ownership transfers, baseline changes, release deliveries, and document changes in immutable audit history.

## 23. Technical Delivery Phases

### Phase 0 — Requirements and architecture

Deliver:

- Approved workflows
- Data dictionary
- Status-transition matrices
- Permission matrix
- Dashboard catalogue
- Document requirement matrix
- Organization-sharing rules
- Definition of done for project, request, release, and handover

### Phase 1 — Multi-organization foundation

- Organization group and organization models
- Organization relationships
- Organization memberships
- Organization-scoped departments and teams
- Active organization context
- Backend organization query scopes
- Organization-aware numbering

### Phase 2 — Egypt migration and Gulf setup

- Create Millensys Group
- Create Egypt Headquarters organization
- Assign existing departments/users/teams to Egypt
- Backfill Egypt ownership on current records
- Verify unchanged Egypt behavior
- Create Gulf organization and departments
- Configure Egypt–Gulf relationships

### Phase 3 — Client and product foundations

- Client-organization links
- Client departments
- Contact department memberships
- Team-product/module ownership
- Contracting/support/implementation provider relationships

### Phase 4 — Project Management core

- Projects and managers
- Products/modules/teams
- Stakeholders, comments, documents, activity
- Project list/detail pages
- Organization/department access scopes

### Phase 5 — Planning and Implementation

- Phases, milestones, tasks, dependencies
- Baselines and Gantt
- Planned/unplanned work
- Implementation workspace
- Implementation issues
- Team/member workload

### Phase 6 — Development Requests and Business

- Intake from Projects, Implementation, Support, and Business
- Requirements and acceptance criteria
- Business gates and approvals
- Triage and Development backlog
- Cross-organization request delivery

### Phase 7 — Development execution and releases

- Development work items and sprints
- QA/UAT results
- Release creation and approval
- Release artifacts and documents
- Multi-department/organization delivery

### Phase 8 — Acceptance and Support handover

- Acceptance templates/checklists
- Required documentation validation
- Handover package generation
- Support review and acceptance
- Historical implementation visibility

### Phase 9 — Dashboards and reporting

- Department dashboards
- Organization dashboards
- Group management dashboard
- Drill-through evidence
- Export and scheduled reports

### Phase 10 — Hardening and rollout

- Security tests
- Performance tuning
- Migration verification
- Pilot organizations
- Training and documentation
- Gradual production rollout

## 24. Migration Strategy

1. Create `Millensys Group`.
2. Create `Egypt Headquarters` as the default organization.
3. Assign every existing internal department, user, team, and profile to Egypt.
4. Backfill existing tickets, clients, contracts, operations, UAT records, handovers, and reports with Egypt ownership.
5. Enable organization-aware security while preserving the automatic Egypt context.
6. Validate that existing Egypt workflows and reports remain unchanged.
7. Create Gulf organization, departments, teams, calendars, profiles, and numbering rules.
8. Configure explicit Egypt–Gulf collaboration rules.
9. Pilot with selected Gulf users and shared-service teams.
10. Enable group reporting after reconciliation checks pass.

Migrations must preserve historical IDs and audit history. Existing Support-ticket ownership must not be rewritten as cross-organization work.

## 25. Testing Strategy

Required automated and UAT coverage:

- Organization isolation
- Related-organization sharing
- Group-level access
- Department/team/user scope
- Client isolation
- Client-department portal visibility
- Project status transitions
- Task dependencies and baselines
- Planned/unplanned task rules
- Development Request transitions
- Business approval gates
- Cross-organization requests
- Release approvals and delivery
- Project acceptance requirements
- Support handover acceptance
- Audit history
- Dashboard calculations
- No double-counting across organizations
- SQL Server migrations and performance
- Existing Egypt workflow regression

## 26. Rollout Plan

1. Multi-organization foundation with Egypt only
2. Gulf organization pilot
3. Projects and Implementation pilot
4. Business requirements pilot
5. Development Request intake
6. Release Management
7. Support handover
8. Group dashboards
9. Organization-wide rollout

Use feature flags so incomplete modules are not exposed prematurely.

## 27. Recommended MVP

The first production milestone should include:

- Multi-organization foundation
- Egypt migration and Gulf configuration
- Organization-scoped permissions
- Client-organization relationships
- Team/product/module ownership
- Project records and managers
- Project phases, milestones, and tasks
- Gantt and list views
- Implementation workspace and issues
- Development Requests from Projects, Implementation, and Support
- Business requirements and approval
- Basic release records and department delivery
- Project acceptance checklist
- Linked Support handover
- Projects, Implementation, and Development dashboards
- Audit history and notifications

Later releases may add advanced capacity planning, native sprint management, repository/CI/CD integrations, financial tracking, customer-facing project access, critical-path optimization, and automated deployment integrations.

## 28. Indicative Timeline

Assuming a dedicated team of approximately four developers, QA support, and active product/process ownership:

| Workstream | Indicative duration |
|---|---:|
| Requirements and architecture | 2–3 weeks |
| Multi-organization foundation | 4–7 weeks |
| Egypt migration and Gulf setup | 2–3 weeks |
| Client and product foundations | 2–3 weeks |
| Project Management core | 3–4 weeks |
| Planning, tasks and Gantt | 4–5 weeks |
| Implementation workspace | 3–4 weeks |
| Development Requests and Business workflow | 4–5 weeks |
| Development execution and Release Management | 5–7 weeks |
| Acceptance and Support handover | 3–4 weeks |
| Dashboards, hardening and rollout | 4–6 weeks |

The multi-organization MVP is expected to require approximately 18–25 weeks. The complete platform is expected to require approximately 34–47 weeks. Estimates depend on staffing, integrations, reporting depth, approval complexity, migration quality, and the availability of business owners for workflow validation.

## 29. Success Measures

- Existing Egypt operations continue without regression.
- Egypt and Gulf data are isolated by default.
- Authorized cross-organization collaboration is explicit and auditable.
- Project progress is visible from deal through Support handover.
- Implementation teams manage planned and unplanned work in one place.
- Development has one governed intake from Projects, Implementation, Support, and Business.
- Business requirements and acceptance decisions are traceable.
- Releases are delivered and acknowledged by each recipient department/organization.
- Support receives a complete, validated handover package.
- Management can compare departments and organizations without double-counting.

## 30. First Decisions Required

Before implementation begins, stakeholders must approve:

1. Exact Egypt and Gulf legal/operational organization structure.
2. Whether Development is organization-specific or a shared group service.
3. Client ownership and service-provider rules.
4. Project, task, Development Request, and release workflows.
5. Cross-organization visibility and transfer rules.
6. Business approval requirements by request type.
7. Required acceptance and handover documents.
8. Numbering formats.
9. Department and organization SLA policies.
10. MVP scope and pilot departments.

