# Wave 1 Implementation Status

Status: `DONE`  
Date: 2026-08-20  
Scope: hierarchy foundation, departments, and resolver correction

## Completed

- Added nullable, indexed, restrictive `clients.parent_client_id` through Alembic revision `0093_client_hierarchy`.
- Added the centralized hierarchy service with ancestors, descendants, scope IDs, path, descendant check, parent-change validation, deterministic ordering, cycle detection, and defensive traversal limits.
- Extended client create/read/update contracts with optional parent selection.
- Added hierarchy, ancestor, and descendant APIs with path and direct/total descendant metadata.
- Rejected missing parents, self-parenting, indirect cycles, and deletion of parents that still have children.
- Added parent-change audit evidence containing old and new hierarchy paths.
- Added client-editor breadcrumb/tree navigation, parent selection, counts, and parent selection during client creation.
- Preserved standalone clients as roots and kept inactive nodes independent from descendant activation.
- Confirmed the existing effective department master foundation from revision `0091_department_master` remains active, assignable, and reusable; no duplicate department model was introduced.
- Corrected the legacy current-SLA helper to use the canonical product/module/service/priority resolver, so an unrelated service override no longer blocks the priority fallback.
- Updated runtime database compatibility guards to require revision `0093_client_hierarchy` and `clients.parent_client_id`.

## Changed modules

- `backend/app/modules/clients/models.py`
- `backend/app/modules/clients/schemas.py`
- `backend/app/modules/clients/routes.py`
- `backend/app/modules/clients/hierarchy.py`
- `backend/app/modules/sla/service.py`
- `backend/app/db/compatibility.py`
- `frontend/src/pages/ClientsPage.tsx`
- `frontend/src/pages/EditClientPage.tsx`
- Hierarchy, SLA fallback, department, compatibility, and release-revision tests

## Migration

- Added `backend/alembic/versions/0093_client_hierarchy.py`.
- Clean SQLite install reached `0093_client_hierarchy`.
- Populated SQLite upgrade reached `0093_client_hierarchy`.
- Temporary rehearsal databases were removed after validation.
- SQL Server clean-install reached `0093_client_hierarchy`, seeded successfully, and passed the runtime compatibility check.
- A populated SQL Server `0092_client_profile` baseline containing a client row was upgraded to `0093_client_hierarchy`; the row was preserved and backfilled as a root.
- Both SQL Server databases verified exactly one hierarchy column, index, and restrictive `NO ACTION` foreign key before the two named disposable rehearsal databases were removed.

## Verification

- Ruff: passed.
- Mypy: passed across 120 source files.
- Pytest: 182 passed.
- Frontend ESLint: passed with zero warnings.
- Frontend Vitest: 3 passed.
- Frontend TypeScript: passed.
- Frontend production Vite build: passed; the existing large vendor chunk advisory remains non-blocking.

## SQL Server portability correction

The first clean-install rehearsal found that SQL Server rejects `ON DELETE RESTRICT`. The ORM self-reference was corrected to omit the dialect-specific clause, which produces SQL Server's restrictive `NO ACTION` behavior. Revision `0093` continues to create explicit SQLite `RESTRICT` and SQL Server `NO ACTION` constraints. Clean and populated rehearsals passed after this correction.

## Remaining gate

None. Wave 1 is complete. Wave 2 requires a new explicit continuation instruction.
