# SupportHub 1.66.19 — Mobile Creation and Assistant Workflow

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Restores all permission-aware Support Assistant lifecycle actions on mobile cards.
- Prioritizes reopened tickets globally in Queue and Mine and highlights them with an accessible brown alert treatment.
- Removes accidental single-click card previews and adds a durable Cards/List default selector.
- Opens Support Assistant fast actions in place without navigating away from the Assistant.
- Adds intentional ticket preview access and horizontal scrolling for the Assistant list layout.
- Adds a fixed mobile ticket-creation action bar so Create remains available without scrolling to the end of the form.
- Moves mobile caller, branch, assignment, team, and follower fields into a scrollable Additional Information slide panel.
- Adds the governed `ticket.copy` permission and Copy to new ticket actions to Support Assistant and the main Tickets Cards/Grid menus.
- Prefills reusable request and classification data while excluding ticket identity, workflow state, assignment history, resolution, and audit data.
- Adds matching English and Arabic labels.

## Database

- No new migration is required; the database head remains `0194_ticket_grid_preferences`.
- Run the packaged seed command after deployment to register and assign the new `ticket.copy` permission.

## Deployment

Deploy to a new versioned directory, run the packaged migration and seed commands, switch IIS paths, and verify mobile creation, in-place Assistant actions, reopened-ticket priority, and Copy to new ticket with representative permission profiles.

## Verification

- Backend Ruff and strict MyPy passed.
- All 393 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and the production build passed.
- The bundled runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- A clean packaged migration completed through `0194_ticket_grid_preferences`.
- ZIP integrity, runtime inclusion, required frontend bundles, and forbidden-data inspection passed.
