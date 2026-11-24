# SupportHub 1.66.169

Release date: 2026-11-21

Status: source and local IIS UAT deployment verified; distributable package not built or published.

## UAT portfolio and defect workflow

- Adds the consolidated internal UAT portfolio, guided execution, portal Active UAT states, structured defect-ticket links, ticket discovery/badges, ticket-to-UAT synchronization, and actionable sign-off readiness.
- Adds migration `0282_uat_defect_links`, including legacy link backfill and one-ticket-per-test duplicate protection.
- Allows governed system-generated UAT defect tickets to operate when interactive ticket-form requirements include fields the UAT action cannot collect.

## Verification

- Local SQL Server `MillensysSupportHub` migrated to `0282_uat_defect_links`; IIS reports the schema compatible.
- SQLite clean and populated upgrade rehearsals passed, including legacy defect-link backfill.
- Ruff, strict MyPy, and all 569 backend tests passed.
- Frontend ESLint completed with no errors and one existing hook warning; TypeScript, all 137 Vitest tests, and the production build passed.
- Local IIS smoke passed for internal portfolio, portal Active UAT, failed-test ticket creation, Tickets discovery, approval/assignment, resolution, and retest. Evidence: `UAT-IIS-20261121182546` / `INC-2026-021555`.
- `git diff --check` passed. Packaging and publication remain deferred.
