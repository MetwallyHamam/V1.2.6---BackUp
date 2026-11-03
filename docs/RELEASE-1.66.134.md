# Millensys Support Hub 1.66.134

## Final database compatibility correction

- Removes the invalid `change_request_details.approved_software_version` compatibility requirement.
- Keeps the approved software version correctly scoped to `deployment_plans`.
- Keeps database head `0262_deployment_schema_reconcile`; no database data or schema change is required.
- Retains exact compatibility diagnostics through `/health/database` and `SupportHubBackend.exe diagnose-db`.

## UAT template lifecycle and ordering

- Separates Edit Current Template from Create New Version, so routine corrections do not increase the version number.
- Retains explicit version history when the user selects New Version and preserves historical cycle snapshots.
- Keeps template archiving and duplication actions available from the template card.
- Adds direct numeric test ordering (`1, 2, 3...`), Up/Down adjustment, and one-click ordering grouped by module.

Deploy the backend and frontend together, preserve production secrets in `backend\web.config`, update `APP_VERSION` to `1.66.134`, and recycle IIS.

- Full standalone artifact: `releases/SupportHub-1.66.134.zip`.
- SHA-256: `19F19C4C1BA672CE93001909F0A19F1CD8531B572AD246346A3799D1B524CEE8`.
