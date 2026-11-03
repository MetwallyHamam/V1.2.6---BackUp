# Millensys Support Hub 1.66.131

## Database compatibility correction

- Adds forward-only migration `0261_deployment_evidence_repair` for databases already stamped at `0260_deployment_share_links`.
- Detects and adds only missing deployment evidence tables, indexes, and the approved software version column.
- Preserves existing deployment, UAT, ticket, client, and configuration data.
- Includes all deployment documentation, issue evidence, rollback, live tracking, client portal, and reporting features from 1.66.130.

## Deployment

- Use this release instead of `1.66.130`.
- Back up SQL Server, deploy the package, then run `backend\runtime\SupportHubBackend.exe migrate` before recycling IIS.
- After migration, `SELECT version_num FROM alembic_version` must return `0261_deployment_evidence_repair`.
- Full standalone artifact: `releases/SupportHub-1.66.131.zip`.
- SHA-256: `5AAEBCBFD3D9C708DAD790CE5754267A781AE148F0DE8DEECCE367BF68CFB8D3`.
