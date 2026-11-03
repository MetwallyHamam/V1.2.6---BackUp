# SupportHub 1.63.0 — Support Assistant

Status: **SELF-CONTAINED WINDOWS X64 RELEASE BUILT AND VERIFIED**

## Scope

- Focused Support Assistant queues and compact ticket cards.
- Existing-workflow actions for self-assignment, progress, resolution, comments, contact/WhatsApp, rating/live links, handover, escalation/help, relations, and full ticket access.
- WebSocket refresh, bounded recovery polling, offline/reconnect feedback, compact/expanded mode, and independent-window opening.
- Installable PWA metadata and application-shell service worker; authenticated API responses are never cached.
- Audited, visibility-validated personal pinning through `support_assistant_preferences`.
- English and Arabic/RTL labels.

## Database

- Required Alembic head: `0186_support_assistant_prefs`.
- New table: `support_assistant_preferences`.
- Upgrade is additive; no existing ticket or Pre-Ticket data is rewritten.

## Verification completed

- Clean database migration from base through `0186_support_assistant_prefs` passed.
- Ruff and strict MyPy passed.
- All 379 backend tests passed in the final release pipeline.
- All 25 frontend test files and all 50 tests passed.
- Frontend ESLint, TypeScript compilation, and production Vite build passed.
- PWA manifest parses, the service worker passes JavaScript syntax validation, and both files are present in the production build output.

## Artifact

- Package: `releases/SupportHub-1.63.0.zip` (`43,089,971` bytes; `1,790` entries).
- SHA-256: `520697C1D6FE4DE781B569B645BFF49ACC9D22D2181895EC49F48A530CF35354`.
- Deployment mode: self-contained Windows x64; no Python installation is required.
- Packaged runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Packaged clean migration passed through `0186_support_assistant_prefs`.
- ZIP contains the Support Assistant PWA manifest/service worker and no forbidden development artifacts.

## Before production deployment

- Approve the production Fast Create Ticket Type and P1–P4 Impact/Urgency mapping, or keep Engineer Pre-Ticket disabled.
- Review production profile assignments for all Pre-Ticket and ticket-action permissions.
- Rehearse the upgrade against a restored production SQL Server copy.
- Complete the Pre-Ticket and Support Assistant checklists in `docs/RELEASE_SMOKE_TEST.md` on staging.
- Back up the production database and application files before deployment.
