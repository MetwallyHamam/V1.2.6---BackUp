# SupportHub 1.66.10 — Third-party Integration Workspace

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Consolidates Outlook / Graph, SMTP Email, and WhatsApp / Inbound API under one **Third-party Integration** Site Settings category with clear inner tabs.
- Adds a built-in inbound API test console that creates a real Pre-Ticket using the currently saved JSON mapping.
- Adds the stable versioned inbound request endpoint while preserving the previous endpoint for compatibility.
- Adds authenticated client lookup and inbound request-status endpoints for vendors.
- Returns clearer field-specific inbound validation details and correlation IDs.
- Updates the bundled PowerShell integration test to use the versioned API.

## API

- `POST /api/v1/integrations/inbound/v1/{provider}/requests`
- `GET /api/v1/integrations/inbound/v1/{provider}/clients?search=...`
- `GET /api/v1/integrations/inbound/v1/{provider}/requests/{event_id}`

## Database

- Required Alembic head remains `0190_inbound_pre_ticket`; no additional migration is required from 1.66.9.

## Deployment

Back up the database, deploy to a new versioned directory, run `backend\runtime\SupportHubBackend.exe migrate`, switch IIS paths, then use **Site Settings → Third-party Integration → WhatsApp / Inbound API → Test integration**.

## Verification

- Backend Ruff and strict MyPy passed; all 386 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, and `recover-admin`.
