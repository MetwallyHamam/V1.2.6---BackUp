# SupportHub 1.66.168

Release date: 2026-11-20

Status: self-contained Windows x64/IIS release built and verified.

## Monitoring integration API

- Adds API-key-authenticated endpoints for monitoring tools to create tickets, read their status, move them to In Progress, and close them with resolution and root-cause summaries.
- Preserves event idempotency and restricts scoped credentials to their configured client.
- Monitoring-created tickets use the `MiMonitoringService` caller automatically.
- Applies the `SYSTEM_MAINTENANCE` flag and pauses the resolution SLA through a governed flag-pause interval.
- Keeps configurable interactive ticket-form requirements from blocking the narrower monitoring API contract.

## Administration and reliability

- Fixes API-key credential creation from the inbound integration settings page.
- Adds portal attachment visibility controls and contract-safe portal responses.
- Includes SQL Server-safe Work Assignment evidence migration behavior.
- Includes advanced maintenance scheduling and the current Work Assignments workflow.

## Database

- Database revision advances to `0281_portal_attachment_access`.
- Run the packaged migration before starting the new application runtime.

## Verification

- Ruff and strict MyPy passed across 214 backend source files.
- All 568 backend tests passed.
- Frontend ESLint, all 133 frontend tests, TypeScript compilation, and production build passed.
- Packaged runtime commands and required release contents were verified.
- Artifact: `releases/SupportHub-1.66.168.zip` (54,171,962 bytes).
- SHA-256: `492A674BAAA5AB2CDEF272E7EB2C6F3187D0F713E6E099BC24909A681E9152FC`.

