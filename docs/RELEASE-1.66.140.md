# Support Hub 1.66.140

Release date: 2026-10-15

## Highlights

- Fixes SQL Server error 1781 when migration `0264_deployment_issue_workflow` resumes after deployment-issue defaults were already created.
- Detects existing defaults on `responsible_party` and `delivered` and preserves them instead of attempting to bind duplicate default constraints.
- Retains the SQL Server `existing_type` correction introduced after `1.66.138`.
- Supports both clean upgrades and safe retries after the approved deployment-issue repair script or a failed migration attempt.

## Database

- Retains database head `0266_deployment_ticket_sync`.
- Corrects retry compatibility in the existing `0264` migration; no new schema revision is introduced.
- Do not stamp the database or remove existing default constraints. Deploy this release and rerun the packaged migration normally.

## Deployment notes

1. Use `1.66.140` instead of `1.66.138` or `1.66.139`.
2. Back up the production database and application files.
3. Stop or recycle the Support Hub application pool.
4. Deploy the complete `1.66.140` release while retaining production configuration.
5. Run `backend\runtime\SupportHubBackend.exe migrate` from the release root.
6. Start the application pool and perform the packaged smoke test.
