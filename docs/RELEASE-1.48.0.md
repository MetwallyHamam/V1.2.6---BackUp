# SupportHub 1.48.0

Release date: 2026-08-28

Status: self-contained Windows x64 feature release.

## Included changes

- Implements B-45 searchable form dropdowns across the system.
- Adds one shared accessible search surface to MUI form selectors, with case-insensitive visible-label filtering, keyboard-safe input, a sticky responsive search field, and an explicit no-results state.
- Preserves existing selected IDs, form payloads, validation behavior, dependent fields, and permission-scoped option loading.
- Leaves dedicated autocomplete/server-backed selectors and application navigation or action menus unchanged.

## Database

Required revision: `0144_handover_cleanup`.

This release adds no migration. Existing 1.47.1 databases already at `0144_handover_cleanup` remain compatible.

## Deployment

Back up the database, extract 1.48.0 to a new immutable directory, preserve protected environment values, run `SupportHubBackend.exe migrate` and `seed`, switch IIS to 1.48.0, restart the application pool, and complete `SMOKE-TEST.md`.

## Verification

The release build runs Ruff, strict MyPy, the full backend test suite, frontend ESLint, the full frontend test suite, TypeScript, and the production frontend build. Packaged-runtime migration, runtime command, metadata, content, ZIP-integrity, and forbidden-file checks are recorded in `RELEASE_STEPS.md`.
