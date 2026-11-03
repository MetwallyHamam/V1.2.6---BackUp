# SupportHub 1.62.0 — Pre-Ticket Entitlement and Resolution Service

## Included behavior

- Shows active uncovered products in Pre-Ticket creation with a clear coverage warning.
- Defers uncovered-contract approval until the Pre-Ticket is converted into an official ticket.
- Uses the existing entitlement approval workflow, leaving the resulting ticket unassigned and pending approval until a manager decides it.
- Adds a required Service Provided selector to the Resolve and Close dialogs, prefilled with the ticket's current service.
- Allows the resolver to select or change the delivered service; the backend validates active Service and Product Module relationships and audits changes.
- Keeps older API transition integrations backward-compatible when they omit the new service value.
- Retains all authorization and SQL Server corrections from 1.61.4.

## Deployment

- Deploy over 1.61.4 and preserve production `backend/web.config` secrets and connection values.
- Run `SupportHubBackend.exe migrate`, then `SupportHubBackend.exe seed`.
- Database head remains `0183_pre_ticket_result_unique`; no new migration is required.

## Verification

- Regression coverage verifies an uncovered product is visible, submits without approval, and requests approval only at conversion.
- Regression coverage verifies resolution changes the ticket service and persists audit evidence.
- Ruff, strict MyPy, all 377 backend tests, frontend ESLint, all 47 frontend tests, TypeScript, and the production Vite build passed.
- The packaged runtime migrated and seeded a clean database through `0183_pre_ticket_result_unique`.
- Standalone commands, manifest and IIS versions, and ZIP integrity passed.
- Package: `releases/SupportHub-1.62.0.zip` (43,060,905 bytes; 1,784 entries; no forbidden generated content).
- SHA-256: `E5FFE35751DC52880514BCF47798F68EB842FEEB5C6FB6890D38521A80D0F760`.
