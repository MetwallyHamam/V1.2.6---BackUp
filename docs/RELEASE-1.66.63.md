# SupportHub 1.66.63 — Operations Planner usability fixes

Release date: 2026-09-24

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Operations Planner improvements

- Shows assigned engineer names directly on operation cards, with a clear unassigned state.
- Opens operation details when an operation card is double-clicked or activated from the keyboard.
- Prevents operation-card double-clicks from opening the calendar creation actions.
- Refreshes the visible planner automatically after creating an operation or applying shifts.

## Deployment

- Database migration advances to `0230_dynamic_reports_center`, including coordinated per-user theme presets and the dynamic reports center schema.
- Back up the production database before deployment.
- Deploy the packaged frontend and backend together.
- Preserve production settings when activating `backend/web_1.66.63.config` as `backend/web.config`.
- Run `SupportHubBackend.exe migrate`, run `SupportHubBackend.exe seed`, then recycle the IIS application pool.
- Verify engineer names, operation-card details, and automatic planner refresh after creating shifts and operations.

## Verification

- The standard standalone release pipeline runs backend lint, strict type checking, and tests.
- The pipeline also runs frontend lint, tests, TypeScript compilation, production build, and Windows runtime packaging.
