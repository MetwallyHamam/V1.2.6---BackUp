# SupportHub 1.66.64 — Support Now planner details

Release date: 2026-09-24

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Support Now Operations Planner

- Shows assigned engineers directly on internal-operation cards.
- Shows client code and name on client-related operations and outdoor visits.
- Displays the current operation status and excludes rejected operations from the calendar.
- Opens operation details in place when a card is double-clicked or activated from the keyboard.
- Prevents operation-card double-clicks from opening calendar creation actions.
- Refreshes Support Now planner data immediately after creating operations or applying shifts.

## Deployment

- Database migration remains `0230_dynamic_reports_center`; this release adds no migration after `1.66.63`.
- Back up the production database before deployment.
- Deploy the packaged frontend and backend together.
- Preserve production settings when activating `backend/web_1.66.64.config` as `backend/web.config`.
- Run `SupportHubBackend.exe migrate`, run `SupportHubBackend.exe seed`, then recycle the IIS application pool.
- Verify engineer names, client identity, rejected-operation filtering, card details, and automatic refresh in Support Now.

## Verification

- The standard standalone release pipeline runs backend lint, strict type checking, and tests.
- The pipeline also runs frontend lint, tests, TypeScript compilation, production build, and Windows runtime packaging.
