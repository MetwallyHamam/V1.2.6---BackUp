# SupportHub 1.66.162

Release date: 2026-11-04

## Hotfixes

- Corrects the SQL Server-specific Work Assignments queue `500 Internal Server Error` using portable `CASE` ordering.
- Corrects the assignment form's invalid `GET /clients?limit=500` request.
- Loads every active client through consecutive validated 200-row API pages, with no overall selector limit.
- Shows fields relevant to the selected task type and stores those details with the assignment.
- Adds searchable, clickable ticket links for ticket follow-up tasks.
- Defaults the planned start to the current local time, the due time to one hour later, and KPI classification to External.
- Limits the multi-engineer selector to active employees in the Support department.

## Database

- Advances the database revision to `0278_work_assignment_context`.
- Run the packaged migration when upgrading from `1.66.160` or `1.66.161`.

## Deployment

Deploy the complete `1.66.162` package and recycle the IIS application pool once. Smoke-test My Workspace, the Work Assignments Mine queue, and opening the Assign Task form with the complete client list.
