# SupportHub 1.66.155

Release date: 2026-10-23

## Highlights

- Makes repeated clicks on the Tickets navigation item alternate between Today's tickets and All Time.
- Resets filtered or ticket-detail navigation back to Today's tickets on the first Tickets navigation click.
- Keeps `PENDING_CLIENT` tickets in the Pending Client board lane after work has previously started.
- Applies the same protection to other pending statuses so an earlier progress timestamp cannot move them back into In Progress visually.
- Retains the dedicated workflow-list layouts delivered in `1.66.154`.

## Database

- Retains database revision `0272_deployment_issue_types`.
- No new database migration is required when upgrading from `1.66.154`.

## Deployment

Deploy the updated frontend and backend package. After deployment, hard-refresh open browser sessions so the updated navigation and board logic is loaded.
