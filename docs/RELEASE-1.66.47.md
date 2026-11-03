# SupportHub 1.66.47 — Client profile and dashboards

Status: **SELF-CONTAINED WINDOWS X64 RELEASE — READY FOR CONTROLLED DEPLOYMENT**

## Correction

- Includes completed resolution SLA evidence for tickets in Resolved or Closed status in the client profile and client hours summary.
- Keeps reopened tickets excluded, even when they retain a previously completed SLA clock.
- Adds a regression test matching an imported resolved ticket with both resolution and closure timestamps.
- Adds personal move, resize, and save controls to Support Now widgets and the main Executive dashboard widgets.
- Removes the duplicate Tickets needing attention section from Support Now. The Need attention card opens the same ticket set used for its count.
- Adds Top 3 Agents, status and priority charts, and a seven-day ticket creation chart to Support Now.
- Includes all functionality from `1.66.46`.

## Database

- Database head remains `0206_ticket_flags`; no schema migration is introduced.
