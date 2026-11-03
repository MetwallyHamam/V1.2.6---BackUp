# SupportHub 1.57.1 — Mobile Reports Navigation

## Purpose

Restore permission-aware access to reports on mobile devices.

## Correction

- Adds a dedicated Reports section to the mobile navigation drawer.
- Exposes Executive, Top Management, Agent KPI, Product and Module, SLA and Workload, and Operations reports according to effective permissions.
- Corrects desktop Reports visibility for users who have Top Management dashboard permission without Agent or Manager dashboard permissions.
- Adds English and Arabic navigation labels for every report destination.

## Database and deployment

Database revision remains `0168_remove_profile_queries`; this corrective release adds no migration. Back up production, deploy to a new immutable directory, run the packaged migration compatibility check, and complete the smoke test before switching IIS.

## Verification

- All 337 backend tests and all 47 frontend tests passed, together with Ruff, strict MyPy, ESLint, TypeScript, and the production frontend build.
- The packaged runtime completed a clean migration and an idempotent second migration through `0168_remove_profile_queries`.
- Archive inspection passed with 1,752 entries and no environment files, databases, caches, or compiled Python source files.
- Package: `releases/SupportHub-1.57.1.zip` (42,889,310 bytes).
- SHA-256: `E9B60B330D952B12D33899F162C62A907031C1E821D81A8F9F10A1F25302EF7B`.
