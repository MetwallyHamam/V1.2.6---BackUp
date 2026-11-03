# SupportHub 1.66.153

Release date: 2026-10-23

## Highlights

- Makes SQL Server application connections use `READ UNCOMMITTED`, the connection-level equivalent of applying `WITH (NOLOCK)` to all reads.
- Keeps the read-isolation behavior limited to SQL Server and configurable through `DATABASE_READ_UNCOMMITTED`.
- Forces the Tickets-page Escalations, Shift Handover, Approvals, and Trash workflows to use their dedicated list layout instead of inheriting the normal ticket board layout.
- Keeps sorting, filters, workflow actions, and existing user layout preferences intact while hiding board-only controls on those workflow tabs.
- Adds a consolidated multi-organization Project Delivery and Product Development implementation plan for Egypt, Gulf, Projects, Implementation, Business, Development, releases, and Support handover.

## Database

- Retains database revision `0272_deployment_issue_types`.
- No new database migration is required when upgrading from `1.66.152`.

## Configuration

- `DATABASE_READ_UNCOMMITTED` defaults to `true` for SQL Server connections.
- Set `DATABASE_READ_UNCOMMITTED=false` to restore the database driver's normal isolation level.

## Deployment

Deploy the updated frontend and backend package and restart the backend process so newly created SQL Server pool connections use the configured isolation level. Existing installations at revision `0272_deployment_issue_types` require no database migration.
