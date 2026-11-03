# SupportHub 1.64.1 — Support Assistant Operational UX

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Separates Queue and Mine ticket-card actions for fast daily handling.
- Queue cards support Assign to Me and Assign & Start Progress without a redundant Open button.
- Mine cards expose Resolve, Pending, Escalate, and Handover through the existing governed ticket dialogs.
- Uses configured ticket-status colors as curved card accents.
- Defaults resolution service selection to Support Activity when a ticket has no existing service.
- Collapses the Assistant description by default and adds shortcuts for the full Support Hub and independent Assistant window.
- Preserves return navigation through ticket and Pre-Ticket creation flows.
- Protects direct ticket creation at both navigation and route levels and revalidates effective access with the server.
- Highlights the Queue tab and plays the user's configured notification sound when a new queue ticket is detected through realtime invalidation or the 30-second recovery poll.

## Database

- Required Alembic head: `0187_support_assistant_daily`.
- No new database migration is required from 1.64.0.

## Deployment

1. Back up the SQL Server database and current application directory.
2. Deploy this package to a new versioned directory while preserving production configuration.
3. Run `backend\runtime\SupportHubBackend.exe migrate`.
4. Verify Queue arrival highlighting/sound and permission-separated ticket/Pre-Ticket creation.

## Verification

- Ruff and strict MyPy passed.
- All 380 backend tests passed.
- All 25 frontend test files and 52 tests passed.
- Frontend lint, TypeScript, and the production Vite build passed.
- The packaged runtime exposed `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version, IIS version, database head, required contents, and ZIP readability passed.
- Archive inspection found 1,791 entries and no forbidden secret, database, cache, or bytecode files.

Artifact: `releases/SupportHub-1.64.1.zip` (`43,097,649` bytes).

SHA-256: `DE2645C68DA88E260F0C9A2346C33E6BEFC748308770F4DC051854D785239B86`.
