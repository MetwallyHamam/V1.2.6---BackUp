# Wave 2 Implementation Status

Status: `DONE`  
Date: 2026-08-20

## Completed

- Added revision `0094_scope_shift` with explicit portal scope modes, backward-compatible `CLIENT_ONLY` backfill, shift-type metadata, and department-specific shift patterns.
- Expanded effective portal client access through the centralized hierarchy service for direct-child or full-descendant scope while retaining exact branch scopes.
- Added hierarchy-scope selection during portal-user creation.
- Removed the portal ticket form's first-client assumption; multi-client users must choose the exact affected client before catalog, entitlement, contract, and ticket submission.
- Portal catalog requests now accept and validate the selected affected client and return authorized client choices.
- Added shift-type create/update APIs and department-filtered shift-pattern list/create APIs, including duplicate and cross-midnight validation.
- Added total-aware customer pagination plus server-side all-matching contract selection with preview, explicit exclusions, primary-customer preservation, and audit evidence.
- Added permission-gated shift-type and shift-pattern administration UI, pattern update support, and create/update audit records.
- Preserved existing ticket service validation for client, branch, requester, contract, and coverage isolation.

## Migration and verification

- Clean SQLite migration reached `0094_scope_shift`.
- Clean SQL Server migration reached `0094_scope_shift` and passed runtime compatibility checks.
- Disposable SQLite and SQL Server rehearsal databases were removed.
- Ruff and Mypy passed for affected backend modules.
- 16 targeted hierarchy, shift, portal, compatibility, and migration-revision tests passed.
- Targeted frontend ESLint and TypeScript passed for portal and user setup changes.
- Full release gates passed: Ruff, Mypy across 120 source files, 184 backend tests, frontend ESLint, 3 Vitest tests, TypeScript, and the production Vite build.
- A populated SQLite database upgraded from revision `0015_teams_delivery` through `0094_scope_shift` and passed compatibility.
- A populated SQL Server database was migrated and seeded at `0093_client_hierarchy`, upgraded to `0094_scope_shift`, and passed compatibility.
- All disposable Wave 2 SQLite and SQL Server rehearsal databases were removed after verification.

## Completion boundary

Wave 2 is complete. No Wave 2A or later work has started.
