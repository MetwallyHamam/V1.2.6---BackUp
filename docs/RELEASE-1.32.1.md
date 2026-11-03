# SupportHub 1.32.1

Corrective release completing Onboarding administration and making contract financial configuration discoverable.

## Changes

- Keeps the Financials tab visible near the start of every contract workspace instead of silently hiding it.
- Shows an explicit `finance.view` permission explanation when financial access is not effective.
- Adds Onboarding Administration for material categories, training topics, unlimited external resources, reusable checklist templates with ordered items, and employee plan assignment.
- Creates personal onboarding plans as snapshots so later template changes do not alter an employee's active checklist.
- Adds API validation and regression coverage for the complete category → material → resource → template → assignment workflow.

No new database migration is required beyond `0121_employee_onboarding` from release 1.32.0.

## Deployment requirements

- Deploy both the `frontend` and `backend` folders from this release. Do not mix frontend assets from 1.31.5 or 1.32.0 with this backend.
- Transfer protected production values into the packaged `backend/web.config`; do not restore the complete old configuration.
- Run `SupportHubBackend.exe migrate` and `SupportHubBackend.exe seed`. Both commands are safe and idempotent when upgrading from 1.32.0.
- Sign out, clear stale site cache if necessary, and sign in again so effective permissions refresh.
- Verify Contract Workspace → Financials and Onboarding → Administration.
