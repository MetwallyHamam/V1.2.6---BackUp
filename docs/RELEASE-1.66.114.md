# Millensys Support Hub 1.66.114

## Knowledge resolution library and escalation email hotfix

- Adds contextual Knowledge Base categories and article scope by product, module, service, and client.
- Adds reusable resolution, root-cause, service, outcome, and permanent-fix templates that engineers can apply from ticket resolution.
- Records Knowledge Base recommendation scores and applied-resolution usage for auditability.
- Validates referenced catalog records before saving scoped knowledge articles.
- Restores SQL Server row-count reporting after contract-lifecycle application locks and before every scheduler stage.
- Prevents pooled SQL Server connections from causing false concurrent-update errors or interrupting escalation and email processing.
- Adds focused regression coverage for knowledge recommendations, resolution application, usage evidence, scheduler locks, and email delivery transaction boundaries.
- Database compatibility advances to `0245_knowledge_resolution`.

## Mandatory deployment order

1. Back up the production database.
2. Deploy the frontend and backend from this release together and preserve production secrets.
3. Run `backend\runtime\SupportHubBackend.exe migrate` and verify database head `0245_knowledge_resolution`.
4. Recycle every IIS application-pool worker to discard existing pooled SQL Server connections.
5. Verify the scheduler health/status reports successful escalation, contract-lifecycle, email-outbox, and Outlook stages.
6. Confirm pending/retry email delivery and perform the release smoke test.
