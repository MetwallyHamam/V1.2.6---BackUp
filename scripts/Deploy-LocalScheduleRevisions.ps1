param([ValidateSet('dist-iis-schedule-revisions', 'dist-iis-project-register', 'dist-iis-handover-permissions', 'dist-iis-project-redesign', 'dist-iis-intake-resubmit', 'dist-iis-project-delivery', 'dist-iis-project-branches')][string]$BuildDirectory = 'dist-iis-schedule-revisions')
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath 'D:\SupportHub\Release').Path
if ($root -ne 'D:\SupportHub\Release') { throw "Unexpected release root: $root" }
$workspace = Split-Path -Parent $PSScriptRoot
$frontendSource = Join-Path $workspace "frontend\$BuildDirectory"
$runtimeSource = Join-Path $workspace "backend\$BuildDirectory\SupportHubBackend"
$frontend = Join-Path $root 'frontend'
$runtime = Join-Path $root 'backend\runtime'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$frontendBackup = "$frontend.pre-schedule-revisions-$stamp"
$runtimeBackup = "$runtime.pre-schedule-revisions-$stamp"
$frontendStage = "$frontend.stage-$stamp"
$runtimeStage = "$runtime.stage-$stamp"
$appcmd = Join-Path $env:windir 'System32\inetsrv\appcmd.exe'
$pools = @('SupportHubFrontEnd', 'SupportHubBackEnd')
$upgradeDrafts = $BuildDirectory -eq 'dist-iis-project-delivery'
$migrationApplied = $false
$databaseBackup = "D:\SupportHub\DB\MillensysSupportHub_pre_0297_$stamp.bak"
$backendSource = Join-Path $workspace 'backend'

function Invoke-BackendPython {
    Push-Location -LiteralPath $backendSource
    try {
        & '.\.venv\Scripts\python.exe' @args
        if ($LASTEXITCODE -ne 0) { throw "Backend maintenance command failed." }
    } finally {
        Pop-Location
    }
}

function Set-Pool([string]$Action, [string]$Pool) {
    & $appcmd $Action apppool "/apppool.name:$Pool"
    if ($LASTEXITCODE -ne 0) { throw "Could not $Action IIS pool $Pool." }
}

function Copy-Build([string]$Source, [string]$Destination) {
    & robocopy $Source $Destination /E /R:2 /W:1 /NFL /NDL /NJH /NJS /NP
    if ($LASTEXITCODE -ge 8) { throw "Build copy failed: $Source" }
}

foreach ($path in @($frontend, $runtime, (Split-Path -Parent $runtime))) {
    $item = Get-Item -LiteralPath $path
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Unexpected linked path: $path" }
}
foreach ($file in @("$frontendSource\index.html", "$runtimeSource\SupportHubBackend.exe", "$runtimeSource\_internal")) {
    if (!(Test-Path -LiteralPath $file)) { throw "Missing build output: $file" }
}
Copy-Build $frontendSource $frontendStage
Copy-Item -LiteralPath "$frontend\web.config" -Destination "$frontendStage\web.config" -Force
Copy-Build $runtimeSource $runtimeStage

try {
    foreach ($pool in $pools) { Set-Pool 'stop' $pool }
    if ($upgradeDrafts) {
        Invoke-BackendPython -c "from app.db.session import engine; from sqlalchemy import text; assert engine.url.host in ('localhost','127.0.0.1','::1') and engine.url.database=='MillensysSupportHub'; connection=engine.connect(); assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='0296_project_templates'; connection.close()"
        if (Test-Path -LiteralPath $databaseBackup) { throw 'Database backup path already exists.' }
        Invoke-BackendPython -m scripts.backup_local_test_database $databaseBackup
        Invoke-BackendPython -m alembic upgrade 0297_project_wizard_drafts
        $migrationApplied = $true
        Invoke-BackendPython -m scripts.seed_local_delivery_workspaces
    }
    Move-Item -LiteralPath $frontend -Destination $frontendBackup
    Move-Item -LiteralPath $runtime -Destination $runtimeBackup
    Move-Item -LiteralPath $frontendStage -Destination $frontend
    Move-Item -LiteralPath $runtimeStage -Destination $runtime
    foreach ($pool in $pools) { Set-Pool 'start' $pool }

    $base = 'http://localhost/SupportHub'
    $checks = @('/', '/projects/3/work-packages', '/projects/3/revisions', '/backend/api/v1/health', '/backend/api/v1/health/database')
    if ($BuildDirectory -ne 'dist-iis-schedule-revisions') { $checks += '/projects/3/register' }
    if ($BuildDirectory -eq 'dist-iis-project-redesign') { $checks += @('/project-my-work', '/projects/3', '/projects/3/collaboration') }
    if ($BuildDirectory -eq 'dist-iis-intake-resubmit') { $checks += @('/project-my-work', '/projects/3/intake', '/implementation-intake') }
    if ($upgradeDrafts -or $BuildDirectory -eq 'dist-iis-project-branches') { $checks += @('/project-my-work', '/project-analytics', '/implementation-workspace', '/implementation-analytics', '/support-handover-inbox') }
    if ($BuildDirectory -eq 'dist-iis-project-branches') { $checks += @('/projects/3/schedule', '/projects?view=backlog', '/projects?view=calendar', '/projects?view=timeline', '/implementation-intake?view=queue') }
    $index = Get-Content -LiteralPath "$frontendSource\index.html" -Raw
    $entry = [regex]::Match($index, '/SupportHub/assets/index-[^"]+\.js').Value
    if (!$entry) { throw 'The frontend build entry is missing.' }
    foreach ($path in $checks) {
        $timeout = if ($path -eq '/backend/api/v1/health') { 55 } else { 25 }
        $result = Invoke-WebRequest -Uri "$base$path" -TimeoutSec $timeout
        if ($result.StatusCode -ne 200) { throw "Smoke check failed: $path" }
        if ($path -notlike '/backend/*' -and !$result.Content.Contains($entry)) {
            throw "IIS is not serving the new build on $path."
        }
        if ($path -eq '/backend/api/v1/health/database') {
            $database = $result.Content | ConvertFrom-Json
            if ($database.schema -ne 'compatible') { throw 'Database schema is not compatible.' }
            Write-Output "Database revision: $($database.revision)"
        }
        Write-Output "$($result.StatusCode) $path"
    }
    $asset = Invoke-WebRequest -Uri "http://localhost$entry" -TimeoutSec 15
    if ($asset.StatusCode -ne 200) { throw 'The deployed frontend asset is unavailable.' }
    Write-Output "Rollback copies: $frontendBackup and $runtimeBackup"
} catch {
    foreach ($pool in $pools) { & $appcmd stop apppool "/apppool.name:$pool" }
    if ($migrationApplied) {
        Invoke-BackendPython -c "from app.db.session import engine; from sqlalchemy import text; connection=engine.connect(); assert connection.execute(text('SELECT COUNT(*) FROM project_wizard_drafts')).scalar_one()==0, 'New drafts exist; manual recovery required'; connection.close()"
        Invoke-BackendPython -m alembic downgrade 0296_project_templates
    }
    foreach ($entry in @(@{Live=$runtime; Backup=$runtimeBackup}, @{Live=$frontend; Backup=$frontendBackup})) {
        if (Test-Path -LiteralPath $entry.Backup) {
            if (Test-Path -LiteralPath $entry.Live) {
                Move-Item -LiteralPath $entry.Live -Destination "$($entry.Live).failed-$stamp"
            }
            Move-Item -LiteralPath $entry.Backup -Destination $entry.Live
        }
    }
    foreach ($pool in $pools) { & $appcmd start apppool "/apppool.name:$pool" }
    throw
}
