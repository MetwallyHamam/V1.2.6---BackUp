# Production-backup upgrade rehearsal

Perform this only on an isolated SQL Server and application environment. The rehearsal target must be a separate database named like `MillensysSupportHub_Rehearsal_20260805`. Never use the live production database as the target.

## 1. Restore, migrate, and seed

The SQLAlchemy URL is passed through an environment variable to avoid putting its password in the process command line. Its database name must exactly match `TargetDatabase`.

```powershell
$sqlPassword = Read-Host "SQL Server password" -AsSecureString
$env:SUPPORTHUB_REHEARSAL_DATABASE_URL = 'mssql+pyodbc://rehearsal_user:password@server/MillensysSupportHub_Rehearsal_20260805?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes'

.\scripts\Invoke-SupportHubUpgradeRehearsal.ps1 `
  -BackupFile '.\backups\MillensysSupportHub-20260805-010000.bak' `
  -TargetDatabase 'MillensysSupportHub_Rehearsal_20260805' `
  -ServerInstance 'staging-sql,1433' `
  -Username 'rehearsal_admin' `
  -Password $sqlPassword `
  -DataDirectory 'D:\SupportHub-Rehearsal\data' `
  -LogDirectory 'D:\SupportHub-Rehearsal\log'
```

The script verifies and restores the backup, maps its logical files to new rehearsal MDF/LDF files, runs `alembic upgrade head`, runs the seed, verifies the current revision, and writes JSON evidence under `rehearsal-evidence`. It refuses a target equal to `ProductionDatabase`.

Use `DataDirectory` and `LogDirectory` when the SQL Server default drive does not have enough free capacity. Both paths must be isolated rehearsal locations writable by the SQL Server service account.

If restore passed but a later migration or seed step failed, correct the connection issue and rerun with `-SkipRestore`. The script first verifies that the separately named rehearsal database exists and is online; it still rejects the production database name and requires the rehearsal URL to name the exact target.

## 2. Start the isolated application and run full smoke checks

Configure a staging SupportHub instance with the same rehearsal database URL. Then run:

```powershell
$env:SUPPORTHUB_SMOKE_LOGIN = 'staging-smoke@example.com'
$env:SUPPORTHUB_SMOKE_PASSWORD = '<password>'
python .\backend\scripts\release_smoke.py `
  --base-url 'https://staging.example.com/SupportHub/backend/api/v1' `
  --create-ticket
```

Record the smoke output with the JSON rehearsal evidence. Verify that the restored historical ticket, contract, SLA, shift, user/profile, dashboard, HR XLSX, ticket CSV, and new smoke ticket are correct.

## 3. Rollback rehearsal

Rollback means switching the isolated application back to its previous application release and restoring the verified pre-upgrade backup to a newly named rollback-test database. Do not use `alembic downgrade` as a production rollback strategy. Point the isolated application at the rollback-test database and repeat the read-only smoke test.

Record release version, source backup, source and target revisions, operator, start/end times, migration result, full smoke result, rollback restore result, rollback smoke result, and any corrective action. `P2.0.10` is complete only when both upgrade and rollback rehearsals succeed.

Remove secret environment variables after the exercise:

```powershell
Remove-Item Env:\SUPPORTHUB_REHEARSAL_DATABASE_URL, Env:\SUPPORTHUB_SMOKE_LOGIN, Env:\SUPPORTHUB_SMOKE_PASSWORD
```

## 4. Attachment storage and authorization rehearsal

Point an isolated application instance at an isolated attachment storage root. Use one employee account with `problem.edit` and visibility of a disposable Problem, plus a second active account that has no visibility of that Problem. Credentials stay in environment variables:

```powershell
$env:SUPPORTHUB_ATTACHMENT_REHEARSAL_LOGIN = 'authorized-staging-user'
$env:SUPPORTHUB_ATTACHMENT_REHEARSAL_PASSWORD = '<password>'
$env:SUPPORTHUB_ATTACHMENT_DENIED_LOGIN = 'out-of-scope-staging-user'
$env:SUPPORTHUB_ATTACHMENT_DENIED_PASSWORD = '<password>'

python .\backend\scripts\attachment_rehearsal.py `
  --base-url 'https://staging.example.com/SupportHub/backend/api/v1' `
  --problem-id 123 `
  --evidence '.\rehearsal-evidence\attachment-rehearsal.json'
```

The rehearsal uploads a unique harmless text file, confirms its SHA-256 after download, and requires both list and download requests from the out-of-scope account to return `403` or `404`. It intentionally leaves the evidence attachment in the disposable Problem so the operator can confirm the stored file is under the isolated root and not an application or web-public directory. Do not run it against a production Problem.

Remove the four attachment rehearsal credential variables after the exercise.
