# SupportHub 1.59.7 — Coverage Planner Controls

## Purpose

Make coverage requirements actionable from the Unified Planner calendar and keep coverage details accurate after engineer assignments change.

## Included behavior

- Calendar coverage details refresh immediately after a shift is edited or deleted, so assigned-engineer counts do not remain stale.
- Managers can create an empty coverage block for a selected day, then assign engineers later.
- Managers can delete an individual coverage block from Coverage details.
- Managers can select multiple calendar days and bulk-delete coverage blocks that start on those days.
- Coverage-block deletion is audited and does not delete existing engineer shifts.

## Deployment

- Deploy over 1.59.6.
- No database migration is required; the database head remains `0177_ticket_archive`.
- Coverage-block creation and deletion require the existing `shift.manage` permission.
