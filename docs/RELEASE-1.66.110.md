# SupportHub 1.66.110

## Purpose

Restore the animated orbit decoration on the desktop login page and package the
correction as a new immutable self-contained Windows x64 release, superseding
`1.66.109` for deployment.

## Changes

- Corrects the login orbit container stacking order so browser rendering does
  not place the animated rings behind the full-page background.
- Adds regression coverage that verifies the orbit decoration uses a visible
  stacking level.
- Database compatibility remains at `0244_checklist_default_template`; no new
  database migration is required from `1.66.109`.

## Deployment

Deploy the packaged frontend and backend together into a new versioned release
directory. Copy protected production environment values into the packaged
backend configuration template and confirm `APP_VERSION=1.66.110` before the
IIS switch. After deployment, force-refresh the login page so the browser loads
the newly fingerprinted frontend assets.
