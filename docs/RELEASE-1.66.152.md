# SupportHub 1.66.152

Release date: 2026-10-17

## Highlights

- Adds a unified client delivery lifecycle to the internal Client Profile and Client Portal.
- Summarizes UAT cycles, deployments, incidents, Change Requests, and Problems with total and active/open counts.
- Provides recent-record drill-down navigation to the appropriate internal or portal workspace.
- Restricts portal lifecycle data to portal-published UAT, client-visible deployments, authorized portal tickets, and Problems linked to those visible tickets.
- Protects internal Problem information by presenting the client-safe linked ticket instead of internal investigation titles or notes.
- Adds the five lifecycle areas to the Client Profile Word report.

## Database

- Retains database revision `0272_deployment_issue_types`.
- No new database migration is required when upgrading from `1.66.151`.

## Deployment

Deploy the updated frontend and backend package. Existing installations at revision `0272_deployment_issue_types` require no additional database migration.
