# SupportHub 1.59.3 — Historical SLA Calculation Correction

## Purpose

Correct SLA calculation failures for historical tickets older than one year.

## Correction

- Replaces the 370-day elapsed-time loop limit with a 100-year data-sanity limit.
- Allows valid long-lived support tickets to appear in ticket lists and be evaluated by the scheduled SLA escalation process.
- Retains a finite guard for clearly corrupt timestamps.
- Adds regression coverage for an SLA period beyond the former one-year limit.

## Deployment

- Deploy this release over 1.59.2 to restore ticket-list and scheduled SLA escalation processing for historical tickets.
- No database migration is required; the database head remains `0177_ticket_archive`.
