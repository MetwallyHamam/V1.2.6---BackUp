# SupportHub 1.66.7 — Support Assistant Backlog and Dashboard Accuracy

Status: **SELF-CONTAINED WINDOWS X64 RELEASE CANDIDATE**

## Highlights

- Adds the permission-controlled Support Assistant Backlog tab with Today, This Week, Last Week, This Month, and custom date ranges.
- Adds Site Settings for Support Assistant refresh timing, warning threshold, page size, Mine status inclusion, Backlog default period, sorting, attention animation, and user overrides.
- Makes Follow-up manual-only and keeps Assistant tab visibility controlled exclusively by permissions.
- Aligns main-dashboard ticket card drill-downs with authoritative SLA calculations, assignment dates, and browser timezone boundaries.
- Corrects Top Management Tickets, Resolved, status, priority, product, root-cause, and engineer-workload drill-down populations.
- Makes Customer SLA and Customer Satisfaction cards open the exact evidence used to calculate their values.
- Excludes archived tickets consistently from Top Management ticket analytics and drill-downs.

## Database

- Required Alembic head: `0189_support_assistant_backlog`.
- Migration `0189_support_assistant_backlog` adds `support_assistant.backlog.view` and grants it to profiles that already have Mine access.

## Deployment

1. Back up the SQL Server database and current application directory.
2. Deploy this package to a new versioned directory while preserving production configuration.
3. Run `backend\runtime\SupportHubBackend.exe migrate`.
4. Switch the IIS frontend and backend paths to the new release.
5. Force-refresh the browser and verify Assistant Backlog access and dashboard card drill-down totals.

## Verification

- Release quality gates, packaged runtime smoke checks, migration verification, artifact size, and SHA-256 are recorded in `RELEASE_STEPS.md`.
