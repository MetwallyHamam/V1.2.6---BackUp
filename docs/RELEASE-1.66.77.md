# SupportHub 1.66.77 - Millensys brand theme

Release date: 2026-09-27

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Millensys brand experience

- Adds a dedicated Millensys Brand color theme based on the corporate Daintree, Blue Chill and Jordy Blue palette.
- Provides coordinated light and dark variants suitable for dense support, CRM, reporting and administration screens.
- Retains all LAN staging compatibility, Support Assistant scrolling, saved-view preference correction and modern theme presets introduced in `1.66.76`.

## Deployment

- Database revision remains `0233_ticket_reports`; no new schema migration is required from `1.66.76`.
- Deploy the packaged frontend and backend together because the Millensys theme identifier is validated by the backend.
- Preserve active secrets and environment values when activating `backend/web_1.66.77.config` as `backend/web.config`.

## Verification

- Full automated release validation is executed by the self-contained release builder before packaging.

