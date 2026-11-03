# SupportHub 1.59.2 — Ticket Creation and Workflow Remediation

## Purpose

Deliver the completed ticket creation and workflow remediation work as a self-contained Windows x64 release.

## Included functionality

- Ticket-creation notification recipients are limited to active, unambiguous accounts that can access the ticket, and notification delivery revalidates access.
- Ticket assignment, reassignment, escalation, and workflow transitions create scoped in-app workflow notifications and outbox events.
- Resolution and closure require required tasks and checklist items to be complete unless an authorized, audited readiness override is supplied.
- Client confirmation records its channel, contact, note, timestamp, and confirming user where available.
- Ticket creation accepts optional initial attachments and validates candidate context when client, product, module, or service selections change.
- Ticket archival replaces destructive bulk deletion. Archived tickets are excluded from normal visibility queries and can be restored through an audited, version-protected operation.

## Database changes

- Advances the database head through `0176_workflow_readiness` and `0177_ticket_archive`.
- Adds client-confirmation, resolution-readiness, required-work-item, and ticket-archive schema support.

## Deployment

- Back up the production database before upgrade.
- Rehearse the upgrade on a production copy before controlled deployment.
- Confirm the database reaches Alembic revision `0177_ticket_archive`.
