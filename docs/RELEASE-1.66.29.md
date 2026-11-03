# SupportHub 1.66.29 — Mentions and Compact Ticket Creation

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Adds permission-controlled ticket mentions for employees, Client Portal users, and other active users who can access the ticket.
- Adds mention actions to Tickets Grid/Cards and Support Assistant, plus `@` activation from the ticket conversation.
- Sends in-system and email notifications, optionally adds mentioned users as followers, and records the mention in ticket history.
- Consolidates outstanding mentions into one attention popup with per-ticket **Open Ticket & Mark Informed** and **Mark all informed** actions.
- Hides final SLA time saved or overrun while a ticket is active and displays the result only after resolution or closure.
- Corrects SLA duration interpolation in the Cards quick preview.
- Makes ticket creation more compact, adds an immediately reachable top Create Ticket action, keeps the bottom action bar sticky, and changes recent caller tickets to a dropdown.

## Database

- Database head remains `0199_ticket_templates`; no migration is required.
- Run the packaged seed command to register the new `ticket.mention` permission.

## Deployment

Deploy to a new versioned directory, back up the database, run the packaged migration and seed commands, switch IIS paths, and complete the supplied smoke test.

## Verification

- Backend Ruff and strict MyPy passed; all 396 backend tests passed.
- Frontend ESLint, all 72 tests, TypeScript compilation, and the production build passed.
- The packaged backend runtime command passed.
- ZIP integrity, manifest, required entries, and forbidden generated-file inspection passed (1,811 entries).
