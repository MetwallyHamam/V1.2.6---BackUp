# SupportHub 1.66.150

Release date: 2026-10-16

## Highlights

- Corrects quarterly KPI history and finalized-report filtering so a Q3 selection cannot include or name overlapping Q4 reviews.
- Re-evaluates pending ticket entitlement when a contract has been extended, automatically releasing stale approval blocks when coverage is now valid.
- Adds configurable Deployment Issue Types to Master Data with seeded Issue, Error, BUG, and Enhancement values; Issue is the default.
- Shows deployment issue types on workflow cards, linked-ticket descriptions, and PDF/Word deployment reports.
- Adds a dedicated deployment issue content editor for title, description, classification, stage, phase, priority, owner, responsible party, next action, due date, and client visibility.
- Adds independently editable Affects workflow and Update needed indicators to deployment issues, linked tickets, cards, and reports.
- Preserves optimistic concurrency checks and audit history for deployment issue updates.

## Database

- Advances the database revision to `0272_deployment_issue_types`.
- Existing deployment issues are assigned the default Issue type during migration.

## Deployment

Run the packaged database migration before starting the updated application runtime.
