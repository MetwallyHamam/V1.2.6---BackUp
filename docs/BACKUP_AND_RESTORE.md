# SQL Server backup and restore

Run backups before every production migration and on a tested schedule. The scripts prompt for a password as a secure value and do not store it in source control.

Administrators can also view backup history and start a checked SQL backup from
**Administration → System Operations**. This action requires
`configuration.manage` and creates an audit record. Restore remains deliberately
server-only.

## Create and verify a backup

Run from the repository root:

```powershell
$dbPassword = Read-Host "SQL Server password" -AsSecureString
.\scripts\Backup-SupportHubDatabase.ps1 -Password $dbPassword
```

Use `-ServerInstance`, `-Database`, `-BackupDirectory`, and `-Username` to override the defaults. The command creates a timestamped `.bak` file and immediately runs `RESTORE VERIFYONLY` with checksums. The default `backups` directory is ignored by Git.

The SQL Server service account—not only the interactive user—must be able to write to the chosen directory. For a remote SQL Server, use a server-visible UNC path.

## Restore drill

Restores are intentionally guarded. Restore into a separate database first:

```powershell
$dbPassword = Read-Host "SQL Server password" -AsSecureString
.\scripts\Restore-SupportHubDatabase.ps1 `
  -BackupFile .\backups\MillensysSupportHub-20260731-120000.bak `
  -TargetDatabase MillensysSupportHub_RestoreTest `
  -Password $dbPassword `
  -ConfirmRestore
```

The script verifies the backup before restoring it. It refuses system database names and refuses to overwrite an existing database unless `-ReplaceExisting` is explicitly supplied. Replacing a database destroys its current contents, so take and verify a fresh backup first.

After a restore drill, point a temporary application configuration at the restored database, run `/api/v1/health/database`, sign in, and inspect clients, tickets, products/modules, assignments, and notifications. Record the backup duration, restore duration, and result.

For a complete release upgrade and rollback rehearsal with recorded JSON evidence, follow `UPGRADE_REHEARSAL.md` and use `scripts\Invoke-SupportHubUpgradeRehearsal.ps1`.

## Operational baseline

- Keep at least one encrypted copy outside the SQL Server host.
- Restrict backup files to database administrators and the service identity.
- Define retention according to business and legal requirements.
- Automate backups with SQL Server Agent or an approved scheduler.
- Test restoration regularly; a backup is not proven until it restores successfully.
