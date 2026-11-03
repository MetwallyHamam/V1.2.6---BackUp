# SupportHub 1.66.78 - Ticket date and time filters

Release date: 2026-09-27

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Ticket filtering

- Upgrades custom and advanced ticket date filters to date-and-time controls.
- Supports exact time boundaries for created, updated, assigned, resolved, first-occurred and closed timestamps.
- Preserves whole-day behavior for existing presets, URLs and saved views that contain date-only values.
- Treats date/time values without an explicit offset as server-local time (`Africa/Cairo`).
- Prevents invalid access-impact requests using the placeholder capability `unknown` and shows a clear administrator-contact message for unmapped routes.
- Loads the HTTP-LAN UUID compatibility layer at application startup before any lazy page can call `crypto.randomUUID()`.

## Deployment

- Database revision remains `0233_ticket_reports`; no new schema migration is required from `1.66.77`.
- Deploy the packaged frontend and backend together because both the controls and API contract changed.
- Preserve active secrets and environment values when activating `backend/web_1.66.78.config` as `backend/web.config`.

## Verification

- Full automated release validation is executed by the self-contained release builder before packaging.
