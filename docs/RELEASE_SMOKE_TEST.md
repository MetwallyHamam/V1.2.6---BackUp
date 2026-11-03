# SupportHub release smoke test

Run this after deploying and migrating an isolated staging environment. Use a test account with access to tickets, contracts, shifts, dashboards, and report exports.

```powershell
$env:SUPPORTHUB_SMOKE_LOGIN = 'staging-smoke@example.com'
$env:SUPPORTHUB_SMOKE_PASSWORD = '<password>'
python .\backend\scripts\release_smoke.py --base-url 'https://staging.example.com/SupportHub/backend/api/v1'
```

The default run is read-only. To include the ticket-creation acceptance check, add `--create-ticket`. This leaves a clearly labelled ticket for auditability and must only be used in staging or another approved test environment.

```powershell
python .\backend\scripts\release_smoke.py --base-url 'https://staging.example.com/SupportHub/backend/api/v1' --create-ticket
```

The command exits with code `0` only when every check succeeds. Credentials are environment variables so they are not exposed in command-line process listings. Remove the two environment variables after testing:

```powershell
Remove-Item Env:\SUPPORTHUB_SMOKE_LOGIN, Env:\SUPPORTHUB_SMOKE_PASSWORD
```

## Engineer Pre-Ticket UAT — 1.60.0+

Run these steps only in staging after migrations reach `0180_pre_ticket_messages`. Keep the `engineer_pre_ticket` Feature Policy OFF until the Fast Create profile has been reviewed.

1. Confirm the Feature Policy starts `OFF`; attempts to submit or mutate a Pre-Ticket must be rejected.
2. Configure a system policy with an active Ticket Type and valid Impact/Urgency mappings for each P1–P4 value. Confirm an incomplete profile cannot be saved in `ENFORCED` mode.
3. Grant `ticket.pre_ticket.create` and `ticket.pre_ticket.view.own` to an engineer test account. Submit a Pre-Ticket at `/tickets/pre-tickets`; repeat the same browser retry and confirm only one `PRE-` record exists.
4. Grant Call Center `ticket.pre_ticket.queue.view`, `ticket.pre_ticket.queue.process`, and `ticket.create`. Claim the Pre-Ticket; verify the engineer receives the claim notification.
5. Request information with a message. Verify only the submitting engineer can respond, the original title remains unchanged, and the record returns to the queue after the response.
6. Use **Convert & Assign to Creator**. Verify one official ticket is created with source `ENGINEER_PRE_TICKET`, assigned to the original Pre-Ticket creator, and its SLA begins at ticket creation—not Pre-Ticket submission.
7. Repeat conversion/retry and confirm the linked ticket is returned without creating a second ticket. Verify audit entries and notification history for each lifecycle action.
8. Verify an inactive Pre-Ticket creator blocks conversion with `PRE_TICKET_CREATOR_UNAVAILABLE`; do not silently reroute ownership.
9. Confirm `GET /api/v1/pre-tickets/metrics/summary` is visible only to `ticket.pre_ticket.report` and does not appear as ticket response/resolution SLA.

After UAT, record the configured Ticket Type, P1–P4 mappings, policy version, test accounts, resulting ticket numbers, and approval in the deployment record.

## Support Assistant UAT — migration 0186+

Use an employee test account with ticket visibility, self-assignment, status transition, public/internal comment, handover, escalation, relation, and link-delivery permissions.

1. Open `/SupportHub/support-workspace` and verify Queue, Mine, Unassigned, In Progress, Follow-up, SLA Risk, and Pre-Tickets only expose records allowed by the account's existing visibility scope.
2. Confirm every ticket card shows Ticket Number, Client, Title, Priority, localized Status, SLA remaining/overdue state, and last update time.
3. Claim an unassigned ticket, start progress, and resolve it. Confirm the standard resolution dialog requires the configured resolution fields and service selection, and normal ticket history/audit entries are created.
4. From the card menu, verify public/internal comments, handover, escalation/help, ticket linking, customer contact/WhatsApp, Rating Link, Live Ticket Update Link, and full-ticket opening. Confirm each unavailable permission hides its action.
5. Pin two visible tickets. Refresh and reopen the Assistant; verify the personal order persists. Confirm another user does not inherit the order and that pinning does not alter ticket priority, SLA, or global queue order.
6. Change a visible ticket in the full Support Hub and confirm the Assistant refreshes after the WebSocket notification. Disconnect and reconnect the browser network and confirm the warning appears and the queue refreshes after reconnection.
7. Verify Compact and Expanded modes, independent-window opening under the configured `/SupportHub/` base path, double-click, Enter-key opening, touch operation, English, Arabic, and RTL layout.
8. Install the Support Assistant from a supported Chromium browser. Confirm it starts at `/SupportHub/support-workspace`, uses the existing authenticated session, respects logout/session expiry, and never exposes cached ticket API data while offline.
9. Record browser versions, test accounts, ticket numbers, observed audit entries, WebSocket/reconnect results, PWA installation result, and UAT approval in the deployment record.
