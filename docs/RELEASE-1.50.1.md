# SupportHub 1.50.1

Release date: 2026-08-29

Status: corrective self-contained Windows x64 release; supersedes 1.50.0.

## Included changes

- Retains the external User Request and controlled ticket-import functionality introduced in 1.50.0.
- Preloads ticket clients, users, types, statuses, contracts, products, modules, environments, services, and existing ticket numbers once per validation request.
- Reuses preloaded references during confirmation instead of issuing multiple database queries for every ticket row.
- Prevents large controlled ticket workbooks from exceeding the IIS request timeout and surfacing as HTTP 502 responses.
- Adds regression coverage for validation and confirmation of a 500-ticket workbook with bounded database reads.

## Database

Required revision: `0144_handover_cleanup`.

This release adds no migration. Existing 1.50.0 databases remain compatible.

## Deployment

Extract 1.50.1 to a new immutable directory, preserve protected environment values, switch IIS from 1.50.0 to 1.50.1, restart the application pool, and retry the ticket workbook upload. Do not reuse a partially staged job from a failed request.

## Verification

The release builder runs Ruff, strict MyPy, the full backend test suite, frontend ESLint, the complete frontend test suite, TypeScript, and the production frontend build. Package verification is recorded in `RELEASE_STEPS.md`.
