# SupportHub 1.66.1 — Dashboard Card Alignment and SLA Alerts

Status: **SELF-CONTAINED RELEASE GENERATED**

## Highlights

- Aligns Executive and Top Management dashboard KPI cards and visual widgets with the modern Support Assistant ticket-card treatment: coloured leading rail, refined gradient surface, depth, and clear interactive hover state.
- Adds a modern red SLA alert frame to Support Assistant tickets that are at risk of a resolution-SLA breach or are already overrun.
- Respects the operating-system reduced-motion preference: SLA alerts remain clearly framed without continuous animation.

## Database

- Required Alembic head: `0188_default_resolution_service`.
- No database migration is added by this release.

## Deployment

1. Back up the SQL Server database and current application directory.
2. Deploy this package to a new versioned directory while preserving production configuration.
3. Run `backend\runtime\SupportHubBackend.exe migrate`.
4. Open the Executive and Top Management dashboards and verify that cards retain their metric and drill-through behaviour.
5. Open Support Assistant with an `AT_RISK` ticket and confirm its red SLA alert frame is visible; verify the animation does not run when reduced motion is enabled.

## Verification

- The release packager completed backend Ruff, strict MyPy, pytest, frontend ESLint, Vitest, TypeScript, and a production Vite build.
- Package contents, manifest metadata, frontend entry point, backend IIS configuration, and archive readability were verified.

Artifact: `releases/SupportHub-1.66.1.zip` (`2,093,573` bytes; `514` entries).

SHA-256: `A2823D1141FBED79FAA737C86C5C246A96EDF2806554121EF60493F0D05C46CA`.
