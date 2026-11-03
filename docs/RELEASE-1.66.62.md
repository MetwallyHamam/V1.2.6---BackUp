# SupportHub 1.66.62 — Bulk SLA setup and settings organization

Release date: 2026-09-24

Status: **READY FOR CONTROLLED DEPLOYMENT**

## SLA and contract improvements

- Adds bulk SLA target creation from products, modules, and services already assigned to contract coverage.
- Allows multiple contract coverage scopes and multiple priorities to be configured in one operation.
- Creates or updates matching SLA targets while preserving individual target editing.
- Adds a dedicated **SLA & Contract Policy** Site Settings category using the existing timer and warning settings.
- Removes duplicate SLA controls from General settings without creating new database values.
- Organizes Contract Types, Contract Templates, and SLA Templates as dedicated Contract Management tabs.

## Deployment

- Database migration remains `0227_contract_ticket_policy`; this release adds no migration after `1.66.61`.
- Back up the production database before deployment.
- Deploy the packaged frontend and backend together.
- Preserve production settings when activating `backend/web_1.66.62.config` as `backend/web.config`.
- Run `SupportHubBackend.exe migrate`, run `SupportHubBackend.exe seed`, then recycle the IIS application pool.
- Verify SLA operational settings, Contract Management navigation, and bulk SLA target creation after deployment.

## Verification

- Backend lint, type checking, contract policy tests, and the bulk SLA regression test passed before packaging.
- Frontend ESLint, TypeScript compilation, and all 86 Vitest tests passed before packaging.
