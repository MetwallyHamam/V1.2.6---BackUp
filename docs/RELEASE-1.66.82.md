# SupportHub 1.66.82 - Simplified service checklists

Release date: 2026-09-27

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Service checklist workflow

- Replaces the operational item presentation with an Excel-style Type, Label, Path/URL, Date and Status grid.
- Limits row status choices to Pending, Complete, Need Attention and Client Responsibility.
- Automatically supplies a default label for Database, System Folder, Service, Report, Profile and Custom row types while keeping it editable.
- Adds rows directly inside the client checklist and defaults new row dates to today.
- Carries each client's latest row configuration into the next scheduled occurrence, resetting status to Pending and date for the new verification.
- Adds an engineer/client monitoring board containing only unfinished checklists; client cards open the checklist directly.

## Reminders and tickets

- Daily due-soon and overdue processing now queues email reminders as well as in-app notifications, with per-day deduplication.
- Scheduled checklists no longer create open tickets.
- Completing a checklist creates one linked Scheduled Service ticket directly in Closed status with resolved and closed timestamps.

## Deployment

- Adds database revision `0234_simple_checklist_rows`.
- Run the packaged migration command before activating the new backend and frontend.
- Deploy both layers together.

## Verification

- Full release validation and packaged-runtime inspection are executed by the self-contained release builder.
