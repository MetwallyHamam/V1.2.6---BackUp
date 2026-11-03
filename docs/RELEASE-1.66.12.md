# SupportHub 1.66.12 — Central Server Time

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Makes the configured server timezone the single business clock for database writes, dashboards, filters, reports, the Support Assistant, and the Client Portal.
- Adds **Site Settings → General → Server date and time**, with an IANA timezone and daylight-saving control.
- Uses `Africa/Cairo` with server daylight rules by default.
- Removes browser-timezone dependence from ticket and pre-ticket date filtering and dashboard period boundaries.
- Ensures public Client Portal, satisfaction, and live-update pages load the central clock.
- Normalizes inbound aware timestamps before database comparisons and prevents repeated shifts of database-local values.

## Database

- Alembic head advances to `0192_server_local_time`.
- On SQL Server, existing `datetimeoffset` values are rewritten from their UTC presentation to the equivalent Egypt server-local offset while preserving the same instant.
- New ORM datetime writes are normalized to the configured server-local offset.

## Deployment

Back up the production database before deployment. Deploy to a new versioned directory, run `backend\runtime\SupportHubBackend.exe migrate`, switch IIS paths, and verify the displayed server time under **Site Settings → General** before reopening access.

## Verification

- Backend Ruff and strict MyPy passed.
- All 392 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and the production build passed.
- The packaged runtime exposed all supported commands and completed a clean, repeatable migration through `0192_server_local_time`.
