# SupportHub 1.66.108

## Purpose

Deliver the latest capacity hardening and service-checklist workspace refinement
as a new immutable self-contained Windows x64 release, superseding `1.66.107`
for deployment.

## Changes

- Runs two backend processes per IIS application for improved request capacity
  and availability during worker recycling.
- Recycles packaged backend workers after a bounded, jittered request count so
  allocator-retained memory is periodically returned to Windows without
  synchronized worker restarts.
- Adds bounded configuration defaults and deployment environment settings for
  worker request limits.
- Adds automated coverage for the production pool, worker, and IIS capacity
  configuration.
- Includes the latest service-checklist workspace refinement.
- Database compatibility remains at `0244_checklist_default_template`.

## Deployment

Deploy the packaged frontend and backend together into a new versioned release
directory. Copy protected production environment values into the packaged
backend configuration template and confirm `APP_VERSION=1.66.108` before the
IIS switch.

The standard release builder validates backend lint, strict typing and tests,
frontend lint and tests, TypeScript compilation, the production frontend build,
and the self-contained Windows runtime before producing the archive.
