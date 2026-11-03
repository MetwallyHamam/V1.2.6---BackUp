# SupportHub 1.50.2

Release date: 2026-08-29

Status: corrective self-contained Windows x64 release; supersedes 1.50.1.

## Included changes

- Retains the optimized large-ticket validation and confirmation logic from 1.50.1.
- Starts confirmed imports as background work and returns immediately with `IMPORTING`, avoiding the global 15-second browser timeout.
- Polls import status automatically while work is active and reports `COMPLETED` or `IMPORT_FAILED` instead of showing a false reference-data error.
- Uses an isolated database session bound to the same deployment database for background confirmation.
- Preserves atomic insertion: a server-side failure rolls back the import and records `IMPORT_FAILED`.
- Warns administrators not to restart IIS or upload duplicate data while an import is running.

## Database

Required revision: `0144_handover_cleanup`.

This release adds no migration. Existing 1.50.x databases remain compatible.

## Deployment

Before retrying an interrupted import, check the job status and verify whether its legacy ticket numbers exist. Extract 1.50.2 to a new immutable directory, preserve protected environment values, switch IIS to 1.50.2, restart the application pool, and use the Data Migration status display while confirmation runs.

## Verification

The release builder runs Ruff, strict MyPy, the full backend test suite, frontend ESLint, the complete frontend test suite, TypeScript, and the production frontend build. Package verification is recorded in `RELEASE_STEPS.md`.
