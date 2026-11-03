# SupportHub 1.66.109

## Purpose

Package the current validated SupportHub source as a new immutable,
self-contained Windows x64 release, superseding `1.66.108` for deployment.

## Changes

- Includes the capacity hardening and service-checklist workspace refinements
  delivered in `1.66.108`.
- Refreshes the deployable frontend, backend, operational scripts,
  documentation, and bundled Windows backend runtime from the current source.
- Database compatibility remains at `0244_checklist_default_template`; no new
  database migration is required from `1.66.108`.

## Deployment

Deploy the packaged frontend and backend together into a new versioned release
directory. Copy protected production environment values into the packaged
backend configuration template and confirm `APP_VERSION=1.66.109` before the
IIS switch.

The standalone release builder validates backend lint, strict typing and tests,
frontend lint and tests, TypeScript compilation, the production frontend build,
and the self-contained Windows runtime before producing the archive.
