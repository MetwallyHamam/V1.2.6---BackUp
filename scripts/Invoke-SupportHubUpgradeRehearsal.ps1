[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$BackupFile,
    [Parameter(Mandatory)]
    [ValidatePattern('^[A-Za-z0-9_-]+_Rehearsal_[A-Za-z0-9_-]+$')]
    [string]$TargetDatabase,
    [string]$ProductionDatabase = "MillensysSupportHub",
    [string]$ServerInstance = "127.0.0.1,1433",
    [string]$Username = "sa",
    [Parameter(Mandatory)]
    [Security.SecureString]$Password,
    [string]$DataDirectory,
    [string]$LogDirectory,
    [string]$EvidenceDirectory = (Join-Path $PSScriptRoot "..\rehearsal-evidence"),
    [switch]$SkipRestore,
    [switch]$ReplaceExisting
)

$ErrorActionPreference = "Stop"
$startedAt = [DateTime]::UtcNow
$result = [ordered]@{
    started_at_utc = $startedAt.ToString("o")
    completed_at_utc = $null
    server_instance = $ServerInstance
    production_database = $ProductionDatabase
    rehearsal_database = $TargetDatabase
    backup_file = (Resolve-Path -LiteralPath $BackupFile).Path
    data_directory = $DataDirectory
    log_directory = $LogDirectory
    database_revision = $null
    restore = "NOT_RUN"
    migration = "NOT_RUN"
    seed = "NOT_RUN"
    smoke = "PENDING_SEPARATE_API_RUN"
    result = "FAILED"
    error = $null
}

if ($TargetDatabase -ieq $ProductionDatabase) {
    throw "The rehearsal target must never be the production database."
}
if (-not $env:SUPPORTHUB_REHEARSAL_DATABASE_URL) {
    throw "Set SUPPORTHUB_REHEARSAL_DATABASE_URL to the SQLAlchemy URL for the rehearsal database."
}
$escapedTarget = [Regex]::Escape($TargetDatabase)
if ($env:SUPPORTHUB_REHEARSAL_DATABASE_URL -notmatch "(?i)/$escapedTarget(?:\?|$)") {
    throw "SUPPORTHUB_REHEARSAL_DATABASE_URL must point to target database '$TargetDatabase'."
}

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\backend")).Path
$python = Join-Path $backendRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Backend virtual-environment Python was not found at $python."
}

$evidenceRoot = [IO.Path]::GetFullPath($EvidenceDirectory)
[IO.Directory]::CreateDirectory($evidenceRoot) | Out-Null
$evidenceFile = Join-Path $evidenceRoot "upgrade-rehearsal-$($startedAt.ToString('yyyyMMdd-HHmmss')).json"
$previousDatabaseUrl = $env:DATABASE_URL

try {
    if ($SkipRestore) {
        $credential = [Net.NetworkCredential]::new($Username, $Password)
        $connectionString = "Server=$ServerInstance;Database=master;User ID=$Username;Password=$($credential.Password);Encrypt=True;TrustServerCertificate=True;Connection Timeout=15"
        $connection = [Data.SqlClient.SqlConnection]::new($connectionString)
        try {
            $connection.Open()
            $command = $connection.CreateCommand()
            $command.CommandText = "SELECT COUNT(*) FROM sys.databases WHERE name = @name AND state_desc = 'ONLINE'"
            [void]$command.Parameters.Add("@name", [Data.SqlDbType]::NVarChar, 128)
            $command.Parameters["@name"].Value = $TargetDatabase
            if ([int]$command.ExecuteScalar() -ne 1) {
                throw "Rehearsal database '$TargetDatabase' does not exist or is not online."
            }
        }
        finally {
            $connection.Dispose()
            $credential.Password = ""
        }
        $result.restore = "SKIPPED_EXISTING_VERIFIED"
    }
    else {
        & (Join-Path $PSScriptRoot "Restore-SupportHubDatabase.ps1") `
            -BackupFile $result.backup_file `
            -TargetDatabase $TargetDatabase `
            -ServerInstance $ServerInstance `
            -Username $Username `
            -Password $Password `
            -DataDirectory $DataDirectory `
            -LogDirectory $LogDirectory `
            -ConfirmRestore `
            -ReplaceExisting:$ReplaceExisting
        $result.restore = "PASSED"
    }

    $env:DATABASE_URL = $env:SUPPORTHUB_REHEARSAL_DATABASE_URL
    Push-Location $backendRoot
    try {
        & $python -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade failed." }
        $result.migration = "PASSED"

        & $python -m app.modules.iam.seed
        if ($LASTEXITCODE -ne 0) { throw "Seed failed." }
        $result.seed = "PASSED"

        $currentRevision = (& $python -m alembic current).Trim()
        $headRevision = (& $python -m alembic heads).Trim()
        if ($LASTEXITCODE -ne 0 -or -not $currentRevision.StartsWith($headRevision.Split(' ')[0])) {
            throw "Database revision '$currentRevision' does not match head '$headRevision'."
        }
        $result.database_revision = $currentRevision
    }
    finally {
        Pop-Location
    }
    $result.result = "DATABASE_REHEARSAL_PASSED"
}
catch {
    $result.error = $_.Exception.Message
    throw
}
finally {
    $result.completed_at_utc = [DateTime]::UtcNow.ToString("o")
    $result | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $evidenceFile -Encoding utf8
    if ($null -eq $previousDatabaseUrl) {
        Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue
    }
    else {
        $env:DATABASE_URL = $previousDatabaseUrl
    }
    Write-Output "Rehearsal evidence: $evidenceFile"
}
