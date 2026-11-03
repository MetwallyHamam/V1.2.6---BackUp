# SupportHub 1.66.46 — Client hours widget paging

Status: **SELF-CONTAINED WINDOWS X64 RELEASE — READY FOR CONTROLLED DEPLOYMENT**

## Corrections

- Shows the top three clients per page in the client working and saved hours widget on every dashboard, with controls for remaining clients.
- Opens the client profile with the widget's date range when a client row is selected, keeping the report cards aligned with the displayed hours.
- Uses the same closed-ticket eligibility as the client profile, so reopened tickets with old SLA clocks do not inflate widget hours.
- Includes all functionality from `1.66.45`.

## Database

- Database head remains `0206_ticket_flags`; no schema migration is introduced.
