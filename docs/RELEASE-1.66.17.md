# SupportHub 1.66.17 — Advanced Ticket Board

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Adds an advanced dynamically grouped ticket board with selectable visible lanes and saved Grid/Cards defaults.
- Adds reliable status-lane drag-and-drop, optimistic updates, workflow-aware protected transitions, and permission feedback.
- Adds configurable card density and fields, swimlanes, lane limits, collapsible and movable lanes, and manual card ordering.
- Adds lane workload and SLA/P1 risk metrics, quick filters, live board refresh, ticket preview, and assistant-style fast actions.
- Adds an explicit Save Layout workflow for durable ticket-grid column order and widths.
- Adds matching English and Arabic labels.

## Database

- No new migration is required; the database head remains `0194_ticket_grid_preferences`.
- Board configuration is stored through the existing saved-view metadata.

## Deployment

Deploy to a new versioned directory, run the packaged migration command, switch IIS paths, and verify saved Grid and Cards defaults, status dragging, lane configuration, preview, and grid layout persistence with representative authorized accounts.

## Verification

- Backend Ruff and strict MyPy passed.
- All 393 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and the production build passed.
- The bundled runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- ZIP integrity, runtime inclusion, and forbidden-data inspection passed.
