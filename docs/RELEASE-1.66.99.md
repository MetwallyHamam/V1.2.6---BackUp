# Millensys Support Hub 1.66.99

## Email queue processing hotfix

- Isolates scheduler stages so failures in SLA, UAT, contract lifecycle, or Outlook processing cannot prevent the email outbox stage from running.
- Records each failed stage independently in scheduler diagnostics while continuing safe stages.
- Adds an audited **Process email queue now** action to System Operations for administrators with `configuration.manage`.
- Expands SMTP diagnostics to include every queued email type, including contract expiration messages.
- Includes the presence and contract-email idempotency fixes from 1.66.98.
- Database compatibility remains `0242_contract_email_key`.

## Deployment

1. Deploy the release and preserve production configuration with `APP_VERSION=1.66.99`.
2. Confirm database head `0242_contract_email_key`.
3. Recycle every IIS application-pool worker.
4. Open System Operations → Third-party integrations → SMTP.
5. Select **Process email queue now** and verify the result counters.

