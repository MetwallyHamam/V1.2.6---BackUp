# SupportHub 1.66.106

## Purpose

Deliver the bilingual login-layout hotfix as a new immutable self-contained
Windows x64 release, superseding `1.66.105` for deployment.

## Changes

- Corrects the login composition for English left-to-right and Arabic
  right-to-left presentation.
- Mirrors the desktop hero, sign-in panel, alignment, and orbit decoration by
  active language direction.
- Localizes the hero statement, platform description, supporting tags, and
  secure-workspace label in English and Arabic.
- Keeps username and password entry left-to-right inside the Arabic form for
  predictable credential input.
- Adds safe vertical scrolling for short displays so form and footer content
  cannot be clipped.
- Uses a modern display-font stack for the "Service operations, unified."
  statement, with appropriate English and Arabic fallbacks.
- Preserves authentication, session, return-path, and password-reset behavior.
- Retains database head `0243_contract_email_subject`; no migration is added.

## Deployment

Deploy the packaged frontend and backend together into a new versioned release
directory. Copy protected production environment values into the packaged
backend configuration template and confirm `APP_VERSION=1.66.106` before the
IIS switch.

The standard release builder validates backend lint, strict typing and tests,
frontend lint and tests, TypeScript compilation, the production frontend build,
and the self-contained Windows runtime before producing the archive.
