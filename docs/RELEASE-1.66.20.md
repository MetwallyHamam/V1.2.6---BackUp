# SupportHub 1.66.20 — Ticket Views and Permission-Safe Workflows

Status: **SELF-CONTAINED WINDOWS X64 RELEASE**

## Highlights

- Adds a durable per-user default Tickets page mode without requiring a Saved View.
- Saves Grid or Cards mode together with columns, widths, grouping, selected lanes, and board settings.
- Corrects deleted Saved View name reuse and filtered Backlog counts.
- Adds colored section accents to Ticket Detail and Customer Success cards.
- Adds engineer names to Satisfaction Results and links ticket IDs and numbers to Ticket Detail.
- Adds the dedicated `ticket.start.progress` permission and separates it from general status changes.
- Removes self-assignment and start-progress access from the default Call Center profile while preserving other permitted status work.
- Hides Support Assistant actions unless the user has every permission required by that action.
- Treats the configured shared Support account as queue ownership: its assigned tickets display in the New lane, while Assigned represents dedicated engineers only.

## Database

- Advances the database head to `0196_ticket_start_progress`.
- Migration `0195_ticket_default_view` stores the personal Tickets page default and card layout.
- Migration `0196_ticket_start_progress` creates the dedicated progress permission, grants it to existing non-Call-Center status profiles, and removes self-assignment from Call Center.

## Deployment

Deploy to a new versioned directory, run the packaged migration and seed commands, switch IIS paths, and verify the Call Center and Support profiles with representative users.

## Verification

The release builder runs backend lint, strict type checks, the complete backend test suite, frontend lint, the complete frontend test suite, TypeScript compilation, and the production frontend build before packaging.
