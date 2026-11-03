# SupportHub 1.49.2

Release date: 2026-08-28

Status: corrective self-contained Windows x64 release; supersedes 1.49.1.

## Included changes

- Retains all functionality and corrections packaged in 1.49.1.
- Corrects shared searchable form dropdowns across Tickets, dialogs, filters, forms, and workspaces so the results list opens below the editable field with a visible gap.
- Removes the competing selected-option autofocus and legacy typeahead behavior; one click focuses the visible field and accepts typing immediately.
- Uses normalized, case-insensitive contains filtering and indexes visible option labels once per menu opening to avoid repeatedly traversing every option while typing.
- Keeps the dropdown menu in MUI's accessible overlay layer and preserves existing selected values, permissions, server-backed loading, dedicated autocomplete controls, and action/navigation menus.

## Database

Required revision: `0144_handover_cleanup`.

This release adds no migration. Existing 1.47.1, 1.48.x, and 1.49.x databases at `0144_handover_cleanup` remain compatible.

## Deployment

Back up the database, extract 1.49.2 to a new immutable directory, preserve protected environment values, run `SupportHubBackend.exe migrate` and `seed`, switch IIS to 1.49.2, restart the application pool, and complete `SMOKE-TEST.md`.

## Verification

The release builder runs Ruff, strict MyPy, the full backend test suite, frontend ESLint, the complete frontend test suite, TypeScript, and the production frontend build. Packaged-runtime, clean-migration, metadata, content, and archive-integrity verification are recorded in `RELEASE_STEPS.md`.
