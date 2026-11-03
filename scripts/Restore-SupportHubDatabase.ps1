[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$BackupFile,
    [Parameter(Mandatory)]
    [string]$TargetDatabase,
    [string]$ServerInstance = "127.0.0.1,1433",
    [string]$Username = "sa",
    [Parameter(Mandatory)]
    [Security.SecureString]$Password,
    [string]$DataDirectory,
    [string]$LogDirectory,
    [switch]$ReplaceExisting,
    [switch]$ConfirmRestore
)

$ErrorActionPreference = "Stop"

if (-not $ConfirmRestore) {
    throw "Restore was not confirmed. Re-run with -ConfirmRestore after checking the target."
}
if ($TargetDatabase -notmatch '^[A-Za-z0-9_-]+$') {
    throw "TargetDatabase may contain only letters, numbers, underscores, and hyphens."
}
if ($TargetDatabase -in @('master', 'model', 'msdb', 'tempdb')) {
    throw "System databases cannot be restored with this script."
}

$resolvedBackup = (Resolve-Path -LiteralPath $BackupFile).Path
$resolvedDataDirectory = if ($DataDirectory) {
    [IO.Directory]::CreateDirectory([IO.Path]::GetFullPath($DataDirectory)).FullName
} else { $null }
$resolvedLogDirectory = if ($LogDirectory) {
    [IO.Directory]::CreateDirectory([IO.Path]::GetFullPath($LogDirectory)).FullName
} else { $resolvedDataDirectory }
$credential = [Net.NetworkCredential]::new($Username, $Password)
$connectionString = "Server=$ServerInstance;Database=master;User ID=$Username;Password=$($credential.Password);Encrypt=True;TrustServerCertificate=True;Connection Timeout=15"
$connection = [Data.SqlClient.SqlConnection]::new($connectionString)

try {
    $connection.Open()
    $escapedDatabase = $TargetDatabase.Replace(']', ']]')
    $existsCommand = $connection.CreateCommand()
    $existsCommand.CommandText = "SELECT COUNT(*) FROM sys.databases WHERE name = @name"
    [void]$existsCommand.Parameters.Add("@name", [Data.SqlDbType]::NVarChar, 128)
    $existsCommand.Parameters["@name"].Value = $TargetDatabase
    $databaseExists = [int]$existsCommand.ExecuteScalar() -gt 0
    if ($databaseExists -and -not $ReplaceExisting) {
        throw "Database '$TargetDatabase' already exists. Use a new target or explicitly pass -ReplaceExisting."
    }

    $verifyCommand = $connection.CreateCommand()
    $verifyCommand.CommandTimeout = 0
    $verifyCommand.CommandText = "RESTORE VERIFYONLY FROM DISK = @path WITH CHECKSUM"
    [void]$verifyCommand.Parameters.Add("@path", [Data.SqlDbType]::NVarChar, 4000)
    $verifyCommand.Parameters["@path"].Value = $resolvedBackup
    [void]$verifyCommand.ExecuteNonQuery()

    $fileListCommand = $connection.CreateCommand()
    $fileListCommand.CommandTimeout = 0
    $fileListCommand.CommandText = "RESTORE FILELISTONLY FROM DISK = @path"
    [void]$fileListCommand.Parameters.Add("@path", [Data.SqlDbType]::NVarChar, 4000)
    $fileListCommand.Parameters["@path"].Value = $resolvedBackup
    $fileList = [Data.DataTable]::new()
    $fileList.Load($fileListCommand.ExecuteReader())
    if ($fileList.Rows.Count -eq 0) {
        throw "The backup contains no database files."
    }

    $pathsCommand = $connection.CreateCommand()
    $pathsCommand.CommandText = "SELECT CAST(SERVERPROPERTY('InstanceDefaultDataPath') AS nvarchar(4000)) AS DataPath, CAST(SERVERPROPERTY('InstanceDefaultLogPath') AS nvarchar(4000)) AS LogPath"
    $pathsReader = $pathsCommand.ExecuteReader()
    if (-not $pathsReader.Read()) {
        throw "SQL Server default data and log paths could not be read."
    }
    $defaultDataPath = [string]$pathsReader["DataPath"]
    $defaultLogPath = [string]$pathsReader["LogPath"]
    $pathsReader.Close()
    if (-not $defaultDataPath -or -not $defaultLogPath) {
        throw "SQL Server did not report default data and log paths."
    }

    $moveClauses = @()
    $fileNumber = 0
    foreach ($file in $fileList.Rows) {
        $fileNumber++
        $logicalName = ([string]$file["LogicalName"]).Replace("'", "''")
        $isLog = [string]$file["Type"] -eq "L"
        $extension = if ($isLog) { ".ldf" } elseif ($fileNumber -eq 1) { ".mdf" } else { ".ndf" }
        $directory = if ($isLog) {
            if ($resolvedLogDirectory) { $resolvedLogDirectory } else { $defaultLogPath }
        } else {
            if ($resolvedDataDirectory) { $resolvedDataDirectory } else { $defaultDataPath }
        }
        $physicalPath = Join-Path $directory "$TargetDatabase-$fileNumber$extension"
        $escapedPhysicalPath = $physicalPath.Replace("'", "''")
        $moveClauses += "MOVE N'$logicalName' TO N'$escapedPhysicalPath'"
    }

    $replaceClause = if ($ReplaceExisting) { ", REPLACE" } else { "" }
    $restoreCommand = $connection.CreateCommand()
    $restoreCommand.CommandTimeout = 0
    $restoreCommand.CommandText = "RESTORE DATABASE [$escapedDatabase] FROM DISK = @path WITH RECOVERY, CHECKSUM, $($moveClauses -join ', ')$replaceClause"
    [void]$restoreCommand.Parameters.Add("@path", [Data.SqlDbType]::NVarChar, 4000)
    $restoreCommand.Parameters["@path"].Value = $resolvedBackup
    [void]$restoreCommand.ExecuteNonQuery()
    Write-Output "Database restored: $TargetDatabase"
}
finally {
    $connection.Dispose()
    $credential.Password = ""
}
