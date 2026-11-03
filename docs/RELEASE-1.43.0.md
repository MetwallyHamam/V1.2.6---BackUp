# SupportHub 1.43.0

Release date: 2026-08-26

This release completes product backlog items B-01 through B-18 across tickets, contracts, onboarding, knowledge, CRM, the Client Portal, scheduling, and authentication.

Status: self-contained Windows x64 package built and verified.

## Highlights

- Adds secure public live ticket-update links with copy and WhatsApp actions.
- Supports multiple typed resources per training material, assignment replacement with history, and task-duration scheduling.
- Adds Training Materials to Knowledge and centralizes Knowledge administration through grouped Master Data navigation.
- Adds Mosaic portal ticket creation and Total Working Hours to the portal dashboard.
- Links CRM services to multiple product modules.
- Improves mobile Clients, contract-workspace closing, unassigned-ticket filtering, portal date filtering, and adjustment-reason management.
- Makes Needs Attention collapsible and moves Advanced Templates into Unified Planner.
- Restores the originally requested ticket URL after authentication.

## Database

Required revision: `0132_service_module_links`.

This release includes additive migrations for public ticket-update tokens and service-to-module links. Back up the production database before migration.

## Deployment

Stop the IIS application pool, preserve the protected production environment values in the new `backend\web.config`, then run from the extracted release root:

```powershell
.\backend\runtime\SupportHubBackend.exe migrate
.\backend\runtime\SupportHubBackend.exe seed
```

Confirm revision `0132_service_module_links`, switch IIS to the immutable `1.43.0` directory, restart the pool, and complete the packaged smoke test.

## Artifact

- Package: `releases/SupportHub-1.43.0.zip`
- Size: 42,272,413 bytes
- Entries: 1,671
- SHA-256: `A49DA7907AD5084D01CA2AF30A17C8102BF5C66DA1C36C94CDAD46F723093583`
- Verification: 287 backend tests, 12 frontend tests, lint, MyPy, TypeScript, production frontend build, standalone runtime help, manifest/database head, ZIP integrity, migration inclusion, and forbidden-file inspection passed.
