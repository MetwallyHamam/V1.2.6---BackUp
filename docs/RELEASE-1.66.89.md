# Millensys Support Hub 1.66.89

## Critical scheduler correction

- Replaces repeated discovery of every running SLA clock with an indexed `escalation_work_items` queue.
- Backfills one work item for each existing running SLA clock during migration.
- Maintains queue state automatically when SLA clocks are created, assigned, started, paused, resumed, breached, completed, reopened, or materially recalculated.
- Reschedules affected queue entries when SLA warning configuration or escalation rules change.
- Evaluates only work items whose `next_evaluation_at` is due, then schedules the next meaningful warning, rule, or breach threshold.
- Preserves escalation-event, notification, and email-outbox deduplication.

## Operational visibility

- Adds due, pending, processing, and completed queue counts to System Operations.
- Shows the next SLA evaluation time beside scheduler stage durations.
- Keeps renewal lifecycle, UAT reminders, email delivery, and Outlook processing as separately measured stages.

## Database

- Database revision: `0237_escalation_work_queue`.
- The migration creates and indexes the queue and safely backfills existing active clocks.

## Deployment

- Keep the production escalation scheduler disabled until this release is deployed and migrated.
- Run `backend/runtime/SupportHubBackend.exe migrate` before re-enabling the scheduler.
- After startup, verify the queue counts in System Operations and monitor process memory across repeated cycles.
