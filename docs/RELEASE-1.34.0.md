# SupportHub 1.34.0

Onboarding content administration and operation scheduling enhancement release.

## Onboarding administration

- Adds edit controls for training-material categories, training materials, material resources/content, and checklist templates.
- Adds safe deletion for categories, materials, and checklist templates by deactivating referenced records so employee onboarding snapshots remain intact.
- Allows material resources to be edited or removed directly from the selected training material.

## Operation scheduling

- Adds From Date and To Date scheduling to operation templates.
- Synchronizes the date range with week 1–4 and weekday selectors.
- Applies all selected range, week, and weekday filters when generating operations.
- Adds `Outdoor / field visit` to operation-template creation.
- Requires a client for outdoor templates and creates governed client-visit occurrences after validating the applicable visit entitlement.

## Database and verification

- Database compatibility remains at revision `0122_operations_permissions`; no new migration is required.
- Backend Ruff, strict MyPy, and all 259 tests passed.
- Frontend ESLint, all 9 tests, TypeScript, and the production Vite build passed.
