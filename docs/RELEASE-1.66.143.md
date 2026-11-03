# Support Hub 1.66.143

Release date: 2026-10-15

## Highlights

- Gives every Deployment Items and Follow-up lane an independent vertical scrollbar and capped viewport.
- Keeps every issue card at its natural readable height instead of compressing high-volume lanes into thin rows.
- Keeps lane headings and counts visible while the cards scroll.
- Preserves horizontal board scrolling and all deployment improvements from `1.66.141`.

## Database

- Retains database head `0267_deployment_defaults`; no new migration is introduced.

## Deployment notes

1. Deploy `1.66.143` instead of `1.66.142`.
2. Retain the production configuration and recycle the Support Hub application pool.
3. Open a populated workflow lane and confirm cards remain full size while the lane scrolls vertically.
