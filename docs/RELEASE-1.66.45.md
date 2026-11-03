# SupportHub 1.66.45 — Client hours correction

Status: **SELF-CONTAINED WINDOWS X64 RELEASE — READY FOR CONTROLLED DEPLOYMENT**

## Correction

- Prevents the client-hours API from failing when completed work belongs to a client that is now inactive. Historical hours remain visible for that client.
- Includes all functionality from `1.66.44`.

## Database

- Database head remains `0206_ticket_flags`; no schema migration is introduced.

## Verification

- The client profile and hours API test covers an inactive client.
