# SupportHub 1.66.40 — Assistant Preference Recovery

Status: **SELF-CONTAINED WINDOWS X64 RELEASE — READY FOR CONTROLLED DEPLOYMENT**

## Corrections

- Allows Support Assistant default-tab and workspace preferences to save when an old pinned ticket was deleted.
- Automatically removes stale missing-ticket pin IDs while preserving valid accessible pinned tickets.
- Replaces the extended Quick Actions button with a compact circular `+` trigger; the click-open labeled and colored action menu remains unchanged.
- Includes all functionality from `1.66.39`.

## Database

- Database head remains `0206_ticket_flags`; no additional migration is introduced.

## Verification

- Backend Ruff and strict MyPy passed; all 402 backend tests passed.
- Frontend ESLint, all 31 test files and 79 tests, TypeScript compilation, and production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest version/database revision and ZIP readability checks passed.
