# SupportHub 1.66.9 — Configurable Inbound Requests API

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Adds a configurable authenticated inbound API suitable for WhatsApp Business and other external systems.
- Routes both Create Ticket and Request Call submissions into the Pre-Ticket queue for call-center review.
- Stores provider, external event ID, requester, phone, request kind, and requested ticket type as structured data.
- Adds a dedicated **Site Settings → Inbound Requests API** tab for mappings, aliases, client matching, defaults, and API credential management.
- Includes `operations\Test-InboundPreTicketIntegration.ps1` and `INBOUND-API-LOCAL-TEST.md` for testing without a third party.

## Database

- Required Alembic head: `0190_inbound_pre_ticket`.

## Deployment

Back up the database, deploy to a new versioned directory, run `backend\runtime\SupportHubBackend.exe migrate`, switch IIS paths, then follow `INBOUND-API-LOCAL-TEST.md`.

## Verification

- Backend Ruff, strict MyPy, all 386 backend tests, frontend ESLint, all 68 frontend tests, TypeScript, and the production build passed.
- The packaged executable exposed all supported commands and completed a clean migration through `0190_inbound_pre_ticket`.
