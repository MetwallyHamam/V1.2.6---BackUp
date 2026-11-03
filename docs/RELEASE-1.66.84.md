# SupportHub 1.66.84 - Bulk checklist plan management

Release date: 2026-09-28

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Client checklist plans

- Adds bulk assignment of multiple clients to one engineer and published checklist template.
- Supports Daily, Weekly, and Monthly recurrence selection with a shared first due date and completion allowance.
- Adds multi-select plan transfer to another engineer with a required transfer reason.
- Transfers scheduled, in-progress, and blocked work while preserving completed checklist ownership and history.
- Audits individual and bulk transfers with the previous engineer, new engineer, reason, and affected unfinished work.
- Safely skips clients that already have an active plan for the selected template during bulk assignment.

## User interface

- Adds Bulk Assign Clients, Select All Plans, and Transfer Selected controls to Client Assignments.
- Provides guided dialogs for assignment and transfer operations.
- Keeps the Engineer Board role-scoped for engineers and team leaders.

## Excel assignment master data

- Preserves the client, engineer, template, frequency, start date/time, duration, and active-state relationship.
- Removes timezone from the user-facing workbook and applies the configured server timezone automatically.
- Retains one highlighted example row and populated client, engineer, and template reference sheets.

## Deployment

- Database revision remains `0234_simple_checklist_rows`; no new migration is required.
- Deploy the packaged frontend and backend together.

## Verification

- Full release validation and packaged-runtime inspection are executed by the self-contained release builder.
