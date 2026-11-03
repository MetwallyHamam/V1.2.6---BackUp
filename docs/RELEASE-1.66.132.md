# Millensys Support Hub 1.66.132

## Complete deployment-schema reconciliation

- Adds migration `0262_deployment_schema_reconcile` for databases that reached revision 0261 but still report `SCHEMA_INCOMPLETE`.
- Reconciles the rollback-plan and approved-version columns, public deployment share links, issue evidence, plan documents, required columns, and indexes.
- Handles missing tables as well as partially created tables without resetting application data.
- Includes all deployment, UAT, integration, client-portal, live-tracking, attachment, and reporting functionality from prior releases.

## Deployment

- Use this release instead of 1.66.130 or 1.66.131.
- Back up SQL Server, deploy the package, and run `backend\runtime\SupportHubBackend.exe migrate` before recycling IIS.
- `SELECT version_num FROM alembic_version` must return `0262_deployment_schema_reconcile` after migration.
- Full standalone artifact: `releases/SupportHub-1.66.132.zip`.
- SHA-256: `A7DE32A083AB4371748446B162859D347EDC8865158E9A461DEBF36140C296C8`.
