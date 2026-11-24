# Unified Company Operations — Professional Implementation Plan

**Status:** Implementation Steps 1–7 and Step 8.1–8.10 complete; Step 8 is in progress; production rollout not started  
**Prepared:** 2026-11-23  
**System:** Millensys Support Hub  
**Business scope:** Project Management, Implementation, Support, shared customer operations  
**Related plan:** `IMPLEMENTATION_DEPARTMENT_COLLABORATION_PLAN.md`

## Implementation progress

> **How to read this document:** `IMPLEMENTATION STEP 1` through `IMPLEMENTATION STEP 8` are the development execution steps. Numbered headings such as `14.3 Representative APIs` are architecture reference chapters, not implementation steps. Search for `IMPLEMENTATION STEP` to move only between executable steps.

### Searchable implementation-step index

| Search text | Direct link | Status |
|---|---|---|
| `IMPLEMENTATION STEP 1` | [Account and Organization foundation](#implementation-step-1) | DONE |
| `IMPLEMENTATION STEP 2` | [Effective-dated department access](#implementation-step-2) | DONE |
| `IMPLEMENTATION STEP 3` | [Customer hierarchy administration UI](#implementation-step-3) | DONE |
| `IMPLEMENTATION STEP 4` | [Project Portfolio foundation](#implementation-step-4) | DONE |
| `IMPLEMENTATION STEP 5` | [Planning and execution](#implementation-step-5) | DONE |
| `IMPLEMENTATION STEP 6` | [Cross-department collaboration](#implementation-step-6) | DONE |
| `IMPLEMENTATION STEP 7` | [Support readiness and handover](#implementation-step-7) | DONE |
| `IMPLEMENTATION STEP 8` | [Governed analytics and rollout](#implementation-step-8) | **IN PROGRESS — 8.1–8.10 DONE** |
| `IMPLEMENTATION STEP 8.1` | [Governed KPI dictionary](#implementation-step-8-1) | DONE |
| `IMPLEMENTATION STEP 8.2` | [Authorization-aware projections](#implementation-step-8-2) | DONE |
| `IMPLEMENTATION STEP 8.3` | [Project Management dashboard](#implementation-step-8-3) | DONE |
| `IMPLEMENTATION STEP 8.4` | [Implementation dashboard](#implementation-step-8-4) | DONE |
| `IMPLEMENTATION STEP 8.5` | [Support-readiness dashboard](#implementation-step-8-5) | DONE |
| `IMPLEMENTATION STEP 8.6` | [Executive Dashboard enhancement](#implementation-step-8-6) | DONE |
| `IMPLEMENTATION STEP 8.7` | [Migration and reconciliation tooling](#implementation-step-8-7) | DONE |
| `IMPLEMENTATION STEP 8.8` | [Security, performance and rollback hardening](#implementation-step-8-8) | DONE |
| `IMPLEMENTATION STEP 8.9` | [Collaboration master-data administration](#implementation-step-8-9) | DONE |
| `IMPLEMENTATION STEP 8.10` | [Pilot release package](#implementation-step-8-10) | DONE |
| `IMPLEMENTATION STEP 8.11` | [Restored-copy rehearsal](#implementation-step-8-11) | **IN PROGRESS — SQL RESTORED-COPY PASSED** |

**Current completed substep:** [IMPLEMENTATION STEP 8.10](#implementation-step-8-10)  
**Active development substep:** [IMPLEMENTATION STEP 8.11](#implementation-step-8-11)  
**Latest durable checkpoint:** [CODEX STOP POINT](#codex-stop-point)

| Step | Scope | Status | Verified result |
|---|---|---|---|
| 1 | Account and Organization foundation | DONE | Migration `0285_customer_structure`, ORM relationships, governed APIs, optional Client-to-Organization link, audit events, compatibility manifest, focused tests, static analysis, type checks, and clean SQLite migration rehearsal pass. Existing parent-client behavior remains unchanged. |
| 2 | Effective-dated department access policies | DONE | Migration `0286_department_policies`; Organization, Client, and Branch assignments; INHERIT/EXTEND/OVERRIDE resolver; legacy Client grant compatibility; access explanation; impact preview; dedicated permissions; audit and authorization coverage; clean migration, Ruff, Mypy, and focused tests pass. |
| 3 | Customer hierarchy administration UI | DONE | Responsive `/customer-structure` workspace, Account/Organization creation, Client linking, Branch browsing, direct-policy editor, inherited-access explanation, mandatory impact preview, bilingual navigation/content, focused tests, TypeScript, ESLint and production build pass. |
| 4 | Project portfolio foundation | DONE | Migration `0287_project_portfolio`; governed intake and customer scope, ownership, departments/teams, phases, milestones, capacity assignment workflow, portfolio APIs and responsive workspace pass focused verification. |
| 5 | Planning and execution | DONE | Migration `0288_project_execution`; planned/unplanned tasks, approval gate, multi-assignee/dependency contracts, work logs/timers, blockers, evidence, reviews, calculated progress, My Work API and compact execution lanes pass focused verification. |
| 6 | Cross-department collaboration | DONE | Migration `0289_project_collaboration`; governed requests and response history, visibility-classified events, typed same-client ticket links, notifications, project collaboration UI and Support-safe ticket history pass focused verification. |
| 7 | Deployment, UAT and Support handover | DONE | Migration `0290_project_support_handover`; evidence-gated readiness sections, Support decisions, stabilization ownership, residual work and explicit Support activation pass focused verification. |
| 8 | Governed analytics and rollout | IN PROGRESS | Steps 8.1–8.10 delivered governed analytics, read-only reconciliation, reversible hardening, the Company Operations Setup workspace and a controlled pilot release package. Restored-copy rehearsal and an explicit deployment decision remain. |

<a id="implementation-step-1"></a>
## IMPLEMENTATION STEP 1 — Account and Organization foundation

**Status:** DONE  
**Migration:** `0285_customer_structure`

### Delivered contracts

- New `accounts` and `organizations` tables with stable codes, active state, optional owner department, audit timestamps, and Account → Organization relationship.
- Nullable `clients.organization_id` foreign key so current records remain valid until classified and migrated.
- Account and Organization list/create/update APIs under `/api/v1/accounts` and `/api/v1/organizations`.
- Organization filtering by Account and authoritative Organization/Client counts.
- Client create/update/read support for the optional Organization link.
- Existing `client.view` and `client.manage` permissions are intentionally reused until Step 2 introduces the dedicated policy permission family atomically.
- No Account/Organization production data was created and no existing Client was migrated automatically.

<a id="implementation-step-2"></a>
## IMPLEMENTATION STEP 2 — Effective-dated department access policies

**Status:** DONE  
**Migration:** `0286_department_policies`

### Delivered contracts

- Effective-dated department assignment tables for Organization, Client, and Branch scopes.
- Policy modes: `INHERIT`, `EXTEND`, and `OVERRIDE`.
- Safe override rule: inherited departments retain customer visibility as `CUSTOMER_VIEWER`; the local policy replaces operational responsibility without silently removing visibility.
- Organization policy inherits to Clients and then Branches by default.
- Existing `clients.owner_department_id` and `client_department_links` remain recognized as permanent legacy assignments during transition.
- Policy assignments support primary owner, shared operator, viewer, and temporary operator relationships plus named access profiles, start/end time, and reason.
- Effective-access explanation API reports department, relationship, profile, source scope, inheritance, view-only state, and effective period.
- Impact-preview API reports affected Client/Branch counts, added departments, and departments retained for visibility.
- Policy replacement retains prior rows as inactive history and records an audit event with the required change reason.
- Dedicated `customer_structure.policy.view` and `customer_structure.policy.manage` permissions were introduced; existing Client permissions remain accepted during staged rollout.

<a id="implementation-step-3"></a>
## IMPLEMENTATION STEP 3 — Customer hierarchy administration UI

**Status:** DONE

### Delivered contracts

- Dedicated `/customer-structure` workspace under the Customers navigation group.
- Compact three-column hierarchy browser for Accounts, Organizations, Clients, and expandable Branches; it collapses responsively to one column on smaller screens.
- Account and Organization creation without mixing these records into the operational Clients page.
- Existing unassigned Clients can be linked to the selected Organization without changing their historical parent-client relationship.
- Policy drawer shows the full effective-access explanation separately from direct assignments owned by the selected scope.
- Policy editing supports mode, department, relationship, access profile, start/end time, and reason.
- `OVERRIDE` displays the retained-visibility safety rule before submission.
- Impact preview is mandatory before Save and reports affected Client/Branch counts plus added and retained-viewer departments.
- English and Arabic navigation, labels, guidance, validation context, empty states, and success messages.
- Route protection and capability registration support both new policy permission and staged legacy Client access.
- Focused tests prove Organization filtering and direct-only policy serialization, preventing inherited assignments from being copied into local policy.
- Production build creates a separate lazy-loaded `CustomerStructurePage` chunk.

<a id="implementation-step-4"></a>
## IMPLEMENTATION STEP 4 — Project Portfolio foundation

**Status:** DONE  
**Migration:** `0287_project_portfolio`

### Delivered contracts

- Governed Project intake scoped to Account → Organization → Client and optional Branches.
- Accountable Project Management department and project manager ownership.
- Participating departments and reusable teams without duplicating department/team masters.
- Project phases, milestone gates, priority, health, schedule, and calculated progress foundation.
- Implementation capacity requests with Accepted, Proposed, Returned, and Rejected responses.
- Portfolio list, detail, options, summary, planning, phase, milestone, and assignment APIs.
- Responsive Project Portfolio workspace with compact KPIs, filters, hierarchy-aware intake, dense rows, and right-side details.
- Existing legacy `ProjectHandover` remains separate from the governed Project Portfolio.

---

## Architecture and business reference

> The numbered chapters below (`1`, `2`, `9.4`, `14.3`, and similar) explain the target architecture and operating model. They are reference material and must not be interpreted as implementation-step numbers. Use the `IMPLEMENTATION STEP` headings and index above for development progress.

## 1. Executive summary

This plan evolves Support Hub into a unified company operations platform in which Project Management, Implementation, and Support work on the same customer structure without mixing their private work, permissions, workflows, or KPIs.

The target operating model is:

```text
Account
└── Organization
    └── Client
        └── Branch

Customer hierarchy
        +
Department visibility and responsibility rules
        +
Department-specific workspaces and workflows
        +
Governed handovers between departments
```

Example:

```text
Account: Millensys Egypt
└── Organization: UHIA
    └── Client: UHIA Luxor
        └── Branch: UHIA Luxor — Karnak
```

The platform will provide:

- A canonical Account → Organization → Client → Branch structure without duplicated customer records.
- Department ownership, sharing, inheritance, temporary assignments, and explicit overrides.
- Project portfolio and project execution workspaces for Project Management.
- Planned and unplanned delivery workspaces for Implementation.
- Existing ticket and SLA operations for Support.
- Controlled Project Management → Implementation → Support handovers.
- Cross-department requests and shared history without exposing private notes or unrelated KPIs.
- Role-specific dashboards with drilldowns to the exact authorized records behind each number.
- A responsive, accessible, low-clutter UI designed around daily work rather than large decorative cards.

## 2. Goals and success definition

### 2.1 Business goals

1. Give every department a focused workspace while maintaining one governed customer record.
2. Allow work to move between departments without email-only coordination or duplicated data entry.
3. Make project scope, baseline, schedule, ownership, risks, delivery, acceptance, and handover traceable.
4. Distinguish planned implementation work from unplanned work and measure its impact.
5. Give Support the implementation and handover context needed to serve the customer after go-live.
6. Prevent users from seeing another department's private work or KPIs unless explicitly authorized.
7. Support future departments without redesigning the customer hierarchy.

### 2.2 Measurable success outcomes

- Every active project has an accountable manager, owning department, customer scope, approved baseline, and delivery status.
- Every executable task has an owner, classification, dates, status, and evidence or completion summary.
- Every unplanned task has a cause, impact, approval outcome, and baseline reference.
- Every cross-department transfer has an owner, acceptance decision, due time, shared timeline, and audit record.
- Every production handover identifies supported scope, branches, products, known issues, access readiness, documentation, and acceptance evidence.
- Support can see authorized handover and implementation history from the ticket/client context without entering the private Implementation workspace.
- Dashboard totals reconcile with authorized drilldown records.
- Customer structure and department access can change without rewriting historical project, ticket, or KPI evidence.

## 3. Scope and boundaries

### 3.1 Included

- Account, Organization, Client, and Branch hierarchy.
- Department ownership and sharing at Organization, Client, and Branch levels.
- Project portfolio, project phases, milestones, tasks, dependencies, risks, issues, changes, work logs, and evidence.
- Planned and unplanned Implementation work.
- Multi-team and multi-engineer assignment.
- Project Management assignment to one or more Implementation teams.
- Cross-department information and assistance requests.
- Support ticket links to implementation issues/tasks where appropriate.
- Deployment, UAT, acceptance, go-live, stabilization, and Support handover.
- Department, manager, team, engineer, customer, and executive dashboards.
- Notifications, audit, reporting, migration, rollout, and operational controls.

### 3.2 Explicitly excluded from the first release

- Replacing the existing ticket engine or SLA engine.
- Treating project tasks as Support tickets.
- Full ERP, payroll, procurement, or general-ledger functionality.
- Automatic customer-portal publication of internal project information.
- Automatic invoicing from work logs without a separately approved finance design.
- AI-based employee scoring or automated performance decisions.
- Destructive removal of the current parent-client hierarchy before data classification and migration approval.

## 4. Design principles

1. **One customer identity:** store each fact at the highest level where it is universally true; inherit it downward and override only when genuinely different.
2. **Hierarchy is not authorization:** customer structure answers “what entity is this?”; department assignments answer “who may see or manage it?”
3. **Visibility is not responsibility:** a department may view a customer without owning its projects, tasks, tickets, or KPIs.
4. **Department workflows remain distinct:** projects, implementation issues/tasks, and Support tickets are separate business records with typed links.
5. **Independent lifecycles and clocks:** project dates, task targets, handover deadlines, and Support SLAs do not overwrite one another.
6. **Shared history, private detail:** cross-department events are explicit; private notes never leak through shared timelines.
7. **Effective-dated access:** temporary implementation-phase access expires automatically and falls back to inherited access.
8. **Backend-enforced scope:** navigation, hidden buttons, and dashboards never substitute for server authorization.
9. **Evidence-based completion:** significant state changes require the appropriate summary, checklist, approval, or evidence.
10. **Explainable metrics:** every KPI has a definition, time basis, exclusions, owner, and authorized drilldown.
11. **Progressive complexity:** common actions stay simple; advanced controls appear only when needed.
12. **Reuse before duplication:** extend current Department, Project Handover, Work Assignment, Deployment, UAT, ticket, dashboard, notification, and audit capabilities where their contracts fit.

## 5. Target organization and customer model

### 5.1 Canonical hierarchy

| Level | Meaning | Example | Operational records |
|---|---|---|---|
| Account | Millensys commercial/regional portfolio | Millensys Egypt | Portfolio targets, internal ownership, regional defaults |
| Organization | Customer corporate/legal group | UHIA | Organization contacts, shared governance, consolidated reporting |
| Client | Contracted or independently operated customer entity | UHIA Luxor | Contracts, projects, tickets, installations, client KPIs |
| Branch | Physical site or service location | Karnak | Local contacts, address, timezone, equipment, site tasks/tickets |

### 5.2 Classification rule

- If it exists only to group multiple customers, it is an **Organization**.
- If it has independent contracts, SLAs, projects, tickets, billing, or operational KPIs, it is a **Client**.
- If it is mainly a physical location under a client, it is a **Branch**.
- A child client remains a Client only when it is independently operational; it must not be used as a substitute for a Branch.

### 5.3 Parent-client transition

The current `parent_client_id` must remain operational during migration. Existing records require classification:

| Current record | Target | Treatment |
|---|---|---|
| Grouping-only parent client | Organization | Create Organization, move children, retain migration mapping |
| Operational parent with contracts/tickets | Client | Keep as Client and link to an Organization |
| Independent child client | Client | Keep as Client under the same Organization |
| Location represented as child client | Branch | Migrate site data and preserve historical ID mapping |
| Duplicate parent/child/branch | Reviewed target | Merge only through governed deduplication; never silently delete history |

The old hierarchy becomes deprecated only after reporting reconciliation and business sign-off. It is removed in a later release, not in the foundation migration.

## 6. Department visibility and responsibility

### 6.1 Assignment dimensions

An Organization, Client, or Branch department assignment contains:

- Department.
- Relationship: `PRIMARY_OWNER`, `SHARED_OPERATOR`, `VIEWER`, or `TEMPORARY_OPERATOR`.
- Access profile.
- Inheritance mode: `INHERIT`, `EXTEND`, or `OVERRIDE`.
- Effective start and end date/time.
- Optional phase/reason/project reference.
- Granting user, approval, timestamps, and revocation history.

### 6.2 Inheritance behavior

```text
Organization assignment
        ↓ inherited unless changed
Client assignment
        ↓ inherited unless changed
Branch assignment
```

- `INHERIT`: use the effective assignments from the parent.
- `EXTEND`: inherit parent assignments and add local assignments.
- `OVERRIDE`: replace inherited assignments for the defined period.
- When a temporary assignment expires, the system automatically returns to the next valid inherited policy.

### 6.3 Example

```text
UHIA Organization
  Primary owner: Support
  Shared operator: Implementation

UHIA Luxor Client
  Mode: INHERIT

Karnak Branch during implementation
  Mode: EXTEND
  Temporary operator: Implementation Team A
  Effective until: stabilization completion

Karnak Branch after stabilization
  Temporary grant expires
  Effective access returns to the Client/Organization policy
```

### 6.4 Access profiles

Use named profiles instead of forcing administrators to select many low-level permissions repeatedly:

| Profile | Typical capabilities |
|---|---|
| Customer Viewer | View basic profile and approved shared history |
| Project Operator | View customer, projects, tasks, shared contacts and delivery evidence |
| Implementation Operator | Execute assigned implementation work and approved client activities |
| Support Operator | View support context, tickets, supported configuration and handover evidence |
| Customer Manager | Manage profile, assignments, contacts and operational relationships |
| Portfolio Manager | View governed consolidated reporting across authorized descendants |

Sensitive access remains separately controlled: credentials, finance, private notes, employee KPIs, exports, and customer publication.

### 6.5 Critical authorization rule

Sharing an Organization or Client with a department must not automatically expose:

- All Support tickets.
- Private project or task notes.
- Engineer performance details.
- Credentials.
- Finance records.
- Customer-private or security-sensitive attachments.

Customer visibility and record-level work authorization must both succeed.

## 7. Department operating model

### 7.1 Project Management Department

Responsibilities:

- Own project intake, governance, scope, baseline, milestones, schedule, dependencies, risks, changes, and delivery health.
- Create the project and select Account, Organization, Client, and optional Branch scope.
- Assign one Implementation department and one or more teams.
- Coordinate cross-team dependencies and customer commitments.
- Approve or route baseline changes according to governance thresholds.
- Track acceptance, readiness, go-live, stabilization, and final handover.

Project Management does not perform all implementation tasks by default and does not own Support ticket resolution.

### 7.2 Implementation Department

Responsibilities:

- Triage assigned projects and confirm capacity.
- Plan phases, tasks, estimates, dependencies, engineers, and technical deliverables.
- Execute planned tasks and record approved work logs/evidence.
- Register unplanned work with cause, impact, and approval.
- Manage implementation issues, blockers, technical risks, deployments, UAT support, and readiness.
- Prepare operational documentation and handover evidence.
- Provide shared progress to Project Management and Support without exposing private details.

### 7.3 Support Department

Responsibilities:

- Review Support readiness before production handover.
- Validate supported scope, contact/escalation paths, documentation, access readiness, known issues, warranty/stabilization rules, and SLA activation.
- Accept, conditionally accept, or return handover with actionable gaps.
- Own customer-facing production incidents, requests, SLAs, communication, and ticket closure after handover.
- Link relevant tickets to implementation issues without converting every ticket into a project task.

## 8. Team and assignment model

### 8.1 Project roles

```text
PROJECT_SPONSOR
PORTFOLIO_MANAGER
PROJECT_MANAGER
PROJECT_COORDINATOR
IMPLEMENTATION_MANAGER
IMPLEMENTATION_TEAM_LEAD
IMPLEMENTATION_ENGINEER
SUPPORT_READINESS_OWNER
SUPPORT_TEAM_LEAD
REVIEWER
OBSERVER
```

### 8.2 Department and team assignment

A project has:

- One accountable owning Project Management department.
- One accountable project manager.
- One primary Implementation department.
- One or more Implementation teams.
- Optional contributing departments/teams.
- One Support readiness owner before handover.
- Effective membership dates for every user/team assignment.

### 8.3 Team allocation workflow

1. Project Manager selects **Request Implementation Assignment**.
2. Request includes customer scope, project type, dates, required capabilities, priority, and capacity expectation.
3. Implementation Manager reviews capacity and dependencies.
4. Manager accepts, returns for clarification, proposes dates, or rejects with a governed reason.
5. On acceptance, the manager selects a primary team and optional contributing teams.
6. Team leads propose engineers and allocation percentages or planned hours.
7. Project Manager confirms the delivery plan or requests adjustment.
8. Assignment history remains effective-dated and auditable.

Multiple teams can contribute, but every phase/task must have one accountable owner.

## 9. End-to-end workflow

### 9.1 High-level lifecycle

```text
Demand / approved request
        ↓
Project intake and qualification
        ↓
Customer scope and department assignment
        ↓
Implementation assignment and capacity response
        ↓
Planning and baseline approval
        ↓
Execution: planned + governed unplanned work
        ↓
Deployment and UAT
        ↓
Operational readiness review
        ↓
Go-live and stabilization
        ↓
Handover to Support
        ↓
Support operation and project closure
```

### 9.2 Project intake

1. An authorized user creates an intake from an approved contract, customer onboarding, Project Handover, change request, or approved manual request.
2. The user selects Account, Organization, Client, and optional Branches.
3. The system shows the effective department access before submission.
4. Intake captures objective, scope, success criteria, project type, priority, target dates, products/services, constraints, and expected deliverables.
5. Project Management qualifies the request as accepted, returned, duplicate, rejected, or awaiting information.
6. Accepted intake creates a governed project draft idempotently.

### 9.3 Planning and baseline

1. Project Manager defines phases, milestones, deliverables, branch scope, dependencies, assumptions, risks, and acceptance criteria.
2. Implementation Manager assigns teams and capacity.
3. Team leads decompose delivery into planned tasks with estimates, owners, assignees, dates, and expected evidence.
4. The system checks missing owners, invalid dates, overloaded engineers, dependency cycles, branch authorization, and milestone conflicts.
5. The draft schedule can be viewed as List, Board, Timeline, or Workload; all are views of the same records.
6. Project Manager submits the baseline.
7. Required approvers approve, return, or reject with comments.
8. Approval creates an immutable baseline snapshot and starts execution.

### 9.4 Planned task execution

```text
DRAFT → PLANNED → ASSIGNED → ACCEPTED → IN_PROGRESS
                                      ├→ BLOCKED → IN_PROGRESS
                                      ├→ ON_HOLD → IN_PROGRESS
                                      └→ AWAITING_REVIEW → COMPLETED
```

Rules:

- One accountable owner; optional contributors and reviewer.
- Starting records actual start and baseline variance.
- A blocked task requires blocker category, owner, impact, and next-review time.
- Progress changes require a short update; completion requires summary and required evidence.
- Reopening is explicit, reasoned, and audited.
- Project progress is calculated from approved task weights or governed effort, never arbitrary card counts.

### 9.5 Unplanned task workflow

1. Engineer selects **Add unplanned work** from the project, issue, phase, deployment, UAT defect, or task.
2. A compact drawer requests cause, description, source, affected scope, estimate, schedule impact, urgency, and supporting evidence.
3. The system records the active baseline version and discovery time.
4. Policy evaluates whether work can start immediately or requires approval.
5. Approver may approve, reject, request details, defer, or require re-baselining.
6. Approved work follows the normal task lifecycle but remains visibly marked `UNPLANNED`.
7. Actual effort and schedule impact contribute to project variance and root-cause reporting.

Cause codes:

```text
CLIENT_REQUEST
TECHNICAL_DISCOVERY
SCOPE_GAP
DEFECT
DEPENDENCY
ENVIRONMENT
EMERGENCY
REWORK
MANAGEMENT_REQUEST
OTHER
```

### 9.6 Cross-team dependency workflow

1. Task owner creates a dependency/request for another team.
2. The receiving team accepts, proposes a target, requests information, or rejects with reason.
3. Accepted requests receive an accountable owner and service target.
4. Both teams see the same shared status, while private notes remain within their departments.
5. Overdue dependencies appear in manager attention queues and project health calculations.

### 9.7 Deployment and UAT

1. Approved implementation tasks produce deployment candidates.
2. Deployment plan captures environment, steps, owners, validation, rollback, timing, and approvals.
3. Execution records step evidence and issues.
4. UAT uses governed cycles, test cases, defects, retests, and sign-off.
5. Failed validation creates or links an implementation issue; it does not silently rewrite completed task history.
6. Successful deployment/UAT contributes evidence to readiness and handover.

### 9.8 Operational readiness and Support handover

Handover is a workflow, not a document upload.

Required readiness areas:

- Customer, client, and branch scope.
- Production products/modules and supported versions.
- Architecture and environment summary.
- Support contract/SLA readiness.
- Contacts and escalation paths.
- Access/credential readiness without exposing secrets in the handover record.
- Monitoring, backup, recovery, and maintenance responsibilities.
- Known issues, workarounds, residual risks, and warranty obligations.
- Runbooks, knowledge articles, troubleshooting guides, and training evidence.
- Open tasks/issues with accountable owners and target dates.
- Deployment and UAT evidence.
- Customer acceptance and go-live approval.

Workflow:

```text
DRAFT
  → INTERNAL_REVIEW
  → SUBMITTED_TO_SUPPORT
  → SUPPORT_REVIEW
      ├→ CHANGES_REQUIRED → SUBMITTED_TO_SUPPORT
      ├→ CONDITIONALLY_ACCEPTED → STABILIZATION
      └→ ACCEPTED → STABILIZATION or SUPPORT_ACTIVE
  → SUPPORT_ACTIVE
  → PROJECT_CLOSURE_REVIEW
  → CLOSED
```

Support may accept with conditions only when every condition has an owner and due date. Critical readiness failures block activation.

### 9.9 Stabilization period

- Define start/end dates, enhanced monitoring, daily/weekly review frequency, and ownership.
- Issues are classified as implementation defect, operational incident, customer request, configuration, or unrelated.
- Support owns customer ticket communication; Implementation owns assigned implementation corrections.
- Exit requires agreed stability thresholds and closure/transfer of residual work.
- Temporary Branch/Client Implementation assignments can expire automatically at stabilization completion.

### 9.10 Support ticket integration

Use typed relationships:

```text
ORIGINATED_FROM_TICKET
RELATED
REQUIRES_IMPLEMENTATION
REQUIRES_SUPPORT
CAUSED_BY_IMPLEMENTATION
KNOWN_ISSUE
POST_GO_LIVE
```

Rules:

- Ticket and project/issue/task retain independent status and ownership.
- Support SLA never becomes the project task clock.
- Shared updates are explicit events; private comments are not copied.
- Support can view approved handover context and cross-department events from the ticket side panel.
- Implementation can view only the authorized customer-safe ticket context needed for its work.
- Closing one record never automatically closes the other.

## 10. Status models

### 10.1 Project

```text
DRAFT
QUALIFICATION
ASSIGNMENT_PENDING
PLANNING
BASELINE_REVIEW
READY
IN_PROGRESS
ON_HOLD
READINESS_REVIEW
STABILIZATION
HANDOVER_PENDING
COMPLETED
CANCELLED
```

### 10.2 Phase and milestone

```text
NOT_STARTED
READY
IN_PROGRESS
BLOCKED
AT_RISK
COMPLETED
SKIPPED
CANCELLED
```

### 10.3 Task

```text
DRAFT
PENDING_APPROVAL
PLANNED
ASSIGNED
ACCEPTED
IN_PROGRESS
BLOCKED
ON_HOLD
AWAITING_REVIEW
COMPLETED
REJECTED
CANCELLED
```

### 10.4 Issue/risk/change

Use distinct record types with governed lifecycles. Do not combine every concern into a generic task.

- Issue: identified problem requiring resolution.
- Risk: uncertain event with probability, impact, response, and owner.
- Change: proposed scope/schedule/cost/baseline modification with approval.
- Decision: documented choice, alternatives, owner, and effective date.

All state transitions must be centralized in backend services, version-checked, and recorded as append-only events.

## 11. UX and information architecture

### 11.1 UX objectives

- Make the next action obvious.
- Keep daily pages dense enough for professional operations without feeling crowded.
- Avoid oversized KPI cards, excessive whitespace, and wide single-record panels.
- Preserve user context with side drawers for quick detail and full pages for complex work.
- Provide the same filters and terminology across dashboards, lists, boards, and reports.
- Make scope visible at all times: Account / Organization / Client / Branch / Department / Team.

### 11.2 Primary navigation

```text
My Work
Portfolio
Projects
Implementation
Support
Customers
Reports
Administration
```

Navigation is permission-driven. Users see the workspace relevant to their role, not empty modules.

### 11.3 Global customer context

Use a compact breadcrumb/context bar:

```text
Millensys Egypt / UHIA / UHIA Luxor / Karnak
[Support] [Implementation] [Active project: UAT] [Branch override until …]
```

It provides:

- Hierarchy navigation.
- Effective department ownership/sharing.
- Active projects, contract/service state, and Support readiness.
- Clear warnings when the user's access is inherited or time-limited.

### 11.4 My Work

Default landing page for employees:

- My assigned tasks.
- Tasks awaiting acceptance/review.
- Blockers and overdue actions.
- Cross-department requests awaiting response.
- Today's planned work and recent updates.
- Compact workload indicator.

Recommended layout:

```text
┌──────────────────────────────────────────────────────────────┐
│ My Work  [Today] [This week] [Department]   Search / Filters │
├──────────────────────────────────────────────────────────────┤
│ 4 due today │ 2 blocked │ 3 reviews │ 1 dependency overdue  │
├───────────────────────────────┬──────────────────────────────┤
│ Priority work list            │ Schedule / capacity          │
│ Dense rows, inline actions    │ Compact chart + conflicts    │
├───────────────────────────────┴──────────────────────────────┤
│ Recent shared updates and requests                           │
└──────────────────────────────────────────────────────────────┘
```

### 11.5 Portfolio workspace

For Project Management and executives:

- Compact KPI strip, maximum 4–6 KPIs per view.
- Health distribution and trend.
- Milestone forecast.
- Capacity and assignment gaps.
- At-risk projects table with reason and next action.
- Organization/Client/Branch and department filters.
- Saved views and export subject to permissions.

### 11.6 Project workspace

Header:

- Project number/name, customer path, health, status, manager, dates, progress, and next milestone.
- Primary actions grouped into one action menu; dangerous actions separated.

Tabs:

```text
Overview | Plan | Tasks | Issues & Risks | Team | Deployment & UAT
Readiness & Handover | Timeline | Documents | Reports
```

View behavior:

- Single click opens a right-side detail drawer.
- **Open full page** is an explicit action for deep editing.
- No hidden double-click behavior.
- List, board, timeline, and workload views share one filter state.
- Tables use sticky headers, clear column density, saved columns, and pagination-safe selection.

### 11.7 Implementation workspace

Sections:

- Intake/assignment queue.
- Active projects.
- Planned tasks.
- Unplanned tasks and approval queue.
- Blocked work.
- Engineer workload.
- Deployment/UAT actions.
- Handover preparation.

The default view prioritizes actionable rows rather than dashboard decoration.

### 11.8 Handover workspace

Use a guided readiness workspace, not a long form:

```text
Readiness summary: 82%   3 blockers   5 warnings

[1 Scope] [2 Service] [3 Access] [4 Knowledge] [5 Known Issues]
[6 Deployment/UAT] [7 Contacts] [8 Acceptance] [9 Support Review]

Left: checklist and evidence
Right: blocker details, owner, due date, discussion, decision history
```

Show exactly why submission is blocked. Allow Support to return individual sections instead of rejecting the entire handover without detail.

### 11.9 Client profile

The Client Profile becomes the operational customer hub:

- Hierarchy and branches.
- Effective department access.
- Contracts/services.
- Active projects and recent implementation history.
- Support tickets and SLA summary, subject to permission.
- Installations/products.
- Handovers and known issues.
- Contacts, documents, timeline, and statistics.

Organization profile provides consolidated authorized statistics across clients. Account profile provides authorized portfolio statistics across organizations.

### 11.10 Responsive and accessible design

- WCAG 2.1 AA target for contrast, focus, keyboard use, labels, and announcements.
- Desktop: dense split views and tables.
- Tablet: collapsible filter rail and drawer detail.
- Mobile: prioritized work list, bottom-sheet filters, and one-column forms.
- Never rely on color alone for status/health.
- Charts require text summaries and accessible drilldowns.
- Preserve draft input when validation or network errors occur.

## 12. Dashboards and analytics

### 12.1 Dashboard contract

Every metric definition must state:

- Business question.
- Formula and aggregation level.
- Included/excluded statuses.
- Date/time field and timezone.
- Authorization scope.
- Refresh behavior.
- Target/threshold owner.
- Drilldown endpoint and empty-state meaning.

### 12.2 Project Management dashboard

Recommended KPIs:

- Active projects by health.
- On-time milestone rate.
- Forecast completion variance.
- Baseline change rate.
- Projects awaiting assignment/baseline/handover.
- Open risks by exposure.
- Cross-team dependency aging.
- Implementation capacity demand versus confirmed allocation.

Primary analysis:

- Health trend by Account, Organization, Client, department, manager, and project type.
- Schedule variance distribution.
- Milestone forecast table.
- Top blockers and delayed decisions.
- Handover readiness funnel.

### 12.3 Implementation manager dashboard

Recommended KPIs:

- Planned tasks due/completed.
- Unplanned effort percentage.
- Blocked task aging.
- Engineer/team capacity and overload.
- Rework rate.
- First-pass review acceptance.
- Deployment/UAT failure or return rate.
- Handover preparation readiness.

### 12.4 Team lead dashboard

- Work awaiting assignment.
- Engineer workload by day/week.
- Tasks at risk or overdue.
- Blockers awaiting lead action.
- Reviews pending.
- Unplanned requests pending approval.
- Dependency commitments due.

### 12.5 Engineer dashboard

- My active/next tasks.
- Today's plan and logged effort.
- Blocked tasks and requested information.
- Reviews/approvals awaiting me.
- Upcoming milestones/deployments.
- Personal delivery trend shown as operational feedback, not opaque employee ranking.

### 12.6 Support readiness dashboard

- Upcoming go-lives.
- Handovers awaiting Support review.
- Critical readiness blockers.
- Stabilization customers.
- Known issues without workaround/owner.
- Missing knowledge, contact, access, or SLA readiness.
- Post-go-live ticket volume and trend.

### 12.7 Executive dashboard

The Executive Dashboard remains useful when it aggregates authorized outcomes without exposing operational noise:

- Portfolio delivery health.
- On-time delivery and milestone forecast.
- Customer/organization delivery footprint.
- Planned versus unplanned effort trend.
- Capacity risk.
- Go-live/handover pipeline.
- Stabilization and post-go-live quality.
- Support load after handover.
- Major risks, decisions, and exceptions requiring management action.

Executive cards must be compact, limited, trend-aware, and clickable. Empty space should be used for meaningful analysis, not oversized cards.

### 12.8 KPI definitions

```text
Schedule variance days
  = forecast/actual finish date − approved baseline finish date

Unplanned effort %
  = approved unplanned work minutes / total approved work minutes × 100

On-time task rate
  = eligible completed tasks completed by approved due date / eligible completed tasks × 100

Blocked aging
  = current time − latest transition into BLOCKED, excluding approved pause periods

First-pass acceptance
  = tasks approved on first review / reviewed tasks × 100

Handover lead time
  = Support acceptance time − first valid handover submission time

Post-go-live defect rate
  = qualifying implementation-related production defects / agreed normalization basis
```

Metrics must not combine records with incompatible lifecycle meanings.

## 13. Proposed domain and data design

Names are provisional and must follow repository conventions and SQL Server/SQLite compatibility requirements.

### 13.1 Customer hierarchy

```text
accounts
organizations
organization_department_assignments
clients.organization_id
client_department_assignments
branch_department_assignments
customer_hierarchy_migration_map
```

Department assignments carry relationship, access profile, inheritance mode, effective dates, phase/reason, approval, and audit data.

Avoid a generic `entity_type/entity_id` authorization table unless the loss of foreign-key integrity is explicitly accepted. Separate assignment tables with a shared service contract are safer.

### 13.2 Project foundation

```text
projects
project_customer_scopes
project_departments
project_teams
project_members
project_phases
project_milestones
project_baselines
project_baseline_items
project_dependencies
project_events
```

### 13.3 Work execution

```text
project_tasks
project_task_assignees
project_task_dependencies
project_work_logs
project_task_reviews
project_issues
project_risks
project_changes
project_decisions
project_evidence
```

### 13.4 Collaboration and handover

```text
cross_department_requests
cross_department_request_events
ticket_project_links
ticket_implementation_issue_links
project_handovers
project_handover_sections
project_handover_items
project_handover_decisions
stabilization_plans
```

### 13.5 Historical reporting snapshots

Operational records should retain stable customer and organizational context needed for historical reporting. At minimum, baseline/event facts must preserve the effective Account, Organization, Client, Branch, department, team, and responsible owner at the time of the event.

Moving a Client to another Organization must not rewrite last year's project or ticket statistics.

## 14. Service and API architecture

### 14.1 Bounded services

- Customer hierarchy service.
- Effective department-access resolver.
- Project portfolio and lifecycle service.
- Planning/baseline service.
- Task, assignment, dependency, and work-log service.
- Issue/risk/change/decision service.
- Cross-department request service.
- Handover/readiness/stabilization service.
- Reporting projection service.
- Notification/outbox and audit integration.

### 14.2 API principles

- Authorization is enforced inside service/query boundaries.
- List endpoints support server pagination, filters, sort, saved views, and stable totals.
- Mutations use optimistic version checks.
- Creation and handover actions use idempotency keys.
- Bulk actions report per-record success/failure and retain selection across pages safely.
- Shared views use dedicated response schemas that cannot serialize private fields accidentally.
- State transitions use named action endpoints or centralized commands, not arbitrary status patching.

### 14.3 Representative APIs

```text
GET/POST   /api/v1/accounts
GET/POST   /api/v1/organizations
GET/PATCH  /api/v1/clients/{id}/department-policy
GET/PATCH  /api/v1/branches/{id}/department-policy
GET        /api/v1/customer-scope/{type}/{id}/effective-access

GET/POST   /api/v1/projects
GET/PATCH  /api/v1/projects/{id}
POST       /api/v1/projects/{id}/request-implementation
POST       /api/v1/projects/{id}/submit-baseline
POST       /api/v1/projects/{id}/approve-baseline

GET/POST   /api/v1/projects/{id}/tasks
POST       /api/v1/project-tasks/{id}/actions/{action}
POST       /api/v1/project-tasks/{id}/work-logs
POST       /api/v1/projects/{id}/unplanned-work

POST       /api/v1/projects/{id}/handover/submit
POST       /api/v1/project-handovers/{id}/support-decision
POST       /api/v1/project-handovers/{id}/activate-support

GET        /api/v1/dashboards/project-portfolio
GET        /api/v1/dashboards/implementation
GET        /api/v1/dashboards/support-readiness
```

## 15. Permissions and data isolation

### 15.1 Permission families

```text
account.view / account.manage
organization.view / organization.manage / organization.share
client.department_policy.view / client.department_policy.manage
branch.department_policy.view / branch.department_policy.manage

project.view.own / project.view.team / project.view.department / project.view.portfolio
project.create / project.manage / project.baseline.submit / project.baseline.approve
project.team.assign / project.capacity.confirm

implementation.task.view / manage / assign / review
implementation.unplanned.create / approve
implementation.worklog.create / approve
implementation.private_history.view

handover.prepare / submit / review / accept / activate_support
cross_department.request.create / respond / manage

dashboard.project / dashboard.implementation / dashboard.support_readiness
report.project.view / export
```

### 15.2 Visibility matrix

| Record | Project Management | Implementation | Support | Executive |
|---|---|---|---|---|
| Customer basic profile | Authorized scope | Authorized scope | Authorized scope | Aggregated/authorized |
| Project baseline/health | Manage/authorized | Authorized project | Shared summary | Aggregated/authorized |
| Private implementation notes | No by default | Authorized members | No | No |
| Implementation KPIs | Portfolio rules | Team/manager rules | No | Aggregated only |
| Support tickets | Typed link/shared fields only | Typed link/shared fields only | Existing ticket scope | Aggregated only |
| Support KPIs | No by default | No | Support scope | Aggregated only |
| Handover evidence | Manage | Prepare | Review/accept | Status summary |
| Credentials | Separate vault permission | Separate vault permission | Separate vault permission | No |

### 15.3 Field-level sharing

Events, comments, documents, and evidence require visibility:

```text
PRIVATE_TO_TEAM
PRIVATE_TO_DEPARTMENT
PROJECT_SHARED
CROSS_DEPARTMENT
CUSTOMER_VISIBLE
```

`CUSTOMER_VISIBLE` requires a separate publication permission and must never be inferred from `CROSS_DEPARTMENT`.

## 16. Notifications and attention management

Notify users for actionable events, including:

- Assignment request/response.
- Task assignment, return, review, blocker, and overdue target.
- Unplanned-work approval.
- Cross-team dependency response and breach.
- Baseline submission/decision.
- Deployment/UAT action.
- Handover submission, returned section, acceptance, condition, and due condition.
- Temporary access approaching expiry.
- Stabilization review and exit decision.

Controls:

- In-app inbox is authoritative.
- Email/digest preferences avoid notification overload.
- Deduplication keys prevent repeated notices.
- Notifications deep-link to an authorized action view.
- If access is revoked, the notification cannot bypass authorization.

## 17. Audit, evidence, and governance

Audit:

- Hierarchy changes and migration mappings.
- Department policy creation, override, expiry, and revocation.
- Project/customer scope and team changes.
- Baseline versions and approvals.
- Planned/unplanned classification and approval.
- Work-log/review changes.
- Cross-department requests and responses.
- Handover section decisions and final activation.
- Link/unlink operations between tickets and project records.
- Export and sensitive evidence access.

Evidence records retain uploader, hash, MIME type, size, storage identifier, visibility, scan state, version, and download audit where applicable.

## 18. Data migration strategy

### 18.1 Discovery and classification

1. Inventory current clients, parent links, branches, locations, departments, contracts, projects, tickets, contacts, and installations.
2. Produce a review sheet classifying every parent/child/branch record.
3. Detect duplicates, circular/broken relationships, missing locations, and contradictory country data.
4. Obtain business approval for Account and Organization mapping.

### 18.2 Additive migration

1. Add Account and Organization structures without removing current fields.
2. Add new department policies and effective-access resolver.
3. Backfill mappings with explicit provenance and exception reporting.
4. Run old and new hierarchy reads in comparison mode.
5. Reconcile client counts, ticket counts, contracts, active projects, and reports.
6. Enable new UI for pilot users behind a feature flag.
7. Stop writing new parent-client grouping records after adoption.
8. Deprecate old fields only after formal sign-off.

### 18.3 Migration safety

- Never invent legally or operationally meaningful data silently.
- Never delete a source record during the first migration.
- Every transformed record retains source ID and migration batch.
- Migration is restartable and idempotent.
- Exceptions are reported for human review.
- Clean-install and populated SQL Server rehearsals are mandatory.

## 19. Delivery roadmap

### Phase 0 — Discovery and decisions

Deliverables:

- Approved terminology and hierarchy rules.
- Existing-data classification report.
- Department access/inheritance policy.
- KPI dictionary.
- Workflow/state-transition catalog.
- UX prototypes tested with representatives from all three departments.

Exit gate: Product owner, Project Management, Implementation, Support, Security, and Data owners approve the contracts.

### Phase 1 — Customer hierarchy and access foundation

- Accounts and Organizations.
- Client/Branch linkage and migration mapping.
- Effective-dated department policies.
- Access preview and impact analysis.
- Backend authorization and audit tests.
- Customer hierarchy/profile UI.

Exit gate: no cross-department data leakage; old/new data reconciliation passes.

### Phase 2 — Project portfolio foundation

- Project intake, scope, roles, teams, phases, milestones, risks, issues, changes, and events.
- Project assignment/capacity response.
- Portfolio list and project workspace shell.
- Project Management dashboard v1.

Exit gate: a Project Manager can govern intake through approved assignment.

### Phase 3 — Planning and execution

- Baselines and versions.
- Planned/unplanned tasks.
- Multi-assignee work, dependencies, work logs, reviews, and evidence.
- List/board/timeline/workload views.
- My Work, Team Lead, and Implementation dashboards.

Exit gate: one pilot project can be planned, baselined, executed, and measured end to end.

### Phase 4 — Cross-department collaboration

- Cross-department requests.
- Support ticket links and shared events.
- Shared/private field schemas.
- Notifications and escalation targets.
- Client/ticket implementation-history panels.

Exit gate: Support and Implementation can collaborate without sharing private queues or KPIs.

### Phase 5 — Deployment, UAT, readiness, and handover

- Integrate existing Deployment and UAT capabilities.
- Readiness checklist/evidence workspace.
- Support review and conditional acceptance.
- Stabilization plan and exit.
- Support readiness dashboard.

Exit gate: an authorized pilot project reaches Support Active with complete evidence and audit history.

### Phase 6 — Analytics and executive view

- Governed KPI projections and drilldowns.
- Portfolio trends, variance, capacity, handover, and post-go-live quality.
- Organization/Account consolidated reports.
- Executive dashboard enhancement.

Exit gate: every displayed metric reconciles with the authorized source records.

### Phase 7 — Hardening and rollout

- Performance, concurrency, security, accessibility, disaster recovery, and migration rehearsal.
- Training, role guides, operational runbooks, and support procedures.
- Pilot → limited rollout → broad rollout.
- Deprecation plan for replaced navigation/fields.

## 20. Testing strategy

### 20.1 Domain and workflow tests

- Hierarchy cycle and invalid classification prevention.
- Inheritance, extension, override, expiry, and fallback.
- Assignment and team eligibility.
- Baseline immutability and change approval.
- Planned/unplanned classification rules.
- Task lifecycle, dependencies, work logs, review, reopen, and cancellation.
- Handover readiness, return, conditional acceptance, and activation.
- Ticket/project independent lifecycle.

### 20.2 Authorization tests

Test every endpoint and field against:

- Same/different Account.
- Same/different Organization.
- Inherited/shared/overridden/expired customer assignment.
- Project member/non-member.
- Same/different team and department.
- Private/shared/customer-visible records.
- Direct URL/API access, export, notification link, and dashboard drilldown.

### 20.3 UI tests

- Role-based navigation and empty states.
- Drawer/full-page behavior.
- Keyboard and screen-reader operation.
- Responsive layouts.
- Pagination-safe multi-selection.
- Saved filters/views and consistent totals.
- Unsaved-change protection.
- Conflict/version handling.
- Clear validation and retry without lost input.

### 20.4 Performance and reliability

- Large Account/Organization/client portfolios.
- Project/task pagination and complex filters.
- Dashboard query budgets and caching correctness.
- Concurrent assignment, task transition, work-log, baseline, and handover decisions.
- Outbox retry, notification deduplication, and audit persistence.
- Backup/restore and rollback rehearsal.

## 21. Observability and operations

Monitor:

- API latency/error rate by module.
- Authorization denials and suspicious scope probes.
- Dashboard query time and stale projections.
- Notification/outbox lag and retries.
- Overdue workflow actions.
- Migration exceptions and reconciliation differences.
- Attachment/evidence failures.
- Background job and scheduled expiry processing.

Operational tools:

- Effective-access explanation: “Why can this user see this record?”
- Scope impact preview before policy changes.
- Workflow transition history.
- Projection rebuild/reconciliation.
- Safe retry for failed notifications/jobs.
- Feature flags and module kill switches.

## 22. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Organization/client/branch duplication | Incorrect reporting and access | Classification rules, migration mapping, reviewed deduplication |
| Sharing leaks private department work | Security and trust failure | Separate customer scope from record scope; field-level schemas and tests |
| Too many statuses/forms | Poor adoption | Progressive disclosure, role defaults, action-based transitions |
| Dashboards disagree | Loss of confidence | KPI dictionary, centralized projections, reconciled drilldowns |
| Unplanned work becomes a bypass | Baseline and capacity distortion | Mandatory cause/impact, thresholds, approvals, audit |
| Handover becomes document-only | Support readiness gaps | Section workflow, evidence, blockers, decisions, stabilization |
| Matrix assignment lacks accountability | Delays and conflict | One accountable owner at project/phase/task/request levels |
| Historical reports change after hierarchy moves | Incorrect management reporting | Effective-dated relationships and historical snapshots |
| Big-bang rollout disrupts operations | Operational failure | Additive schema, feature flags, pilot rollout, rollback gates |

## 23. Business decisions required before development

1. What legally/operationally distinguishes Organization, Client, and Branch?
2. Can a Client belong to more than one Organization, or exactly one at a time?
3. Which department owns Account and Organization maintenance?
4. Does Organization sharing default to all descendant Clients/Branches?
5. When may a Client/Branch use `OVERRIDE` rather than `EXTEND`?
6. Which records are visible with customer access alone, and which require project/ticket membership?
7. Who approves baseline, unplanned work, re-baselining, and schedule changes at each threshold?
8. How is team capacity measured: percentage, planned hours, calendar availability, or a combination?
9. Which evidence is mandatory before deployment, UAT sign-off, handover, and closure?
10. What constitutes conditional Support acceptance, and which blockers are always critical?
11. How long is stabilization, and who owns defects during it?
12. Which project/implementation data may Support see from a ticket or Client Profile?
13. Which data may be published to the Client Portal, and who approves publication?
14. Which KPI targets are company-wide versus department/project-specific?
15. What retention/export policy applies to work logs, evidence, private notes, and customer-visible events?

## 24. Recommended first production slice

Use one controlled pilot:

- One Account: Millensys Egypt.
- One Organization: UHIA.
- One or two Clients and selected Branches.
- Project Management, one Implementation department/team, and one Support team.
- Customer hierarchy and effective department access.
- Project intake, assignment, baseline, planned/unplanned tasks, blockers, and work logs.
- One controlled deployment/UAT path.
- Readiness and Support handover.
- Shared ticket/implementation history.
- Project, Implementation, and Support readiness dashboards with limited approved KPIs.

Do not include automatic customer publication, finance automation, complex billing, or company-wide employee ranking in the pilot.

## 25. Final acceptance criteria

- The system represents Account → Organization → Client → Branch without duplicated grouping records.
- Department access is inherited, extendable, overridable, effective-dated, explainable, and audited.
- Project Management can intake, assign, baseline, monitor, and hand over projects.
- Implementation can plan and execute multi-team planned/unplanned work with evidence and accurate timing.
- Support can review readiness, accept handover, and access approved implementation history from customer/ticket context.
- Departments cannot view unauthorized private work, tickets, KPIs, finance, credentials, or attachments.
- Every cross-department request and handover has accountable ownership and traceable decisions.
- Role-based UI is clear, responsive, keyboard accessible, and avoids excessive whitespace/oversized cards.
- Dashboard metrics reconcile with their authorized drilldowns and approved definitions.
- Migration preserves current records and history and produces a reviewed exception report.
- Clean and populated SQL Server deployment rehearsals, security tests, accessibility checks, and rollback tests pass before production rollout.

---

<a id="implementation-step-5"></a>
## IMPLEMENTATION STEP 5 — Planning and execution

**Status:** DONE  
**Migration:** `0288_project_execution`

### Delivered contracts

- `project_tasks` preserves project/phase scope, accountable owner, planned dates, estimate, weight, progress, independent lifecycle, completion summary, baseline reference, and planned/unplanned classification.
- `project_task_assignees` and `project_task_dependencies` support several contributing engineers with one accountable owner and same-project dependency validation.
- Every unplanned task requires cause, source, impact, schedule impact, and an auditable `PENDING → APPROVED/REJECTED` decision before execution can begin.
- Task transitions are server-governed across Backlog, Ready, In Progress, Blocked, Review, Done, and Cancelled; completion/review records preserve decision evidence.
- Manual work logs and single-active-user timers preserve independent implementation effort without modifying Support SLA clocks.
- Structured blockers require category, description, owner, impact, and next review; clearing the final open blocker returns the task to Ready.
- `project_evidence` provides typed, visibility-classified evidence metadata while binary evidence storage/upload policy remains a later hardening decision.
- Project progress is calculated from eligible approved task weights and progress, excluding rejected/cancelled work rather than counting cards.
- `/projects/{id}/execution` provides compact lifecycle lanes, planned/unplanned intake, approval visibility, task details, progress, estimate/logged effort, actions, and timer controls.
- `/project-tasks/my-work` provides the authorized personal execution feed; team capacity and analytics projections remain Step 8.
- Support profiles were not granted private implementation execution access. Visibility will be introduced through explicit shared events and typed links in Step 6.

<a id="implementation-step-6"></a>
## IMPLEMENTATION STEP 6 — Cross-department collaboration

**Status:** DONE  
**Migration:** `0289_project_collaboration`

### Delivered contracts

- `cross_department_requests` and append-only `cross_department_request_events` preserve requesting/requested departments, accountable owner, priority, due date, decisions, notes, and actors.
- The request lifecycle supports Pending, Proposed, Accepted, Returned, Rejected, and Completed through validated response actions rather than arbitrary status updates.
- Department members/heads receive in-system request notifications; the requester receives response notifications with deep links to the execution workspace.
- `project_collaboration_events` separates `PROJECT_PRIVATE`, `DEPARTMENT_SHARED`, and `SUPPORT_SHARED` updates. Support ticket history serializes only `SUPPORT_SHARED` events.
- `ticket_project_links` uses approved relationship types and requires the Ticket and Project to belong to the same Client.
- Ticket and project/task lifecycles remain independent: linking or closing one record never mutates the other, and Support SLA clocks remain untouched.
- The Project Execution workspace includes compact Request, Publish Update, and Link Ticket actions plus request/shared-update/link counts.
- Ticket Detail shows an Implementation History panel only when typed links exist and only with approved shared summaries/events.
- Private implementation history requires its own permission and is not granted to Support profiles.

<a id="implementation-step-7"></a>
## IMPLEMENTATION STEP 7 — Support readiness and handover

**Status:** DONE  
**Migration:** `0290_project_support_handover`

### Delivered contracts

- `project_support_handovers`, readiness sections/items, append-only Support decisions, stabilization plans, and residual items form a governed handover package separate from the legacy handover form.
- Initialization creates standard sections for supported scope, operational access, documentation/training, deployment/UAT evidence, and known residual work.
- Required items cannot become Ready when required same-project evidence is missing; readiness percentage is calculated from mandatory items.
- Submission is blocked below 100% readiness and moves the Project into Readiness Review without altering any Support ticket.
- Support can Accept, Conditionally Accept, Request Changes, or Reject with mandatory decision notes and requester notification.
- Activation requires acceptance and a dated stabilization plan with Implementation owner, Support owner, review frequency, and measurable exit criteria.
- Conditional acceptance additionally requires at least one accountable residual item with department, user, severity, and target date.
- Explicit activation starts stabilization, records the activating user/time, and sets Client support commencement only when it was previously unset.
- The execution workspace includes compact readiness progress, evidence-gated section items, submission, Support decision, stabilization, and activation controls.
- Existing deployment and UAT records can supply typed `project_evidence`; direct normalized deployment/UAT foreign-key projection remains part of Step 8 hardening rather than duplicating those mature modules.

<a id="implementation-step-8"></a>
## IMPLEMENTATION STEP 8 — Governed analytics and rollout

**Status:** IN PROGRESS — SUBSTEPS 8.1–8.10 COMPLETE

### Objective

Convert the completed operational foundation into authorization-aware management information and a production-safe pilot release. Step 8 does not mean only adding charts; it includes KPI governance, dashboards, migration/reconciliation tooling, security and performance hardening, and controlled rollout evidence.

### Planned substeps

1. Define the governed KPI dictionary, formulas, eligibility rules, scopes, targets, and authorized drilldowns.
2. Build authorization-aware projection/query services for Project Portfolio, Implementation execution, and Support readiness.
3. Deliver the Project Management dashboard and exact-record drilldowns.
4. Deliver the Implementation department/team/engineer dashboard, including planned versus unplanned effort, estimate accuracy, overdue work, blockers, and review results.
5. Deliver the Support-readiness dashboard, including missing evidence, review queue, residual work, stabilization, and activation risk.
6. Enhance the Executive Dashboard with Account/Organization aggregation and authorized company-level portfolio trends.
7. Build dry-run customer/project migration and reconciliation tooling with exception reports and no automatic destructive classification.
8. Complete access-isolation, audit, performance, concurrency, accessibility, and migration rollback hardening.
9. Deliver a dedicated Collaboration Master Data administration workspace for hierarchy, departments/teams, access profiles, Project/Implementation catalogs, and handover governance; reuse existing governed editors and clearly identify system-controlled definitions.
10. Produce the pilot release package, feature-flag plan, permission matrix, acceptance checklist, backup/rollback instructions, and monitoring plan.
11. Rehearse locally and on a restored database copy; production deployment remains a separate explicit approval.

<a id="implementation-step-8-1"></a>
### IMPLEMENTATION STEP 8.1 — Governed KPI dictionary and authorization contract

**Status:** DONE  
**Migration:** `0291_project_kpi_dictionary`

#### Delivered contracts

- `project_kpi_definitions` stores stable code, domain, formula, numerator/denominator meaning, unit, target direction, zero-denominator policy, time basis, eligibility, exclusions, allowed scopes, owner, version, required permission, and authorized drilldown resource.
- Twelve canonical definitions cover Project delivery, Implementation execution, Support readiness, and Executive aggregation without yet materializing KPI results.
- Permissions are deliberately separated: `analytics.dictionary.view`, `analytics.project.view`, `analytics.implementation.view`, `analytics.support_readiness.view`, and `analytics.executive.view`.
- Role grants are least privilege: Support Manager receives dictionary and Support-readiness access, Project Handover receives operational project/implementation/readiness access, Top Management receives authorized aggregate access, and Administrator receives all five.
- Read-only APIs: `GET /api/v1/project-analytics/kpi-dictionary`, `GET /api/v1/project-analytics/kpi-dictionary/{code}`, and `GET /api/v1/project-analytics/scope-policy`.
- Dictionary access never grants calculated values. Every future projection must independently enforce the metric permission plus effective Account/Organization/Client/Branch and department scope; drilldowns must be equal or narrower.
- SQL Server portability was verified locally. Unsupported `RESTRICT` DDL was normalized to SQL Server's equivalent default `NO ACTION`, and the project-evidence foreign key was corrected to avoid a multiple-cascade path while retaining evidence at Project level.

#### Verification evidence

- Ruff and MyPy passed.
- Focused dictionary, authorization, database-compatibility, and release-revision tests passed.
- Clean SQLite migration reached `0291` with 12 definitions, five permissions, and zero incomplete definitions.
- Authorized local SQL Server database `MillensysSupportHub` at `127.0.0.1` migrated from `0284` through `0291`; application database compatibility reports `READY`.
- No remote or production database was migrated and no customer hierarchy records were classified or converted.

<a id="implementation-step-8-2"></a>
### IMPLEMENTATION STEP 8.2 — Authorization-aware KPI projections

**Status:** DONE  
**Migration:** None — query/service layer only

#### Delivered contracts

- Central projection endpoint: `GET /api/v1/project-analytics/projections/{domain}` for `PROJECT`, `IMPLEMENTATION`, `SUPPORT_READINESS`, and `EXECUTIVE`.
- Exact-record reconciliation endpoint: `GET /api/v1/project-analytics/projections/kpi/{code}/drilldown`.
- Required bounded reporting period plus optional Account, Organization, Client, Department, and Project filters; periods longer than 731 days are rejected.
- Each projection returns status, value, unit, numerator, denominator, eligible count, drilldown count, effective department scope, and whether the caller has global Executive scope.
- Aggregate and drilldown use the same calculation function and authorized Project set, preventing totals from disagreeing with detail records.
- Domain permissions remain independent. Support-readiness access does not grant Implementation results, dictionary access does not grant calculated values, and unauthorized requested departments are rejected.
- Department analytics require Project department participation. Support-readiness additionally recognizes effective customer-department assignments. Executive scope requires the explicit Executive analytics permission.
- Implemented calculations: Project on-time snapshot, at-risk Project count, approved unplanned effort percentage, estimate accuracy, open-blocker aging, first-pass review rate, handover readiness, handover cycle time, open residual count, and cross-department response time.
- `TASK_ON_TIME_RATE` and `MILESTONE_ON_TIME_RATE` deliberately return `UNAVAILABLE`: their entities lack authoritative completion timestamps, and `updated_at` is not accepted as KPI evidence.
- Empty eligible populations follow the governed `NULL` policy for rates/averages and return zero for count metrics.

#### Verification evidence

- Aggregate numerator and denominator contributions reconcile exactly with returned drilldown rows in focused tests.
- Real-login authorization test confirms a Support Manager cannot query Implementation analytics.
- Ruff and MyPy pass across the backend; 30 focused Project/analytics/compatibility tests pass.
- All four projection domains execute successfully against authorized local SQL Server `127.0.0.1/MillensysSupportHub` at revision `0291`.
- SQL Server boolean predicates were verified with the active `pymssql` driver; no schema or customer-data change was required for Step 8.2.

<a id="implementation-step-8-3"></a>
### IMPLEMENTATION STEP 8.3 — Project Management dashboard

**Status:** DONE  
**Migration:** None — frontend presentation over Step 8.2 contracts

#### Delivered UI/UX

- New permission-protected `/project-analytics` workspace and Project Analytics navigation item, visible only with `analytics.project.view`.
- Compact responsive KPI grid: one column on phones, two on tablets, and four on desktop, avoiding oversized cards and excessive whitespace.
- Bounded date filters plus cascading Account → Organization → Client and Department filters; the frontend sends only active filters to the governed projection service.
- Clear distinction between numeric values, no eligible population (`—`), and unavailable metrics with the authoritative data-quality explanation.
- Every available KPI opens a right-side exact-record drilldown showing numerator and denominator contributions and links to the relevant Project execution workspace.
- Dedicated “Projects requiring attention” table is sourced from the same `AT_RISK_PROJECT_COUNT` drilldown, so the displayed count and records cannot diverge.
- Effective-scope indicator distinguishes company-authorized access from department-scoped access without exposing unauthorized customer or department options through analytics responses.
- Accessible loading, error, empty, warning, and success states; responsive table/drawer behavior; English and Arabic navigation labels.
- The screen never recalculates KPI values in the browser and never substitutes `updated_at` for missing completion evidence.

#### Verification evidence

- TypeScript project build and focused ESLint checks pass.
- Four focused Project portfolio/analytics frontend tests pass, including active-filter serialization and local-date stability.
- Production Vite build passes; `ProjectAnalyticsPage` is emitted as its own lazy-loaded chunk of approximately 10.7 kB before gzip.
- Existing Vite warnings concern pre-existing mixed static/dynamic imports and large shared bundles; no new build failure or dashboard-specific bundle warning was introduced.
- Source and production build output were updated locally; no web-server deployment or remote environment change occurred.

<a id="implementation-step-8-4"></a>
### IMPLEMENTATION STEP 8.4 — Implementation department dashboard

**Status:** DONE  
**Migration:** None — governed service and frontend extension

#### Delivered authorization and projection extensions

- Step 8.2 filters now support `team_id` and `user_id` for both aggregate and exact-record drilldown endpoints.
- New `GET /api/v1/project-analytics/options/IMPLEMENTATION` returns only authorized departments, teams, and engineers.
- Non-Executive callers may request only teams owned by an effective department and engineers within their effective department scope; unauthorized requests are rejected server-side.
- Team analytics include Projects assigned to that team and tasks owned by or assigned to its members.
- Engineer analytics include tasks owned by or assigned to that engineer; effort and estimate evidence use that engineer’s own worklogs.
- Selected team/engineer filters are returned in the effective scope response so the UI can show whether it is a department, team, or engineer view.
- Aggregate and drilldown continue to share the same task/worklog authorization set; no cross-department Support work is included merely because the customer is shared.

#### Delivered UI/UX

- New permission-protected `/implementation-analytics` workspace and Implementation Analytics navigation item, visible only with `analytics.implementation.view`.
- Compact five-column desktop KPI grid for approved-unplanned effort, estimate accuracy, blocker aging, first-pass review, and task on-time data quality; responsive one/two-column layouts on smaller screens.
- Bounded reporting period plus cascading Account, Organization, Client, Department, Team, and Engineer filters.
- Dedicated open-blocker focus table linked to the Project execution workspace.
- Right-side evidence drilldown displays exact numerator/denominator contributions and Project links.
- Clear department/team/engineer scope indicator, empty-evidence state, and unavailable completion-time warning.
- English and Arabic navigation labels; no oversized cards, wide empty panels, or duplicated client-side KPI calculations.

#### Verification evidence

- Ruff and MyPy pass across the backend.
- 26 focused analytics, Project execution/portfolio, compatibility, and release-revision backend tests pass, including team/engineer evidence scoping.
- Local SQL Server successfully executes authorized Implementation options and all five Implementation projection definitions at revision `0291`.
- TypeScript and focused ESLint checks pass.
- Five focused Project/Implementation analytics frontend tests pass.
- Production Vite build passes; `ImplementationAnalyticsPage` is emitted as its own lazy-loaded chunk of approximately 11.6 kB before gzip.
- No database migration, customer-data change, web-server deployment, or remote environment change was required.

<a id="implementation-step-8-5"></a>
### IMPLEMENTATION STEP 8.5 — Support-readiness dashboard

**Status:** DONE  
**Migration:** None — governed queue and frontend extension

#### Delivered backend contracts

- New `GET /api/v1/project-analytics/support-readiness/queue` uses the same Account, Organization, Client, Department, Project and effective customer-access authorization as Support-readiness KPI projections.
- Queue summary reports total handovers, submitted reviews requiring Support action, high activation risk, and active stabilization count.
- Each queue row exposes only shared readiness state: readiness percentage, missing required/evidence counts, open/overdue residual counts, stabilization status/end date, and explicit risk reasons.
- Activation-risk explanations distinguish missing evidence, unready required items, absent stabilization plan, overdue residual work, passed stabilization end date, and returned/rejected Implementation action.
- Risk ordering is deterministic (`HIGH`, `MEDIUM`, `LOW`) and does not expose private Implementation task notes or unrelated Support queues.

#### Delivered UI/UX

- New permission-protected `/support-readiness` workspace and Support Readiness navigation item, visible only with `analytics.support_readiness.view`.
- Three compact governed KPI cards for readiness, handover cycle time and open residual work, each with exact-record drilldown.
- Bounded period and cascading Account, Organization, Client and Support Department filters.
- Four dense queue summary cards for handovers, review required, activation risk and active stabilization.
- Operational readiness table combines status, readiness progress, evidence gaps, residual exposure, stabilization state, explicit risk reasons and direct Review action.
- Responsive drawer presents exact readiness item/residual/handover evidence without duplicating KPI calculations.
- English and Arabic navigation labels plus clear empty, loading, error, success and risk states.

#### Verification evidence

- Ruff and MyPy pass across the backend.
- 28 focused analytics, handover, collaboration, compatibility and revision backend tests pass, including explained activation-risk coverage.
- Local SQL Server successfully executes all three Support-readiness projections and the governed queue at revision `0291`.
- TypeScript and focused ESLint checks pass.
- Six focused Project/Implementation/Support-readiness frontend tests pass.
- Production Vite build passes; `SupportReadinessAnalyticsPage` is emitted as its own lazy-loaded chunk of approximately 10.9 kB before gzip.
- No database migration, customer-data change, web-server deployment, or remote environment change was required.

<a id="implementation-step-8-6"></a>
### IMPLEMENTATION STEP 8.6 — Executive Dashboard enhancement

**Status:** DONE  
**Migration:** None — governed service and existing Executive Dashboard extension

#### Delivered backend contracts

- New `GET /api/v1/project-analytics/executive/portfolio` returns an authorized Account/Organization Project portfolio using the same Executive scope policy as the governed KPI projections.
- Portfolio totals include visible Projects and at-risk Projects; each hierarchy row includes Project count, at-risk count, average progress, handover count and average readiness.
- Account and Organization names are resolved server-side only after the caller's authorized Project set is established.
- Executive Project risk and cross-department response metrics continue to use the Step 8.2 projection and exact-record drilldown contracts, preventing UI-only calculations or broader detail access.
- Empty authorized populations return valid zero totals and no rows; hierarchy filters cannot broaden the effective Executive scope.

#### Delivered UI/UX

- The existing `/dashboard` Executive overview now includes a compact Unified Company Operations panel; no duplicate Executive page or navigation route was introduced.
- Cascading Account and Organization filters reuse the dashboard reporting period and are sent to both the portfolio and governed KPI services.
- Four dense summary cards show visible Projects, at-risk Projects and the two Executive KPIs without oversized cards or wide empty sections.
- A compact Account/Organization table presents progress, handovers and readiness with clear risk emphasis and a bounded scroll area.
- Clicking a governed KPI opens a right-side exact-record evidence drawer with Project links.
- Direct links connect executives to Project Management, Implementation and Support-readiness analytics while those pages retain their own permissions.
- Loading, error, empty and scope-explanation states are explicit; values are never recalculated in the browser.

#### Verification evidence

- Ruff and MyPy pass for the Executive analytics backend changes.
- 26 focused analytics, Project portfolio, database-compatibility and release-revision backend tests pass, including Account/Organization aggregation coverage.
- The configured local SQL Server (`mssql`, `127.0.0.1/MillensysSupportHub`, revision `0291`) successfully executes the Executive portfolio and both Executive KPI projections. Its current 30-day authorized sample contains zero Projects, correctly returning an empty portfolio rather than an error.
- TypeScript and focused ESLint checks pass.
- Twelve focused Executive/Project/Implementation/Support-readiness/dashboard frontend tests pass.
- Production Vite build passes. Existing mixed-import and shared-chunk size warnings remain non-blocking and were not introduced by this panel.
- No schema migration, customer-data change, web-server deployment, permission rollout, or remote/production change occurred.

<a id="implementation-step-8-7"></a>
### IMPLEMENTATION STEP 8.7 — Dry-run migration and reconciliation tooling

**Status:** DONE  
**Migration:** None — read-only evidence tooling

#### Delivered reconciliation contracts

- `app.modules.projects.migration_reconciliation` builds deterministic Account/Organization/Client/Branch and Project reconciliation evidence without flushing, committing, or changing ORM records.
- Independent before/after database snapshots cover Accounts, Organizations, Clients, legacy parents/children, Branches, Projects, and Clients lacking Organization links.
- Every Client receives a traceable classification, confidence, rationale, reference counts and `automatic_action: NONE`.
- Grouping parents with children and no direct ticket, contract or Project evidence are review-only Organization candidates.
- Parent-named child records with no direct operational evidence are review-only Branch candidates; conversion is never authorized from name similarity alone.
- Operational parents remain Clients. Duplicate/ambiguous structures are not merged or deleted.
- Project reconciliation validates Project → Account → Organization → Client → primary Branch consistency and emits critical exceptions for broken hierarchy keys.
- Exceptions carry severity, stable code, entity identity, detail and required review action.
- CLI output supports structured JSON, UTF-8 CSV exceptions and human-readable Markdown. It has no apply mode and explicitly rolls back its session.

#### Execution command

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m scripts.reconcile_company_structure `
  --json-report <review-path>\reconciliation.json `
  --exceptions-csv <review-path>\exceptions.csv `
  --markdown-report <review-path>\reconciliation.md
```

#### Verification evidence

- Ruff and strict MyPy pass for the reconciliation service and CLI.
- Eighteen focused reconciliation, Project portfolio, database-compatibility and release-revision tests pass.
- Tests prove grouping/Branch suggestions remain review-only, critical Project hierarchy mismatches are detected, before/after counts match and Client timestamps are unchanged.
- A real read-only rehearsal against local SQL Server `127.0.0.1/MillensysSupportHub` at revision `0291` generated all three report formats.
- The local baseline contains 422 Clients, one legacy parent grouping, two child Clients, 76 Branches, zero Accounts, zero Organizations and zero unified Projects.
- All 422 Clients are currently unlinked from an Organization and were therefore reported as high-severity mapping exceptions. This is expected migration evidence, not an automatic failure or authorization to classify them.
- Independent before/after snapshots were identical and the report recorded zero automatic changes.
- Evidence files were written only to the operating-system temporary directory; no customer record, schema, repository migration, web deployment or remote/production environment was changed.

<a id="implementation-step-8-8"></a>
### IMPLEMENTATION STEP 8.8 — Security, performance, concurrency, accessibility and rollback hardening

**Status:** DONE  
**Migration:** `0292_unified_ops_hardening`

#### Delivered database and concurrency hardening

- A filtered unique index on `project_work_logs(user_id)` where `is_timer = 1` and `ended_at IS NULL` enforces one active Project timer per engineer at database level, closing the race left by application-only checking.
- SQL Server and SQLite use explicit filtered-index predicates, and the ORM metadata carries the same invariant for test-schema parity.
- Composite hierarchy index supports Account → Organization → Client active Project filtering.
- Department/Project scope index supports authorization and departmental analytics joins.
- Status/update/Project handover index supports the Support-readiness review queue.
- Compatibility head advanced to `0292_unified_ops_hardening`; revision identifiers remain within Alembic's default 32-character version column.

#### Security, audit and accessibility evidence

- Focused permission tests confirm analytics domains remain independent and unauthorized Implementation projection requests return `403` without evidence leakage.
- Existing Project collaboration coverage verifies private events remain excluded without the private-history permission, while Support-shared history remains intentionally visible.
- Existing Project, execution, collaboration and handover mutation tests continue to verify permission gates and audit-event creation after the index changes.
- Executive KPI actions, the Account/Organization portfolio table, progress indicators, evidence drawer and loading state now have explicit accessible names/labels.
- Permission-route tests confirm users without the required frontend permission are redirected to the access-denied experience.

#### Upgrade, rollback and verification evidence

- Ruff and strict MyPy pass for the hardening migration/model changes.
- Thirty-four focused analytics, execution, collaboration, handover, reconciliation, compatibility and revision backend tests pass.
- An isolated clean SQLite database successfully rehearsed: full upgrade to `0292` → downgrade to `0291` → re-upgrade to `0292`; all hardening indexes were restored.
- The authorized local SQL Server upgraded forward from `0291` to `0292`; inspection confirms the unique active-timer index plus hierarchy and handover indexes exist.
- The local SQL Server was not downgraded and no customer/business record was modified.
- TypeScript, focused ESLint, seven permission/analytics frontend tests and the production Vite build pass.
- Existing mixed static/dynamic import and shared-bundle size warnings remain non-blocking and pre-existing.

<a id="implementation-step-8-9"></a>
### IMPLEMENTATION STEP 8.9 — Collaboration master-data administration

**Status:** DONE  
**Migration:** None — administration workspace over existing governed sources

#### Delivered UI/UX

- New permission-protected `/company-operations-setup` workspace and Company Operations Setup navigation entry.
- One compact administration map covers company/customer hierarchy, departments/teams/people, collaboration access governance, Project/Implementation setup, Support handover governance and system-controlled definitions.
- Each editable area links to its existing authoritative editor (`/customer-structure`, `/crm`, `/projects`, or `/support-readiness`) instead of creating duplicate forms and conflicting sources of truth.
- Permission-aware actions distinguish management from review access.
- Governed editor and system-controlled badges make editability explicit.
- Access profiles, task classifications, evidence types, the handover template and KPI dictionary are clearly presented as read-only system definitions until configurable persistence, versioning and approval rules are authorized.
- The workspace warns that the current local migration baseline has 422 Clients awaiting approved Organization mapping before pilot Project creation.
- English and Arabic navigation labels, responsive two-column/one-column layout, accessible link actions and clear governance explanations are included.

#### Verification evidence

- TypeScript and focused ESLint checks pass.
- Seven focused setup, hierarchy, Project and permission-route frontend tests pass.
- Production Vite build passes and emits `CompanyOperationsSetupPage` as a dedicated lazy-loaded chunk of approximately 4.4 kB before gzip.
- Existing shared-bundle and mixed-import warnings remain non-blocking and pre-existing.
- No database migration, customer classification, permission grant, web-server deployment or remote/production change occurred.

The next governance decision is whether system-controlled definitions should remain versioned release configuration or become editable effective-dated catalogs. That decision is not required for pilot packaging because their current definitions are explicit and stable.

<a id="implementation-step-8-10"></a>
### IMPLEMENTATION STEP 8.10 — Pilot release package and operational controls

**Status:** DONE  
**Migration:** None — release-governance documentation only

The companion [Unified Company Operations Pilot Release Package](UNIFIED_COMPANY_OPERATIONS_PILOT_RELEASE_PACKAGE.md) defines the feature-control decision, minimum permission matrix, named-pilot approval template, acceptance checklist, backup/deployment/rollback runbook, monitoring and alert thresholds, evidence register and signed deployment decision record.

#### Delivered governance contracts

- The package explicitly records that the current implementation is permission- and scope-gated but has no dedicated Unified Operations runtime feature flag.
- Production activation is `NO-GO` until Step 8.11 rehearses either the preferred backend-enforced `unified_company_operations` kill switch or an explicitly accepted permission-withdrawal exception.
- The least-privilege matrix separates customer-structure administration, Project Management, Implementation management/engineering, Support management/engineering, Executive observation and release operation.
- The named-pilot template requires approved hierarchy, departments, teams, users, one Project, observation period, escalation channel and evidence owners without embedding credentials.
- Acceptance covers hierarchy isolation, denied access, planned/unplanned execution, timer concurrency, private/shared history, same-client ticket linking, readiness gates, analytics reconciliation, legacy ticket/SLA protection, accessibility and audit.
- The rollback runbook prefers disabling new pilot mutations while preserving evidence, requires verified backup restoration, and prohibits casual production database downgrade.
- Monitoring defines initial thresholds and owners for health, schema, authorization, privacy, timer, handover, KPI, backup and ticket/SLA signals.
- The decision record remains `NO-GO`; preparing the package does not select a customer, approve mappings, grant permissions, deploy software or activate workflows.

#### Verification evidence

- Package contents were checked against the implemented permission codes, route dependencies, profile seeds, database head `0292` and existing feature-policy registry.
- Markdown links and required package sections were verified locally.
- No application source, migration, customer record, permission grant, database, web server or remote environment was changed.

<a id="implementation-step-8-11"></a>
### IMPLEMENTATION STEP 8.11 — Restored-copy release rehearsal

**Status:** IN PROGRESS — POPULATED SQL SERVER RESTORED-COPY PASSED; PILOT APPROVALS/ACTIVATION EVIDENCE PENDING

The first rehearsal is recorded in [Unified Company Operations Restored-Copy Rehearsal](UNIFIED_COMPANY_OPERATIONS_RESTORED_COPY_REHEARSAL.md). A clean isolated SQLite database upgraded and seeded successfully; its byte-identical restore copy reported compatibility at `0292`, completed the `0292 → 0291 → 0292` rollback cycle, and returned to `READY`. Read-only reconciliation generated JSON, CSV and Markdown with zero automatic changes, and 35 focused hierarchy, Project, execution, collaboration, handover, analytics, reconciliation and release-revision tests passed.

After the local SQL Server licensing repair, a checksum-verified native backup was restored to the unique `MillensysSupportHub_UCO_Rehearsal_20261124_131106` database on `D:`. The populated copy reported `READY` at `0292`, reconciled 422 Clients and 76 Branches with the expected 422 missing-Organization exceptions and zero automatic changes, completed `0292 → 0291 → 0292`, and retained identical monitored counts. The source `MillensysSupportHub` remained at `0292` and was not modified by the rehearsal. Fifteen focused frontend tests, focused Unified Operations ESLint, TypeScript, the production build, backend Ruff and strict MyPy across 232 source files also passed.

This evidence remains partial because there is no approved pilot mapping or Project and no dedicated Unified Operations runtime flag. The same-token permission-withdrawal drill now passes on the designated testing database (`200` before profile removal, `403` afterward, complete synthetic identity cleanup). That drill also exposed and corrected SQL Server-invalid `.is_(True)` predicates across the Project modules; Ruff, MyPy and 21 focused tests pass after the fix. The packaged runtime now ignores unresolved `REPLACE_*` deployment placeholders instead of masking valid host/`.env` secrets; 19 focused tests pass and direct `diagnose-db → seed → diagnose-db` succeeds without a database-URL override. The local IIS backend was rebuilt and deployed over a timestamped rollback copy after the active November 22 runtime was found to expect obsolete revision `0284`; deployed and live health now report `READY`/compatible at `0292`. The tested frontend build was then deployed over rollback copy `frontend.pre-uco-20261124-143819`; the home page and three new Unified Operations SPA routes return HTTP `200`, and their dedicated chunks are present. Step 8.11 remains open for the signed feature-control choice, approved pilot mapping/participants, manual accessibility/ticket regression checks, alert delivery, application/storage recovery, operational owner sign-off and the deployment decision.

No production/remote environment, customer record, mapping or permission assignment was changed. Only the designated local testing database and local IIS test deployment were used.

### Step 8 completion gate

- Dashboard totals reconcile with authorized drilldowns and documented formulas.
- Department, customer, private-history, evidence, ticket, portal, and executive aggregation boundaries pass security tests.
- Migration dry runs provide reviewed mapping, exception, before/after count, and rollback evidence.
- Clean and populated database rehearsals, performance checks, frontend production build, and accessibility checks pass.
- A named pilot Account, Organization, Clients/Branches, departments, teams, users, and one pilot Project are approved before operational activation.
- No production migration, deployment, data conversion, or permission rollout occurs without a separate release decision.

### 8.12 Governed New Project creation wizard — locally delivered

**Migrations:** `0293_project_creation_wizard`, `0294_project_status_capacity`  
**Local deployment:** `20261124-154639`  
**Database backups:** `D:\SupportHub\DB\MillensysSupportHub_pre_0293_20261124-154436.bak`; `D:\SupportHub\DB\MillensysSupportHub_pre_0294_20261124-160544.bak`

The Project portfolio now opens a seven-step, Next/Next guided creation workflow:

1. Select the Account and an existing Organization/Client, or create the Organization and Client inline; select existing Branches or add a Branch.
2. Select the Client's Products and Modules.
3. Assign the Project Management department/manager, requested delivery department, Team and intake engineer, with hierarchy-aware filtering.
4. Define the Project identity, description, priority and planned dates.
5. Build Phases and Tasks with phase/task date-times, Product/Module scope, estimates and assigned engineers.
6. Register governed document/evidence references.
7. Review the complete structure and either save it as `DRAFT` or publish it as `AWAITING_IMPLEMENTATION_ACCEPTANCE`.

Publish is atomic: the Project, branches, scopes, phases, tasks, assignees, evidence references and delivery-department assignment request are committed together or rolled back together. A delivery department's acceptance moves the Project to `READY_FOR_EXECUTION`. Draft Projects remain visible only within the governed Project visibility boundary and do not create a delivery assignment request.

The database revisions add Project/Phase Product and Module scope tables, task Product/Module and planned date-time fields, Project intake-owner and publication audit fields, and a 50-character Project status column that safely stores `AWAITING_IMPLEMENTATION_ACCEPTANCE`. Compatibility checks and release tests now require `0294_project_status_capacity`.

Verification evidence:

- A clean isolated SQLite database completed full upgrade, `0293 → 0292` downgrade and re-upgrade to `0293`, then reported `READY`.
- The authorized local `MillensysSupportHub` testing database was protected by a checksum-verified native backup, migrated from `0292` to `0293`, seeded and diagnosed as compatible.
- Backend Ruff, strict Project-module MyPy and focused Project portfolio/execution/handover/revision tests passed.
- Frontend TypeScript, focused ESLint, Project/Customer Structure tests and the production build passed.
- The packaged backend and frontend were deployed only to local IIS. After the SQL Server status-capacity correction, live health reports schema `compatible` at `0294_project_status_capacity`; `/SupportHub/projects` returns HTTP `200`; the protected wizard endpoint returns the expected HTTP `401` without authentication.

Known follow-up scope: saving an incomplete partial draft and resuming/editing it is not yet implemented; Draft currently means a complete plan held before publication. The wizard registers governed document references, while direct binary uploads continue through the secured evidence workflow. These items do not block the locally deployed planned-project intake path but must be scheduled if they are required for the production release.

### 8.13 Unified Collaboration workspace and hardening roadmap

The senior engineering review identified that the delivered Project, Implementation analytics, execution and handover primitives do not yet form complete role-oriented workspaces. It also identified scope inconsistencies across detail/summary/mutation endpoints, an overloaded `PROJECT_HANDOVER` profile, missing Implementation intake UI, no centralized Project state machine and incomplete Draft/plan governance.

The controlled continuation plan is [Unified Collaboration Workspaces — Enhancement Execution Plan](UNIFIED_COLLABORATION_WORKSPACES_ENHANCEMENT_PLAN.md). It extends the current `company_projects` foundation at revision `0294_project_status_capacity`; it does not authorize a parallel `implementation_projects` schema or any production activation.

Execution order is security-first: decisions and scope contract, authorization hardening, lifecycle/intake workflow, least-privilege profiles, role workspaces/navigation, Project command center, handover enforcement, then analytics and rollout hardening. The first implementation slice must close authorization and assignment-response gaps before dashboard expansion.

## Implementation control status

Implementation has started in controlled, independently verifiable steps. Step completion authorizes source changes and test migrations only; production migration, customer-data conversion, deployment, permission rollout, and workflow activation remain separate explicit release decisions. Unresolved business decisions must be closed before the step that depends on them begins.

<a id="codex-stop-point"></a>
============================================================
CODEX STOP POINT
Status: STEP 8.11 IN PROGRESS — POPULATED SQL SERVER RESTORED-COPY REHEARSAL PASSED; STEP 8 REMAINS IN PROGRESS
Completed scope: Native backup verification, unique populated SQL Server restore, compatibility diagnosis, populated read-only reconciliation, `0292 → 0291 → 0292` rollback cycle, unchanged source verification and automated backend/frontend gates
Delivered rehearsal evidence: Companion `UNIFIED_COMPANY_OPERATIONS_RESTORED_COPY_REHEARSAL.md`; SQL restored copy returned READY at `0292`; 422 known mapping exceptions and zero automatic changes; before/after monitored counts identical
Last completed item: Corrected the wizard's Organization/Client/Team hierarchy filtering and the SQL Server publication failure caused by the original 30-character Project status column. Migration `0294_project_status_capacity` widens the field to 50 characters; focused backend tests, Ruff, strict MyPy and the clean `0294 → 0293 → 0294` rehearsal pass. The local database and packaged IIS backend now report compatible at `0294_project_status_capacity`; rollback stamp `20261124-160735`
Next planned item: Execute Wave 0 of `UNIFIED_COLLABORATION_WORKSPACES_ENHANCEMENT_PLAN.md`: approve lifecycle, permission and scope matrices; then implement authorization hardening before role workspace/dashboard expansion
Safe to continue from here: YES
Local SQL Server database migrated: YES — `127.0.0.1/MillensysSupportHub`, revisions `0285` through `0294`
Production/remote database migrated: NO
Frontend deployed: YES — local IIS test frontend refreshed with rollback copy `frontend.pre-project-wizard-20261124-154639`; the follow-up status-filter refresh has rollback copy `frontend.pre-project-status-20261124-155107`; production/remote frontend unchanged
Existing customer records changed: NO
Policy decision applied: OVERRIDE replaces operational responsibility but retains inherited customer visibility; Organization policy inherits to descendant Clients and Branches by default
Project/Handover boundary: Existing legacy `ProjectHandover` remains unchanged; the new governed readiness package is additive and no legacy records were converted automatically
Step 8.11 rehearsal boundary: Isolated workspace SQLite files, one uniquely named local SQL Server restored-copy database, the designated `MillensysSupportHub` testing database and the local IIS test site; the testing database received only the idempotent application seed and a fully removed synthetic permission identity; the local web deployment is rollback-protected; no pilot was named, no mapping was approved/applied, and no customer, ticket, Project, hierarchy, remote/production environment or workflow activation was changed
Policy decision applied: All unplanned work requires approval in this foundation. Configurable threshold-based auto-approval may be added only after governance thresholds are approved
Blocking decision(s): SQL Server restored-copy, runtime configuration and technical permission-withdrawal evidence now pass; Step 8.11 completion still requires approved pilot mapping/participants, feature-control choice, monitoring owners, manual acceptance and recovery drill; production activation additionally requires artifact/build selection, KPI targets and a signed GO/CONDITIONAL GO decision; making system-defined access profiles, task classifications, evidence types or handover templates editable remains a later explicit governance decision
============================================================
