# SupportHub 1.66.2 — Self-Contained Windows Package

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Delivers the Executive and Top Management dashboard card alignment with the modern Support Assistant visual treatment.
- Delivers red, reduced-motion-aware SLA alert frames for Support Assistant tickets that are at risk of breach or already overrun.
- Packages the backend runtime as a self-contained Windows x64 executable; a separate Python installation is not required on the IIS server.

## Database

- Required Alembic head: `0188_default_resolution_service`.
- No database migration is added by this release.

## Deployment

1. Back up the SQL Server database and current application directory.
2. Deploy this package to a new versioned directory while preserving production configuration.
3. Run `backend\runtime\SupportHubBackend.exe migrate`.
4. Verify the Executive and Top Management dashboards and Support Assistant SLA alert frames.

## Verification

- Ruff and strict MyPy passed across 154 backend source files; all 383 backend tests passed.
- Frontend ESLint, all 25 test files and 57 tests, TypeScript, and the production Vite build passed.
- PyInstaller produced the bundled Windows backend runtime.
- Manifest version, database head, deployment mode, required frontend/runtime contents, and ZIP readability passed.

Artifact: `releases/SupportHub-1.66.2.zip` (`42,451,437` bytes; `1,792` entries).

SHA-256: `EE7AB7282D85FBA73CE4E016B0AD52D321FA60F48F55E6F995827D544DB40909`.
