# SupportHub 1.61.1 — Pre-Ticket Conversion and Navigation Corrections

## Included behavior

- Adds a controlled Call Center conversion dialog for completing missing optional Pre-Ticket Client, Contact, Product, Module, and Service context.
- Keeps context already submitted by the engineer immutable and records completed context in conversion audit evidence.
- Prevents engineer self-service conversion from supplying missing context; normal ticket validation remains authoritative.
- Restores covered products in Pre-Ticket creation and conversion by removing an invalid frontend `is_active` filter from the already active-only contract catalog response.
- Removes duplicate Engineer Pre-Tickets configuration, Email Integration, and Ticket Form Settings shortcuts from the Configuration sidebar. These remain available inside Site Settings.

## Deployment

- Deploy over 1.61.0 and run `SupportHubBackend.exe migrate`, then `SupportHubBackend.exe seed` as the standard compatibility check.
- Database revision remains `0182_pre_ticket_form_context`; this release adds no migration.
- Preserve production `backend/web.config` secrets and connection values while keeping `APP_VERSION=1.61.1`.

## Verification

- Ruff and strict MyPy passed; all 374 backend tests passed.
- Frontend ESLint, all 47 frontend tests, TypeScript, and the production Vite build passed.
- The packaged runtime completed a clean migration and seed through `0182_pre_ticket_form_context`.
- An isolated packaged-runtime rehearsal ran 1.61.0 migration/seed followed by 1.61.1 migration/seed twice; both 1.61.1 passes were idempotent and the database remained at `0182_pre_ticket_form_context`.
- Standalone runtime commands, manifest/version/database-head consistency, ZIP integrity, and the forbidden-file scan passed.
- Package: `releases/SupportHub-1.61.1.zip` (43,049,196 bytes).
- SHA-256: `DC9CDD6EBF717BC205464DB015EBB04AF82C99DB1CDB35691A889EA5DBB9C401`.
