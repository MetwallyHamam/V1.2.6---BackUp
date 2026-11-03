# SupportHub 1.49.3

Release date: 2026-08-28

Status: corrective self-contained Windows x64 release; supersedes 1.49.2.

## Included changes

- Retains all functionality and corrections packaged in 1.49.2.
- Forces shared searchable form dropdown result lists across Tickets, dialogs, filters, forms, administration, and workspaces to begin six pixels below their fields.
- Prevents MUI's automatic placement from moving a result list above or over its editable search field.
- Limits menu height to the viewport space available below the field and recalculates placement during scrolling and window resizing.
- Preserves immediate field typing, normalized case-insensitive contains filtering, selected values, permissions, server-backed loading, accessibility, dedicated autocomplete controls, and action/navigation menus.

## Database

Required revision: `0144_handover_cleanup`.

This release adds no migration. Existing 1.47.1, 1.48.x, and 1.49.x databases at `0144_handover_cleanup` remain compatible.

## Deployment

Back up the database, extract 1.49.3 to a new immutable directory, preserve protected environment values, run `SupportHubBackend.exe migrate` and `seed`, switch IIS to 1.49.3, restart the application pool, and complete `SMOKE-TEST.md`.

## Verification

The release builder runs Ruff, strict MyPy, the full backend test suite, frontend ESLint, the complete frontend test suite, TypeScript, and the production frontend build. Packaged-runtime, clean-migration, metadata, content, and archive-integrity verification are recorded in `RELEASE_STEPS.md`.
