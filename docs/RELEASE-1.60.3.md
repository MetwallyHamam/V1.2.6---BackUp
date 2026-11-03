# SupportHub 1.60.3 — Pre-Ticket Discovery

## Included behavior

- Adds an **Engineer Pre-Tickets** entry in Site Settings. It opens Feature & Policy Control directly on the Engineer Pre-Tickets system policy.
- Adds a **New Pre-Ticket** fast action to the Tickets page for users with `ticket.pre_ticket.create`.
- Retains Feature Policy as the single governed source for enabling or disabling Pre-Tickets; the new Site Settings entry is a direct, discoverable configuration path.

## Deployment

- Deploy over 1.60.2. No database migration is required; database head remains `0181_pre_ticket_queue_views`.
- The Site Settings configuration entry requires `feature_policy.view`; changing policy mode requires `feature_policy.manage`.
- Pre-Ticket submission remains guarded by `ticket.pre_ticket.create` and the effective Engineer Pre-Tickets policy mode.

## Follow-up

- Pre-Ticket form-field configurability is deliberately not included until the mandatory/optional rules for Client, Contact, Product, Proposed Priority, and Title are approved.
