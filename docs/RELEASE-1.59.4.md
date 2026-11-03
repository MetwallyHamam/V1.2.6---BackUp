# SupportHub 1.59.4 — SQL Server Breached-Ticket Drill-Through Correction

## Purpose

Correct the SQL Server parameter-limit failure when opening a dashboard breached-ticket drill-through containing more than 2,100 tickets.

## Correction

- Replaces the in-memory breached-ticket ID list in the ticket-list route with the existing database-side `TicketSlaClock` filter.
- Prevents SQL Server ODBC error `07002` caused by expanding a large `tickets.id IN (...)` parameter list during count and paging queries.
- Preserves dashboard and ticket-list breached-ticket filtering while allowing production-scale queues.

## Deployment

- Deploy this release over 1.59.3.
- No database migration is required; the database head remains `0177_ticket_archive`.
