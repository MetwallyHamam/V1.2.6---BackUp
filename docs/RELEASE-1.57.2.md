# SupportHub 1.57.2 — SQL Server Migration Correction

## Purpose

Correct the `0168_remove_profile_queries` migration failure observed when upgrading an existing SQL Server database through the packaged runtime.

## Correction

- Replaces the driver-dependent inserted-primary-key lookup with a deterministic lookup by the dashboard's unique governed code.
- Makes the migration retry-safe when a prior interrupted attempt left the migrated dashboard row in place.
- Preserves legacy profile widget selections as governed Executive dashboard assignments before removing the retired profile query column.
- Includes the mobile Reports navigation correction from 1.57.1.

## Database and deployment

Database revision remains `0168_remove_profile_queries`. Keep the application stopped, back up production, deploy this package to a new immutable directory, and rerun the packaged migration command. Do not continue deploying release 1.57.1.

## Verification

- Ruff, strict MyPy, all 339 backend tests, ESLint, all 47 frontend tests, TypeScript, and the production frontend build passed.
- The packaged runtime upgraded a staged 0167 database containing legacy profile widgets, preserved its two widgets and governed Executive assignment, removed the retired column, and completed an idempotent second migration.
- Archive inspection passed with 1,754 entries and no environment files, databases, caches, or compiled Python source files.
- Package: `releases/SupportHub-1.57.2.zip` (42,891,895 bytes).
- SHA-256: `778EE5E3B7D229CDED24D6D2D25969BF767A899DC8AE6501BE3DBB91E938C4D2`.
