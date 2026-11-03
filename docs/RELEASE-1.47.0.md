# SupportHub 1.47.0

Release date: 2026-08-27

Status: self-contained Windows x64 release.

## Included changes

- Adds separate Cairo-day JSON error and exception logs while preserving IIS/Uvicorn process-output logs.
- Keeps routine access-token renewal silent and reports connection restoration only after a real transient failure.
- Completes the governed missing-access icon workflow for normal requests and credential-authorized shared-profile grants, including source evidence and impact preview.
- Compacts Contract Workspace customer summaries into a count and short preview with an on-demand searchable, server-paginated dialog.
- Adds six dedicated Project Delivery permissions and minimum-data Project Handover APIs for client lookup/onboarding, caller and client-access creation, engineer lookup, product selection, and safe contract-template application.
- Removes the Project Handover profile's legacy dependency on broad Clients and Internal Operations workspace permissions. Existing credential reveal remains excluded.

## Database

Required revision: `0143_project_delivery`.

Migration `0143_project_delivery` creates the scoped Project Delivery permissions, assigns them to the system Project Handover profile, and removes that profile's legacy `client.view` and `internal_operation.view` assignments.

## Deployment

Back up the database, extract `1.47.0` to a new immutable directory, preserve protected environment values, grant the IIS application-pool identity Modify access to the configured daily error-log directory, run `SupportHubBackend.exe migrate` and `seed`, switch IIS to `1.47.0`, restart the application pool, and complete `SMOKE-TEST.md`.

## Verification

Final artifact metadata, hashes, test counts, and integrity checks are recorded in `RELEASE_STEPS.md`.
