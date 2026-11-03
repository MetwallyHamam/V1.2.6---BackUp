# SupportHub 1.50.0

Release date: 2026-08-28

Status: self-contained Windows x64 feature release; supersedes 1.49.3.

## Included changes

- Adds direct ticket import compatibility for the external User Request Excel export while retaining the controlled Support Hub ticket template.
- Maps `Organization->Name` to one unique current Support Hub client name.
- Maps legacy Critical, High, Medium, and Low priorities to P1, P2, P3, and P4 and translates supported legacy statuses to current ticket statuses.
- Matches assigned agents and client callers by normalized full name, links exact current service/contact records when available, and preserves legacy identifiers and unmatched optional service metadata.
- Rejects missing, unknown, or ambiguous core references during staging and retains explicit validation and confirmation before atomic insertion.
- Adds Data Migration guidance for the supported external workbook format.

## Database

Required revision: `0144_handover_cleanup`.

This release adds no migration. Existing 1.47.1 through 1.49.3 databases at `0144_handover_cleanup` remain compatible.

## Deployment

Back up the database, extract 1.50.0 to a new immutable directory, preserve protected environment values, run `SupportHubBackend.exe migrate` and `seed`, switch IIS to 1.50.0, restart the application pool, and complete `SMOKE-TEST.md`.

## Verification

The release builder runs Ruff, strict MyPy, the full backend test suite, frontend ESLint, the complete frontend test suite, TypeScript, and the production frontend build. Package verification is recorded in `RELEASE_STEPS.md`.
