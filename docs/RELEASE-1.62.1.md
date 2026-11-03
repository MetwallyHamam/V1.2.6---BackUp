# SupportHub 1.62.1 — Independent Pre-Ticket Conversion Permission

## Included behavior

- Adds `ticket.pre_ticket.convert_assign` specifically for converting a Pre-Ticket and assigning the resulting official ticket to its creator.
- Removes the previous `ticket.create` prerequisite from the Convert & Assign action.
- Separates conversion from `ticket.pre_ticket.queue.process`; claim, information request, rejection, and cancellation remain queue-processing actions.
- Shows Convert & Assign only to users with the new permission.
- Grants the new permission to the system Call Center profile during migration for upgrade continuity; custom profiles can be governed independently.
- Retains the uncovered-product approval and resolution-service enhancements from 1.62.0.

## Deployment

- Deploy over 1.62.0 and preserve production `backend/web.config` secrets and connection values.
- Run `SupportHubBackend.exe migrate`, then `SupportHubBackend.exe seed`.
- Database head advances to `0184_pre_ticket_convert_perm`.

## Verification

- Regression coverage converts a Pre-Ticket using a user with `ticket.pre_ticket.convert_assign` who lacks both `ticket.create` and `ticket.pre_ticket.queue.process`.
- Clean migration reached 0184 and seeded the permission exactly once.
- Ruff, strict MyPy, focused backend tests, frontend ESLint, and TypeScript passed before packaging.
- Packaging is deferred by request; no 1.62.1 artifact has been built.
