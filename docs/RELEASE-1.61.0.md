# SupportHub 1.61.0 — Configurable Pre-Ticket Context

## Included behavior

- Adds **Pre-Ticket Form Settings** beside the existing Ticket Form Settings.
- Keeps Client, Contact, Product, Module, and Service visible at all times.
- Makes the mandatory state of each field configurable; all five are mandatory by default.
- Adds Product → Module → Service selection to Pre-Ticket creation and validates active, linked catalog values.
- Carries Module and Service into official ticket conversion so contract coverage is matched at the configured module/service level.
- Includes the Site Settings Engineer Pre-Tickets entry and the Tickets-page **New Pre-Ticket** fast action introduced in 1.60.3.

## Deployment

- Deploy over 1.60.3 and run `SupportHubBackend.exe migrate`, then `SupportHubBackend.exe seed`.
- Database revision advances to `0182_pre_ticket_form_context`.
- Existing Pre-Tickets remain valid; the newly added Module and Service columns are nullable.
- Form configuration changes require `configuration.manage`. Engineers with `ticket.pre_ticket.create` can read the effective form configuration.

## Verification

- Clean database migration to revision `0182_pre_ticket_form_context` passed.
- Ruff and strict MyPy passed across 154 source files; all 374 backend tests passed.
- Frontend ESLint, all 47 frontend tests, TypeScript, and the production Vite build passed.
- Standalone runtime commands, manifest revision/version, and ZIP integrity passed (1,783 entries).
- Package: `releases/SupportHub-1.61.0.zip` (43,044,874 bytes).
- SHA-256: `F5D3298604CBB0DAB6E91793038D26F1B1625F19D87115420CDD1845D74C674C`.
