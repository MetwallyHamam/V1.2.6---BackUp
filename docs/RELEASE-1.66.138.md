# Support Hub 1.66.138

Release date: 2026-10-15

## Highlights

- Integrates deployment issues with incident tickets using bidirectional, loop-safe workflow synchronization.
- Adds the explicit Reopened deployment-issue state and preserves resolution and delivery history when an issue recurs.
- Synchronizes resolution text, root causes, services provided, pending ownership, delivery, closure, and reopen details between the linked records.
- Exposes existing ticket flags on linked deployment issues, including governed SLA-pause and resume behavior.
- Adds a visible, default-enabled option to automatically create and link an incident ticket when an internal deployment issue is created.
- Enhances deployment PDF and Word reports with resolution services, multiple root causes, delivery details, and reopen context.

## Database

- Advances the database head to `0266_deployment_ticket_sync`.
- Adds deployment-issue reopen details and normalized root-cause and resolution-service links.
- Enforces one deployment issue per linked ticket.

Run the packaged database migration before starting the application pool.

## Deployment notes

1. Back up the production database and application files.
2. Stop or recycle the Support Hub application pool.
3. Deploy the release files and retain the production environment configuration.
4. Run `SupportHubBackend.exe migrate` from the packaged backend runtime.
5. Start the application pool and perform the packaged smoke test.

