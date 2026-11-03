# SupportHub 1.66.83 - Service checklist assignments

Release date: 2026-09-28

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Service checklist operations

- Adds separate Client Assignments, Engineer Board, Work Queue, and Templates & Schedules tabs.
- Links each recurring checklist schedule to a client, engineer, and published template.
- Allows checklist managers to transfer an assignment to another engineer while preserving completed history.
- Updates all unfinished occurrences when an assignment is transferred.
- Gives engineers an own-work view and team leaders a department-wide monitoring board.
- Shows completed, open, client-responsibility, checklist progress, due date, and evidence-gap indicators.

## Excel assignment master data

- Exports an Excel assignment template with client, engineer, and published-template reference sheets.
- Includes one highlighted example row and concise import instructions.
- Imports client, engineer, template, frequency, start date/time, duration, timezone, and active state.
- Supports DAILY, WEEKLY, and MONTHLY frequency values; monthly uses the existing 30-day recurrence convention.

## Scheduler hardening

- Bounds SLA and Outlook scheduler batches to prevent unbounded worker growth.
- Removes the full historical Outlook-message scan from each scheduler cycle.
- Isolates scheduled stages in separate database sessions and releases their object graphs after completion.

## Deployment

- Database revision remains `0234_simple_checklist_rows`; no new migration is required.
- Deploy the packaged frontend and backend together.
- Re-enable the escalation scheduler only after deploying this release.

## Verification

- Full release validation and packaged-runtime inspection are executed by the self-contained release builder.
