# Dashboard Drill-through Accuracy

Last updated: 2026-08-30

## Objective

Every clickable dashboard card or chart segment must open the same population used to calculate its displayed value, including the selected period, date basis, dashboard scope, and master-data filters.

## Audit status

| Dashboard | Status | Result |
| --- | --- | --- |
| Executive / employee dashboard | Completed | KPI cards and status/priority charts now retain period, creation/resolution/assignment basis, dashboard scope, and master-data filters. Today cards now use bounded From/To dates. |
| Top Management dashboard | Completed | Ticket drilldowns now use ticket-queue date parameters. Country, zone, location, team, and engineer filters are supported by the queue. Status, priority, product, workload, and country chart segments add their own category filter. |
| Client Profile dashboard | Completed | Metric, priority, status, product, module, service, trend, impact, and evidence links are server-generated with client and reporting-period filters. |
| Client Portal dashboard | Completed | Request, incident, closed, pending, SLA, saved-hours, and working-hours cards retain the portal reporting period and use governed portal views. |
| Manager contract overview | Completed | Active, inactive, expiry-window, and missing-renewal cards map to supported contract filters. |
| Financial analytics dashboard | Completed | Current analytics are not ticket drillthrough controls; there was no misleading ticket redirect to correct. |
| Inactive clients KPI | Completed | Opens the client list with the inactive master-status filter. |

## Validation

- Backend Ruff: passed.
- Backend strict MyPy for changed modules: passed.
- Dashboard, Top Management, and ticket test suites: passed (42 tests).
- Frontend TypeScript: passed.
- Frontend ESLint: passed.
- Frontend tests: 42/42 passed across 21 files.

## Release state

Packaged and verified in SupportHub `1.51.1`: `releases/SupportHub-1.51.1.zip`.
