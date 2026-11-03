param(
    [string]$BaseUrl = 'https://millensysonline.net/SupportHub/SupportHub/backend/api/v1',
    [Parameter(Mandatory = $true)][string]$ApiKey,
    [string]$ProviderKey = 'whatsapp',
    [Parameter(Mandatory = $true)][string]$Client,
    [ValidateSet('CREATE_TICKET', 'REQUEST_CALL')][string]$RequestType = 'REQUEST_CALL'
)

$ErrorActionPreference = 'Stop'
$eventId = 'local-test-' + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
$endpoint = $BaseUrl.TrimEnd('/') + '/integrations/inbound/v1/' + $ProviderKey + '/requests'
$headers = @{ 'X-API-Key' = $ApiKey }
$payload = @{
    external_message_id = $eventId
    request_type        = $RequestType
    client              = $Client
    ticket_type         = 'INCIDENT'
    title               = 'Local inbound integration test request'
    description         = 'Created by the bundled local test script without a third-party service.'
    caller_name         = 'Local Test Caller'
    caller_number       = '+201000766088'
} | ConvertTo-Json

Write-Host "Submitting $RequestType to $endpoint"
$created = Invoke-RestMethod -Method Post -Uri $endpoint -Headers $headers -ContentType 'application/json' -Body $payload
$created | Format-List
if ($created.duplicate -or -not $created.pre_ticket_number) { throw 'The first request did not create a Pre-Ticket.' }

Write-Host 'Repeating the same event to verify duplicate protection...'
$duplicate = Invoke-RestMethod -Method Post -Uri $endpoint -Headers $headers -ContentType 'application/json' -Body $payload
$duplicate | Format-List
if (-not $duplicate.duplicate -or $duplicate.pre_ticket_id -ne $created.pre_ticket_id) { throw 'Duplicate protection verification failed.' }

Write-Host "PASS: $($created.pre_ticket_number) was created once and is ready in the Pre-Ticket queue." -ForegroundColor Green
