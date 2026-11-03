# SupportHub 1.66.67 — Modern themes and live operations UX

Release date: 2026-09-24

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Appearance and personalization

- Adds Cobalt Sky, Midnight Cyan, Sand & Terracotta, Graphite Lime, and Nordic Blue user themes.
- Retains all existing themes and per-user, server-backed light, dark, and device-mode preferences.
- Applies each palette consistently to headers, navigation, pages, cards, controls, borders, and typography.
- Keeps operational status, priority, warning, success, and error colors semantically recognizable.

## Support Now

- Makes Operations Planner shift and operation cards follow the selected theme colors and font.
- Adds a compact, horizontally scrollable Online Engineers strip to the Live Operations header.
- Uses real presence heartbeats, refreshes every 15 seconds, and distinguishes available engineers from engineers working on tickets.
- Opens the selected engineer's current open-ticket queue from their compact card.

## Ticket grid navigation

- Moves the synchronized horizontal scrollbar to a document-level portal so application-shell scrolling and clipped page ancestors cannot hide it.
- Keeps the scrollbar fixed at the browser viewport bottom whenever the wide ticket grid is visible.
- Preserves bidirectional synchronization with the normal ticket-table scrollbar.

## Deployment

- Database compatibility revision remains `0231_sla_client_dependency_flags`; no new schema migration is introduced.
- Back up the production database and configuration before deployment.
- Deploy the packaged frontend and backend together.
- Preserve production settings when activating `backend/web_1.66.67.config` as `backend/web.config`.
- Run `SupportHubBackend.exe migrate`, run `SupportHubBackend.exe seed`, then recycle the IIS application pool.
- Verify user theme saving, Support Now presence cards and planner colors, and the fixed ticket-grid scrollbar.

## Verification

- The standalone release pipeline runs backend lint, strict type checking, and the complete backend test suite.
- The pipeline also runs frontend lint, all frontend tests, TypeScript compilation, production build, and Windows runtime packaging.
