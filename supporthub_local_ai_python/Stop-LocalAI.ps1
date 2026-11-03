[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$serviceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimePath = Join-Path $serviceRoot '.runtime'

function Stop-ManagedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$PidFile,
        [Parameter(Mandatory = $true)][string]$Label
    )

    if (-not (Test-Path -LiteralPath $PidFile)) {
        Write-Host "$Label was not started by Start-LocalAI.ps1."
        return
    }

    $savedPid = 0
    [void][int]::TryParse((Get-Content -LiteralPath $PidFile -Raw).Trim(), [ref]$savedPid)
    $process = Get-Process -Id $savedPid -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $savedPid -Force
        Write-Host "$Label stopped."
    }
    else {
        Write-Host "$Label was already stopped."
    }
    Remove-Item -LiteralPath $PidFile -Force
}

Stop-ManagedProcess -PidFile (Join-Path $runtimePath 'local-ai.pid') -Label 'Support Hub Local AI'
Stop-ManagedProcess -PidFile (Join-Path $runtimePath 'ollama.pid') -Label 'Ollama'

