# SupportHub 1.66.18 — Mobile Ticket Actions and Layout

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Keeps mobile Grid mode as a true horizontally scrollable ticket table instead of rendering it as cards.
-+- Reworks the mobile Cards board with aligned full-width lanes, snap scrolling, compact headers, stable actions, and controlled title wrapping.
- Restores pending-ticket actions on Cards, including return to progress, Pending Client resolution, escalation/help, and handover according to permissions.
- Adds Change Status and the complete fast-action menu to right-click and three-dot card actions.
- Makes Support Assistant cards touch-friendly with a visible three-dot action menu.
- Simplifies the Support Assistant mobile header into Refresh plus a consolidated overflow menu.
- Adds matching English and Arabic labels.

## Database

- No new migration is required; the database head remains `0194_ticket_grid_preferences`.

## Deployment

Deploy to a new versioned directory, run the packaged migration command, switch IIS paths, and verify mobile Grid/Cards separation, pending workflows, and Support Assistant mobile actions with representative permission profiles.

## Verification

- Backend Ruff and strict MyPy passed.
- All 393 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and the production build passed.
- The bundled runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- ZIP integrity, runtime inclusion, and forbidden-data inspection passed.
