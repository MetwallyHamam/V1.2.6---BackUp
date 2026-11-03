# SupportHub 1.66.107

## Purpose

Deliver the login-orbit visual refinement as a new immutable self-contained
Windows x64 release, superseding `1.66.106` for deployment.

## Changes

- Reduces the desktop login orbit footprint so the decoration remains compact.
- Animates both orbit rings independently instead of leaving the outer orbit
  stationary.
- Uses opposing clockwise and counter-clockwise motion to keep both rings
  visually distinct.
- Honors the user's reduced-motion preference for both animations.
- Makes the mobile login safely scrollable instead of clipping content on short
  screens, including compact spacing for low-height devices.
- Respects phone safe-area insets and keeps the sign-in card centered across
  supported mobile widths.
- Adds governed default service-checklist template selection while preserving
  published-template immutability.
- Preserves authentication, session, return-path, localization, and responsive
  login behavior.
- Advances the database head to `0244_checklist_default_template`.

## Deployment

Deploy the packaged frontend and backend together into a new versioned release
directory. Copy protected production environment values into the packaged
backend configuration template and confirm `APP_VERSION=1.66.107` before the
IIS switch.

The standard release builder validates backend lint, strict typing and tests,
frontend lint and tests, TypeScript compilation, the production frontend build,
and the self-contained Windows runtime before producing the archive.
