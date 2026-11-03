# Support Hub 1.66.139

Release date: 2026-10-15

## Highlights

- Fixes the SQL Server upgrade failure in migration `0264_deployment_issue_workflow`.
- Supplies the existing SQL column types when Alembic changes deployment-issue workflow columns to `NOT NULL`, as required by the Microsoft SQL Server dialect.
- Allows databases upgrading from releases before `1.66.138` to complete the deployment-issue workflow migrations normally.
- Preserves safe reruns when a previous upgrade attempt or approved repair script already created the workflow columns.

## Database

- Retains the database head at `0266_deployment_ticket_sync`.
- Corrects migration execution compatibility only; it does not introduce an additional schema revision.

Run the packaged database migration before starting the application pool.

## Deployment notes

1. Back up the production database and application files.
2. Stop or recycle the Support Hub application pool.
3. Deploy the complete `1.66.139` release while retaining the production environment configuration.
4. Run `SupportHubBackend.exe migrate` from the packaged backend runtime.
5. Start the application pool and perform the packaged smoke test.
