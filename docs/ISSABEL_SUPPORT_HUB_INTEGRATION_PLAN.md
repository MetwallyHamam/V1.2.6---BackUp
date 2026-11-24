# Issabel–Support Hub Integration Plan

**Status:** Proposed  
**Prepared:** 2026-11-23  
**Target PBX:** Issabel 4.0 / Asterisk 11.25.3 on CentOS 7.9  
**Target application:** Millensys Support Hub

## 1. Purpose

Integrate Issabel telephony with Support Hub so Call Center and Support employees can identify callers, register and track call requests, link calls to clients and tickets, place controlled outbound calls, and review call history without giving either system direct write access to the other's database.

The integration must preserve Support Hub authorization, audit, ticket entitlement, and SLA rules. A telephone call or Pre-Ticket does not start an official ticket SLA. The SLA begins only when Support Hub creates the official ticket through its existing governed workflow.

## 2. Scope

### Phase 1 — Minimum viable integration

- Receive completed inbound, outbound, missed, busy, and failed call records.
- Normalize external telephone numbers.
- Match callers to Support Hub clients and contacts.
- Create an idempotent `REQUEST_CALL` Pre-Ticket for configured call scenarios.
- Show the Issabel call identifier and call details on the Pre-Ticket.
- Provide an unmatched-caller review queue.
- Reconcile AMI events against CDR records.
- Provide operational logs, retry, health status, and alerting.

### Phase 2 — Live call experience

- Consume live Asterisk Manager Interface (AMI) events.
- Display an incoming-call notification to authorized Support Hub users.
- Open the matching client/contact profile and recent tickets.
- Show agent, extension, queue, direction, and current call state.
- Allow the user to link a live or completed call to a ticket or Pre-Ticket.

### Phase 3 — Controlled click-to-call

- Add click-to-call actions on authorized client, contact, ticket, and Pre-Ticket screens.
- Originate calls through a restricted AMI account and an approved dial-plan context.
- Validate agent-to-extension ownership and destination-number rules.
- Audit every originate request and its outcome.

### Phase 4 — Recordings and reporting

- Store recording metadata, not recording binaries, in Support Hub.
- Retrieve recordings through an authenticated proxy with permission and scope checks.
- Apply retention, legal, privacy, and download policies.
- Add queue, agent, missed-call, callback, disposition, and ticket-link reports.

### Out of scope for the first release

- Replacing Issabel queues, agents, trunks, or dial plans.
- Giving Issabel direct access to the Support Hub SQL Server database.
- Giving Support Hub write access to the Issabel CDR database.
- Browser-based WebRTC softphones.
- Automatic official-ticket creation for every call.
- Public exposure of AMI or recording folders.
- Upgrading the legacy Issabel server as part of the connector delivery.

## 3. Architecture

```text
Phones / trunks
      |
Issabel 4 / Asterisk 11
      |-- AMI TCP 5038: live events and restricted Originate
      |-- CDR: completed-call reconciliation (read only)
      |-- recordings: metadata and protected retrieval (optional)
      |
Issabel Integration Gateway
      |-- durable event store and retry queue
      |-- number normalization and event correlation
      |-- health monitoring and structured logs
      |
      +-- HTTPS + scoped API key --> Support Hub integration API
                                      |-- Pre-Ticket intake
                                      |-- telephony call records
                                      |-- client/contact matching
                                      |-- live notifications
                                      |-- click-to-call authorization
                                      |-- audit and reporting
```

The gateway should run on a supported, patched host separate from the CentOS 7 PBX. It maintains the long-running AMI connection and isolates Asterisk 11 protocol details from Support Hub. It must buffer events locally when Support Hub is temporarily unavailable.

## 4. Required from Issabel

### 4.1 Ownership and access

The Issabel/PBX administrator must provide:

- A named technical owner and maintenance window.
- Issabel private IP address, hostname, site, and environment name.
- Integration Gateway private IP address.
- Network path between the gateway and Issabel.
- SSH access for the PBX administrator; the application team does not require unrestricted root access.
- A tested configuration backup and PBX recovery procedure before changes.

### 4.2 PBX inventory

Provide the following inventory:

- Exact Issabel and Asterisk versions.
- Extension technology: `SIP`, `PJSIP`, `IAX2`, DAHDI, or combination.
- Extension ranges and extension-to-employee mapping.
- Queue numbers, queue names, agent identifiers, and membership model.
- Inbound routes and DIDs relevant to Support Hub.
- Outbound route names, permitted destinations, trunk prefixes, and dialing prefixes.
- Internal dial-plan context used by trusted extensions.
- Business country code, area code, and telephone-number formats.
- Time zone, NTP source, and current clock synchronization status.
- Busy, no-answer, abandoned, transferred, and answered call behavior.

Recommended discovery commands include:

```bash
asterisk -rx "core show version"
asterisk -rx "manager show settings"
asterisk -rx "cdr show status"
asterisk -rx "queue show"
asterisk -rx "sip show peers"
asterisk -rx "pjsip show endpoints"
asterisk -rx "dialplan show from-internal"
date
timedatectl
```

Commands for unloaded channel drivers may fail and can be ignored. Passwords and secrets must be removed from supplied evidence.

### 4.3 Restricted AMI account

Create one dedicated AMI account for the gateway. Do not reuse an Issabel administrator account.

Proposed starting configuration in `/etc/asterisk/manager_custom.conf`:

```ini
[supporthub]
secret = REPLACE_WITH_LONG_RANDOM_SECRET
deny = 0.0.0.0/0.0.0.0
permit = GATEWAY_IP/255.255.255.255
read = call,agent,user,reporting,cdr,dialplan
write = originate
writetimeout = 5000
```

Final permissions must be confirmed against the actual Asterisk 11 build. The account must not receive `command`, `system`, or `config` write access. If Phase 3 is not enabled, omit all write permissions.

Acceptance evidence:

- AMI listens only on the intended interface or is firewall-restricted.
- TCP 5038 is reachable only from the gateway.
- Invalid-source and invalid-password attempts are rejected.
- The account can receive required call/queue events.
- `Originate` works only when Phase 3 is approved.
- The account cannot execute arbitrary CLI or configuration commands.

### 4.4 CDR access

Provide:

- CDR backend type: MySQL/MariaDB, ODBC, CSV, or other.
- Database and table names.
- Available columns, especially `uniqueid`, linked ID if present, source, destination, channel, destination channel, start, answer, end, duration, billable seconds, disposition, account code, and user field.
- Data retention and purge schedule.
- A dedicated read-only database account restricted by source IP, if direct CDR reconciliation is selected.

The gateway must never update Issabel CDR data. If safe database access cannot be provided, use a scheduled export or PBX-side read-only publisher.

### 4.5 Recordings, when Phase 4 is approved

Provide:

- Whether call recording is enabled and for which calls.
- Recording directory and naming convention.
- Mapping from CDR/AMI identifiers to recording files.
- File format, retention period, storage capacity, and archive process.
- Consent, privacy, and legal rules.
- A least-privilege retrieval method for the gateway.

Recording directories must not become public web directories. Support Hub must authorize playback and download for every request.

### 4.6 Issabel security requirements

- Keep AMI private; never publish TCP 5038 to the internet.
- Restrict AMI, CDR, SSH, and recording access by gateway IP and firewall.
- Use unique secrets and an agreed rotation procedure.
- Synchronize time with a trusted NTP source.
- Forward relevant authentication and service failures to monitoring.
- Document configuration-file changes so Issabel regeneration does not overwrite them.
- Maintain a separate migration plan because CentOS 7 and Asterisk 11 are legacy platforms.

## 5. Required from Support Hub

### 5.1 Existing capabilities to configure and reuse

Support Hub already provides the following foundation:

- `POST /api/v1/integrations/inbound/v1/{provider_key}/requests`
- Idempotency using an external event ID.
- Configurable JSON field paths and request-type aliases.
- `REQUEST_CALL` intake into the governed Pre-Ticket queue.
- Client matching by code and/or exact name.
- Scoped, revocable API credentials whose full key is shown once.
- Client and ticket-type lookup endpoints.
- Status lookup by external event ID.
- Audit, notifications, Call Center claiming, and controlled ticket conversion.

Configuration required under **Site Settings → Inbound Requests API**:

- Create an enabled provider profile such as `issabel`.
- Use `PRE_TICKET` processing mode for the first release.
- Map the gateway's fields to `event_id`, `request_type`, `client`, `ticket_type`, `title`, `description`, `caller_name`, and `caller_number`.
- Map the gateway call-request value to `REQUEST_CALL`.
- Select an active default ticket type and proposed priority.
- Create a provider-scoped API credential and store it only in the gateway secret store.
- Configure an active integration actor.
- Enable Engineer Pre-Tickets and confirm Call Center permissions.

### 5.2 New Support Hub telephony backend

Implement an additive telephony module with:

- `telephony_connections`: non-secret Issabel connection metadata and enabled features.
- `telephony_extensions`: Support Hub user to PBX extension mapping with effective dates.
- `telephony_calls`: one correlated logical call per Asterisk linked ID or correlation key.
- `telephony_call_legs`: channels, transfers, queue legs, agents, times, and dispositions.
- `telephony_call_links`: links to client, contact, Pre-Ticket, and ticket.
- `telephony_recordings`: recording metadata and retention state.
- `telephony_event_deliveries`: event idempotency, payload hash, processing status, attempts, and errors.
- `telephony_originate_requests`: requester, agent extension, normalized destination, result, and audit correlation.

Required service behavior:

- Accept versioned, authenticated gateway events.
- Reject duplicate event IDs without duplicating calls or Pre-Tickets.
- Preserve raw external identifiers and source timestamps.
- Normalize telephone numbers to a configurable canonical format, preferably E.164 where possible.
- Match exact normalized numbers only; ambiguous matches go to review.
- Apply client, branch, ticket, and user visibility scopes to every read.
- Keep call ingestion separate from official-ticket creation.
- Correlate live AMI events, CDR completion, transfers, and recordings.
- Record structured errors without logging credentials or unnecessary caller data.

### 5.3 Proposed Support Hub endpoints

Gateway-facing endpoints:

```text
POST /api/v1/integrations/telephony/v1/events
POST /api/v1/integrations/telephony/v1/cdr
POST /api/v1/integrations/telephony/v1/recordings/metadata
GET  /api/v1/integrations/telephony/v1/events/{event_id}
GET  /api/v1/integrations/telephony/v1/health
```

User-facing endpoints:

```text
GET  /api/v1/telephony/calls
GET  /api/v1/telephony/calls/{call_id}
POST /api/v1/telephony/calls/{call_id}/links
POST /api/v1/telephony/calls/{call_id}/create-pre-ticket
POST /api/v1/telephony/originate
GET  /api/v1/telephony/recordings/{recording_id}/stream
```

The existing configurable inbound API remains the Phase 1 path for `REQUEST_CALL`. New endpoints are required where the current generic Pre-Ticket payload cannot represent full call lifecycle, legs, transfers, agent state, recording metadata, or click-to-call.

### 5.4 Permissions

Add narrow permissions; do not authorize by profile name:

```text
telephony.call.view
telephony.call.view.department
telephony.call.link
telephony.call.create_pre_ticket
telephony.originate
telephony.recording.play
telephony.recording.download
telephony.report.view
telephony.integration.manage
telephony.extension.manage
```

Default grants should be conservative. Recording download should be more restricted than playback. Integration management must not imply access to call content.

### 5.5 User interface

Add:

- Telephony settings for connections, features, number rules, queues, and extensions.
- Call history with server-side filtering and scoped export.
- Incoming-call notification with matched client/contact and recent tickets.
- Unmatched/ambiguous caller review workflow.
- Call detail timeline showing queue, agent, transfers, disposition, links, and recording.
- Link/unlink actions with audit evidence.
- Click-to-call buttons that show the selected agent extension and normalized destination before confirmation.
- Health panel for AMI, last event, last CDR reconciliation, backlog, and failures.

### 5.6 Notifications and live updates

Use the existing notification infrastructure for durable alerts. Live-call popups may use the existing single-instance WebSocket capability during initial deployment. If Support Hub is scaled to multiple application instances, Redis or an equivalent fan-out mechanism is required before live event delivery can be considered reliable.

## 6. Required from the Integration Gateway

The gateway is a separate deliverable and must provide:

- Persistent AMI connection with reconnect and bounded exponential backoff.
- AMI message parsing compatible with Asterisk 11 event shapes.
- Call/leg state machine and correlation using `Uniqueid`, linked identifiers when available, channels, and timestamps.
- Durable local queue so events survive restart and Support Hub downtime.
- CDR polling or import with a high-water mark and overlap window.
- Idempotent HTTPS delivery to Support Hub.
- Configurable number normalization and prefix rules.
- TLS certificate validation.
- Secret storage outside source code and logs.
- Structured logs, metrics, health endpoint, and failure alerts.
- Graceful shutdown and restart recovery.
- Data-retention limits for raw payloads and local queues.
- No inbound public listener unless explicitly required and secured.

Recommended deployment: a managed Windows or supported Linux service close to Issabel and Support Hub. Do not install new integration runtimes directly on the legacy PBX unless no safe alternative exists.

## 7. Data contract

### 7.1 Initial `REQUEST_CALL` payload

Example gateway payload using the existing configurable inbound API:

```json
{
  "event_id": "issabel:pbx01:call:1700001234.55",
  "request_type": "REQUEST_CALL",
  "client": "CLIENT-CODE",
  "ticket_type": "CALL",
  "title": "Incoming support call from +201001234567",
  "description": "Queue: 600; disposition: MISSED; started: 2026-11-23T10:15:00+02:00",
  "caller_name": "Optional caller ID name",
  "caller_number": "+201001234567"
}
```

The exact external event ID must remain stable across retries. It must include the PBX identity because two PBXs can generate the same Asterisk `Uniqueid`.

### 7.2 Full telephony event fields

The versioned telephony contract should include:

- Schema version, event ID, event type, PBX ID, occurred time, and received time.
- Asterisk unique ID, linked ID when available, parent ID, channel, and destination channel.
- Direction, source, destination, normalized external number, DID, context, and trunk.
- Queue, agent, extension, disposition, hangup cause, duration, and billable seconds.
- Recording reference and checksum when available.
- Optional Support Hub client/contact hints; hints never bypass server-side validation.

## 8. Business rules

- Do not create a Pre-Ticket for every low-level AMI event.
- Create at most one configured Pre-Ticket per logical call and scenario.
- Recommended automatic scenarios: missed queue calls, abandoned calls above an agreed threshold, and explicitly classified support calls.
- Answered calls may be stored as call history without automatically creating work.
- Unknown or ambiguous numbers remain unmatched; never guess a client.
- A number matching multiple contacts requires Call Center selection.
- Transfers remain legs of the same logical call where correlation evidence supports it.
- Reprocessed AMI/CDR data updates the same call and never creates duplicates.
- Click-to-call requires an active mapped extension, permission, allowed destination, and an approved context.
- Official ticket creation continues through current Pre-Ticket conversion, entitlement, assignment, authorization, and SLA logic.

## 9. Security and privacy controls

- Private network or VPN between Issabel, gateway, and Support Hub.
- HTTPS with certificate validation for every gateway-to-Support Hub request.
- IP-restricted and least-privilege AMI and CDR accounts.
- API keys stored encrypted or in the operating-system secret store and rotated.
- No secrets in repository files, URLs, payload logs, or screenshots.
- Rate limiting and maximum payload sizes on integration endpoints.
- Replay protection through stable event IDs and payload hashes.
- Audit log for viewing, linking, originating, playing, and downloading recordings.
- Phone-number masking where full display is not necessary.
- Defined retention for raw events, call metadata, recordings, and logs.
- Backup and restore coverage for new Support Hub tables and gateway durable state.
- Threat review before enabling recordings or outbound origination.

## 10. Delivery plan

### Stage 0 — Discovery and approval

1. Name PBX, network, Support Hub, security, and Call Center owners.
2. Complete the Issabel inventory and sample-call capture.
3. Define which calls create Pre-Tickets.
4. Approve number normalization, retention, recording, and click-to-call policies.
5. Confirm the gateway host and network routes.
6. Record baseline PBX and Support Hub backups.

**Exit:** signed data mapping, security design, test cases, and rollback plan.

### Stage 1 — Connectivity proof

1. Create the read-only AMI account without `originate` permission.
2. Restrict firewall access to the gateway.
3. Capture representative inbound, missed, answered, transferred, queued, and outbound calls.
4. Confirm stable identifiers and Asterisk 11 event shapes.
5. Confirm CDR availability and time synchronization.
6. Configure the Support Hub `issabel` provider and test credential.
7. Submit a synthetic `REQUEST_CALL` twice and verify one Pre-Ticket.

**Exit:** secure connectivity and end-to-end idempotent Pre-Ticket proof.

### Stage 2 — Phase 1 build

1. Build the gateway AMI consumer, durable queue, CDR reconciliation, and Support Hub client.
2. Add telephony persistence, permissions, settings, APIs, and migrations.
3. Implement exact number matching and unmatched review.
4. Add call history, call detail, Pre-Ticket link, health, and audit UI.
5. Add monitoring, retry, dead-letter handling, and reconciliation tools.
6. Add automated unit, integration, authorization, migration, and failure-recovery tests.

**Exit:** all Phase 1 acceptance criteria pass in test.

### Stage 3 — Staging and UAT

1. Deploy to an isolated or controlled staging path.
2. Run the complete call scenario matrix.
3. Validate client/branch/user scope and Call Center permissions.
4. Test Support Hub outage, gateway restart, AMI reconnect, duplicate delivery, late CDR, and clock skew.
5. Reconcile daily PBX CDR count and dispositions against Support Hub.
6. Obtain Call Center, PBX, security, and application-owner approval.

**Exit:** signed UAT evidence and production runbook.

### Stage 4 — Production pilot

1. Enable one queue and a small group of extensions.
2. Initially operate in call-history mode; enable automatic Pre-Tickets after reconciliation is stable.
3. Monitor event delay, backlog, duplicates, unmatched rate, and PBX resource use.
4. Review results daily during the pilot.
5. Expand queue by queue after approval.

**Exit:** stable pilot for an agreed observation period with no critical defects.

### Stage 5 — Optional capabilities

Enable in separate approvals:

1. Live incoming-call notifications.
2. Click-to-call and AMI `originate` permission.
3. Protected recording playback.
4. Recording download, if legally and operationally approved.
5. Advanced agent and queue reporting.

## 11. Test matrix

At minimum, test:

- Known and unknown inbound caller.
- Number matching one contact and multiple contacts.
- Answered, no-answer, busy, failed, abandoned, and missed calls.
- Queue call answered by an agent.
- Blind and attended transfer.
- Outbound answered and failed calls.
- Repeated AMI events and repeated API delivery.
- Gateway restart during a call.
- AMI disconnect and reconnect.
- Support Hub unavailable and later recovered.
- CDR arriving late or disagreeing with an interim AMI state.
- Cairo time-zone boundaries and clock skew.
- Unauthorized call, recording, export, and originate access.
- User attempting to originate from another employee's extension.
- Invalid, premium, international, and malformed destinations.
- API-key revocation and rotation.
- Recording missing, expired, or moved.
- Retention purge and audit preservation.

## 12. Acceptance criteria

Phase 1 is accepted when:

- At least 99% of supported completed calls appear in Support Hub within the agreed latency.
- Replaying any delivered event creates no duplicate call or Pre-Ticket.
- The daily supported-call count and dispositions reconcile with Issabel CDR within the agreed tolerance.
- Known callers match correctly; ambiguous callers are never automatically assigned.
- Configured missed/abandoned calls create exactly one `REQUEST_CALL` Pre-Ticket.
- Existing Call Center claim and conversion workflows remain authoritative.
- No AMI, database, API, or recording secret appears in logs or source control.
- Authorization tests prove call and recording data cannot cross user/client scope.
- Gateway and Support Hub recover without event loss after tested restarts and outages.
- PBX call handling shows no unacceptable performance degradation.
- Operations has approved monitoring, backup, restore, key rotation, and rollback runbooks.

Phase 3 is accepted only when unauthorized destinations and extensions are denied, every request is audited, and call outcomes correlate to the originating request.

## 13. Monitoring and operations

Monitor:

- AMI connected state and reconnect count.
- Timestamp and age of last AMI event.
- Timestamp and result of last CDR reconciliation.
- Gateway queue depth, oldest queued event, retry rate, and dead letters.
- Support Hub API success, latency, authentication failures, and throttling.
- Duplicate-event rate, unmatched-caller rate, and AMI/CDR mismatch count.
- Recording retrieval failures and storage capacity, if enabled.

Runbooks must cover:

- Restarting the gateway safely.
- AMI credential and Support Hub API-key rotation.
- Replaying dead letters without duplicates.
- Rebuilding a date range from CDR.
- Investigating missing or duplicate calls.
- Disabling automatic Pre-Ticket creation while retaining call capture.
- Disabling click-to-call immediately.
- Revoking recording access.

## 14. Rollback

Rollback must be feature-based and preserve evidence:

1. Disable automatic Pre-Ticket rules.
2. Disable live notifications and click-to-call in Support Hub.
3. Revoke the Support Hub integration API key.
4. Disable the dedicated AMI account and firewall rule.
5. Stop the gateway after its durable queue and diagnostic state are preserved.
6. Keep already created calls, Pre-Tickets, tickets, and audit records; do not delete business evidence.
7. Revert Issabel configuration only from the verified backup and through the PBX administrator.

## 15. Information checklist before implementation

### Issabel team

- [ ] PBX owner and maintenance window
- [ ] Private IP/hostname and gateway IP
- [ ] Version and channel-driver inventory
- [ ] Extensions, employees, queues, agents, DIDs, and routes
- [ ] Dial-plan context and prefix rules
- [ ] Dedicated restricted AMI account
- [ ] CDR backend, schema, sample rows, and retention
- [ ] Sample AMI traces for the agreed call scenarios
- [ ] Recording policy and metadata, if applicable
- [ ] Time synchronization evidence
- [ ] Firewall, backup, recovery, and rollback approval

### Support Hub team

- [ ] Application owner, Call Center owner, and security owner
- [ ] Staging and production base URLs
- [ ] Enabled `issabel` inbound provider profile
- [ ] Scoped API credential and integration actor
- [ ] Active default call ticket type and proposed priority
- [ ] Pre-Ticket feature policy and Call Center permissions
- [ ] Telephone normalization and client/contact matching rules
- [ ] New telephony schema/API/UI design approval
- [ ] Retention, masking, audit, recording, and export policies
- [ ] Monitoring, backup, restore, deployment, and rollback runbooks

### Gateway team

- [ ] Supported host and service account
- [ ] Network reachability to Issabel and Support Hub
- [ ] Secret store and TLS trust configuration
- [ ] Durable storage and retention capacity
- [ ] AMI/CDR compatibility proof
- [ ] Metrics, health checks, structured logs, and alerts
- [ ] Deployment, upgrade, restart, replay, and recovery procedures

## 16. Decisions required before coding

1. Which exact call scenarios should create a `REQUEST_CALL` Pre-Ticket?
2. Is Phase 1 limited to one PBX, one queue, and one site?
3. What canonical telephone format and prefix rules apply?
4. Should client matching use contact numbers only, client main numbers, or both?
5. How should duplicate numbers across clients be handled operationally?
6. What are the call metadata and raw-event retention periods?
7. Are recordings excluded, playback-only, or downloadable?
8. Which roles may view calls, link calls, originate calls, and access recordings?
9. Which outbound destinations are allowed, and is user confirmation mandatory?
10. What reconciliation tolerance and production pilot duration are acceptable?

