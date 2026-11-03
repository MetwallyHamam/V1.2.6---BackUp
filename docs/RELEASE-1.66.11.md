# SupportHub 1.66.11 — Multi-vendor Inbound Integrations

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Replaces the WhatsApp-only inbound configuration with independent vendor profiles.
- Lets administrators enable or disable every inbound payload field and mark enabled fields as required or optional.
- Adds vendor-scoped API credentials so a credential cannot be used against another vendor profile.
- Loads default Ticket Types dynamically from master data and adds the active `WHATSAPP` Ticket Type.
- Adds a vendor-authenticated Ticket Type lookup endpoint for external integrations.
- Renames the public inbound fields to `caller_name` and `caller_number`, while migrating existing legacy mappings.
- Updates the Site Settings test console to follow each vendor's enabled fields, required rules, mappings, defaults, and credential scope.
- Corrects the Third-party Integration navigation label.
- Corrects high-volume Ticket-page filtering on SQL Server, including Ticket Number and other combined criteria.

## API

- `POST /api/v1/integrations/inbound/v1/{provider}/requests`
- `GET /api/v1/integrations/inbound/v1/{provider}/clients?search=...`
- `GET /api/v1/integrations/inbound/v1/{provider}/ticket-types`
- `GET /api/v1/integrations/inbound/v1/{provider}/requests/{event_id}`

Disabled fields are ignored. Missing required fields return `REQUIRED_FIELDS_MISSING` with the relevant field names.

## Database

- Alembic head advances to `0191_inbound_vendor_profiles`.
- The migration adds vendor scope to integration API credentials and seeds the WhatsApp Ticket Type when it does not already exist.

## Deployment

Back up the database, deploy to a new versioned directory, run `backend\runtime\SupportHubBackend.exe migrate`, switch IIS paths, then review **Site Settings → Third-party Integration → WhatsApp / Inbound API** before enabling vendor profiles.

## Verification

- Backend Ruff and strict MyPy passed; all 388 backend tests passed.
- Frontend ESLint, all 68 tests, TypeScript, and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- A clean packaged-runtime migration passed through `0191_inbound_vendor_profiles`.
