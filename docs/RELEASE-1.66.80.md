# SupportHub 1.66.80 - Scheduler performance optimization

Release date: 2026-09-27

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Scheduler optimization

- Bulk-loads running SLA tickets, policies, calendars, calendar days, holidays, recipients and existing escalation events once per cycle.
- Removes repeated ticket, policy, calendar and recipient queries from the per-clock evaluation loop.
- Records total cycle duration and individual escalation, UAT reminder, email-outbox and Outlook stage timings.
- Shows the latest scheduler timings in System Operations so expensive stages can be identified from production evidence.
- Keeps the SQL Server application lock and notification/event deduplication guarantees unchanged.

## LAN reliability

- Copies rating and live-tracking messages through an HTTP-compatible fallback when the secure Clipboard API is unavailable.
- Keeps the prepared message visible for manual selection if the browser blocks automatic copying entirely.
- Uses two backend processes as the packaged baseline; operators may retain their active `web.config` process count during deployment.

## Deployment

- Database revision remains `0233_ticket_reports`; no schema migration is required from `1.66.79`.
- Preserve the active `SECRET_KEY`, database settings, integration secrets and chosen `processesPerApplication` value when activating `backend/web_1.66.80.config`.

## Verification

- Full automated release validation and packaged-runtime checks are executed by the self-contained release builder before packaging.
