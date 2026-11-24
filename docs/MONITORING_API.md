# Monitoring ticket API

All requests use the application API prefix and an API key in the `X-API-Key` header.
Create or revoke keys from the existing integration API-client administration screen/API. For
best isolation, scope each key to one client.

## Create a ticket

`POST /api/v1/integrations/api/tickets`

```json
{
  "event_id": "monitor-alert-1001",
  "client_id": 12,
  "ticket_type_code": "INCIDENT",
  "subject": "Database service unavailable",
  "description": "The database health check failed for five minutes.",
  "impact": "HIGH",
  "urgency": "HIGH"
}
```

`event_id` is the monitoring tool's unique event identifier. Repeating it returns the original
ticket instead of creating a duplicate.

## Read ticket status

`GET /api/v1/integrations/api/tickets/{ticket_id}`

## Change status

`PATCH /api/v1/integrations/api/tickets/{ticket_id}/status`

```json
{
  "event_id": "monitor-alert-1001-start",
  "status_code": "IN_PROGRESS"
}
```

Use a unique `event_id` for every status operation. Repeating an operation ID is safe and returns
`"duplicate": true`. Status changes follow the normal ticket workflow, so invalid jumps are
rejected with HTTP 409.

## Close with a resolution

```json
{
  "event_id": "monitor-alert-1001-recovered",
  "status_code": "CLOSED",
  "resolution_summary": "The database service recovered and health checks are passing.",
  "root_cause_summary": "The database service stopped unexpectedly. Monitoring restarted it."
}
```

When an active ticket is closed, the API resolves and closes it in one transaction. Both summaries
are required by the normal resolution workflow. A key cannot access tickets created by another key.

## Common responses

- `200`: status read or update succeeded.
- `201`: ticket created, or an existing ticket returned for a repeated create event.
- `401`: missing, invalid, or revoked API key.
- `404`: ticket is not owned by this API key.
- `409`: invalid workflow transition or missing required resolution information.
- `422`: request JSON validation failed.
