# SupportHub 1.66.8 — Support Assistant, Dashboard Accuracy, and Inactive-Client Approval

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Includes the Support Assistant Backlog, Site Settings, manual-only Follow-up behavior, configurable sorting, refresh intervals, warning threshold, Mine statuses, and user overrides.
- Aligns main and Top Management dashboard values with their exact drill-down/evidence populations.
- Restores selection of inactive or ticket-restricted clients in Ticket creation while keeping them visibly highlighted in red.
- Preserves the explicit warning and confirmation flow; confirmed requests are created unassigned as `PENDING_APPROVAL`, without contract or SLA activation until approval.

## Database

- Required Alembic head: `0189_support_assistant_backlog`.
- Migration `0189_support_assistant_backlog` adds the permission-controlled Assistant Backlog.

## Deployment

1. Back up the SQL Server database and current application directory.
2. Deploy this package to a new versioned directory while preserving production configuration.
3. Run `backend\runtime\SupportHubBackend.exe migrate`.
4. Switch the IIS frontend and backend paths to the new release.
5. Force-refresh the browser and verify inactive-client confirmation, Assistant Backlog, and dashboard drill-down totals.

## Verification

- Backend Ruff, strict MyPy, and all 385 backend tests passed.
- Frontend ESLint, all 68 frontend tests, TypeScript, and the production Vite build passed.
- The bundled executable exposes `serve`, `migrate`, `seed`, and `recover-admin`; a clean packaged migration passed through `0189_support_assistant_backlog`.
