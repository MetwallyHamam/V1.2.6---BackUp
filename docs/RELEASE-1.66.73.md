# SupportHub 1.66.73 — Ticket reports and client action dialogs

Release date: 2026-09-26

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Ticket reports

- Adds Incident Report and Ticket Report workflows for closed tickets.
- Opens a completion form before export so ticket data can be reviewed and missing manual fields can be supplied.
- Adds the Reports tab to the Tickets workspace for returning to generated reports.
- Supports versioned PDF report publication and mobile-responsive public share links.
- Uses the configured application base URL when generating report links.
- Adds database revision `0233_ticket_reports`.

## Client actions

- Presents client access and contact actions in dialogs rather than redirecting immediately to the client page.
- Combines access viewing, addition and editing into the Show access dialog.
- Adds contact actions for WhatsApp, rating links and live tracking.
- Supports copying prepared rating and live-tracking messages and optional email or WhatsApp delivery.

## Approval planning

- Adds `docs/APPROVAL_ENHANCEMENTS.md` as a future implementation specification.
- Records that product coverage is the primary ticket-entitlement dimension and service coverage approval behavior must follow configuration.
- No approval workflow behavior or approval permissions are changed in this release.

## Deployment

- Database revision: `0233_ticket_reports`.
- Back up the production database, uploaded files and configuration before deployment.
- Run the packaged backend migration command before starting the updated application.
- Deploy the packaged frontend and backend together and preserve production settings when activating `backend/web_1.66.73.config` as `backend/web.config`.

## Verification

- Backend Ruff and strict MyPy passed; all 451 backend tests passed.
- Frontend ESLint, all 87 Vitest tests, TypeScript compilation and the production build passed.
- The packaged runtime exposes `serve`, `migrate`, `seed` and `recover-admin`.
- Manifest version `1.66.73`, database head `0233_ticket_reports`, ZIP readability and forbidden-file inspection passed.
- Artifact: `releases/SupportHub-1.66.73.zip` (52,857,386 bytes; 1,981 entries).
- SHA-256: `F9259FF5378E0844E8D2958E10AB954F7C368150F1043C24A63E390116F6591A`.

