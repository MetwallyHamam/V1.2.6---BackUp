# SupportHub 1.66.154

Release date: 2026-10-23

## Highlights

- Corrects the workflow-tab layout isolation introduced in `1.66.153`.
- Gives Escalations, Shift Handover, Approvals, and Trash fixed workflow-specific list columns instead of reusing the saved Tickets columns, widths, density, or grouping.
- Hides column and board-layout customization on those dedicated workflow tabs while preserving their filters, sorting, selection, and actions.
- Adds Archived and Archive Reason columns to the Trash workflow.
- Preserves each user's normal Tickets layout unchanged when moving between regular tickets and workflow tabs.
- Retains the SQL Server `READ UNCOMMITTED` connection behavior and multi-organization implementation plan from `1.66.153`.

## Database

- Retains database revision `0272_deployment_issue_types`.
- No new database migration is required when upgrading from `1.66.153`.

## Deployment

Deploy the updated frontend and backend package. Existing installations at revision `0272_deployment_issue_types` require no database migration.
