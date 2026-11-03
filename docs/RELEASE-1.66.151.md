# SupportHub 1.66.151

Release date: 2026-10-16

## Highlights

- Redesigns the deployment Word report issues section as a structured ticket register.
- Gives every issue intake field its own column, including ticket number, record type, issue type, product, module, description, stage, phase, workflow impact, update requirement, priority, reporter, reported date, and responsible party.
- Adds a coordinated workflow and resolution table with owner, status, workflow context, next action, due date, resolution, resolver department, resolved by, root cause, service provided, resolution and delivery dates, and linked problems.
- Uses A3 landscape pages, fixed column widths, compact typography, wrapped content, repeating headers, alternating rows, and non-splitting ticket rows to keep wide reports readable.
- Applies the enhanced Word layout to both internal and shared deployment reports.

## Database

- Retains database revision `0272_deployment_issue_types`.
- No new database migration is required when upgrading from `1.66.150`.

## Deployment

Deploy the updated frontend and backend package. Existing deployments already at database revision `0272_deployment_issue_types` do not require a new migration.
