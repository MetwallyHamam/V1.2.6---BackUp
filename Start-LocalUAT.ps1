$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$appRoot = Join-Path $root '1.16.1'
$backend = Join-Path $appRoot 'backend'
$frontend = Join-Path $appRoot 'frontend'

$backendProcess = Start-Process -FilePath (Join-Path $backend 'runtime\SupportHubBackend.exe') -ArgumentList 'serve','--host','127.0.0.1','--port','8000' -WorkingDirectory $backend -WindowStyle Hidden -PassThru
$frontendProcess = Start-Process -FilePath 'python' -ArgumentList @('"' + (Join-Path $root 'Serve-LocalUATFrontend.py') + '"') -WorkingDirectory $root -WindowStyle Hidden -PassThru

Set-Content -LiteralPath (Join-Path $root '.localuat-processes') -Value "$($backendProcess.Id)`n$($frontendProcess.Id)"
Start-Sleep -Seconds 3
Start-Process 'http://127.0.0.1:5173/SupportHub/login'
Write-Host 'Local UAT started: http://127.0.0.1:5173/SupportHub/login'
Write-Host 'Run Stop-LocalUAT.ps1 when finished.'
