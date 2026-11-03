# Millensys Support Hub 1.66.93

## Contract expiration notification delivery

- Replaces manually entered To and CC addresses with active system-user selections.
- Sends each selected user both an in-system reminder and an email to the user's current system email address.
- Evaluates active contracts immediately after a notification rule is saved while retaining scheduled milestone processing.
- Adds catch-up behavior so a contract already inside a configured reminder window receives the nearest missed milestone once.
- Preserves legacy address-based configuration by matching existing addresses to active system users.

## Delivery evidence and duplicate prevention

- Adds a durable contract-expiration notification ledger by contract term, milestone, channel, and recipient.
- Tracks queued, delivered, sent, retry, failed, and skipped outcomes with timestamps and error details.
- Prevents duplicate in-system notifications and emails across repeated scheduler executions.
- Adds recent notification activity to the Contract workspace Notifications section.

## Database and deployment

- Database compatibility advances to `0239_contract_notify_log`.
- Deploy the packaged frontend and backend together.
- Run `backend/runtime/SupportHubBackend.exe migrate` before starting the upgraded application.
- Review the selected To and CC system users after deployment, then save the rule to evaluate currently expiring contracts immediately.
