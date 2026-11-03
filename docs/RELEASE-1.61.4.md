# SupportHub 1.61.4 — Independent Pre-Ticket Creation Permission

## Included behavior

- Allows employees with `ticket.pre_ticket.create` to complete and submit the Pre-Ticket form without `ticket.create`.
- Allows the same permission to read the client options, contacts, Pre-Ticket form settings, and covered contract catalog required by that form.
- Keeps official ticket creation protected independently by `ticket.create`.
- Keeps Pre-Ticket conversion into an official ticket subject to the existing conversion and official-ticket authorization rules.
- Retains the SQL Server migration-driver correction and all functionality from 1.61.3.

## Deployment

- Deploy over 1.61.3 and preserve production `backend/web.config` secrets and connection values.
- Run `SupportHubBackend.exe migrate`, then `SupportHubBackend.exe seed`.
- Database head remains `0183_pre_ticket_result_unique`; no new migration is required.

## Verification

- Regression coverage creates a Pre-Ticket using a user who has `ticket.pre_ticket.create` and explicitly lacks `ticket.create`.
- The same regression confirms official ticket creation remains denied for that user.
- Ruff, strict MyPy, all 8 focused Pre-Ticket tests, all 376 backend tests, frontend ESLint, all 47 frontend tests, TypeScript, and the production build passed.
- The packaged runtime migrated and seeded a clean database through `0183_pre_ticket_result_unique`.
- Standalone commands, manifest and IIS versions, and ZIP integrity passed.
- Package: `releases/SupportHub-1.61.4.zip` (43,057,340 bytes; 1,784 entries; no forbidden generated content).
- SHA-256: `5A77352D46B8DDDDAA830433C491034FCAD5DB99DDCF2764566382BA30FCF1D8`.
