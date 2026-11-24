# SupportHub 1.66.166

Release date: 2026-11-07

Status: source implementation complete; release package not built.

## Advanced system maintenance

- Schedule log cleanup, verified SQL Server database backups, and compressed backend/frontend backups.
- Supports daily, weekly, and monthly execution using the server's configured timezone.
- Each schedule controls retention days, minimum copies to preserve, enabled state, and next execution.
- Administrators can run each maintenance type immediately and inspect status, duration, deleted-item count, artifact size/path, summary, and errors.
- SQL Server backups continue to use `COPY_ONLY`, `CHECKSUM`, and `RESTORE VERIFYONLY`.
- Application source/destination paths are controlled through server configuration rather than browser input.

## Access control

- `maintenance.view` — view schedules and history.
- `maintenance.manage` — create and edit schedules.
- `maintenance.run` — start manual maintenance.

## Deployment configuration

- `MAINTENANCE_BACKUP_PATH` defaults to `../backups/application`.
- `MAINTENANCE_APPLICATION_PATHS` defaults to `.,../frontend`.
- `MAINTENANCE_SCHEDULER_ENABLED` defaults to enabled; no work runs until an enabled schedule exists.
- Database revision advances to `0280_maintenance_scheduling`.
