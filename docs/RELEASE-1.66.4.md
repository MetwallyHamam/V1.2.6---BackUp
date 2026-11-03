# SupportHub 1.66.4 — Support Assistant and Dashboard Accuracy

Status: **SELF-CONTAINED WINDOWS X64 RELEASE GENERATED AND VERIFIED**

## Highlights

- Synchronizes new-queue ticket visibility, Queue-tab attention color, and notification sound so one detected arrival triggers the visual and audible alerts together.
- Adds a reduced-motion-aware orange flashing frame for Queue tickets that remain unreceived and unassigned for at least nine minutes.
- Adds the actionable Pre-Tickets queue and count directly to the Tickets page, including immediate count refresh after workflow actions.
- Adds saved, draggable Support Assistant width; Compact, Standard, and Wide presets; true compact-width behavior; RTL resizing; and responsive card columns without changing ticket-card click behavior.
- Replaces the doubled dashboard widget edge with one clean rounded inset accent.
- Aligns SLA breach, Unassigned, online-engineer, Approvals, repeated-issue, date, timezone, and dashboard-scope drill-down filters with the values displayed by their widgets.

## Database

- Required Alembic head: `0188_default_resolution_service`.
- No database migration is added by this release.

## Deployment

1. Back up the current SQL Server database and application directory.
2. Deploy this package to a new versioned directory while preserving production configuration.
3. Run `backend\runtime\SupportHubBackend.exe migrate`.
4. Switch the IIS frontend and backend application paths to the new release.
5. Force-refresh the browser and verify Queue alerts, Support Assistant resizing, Pre-Tickets, and dashboard card drill-down counts.

## Verification

- Backend Ruff, strict MyPy, and the full backend test suite passed.
- Frontend ESLint, the full Vitest suite, TypeScript, and the production Vite build passed.
- PyInstaller produced the bundled Windows backend runtime.
- The bundled executable exposed `serve`, `migrate`, `seed`, and `recover-admin`; a clean packaged migration passed through `0188_default_resolution_service`.
- Manifest version, database head, deployment mode, IIS executable configuration, required frontend/runtime contents, and ZIP readability passed.

Artifact: `releases/SupportHub-1.66.4.zip` (`43,186,581` bytes; `1,792` entries).

SHA-256: `D9BFA64BFB7762511F28972B3778E8CF3D2B9C006464A224A428C764E7845ABD`.
