# Support Hub 1.66.142

Release date: 2026-10-15

## Highlights

- Caps every Deployment Items and Follow-up lane to a compact viewport instead of allowing large issue volumes to extend the full page.
- Adds an independent thin vertical scrollbar to each workflow lane so all remaining cards stay accessible.
- Keeps the lane heading and item count visible while its cards scroll.
- Preserves the board's horizontal lane scrolling and contains mouse-wheel scrolling inside the active lane.
- Includes all deployment workflow, server-time, resolver, Change Request, catalog-default, and report improvements from `1.66.141`.

## Database

- Retains database head `0267_deployment_defaults`; no additional migration is required after upgrading from `1.66.141`.

## Deployment notes

1. Back up the application files.
2. Deploy the complete `1.66.142` release while retaining production configuration.
3. Recycle the Support Hub application pool.
4. Open a deployment with more than ten follow-up items and confirm each lane scrolls independently.
