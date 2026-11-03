# SupportHub 1.66.112

## Purpose

Restore continuous, clearly visible motion to both login-page orbit rings while
keeping the central SH mark stable and readable. This immutable self-contained
Windows x64 release supersedes `1.66.111` for deployment.

## Changes

- Gives the outer orbit an explicit clockwise rotation and the inner orbit an
  independent, faster counter-clockwise rotation.
- Keeps the SH tile outside the rotating layers so the logo never rotates or
  wraps with either orbit.
- Preserves the established SupportHub colors, ambient background motion,
  responsive layout, and authentication behavior.
- Retains database compatibility at `0244_checklist_default_template`; no new
  database migration is required from `1.66.111`.

## Deployment

Deploy the packaged frontend and backend together into a new versioned release
directory. Copy protected production environment values into the packaged
backend configuration template and confirm `APP_VERSION=1.66.112` before the
IIS switch. Force-refresh the login page after deployment to load the newly
fingerprinted frontend assets.
