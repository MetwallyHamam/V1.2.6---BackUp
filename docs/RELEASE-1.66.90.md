# Millensys Support Hub 1.66.90

## Contract and renewal hardening

- Treats linked contract clients as peers; contract creation no longer requires a user-selected primary client.
- Allows escalation contacts and coverage branches from any linked client.
- Aligns term-bound coverage when contract dates change and returns specific coverage, ticket, or renewal conflict messages.
- Makes active approval groups selectable by contract editors without granting group-administration permission.
- Strengthens renewal closure, successor, task, notification, concurrency, entitlement, and SLA-calendar validation.

## Service checklist workflow and monitoring

- Shows the earliest actionable checklist occurrence instead of allowing future generated work to hide overdue or blocked events.
- Separates My Checklists scope, refreshes monitoring automatically, and calculates due and attention status from current work.
- Enforces evidence and client-handoff workflows and makes completed or cancelled events read-only.
- Synchronizes checklist start and reassignment with linked ticket status and task ownership.
- Protects template retirement, paused schedules, reminders, inactive imports, evidence reporting, and public share data.

## Database and deployment

- Database compatibility remains at `0237_escalation_work_queue`; no migration is introduced.
- Deploy the packaged frontend and backend together.
- Run `backend/runtime/SupportHubBackend.exe migrate` before starting the upgraded application.
