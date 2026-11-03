# Integrations

## Monitoring webhook

`POST /api/v1/integrations/monitoring/events` creates an incident from a monitoring alert.
Authenticate with the `X-Integration-Key` header configured by `MONITORING_WEBHOOK_KEY`.

Example payload:

```json
{
  "event_id": "monitor-event-1001",
  "alert_key": "server-7/cpu",
  "client_id": 1,
  "subject": "Server CPU usage is critical",
  "description": "CPU usage has remained above 95 percent for ten minutes.",
  "severity": "CRITICAL",
  "occurred_at": "2026-07-31T10:00:00Z"
}
```

`event_id` is the idempotency key. Repeating it returns the original ticket with
`duplicate: true` and does not create another ticket. Each accepted delivery stores its
payload, correlation ID, processing state, linked ticket, attempt count, and timestamps.

The configured `INTEGRATION_ACTOR_USERNAME` must identify an active employee account.
Rotate the webhook key before making this endpoint reachable outside the local machine.

## Inbound support email

An email gateway can call `POST /api/v1/integrations/email/events` using the
`X-Integration-Key` header configured by `INBOUND_EMAIL_WEBHOOK_KEY`. A message without
`ticket_number` creates an incident. A message with a valid ticket number appends a
public comment. The supplied client must own the referenced ticket.

The gateway's stable message ID is required as `message_id` and acts as the idempotency
key, preventing provider retries from creating duplicate tickets or comments.

## Outbound email

Email delivery consumes eligible events from the transactional outbox. Configure the
`SMTP_*` settings in `backend/web.config`, then set `SMTP_ENABLED=true`. Processing can
be triggered by an administrator with `POST /api/v1/notifications/email/process`; a
production scheduler can call the same service on an interval.

Each recipient delivery is stored separately. Transient SMTP failures use exponential
backoff. A delivery becomes `DEAD` after `EMAIL_MAX_ATTEMPTS`, retaining the last error
for operational diagnosis. Successfully delivered outbox events are not sent twice.

## SMS gateway

Urgent notification events can be sent to a provider-neutral HTTP gateway. Configure
`SMS_GATEWAY_URL`, `SMS_API_TOKEN`, and `SMS_SENDER_ID`, then set `SMS_ENABLED=true`.
The gateway receives JSON containing `to`, `message`, and `sender_id` and may return a
`message_id`.

An administrator or scheduler triggers processing with
`POST /api/v1/notifications/sms/process`. Each recipient delivery has its own terminal
or retry state. Recipients without phone numbers are recorded as skipped; failed calls
use exponential backoff and become dead letters after `SMS_MAX_ATTEMPTS`.

## iTop ticket migration

Administrators can import up to 500 legacy tickets per request with
`POST /api/v1/integrations/itop/tickets/import`. Each item supplies the iTop external
ID, target client, ticket type, impact, urgency, description, original status, and
optional original creation timestamp.

The importer creates provenance text and an auditable mapping from the iTop ID to the
new ticket. Rerunning a batch safely skips mapped IDs and returns their existing Support
Hub ticket numbers.

## API clients for Millensys applications

The configurable inbound requests endpoint is `POST /api/v1/integrations/inbound/{provider_key}/requests`. Both ticket and call requests enter the Pre-Ticket queue for review. Administrators configure JSON field paths, request-type aliases, client matching, defaults, and credentials under **Site Settings → Inbound Requests API**. A third-party-free PowerShell test is documented in `INBOUND_API_LOCAL_TEST.md` and bundled with each release.

Administrators create a scoped credential with `POST /api/v1/integrations/api-clients`.
The response displays the `msh_...` API key once; only its SHA-256 hash is persisted.
Supplying a `client_id` restricts the credential to tickets for that client.

Applications create tickets at `POST /api/v1/integrations/api/tickets` using the
`X-API-Key` header and a stable `event_id`. Repeated event IDs return the original
ticket. Administrators revoke credentials with
`DELETE /api/v1/integrations/api-clients/{id}`; revoked keys immediately return 401.

## Microsoft Teams

SLA escalation events can be delivered as Microsoft Teams Adaptive Cards. Configure an
incoming webhook URL in `TEAMS_WEBHOOK_URL`, then set `TEAMS_ENABLED=true`.
Administrators or a scheduler trigger delivery with
`POST /api/v1/notifications/teams/process`.

Each outbox event is delivered once. Webhook failures use exponential backoff and move
to a durable dead-letter state after `TEAMS_MAX_ATTEMPTS`.
