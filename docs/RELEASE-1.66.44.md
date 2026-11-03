# SupportHub 1.66.44 — Contract and SLA Workspace

Status: **SELF-CONTAINED WINDOWS X64 RELEASE — READY FOR CONTROLLED DEPLOYMENT**

## Enhancements and corrections

- Adds a reusable SLA master-data tab beside contract templates, with target creation, editing, activation, deletion, and publication.
- Lets contracts link reusable SLAs or make a contract-specific copy with product and effective-date targets.
- Publishes matching policy and target snapshots when active SLA settings or targets change, including contract-specific copies.
- Requires a current published SLA with targets when linking contracts or applying contract templates.
- Applies product, service, priority, and effective-date target selection consistently when creating or re-evaluating ticket SLA clocks. Missing or ambiguous targets and inactive linked SLAs return explicit errors.
- Shows shared-policy usage counts and confirms changes affecting linked contracts. Adds a contract coverage preview for P1–P4 targets.
- Adds client working, SLA target, and saved-hour measures to Support Now, the client profile, Executive Dashboard, and Top Management. The chart is available in Dashboard Administration's widget catalog and Top Management's Customize dialog.
- Includes all functionality from `1.66.43`.

## Database

- Database head remains `0206_ticket_flags`; no new schema migration is introduced.
- Run the packaged `seed` command during deployment to ensure the default SLA has a published target snapshot.
- The exact production SLA creation error has not been reproduced without its API response and deployed database state.

## Verification

- Backend Ruff and strict MyPy passed; all 406 backend tests passed.
- Frontend ESLint, all 79 tests, TypeScript compilation, and production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed`, and `recover-admin`.
- Manifest and ZIP integrity checks passed.
