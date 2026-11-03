# SupportHub 1.33.0

Unified Operations Workspace and contract-finance discoverability release.

## Operations Workspace

- Removed the standalone Shift Calendar navigation entry; legacy `/shifts` links now redirect to the unified Operations Calendar.
- Kept shift scheduling available inside Operations Workspace for authorized workforce planners.
- Loads shifts, internal operations, and visits independently according to each user's effective permissions.
- Hides calendar filters, legends, shift templates, settings, and actions when their source permission is unavailable.
- Adds granular Internal Operations permissions for workspace access, calendar visibility, creation, assignment, scheduling, lifecycle transitions, comments, evidence, templates, types, and conflict overrides.
- Existing profiles inherit equivalent granular permissions from `internal_operation.view` and `internal_operation.manage` during migration.

## Contract Financials

- Keeps Financials permanently visible near the beginning of the Contract Workspace tabs.
- Supports direct contract-workspace links using `contract_id` and `tab=finance` query parameters.
- Keeps read access under `finance.view` and write access under `finance.manage`.
- Users without financial read access see an explicit permission explanation instead of a missing tab.

## Database and verification

- Database revision: `0122_operations_permissions`.
- Clean migration rehearsal passed through the new head.
- Backend Ruff, MyPy, and 257 tests passed.
- Frontend ESLint, 9 tests, TypeScript, and production build passed.
