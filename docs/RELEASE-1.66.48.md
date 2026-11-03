# SupportHub 1.66.48 — Customer work hour widgets

Status: **SELF-CONTAINED WINDOWS X64 RELEASE — READY FOR CONTROLLED DEPLOYMENT**

## Corrections

- Loads the customer consumption and work-hour charts on the Executive dashboard.
- Includes Resolved and Closed tickets with completed resolution SLA evidence in Client working and saved hours.
- Renames the customer work-hour chart to Support work hours per customer. It uses approved ticket worklogs where available, and completed resolution SLA time for tickets without an approved worklog in the selected period.
- Includes all functionality from `1.66.47`.

## Database

- Database head remains `0206_ticket_flags`; no schema migration is introduced.
