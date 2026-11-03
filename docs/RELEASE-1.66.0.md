# SupportHub 1.66.0 — Modern Support Assistant Workflow

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Makes assigned Mine cards expose **Start Progress** and **Handover**, then switches in-progress cards to **Resolve**, **Pending**, and **Escalate** actions.
- Limits the Follow-up tab to tickets that are currently In Progress or explicitly marked for follow-up.
- Sorts Queue and Mine by newest creation date first.
- Replaces the three-dot card menu with right-click actions and the accessible `Shift+F10` equivalent.
- Adds drag-and-drop card ordering persisted through the engineer's existing Support Assistant preferences.
- Modernizes the Assistant with responsive surfaces, hover elevation, light/dark styling, and a dynamic status-colored shadow rail.
- Displays the ticket creation time on Assistant cards.

## Database

- Required Alembic head: `0188_default_resolution_service`.
- No database migration is added by this release.

## Deployment

1. Back up the SQL Server database and current application directory.
2. Deploy this package to a new versioned directory while preserving production configuration.
3. Run `backend\runtime\SupportHubBackend.exe migrate`.
4. Verify Queue and Mine use newest-created ordering.
5. Assign a Queue ticket without starting it and confirm the Mine card shows Start Progress and Handover.
6. Start the ticket and confirm the card shows Resolve, Pending, and Escalate.
7. Verify right-click actions, drag ordering, and Follow-up membership.

## Verification

- Ruff and strict MyPy passed across 154 backend source files.
- All 383 backend tests passed.
- Frontend lint, all 25 test files and 55 tests, TypeScript, and the production Vite build passed.
- The packaged runtime exposed `serve`, `migrate`, `seed`, and `recover-admin` and completed a clean migration through `0188_default_resolution_service`.
- Manifest version, IIS version, database head, required contents, ZIP readability, and forbidden-file inspection passed.
- Archive inspection found 1,792 entries and no forbidden secret, database, cache, bytecode, or dependency-source files.

Artifact: `releases/SupportHub-1.66.0.zip` (`43,106,217` bytes).

SHA-256: `10BD74E5684A3E7592AF2657D41A1BDCD093A6EA6DBA1BBA44BE81CBC90C08B5`.
