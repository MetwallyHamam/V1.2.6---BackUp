# Millensys Support Hub 1.66.127

## UAT workspace and cycle management

- Adds Product and Module workspace filters and persistent manual test-case ordering.
- Exposes assigned UAT workspaces in the client portal and supports editing active-cycle dates, engineers, client engineers, coordinators, release details, and ownership.
- Keeps UAT creation in one form with multiple templates, automatic name/code generation, and the product inherited from each template.

## Multi-vendor inbound integrations

- Expands third-party integrations to support multiple vendors and source systems.
- Adds per-vendor API Key or HTTP Basic authentication with securely hashed passwords.
- Supports direct-ticket and pre-ticket intake modes plus a status endpoint for monitoring tools to synchronize ticket lifecycle and resolution details.

## Deployment live tracking and follow-up

- Adds a simple deployment plan linked to a client and optionally to an approved UAT cycle.
- Provides ordered activities, owners, planned windows, live status, comments, actual time, and client-portal tracking.
- Adds deployment issues with status, priority, implementation phase, owner, next action, resolution, and automatic incident-ticket creation.
- Adds live summaries for planned versus actual effort, issue totals, pending phases, closure, follow-up, and next actions.
- Adds branded PDF and Word reports whose filenames include the client name and planned deployment date.

## Database and deployment

- Database compatibility advances to `0259_deployment_follow_up` and includes migrations `0256` through `0259`.
- Back up production, quiesce IIS, run the packaged `migrate` command, deploy frontend and backend together, apply `web_1.66.127.config` as appropriate, and recycle the application pool.
- Verify internal and client-portal UAT access, an authenticated vendor ticket round trip, deployment live tracking, automatic issue ticket creation, and both report formats after deployment.

## Verification

- Ruff and strict MyPy passed across 202 backend source files.
- All 543 backend tests passed.
- Frontend ESLint, all 121 tests across 46 files, TypeScript compilation, and the production build passed.
- The release manifest records database head `0259_deployment_follow_up`.
- The self-contained Windows x64 runtime starts successfully and completed clean and repeat migrations through the database head.
