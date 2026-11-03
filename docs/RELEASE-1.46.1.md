# SupportHub 1.46.1

Release date: 2026-08-27

Status: corrected self-contained Windows x64 release.

## Access-request correction

- Replaces dead-end permission warnings from API actions with an automatic **Access required** dialog.
- Identifies the exact missing permission at the shared backend authorization boundary.
- Allows users to submit a narrowly bound `action:<permission>` request with a business justification.
- Retains the existing pending-request detection, approval notifications, permission refresh, audit evidence, and return path.
- Keeps high-risk permissions restricted to Profiles & Privileges.

This release supersedes `1.46.0` for deployment and retains every feature listed in its release notes.

## Database

Required revision remains `0142_portal_training`; no new migration is required.

## Deployment

Back up the database, extract `1.46.1` to a new immutable directory, preserve protected environment values, run `SupportHubBackend.exe migrate` and `seed`, switch IIS to `1.46.1`, restart the application pool, and complete `SMOKE-TEST.md`.

## Verification

Final artifact metadata and gate results are recorded in `RELEASE_STEPS.md`.
