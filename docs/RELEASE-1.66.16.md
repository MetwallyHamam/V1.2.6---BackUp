# SupportHub 1.66.16 — Ticket Grid and Card Views

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Enables direct drag-and-drop reordering of ticket-grid column headers.
- Enables direct column resizing from each header edge and persists widths per user.
- Adds a selectable Jira-style card view with dynamic columns based on the chosen ticket grouping.
- Supports dragging cards between status columns to change ticket status for authorized users.
- Saves the grid/card mode, grouping, filters, sorting, and visible columns as part of ticket saved views.
- Adds matching English and Arabic interface labels.

## Database

- No new migration is required; the database head remains `0194_ticket_grid_preferences`.

## Deployment

Deploy to a new versioned directory, run the packaged migration command, switch IIS paths, and verify grid resizing, column ordering, saved card views, and status-card drag-and-drop with a representative authorized account.

## Verification

- Backend Ruff and strict MyPy passed.
- All 393 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and the production build passed.
- The bundled runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- ZIP integrity, required runtime inclusion, and forbidden-data inspection passed.
