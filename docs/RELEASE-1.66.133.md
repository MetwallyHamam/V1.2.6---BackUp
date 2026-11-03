# Millensys Support Hub 1.66.133

## Exact database compatibility diagnostics

- Keeps database head `0262_deployment_schema_reconcile` and does not modify application data.
- Reports the exact missing table and columns through `/health/database`, API errors, startup logs, and the new `diagnose-db` runtime command.
- Removes ambiguity from `SCHEMA_INCOMPLETE` failures after successful migration.

Run `backend\runtime\SupportHubBackend.exe diagnose-db` from the installed release backend directory to obtain the authoritative database result.
