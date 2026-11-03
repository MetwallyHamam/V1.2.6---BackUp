# SupportHub 1.47.1

Release date: 2026-08-28

Status: corrected self-contained Windows x64 release; supersedes 1.47.0.

## Included changes

- Retains the daily Cairo-day exception logging, silent routine token renewal, governed missing-access workflow, compact Contract Workspace, and scoped Project Delivery workflow shipped in 1.47.0.
- Corrects Project Handover isolation for renamed profiles and legacy direct user overrides. Migration `0144_handover_cleanup` restores the complete dedicated permission baseline and removes broad Client, Contract, and Operations grants originating from the Project Handover role.
- Adds exact frontend route guards so Contract and Operations workspaces remain hidden and inaccessible without their independent workspace permissions.
- Shows profile-derived permission sources, effective permissions, and direct ALLOW/DENY override history on Edit User for administrators with `profile.manage`.
- Implements B-42 responsive containment, scrollable data regions and tabs, touch-friendly controls, mobile dialogs, and targeted fixes across Tickets, Saved Views, Complaints, Knowledge Base, Profile Privileges, Master Data, and Data Imports.
- Implements B-43 by consolidating Client Portal training into Knowledge Base → Training Materials, preserving the existing portal-publication flag and secured feed, removing duplicate navigation, and redirecting the legacy URL.

## Database

Required revision: `0144_handover_cleanup`.

Migration `0144_handover_cleanup` is a corrective authorization migration. It recognizes canonical and renamed Project Handover profiles, assigns the eight dedicated `project_handover.*` permissions, removes broad profile permissions, and removes active broad `ALLOW` overrides for users assigned those profiles. Independently assigned permissions from other active profiles remain effective.

## Deployment

Do not deploy 1.47.0. Back up the database, extract 1.47.1 to a new immutable directory, preserve protected environment values, grant the IIS application-pool identity Modify access to the configured daily error-log directory, run `SupportHubBackend.exe migrate` and `seed`, switch IIS to 1.47.1, restart the application pool, and complete `SMOKE-TEST.md`.

## Verification

Ruff and strict MyPy passed across 149 source files; all 306 backend tests passed. Frontend ESLint, all 29 tests, TypeScript, and the production build passed. A clean packaged-runtime migration reached `0144_handover_cleanup`; runtime commands, manifest/version/head consistency, required contents, ZIP integrity, and forbidden-file checks passed. Artifact metadata and SHA-256 are recorded in `RELEASE_STEPS.md`.
