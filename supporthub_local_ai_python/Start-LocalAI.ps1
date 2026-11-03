[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$serviceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimePath = Join-Path $serviceRoot '.runtime'
$logPath = Join-Path $serviceRoot 'logs'
$pythonPath = Join-Path $serviceRoot 'venv\Scripts\python.exe'
$localAiPidPath = Join-Path $runtimePath 'local-ai.pid'
$ollamaPidPath = Join-Path $runtimePath 'ollama.pid'

New-Item -ItemType Directory -Path $runtimePath, $logPath -Force | Out-Null

function Test-Endpoint {
    param([Parameter(Mandatory = $true)][string]$Uri)
    try {
        Invoke-RestMethod -Uri $Uri -TimeoutSec 3 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Local AI virtual environment was not found. From '$serviceRoot', run: python -m venv venv; .\venv\Scripts\python.exe -m pip install -r requirements.txt"
}

$environmentPath = Join-Path $serviceRoot '.env'
if (-not (Test-Path -LiteralPath $environmentPath)) {
    Copy-Item -LiteralPath (Join-Path $serviceRoot '.env.example') -Destination $environmentPath
}

$providerLine = Get-Content -LiteralPath $environmentPath | Where-Object { $_ -match '^\s*AI_PROVIDER\s*=' } | Select-Object -Last 1
$aiProvider = if ($providerLine) { ($providerLine -split '=', 2)[1].Trim().ToUpperInvariant() } else { 'OLLAMA' }

if ($aiProvider -eq 'OLLAMA' -and -not (Test-Endpoint -Uri 'http://127.0.0.1:11434/api/tags')) {
    $ollamaCommand = Get-Command ollama.exe -ErrorAction SilentlyContinue
    if (-not $ollamaCommand) {
        $fallbackOllama = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
        if (Test-Path -LiteralPath $fallbackOllama) {
            $ollamaExecutable = $fallbackOllama
        }
        else {
            throw 'Ollama was not found. Install Ollama for Windows and ensure ollama.exe is available.'
        }
    }
    else {
        $ollamaExecutable = $ollamaCommand.Source
    }

    $ollamaProcess = Start-Process -FilePath $ollamaExecutable -ArgumentList 'serve' -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $logPath 'ollama.out.log') `
        -RedirectStandardError (Join-Path $logPath 'ollama.error.log')
    Set-Content -LiteralPath $ollamaPidPath -Value $ollamaProcess.Id -Encoding ascii

    $ollamaReady = $false
    foreach ($attempt in 1..20) {
        Start-Sleep -Milliseconds 500
        if (Test-Endpoint -Uri 'http://127.0.0.1:11434/api/tags') {
            $ollamaReady = $true
            break
        }
    }
    if (-not $ollamaReady) {
        throw "Ollama did not become ready. Check '$logPath\ollama.error.log'."
    }
}

if (-not (Test-Endpoint -Uri 'http://127.0.0.1:8090/health')) {
    $localAiProcess = Start-Process -FilePath $pythonPath `
        -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8090' `
        -WorkingDirectory $serviceRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $logPath 'local-ai.out.log') `
        -RedirectStandardError (Join-Path $logPath 'local-ai.error.log')
    Set-Content -LiteralPath $localAiPidPath -Value $localAiProcess.Id -Encoding ascii

    $localAiReady = $false
    foreach ($attempt in 1..30) {
        Start-Sleep -Milliseconds 500
        if (Test-Endpoint -Uri 'http://127.0.0.1:8090/health') {
            $localAiReady = $true
            break
        }
    }
    if (-not $localAiReady) {
        throw "Local AI did not become ready. Check '$logPath\local-ai.error.log'."
    }
}

Write-Host "Support Hub AI Gateway is running with provider $aiProvider."
Write-Host 'Local AI health: http://127.0.0.1:8090/health'
