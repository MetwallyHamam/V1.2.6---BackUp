# Millensys Support Hub 1.66.98

## Presence heartbeat concurrency hotfix

- Changes the presence heartbeat to an atomic timestamp update, preventing conflicts when multiple tabs or requests update the same user's presence.
- Keeps best-effort presence failures silent instead of interrupting active work with a global error notification.
- Replaces the misleading generic ticket concurrency message with an entity-neutral record message.
- Includes the contract expiration email idempotency protections from 1.66.97.
- Database compatibility remains `0242_contract_email_key`; deployments upgrading from 1.66.96 or earlier must run migrations.

## Deployment

1. Keep SMTP disabled until the `0242_contract_email_key` migration is confirmed.
2. Deploy the release and set `APP_VERSION=1.66.98` while preserving production secrets.
3. Run the packaged migration command.
4. Recycle every IIS application-pool worker.
5. Re-enable SMTP only after the migration and worker recycle are complete.

