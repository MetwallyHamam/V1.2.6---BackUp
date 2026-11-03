param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version,
    [string]$OutputRoot = (Join-Path $PSScriptRoot '..\releases'),
    [string]$ApiUrl = '/SupportHub/backend/api/v1',
    [string]$BasePath = '/SupportHub/',
    [string]$BackendPath = '/SupportHub/backend'
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$releaseRoot = Join-Path ([System.IO.Path]::GetFullPath($OutputRoot)) $Version
if (Test-Path -LiteralPath $releaseRoot) {
    throw "Release $Version already exists. Release directories are immutable."
}

$releaseNotes = Join-Path $projectRoot "docs\RELEASE-$Version.md"
$releaseLog = Join-Path $projectRoot 'RELEASE_STEPS.md'
if (-not (Test-Path -LiteralPath $releaseNotes)) {
    throw "Release notes are required: docs\RELEASE-$Version.md"
}
if (-not (Test-Path -LiteralPath $releaseLog)) {
    throw 'RELEASE_STEPS.md is required.'
}
if (-not (Select-String -LiteralPath $releaseLog -SimpleMatch "## $Version" -Quiet)) {
    throw "RELEASE_STEPS.md must contain a ## $Version entry before packaging."
}

$frontendRoot = Join-Path $projectRoot 'frontend'
$backendRoot = Join-Path $projectRoot 'backend'
$python = Join-Path $backendRoot '.venv\Scripts\python.exe'
$pytestTemp = Join-Path $projectRoot ".release-pytest-$Version"
if (Test-Path -LiteralPath $pytestTemp) { Remove-Item -LiteralPath $pytestTemp -Recurse -Force }
Push-Location $backendRoot
try {
    & $python -m ruff check app alembic scripts
    if ($LASTEXITCODE -ne 0) { throw 'Backend lint failed.' }
    & $python -m mypy app
    if ($LASTEXITCODE -ne 0) { throw 'Backend type check failed.' }
    & $python -m pytest --basetemp $pytestTemp
    if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed.' }
}
finally {
    Pop-Location
    if (Test-Path -LiteralPath $pytestTemp) { Remove-Item -LiteralPath $pytestTemp -Recurse -Force }
}

$env:VITE_API_URL = $ApiUrl
$env:VITE_BASE_PATH = $BasePath
Push-Location $frontendRoot
try {
    & node '.\node_modules\eslint\bin\eslint.js' . --max-warnings 0
    if ($LASTEXITCODE -ne 0) { throw 'Frontend lint failed.' }
    & node '.\node_modules\vitest\vitest.mjs' run
    if ($LASTEXITCODE -ne 0) { throw 'Frontend tests failed.' }
    & node '.\node_modules\typescript\bin\tsc' -b
    if ($LASTEXITCODE -ne 0) { throw 'Frontend TypeScript build failed.' }
    $frontendDist = Join-Path $frontendRoot 'dist'
    if (Test-Path -LiteralPath $frontendDist) { Remove-Item -LiteralPath $frontendDist -Recurse -Force }
    & node '.\node_modules\vite\bin\vite.js' build
    if ($LASTEXITCODE -ne 0 -and -not (Test-Path -LiteralPath (Join-Path $frontendRoot 'dist\index.html'))) {
        throw 'Frontend Vite build failed.'
    }
}
finally {
    Pop-Location
    Remove-Item Env:\VITE_API_URL -ErrorAction SilentlyContinue
    Remove-Item Env:\VITE_BASE_PATH -ErrorAction SilentlyContinue
}

$frontendTarget = Join-Path $releaseRoot 'frontend'
$backendTarget = Join-Path $releaseRoot 'backend'
$databaseTarget = Join-Path $releaseRoot 'database'
$operationsTarget = Join-Path $releaseRoot 'operations'
$localAiTarget = Join-Path $releaseRoot 'local-ai'
New-Item -ItemType Directory -Path $frontendTarget, $backendTarget, $databaseTarget, $operationsTarget, $localAiTarget -Force | Out-Null
Copy-Item -Path (Join-Path $frontendRoot 'dist\*') -Destination $frontendTarget -Recurse -Force
$frontendConfig = Join-Path $frontendTarget 'web.config'
$frontendContent = Get-Content -LiteralPath $frontendConfig -Raw
$indexPath = (($BasePath.TrimEnd('/')) + '/index.html')
if ($indexPath -eq '/index.html') { $indexPath = '/index.html' }
$frontendContent = $frontendContent.Replace('/SupportHub/backend/', ($BackendPath.TrimEnd('/') + '/')).Replace('/SupportHub/index.html', $indexPath)
Set-Content -LiteralPath $frontendConfig -Value $frontendContent -Encoding utf8

$backendItems = @('app', 'alembic', 'scripts', 'alembic.ini', 'pyproject.toml')
foreach ($item in $backendItems) {
    Copy-Item -Path (Join-Path $backendRoot $item) -Destination $backendTarget -Recurse -Force
}
$backendConfigName = "web_$Version.config"
$backendConfig = Join-Path $backendTarget $backendConfigName
Copy-Item -LiteralPath (Join-Path $backendRoot 'web.config') -Destination $backendConfig
$localAiRoot = Join-Path $projectRoot 'supporthub_local_ai_python'
$localAiItems = @(
    'app',
    'requirements.txt',
    'README.md',
    'run.bat',
    'Start-LocalAI.ps1',
    'Stop-LocalAI.ps1',
    '.env.example'
)
foreach ($item in $localAiItems) {
    Copy-Item -LiteralPath (Join-Path $localAiRoot $item) -Destination $localAiTarget -Recurse -Force
}
Copy-Item -LiteralPath (Join-Path $projectRoot 'docs\LOCAL_AI_DEPLOYMENT.md') -Destination (Join-Path $localAiTarget 'DEPLOYMENT.md')
$releaseRootPath = [System.IO.Path]::GetFullPath($releaseRoot).TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
$pythonPackageTargets = @($backendTarget, $localAiTarget)
$pythonCacheDirectories = @($pythonPackageTargets | ForEach-Object { Get-ChildItem -LiteralPath $_ -Directory -Recurse -Force | Where-Object { $_.Name -eq '__pycache__' } })
foreach ($generatedItem in $pythonCacheDirectories) {
    $generatedPath = [System.IO.Path]::GetFullPath($generatedItem.FullName)
    if (-not $generatedPath.StartsWith($releaseRootPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Generated Python item escaped the release root: $generatedPath"
    }
    Remove-Item -LiteralPath $generatedPath -Recurse -Force
}
$generatedBytecodeFiles = @($pythonPackageTargets | ForEach-Object { Get-ChildItem -LiteralPath $_ -File -Recurse -Force | Where-Object { $_.Extension -in @('.pyc', '.pyo') } })
foreach ($generatedItem in $generatedBytecodeFiles) {
    $generatedPath = [System.IO.Path]::GetFullPath($generatedItem.FullName)
    if (-not $generatedPath.StartsWith($releaseRootPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Generated Python item escaped the release root: $generatedPath"
    }
    Remove-Item -LiteralPath $generatedPath -Force
}
$databaseScripts = Get-ChildItem -LiteralPath (Join-Path $projectRoot 'scripts') -Filter 'SupportHub-*-Database-Upgrade.sql' -File
foreach ($databaseScript in $databaseScripts) {
    Copy-Item -LiteralPath $databaseScript.FullName -Destination $databaseTarget
}
$optionalDataScripts = @(
    'Insert-DefaultSla.sql',
    'Migrate-MissingTicketRootCauses.sql',
    'Migrate-ResolutionRootCauses.sql',
    'SupportHub-Reports-Catalog-Expansion.sql',
    'Reset-UAT-Master-Data.sql'
)
foreach ($dataScript in $optionalDataScripts) {
    Copy-Item -LiteralPath (Join-Path $projectRoot "scripts\$dataScript") -Destination $databaseTarget
}
$operationScripts = @('Backup-SupportHubDatabase.ps1', 'Restore-SupportHubDatabase.ps1', 'Invoke-SupportHubUpgradeRehearsal.ps1', 'Reset-SupportHubTransactions.sql', 'Test-InboundPreTicketIntegration.ps1')
foreach ($operationScript in $operationScripts) {
    Copy-Item -LiteralPath (Join-Path $projectRoot "scripts\$operationScript") -Destination $operationsTarget
}
Copy-Item -LiteralPath (Join-Path $projectRoot 'docs\DATABASE_UPGRADE_POLICY.md') -Destination (Join-Path $databaseTarget 'README.md')
Copy-Item -LiteralPath (Join-Path $projectRoot 'docs\RELEASE_SMOKE_TEST.md') -Destination (Join-Path $releaseRoot 'SMOKE-TEST.md')
Copy-Item -LiteralPath (Join-Path $projectRoot 'docs\UPGRADE_REHEARSAL.md') -Destination (Join-Path $releaseRoot 'UPGRADE-REHEARSAL.md')
Copy-Item -LiteralPath (Join-Path $projectRoot 'docs\LOGIN_RECOVERY.md') -Destination (Join-Path $releaseRoot 'LOGIN-RECOVERY.md')
Copy-Item -LiteralPath (Join-Path $projectRoot 'docs\INBOUND_API_LOCAL_TEST.md') -Destination (Join-Path $releaseRoot 'INBOUND-API-LOCAL-TEST.md')
Copy-Item -LiteralPath $releaseNotes -Destination (Join-Path $releaseRoot 'RELEASE-NOTES.md')
Copy-Item -LiteralPath $releaseLog -Destination (Join-Path $releaseRoot 'RELEASE-STEPS.md')
$implementationPlan = Join-Path $projectRoot 'MULTI_ORGANIZATION_PROJECT_DELIVERY_IMPLEMENTATION_PLAN.md'
if (Test-Path -LiteralPath $implementationPlan) {
    Copy-Item -LiteralPath $implementationPlan -Destination (Join-Path $releaseRoot 'IMPLEMENTATION-PLAN.md')
}
$backlogNotes = Join-Path $projectRoot 'docs\Backlog\Notes.md'
if (-not (Test-Path -LiteralPath $backlogNotes)) {
    $backlogNotes = Join-Path $projectRoot 'docs\Completed\Notes.md'
}
if (-not (Test-Path -LiteralPath $backlogNotes)) {
    throw 'Backlog/completed Notes.md is required.'
}
Copy-Item -LiteralPath $backlogNotes -Destination (Join-Path $releaseRoot 'BACKLOG-NOTES.md')
Copy-Item -LiteralPath (Join-Path $projectRoot 'docs\Backlog\Remaining.md') -Destination (Join-Path $releaseRoot 'REMAINING-BACKLOG.md')
$permissionCatalog = Join-Path $projectRoot 'docs\SupportHub-Permissions.xlsx'
if (Test-Path -LiteralPath $permissionCatalog) {
    Copy-Item -LiteralPath $permissionCatalog -Destination (Join-Path $releaseRoot 'PERMISSIONS.xlsx')
}
[xml]$backendXml = Get-Content -LiteralPath $backendConfig
$pathVariable = $backendXml.configuration.'system.webServer'.httpPlatform.environmentVariables.environmentVariable | Where-Object { $_.name -eq 'APPLICATION_PATH_BASE' }
$pathVariable.value = $BackendPath
$versionVariable = $backendXml.configuration.'system.webServer'.httpPlatform.environmentVariables.environmentVariable | Where-Object { $_.name -eq 'APP_VERSION' }
if (-not $versionVariable) { throw "APP_VERSION is missing from backend $backendConfigName." }
$versionVariable.value = $Version
$backendXml.Save($backendConfig)

Push-Location $backendRoot
try {
    $databaseRevision = (& '.\.venv\Scripts\python.exe' -m alembic heads).Trim()
}
finally {
    Pop-Location
}
$manifest = [ordered]@{
    application = 'Millensys Support Hub'
    version = $Version
    built_at_utc = [DateTime]::UtcNow.ToString('o')
    api_url = $ApiUrl
    base_path = $BasePath
    backend_path = $BackendPath
    backend_config_template = "backend/$backendConfigName"
    database_revision = $databaseRevision
    local_ai_included = $true
    local_ai_model = 'qwen2.5:3b'
}
$manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $releaseRoot 'release-manifest.json') -Encoding utf8
Compress-Archive -Path (Join-Path $releaseRoot '*') -DestinationPath (Join-Path ([System.IO.Path]::GetDirectoryName($releaseRoot)) "SupportHub-$Version.zip") -Force
Write-Host "Release created: $releaseRoot"
