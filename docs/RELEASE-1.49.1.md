# SupportHub 1.49.1

Release date: 2026-08-28

Status: corrected self-contained Windows x64 release; supersedes 1.49.0.

## Included changes

- Retains the B-38/B-44 Mosaic workflow, B-46 public tracking/satisfaction improvements, and B-45 system-wide dropdown behavior from 1.49.0.
- Replaces Client Portal form and filter selects with true editable autocomplete fields using normalized, case-insensitive contains filtering.
- Positions autocomplete results below the editable field with a visible gap so the list does not cover the search area.
- Selects a portal account's sole authorized client in the first catalog response, prevents the transient Mosaic client prompt, and removes the redundant second catalog request.
- Preserves explicit scoped selection for genuine multi-client portal accounts.
- Keeps Client Portal ticket numbers as one unbroken link beside the source chip in the internal Tickets list.

## Database

Required revision: `0144_handover_cleanup`.

This release adds no migration. Existing 1.47.1, 1.48.x, and 1.49.0 databases at `0144_handover_cleanup` remain compatible.

## Deployment

Do not deploy 1.49.0. Back up the database, extract 1.49.1 to a new immutable directory, preserve protected environment values, run `SupportHubBackend.exe migrate` and `seed`, switch IIS to 1.49.1, restart the application pool, and complete `SMOKE-TEST.md`.

## Verification

The release build runs Ruff, strict MyPy, the full backend test suite, frontend ESLint, the complete frontend test suite, TypeScript, and the production frontend build. Packaged-runtime, clean-migration, metadata, content, and archive-integrity verification are recorded in `RELEASE_STEPS.md`.
