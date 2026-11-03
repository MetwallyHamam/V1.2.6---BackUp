# SupportHub 1.66.75 - Report discovery and organization hierarchy

Release date: 2026-09-27

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Reports Center

- Reorganizes the report catalog into visible categories with report counts and catalog search.
- Replaces identifier and free-text filtering with searchable, permission-aware lookup controls for clients, users, products, modules, environments, services, categories, subcategories, teams, contracts, ticket types and ticket statuses.
- Adds dependent Product to Module, Category to Subcategory and Client to Contract filtering, including automatic clearing of incompatible child selections.
- Supports lookup metadata in new report definitions while upgrading conventional filters in existing definitions without a data migration.
- Includes the optional expanded Reports Center catalog SQL utility, including the one-row-per-ticket turnaround report.

## Organization hierarchy

- Preserves the Support Now hierarchy card design while adding responsive Chart and Outline views.
- Adds hierarchy search, ancestor expansion, match highlighting, node expansion, descendant counts, zoom, fit-to-screen, drag-to-pan and full-screen viewing.
- Contains horizontal overflow inside the chart canvas and uses a mobile-friendly vertical outline to avoid page-level horizontal scrolling.
- Uses the same hierarchy viewer in Support Now administration and Onboarding while retaining their existing data sources and administration behavior.

## Included corrections

- Retains the enhanced ticket and incident reporting experience, external-AI preparation prompt, ticket-event timeline support and responsive shared reports from the preceding report release.
- Retains corrected Send Action client-contact validation, Support Now calendar date handling and Assistant tab context-menu behavior.

## Deployment

- Database revision remains `0233_ticket_reports`; no new schema migration is required from `1.66.74`.
- The optional `database/SupportHub-Reports-Catalog-Expansion.sql` script adds or updates the expanded report catalog and should be reviewed before execution in production.
- Back up the production database, uploaded files and configuration before deployment.
- Deploy the packaged frontend and backend together and preserve production settings when activating `backend/web_1.66.75.config` as `backend/web.config`.

## Verification

- Backend Ruff and strict MyPy passed; all 454 backend tests passed.
- Frontend ESLint, all 87 Vitest tests, TypeScript compilation and the production build passed.
- The packaged executable exposes `serve`, `migrate`, `seed` and `recover-admin`.
- Manifest version `1.66.75`, database head `0233_ticket_reports`, report-catalog SQL inclusion, ZIP readability and forbidden-file inspection passed.
