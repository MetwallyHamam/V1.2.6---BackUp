# SupportHub 1.66.111

## Purpose

Restore visible ambient motion across the login-page background and package the
correction as a new immutable self-contained Windows x64 release, superseding
`1.66.110` for deployment.

## Changes

- Animates the login background grid with a slow continuous drift.
- Adds independently floating teal and pulsing blue ambient glow layers.
- Retains the corrected visible stacking order for both orbit rings.
- Honors the operating system's reduced-motion preference by presenting the
  same visual layers without movement.
- Adds regression coverage for the login background animation contract.
- Database compatibility remains at `0244_checklist_default_template`; no new
  database migration is required from `1.66.110`.

## Deployment

Deploy the packaged frontend and backend together into a new versioned release
directory. Copy protected production environment values into the packaged
backend configuration template and confirm `APP_VERSION=1.66.111` before the
IIS switch. Force-refresh the login page after deployment to load the newly
fingerprinted frontend assets.
