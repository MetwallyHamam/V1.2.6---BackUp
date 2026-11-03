# SupportHub 1.61.3 — SQL Server Migration Driver Correction

## Included behavior

- Corrects the migration failure raised by the production `pymssql` SQLAlchemy dialect while applying migration `0183_pre_ticket_result_unique`.
- Replaces unsupported unique-constraint reflection with a parameterized SQL Server system-catalog query.
- Continues to discover auto-generated constraint names and scopes discovery to the configured default database schema.
- Retains the filtered unique index fix and all functionality packaged in 1.61.2.

## Deployment

- Deploy 1.61.3 instead of 1.61.2 and preserve production `backend/web.config` secrets and connection values.
- Run `SupportHubBackend.exe migrate`, then `SupportHubBackend.exe seed`.
- Database revision remains `0183_pre_ticket_result_unique`; the failed 1.61.2 attempt did not reach or stamp that revision.

## Verification

- Ruff and strict MyPy passed across 154 backend source files.
- Migration compatibility tests confirm the unsupported reflection API is absent and SQL Server catalog discovery is used.
- All 375 backend tests and all 47 frontend tests passed; the production frontend bundle built successfully.
- The packaged runtime migrated and seeded a clean database through `0183_pre_ticket_result_unique`.
- Standalone commands, manifest and IIS versions, and ZIP integrity passed.
- Package: `releases/SupportHub-1.61.3.zip` (43,052,409 bytes; 1,784 entries; no forbidden generated content).
- SHA-256: `034C84E84C7CA0F9AE2F19C8FCE70910A7420431B216E092AA1EA728991D3268`.
