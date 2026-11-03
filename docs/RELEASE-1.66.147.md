# Support Hub 1.66.147

Release date: 2026-10-16

## Highlights

- Adds a configurable Ticket Type master-data flag controlling availability when creating tickets from deployment issues.
- Enables Incident and Service Request by default and hides other Ticket Types from the deployment issue form.
- Enforces the configured Ticket Type availability in the backend as well as the user interface.
- Fixes the Ticket Flags panel inside narrow deployment cards so its heading and controls remain readable.

## Database

- Advances the database head to `0269_deployment_ticket_types`.
- Adds `ticket_types.available_for_deployment_issue` and enables it for Incident and Service Request during migration.

## Deployment notes

1. Deploy `1.66.147` and allow the startup migration to reach `0269_deployment_ticket_types`.
2. Retain production configuration and recycle the Support Hub application pool.
3. Open Ticket Type master data to review the new deployment-issue availability switch.
4. Confirm the deployment issue Ticket Type list initially contains Incident and Service Request only.
