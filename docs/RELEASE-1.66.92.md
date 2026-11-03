# Millensys Support Hub 1.66.92

## Contract expiration notification rules

- Adds a permission-controlled Notifications section to the Contract workspace.
- Configures expiration reminder milestones, enabled state, To recipients, CC recipients, and reusable subject/body templates.
- Supports contract number, contract name, end date, remaining days, and renewal-status placeholders.
- Queues durable, deduplicated expiration email events while preserving existing in-app renewal reminders.
- Protects concurrent edits with version checking and records configuration changes in the audit log.

## Access governance

- Adds `contract.notification_rules.manage` for configuring contract notification rules.
- Grants the permission to Administrator by default; administrators can assign it to selected profiles through the existing profile permission workspace.

## Database and deployment

- Database compatibility advances to `0238_contract_notify_perm`.
- Deploy the packaged frontend and backend together.
- Run `backend/runtime/SupportHubBackend.exe migrate` before starting the upgraded application.
