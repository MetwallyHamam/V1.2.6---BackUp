[CmdletBinding()]
param(
    [string]$ServerInstance = "127.0.0.1,1433",
    [string]$Database = "MillensysSupportHub",
    [string]$BackupDirectory = (Join-Path $PSScriptRoot "..\backups"),
    [string]$Username = "sa",
    [Parameter(Mandatory)]
    [Security.SecureString]$Password
)

$ErrorActionPreference = "Stop"

if ($Database -notmatch '^[A-Za-z0-9_-]+$') {
    throw "Database may contain only letters, numbers, underscores, and hyphens."
}

$backupRoot = [IO.Path]::GetFullPath($BackupDirectory)
[IO.Directory]::CreateDirectory($backupRoot) | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupFile = Join-Path $backupRoot "$Database-$timestamp.bak"

$credential = [Net.NetworkCredential]::new($Username, $Password)
$connectionString = "Server=$ServerInstance;Database=master;User ID=$Username;Password=$($credential.Password);Encrypt=True;TrustServerCertificate=True;Connection Timeout=15"
$connection = [Data.SqlClient.SqlConnection]::new($connectionString)

try {
    $connection.Open()
    $escapedDatabase = $Database.Replace(']', ']]')
    $command = $connection.CreateCommand()
    $command.CommandTimeout = 0
    $command.CommandText = "BACKUP DATABASE [$escapedDatabase] TO DISK = @path WITH COPY_ONLY, CHECKSUM, COMPRESSION, INIT; RESTORE VERIFYONLY FROM DISK = @path WITH CHECKSUM;"
    [void]$command.Parameters.Add("@path", [Data.SqlDbType]::NVarChar, 4000)
    $command.Parameters["@path"].Value = $backupFile
    [void]$command.ExecuteNonQuery()
    Write-Output "Verified backup created: $backupFile"
}
finally {
    $connection.Dispose()
    $credential.Password = ""
}
