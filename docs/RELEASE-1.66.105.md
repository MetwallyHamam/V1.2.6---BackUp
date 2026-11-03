# SupportHub 1.66.105

## Purpose

Deliver the presentation-aligned SupportHub login experience as a new immutable
self-contained Windows x64 release.

## Changes

- Replaces the photographic login background with the SupportHub executive
  visual language: deep navy, teal highlights, soft radial light, and circular
  orbit motion.
- Removes the square/grid background treatment.
- Adds the Millensys Support Hub brand lockup and the "Service operations,
  unified." platform proposition.
- Preserves the existing authentication, return-path, session-expiry, password
  reset, validation, and localization behavior.
- Adds a responsive mobile composition with a compact brand header, touch-sized
  sign-in action, and the platform proposition displayed below the form.
- Retains the current database head `0243_contract_email_subject`; this release
  requires no new database migration.

## Deployment

Deploy the packaged frontend and backend together into a new versioned release
directory. Copy protected production environment values into the packaged
backend configuration template and confirm `APP_VERSION=1.66.105` before the
IIS switch.

The standard release builder validates backend lint, strict typing and tests,
frontend lint and tests, TypeScript compilation, the production frontend build,
and the self-contained Windows runtime before producing the archive.
