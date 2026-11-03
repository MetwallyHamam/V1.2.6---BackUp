# SupportHub 1.66.32 — Theme-Aware Management Map

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Corrects the Top Management world map presentation in both light and dark modes.
- Adds theme-aware ocean, land, border, grid, shadow, supported-market, hover-card, client-text, and legend-chip colors.
- Improves country hover contrast and tooltip positioning.
- Retains linked-client names, keyboard focus, and country drill-down behavior.
- Leaves all Tickets and Support Assistant right-click and fast-action menus unchanged.

## Database

- Database head remains `0199_ticket_templates`; no new migration is required.

## Deployment

Deploy to a new versioned directory, back up the database, run the packaged migration and seed commands, switch IIS paths, and complete the supplied smoke test.

## Verification

- Backend Ruff and strict MyPy passed; all 397 backend tests passed.
- Frontend ESLint, all 72 tests, TypeScript compilation, and the production build passed.
- The packaged runtime exposed `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version, database head, deployment mode, required contents, ZIP integrity, and forbidden-file inspection passed.
- Final artifact details are recorded in `RELEASE_STEPS.md`.
