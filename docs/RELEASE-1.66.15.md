# SupportHub 1.66.15 — Compact Personal Ticket Workspace

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Adds per-user ticket-grid layouts with drag-and-drop column ordering, visible-column selection, compact or standard density, page size, sorting, and grouping.
- Moves saved ticket views into editable tabs below the Tickets filter bar and removes the separate Saved Views sidebar entry.
- Adds saved-view update, rename, default, and delete controls while retaining governed Private, Team, Department, and Global scopes.
- Adds Created, Updated, Assigned, Resolved, and Closed date filtering with Today, Yesterday, This Week, Last Week, This Month, Last Month, Custom, and All Time presets.
- Compacts ticket headers, toolbars, actions, filters, table rows, and the inactive-client indicator.
- Adds sticky and directly sortable table headers, sort-direction indicators, truncation tooltips, compact active-filter handling, and scroll-position restoration.
- Adds native middle/scroll-wheel ticket opening in a new browser tab and responsive ticket cards on mobile devices.
- Adds matching English and Arabic labels.

## Database

- Advances the database head to `0194_ticket_grid_preferences`.
- Adds the `ticket_grid_preferences` table for durable, cross-browser per-user grid configuration.
- Adds an audited update endpoint for owned saved views.

## Deployment

Back up the production database before deployment. Deploy to a new versioned directory, run `backend\runtime\SupportHubBackend.exe migrate`, switch IIS paths, and verify the Tickets page with a representative engineer account.

## Verification

- Backend Ruff and strict MyPy passed.
- All 393 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and the production build passed.
- Standalone runtime commands and a clean packaged migration through `0194_ticket_grid_preferences` passed.
- ZIP integrity, required migration inclusion, and forbidden-data inspection passed.
