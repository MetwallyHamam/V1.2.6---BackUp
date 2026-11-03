# Millensys Support Hub 1.66.94

## Contract expiration reminder correction

- Fixes contract-specific future renewal-notice dates incorrectly suppressing global expiration milestones.
- Ensures a contract with two days remaining catches up once at the configured seven-day milestone.
- Preserves the contract-specific renewal-notice date as a fallback when no global milestone applies.
- Continues recording and deduplicating in-system and email delivery independently.

## Branded contract email

- Uses the standard responsive Millensys Support Hub HTML email shell.
- Adds a dedicated Contract Expiration badge and warning accent.
- Includes the configured contract subject/body and a branded Open in Support Hub action linked to the contract workspace.
- Retains a plain-text alternative for mail clients that do not render HTML.

## Database and deployment

- Database compatibility remains `0239_contract_notify_log`; no new migration is required from `1.66.93`.
- Deploy the packaged frontend and backend together.
- Save the contract notification rule after deployment to evaluate currently expiring contracts immediately.
