# SupportHub 1.66.6 — Resolution and Escalation Workflow Refinement

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Compresses the resolution dialog's optional knowledge, close-after-resolve, saved-default, and attachment controls while retaining guidance in tooltips.
- Highlights inactive clients in red in Ticket and Pre-Ticket creation and prevents accidental selection of inactive or ticket-restricted clients.
- Adds bidirectional escalation closure: closing the final escalation child closes its main ticket, while closure by the main ticket's dedicated engineer closes all directly linked active escalation children.
- Preserves atomic workflow updates, readiness validation, status history, audit evidence, SLA completion, pending-handover completion, notifications, and satisfaction processing across escalation closure.
- Copies the validated main-ticket resolution evidence to unresolved escalation children closed by the parent workflow.

## Database

- Required Alembic head: `0188_default_resolution_service`.
- No database migration is added by this release.

## Deployment

1. Back up the current SQL Server database and application directory.
2. Deploy this package to a new versioned directory while preserving production configuration.
3. Run `backend\runtime\SupportHubBackend.exe migrate`.
4. Switch the IIS frontend and backend application paths to the new release.
5. Force-refresh the browser and verify resolution-dialog density, inactive-client options, and both escalation closure directions.

## Verification

- Backend Ruff, strict MyPy, and all 384 backend tests passed.
- Frontend ESLint, all 68 frontend tests, TypeScript, and the production Vite build passed.
- PyInstaller produced the bundled Windows backend runtime.
- The bundled executable exposed `serve`, `migrate`, `seed`, and `recover-admin`; a clean packaged migration passed through `0188_default_resolution_service`.
- Manifest version, database head, deployment mode, IIS executable configuration, required frontend/runtime contents, and ZIP readability passed.

Artifact: `releases/SupportHub-1.66.6.zip` (`43,113,588` bytes; `1,792` entries).

SHA-256: `A45448984927C3F8AA378DE26F5F78A43D1E4B5C28A786B5922602442CDFEF48`.
