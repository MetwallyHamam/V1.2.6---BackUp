# Internal Ticketing MVP

This increment provides the internal ticket foundation:

- Incident, service request, problem, change, access request, and monitoring alert types
- Human-readable numbers such as `INC-2026-000001`
- Client, branch, requester, product, module, environment, and service references
- Impact and urgency with server-side priority derivation
- New-to-closed controlled workflow transitions
- Public comments and permission-protected internal notes
- Assignment to user/team
- Optimistic concurrency through the ticket version
- Immutable status history and audit records
- Permission- and scope-filtered ticket queries
- Related, duplicate, parent/child, and caused-by ticket links
- Unified permission-filtered activity timeline for status, comments, attachments,
  assignments, ticket relationships, and knowledge links

The backend remains authoritative for priority, visibility, internal-note access,
and status transitions. The browser does not independently decide whether an
operation is allowed.

Relationship creation and removal require `ticket.relate`. Both tickets must be
visible to the acting user, symmetric reverse duplicates are rejected, and all
changes are audited.

Primary endpoints:

- `GET|POST /api/v1/tickets`
- `GET /api/v1/tickets/{ticket_id}`
- `POST /api/v1/tickets/{ticket_id}/transition`
- `GET|POST /api/v1/tickets/{ticket_id}/comments`
- `GET /api/v1/tickets/{ticket_id}/timeline`
- `POST /api/v1/tickets/{ticket_id}/assignment`
- `GET|POST /api/v1/tickets/{ticket_id}/relations`
- `DELETE /api/v1/tickets/{ticket_id}/relations/{relation_id}`
- `GET /api/v1/ticket-types`
- `GET /api/v1/ticket-statuses`
