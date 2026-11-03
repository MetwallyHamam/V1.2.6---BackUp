# Support Hub 1.66.144

Release date: 2026-10-15

## Highlights

- Fixes the Resolved lane by enforcing natural readable height directly on every card; cards can no longer collapse into thin rows.
- Keeps each workflow lane in a capped, independently scrollable viewport.
- Adds drag-and-drop workflow transitions between deployment-item lanes.
- Highlights the active drop target and dims the card being moved.
- Routes every valid drop through the existing workflow dialog so required reasons, resolution details, root cause, service, and server-time dates remain governed.
- Rejects invalid direct status jumps with a clear message.

## Database

- Retains database head `0267_deployment_defaults`; no new migration is introduced.

## Deployment notes

1. Deploy `1.66.144` instead of `1.66.142` or `1.66.143`.
2. Retain production configuration and recycle the Support Hub application pool.
3. Confirm Resolved cards remain full size and scroll vertically.
4. Drag a card into an allowed target lane, complete the workflow dialog, and save.
