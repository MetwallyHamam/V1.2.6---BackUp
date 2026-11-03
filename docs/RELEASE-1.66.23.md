# SupportHub 1.66.23 — Ticket Creation and Board Resolution Fixes

Status: **SELF-CONTAINED WINDOWS X64 RELEASE CANDIDATE**

## Highlights

- Returns users to the originating workspace or ticket list after ticket creation instead of opening the new ticket detail page.
- Returns Client Portal users to My Requests after ticket creation.
- Keeps the Tickets board open when a card is dropped into the Resolved lane.
- Opens the in-board resolution workflow with the dropped ticket and Resolved status preselected.
- Includes all contract coverage, Saved View/layout, navigation shell, ticket toolbar, and dashboard-layout enhancements from `1.66.22`.

## Database

- Database head remains `0198_saved_view_layout_scope`.

## Deployment

Deploy to a new versioned directory, back up the database, run the packaged migration and seed commands, switch IIS paths, and complete the supplied smoke test.

## Verification

The release builder runs backend lint, strict type checks, the complete backend test suite, frontend lint, the complete frontend test suite, TypeScript compilation, and the production frontend build before packaging.
