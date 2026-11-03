# SupportHub 1.66.5 — Assistant Window and Queue Warning Corrections

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Makes the independent Support Assistant popup follow native window-frame resizing.
- Makes Compact, Standard, Wide, and drag resizing change the popup window itself as well as its responsive content.
- Corrects the nine-minute orange Queue warning for tickets held by the shared/default support account while still awaiting a dedicated engineer.
- Fits dashboard widget accent borders cleanly to the cards' curved edges.
- Includes the Support Assistant alert synchronization, Pre-Tickets tab/count, and dashboard drill-down accuracy improvements from 1.66.4.

## Database

- Required Alembic head: `0188_default_resolution_service`.
- No database migration is added by this release.

## Deployment

1. Back up the current SQL Server database and application directory.
2. Deploy this package to a new versioned directory while preserving production configuration.
3. Run `backend\runtime\SupportHubBackend.exe migrate`.
4. Switch the IIS frontend and backend application paths to the new release.
5. Force-refresh the browser and verify Queue warnings, popup resizing, dashboard card borders, Pre-Tickets, and dashboard drill-down counts.

## Verification

- Backend Ruff, strict MyPy, and all 383 backend tests passed.
- Frontend ESLint, all 68 frontend tests, TypeScript, and the production Vite build passed.
- PyInstaller produced the bundled Windows backend runtime.
- The bundled executable exposed `serve`, `migrate`, `seed`, and `recover-admin`; a clean packaged migration passed through `0188_default_resolution_service`.
- Manifest version, database head, deployment mode, IIS executable configuration, required frontend/runtime contents, and ZIP readability passed.

Artifact: `releases/SupportHub-1.66.5.zip` (`43,109,608` bytes; `1,792` entries).

SHA-256: `8D148DCD49EAF67DBBD0D21C704AE04377169533B61CBE5914D8C063F799D25F`.
