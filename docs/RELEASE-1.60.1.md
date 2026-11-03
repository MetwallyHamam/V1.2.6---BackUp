# SupportHub 1.60.1 — Pre-Ticket Fast Create Completion

## Purpose

Package the remaining Pre-Ticket usability and configuration work completed after 1.60.0.

## Included behavior

- Inline Contact creation during Pre-Ticket submission; the new Contact is selected immediately.
- Call Center queue local search, ten-item paging, and CSV export for users with report permission.
- Guided Fast Create profile editor in Feature Policy control. It selects the active default Ticket Type and maps P1–P4 to Impact and Urgency.
- The Fast Create profile is required only when the feature policy is enforced; OFF and SHADOW policies can be saved without prematurely selecting production values.
- Additional automated Call Center lifecycle coverage and expanded staging UAT steps.

## Deployment

- Deploy over 1.60.0 and run migrations through `0180_pre_ticket_messages` (no new database migration).
- Keep `engineer_pre_ticket` OFF until an approved Ticket Type and P1–P4 mapping are configured, permissions are assigned, and staging UAT is accepted.
