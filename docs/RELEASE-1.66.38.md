# SupportHub 1.66.38 — Support Now and Operations Workflow

Status: **SELF-CONTAINED WINDOWS X64 RELEASE — READY FOR CONTROLLED DEPLOYMENT**

## Enhancements

- Renames Home to Support Now and groups Executive Dashboard and Top Management Dashboards in that sidebar section.
- Adds Support Now as the default landing-page choice for new profiles and profiles without a configured landing page.
- Expands Support Now with the planner, inactive-client paging, ticket and operation approvals, and logged-in-user operation cards.
- Adds direct internal-operation creation from global Quick Actions and an Ops tab in Support Assistant.
- Adds planner double-click actions for internal operations and painted shifts, including date-aware manual multi-engineer assignment and shift-type times.
- Adds governed ticket flags, optional SLA pause/resume behavior, master-data maintenance, permissions, and flag removal.
- Adds ticket flag actions to ticket cards/rows and the Support Assistant three-dot menu.
- Keeps saved-view date filters focused on the selected date type and period.
- Replaces verbose network, timeout, and gateway errors in the UI with short recovery hints while retaining diagnostic details and correlation references in logs.

## Corrections

- Removes the duplicate Create Ticket and Create Pre-Ticket buttons from Support Assistant; both actions remain in global Quick Actions.
- Removes the redundant current-user request formerly used by those Assistant buttons.
- Includes all functionality from `1.66.37`.

## Database

- Database head advances to `0206_ticket_flags` for governed ticket-flag definitions, assignments, and SLA-pause evidence.

## Verification

- Backend Ruff and strict MyPy passed; all 402 backend tests passed.
- Frontend ESLint, all 31 test files and 79 tests, TypeScript compilation, and the production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version `1.66.38`, database head `0206_ticket_flags`, self-contained deployment mode, ZIP readability, and required runtime contents passed.
