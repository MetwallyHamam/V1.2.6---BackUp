# Millensys Support Hub 1.66.96

## Contract expiration email anti-spam hotfix

- Sends one SMTP message per contract milestone with real To and CC headers.
- Stops treating CC recipients as separate standalone messages.
- Records recipient delivery evidence by email address instead of a nullable system-user reference.
- Prevents the SQL Server post-send persistence failure that left a successfully transmitted message stuck in processing.
- Automatically refreshes recent contract-notification activity every 15 seconds.

## Existing stuck delivery protection

- Marks existing contract-expiration outbox records left in `PROCESSING` as sent during migration.
- Synchronizes their contract notification ledger status to `SENT`.
- This intentionally prevents previously transmitted messages from being sent again after SMTP is re-enabled.

## Database and deployment

- Database compatibility advances to `0241_email_recipient_key`.
- Keep SMTP disabled during deployment.
- Run `backend/runtime/SupportHubBackend.exe migrate` before starting the upgraded application.
- Recycle every IIS backend worker, verify the migration head, and only then re-enable SMTP.
