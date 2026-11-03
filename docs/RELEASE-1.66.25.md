# SupportHub 1.66.25 — Client Portal Ticket Email Fix

Status: **SELF-CONTAINED WINDOWS X64 RELEASE — GENERATED AND VERIFIED**

## Highlights

- Treats both standard Client Portal and Mosaic ticket creation as Client Portal origins for ticket-creation email notifications.
- Applies the enabled Client Portal email settings, governed recipient filtering, templates, and delivery queue to both creation methods.
- Adds regression coverage for both `CLIENT_PORTAL` and `MOSAIC` source channels.
- Includes all enhancements and corrections from `1.66.24`.

## Database

- Database head remains `0198_view_layout_scope`; no migration is required.

## Deployment

Deploy to a new versioned directory, back up the database, run the packaged migration and seed commands, switch IIS paths, and complete the supplied smoke test.

## Verification

- Backend Ruff and strict MyPy passed; all 395 backend tests passed.
- Frontend ESLint, all 70 tests, TypeScript compilation, and the production build passed.
- The bundled runtime command, ZIP integrity, required entries, and forbidden generated-file inspection passed.
