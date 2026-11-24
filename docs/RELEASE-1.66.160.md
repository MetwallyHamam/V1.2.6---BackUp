# SupportHub 1.66.160

Release date: 2026-11-03

## Highlights

- Adds My Workspace as a personal, server-saved area for favorites, recent pages, saved ticket views, Support Assistant tabs, pinned tickets, shifts, visits, assigned operations, approvals, and upcoming work.
- Keeps Support Now (`/home`) and Support Assistant (`/support-workspace`) as separate products with their existing operational-dashboard and personal-assistant responsibilities.
- Reorganizes employee navigation into clearer My Work, Service Management, Customers, Operations, Knowledge, Analytics, and administration-oriented areas without changing the approved Top Management dashboard.
- Adds a permission-scoped unified attention center for critical and due tickets, upcoming shifts and visits, assigned operations, approvals, and important notifications.
- Adds per-user attention categories, one-hour snoozing, and restoration of snoozed work.
- Improves Notifications with urgency groups, responsive filters, selection, bulk read actions, safe dismissal, and open-and-read behavior.
- Improves Tickets on mobile with responsive cards, sticky bulk controls, visible active filters, and a persistent create action while retaining the configurable desktop table.
- Improves Saved Views with search, scope filtering, responsive cards, duplication as a personal copy, default-state clarity, and direct My Workspace favorites.
- Adds governed Work Assignments for one or many engineers, department claiming, multiple-client work, lifecycle tracking, conversion links, live status sharing, and weighted Engineer KPI contribution without duplicate credit.

## Database

- Advances the database revision to `0277_work_assignments`.
- Migration `0275_personal_workspace` adds personal favorites, recent-page history, and workspace settings to Support Assistant preferences.
- Migration `0276_notification_dismissal` adds recoverable notification dismissal state.
- Migration `0277_work_assignments` adds assignments, multiple assignees and clients, conversion links, audit events, secure live-share tokens, and assignment permissions.
- Back up the production database and run the packaged migration command before starting the upgraded application.

## Validation

- Support Assistant remains unchanged and its focused regression suite verifies its original personal-assistant/PWA behavior.
- Notification dismissal and unified-attention preference APIs enforce signed-in-user ownership and existing permission scopes.
- Full backend, frontend, migration, packaging, and archive verification results are recorded in `RELEASE_STEPS.md`.

## Deployment

Back up the database, stop or quiesce the IIS application, deploy the full package, run the packaged database migration command, apply the versioned backend configuration deliberately, and recycle the application pool once. Hard-refresh open browser sessions after deployment.

Smoke-test Support Now and Support Assistant as separate routes, My Workspace persistence, notification read/dismiss actions, attention snoozing, Saved View favorites, and Tickets on desktop and mobile.
