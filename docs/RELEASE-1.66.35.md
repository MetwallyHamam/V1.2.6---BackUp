# SupportHub 1.66.35 — Dashboard and Gateway Recovery

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Eliminates repeated execution of the permission-filtered ticket scope while loading dashboard filter metadata.
- Aggregates online-engineer ticket counts and priorities in SQL instead of materializing every active ticket in Python.
- Applies the analytical request timeout to dashboard metadata and online-engineer requests.
- Automatically retries read-only requests after short-lived IIS/backend `502`, `503`, or `504` responses.
- Includes all deployable enhancements and corrections from `1.66.34`.

## Database

- Database head remains `0203_checklist_schedules`; environments already upgraded for `1.66.34` require no new schema migration.

## Deployment

Deploy the frontend and backend from this same release together. Back up SQL Server, run the packaged migration command, switch both IIS paths, recycle the application pool, and complete the supplied smoke test. Confirm that `/api/v1/health` reports version `1.66.35` after the switch.

## Verification

- Backend Ruff and strict MyPy passed; all 401 backend tests passed.
- Frontend ESLint, all 72 tests, TypeScript compilation, and the production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.35`, database head `0203_checklist_schedules`, self-contained deployment mode, required contents, ZIP readability, and forbidden-file inspection passed (1,830 entries).
- Initial artifact: `releases/SupportHub-1.66.35.zip` (43,343,240 bytes).
- Initial SHA-256: `AF9792169B54F5BDBF610F86C53A5BBD0B387CF2A7170EFA44E60008E32569F6`.
- Final artifact after documentation refresh: `releases/SupportHub-1.66.35.zip` (43,343,580 bytes; 1,830 entries).
- Final SHA-256: `99F21011B4C4A38E384342678DFF877DDCF8B4090160160E360887F93F207B61`.
