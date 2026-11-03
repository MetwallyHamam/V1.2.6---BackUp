# SupportHub 1.60.0 — Engineer Pre-Tickets

## Purpose

Introduce a governed Engineer Pre-Ticket workflow so engineers can register a minimal request, Call Center can validate it, and an official ticket can be created and assigned directly to the Pre-Ticket creator.

## Included behavior

- Engineer submission, My Pre-Tickets, idempotent retry, and owner-only Confirm & Create Ticket.
- Call Center queue with claim, information request, engineer response, rejection, cancellation, and **Convert & Assign to Creator**.
- Official ticket creation reuses the normal ticket service; SLA begins only when the official ticket is created.
- Feature Policy is OFF by default. Enabling it requires an active Ticket Type and complete P1–P4 Impact/Urgency mapping.
- In-app lifecycle notifications, audit evidence, and permission-gated timing summary.
- English and Arabic Pre-Ticket headings, help text, and metrics labels.

## Deployment

- Deploy over 1.59.7.
- Run database migrations through `0180_pre_ticket_messages`.
- Before enablement, configure the system `engineer_pre_ticket` Feature Policy with `ENFORCED` mode, an active Ticket Type, and P1–P4 Impact/Urgency mappings.
- Assign the new `ticket.pre_ticket.*` permissions to the required engineer, Call Center, and reporting profiles.
- Keep the feature policy OFF until the Fast Create profile has been approved and UAT is complete.
