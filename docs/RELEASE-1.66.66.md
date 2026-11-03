# SupportHub 1.66.66 — Ticket search and grid navigation

Release date: 2026-09-24

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Ticket queue improvements

- Extends the Tickets page general search to match client names and client codes as well as ticket numbers and subjects.
- Keeps client searching server-side so visibility rules, result totals, sorting, and pagination remain authoritative.
- Adds a synchronized horizontal scrollbar at the bottom of the browser viewport while wide ticket columns extend below the visible area.
- Retains the normal table scrollbar when the bottom of the ticket grid is visible.
- Preserves sticky headers, resized columns, RTL layout, paging, and grid/card switching.

## Deployment

- Database compatibility revision remains `0231_sla_client_dependency_flags`; no new schema migration is introduced by this release.
- Back up the production database and configuration before deployment.
- Deploy the packaged frontend and backend together.
- Preserve production settings when activating `backend/web_1.66.66.config` as `backend/web.config`.
- Run `SupportHubBackend.exe migrate`, run `SupportHubBackend.exe seed`, then recycle the IIS application pool.
- Verify ticket searches using a partial client name and client code, then verify horizontal navigation with a wide column selection.

## Verification

- The standalone release pipeline runs backend lint, strict type checking, and the complete backend test suite.
- The pipeline also runs frontend lint, all frontend tests, TypeScript compilation, production build, and Windows runtime packaging.
