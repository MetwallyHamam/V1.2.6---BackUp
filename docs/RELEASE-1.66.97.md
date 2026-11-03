# Millensys Support Hub 1.66.97

## Contract expiration email idempotency hotfix

- Prevents overlapping IIS workers and notification-rule saves from enqueueing the same contract expiration milestone more than once.
- Adds a database-enforced unique contract expiration event key.
- Quarantines historical duplicate outbox events during upgrade so they cannot send after SMTP is enabled again.
- Adds a final sender-side duplicate guard before SMTP delivery.
- Preserves one grouped message with real To and CC headers.
- Database compatibility advances to `0242_contract_email_key`.

## Mandatory deployment order

1. Disable SMTP delivery and recycle every IIS worker before deployment.
2. Deploy the release and preserve production secrets while setting `APP_VERSION=1.66.97`.
3. Run the database migration and verify head `0242_contract_email_key`.
4. Recycle every IIS application-pool worker again.
5. Confirm duplicate queued expiration events are no longer active, then enable SMTP.

