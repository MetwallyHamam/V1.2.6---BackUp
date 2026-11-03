# SupportHub 1.46.0

Release date: 2026-08-27

Status: self-contained Windows x64 release.

## Highlights

- Prevents unexpected logout during recoverable refresh/network failures, coordinates multi-tab authentication, reports safe reason codes, and adds renewable 30-day inactivity handling.
- Adds unified permission-aware Send Actions for satisfaction, live ticket tracking, and complaint tracking.
- Adds governed access requests with password step-up approval, immutable evidence, expiring overrides, notifications, and access-required UI.
- Adds a scoped Inactive Clients KPI and drilldown across Clients, Tickets, Support Dashboard, and Top Management Dashboard.
- Adds governed Client Portal Training Materials publication with safe public resources, audit logging, and a dedicated permission.
- Consolidates Contract Templates and compact Contract Types inside Contract Workspace, including linked-client counts and paginated drilldown.
- Simplifies Clients-page information/profile navigation and preserves list filters and pagination.
- Corrects mobile multi-select dismissal behavior.

## Completed backlog included

This release packages **B-24**, **B-29–B-32**, **B-34**, **B-35**, **B-37**, and **B-39**, while retaining all capabilities from corrected release `1.45.1`.

## Remaining backlog

- **B-36 — One structured application log file per day**
- **B-38 — Guided Mosaic portal ticket creation**

Full requirements and implementation history are included as `BACKLOG-NOTES.md`; the canonical remaining queue is included as `REMAINING-BACKLOG.md`.

## Database

Required revision: `0142_portal_training`.

Migrations `0139`–`0142` add authentication events, inactivity-session support, governed access requests, and Client Portal Training Material visibility/permission data. Back up and rehearse the production upgrade before changing the IIS application directory.

## Deployment

1. Back up the production database and preserve protected environment values.
2. Extract release `1.46.0` to a new immutable directory.
3. Run `./backend/runtime/SupportHubBackend.exe migrate` and confirm `0142_portal_training`.
4. Run `./backend/runtime/SupportHubBackend.exe seed` and review the new access-request and portal-training permissions.
5. Switch IIS to the new directory, restart the application pool, and complete `SMOKE-TEST.md`.

## Verification

Final artifact size, entry count, SHA-256, and release-gate results are recorded in `RELEASE_STEPS.md` after packaging.
