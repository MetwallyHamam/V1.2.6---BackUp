# SupportHub 1.66.79 - Ticket date/time filters and LAN hardening

Release date: 2026-09-27

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Included changes

- Adds exact date-and-time ticket filters for created, updated, assigned, resolved, first-occurred and closed timestamps.
- Preserves whole-day behavior for existing date-only presets, URLs and saved views.
- Prevents access-impact calls using the invalid placeholder capability `unknown` and explains unmapped routes clearly.
- Loads the HTTP-LAN UUID compatibility layer at application startup before lazy page code.
- Includes the complete `1.66.78` validated source plus a self-contained Windows x64 backend runtime.

## Deployment

- Database revision remains `0233_ticket_reports`; no schema migration is required from `1.66.77`.
- Deploy the packaged frontend and backend together.
- Preserve active secrets and environment values when activating `backend/web_1.66.79.config` as `backend/web.config`.
- PWA installation still requires an HTTPS URL opened directly in Chrome or Edge; embedded Assistant webviews and plain LAN HTTP do not expose the browser install prompt.

## Verification

- Full automated release validation and packaged-runtime checks are executed by the self-contained release builder before packaging.
