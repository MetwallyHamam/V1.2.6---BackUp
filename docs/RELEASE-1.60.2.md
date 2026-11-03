# SupportHub 1.60.2 — Pre-Ticket Queue Completion

## Purpose

Package the Pre-Ticket queue improvements completed after 1.60.1.

## Included behavior

- Call Center queue search, paging, status filtering, and CSV export run on the server, with accurate filtered totals and complete matching exports.
- Call Center users can save, apply, and remove private named queue views containing a search term and status filter.
- Database compatibility advances to `0181_pre_ticket_queue_views` through an additive migration.

## Deployment

- Deploy over 1.60.1 and run migrations through `0181_pre_ticket_queue_views`.
- Queue views are private to their creator and require existing queue-view permission; CSV export additionally requires the existing Pre-Ticket report permission.
- Keep `engineer_pre_ticket` OFF until the approved Fast Create profile, permission assignments, and staging UAT are complete.

## Remaining release readiness

- A production-copy upgrade rehearsal and controlled staging UAT are still required before production enablement.
