# SupportHub 1.66.21 — Support Assistant Action Navigation Fix

Status: **SELF-CONTAINED WINDOWS X64 RELEASE**

## Highlights

- Corrects Support Assistant ticket actions on mobile and desktop.
- Ticket action pages now open through the authenticated application route instead of an embedded iframe, avoiding the server's frame-protection error.
- Returning from an action restores the active Support Assistant tab.

## Database

- Database head remains `0196_ticket_start_progress`; no migration is required.

## Deployment

Deploy to a new versioned directory, run the packaged migration and seed commands, switch IIS paths, and confirm ticket actions open and return to the Support Assistant correctly on a mobile device.

## Verification

The release builder runs backend lint, strict type checks, the complete backend test suite, frontend lint, the complete frontend test suite, TypeScript compilation, and the production frontend build before packaging.
