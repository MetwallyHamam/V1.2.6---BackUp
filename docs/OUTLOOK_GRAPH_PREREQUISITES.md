# Outlook / Microsoft Graph prerequisites

This is the security and tenant checklist for the `Support@millensys.com` integration. Do not store the client secret in Site Settings or the database; deployment supplies it as a protected process secret.

## Microsoft Entra application

- Register a single-tenant confidential application in the Millensys tenant.
- Use application authentication (client credentials), not a shared mailbox password or delegated user token.
- Grant Microsoft Graph application permissions `Mail.Read`, `Mail.Send`, and `MailboxSettings.Read` only if mailbox timezone/settings are consumed.
- Grant tenant administrator consent after security review.
- Restrict application mailbox access to `Support@millensys.com` using the tenant's supported Exchange Online application-access policy or application RBAC mechanism.
- Record tenant ID, client ID, mailbox address, and credential expiry owner. Store the client secret or certificate outside source control and the database.

## Webhook endpoint

- Publish an HTTPS endpoint reachable by Microsoft Graph, with a certificate trusted by Microsoft.
- Accept and echo Graph validation tokens only on the subscription-validation route.
- Generate a high-entropy client-state secret and compare it in constant time for every notification.
- Acknowledge valid notifications quickly and enqueue processing; never fetch/process mailbox content inline.
- Configure lifecycle notifications and a delta reconciliation cursor so missed or removed subscriptions recover safely.

## Minimum operational controls

- Start `outlook_inbound_email`, `email_creation_acknowledgement`, and `email_status_notifications` in `OFF`, then use `SHADOW` before `ENFORCED`.
- Define allowed domains/addresses, blocked senders, unknown-sender behavior, attachment limits/types, retry limits, and retention before enabling ingestion.
- Monitor subscription expiry, token failures, throttling, queue age, dead-letter count, duplicate rate, and last successful delta synchronization.
- Rotate credentials before expiry and test disablement, renewal, reconciliation, and rollback in staging.

P8 will use Graph message ID plus Internet Message-ID for deduplication and will pass every new-ticket request through P4 entitlement decisions before a ticket can be created.
