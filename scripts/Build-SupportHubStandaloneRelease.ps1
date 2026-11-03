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
if (Test-Path -LiteralPath $releaseRoot) { throw "Release $Version already exists." }

# Start from the normal release so frontend paths, backend configuration and
# the database revision manifest remain identical to the supported deployment.
& (Join-Path $PSScriptRoot 'Build-SupportHubRelease.ps1') -Version $Version -OutputRoot $OutputRoot -ApiUrl $ApiUrl -BasePath $BasePath -BackendPath $BackendPath
if ($LASTEXITCODE -ne 0) { throw 'Base release build failed.' }

$backendRoot = Join-Path $projectRoot 'backend'
$backendTarget = Join-Path $releaseRoot 'backend'
$buildRoot = Join-Path $projectRoot '.standalone-build'
$python = Join-Path $backendRoot '.venv\Scripts\python.exe'
Push-Location $backendRoot
try {
    & $python -m PyInstaller --noconfirm --clean --onedir --name SupportHubBackend --distpath (Join-Path $buildRoot 'dist') --workpath (Join-Path $buildRoot 'work') --specpath $buildRoot --collect-all app --collect-all pymssql --collect-all pyodbc --collect-all uvicorn --collect-all alembic --hidden-import sqlalchemy.dialects.mssql.pymssql --hidden-import sqlalchemy.dialects.mssql.pyodbc '.\supporthub_runtime.py'
    if ($LASTEXITCODE -ne 0) { throw 'Standalone backend build failed.' }
}
finally { Pop-Location }

Copy-Item -LiteralPath (Join-Path $buildRoot 'dist\SupportHubBackend') -Destination (Join-Path $backendTarget 'runtime') -Recurse -Force
$configPath = Join-Path $backendTarget "web_$Version.config"
[xml]$config = Get-Content -LiteralPath $configPath
$platform = $config.configuration.'system.webServer'.httpPlatform
$platform.processPath = '.\runtime\SupportHubBackend.exe'
$platform.arguments = 'serve --host 127.0.0.1 --port %HTTP_PLATFORM_PORT%'
$config.Save($configPath)

$manifestPath = Join-Path $releaseRoot 'release-manifest.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$manifest | Add-Member -NotePropertyName deployment_mode -NotePropertyValue 'self-contained-windows-x64'
$manifest | Add-Member -NotePropertyName requires_python_install -NotePropertyValue $false
$manifest | ConvertTo-Json | Set-Content -LiteralPath $manifestPath -Encoding utf8

$zipPath = Join-Path ([System.IO.Path]::GetDirectoryName($releaseRoot)) "SupportHub-$Version.zip"
Remove-Item -LiteralPath $zipPath -Force
Compress-Archive -Path (Join-Path $releaseRoot '*') -DestinationPath $zipPath
Write-Host "Standalone release created: $zipPath"
