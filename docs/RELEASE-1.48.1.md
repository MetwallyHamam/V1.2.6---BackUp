# SupportHub 1.48.1

Release date: 2026-08-28

Status: corrected self-contained Windows x64 release; supersedes 1.48.0.

## Included changes

- Retains B-45 searchable form dropdown coverage from 1.48.0.
- Replaces the detached paper-level search surface with a search input integrated directly inside each MUI form dropdown list.
- Corrects filtering to use normalized, case-insensitive contained-text matching against the complete visible option label, including accent-insensitive matching where Unicode normalization supports it.
- Preserves option values, form payloads, validation, permission-scoped data loading, and existing autocomplete/server-backed controls.
- Application navigation and action menus remain unchanged.

## Database

Required revision: `0144_handover_cleanup`.

This release adds no migration. Existing 1.47.1 or 1.48.0 databases at `0144_handover_cleanup` remain compatible.

## Deployment

Do not deploy 1.48.0. Back up the database, extract 1.48.1 to a new immutable directory, preserve protected environment values, run `SupportHubBackend.exe migrate` and `seed`, switch IIS to 1.48.1, restart the application pool, and complete `SMOKE-TEST.md`.

## Verification

The release build runs Ruff, strict MyPy, the full backend test suite, frontend ESLint, the full frontend test suite including real MUI Select integration coverage, TypeScript, and the production frontend build. Packaged-runtime and archive verification are recorded in `RELEASE_STEPS.md`.
