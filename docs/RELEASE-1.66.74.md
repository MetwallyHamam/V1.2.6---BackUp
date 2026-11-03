# SupportHub 1.66.74 - Professional ticket and incident reporting

Release date: 2026-09-26

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Report preparation

- Separates Ticket Service Reports from formal Incident Reports with purpose-built sections and validation.
- Adds modern report forms with human-written fields, automatically imported ticket facts and editable structured rows.
- Imports approved worklogs into Ticket Reports and ticket lifecycle events into Incident Reports.
- Allows report-only ticket events, timeline entries and corrective actions without modifying source ticket data.
- Adds a permanent Add ticket event action to the main ticket so engineers can record operational milestones for future reports.
- Adds a privacy-aware external-AI prompt generator that returns ready-to-copy report sections without requiring an AI integration or API key.

## Export and presentation

- Replaces generic field dumps with distinct, branded PDF and Word layouts.
- Adds executive conclusions, incident identification, impact, detection and response, structured timelines, root-cause analysis, corrective actions, SLA results and closure approval to Incident Reports.
- Adds request details, classification, structured work performed, resolution, customer confirmation and SLA results to Ticket Reports.
- Omits empty optional sections instead of printing placeholder values.
- Uses compact tables, controlled section starts and non-splitting rows for cleaner pagination.
- Uses text-only Word headers and footers while retaining professional Millensys typography and report identity.

## Sharing and reports workspace

- Modernizes the Tickets Reports tab with clear report-type guidance, draft editing, publishing, exports and secure-link history.
- Modernizes the public shared-report page with responsive client, ticket, priority and status cards plus mobile-friendly structured content.
- Keeps shared URLs aligned with the configured frontend base URL and restricts sharing to published report versions.

## Deployment

- Database revision remains `0233_ticket_reports`; no new migration is required from `1.66.73`.
- Back up the production database, uploaded files and configuration before deployment.
- Deploy the packaged frontend and backend together and preserve production settings when activating `backend/web_1.66.74.config` as `backend/web.config`.

## Verification

- Backend Ruff and strict MyPy passed; all 451 backend tests passed.
- Frontend ESLint, all 87 Vitest tests, TypeScript compilation and the production build passed.
- The self-contained packaged runtime exposes `serve`, `migrate`, `seed` and `recover-admin`.
- Manifest version `1.66.74`, database head `0233_ticket_reports`, ZIP readability and forbidden-file inspection passed.

