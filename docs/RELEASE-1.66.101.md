# Support Hub 1.66.101

Fixes email jobs becoming stuck in PROCESSING with zero attempts when SQL
Server reports an unknown affected-row count. Claims now use OUTPUT/RETURNING
to identify the claimed record rather than relying on rowcount.

Includes the scheduler transaction and uncertain-delivery protections from
1.66.100. Database head remains `0242_contract_email_key`.

Deploy with SMTP disabled and old IIS workers stopped. Preserve production
configuration and set APP_VERSION=1.66.101. Restart all workers after deployment.
This release does not automatically reset historical PROCESSING events.
Review stuck event 63 and its delivery evidence before a controlled retry;
never bulk-reset uncertain or previously sent messages.

Regression coverage simulates rowcount=-1, verifies successful delivery and
checks that a second processing pass does not send again. Production SQL Server
and mailbox delivery still require deployment verification.
