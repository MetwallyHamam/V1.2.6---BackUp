# Codex Execution Prompts

## How to Use These Prompts

Run one prompt at a time in VS Code. Before each prompt, provide Codex the repository path and ask it to inspect existing code first. Do not ask Codex to build all modules in one pass.

After every prompt, require:

1. List of files changed.
2. Explanation of design decisions.
3. Commands executed.
4. Test results.
5. Known limitations/TODOs.
6. No placeholder security logic.

## Prompt 0 — Create Repository Foundation

```text
You are implementing Millensys Support Hub, a production-oriented ticketing, CRM, contracts, client portal, knowledge base, SLA, escalation, notifications, and workforce web application.

Read all files in the project planning pack before making changes. Create a monorepo with backend, frontend, infrastructure, docs, scripts, and tests directories.

Backend requirements:
- Python FastAPI modular-monolith structure.
- SQLAlchemy 2.x, Alembic, Pydantic settings, pyodbc SQL Server adapter.
- Structured JSON logging and correlation ID middleware.
- Standard API error envelope.
- Health/live, health/ready, dependencies, and version endpoints.
- pytest, coverage, Ruff, mypy, pre-commit.
- Environment config validation and .env.example only; never create real secrets.

Frontend requirements:
- React, TypeScript, Vite.
- Material UI or Ant Design; choose one and document the reason.
- Routing, protected application shell, query client, API client, error boundary.
- ESLint, formatting, unit test setup.

Create an architecture decision record for all major choices. Add local developer instructions. Add CI configuration that runs lint, types, tests, builds, and migration validation.

Do not implement business modules yet. Run all available checks and report results.
```

## Prompt 1 — SQL Server Core and Identity

```text
Inspect the existing repository and planning documents. Implement database connection management, Alembic migrations, and identity/RBAC foundations.

Create domain models and APIs for users, roles, permissions, teams, and team memberships. Roles must be permission bundles; endpoint authorization must rely on permissions and deny by default.

Support local authentication for development/client accounts using a modern password hash. Design an authentication provider interface so Microsoft Entra ID OIDC can be added without rewriting authorization.

Implement secure session/token handling, logout/revocation, failed-login throttling hooks, audit events, rowversion-based optimistic concurrency, validation, pagination, and tests.

Seed a minimal permission catalog through migration or explicit seed command. Never seed production passwords.

Prove in tests that normal users cannot perform administrator operations.
```

## Prompt 2 — CRM Master Data

```text
Implement the CRM domain for clients, client statuses, branches, contacts, contact branch access, products, modules, client installations, environments, services, and vendors.

Use SQL Server constraints, indexes, rowversion, soft-delete only where justified, and audit events. Add API CRUD/search endpoints with permission policies and server-side pagination/filtering.

Client status must support Active, Implementation, On Hold, Suspended, Expired Contract, and Terminated behavior flags. Do not store credentials in installation records.

Build React administration and agent search screens with loading, empty, error, validation, and concurrency-conflict states. Add tests for client and branch visibility.
```

## Prompt 3 — Ticketing Vertical Slice

```text
Implement a complete internal ticketing vertical slice.

Ticket types: incident, service request, problem, change, access request, monitoring alert.
Implement catalogs, ticket numbering, client/branch/requester, product/module/environment, category/subcategory/service, impact, urgency, derived priority, assigned team/user, status, subject, description, timestamps, flags, comments, internal notes, watchers, tags, tasks, links, and activity timeline.

Implement a backend workflow state machine. The frontend must not be the authority for transition validity. Store status and assignment history. Add rowversion concurrency.

Implement secure attachment metadata and storage adapter interface. Include extension/MIME/size checks and a malware-scan status hook. Authorization must be checked on download.

Build agent ticket list, quick create, full create, and ticket workspace screens. Include server-side filtering/sorting/pagination, column chooser, and an initial saved-view model.

Add comprehensive tests including unauthorized object access, public versus internal comments, transition validation, and concurrent update conflict.
```

## Prompt 4 — Client Portal

```text
Implement a separate client portal experience using the same API/domain with explicit portal policies.

Client users may see only tickets for their authorized client and branches. They can create tickets, add public comments and approved attachments, view public timeline events, confirm resolution, reopen with a reason, and submit satisfaction feedback.

They must never receive internal notes, internal attachments, hidden fields, internal user metadata, or internal SLA commentary. Apply authorization to REST APIs, WebSocket events, search, exports, and attachment downloads.

Add service announcements and a knowledge-search step before submission. Build cross-client isolation tests that try guessed IDs and direct URLs.
```

## Prompt 5 — Contracts and SLA

```text
Implement contracts, coverage, entitlements, service catalog, business calendars, holidays, SLA policies, and SLA targets.

Create a deterministic SLA engine for first response and resolution. It must support timezone-aware business hours, multiple daily work periods, weekends, holidays, pause states, recalculation history, warning thresholds, and breach events.

Store selected rule IDs and calculation version. Never calculate deadlines only in the browser.

Build contract administration and a ticket SLA panel. Add property-based or table-driven tests for weekends, holidays, pauses, daylight/timezone cases, priority changes, and contract expiry.
```

## Prompt 6 — Assignment, Escalation, and Notifications

```text
Implement configurable assignment and escalation.

Assignment strategies: manual, queue, round robin, least workload, skills, client/product ownership, and active shift/on-call eligibility.

Escalation triggers: unassigned time, SLA percentages, breach, inactivity, critical priority, patient safety, reopen count, and dissatisfaction. Actions: notify, reassign, create task, require acknowledgment, and escalate to leadership.

Use an outbox pattern and durable background jobs. Ensure idempotency so the same threshold cannot create duplicate escalation events.

Implement notification center, preferences, email delivery abstraction, WebSocket fan-out through Redis, reconnect/missed-notification retrieval, read/acknowledged states, severity, quiet hours, deduplication, retries, and dead-letter state.

Implement browser notification and optional sound. Audio must only be enabled after explicit user interaction. Add a test-sound control and visual fallback when blocked.
```

## Prompt 7 — Shift Calendar

```text
Implement workforce scheduling: shift types, recurring shifts, employee/team calendar, primary/backup on-call, leave, shift swap request/approval, coverage warnings, and handover notes.

Prevent overlap unless a privileged user provides an override reason. Audit all overrides. Integrate assignment eligibility with active shift/on-call, team, and skill.

Build month/week/day calendar views and filters for team, employee, shift type, and on-call role. Add timezone-safe tests.
```

## Prompt 8 — Knowledge Base

```text
Implement knowledge articles with draft, review, approved, published, and retired workflow. Add internal/client visibility, categories, tags, product links, owner/reviewer, review date, sanitized rich text, attachments, version history, feedback, ticket linking, and convert-resolution-to-draft.

Implement SQL Server full-text search behind a search service interface. Exact identifier search must still use normal indexed fields.

Only approved, published, authorized articles appear in the portal. Add tests for workflow, visibility, sanitation, and version history.
```

## Prompt 9 — Excel Imports

```text
Implement secure master-data Excel import for clients, branches, contacts, products, installations, contracts, users, and classifications.

Generate controlled templates. Upload to protected storage. Parse into staging tables. Validate headers, types, required fields, references, duplicates, allowed values, formula injection, and business rules. Show preview and row errors before commit.

No invalid job may modify production tables. Commit valid confirmed imports in batches with idempotency key and audit. Produce an error/result workbook. Add tests for malformed, oversized, duplicate, replayed, and partially invalid files.
```

## Prompt 10 — Advanced Filters, Views, and Dashboards

```text
Implement a validated advanced-filter AST supporting nested AND/OR groups. Define safe field/operator registries; never accept raw SQL from clients.

Add saved views with private, team, and global scope, columns, sort, grouping, default view, and dashboard pinning. Add role-aware bulk actions.

Build agent and manager dashboards from the specification. Every chart/widget must drill into the underlying filtered list. Optimize SQL Server queries and add required indexes based on measured query plans.

Add export permissions, row limits, audit, and CSV/Excel formula-injection protection.
```

## Prompt 11 — Integrations and Hardening

```text
Add integration adapters for inbound/outbound email, SMS, monitoring alerts, Entra ID OIDC, and future iTop import. Every inbound event requires validation, idempotency, correlation ID, retries, and dead-letter handling.

Then harden the application against the project security checklist: CSP, CORS allowlist, trusted hosts, CSRF strategy, rate limits, secure cookies/tokens, secret scanning, dependency scanning, SAST, upload security, sanitized errors, and audit coverage.

Add load tests for ticket lists, dashboards, WebSockets, notification bursts, SLA scheduling, and large imports. Add production deployment and rollback runbooks.
```

## Prompt 12 — Final Architecture Review

```text
Perform a complete production-readiness review without making broad rewrites first.

Compare the implementation against every planning document and produce a traceability matrix: requirement, implementation location, tests, status, and gap. Review domain boundaries, authorization, object-level client isolation, migrations, indexes, transaction boundaries, background job idempotency, audit coverage, sensitive-data handling, observability, backup/restore, and deployment safety.

Fix only clearly justified critical/high issues in small commits. Run the full test/check suite and provide remaining risks ordered by severity.
```

## Prompt 1A — Default Profiles and Effective Permissions

```text
Extend the existing identity/RBAC implementation with managed user profiles for Millensys Support Hub.

Create default system profiles: CALL_CENTER, L1, L2, L3, SUPPORT_MANAGER, SYSTEM_ADMINISTRATOR, and CLIENT_PORTAL. A profile is a permission bundle with default scope, dashboard, saved view, and notification preferences. Authorization must use permission codes, never hard-coded profile-name checks.

Implement SQL Server/Alembic models for Profile, Permission, ProfilePermission, UserProfile, UserPermissionOverride, UserClientScope, and UserBranchScope. Support active dates, expiry, explicit allow/deny overrides, reason, approver, rowversion concurrency, and complete audit events. Explicit deny must win. Default is deny.

Build administration APIs and UI to:
- create a user and select a default profile;
- assign additional profiles;
- display a calculated effective-permission preview before save;
- clone a system profile into a custom profile;
- edit custom profile permissions by module;
- compare profiles;
- inspect affected users and profile history;
- manage client and branch scope for portal users.

Enforce these safeguards:
- Client Portal requires ClientId and authorized branches;
- internal employee profiles cannot be assigned to portal-only identities;
- Administrator assignment requires reason, step-up authentication hook, and audit;
- system profiles cannot be deleted;
- high-risk profile changes invalidate active permission caches and optionally revoke sessions;
- every endpoint, WebSocket event, export, search result, and attachment download applies effective permissions and object scope.

Seed the permission catalog and profile mappings idempotently. Add a matrix test for all default profiles, including proof that Call Center cannot read internal notes, L1 cannot use L3 operations, Client Portal cannot cross client boundaries, and Manager cannot grant Administrator unless explicitly authorized.

Use 12_USER_PROFILES_AND_PRIVILEGES.md as the functional source of truth. Run migrations and all tests, then report changed files and results.
```
