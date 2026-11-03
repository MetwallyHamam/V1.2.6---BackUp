# Millensys Support Hub 1.66.95

## Contract notification SQL Server hotfix

- Removes SQL Server-hostile unique constraints from nullable notification-ledger references.
- Allows one contract milestone to record multiple selected in-system recipients plus its email queue record.
- Fixes the 500 response when saving a contract notification rule with To and CC users.
- Makes rule configuration, audit evidence, and immediate lifecycle evaluation atomic so a failed evaluation cannot partially save a new rule version.
- Retains the global-milestone correction and branded contract-expiration HTML email introduced in `1.66.94`.

## Database and deployment

- Database compatibility advances to `0240_contract_notify_null`.
- Run `backend/runtime/SupportHubBackend.exe migrate` before starting the upgraded application.
- Recycle every IIS backend worker after deployment.
- Reload the rule after deployment because failed `1.66.94` attempts may already have advanced its version, then save it once.
