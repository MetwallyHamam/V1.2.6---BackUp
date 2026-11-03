# Support Hub 1.66.137

## Deployment board card layout

- Keeps content, workflow selectors, helper text, evidence links, and long unbroken values inside every issue card.
- Applies the correction consistently across Open, In Progress, Pending Implementation, Resolved, and Closed lanes.
- Truncates compact status values cleanly while retaining readable wrapped card content.

## Ticket period-filter navigation

- Preserves the complete Tickets-list filter URL when opening a ticket from grid, board, mobile, preview, context-menu, and workflow-action paths.
- Returns users to the same selected period and filters instead of resetting the period to All time.
- Extends the shared semantic-link component to support router navigation state safely.

## Database

- Database revision remains `0263_deployment_issue_stage`.
- No additional database migration or data reset is required when upgrading from `1.66.136`.
