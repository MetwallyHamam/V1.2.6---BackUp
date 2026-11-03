# SupportHub 1.66.3 — Refined SLA Alert Frame

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Replaces the Support Assistant SLA alert's double red frame with one clean red border and integrated red leading rail.
- Uses a restrained breathing glow for running tickets that have consumed at least 50% of their resolution SLA.
- Uses a stable, strong red frame for already-breached tickets and respects reduced-motion preferences.
- Retains the Support Assistant-inspired card treatment across Executive and Top Management dashboard widgets.

## Database

- Required Alembic head: `0188_default_resolution_service`.
- No database migration is added by this release.

## Deployment

1. Back up the current SQL Server database and application directory.
2. Deploy this package to a new versioned directory while preserving production configuration.
3. Run `backend\runtime\SupportHubBackend.exe migrate`.
4. Switch the IIS frontend and backend application paths to the new release.
5. Force-refresh the browser and verify normal, near-breach, and breached Support Assistant cards.

## Verification

- Ruff and strict MyPy passed across 154 backend source files; all 383 backend tests passed.
- Frontend ESLint, all 25 test files and 57 tests, TypeScript, and the production Vite build passed.
- PyInstaller produced the bundled Windows backend runtime.
- Manifest version, database head, deployment mode, Support Assistant bundle, required frontend/runtime contents, and ZIP readability passed.

Artifact: `releases/SupportHub-1.66.3.zip` (`42,451,018` bytes; `1,792` entries).

SHA-256: `4C75D5CC0F8F86F067359C0C0C3079581A6BB2E177083CF87FD079A3A6593799`.
