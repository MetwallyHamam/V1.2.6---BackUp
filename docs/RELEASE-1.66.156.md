# SupportHub 1.66.156

Release date: 2026-10-24

## Highlights

- Keeps the Tickets navigation item on Today's tickets when it is clicked repeatedly; it no longer toggles to All Time.
- Keeps client-pending and other pending tickets in their actual pending lanes after work has started.
- Allows multiple tickets to be linked to a Problem in one atomic relationship action.
- Adds version-safe removal of linked Problem tickets with a required audit reason.
- Adds the required root-cause and permanent-fix summaries directly to the Close Problem dialog.
- Adds a dedicated native ITOP ticket migration tab with preview and confirmation controls for missing clients, engineers, and callers.
- Migrates ITOP ticket details, caller links, assignment history, public and private logs, resolution summaries, statuses, and historical dates while leaving unavailable product data empty.

## Database

- Retains database revision `0272_deployment_issue_types`.
- No new database migration is required when upgrading from `1.66.154`.

## Deployment

Deploy the updated frontend and backend package. After deployment, hard-refresh open browser sessions so the updated navigation, Problem Management, and Data Migration interfaces are loaded.
