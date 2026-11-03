# Millensys Support Hub 1.66.128

## SQL Server migration correction

- Corrects migration `0257_integration_basic_auth` for existing integration API clients whose new Basic-auth username is empty.
- Creates the username uniqueness rule as a SQL Server filtered unique index with `api_username IS NOT NULL`.
- Preserves uniqueness for configured usernames while allowing multiple existing API-key vendors to retain a null username.
- Adds regression coverage for the SQL Server-specific index predicate.

## Included functionality

- Includes the complete UAT workspace, multi-vendor integration, deployment live tracking, follow-up, ticket automation, and branded PDF/Word reporting functionality from `1.66.127`.
- Database compatibility remains `0259_deployment_follow_up`.

## Deployment

Use this release instead of `1.66.127`. Back up production, deploy frontend and backend together, then run `backend\runtime\SupportHubBackend.exe migrate`. A database left at revision `0256_uat_test_display_order` by the failed attempt can be migrated directly; no manual deletion or username update is required.

## Verification

The standalone release pipeline runs backend lint, strict typing, all backend tests, frontend lint/tests/type-check/build, Windows x64 runtime packaging, packaged-runtime startup, migration validation, manifest checks, and archive inspection.
