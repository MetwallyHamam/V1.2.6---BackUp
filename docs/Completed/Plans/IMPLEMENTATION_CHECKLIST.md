# Phase 0–1 Implementation Checklist

- [x] Monorepo, configuration, logging, error handling, correlation IDs, and health API
- [x] SQLAlchemy session management and SQL Server-compatible Alembic migration
- [x] Users, profiles, permissions, assignments, overrides, scopes, tokens, and audit models
- [x] Password hashing, login throttling/lockout, JWT access tokens, refresh rotation, logout
- [x] Permission dependencies and effective-permission calculation with deny precedence
- [x] User/profile/permission APIs and idempotent seed command
- [x] React/TypeScript shell, login, protected routes, users, profiles, and permission preview
- [x] Backend and frontend automated tests
- [x] CI, lint, type checking, developer documentation, and final verification

## Roadmap Phases A–C

- [x] Phase A: CRM master data, dependent ticket context, inactive-client confirmation, assignment, followers, authorization, and audit
- [x] Phase B: tasks/checklists, server-side queue operations, nested filters, columns, saved views, bulk assignment, authorization, and audit
- [x] Phase C: full contract details, multidimensional coverage, deterministic entitlement/limits, ticket snapshots/overrides, documents, renewals, authorization, and audit
- [x] SQL Server migrations through `0057_sla_clock_lifecycle`
- [x] Backend and frontend quality gates and local `/SupportHub` deployment verification
