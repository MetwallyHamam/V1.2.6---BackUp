# SupportHub 1.66.161

Release date: 2026-11-04

## Hotfix

- Corrects a SQL Server-specific `500 Internal Server Error` when My Workspace or Work Assignments loads the current engineer's task queue.
- Replaces the unsupported direct boolean due-date ordering expression with a SQL Server-safe `CASE` expression.
- Preserves due-dated assignments first, ordered by due date, followed by assignments without a due date.

## Database

- Retains database revision `0277_work_assignments`.
- No additional migration is required when upgrading from `1.66.160`.

## Deployment

Deploy the complete `1.66.161` package and recycle the IIS application pool once. The database already at `0277_work_assignments` does not require another migration. Smoke-test My Workspace and `GET /api/v1/work-assignments?scope=MINE&limit=20` using an employee account.
