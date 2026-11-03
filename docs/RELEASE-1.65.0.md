# SupportHub 1.65.0 — Resolution Services and Dashboard Reliability

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Prevents read-only SLA previews from failing when a ticket receives a concurrent background update; the current ticket version is returned for the eventual guarded save.
- Hides Pending, Escalate, and Handover actions on Resolved and Closed tickets in Support Assistant Mine cards.
- Adds a governed **Default service provided in resolution** flag to Service master data and automatically selects the existing Support Activity service during migration when it can be identified.
- Supports selecting and persisting multiple services provided during ticket resolution without changing the ticket's SLA/classification service.
- Displays provided services on resolved tickets and preserves them with archived resolution evidence when a ticket is reopened.
- Ensures hidden-widget preferences from an old dashboard cannot suppress widgets, including Top 3 Support Agents, on a newly assigned dashboard.

## Database

- Required Alembic head: `0188_default_resolution_service`.
- Migration `0188_default_resolution_service` adds the default-resolution-service flag, the ticket resolution-services association, and archived resolution-service evidence.

## Deployment

1. Back up the SQL Server database and current application directory.
2. Deploy this package to a new versioned directory while preserving production configuration.
3. Run `backend\runtime\SupportHubBackend.exe migrate`.
4. In CRM Service master data, confirm Support Activity is marked as the default resolution service.
5. Verify a resolved ticket can record multiple provided services and that Top 3 Support Agents appears on its assigned dashboard.

## Verification

- Ruff and strict MyPy passed across 154 backend source files.
- All 383 backend tests passed.
- Frontend lint, all 25 test files and 53 tests, TypeScript, and the production Vite build passed.
- The packaged runtime exposed `serve`, `migrate`, `seed`, and `recover-admin` and completed a clean migration through `0188_default_resolution_service`.
- Manifest version, IIS version, database head, required contents, ZIP readability, and forbidden-file inspection passed.
- Archive inspection found 1,792 entries and no forbidden secret, database, cache, or bytecode files.

Artifact: `releases/SupportHub-1.65.0.zip` (`43,104,629` bytes).

SHA-256: `80826843986D6DCE52D28ECD304942A0844E64D30D0628CD85E04A8776759CB8`.
