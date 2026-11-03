# SupportHub 1.49.0

Release date: 2026-08-28

Status: self-contained Windows x64 feature release.

## Included changes

- Completes B-38/B-44 by restoring **Create with Mosaic** as a responsive guided Product → Module → linked Service card workflow with URL-restored path state, Back/Change controls, retained draft details, and review before submission.
- Adds authoritative Mosaic catalog-scope and product/module/service relationship validation while preserving normal portal creation, entitlement approval, attachments, and duplicate-submission safeguards.
- Completes B-46 with responsive public ticket tracking, client-safe escalation evidence, server-derived satisfaction states, and secure idempotent inline satisfaction for eligible closed tickets.
- Includes the B-45 direct-in-field dropdown correction across form selects on pages and in dialogs: the first click focuses the original field for immediate normalized, case-insensitive contains filtering without a second search box.
- Preserves dedicated autocomplete/server-backed data scope and leaves navigation, action, account, and context menus unchanged.

## Database

Required revision: `0144_handover_cleanup`.

This release adds no migration. Existing 1.47.1 and 1.48.x databases at `0144_handover_cleanup` remain compatible.

## Deployment

Back up the database, extract 1.49.0 to a new immutable directory, preserve protected environment values, run `SupportHubBackend.exe migrate` and `seed`, switch IIS to 1.49.0, restart the application pool, and complete `SMOKE-TEST.md`.

## Verification

The release build runs Ruff, strict MyPy, the full backend test suite, frontend ESLint, the full frontend test suite, TypeScript, and the production frontend build. Packaged-runtime, clean-migration, metadata, content, and archive-integrity verification are recorded in `RELEASE_STEPS.md`.
