$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$file = Join-Path $root '.localuat-processes'
if (Test-Path -LiteralPath $file) {
    foreach ($processId in Get-Content -LiteralPath $file) {
        if ($processId -match '^\d+$') { Stop-Process -Id ([int]$processId) -ErrorAction SilentlyContinue }
    }
    Remove-Item -LiteralPath $file -Force
}
Write-Host 'Local UAT stopped.'
