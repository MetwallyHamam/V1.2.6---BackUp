# Codex Account Handoff — Unified Company Operations

**Last updated:** 2026-11-24 (Africa/Cairo)  
**Workspace:** `D:\Metwally\Developing tools\Support Operations Systems\Web CRM & Ticketing System\V1.2.6 - BackUp`  
**Active objective:** Execute the security-first Unified Collaboration workspace roadmap after the governed New Project wizard was delivered and locally deployed.

## Current local environment

- Local IIS application: `http://localhost/SupportHub/`
- Test database: `MillensysSupportHub` on the local SQL Server instance.
- Current deployed/database revision: `0295_project_lifecycle`.
- Production and remote environments are out of scope.

## Requested wizard behavior

The user requested a Next/Next guided wizard covering Organization/Client/Branch creation or selection, products/modules, department/team/intake engineer, phases, product/module tasks, schedules, documents, review, Save Draft and Publish. Publishing must create the delivery-department intake request; the department accepts before execution begins.

## Completed implementation

- Added and rehearsed `0293_project_creation_wizard`, including project/phase product-module scopes, task scheduling/scope, intake ownership and publish metadata.
- Added atomic `POST /api/v1/projects/wizard` Draft/Publish behavior and delivery-department assignment requests on Publish.
- Added the seven-step React wizard for customer, product/module, ownership, project, phases/tasks, document references and review.
- Added inline Organization, Client and Branch creation; team/member filtering; phase/task schedules; and product/module task scope.
- Backed up the test database to `D:\SupportHub\DB\MillensysSupportHub_pre_0293_20261124-154436.bak`, migrated it to `0293`, seeded it and confirmed compatibility.
- Deployed backend and full wizard frontend to local IIS with rollback copies stamped `20261124-154639`; a validated status-filter frontend refresh has rollback copy `frontend.pre-project-status-20261124-155107`.
- Live verification passed: database health is compatible at `0293`, `/SupportHub/projects` returns HTTP 200, and the protected wizard route returns the expected unauthenticated HTTP 401.
- Corrected numeric/string hierarchy-ID filtering that hid valid Organizations (and could hide Clients/Teams) in the wizard; validated frontend deployed with rollback copy `frontend.pre-project-org-filter-20261124-155821`.
- Corrected SQL Server publication failure caused by the 30-character `company_projects.status` column; migration `0294_project_status_capacity` widens it to 50 characters for `AWAITING_IMPLEMENTATION_ACCEPTANCE`. Backup: `D:\SupportHub\DB\MillensysSupportHub_pre_0294_20261124-160544.bak`; backend rollback stamp: `20261124-160735`.
- Corrected the Project drawer's root-relative execution link so React Router preserves the `/SupportHub` IIS basename. Local route `/SupportHub/projects/3/execution` returns HTTP 200; frontend rollback copy: `frontend.pre-project-route-link-20261124-161226`.
- Treated an absent Support handover as an expected workflow state instead of a global API error. Projects in Draft or awaiting Implementation acceptance now explain the prerequisite and hide premature initialization; frontend rollback copy: `frontend.pre-handover-state-20261124-161630`.
- Backend lint/type checks, focused project tests, frontend TypeScript/ESLint/tests, production build and clean migration upgrade/downgrade/re-upgrade rehearsal passed.

## Known follow-up improvements

1. Drafts are saved only after the wizard's required planning data is complete; partial-draft resume/edit is not yet implemented.
2. The wizard records governed document references; direct binary upload remains in the secured evidence workflow.
3. Complete the remaining Step 8.11 pilot, manual acceptance, monitoring/recovery and GO/NO-GO governance work before any production activation.

## Approved planning continuation

- Senior engineering review confirmed missing role workspaces/navigation plus authorization, lifecycle, profile, intake and plan-governance gaps.
- Execution roadmap: `docs/Planned/Colbrating/UNIFIED_COLLABORATION_WORKSPACES_ENHANCEMENT_PLAN.md`.
- Start at Wave 0 (lifecycle, permission and scope matrices), then Wave 1 authorization hardening. Do not start dashboard expansion before those gates pass.
- The roadmap extends `company_projects`; do not implement a parallel `implementation_projects` authority from the older proposal.

## Active implementation slice

- Added `backend/app/modules/projects/access.py` as the central authorized-Project scope and privacy-preserving Project/task access service.
- Applied it to Project list/summary/detail/plan, assignment requests/responses, execution child resources and Support handover operations.
- Assignment response now requires the requested department (unless `project.manage`) and rejects Teams outside that department.
- Added `GET /api/v1/projects/assignment-requests/inbox`, scoped to the actor's authorized Projects and department.
- Added `/implementation-intake`, its permission route, sidebar navigation, Arabic/English labels, status filters and governed Accept/Propose/Return/Reject dialog.
- Backend Ruff/MyPy and 9 focused Project tests passed; the expanded portfolio suite passed 6 tests. Frontend focused lint/TypeScript and intake test passed; the full suite passed 157 tests and the production build completed.
- Deployed this slice to local IIS with backend rollback folders `runtime/app/alembic.pre-collab-20261124-164753` and frontend rollback folder `frontend.pre-collab-20261124-164753`. The first runtime copy omitted PyInstaller's required `_internal` nesting; it was isolated as `runtime.failed-collab-20261124-164753`, corrected from the exact packaged directory, and revalidated.
- Live smoke verification passed: application and `/SupportHub/implementation-intake` return HTTP 200, backend health returns HTTP 200, `MillensysSupportHub` is reachable/compatible at `0294_project_status_capacity`, and the unauthenticated intake API correctly returns HTTP 401.

## Lifecycle governance continuation

- Added migration `0295_project_lifecycle`: `row_version` on Projects and assignment requests plus append-only `project_status_transitions` history.
- Added the canonical lifecycle service with validated source/target transitions and mandatory reasons for returned, rejected, held and cancelled states.
- Removed `status` from generic Project patching; status changes now use the versioned `/projects/{id}/transition` command.
- Intake Accept/Propose/Return/Reject now moves the Project to `READY_FOR_EXECUTION`, `INTAKE_PROPOSED`, `INTAKE_RETURNED` or `INTAKE_REJECTED`, records history, and prevents stale duplicate decisions.
- Clean upgrade/downgrade/re-upgrade rehearsal passed. Local SQL backup: `D:\SupportHub\DB\MillensysSupportHub_pre_0295_20261124-170331.bak`.
- Migrated `MillensysSupportHub` to `0295_project_lifecycle` and deployed backend/frontend with rollback stamp `20261124-170709`.
- Live health/database/intake smoke tests passed; the database reports compatible at `0295`, the intake page returns HTTP 200 and its unauthenticated API returns HTTP 401.
- Connected task execution and Support handover to the canonical lifecycle: first task action/worklog/timer starts execution, final eligible task approval opens delivery review, handover initialization opens preparation, submission opens Support review, and Support activation starts stabilization.
- Execution mutations now reject pre-acceptance and terminal Project states with `PROJECT_NOT_EXECUTABLE`; legacy `PLANNING`/`ACTIVE` remain temporarily supported pending the approved data-mapping conversion.
- Focused execution, handover and portfolio suites passed with transition-history assertions. Backend-only local deployment rollback stamp: `20261124-171420`; health and database compatibility at `0295_project_lifecycle` passed afterward.
- Added centralized lifecycle notifications for Project Manager/intake owner, optimistic hold/resume commands that restore the last governed state, residual-work closure, and validated stabilization completion to `COMPLETED`.
- Updated the Project execution workspace with status, permission-aware hold/resume controls, residual-work actions and stabilization completion evidence dialog.
- Backend Ruff/MyPy and 11 focused lifecycle tests passed; frontend ESLint/TypeScript, 2 focused tests and production build passed. Local backend/frontend rollback stamp: `20261124-202323`; health, database compatibility and `/SupportHub/projects/3/execution` returned HTTP 200.
- Hardened all Project collaboration routes with the centralized Project scope. Requested departments receive limited visibility through their cross-department request; unrelated departments cannot inspect/respond by guessed Project or request IDs. Requesting-department spoofing and cross-department owner assignment are rejected.
- Ticket implementation history is now filtered to Projects authorized to the caller. The expanded 14-test Project portfolio/execution/handover/collaboration matrix, Ruff and MyPy passed.
- Backend-only local rollback stamp: `20261124-225836`; health and database compatibility at `0295_project_lifecycle` passed, and unauthenticated collaboration access returned HTTP 401.
- Reconciled collaboration with authoritative Ticket visibility. Implementation-history reads, ticket links and ticket-referenced events now require both authorized Project scope and visibility of the Ticket; unauthorized guessed Ticket IDs return privacy-preserving HTTP 404. Ticket-referenced events also enforce the same Client as the Project.
- Ruff and MyPy passed; 16 focused collaboration/portfolio/execution/handover tests passed. Backend-only rollback folder: `D:\SupportHub\Release\backend\runtime.pre-ticket-authorization-20261124-231112`. Live health/database returned HTTP 200 at `0295_project_lifecycle`, and unauthenticated Implementation-history returned HTTP 401.
- Next: produce read-only least-privilege profile previews for Project Management, Implementation Manager, Team Leader, Engineer and Support, then implement the Wave 4 workspace/navigation shells. Do not assign profiles or rewrite legacy Project statuses without approved mappings.
- Seeded the five Wave 3 least-privilege profiles without assigning them to users: `PROJECT_MANAGER`, `IMPLEMENTATION_MANAGER`, `IMPLEMENTATION_TEAM_LEADER`, `IMPLEMENTATION_ENGINEER` and `SUPPORT_HANDOVER_REVIEWER`.
- Split engineer execution into assignment-scoped `implementation.task.execute`, `implementation.task.blocker.manage` and `implementation.task.evidence.create` permissions. Status, blocker and evidence mutations now require the corresponding capability and an explicit task assignment; the engineer bundle no longer receives broad `implementation.task.manage`.
- Extended the read-only `PROJECT_HANDOVER` preview with candidate permission gained/lost/retained deltas for all five profiles. Existing assignments remain unchanged and still require an approved mapping.

## Safety

Project Templates and the planned Gantt schedule are deployed locally at revision `0296_project_templates`. The wizard publishes templates at Review and copies published versions at Customer scope. Database backup was verified at `D:\SupportHub\DB\MillensysSupportHub_pre_0296_20261125.bak`. IIS rollback stamp is `20261125-000402`. Projectuser login, authenticated template list and portfolio, database health and the schedule route returned HTTP 200.

Added `project.manage.assigned` for the named Project Manager to update the project, add phases and milestones, and hold or resume it. The execution page uses the same manager check for hold and resume. The generic lifecycle transition command still requires `project.manage`. Portfolio regression tests verify that department visibility alone cannot authorize edits.

Deployed backend and frontend to local IIS with rollback stamp `20261124-233552`. Created `Projectuser` in `MillensysSupportHub` and assigned `PROJECT_MANAGER_LOCAL_TEST` for customer setup, project creation and publication, scoped management, collaboration, and Sup