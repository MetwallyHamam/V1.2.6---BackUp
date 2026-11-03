# Millensys Support Hub 1.66.129

## Professional deployment workspace

- Corrects the deployment-step Start response on SQL Server by safely normalizing database timestamps before calculating actual duration.
- Adds expiring, revocable, read-only stakeholder links with a branded public live tracker that refreshes every 15 seconds.
- Adds editable deployment name, owner, dates, scope, and rollback plan, including after finalization.
- Adds a structured rollback plan to the workspace and branded PDF/Word reports.
- Allows scoped client-portal users to report deployment issues and records a visible timeline update identifying the client submission.
- Keeps internal ticket automation and internal ownership controls hidden from client users.

## Database and deployment

- Database compatibility advances to `0260_deployment_share_links`.
- Use this release instead of `1.66.128`. Back up production, deploy frontend and backend together, and run `backend\runtime\SupportHubBackend.exe migrate` before recycling IIS.
