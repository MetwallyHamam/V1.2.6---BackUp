# SupportHub 1.66.43 — Assistant and Ticket Workspace Improvements

Status: **SELF-CONTAINED WINDOWS X64 RELEASE — READY FOR CONTROLLED DEPLOYMENT**

## Enhancements and corrections

- Adds per-user Quick Actions visibility controls through the `+` button's right-click menu.
- Lets users drag the `+` button and saves its position in that browser, with a reset action.
- Removes the redundant page context header above Support Assistant.
- Makes the Tickets page row-count menu open upward so its options remain visible near the bottom of the page.
- Shows approved work hours as a per-client chart and applies the dashboard's selected date and scope filters.
- Includes SQL Server scripts to insert the default SLA and preview or apply conservative root-cause classification from legacy resolution summaries.
- Includes all functionality from `1.66.42`.

## Database

- Database head remains `0206_ticket_flags`; no additional migration is introduced.
- The included SQL scripts are optional operator-run data tasks. Review and back up the database before applying them.

## Verification

- Backend Ruff and strict MyPy passed; all 404 backend tests passed.
- Frontend ESLint, all 79 tests, TypeScript compilation, and production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest, required contents, and ZIP integrity checks passed.
